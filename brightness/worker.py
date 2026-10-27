"""One hardware worker, bounded queue, latest value wins for each display."""
from collections import OrderedDict
from threading import Condition, Thread


class HardwareWorker:
    def __init__(self, hardware, emit):
        self.hardware = hardware
        self.emit = emit
        self.condition = Condition()
        self.pending = OrderedDict()
        self.scan_requested = False
        self.stopping = False
        self.thread = Thread(target=self._run, name="brightness-hardware", daemon=True)
        self.thread.start()

    def scan(self):
        with self.condition:
            self.scan_requested = True
            self.condition.notify()

    def write(self, display, value, revision):
        with self.condition:
            self.pending[display.id] = (display, value, revision)
            self.condition.notify()

    def stop(self):
        with self.condition:
            self.stopping = True
            self.pending.clear()
            self.condition.notify()

    def _run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.stopping or self.pending or self.scan_requested)
                if self.stopping:
                    return
                if self.pending:
                    _, (display, value, revision) = self.pending.popitem(last=False)
                    action = "write"
                else:
                    self.scan_requested = False
                    action = "scan"
            try:
                if action == "scan":
                    self.emit("scan", self.hardware.discover())
                else:
                    actual = self.hardware.set_brightness(display, value)
                    self.emit("write", (display.id, revision, actual, None))
            except Exception as exc:
                # A faulty driver must never silently kill the worker.
                if action == "scan":
                    self.emit("scan-error", str(exc))
                else:
                    self.emit("write", (display.id, revision, None, str(exc)))
