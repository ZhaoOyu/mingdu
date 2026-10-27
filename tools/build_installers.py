#!/usr/bin/env python3
"""Wrap the tested native bundle in a DMG or per-user Windows installer."""
from pathlib import Path
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from brightness import __version__


def build():
    if sys.platform == 'win32':
        compiler = shutil.which('ISCC') or str(Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Inno Setup 6/ISCC.exe')
        subprocess.run([compiler, f'/DAppVersion={__version__}', str(ROOT / 'packaging/windows.iss')], check=True)
        installer = ROOT / 'dist' / f'mingdu-{__version__}-windows-x86_64-setup.exe'
        # Exercise installation, the installed application, and uninstallation on CI.
        destination = ROOT / 'build/installed-smoke'
        subprocess.run([str(installer), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', f'/DIR={destination}'], check=True)
        try:
            subprocess.run([sys.executable, str(ROOT / 'tests/qt_instance_smoke.py'), '--executable', str(destination / 'Mingdu.exe')], check=True)
        finally:
            subprocess.run([str(destination / 'unins000.exe'), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], check=True)
            # Inno's uninstaller may delegate cleanup to another process.
            deadline = time.monotonic() + 30
            while (destination / 'Mingdu.exe').exists() and time.monotonic() < deadline:
                time.sleep(0.2)
            if (destination / 'Mingdu.exe').exists():
                raise RuntimeError('Uninstaller did not remove the installed application')
    elif sys.platform == 'darwin':
        arch = platform.machine().lower()
        target = ROOT / 'dist' / f'mingdu-{__version__}-macos-{arch}.dmg'
        with tempfile.TemporaryDirectory(prefix='mingdu-dmg-') as temporary:
            staging = Path(temporary)
            shutil.copytree(ROOT / 'dist/Mingdu.app', staging / 'Mingdu.app', symlinks=True)
            (staging / 'Applications').symlink_to('/Applications', target_is_directory=True)
            shutil.copy2(ROOT / 'docs/INSTALL.md', staging / 'INSTALL.md')
            subprocess.run(['hdiutil', 'create', '-volname', 'Mingdu', '-srcfolder', str(staging), '-ov', '-format', 'UDZO', str(target)], check=True)
        subprocess.run(['hdiutil', 'verify', str(target)], check=True)
    else:
        print('Linux uses the separate deb builder and portable archive.')


if __name__ == '__main__':
    build()
