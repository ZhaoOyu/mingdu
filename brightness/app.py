"""GTK panel and AppIndicator status menu. All widget access stays on GTK's thread."""
from pathlib import Path
import signal

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3 as AppIndicator, Gdk, Gio, GLib, Gtk

from .settings import Settings
from .worker import HardwareWorker


CSS = b"""
.brightness-window { background: #f5f4f1; color: #272b30; }
.brightness-window headerbar { background: #f5f4f1; color: #272b30; box-shadow: none; }
.brightness-window .hero { font-size: 26px; font-weight: 800; }
.brightness-window .muted { color: #6d7177; font-size: 12px; }
.brightness-window .eyebrow { color: #a85c24; font-size: 11px; font-weight: 700; }
.brightness-window .card { background: #ffffff; border: 1px solid #e5e3de; border-radius: 16px; padding: 18px; }
.brightness-window .monitor-name { font-size: 15px; font-weight: 700; }
.brightness-window .value { font-size: 28px; font-weight: 700; color: #b65d27; }
.brightness-window .badge { color: #397263; background: #edf5ef; border-radius: 6px; padding: 4px 8px; font-size: 10px; }
.brightness-window scale trough { min-height: 6px; border-radius: 8px; background: #eae8e3; }
.brightness-window scale highlight { background: #d78043; border-color: #d78043; border-radius: 8px; }
.brightness-window scale slider { background: #ffffff; border: 2px solid #cd743b; min-width: 16px; min-height: 16px; }
.brightness-window button { background: #ffffff; color: #30343a; border: 1px solid #dedcd7; border-radius: 9px; padding: 7px 12px; }
.brightness-window button:disabled { color: #9b9b9b; background: #f1f0ee; }
.brightness-window .preset { background: #ffffff; border: 1px solid #e5e3de; box-shadow: none; }
.brightness-window .status { color: #6d7177; font-size: 11px; }
.brightness-window .error { color: #b23c28; }
.brightness-window .empty { padding: 28px; }
"""


def label(text, style=None, xalign=0):
    widget = Gtk.Label(label=text, xalign=xalign)
    if style:
        widget.get_style_context().add_class(style)
    return widget


def box(vertical=False, spacing=10):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)


class BrightnessApp(Gtk.Application):
    def __init__(self, hardware, args):
        super().__init__(application_id="io.github.mingdu.Brightness" + (".Demo" if args.demo else ""),
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.hardware, self.args = hardware, args
        self.settings = Settings()
        self.window = None
        self.worker = None
        self.displays = {}
        self.values = {}
        self.confirmed = {}
        self.revisions = {}
        self.pending = set()
        self.write_errors = {}
        self.debounce = {}
        self.cards = {}
        self.menu_displays = {}
        self.scanning = False
        self.updating = False
        self.closed = False
        self.warnings = []
        self.launcher = Path(__file__).resolve().parent.parent / "mingdu"

    def do_activate(self):
        if self.window is not None:
            self.show_panel()
            return
        self.hold()
        self._build_window()
        self.indicator = AppIndicator.Indicator.new(
            "mingdu-demo" if self.args.demo else "mingdu-brightness",
            "display-brightness-symbolic", AppIndicator.IndicatorCategory.HARDWARE,
        )
        self.indicator.set_title("明度 · 显示器亮度")
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.indicator.connect("scroll-event", self._scroll)
        self._build_menu()
        self.worker = HardwareWorker(self.hardware, lambda event, data: GLib.idle_add(self._event, event, data))
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, self._quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self._quit)
        self.refresh()
        if not self.args.background:
            self.show_panel()
        # A background launch without a tray host must not leave an invisible app.
        GLib.timeout_add_seconds(4, self._check_tray)

    def _build_window(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = Gtk.ApplicationWindow(application=self, title="明度 · 显示器亮度")
        self.window.set_default_size(500, 800)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_icon_name("display-brightness-symbolic")
        self.window.get_style_context().add_class("brightness-window")
        self.window.connect("delete-event", self._hide)
        header = Gtk.HeaderBar(title="明度", subtitle="BRIGHTNESS" + (" · 演示" if self.args.demo else ""), show_close_button=True)
        header.set_decoration_layout(":close")
        self.refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.refresh_button.set_tooltip_text("重新检测显示器并读取当前亮度")
        self.refresh_button.connect("clicked", lambda *_: self.refresh())
        header.pack_end(self.refresh_button)
        self.window.set_titlebar(header)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.window.add(scroll)
        content = box(True, 18)
        content.set_border_width(24)
        scroll.add(content)
        intro = box(True, 7)
        intro.pack_start(label("让屏幕，刚刚好。", "hero"), False, False, 0)
        intro.pack_start(label("从顶部状态栏，轻松掌控每一块屏幕。", "muted"), False, False, 0)
        content.pack_start(intro, False, False, 0)
        summary = box()
        summary.pack_start(label("显示器 / DISPLAYS", "eyebrow"), True, True, 0)
        self.count_label = label("正在检测…", "muted")
        summary.pack_end(self.count_label, False, False, 0)
        content.pack_start(summary, False, False, 0)
        self.monitor_box = box(True, 12)
        content.pack_start(self.monitor_box, False, False, 0)
        self.presets = box(spacing=8)
        for title, value in [("夜间 · 25%", 25), ("日常 · 60%", 60), ("明亮 · 100%", 100)]:
            button = Gtk.Button(label=title)
            button.get_style_context().add_class("preset")
            button.set_tooltip_text(f"将所有显示器调节到 {value}%")
            button.connect("clicked", lambda _, v=value: self.set_all(v))
            self.presets.pack_start(button, True, True, 0)
        content.pack_start(self.presets, False, False, 0)
        preferences = box(True, 14)
        preferences.get_style_context().add_class("card")
        target_row = box()
        target_row.pack_start(label("状态栏滚轮控制"), True, True, 0)
        self.target_combo = Gtk.ComboBoxText()
        self.target_combo.connect("changed", self._target_changed)
        target_row.pack_end(self.target_combo, False, False, 0)
        preferences.pack_start(target_row, False, False, 0)
        start_row = box()
        start_row.pack_start(label("登录后自动启动"), True, True, 0)
        self.autostart_switch = Gtk.Switch()
        self.autostart_switch.set_active(self.settings.autostart)
        self.autostart_switch.set_sensitive(not self.args.demo)
        self.autostart_switch.connect("notify::active", self._autostart_switch_changed)
        start_row.pack_end(self.autostart_switch, False, False, 0)
        preferences.pack_start(start_row, False, False, 0)
        content.pack_start(preferences, False, False, 0)
        self.status_label = label("正在连接显示器…", "status")
        self.status_label.set_line_wrap(True)
        self.status_label.set_max_width_chars(54)
        content.pack_start(self.status_label, False, False, 0)
        self.diagnostics = Gtk.Expander(label="设备诊断与帮助")
        self.diagnostic_text = label("")
        self.diagnostic_text.set_line_wrap(True)
        self.diagnostic_text.set_max_width_chars(52)
        self.diagnostic_text.set_selectable(True)
        self.diagnostics.add(self.diagnostic_text)
        content.pack_start(self.diagnostics, False, False, 0)
        footer = label("滚轮每次调节 5% · 关闭窗口后仍在状态栏运行", "status")
        footer.set_line_wrap(True)
        content.pack_start(footer, False, False, 0)

    def _render_displays(self):
        self.updating = True
        for child in self.monitor_box.get_children():
            child.destroy()
        self.cards.clear()
        if not self.displays:
            empty = box(True, 12)
            empty.get_style_context().add_class("card")
            empty.get_style_context().add_class("empty")
            empty.pack_start(Gtk.Image.new_from_icon_name("video-display-symbolic", Gtk.IconSize.DIALOG), False, False, 0)
            empty.pack_start(label("未发现可调节的显示器", "monitor-name", 0.5), False, False, 0)
            hint = label("连接显示器并开启 DDC/CI，\n然后点击右上角刷新。", "muted", 0.5)
            hint.set_justify(Gtk.Justification.CENTER)
            empty.pack_start(hint, False, False, 0)
            self.monitor_box.pack_start(empty, False, False, 0)
        for display in self.displays.values():
            card = box(True, 12)
            card.get_style_context().add_class("card")
            top = box(spacing=12)
            top.pack_start(Gtk.Image.new_from_icon_name("video-display-symbolic", Gtk.IconSize.DND), False, False, 0)
            info = box(True, 5)
            name = label(display.name, "monitor-name")
            name.set_line_wrap(True)
            name.set_max_width_chars(24)
            info.pack_start(name, False, False, 0)
            subtitle = {"backlight": "内置背光", "ddc": "DDC/CI", "demo": "演示设备"}[display.kind]
            badge = label(subtitle, "badge")
            badge.set_halign(Gtk.Align.START)
            info.pack_start(badge, False, False, 0)
            top.pack_start(info, True, True, 0)
            number = label(f"{display.value}%", "value", 1)
            top.pack_end(number, False, False, 0)
            card.pack_start(top, False, False, 0)
            controls = box(spacing=6)
            minus = Gtk.Button.new_from_icon_name("list-remove-symbolic", Gtk.IconSize.MENU)
            minus.set_tooltip_text("降低 5%")
            minus.connect("clicked", lambda _, key=display.id: self.adjust(key, -5))
            controls.pack_start(minus, False, False, 0)
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
            scale.set_draw_value(False)
            scale.set_value(max(1, display.value))
            scale.get_accessible().set_name(f"{display.name}亮度")
            scale.connect("value-changed", self._scale_changed, display.id)
            controls.pack_start(scale, True, True, 0)
            plus = Gtk.Button.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU)
            plus.set_tooltip_text("提高 5%")
            plus.connect("clicked", lambda _, key=display.id: self.adjust(key, 5))
            controls.pack_end(plus, False, False, 0)
            card.pack_start(controls, False, False, 0)
            self.cards[display.id] = (scale, number, card)
            self.monitor_box.pack_start(card, False, False, 0)
        self.count_label.set_text(f"{len(self.displays)} 台已连接")
        self.target_combo.remove_all()
        self.target_combo.append("all", "所有显示器")
        for display in self.displays.values():
            self.target_combo.append(display.id, display.name)
        target = self.settings.data["scroll_target"]
        self.target_combo.set_active_id(target if target in self.displays else "all")
        self.updating = False
        self.monitor_box.show_all()
        self._build_menu()
        self._sync_sensitivity()
        self._update_labels()

    def _menu_item(self, menu, text, callback=None):
        item = Gtk.MenuItem(label=text)
        if callback:
            item.connect("activate", lambda *_: callback())
        menu.append(item)
        return item

    def _build_menu(self):
        menu = Gtk.Menu()
        self.menu_displays.clear()
        self.open_item = self._menu_item(menu, "打开亮度面板…", self.show_panel)
        menu.append(Gtk.SeparatorMenuItem())
        self.control_items = []
        if not self.displays:
            item = self._menu_item(menu, "未发现可调节的显示器")
            item.set_sensitive(False)
        for display in self.displays.values():
            item = self._menu_item(menu, display.name)
            submenu = Gtk.Menu()
            self._menu_item(submenu, "提高 5%", lambda key=display.id: self.adjust(key, 5))
            self._menu_item(submenu, "降低 5%", lambda key=display.id: self.adjust(key, -5))
            submenu.append(Gtk.SeparatorMenuItem())
            for value in (25, 50, 75, 100):
                self._menu_item(submenu, f"{value}%", lambda key=display.id, v=value: self.request(key, v))
            item.set_submenu(submenu)
            self.menu_displays[display.id] = item
            self.control_items.append(item)
        menu.append(Gtk.SeparatorMenuItem())
        for title, callback in [
            ("全部提高 5%", lambda: self.adjust_all(5)),
            ("全部降低 5%", lambda: self.adjust_all(-5)),
            ("夜间 · 25%", lambda: self.set_all(25)),
            ("日常 · 60%", lambda: self.set_all(60)),
            ("明亮 · 100%", lambda: self.set_all(100)),
        ]:
            self.control_items.append(self._menu_item(menu, title, callback))
        menu.append(Gtk.SeparatorMenuItem())
        self.menu_refresh = self._menu_item(menu, "重新检测显示器", self.refresh)
        self.menu_autostart = Gtk.CheckMenuItem(label="登录后自动启动")
        self.menu_autostart.set_active(self.settings.autostart)
        self.menu_autostart.set_sensitive(not self.args.demo)
        self.menu_autostart.connect("toggled", lambda item: self._autostart(item.get_active()))
        menu.append(self.menu_autostart)
        self._menu_item(menu, "退出明度", self._quit)
        menu.show_all()
        # libayatana keeps a non-owning pointer to the old secondary item.
        self.indicator.set_secondary_activate_target(None)
        self.indicator.set_menu(menu)
        self.indicator.set_secondary_activate_target(self.open_item)
        self.menu = menu

    def show_panel(self):
        self.window.show_all()
        self.window.present()

    def _hide(self, *_):
        if self.indicator.get_property("connected"):
            self.window.hide()
        else:
            self._quit()
        return True

    def _check_tray(self):
        if not self.closed and not self.indicator.get_property("connected"):
            self.warnings.append("未发现状态栏托盘宿主。GNOME 请安装并启用 Ubuntu AppIndicators 扩展；当前可继续使用窗口调节。")
            self._diagnostics()
            if self.args.background:
                self.show_panel()
        return False

    def _sync_sensitivity(self):
        enabled = bool(self.displays) and not self.scanning
        self.monitor_box.set_sensitive(not self.scanning)
        self.presets.set_sensitive(enabled)
        self.refresh_button.set_sensitive(not self.scanning)
        self.menu_refresh.set_sensitive(not self.scanning)
        for item in self.control_items:
            item.set_sensitive(enabled)

    def refresh(self):
        if self.scanning or self.closed:
            return
        # Flush slider debounces before queuing the scan so it reads the new values.
        for key in list(self.debounce):
            GLib.source_remove(self.debounce.pop(key))
            self._dispatch(key)
        self.scanning = True
        self._sync_sensitivity()
        self._status("正在检测显示器，外接屏幕可能需要一些时间…")
        self.worker.scan()

    def request(self, key, value):
        if self.scanning or key not in self.displays or self.closed:
            return
        value = max(1, min(100, round(value)))
        self.values[key] = value
        self.revisions[key] = self.revisions.get(key, 0) + 1
        self.pending.add(key)
        self.write_errors.pop(key, None)
        if key in self.debounce:
            GLib.source_remove(self.debounce.pop(key))
        self.debounce[key] = GLib.timeout_add(160, self._dispatch, key)
        self._update_labels()
        self._status("正在应用亮度…")

    def _dispatch(self, key):
        self.debounce.pop(key, None)
        self.worker.write(self.displays[key], self.values[key], self.revisions[key])
        return False

    def adjust(self, key, delta):
        self.request(key, self.values.get(key, 50) + delta)

    def adjust_all(self, delta):
        for key in self.displays:
            self.adjust(key, delta)

    def set_all(self, value):
        for key in self.displays:
            self.request(key, value)

    def _scale_changed(self, scale, key):
        if not self.updating:
            self.request(key, scale.get_value())

    def _scroll(self, indicator, steps, direction):
        if direction not in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN):
            return
        delta = 5 if direction == Gdk.ScrollDirection.UP else -5
        key = self.target_combo.get_active_id()
        if key in self.displays:
            self.adjust(key, delta)
        else:
            self.adjust_all(delta)

    def _target_changed(self, combo):
        if self.updating:
            return
        self.settings.data["scroll_target"] = combo.get_active_id() or "all"
        try:
            if not self.args.demo:
                self.settings.save()
        except OSError as exc:
            self._status(f"无法保存设置：{exc}", error=True)
        self._update_labels()

    def _autostart_switch_changed(self, switch, _):
        self._autostart(switch.get_active())

    def _autostart(self, enabled):
        if self.updating or self.args.demo:
            return
        try:
            self.settings.set_autostart(enabled, self.launcher)
        except (OSError, ValueError) as exc:
            self._status(f"无法更改自启动：{exc}", error=True)
        self.updating = True
        self.autostart_switch.set_active(self.settings.autostart)
        self.menu_autostart.set_active(self.settings.autostart)
        self.updating = False

    def _event(self, event, data):
        if self.closed:
            return False
        if event == "scan":
            self.scanning = False
            self.displays = {d.id: d for d in data.displays}
            self.values = {d.id: d.value for d in data.displays}
            self.confirmed = self.values.copy()
            self.pending.clear()
            self.write_errors.clear()
            self.warnings = data.warnings
            self._render_displays()
            self._diagnostics()
            self._status("已读取当前亮度 · 拖动滑块即可调节" if self.displays else "暂无可调节设备，请展开诊断查看原因。")
        elif event == "scan-error":
            self.scanning = False
            self._sync_sensitivity()
            self._status(f"检测失败：{data}", error=True)
        elif event == "write":
            key, revision, actual, error = data
            if key not in self.displays:
                return False
            if error is None:
                self.confirmed[key] = actual
            if revision != self.revisions.get(key):
                return False
            self.pending.discard(key)
            self.values[key] = self.confirmed[key]
            self._update_labels()
            if error:
                self.write_errors[key] = error
                message = f"{self.displays[key].name} 调节失败：{error}"
                self.warnings.append(message)
                self.warnings = self.warnings[-12:]
                self._diagnostics()
                self._status("调节失败，已恢复为最近一次确认的亮度；请查看设备诊断。", error=True)
                # A tray-only failure should also be visible to the user.
                notification = Gio.Notification.new("明度：亮度调节失败")
                notification.set_body(message[:240])
                self.send_notification("brightness-error", notification)
            elif not self.pending and not self.scanning:
                self._status("部分显示器调节失败，请查看设备诊断。" if self.write_errors else "亮度已更新", error=bool(self.write_errors))
        return False

    def _update_labels(self):
        self.updating = True
        for key, value in self.values.items():
            if key in self.cards:
                scale, number, _ = self.cards[key]
                scale.set_value(max(1, value))
                number.set_text(f"{value}%" + (" ·" if key in self.pending else ""))
            if key in self.menu_displays:
                self.menu_displays[key].set_label(f"{self.displays[key].name}   {value}%" + (" …" if key in self.pending else ""))
        target = self.target_combo.get_active_id()
        values = [self.values[target]] if target in self.values else list(self.values.values())
        text = f"{values[0]}%" if values and len(set(values)) == 1 else (f"{len(values)} 屏" if values else "")
        if self.args.demo:
            text = "演示 " + text
        self.indicator.set_label(text, "100%")
        self.updating = False

    def _diagnostics(self):
        help_text = (
            "内置屏幕：需要系统提供 /sys/class/backlight 设备。\n"
            "外接屏幕：安装 ddcutil，在显示器菜单开启 DDC/CI。\n"
            "连接或唤醒显示器后，请点击刷新重新检测。\n"
            "终端诊断：ddcutil detect；ddcutil environment。\n"
            "首次安装依赖后可能需要注销并重新登录。"
        )
        self.diagnostic_text.set_text("\n\n".join(self.warnings + [help_text]))
        self.diagnostics.set_expanded(not self.displays or self.args.demo)

    def _status(self, text, error=False):
        self.status_label.set_text(text)
        context = self.status_label.get_style_context()
        (context.add_class if error else context.remove_class)("error")

    def _quit(self, *_):
        self.closed = True
        for source in self.debounce.values():
            GLib.source_remove(source)
        self.debounce.clear()
        if self.worker:
            self.worker.stop()
        if hasattr(self, "indicator"):
            self.indicator.set_status(AppIndicator.IndicatorStatus.PASSIVE)
        self.quit()
        return False
