"""
Idle detection + active-duration math.

Converts raw foreground wall-time into *active* seconds (drops "away" idle time and
clamps runaway gaps from sleep/hibernate). Timing constants for the tracking loop
live here too so they are tuned in one place.
"""

from __future__ import annotations

from . import win32

# Wake at least this often to refresh title (browser tabs), periodic flush, etc.
TITLE_REFRESH_SEC = 2.0
# How long a single window segment may accumulate before a periodic flush.
PERIODIC_FLUSH_SEC = 60
# Idle inside a segment beyond this many seconds is treated as "away" and NOT counted.
# Active windows refresh input well within this, so normal usage is unaffected.
ACTIVE_IDLE_GRACE_SEC = 15
# A healthy loop flushes within ~PERIODIC_FLUSH_SEC. Anything much larger means the
# process was suspended/stalled (sleep, hibernate, thread starvation): clamp it so a
# multi-hour gap is never attributed to a single window.
MAX_SEGMENT_SEC = PERIODIC_FLUSH_SEC + 10
# Skip near-zero segments (rapid window flips / fully-idle periods) to avoid noise rows.
MIN_SEGMENT_SEC = 1.0


def seconds_since_last_input() -> float:
    return win32.seconds_since_last_input()


def effective_duration(raw_spent: float, idle_seconds: float) -> float:
    """
    Convert raw foreground wall-time into *active* seconds:
    1) clamp runaway gaps (sleep/stall) to MAX_SEGMENT_SEC,
    2) drop idle time beyond ACTIVE_IDLE_GRACE_SEC ("away" time).
    """
    raw_spent = max(0.0, float(raw_spent))
    idle_in_seg = min(raw_spent, max(0.0, float(idle_seconds)))
    spent = min(raw_spent, MAX_SEGMENT_SEC)
    away = max(0.0, idle_in_seg - ACTIVE_IDLE_GRACE_SEC)
    return max(0.0, spent - away)
