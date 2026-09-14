# Provides reusable microphone capture operations for live audio applications.

import queue
import threading
from typing import Any

import sounddevice as sd

from config import Settings


def start_input_stream(
    audio_q: "queue.Queue[bytes]",
    stop_evt: threading.Event,
    *,
    sample_rate: int,
    channels: int = 1,
    device: int | str | None = None,
) -> sd.InputStream:
    # Starts a microphone stream and queues raw PCM frames.
    # --------------------------------------------------------------------------
    # The callback never blocks; overflowing frames are discarded to keep the
    # PortAudio capture thread real-time.
    # @param audio_q: Bounded queue that receives PCM S16LE frame bytes.
    # @param stop_evt: Event that requests capture shutdown.
    # @param sample_rate: Microphone sampling frequency in Hz.
    # @param channels: Number of microphone channels to capture.
    # @param device: Optional SoundDevice input device index or name.
    # @return: Started SoundDevice input stream owned by the caller.
    # @throws PortAudioError: If the selected input device cannot be opened.
    # --------------------------------------------------------------------------

    def callback(indata: Any, _frames: int, _time_info: Any, _status: sd.CallbackFlags) -> None:
        # Queues one microphone frame from PortAudio.
        # ----------------------------------------------------------------------
        # @param indata: NumPy audio frame supplied by SoundDevice.
        # @param _frames: Sample count supplied by SoundDevice.
        # @param _time_info: PortAudio timing metadata for the frame.
        # @param _status: PortAudio status flags for the callback.
        # @return: None.
        # ----------------------------------------------------------------------
        # stop capture at a callback boundary after shared shutdown is requested.
        if stop_evt.is_set():
            raise sd.CallbackStop

        # copy callback-owned memory before passing the frame to another thread.
        try:
            audio_q.put_nowait(indata.copy().tobytes())
        except queue.Full:
            # drop overflow rather than stalling the real-time audio callback.
            pass
    #end def

    # let SoundDevice select a suitable block size for the active input device.
    stream = sd.InputStream(
        device=device,
        samplerate=sample_rate,
        channels=channels,
        dtype="int16",
        blocksize=0,
        callback=callback,
    )
    stream.start()
    return stream
#end def


def start_microphone(
    audio_q: "queue.Queue[bytes]",
    stop_evt: threading.Event,
    settings: Settings,
) -> sd.InputStream:
    # Starts microphone capture using the shared application settings.
    # --------------------------------------------------------------------------
    # @param audio_q: Bounded queue that receives PCM S16LE frame bytes.
    # @param stop_evt: Event that requests capture shutdown.
    # @param settings: Validated application audio settings.
    # @return: Started SoundDevice input stream owned by the caller.
    # @throws PortAudioError: If the configured input device cannot be opened.
    # --------------------------------------------------------------------------
    return start_input_stream(
        audio_q,
        stop_evt,
        sample_rate=settings.audio.sample_rate,
        channels=settings.audio.channels,
    )
#end def


def stop_input_stream(stream: sd.InputStream | None) -> None:
    # Stops and closes an owned microphone stream safely.
    # --------------------------------------------------------------------------
    # Cleanup is idempotent from the caller's perspective and suppresses device
    # teardown failures so an earlier application error remains visible.
    # @param stream: Input stream to release, or None when startup did not finish.
    # @return: None.
    # --------------------------------------------------------------------------
    # skip cleanup when microphone initialization never produced a stream.
    if stream is None:
        return

    # release both PortAudio capture and its underlying device handle.
    try:
        stream.stop()
        stream.close()
    except Exception:
        pass
#end def


def list_devices() -> Any:
    # Returns SoundDevice's available audio-device report.
    # --------------------------------------------------------------------------
    # @return: Device information returned by SoundDevice.
    # --------------------------------------------------------------------------
    return sd.query_devices()
#end def
