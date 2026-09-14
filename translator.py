# Launches the live microphone-to-subtitle translator.

from __future__ import annotations

import sys
from pathlib import Path


# make repository source modules importable from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from app import translator_main


# delegate process behavior to the application composition root.
if __name__ == "__main__":
    raise SystemExit(translator_main())
