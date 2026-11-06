# Provides reusable Soniox streaming and token-processing components.

from __future__ import annotations

import json
import queue
import threading
import textwrap
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from websockets.sync.client import ClientConnection, connect

from config import Settings
from subtitles import SubtitleState


# Callback invoked with each ordered batch of Soniox tokens.
# @type Callable[[list[dict[str, Any]]], None]
TokenHandler = Callable[[list[dict[str, Any]]], None]


class SonioxStreamError(RuntimeError):
    # Represents an error response returned by a Soniox real-time session.
    # --------------------------------------------------------------------------
    # The message contains Soniox's human-readable error detail for display by the
    # application boundary.
    # --------------------------------------------------------------------------
    pass
#end class


def format_for_screen(raw: str, settings: Settings) -> list[str]:
    # Wraps recent text into the configured subtitle-window capacity.
    # --------------------------------------------------------------------------
    # @param raw: Unformatted text buffer to render.
    # @param settings: Validated UI display limits.
    # @return: Most recent wrapped lines, or an empty list when text is blank.
    # --------------------------------------------------------------------------
    # normalize empty input before applying display limits.
    raw = raw.strip()
    if not raw:
        return []

    # retain only recent content so stale subtitles cannot dominate the display.
    if len(raw) > settings.ui.max_display_chars:
        raw = raw[-settings.ui.max_display_chars:].lstrip()

    # wrap and retain only lines that fit the configured subtitle window.
    wrapped_lines = textwrap.wrap(
        raw,
        width=settings.ui.max_line_chars_approx,
        break_long_words=False,
    )
    if len(wrapped_lines) > settings.ui.max_lines_on_screen:
        wrapped_lines = wrapped_lines[-settings.ui.max_lines_on_screen:]
    return wrapped_lines
#end def


def normalize_for_search(value: str) -> str:
    # Normalizes whitespace for reliable text comparison.
    # --------------------------------------------------------------------------
    # @param value: Source text to normalize.
    # @return: Trimmed text with internal whitespace collapsed.
    # --------------------------------------------------------------------------
    return " ".join(value.strip().split())
#end def


def build_realtime_config(
    *,
    api_key: str,
    model: str,
    audio_format: str,
    sample_rate: int,
    channels: int,
    language_hints: Iterable[str] = (),
    enable_endpoint_detection: bool = False,
    enable_speaker_diarization: bool = False,
    enable_language_identification: bool = False,
    translation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    # Builds a Soniox real-time session configuration.
    # --------------------------------------------------------------------------
    # This shared builder keeps raw-audio metadata consistent for transcription
    # and translation clients while exposing feature-specific switches.
    # @param api_key: Soniox credential used to authenticate the stream.
    # @param model: Soniox real-time model identifier.
    # @param audio_format: Soniox raw-audio encoding identifier.
    # @param sample_rate: Audio sampling frequency in Hz.
    # @param channels: Number of audio channels.
    # @param language_hints: Preferred recognition languages.
    # @param enable_endpoint_detection: Whether pauses force early finalization.
    # @param enable_speaker_diarization: Whether tokens include speaker labels.
    # @param enable_language_identification: Whether tokens include language labels.
    # @param translation: Optional Soniox translation configuration block.
    # @return: JSON-serializable Soniox session configuration.
    # --------------------------------------------------------------------------
    # include common authentication, model, and raw-audio fields for every session.
    config: dict[str, Any] = {
        "api_key": api_key,
        "model": model,
        "audio_format": audio_format,
        "sample_rate": sample_rate,
        "num_channels": channels,
        "language_hints": list(language_hints),
        "enable_endpoint_detection": enable_endpoint_detection,
        "enable_speaker_diarization": enable_speaker_diarization,
        "enable_language_identification": enable_language_identification,
    }

    # add translation only for consumers that request translated tokens.
    if translation is not None:
        config["translation"] = dict(translation)
    return config
#end def


def build_soniox_config(settings: Settings) -> dict[str, Any]:
    # Builds the translator's Soniox real-time session configuration.
    # --------------------------------------------------------------------------
    # @param settings: Validated translator application settings.
    # @return: JSON-serializable Soniox session configuration.
    # --------------------------------------------------------------------------
    return build_realtime_config(
        api_key=settings.soniox.api_key,
        model=settings.soniox.model,
        audio_format=settings.audio.audio_format,
        sample_rate=settings.audio.sample_rate,
        channels=settings.audio.channels,
        language_hints=(settings.translation.source_language,),
        enable_endpoint_detection=settings.soniox.enable_endpoint_detection,
        translation={
            "type": "one_way",
            "target_language": settings.translation.target_language,
        },
    )
#end def


def stream_realtime(
    *,
    ws_url: str,
    config: Mapping[str, Any],
    audio_q: "queue.Queue[bytes]",
    stop_evt: threading.Event,
    on_tokens: TokenHandler,
) -> None:
    # Runs a reusable Soniox real-time audio session.
    # --------------------------------------------------------------------------
    # A sender thread forwards queued PCM frames while the calling thread receives
    # ordered token batches. Setting stop_evt sends Soniox's end-of-stream marker.
    # @param ws_url: Soniox real-time WebSocket endpoint.
    # @param config: JSON-serializable session configuration.
    # @param audio_q: Bounded queue of audio frame bytes.
    # @param stop_evt: Shared event that requests graceful stream shutdown.
    # @param on_tokens: Consumer invoked for every non-empty token batch.
    # @return: None.
    # @throws SonioxStreamError: If Soniox returns an error response.
    # --------------------------------------------------------------------------
    # establish and configure the session before starting the audio sender.
    with connect(ws_url, ping_interval=20) as websocket:
        websocket.send(json.dumps(dict(config)))
        sender = threading.Thread(
            target=_send_audio,
            args=(websocket, audio_q, stop_evt),
            name="soniox-audio-sender",
            daemon=True,
        )
        sender.start()

        try:
            # receive JSON results until local shutdown or remote completion.
            while not stop_evt.is_set():
                message = websocket.recv()
                if message is None or isinstance(message, bytes):
                    continue

                # reject malformed server data and surface structured API errors.
                try:
                    response = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if response.get("error_code") is not None:
                    raise SonioxStreamError(
                        response.get("error_message", response.get("error_type", "Soniox error"))
                    )

                # deliver each token batch once before honoring remote completion.
                tokens = response.get("tokens") or []
                if tokens:
                    on_tokens(tokens)
                if response.get("finished"):
                    break
        finally:
            # ask the sender to emit the end marker while the socket remains open.
            stop_evt.set()
            sender.join(timeout=2)
#end def


def token_is_original_spoken(token: Mapping[str, Any]) -> bool:
    # Identifies tokens that represent original speech rather than translation.
    # --------------------------------------------------------------------------
    # @param token: Soniox token payload.
    # @return: True when the token belongs to the spoken transcript.
    # --------------------------------------------------------------------------
    return token.get("translation_status", "none") in ("none", "original")
#end def


def token_is_end_of_sentence(token: Mapping[str, Any]) -> bool:
    # Identifies Soniox's original-speech sentence boundary marker.
    # --------------------------------------------------------------------------
    # @param token: Soniox token payload.
    # @return: True when the token is the original-speech end marker.
    # --------------------------------------------------------------------------
    return token.get("translation_status", "none") == "none" and token.get("text") == "<end>"
#end def


def token_is_translation(token: Mapping[str, Any]) -> bool:
    # Identifies tokens emitted by Soniox's translation pipeline.
    # --------------------------------------------------------------------------
    # @param token: Soniox token payload.
    # @return: True when the token is translated text.
    # --------------------------------------------------------------------------
    return token.get("translation_status") == "translation"
#end def


def token_is_final(token: Mapping[str, Any]) -> bool:
    # Identifies tokens that Soniox will not revise later.
    # --------------------------------------------------------------------------
    # @param token: Soniox token payload.
    # @return: True when the token is final.
    # --------------------------------------------------------------------------
    return bool(token.get("is_final", False))
#end def


def append_final_translation(
    subtitles: SubtitleState,
    translated_piece: str,
    settings: Settings,
) -> None:
    # Formats final translated text and appends it to shared subtitle state.
    # --------------------------------------------------------------------------
    # @param subtitles: Thread-safe subtitle state updated for the UI.
    # @param translated_piece: Final Soniox translation text.
    # @param settings: Validated subtitle display settings.
    # @return: None.
    # --------------------------------------------------------------------------
    # avoid updating UI state for empty finalization events.
    if not translated_piece:
        return
    subtitles.add(format_for_screen(translated_piece, settings))
#end def


def soniox_worker(
    audio_q: "queue.Queue[bytes]",
    subtitles: SubtitleState,
    stop_evt: threading.Event,
    settings: Settings,
) -> None:
    # Streams microphone frames and applies matching translations to subtitles.
    # --------------------------------------------------------------------------
    # @param audio_q: Bounded queue of microphone PCM frame bytes.
    # @param subtitles: Shared subtitle state consumed by the UI thread.
    # @param stop_evt: Event requesting graceful stream shutdown.
    # @param settings: Validated Soniox, audio, and translation settings.
    # @return: None.
    # @throws RuntimeError: If the Soniox API key is missing.
    # --------------------------------------------------------------------------
    # reject missing credentials before establishing the remote connection.
    if not settings.soniox.api_key:
        raise RuntimeError("Missing SONIOX_API_KEY environment variable.")

    def handle_tokens(tokens: list[dict[str, Any]]) -> None:
        # Filters one token batch into displayable translation text.
        # ----------------------------------------------------------------------
        # @param tokens: Ordered Soniox token payloads from one response.
        # @return: None.
        # ----------------------------------------------------------------------
        # select translated tokens matching the configured language pair and finality.
        translated_parts: list[str] = []
        for token in tokens:
            if not token_is_translation(token):
                continue
            if token.get("source_language") != settings.translation.source_language:
                continue
            if token.get("language") != settings.translation.target_language:
                continue
            if settings.translation.display_only_final_translations and not token_is_final(token):
                continue
            translated_parts.append(str(token.get("text", "")))

        # update shared subtitle state only when the response adds visible text.
        translated_piece = "".join(translated_parts)
        if translated_piece:
            print(">>>", translated_piece)
            append_final_translation(subtitles, translated_piece, settings)
    #end def

    # compose translator-specific token handling with the shared stream lifecycle.
    stream_realtime(
        ws_url=settings.soniox.ws_url,
        config=build_soniox_config(settings),
        audio_q=audio_q,
        stop_evt=stop_evt,
        on_tokens=handle_tokens,
    )
#end def


def _send_audio(
    websocket: ClientConnection,
    audio_q: "queue.Queue[bytes]",
    stop_evt: threading.Event,
) -> None:
    # Sends queued audio frames and finalizes the Soniox stream on shutdown.
    # --------------------------------------------------------------------------
    # @param websocket: Connected Soniox WebSocket.
    # @param audio_q: Bounded queue of audio frame bytes.
    # @param stop_evt: Event requesting graceful stream shutdown.
    # @return: None.
    # --------------------------------------------------------------------------
    try:
        # wait briefly for frames so shutdown remains responsive during silence.
        while not stop_evt.is_set():
            try:
                websocket.send(audio_q.get(timeout=0.1))
            except queue.Empty:
                continue

        # send the documented empty binary frame to finalize pending tokens.
        websocket.send(b"")
    except Exception:
        # leave connection errors to the receiver and ensure all workers stop.
        stop_evt.set()
#end def
