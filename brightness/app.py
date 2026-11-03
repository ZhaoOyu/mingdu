"""GTK panel and AppIndicator status menu. All widget access stays on GTK's thread."""
from . import language
from .language import tr
from pathlib import Path
import signal

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3 as AppIndicator, Gdk, Gio, GLib, Gtk, Pango

from . import __version__
from .settings import Settings
from .presentation import brightness_summary, device_kind
from .gtk_icon import IconCache
from .worker import HardwareWorker


CSS = b"""
.brightness-window { background: @theme_bg_color; color: @theme_fg_color; }
.brightness-window .hero { font-size: 17px; font-weight: bold; }
.brightness-window .muted { color: alpha(@theme_fg_color, 0.62); font-size: 12px; }
.brightness-window .card { background: transparent; border-bottom: 1px solid alpha(@theme_fg_color, 0.16); padding: 2px 0 12px; }
.brightness-window .monitor-name { font-size: 14px; font-weight: bold; }
.brightness-window .value { font-size: 18px; font-weight: bold; }
.brightness-window button { padding: 4px 8px; min-height: 22px; }
.brightness-window .status { color: alpha(@theme_fg_color, 0.62); font-size: 11px; }
.brightness-window .error { color: @error_color; }
.brightness-window .empty { padding: 16px 0; }
"""


def label(text, style=None, xalign=0):
    widget = Gtk.Label(label=tr(text), xalign=xalign)
    if style:
        widget.get_style_context().add_class(style)
    widget.set_valign(Gtk.Align.CENTER)
    return widget


def box(vertical=False, spacing=10):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)


class BrightnessApp(Gtk.Application):
    def __init__(self, hardware, args):
        super().__init__(application_id="io.github.mingdu.Brightness" + (".Demo" if args.demo else ""),
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.hardware, self.args = hardware, args
        self.settings = Settings()
        language.select(self.settings.data.get("interfaceLanguage"))
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
        self.icon_cache = IconCache()
        self.icon_path = None
        self._panel_size = None
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
        self.indicator.set_title(tr("明度 · 显示器亮度"))
        self.indicator.set_icon_theme_path(self.icon_cache.directory.name)
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
        self.window = Gtk.ApplicationWindow(application=self, title=tr("明度" + (" · 演示" if self.args.demo else "")))
        self.window.set_default_size(380, 520)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_icon_name("display-brightness-symbolic")
        self.window.get_style_context().add_class("brightness-window")
        self.window.connect("delete-event", self._hide)
        self.window.connect("key-press-event", self._key_pressed)
        self.window.connect("focus-out-event", self._focus_out)
        self._build_content()

    def _build_content(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.window.add(scroll)
        content = self.content = box(True, 12)
        content.set_border_width(18)
        content.set_size_request(360, -1)
        scroll.add(content)
        heading = box(spacing=10)
        icon = Gtk.Image.new_from_icon_name("display-brightness-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        icon.set_pixel_size(24)
        heading.pack_start(icon, False, False, 0)
        heading.pack_start(label("明度 · 演示" if self.args.demo else "明度", "hero"), True, True, 0)
        self.count_label = label("检测中", "muted")
        heading.pack_start(self.count_label, False, False, 0)
        self.refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.refresh_button.set_tooltip_text(tr("重新检测显示器并读取当前亮度"))
        self.refresh_button.get_accessible().set_name(tr("刷新显示器"))
        self.refresh_button.connect("clicked", lambda *_: self.refresh())
        heading.pack_end(self.refresh_button, False, False, 0)
        content.pack_start(heading, False, False, 0)
        content.pack_start(Gtk.Separator(), False, False, 0)
        self.monitor_box = box(True, 10)
        content.pack_start(self.monitor_box, False, False, 0)
        content.pack_start(label("所有屏幕 · 快捷亮度", "muted"), False, False, 0)
        self.presets = box(spacing=6)
        self.preset_handlers = []
        for title, value in [("夜间 25%", 25), ("日常 60%", 60), ("明亮 100%", 100)]:
            button = Gtk.ToggleButton(label=tr(title))
            button.set_tooltip_text(tr(f"将所有显示器调节到 {value}%"))
            handler = button.connect("clicked", lambda _, v=value: self.set_all(v))
            self.preset_handlers.append((button, value, handler))
            self.presets.pack_start(button, True, True, 0)
        content.pack_start(self.presets, False, False, 0)
        content.pack_start(Gtk.Separator(), False, False, 0)
        target_row = box()
        target_row.pack_start(label("状态栏屏幕"), True, True, 0)
        self.target_combo = Gtk.ComboBoxText()
        self.target_combo.set_tooltip_text(tr("选择圆环显示和托盘滚轮控制的屏幕；滚轮支持取决于桌面环境。"))
        self.target_combo.get_accessible().set_name(tr("状态栏显示与滚轮控制的屏幕"))
        for renderer in self.target_combo.get_cells():
            renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            renderer.set_property("max-width-chars", 16)
        self.target_combo.connect("changed", self._target_changed)
        target_row.pack_end(self.target_combo, False, False, 0)
        content.pack_start(target_row, False, False, 0)
        self.status_label = label("正在连接显示器…", "status")
        self.status_label.set_line_wrap(True)
        self.status_label.set_max_width_chars(36)
        self.status_label.set_size_request(-1, 30)
        content.pack_start(self.status_label, False, False, 0)
        actions = box(spacing=6)
        self.diagnostics = Gtk.Expander(label=tr("设备诊断"))
        self.diagnostic_text = label("")
        self.diagnostic_text.set_line_wrap(True)
        self.diagnostic_text.set_max_width_chars(36)
        self.diagnostic_text.set_selectable(True)
        diagnostic_scroll = Gtk.ScrolledWindow()
        diagnostic_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        diagnostic_scroll.set_min_content_height(140)
        diagnostic_scroll.add(self.diagnostic_text)
        self.diagnostics.add(diagnostic_scroll)
        self.diagnostics.connect("notify::expanded", lambda *_: GLib.idle_add(self._resize_panel))
        actions.pack_start(self.diagnostics, True, True, 0)
        quit_button = Gtk.Button(label=tr("退出"))
        quit_button.set_valign(Gtk.Align.START)
        quit_button.connect("clicked", self._quit)
        actions.pack_end(quit_button, False, False, 0)
        content.pack_start(actions, False, False, 0)
        content.pack_start(Gtk.Separator(), False, False, 0)
        content.pack_start(self.language_row(), False, False, 0)
        footer = box()
        self.autostart_switch = Gtk.CheckButton(label=tr("登录系统时启动"))
        self.autostart_switch.set_active(self.settings.autostart)
        self.autostart_switch.set_sensitive(not self.args.demo)
        self.autostart_switch.connect("toggled", lambda button: self._autostart(button.get_active()))
        footer.pack_start(self.autostart_switch, True, True, 0)
        footer.pack_end(label("v" + __version__, "muted"), False, False, 0)
        content.pack_start(footer, False, False, 0)

    def language_row(self):
        row = Gtk.Box(spacing=8)
        row.pack_start(Gtk.Label(label=tr("Language" if language.english() else "语言"), xalign=0), True, True, 0)
        combo = self.languages = Gtk.ComboBoxText()
        for key, name in zip(language.CHOICES, language.names()):
            combo.append(key, name)
        combo.set_active_id(language.choice)
        combo.connect("changed", self.change_language)
        row.pack_end(combo, False, False, 0)
        return row

    def change_language(self, combo):
        value = combo.get_active_id()
        if not self.args.demo:
            try:
                self.settings.set_language(value)
            except OSError as error:
                self._status(str(error), True)
                return
        language.select(value)
        self.window.get_child().destroy()
        self.window.set_title(tr("明度 · 演示" if self.args.demo else "明度"))
        self.indicator.set_title(tr("明度 · 显示器亮度"))
        self._build_content()
        self._render_displays()
        self._diagnostics()
        self._status(getattr(self, "_last_message", "已读取当前亮度"))
        self.window.show_all()

    def _resize_panel(self):
        if self.closed:
            return False
        _, height = self.content.get_preferred_height_for_width(380)
        monitor = self.window.get_display().get_primary_monitor()
        limit = min(720, monitor.get_workarea().height - 40) if monitor else 720
        size = (380, min(limit, max(340, height)))
        if size != self._panel_size:
            self.window.resize(*size)
            self._panel_size = size
        return False

    def _key_pressed(self, _, event):
        if event.keyval == Gdk.KEY_Escape and self.indicator.get_property("connected"):
            return self._hide()
        return False

    def _focus_out(self, *_):
        # Native combo menus must stay usable while they temporarily own the grab.
        if self.indicator.get_property("connected") and Gtk.grab_get_current() is None:
            self.window.hide()
        return False

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
            card = box(True, 6)
            card.get_style_context().add_class("card")
            top = box(spacing=12)
            top.pack_start(Gtk.Image.new_from_icon_name("video-display-symbolic", Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
            info = box(True, 2)
            name = label(display.name, "monitor-name")
            name.set_line_wrap(True)
            name.set_max_width_chars(20)
            info.pack_start(name, False, False, 0)
            subtitle = device_kind(display.kind)
            badge = label(subtitle, "muted")
            badge.set_halign(Gtk.Align.START)
            info.pack_start(badge, False, False, 0)
            top.pack_start(info, True, True, 0)
            number = label(f"{display.value}%", "value", 1)
            top.pack_end(number, False, False, 0)
            card.pack_start(top, False, False, 0)
            controls = box(spacing=6)
            minus = Gtk.Button.new_from_icon_name("list-remove-symbolic", Gtk.IconSize.MENU)
            minus.set_tooltip_text(tr("降低 5%"))
            minus.connect("clicked", lambda _, key=display.id: self.adjust(key, -5))
            controls.pack_start(minus, False, False, 0)
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
            scale.set_draw_value(False)
            scale.set_value(max(1, display.value))
            scale.get_accessible().set_name(tr(f"{display.name}亮度"))
            scale.connect("value-changed", self._scale_changed, display.id)
            controls.pack_start(scale, True, True, 0)
            plus = Gtk.Button.new_from_icon_name("list-add-symbolic", Gtk.IconSize.MENU)
            plus.set_tooltip_text(tr("提高 5%"))
            plus.connect("clicked", lambda _, key=display.id: self.adjust(key, 5))
            controls.pack_end(plus, False, False, 0)
            card.pack_start(controls, False, False, 0)
            self.cards[display.id] = (scale, number, card)
            self.monitor_box.pack_start(card, False, False, 0)
        self.count_label.set_text(tr(f"{len(self.displays)} 台屏幕"))
        self.target_combo.remove_all()
        self.target_combo.append("all", tr("所有显示器"))
        for display in self.displays.values():
            self.target_combo.append(display.id, tr(display.name))
        target = self.settings.data["scroll_target"]
        self.target_combo.set_active_id(target if target in self.displays else "all")
        self.updating = False
        self.monitor_box.show_all()
        self._build_menu()
        self._sync_sensitivity()
        self._update_labels()
        GLib.idle_add(self._resize_panel)

    def _menu_item(self, menu, text, callback=None):
        item = Gtk.MenuItem(label=tr(text))
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
        self.menu_autostart = Gtk.CheckMenuItem(label=tr("登录后自动启动"))
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
        connected = self.indicator.get_property("connected")
        self.window.set_decorated(not connected)
        self.window.set_skip_taskbar_hint(connected)
        self.window.set_type_hint(Gdk.WindowTypeHint.UTILITY if connected else Gdk.WindowTypeHint.NORMAL)
        self.window.show_all()
        self._resize_panel()
        if connected:
            display = self.window.get_display()
            _, x, y = display.get_default_seat().get_pointer().get_position()
            monitor = display.get_monitor_at_point(x, y)
            if monitor:
                area = monitor.get_workarea()
                width, height = self.window.get_size()
                x = max(area.x + 8, min(x - width // 2, area.x + area.width - width - 8))
                y = area.y + 8 if y < area.y + area.height // 2 else area.y + area.height - height - 8
                self.window.move(x, max(area.y + 8, y))
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
            self._update_labels()
        return False

    def _update_labels(self):
        self.updating = True
        for key, value in self.values.items():
            if key in self.cards:
                scale, number, _ = self.cards[key]
                scale.set_value(max(1, value))
                number.set_text(tr(f"{value}%" + (" ·" if key in self.pending else "")))
            if key in self.menu_displays:
                self.menu_displays[key].set_label(tr(f"{self.displays[key].name}   {value}%" + (" …" if key in self.pending else "")))
        target = self.target_combo.get_active_id()
        self.tray_summary = brightness_summary(self.displays, self.confirmed, target, self.write_errors)
        path = self.icon_cache.path(self.tray_summary)
        if path != self.icon_path:
            self.indicator.set_icon_full(str(path), tr(self.tray_summary.description))
            self.icon_path = path
        self.indicator.set_label(tr("演示" if self.args.demo else ""), "")
        self.indicator.set_title(tr("明度 · " + self.tray_summary.description))
        for button, value, handler in self.preset_handlers:
            button.handler_block(handler)
            button.set_active(bool(self.confirmed) and not self.pending and not self.write_errors
                              and all(v == value for v in self.confirmed.values()))
            button.handler_unblock(handler)
        self.updating = False

    def _diagnostics(self):
        help_text = (
            "内置屏幕：需要系统提供 /sys/class/backlight 设备。\n"
            "外接屏幕：安装 ddcutil，在显示器菜单开启 DDC/CI。\n"
            "连接或唤醒显示器后，请点击刷新重新检测。\n"
            "终端诊断：ddcutil detect；ddcutil environment。\n"
            "首次安装依赖后可能需要注销并重新登录。"
        )
        self.diagnostic_text.set_text(tr("\n\n".join(self.warnings + [help_text])))
        self.diagnostics.set_expanded(not bool(self.displays))

    def _status(self, text, error=False):
        self._last_message = text
        self.status_label.set_text(tr(("演示 · " if self.args.demo else "") + text))
        GLib.idle_add(self._resize_panel)
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
        self.icon_cache.close()
        self.quit()
        return False
