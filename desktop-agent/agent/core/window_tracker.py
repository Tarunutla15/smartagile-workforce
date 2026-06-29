"""
Window tracker: reports the current foreground window as a :class:`RawWindow`.

Uses a Win32 ``SetWinEventHook`` (EVENT_SYSTEM_FOREGROUND) for instant focus-change
notifications, with a timer-based refresh as fallback. Falls back to ``pywinctl`` if the
Win32 path yields no executable.
"""

from __future__ import annotations

import ctypes
import logging
import queue
import threading
import time
from ctypes import wintypes

import pywinctl

from . import win32
from ..plugins.base import RawWindow

logger = logging.getLogger(__name__)


class WindowTracker:
    def __init__(self) -> None:
        self.foreground_queue: queue.Queue = queue.Queue()
        self._running = False
        self._hook_thread: threading.Thread | None = None
        self._hook_handle = [None]
        self._hook_tid = [0]
        self._callback_ref: list = []  # keep WINFUNCTYPE alive (avoid GC)

    # -- foreground hook -------------------------------------------------
    def start(self) -> queue.Queue:
        self._running = True
        self._hook_thread = threading.Thread(
            target=self._hook_loop, name="smartagile-foreground-hook", daemon=False
        )
        self._hook_thread.start()
        return self.foreground_queue

    def _hook_loop(self) -> None:
        self._hook_tid[0] = win32.kernel32.GetCurrentThreadId()

        def _callback(_hook, event, hwnd, _id_object, _id_child, _tid, _time_ms):
            try:
                if hwnd and event == win32.EVENT_SYSTEM_FOREGROUND:
                    self.foreground_queue.put_nowait(int(hwnd))
            except queue.Full:
                pass

        proc = win32.make_win_event_proc(_callback)
        self._callback_ref.append(proc)
        hook = win32.user32.SetWinEventHook(
            win32.EVENT_SYSTEM_FOREGROUND,
            win32.EVENT_SYSTEM_FOREGROUND,
            0,
            proc,
            0,
            0,
            win32.WINEVENT_OUTOFCONTEXT,
        )
        self._hook_handle[0] = hook
        if not hook:
            logger.warning("SetWinEventHook failed; using timer-based foreground refresh only.")
            from .idle_tracker import TITLE_REFRESH_SEC

            while self._running:
                time.sleep(TITLE_REFRESH_SEC)
            return

        msg = wintypes.MSG()
        while self._running:
            r = win32.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r == 0 or r == -1:
                break
            win32.user32.TranslateMessage(ctypes.byref(msg))
            win32.user32.DispatchMessageW(ctypes.byref(msg))
        if self._hook_handle[0]:
            win32.user32.UnhookWinEvent(self._hook_handle[0])
            self._hook_handle[0] = None

    def stop(self) -> None:
        self._running = False
        if self._hook_tid[0]:
            win32.user32.PostThreadMessageW(self._hook_tid[0], win32.WM_QUIT, 0, 0)
        if self._hook_thread is not None:
            self._hook_thread.join(timeout=15)

    def drain(self) -> None:
        """Discard any queued foreground notifications (we re-read live state)."""
        while True:
            try:
                self.foreground_queue.get_nowait()
            except queue.Empty:
                break

    # -- reading the foreground window -----------------------------------
    def read(self) -> RawWindow | None:
        """Current foreground window via Win32; falls back to pywinctl."""
        hwnd = win32.get_foreground_hwnd()
        if hwnd:
            title = win32.get_window_text(hwnd)
            pid = win32.pid_for_hwnd(hwnd)
            path = win32.process_image_path(pid)
            app_id = path if path else (f"pid:{pid}" if pid else "")
            if app_id:
                return RawWindow(exe_path=app_id, window_title=title, pid=pid)
        # Fallback: COM-based pywinctl (no per-call COM init in the fast path).
        try:
            ctypes.windll.ole32.CoInitialize(None)
            active = pywinctl.getActiveWindow()
            if active is not None:
                return RawWindow(exe_path=active.getAppName() or "", window_title=active.title or "", pid=0)
            return None
        except Exception as e:  # noqa: BLE001
            logger.debug("pywinctl fallback failed: %s", e)
            return None
        finally:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:  # noqa: BLE001
                pass
