"""Lazy platform selection: importing on one OS never loads another OS's DLLs."""
import sys

from brightness.backends import DemoHardware, Hardware, HardwareError


def create_hardware(demo=False, platform=None):
    if demo:
        return DemoHardware()
    platform = platform or sys.platform
    if platform.startswith("linux"):
        return Hardware()
    if platform == "win32":
        from .windows import WindowsHardware
        return WindowsHardware()
    if platform == "darwin":
        from .macos import MacHardware
        return MacHardware()
    raise HardwareError(f"暂不支持的平台：{platform}")
