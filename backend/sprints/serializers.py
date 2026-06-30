from django.contrib.auth import get_user_model
from rest_framework import serializers

from tasks.models import Project, Task
from tasks.serializers import UserMiniSerializer

from .models import Sprint, SprintStatusChange, WorkItemComment

User = get_user_model()


class SprintSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    # Lightweight rollups for the sprint list / header (computed from prefetched items).
    item_count = serializers.SerializerMethodField()
    done_count = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    done_points = serializers.SerializerMethodField()

    class Meta:
        model = Sprint
        fields = [
            "id",
            "project",
            "project_name",
            "name",
            "goal",
            "start_date",
            "end_date",
            "status",
            "committed_points",
            "created_at",
            "started_at",
            "completed_at",
            "item_count",
            "done_count",
            "total_points",
            "done_points",
        ]
        read_only_fields = [
            "id",
            "project_name",
            "committed_points",
            "created_at",
            "started_at",
            "completed_at",
            "item_count",
            "done_count",
            "total_points",
            "done_points",
        ]

    def _items(self, obj):
        return list(obj.items.all())

    def get_item_count(self, obj):
        return len(self._items(obj))

    def get_done_count(self, obj):
        return sum(1 for i in self._items(obj) if i.status == "done")

    def get_total_points(self, obj):
        return round(sum(float(i.story_points or 0) for i in self._items(obj)), 2)

    def get_done_points(self, obj):
        return round(
            sum(float(i.story_points or 0) for i in self._items(obj) if i.status == "done"), 2
        )


class WorkItemSerializer(serializers.ModelSerializer):
    """A sprint/backlog work item (backed by ``tasks.Task``)."""

    project_name = serializers.CharField(source="project.name", read_only=True, allow_null=True)
    status_category = serializers.CharField(read_only=True)
    assignee = UserMiniSerializer(source="user", read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="user",
        allow_null=True,
        required=False,
        write_only=True,
    )
    sprint = serializers.PrimaryKeyRelatedField(
        queryset=Sprint.objects.all(), allow_null=True, required=False
    )
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "status_category",
            "item_type",
            "priority",
            "story_points",
            "rank",
            "sprint",
            "project",
            "project_name",
            "assignee",
            "assignee_id",
            "created_by",
            "created_at",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "status_category",
            "project_name",
            "assignee",
            "created_by",
            "created_at",
            "started_at",
            "completed_at",
        ]


class StatusChangeSerializer(serializers.ModelSerializer):
    """One entry in a work item's status-history timeline."""

    changed_by = UserMiniSerializer(read_only=True)

    class Meta:
        model = SprintStatusChange
        fields = [
            "id",
            "from_status",
            "to_status",
            "points_at_change",
            "changed_by",
            "changed_at",
        ]


class WorkItemCommentSerializer(serializers.ModelSerializer):
    author = UserMiniSerializer(read_only=True)

    class Meta:
        model = WorkItemComment
        fields = ["id", "author", "body", "created_at"]
        read_only_fields = ["id", "author", "created_at"]
