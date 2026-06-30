"""
Team ("group") analytics for the Group dashboard.

A "group" in SmartAgile is a project's team: its lead, manager, members, and the
assignees of its tasks. Everything here is aggregated from real ``UsageEvent`` rows
(desktop agent) plus task / sprint state, so the Group dashboard reflects live data
instead of mock arrays.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from tasks.models import Project, Task

from .models import Sprint

User = get_user_model()

DONE = "done"
WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def group_member_ids(project) -> list[int]:
    """Lead + manager + members + assignees of the project's tasks."""
    ids: set[int] = set()
    if project.lead_id:
        ids.add(project.lead_id)
    if project.manager_id:
        ids.add(project.manager_id)
    ids.update(project.members.values_list("user_id", flat=True))
    ids.update(
        Task.objects.filter(project=project)
        .exclude(user_id=None)
        .values_list("user_id", flat=True)
    )
    return sorted(ids)


def group_summary(project, *, days: int = 14) -> dict[str, Any]:
    # Imported lazily to keep the sprints app import order independent of smartagile.
    from smartagile.insights import WORK_Q
    from smartagile.models import UsageEvent

    now = timezone.now()
    since = now - timedelta(days=days)
    member_ids = group_member_ids(project)
    users = {u.id: u for u in User.objects.filter(pk__in=member_ids)}

    # NOTE: .order_by() clears UsageEvent's default Meta ordering so it can't leak
    # into GROUP BY and split the per-key sums across rows.
    base = (
        UsageEvent.objects.filter(
            user_id__in=member_ids, occurred_at__gte=since, occurred_at__lte=now
        ).order_by()
        if member_ids
        else UsageEvent.objects.none()
    )

    office_by_user = {
        r["user_id"]: float(r["s"] or 0)
        for r in base.values("user_id").annotate(s=Sum("duration_seconds"))
    }
    focus_by_user = {
        r["user_id"]: float(r["s"] or 0)
        for r in base.filter(WORK_Q).values("user_id").annotate(s=Sum("duration_seconds"))
    }

    members: list[dict[str, Any]] = []
    for uid in member_ids:
        office = office_by_user.get(uid, 0.0)
        focus = focus_by_user.get(uid, 0.0)
        u = users.get(uid)
        members.append(
            {
                "user_id": uid,
                "username": u.username if u else f"user {uid}",
                "office_hours": round(office / 3600, 2),
                "focus_hours": round(focus / 3600, 2),
                "productivity_pct": round(focus / office * 100, 1) if office else 0.0,
            }
        )
    members.sort(key=lambda m: m["focus_hours"], reverse=True)

    # Per-day office / focus seconds.
    office_by_day = {
        r["d"]: float(r["s"] or 0)
        for r in base.annotate(d=TruncDate("occurred_at"))
        .values("d")
        .annotate(s=Sum("duration_seconds"))
    }
    focus_by_day = {
        r["d"]: float(r["s"] or 0)
        for r in base.filter(WORK_Q)
        .annotate(d=TruncDate("occurred_at"))
        .values("d")
        .annotate(s=Sum("duration_seconds"))
    }

    day_list: list = []
    d = since.date()
    end = now.date()
    while d <= end:
        day_list.append(d)
        d += timedelta(days=1)

    team_trend = {
        "labels": [dd.strftime("%b %d") for dd in day_list],
        "focus_hours": [round(focus_by_day.get(dd, 0.0) / 3600, 2) for dd in day_list],
        "office_hours": [round(office_by_day.get(dd, 0.0) / 3600, 2) for dd in day_list],
    }

    wd_office = [0.0] * 7
    wd_focus = [0.0] * 7
    for dd in day_list:
        wd = dd.weekday()
        wd_office[wd] += office_by_day.get(dd, 0.0)
        wd_focus[wd] += focus_by_day.get(dd, 0.0)
    time_tracking = {
        "labels": WEEKDAY_LABELS,
        "office_hours": [round(x / 3600, 2) for x in wd_office],
        "focus_hours": [round(x / 3600, 2) for x in wd_focus],
    }

    # Per-sprint completion (project status).
    sprints = list(
        Sprint.objects.filter(project=project).order_by("start_date", "id").prefetch_related("items")
    )
    ps_labels: list[str] = []
    ps_completion: list[float] = []
    for s in sprints:
        items = list(s.items.all())
        total = len(items)
        done = sum(1 for i in items if i.status == DONE)
        ps_labels.append(s.name)
        ps_completion.append(round(done / total * 100, 1) if total else 0.0)

    # Task distribution across the whole project.
    task_qs = Task.objects.filter(project=project)
    todo = task_qs.filter(status="todo").count()
    in_progress = task_qs.filter(status="inProgress").count()
    done_count = task_qs.filter(status="done").count()
    task_distribution = {
        "labels": ["To Do", "In Progress", "Done"],
        "values": [todo, in_progress, done_count],
    }

    total_office = sum(office_by_user.values())
    total_focus = sum(focus_by_user.values())

    return {
        "group": {
            "id": project.id,
            "name": project.name,
            "member_count": len(member_ids),
        },
        "range": {"since": since.isoformat(), "until": now.isoformat(), "days": days},
        "members": members,
        "time_tracking": time_tracking,
        "team_trend": team_trend,
        "project_status": {"labels": ps_labels, "completion": ps_completion},
        "task_distribution": task_distribution,
        "totals": {
            "focus_hours": round(total_focus / 3600, 2),
            "office_hours": round(total_office / 3600, 2),
            "productivity_pct": round(total_focus / total_office * 100, 1) if total_office else 0.0,
            "open_tasks": todo + in_progress,
            "done_tasks": done_count,
            "member_count": len(member_ids),
        },
    }


def org_summary(*, days: int = 14, top_n: int = 10) -> dict[str, Any]:
    """
    Org-wide live summary for the admin Overview: headline counts, top performers,
    per-project completion, weekday time-tracking, daily focus trend, task mix.
    Aggregated across all users / projects / tasks.
    """
    from smartagile.insights import WORK_Q
    from smartagile.models import UsageEvent

    now = timezone.now()
    since = now - timedelta(days=days)

    base = UsageEvent.objects.filter(
        occurred_at__gte=since, occurred_at__lte=now
    ).order_by()

    # Per-user focus/office (top performers).
    office_by_user = {
        r["user_id"]: float(r["s"] or 0)
        for r in base.values("user_id").annotate(s=Sum("duration_seconds"))
    }
    focus_by_user = {
        r["user_id"]: float(r["s"] or 0)
        for r in base.filter(WORK_Q).values("user_id").annotate(s=Sum("duration_seconds"))
    }
    user_ids = list(office_by_user.keys())
    users = {u.id: u for u in User.objects.filter(pk__in=user_ids)}
    members = []
    for uid in user_ids:
        office = office_by_user.get(uid, 0.0)
        focus = focus_by_user.get(uid, 0.0)
        u = users.get(uid)
        members.append(
            {
                "user_id": uid,
                "username": u.username if u else f"user {uid}",
                "office_hours": round(office / 3600, 2),
                "focus_hours": round(focus / 3600, 2),
                "productivity_pct": round(focus / office * 100, 1) if office else 0.0,
            }
        )
    members.sort(key=lambda m: m["focus_hours"], reverse=True)
    members = members[:top_n]

    # Per-day office / focus.
    office_by_day = {
        r["d"]: float(r["s"] or 0)
        for r in base.annotate(d=TruncDate("occurred_at"))
        .values("d")
        .annotate(s=Sum("duration_seconds"))
    }
    focus_by_day = {
        r["d"]: float(r["s"] or 0)
        for r in base.filter(WORK_Q)
        .annotate(d=TruncDate("occurred_at"))
        .values("d")
        .annotate(s=Sum("duration_seconds"))
    }
    day_list: list = []
    d = since.date()
    end = now.date()
    while d <= end:
        day_list.append(d)
        d += timedelta(days=1)

    team_trend = {
        "labels": [dd.strftime("%b %d") for dd in day_list],
        "focus_hours": [round(focus_by_day.get(dd, 0.0) / 3600, 2) for dd in day_list],
        "office_hours": [round(office_by_day.get(dd, 0.0) / 3600, 2) for dd in day_list],
    }
    wd_office = [0.0] * 7
    for dd in day_list:
        wd_office[dd.weekday()] += office_by_day.get(dd, 0.0)
    time_tracking = {
        "labels": WEEKDAY_LABELS,
        "office_hours": [round(x / 3600, 2) for x in wd_office],
    }

    # Per-project completion (done tasks / total tasks), top by task volume.
    project_status = _project_completion(top_n=top_n)

    # Org-wide task distribution.
    todo = Task.objects.filter(status="todo").count()
    in_progress = Task.objects.filter(status="inProgress").count()
    done_count = Task.objects.filter(status="done").count()
    task_distribution = {
        "labels": ["To Do", "In Progress", "Done"],
        "values": [todo, in_progress, done_count],
    }

    total_office = sum(office_by_user.values())
    total_focus = sum(focus_by_user.values())

    return {
        "range": {"since": since.isoformat(), "until": now.isoformat(), "days": days},
        "members": members,
        "time_tracking": time_tracking,
        "team_trend": team_trend,
        "project_status": project_status,
        "task_distribution": task_distribution,
        "totals": {
            "people": User.objects.count(),
            "projects": Project.objects.count(),
            "active_people": len(user_ids),
            "focus_hours": round(total_focus / 3600, 2),
            "office_hours": round(total_office / 3600, 2),
            "productivity_pct": round(total_focus / total_office * 100, 1) if total_office else 0.0,
            "open_tasks": todo + in_progress,
            "done_tasks": done_count,
        },
    }


def _project_completion(*, top_n: int = 10) -> dict[str, Any]:
    """Completion % (done/total tasks) per project, ordered by task volume."""
    from django.db.models import Count, Q

    rows = (
        Project.objects.annotate(
            total=Count("tasks"),
            done=Count("tasks", filter=Q(tasks__status="done")),
        )
        .filter(total__gt=0)
        .order_by("-total")[:top_n]
    )
    labels, completion = [], []
    for p in rows:
        labels.append(p.name)
        completion.append(round(p.done / p.total * 100, 1) if p.total else 0.0)
    return {"labels": labels, "completion": completion}
