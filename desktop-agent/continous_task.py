"""
SmartAgile desktop agent — entrypoint.

The tracking logic now lives in the ``agent`` package (core trackers + plugin layer);
this file just wires it together and keeps the public surface stable:

    start_continous_task(user_id)  / stop_continous_task()

Run directly with ``python continous_task.py`` (the front-end "Connect desktop app"
button talks to the localhost pairing server started here).
"""

from __future__ import annotations

import logging
import threading

from agent.core.engine import TrackingEngine
from local_pairing_server import pairing_port, start_pairing_server

logger = logging.getLogger(__name__)

running_flag = False
thread: threading.Thread | None = None
_engine: TrackingEngine | None = None
User_global_id = 0


def start_continous_task(user_id):
    """Start the localhost pairing server + the tracking engine (idempotent)."""
    global running_flag, thread, _engine, User_global_id
    start_pairing_server()
    User_global_id = user_id
    if running_flag:
        return
    running_flag = True
    _engine = TrackingEngine(user_id)
    thread = threading.Thread(target=_engine.run, name="smartagile-engine", daemon=False)
    thread.start()
    print(f"Task started for user: {user_id}", flush=True)


def stop_continous_task():
    global running_flag, thread, _engine
    if not running_flag:
        return
    running_flag = False
    if _engine is not None:
        _engine.stop()
    if thread is not None:
        thread.join()
    print("Task stopped", flush=True)


def ensure_engine_alive() -> None:
    """Watchdog: if the tracking thread has died, start a fresh engine.

    The engine loop is now resilient per-iteration, but this is defence-in-depth so a
    single fatal error can never leave the agent 'running' yet silently not tracking.
    """
    global thread, _engine
    if not running_flag:
        return
    if thread is not None and thread.is_alive():
        return
    logger.warning("engine thread not alive; restarting tracking engine")
    _engine = TrackingEngine(User_global_id)
    thread = threading.Thread(target=_engine.run, name="smartagile-engine", daemon=False)
    thread.start()


if __name__ == "__main__":
    import os
    import sys
    import time

    import auth_store

    logging.basicConfig(level=logging.INFO)
    # Frozen Windows consoles default to cp1252 and choke on non-ASCII; prefer UTF-8.
    for _stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # Two agents at once double-count every tracked second; refuse a second copy.
    from agent.core import single_instance

    if not single_instance.acquire():
        print(
            "Another SmartAgile agent is already running on this PC. "
            "Exiting to avoid double-counting usage.",
            flush=True,
        )
        sys.exit(0)
    # Optional; only for log context — default 1 without any env.
    _uid_raw = os.environ.get("SMARTAGILE_USER_ID", "").strip()
    if _uid_raw:
        try:
            uid = int(_uid_raw)
            if uid <= 0:
                uid = 1
        except ValueError:
            uid = 1
    else:
        uid = 1
    print("Starting desktop agent for user id", uid, "- Ctrl+C to stop", flush=True)
    start_continous_task(uid)
    p = pairing_port()
    print(
        f"Pairing: http://127.0.0.1:{p}/health - SmartAgile > Settings > Connect desktop app - "
        f"tokens file: {auth_store.store_path()}",
        flush=True,
    )
    has_auth = bool(
        os.environ.get("SMARTAGILE_ACCESS_TOKEN")
        or os.environ.get("SMARTAGILE_TAB_TOKEN")
        or auth_store.get_refresh()
    )
    if not has_auth:
        print("No auth yet: use Connect in Settings, or set SMARTAGILE_ACCESS_TOKEN for dev.")
    try:
        while running_flag:
            time.sleep(2)
            ensure_engine_alive()  # restart tracking if the engine thread ever dies
    except KeyboardInterrupt:
        stop_continous_task()
