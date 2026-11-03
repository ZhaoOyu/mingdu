"""Assemble the macOS app with Swift and the architecture-specific display tools."""
import os
import platform
import plistlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from brightness import __version__
from tools.build_macos_helpers import build_helpers

ROOT = Path(__file__).resolve().parents[1]


def build_app():
    helpers = build_helpers()
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "build") as temporary:
        app = Path(temporary) / "Mingdu.app"
        contents = app / "Contents"
        macos = contents / "MacOS"
        macos.mkdir(parents=True)
        environment = os.environ.copy()
        developer = "/Applications/Xcode.app/Contents/Developer"
        if Path(developer).is_dir():
            environment.setdefault("DEVELOPER_DIR", developer)
        subprocess.run(["xcrun", "swiftc", "-swift-version", "5", "-O", "-target",
                        platform.machine()+"-apple-macosx15.0", "-module-cache-path",
                        str(ROOT / "build/swift-module-cache"), *sorted((ROOT / "macos").glob("*.swift")),
                        "-o", macos / "Mingdu"], env=environment, check=True)
        resources = contents / "Resources"
        shutil.copytree(helpers / "docs", resources / "docs/helpers")
        shutil.copytree(helpers / "bin", contents / "Frameworks/helpers")
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            shutil.copy2(ROOT / name, resources)
        (contents / "Info.plist").write_bytes(plistlib.dumps(dict(
            CFBundleName="Mingdu", CFBundleDisplayName="明度", CFBundleExecutable="Mingdu",
            CFBundleIdentifier="io.github.mingdu.Brightness", CFBundleShortVersionString=__version__,
            CFBundleVersion=__version__, CFBundlePackageType="APPL", LSUIElement=True,
            NSHighResolutionCapable=True, LSMinimumSystemVersion="15.0")))
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", app], check=True)
        subprocess.run(["codesign", "--verify", "--deep", "--strict", app], check=True)
        target = dist / app.name
        if target.exists():
            target.rename(Path(temporary) / "previous.app")
        app.rename(target)
