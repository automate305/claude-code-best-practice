# LocalFlow — Private, Local Whisper Flow

A private, fully local voice-dictation tool inspired by [Wispr Flow](https://wisprflow.ai/).
Hold a hotkey, speak, release — clean text is inserted at your cursor in **any** app.
Unlike Wispr Flow, **no audio, text, or screen context ever leaves your machine**.

## Architecture

Wispr Flow's pipeline is: OS-level hotkey → capture audio → send to cloud ASR →
cloud LLM cleanup → inject text at the cursor. LocalFlow keeps the same pipeline
but swaps every cloud stage for a local component:

```
┌─────────────┐   press    ┌──────────────┐   release   ┌────────────────┐
│ Hotkey      │ ─────────► │ Recorder     │ ──────────► │ Transcriber    │
│ (pynput,    │            │ (sounddevice │             │ (faster-whisper│
│  global     │            │  16 kHz mono │             │  CTranslate2,  │
│  push-to-   │            │  in-memory)  │             │  CPU or GPU)   │
│  talk)      │            └──────────────┘             └───────┬────────┘
└─────────────┘                                                 │ raw text
                                                                ▼
┌─────────────┐            ┌──────────────────────────────────────────────┐
│ Active app  │ ◄───────── │ Formatter                                    │
│ cursor      │  paste /   │ 1. rule-based: strip fillers (um, uh, …),    │
│ (Injector:  │  type      │    fix spacing, capitalize sentences         │
│  clipboard  │            │ 2. optional: polish via local Ollama LLM     │
│  + Ctrl/Cmd │            │    (off by default, still 100% on-device)    │
│  +V, restore│            └──────────────────────────────────────────────┘
│  clipboard) │
└─────────────┘
```

| Stage | Wispr Flow (cloud) | LocalFlow (local) |
|-------|--------------------|--------------------|
| Trigger | Global hotkey | `pynput` push-to-talk (hold to record) |
| Audio | Uploaded to servers | `sounddevice`, kept in RAM only |
| Speech-to-text | Proprietary cloud ASR | `faster-whisper` (Whisper via CTranslate2) |
| Cleanup | Cloud LLM, screen context uploaded | Local rules + optional local Ollama model |
| Insertion | OS-level text injection | Clipboard paste (clipboard restored) or typing |

## Privacy guarantees

- **No network calls at runtime.** The only download is the Whisper model itself,
  once, from Hugging Face. Pre-download it and set `HF_HUB_OFFLINE=1` to run
  fully air-gapped.
- Audio is held in memory and discarded after transcription — nothing is written
  to disk unless you enable `save_recordings` for debugging.
- The optional LLM polish step talks only to `localhost` (Ollama).

## Install

Requires Python 3.10+.

```bash
cd local-whisper-flow
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Platform notes:
- **macOS**: grant Terminal/your shell *Accessibility* and *Microphone* permissions
  (System Settings → Privacy & Security). Paste uses `Cmd+V` automatically.
- **Linux**: works on X11; on Wayland, global hotkeys need your compositor's
  permission or an X11 session. `sudo apt install portaudio19-dev` if PortAudio is missing.
- **Windows**: works out of the box.

## Run

```bash
python -m localflow
```

Hold **F9** (default), speak, release. Text appears at your cursor.

## Configure

First run writes `~/.config/localflow/config.json` with defaults:

```json
{
  "hotkey": "fn",
  "model": "small",
  "device": "auto",
  "compute_type": "auto",
  "language": null,
  "fillers": ["um", "uh", "uhm", "erm", "er", "ah", "hmm", "mmm"],
  "replacements": {},
  "ensure_punctuation": true,
  "inject_mode": "paste",
  "min_seconds": 0.4,
  "ollama_polish": false,
  "ollama_model": "llama3.2",
  "ollama_url": "http://localhost:11434",
  "save_recordings": false,
  "history": true,
  "dashboard": true,
  "dashboard_port": 8765
}
```

- `hotkey`: single key or combo (`"ctrl+alt"`) — all parts held = recording.
  Defaults to `"fn"` on macOS (the bottom-left key), `"f9"` elsewhere: the OS
  never exposes fn on Windows/Linux keyboards. On macOS, set System Settings →
  Keyboard → *Press 🌐 key* to **Do Nothing** so tapping fn doesn't also open
  the emoji picker or Apple dictation.
- `model`: `tiny`/`base`/`small`/`medium`/`large-v3` or distil variants.
  `small` is a good CPU default; `distil-large-v3` if you have a GPU.
- `language`: `null` auto-detects; set `"en"` to skip per-utterance language
  detection — a free speed win if you only dictate English.
- Feeling slow on CPU? `"model": "base.en"` with `"language": "en"` is the
  speed sweet spot; `"small.en"` splits the difference with `small`.
- `replacements`: your autocorrect dictionary, applied on every dictation —
  case-insensitive, whole-word. E.g. `{"local whisperer": "LocalFlow"}` fixes a
  name Whisper keeps mishearing.
- `ensure_punctuation`: guarantees each utterance ends with a sentence
  terminator (Whisper occasionally drops the final period on short phrases).
- `spoken_punctuation`: say the mark to type it — Whisper rarely infers `!` or
  `?` from voice tone alone. Commands: **"exclamation mark"** (or "exclamation
  point", or just "exclamation") → `!`, **"question mark"** → `?`, **"period"** /
  **"full stop"** → `.`, **"comma"** → `,`, **"new line"**, **"new paragraph"**.
  Trade-off: dictating a sentence *about* the word "period" will convert it;
  set `false` to disable.
- `inject_mode`: `"paste"` (fast, restores your clipboard) or `"type"` (slower,
  never touches the clipboard).
- `ollama_polish`: set `true` (with [Ollama](https://ollama.com) running) to have a
  local LLM fix grammar and flow, like Wispr Flow's cloud cleanup — but on-device.
- `history` / `dashboard` / `dashboard_port`: dictation log and the local
  dashboard (below).

## Dashboard

While LocalFlow runs, open **http://127.0.0.1:8765** for a Wispr Flow-style
dashboard: total dictations, words dictated, today's count, average transcribe
latency, plus a searchable history of everything you've dictated with per-entry
copy buttons. It auto-refreshes as you dictate.

Privacy: the history lives in `~/.config/localflow/history.jsonl` and the
dashboard binds to `127.0.0.1` only — nothing is reachable from the network.
Set `"history": false` to keep no log at all, or `"dashboard": false` to log
without serving the page.

## Tests

The pure-logic modules (formatter, config) have unit tests that run anywhere:

```bash
python -m unittest discover -s tests
```
