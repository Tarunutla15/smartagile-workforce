"""
Resolve a structured period spec (from the analytics planner) into a concrete,
timezone-aware [since_dt, until_dt) window plus a human label.

Dates are computed in the project's active timezone (settings.TIME_ZONE). The LLM
only classifies the *kind* of period; all date math happens here (deterministic).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from django.utils import timezone


def _start_of_day(d: date):
    """Aware datetime at 00:00 local time for date `d`."""
    tz = timezone.get_current_timezone()
    naive = datetime.combine(d, time.min)
    try:
        return timezone.make_aware(naive, tz)
    except Exception:
        # DST edge / already-aware fallbacks: best-effort.
        return timezone.make_aware(naive)


def _parse_iso_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def resolve_period(period: dict[str, Any] | None, *, now=None) -> tuple[Any, Any, str]:
    """
    Returns (since_dt, until_dt, label).

    Supported kinds: today, yesterday, this_week, last_week, last_n_days,
    this_month, custom. Unknown / malformed specs fall back to "today".
    """
    now = now or timezone.now()
    today = timezone.localtime(now).date()
    kind = str((period or {}).get("kind") or "today").strip().lower()

    if kind == "yesterday":
        y = today - timedelta(days=1)
        return _start_of_day(y), _start_of_day(today), "yesterday"

    if kind == "this_week":
        monday = today - timedelta(days=today.weekday())
        return _start_of_day(monday), now, "this week"

    if kind == "last_week":
        this_monday = today - timedelta(days=today.weekday())
        last_monday = this_monday - timedelta(days=7)
        return _start_of_day(last_monday), _start_of_day(this_monday), "last week"

    if kind == "last_n_days":
        try:
            n = int((period or {}).get("n") or 7)
        except (TypeError, ValueError):
            n = 7
        n = max(1, min(n, 90))
        since = _start_of_day(today - timedelta(days=n - 1))
        return since, now, f"the last {n} days"

    if kind == "this_month":
        first = today.replace(day=1)
        return _start_of_day(first), now, "this month"

    if kind == "last_month":
        first_this = today.replace(day=1)
        first_prev = (first_this - timedelta(days=1)).replace(day=1)
        return _start_of_day(first_prev), _start_of_day(first_this), "last month"

    if kind == "custom":
        since_d = _parse_iso_date((period or {}).get("since"))
        until_d = _parse_iso_date((period or {}).get("until"))
        if since_d:
            since = _start_of_day(since_d)
            # `until` is inclusive of that day -> use start of the next day as exclusive bound.
            until = _start_of_day(until_d + timedelta(days=1)) if until_d else now
            label = (
                f"{since_d.isoformat()} to {until_d.isoformat()}"
                if until_d
                else f"since {since_d.isoformat()}"
            )
            return since, until, label

    # Default: today (00:00 -> now).
    return _start_of_day(today), now, "today"


# Default "previous comparable period" shift + label, keyed on the current period kind.
# today/this_week align by time-of-day (1d / 7d back); others shift by their own length.
_PREV_LABELS = {"today": "yesterday", "this_week": "last week", "this_month": "last month"}


def resolve_comparison(
    period: dict[str, Any] | None,
    compare_to: dict[str, Any] | None = None,
    *,
    now=None,
):
    """
    Returns (current, previous) where each is (since_dt, until_dt, label).

    `compare_to` (if given) defines the previous window explicitly; otherwise we derive
    the immediately-preceding comparable window (same elapsed length, time-of-day aligned
    for today/this_week, calendar-aligned for this_month).
    """
    now = now or timezone.now()
    cur_since, cur_until, cur_label = resolve_period(period, now=now)

    if compare_to:
        return (cur_since, cur_until, cur_label), resolve_period(compare_to, now=now)

    kind = str((period or {}).get("kind") or "today").strip().lower()
    duration = cur_until - cur_since
    if kind == "today":
        shift = timedelta(days=1)
    elif kind == "this_week":
        shift = timedelta(days=7)
    elif kind == "this_month":
        # Align to last month: same elapsed offset from the 1st of the previous month.
        first_this = cur_since.date()
        last_month_last_day = first_this - timedelta(days=1)
        first_prev = last_month_last_day.replace(day=1)
        prev_since = _start_of_day(first_prev)
        prev_until = prev_since + duration
        return (cur_since, cur_until, cur_label), (prev_since, prev_until, "last month")
    else:
        shift = duration

    prev_since = cur_since - shift
    prev_until = cur_until - shift
    label = _PREV_LABELS.get(kind, "the previous period")
    return (cur_since, cur_until, cur_label), (prev_since, prev_until, label)
