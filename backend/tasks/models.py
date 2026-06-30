from django.conf import settings
from django.db import models


class Project(models.Model):
    """Org-level project: team, lead, manager (admin-managed)."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_created",
    )
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_led",
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_managed",
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )

    class Meta:
        unique_together = [["project", "user"]]

    def __str__(self):
        return f"{self.user_id} in {self.project_id}"


class Task(models.Model):
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('inProgress', 'In Progress'),
        ('done', 'Done'),
    ]

    # Agile work-item metadata (used by the `sprints` app; all optional so existing
    # task flows keep working unchanged). Maps each board status to a metric category.
    STATUS_CATEGORY = {
        'todo': 'todo',
        'inProgress': 'in_progress',
        'done': 'done',
    }

    ITEM_TYPE_CHOICES = [
        ('story', 'Story'),
        ('task', 'Task'),
        ('bug', 'Bug'),
        ('chore', 'Chore'),
        ('spike', 'Spike'),
    ]

    PRIORITY_CHOICES = [
        ('none', 'None'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    title = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_created",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # --- Agile fields (Zoho Sprints-style) ---
    sprint = models.ForeignKey(
        "sprints.Sprint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
    )
    item_type = models.CharField(max_length=12, choices=ITEM_TYPE_CHOICES, default="task")
    priority = models.CharField(max_length=8, choices=PRIORITY_CHOICES, default="medium")
    story_points = models.FloatField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    rank = models.FloatField(default=0, help_text="Manual ordering within backlog / board column.")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.title

    @property
    def status_category(self):
        return self.STATUS_CATEGORY.get(self.status, "todo")

    @property
    def is_done(self):
        return self.status == "done"
