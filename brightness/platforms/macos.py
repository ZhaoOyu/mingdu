"""Adapters for separately installed macOS command-line hardware helpers.

No helper binaries or upstream code are bundled. Use stable UUIDs/CG display IDs
where possible; ddcctl's index-only API is resolved anew before each operation.
"""
import platform
from pathlib import Path
import re
import shutil

from brightness.backends import Display, HardwareError, ScanResult, percent, raw_value, run_command


UUID = r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}"


def find_helper(name):
    found = shutil.which(name)
    if found:
        return found
    # Finder-launched .app bundles do not inherit the user's shell PATH.
    for directory in ("/opt/homebrew/bin", "/usr/local/bin"):
        path = Path(directory) / name
        if path.is_file() and path.stat().st_mode & 0o111:
            return str(path)
    return None


def parse_m1_displays(output):
    return [(match.group(2).upper(), match.group(1).strip())
            for match in re.finditer(r"^\s*\[\d+\]\s+(.+?)\s+\((" + UUID + r")\)\s*$", output, re.M)]


def parse_ddcctl_displays(output):
    # Enumeration order is exactly the order of NSScreen's CGDisplay lines.
    return [(str(index + 1), match.group(1).upper()) for index, match in enumerate(
        re.finditer(r"CGDisplay\s+(" + UUID + r")\s+dispID\(#\d+\)", output))]


def parse_ddcctl_brightness(output):
    match = re.search(r"I: VCP control #16 \(0x10\) = current:\s*(\d+), max:\s*(\d+)", output)
    if not match:
        raise HardwareError("ddcctl 未能读取亮度，请检查 DDC/CI 和连接方式")
    current, maximum = map(int, match.groups())
    if maximum <= 0 or current > maximum:
        raise HardwareError("ddcctl 返回了无效的亮度范围")
    return current, maximum


def parse_apple_brightness(output):
    ids = {}
    for line in output.splitlines():
        match = re.search(r"^display (\d+): .*?ID (0x[\da-fA-F]+)", line)
        if match:
            ids[match.group(1)] = match.group(2)
    displays = []
    for match in re.finditer(r"^display (\d+): brightness ([\d.]+)\s*$", output, re.M):
        index, value = match.groups()
        try:
            current = float(value)
        except ValueError:
            continue
        if index in ids and 0 <= current <= 1:
            displays.append(Display(f"apple:{ids[index]}", f"Apple 背光屏幕 {int(index) + 1}",
                                    "apple", ids[index], 100, round(current * 100)))
    return displays


class MacHardware:
    def __init__(self, runner=run_command, finder=find_helper, machine=None):
        self.run, self.find = runner, finder
        self.machine = machine or platform.machine()

    def _read_m1(self, tool, identifier):
        try:
            current = int(self.run([tool, "display", identifier, "get", "luminance"]).strip())
            maximum = int(self.run([tool, "display", identifier, "max", "luminance"]).strip())
        except ValueError as exc:
            raise HardwareError("m1ddc 返回了无法识别的亮度数据") from exc
        if current < 0 or maximum <= 0 or current > maximum:
            raise HardwareError("此显示器无法读取 DDC/CI 亮度")
        return current, maximum

    def _list_intel(self, tool):
        return parse_ddcctl_displays(self.run([tool], merge_stderr=True, allowed_returncodes=(0, 1)))

    def discover(self):
        result = ScanResult()
        apple = self.find("brightness")
        if apple:
            try:
                result.displays.extend(parse_apple_brightness(self.run(
                    [apple, "-l"], merge_stderr=True, allowed_returncodes=(0, 1))))
            except HardwareError as exc:
                result.warnings.append(f"Apple 背光读取失败：{exc}")
        else:
            result.warnings.append("内置屏幕和 Apple 背光支持：请安装 brew install brightness。")
        name = "m1ddc" if self.machine in ("arm64", "aarch64") else "ddcctl"
        tool = self.find(name)
        if not tool:
            result.warnings.append(f"外接 DDC/CI 支持：请安装 brew install {name}。")
            return result
        try:
            if name == "m1ddc":
                candidates = parse_m1_displays(self.run([tool, "display", "list"]))
                for identifier, display_name in candidates:
                    try:
                        current, maximum = self._read_m1(tool, identifier)
                        result.displays.append(Display(f"m1ddc:{identifier}", display_name, "m1ddc",
                                                       identifier, maximum, percent(current, maximum)))
                    except HardwareError as exc:
                        result.warnings.append(f"{display_name}：{exc}")
            else:
                for index, identifier in self._list_intel(tool):
                    try:
                        output = self.run([tool, "-d", index, "-b", "?"], merge_stderr=True)
                        current, maximum = parse_ddcctl_brightness(output)
                        result.displays.append(Display(f"ddcctl:{identifier}", f"外接屏幕 {index}", "ddcctl",
                                                       identifier, maximum, percent(current, maximum)))
                    except HardwareError as exc:
                        result.warnings.append(f"外接屏幕 {index}：{exc}")
        except HardwareError as exc:
            result.warnings.append(f"macOS 外接屏幕检测失败：{exc}")
        return result

    def set_brightness(self, display, value):
        raw = raw_value(value, display.maximum)
        tool_name = "brightness" if display.kind == "apple" else display.kind
        if tool_name not in ("brightness", "m1ddc", "ddcctl"):
            raise HardwareError("不是 macOS 可控制的设备")
        tool = self.find(tool_name)
        if not tool:
            raise HardwareError(f"找不到 {tool_name}，请安装后刷新")
        if display.kind == "apple":
            self.run([tool, "-d", display.address, f"{value / 100:.2f}"])
            current = parse_apple_brightness(self.run([tool, "-l"], merge_stderr=True, allowed_returncodes=(0, 1)))
            for device in current:
                if device.address == display.address:
                    return device.value
            raise HardwareError("Apple 屏幕已断开，无法确认设置结果")
        if display.kind == "m1ddc":
            self.run([tool, "display", display.address, "set", "luminance", str(raw)])
            current, maximum = self._read_m1(tool, display.address)
            return percent(current, maximum)
        candidates = [(index, identifier) for index, identifier in self._list_intel(tool)
                      if identifier == display.address]
        if len(candidates) != 1:
            raise HardwareError("显示器已断开或标识不唯一，请刷新")
        index = candidates[0][0]
        output = self.run([tool, "-d", index, "-b", str(raw)], merge_stderr=True)
        if re.search(r"\bE:", output):
            raise HardwareError(output[-1000:])
        current, maximum = parse_ddcctl_brightness(self.run([tool, "-d", index, "-b", "?"], merge_stderr=True))
        return percent(current, maximum)
