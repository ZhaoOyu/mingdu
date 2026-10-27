#!/usr/bin/python3
"""Install only this application in the user's XDG directories, no sudo."""
import argparse
import os
from pathlib import Path
import shutil
import sys

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from brightness.settings import atomic_write, config_dir, desktop_entry


def main():
    parser = argparse.ArgumentParser(description="安装或卸载明度（当前用户）")
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    destination = data / "mingdu"
    applications = data / "applications"
    desktop = applications / "io.github.mingdu.Brightness.desktop"
    if args.uninstall:
        if destination.is_symlink():
            raise SystemExit("安装目录是符号链接，停止卸载。")
        if (destination / ".mingdu-install").is_file():
            shutil.rmtree(destination)
        desktop.unlink(missing_ok=True)
        (config_dir() / "autostart/io.github.mingdu.Brightness.desktop").unlink(missing_ok=True)
        print("已卸载明度；保留 ~/.config/mingdu 中的设置。")
        return
    if destination.resolve() == SOURCE:
        raise SystemExit("当前已位于安装目录，无需再次安装。")
    if destination.is_symlink():
        raise SystemExit("安装目录是符号链接，停止安装。")
    if destination.exists() and not (destination / ".mingdu-install").is_file():
        raise SystemExit(f"{destination} 已存在且不属于明度，请更换 XDG_DATA_HOME。")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE / "brightness", destination / "brightness", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(SOURCE / "mingdu", destination / "mingdu")
    (destination / "mingdu").chmod(0o755)
    shutil.copy2(SOURCE / "README.md", destination / "README.md")
    (destination / ".mingdu-install").write_text("1\n")
    atomic_write(desktop, desktop_entry(destination / "mingdu"))
    # Existing autostart entries must follow the installed copy, not source files.
    autostart = config_dir() / "autostart/io.github.mingdu.Brightness.desktop"
    if autostart.exists():
        atomic_write(autostart, desktop_entry(destination / "mingdu", background=True))
    print(f"安装完成。在应用列表搜索“明度”，或运行：\n{destination / 'mingdu'}")


if __name__ == "__main__":
    main()
