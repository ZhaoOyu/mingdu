"""AppKit integration with simulated hardware only; requires a Mac GUI session."""
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import AppKit as A
from Foundation import NSDate, NSRunLoop
from brightness.macos_app import BrightnessPanel
from brightness.native_controller import NativeController
from brightness.backends import DemoHardware, HardwareError, ScanResult
from brightness.settings import Settings
from brightness.startup import Startup


def main():
    app = A.NSApplication.sharedApplication()
    app.setActivationPolicy_(A.NSApplicationActivationPolicyAccessory)
    class Hardware(DemoHardware):
        writes = 0
        fail = empty = False
        def discover(self):
            return ScanResult([], ['No displays']) if self.empty else super().discover()
        def set_brightness(self, device, value):
            self.writes += 1
            if self.fail:
                raise HardwareError('Disconnected')
            return super().set_brightness(device, value)
    hardware = Hardware()
    controller = NativeController(hardware)
    with tempfile.TemporaryDirectory() as directory:
        panel = BrightnessPanel.alloc().init()
        panel.configure(controller, True, Settings(directory), Startup('linux',root=directory,command=['test']))
        def settle(predicate):
            end = time.monotonic() + 4
            while time.monotonic() < end:
                panel.tick_(None)
                NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(.01))
                if predicate():
                    return
            raise AssertionError('AppKit state did not settle')
        try:
            controller.refresh()
            settle(lambda: not controller.scanning)
            assert hardware.writes == 0
            assert isinstance(panel.popover, A.NSPopover)
            assert isinstance(panel.material, A.NSVisualEffectView)
            assert panel.popover.behavior() == A.NSPopoverBehaviorTransient
            assert panel.button.image().isTemplate()
            assert panel.summary.text == '≠'
            assert not panel.auto.isEnabled()
            first, second = controller.displays
            panel.target.selectItemAtIndex_(1)
            panel.target_(panel.target)
            assert panel.summary.value == 65
            slider = panel.rows[first][0]
            assert isinstance(slider, A.NSSlider)
            slider.setDoubleValue_(43)
            panel.brightness_(slider)
            assert panel.summary.value == 65
            settle(lambda: not controller.pending)
            assert panel.summary.value == 43 and hardware.values[second] == 80
            panel.presets[0].performClick_(None)
            settle(lambda: not controller.pending)
            assert set(hardware.values.values()) == {25}
            assert [b.state() for b in panel.presets] == [1, 0, 0]
            hardware.fail = True
            slider.setDoubleValue_(90)
            panel.brightness_(slider)
            settle(lambda: not controller.pending)
            assert panel.summary.text == '!' and slider.doubleValue() == 25
            assert controller.error
            hardware.fail = False
            hardware.empty = True
            panel.refresh_(None)
            settle(lambda: not controller.scanning)
            assert panel.diagnostics_open
            assert not any(b.isEnabled() for b in panel.presets)
            assert panel.visible_height <= 720
            print('PASS: native AppKit material, controls, debounce, confirmed ring, presets, rollback and empty state')
        finally:
            panel.close()
            controller.worker.thread.join(2)


if __name__ == '__main__':
    main()
