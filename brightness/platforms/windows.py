"""Windows DDC/CI via DXVA2 and laptop backlights via WMI.

Physical-monitor handles are acquired for each operation and always released.
PowerShell runs without a console or profile; dynamic strings are base64 data.
"""
from contextlib import contextmanager
import base64
import ctypes as ct
from dataclasses import dataclass
import json
import os

from brightness.backends import Display, HardwareError, ScanResult, percent, raw_value, run_command


@dataclass
class NativeMonitor:
    address: str
    name: str
    handle: object


class WindowsDDC:
    def __init__(self):
        if os.name != "nt":
            raise HardwareError("Windows 显示器接口只能在 Windows 上运行")
        self.user = ct.WinDLL("user32", use_last_error=True)
        self.dxva = ct.WinDLL("dxva2", use_last_error=True)
        handle, dword, boolean = ct.c_void_p, ct.c_uint32, ct.c_int32

        class Rect(ct.Structure):
            _fields_ = [(name, ct.c_int32) for name in ("left", "top", "right", "bottom")]

        class MonitorInfo(ct.Structure):
            _fields_ = [("cbSize", dword), ("rcMonitor", Rect), ("rcWork", Rect),
                        ("dwFlags", dword), ("szDevice", ct.c_wchar * 32)]

        class DisplayDevice(ct.Structure):
            _fields_ = [("cb", dword), ("DeviceName", ct.c_wchar * 32),
                        ("DeviceString", ct.c_wchar * 128), ("StateFlags", dword),
                        ("DeviceID", ct.c_wchar * 128), ("DeviceKey", ct.c_wchar * 128)]

        class PhysicalMonitor(ct.Structure):
            _fields_ = [("handle", handle), ("description", ct.c_wchar * 128)]

        self.Info, self.Device, self.Physical = MonitorInfo, DisplayDevice, PhysicalMonitor
        self.Callback = ct.WINFUNCTYPE(boolean, handle, handle, ct.POINTER(Rect), ct.c_ssize_t)
        signatures = [
            (self.user.EnumDisplayMonitors, [handle, ct.POINTER(Rect), self.Callback, ct.c_ssize_t]),
            (self.user.GetMonitorInfoW, [handle, ct.POINTER(MonitorInfo)]),
            (self.user.EnumDisplayDevicesW, [ct.c_wchar_p, dword, ct.POINTER(DisplayDevice), dword]),
            (self.dxva.GetNumberOfPhysicalMonitorsFromHMONITOR, [handle, ct.POINTER(dword)]),
            (self.dxva.GetPhysicalMonitorsFromHMONITOR, [handle, dword, ct.POINTER(PhysicalMonitor)]),
            (self.dxva.DestroyPhysicalMonitors, [dword, ct.POINTER(PhysicalMonitor)]),
            (self.dxva.GetVCPFeatureAndVCPFeatureReply,
             [handle, ct.c_ubyte, ct.POINTER(ct.c_int), ct.POINTER(dword), ct.POINTER(dword)]),
            (self.dxva.SetVCPFeature, [handle, ct.c_ubyte, dword]),
        ]
        for function, args in signatures:
            function.argtypes, function.restype = args, boolean

    @staticmethod
    def _error(action):
        return HardwareError(f"{action}失败（Windows 错误 {ct.get_last_error()}），请检查连接和 DDC/CI")

    @contextmanager
    def monitors(self):
        allocated, monitors, warnings = [], [], []

        def collect(hmonitor, _hdc, _rect, _data):
            try:
                info = self.Info()
                info.cbSize = ct.sizeof(info)
                if not self.user.GetMonitorInfoW(hmonitor, ct.byref(info)):
                    raise self._error("读取显示器信息")
                count = ct.c_uint32()
                if not self.dxva.GetNumberOfPhysicalMonitorsFromHMONITOR(hmonitor, ct.byref(count)):
                    raise self._error("枚举物理显示器")
                if count.value == 0:
                    return 1
                if count.value > 128:
                    raise HardwareError("驱动返回了异常的显示器数量")
                physical = (self.Physical * count.value)()
                if not self.dxva.GetPhysicalMonitorsFromHMONITOR(hmonitor, count, physical):
                    raise self._error("获取物理显示器句柄")
                allocated.append((count, physical))
                for index, monitor in enumerate(physical):
                    device = self.Device()
                    device.cb = ct.sizeof(device)
                    identified = self.user.EnumDisplayDevicesW(info.szDevice, index, ct.byref(device), 1)
                    identity = device.DeviceID if identified and device.DeviceID else info.szDevice
                    address = json.dumps([identity, index, monitor.description], ensure_ascii=True)
                    monitors.append(NativeMonitor(address, monitor.description or info.szDevice, monitor.handle))
            except Exception as exc:
                warnings.append(str(exc))
            return 1

        callback = self.Callback(collect)
        try:
            if not self.user.EnumDisplayMonitors(None, None, callback, 0):
                raise self._error("枚举桌面显示器")
            yield monitors, warnings
        finally:
            for count, physical in allocated:
                self.dxva.DestroyPhysicalMonitors(count, physical)

    def read(self, monitor):
        current, maximum, kind = ct.c_uint32(), ct.c_uint32(), ct.c_int()
        if not self.dxva.GetVCPFeatureAndVCPFeatureReply(
                monitor.handle, 0x10, ct.byref(kind), ct.byref(current), ct.byref(maximum)):
            raise self._error("读取亮度")
        if maximum.value <= 0 or current.value > maximum.value:
            raise HardwareError("显示器返回了无效的亮度范围")
        return current.value, maximum.value

    def write(self, monitor, value):
        if not self.dxva.SetVCPFeature(monitor.handle, 0x10, value):
            raise self._error("设置亮度")


class WindowsWMI:
    def __init__(self, runner=run_command):
        self.run = runner

    def _script(self, script):
        preamble = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; "
        encoded = base64.b64encode((preamble + script).encode("utf-16-le")).decode("ascii")
        # Use the system executable, not an arbitrary powershell.exe on PATH.
        executable = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                  "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        return self.run([executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], timeout=15)

    def discover(self):
        output = self._script(
            "$items=@(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness | "
            "Where-Object {$_.Active} | Select-Object InstanceName,CurrentBrightness); "
            "ConvertTo-Json -InputObject $items -Compress"
        )
        try:
            data = json.loads(output.lstrip("\ufeff").strip() or "[]")
            if not isinstance(data, list):
                raise ValueError("expected a list")
            return [Display(f"wmi:{entry['InstanceName']}", f"内置屏幕 {index + 1}", "wmi",
                            entry["InstanceName"], 100, int(entry["CurrentBrightness"]))
                    for index, entry in enumerate(data)
                    if isinstance(entry.get("InstanceName"), str) and 0 <= int(entry["CurrentBrightness"]) <= 100]
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise HardwareError("无法解析 Windows 背光信息") from exc

    def write(self, display, value):
        name = base64.b64encode(display.address.encode("utf-8")).decode("ascii")
        output = self._script(
            f"$name=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{name}')); "
            "$monitor=@(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods | "
            "Where-Object {$_.InstanceName -eq $name}); "
            "if ($monitor.Count -ne 1) {throw 'Monitor disconnected or ambiguous'}; "
            f"$result=Invoke-CimMethod -InputObject $monitor[0] -MethodName WmiSetBrightness -Arguments @{{Timeout=[uint32]0;Brightness=[byte]{value}}}; "
            "if ($result.ReturnValue -ne 0) {throw ('WmiSetBrightness failed: '+$result.ReturnValue)}; "
            "$actual=Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness | "
            "Where-Object {$_.InstanceName -eq $name}; "
            "if ($null -eq $actual) {throw 'Monitor disconnected'}; $actual.CurrentBrightness"
        )
        try:
            actual = int(output.strip())
            if not 0 <= actual <= 100:
                raise ValueError()
            return actual
        except ValueError as exc:
            raise HardwareError("无法确认 Windows 背光设置结果") from exc


class WindowsHardware:
    def __init__(self, ddc=None, wmi=None):
        self.ddc = ddc if ddc is not None else WindowsDDC()
        self.wmi = wmi if wmi is not None else WindowsWMI()

    def discover(self):
        result = ScanResult()
        try:
            result.displays.extend(self.wmi.discover())
        except HardwareError as exc:
            result.warnings.append(f"Windows 内置背光不可用：{exc}")
        try:
            with self.ddc.monitors() as (monitors, warnings):
                result.warnings.extend(warnings)
                for monitor in monitors:
                    try:
                        current, maximum = self.ddc.read(monitor)
                        result.displays.append(Display(
                            f"win-ddc:{monitor.address}", monitor.name, "win-ddc", monitor.address,
                            maximum, percent(current, maximum),
                        ))
                    except HardwareError as exc:
                        result.warnings.append(f"{monitor.name}：{exc}")
        except HardwareError as exc:
            result.warnings.append(str(exc))
        return result

    def set_brightness(self, display, value):
        raw_value(value, display.maximum)  # Validate before dispatching to native APIs.
        if display.kind == "wmi":
            return self.wmi.write(display, value)
        if display.kind != "win-ddc":
            raise HardwareError("不是 Windows 可控制的设备")
        with self.ddc.monitors() as (monitors, _warnings):
            matches = [monitor for monitor in monitors if monitor.address == display.address]
            if len(matches) != 1:
                raise HardwareError("显示器已断开或标识不唯一，请刷新设备")
            monitor = matches[0]
            _, maximum = self.ddc.read(monitor)
            self.ddc.write(monitor, raw_value(value, maximum))
            current, maximum = self.ddc.read(monitor)
            return percent(current, maximum)
