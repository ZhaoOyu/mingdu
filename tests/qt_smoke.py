"""Real Qt widgets + simulated hardware; safe on hosted CI without monitors."""
import os
from pathlib import Path
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from brightness.backends import DemoHardware, HardwareError, ScanResult
from brightness.qt_app import Controller, Panel
from brightness.settings import Settings
from brightness.startup import Startup


def settle(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Qt state did not settle")


def main():
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    class Hardware(DemoHardware):
        fail = False
        empty = False
        def discover(self):
            return ScanResult([], ["测试：无设备"]) if self.empty else super().discover()
        def set_brightness(self, display, value):
            if self.fail:
                raise HardwareError("测试：设备断开")
            return super().set_brightness(display, value)
    hardware = Hardware()
    with tempfile.TemporaryDirectory() as temporary:
        controller = Controller(hardware)
        panel = Panel(controller, demo=True, settings=Settings(temporary),
                      startup=Startup("linux", root=temporary, command=["test"]))
        panel.show()
        try:
            controller.refresh()
            settle(lambda: not controller.scanning and len(controller.displays) == 2)
            first, second = list(controller.displays)
            slider = panel.cards[first][0]
            for value in (40, 41, 42, 43):
                slider.setValue(value)
            settle(lambda: not controller.pending)
            assert hardware.values[first] == 43
            assert hardware.values[second] == 80
            # QAction's checked bool must not overwrite the captured display ID.
            panel.device_menus[second].actions()[1].trigger()
            settle(lambda: not controller.pending)
            assert hardware.values[second] == 75
            panel.target.setCurrentIndex(panel.target.findData(first))
            panel._scroll(5)
            settle(lambda: not controller.pending)
            assert hardware.values[first] == 48 and hardware.values[second] == 75
            panel.preset_buttons[0].click()
            settle(lambda: not controller.pending)
            assert set(hardware.values.values()) == {25}
            hardware.fail = True
            controller.request(first, 90)
            settle(lambda: not controller.pending)
            assert controller.values[first] == 25 and controller.errors
            assert "失败" in panel.status_label.text()
            hardware.fail = False
            controller.request(first, 65)
            controller.request(second, 80)
            controller.refresh()
            settle(lambda: not controller.scanning)
            assert controller.values[first] == 65 and controller.values[second] == 80
            assert not controller.errors
            assert not panel.autostart.isEnabled()
            # The result of an old request must not move a newer slider backward.
            controller.request(first, 70)
            revision = controller.revisions[first]
            controller._event("write", (first, revision - 1, 60, None))
            assert controller.values[first] == 70
            settle(lambda: not controller.pending)
            assert controller.values[first] == 70
            panel.resize(520, 820)
            QApplication.processEvents()
            (ROOT / "dist").mkdir(exist_ok=True)
            assert panel.grab().save(str(ROOT / "dist/qt-preview.png"))
            hardware.empty = True
            panel.refresh_button.click()
            settle(lambda: not controller.scanning)
            assert not controller.displays
            assert not panel.preset_buttons[0].isEnabled()
            assert panel.diagnostic_button.isChecked()
            print("PASS: Qt widgets, tray actions, multi-monitor presets, debounce, readback, stale result, failure rollback, refresh and empty state")
        finally:
            panel.quit()
            controller.worker.thread.join(2)
            panel.deleteLater()
            QApplication.processEvents()


if __name__ == "__main__":
    main()
