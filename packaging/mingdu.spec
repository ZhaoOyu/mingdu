# Build on each target OS; PyInstaller is not a cross-compiler.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH).parent
data = [(str(root / name), "docs") for name in (
    "LICENSE", "README.md", "README.en.md", "THIRD_PARTY_NOTICES.md",
)]
data += copy_metadata("PySide6-Essentials") + copy_metadata("shiboken6")
data += [(str(root / "licenses"), "docs/licenses")]
a = Analysis(
    [str(root / "brightness/launcher.py")],
    pathex=[str(root)], binaries=[], datas=data,
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["gi", "brightness.app", "tkinter"], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Mingdu",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=sys.platform.startswith("linux"), disable_windowed_traceback=False,
)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Mingdu")
if sys.platform == "darwin":
    app = BUNDLE(
        collection, name="Mingdu.app", bundle_identifier="io.github.mingdu.Brightness",
        info_plist={"LSUIElement": True, "NSHighResolutionCapable": True,
                    "CFBundleDisplayName": "明度 Brightness"},
    )
