"""Per-user startup registration; never requires administrator privileges."""
from pathlib import Path
import plistlib
import subprocess
import sys

from .settings import atomic_write, config_dir


IDENTIFIER = "io.github.mingdu.Brightness"


def launch_command():
    if getattr(sys, "frozen", False):
        return [sys.executable, "--background"]
    return [sys.executable, str(Path(__file__).with_name("launcher.py").resolve()), "--background"]


def quote_desktop_argument(value):
    if "\n" in value or "\r" in value:
        raise ValueError("启动命令不能包含换行")
    value = value.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return '"' + value.replace("%", "%%").replace("\\", "\\\\") + '"'


class Startup:
    def __init__(self, platform=None, home=None, root=None, command=None):
        self.platform = platform or sys.platform
        self.home = Path(home) if home else Path.home()
        self.root = Path(root) if root else config_dir()
        self.command = command or launch_command()

    @property
    def path(self):
        if self.platform == "darwin":
            return self.home / "Library/LaunchAgents" / f"{IDENTIFIER}.plist"
        return self.root / "autostart" / f"{IDENTIFIER}.desktop"

    @staticmethod
    def _registry():
        import winreg
        return winreg

    @property
    def enabled(self):
        if self.platform == "win32":
            reg = self._registry()
            try:
                with reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                    value, _ = reg.QueryValueEx(key, IDENTIFIER)
                    return value == subprocess.list2cmdline(self.command)
            except FileNotFoundError:
                return False
        return self.path.is_file()

    def set_enabled(self, enabled):
        if self.platform == "win32":
            reg = self._registry()
            with reg.CreateKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                if enabled:
                    reg.SetValueEx(key, IDENTIFIER, 0, reg.REG_SZ, subprocess.list2cmdline(self.command))
                else:
                    try:
                        reg.DeleteValue(key, IDENTIFIER)
                    except FileNotFoundError:
                        pass
        elif not enabled:
            self.path.unlink(missing_ok=True)
        elif self.platform == "darwin":
            content = plistlib.dumps({"Label": IDENTIFIER, "ProgramArguments": self.command,
                                     "RunAtLoad": True, "ProcessType": "Interactive"}).decode("utf-8")
            atomic_write(self.path, content)
        elif self.platform.startswith("linux"):
            content = (
                "[Desktop Entry]\nType=Application\nName=明度 Brightness\n"
                "Exec=" + " ".join(quote_desktop_argument(arg) for arg in self.command) + "\n"
                "Icon=display-brightness-symbolic\nTerminal=false\nX-GNOME-Autostart-enabled=true\n"
            )
            atomic_write(self.path, content)
        else:
            raise OSError("此平台暂不支持登录自启")
