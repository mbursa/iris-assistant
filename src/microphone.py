import numpy as np
import queue
import threading
import sounddevice as sd

from config import Settings

# =============================================================================
#                              AUDIO CAPTURE
# =============================================================================

def start_microphone(
    audio_q: "queue.Queue[bytes]",
    stop_evt: threading.Event,
    settings: Settings,
) -> sd.InputStream:
    """
    Start capturing microphone audio using sounddevice.

    We push raw bytes (PCM 16-bit little-endian) into audio_q.
    The Soniox WebSocket API expects raw audio frames as binary websocket messages
    after the initial JSON configuration message. :contentReference[oaicite:10]{index=10}
    """

    def callback(indata, frames, time_info, status):
        # This callback runs on a sounddevice audio thread.
        if stop_evt.is_set():
            raise sd.CallbackStop

        # indata is a numpy array with dtype int16 that needs to be
        # converted to bytes for WebSocket binary frame
        try:
            audio_q.put_nowait(indata.copy().tobytes())
        except queue.Full:
            # If we're overloaded, drop audio chunks rather than blocking the audio callback.
            # Dropping occasionally is preferable to stalling and breaking real-time capture.
            pass
    #end def

    stream = sd.InputStream(
        samplerate=settings.audio.sample_rate,
        channels=settings.audio.channels,
        dtype="int16",
        blocksize=0,   # let sounddevice choose a suitable block size
        callback=callback,
    )

    stream.start()
    return stream
#end def