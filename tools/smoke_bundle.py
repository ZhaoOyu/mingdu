"""Launch the built app twice in demo mode to test bundled Qt and IPC."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
executable = root / "dist" / ("Mingdu.app/Contents/MacOS/Mingdu" if sys.platform == "darwin" else
                             "Mingdu/Mingdu.exe" if sys.platform == "win32" else "Mingdu/Mingdu")
if sys.platform == "darwin":
    sys.path.insert(0, str(root))
    from tools.build_macos_helpers import helper_names
    contents = executable.parent.parent
    docs = contents / "Resources/docs/helpers"
    manifest = json.loads((docs / "manifest.json").read_text())
    assert {entry["name"] for entry in manifest} == set(helper_names())
    for entry in manifest:
        name = entry["name"]
        helper = contents / "Frameworks/helpers" / name
        assert helper.is_file() and helper.stat().st_mode & 0o111
        subprocess.run(["lipo", str(helper), "-verify_arch", platform.machine()], check=True)
        assert (docs / f"{name}-LICENSE.txt").stat().st_size > 100
        source = docs / f"{name}-source.tar.gz"
        assert hashlib.sha256(source.read_bytes()).hexdigest() == entry["source_sha256"]
    subprocess.run([str(executable), "--demo", "--smoke-test"], check=True, timeout=12)
    print("PASS: bundled helpers, architecture, source archives and license notices")
subprocess.run([sys.executable, str(root / "tests/qt_instance_smoke.py"), "--executable", str(executable)]
               + (["--native"] if sys.platform == "darwin" else []), check=True)
