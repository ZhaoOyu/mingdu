"""macOS process lock and distributed activation notification, without Qt."""
import fcntl
from hashlib import sha256
import os
import time

from Foundation import NSDistributedNotificationCenter


class NativeInstance:
    def __init__(self, settings, demo=False):
        root = settings.path.parent
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / ('native-demo.lock' if demo else 'native-main.lock')
        self.name = 'io.github.mingdu.activate.' + sha256(str(self.path).encode()).hexdigest()[:20]
        self.file = None

    def acquire(self):
        self.file = self.path.open('a+')
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            for _ in range(40):
                self.file.seek(0)
                if self.file.read().strip():
                    break
                time.sleep(.05)
            NSDistributedNotificationCenter.defaultCenter().postNotificationName_object_userInfo_deliverImmediately_(
                self.name, None, None, True)
            self.file.close()
            self.file = None
            return False
        self.file.seek(0)
        self.file.truncate()
        return True

    def ready(self, panel):
        NSDistributedNotificationCenter.defaultCenter().addObserver_selector_name_object_(panel, 'activate:', self.name, None)
        self.file.write(str(os.getpid()))
        self.file.flush()

    def close(self):
        if self.file:
            self.file.seek(0)
            self.file.truncate()
            fcntl.flock(self.file, fcntl.LOCK_UN)
            self.file.close()
            self.file = None
