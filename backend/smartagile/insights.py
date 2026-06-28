"""
Intelligence layer: features from UsageEvent + rule-based + statistical insights.
"""

from __future__ import annotations

import re
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncWeek
from django.utils import timezone

from .models import UsageEvent, UsageDailyRollup


def canonical_category(value: str | None) -> str:
    """
    Collapse the desktop ML classifier's noisy category labels into one canonical form.

    Handles separator + qualifier variants so they aggregate together, e.g.:
      "work", "work-related", "Work Related"          -> "work"
      "entertainment related", "entertainment-related" -> "entertainment"
    Empty / missing categories return "" (callers display them as "uncategorized").
    """
    s = (value or "").strip().lower()
    if not s:
        return ""
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*related$", "", s).strip()  # drop trailing "related" qualifier
    return s


# Categories the desktop ML classifier treats as focused work. We match the raw variants
# in SQL (WORK_Q) and the canonical form ("work") when aggregating in Python.
WORK_Q = (
    Q(category__iexact="work")
    | Q(category__iexact="work-related")
    | Q(category__iexact="work related")
)


@dataclass
class DayFeatures:
    day: str
    total_duration_seconds: float
    work_duration_seconds: float
    distracted_duration_seconds: float
    event_count: int
    app_switch_count: int
    deep_work_segment_count: int
    focus_score: float | None

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self)}


def compute_features_from_events(user_id: int, d: date) -> DayFeatures:
    """Aggregate one user's UsageEvent rows for a calendar day (in the active TZ, date part of occurred_at)."""
    base = UsageEvent.objects.filter(user_id=user_id, occurred_at__date=d)
    total = float(base.aggregate(s=Sum("duration_seconds"))["s"] or 0)
    work = float(
        base.filter(WORK_Q).aggregate(s=Sum("duration_seconds"))["s"] or 0
    )
    distracted = max(0.0, total - work)
    event_count = base.count()
    deep_work = base.filter(WORK_Q, duration_seconds__gte=900).count()

    ordered = list(
        base.order_by("occurred_at", "id").values_list("name", "source_type")
    )
    app_switch_count = 0
    for i in range(1, len(ordered)):
        if ordered[i] != ordered[i - 1]:
            app_switch_count += 1

    if total > 0:
        focus = work / total
    else:
        focus = None

    return DayFeatures(
        day=d.isoformat(),
        total_duration_seconds=round(total, 2),
        work_duration_seconds=round(work, 2),
        distracted_duration_seconds=round(distracted, 2),
        event_count=event_count,
        app_switch_count=app_switch_count,
        deep_work_segment_count=deep_work,
        focus_score=round(focus, 4) if focus is not None else None,
    )


def compute_features_from_events_window(
    user_id: int,
    *,
    since_dt,
    until_dt=None,
) -> DayFeatures:
    """
    Aggregate one user's UsageEvent rows for a time window (occurred_at in [since_dt, until_dt)).
    Returns a DayFeatures-like object with day="window".
    """
    if until_dt is None:
        until_dt = timezone.now()
    base = UsageEvent.objects.filter(user_id=user_id, occurred_at__gte=since_dt, occurred_at__lt=until_dt)
    total = float(base.aggregate(s=Sum("duration_seconds"))["s"] or 0)
    work = float(base.filter(WORK_Q).aggregate(s=Sum("duration_seconds"))["s"] or 0)
    distracted = max(0.0, total - work)
    event_count = base.count()
    deep_work = base.filter(WORK_Q, duration_seconds__gte=900).count()

    ordered = list(base.order_by("occurred_at", "id").values_list("name", "source_type"))
    app_switch_count = 0
    for i in range(1, len(ordered)):
        if ordered[i] != ordered[i - 1]:
            app_switch_count += 1

    focus = (work / total) if total > 0 else None

    return DayFeatures(
        day="window",
        total_duration_seconds=round(total, 2),
        work_duration_seconds=round(work, 2),
        distracted_duration_seconds=round(distracted, 2),
        event_count=event_count,
        app_switch_count=app_switch_count,
        deep_work_segment_count=deep_work,
        focus_score=round(focus, 4) if focus is not None else None,
    )


def _app_activity_from_rows(
    rows: list[dict[str, Any]], *, top_pairs: int, top_apps: int
) -> dict[str, Any]:
    """Shared aggregation for app-activity detail (used by day + window variants)."""
    if not rows:
        return {
            "top_switch_pairs": [],
            "most_opened_apps": [],
            "most_time_in_apps": [],
        }

    duration_by_key: dict[tuple[str, str], float] = defaultdict(float)
    opens_by_key: dict[tuple[str, str], int] = defaultdict(int)
    for r in rows:
        key = (r["name"] or "", r["source_type"] or "")
        duration_by_key[key] += float(r["duration_seconds"] or 0)
        opens_by_key[key] += 1

    switch_counter: Counter[tuple[tuple[str, str], tuple[str, str]]] = Counter()
    prev: tuple[str, str] | None = None
    for r in rows:
        key = (r["name"] or "", r["source_type"] or "")
        if prev is not None and key != prev:
            switch_counter[(prev, key)] += 1
        prev = key

    pair_items: list[dict[str, Any]] = []
    for (a, b), c in switch_counter.most_common(top_pairs):
        (an, ast), (bn, bst) = a, b
        pair_items.append(
            {
                "from_name": an,
                "from_source_type": ast,
                "to_name": bn,
                "to_source_type": bst,
                "count": c,
            }
        )

    app_keys = list(duration_by_key.keys())
    by_opens = sorted(
        app_keys, key=lambda k: (-opens_by_key[k], -duration_by_key[k], k[0])
    )[:top_apps]
    by_time = sorted(
        app_keys, key=lambda k: (-duration_by_key[k], -opens_by_key[k], k[0])
    )[:top_apps]

    def app_row(k: tuple[str, str]) -> dict[str, Any]:
        n, st = k
        return {
            "name": n,
            "source_type": st,
            "open_count": opens_by_key[k],
            "duration_seconds": round(duration_by_key[k], 2),
        }

    return {
        "top_switch_pairs": pair_items,
        "most_opened_apps": [app_row(k) for k in by_opens],
        "most_time_in_apps": [app_row(k) for k in by_time],
    }


def _ordered_activity_rows(base) -> list[dict[str, Any]]:
    return list(
        base.order_by("occurred_at", "id").values("name", "source_type", "duration_seconds")
    )


def compute_app_activity_detail(
    user_id: int, d: date, *, top_pairs: int = 12, top_apps: int = 12
) -> dict[str, Any]:
    """Per-day app usage: most common A→B context switches and per-app time / open counts."""
    base = UsageEvent.objects.filter(user_id=user_id, occurred_at__date=d)
    return _app_activity_from_rows(
        _ordered_activity_rows(base), top_pairs=top_pairs, top_apps=top_apps
    )


def compute_app_activity_detail_window(
    user_id: int, *, since_dt, until_dt, top_pairs: int = 12, top_apps: int = 12
) -> dict[str, Any]:
    """Same as compute_app_activity_detail, but over an arbitrary [since_dt, until_dt) window."""
    base = UsageEvent.objects.filter(
        user_id=user_id, occurred_at__gte=since_dt, occurred_at__lt=until_dt
    )
    return _app_activity_from_rows(
        _ordered_activity_rows(base), top_pairs=top_pairs, top_apps=top_apps
    )


def compute_time_on_app_window(
    user_id: int, app_name: str, *, since_dt, until_dt
) -> dict[str, Any]:
    """
    Total time + open count for ONE app/software over a window.

    Matches `name` case-insensitively: exact match first, then falls back to substring
    (so "vs code" finds "Visual Studio Code"). Returns matched=False when nothing is found.
    """
    name = (app_name or "").strip()
    base = UsageEvent.objects.filter(
        user_id=user_id, occurred_at__gte=since_dt, occurred_at__lt=until_dt
    )
    if not name:
        return {"query_name": name, "matched": False, "duration_seconds": 0.0, "open_count": 0}

    exact = base.filter(name__iexact=name)
    qs = exact if exact.exists() else base.filter(name__icontains=name)
    dur = float(qs.aggregate(s=Sum("duration_seconds"))["s"] or 0)
    opens = qs.count()
    resolved = qs.values_list("name", flat=True).first() or name
    return {
        "query_name": name,
        "app_name": resolved,
        "matched": opens > 0,
        "duration_seconds": round(dur, 2),
        "open_count": int(opens),
    }


def _browser_pages_from_rows(
    rows: list[dict[str, Any]],
    *,
    browser_name: str | None,
    top_pages: int,
    rank_by: str = "duration",
) -> dict[str, Any]:
    """Shared aggregation for browser "page title" detail (day + window variants)."""
    if not rows:
        return {"browser_name": browser_name, "most_time_in_pages": []}

    dur: dict[str, float] = defaultdict(float)
    opens: dict[str, int] = defaultdict(int)
    for r in rows:
        title = (r.get("context") or "").strip()
        if not title:
            continue
        title = title[:256]
        dur[title] += float(r.get("duration_seconds") or 0)
        opens[title] += 1

    if rank_by == "open_count":
        sort_key = lambda k: (-opens[k], -dur[k], k)  # noqa: E731
    else:
        sort_key = lambda k: (-dur[k], -opens[k], k)  # noqa: E731
    top = sorted(dur.keys(), key=sort_key)[: max(1, min(int(top_pages), 50))]
    return {
        "browser_name": (browser_name or rows[0].get("name") or "").strip() or None,
        "most_time_in_pages": [
            {"title": k, "duration_seconds": round(dur[k], 2), "open_count": int(opens[k])}
            for k in top
        ],
    }


def _browser_base(user_id: int, browser_name: str | None):
    base = UsageEvent.objects.filter(
        user_id=user_id, source_type=UsageEvent.SourceType.BROWSER
    )
    if browser_name:
        base = base.filter(name__iexact=str(browser_name).strip())
    return base


def compute_browser_page_activity_detail(
    user_id: int,
    d: date,
    *,
    browser_name: str | None = None,
    top_pages: int = 15,
) -> dict[str, Any]:
    """
    Per-day browser "pages" inferred from UsageEvent.context.

    Notes:
    - The desktop agent currently sends browser events with:
      - name = software name (e.g. "Google Chrome")
      - context = normalized window/tab title (NOT a URL)
    - Therefore this returns "page titles" rather than strict website URLs.
    """
    base = _browser_base(user_id, browser_name).filter(occurred_at__date=d)
    rows = list(base.values("name", "context", "duration_seconds").order_by("occurred_at", "id"))
    return _browser_pages_from_rows(rows, browser_name=browser_name, top_pages=top_pages)


def compute_browser_page_activity_detail_window(
    user_id: int,
    *,
    since_dt,
    until_dt,
    browser_name: str | None = None,
    top_pages: int = 15,
    rank_by: str = "duration",
) -> dict[str, Any]:
    """Same as compute_browser_page_activity_detail, over [since_dt, until_dt)."""
    base = _browser_base(user_id, browser_name).filter(
        occurred_at__gte=since_dt, occurred_at__lt=until_dt
    )
    rows = list(base.values("name", "context", "duration_seconds").order_by("occurred_at", "id"))
    return _browser_pages_from_rows(
        rows, browser_name=browser_name, top_pages=top_pages, rank_by=rank_by
    )


def compute_time_on_site_window(
    user_id: int,
    site_query: str,
    *,
    since_dt,
    until_dt,
    browser_name: str | None = None,
) -> dict[str, Any]:
    """
    Total time + visit count for a website/page over a window, matched by substring on
    the page TITLE (UsageEvent.context). Titles are not guaranteed URLs.
    """
    q = (site_query or "").strip()
    if not q:
        return {"query": q, "matched": False, "duration_seconds": 0.0, "open_count": 0, "sample_titles": []}

    base = _browser_base(user_id, browser_name).filter(
        occurred_at__gte=since_dt, occurred_at__lt=until_dt, context__icontains=q
    )
    dur = float(base.aggregate(s=Sum("duration_seconds"))["s"] or 0)
    opens = base.count()
    sample = (
        base.values("context")
        .annotate(d=Sum("duration_seconds"))
        .order_by("-d")
        .values_list("context", flat=True)[:5]
    )
    return {
        "query": q,
        "matched": opens > 0,
        "duration_seconds": round(dur, 2),
        "open_count": int(opens),
        "sample_titles": [s[:256] for s in sample if s],
    }


# Canonical categories treated as focused work (see canonical_category / WORK_Q).
_WORK_CATEGORIES = {"work"}


def compute_category_breakdown_window(
    user_id: int,
    *,
    since_dt,
    until_dt,
    top: int = 10,
) -> dict[str, Any]:
    """
    Time-per-category over a window (work vs distraction split + ranked categories).

    Categories come from UsageEvent.category (populated by the desktop ML models) and are
    canonicalized here so noisy variants ("work" / "work-related", "entertainment related" /
    "entertainment-related") merge into a single bucket. Empty -> "uncategorized".
    """
    base = UsageEvent.objects.filter(
        user_id=user_id, occurred_at__gte=since_dt, occurred_at__lt=until_dt
    )
    merged: dict[str, dict[str, float]] = defaultdict(lambda: {"dur": 0.0, "n": 0})
    for r in base.values("category").annotate(dur=Sum("duration_seconds"), n=Count("id")):
        name = canonical_category(r["category"]) or "uncategorized"
        merged[name]["dur"] += float(r["dur"] or 0)
        merged[name]["n"] += int(r["n"] or 0)

    total = sum(v["dur"] for v in merged.values())
    work = sum(v["dur"] for k, v in merged.items() if k in _WORK_CATEGORIES)
    distracted = max(0.0, total - work)

    cats = [
        {
            "category": k,
            "duration_seconds": round(v["dur"], 2),
            "event_count": int(v["n"]),
            "share": round(v["dur"] / total, 4) if total > 0 else 0.0,
        }
        for k, v in merged.items()
    ]
    cats.sort(key=lambda c: (-c["duration_seconds"], c["category"]))
    return {
        "total_duration_seconds": round(total, 2),
        "work_duration_seconds": round(work, 2),
        "distracted_duration_seconds": round(distracted, 2),
        "focus_score": round(work / total, 4) if total > 0 else None,
        "categories": cats[: max(1, min(int(top), 25))],
    }


def compute_top_apps_split_window(
    user_id: int, *, since_dt, until_dt, top: int = 5
) -> dict[str, Any]:
    """Top apps by time, split into focused-work vs distraction (used by `explain`)."""
    base = UsageEvent.objects.filter(
        user_id=user_id, occurred_at__gte=since_dt, occurred_at__lt=until_dt
    )

    def _rows(qs):
        out = []
        for r in (
            qs.values("name")
            .annotate(s=Sum("duration_seconds"), n=Count("id"))
            .order_by("-s")[: max(1, min(int(top), 10))]
        ):
            out.append(
                {"name": r["name"], "duration_seconds": round(float(r["s"] or 0), 2),
                 "open_count": int(r["n"] or 0)}
            )
        return out

    return {"work_apps": _rows(base.filter(WORK_Q)), "distraction_apps": _rows(base.exclude(WORK_Q))}


def _trend_direction(values: list[float | None], *, eps: float) -> tuple[float | None, str]:
    """Least-squares slope over non-null points -> (slope_per_bucket, up|down|flat)."""
    pts = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(pts) < 2:
        return None, "flat"
    n = len(pts)
    sx = sum(i for i, _ in pts)
    sy = sum(v for _, v in pts)
    sxx = sum(i * i for i, _ in pts)
    sxy = sum(i * v for i, v in pts)
    denom = n * sxx - sx * sx
    if denom == 0:
        return None, "flat"
    slope = (n * sxy - sx * sy) / denom
    direction = "flat" if abs(slope) < eps else ("up" if slope > 0 else "down")
    return round(slope, 4), direction


def compute_metric_trend(
    user_id: int,
    *,
    since_dt,
    until_dt,
    base_metric: str = "focus",
    bucket: str = "day",
    app_name: str | None = None,
    site_query: str | None = None,
    max_points: int = 60,
) -> dict[str, Any]:
    """
    Bucketed time series for a metric over a window.

    base_metric: focus | work_time | total_time | time_on_app | time_on_site
    bucket: "day" (TruncDate) or "week" (TruncWeek). Values are duration seconds, except
    focus which is a 0..1 ratio (work/total) per bucket.
    """
    bm = (base_metric or "focus").strip()
    trunc = TruncWeek if bucket == "week" else TruncDate
    base = UsageEvent.objects.filter(
        user_id=user_id, occurred_at__gte=since_dt, occurred_at__lt=until_dt
    )

    if bm == "time_on_app" and app_name:
        nm = app_name.strip()
        exact = base.filter(name__iexact=nm)
        base = exact if exact.exists() else base.filter(name__icontains=nm)
    elif bm == "time_on_site" and site_query:
        base = base.filter(
            source_type=UsageEvent.SourceType.BROWSER, context__icontains=site_query.strip()
        )

    totals: dict[Any, float] = {}
    for row in (
        base.annotate(b=trunc("occurred_at")).values("b").annotate(s=Sum("duration_seconds")).order_by("b")
    ):
        totals[row["b"]] = float(row["s"] or 0)

    works: dict[Any, float] = {}
    if bm in ("focus", "focus_summary", "focus_score", "work_time", "work"):
        for row in (
            base.filter(WORK_Q).annotate(b=trunc("occurred_at")).values("b").annotate(s=Sum("duration_seconds"))
        ):
            works[row["b"]] = float(row["s"] or 0)

    is_focus = bm in ("focus", "focus_summary", "focus_score")
    unit = "ratio" if is_focus else "seconds"
    keys = sorted(totals.keys())
    if len(keys) > max_points:
        keys = keys[-max_points:]

    points: list[dict[str, Any]] = []
    for b in keys:
        if is_focus:
            t = totals.get(b, 0.0)
            v = round(works.get(b, 0.0) / t, 4) if t > 0 else None
        elif bm in ("work_time", "work"):
            v = round(works.get(b, 0.0), 2)
        else:  # total_time / time_on_app / time_on_site
            v = round(totals.get(b, 0.0), 2)
        points.append({"bucket": b.isoformat() if hasattr(b, "isoformat") else str(b), "value": v})

    values = [p["value"] for p in points]
    non_null = [v for v in values if v is not None]
    eps = 0.005 if is_focus else 30.0
    slope, direction = _trend_direction(values, eps=eps)

    def _peak(reverse: bool):
        cand = [(p["bucket"], p["value"]) for p in points if p["value"] is not None]
        if not cand:
            return None
        return sorted(cand, key=lambda kv: kv[1], reverse=reverse)[0][0]

    summary = {
        "first": non_null[0] if non_null else None,
        "last": non_null[-1] if non_null else None,
        "min": min(non_null) if non_null else None,
        "max": max(non_null) if non_null else None,
        "avg": round(sum(non_null) / len(non_null), 4) if non_null else None,
        "slope_per_bucket": slope,
        "direction": direction,
        "min_bucket": _peak(reverse=False),
        "max_bucket": _peak(reverse=True),
    }
    return {
        "base_metric": bm,
        "unit": unit,
        "bucket": bucket,
        "app_name": app_name,
        "site_query": site_query,
        "points": points,
        "summary": summary,
    }


def _rollup_to_features(r: UsageDailyRollup) -> DayFeatures:
    t = float(r.total_duration_seconds or 0)
    w = float(r.work_duration_seconds or 0)
    d = max(0.0, t - w)
    fs = (w / t) if t > 0 else None
    return DayFeatures(
        day=r.day.isoformat(),
        total_duration_seconds=round(t, 2),
        work_duration_seconds=round(w, 2),
        distracted_duration_seconds=round(d, 2),
        event_count=int(r.event_count or 0),
        app_switch_count=int(getattr(r, "app_switch_count", 0) or 0),
        deep_work_segment_count=int(getattr(r, "deep_work_segment_count", 0) or 0),
        focus_score=round(fs, 4) if fs is not None else None,
    )


def load_baseline_rollups(
    user_id: int, target: date, days: int = 7
) -> list[DayFeatures]:
    """Previous `days` calendar days before `target` from DB rollup if present."""
    start = target - timedelta(days=days)
    qs = (
        UsageDailyRollup.objects.filter(
            user_id=user_id, day__gte=start, day__lt=target
        )
        .order_by("day")
    )
    return [_rollup_to_features(r) for r in qs]


def build_insights(
    target: DayFeatures, baseline: list[DayFeatures]
) -> list[dict[str, Any]]:
    """Rule-based + simple z-score on focus_score and work time."""
    out: list[dict[str, Any]] = []
    t = target.total_duration_seconds
    w = target.work_duration_seconds
    d = target.distracted_duration_seconds
    sw = target.app_switch_count
    focus = target.focus_score

    if t < 300:
        return [
            {
                "type": "low_data",
                "severity": "info",
                "title": "Not enough activity yet",
                "body": "With under ~5 minutes of tracked time for this day, patterns are not reliable. Use the agent for a full workday to see insights.",
            }
        ]

    if d > w and t > 3600:
        out.append(
            {
                "type": "distraction_ratio",
                "severity": "warning",
                "title": "High distraction time",
                "body": f"Non-work activity (~{int(d/60)} min) exceeded focused work (~{int(w/60)} min) on this day. Consider batching focus blocks and limiting context switching.",
            }
        )

    if sw > 30:
        out.append(
            {
                "type": "context_switches",
                "severity": "info",
                "title": "Frequent app and context switching",
                "body": f"About {sw} switches between applications were detected. Batching similar work and reducing hop frequency often improves flow.",
            }
        )

    if target.deep_work_segment_count < 1 and t > 7200 and w > 1800:
        out.append(
            {
                "type": "deep_work",
                "severity": "info",
                "title": "Few long focus blocks",
                "body": "Few sessions longer than 15 minutes in a work-tagged app. Try calendar blocks for deep work with notifications off.",
            }
        )

    scores = [f.focus_score for f in baseline if f.focus_score is not None]
    if len(scores) >= 3 and focus is not None:
        mu = statistics.mean(scores)
        try:
            sigma = statistics.pstdev(scores)
        except statistics.StatisticsError:
            sigma = 0
        if sigma > 0.01 and focus < mu - 2 * sigma:
            out.append(
                {
                    "type": "anomaly_focus",
                    "severity": "warning",
                    "title": "Focus lower than your usual",
                    "body": f"Today's focus ratio ({focus:.0%}) is well below your recent 7-day pattern (≈{mu:.0%}). Worth checking what changed: meetings, context, or non-work time.",
                }
            )

    work_mins = [f.work_duration_seconds / 60.0 for f in baseline if f.total_duration_seconds > 300]
    if len(work_mins) >= 3:
        wmin = w / 60.0
        mu_w = statistics.mean(work_mins)
        try:
            sig_w = statistics.pstdev(work_mins)
        except statistics.StatisticsError:
            sig_w = 0
        if sig_w > 1 and wmin < mu_w - 2 * sig_w:
            out.append(
                {
                    "type": "anomaly_work_time",
                    "severity": "info",
                    "title": "Less focused work time than usual",
                    "body": f"Tracked work time today is low compared to your last week. This may be expected (leave, light day) or worth reviewing workload.",
                }
            )

    if not out and focus is not None and focus >= 0.55 and d <= w:
        out.append(
            {
                "type": "positive",
                "severity": "success",
                "title": "Solid work-to-time balance",
                "body": f"Work-related time is a healthy share of tracked hours (focus ≈{focus:.0%}). Keep patterns that are working for you.",
            }
        )

    if not out:
        out.append(
            {
                "type": "neutral",
                "severity": "info",
                "title": "No strong signals",
                "body": "We did not find notable patterns for this day. As more data accumulates, trends and baselines will sharpen.",
            }
        )

    return out


def sync_rollup_for_day(user_id: int, d: date) -> UsageDailyRollup:
    """Recompute and save UsageDailyRollup row from events (for ETL or on-demand)."""
    f = compute_features_from_events(user_id, d)
    r, _ = UsageDailyRollup.objects.update_or_create(
        user_id=user_id,
        day=d,
        defaults={
            "total_duration_seconds": f.total_duration_seconds,
            "work_duration_seconds": f.work_duration_seconds,
            "event_count": f.event_count,
            "distracted_duration_seconds": f.distracted_duration_seconds,
            "app_switch_count": f.app_switch_count,
            "deep_work_segment_count": f.deep_work_segment_count,
            "focus_score": f.focus_score,
        },
    )
    return r
