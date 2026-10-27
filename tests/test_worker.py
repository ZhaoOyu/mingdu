from queue import Queue
from threading import Event
import unittest

from brightness.backends import DemoHardware, Display, HardwareError
from brightness.worker import HardwareWorker


class WorkerTests(unittest.TestCase):
    def test_rapid_writes_coalesce_and_scan_follows_final_write(self):
        entered, release = Event(), Event()
        events = Queue()
        calls = []
        class SlowHardware(DemoHardware):
            def set_brightness(self, display, value):
                calls.append(value)
                if len(calls) == 1:
                    entered.set()
                    if not release.wait(2):
                        raise RuntimeError("test timed out")
                return super().set_brightness(display, value)
        hardware = SlowHardware()
        worker = HardwareWorker(hardware, lambda event, data: events.put((event, data)))
        display = hardware.discover().displays[0]
        try:
            worker.write(display, 20, 1)
            self.assertTrue(entered.wait(2))
            for revision, value in enumerate(range(21, 90), 2):
                worker.write(display, value, revision)
            worker.scan()
            release.set()
            first = events.get(timeout=2)
            last = events.get(timeout=2)
            scan = events.get(timeout=2)
            self.assertEqual(first[0], "write")
            self.assertEqual(last[1][2], 89)
            self.assertEqual(scan[0], "scan")
            self.assertEqual(scan[1].displays[0].value, 89)
            self.assertEqual(calls, [20, 89])
        finally:
            release.set()
            worker.stop()
            worker.thread.join(2)
        self.assertFalse(worker.thread.is_alive())

    def test_failed_device_does_not_stop_other_devices(self):
        events = Queue()
        class Hardware(DemoHardware):
            def set_brightness(self, display, value):
                if display.id == "broken":
                    raise HardwareError("unplugged")
                return value
        worker = HardwareWorker(Hardware(), lambda event, data: events.put((event, data)))
        try:
            worker.write(Display("broken", "broken", "ddc", "1", 100, 50), 20, 1)
            worker.write(Display("working", "working", "ddc", "2", 100, 50), 60, 2)
            self.assertEqual(events.get(timeout=2)[1][-1], "unplugged")
            self.assertEqual(events.get(timeout=2)[1][2], 60)
        finally:
            worker.stop()
            worker.thread.join(2)

    def test_unexpected_discovery_exception_is_reported(self):
        events = Queue()
        class Broken:
            def discover(self):
                raise RuntimeError("driver failed")
        worker = HardwareWorker(Broken(), lambda event, data: events.put((event, data)))
        try:
            worker.scan()
            self.assertEqual(events.get(timeout=2), ("scan-error", "driver failed"))
        finally:
            worker.stop()
            worker.thread.join(2)


if __name__ == "__main__":
    unittest.main()
