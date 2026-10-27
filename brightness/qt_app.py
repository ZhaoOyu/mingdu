"""Cross-platform Qt tray UI. Hardware requests run in a bounded worker queue."""
from hashlib import sha256
from pathlib import Path
import sys

from PySide6.QtCore import QEvent, QLockFile, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QSlider,
    QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget,
)

from . import __version__
from .settings import Settings
from .startup import Startup
from .worker import HardwareWorker


STYLE = """
QMainWindow, QWidget#content { background: #f5f4f1; color: #272b30; }
QLabel { color: #272b30; background: transparent; }
QLabel#hero { font-size: 26px; font-weight: bold; }
QLabel#muted { color: #6d7177; font-size: 12px; }
QLabel#eyebrow { color: #a85c24; font-size: 12px; font-weight: bold; }
QFrame#card { background: white; border: 1px solid #e5e3de; border-radius: 14px; }
QLabel#monitor { font-size: 15px; font-weight: bold; }
QLabel#value { color: #b65d27; font-size: 25px; font-weight: bold; }
QPushButton, QComboBox { background: white; color: #30343a; border: 1px solid #dedcd7; border-radius: 8px; padding: 8px; }
QPushButton:hover { background: #fff4e8; }
QPushButton:disabled { color: #999; background: #eeece8; }
QSlider::groove:horizontal { height: 6px; background: #eae8e3; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #d78043; border-radius: 3px; }
QSlider::handle:horizontal { background: white; border: 2px solid #cd743b; width: 16px; margin: -6px 0; border-radius: 9px; }
QCheckBox { color: #30343a; background: transparent; spacing: 10px; }
QTextEdit { background: white; color: #30343a; border: 1px solid #dedcd7; border-radius: 8px; padding: 8px; }
QScrollArea { border: none; background: #f5f4f1; }
"""


def sun_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#dc8445"), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawEllipse(20, 20, 24, 24)
    for angle in range(0, 360, 45):
        painter.save()
        painter.translate(32, 32)
        painter.rotate(angle)
        painter.drawLine(0, -23, 0, -28)
        painter.restore()
    painter.end()
    return QIcon(pixmap)


class Controller(QObject):
    events = Signal(str, object)
    rebuilt = Signal()
    changed = Signal()
    status = Signal(str, bool)
    failure = Signal(str)

    def __init__(self, hardware):
        super().__init__()
        self.displays, self.values, self.confirmed = {}, {}, {}
        self.revisions, self.timers, self.errors = {}, {}, {}
        self.pending = set()
        self.warnings = []
        self.scanning = self.closed = False
        self.events.connect(self._event, Qt.ConnectionType.QueuedConnection)
        self.worker = HardwareWorker(hardware, self._emit)

    def _emit(self, event, data):
        if not self.closed:
            self.events.emit(event, data)

    def refresh(self):
        if self.closed or self.scanning:
            return
        for key in list(self.timers):
            self._dispatch(key)
        self.scanning = True
        self.changed.emit()
        self.status.emit("正在检测显示器，DDC/CI 设备可能需要一些时间…", False)
        self.worker.scan()

    def request(self, key, value):
        if self.closed or self.scanning or key not in self.displays:
            return
        self.values[key] = max(1, min(100, round(value)))
        self.revisions[key] = self.revisions.get(key, 0) + 1
        self.pending.add(key)
        self.errors.pop(key, None)
        if key in self.timers:
            self.timers[key].stop()
            self.timers[key].deleteLater()
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda k=key: self._dispatch(k))
        self.timers[key] = timer
        timer.start(160)
        self.changed.emit()
        self.status.emit("正在应用亮度…", False)

    def adjust(self, key, delta):
        self.request(key, self.values.get(key, 50) + delta)

    def set_all(self, value):
        for key in self.displays:
            self.request(key, value)

    def adjust_all(self, delta):
        for key in self.displays:
            self.adjust(key, delta)

    def _dispatch(self, key):
        timer = self.timers.pop(key, None)
        if timer:
            timer.stop()
            timer.deleteLater()
        self.worker.write(self.displays[key], self.values[key], self.revisions[key])

    @Slot(str, object)
    def _event(self, event, data):
        if self.closed:
            return
        if event == "scan":
            self.scanning = False
            self.displays = {d.id: d for d in data.displays}
            self.values = {d.id: d.value for d in data.displays}
            self.confirmed = self.values.copy()
            self.pending.clear()
            self.errors.clear()
            self.warnings = data.warnings
            self.rebuilt.emit()
            self.changed.emit()
            self.status.emit("已读取当前亮度" if self.displays else "未发现可调节设备，请展开设备诊断。", False)
        elif event == "scan-error":
            self.scanning = False
            self.changed.emit()
            self.status.emit(f"设备检测失败：{data}", True)
        elif event == "write":
            key, revision, value, error = data
            if key not in self.displays:
                return
            if error is None:
                self.confirmed[key] = value
            if revision != self.revisions.get(key):
                return
            self.pending.discard(key)
            self.values[key] = self.confirmed[key]
            if error:
                self.errors[key] = error
                self.warnings = (self.warnings + [f"{self.displays[key].name}：{error}"])[-12:]
                self.failure.emit(f"{self.displays[key].name}：{error}")
            self.changed.emit()
            if self.errors:
                self.status.emit("部分设备调节失败，已回到最近确认值；请查看诊断。", True)
            elif not self.pending and not self.scanning:
                self.status.emit("亮度已更新", False)

    def close(self):
        self.closed = True
        for timer in self.timers.values():
            timer.stop()
        self.timers.clear()
        self.worker.stop()


class TrayIcon(QSystemTrayIcon):
    scrolled = Signal(int)

    def event(self, event):
        if event.type() == QEvent.Type.Wheel:
            delta = event.angleDelta().y()
            if delta:
                self.scrolled.emit(5 if delta > 0 else -5)
                return True
        return super().event(event)


def text_label(text, name=None):
    label = QLabel(text)
    label.setWordWrap(True)
    if name:
        label.setObjectName(name)
    return label


class Panel(QMainWindow):
    def __init__(self, controller, demo=False, settings=None, startup=None):
        super().__init__()
        self.controller, self.demo = controller, demo
        self.settings = settings if settings is not None else Settings()
        self.startup = startup if startup is not None else Startup()
        self.cards, self.device_menus = {}, {}
        self.quitting = False
        self.setWindowTitle("明度 Brightness" + (" · 演示" if demo else ""))
        self.setWindowIcon(sun_icon())
        self.resize(520, 760)
        self.setStyleSheet(STYLE)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("content")
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(18)
        scroll.setWidget(content)
        self.setCentralWidget(scroll)
        heading = QHBoxLayout()
        heading.addWidget(text_label("让屏幕，刚刚好。", "hero"), 1)
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(controller.refresh)
        heading.addWidget(self.refresh_button)
        self.layout.addLayout(heading)
        self.layout.addWidget(text_label("从状态栏，轻松掌控每一块屏幕。", "muted"))
        self.count_label = text_label("显示器 / DISPLAYS", "eyebrow")
        self.layout.addWidget(self.count_label)
        self.devices = QWidget()
        self.devices_layout = QVBoxLayout(self.devices)
        self.devices_layout.setContentsMargins(0, 0, 0, 0)
        self.devices_layout.setSpacing(12)
        self.layout.addWidget(self.devices)
        presets = QHBoxLayout()
        self.preset_buttons = []
        for title, value in [("夜间 · 25%", 25), ("日常 · 60%", 60), ("明亮 · 100%", 100)]:
            button = QPushButton(title)
            button.clicked.connect(lambda _checked=False, v=value: controller.set_all(v))
            presets.addWidget(button)
            self.preset_buttons.append(button)
        self.layout.addLayout(presets)
        self.target = QComboBox()
        self.target.setAccessibleName("状态栏滚轮控制的显示器")
        self.target.currentIndexChanged.connect(self._target_changed)
        target_row = QHBoxLayout()
        target_row.addWidget(text_label("滚轮控制（托盘宿主支持时）", "muted"))
        target_row.addWidget(self.target, 1)
        self.layout.addLayout(target_row)
        self.autostart = QCheckBox("登录后自动启动")
        self.autostart.setEnabled(not demo)
        try:
            self.autostart.setChecked(self.startup.enabled)
        except OSError:
            pass
        self.autostart.toggled.connect(self._set_autostart)
        self.layout.addWidget(self.autostart)
        self.status_label = text_label("正在连接显示器…", "muted")
        self.layout.addWidget(self.status_label)
        self.diagnostic_button = QPushButton("设备信息与诊断 ▸")
        self.diagnostic_button.setCheckable(True)
        self.diagnostic_button.toggled.connect(self._toggle_diagnostics)
        self.layout.addWidget(self.diagnostic_button)
        self.diagnostics = QTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setMinimumHeight(140)
        self.diagnostics.hide()
        self.layout.addWidget(self.diagnostics)
        self.layout.addWidget(text_label(f"明度 {__version__} · MIT 开源软件" + (" · 模拟设备，不改变真实亮度" if demo else ""), "muted"))
        self.layout.addStretch()
        self.tray = TrayIcon(sun_icon(), self)
        self.tray.activated.connect(self._activated)
        self.tray.scrolled.connect(self._scroll)
        self.tray.messageClicked.connect(self.show_panel)
        self.tray.show()
        controller.rebuilt.connect(self.rebuild)
        controller.changed.connect(self.update_values)
        controller.status.connect(self._status)
        controller.failure.connect(self._notify_error)
        self._build_menu()
        self.update_values()

    def _build_menu(self):
        old_menu = getattr(self, "menu", None)
        self.menu = QMenu(self)
        self.menu.addAction("打开亮度面板…", self.show_panel)
        self.menu.addSeparator()
        self.device_menus = {}
        self.control_actions = []
        for device in self.controller.displays.values():
            submenu = self.menu.addMenu(device.name)
            submenu.addAction("提高 5%", lambda checked=False, key=device.id: self.controller.adjust(key, 5))
            submenu.addAction("降低 5%", lambda checked=False, key=device.id: self.controller.adjust(key, -5))
            submenu.addSeparator()
            for value in (25, 50, 75, 100):
                submenu.addAction(f"{value}%", lambda checked=False, key=device.id, v=value: self.controller.request(key, v))
            self.device_menus[device.id] = submenu
            self.control_actions.append(submenu.menuAction())
        if not self.device_menus:
            self.menu.addAction("未发现可调节的显示器").setEnabled(False)
        self.menu.addSeparator()
        for title, callback in [("全部提高 5%", lambda: self.controller.adjust_all(5)),
                                ("全部降低 5%", lambda: self.controller.adjust_all(-5)),
                                ("夜间 · 25%", lambda: self.controller.set_all(25)),
                                ("日常 · 60%", lambda: self.controller.set_all(60))]:
            self.control_actions.append(self.menu.addAction(title, callback))
        self.menu.addSeparator()
        self.refresh_action = self.menu.addAction("重新检测显示器", self.controller.refresh)
        self.menu.addAction("退出明度", self.quit)
        self.tray.setContextMenu(self.menu)
        if old_menu:
            old_menu.deleteLater()

    def rebuild(self):
        while self.devices_layout.count():
            item = self.devices_layout.takeAt(0)
            item.widget().deleteLater()
        self.cards.clear()
        for device in self.controller.displays.values():
            card = QFrame()
            card.setObjectName("card")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(18, 18, 18, 18)
            heading = QHBoxLayout()
            title = QVBoxLayout()
            title.addWidget(text_label(device.name, "monitor"))
            kind = {"backlight": "Linux 内置背光", "ddc": "DDC/CI · Linux", "wmi": "Windows 内置背光",
                    "win-ddc": "DDC/CI · Windows", "apple": "Apple 背光", "m1ddc": "DDC/CI · Apple Silicon",
                    "ddcctl": "DDC/CI · Intel Mac", "demo": "演示设备"}.get(device.kind, device.kind)
            title.addWidget(text_label(kind, "muted"))
            heading.addLayout(title, 1)
            value_label = text_label(f"{device.value}%", "value")
            heading.addWidget(value_label)
            layout.addLayout(heading)
            row = QHBoxLayout()
            minus, plus = QPushButton("−"), QPushButton("+")
            minus.setFixedWidth(40)
            plus.setFixedWidth(40)
            minus.clicked.connect(lambda _checked=False, key=device.id: self.controller.adjust(key, -5))
            plus.clicked.connect(lambda _checked=False, key=device.id: self.controller.adjust(key, 5))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(1, 100)
            slider.setPageStep(5)
            slider.setValue(max(1, device.value))
            slider.setAccessibleName(f"{device.name}亮度百分比")
            slider.valueChanged.connect(lambda value, key=device.id: self.controller.request(key, value))
            row.addWidget(minus)
            row.addWidget(slider, 1)
            row.addWidget(plus)
            layout.addLayout(row)
            self.devices_layout.addWidget(card)
            self.cards[device.id] = (slider, value_label)
        if not self.cards:
            self.devices_layout.addWidget(text_label("未发现可调节设备。\n检查连接、驱动或 DDC/CI 设置后点击刷新。"))
        self.count_label.setText(f"显示器 / DISPLAYS · {len(self.cards)} 台")
        self.target.blockSignals(True)
        self.target.clear()
        self.target.addItem("所有显示器", "all")
        for device in self.controller.displays.values():
            self.target.addItem(device.name, device.id)
        index = self.target.findData(self.settings.data["scroll_target"])
        self.target.setCurrentIndex(max(0, index))
        self.target.blockSignals(False)
        self.diagnostic_button.setChecked(not bool(self.cards))
        self._build_menu()

    def update_values(self):
        controller = self.controller
        for key, value in controller.values.items():
            if key in self.cards:
                slider, number = self.cards[key]
                slider.blockSignals(True)
                slider.setValue(max(1, value))
                slider.blockSignals(False)
                number.setText(f"{value}%" + (" ·" if key in controller.pending else ""))
            if key in self.device_menus:
                self.device_menus[key].setTitle(f"{controller.displays[key].name}   {value}%" + (" …" if key in controller.pending else ""))
        self.devices.setEnabled(not controller.scanning)
        enabled = bool(controller.displays) and not controller.scanning
        for button in self.preset_buttons:
            button.setEnabled(enabled)
        for action in self.control_actions:
            action.setEnabled(enabled)
        self.refresh_action.setEnabled(not controller.scanning)
        self.refresh_button.setEnabled(not controller.scanning)
        tooltip = "\n".join(f"{controller.displays[key].name}: {value}%" for key, value in controller.values.items())
        self.tray.setToolTip(("明度 · 演示\n" if self.demo else "明度\n") + (tooltip or "未发现设备"))
        devices = [f"{d.name} · {d.kind} · 最大原始值 {d.maximum}" for d in controller.displays.values()]
        help_text = "连接或唤醒显示器后请刷新。外接显示器需开启 DDC/CI。\nmacOS 需安装相应硬件辅助工具；详见 README。"
        self.diagnostics.setPlainText("\n\n".join(devices + controller.warnings + [help_text]))

    def _toggle_diagnostics(self, enabled):
        self.diagnostics.setVisible(enabled)
        self.diagnostic_button.setText("设备信息与诊断 ▾" if enabled else "设备信息与诊断 ▸")

    def _target_changed(self, _index):
        self.settings.data["scroll_target"] = self.target.currentData() or "all"
        if not self.demo:
            try:
                self.settings.save()
            except OSError as exc:
                self._status(f"无法保存偏好设置：{exc}", True)

    def _set_autostart(self, enabled):
        if self.demo:
            return
        try:
            self.startup.set_enabled(enabled)
        except (OSError, ValueError) as exc:
            self.autostart.blockSignals(True)
            self.autostart.setChecked(not enabled)
            self.autostart.blockSignals(False)
            self._status(f"无法设置登录自启：{exc}", True)

    def _scroll(self, delta):
        key = self.target.currentData()
        if key in self.controller.displays:
            self.controller.adjust(key, delta)
        else:
            self.controller.adjust_all(delta)

    def _status(self, message, error):
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #b23c28;" if error else "color: #6d7177;")

    def _notify_error(self, message):
        self.tray.showMessage("明度：亮度调节失败", message[:240], QSystemTrayIcon.MessageIcon.Warning)

    def _activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick,
                      QSystemTrayIcon.ActivationReason.MiddleClick):
            self.show_panel()

    def show_panel(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if not self.quitting and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
        else:
            self.quit()
            event.accept()

    def quit(self):
        self.quitting = True
        self.controller.close()
        self.tray.hide()
        QApplication.instance().quit()


class SingleInstance:
    """Lock arbitrates startup, local IPC activates the existing window."""
    def __init__(self, settings, demo=False):
        root = settings.path.parent
        root.mkdir(parents=True, exist_ok=True)
        suffix = "demo" if demo else "main"
        self.lock = QLockFile(str(root / f"qt-{suffix}.lock"))
        self.name = "mingdu-" + sha256((str(root.resolve()) + suffix).encode()).hexdigest()[:24]
        self.server = QLocalServer()

    def acquire(self):
        if not self.lock.tryLock(0):
            client = QLocalSocket()
            client.connectToServer(self.name)
            if client.waitForConnected(1500):
                client.write(b"show")
                client.waitForBytesWritten(1500)
                client.disconnectFromServer()
                return False
            raise OSError("明度可能正在启动，或实例锁不可访问。请稍后重试。")
        QLocalServer.removeServer(self.name)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not self.server.listen(self.name):
            self.lock.unlock()
            raise OSError(self.server.errorString())
        return True

    def activate_on_connection(self, panel):
        def activate():
            while self.server.hasPendingConnections():
                socket = self.server.nextPendingConnection()
                panel.show_panel()
                socket.disconnectFromServer()
                socket.deleteLater()
        self.server.newConnection.connect(activate)

    def close(self):
        self.server.close()
        self.lock.unlock()


def run(hardware, args):
    app = QApplication([sys.argv[0]])
    app.setApplicationName("Mingdu")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Mingdu")
    app.setQuitOnLastWindowClosed(False)
    settings = Settings()
    instance = SingleInstance(settings, args.demo)
    try:
        if not instance.acquire():
            return 0
    except OSError as exc:
        QMessageBox.critical(None, "无法启动明度", str(exc))
        return 1
    controller = Controller(hardware)
    panel = Panel(controller, args.demo, settings=settings)
    instance.activate_on_connection(panel)
    if not args.background or not QSystemTrayIcon.isSystemTrayAvailable():
        panel.show()
    QTimer.singleShot(0, controller.refresh)
    # Some tray hosts become available only after login finishes.
    QTimer.singleShot(4000, lambda: panel.show() if not QSystemTrayIcon.isSystemTrayAvailable() else None)
    app.aboutToQuit.connect(controller.close)
    app.aboutToQuit.connect(instance.close)
    return app.exec()
