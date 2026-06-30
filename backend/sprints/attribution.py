"""
Attribute desktop usage events to agile work items via the user's work sessions.

A ``TaskWorkSession`` records that a user was actively working on a task between
``started_at`` and ``ended_at`` (or now, if still open). When usage events are
persisted we stamp each one with the task whose session covers its timestamp, so
we can later report *actual focus time per work item / sprint*.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from .models import TaskWorkSession


def active_session(user_id: int):
    """The user's currently-open work session, or None."""
    return (
        TaskWorkSession.objects.filter(user_id=user_id, ended_at__isnull=True)
        .order_by("-started_at")
        .first()
    )


def start_session(user_id: int, task_id: int) -> TaskWorkSession:
    """Open a new session for the task, closing any previously-open one first."""
    now = timezone.now()
    TaskWorkSession.objects.filter(user_id=user_id, ended_at__isnull=True).update(ended_at=now)
    return TaskWorkSession.objects.create(user_id=user_id, task_id=task_id, started_at=now)


def stop_session(user_id: int) -> TaskWorkSession | None:
    """Close the user's open session (if any) and return it."""
    now = timezone.now()
    session = active_session(user_id)
    if session is None:
        return None
    session.ended_at = now
    session.save(update_fields=["ended_at"])
    return session


def attribute_events(user_id: int, events: list) -> int:
    """
    Set ``work_item_id`` in place on UsageEvent instances (pre-save) by matching each
    event's ``occurred_at`` to a covering work session. Returns the count attributed.

    ``events`` is the list of unsaved UsageEvent objects from the ingest batch (one user).
    """
    if not events:
        return 0

    times = [e.occurred_at for e in events if e.occurred_at is not None]
    if not times:
        return 0
    lo, hi = min(times), max(times)

    # Sessions that could overlap the batch window: started before the last event and
    # either still open or ended after the first event.
    sessions = list(
        TaskWorkSession.objects.filter(user_id=user_id, started_at__lte=hi)
        .filter(Q(ended_at__gte=lo) | Q(ended_at__isnull=True))
        .order_by("started_at")
    )
    if not sessions:
        return 0

    now = timezone.now()
    attributed = 0
    for e in events:
        t = e.occurred_at
        if t is None:
            continue
        chosen_task = None
        for s in sessions:
            end = s.ended_at or now
            if s.started_at <= t <= end:
                chosen_task = s.task_id  # later (more recent) overlap wins
        if chosen_task is not None:
            e.work_item_id = chosen_task
            attributed += 1
    return attributed
