"""Absolute-path launch target for source, wheel and frozen builds."""
from pathlib import Path
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brightness.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
