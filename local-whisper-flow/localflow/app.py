"""Orchestrator: hotkey → record → transcribe → format → inject.

Transcription runs on a worker thread so the global key listener never blocks —
otherwise held keys elsewhere on the system would stutter during inference.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any

from . import formatter, history
from .config import parse_hotkey
from .recorder import SAMPLE_RATE, Recorder
from .transcriber import Transcriber

# pynput reports left/right variants; the config uses the generic name.
_KEY_ALIASES = {
    "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "shift_l": "shift", "shift_r": "shift",
    "cmd_l": "cmd", "cmd_r": "cmd",
}


# macOS: fn is absent from pynput's key table; it arrives as a bare vk.
_DARWIN_VK_NAMES = {0x3F: "fn"}


def _key_name(key) -> str | None:
    if hasattr(key, "char") and key.char:
        return key.char.lower()
    name = getattr(key, "name", None)
    if name:
        return _KEY_ALIASES.get(name, name)
    if sys.platform == "darwin":
        return _DARWIN_VK_NAMES.get(getattr(key, "vk", None))
    return None


class App:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.hotkey = parse_hotkey(config["hotkey"])
        self.recorder = Recorder()
        self.transcriber: Transcriber | None = None
        self._pressed: set[str] = set()

    def run(self) -> None:
        from pynput import keyboard  # lazy: needs a display server

        print(f"Loading Whisper model '{self.config['model']}' (first run downloads it)…")
        self.transcriber = Transcriber(
            model=self.config["model"],
            device=self.config["device"],
            compute_type=self.config["compute_type"],
            language=self.config["language"],
        )
        if self.config["dashboard"]:
            from .dashboard import start_dashboard

            port = self.config["dashboard_port"]
            start_dashboard(port)
            print(f"Dashboard: http://127.0.0.1:{port}")
        print(f"Ready. Hold [{self.config['hotkey']}] to dictate; Ctrl+C here to quit.")
        with keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        ) as listener:
            listener.join()

    def _press_name(self, name: str) -> None:
        self._pressed.add(name)
        if self.hotkey <= self._pressed and not self.recorder.recording:
            print("● recording…")
            self.recorder.start()

    def _release_name(self, name: str) -> None:
        self._pressed.discard(name)
        if self.recorder.recording and not self.hotkey <= self._pressed:
            audio = self.recorder.stop()
            threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    def _on_press(self, key) -> None:
        name = _key_name(key)
        if name is not None:
            self._press_name(name)

    def _on_release(self, key) -> None:
        name = _key_name(key)
        if name is None:
            return
        # macOS reports fn only via on_release, for both directions of travel;
        # alternate the events into press/release so hold-to-talk works.
        if name == "fn" and sys.platform == "darwin" and "fn" not in self._pressed:
            self._press_name("fn")
            return
        self._release_name(name)

    def _process(self, audio) -> None:
        seconds = len(audio) / SAMPLE_RATE
        if seconds < self.config["min_seconds"]:
            print(f"  (ignored: {seconds:.2f}s is below min_seconds)")
            return
        if self.config["save_recordings"]:
            self._save_wav(audio)
        assert self.transcriber is not None
        started = time.time()
        raw = self.transcriber.transcribe(audio)
        latency = time.time() - started
        text = formatter.clean(
            raw,
            self.config["fillers"],
            replacements=self.config["replacements"],
            ensure_punctuation=self.config["ensure_punctuation"],
        )
        if text and self.config["ollama_polish"]:
            text = formatter.polish_with_ollama(
                text, self.config["ollama_model"], self.config["ollama_url"]
            )
        if not text:
            print("  (no speech detected)")
            return
        from .injector import inject

        inject(text, self.config["inject_mode"])
        print(f"✓ inserted: {text}")
        if self.config["history"]:
            history.record({
                "ts": time.time(),
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "seconds": round(seconds, 2),
                "latency": round(latency, 2),
                "raw": raw,
                "text": text,
                "words": len(text.split()),
            })

    def _save_wav(self, audio) -> None:
        import wave

        import numpy as np

        out_dir = Path.home() / ".config" / "localflow" / "recordings"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{time.strftime('%Y%m%d-%H%M%S')}.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes((audio * 32767).astype(np.int16).tobytes())
