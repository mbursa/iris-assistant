# Launches the live, speaker-aware microphone transcriber.

from __future__ import annotations

import sys
from pathlib import Path


# make repository source modules importable from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from app import transcriber_main


# delegate process behavior to the application composition root.
if __name__ == "__main__":
    raise SystemExit(transcriber_main())
