"""Dictation history: append-only JSONL next to the config file.

JSONL so a crash mid-write can corrupt at most one line; reads skip bad lines.
Everything stays on disk in the user's config dir — the dashboard reads it over
localhost only.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .config import config_path

_LOCK = threading.Lock()


def history_path() -> Path:
    return config_path().parent / "history.jsonl"


def record(entry: dict[str, Any], path: Path | None = None) -> None:
    path = path or history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_all(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or history_path()
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries
