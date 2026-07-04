"""Text cleanup: Wispr Flow's cloud LLM pass, replaced by local rules + optional Ollama.

The rule pass is deterministic and instant: strip non-lexical fillers, repair
the punctuation gaps they leave, and capitalize sentence starts. The optional
Ollama pass adds LLM-quality rewriting while still talking only to localhost.
"""

from __future__ import annotations

import json
import re
import urllib.request

DEFAULT_FILLERS = ["um", "uh", "uhm", "erm", "er", "ah", "hmm", "mmm"]

POLISH_PROMPT = (
    "Fix grammar, punctuation, and flow of this dictated text. Keep the meaning "
    "and tone. Return ONLY the corrected text, nothing else.\n\n{text}"
)


def clean(text: str, fillers: list[str] | None = None) -> str:
    """Deterministic cleanup: fillers out, punctuation repaired, sentences capitalized."""
    fillers = DEFAULT_FILLERS if fillers is None else fillers
    if fillers:
        pattern = r"(?i)\b(?:" + "|".join(re.escape(f) for f in fillers) + r")\b[,.]?"
        text = re.sub(pattern, "", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)  # no space before punctuation
    text = re.sub(r",[\s,]*,", ",", text)  # collapse comma runs left by fillers
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"^[,.;:\s]+", "", text)  # orphan punctuation at the start
    return _capitalize_sentences(text)


def _capitalize_sentences(text: str) -> str:
    return re.sub(
        r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text
    )


def polish_with_ollama(
    text: str, model: str, url: str = "http://localhost:11434", timeout: float = 30.0
) -> str:
    """Rewrite via a local Ollama model. Fails open: returns the input on any error."""
    if not text:
        return text
    try:
        body = json.dumps(
            {"model": model, "prompt": POLISH_PROMPT.format(text=text), "stream": False}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{url.rstrip('/')}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8")).get("response", "").strip()
        return result or text
    except Exception:
        return text
