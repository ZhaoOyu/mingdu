#!/usr/bin/python3
"""Build an architecture-independent package without root or pip."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brightness import __version__
from brightness.settings import desktop_entry


def build():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mingdu-deb-") as temporary:
        package = Path(temporary)
        app = package / "usr/share/mingdu"
        app.mkdir(parents=True)
        shutil.copytree(ROOT / "brightness", app / "brightness", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(ROOT / "mingdu", app / "mingdu")
        (app / "mingdu").chmod(0o755)
        binary = package / "usr/bin/mingdu"
        binary.parent.mkdir(parents=True)
        # A small shell launcher preserves argv and works independently of cwd.
        binary.write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/share/mingdu/mingdu "$@"\n')
        binary.chmod(0o755)
        desktop = package / "usr/share/applications/io.github.mingdu.Brightness.desktop"
        desktop.parent.mkdir(parents=True)
        desktop.write_text(desktop_entry("/usr/bin/mingdu"))
        docs = package / "usr/share/doc/mingdu"
        docs.mkdir(parents=True)
        shutil.copy2(ROOT / "README.md", docs / "README.md")
        shutil.copy2(ROOT / "LICENSE", docs / "copyright")
        shutil.copy2(ROOT / "docs/INSTALL.md", docs / "INSTALL.md")
        control = package / "DEBIAN/control"
        control.parent.mkdir()
        control.write_text(
            f"Package: mingdu\nVersion: {__version__}\nSection: utils\nPriority: optional\n"
            "Architecture: all\nMaintainer: Mingdu Contributors <maintainers@example.invalid>\n"
            "Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-3.0, gir1.2-ayatanaappindicator3-0.1, libglib2.0-bin\n"
            "Recommends: ddcutil, gnome-shell-extension-appindicator\n"
            "Description: Native display brightness panel and status indicator\n"
            " Adjust internal backlights and DDC/CI monitors from the Ubuntu panel.\n"
        )
        # TemporaryDirectory is 0700, and the user's umask may allow group writes.
        # A system package must carry conventional permissions for every entry.
        for path in [package, *package.rglob("*")]:
            path.chmod(0o755 if path.is_dir() or path in (binary, app / "mingdu") else 0o644)
        target = output / f"mingdu_{__version__}_all.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(package), str(target)], check=True)
        print(target)


if __name__ == "__main__":
    build()
