import queue
import threading

import subtitles
import microphone
import soniox
import window
from config import Settings, load_settings


def _safe_settings_summary(settings: Settings) -> str:
    return (
        "Loaded settings: "
        f"sample_rate={settings.audio.sample_rate}, "
        f"channels={settings.audio.channels}, "
        f"source_language={settings.translation.source_language}, "
        f"target_language={settings.translation.target_language}, "
        f"ws_url={settings.soniox.ws_url}, "
        f"api_key={'set' if settings.soniox.api_key else 'missing'}"
    )


def main() -> int:
    """
    Application's entry point:
      - create shared state
      - start microphone capture
      - start Soniox streaming thread
      - run UI loop that:
          * shows state.display_text
          * clears after CLEAR_SUBTITLES_AFTER_SECONDS of inactivity (no new final translation tokens)
    """

    settings = load_settings()
    print(_safe_settings_summary(settings))

    audio_q: "queue.Queue[bytes]" = queue.Queue(maxsize=settings.performance.audio_queue_max_chunks)
    stop_evt = threading.Event()
    state = subtitles.SubtitleState(max_lines=settings.ui.max_lines_on_screen)

    # start microphone capture
    mic_stream = microphone.start_microphone(audio_q, stop_evt, settings)

    # start Soniox streaming worker
    worker = threading.Thread(target=soniox.soniox_worker, args=(audio_q, state, stop_evt, settings), daemon=True)
    worker.start()

    # start UI
    win = window.SubtitleWindow(settings)

    try:
        win.run(state, settings.performance.ui_tick_ms)
    finally:
        # stop everything cleanly
        stop_evt.set()
        try:
            mic_stream.stop()
            mic_stream.close()
        except Exception:
            pass
    return 0
    #end try
#end def