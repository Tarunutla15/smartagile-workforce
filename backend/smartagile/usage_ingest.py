"""Validate desktop agent usage payloads before queue persistence."""

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import UsageEvent

MAX_BATCH = 2000


def normalize_usage_events(raw_list):
    """
    raw_list: list of dicts from JSON.
    Returns (events_for_task, errors). events_for_task is list of dicts with model field keys.
    """
    if not isinstance(raw_list, list):
        return [], ["body must be a JSON array"]
    if len(raw_list) > MAX_BATCH:
        return [], [f"at most {MAX_BATCH} events per request"]

    out = []
    errors = []
    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            errors.append(f"event {i}: must be an object")
            continue
        st = item.get("source_type")
        if st not in (UsageEvent.SourceType.APPLICATION, UsageEvent.SourceType.BROWSER):
            errors.append(f"event {i}: source_type must be application or browser")
            continue
        name = item.get("name")
        if not name or not isinstance(name, str):
            errors.append(f"event {i}: name is required")
            continue
        name = name[:512]
        context = item.get("context", "") or ""
        if not isinstance(context, str):
            context = str(context)
        context = context[:1024]
        category = item.get("category", "") or ""
        if not isinstance(category, str):
            category = str(category)
        category = category[:128]
        try:
            duration_seconds = float(item.get("duration_seconds", 0))
        except (TypeError, ValueError):
            errors.append(f"event {i}: duration_seconds invalid")
            continue
        if duration_seconds < 0:
            errors.append(f"event {i}: duration_seconds must be >= 0")
            continue

        def _f(key, default=0.0):
            try:
                return float(item.get(key, default))
            except (TypeError, ValueError):
                return default

        # Raw value is "seconds since last input" at segment end; cap to segment so sums are not inflated.
        idle_seconds = _f("idle_seconds", 0)
        idle_seconds = min(duration_seconds, max(0.0, idle_seconds))
        keystrokes = _f("keystrokes", 0)
        clicks = _f("clicks", 0)
        scrolls = _f("scrolls", 0)

        occurred_raw = item.get("occurred_at")
        occurred_at = None
        if occurred_raw:
            s = str(occurred_raw)
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            occurred_at = parse_datetime(s)
            if occurred_at is None:
                errors.append(f"event {i}: occurred_at invalid ISO datetime")
                continue
            if timezone.is_naive(occurred_at):
                occurred_at = timezone.make_aware(occurred_at, timezone.get_current_timezone())
        else:
            occurred_at = timezone.now()

        out.append(
            {
                "source_type": st,
                "name": name,
                "context": context,
                "category": category,
                "duration_seconds": duration_seconds,
                "idle_seconds": idle_seconds,
                "keystrokes": keystrokes,
                "clicks": clicks,
                "scrolls": scrolls,
                "occurred_at": occurred_at,
            }
        )

    return out, errors
