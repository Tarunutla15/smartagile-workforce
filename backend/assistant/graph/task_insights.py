"""
Read-only task analytics for the "task_insights" agent.

Distinct from the action-oriented `tasks` agent (create/delete/update/rename): this
module never mutates anything. It aggregates the user's Task rows into a compact,
JSON-serializable snapshot the assistant can reason over — status mix, completion rate,
per-project distribution, aging (stale) pending work, recently created/completed items,
and a "what should I work on next" suggestion.

The Task model only has title/status/project/created_at (no due date / completion
timestamp), so "aging" is derived from created_at, and recency uses created_at.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone

_STATUSES = ("todo", "inProgress", "done")
_PENDING = ("todo", "inProgress")


def _age_days(created_at, now) -> int | None:
    if not created_at:
        return None
    try:
        return max(0, int((now - created_at).total_seconds() // 86400))
    except Exception:
        return None


def _task_row(t, now) -> dict[str, Any]:
    created = getattr(t, "created_at", None)
    return {
        "id": t.pk,
        "title": t.title,
        "status": t.status,
        "project_id": t.project_id,
        "project_name": t.project.name if t.project_id else None,
        "created_at": created.isoformat() if created else None,
        "age_days": _age_days(created, now),
    }


def build_task_insights(user) -> dict[str, Any]:
    """
    Aggregate a full read-only task snapshot for one user. JSON-serializable.
    """
    from tasks.models import Task

    now = timezone.now()
    today = timezone.localtime(now).date()
    week_monday = today.fromordinal(today.toordinal() - today.weekday())

    qs = list(
        Task.objects.filter(user_id=user.pk)
        .select_related("project")
        .order_by("-created_at", "-id")
    )
    rows = [_task_row(t, now) for t in qs]

    status_counts = {s: 0 for s in _STATUSES}
    for r in rows:
        st = r["status"] if r["status"] in status_counts else "todo"
        status_counts[st] += 1

    total = len(rows)
    done = status_counts["done"]
    pending_rows = [r for r in rows if r["status"] in _PENDING]
    in_progress_rows = [r for r in rows if r["status"] == "inProgress"]
    todo_rows = [r for r in rows if r["status"] == "todo"]

    completion_pct = round((done / total) * 100) if total else 0

    # Per-project distribution (pending only — that's what needs planning).
    by_project: dict[str, dict[str, Any]] = {}
    for r in pending_rows:
        key = r["project_name"] or "No project"
        slot = by_project.setdefault(key, {"project": key, "pending": 0, "in_progress": 0, "todo": 0})
        slot["pending"] += 1
        if r["status"] == "inProgress":
            slot["in_progress"] += 1
        else:
            slot["todo"] += 1
    projects = sorted(by_project.values(), key=lambda x: -x["pending"])[:8]

    # Aging: oldest pending first (most stale work that may be stuck).
    aging = sorted(
        pending_rows,
        key=lambda r: (r["age_days"] is None, -(r["age_days"] or 0)),
    )[:5]

    created_today = sum(
        1 for t in qs if getattr(t, "created_at", None) and timezone.localtime(t.created_at).date() == today
    )
    created_this_week = sum(
        1 for t in qs if getattr(t, "created_at", None) and timezone.localtime(t.created_at).date() >= week_monday
    )

    # "What to work on next": in-progress items take priority (finish what's started),
    # then the oldest todo. Mirrors common agile WIP-limit advice.
    if in_progress_rows:
        next_up = in_progress_rows[:3]
        next_reason = "in_progress"
    else:
        next_up = sorted(
            todo_rows, key=lambda r: (r["age_days"] is None, -(r["age_days"] or 0))
        )[:3]
        next_reason = "oldest_todo"

    recently_done = [r for r in rows if r["status"] == "done"][:5]

    return {
        "kind": "task_insights",
        "generated_at": now.isoformat(),
        "totals": {
            "total": total,
            "todo": status_counts["todo"],
            "in_progress": status_counts["inProgress"],
            "done": done,
            "pending": len(pending_rows),
            "completion_pct": completion_pct,
        },
        "created_today": created_today,
        "created_this_week": created_this_week,
        "by_project": projects,
        "aging_pending": aging,
        "next_up": {"reason": next_reason, "tasks": next_up},
        "recently_done": recently_done,
        "has_tasks": total > 0,
    }


def format_task_insights_markdown(ctx: dict[str, Any]) -> str:
    """Deterministic fallback summary (used when no LLM is configured)."""
    if not ctx.get("has_tasks"):
        return (
            "You don't have any tasks in SmartAgile yet. "
            "Add some from the Tasks section or ask me to create one."
        )
    t = ctx.get("totals") or {}
    lines = [
        f"You have **{t.get('total', 0)}** tasks — "
        f"**{t.get('todo', 0)}** to do, **{t.get('in_progress', 0)}** in progress, "
        f"**{t.get('done', 0)}** done (**{t.get('completion_pct', 0)}%** complete).",
    ]

    next_up = (ctx.get("next_up") or {}).get("tasks") or []
    if next_up:
        reason = (ctx.get("next_up") or {}).get("reason")
        header = (
            "Finish what's in progress first:"
            if reason == "in_progress"
            else "Suggested next (your oldest open tasks):"
        )
        lines.append("\n**What to work on next** — " + header)
        for r in next_up:
            age = f" · open {r['age_days']}d" if r.get("age_days") is not None else ""
            lines.append(f"- **{r.get('title')}** (ID {r.get('id')}, {r.get('status')}){age}")

    aging = ctx.get("aging_pending") or []
    if aging and (ctx.get("next_up") or {}).get("reason") != "oldest_todo":
        lines.append("\n**Aging / possibly stuck:**")
        for r in aging[:3]:
            age = f" · open {r['age_days']}d" if r.get("age_days") is not None else ""
            lines.append(f"- **{r.get('title')}** (ID {r.get('id')}, {r.get('status')}){age}")

    projects = ctx.get("by_project") or []
    if len(projects) > 1:
        lines.append("\n**Pending by project:** " + ", ".join(
            f"{p['project']} ({p['pending']})" for p in projects[:5]
        ))

    return "\n".join(lines)
