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
from brightness.presentation import BrightnessSummary


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
        writes = 0
        fail = False
        empty = False
        def discover(self):
            return ScanResult([], ["测试：设备已断开"]) if self.empty else super().discover()
        def set_brightness(self, display, value):
            self.writes += 1
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
            app.languages.set_active_id("en")
            assert app.autostart_switch.get_label() == "Open at login"
            app.languages.set_active_id("zh-Hans")
            assert app.autostart_switch.get_label() == "登录系统时启动"
            assert hardware.writes == 0
            assert app.tray_summary.text == "≠"
            first, second = list(app.displays)
            app.target_combo.set_active_id(first)
            assert app.tray_summary.value == 65
            # Render through GTK's real symbolic loader: keep the hollow ring,
            # progress opacity and outlined native-font digits after recoloring.
            path = app.icon_cache.path(BrightnessSummary(25, "25", "test"))
            theme = Gtk.IconTheme.new()
            theme.append_search_path(app.icon_cache.directory.name)
            info = theme.lookup_icon(path.stem, 192, Gtk.IconLookupFlags.FORCE_SIZE)
            pixels, symbolic = info.load_symbolic_for_context(app.window.get_style_context())
            assert symbolic
            data = pixels.get_pixels()
            def alpha(x, y):
                return data[y * pixels.get_rowstride() + x * 4 + 3]
            assert alpha(96, 32) == 0
            assert alpha(8, 96) > 240
            assert 50 < alpha(184, 96) < 90
            assert any(alpha(x, y) > 200 for x in range(56, 136) for y in range(64, 120))
            assert alpha(96, 161) > 240  # The bottom sun remains visible.
            scale = app.cards[first][0]
            scale.set_value(43)
            scale.set_value(44)
            scale.set_value(45)
            assert app.tray_summary.value == 65
            pump_until(lambda: not app.pending)
            assert app.tray_summary.value == 45
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
            assert [b.get_active() for b in app.presets.get_children()] == [True, False, False]
            hardware.fail = True
            app.request(first, 90)
            pump_until(lambda: not app.pending)
            assert app.values[first] == 25
            assert "失败" in app.status_label.get_text()
            assert app.write_errors
            assert app.tray_summary.text == "!"
            hardware.fail = False
            app.request(first, 65)
            app.request(second, 80)
            app.refresh()  # Must flush debounces before reading hardware.
            pump_until(lambda: not app.scanning and not app.pending)
            assert app.values[first] == 65 and app.values[second] == 80
            assert not app.write_errors
            app.diagnostics.set_expanded(False)
            app._resize_panel()
            pump_until(lambda: app.window.get_mapped())
            # Give GTK one frame to finish size allocation before drawing.
            deadline = time.monotonic() + 0.3
            pump_until(lambda: time.monotonic() > deadline)
            width, height = app.window.get_size()
            assert width == 380 and height <= 720, (width, height)
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
