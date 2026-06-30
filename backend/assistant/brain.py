"""
Productivity data + deterministic formatting. LangGraph lives in `assistant.graph`.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from django.utils import timezone

from smartagile.insights import (
    build_insights,
    compute_app_activity_detail,
    compute_app_activity_detail_window,
    compute_browser_page_activity_detail,
    compute_browser_page_activity_detail_window,
    compute_category_breakdown_window,
    compute_features_from_events,
    compute_features_from_events_window,
    compute_metric_trend,
    compute_time_on_app_window,
    compute_time_on_site_window,
    compute_top_apps_split_window,
    load_baseline_rollups,
)


def _add_duration_human(app_activity: dict[str, Any] | None) -> None:
    """Attach friendly 'duration_human' strings to app-activity rows in place."""
    if not app_activity:
        return
    for bucket in ("most_time_in_apps", "most_opened_apps"):
        for row in app_activity.get(bucket) or []:
            if isinstance(row, dict) and row.get("duration_seconds") is not None:
                row["duration_human"] = _fmt_sec(float(row["duration_seconds"] or 0))


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
    _add_duration_human(app_activity)
    for row in (chrome_pages or {}).get("most_time_in_pages") or []:
        if isinstance(row, dict) and row.get("duration_seconds") is not None:
            row["duration_human"] = _fmt_sec(float(row["duration_seconds"] or 0))

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


def build_productivity_window_context(
    user,
    *,
    since_dt,
    until_dt,
    label: str,
    metric: str | None = None,
    app_name: str | None = None,
    site_query: str | None = None,
    browser_name: str | None = None,
    rank_by: str = "duration",
    limit: int = 5,
) -> dict[str, Any]:
    """
    Analytics snapshot over an arbitrary [since_dt, until_dt) window.

    Same shape as build_productivity_context (so the synthesizer reads it the same way),
    plus `period`, `query`, and a metric-specific focus block:
      - time_on_app        -> app_focus
      - top_sites          -> browser_pages (windowed)
      - time_on_site       -> site_focus
      - category_breakdown -> category_breakdown
    Baseline/insight cards are day-based, so they stay empty here.
    """
    uid = user.pk
    features = compute_features_from_events_window(uid, since_dt=since_dt, until_dt=until_dt)
    total = float(features.total_duration_seconds or 0.0)
    top_apps = max(int(limit), 12)
    app_activity = compute_app_activity_detail_window(
        uid, since_dt=since_dt, until_dt=until_dt, top_pairs=10, top_apps=top_apps
    )
    _add_duration_human(app_activity)

    ctx: dict[str, Any] = {
        "date": label,  # the synthesizer phrases answers around this period label
        "period": {
            "label": label,
            "since": since_dt.isoformat(),
            "until": until_dt.isoformat(),
        },
        "query": {
            "metric": metric,
            "rank_by": rank_by,
            "app_name": app_name,
            "site_query": site_query,
            "limit": limit,
        },
        "has_data": total > 0,
        "features": features.to_dict(),
        "app_activity": app_activity,
        "browser_pages": None,
        "baseline_sample_days": 0,
        "insights": [],
    }

    if metric == "time_on_app" and app_name:
        focus = compute_time_on_app_window(uid, app_name, since_dt=since_dt, until_dt=until_dt)
        if focus.get("duration_seconds") is not None:
            focus["duration_human"] = _fmt_sec(float(focus["duration_seconds"] or 0))
        ctx["app_focus"] = focus

    elif metric == "top_sites":
        pages = compute_browser_page_activity_detail_window(
            uid,
            since_dt=since_dt,
            until_dt=until_dt,
            browser_name=browser_name,
            top_pages=max(int(limit), 10),
            rank_by=rank_by,
        )
        for row in pages.get("most_time_in_pages") or []:
            if isinstance(row, dict) and row.get("duration_seconds") is not None:
                row["duration_human"] = _fmt_sec(float(row["duration_seconds"] or 0))
        ctx["browser_pages"] = {"browser": pages}

    elif metric == "time_on_site" and site_query:
        site = compute_time_on_site_window(
            uid, site_query, since_dt=since_dt, until_dt=until_dt, browser_name=browser_name
        )
        if site.get("duration_seconds") is not None:
            site["duration_human"] = _fmt_sec(float(site["duration_seconds"] or 0))
        ctx["site_focus"] = site

    elif metric == "category_breakdown":
        cats = compute_category_breakdown_window(uid, since_dt=since_dt, until_dt=until_dt)
        for row in cats.get("categories") or []:
            if isinstance(row, dict) and row.get("duration_seconds") is not None:
                row["duration_human"] = _fmt_sec(float(row["duration_seconds"] or 0))
        for key in ("work_duration_seconds", "distracted_duration_seconds"):
            if cats.get(key) is not None:
                cats[f"{key.replace('_seconds', '')}_human"] = _fmt_sec(float(cats[key] or 0))
        ctx["category_breakdown"] = cats

    return ctx


def _window_metric_value(
    user,
    base_metric: str,
    since_dt,
    until_dt,
    *,
    app_name: str | None = None,
    site_query: str | None = None,
) -> dict[str, Any]:
    """One numeric value (+ human string + detail) for a base metric over a window."""
    uid = user.pk
    bm = (base_metric or "total_time").strip()

    if bm in ("focus_summary", "focus", "focus_score"):
        f = compute_features_from_events_window(uid, since_dt=since_dt, until_dt=until_dt)
        fs = f.focus_score
        return {
            "value": fs,
            "unit": "ratio",
            "value_human": (f"{float(fs):.0%}" if fs is not None else "n/a"),
            "detail": f.to_dict(),
        }
    if bm in ("time_on_app",) and app_name:
        r = compute_time_on_app_window(uid, app_name, since_dt=since_dt, until_dt=until_dt)
        return {"value": float(r["duration_seconds"] or 0), "unit": "seconds",
                "value_human": _fmt_sec(float(r["duration_seconds"] or 0)), "detail": r}
    if bm in ("time_on_site",) and site_query:
        r = compute_time_on_site_window(uid, site_query, since_dt=since_dt, until_dt=until_dt)
        return {"value": float(r["duration_seconds"] or 0), "unit": "seconds",
                "value_human": _fmt_sec(float(r["duration_seconds"] or 0)), "detail": r}
    if bm in ("top_apps", "top_app"):
        a = compute_app_activity_detail_window(uid, since_dt=since_dt, until_dt=until_dt, top_apps=5)
        rows = a.get("most_time_in_apps") or []
        top = rows[0] if rows else None
        v = float(top["duration_seconds"] or 0) if top else 0.0
        return {"value": v, "unit": "seconds", "label": (top.get("name") if top else None),
                "value_human": _fmt_sec(v), "detail": top}
    if bm == "category_breakdown":
        c = compute_category_breakdown_window(uid, since_dt=since_dt, until_dt=until_dt)
        return {"value": float(c["work_duration_seconds"] or 0), "unit": "seconds",
                "value_human": _fmt_sec(float(c["work_duration_seconds"] or 0)), "detail": c}

    # Default: total tracked time.
    f = compute_features_from_events_window(uid, since_dt=since_dt, until_dt=until_dt)
    v = float(f.total_duration_seconds or 0)
    return {"value": v, "unit": "seconds", "value_human": _fmt_sec(v), "detail": f.to_dict()}


def build_comparison_context(
    user,
    *,
    base_metric: str,
    current: tuple,
    previous: tuple,
    app_name: str | None = None,
    site_query: str | None = None,
) -> dict[str, Any]:
    """
    Compare one base metric across two resolved windows.

    `current` / `previous` are (since_dt, until_dt, label) tuples (from resolve_comparison).
    Returns a ctx with a `comparison` block the synthesizer turns into a sentence.
    """
    cs, cu, cl = current
    ps, pu, pl = previous
    cur = _window_metric_value(user, base_metric, cs, cu, app_name=app_name, site_query=site_query)
    prev = _window_metric_value(user, base_metric, ps, pu, app_name=app_name, site_query=site_query)

    cv, pv = cur.get("value"), prev.get("value")
    is_ratio = cur.get("unit") == "ratio"
    delta = None
    delta_human = None
    pct_change = None
    direction = "same"
    if isinstance(cv, (int, float)) and isinstance(pv, (int, float)):
        delta = round(cv - pv, 4)
        if abs(delta) < (1e-4 if is_ratio else 1.0):
            direction = "same"
        else:
            direction = "up" if delta > 0 else "down"
        if is_ratio:
            delta_human = f"{delta:+.0%}"
        else:
            delta_human = _fmt_sec(abs(delta))
        if pv:
            pct_change = round((cv - pv) / abs(pv) * 100.0, 1)

    return {
        "date": f"{cl} vs {pl}",
        "has_data": bool(cv) or bool(pv),
        "comparison": {
            "metric": base_metric,
            "app_name": app_name,
            "site_query": site_query,
            "current": {"label": cl, "since": cs.isoformat(), "until": cu.isoformat(), **cur},
            "previous": {"label": pl, "since": ps.isoformat(), "until": pu.isoformat(), **prev},
            "delta": delta,
            "delta_human": delta_human,
            "pct_change": pct_change,
            "direction": direction,
        },
    }


def _humanize_value(value, unit: str) -> str:
    if value is None:
        return "n/a"
    if unit == "ratio":
        return f"{float(value):.0%}"
    return _fmt_sec(float(value))


def build_trend_context(
    user,
    *,
    since_dt,
    until_dt,
    label: str,
    base_metric: str = "focus",
    bucket: str = "day",
    app_name: str | None = None,
    site_query: str | None = None,
) -> dict[str, Any]:
    """Bucketed time series + summary for a metric over a window (the `trend` metric)."""
    trend = compute_metric_trend(
        user.pk,
        since_dt=since_dt,
        until_dt=until_dt,
        base_metric=base_metric,
        bucket=bucket,
        app_name=app_name,
        site_query=site_query,
    )
    unit = trend.get("unit") or "seconds"
    for p in trend.get("points") or []:
        p["value_human"] = _humanize_value(p.get("value"), unit)
    summary = trend.get("summary") or {}
    for k in ("first", "last", "min", "max", "avg"):
        if summary.get(k) is not None:
            summary[f"{k}_human"] = _humanize_value(summary.get(k), unit)

    return {
        "date": label,
        "period": {"label": label, "since": since_dt.isoformat(), "until": until_dt.isoformat()},
        "query": {
            "metric": "trend",
            "base_metric": base_metric,
            "bucket": bucket,
            "app_name": app_name,
            "site_query": site_query,
        },
        "has_data": any(p.get("value") for p in (trend.get("points") or [])),
        "trend": trend,
    }


def build_explanation_context(
    user,
    *,
    current: tuple,
    previous: tuple,
) -> dict[str, Any]:
    """
    Multi-tool diagnostic for the `explain` metric.

    Bundles focus features, category breakdown, work/distraction app split, and a
    focus-vs-previous comparison into one `explanation` block the synthesizer turns
    into a coach-style "why" answer.
    """
    cs, cu, cl = current
    ps, pu, pl = previous
    uid = user.pk

    features = compute_features_from_events_window(uid, since_dt=cs, until_dt=cu)
    cats = compute_category_breakdown_window(uid, since_dt=cs, until_dt=cu)
    split = compute_top_apps_split_window(uid, since_dt=cs, until_dt=cu, top=5)
    prev_features = compute_features_from_events_window(uid, since_dt=ps, until_dt=pu)

    for row in cats.get("categories") or []:
        if row.get("duration_seconds") is not None:
            row["duration_human"] = _fmt_sec(float(row["duration_seconds"] or 0))
    for grp in ("work_apps", "distraction_apps"):
        for row in split.get(grp) or []:
            if row.get("duration_seconds") is not None:
                row["duration_human"] = _fmt_sec(float(row["duration_seconds"] or 0))

    cur_focus = features.focus_score
    prev_focus = prev_features.focus_score
    delta = None
    direction = "same"
    if cur_focus is not None and prev_focus is not None:
        delta = round(cur_focus - prev_focus, 4)
        if abs(delta) >= 0.005:
            direction = "up" if delta > 0 else "down"

    top_distraction_categories = [
        c for c in (cats.get("categories") or []) if c.get("category") not in ("work", "uncategorized")
    ][:3]

    explanation = {
        "period": cl,
        "focus_score": cur_focus,
        "work_duration_human": _fmt_sec(float(features.work_duration_seconds or 0)),
        "distracted_duration_human": _fmt_sec(float(features.distracted_duration_seconds or 0)),
        "app_switch_count": features.app_switch_count,
        "deep_work_segment_count": features.deep_work_segment_count,
        "vs_previous": {
            "previous_label": pl,
            "previous_focus": prev_focus,
            "delta": delta,
            "direction": direction,
        },
        "top_distraction_categories": top_distraction_categories,
        "top_distraction_apps": split.get("distraction_apps"),
        "top_work_apps": split.get("work_apps"),
    }

    return {
        "date": cl,
        "period": {"label": cl, "since": cs.isoformat(), "until": cu.isoformat()},
        "query": {"metric": "explain"},
        "has_data": float(features.total_duration_seconds or 0) > 0,
        "features": features.to_dict(),
        "explanation": explanation,
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
    payload = {
        "kind": "productivity_snapshot",
        "date": ctx.get("date"),
        "has_data": ctx.get("has_data"),
        "features": ctx.get("features"),
        "app_activity": ctx.get("app_activity"),
        "browser_pages": ctx.get("browser_pages"),
        "baseline_sample_days": ctx.get("baseline_sample_days"),
        "insights": (ctx.get("insights") or [])[:8],
    }
    # Analytics (windowed) extras — present only for the relevant query kinds.
    for key in (
        "period",
        "query",
        "app_focus",
        "site_focus",
        "category_breakdown",
        "comparison",
        "trend",
        "explanation",
    ):
        if ctx.get(key) is not None:
            payload[key] = ctx.get(key)
    return payload


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
    scope: str | None = None,
    project_id: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Return (visible_markdownish_text, structured_json for result_json).
    Delegates to the LangGraph runner with intent routing.
    """
    from .graph.runner import run_assistant_graph

    return run_assistant_graph(
        user, user_text, session_id=session_id, scope=scope, project_id=project_id
    )
