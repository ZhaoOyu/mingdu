"""Exercise real GTK widgets with simulated hardware. Run in Xvfb or a desktop."""
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brightness.app import BrightnessApp, Gdk, GLib, Gtk
from brightness.backends import DemoHardware, HardwareError, ScanResult
from brightness.settings import Settings


def pump_until(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("GTK state did not settle before timeout")


def main():
    if not Gtk.init_check()[0]:
        raise SystemExit("GUI smoke test needs a display (use xvfb-run)")
    class TestHardware(DemoHardware):
        fail = False
        empty = False
        def discover(self):
            return ScanResult([], ["测试：设备已断开"]) if self.empty else super().discover()
        def set_brightness(self, display, value):
            if self.fail:
                raise HardwareError("测试：显示器连接断开")
            return super().set_brightness(display, value)
    hardware = TestHardware()
    app = BrightnessApp(hardware, SimpleNamespace(demo=True, background=False))
    with tempfile.TemporaryDirectory() as settings_root:
        app.settings = Settings(settings_root)
        app.register(None)
        app.activate()
        try:
            pump_until(lambda: len(app.displays) == 2 and not app.scanning)
            first, second = list(app.displays)
            scale = app.cards[first][0]
            scale.set_value(43)
            scale.set_value(44)
            scale.set_value(45)
            pump_until(lambda: not app.pending)
            assert hardware.values[first] == 45
            assert hardware.values[second] == 80
            app.target_combo.set_active_id(first)
            app._scroll(app.indicator, 120, Gdk.ScrollDirection.UP)
            pump_until(lambda: not app.pending)
            assert hardware.values[first] == 50
            assert hardware.values[second] == 80
            # Activate actual menu items, including direct status-bar adjustment.
            app.menu_displays[second].get_submenu().get_children()[1].activate()
            pump_until(lambda: not app.pending)
            assert hardware.values[second] == 75
            app.presets.get_children()[0].clicked()
            pump_until(lambda: not app.pending)
            assert set(hardware.values.values()) == {25}
            hardware.fail = True
            app.request(first, 90)
            pump_until(lambda: not app.pending)
            assert app.values[first] == 25
            assert "失败" in app.status_label.get_text()
            assert app.write_errors
            hardware.fail = False
            app.request(first, 65)
            app.request(second, 80)
            app.refresh()  # Must flush debounces before reading hardware.
            pump_until(lambda: not app.scanning and not app.pending)
            assert app.values[first] == 65 and app.values[second] == 80
            assert not app.write_errors
            app.diagnostics.set_expanded(False)
            app.window.resize(500, 900)
            pump_until(lambda: app.window.get_mapped())
            # Give GTK one frame to finish size allocation before drawing.
            deadline = time.monotonic() + 0.3
            pump_until(lambda: time.monotonic() > deadline)
            width, height = app.window.get_size()
            screenshot = Gdk.pixbuf_get_from_window(app.window.get_window(), 0, 0, width, height)
            assert screenshot is not None
            (ROOT / "dist").mkdir(exist_ok=True)
            screenshot.savev(str(ROOT / "dist/preview.png"), "png", [], [])
            hardware.empty = True
            app.refresh()
            pump_until(lambda: not app.scanning)
            assert not app.displays
            assert not app.presets.get_sensitive()
            assert app.diagnostics.get_expanded()
            print("PASS: GTK startup, slider debounce, targeted scroll, tray menu, presets, failure rollback, refresh ordering, empty state")
        finally:
            app._quit()
            app.worker.thread.join(2)
            app.window.destroy()


if __name__ == "__main__":
    main()
