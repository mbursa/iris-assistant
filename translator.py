"""
Soniox subtitles app (Windows, Python, no compilation)

What it does
------------
1) Captures microphone audio (16 kHz, mono, signed 16-bit PCM).
2) Streams audio to Soniox Real-time WebSocket API.
3) Always receives transcription tokens (and also translation tokens because we enable one-way translation).
4) Displays NOTHING until it hears the magic phrase in the *spoken transcript*:
       "sirius, we can start"
5) After the magic phrase is detected, it displays FINAL translation tokens in English
   (translation_status == "translation", language == "en", is_final == True).
6) It constantly replaces the on-screen text with the current accumulated translation buffer.
7) If no new final translation token arrives for a few seconds, it clears the subtitles.

Relevant Soniox docs
--------------------
- WebSocket endpoint, configuration message, binary audio frames, token response schema: :contentReference[oaicite:4]{index=4}
- Real-time translation modes and token metadata translation_status / language: :contentReference[oaicite:5]{index=5}
"""


from __future__ import annotations

import sys
from pathlib import Path

# make src importable, no matter where you run from
root = Path(__file__).resolve().parent
src = root / "src"
sys.path.insert(0, str(src))

from app import main  # now imports from src/app.py

if __name__ == "__main__":
    raise SystemExit(main())

exit();

