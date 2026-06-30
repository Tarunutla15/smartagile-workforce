"""
Sprint analytics computed from work items + the status-change audit log + usage events.

These feed the Sprint dashboard charts:
  - velocity_history  -> Velocity bar chart (commitment vs completed)
  - burndown          -> Burndown line chart (ideal vs actual remaining points)
  - type_distribution -> Task distribution bar/pie (planned vs completed by type)
  - sprint_summary    -> stat cards (velocity, open items, completion %)
  - sprint_effort     -> focus / office hours from the desktop agent (the differentiator)
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

from django.utils import timezone

from tasks.models import Task

from .models import Sprint, SprintStatusChange

DONE = "done"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _aware(d, end_of_day: bool = False):
    """DateField -> timezone-aware datetime at start (or end) of that local day."""
    if d is None:
        return None
    t = time.max if end_of_day else time.min
    naive = datetime.combine(d, t)
    return timezone.make_aware(naive, timezone.get_current_timezone())


def _sprint_window(sprint: Sprint):
    """[since, until) datetimes covering the sprint (falls back to created..now)."""
    since = _aware(sprint.start_date) or sprint.created_at
    if sprint.end_date:
        until = _aware(sprint.end_date) + timedelta(microseconds=1)
    else:
        until = timezone.now()
    return since, until


def _items(sprint: Sprint):
    return sprint.items.all()


def _sum_points(items) -> float:
    return float(sum(float(i.story_points or 0) for i in items))


# --------------------------------------------------------------------------- #
# summary (stat cards)
# --------------------------------------------------------------------------- #
def sprint_summary(sprint: Sprint) -> dict[str, Any]:
    items = list(_items(sprint))
    total = len(items)
    done = [i for i in items if i.status == DONE]
    total_points = _sum_points(items)
    done_points = _sum_points(done)
    open_items = total - len(done)
    completion = round(len(done) / total * 100, 1) if total else 0.0
    points_completion = round(done_points / total_points * 100, 1) if total_points else 0.0
    return {
        "item_count": total,
        "done_count": len(done),
        "open_count": open_items,
        "total_points": round(total_points, 2),
        "done_points": round(done_points, 2),
        "committed_points": round(float(sprint.committed_points or 0), 2),
        "completion_pct": completion,
        "points_completion_pct": points_completion,
    }


# --------------------------------------------------------------------------- #
# velocity (commitment vs completed over recent sprints in the project)
# --------------------------------------------------------------------------- #
def velocity_history(project_id: int, *, last: int = 6) -> dict[str, Any]:
    sprints = list(
        Sprint.objects.filter(project_id=project_id)
        .exclude(status=Sprint.Status.PLANNED)
        .order_by("start_date", "id")
        .prefetch_related("items")
    )[-last:]

    labels, commitment, completed = [], [], []
    for s in sprints:
        items = list(s.items.all())
        committed = float(s.committed_points or 0) or _sum_points(items)
        done_pts = _sum_points([i for i in items if i.status == DONE])
        labels.append(s.name)
        commitment.append(round(committed, 2))
        completed.append(round(done_pts, 2))

    avg_velocity = round(sum(completed) / len(completed), 2) if completed else 0.0
    return {
        "labels": labels,
        "commitment": commitment,
        "completed": completed,
        "average_velocity": avg_velocity,
    }


# --------------------------------------------------------------------------- #
# burndown (ideal vs actual remaining points per day, from the audit log)
# --------------------------------------------------------------------------- #
def burndown(sprint: Sprint) -> dict[str, Any]:
    items = list(_items(sprint))
    committed = float(sprint.committed_points or 0) or _sum_points(items)

    start = sprint.start_date or (sprint.created_at.date() if sprint.created_at else timezone.localdate())
    end = sprint.end_date or timezone.localdate()
    if end < start:
        end = start

    days: list = []
    d = start
    while d <= end:
        days.append(d)
        d += timedelta(days=1)

    # Net done points cumulatively from the status-change log (re-opens subtract).
    changes = list(
        SprintStatusChange.objects.filter(sprint=sprint).order_by("changed_at", "id")
    )
    done_delta_by_day: dict[Any, float] = {}
    for c in changes:
        day = timezone.localtime(c.changed_at).date()
        delta = 0.0
        if c.to_status == DONE:
            delta += float(c.points_at_change or 0)
        if c.from_status == DONE:
            delta -= float(c.points_at_change or 0)
        if delta:
            done_delta_by_day[day] = done_delta_by_day.get(day, 0.0) + delta

    has_log = bool(changes)
    today = timezone.localdate()

    ideal, actual = [], []
    n = len(days)
    cumulative_done = 0.0
    for idx, day in enumerate(days):
        # ideal: straight line from committed -> 0 across the sprint
        ideal.append(round(committed * (1 - idx / (n - 1)), 2) if n > 1 else 0.0)

        cumulative_done += done_delta_by_day.get(day, 0.0)
        if day > today:
            actual.append(None)  # future days have no actual yet
        elif has_log:
            actual.append(round(max(committed - cumulative_done, 0.0), 2))
        else:
            # No audit history (legacy items): flat at remaining-from-current-done.
            current_remaining = committed - _sum_points([i for i in items if i.status == DONE])
            actual.append(round(max(current_remaining, 0.0), 2))

    return {
        "days": [d.isoformat() for d in days],
        "ideal": ideal,
        "actual": actual,
        "committed_points": round(committed, 2),
    }


# --------------------------------------------------------------------------- #
# distribution (planned vs completed by work-item type)
# --------------------------------------------------------------------------- #
def type_distribution(sprint: Sprint) -> dict[str, Any]:
    items = list(_items(sprint))
    types = [c[0] for c in Task.ITEM_TYPE_CHOICES]
    labels = [c[1] for c in Task.ITEM_TYPE_CHOICES]
    planned = {t: 0 for t in types}
    completed = {t: 0 for t in types}
    for i in items:
        t = i.item_type if i.item_type in planned else "task"
        planned[t] += 1
        if i.status == DONE:
            completed[t] += 1
    return {
        "labels": labels,
        "types": types,
        "planned": [planned[t] for t in types],
        "completed": [completed[t] for t in types],
    }


# --------------------------------------------------------------------------- #
# effort (focus / office hours from the desktop agent) - the differentiator
# --------------------------------------------------------------------------- #
def _sprint_member_ids(sprint: Sprint) -> list[int]:
    ids: set[int] = set()
    project = sprint.project
    if project.lead_id:
        ids.add(project.lead_id)
    if project.manager_id:
        ids.add(project.manager_id)
    ids.update(project.members.values_list("user_id", flat=True))
    ids.update(
        sprint.items.exclude(user_id=None).values_list("user_id", flat=True)
    )
    return sorted(ids)


def sprint_effort(sprint: Sprint) -> dict[str, Any]:
    """
    Real tracked time for sprint members over the sprint window, from UsageEvent.

    This is what generic agile tools cannot show: planned points vs *actual focus
    hours* invested in the sprint.
    """
    # Imported lazily so the sprints app has no hard dependency on smartagile import order.
    from smartagile.insights import compute_features_from_events_window

    since, until = _sprint_window(sprint)
    member_ids = _sprint_member_ids(sprint)

    per_member: list[dict[str, Any]] = []
    office_total = 0.0
    focus_total = 0.0
    for uid in member_ids:
        f = compute_features_from_events_window(uid, since_dt=since, until_dt=until)
        office_total += f.total_duration_seconds
        focus_total += f.work_duration_seconds
        per_member.append(
            {
                "user_id": uid,
                "office_seconds": f.total_duration_seconds,
                "focus_seconds": f.work_duration_seconds,
                "focus_score": f.focus_score,
            }
        )

    return {
        "since": since.isoformat() if since else None,
        "until": until.isoformat() if until else None,
        "member_count": len(member_ids),
        "office_seconds": round(office_total, 2),
        "focus_seconds": round(focus_total, 2),
        "office_hours": round(office_total / 3600, 2),
        "focus_hours": round(focus_total / 3600, 2),
        "focus_score": round(focus_total / office_total, 4) if office_total else None,
        "per_member": per_member,
    }


def sprint_item_effort(sprint: Sprint) -> dict[str, Any]:
    """
    Actual tracked time per work item, from UsageEvents attributed to that item
    (via the user's focus timer). Returns a per-item map keyed by task id plus totals.
    """
    from django.db.models import Sum

    from smartagile.insights import WORK_Q
    from smartagile.models import UsageEvent

    item_ids = list(sprint.items.values_list("id", flat=True))
    if not item_ids:
        return {"items": {}, "office_seconds": 0.0, "focus_seconds": 0.0}

    # NOTE: .order_by() clears UsageEvent's default Meta ordering, which would otherwise
    # leak into GROUP BY and split the per-item sums across rows.
    base = UsageEvent.objects.filter(work_item_id__in=item_ids).order_by()
    office_map = {
        r["work_item_id"]: float(r["s"] or 0)
        for r in base.values("work_item_id").annotate(s=Sum("duration_seconds"))
    }
    focus_map = {
        r["work_item_id"]: float(r["s"] or 0)
        for r in base.filter(WORK_Q).values("work_item_id").annotate(s=Sum("duration_seconds"))
    }

    items: dict[int, Any] = {}
    for iid in item_ids:
        office = office_map.get(iid, 0.0)
        focus = focus_map.get(iid, 0.0)
        if office or focus:
            items[iid] = {
                "office_seconds": round(office, 2),
                "focus_seconds": round(focus, 2),
                "focus_hours": round(focus / 3600, 2),
            }
    return {
        "items": items,
        "office_seconds": round(sum(office_map.values()), 2),
        "focus_seconds": round(sum(focus_map.values()), 2),
        "focus_hours": round(sum(focus_map.values()) / 3600, 2),
    }


def work_item_effort(task) -> dict[str, Any]:
    """
    Actual tracked time for a single work item: focus / office seconds from
    attributed UsageEvents plus the number of recorded focus sessions.
    """
    from django.db.models import Count, Sum

    from smartagile.insights import WORK_Q
    from smartagile.models import UsageEvent

    from .models import TaskWorkSession

    base = UsageEvent.objects.filter(work_item_id=task.pk)
    office = float(base.aggregate(s=Sum("duration_seconds"))["s"] or 0)
    focus = float(base.filter(WORK_Q).aggregate(s=Sum("duration_seconds"))["s"] or 0)
    sessions = TaskWorkSession.objects.filter(task=task).aggregate(c=Count("id"))["c"] or 0
    return {
        "office_seconds": round(office, 2),
        "focus_seconds": round(focus, 2),
        "office_hours": round(office / 3600, 2),
        "focus_hours": round(focus / 3600, 2),
        "session_count": sessions,
    }
