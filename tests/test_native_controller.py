import time
import unittest

from brightness.backends import DemoHardware, HardwareError, ScanResult
from brightness.native_controller import NativeController


class Hardware(DemoHardware):
    fail = False
    empty = False
    writes = 0

    def discover(self):
        return ScanResult([], ['No devices']) if self.empty else super().discover()

    def set_brightness(self, display, value):
        self.writes += 1
        if self.fail:
            raise HardwareError('Disconnected')
        return super().set_brightness(display, value)


class NativeControllerTests(unittest.TestCase):
    def setUp(self):
        self.hardware = Hardware()
        self.controller = NativeController(self.hardware)
        self.controller.refresh()
        self.settle(lambda: not self.controller.scanning)
        self.first, self.second = self.controller.displays

    def tearDown(self):
        self.controller.close()
        self.controller.worker.thread.join(2)

    def settle(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            self.controller.poll()
            if predicate():
                return
            time.sleep(.01)
        self.fail('Hardware state did not settle')

    def test_read_only_startup_and_debounce_keeps_confirmed_value(self):
        self.assertEqual(self.hardware.writes, 0)
        for value in (40, 41, 43):
            self.controller.request(self.first, value)
        self.assertEqual(self.controller.confirmed[self.first], 65)
        self.settle(lambda: not self.controller.pending)
        self.assertEqual(self.hardware.writes, 1)
        self.assertEqual(self.controller.confirmed[self.first], 43)
        self.assertEqual(self.hardware.values[self.second], 80)

    def test_failure_rollback_and_refresh_flush(self):
        self.hardware.fail = True
        self.controller.request(self.first, 90)
        self.settle(lambda: not self.controller.pending)
        self.assertEqual(self.controller.values[self.first], 65)
        self.assertIn(self.first, self.controller.errors)
        self.hardware.fail = False
        self.controller.set_all(60)
        self.controller.refresh()
        self.settle(lambda: not self.controller.scanning)
        self.assertEqual(set(self.controller.confirmed.values()), {60})
        self.assertFalse(self.controller.errors)

    def test_stale_result_does_not_replace_new_target(self):
        self.controller.request(self.first, 70)
        revision = self.controller.revisions[self.first]
        self.controller.events.put(('write', (self.first, revision - 1, 55, None)))
        self.controller.poll()
        self.assertEqual(self.controller.values[self.first], 70)
        self.assertEqual(self.controller.confirmed[self.first], 55)
        self.settle(lambda: not self.controller.pending)
        self.assertEqual(self.controller.confirmed[self.first], 70)

    def test_empty_refresh_replaces_previous_displays(self):
        self.hardware.empty = True
        self.controller.refresh()
        self.settle(lambda: not self.controller.scanning)
        self.assertFalse(self.controller.displays)
        self.assertFalse(self.controller.confirmed)
