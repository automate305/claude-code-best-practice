"""Local speech-to-text via faster-whisper (CTranslate2).

The model loads once and stays resident, so after the first transcription
latency is dominated by audio length, not model startup. Set HF_HUB_OFFLINE=1
after the first model download to guarantee zero network access.
"""

from __future__ import annotations


class Transcriber:
    def __init__(
        self,
        model: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        language: str | None = None,
    ) -> None:
        from faster_whisper import WhisperModel  # lazy: heavy import

        if compute_type == "auto":
            # int8 keeps CPU inference fast and small; CTranslate2 picks the
            # best type itself on CUDA.
            compute_type = "int8" if device in ("auto", "cpu") else "default"
        self._model = WhisperModel(model, device=device, compute_type=compute_type)
        self._language = language

    def transcribe(self, audio) -> str:
        """audio: 1-D float32 numpy array at 16 kHz. Returns raw text."""
        segments, _info = self._model.transcribe(
            audio,
            language=self._language,
            vad_filter=True,  # trims leading/trailing silence around the press
            beam_size=5,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
