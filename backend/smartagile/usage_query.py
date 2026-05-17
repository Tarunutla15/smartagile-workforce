"""Aggregate usage rows for dashboards (legacy JSON shape for the React app)."""

from django.db.models import Sum
from django.db.models.functions import TruncDate

from .models import UsageEvent


def _usage_row_to_item(app_or_browser, task_or_site, category, duration, idle_seconds, row_date):
    d = row_date.isoformat() if hasattr(row_date, "isoformat") else row_date
    return {
        "applicationname": app_or_browser,
        "task": task_or_site,
        "category": category,
        "duration": float(duration) if duration is not None else 0,
        "idle_seconds": float(idle_seconds) if idle_seconds is not None else 0,
        "date": d,
    }


def usage_rows_for_signup_user_id(user_pk: int):
    """
    Same shape as legacy /api/appdata/: list of dicts with applicationname, task, category,
    duration (seconds), idle_seconds (seconds), date.
    Aggregates UsageEvent rows by day + dimensions.
    """
    uid = int(user_pk)
    rows = (
        UsageEvent.objects.filter(user_id=uid)
        .annotate(day=TruncDate("occurred_at"))
        .values("source_type", "name", "context", "category", "day")
        .annotate(
            duration=Sum("duration_seconds"),
            idle_seconds=Sum("idle_seconds"),
        )
        .order_by("day", "name", "context", "category")
    )
    out = []
    for row in rows:
        out.append(
            _usage_row_to_item(
                row["name"],
                row["context"] or "",
                row["category"] or "",
                row["duration"],
                row["idle_seconds"],
                row["day"],
            )
        )
    return out
