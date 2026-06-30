"""In-process upload status, shared between the HTTP writer and the pairing server.

The pairing server (`local_pairing_server.py`) and the upload loop
(`http_batch_writer.py`) run in the same process, so the writer records the outcome of
each upload attempt here and the pairing server exposes it on `/health`. The web app's
Settings page reads that to show "tracking active" vs. "reconnect needed" — which is the
only way to surface a **silently expired token** (the agent can't report that through the
authenticated ingest endpoint, because the whole problem is that auth failed).

Thread-safe and dependency-free so importing it can never break either thread.
"""

from __future__ import annotations

import threading
import time

# Auth/connection states reported to the UI.
OK = "ok"  # last upload accepted
WAITING_PAIR = "waiting_pair"  # no token yet — connect from Settings
NEEDS_RECONNECT = "needs_reconnect"  # token rejected/expired — pair again
TRANSIENT = "transient"  # server/network blip — retrying
UNKNOWN = "unknown"  # nothing attempted yet

_lock = threading.Lock()
_state = {
    "auth_state": UNKNOWN,
    "last_ok_at": None,        # epoch seconds of last accepted batch
    "last_attempt_at": None,   # epoch seconds of last upload attempt
    "last_error": "",          # short human-readable last error
    "consecutive_failures": 0,
    "events_uploaded": 0,      # cumulative accepted events (this process)
}


def _now() -> float:
    return time.time()


def record_ok(n: int = 0) -> None:
    with _lock:
        _state["auth_state"] = OK
        _state["last_ok_at"] = _now()
        _state["last_attempt_at"] = _state["last_ok_at"]
        _state["last_error"] = ""
        _state["consecutive_failures"] = 0
        _state["events_uploaded"] += max(0, int(n))


def record_waiting_pair() -> None:
    with _lock:
        # Don't clobber a more specific error; only set when not already failing on auth.
        if _state["auth_state"] != NEEDS_RECONNECT:
            _state["auth_state"] = WAITING_PAIR
        _state["last_attempt_at"] = _now()


def record_needs_reconnect(detail: str = "") -> None:
    with _lock:
        _state["auth_state"] = NEEDS_RECONNECT
        _state["last_attempt_at"] = _now()
        _state["last_error"] = (detail or "session expired — pair again")[:200]
        _state["consecutive_failures"] += 1


def record_transient(detail: str = "") -> None:
    with _lock:
        # A transient blip should not erase a known-good auth state; just note it.
        if _state["auth_state"] not in (NEEDS_RECONNECT,):
            _state["auth_state"] = TRANSIENT
        _state["last_attempt_at"] = _now()
        _state["last_error"] = (detail or "temporary upload error")[:200]
        _state["consecutive_failures"] += 1


def snapshot() -> dict:
    """JSON-serializable copy with derived fields for the UI."""
    with _lock:
        s = dict(_state)
    now = _now()
    last_ok = s["last_ok_at"]
    s["seconds_since_ok"] = int(now - last_ok) if last_ok else None
    # "Uploading" if we accepted a batch in the last 3 minutes.
    s["uploading"] = bool(last_ok and (now - last_ok) <= 180)
    return s
