#!/usr/bin/env python3
"""Build native onedir distributions and archives on the current OS."""
import hashlib
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brightness import __version__


def build():
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build/pyinstaller"),
        str(ROOT / "packaging/mingdu.spec"),
    ], cwd=ROOT, check=True)
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    architecture = platform.machine().lower().replace("amd64", "x86_64").replace("aarch64", "arm64")
    base = ROOT / "dist" / f"mingdu-{__version__}-{system}-{architecture}"
    if system == "macos":
        # ditto preserves the framework symlinks inside .app bundles.
        archive = Path(str(base) + ".zip")
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                        str(ROOT / "dist/Mingdu.app"), str(archive)], check=True)
    else:
        archive = Path(shutil.make_archive(str(base), "zip" if system == "windows" else "gztar",
                                           root_dir=ROOT / "dist", base_dir="Mingdu"))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(f"{checksum}  {archive.name}\n", encoding="utf-8")
    print(f"Built {archive}")


if __name__ == "__main__":
    build()
