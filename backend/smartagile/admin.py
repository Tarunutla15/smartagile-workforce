from django.contrib import admin

from .models import AuthSessionEvent, KnowledgeChunk, UsageDailyRollup, UsageEvent


@admin.register(AuthSessionEvent)
class AuthSessionEventAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "event", "created_at")
    list_filter = ("event",)
    search_fields = ("user__email",)


@admin.register(UsageDailyRollup)
class UsageDailyRollupAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "day", "total_duration_seconds", "work_duration_seconds", "event_count", "updated_at")
    list_filter = ("day",)
    search_fields = ("user__email",)
    date_hierarchy = "day"


@admin.register(UsageEvent)
class UsageEventAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "source_type", "name", "duration_seconds", "occurred_at")
    list_filter = ("source_type",)
    search_fields = ("user__email", "name", "context")
    date_hierarchy = "occurred_at"


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "source_type", "source_id", "title", "updated_at")
    list_filter = ("source_type",)
    search_fields = ("title", "text")
    raw_id_fields = ("project", "task", "sprint")
    readonly_fields = ("content_hash", "updated_at")
