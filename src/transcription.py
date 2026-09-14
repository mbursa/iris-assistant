# Provides configuration and rendering components for live meeting transcription.

from __future__ import annotations

import argparse
import os
import queue
import threading
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, TextIO

import soniox
from config import read_dotenv


# Default Soniox real-time WebSocket endpoint.
# @var str
DEFAULT_WS_URL = "wss://stt-rt.soniox.com/transcribe-websocket"
# Default Soniox real-time speech-to-text model.
# @var str
DEFAULT_MODEL = "stt-rt-v5"
# Default microphone sampling frequency in Hz.
# @var int
DEFAULT_SAMPLE_RATE = 16_000
# Default microphone channel count.
# @var int
DEFAULT_CHANNELS = 1
# Default maximum number of queued microphone frames.
# @var int
DEFAULT_QUEUE_MAX_CHUNKS = 300


@dataclass(frozen=True)
class TranscriberOptions:
    # Defines runtime options for speaker-aware microphone transcription.
    # --------------------------------------------------------------------------
    # @var api_key: Soniox credential used to authenticate the stream.
    # @var ws_url: Soniox real-time WebSocket endpoint.
    # @var model: Soniox speech-to-text model identifier.
    # @var sample_rate: Microphone sampling frequency in Hz.
    # @var channels: Number of microphone channels.
    # @var language_hints: Preferred speech-recognition languages.
    # @var enable_endpoint_detection: Whether pauses force early finalization.
    # @var device: Optional SoundDevice input device index or name.
    # @var output_file: Optional append-only transcript file path.
    # @var list_devices: Whether startup should print devices and exit.
    # @var queue_max_chunks: Maximum number of queued microphone frames.
    # --------------------------------------------------------------------------
    # Soniox API credential loaded from local configuration.
    api_key: str
    # Soniox real-time WebSocket endpoint.
    ws_url: str = DEFAULT_WS_URL
    # Soniox real-time speech-to-text model identifier.
    model: str = DEFAULT_MODEL
    # Microphone sampling frequency in Hz.
    sample_rate: int = DEFAULT_SAMPLE_RATE
    # Number of captured microphone channels.
    channels: int = DEFAULT_CHANNELS
    # Preferred recognition languages in priority order.
    language_hints: tuple[str, ...] = ("en",)
    # Whether Soniox should finalize tokens after detected pauses.
    enable_endpoint_detection: bool = False
    # Optional SoundDevice input device index or name.
    device: int | str | None = None
    # Optional file that receives a copy of console transcript output.
    output_file: Path | None = None
    # Whether the CLI should list audio devices instead of transcribing.
    list_devices: bool = False
    # Bounded microphone-frame queue capacity.
    queue_max_chunks: int = DEFAULT_QUEUE_MAX_CHUNKS

    def validate(self) -> None:
        # Validates values required to start microphone transcription.
        # ----------------------------------------------------------------------
        # @return: None.
        # @throws ValueError: If credentials, connection values, or audio limits are invalid.
        # ----------------------------------------------------------------------
        # reject invalid values before opening microphone or network resources.
        if not self.api_key:
            raise ValueError("SONIOX_API_KEY is required. Set it in the environment or .env file.")
        if not self.ws_url:
            raise ValueError("Soniox WebSocket URL cannot be empty.")
        if not self.model:
            raise ValueError("Soniox model cannot be empty.")
        if self.sample_rate <= 0:
            raise ValueError("Microphone sample rate must be greater than zero.")
        if self.channels <= 0:
            raise ValueError("Microphone channel count must be greater than zero.")
        if self.queue_max_chunks <= 0:
            raise ValueError("Audio queue capacity must be greater than zero.")
    #end def
#end class


class TranscriptPrinter:
    # Renders final Soniox tokens as timestamped speaker transcript segments.
    # --------------------------------------------------------------------------
    # Mutable state retains the active speaker and token boundary so consecutive
    # tokens are grouped into readable turns without buffering the full meeting.
    # --------------------------------------------------------------------------

    def __init__(self, output_path: Path | None = None) -> None:
        # Initializes console and optional file transcript output.
        # ----------------------------------------------------------------------
        # @param output_path: Optional UTF-8 file opened in append mode.
        # @return: None.
        # @throws OSError: If the requested output file cannot be opened.
        # ----------------------------------------------------------------------
        # retain the active speaker until a speaker change or long pause occurs.
        self._speaker: str | None = None
        # retain the latest token boundary for silence-gap detection.
        self._last_end_ms: int | float | None = None
        # track whether a prior segment needs a separating newline.
        self._wrote_output = False
        # retain ownership of the optional append-only output stream until finish.
        self._output: TextIO | None = (
            output_path.open("a", encoding="utf-8") if output_path is not None else None
        )
    #end def

    def write_tokens(self, tokens: Iterable[dict[str, Any]]) -> None:
        # Prints final original-speech tokens grouped by speaker.
        # ----------------------------------------------------------------------
        # @param tokens: Soniox token payloads received in stream order.
        # @return: None.
        # ----------------------------------------------------------------------
        # exclude revisable, translated, empty, and control tokens.
        for token in tokens:
            if not token.get("is_final") or token.get("translation_status") == "translation":
                continue

            text = token.get("text", "")
            if not isinstance(text, str) or not text or text == "<end>":
                continue

            # begin a new turn after a speaker change or more than 1.5 seconds of silence.
            speaker = str(token.get("speaker") or "Unknown")
            start_ms = token.get("start_ms")
            new_segment = (
                speaker != self._speaker
                or (
                    isinstance(start_ms, (int, float))
                    and isinstance(self._last_end_ms, (int, float))
                    and start_ms - self._last_end_ms > 1_500
                )
            )
            if new_segment:
                if self._wrote_output:
                    self._write("\n")
                self._write(f"[{self._timestamp(start_ms)} Speaker {speaker}] ")
                self._speaker = speaker
                self._wrote_output = True

            # preserve Soniox token spacing while updating the latest time boundary.
            self._write(text)
            end_ms = token.get("end_ms")
            if isinstance(end_ms, (int, float)):
                self._last_end_ms = end_ms
    #end def

    def finish(self) -> None:
        # Terminates any active console transcript line.
        # ----------------------------------------------------------------------
        # @return: None.
        # ----------------------------------------------------------------------
        # terminate the active line before closing the owned append stream.
        if self._wrote_output:
            self._write("\n")
            self._wrote_output = False
        if self._output is not None:
            self._output.close()
            self._output = None
    #end def

    def _write(self, value: str) -> None:
        # Writes identical transcript content to the console and optional file.
        # ----------------------------------------------------------------------
        # Each write is flushed so the append-only file follows live console output.
        # @param value: Transcript text to emit without added separators.
        # @return: None.
        # @throws OSError: If writing or flushing the output file fails.
        # ----------------------------------------------------------------------
        print(value, end="", flush=True)
        if self._output is not None:
            self._output.write(value)
            self._output.flush()
    #end def

    @staticmethod
    def _timestamp(milliseconds: object) -> str:
        # Converts a Soniox millisecond offset into a display timestamp.
        # ----------------------------------------------------------------------
        # @param milliseconds: Stream-relative token offset in milliseconds.
        # @return: HH:MM:SS timestamp or a placeholder when timing is unavailable.
        # ----------------------------------------------------------------------
        # preserve a stable prefix when the server omits token timing metadata.
        if not isinstance(milliseconds, (int, float)):
            return "--:--:--"
        total_seconds = max(0, int(milliseconds // 1_000))
        hours, remainder = divmod(total_seconds, 3_600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    #end def
#end class


def load_transcriber_options(argv: Sequence[str] | None = None) -> TranscriberOptions:
    # Loads dotenv, environment, and command-line transcriber options.
    # --------------------------------------------------------------------------
    # Command-line values override process environment, which overrides `.env`.
    # @param argv: Optional argument sequence; None reads the process command line.
    # @return: Parsed transcriber options without opening external resources.
    # --------------------------------------------------------------------------
    # combine configuration sources without mutating the process environment.
    root = Path(__file__).resolve().parent.parent
    env = {**read_dotenv(root / ".env"), **os.environ}

    # define the standalone transcriber interface and environment-backed defaults.
    parser = argparse.ArgumentParser(
        description="Transcribe microphone audio with Soniox real-time STT."
    )
    parser.add_argument("--api-key", default=env.get("SONIOX_API_KEY", ""))
    parser.add_argument("--device", type=_parse_device, help="SoundDevice input device ID or name.")
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=_environment_int(env, "SONIOX_SAMPLE_RATE", DEFAULT_SAMPLE_RATE),
    )
    parser.add_argument(
        "--language-hint",
        action="append",
        default=None,
        metavar="LANG",
        help="Preferred speech language; repeat for multilingual meetings.",
    )
    parser.add_argument("--model", default=env.get("SONIOX_MODEL", DEFAULT_MODEL))
    parser.add_argument("--ws-url", default=env.get("SONIOX_WS_URL", DEFAULT_WS_URL))
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Append a copy of the speaker-labelled transcript to this UTF-8 file.",
    )
    parser.add_argument(
        "--enable-endpoint-detection",
        action="store_true",
        help="Finalize after pauses sooner; leaving this off gives diarization more context.",
    )
    parser.add_argument("--list-devices", action="store_true", help="List audio devices and exit.")
    args = parser.parse_args(argv)

    # use comma-separated environment hints only when CLI hints were not supplied.
    language_hints = args.language_hint
    if language_hints is None:
        language_hints = [
            value.strip()
            for value in env.get("SONIOX_LANGUAGE_HINTS", "en").split(",")
            if value.strip()
        ]

    return TranscriberOptions(
        api_key=args.api_key.strip(),
        ws_url=args.ws_url,
        model=args.model,
        sample_rate=args.sample_rate,
        language_hints=tuple(language_hints),
        enable_endpoint_detection=args.enable_endpoint_detection,
        device=args.device,
        output_file=args.output_file,
        list_devices=args.list_devices,
    )
#end def


def build_session_config(options: TranscriberOptions) -> dict[str, Any]:
    # Builds the speaker-aware Soniox configuration for a transcriber session.
    # --------------------------------------------------------------------------
    # @param options: Validated transcriber runtime options.
    # @return: JSON-serializable Soniox real-time session configuration.
    # --------------------------------------------------------------------------
    return soniox.build_realtime_config(
        api_key=options.api_key,
        model=options.model,
        audio_format="pcm_s16le",
        sample_rate=options.sample_rate,
        channels=options.channels,
        language_hints=options.language_hints,
        enable_endpoint_detection=options.enable_endpoint_detection,
        enable_speaker_diarization=True,
        enable_language_identification=True,
    )
#end def


def run_session(
    options: TranscriberOptions,
    audio_q: "queue.Queue[bytes]",
    stop_evt: threading.Event,
    on_tokens: Callable[[list[dict[str, Any]]], None],
) -> None:
    # Runs a speaker-aware transcription session over the shared Soniox client.
    # --------------------------------------------------------------------------
    # @param options: Validated transcriber runtime options.
    # @param audio_q: Bounded queue of microphone PCM frame bytes.
    # @param stop_evt: Event requesting graceful stream shutdown.
    # @param on_tokens: Consumer invoked for each ordered Soniox token batch.
    # @return: None.
    # --------------------------------------------------------------------------
    soniox.stream_realtime(
        ws_url=options.ws_url,
        config=build_session_config(options),
        audio_q=audio_q,
        stop_evt=stop_evt,
        on_tokens=on_tokens,
    )
#end def


def _environment_int(env: Mapping[str, str], key: str, default: int) -> int:
    # Reads an integer environment value with a safe fallback.
    # --------------------------------------------------------------------------
    # @param env: Environment-style source mapping.
    # @param key: Value name to read.
    # @param default: Value returned when the source value is invalid or absent.
    # @return: Parsed integer or the supplied fallback.
    # --------------------------------------------------------------------------
    # keep malformed optional environment values from breaking argument parsing.
    try:
        return int(env.get(key, str(default)).strip())
    except (AttributeError, ValueError):
        return default
#end def


def _parse_device(value: str) -> int | str:
    # Converts numeric device selectors while preserving device names.
    # --------------------------------------------------------------------------
    # @param value: Raw command-line device selector.
    # @return: Integer device index or unchanged device name.
    # --------------------------------------------------------------------------
    # SoundDevice treats integer indexes differently from textual name matching.
    try:
        return int(value)
    except ValueError:
        return value
#end def
