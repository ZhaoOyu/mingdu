"""AppKit menu-bar app: native popover, system material, SF Symbols and controls."""
from . import language
from .language import tr
import AppKit as A
import objc
from Foundation import NSObject, NSTimer, NSRunLoop, NSRunLoopCommonModes, NSAttributedString

from . import __version__
from .native_controller import NativeController
from .native_instance import NativeInstance
from .presentation import RING_START, RING_SWEEP, brightness_summary, device_kind
from .settings import Settings
from .startup import Startup


def symbol(name, title):
    return A.NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, tr(title))


def status_image(summary):
    image = A.NSImage.alloc().initWithSize_((26, 24))
    image.lockFocus()
    try:
        for alpha, sweep in ((.28, RING_SWEEP), (1, (summary.value or 0) * RING_SWEEP / 100)):
            if sweep <= 0:
                continue
            A.NSColor.blackColor().colorWithAlphaComponent_(alpha).setStroke()
            path = A.NSBezierPath.bezierPath()
            path.setLineWidth_(2.4)
            path.setLineCapStyle_(A.NSRoundLineCapStyle)
            path.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
                (13, 12), 10.7, RING_START, RING_START - sweep, True)
            path.stroke()
        text = NSAttributedString.alloc().initWithString_attributes_(summary.text, {
            A.NSFontAttributeName: A.NSFont.monospacedDigitSystemFontOfSize_weight_(
                9 if len(summary.text) > 2 else 10.5, A.NSFontWeightBold),
            A.NSForegroundColorAttributeName: A.NSColor.blackColor(),
        })
        text.drawAtPoint_((13 - text.size().width / 2, 7))
        sun = symbol('sun.max.fill', '亮度')
        sun.drawInRect_fromRect_operation_fraction_(
            ((8.8, .2), (8.4, 8.4)), ((0, 0), (0, 0)), A.NSCompositingOperationSourceOver, 1)
    finally:
        image.unlockFocus()
    image.setTemplate_(True)
    return image


class BrightnessPanel(NSObject):
    @objc.python_method
    def configure(self, controller, demo=False, settings=None, startup=None):
        self.controller, self.demo = controller, demo
        self.settings = settings if settings is not None else Settings()
        language.select(self.settings.data.get("interfaceLanguage"))
        self.startup = startup if startup is not None else Startup()
        self.generation = -1
        self.diagnostics_open = False
        self.closed = False
        self.icon_key = None
        self.status = A.NSStatusBar.systemStatusBar().statusItemWithLength_(A.NSVariableStatusItemLength)
        self.button = self.status.button()
        self.button.setTarget_(self)
        self.button.setAction_('toggle:')
        self.button.setTitle_(tr('演示' if demo else ''))
        self.popover = A.NSPopover.alloc().init()
        self.popover.setBehavior_(A.NSPopoverBehaviorTransient)
        self.popover.setAnimates_(True)
        self.view_controller = A.NSViewController.alloc().init()
        self.popover.setContentViewController_(self.view_controller)
        self.tick_(None)
        self.timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(.05, self, 'tick:', None, True)
        NSRunLoop.mainRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)

    @objc.python_method
    def rect(self, x, top, width, height):
        return ((x, self.height - top - height), (width, height))

    @objc.python_method
    def text(self, title, x, top, width, size=13, bold=False, secondary=False, height=20):
        field = A.NSTextField.labelWithString_(tr(title))
        field.setFrame_(self.rect(x, top, width, height))
        field.setFont_(A.NSFont.systemFontOfSize_weight_(size, A.NSFontWeightSemibold if bold else A.NSFontWeightRegular))
        field.setTextColor_(A.NSColor.secondaryLabelColor() if secondary else A.NSColor.labelColor())
        field.setLineBreakMode_(A.NSLineBreakByWordWrapping if height > 24 else A.NSLineBreakByTruncatingTail)
        field.setMaximumNumberOfLines_(2 if height > 24 else 1)
        field.setToolTip_(tr(title))
        self.content.addSubview_(field)
        return field

    @objc.python_method
    def centered(self, field, x, center, width):
        height = field.intrinsicContentSize().height
        field.setFrame_(self.rect(x, center - height / 2, width, height))

    @objc.python_method
    def glyph(self, name, title, x, top, size=22):
        view = A.NSImageView.alloc().initWithFrame_(self.rect(x, top, size, size))
        view.setImage_(symbol(name, title))
        view.setContentTintColor_(A.NSColor.secondaryLabelColor())
        self.content.addSubview_(view)

    @objc.python_method
    def separator(self, top):
        line = A.NSBox.alloc().initWithFrame_(self.rect(18, top, 304, 1))
        line.setBoxType_(A.NSBoxSeparator)
        self.content.addSubview_(line)

    @objc.python_method
    def action(self, title, selector, x, top, width, image=None):
        button = A.NSButton.buttonWithTitle_target_action_(tr(title), self, selector)
        button.setFrame_(self.rect(x, top, width, 28))
        button.setBezelStyle_(A.NSBezelStyleRounded)
        button.setFont_(A.NSFont.systemFontOfSize_(12))
        if image:
            button.setImage_(symbol(image, title))
            button.setImagePosition_(A.NSImageLeft)
        self.content.addSubview_(button)
        return button

    @objc.python_method
    def build(self):
        self.keys = list(self.controller.displays)
        monitor_height = max(1, len(self.keys)) * 100
        self.height = 48 + monitor_height + 240 + (142 if self.diagnostics_open else 0) + 38
        screen = self.button.window().screen() or A.NSScreen.mainScreen()
        self.visible_height = min(self.height, screen.visibleFrame().size.height - 70, 720)
        self.material = A.NSVisualEffectView.alloc().initWithFrame_(((0, 0), (340, self.visible_height)))
        self.material.setMaterial_(A.NSVisualEffectMaterialPopover)
        self.material.setBlendingMode_(A.NSVisualEffectBlendingModeBehindWindow)
        self.material.setState_(A.NSVisualEffectStateActive)
        self.scroll = A.NSScrollView.alloc().initWithFrame_(self.material.bounds())
        self.scroll.setDrawsBackground_(False)
        self.scroll.setBorderType_(A.NSNoBorder)
        self.scroll.setHasVerticalScroller_(self.height > self.visible_height)
        self.scroll.setAutohidesScrollers_(True)
        self.content = A.NSView.alloc().initWithFrame_(((0, 0), (340, self.height)))
        self.scroll.setDocumentView_(self.content)
        self.material.addSubview_(self.scroll)
        self.glyph('sun.max', '明度', 18, 15)
        heading = self.text('明度 · 演示' if self.demo else '明度', 52, 0, 208, 16, True)
        heading.setFont_(A.NSFont.systemFontOfSize_weight_(16, A.NSFontWeightBold))
        self.centered(heading, 52, 26, 208)
        count = self.text(f'{len(self.keys)} 台屏幕', 258, 0, 62, 11, secondary=True)
        count.setAlignment_(A.NSTextAlignmentRight)
        self.centered(count, 258, 26, 62)
        self.separator(48)
        self.rows = {}
        for index, key in enumerate(self.keys):
            device = self.controller.displays[key]
            top = 64 + index * 100
            self.glyph('laptopcomputer' if device.kind in ('apple', 'backlight', 'wmi') else 'display', device.name, 20, top)
            title = self.text(device.name, 54, top, 184, 14, True)
            self.centered(title, 54, top + 11, 184)
            value = self.text('', 242, top, 78, 16, True)
            value.setAlignment_(A.NSTextAlignmentRight)
            self.centered(value, 242, top + 11, 78)
            self.text(device_kind(device.kind), 54, top + 26, 264, 11, secondary=True)
            self.glyph('sun.min', '降低亮度', 20, top + 51, 16)
            slider = A.NSSlider.sliderWithValue_minValue_maxValue_target_action_(device.value, 1, 100, self, 'brightness:')
            slider.setFrame_(self.rect(50, top + 45, 244, 26))
            slider.setContinuous_(True)
            slider.setTag_(index)
            slider.setAccessibilityLabel_(tr(device.name + '亮度百分比'))
            self.content.addSubview_(slider)
            self.glyph('sun.max', '提高亮度', 302, top + 51, 16)
            self.rows[key] = (slider, value)
            self.separator(top + 84)
        if not self.keys:
            self.text('未发现可调节屏幕', 20, 72, 300, 14, True)
            self.text('连接显示器并开启 DDC/CI，再点击刷新。', 20, 104, 300, 12, secondary=True, height=34)
            self.separator(148)
        top = 48 + monitor_height
        self.text('所有屏幕 · 快捷亮度', 20, top + 12, 300, 11, secondary=True)
        self.presets = []
        for index, (title, amount) in enumerate((('夜间 25%', 25), ('日常 60%', 60), ('明亮 100%', 100))):
            button = self.action(title, 'preset:', 18 + index * 103, top + 36, 98)
            button.setButtonType_(A.NSPushOnPushOffButton)
            button.setTag_(amount)
            self.presets.append(button)
        self.separator(top + 76)
        title = self.text('状态栏屏幕', 20, top + 91, 126, 12)
        self.centered(title, 20, top + 103, 126)
        self.target = A.NSPopUpButton.alloc().initWithFrame_pullsDown_(self.rect(150, top + 88, 172, 30), False)
        self.target.addItemsWithTitles_([tr('所有显示器')] + [tr(self.controller.displays[key].name) for key in self.keys])
        selected = self.settings.data['scroll_target']
        self.target.selectItemAtIndex_(self.keys.index(selected) + 1 if selected in self.keys else 0)
        self.target.setTarget_(self)
        self.target.setAction_('target:')
        self.target.setAccessibilityLabel_(tr('状态栏显示的屏幕'))
        self.content.addSubview_(self.target)
        self.message = self.text('', 20, top + 128, 300, 11, secondary=True, height=34)
        self.refresh_button = self.action('刷新', 'refresh:', 18, top + 167, 88, 'arrow.clockwise')
        self.diagnostic_button = self.action('设备诊断', 'diagnostics:', 112, top + 167, 116, 'info.circle')
        self.action('退出', 'quit:', 234, top + 167, 88, 'power')
        if self.diagnostics_open:
            scroller = A.NSScrollView.alloc().initWithFrame_(self.rect(20, top + 203, 300, 132))
            scroller.setHasVerticalScroller_(True)
            scroller.setDrawsBackground_(False)
            self.diagnostic_text = A.NSTextView.alloc().initWithFrame_(((0, 0), (286, 132)))
            self.diagnostic_text.setEditable_(False)
            self.diagnostic_text.setDrawsBackground_(False)
            self.diagnostic_text.setFont_(A.NSFont.systemFontOfSize_(11))
            self.diagnostic_text.setTextColor_(A.NSColor.secondaryLabelColor())
            self.diagnostic_text.setVerticallyResizable_(True)
            self.diagnostic_text.setHorizontallyResizable_(False)
            self.diagnostic_text.textContainer().setWidthTracksTextView_(True)
            scroller.setDocumentView_(self.diagnostic_text)
            self.content.addSubview_(scroller)
            top += 142
        self.text("Language" if language.english() else "语言", 20, top + 208, 130, 12)
        self.languages = A.NSPopUpButton.alloc().initWithFrame_pullsDown_(self.rect(164, top + 208 - 4, 158, 28), False)
        self.languages.addItemsWithTitles_(language.names())
        self.languages.selectItemAtIndex_(language.CHOICES.index(language.choice))
        self.languages.setTarget_(self)
        self.languages.setAction_("languageChanged:")
        self.content.addSubview_(self.languages)
        top += 38
        self.auto = A.NSButton.checkboxWithTitle_target_action_(tr('登录系统时启动'), self, 'startup:')
        self.auto.setFrame_(self.rect(20, top + 208, 200, 22))
        self.auto.setFont_(A.NSFont.systemFontOfSize_(11))
        self.auto.setEnabled_(not self.demo)
        self.auto.setState_(int(self.startup.enabled))
        self.content.addSubview_(self.auto)
        self.text('v' + __version__, 268, top + 210, 54, 11, secondary=True)
        self.view_controller.setView_(self.material)
        self.popover.setContentSize_((340, self.visible_height))
        self.scroll.contentView().scrollToPoint_((0, self.height - self.visible_height))
        self.scroll.reflectScrolledClipView_(self.scroll.contentView())

    def tick_(self, _):
        if self.closed:
            return
        changed = self.controller.poll()
        if self.generation != self.controller.generation:
            self.generation = self.controller.generation
            self.diagnostics_open = not bool(self.controller.displays)
            self.build()
            changed = True
        if changed:
            self.update()

    @objc.python_method
    def update(self):
        controller = self.controller
        self.summary = brightness_summary(controller.displays, controller.confirmed,
                                          self.settings.data['scroll_target'], controller.errors)
        if self.icon_key != self.summary:
            self.button.setImage_(status_image(self.summary))
            self.icon_key = self.summary
        self.button.setToolTip_(tr('明度\n' + self.summary.description))
        self.button.setAccessibilityLabel_(tr('明度，' + self.summary.description))
        for key, (slider, label) in self.rows.items():
            slider.setDoubleValue_(max(1, controller.values[key]))
            slider.setEnabled_(not controller.scanning)
            label.setStringValue_(tr(f'{controller.values[key]}%' + (' ·' if key in controller.pending else '')))
        for button in self.presets:
            button.setEnabled_(bool(controller.displays) and not controller.scanning)
            button.setState_(int(bool(controller.confirmed) and not controller.pending and not controller.errors
                                 and all(v == button.tag() for v in controller.confirmed.values())))
        self.refresh_button.setEnabled_(not controller.scanning)
        self.message.setStringValue_(tr(('演示 · ' if self.demo else '') + controller.message))
        self.message.setTextColor_(A.NSColor.systemRedColor() if controller.error else A.NSColor.secondaryLabelColor())
        self.message.setToolTip_(tr(self.message.stringValue()))
        if self.diagnostics_open:
            self.diagnostic_text.setString_(tr('\n\n'.join(controller.warnings + [
                '连接或唤醒显示器后请刷新。外接屏幕需开启 DDC/CI。新版 Mac 安装包自带辅助工具。'])))

    def brightness_(self, sender):
        self.controller.request(self.keys[sender.tag()], sender.doubleValue())
        self.tick_(None)

    def preset_(self, sender):
        self.controller.set_all(sender.tag())
        self.tick_(None)

    def target_(self, sender):
        index = sender.indexOfSelectedItem()
        self.settings.data['scroll_target'] = self.keys[index - 1] if index else 'all'
        if not self.demo:
            try:
                self.settings.save()
            except OSError as error:
                self.controller.status(f'无法保存偏好设置：{error}', True)
        self.update()

    def diagnostics_(self, _):
        self.diagnostics_open = not self.diagnostics_open
        self.build()
        self.update()

    def refresh_(self, _):
        self.controller.refresh()
        self.tick_(None)

    def languageChanged_(self, sender):
        value = language.CHOICES[sender.indexOfSelectedItem()]
        if not self.demo:
            try:
                self.settings.set_language(value)
            except OSError as error:
                self.controller.status(str(error), True)
                return
        language.select(value)
        self.button.setTitle_(tr("演示") if self.demo else "")
        self.build()
        self.update()

    def startup_(self, sender):
        try:
            self.startup.set_enabled(bool(sender.state()))
        except (OSError, ValueError) as error:
            self.controller.status(f'无法设置登录自启：{error}', True)
        sender.setState_(int(self.startup.enabled))
        self.tick_(None)

    def toggle_(self, _):
        if self.popover.isShown():
            self.popover.performClose_(None)
        else:
            self.show()

    @objc.python_method
    def show(self):
        self.tick_(None)
        A.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.popover.showRelativeToRect_ofView_preferredEdge_(self.button.bounds(), self.button, A.NSMinYEdge)

    def activate_(self, _):
        self.show()

    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, visible):
        self.show()
        return True

    def applicationWillTerminate_(self, _):
        self.close()
        if hasattr(self, 'instance'):
            self.instance.close()

    @objc.python_method
    def close(self):
        if self.closed:
            return
        self.closed = True
        self.timer.invalidate()
        self.popover.close()
        A.NSStatusBar.systemStatusBar().removeStatusItem_(self.status)
        self.controller.close()

    def quit_(self, _):
        self.close()
        A.NSApplication.sharedApplication().terminate_(None)


def run(hardware, args):
    app = A.NSApplication.sharedApplication()
    app.setActivationPolicy_(A.NSApplicationActivationPolicyAccessory)
    settings = Settings()
    instance = NativeInstance(settings, args.demo)
    if not instance.acquire():
        return 0
    controller = NativeController(hardware)
    panel = BrightnessPanel.alloc().init()
    panel.configure(controller, args.demo, settings)
    panel.instance = instance
    app.setDelegate_(panel)
    instance.ready(panel)
    controller.refresh()
    if not args.background:
        panel.show()
    try:
        app.run()
    finally:
        panel.close()
        instance.close()
    return 0
