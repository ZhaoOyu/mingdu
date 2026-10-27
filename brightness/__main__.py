import argparse
import json
import sys
import os
import importlib.util
from dataclasses import asdict

from . import __version__
from .backends import HardwareError
from .platforms import create_hardware


def main():
    parser = argparse.ArgumentParser(description="明度 · 跨平台状态栏亮度调节")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--background", action="store_true", help="启动时仅显示状态栏图标")
    parser.add_argument("--demo", action="store_true", help="模拟双屏，不改变真实硬件")
    parser.add_argument("--diagnose", action="store_true", help="输出设备检测 JSON，不启动界面")
    parser.add_argument("--ui", choices=("auto", "qt", "gtk"), default="auto", help="自动选择 Qt 或 Ubuntu GTK 界面")
    args = parser.parse_args()
    try:
        hardware = create_hardware(args.demo)
    except (HardwareError, OSError) as exc:
        print(f"硬件接口初始化失败：{exc}", file=sys.stderr)
        return 1
    if args.diagnose:
        result = hardware.discover()
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 0 if result.displays else 1
    use_qt = args.ui == "qt" or (args.ui == "auto" and (
        getattr(sys, "frozen", False) or not sys.platform.startswith("linux") or importlib.util.find_spec("PySide6") is not None))
    if use_qt:
        if sys.platform.startswith("linux") and not any(os.environ.get(name) for name in (
                "DISPLAY", "WAYLAND_DISPLAY", "QT_QPA_PLATFORM")):
            print("无法连接图形桌面。无图形环境可使用 --diagnose。", file=sys.stderr)
            return 1
        try:
            from .qt_app import run
        except ImportError as exc:
            print(f'无法加载 Qt 界面：{exc}\n请在虚拟环境中安装：python -m pip install ".[qt]"', file=sys.stderr)
            return 1
        return run(hardware, args)
    if not sys.platform.startswith("linux"):
        print("GTK 界面仅用于 Linux，请使用 --ui qt。", file=sys.stderr)
        return 1
    try:
        from .app import BrightnessApp
    except (ImportError, ValueError) as exc:
        print(f"无法加载桌面组件：{exc}\n请安装：sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1", file=sys.stderr)
        return 1
    from gi.repository import Gtk
    if not Gtk.init_check()[0]:
        print("无法连接图形桌面。请在 Ubuntu 桌面会话中运行；无图形环境可使用 --diagnose。", file=sys.stderr)
        return 1
    return BrightnessApp(hardware, args).run([sys.argv[0]])


if __name__ == "__main__":
    raise SystemExit(main())
