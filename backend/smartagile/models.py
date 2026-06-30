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
    # Optional browser context (best-effort, only when URL capture is enabled on the agent).
    url = models.CharField(max_length=1024, blank=True, default="")
    domain = models.CharField(max_length=256, blank=True, default="", db_index=True)
    # Optional attribution to an agile work item (set at ingest from the user's active
    # work session). Lets us report actual focus time spent per task / sprint.
    work_item = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usage_events",
        db_index=True,
    )
    duration_seconds = models.FloatField()
    idle_seconds = models.FloatField(default=0)
    keystrokes = models.FloatField(default=0)
    clicks = models.FloatField(default=0)
    scrolls = models.FloatField(default=0)
    occurred_at = models.DateTimeField()
    # Agent-generated unique id per captured segment. Lets the ingest endpoint be
    # idempotent: a batch the agent retried after an unclear/transient failure cannot
    # be double-counted (see UniqueConstraint below). Blank for legacy/manual rows.
    client_event_id = models.CharField(max_length=64, blank=True, default="", db_index=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-occurred_at"], name="usage_user_occurred_desc"),
            models.Index(fields=["user", "occurred_at"], name="usage_user_occurred_asc"),
        ]
        constraints = [
            # Idempotency: at most one row per (user, client_event_id) when an id is
            # present. Empty ids (legacy/manual inserts) are exempt so they never clash.
            models.UniqueConstraint(
                fields=["user", "client_event_id"],
                condition=~models.Q(client_event_id=""),
                name="usage_user_client_event_uniq",
            ),
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


class KnowledgeChunk(models.Model):
    """Embedded text from agile content (work items, comments, sprint goals) for doc-RAG.

    The assistant retrieves these to answer questions grounded in real project discussion
    — "what blockers were raised?", "summarize the auth bug". Retrieval is cosine over
    ``embedding`` with a keyword fallback when embeddings aren't configured, and is always
    scoped to projects the asking user can see. One chunk per source row (``source_type`` +
    ``source_id``); ``content_hash`` lets the indexer skip rows whose text hasn't changed.
    """

    class SourceType(models.TextChoices):
        WORK_ITEM = "work_item", "Work item"
        COMMENT = "comment", "Comment"
        SPRINT_GOAL = "sprint_goal", "Sprint goal"

    project = models.ForeignKey(
        "tasks.Project", on_delete=models.CASCADE, related_name="knowledge_chunks"
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_id = models.PositiveIntegerField()
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="knowledge_chunks",
    )
    sprint = models.ForeignKey(
        "sprints.Sprint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knowledge_chunks",
    )
    title = models.CharField(max_length=300, blank=True, default="")
    text = models.TextField()
    embedding = models.JSONField(null=True, blank=True)
    content_hash = models.CharField(max_length=64, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id"], name="knowledge_source_uniq"
            ),
        ]
        indexes = [
            models.Index(fields=["project", "source_type"]),
        ]

    def __str__(self):
        return f"KnowledgeChunk {self.source_type}#{self.source_id} p{self.project_id}"


class Notification(models.Model):
    """A proactive nudge surfaced to a user (sprint risk, personal focus, assigned work).

    Generated by scheduled scans (``smartagile.tasks.scan_*``). ``dedupe_key`` makes
    generation idempotent — re-running a scan within the same window won't create
    duplicates — while still letting a nudge re-fire on a new day (the key embeds a date).
    """

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=40)
    severity = models.CharField(
        max_length=12, choices=Severity.choices, default=Severity.INFO
    )
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500, blank=True, default="")
    # In-app deep link (e.g. "/sprint-dashboard?project=3&sprint=12").
    link = models.CharField(max_length=300, blank=True, default="")
    # Idempotency handle, unique per user (see class docstring).
    dedupe_key = models.CharField(max_length=200)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dedupe_key"], name="notification_user_dedupe_uniq"
            ),
        ]
        indexes = [
            models.Index(fields=["user", "read_at", "-created_at"]),
        ]

    def __str__(self):
        return f"Notification u{self.user_id} {self.kind} {self.title!r}"


class AgentStatus(models.Model):
    """Liveness of a user's desktop agent, updated whenever it uploads usage.

    Because the agent uploads on a short interval while active, ``last_seen_at`` acts as a
    server-side heartbeat: the app can tell whether tracking is actually flowing (vs. an
    agent that is "running" but silently stalled / disconnected / token-expired).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_status",
    )
    # Last time the agent successfully reached the ingest endpoint (heartbeat).
    last_seen_at = models.DateTimeField(null=True, blank=True)
    # Latest activity timestamp among events in the most recent accepted batch.
    last_event_at = models.DateTimeField(null=True, blank=True)
    # Optional client build string (from the X-SmartAgile-Agent-Version header).
    agent_version = models.CharField(max_length=64, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Agent statuses"

    def __str__(self):
        return f"AgentStatus user={self.user_id} last_seen={self.last_seen_at}"
