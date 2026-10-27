"""Hardware access, independent of GTK. No shell commands or elevated GUI."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import shutil
import subprocess


class HardwareError(RuntimeError):
    pass


def run_command(args: list[str], timeout: int = 12, merge_stderr: bool = False,
                allowed_returncodes=(0,)) -> str:
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
            env={**os.environ, "LC_ALL": "C"}, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
    except FileNotFoundError as exc:
        raise HardwareError(f"未安装 {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HardwareError(f"{args[0]} 响应超时，请检查显示器连接") from exc
    except OSError as exc:
        raise HardwareError(f"无法运行 {args[0]}：{exc}") from exc
    if result.returncode not in allowed_returncodes:
        detail = (result.stderr.strip() or result.stdout.strip() or "命令执行失败")
        raise HardwareError(detail[-1200:])
    return result.stdout + ("\n" + result.stderr if merge_stderr else "")


def percent(raw: int, maximum: int) -> int:
    if maximum <= 0:
        raise HardwareError("显示器返回的最大亮度无效")
    return max(0, min(100, round(raw * 100 / maximum)))


def raw_value(value: int, maximum: int) -> int:
    if not 1 <= value <= 100:
        raise ValueError("亮度必须在 1–100 之间")
    if maximum <= 0:
        raise HardwareError("显示器返回的最大亮度无效")
    return max(1, round(value * maximum / 100))


@dataclass(frozen=True)
class Display:
    id: str
    name: str
    kind: str
    address: str
    maximum: int
    value: int


@dataclass
class ScanResult:
    displays: list[Display] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_vcp(output: str) -> tuple[int, int]:
    match = re.search(r"^\s*VCP\s+10\s+C\s+(\d+)\s+(\d+)\s*$", output, re.M)
    if not match:
        raise HardwareError("显示器未返回可调节的亮度（VCP 10），请开启 DDC/CI")
    current, maximum = map(int, match.groups())
    if maximum <= 0 or current > maximum:
        raise HardwareError("显示器返回的亮度范围无效")
    return current, maximum


def parse_detect(output: str) -> list[tuple[str, str]]:
    """Only numbered, valid displays; ignore 'Invalid display' sections."""
    found = []
    for block in re.split(r"(?m)^(?=Display\s+\d+|Invalid display|Phantom display)", output):
        if not re.match(r"Display\s+\d+", block):
            continue
        bus = re.search(r"I2C bus:\s*/dev/i2c-(\d+)", block)
        monitor = re.search(r"Monitor:\s*(.+)", block)
        if bus:
            fields = monitor.group(1).strip().split(":") if monitor else []
            name = fields[1].strip() if len(fields) > 1 else ""
            found.append((bus.group(1), name or f"外接显示器 · I²C {bus.group(1)}"))
    return list(dict.fromkeys(found))


class Hardware:
    def __init__(self, runner=run_command, backlight_root=Path("/sys/class/backlight"), which=shutil.which):
        self.run = runner
        self.backlight_root = Path(backlight_root)
        self.which = which

    def discover(self) -> ScanResult:
        result = ScanResult()
        try:
            paths = sorted(self.backlight_root.iterdir())
        except OSError as exc:
            paths = []
            result.warnings.append(f"无法读取系统背光设备：{exc}")
        for path in paths:
            try:
                maximum = int((path / "max_brightness").read_text())
                current = int((path / "brightness").read_text())
                result.displays.append(Display(
                    f"backlight:{path.name}", f"内置屏幕 · {path.name}",
                    "backlight", path.name, maximum, percent(current, maximum),
                ))
            except (OSError, ValueError, HardwareError) as exc:
                result.warnings.append(f"{path.name}：{exc}")
        if not self.which("ddcutil"):
            result.warnings.append("外接屏幕支持未启用：请安装 ddcutil（sudo apt install ddcutil）。")
            return result
        try:
            output = self.run(["ddcutil", "detect", "--brief"], timeout=45)
            candidates = parse_detect(output)
            if "Invalid display" in output:
                result.warnings.append("部分显示器不支持 DDC/CI 或无法访问；请检查显示器菜单、连接线和 I²C 权限。")
            for bus, name in candidates:
                try:
                    current, maximum = parse_vcp(self.run([
                        "ddcutil", "--bus", bus, "getvcp", "10", "--terse",
                    ]))
                    result.displays.append(Display(
                        f"ddc:{bus}", name, "ddc", bus, maximum, percent(current, maximum),
                    ))
                except HardwareError as exc:
                    result.warnings.append(f"{name}：{exc}")
        except HardwareError as exc:
            result.warnings.append(f"外接屏幕检测失败：{exc}")
        return result

    def set_brightness(self, display: Display, value: int) -> int:
        raw = raw_value(value, display.maximum)
        if display.kind == "backlight":
            # 'auto' resolves the caller's session, including user-service launches.
            self.run([
                "gdbus", "call", "--system", "--dest", "org.freedesktop.login1",
                "--object-path", "/org/freedesktop/login1/session/auto",
                "--method", "org.freedesktop.login1.Session.SetBrightness",
                "backlight", display.address, str(raw),
            ])
        elif display.kind == "ddc":
            # Keep ddcutil's default verification enabled; do not use --noverify.
            self.run(["ddcutil", "--bus", display.address, "setvcp", "10", str(raw)])
        else:
            raise HardwareError(f"未知的显示器类型：{display.kind}")
        return percent(raw, display.maximum)


class DemoHardware:
    """Explicitly opt-in preview; never communicates with physical monitors."""
    def __init__(self):
        self.values = {"demo:internal": 65, "demo:external": 80}

    def discover(self):
        return ScanResult([
            Display("demo:internal", "内置屏幕", "demo", "eDP-1", 100, self.values["demo:internal"]),
            Display("demo:external", "DELL U2723QE", "demo", "DP-1", 100, self.values["demo:external"]),
        ], ["演示模式：所有数值均为模拟，不会改变真实屏幕亮度。"])

    def set_brightness(self, display, value):
        raw_value(value, 100)
        self.values[display.id] = value
        return value
