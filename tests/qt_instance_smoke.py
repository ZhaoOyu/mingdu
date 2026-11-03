"""Verify two real processes activate one Qt instance, using only demo hardware."""
import os
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, help="Validate a frozen executable instead of source")
    parser.add_argument("--native", action="store_true", help="Test default macOS AppKit frontend")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="mingdu-instance-") as directory:
        root = Path(directory)
        environment = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "HOME": directory,
                       "APPDATA": directory, "XDG_CONFIG_HOME": directory,
                       "PYTHONPATH": str(ROOT), "PYTHONUTF8": "1"}
        entry = [str(args.executable.resolve())] if args.executable else [sys.executable, "-m", "brightness"]
        command = entry + ["--demo", "--ui", "auto" if args.native else "qt", "--background"]
        lock_name = "native-demo.lock" if args.native else "qt-demo.lock"
        with (root / "output.log").open("w+", encoding="utf-8") as log:
            first = subprocess.Popen(command, cwd=root, env=environment, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if first.poll() is not None:
                        raise AssertionError("First instance exited during startup")
                    if any(path.stat().st_size for path in root.rglob(lock_name)):
                        break
                    time.sleep(0.05)
                else:
                    raise AssertionError("First instance did not acquire the lock")
                second = subprocess.run(command, cwd=root, env=environment, capture_output=True,
                                        text=True, timeout=8)
                assert second.returncode == 0, second.stderr
                assert first.poll() is None
                print("PASS: secondary process exits after activating existing demo instance (" + ("AppKit" if args.native else "Qt") + ")")
            finally:
                first.terminate()
                try:
                    first.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    first.kill()
                    first.wait(timeout=5)
                log.seek(0)
                output = log.read()
                if "Traceback (most recent call last)" in output:
                    raise AssertionError(output)


if __name__ == "__main__":
    main()
