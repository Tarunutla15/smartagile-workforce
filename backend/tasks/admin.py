from django.contrib import admin

from .models import Project, ProjectMember, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "lead", "manager", "created_at")
    search_fields = ("name",)


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "user")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "user", "project", "created_at")
    list_filter = ("status",)
