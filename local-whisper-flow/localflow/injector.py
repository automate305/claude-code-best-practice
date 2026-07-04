"""Insert text at the cursor of whatever app has focus.

Paste mode is the default because it is near-instant regardless of text length
and survives apps that throttle synthetic keystrokes; the user's clipboard is
saved and restored around the paste. Type mode never touches the clipboard.
"""

from __future__ import annotations

import sys
import time


def inject(text: str, mode: str = "paste") -> None:
    if not text:
        return
    if mode == "type":
        _type(text)
    else:
        _paste(text)


def _type(text: str) -> None:
    from pynput.keyboard import Controller

    Controller().type(text)


def _paste(text: str) -> None:
    import pyperclip
    from pynput.keyboard import Controller, Key

    try:
        previous = pyperclip.paste()
    except Exception:
        previous = None
    pyperclip.copy(text)
    kb = Controller()
    modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl
    time.sleep(0.05)  # let the clipboard settle before the paste keystroke
    with kb.pressed(modifier):
        kb.press("v")
        kb.release("v")
    if previous is not None:
        # restore after the target app has read the clipboard
        time.sleep(0.3)
        try:
            pyperclip.copy(previous)
        except Exception:
            pass
