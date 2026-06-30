from django.conf import settings
from django.db import models


class Sprint(models.Model):
    """
    A time-boxed iteration on a project (Zoho Sprints-style).

    Work items (``tasks.Task``) point here via ``Task.sprint``; items with
    ``sprint = NULL`` form the project backlog.
    """

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    project = models.ForeignKey(
        "tasks.Project",
        on_delete=models.CASCADE,
        related_name="sprints",
    )
    name = models.CharField(max_length=200)
    goal = models.TextField(blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNED)
    # Snapshot of committed story points, captured when the sprint is started.
    # Used as the burndown starting line and the velocity "commitment" bar.
    committed_points = models.FloatField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sprints_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date", "-id"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "-start_date"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.project_id})"


class SprintStatusChange(models.Model):
    """
    Audit log of work-item status transitions inside a sprint.

    This is the source of truth for the burndown / cumulative-flow charts and for
    cycle-time analytics: we never have to guess *when* an item became done.
    """

    sprint = models.ForeignKey(
        Sprint,
        on_delete=models.CASCADE,
        related_name="status_changes",
        null=True,
        blank=True,
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="status_changes",
    )
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20)
    # Story points on the item at the moment of the change (items can be re-estimated).
    points_at_change = models.FloatField(default=0)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sprint_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at", "id"]
        indexes = [
            models.Index(fields=["sprint", "changed_at"]),
            models.Index(fields=["task", "changed_at"]),
        ]

    def __str__(self):
        return f"#{self.task_id} {self.from_status}->{self.to_status} @ {self.changed_at}"


class TaskWorkSession(models.Model):
    """
    A period during which a user was actively working on a task ("focus timer").

    UsageEvents whose ``occurred_at`` falls inside an (open or closed) session are
    attributed to the session's task at ingest time, giving us *actual* focus time
    per work item. At most one open session (``ended_at IS NULL``) per user.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_work_sessions",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="work_sessions",
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["user", "ended_at"]),
        ]

    def __str__(self):
        state = "open" if self.ended_at is None else "closed"
        return f"WorkSession u{self.user_id} task{self.task_id} ({state})"

    @property
    def duration_seconds(self) -> float:
        from django.utils import timezone

        end = self.ended_at or timezone.now()
        return max(0.0, (end - self.started_at).total_seconds())


class WorkItemComment(models.Model):
    """A comment on a work item (the item-detail discussion feed)."""

    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="work_item_comments",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["task", "created_at"]),
        ]

    def __str__(self):
        return f"Comment u{self.author_id} on task{self.task_id}"
