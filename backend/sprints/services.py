"""
Sprint domain services: access checks and the single place that mutates a work
item's status so the audit log (``SprintStatusChange``) stays consistent.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from tasks.models import Project, Task

from .models import Sprint, SprintStatusChange

DONE_STATUS = "done"
IN_PROGRESS_STATUS = "inProgress"


def visible_project_ids(user) -> set[int]:
    """Projects the user can see: as lead, manager, or member (admins see all)."""
    if getattr(user, "role", None) == "admin":
        return set(Project.objects.values_list("id", flat=True))
    return set(
        Project.objects.filter(
            Q(lead_id=user.pk) | Q(manager_id=user.pk) | Q(members__user_id=user.pk)
        )
        .values_list("id", flat=True)
        .distinct()
    )


def can_view_project(user, project_id: int) -> bool:
    return project_id in visible_project_ids(user)


def manageable_project_ids(user) -> set[int]:
    """Projects the user can manage/lead (admins manage all)."""
    if getattr(user, "role", None) == "admin":
        return set(Project.objects.values_list("id", flat=True))
    return set(
        Project.objects.filter(Q(lead_id=user.pk) | Q(manager_id=user.pk))
        .values_list("id", flat=True)
        .distinct()
    )


def assistant_role(user) -> str:
    """
    Effective role for the assistant's perspective control:
      - "admin"    : org-wide visibility, may pick any project.
      - "manager"  : leads/manages ≥1 project — team & project views for those.
      - "employee" : own work only (no team/project perspective).
    """
    if getattr(user, "role", None) == "admin":
        return "admin"
    if manageable_project_ids(user):
        return "manager"
    return "employee"


def effective_assistant_scope(user, scope: str | None) -> str:
    """
    Clamp a requested perspective to what the user is allowed to use.
    Employees are always restricted to their own work ("me"); only managers
    and admins may use the "team"/"project" perspectives.
    """
    scope = (scope or "me").strip().lower()
    if scope not in ("me", "team", "project"):
        scope = "me"
    if scope in ("team", "project") and assistant_role(user) == "employee":
        return "me"
    return scope


def can_manage_project(user, project: Project | int) -> bool:
    """Lead, manager, or admin may manage sprints (create/start/complete, plan backlog)."""
    if getattr(user, "role", None) == "admin":
        return True
    pid = project.pk if isinstance(project, Project) else project
    return Project.objects.filter(
        Q(pk=pid) & (Q(lead_id=user.pk) | Q(manager_id=user.pk))
    ).exists()


def apply_status_change(task: Task, new_status: str, *, changed_by=None) -> Task:
    """
    Move a task to ``new_status``, maintaining started/completed timestamps and
    writing a ``SprintStatusChange`` row. No-op (no log) if status is unchanged.
    """
    old_status = task.status
    if new_status == old_status:
        return task

    now = timezone.now()
    task.status = new_status

    # Maintain lifecycle timestamps for cycle-time analytics.
    if new_status == IN_PROGRESS_STATUS and task.started_at is None:
        task.started_at = now
    if new_status == DONE_STATUS:
        task.completed_at = now
    elif old_status == DONE_STATUS:
        # Re-opened: clear completion so burndown reflects it again.
        task.completed_at = None

    task.save(update_fields=["status", "started_at", "completed_at"])

    SprintStatusChange.objects.create(
        sprint=task.sprint,
        task=task,
        from_status=old_status or "",
        to_status=new_status,
        points_at_change=float(task.story_points or 0),
        changed_by=changed_by,
    )
    return task


def start_sprint(sprint: Sprint, *, by=None) -> Sprint:
    """Activate a sprint and snapshot its committed points (sum of item estimates)."""
    committed = sum(
        float(p or 0)
        for p in sprint.items.values_list("story_points", flat=True)
    )
    sprint.committed_points = committed
    sprint.status = Sprint.Status.ACTIVE
    if sprint.started_at is None:
        sprint.started_at = timezone.now()
    if sprint.start_date is None:
        sprint.start_date = timezone.localdate()
    sprint.save(update_fields=["committed_points", "status", "started_at", "start_date"])
    return sprint


def complete_sprint(sprint: Sprint, *, move_incomplete_to=None, by=None) -> Sprint:
    """
    Mark a sprint completed. Optionally move unfinished items to another sprint
    (``move_incomplete_to``) or back to the backlog (pass ``"backlog"``).
    """
    sprint.status = Sprint.Status.COMPLETED
    sprint.completed_at = timezone.now()
    sprint.save(update_fields=["status", "completed_at"])

    if move_incomplete_to is not None:
        incomplete = sprint.items.exclude(status=DONE_STATUS)
        if move_incomplete_to == "backlog":
            incomplete.update(sprint=None)
        elif isinstance(move_incomplete_to, Sprint):
            incomplete.update(sprint=move_incomplete_to)
    return sprint
