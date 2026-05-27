import os
import threading
import queue
import json
import textwrap
import time
from websockets.sync.client import connect
import pygame

from config import Settings
from subtitles import SubtitleState


# =============================================================================
#                           TEXT / DISPLAY HELPERS
# =============================================================================




def format_for_screen(raw: str, settings: Settings) -> list[str]:
    """
    Convert an arbitrary long string into a block of wrapped lines that:
      - approximately fits on screen
      - uses at most MAX_LINES_ON_SCREEN lines
      - keeps the *most recent* content when overflowing
    """
    raw = raw.strip()
    if not raw:
        return ""

    # Clip extremely long buffers (defensive)
    if len(raw) > settings.ui.max_display_chars:
        raw = raw[-settings.ui.max_display_chars:].lstrip()

    # Wrap to approximate line length
    wrapped_lines = textwrap.wrap(raw, width=settings.ui.max_line_chars_approx, break_long_words=False)

    # Keep only the last MAX_LINES lines (subtitle-like behavior)
    if len(wrapped_lines) > settings.ui.max_lines_on_screen:
        wrapped_lines = wrapped_lines[-settings.ui.max_lines_on_screen:]

    return wrapped_lines
#end def


# =============================================================================
#                        SONIOX STREAMING + TOKEN HANDLING
# =============================================================================


def normalize_for_search(s: str) -> str:
    """
    Normalize text for robust phrase matching.
    - Lowercases (optional elsewhere)
    - Collapses whitespace
    - Strips leading/trailing spaces
    """
    return " ".join(s.strip().split())
#end def



def build_soniox_config(settings: Settings) -> dict:
    """
    Build the JSON configuration object sent as the first WebSocket message.

    Per Soniox docs:
    - Send a JSON config message (api_key, model, audio_format, etc.)
    - Then send audio frames as binary WebSocket frames. :contentReference[oaicite:11]{index=11}

    We enable one-way translation (target_language='en'). :contentReference[oaicite:12]{index=12}
    """
    cfg = {
        "api_key": settings.soniox.api_key,
        "model": settings.soniox.model,
        "audio_format": settings.audio.audio_format,
        "sample_rate": settings.audio.sample_rate,
        "num_channels": settings.audio.channels,
        "language_hints": list(settings.soniox.language_hints),
        "enable_endpoint_detection": settings.soniox.enable_endpoint_detection,
        "translation": {
            "type": "one_way",
            "target_language": settings.translation.target_language,
        },
    }
    return cfg


def token_is_original_spoken(token: dict) -> bool:
    """
    Return True if token represents original spoken transcript.

    Soniox translation tokens are labeled with translation_status:
      - "original" or "none" represent spoken transcript
      - "translation" represent translated text :contentReference[oaicite:13]{index=13}
    """
    status = token.get("translation_status", "none")
    return status in ("none", "original")


def token_is_end_of_sentence(token: dict) -> bool:
    """
    Return True if token represents end of sentence.
    """
    return (token.get("translation_status", "none") == "none") and (token.get("text") == "<end>")
#end def


def token_is_translation(token: dict) -> bool:
    """
    Return True if token represents translated text.
    """
    return token.get("translation_status") == "translation"


def token_is_final(token: dict) -> bool:
    """
    Return True if token is finalized.
    Soniox includes `is_final` boolean on tokens. :contentReference[oaicite:14]{index=14}
    """
    return bool(token.get("is_final", False))


def append_final_translation(subtitles: SubtitleState, translated_piece: str, settings: Settings) -> None:
    """
    Append translated text into the translation buffer, then update formatted display text.
    This is called ONLY once we're triggered (magic phrase heard), and ONLY for final tokens.
    """
    if not translated_piece:
        return

    formatted_lines = format_for_screen(translated_piece, settings)
    subtitles.add(formatted_lines)
#end def


def soniox_worker(
    audio_q: "queue.Queue[bytes]",
    subtitles: SubtitleState,
    stop_evt: threading.Event,
    settings: Settings,
) -> None:
    """
    Background thread that:
      1) opens the Soniox WebSocket
      2) sends JSON config
      3) streams audio frames (binary)
      4) receives JSON token messages and updates shared subtitles

    Token stream details:
    - Responses are JSON with "tokens": [...] :contentReference[oaicite:15]{index=15}
    - Tokens include `text`, `is_final`, and translation metadata (`translation_status`, `language`, `source_language`) :contentReference[oaicite:16]{index=16}
    """

    api_key = settings.soniox.api_key
    if not api_key:
        raise RuntimeError("Missing SONIOX_API_KEY environment variable.")

    config = build_soniox_config(settings)

    spoken_buffer = ""

    # Connect to Soniox WebSocket endpoint :contentReference[oaicite:17]{index=17}
    with connect(settings.soniox.ws_url, ping_interval=20) as ws:
        # First message must be JSON config :contentReference[oaicite:18]{index=18}
        ws.send(json.dumps(config))

        # --- Audio sender thread ---
        # We keep sending raw audio chunks from audio_q as binary frames. :contentReference[oaicite:19]{index=19}
        def send_audio_loop() -> None:
            while not stop_evt.is_set():
                try:
                    chunk = audio_q.get(timeout=0.1)
                except queue.Empty:
                    continue
                try:
                    ws.send(chunk)  # binary websocket frame
                except Exception:
                    # If the socket is closed/errored, we stop.
                    break

        sender = threading.Thread(target=send_audio_loop, daemon=True)
        sender.start()

        # --- Receiver loop ---
        # We parse token messages. For magic phrase detection, we use FINAL original-spoken tokens.
        # For subtitles, after triggered, we use FINAL translation tokens in English.
        while not stop_evt.is_set():
            try:
                msg = ws.recv()
            except Exception:
                break

            if msg is None:
                continue

            # Soniox sends JSON responses; audio is binary from client -> server. :contentReference[oaicite:20]{index=20}
            if isinstance(msg, (bytes, bytearray)):
                continue

            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                continue

            # If the server indicates finished, we could stop gracefully.
            # Finished response is documented as {"finished": true, ...}. :contentReference[oaicite:21]{index=21}
            if data.get("finished"):
                break

            tokens = data.get("tokens") or []
            if not tokens:
                continue

            #print(tokens)

            # --- 1) Build spoken transcript pieces ---
            # We only use FINAL spoken tokens to avoid matching transient partial text.
            spoken_piece = ""
            for t in tokens:
                if token_is_original_spoken(t) and token_is_final(t):
                    # token['text'] may contain leading spaces (subword tokenization). Keep it as-is.
                    spoken_piece += t.get("text", "")

            translated_piece = ""
            for t in tokens:
                if not token_is_translation(t):
                    continue
                    
                if t.get("source_language") != settings.translation.source_language:
                    continue

                # Only English translations
                if t.get("language") != settings.translation.target_language:
                    continue

                # Only final tokens if requested :contentReference[oaicite:22]{index=22}
                if settings.translation.display_only_final_translations and not token_is_final(t):
                    continue

                #print(t)
                translated_piece += t.get("text", "")
            #end for

            if translated_piece:
                print('>>>', translated_piece)
                append_final_translation(subtitles, translated_piece, settings)
        #end while
    #end with
#end def
