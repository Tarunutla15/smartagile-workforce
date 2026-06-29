"""Single-instance guard.

Two agents running at once is catastrophic for data quality: both track the same
global foreground window and upload near-identical segments, so every tracked
second is counted twice. This module lets the entrypoint refuse to start a second
copy.

On Windows we use a named mutex (the canonical single-instance primitive, works in
a frozen PyInstaller exe). Everywhere else we fall back to a PID lock file. If the
guard can't be established for any reason we fail open (allow start) rather than
block a legitimate launch.
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile

logger = logging.getLogger(__name__)

_MUTEX_NAME = "SmartAgileDesktopAgent_SingleInstance"
_ERROR_ALREADY_EXISTS = 183

# Hold references so the OS handle / file stays alive for the process lifetime.
_held: list = []


def _acquire_windows() -> bool:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]

    handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    last_error = kernel32.GetLastError()
    if not handle:
        logger.warning("CreateMutexW failed (err=%s); allowing start", last_error)
        return True
    if last_error == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False
    _held.append(handle)
    return True


def _acquire_posix() -> bool:
    lock_path = os.path.join(tempfile.gettempdir(), "smartagile-agent.lock")
    try:
        import fcntl

        fh = open(lock_path, "w")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            fh.close()
            return False
        fh.write(str(os.getpid()))
        fh.flush()
        _held.append(fh)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("POSIX lock failed (%s); allowing start", exc)
        return True


def acquire() -> bool:
    """Return True if this process is the only agent; False if one is already running."""
    try:
        if sys.platform.startswith("win"):
            return _acquire_windows()
        return _acquire_posix()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Single-instance guard error (%s); allowing start", exc)
        return True
