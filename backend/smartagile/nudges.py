"""Proactive nudges: scan agile + usage data and create Notification rows.

Pure functions (no Celery here) so they're trivially unit-testable; the Celery wrappers
in ``tasks.py`` just call these on a schedule. Every nudge is created through ``_emit``,
which is idempotent per ``(user, dedupe_key)`` — re-running a scan in the same window is a
no-op, but the date embedded in each key lets a still-relevant nudge re-fire the next day.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Notification

logger = logging.getLogger(__name__)

# Tunables.
SPRINT_ENDING_DAYS = 2          # warn when a sprint ends within this many days
STUCK_IN_PROGRESS_DAYS = 3      # an item in progress longer than this is "stuck"
FOCUS_DIP_THRESHOLD = 40.0      # focus_score below this (with real activity) → nudge
FOCUS_MIN_TRACKED_SECONDS = 1800  # ignore days with <30 min tracked (too little signal)


def _emit(user_id, *, kind, severity, title, body, link, dedupe_key) -> bool:
    """Create a notification if one with this dedupe_key doesn't already exist.

    Returns True when a new row was created. Never raises (a single bad nudge must not
    abort a whole scan).
    """
    try:
        _, created = Notification.objects.get_or_create(
            user_id=user_id,
            dedupe_key=dedupe_key,
            defaults={
                "kind": kind,
                "severity": severity,
                "title": title[:200],
                "body": body[:500],
                "link": link[:300],
            },
        )
        return created
    except Exception:
        logger.exception("nudge emit failed user_id=%s kind=%s", user_id, kind)
        return False


def _sprint_link(project_id, sprint_id) -> str:
    return f"/sprint-dashboard?project={project_id}&sprint={sprint_id}"


def _project_managers(project) -> set[int]:
    """Lead + manager ids for a project (the people who own sprint health)."""
    out = set()
    if project.lead_id:
        out.add(project.lead_id)
    if project.manager_id:
        out.add(project.manager_id)
    return out


def scan_sprint_risks() -> int:
    """Notify project leads/managers about at-risk active sprints. Returns nudges created."""
    from sprints.models import Sprint
    from tasks.models import Task

    today = timezone.localdate()
    created = 0
    active = Sprint.objects.filter(status=Sprint.Status.ACTIVE).select_related("project")

    for sprint in active:
        project = sprint.project
        if project is None:
            continue
        recipients = _project_managers(project)
        if not recipients:
            continue

        items = Task.objects.filter(sprint_id=sprint.pk)
        incomplete = items.exclude(status="done")
        incomplete_count = incomplete.count()
        link = _sprint_link(project.pk, sprint.pk)

        # 1) Sprint ending soon with unfinished work.
        if sprint.end_date and incomplete_count > 0:
            days_left = (sprint.end_date - today).days
            if 0 <= days_left <= SPRINT_ENDING_DAYS:
                when = "today" if days_left == 0 else f"in {days_left} day(s)"
                for uid in recipients:
                    created += _emit(
                        uid,
                        kind="sprint_ending",
                        severity="warning",
                        title=f"“{sprint.name}” ends {when}",
                        body=f"{incomplete_count} item(s) still open in {project.name}.",
                        link=link,
                        dedupe_key=f"sprint_ending:{sprint.pk}:{today.isoformat()}",
                    )

        # 2) Items stuck in progress.
        stuck_before = timezone.now() - timedelta(days=STUCK_IN_PROGRESS_DAYS)
        stuck_count = incomplete.filter(
            status="inProgress",
        ).filter(
            Q(started_at__lt=stuck_before)
            | (Q(started_at__isnull=True) & Q(created_at__lt=stuck_before))
        ).count()
        if stuck_count > 0:
            for uid in recipients:
                created += _emit(
                    uid,
                    kind="items_stuck",
                    severity="warning",
                    title=f"{stuck_count} item(s) stuck in progress",
                    body=(
                        f"In “{sprint.name}” ({project.name}), {stuck_count} item(s) have been "
                        f"in progress over {STUCK_IN_PROGRESS_DAYS} days."
                    ),
                    link=link,
                    dedupe_key=f"items_stuck:{sprint.pk}:{today.isoformat()}",
                )

    logger.info("scan_sprint_risks: created %s nudge(s)", created)
    return created


def scan_personal_nudges() -> int:
    """Notify individuals about their own at-risk work + focus dips. Returns nudges created."""
    from sprints.models import Sprint
    from tasks.models import Task

    from .models import UsageDailyRollup

    today = timezone.localdate()
    created = 0

    # 1) "Your items are due this sprint" — assignee-scoped.
    active = Sprint.objects.filter(
        status=Sprint.Status.ACTIVE,
        end_date__isnull=False,
        end_date__gte=today,
        end_date__lte=today + timedelta(days=SPRINT_ENDING_DAYS),
    ).select_related("project")

    for sprint in active:
        project = sprint.project
        if project is None:
            continue
        link = _sprint_link(project.pk, sprint.pk)
        # Count each assignee's still-open items in this ending sprint.
        rows = (
            Task.objects.filter(sprint_id=sprint.pk, user_id__isnull=False)
            .exclude(status="done")
            .values_list("user_id", flat=True)
        )
        counts: dict[int, int] = {}
        for uid in rows:
            counts[uid] = counts.get(uid, 0) + 1
        days_left = (sprint.end_date - today).days
        when = "today" if days_left == 0 else f"in {days_left} day(s)"
        for uid, n in counts.items():
            created += _emit(
                uid,
                kind="my_items_due",
                severity="info",
                title=f"You have {n} open item(s) in “{sprint.name}”",
                body=f"This sprint ends {when}. Wrap up your remaining work in {project.name}.",
                link=link,
                dedupe_key=f"my_items_due:{sprint.pk}:{today.isoformat()}",
            )

    # 2) Focus dip — based on yesterday's rollup.
    yesterday = today - timedelta(days=1)
    dips = UsageDailyRollup.objects.filter(
        day=yesterday,
        focus_score__isnull=False,
        focus_score__lt=FOCUS_DIP_THRESHOLD,
        total_duration_seconds__gte=FOCUS_MIN_TRACKED_SECONDS,
    )
    for r in dips:
        created += _emit(
            r.user_id,
            kind="focus_dip",
            severity="info",
            title="Your focus dipped yesterday",
            body=(
                f"Focus score was {round(r.focus_score)}%. Ask the assistant for tips, or "
                "plan a deep-work block today."
            ),
            link="/employee/dashboard",
            dedupe_key=f"focus_dip:{yesterday.isoformat()}",
        )

    logger.info("scan_personal_nudges: created %s nudge(s)", created)
    return created
