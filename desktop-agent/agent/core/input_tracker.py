"""
Input tracker: counts keystrokes / clicks / scrolls per segment via pynput.

Counters are thread-safe; ``snapshot_and_reset`` is called at each segment boundary
so activity never bleeds into the next window.
"""

from __future__ import annotations

import threading

from pynput import keyboard, mouse


class InputTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._keystrokes = 0
        self._clicks = 0
        self._scrolls = 0
        self._mouse_listener: mouse.Listener | None = None
        self._keyboard_listener: keyboard.Listener | None = None

    def _on_click(self, x, y, button, pressed):
        if pressed:
            with self._lock:
                self._clicks += 1
        return True

    def _on_scroll(self, x, y, dx, dy):
        with self._lock:
            self._scrolls += 1
        return True

    def _on_press(self, key):
        with self._lock:
            self._keystrokes += 1
        return True

    def start(self) -> None:
        self._mouse_listener = mouse.Listener(on_click=self._on_click, on_scroll=self._on_scroll)
        self._keyboard_listener = keyboard.Listener(on_press=self._on_press)
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def snapshot_and_reset(self) -> tuple[int, int, int]:
        with self._lock:
            ks, cl, sc = self._keystrokes, self._clicks, self._scrolls
            self._keystrokes = self._clicks = self._scrolls = 0
        return ks, cl, sc

    def stop(self) -> None:
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
        if self._keyboard_listener is not None:
            self._keyboard_listener.stop()
