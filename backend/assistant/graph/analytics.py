"""
Productivity analytics agent (Phase 1 + Phase 2).

Flow: a user's natural-language question -> `plan_analytics_query` (LLM, strict JSON)
-> `run_analytics_query` (deterministic DB aggregation over a resolved time window).

Supported metrics:
  * top_apps           - "which app did I spend most time on this week?"
  * time_on_app        - "how much time did I spend on Figma today?"
  * focus_summary      - "how focused was I last week?"
  * top_sites          - "what websites did I spend the most time on this week?"
  * time_on_site       - "how much time on YouTube today?"
  * category_breakdown - "how much time on work vs distractions this week?"
  * compare            - "did I focus more this week than last week?"

The planner returns None for greetings / vague questions, so the caller falls back to
the existing day snapshot (no regression).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .llm_factory import invoke_system_human_resilient, is_llm_configured
from .periods import resolve_period

logger = logging.getLogger(__name__)

_METRICS = frozenset(
    {
        "top_apps",
        "time_on_app",
        "focus_summary",
        "top_sites",
        "time_on_site",
        "category_breakdown",
        "compare",
        "trend",
        "explain",
    }
)
# Metrics that `compare` can diff across two periods.
_COMPARE_BASE = frozenset(
    {"focus_summary", "total_time", "time_on_app", "time_on_site", "top_apps", "category_breakdown"}
)
# Metrics that `trend` can plot over time.
_TREND_BASE = frozenset({"focus", "work_time", "total_time", "time_on_app", "time_on_site"})
_PERIOD_KINDS = frozenset(
    {
        "today",
        "yesterday",
        "this_week",
        "last_week",
        "last_n_days",
        "this_month",
        "last_month",
        "custom",
    }
)

# Few-shot examples teach the schema far better than a long rulebook.
_FEWSHOTS = [
    (
        "on which app did I spend most of my time",
        {"metric": "top_apps", "app_name": None, "rank_by": "duration", "limit": 5,
         "period": {"kind": "today", "n": None, "since": None, "until": None}},
    ),
    (
        "which apps did I use the most this week",
        {"metric": "top_apps", "app_name": None, "rank_by": "duration", "limit": 5,
         "period": {"kind": "this_week", "n": None, "since": None, "until": None}},
    ),
    (
        "what app did I open the most today",
        {"metric": "top_apps", "app_name": None, "rank_by": "open_count", "limit": 5,
         "period": {"kind": "today", "n": None, "since": None, "until": None}},
    ),
    (
        "how much time did I spend on Figma this week",
        {"metric": "time_on_app", "app_name": "Figma", "rank_by": "duration", "limit": 5,
         "period": {"kind": "this_week", "n": None, "since": None, "until": None}},
    ),
    (
        "time spent in VS Code over the last 7 days",
        {"metric": "time_on_app", "app_name": "VS Code", "rank_by": "duration", "limit": 5,
         "period": {"kind": "last_n_days", "n": 7, "since": None, "until": None}},
    ),
    (
        "how focused was I last week",
        {"metric": "focus_summary", "app_name": None, "rank_by": "duration", "limit": 5,
         "period": {"kind": "last_week", "n": None, "since": None, "until": None}},
    ),
    (
        "was I distracted this month",
        {"metric": "focus_summary", "app_name": None, "rank_by": "duration", "limit": 5,
         "period": {"kind": "this_month", "n": None, "since": None, "until": None}},
    ),
    (
        "what websites did I spend the most time on this week",
        {"metric": "top_sites", "site_query": None, "rank_by": "duration", "limit": 5,
         "period": {"kind": "this_week", "n": None, "since": None, "until": None}},
    ),
    (
        "how much time did I spend on youtube today",
        {"metric": "time_on_site", "site_query": "youtube", "rank_by": "duration", "limit": 5,
         "period": {"kind": "today", "n": None, "since": None, "until": None}},
    ),
    (
        "how much time on work vs distractions this week",
        {"metric": "category_breakdown", "rank_by": "duration", "limit": 10,
         "period": {"kind": "this_week", "n": None, "since": None, "until": None}},
    ),
    (
        "what category did I spend the most time on this month",
        {"metric": "category_breakdown", "rank_by": "duration", "limit": 10,
         "period": {"kind": "this_month", "n": None, "since": None, "until": None}},
    ),
    (
        "did I focus more this week than last week",
        {"metric": "compare", "base_metric": "focus_summary",
         "period": {"kind": "this_week", "n": None, "since": None, "until": None},
         "compare_to": {"kind": "last_week", "n": None, "since": None, "until": None}},
    ),
    (
        "am I spending more time on youtube this week compared to last week",
        {"metric": "compare", "base_metric": "time_on_site", "site_query": "youtube",
         "period": {"kind": "this_week", "n": None, "since": None, "until": None},
         "compare_to": {"kind": "last_week", "n": None, "since": None, "until": None}},
    ),
    (
        "how has my focus trended this week",
        {"metric": "trend", "base_metric": "focus", "bucket": "day",
         "period": {"kind": "this_week", "n": None, "since": None, "until": None}},
    ),
    (
        "show my daily work time over the last 2 weeks",
        {"metric": "trend", "base_metric": "work_time", "bucket": "day",
         "period": {"kind": "last_n_days", "n": 14, "since": None, "until": None}},
    ),
    (
        "what's my youtube usage trend this month",
        {"metric": "trend", "base_metric": "time_on_site", "site_query": "youtube", "bucket": "week",
         "period": {"kind": "this_month", "n": None, "since": None, "until": None}},
    ),
    (
        "why was my focus low this week",
        {"metric": "explain",
         "period": {"kind": "this_week", "n": None, "since": None, "until": None}},
    ),
    (
        "what's hurting my productivity this month",
        {"metric": "explain",
         "period": {"kind": "this_month", "n": None, "since": None, "until": None}},
    ),
    (
        "hey there",
        {"metric": "none"},
    ),
]

_PLANNER_SYSTEM = (
    "You convert a SmartAgile user's productivity question into a STRICT JSON analytics query.\n"
    "Output JSON ONLY — no markdown, no explanation.\n\n"
    "Schema:\n"
    "{\n"
    '  "metric": "top_apps" | "time_on_app" | "focus_summary" | "top_sites" | "time_on_site"\n'
    '          | "category_breakdown" | "compare" | "trend" | "explain" | "none",\n'
    '  "app_name": <string or null>,   // the app for time_on_app\n'
    '  "site_query": <string or null>, // the website/page keyword for time_on_site (e.g. "youtube")\n'
    '  "rank_by": "duration" | "open_count",\n'
    '  "limit": <int 1-10>,\n'
    '  "period": {"kind": "today|yesterday|this_week|last_week|last_n_days|this_month|last_month|custom",\n'
    '             "n": <int or null>, "since": <YYYY-MM-DD or null>, "until": <YYYY-MM-DD or null>},\n'
    '  "base_metric": <for compare: focus_summary|total_time|time_on_app|time_on_site|top_apps|'
    "category_breakdown; for trend: focus|work_time|total_time|time_on_app|time_on_site>,\n"
    '  "bucket": "day" | "week",   // only for trend (default day; week for long ranges)\n'
    '  "compare_to": <a period object, for compare (the other period) or explain (the baseline); '
    "may be null to use the immediately-preceding comparable period>\n"
    "}\n\n"
    "Pick the metric:\n"
    "- top_apps: which app/application was used most, top/most-used apps, or most OPENED app "
    '(use rank_by="open_count" for opened/launched/frequency; otherwise rank_by="duration").\n'
    "- time_on_app: how much time on ONE specific named app; put that app in app_name.\n"
    "- focus_summary: focus, distraction, productivity, deep work, or context-switching over a period.\n"
    "- top_sites: which websites/web pages were used most (browser activity); rank_by as for top_apps.\n"
    "- time_on_site: how much time on ONE specific website/page; put the keyword in site_query.\n"
    "- category_breakdown: time per category, or work vs distraction split over a period.\n"
    "- compare: comparing one metric across two time periods ('more/less than', 'vs', 'compared to'). "
    "Set base_metric to what is compared, `period` to the CURRENT/first period, and compare_to to the "
    "other period (or null to auto-use the preceding period). Carry app_name/site_query when relevant.\n"
    "- trend: how a metric changes OVER TIME ('trend', 'over the last N days', 'daily/weekly'). Set "
    "base_metric to the thing plotted and bucket to day (default) or week. Carry app_name/site_query.\n"
    "- explain: diagnostic WHY questions ('why was my focus low', 'what is hurting/helping my "
    "productivity'). Just set the period (and optionally compare_to as the baseline).\n"
    "- none: greetings or vague messages with no measurable productivity intent.\n\n"
    "Period: default kind=today when no time is mentioned. Map 'this week'->this_week, "
    "'last week'->last_week, 'yesterday'->yesterday, 'this month'->this_month, 'last month'->last_month, "
    "'last/past N days'->last_n_days with n=N, explicit dates->custom (since/until as YYYY-MM-DD).\n"
    "Never invent an app_name or site_query. If time_on_app has no named app, use top_apps; "
    "if time_on_site has no site keyword, use top_sites.\n\n"
    "Examples:\n"
    + "\n".join(
        f'user: {msg}\njson: {json.dumps(out, ensure_ascii=False)}' for msg, out in _FEWSHOTS
    )
)


def _parse_json_obj(content: str) -> dict[str, Any] | None:
    s = (content or "").strip()
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
        return o if isinstance(o, dict) else None
    except Exception:
        return None


def _norm_period(period: Any) -> dict[str, Any]:
    period = period if isinstance(period, dict) else {}
    kind = str(period.get("kind") or "today").strip().lower()
    if kind not in _PERIOD_KINDS:
        kind = "today"
    return {
        "kind": kind,
        "n": period.get("n"),
        "since": period.get("since"),
        "until": period.get("until"),
    }


def _normalize_query(o: dict[str, Any]) -> dict[str, Any] | None:
    metric = str(o.get("metric") or "").strip()
    if metric not in _METRICS:
        return None  # "none" / unknown -> caller falls back to day snapshot.

    rank_by = str(o.get("rank_by") or "duration").strip()
    if rank_by not in ("duration", "open_count"):
        rank_by = "duration"

    try:
        limit = int(o.get("limit") or 5)
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, 10))

    app_name = o.get("app_name")
    app_name = str(app_name).strip() if app_name else None
    site_query = o.get("site_query")
    site_query = str(site_query).strip() if site_query else None

    # Degrade single-target metrics that are missing their target.
    if metric == "time_on_app" and not app_name:
        metric = "top_apps"
    if metric == "time_on_site" and not site_query:
        metric = "top_sites"

    out: dict[str, Any] = {
        "metric": metric,
        "app_name": app_name,
        "site_query": site_query,
        "rank_by": rank_by,
        "limit": limit,
        "period": _norm_period(o.get("period")),
    }

    if metric == "compare":
        base = str(o.get("base_metric") or "").strip()
        if base not in _COMPARE_BASE:
            base = "total_time"
        # If the chosen base needs a target it doesn't have, pick a sensible base instead.
        if base == "time_on_app" and not app_name:
            base = "top_apps"
        if base == "time_on_site" and not site_query:
            base = "total_time"
        out["base_metric"] = base
        out["compare_to"] = _norm_period(o["compare_to"]) if o.get("compare_to") else None

    elif metric == "trend":
        base = str(o.get("base_metric") or "").strip()
        if base not in _TREND_BASE:
            base = "focus"
        if base == "time_on_app" and not app_name:
            base = "total_time"
        if base == "time_on_site" and not site_query:
            base = "total_time"
        out["base_metric"] = base
        out["bucket"] = "week" if str(o.get("bucket") or "").strip().lower().startswith("week") else "day"

    elif metric == "explain":
        out["compare_to"] = _norm_period(o["compare_to"]) if o.get("compare_to") else None

    return out


def plan_analytics_query(
    user_text: str,
    *,
    recent_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """LLM planner. Returns a normalized analytics query, or None to fall back."""
    t = (user_text or "").strip()
    if not t or not is_llm_configured():
        return None
    try:
        human = json.dumps(
            {"user_message": t, "recent_messages": (recent_messages or [])[-8:]},
            ensure_ascii=False,
            default=str,
        )[:8000]
        raw, _ = invoke_system_human_resilient(_PLANNER_SYSTEM, human)
        o = _parse_json_obj(raw)
        return _normalize_query(o) if o else None
    except Exception:
        logger.exception("plan_analytics_query failed")
        return None


def run_analytics_query(user: Any, query: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve the period(s) and build the matching context for the query."""
    from ..brain import build_comparison_context, build_productivity_window_context

    if not query:
        return None

    metric = query.get("metric")
    if metric == "compare":
        from .periods import resolve_comparison

        current, previous = resolve_comparison(query.get("period"), query.get("compare_to"))
        return build_comparison_context(
            user,
            base_metric=query.get("base_metric") or "total_time",
            current=current,
            previous=previous,
            app_name=query.get("app_name"),
            site_query=query.get("site_query"),
        )

    if metric == "explain":
        from ..brain import build_explanation_context
        from .periods import resolve_comparison

        current, previous = resolve_comparison(query.get("period"), query.get("compare_to"))
        return build_explanation_context(user, current=current, previous=previous)

    if metric == "trend":
        from ..brain import build_trend_context

        since_dt, until_dt, label = resolve_period(query.get("period"))
        return build_trend_context(
            user,
            since_dt=since_dt,
            until_dt=until_dt,
            label=label,
            base_metric=query.get("base_metric") or "focus",
            bucket=query.get("bucket") or "day",
            app_name=query.get("app_name"),
            site_query=query.get("site_query"),
        )

    since_dt, until_dt, label = resolve_period(query.get("period"))
    return build_productivity_window_context(
        user,
        since_dt=since_dt,
        until_dt=until_dt,
        label=label,
        metric=metric,
        app_name=query.get("app_name"),
        site_query=query.get("site_query"),
        rank_by=query.get("rank_by") or "duration",
        limit=int(query.get("limit") or 5),
    )
