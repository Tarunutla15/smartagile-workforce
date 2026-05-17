from django.contrib import admin

from .models import AuthSessionEvent, UsageDailyRollup, UsageEvent


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
