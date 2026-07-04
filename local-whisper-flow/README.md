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
  "hotkey": "f9",
  "model": "small",
  "device": "auto",
  "compute_type": "auto",
  "language": null,
  "fillers": ["um", "uh", "uhm", "erm", "er", "ah", "hmm", "mmm"],
  "inject_mode": "paste",
  "min_seconds": 0.4,
  "ollama_polish": false,
  "ollama_model": "llama3.2",
  "ollama_url": "http://localhost:11434",
  "save_recordings": false
}
```

- `hotkey`: single key (`"f9"`) or combo (`"ctrl+alt"`) — all parts held = recording.
- `model`: `tiny`/`base`/`small`/`medium`/`large-v3` or distil variants.
  `small` is a good CPU default; `distil-large-v3` if you have a GPU.
- `language`: `null` auto-detects; set `"en"` to skip detection (faster).
- `inject_mode`: `"paste"` (fast, restores your clipboard) or `"type"` (slower,
  never touches the clipboard).
- `ollama_polish`: set `true` (with [Ollama](https://ollama.com) running) to have a
  local LLM fix grammar and flow, like Wispr Flow's cloud cleanup — but on-device.

## Tests

The pure-logic modules (formatter, config) have unit tests that run anywhere:

```bash
python -m unittest discover -s tests
```
