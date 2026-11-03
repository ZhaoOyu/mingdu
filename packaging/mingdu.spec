# Build on each target OS; PyInstaller is not a cross-compiler.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH).parent
data = [(str(root / name), "docs") for name in (
    "LICENSE", "README.md", "README.en.md", "THIRD_PARTY_NOTICES.md",
)]
if sys.platform == "darwin":
    data += copy_metadata("pyobjc-core") + copy_metadata("pyobjc-framework-Cocoa")
else:
    data += copy_metadata("PySide6-Essentials") + copy_metadata("shiboken6")
data += [(str(root / "licenses"), "docs/licenses"),
         (str(root / "docs/INSTALL.md"), "docs")]
helper_binaries = []
if sys.platform == "darwin":
    sys.path.insert(0, str(root))
    from tools.build_macos_helpers import helper_names
    helper_root = root / "build/macos-helpers"
    for name in helper_names():
        helper = helper_root / "bin" / name
        if not helper.is_file():
            raise RuntimeError("Missing bundled helper; run tools/build_desktop.py first")
        helper_binaries.append((str(helper), "helpers"))
    data.append((str(helper_root / "docs"), "docs/helpers"))
a = Analysis(
    [str(root / "brightness/launcher.py")],
    pathex=[str(root)], binaries=helper_binaries, datas=data,
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["gi", "brightness.app", "tkinter"] + (
        ["PySide6", "shiboken6", "brightness.qt_app"] if sys.platform == "darwin" else
        ["AppKit", "Foundation", "objc", "brightness.macos_app", "brightness.native_instance"]), noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="Mingdu",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=sys.platform.startswith("linux"), disable_windowed_traceback=False,
)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Mingdu")
if sys.platform == "darwin":
    from brightness import __version__
    app = BUNDLE(
        collection, name="Mingdu.app", version=__version__, bundle_identifier="io.github.mingdu.Brightness",
        info_plist={"LSUIElement": True, "NSHighResolutionCapable": True,
                    "CFBundleDisplayName": "明度 Brightness"},
    )
