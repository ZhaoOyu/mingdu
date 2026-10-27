"""XDG configuration and login startup."""
import json
import os
from pathlib import Path
import tempfile
import sys


def config_dir():
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, encoding="utf-8", delete=False) as file:
            temporary = Path(file.name)
            file.write(text)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


class Settings:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else config_dir()
        self.path = self.root / "mingdu" / "settings.json"
        self.data = {"scroll_target": "all"}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("scroll_target"), str):
                self.data["scroll_target"] = data["scroll_target"]
        except (OSError, ValueError):
            pass

    def save(self):
        atomic_write(self.path, json.dumps(self.data, ensure_ascii=False, indent=2) + "\n")

    @property
    def autostart_path(self):
        return self.root / "autostart" / "io.github.mingdu.Brightness.desktop"

    @property
    def autostart(self):
        return self.autostart_path.exists()

    def set_autostart(self, enabled, launcher):
        if enabled:
            atomic_write(self.autostart_path, desktop_entry(launcher, background=True))
        else:
            self.autostart_path.unlink(missing_ok=True)


def desktop_entry(launcher, background=False):
    # Desktop Exec has its own quoting rules, not POSIX shell quoting.
    path = str(Path(launcher).resolve())
    if "\n" in path or "\r" in path:
        raise ValueError("启动器路径不能包含换行")
    path = path.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    path = path.replace("%", "%%")
    # Backslashes are interpreted once by the desktop-entry string parser.
    path = path.replace("\\", "\\\\")
    return (
        "[Desktop Entry]\nType=Application\nName=明度 Brightness\n"
        "Comment=在状态栏调节显示器亮度\n"
        f'Exec="{path}"' + (" --background" if background else "") + "\n"
        "Icon=display-brightness-symbolic\nTerminal=false\n"
        "Categories=Settings;HardwareSettings;\n"
        "StartupNotify=false\nX-GNOME-Autostart-enabled=true\n"
    )
