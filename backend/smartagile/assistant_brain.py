"""
Productivity data + deterministic formatting. LangGraph lives in `assistant_graph`.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from django.utils import timezone

from .insights import (
    build_insights,
    compute_app_activity_detail,
    compute_browser_page_activity_detail,
    compute_features_from_events,
    compute_features_from_events_window,
    load_baseline_rollups,
)


def _fmt_sec(s: float) -> str:
    s = int(round(s))
    if s < 60:
        return f"{s}s"
    m, sec = divmod(s, 60)
    if m < 60:
        return f"{m}m {sec}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def build_productivity_context(
    user, d: date | None = None
) -> dict[str, Any]:
    """
    Deterministic feature snapshot for one calendar day (server tz when d is None).
    Safe to pass to an LLM as JSON; numbers are from UsageEvent aggregation.
    """
    if d is None:
        d = timezone.localdate()
    uid = user.pk
    features = compute_features_from_events(uid, d)
    app_activity = compute_app_activity_detail(uid, d, top_pairs=10, top_apps=12)
    chrome_pages = compute_browser_page_activity_detail(uid, d, browser_name="Google Chrome", top_pages=15)
    baseline = load_baseline_rollups(uid, d, days=7)
    insight_cards = build_insights(features, baseline)
    total = float(features.total_duration_seconds or 0.0)
    # Add friendly duration strings for UI/LLM responses.
    try:
        for row in (app_activity or {}).get("most_time_in_apps") or []:
            if isinstance(row, dict) and row.get("duration_seconds") is not None:
                row["duration_human"] = _fmt_sec(float(row["duration_seconds"] or 0))
        for row in (app_activity or {}).get("most_opened_apps") or []:
            if isinstance(row, dict) and row.get("duration_seconds") is not None:
                row["duration_human"] = _fmt_sec(float(row["duration_seconds"] or 0))
        for row in (chrome_pages or {}).get("most_time_in_pages") or []:
            if isinstance(row, dict) and row.get("duration_seconds") is not None:
                row["duration_human"] = _fmt_sec(float(row["duration_seconds"] or 0))
    except Exception:
        # Non-critical formatting: keep raw seconds if any unexpected shape
        pass

    return {
        "date": d.isoformat(),
        "has_data": total > 0,
        "features": features.to_dict(),
        "app_activity": app_activity,
        "browser_pages": {
            "chrome": chrome_pages,
        },
        "baseline_sample_days": len(baseline),
        "insights": insight_cards[:12],
    }


def build_current_productivity_context(
    user,
    *,
    minutes: int = 15,
) -> dict[str, Any]:
    """
    "Right now" snapshot: aggregates recent UsageEvent rows in a rolling time window.
    """
    minutes = max(3, min(int(minutes), 120))
    until_dt = timezone.now()
    since_dt = until_dt - timezone.timedelta(minutes=minutes)
    uid = user.pk

    features = compute_features_from_events_window(uid, since_dt=since_dt, until_dt=until_dt)
    total = float(features.total_duration_seconds or 0.0)

    # If there is no recent activity in the window, fall back to "today so far"
    # so "currently" still produces a useful answer.
    if total <= 0:
        d = timezone.localdate()
        day_ctx = build_productivity_context(user, d)
        return {
            **day_ctx,
            "window": {
                "minutes": minutes,
                "since": since_dt.isoformat(),
                "until": until_dt.isoformat(),
                "mode": "fallback_to_today",
            },
        }

    # Window mode: keep baseline/insights empty (they are day-based).
    return {
        "date": timezone.localdate().isoformat(),
        "window": {
            "minutes": minutes,
            "since": since_dt.isoformat(),
            "until": until_dt.isoformat(),
            "mode": "window",
        },
        "has_data": total > 0,
        "features": features.to_dict(),
        "app_activity": None,
        "browser_pages": None,
        "baseline_sample_days": 0,
        "insights": [],
    }


def format_productivity_markdown(ctx: dict[str, Any]) -> str:
    """User-visible text from a productivity context dict (no LLM)."""
    d = ctx.get("date", "")
    features = ctx.get("features") or {}
    if not ctx.get("has_data"):
        return (
            f"I do not have usage events for {d} yet. "
            "When the desktop agent is running, I can summarize focus, distraction, and switching here."
        )

    focus = features.get("focus_score")
    w = float(features.get("work_duration_seconds") or 0)
    dist = float(features.get("distracted_duration_seconds") or 0)
    sw = int(features.get("app_switch_count") or 0)
    deep = int(features.get("deep_work_segment_count") or 0)

    lines: list[str] = [
        f"Here is your productivity snapshot for **{d}** (from tracked activity).",
    ]
    if focus is not None:
        lines.append(f"- **Focus (work / total time):** {float(focus):.0%}.")
    lines.append(
        f"- **Work vs distraction:** {_fmt_sec(w)} work, "
        f"{_fmt_sec(dist)} estimated distraction."
    )
    lines.append(
        f"- **Context switches (app changes):** {sw} · "
        f"**Deep work blocks (15m+ work):** {deep}."
    )
    insight_cards = ctx.get("insights") or []
    if insight_cards:
        lines.append("**Notable points:**")
        for c in insight_cards[:5]:
            c = c or {}
            title = c.get("title") or ""
            body = c.get("body") or c.get("message") or ""
            if body:
                lines.append(f"  - {title}: {body}" if title else f"  - {body}")
            elif title:
                lines.append(f"  - {title}")
    else:
        lines.append(
            "_No automatic insight cards for this day; metrics above are from raw totals._"
        )
    return "\n\n".join(lines)


def productivity_result_json(ctx: dict[str, Any]) -> dict[str, Any]:
    """Structured storage payload for the assistant message."""
    return {
        "kind": "productivity_snapshot",
        "date": ctx.get("date"),
        "has_data": ctx.get("has_data"),
        "features": ctx.get("features"),
        "app_activity": ctx.get("app_activity"),
        "browser_pages": ctx.get("browser_pages"),
        "baseline_sample_days": ctx.get("baseline_sample_days"),
        "insights": (ctx.get("insights") or [])[:8],
    }


def build_productivity_snapshot(
    user, d: date | None = None
) -> tuple[str, dict[str, Any]]:
    """
    Full deterministic reply (text + result_json) for a productivity snapshot.
    Used as fallback when the graph runs without an LLM synthesizer.
    """
    ctx = build_productivity_context(user, d)
    return format_productivity_markdown(ctx), productivity_result_json(ctx)


def _compact_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)[:24000]


def build_productivity_snapshot_for_llm(ctx: dict[str, Any]) -> str:
    """Narrow JSON string for LLM input (capped)."""
    return _compact_json(ctx)


def generate_assistant_reply(
    user,
    user_text: str,
    *,
    session_id: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Return (visible_markdownish_text, structured_json for result_json).
    Delegates to the LangGraph runner with intent routing.
    """
    from .assistant_graph.runner import run_assistant_graph

    return run_assistant_graph(user, user_text, session_id=session_id)
