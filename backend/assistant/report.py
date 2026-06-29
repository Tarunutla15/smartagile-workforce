"""
On-demand usage report: resolve a period from a chat message, aggregate the user's
tracked activity for that period, and render a branded HTML + plaintext email.

Data comes from the same UsageEvent aggregation used by the analytics agent
(`smartagile.insights`), so the emailed numbers match the dashboard / assistant.
"""

from __future__ import annotations

import html
import re
from typing import Any

from smartagile.insights import (
    compute_app_activity_detail_window,
    compute_browser_page_activity_detail_window,
    compute_category_breakdown_window,
    compute_features_from_events_window,
)

from .graph.periods import resolve_period

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Brand colors (matches the indigo/violet front-end theme).
_INDIGO = "#4f46e5"
_INDIGO_DARK = "#4338ca"
_VIOLET = "#7c3aed"
_SLATE = "#0f172a"
_MUTED = "#64748b"


def _fmt_sec(s: float | int | None) -> str:
    s = int(round(float(s or 0)))
    if s < 60:
        return f"{s}s"
    m, sec = divmod(s, 60)
    if m < 60:
        return f"{m}m {sec}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


# Page/app names that carry no information for a human-readable report.
_NOISE_NAMES = frozenset({"", "unknown", "unknown software", "new tab", "untitled"})


def _merge_named_rows(
    items: list[dict[str, Any]] | None,
    *name_keys: str,
    drop_noise: bool = False,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """
    Collapse rows that refer to the same thing under different name variants
    (trailing space / casing / multiple source types -> one "Cursor"), summing
    duration + open_count. `name_keys` are tried in order to read the label.
    """
    agg: dict[str, dict[str, Any]] = {}
    for row in items or []:
        if not isinstance(row, dict):
            continue
        raw = ""
        for k in name_keys:
            v = row.get(k)
            if v:
                raw = v
                break
        display = str(raw).strip()
        norm = display.lower()
        if drop_noise and norm in _NOISE_NAMES:
            continue
        if not norm:
            display, norm = "Unknown", "unknown"
        dur = float(row.get("duration_seconds") or 0)
        opens = int(row.get("open_count") or 0)
        cur = agg.get(norm)
        if cur is None:
            agg[norm] = {"name": display, "_disp_dur": dur, "duration_seconds": dur, "open_count": opens}
        else:
            cur["duration_seconds"] += dur
            cur["open_count"] += opens
            if dur > cur["_disp_dur"]:  # keep the label from the largest contributor
                cur["name"], cur["_disp_dur"] = display, dur

    out = [
        {
            "name": v["name"],
            "duration_seconds": round(v["duration_seconds"], 2),
            "duration_human": _fmt_sec(v["duration_seconds"]),
            "open_count": v["open_count"] or None,
        }
        for v in agg.values()
    ]
    out.sort(key=lambda r: -r["duration_seconds"])
    return out[:limit]


def extract_recipient(user_text: str, default_email: str | None) -> tuple[str | None, bool]:
    """
    Return (recipient_email, explicit). If the message names an email address, use it
    (explicit=True); otherwise fall back to the user's own account email.
    """
    m = _EMAIL_RE.search(user_text or "")
    if m:
        return m.group(0).strip(), True
    return ((default_email or "").strip() or None), False


def resolve_report_period(user_text: str) -> dict[str, Any]:
    """
    Map natural language to a period spec understood by `resolve_period`.

    Defaults to `yesterday` (the most common "send me the report" request is for a
    completed day). Returns a dict with kind/n/since/until.
    """
    t = (user_text or "").lower()

    # Respect explicit negations like "today report, not yesterday" so the negated
    # day doesn't win just because it appears as a substring in the message.
    t = re.sub(r"\bnot\s+(?:the\s+)?(today|yesterday)\b", " ", t)

    m = re.search(r"\b(?:last|past|previous)\s+(\d{1,2})\s+days?\b", t)
    if m:
        try:
            n = max(1, min(int(m.group(1)), 90))
        except ValueError:
            n = 7
        return {"kind": "last_n_days", "n": n, "since": None, "until": None}

    # Order matters: check the more specific phrases first.
    if "last week" in t or "previous week" in t:
        kind = "last_week"
    elif "this week" in t or "the week" in t:
        kind = "this_week"
    elif "last month" in t or "previous month" in t:
        kind = "last_month"
    elif "this month" in t:
        kind = "this_month"
    elif "yesterday" in t:
        kind = "yesterday"
    elif "today" in t or "so far" in t:
        kind = "today"
    else:
        kind = "yesterday"

    return {"kind": kind, "n": None, "since": None, "until": None}


def build_usage_report(user, period: dict[str, Any]) -> dict[str, Any]:
    """
    Aggregate a full usage report for one period: totals, work vs distraction, focus,
    top apps, top websites, and a category breakdown. JSON-serializable.
    """
    since_dt, until_dt, label = resolve_period(period)
    uid = user.pk

    features = compute_features_from_events_window(uid, since_dt=since_dt, until_dt=until_dt)
    total = float(features.total_duration_seconds or 0.0)

    app_activity = compute_app_activity_detail_window(
        uid, since_dt=since_dt, until_dt=until_dt, top_pairs=10, top_apps=10
    )
    pages = compute_browser_page_activity_detail_window(
        uid, since_dt=since_dt, until_dt=until_dt, top_pages=10
    )
    cats = compute_category_breakdown_window(uid, since_dt=since_dt, until_dt=until_dt)

    # Apps: merge name variants ("Cursor" / " Cursor" / different source types) into one row.
    top_apps = _merge_named_rows((app_activity or {}).get("most_time_in_apps"), "name")
    # Sites: page rows are keyed on `title`; drop empty/"Unknown" titles so the list is useful.
    top_sites = _merge_named_rows(
        (pages or {}).get("most_time_in_pages"), "title", "name", drop_noise=True
    )

    categories = []
    for row in (cats or {}).get("categories") or []:
        if not isinstance(row, dict):
            continue
        categories.append(
            {
                "category": row.get("category") or "uncategorized",
                "duration_seconds": float(row.get("duration_seconds") or 0),
                "duration_human": _fmt_sec(row.get("duration_seconds")),
            }
        )

    focus = features.focus_score
    work = float(features.work_duration_seconds or 0)
    distracted = float(features.distracted_duration_seconds or 0)

    return {
        "period_label": label,
        "since": since_dt.isoformat(),
        "until": until_dt.isoformat(),
        "has_data": total > 0,
        "summary": {
            "total_seconds": total,
            "total_human": _fmt_sec(total),
            "work_seconds": work,
            "work_human": _fmt_sec(work),
            "distracted_seconds": distracted,
            "distracted_human": _fmt_sec(distracted),
            "focus_score": focus,
            "focus_pct": (f"{float(focus):.0%}" if focus is not None else "n/a"),
            "app_switch_count": int(features.app_switch_count or 0),
            "deep_work_segment_count": int(features.deep_work_segment_count or 0),
        },
        "top_apps": top_apps,
        "top_sites": top_sites,
        "categories": categories[:8],
    }


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def summary_preview(report: dict[str, Any]) -> str:
    """Short markdown-ish text for the chat draft bubble."""
    s = report.get("summary") or {}
    label = report.get("period_label") or "the period"
    if not report.get("has_data"):
        return f"There is no tracked activity for **{label}** yet (is the desktop agent running?)."
    apps = report.get("top_apps") or []
    top_app = apps[0]["name"] if apps else None
    line = (
        f"Usage report for **{label}**: **{s.get('total_human')}** tracked, "
        f"focus **{s.get('focus_pct')}** ({s.get('work_human')} work / "
        f"{s.get('distracted_human')} distraction)."
    )
    if top_app:
        line += f" Top app: **{_esc(top_app)}** ({apps[0]['duration_human']})."
    return line


def render_report_email(report: dict[str, Any], *, user=None) -> tuple[str, str, str]:
    """Return (subject, html_body, text_body) for the report."""
    label = report.get("period_label") or "your activity"
    subject = f"SmartAgile usage report — {label}"
    s = report.get("summary") or {}
    greeting_name = ""
    if user is not None:
        greeting_name = (getattr(user, "first_name", "") or getattr(user, "username", "") or "").strip()

    if not report.get("has_data"):
        text = (
            f"Hi {greeting_name or 'there'},\n\n"
            f"There is no tracked activity for {label} yet. "
            "Make sure the SmartAgile desktop agent is running.\n\n— SmartAgile"
        )
        html_body = (
            f"<div style=\"font-family:Arial,Helvetica,sans-serif;color:{_SLATE}\">"
            f"<p>Hi {_esc(greeting_name) or 'there'},</p>"
            f"<p>There is no tracked activity for <strong>{_esc(label)}</strong> yet. "
            "Make sure the SmartAgile desktop agent is running.</p>"
            "<p>— SmartAgile</p></div>"
        )
        return subject, html_body, text

    def _table(title: str, rows: list[dict[str, Any]], with_count: bool = False) -> str:
        if not rows:
            return ""
        head = (
            f"<tr><th align=\"left\" style=\"padding:8px 12px;font-size:12px;text-transform:uppercase;"
            f"letter-spacing:.5px;color:{_MUTED};border-bottom:1px solid #e2e8f0\">{_esc(title)}</th>"
            f"<th align=\"right\" style=\"padding:8px 12px;font-size:12px;color:{_MUTED};"
            "border-bottom:1px solid #e2e8f0\">Time</th></tr>"
        )
        body = ""
        for r in rows:
            extra = ""
            if with_count and r.get("open_count") is not None:
                extra = f" <span style=\"color:{_MUTED};font-size:12px\">· opened {int(r['open_count'])}×</span>"
            body += (
                f"<tr><td style=\"padding:8px 12px;border-bottom:1px solid #f1f5f9\">"
                f"{_esc(r.get('name'))}{extra}</td>"
                f"<td align=\"right\" style=\"padding:8px 12px;border-bottom:1px solid #f1f5f9;"
                f"font-variant-numeric:tabular-nums;color:{_SLATE}\">{_esc(r.get('duration_human'))}</td></tr>"
            )
        return (
            "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
            "style=\"border-collapse:collapse;margin:8px 0 20px\">"
            f"{head}{body}</table>"
        )

    def _stat(lbl: str, val: str) -> str:
        return (
            "<td style=\"padding:6px 0\">"
            f"<div style=\"font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:{_MUTED}\">{_esc(lbl)}</div>"
            f"<div style=\"font-size:20px;font-weight:700;color:{_SLATE}\">{_esc(val)}</div></td>"
        )

    cats_rows = "".join(
        f"<tr><td style=\"padding:6px 12px;border-bottom:1px solid #f1f5f9;text-transform:capitalize\">"
        f"{_esc(c.get('category'))}</td>"
        f"<td align=\"right\" style=\"padding:6px 12px;border-bottom:1px solid #f1f5f9;color:{_SLATE}\">"
        f"{_esc(c.get('duration_human'))}</td></tr>"
        for c in (report.get("categories") or [])
    )
    cats_table = (
        "<table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" "
        "style=\"border-collapse:collapse;margin:8px 0 20px\">"
        f"<tr><th align=\"left\" style=\"padding:8px 12px;font-size:12px;text-transform:uppercase;"
        f"letter-spacing:.5px;color:{_MUTED};border-bottom:1px solid #e2e8f0\">Category</th>"
        f"<th align=\"right\" style=\"padding:8px 12px;font-size:12px;color:{_MUTED};"
        "border-bottom:1px solid #e2e8f0\">Time</th></tr>"
        f"{cats_rows}</table>"
        if cats_rows
        else ""
    )

    html_body = f"""\
<div style="margin:0;padding:0;background:#f1f5f9">
  <div style="max-width:640px;margin:0 auto;padding:24px 16px;font-family:Arial,Helvetica,sans-serif">
    <div style="background:linear-gradient(90deg,{_INDIGO_DARK},{_INDIGO} 50%,{_VIOLET});
                border-radius:16px 16px 0 0;padding:24px 28px;color:#fff">
      <div style="font-size:13px;opacity:.85;letter-spacing:.5px">SMARTAGILE</div>
      <div style="font-size:22px;font-weight:700;margin-top:4px">Usage report — {_esc(label)}</div>
    </div>
    <div style="background:#fff;border-radius:0 0 16px 16px;padding:24px 28px;
                box-shadow:0 10px 30px rgba(15,23,42,.08)">
      <p style="color:{_SLATE};margin-top:0">Hi {_esc(greeting_name) or 'there'}, here is your tracked activity for <strong>{_esc(label)}</strong>.</p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
        <tr>{_stat('Total tracked', s.get('total_human'))}{_stat('Focus', s.get('focus_pct'))}</tr>
        <tr>{_stat('Work', s.get('work_human'))}{_stat('Distraction', s.get('distracted_human'))}</tr>
        <tr>{_stat('App switches', str(s.get('app_switch_count')))}{_stat('Deep-work blocks', str(s.get('deep_work_segment_count')))}</tr>
      </table>
      <div style="height:1px;background:#e2e8f0;margin:20px 0"></div>
      {_table('Top apps', report.get('top_apps') or [], with_count=True)}
      {_table('Top websites', report.get('top_sites') or [])}
      {cats_table}
      <p style="color:{_MUTED};font-size:12px;margin-bottom:0">
        Sent from your SmartAgile assistant. Times reflect active (non-idle) tracked usage.
      </p>
    </div>
  </div>
</div>"""

    # Plaintext fallback.
    lines = [
        f"SmartAgile usage report — {label}",
        "",
        f"Total tracked: {s.get('total_human')}",
        f"Focus: {s.get('focus_pct')}  (work {s.get('work_human')} / distraction {s.get('distracted_human')})",
        f"App switches: {s.get('app_switch_count')}   Deep-work blocks: {s.get('deep_work_segment_count')}",
        "",
    ]
    if report.get("top_apps"):
        lines.append("Top apps:")
        for r in report["top_apps"]:
            lines.append(f"  - {r['name']}: {r['duration_human']}")
        lines.append("")
    if report.get("top_sites"):
        lines.append("Top websites:")
        for r in report["top_sites"]:
            lines.append(f"  - {r['name']}: {r['duration_human']}")
        lines.append("")
    if report.get("categories"):
        lines.append("Categories:")
        for c in report["categories"]:
            lines.append(f"  - {c['category']}: {c['duration_human']}")
        lines.append("")
    lines.append("— SmartAgile")
    text = "\n".join(lines)

    return subject, html_body, text
