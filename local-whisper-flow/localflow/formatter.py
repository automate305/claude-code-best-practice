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

# Spoken punctuation commands (Dragon/Apple-dictation style). Whisper small
# rarely infers ! or ? from voice tone, so saying the mark is the reliable way.
_SPOKEN_PUNCTUATION = [
    (r"exclamation(?:\s+(?:mark|point))?", "!"),
    (r"question\s+mark", "?"),
    (r"full\s+stop|period", "."),
    (r"comma", ","),
    (r"new\s+paragraph", "\n\n"),
    (r"new\s+line", "\n"),
]

POLISH_PROMPT = (
    "Fix grammar, punctuation, and flow of this dictated text. Keep the meaning "
    "and tone. Return ONLY the corrected text, nothing else.\n\n{text}"
)


def clean(
    text: str,
    fillers: list[str] | None = None,
    replacements: dict[str, str] | None = None,
    ensure_punctuation: bool = False,
    spoken_punctuation: bool = False,
) -> str:
    """Deterministic cleanup: fillers out, punctuation repaired, sentences capitalized.

    replacements is the user's autocorrect dictionary (case-insensitive,
    whole-word), applied before everything else so its output flows through the
    same cleanup. ensure_punctuation guarantees the utterance ends in a
    sentence terminator.
    """
    fillers = DEFAULT_FILLERS if fillers is None else fillers
    for wrong, right in (replacements or {}).items():
        text = re.sub(
            r"(?i)\b" + re.escape(wrong) + r"\b", right.replace("\\", r"\\"), text
        )
    if fillers:
        pattern = r"(?i)\b(?:" + "|".join(re.escape(f) for f in fillers) + r")\b[,.]?"
        text = re.sub(pattern, "", text)
    if spoken_punctuation:
        for spoken, mark in _SPOKEN_PUNCTUATION:
            # absorb the comma/period Whisper wraps around the spoken command
            text = re.sub(r"(?i)[,.]?\s*\b(?:" + spoken + r")\b[,.]?", mark, text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)  # no space before punctuation
    text = re.sub(r",[\s,]*,", ",", text)  # collapse comma runs left by fillers
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    text = re.sub(r"^[,.;:\s]+", "", text)  # orphan punctuation at the start
    text = _capitalize_sentences(text)
    if ensure_punctuation and text and text[-1].isalnum():
        text += "."
    return text


def _capitalize_sentences(text: str) -> str:
    return re.sub(
        r"(^|[.!?]\s+|\n)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text
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
