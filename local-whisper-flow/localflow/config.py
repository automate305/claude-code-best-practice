"""Configuration: JSON file in the user config dir, merged over defaults."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    # fn is a macOS-only concept: on other platforms the OS never sees the key
    "hotkey": "fn" if sys.platform == "darwin" else "f9",
    "model": "small",
    "device": "auto",
    "compute_type": "auto",
    "language": None,
    "fillers": ["um", "uh", "uhm", "erm", "er", "ah", "hmm", "mmm"],
    "replacements": {},
    "ensure_punctuation": True,
    "spoken_punctuation": True,
    "inject_mode": "paste",  # "paste" or "type"
    "min_seconds": 0.4,
    "ollama_polish": False,
    "ollama_model": "llama3.2",
    "ollama_url": "http://localhost:11434",
    "save_recordings": False,
    "history": True,
    "dashboard": True,
    "dashboard_port": 8765,
}


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "localflow" / "config.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load config, creating the file with defaults on first run.

    Unknown keys are preserved so users can annotate; known keys fall back to
    defaults when missing so upgrades never break an old config file.
    """
    path = path or config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DEFAULTS, indent=2) + "\n", encoding="utf-8")
        return dict(DEFAULTS)
    user = json.loads(path.read_text(encoding="utf-8"))
    merged = dict(DEFAULTS)
    merged.update(user)
    return merged


def parse_hotkey(spec: str) -> frozenset[str]:
    """Parse "ctrl+alt" / "f9" into a normalized set of key names."""
    parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
    if not parts:
        raise ValueError(f"empty hotkey spec: {spec!r}")
    return frozenset(parts)
