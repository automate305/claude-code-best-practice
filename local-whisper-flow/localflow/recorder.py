"""Microphone capture: 16 kHz mono float32, held in memory only.

16 kHz is Whisper's native sample rate, so recording at it directly avoids a
resample step before transcription.
"""

from __future__ import annotations

import threading

SAMPLE_RATE = 16_000


class Recorder:
    def __init__(self) -> None:
        self._frames: list = []
        self._stream = None
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self._stream is not None:
            return
        import sounddevice as sd  # lazy: needs PortAudio, absent on CI boxes

        self._frames = []

        def callback(indata, _frames, _time, _status):
            with self._lock:
                self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=callback
        )
        self._stream.start()

    def stop(self):
        """Stop and return the captured audio as a 1-D float32 numpy array."""
        import numpy as np

        stream, self._stream = self._stream, None
        if stream is None:
            return np.zeros(0, dtype="float32")
        stream.stop()
        stream.close()
        with self._lock:
            frames, self._frames = self._frames, []
        if not frames:
            return np.zeros(0, dtype="float32")
        return np.concatenate(frames).flatten()
