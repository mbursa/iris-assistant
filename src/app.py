# Composes application components for translation and transcription entry points.

from __future__ import annotations

import argparse
import queue
import sys
import threading
from collections.abc import Sequence

import microphone
import soniox
import subtitles
import transcription
import window
from config import Settings, load_settings
from languages import resolve_translation_languages


def translator_main(argv: Sequence[str] | None = None) -> int:
    # Starts microphone translation, Soniox streaming, and the subtitle UI.
    # --------------------------------------------------------------------------
    # The UI owns the foreground thread while the reusable Soniox worker runs in a
    # daemon thread and consumes frames from the shared microphone component.
    # @param argv: Optional command-line arguments; None reads the process arguments.
    # @return: Process exit code.
    # --------------------------------------------------------------------------
    # require a per-run source while allowing the target to follow direction defaults.
    parser = argparse.ArgumentParser(
        description="Translate microphone audio with Soniox real-time translation."
    )
    parser.add_argument(
        "--source-lang",
        required=True,
        metavar="LANG",
        help="Spoken source language (required; 'cz' is normalized to 'cs').",
    )
    parser.add_argument(
        "--target-lang",
        metavar="LANG",
        help="Translation target (default: en for Czech source, otherwise cs).",
    )
    # parse the complete direction before any configuration or hardware work.
    args = parser.parse_args(argv)

    # normalize the requested direction before loading non-language configuration.
    try:
        source_language, target_language = resolve_translation_languages(
            args.source_lang,
            args.target_lang,
        )
    except ValueError as error:
        parser.error(str(error))

    # load validated non-language settings with the resolved runtime direction.
    settings = load_settings(
        source_language=source_language,
        target_language=target_language,
    )
    print(_safe_settings_summary(settings))

    # create shared transport and display state for the application components.
    audio_q: "queue.Queue[bytes]" = queue.Queue(
        maxsize=settings.performance.audio_queue_max_chunks
    )
    stop_evt = threading.Event()
    state = subtitles.SubtitleState(max_lines=settings.ui.max_lines_on_screen)

    # start the common microphone producer and translator-specific Soniox consumer.
    mic_stream = microphone.start_microphone(audio_q, stop_evt, settings)
    worker = threading.Thread(
        target=soniox.soniox_worker,
        args=(audio_q, state, stop_evt, settings),
        name="soniox-translation-worker",
        daemon=True,
    )
    worker.start()

    # run the subtitle UI until the user closes its foreground event loop.
    subtitle_window = window.SubtitleWindow(settings)
    try:
        subtitle_window.run(state, settings.performance.ui_tick_ms)
    finally:
        # signal streaming shutdown before releasing the shared microphone device.
        stop_evt.set()
        microphone.stop_input_stream(mic_stream)
    return 0
#end def


def transcriber_main(argv: Sequence[str] | None = None) -> int:
    # Starts speaker-aware microphone transcription in the console.
    # --------------------------------------------------------------------------
    # The foreground Soniox stream consumes the same reusable microphone producer
    # used by the translator and delegates token presentation to TranscriptPrinter.
    # @param argv: Optional command-line arguments; None reads the process arguments.
    # @return: Process exit code.
    # --------------------------------------------------------------------------
    # load CLI and environment options without opening external resources.
    options = transcription.load_transcriber_options(argv)
    if options.list_devices:
        print(microphone.list_devices())
        return 0

    # reject invalid options before allocating microphone or network resources.
    try:
        options.validate()
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2

    # print options summary for debugging purposes.
    print(
        "Transcriber options: "
        f"sample_rate={options.sample_rate}, "
        f"channels={options.channels}, "
        f"source_language={options.source_language}, "
        f"device={options.device}, "
        f"queue_max_chunks={options.queue_max_chunks}, "
        f"output_file={options.output_file}",
        file=sys.stderr,
    )

    # create shared transport state and the dedicated transcript renderer.
    audio_q: "queue.Queue[bytes]" = queue.Queue(maxsize=options.queue_max_chunks)
    stop_evt = threading.Event()
    try:
        printer = transcription.TranscriptPrinter(options.output_file)
    except OSError as error:
        print(f"Cannot open transcript output file: {error}", file=sys.stderr)
        return 2

    mic_stream = None
    try:
        # start the common microphone producer with transcriber-specific audio options.
        mic_stream = microphone.start_input_stream(
            audio_q,
            stop_evt,
            sample_rate=options.sample_rate,
            channels=options.channels,
            device=options.device,
        )

        # delegate the feature-specific session to the transcription component.
        print("Connecting to Soniox; press Ctrl+C to stop.", file=sys.stderr)
        transcription.run_session(
            options,
            audio_q=audio_q,
            stop_evt=stop_evt,
            on_tokens=printer.write_tokens,
        )
    except KeyboardInterrupt:
        print("Stopping…", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"Transcription failed: {error}", file=sys.stderr)
        return 1
    finally:
        # release the common streaming and microphone resources in dependency order.
        stop_evt.set()
        microphone.stop_input_stream(mic_stream)
        printer.finish()
    return 0
#end def


def _safe_settings_summary(settings: Settings) -> str:
    # Builds a log-safe summary of the active translator configuration.
    # --------------------------------------------------------------------------
    # The API key is represented only by presence so startup logs do not disclose it.
    # @param settings: Validated application configuration.
    # @return: Human-readable configuration summary safe for console output.
    # --------------------------------------------------------------------------
    return (
        "Loaded settings: "
        f"sample_rate={settings.audio.sample_rate}, "
        f"channels={settings.audio.channels}, "
        f"source_language={settings.translation.source_language}, "
        f"target_language={settings.translation.target_language}, "
        f"ws_url={settings.soniox.ws_url}, "
        f"api_key={'set' if settings.soniox.api_key else 'missing'}"
    )
#end def


def main(argv: Sequence[str] | None = None) -> int:
    # Preserves the original translator entry-point name for existing callers.
    # --------------------------------------------------------------------------
    # @param argv: Optional command-line arguments; None reads the process arguments.
    # @return: Process exit code from the translator application.
    # --------------------------------------------------------------------------
    return translator_main(argv)
#end def
