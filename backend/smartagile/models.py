from django.conf import settings
from django.db import models


class AuthSessionEvent(models.Model):
    """One row per web login or logout (app session), for counts and history."""

    class EventType(models.TextChoices):
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="auth_events",
    )
    event = models.CharField(max_length=16, choices=EventType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} {self.event} @ {self.created_at}"


class UsageEvent(models.Model):
    """Single-table storage for desktop-reported app/browser usage (replaces per-user SQL tables)."""

    class SourceType(models.TextChoices):
        APPLICATION = "application", "Application"
        BROWSER = "browser", "Browser"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_events",
    )
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    name = models.CharField(max_length=512)
    context = models.CharField(max_length=1024, blank=True, default="")
    category = models.CharField(max_length=128, blank=True, default="")
    duration_seconds = models.FloatField()
    idle_seconds = models.FloatField(default=0)
    keystrokes = models.FloatField(default=0)
    clicks = models.FloatField(default=0)
    scrolls = models.FloatField(default=0)
    occurred_at = models.DateTimeField()

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-occurred_at"], name="usage_user_occurred_desc"),
            models.Index(fields=["user", "occurred_at"], name="usage_user_occurred_asc"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.source_type} {self.name} @ {self.occurred_at}"


class UsageDailyRollup(models.Model):
    """Per-user daily aggregates (filled by Celery ETL from UsageEvent)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_rollups",
    )
    day = models.DateField()
    total_duration_seconds = models.FloatField(default=0)
    work_duration_seconds = models.FloatField(default=0)
    event_count = models.PositiveIntegerField(default=0)
    distracted_duration_seconds = models.FloatField(default=0)
    app_switch_count = models.PositiveIntegerField(default=0)
    deep_work_segment_count = models.PositiveIntegerField(default=0)
    focus_score = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "day"], name="usage_rollup_user_day_uniq"),
        ]
        ordering = ["-day", "-id"]

    def __str__(self):
        return f"{self.user_id} {self.day}"


class AssistantChatSession(models.Model):
    """User-scoped assistant chat; messages persist for history and UI sync."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_chat_sessions",
    )
    title = models.CharField(max_length=200, default="New chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
        ]

    def __str__(self):
        return f"AssistantChat {self.user_id} {self.title!r}"


class AssistantChatMessage(models.Model):
    """One user or assistant turn; assistant may include structured JSON in result_json."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    session = models.ForeignKey(
        AssistantChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    result_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
        ]

    def __str__(self):
        return f"{self.role} #{self.session_id} @ {self.created_at}"


class UserMemory(models.Model):
    """
    Long-term semantic memory extracted from chats.

    `embedding` stores an OpenAI-compatible embedding vector (list[float]) or null when
    embeddings are unavailable; retrieval falls back to keyword heuristics in that case.
    """

    class MemoryType(models.TextChoices):
        HABIT = "habit", "Habit"
        PREFERENCE = "preference", "Preference"
        CONSTRAINT = "constraint", "Constraint"
        PROJECT_CONTEXT = "project_context", "Project context"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memories",
    )
    type = models.CharField(max_length=32, choices=MemoryType.choices, default=MemoryType.OTHER)
    content = models.TextField()
    embedding = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=64, default="assistant_chat")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(default=0)

    class Meta:
        ordering = ["-last_used_at", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "-last_used_at"]),
            models.Index(fields=["user", "type", "-created_at"]),
        ]

    def __str__(self):
        return f"Memory {self.user_id} {self.type}: {self.content[:48]!r}"
