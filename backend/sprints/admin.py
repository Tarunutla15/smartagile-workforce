from django.contrib import admin

from .models import Sprint, SprintStatusChange, WorkItemComment


@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "project", "status", "start_date", "end_date", "committed_points")
    list_filter = ("status",)
    search_fields = ("name", "goal")
    autocomplete_fields = ("project", "created_by")


@admin.register(SprintStatusChange)
class SprintStatusChangeAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "sprint", "from_status", "to_status", "points_at_change", "changed_at")
    list_filter = ("to_status",)
    search_fields = ("task__title",)


@admin.register(WorkItemComment)
class WorkItemCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "author", "created_at")
    search_fields = ("body", "task__title")
    raw_id_fields = ("task", "author")
