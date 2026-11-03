"""Main-thread state for the AppKit frontend; serial hardware worker and debounce."""
import queue
import time

from .worker import HardwareWorker


class NativeController:
    def __init__(self, hardware):
        self.events = queue.SimpleQueue()
        self.worker = HardwareWorker(hardware, lambda kind, data: self.events.put((kind, data)))
        self.displays, self.values, self.confirmed = {}, {}, {}
        self.revisions, self.deadlines, self.errors = {}, {}, {}
        self.pending = set()
        self.warnings = []
        self.scanning = self.closed = False
        self.message, self.error = "正在读取显示器…", False
        self.generation = 0
        self.changed = True

    def status(self, message, error=False):
        self.message, self.error, self.changed = message, error, True

    def refresh(self):
        if self.scanning or self.closed:
            return
        for key in list(self.deadlines):
            self.dispatch(key)
        self.scanning = True
        self.status("正在读取显示器亮度…")
        self.worker.scan()

    def request(self, key, value):
        if self.scanning or self.closed or key not in self.displays:
            return
        self.values[key] = max(1, min(100, round(value)))
        self.revisions[key] = self.revisions.get(key, 0) + 1
        self.pending.add(key)
        self.errors.pop(key, None)
        self.deadlines[key] = time.monotonic() + .16
        self.status("正在应用亮度…")

    def set_all(self, value):
        for key in self.displays:
            self.request(key, value)

    def dispatch(self, key):
        self.deadlines.pop(key, None)
        self.worker.write(self.displays[key], self.values[key], self.revisions[key])

    def poll(self):
        if self.closed:
            return False
        for key, deadline in list(self.deadlines.items()):
            if time.monotonic() >= deadline:
                self.dispatch(key)
        while not self.events.empty():
            kind, data = self.events.get()
            if kind == "scan":
                self.scanning = False
                self.displays = {d.id: d for d in data.displays}
                self.values = {d.id: d.value for d in data.displays}
                self.confirmed = self.values.copy()
                self.pending.clear()
                self.errors.clear()
                self.warnings = data.warnings
                self.generation += 1
                self.status("已读取当前亮度" if self.displays else "未发现可调节屏幕，请查看设备诊断。")
            elif kind == "scan-error":
                self.scanning = False
                self.status(f"设备读取失败：{data}", True)
            elif kind == "write":
                key, revision, value, error = data
                if key not in self.displays:
                    continue
                if error is None:
                    self.confirmed[key] = value
                self.changed = True
                if revision != self.revisions.get(key):
                    continue
                self.pending.discard(key)
                self.values[key] = self.confirmed[key]
                if error:
                    self.errors[key] = error
                    self.warnings = (self.warnings + [f"{self.displays[key].name}：{error}"])[-12:]
                if self.errors:
                    self.status("调节失败，已恢复显示最近确认值。请查看设备诊断。", True)
                elif not self.pending and not self.scanning:
                    self.status("亮度已更新")
        changed, self.changed = self.changed, False
        return changed

    def close(self):
        self.closed = True
        self.deadlines.clear()
        self.worker.stop()
