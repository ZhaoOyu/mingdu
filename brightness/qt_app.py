"""Cross-platform Qt tray UI. Hardware requests run in a bounded worker queue."""
from . import language
from .language import tr
from hashlib import sha256
from pathlib import Path
import sys

from PySide6.QtCore import QEvent, QLockFile, QObject, QPoint, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QCursor, QPalette
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
from .presentation import brightness_summary, device_kind
from .qt_style import blended_color, brightness_icon, panel_style, symbol_icon


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
        language.select(self.settings.data.get("interfaceLanguage"))
        self.startup = startup if startup is not None else Startup()
        self.cards, self.device_menus, self.device_icons = {}, {}, {}
        self.quitting = self._applying_theme = self._status_error = False
        self.popover_mode = QSystemTrayIcon.isSystemTrayAvailable()
        if self.popover_mode:
            self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self._build_content()
        self.tray = TrayIcon(symbol_icon(), self)
        self.tray.activated.connect(self._activated)
        self.tray.scrolled.connect(self._scroll)
        self.tray.messageClicked.connect(self.show_panel)
        self.tray.show()
        controller.rebuilt.connect(self.rebuild)
        controller.changed.connect(self.update_values)
        controller.status.connect(self._status)
        controller.failure.connect(self._notify_error)
        self._build_menu()
        self._apply_theme()
        self.update_values()

    def _build_content(self):
        controller, demo = self.controller, self.demo
        self.setWindowTitle(tr("明度" + (" · 演示" if demo else "")))
        self.resize(380, 500)
        self.setMinimumWidth(360)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("content")
        self.layout = QVBoxLayout(content)
        self.layout.setContentsMargins(18, 16, 18, 16)
        self.layout.setSpacing(12)
        scroll.setWidget(content)
        self.setCentralWidget(scroll)
        heading = QHBoxLayout()
        heading.setSpacing(10)
        self.header_icon = QLabel()
        self.header_icon.setFixedSize(24, 24)
        heading.addWidget(self.header_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        heading.addWidget(text_label(tr("明度 · 演示" if demo else "明度"), "hero"), 1)
        self.count_label = text_label(tr("检测中"), "muted")
        heading.addWidget(self.count_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self.refresh_button = QPushButton()
        self.refresh_button.setFixedSize(30, 30)
        self.refresh_button.setToolTip(tr("重新检测显示器并读取当前亮度"))
        self.refresh_button.setAccessibleName(tr("刷新显示器"))
        self.refresh_button.clicked.connect(controller.refresh)
        heading.addWidget(self.refresh_button)
        self.layout.addLayout(heading)
        self.separator()
        self.devices = QWidget()
        self.devices_layout = QVBoxLayout(self.devices)
        self.devices_layout.setContentsMargins(0, 0, 0, 0)
        self.devices_layout.setSpacing(10)
        self.layout.addWidget(self.devices)
        self.layout.addWidget(text_label(tr("所有屏幕 · 快捷亮度"), "muted"))
        presets = QHBoxLayout()
        presets.setSpacing(6)
        self.preset_buttons = []
        for title, value in [("夜间 25%", 25), ("日常 60%", 60), ("明亮 100%", 100)]:
            button = QPushButton(tr(title))
            button.setCheckable(True)
            button.setToolTip(tr(f"将所有显示器调节到 {value}%"))
            button.clicked.connect(lambda _checked=False, v=value: controller.set_all(v))
            presets.addWidget(button, 1)
            self.preset_buttons.append(button)
        self.layout.addLayout(presets)
        self.separator()
        self.target = QComboBox()
        self.target.setMinimumWidth(150)
        self.target.setMaximumWidth(220)
        self.target.setAccessibleName(tr("状态栏显示与滚轮控制的屏幕"))
        self.target.setToolTip(tr("选择圆环显示和托盘滚轮控制的屏幕；滚轮支持取决于桌面环境。"))
        self.target.currentIndexChanged.connect(self._target_changed)
        target_row = QHBoxLayout()
        target_row.addWidget(text_label(tr("状态栏屏幕")), 1)
        target_row.addWidget(self.target)
        self.layout.addLayout(target_row)
        self.status_label = text_label(tr("正在连接显示器…"), "muted")
        self.status_label.setMinimumHeight(30)
        self.layout.addWidget(self.status_label)
        actions = QHBoxLayout()
        self.diagnostic_button = QPushButton(tr("设备诊断 ▸"))
        self.diagnostic_button.setCheckable(True)
        self.diagnostic_button.toggled.connect(self._toggle_diagnostics)
        actions.addWidget(self.diagnostic_button, 1)
        quit_button = QPushButton(tr("退出"))
        quit_button.clicked.connect(self.quit)
        actions.addWidget(quit_button)
        self.layout.addLayout(actions)
        self.diagnostics = QTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setFixedHeight(140)
        self.diagnostics.hide()
        self.layout.addWidget(self.diagnostics)
        self.separator()
        language_row = QHBoxLayout()
        language_row.addWidget(QLabel("Language" if language.english() else "语言"), 1)
        languages = self.languages = QComboBox()
        languages.addItems(language.names())
        languages.setCurrentIndex(language.CHOICES.index(language.choice))
        languages.currentIndexChanged.connect(self.change_language)
        language_row.addWidget(languages)
        self.layout.addLayout(language_row)
        footer = QHBoxLayout()
        self.autostart = QCheckBox(tr("登录系统时启动"))
        self.autostart.setEnabled(not demo)
        try:
            self.autostart.setChecked(self.startup.enabled)
        except OSError:
            pass
        self.autostart.toggled.connect(self._set_autostart)
        footer.addWidget(self.autostart, 1)
        footer.addWidget(text_label("v" + __version__, "muted"))
        self.layout.addLayout(footer)

    def change_language(self, index):
        value = language.CHOICES[index]
        if not self.demo:
            try:
                self.settings.set_language(value)
            except OSError as error:
                self._status(str(error), True)
                return
        language.select(value)
        self.cards.clear()
        self.device_icons.clear()
        self._build_content()
        self.rebuild()
        self.update_values()
        self._status(getattr(self, "_last_message", "已读取当前亮度"), self._status_error)

    def separator(self):
        line = QFrame()
        line.setObjectName("separator")
        line.setFixedHeight(1)
        self.layout.addWidget(line)

    def _fit_panel(self):
        if self.quitting:
            return
        self.layout.invalidate()
        self.layout.activate()
        height = self.layout.totalHeightForWidth(self.width())
        if height <= 0:
            height = self.layout.sizeHint().height()
        screen = self.screen()
        limit = min(720, screen.availableGeometry().height() - 40) if screen else 720
        self.resize(self.width(), min(limit, max(340, height + 4)))

    def _apply_theme(self):
        if self._applying_theme:
            return
        self._applying_theme = True
        try:
            palette = QApplication.palette()
            self.setStyleSheet(panel_style(palette))
            self.header_icon.setPixmap(symbol_icon().pixmap(24, 24))
            self.refresh_button.setIcon(symbol_icon("refresh"))
            self.setWindowIcon(symbol_icon())
            for icon in self.device_icons.values():
                icon.setPixmap(symbol_icon("monitor", blended_color(palette, 0.62)).pixmap(24, 24))
            self._status(getattr(self, "_last_message", "正在连接显示器…"), self._status_error)
            self._update_tray()
        finally:
            self._applying_theme = False

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ApplicationPaletteChange and hasattr(self, "tray"):
            self._apply_theme()

    def event(self, event):
        if event.type() == QEvent.Type.WindowDeactivate and getattr(self, "popover_mode", False):
            QTimer.singleShot(0, self._hide_if_inactive)
        return super().event(event)

    def _hide_if_inactive(self):
        if (self.popover_mode and not self.isActiveWindow() and not QApplication.activePopupWidget()
                and not QApplication.activeModalWidget()):
            self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _build_menu(self):
        old_menu = getattr(self, "menu", None)
        self.menu = QMenu(self)
        self.menu.addAction(tr("打开亮度面板…"), self.show_panel)
        self.menu.addSeparator()
        self.device_menus = {}
        self.control_actions = []
        for device in self.controller.displays.values():
            submenu = self.menu.addMenu(tr(device.name))
            submenu.addAction(tr("提高 5%"), lambda checked=False, key=device.id: self.controller.adjust(key, 5))
            submenu.addAction(tr("降低 5%"), lambda checked=False, key=device.id: self.controller.adjust(key, -5))
            submenu.addSeparator()
            for value in (25, 50, 75, 100):
                submenu.addAction(f"{value}%", lambda checked=False, key=device.id, v=value: self.controller.request(key, v))
            self.device_menus[device.id] = submenu
            self.control_actions.append(submenu.menuAction())
        if not self.device_menus:
            self.menu.addAction(tr("未发现可调节的显示器")).setEnabled(False)
        self.menu.addSeparator()
        for title, callback in [("全部提高 5%", lambda: self.controller.adjust_all(5)),
                                ("全部降低 5%", lambda: self.controller.adjust_all(-5)),
                                ("夜间 · 25%", lambda: self.controller.set_all(25)),
                                ("日常 · 60%", lambda: self.controller.set_all(60))]:
            self.control_actions.append(self.menu.addAction(tr(title), callback))
        self.menu.addSeparator()
        self.refresh_action = self.menu.addAction(tr("重新检测显示器"), self.controller.refresh)
        self.menu.addAction(tr("退出明度"), self.quit)
        self.tray.setContextMenu(None if sys.platform == "darwin" else self.menu)
        if old_menu:
            old_menu.deleteLater()

    def rebuild(self):
        while self.devices_layout.count():
            item = self.devices_layout.takeAt(0)
            item.widget().deleteLater()
        self.cards.clear()
        self.device_icons.clear()
        for device in self.controller.displays.values():
            card = QFrame()
            card.setObjectName("card")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(0, 2, 0, 12)
            layout.setSpacing(6)
            heading = QHBoxLayout()
            heading.setSpacing(12)
            icon = QLabel()
            icon.setFixedSize(24, 24)
            heading.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)
            self.device_icons[device.id] = icon
            title = QVBoxLayout()
            title.setSpacing(2)
            title.addWidget(text_label(tr(device.name), "monitor"))
            title.addWidget(text_label(tr(device_kind(device.kind)), "muted"))
            heading.addLayout(title, 1)
            value_label = text_label(f"{device.value}%", "value")
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_label.setMinimumWidth(60)
            heading.addWidget(value_label, 0, Qt.AlignmentFlag.AlignVCenter)
            layout.addLayout(heading)
            row = QHBoxLayout()
            row.setSpacing(6)
            minus, plus = QPushButton(tr("−")), QPushButton(tr("+"))
            for button, text in ((minus, "降低 5%"), (plus, "提高 5%")):
                button.setFixedWidth(30)
                button.setToolTip(tr(text))
                button.setAccessibleName(tr(device.name + "：" + text))
            minus.clicked.connect(lambda _checked=False, key=device.id: self.controller.adjust(key, -5))
            plus.clicked.connect(lambda _checked=False, key=device.id: self.controller.adjust(key, 5))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(1, 100)
            slider.setPageStep(5)
            slider.setValue(max(1, device.value))
            slider.setAccessibleName(tr(f"{device.name}亮度百分比"))
            slider.valueChanged.connect(lambda value, key=device.id: self.controller.request(key, value))
            row.addWidget(minus)
            row.addWidget(slider, 1)
            row.addWidget(plus)
            layout.addLayout(row)
            self.devices_layout.addWidget(card)
            self.cards[device.id] = (slider, value_label)
        if not self.cards:
            self.devices_layout.addWidget(text_label(tr("未发现可调节的显示器。\n检查连接并开启 DDC/CI，再点击刷新。")))
        self.count_label.setText(tr(f"{len(self.cards)} 台屏幕"))
        self.target.blockSignals(True)
        self.target.clear()
        self.target.addItem(tr("所有显示器"), "all")
        for device in self.controller.displays.values():
            self.target.addItem(tr(device.name), device.id)
        index = self.target.findData(self.settings.data["scroll_target"])
        self.target.setCurrentIndex(max(0, index))
        self.target.blockSignals(False)
        self.diagnostic_button.setChecked(not bool(self.cards))
        self._build_menu()
        self._apply_theme()
        QTimer.singleShot(0, self._fit_panel)

    def _update_tray(self):
        controller = self.controller
        self.tray_summary = brightness_summary(controller.displays, controller.confirmed,
                                               self.target.currentData(), controller.errors)
        self.tray.setIcon(brightness_icon(self.tray_summary))
        values = "\n".join(f"{controller.displays[key].name}: {value}%" for key, value in controller.confirmed.items()
                           if key in controller.displays)
        self.tray.setToolTip(tr(("明度 · 演示\n" if self.demo else "明度\n")
                            + self.tray_summary.description + ("\n" + values if values else "")))

    def update_values(self):
        controller = self.controller
        for key, value in controller.values.items():
            if key in self.cards:
                slider, number = self.cards[key]
                slider.blockSignals(True)
                slider.setValue(max(1, value))
                slider.blockSignals(False)
                number.setText(tr(f"{value}%" + (" ·" if key in controller.pending else "")))
            if key in self.device_menus:
                self.device_menus[key].setTitle(tr(f"{controller.displays[key].name}   {value}%" + (" …" if key in controller.pending else "")))
        self.devices.setEnabled(not controller.scanning)
        enabled = bool(controller.displays) and not controller.scanning
        for button, value in zip(self.preset_buttons, (25, 60, 100)):
            button.setEnabled(enabled)
            button.setChecked(bool(controller.confirmed) and not controller.pending and not controller.errors
                              and all(v == value for v in controller.confirmed.values()))
        for action in self.control_actions:
            action.setEnabled(enabled)
        self.refresh_action.setEnabled(not controller.scanning)
        self.refresh_button.setEnabled(not controller.scanning)
        self._update_tray()
        devices = [f"{d.name} · {d.kind} · 最大原始值 {d.maximum}" for d in controller.displays.values()]
        help_text = "连接或唤醒显示器后请刷新。外接显示器需开启 DDC/CI。\n新版 macOS 安装包自带辅助工具；源码运行请参阅安装指南。"
        self.diagnostics.setPlainText(tr("\n\n".join(devices + controller.warnings + [help_text])))

    def _toggle_diagnostics(self, enabled):
        self.diagnostics.setVisible(enabled)
        self.diagnostic_button.setText(tr("设备诊断 ▾" if enabled else "设备诊断 ▸"))
        QTimer.singleShot(0, self._fit_panel)

    def _target_changed(self, _index):
        self._update_tray()
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
        self._last_message = message
        self._status_error = error
        self.status_label.setText(tr(("演示 · " if self.demo else "") + message.removeprefix("演示 · ")))
        dark = QApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128
        color = ("#ff938c" if dark else "#b3261e") if error else blended_color(QApplication.palette(), 0.62).name()
        self.status_label.setStyleSheet(f"color: {color};")
        QTimer.singleShot(0, self._fit_panel)

    def _notify_error(self, message):
        self.tray.showMessage(tr("明度：亮度调节失败"), tr(message[:240]), QSystemTrayIcon.MessageIcon.Warning)

    def _activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Context and sys.platform == "darwin":
            self.menu.popup(QCursor.pos())
            return
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick,
                      QSystemTrayIcon.ActivationReason.MiddleClick):
            if self.isVisible() and self.popover_mode:
                self.hide()
            else:
                self.show_panel()

    def show_panel(self):
        self._fit_panel()
        if self.popover_mode:
            tray_rect = self.tray.geometry()
            anchor = tray_rect.center() if tray_rect.isValid() else QCursor.pos()
            screen = QApplication.screenAt(anchor) or self.screen()
            area = screen.availableGeometry()
            x = max(area.left() + 8, min(anchor.x() - self.width() // 2, area.right() - self.width() - 8))
            below = anchor.y() < area.center().y()
            y = (tray_rect.bottom() + 6 if tray_rect.isValid() else area.top() + 6) if below else anchor.y() - self.height() - 12
            y = max(area.top() + 6, min(y, area.bottom() - self.height() - 6))
            self.move(QPoint(x, y))
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
        panel.show_panel()
    QTimer.singleShot(0, controller.refresh)
    # Some tray hosts become available only after login finishes.
    QTimer.singleShot(4000, lambda: panel.show() if not QSystemTrayIcon.isSystemTrayAvailable() else None)
    app.aboutToQuit.connect(controller.close)
    app.aboutToQuit.connect(instance.close)
    return app.exec()
