"""Launch the built app twice in demo mode to test bundled Qt and IPC."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
executable = root / "dist" / ("Mingdu.app/Contents/MacOS/Mingdu" if sys.platform == "darwin" else
                             "Mingdu/Mingdu.exe" if sys.platform == "win32" else "Mingdu/Mingdu")
subprocess.run([sys.executable, str(root / "tests/qt_instance_smoke.py"), "--executable", str(executable)], check=True)
