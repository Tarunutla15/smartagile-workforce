from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Project, ProjectMember, Task

User = get_user_model()


class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]


class TaskSerializer(serializers.ModelSerializer):
    """Tasks for the signed-in employee."""

    project_name = serializers.CharField(source="project.name", read_only=True, allow_null=True)
    task_origin = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "status",
            "created_at",
            "project",
            "project_name",
            "task_origin",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "project",
            "project_name",
            "task_origin",
        ]

    def get_task_origin(self, obj):
        request = self.context.get("request")
        uid = request.user.pk if request and request.user.is_authenticated else None
        if not uid:
            return "personal"
        if obj.created_by_id is None:
            return "personal"
        if obj.created_by_id == uid:
            return "personal"
        return "assigned"


class ProjectEmployeeSerializer(serializers.ModelSerializer):
    """Projects the current user is on (member, lead, or manager)."""

    lead = UserMiniSerializer(read_only=True)
    manager = UserMiniSerializer(read_only=True)
    your_role = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["id", "name", "description", "created_at", "lead", "manager", "your_role"]

    def get_your_role(self, obj):
        request = self.context.get("request")
        uid = request.user.pk if request and request.user.is_authenticated else None
        if not uid:
            return None
        roles = []
        if obj.lead_id == uid:
            roles.append("lead")
        if obj.manager_id == uid:
            roles.append("manager")
        if obj.members.filter(user_id=uid).exists():
            roles.append("member")
        return ", ".join(dict.fromkeys(roles)) if roles else "member"


class AdminTaskSerializer(serializers.ModelSerializer):
    assignee = UserMiniSerializer(source="user", read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="user",
        allow_null=True,
        required=False,
    )
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        allow_null=True,
        required=False,
    )
    project_name = serializers.CharField(source="project.name", read_only=True, allow_null=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "status",
            "created_at",
            "project",
            "project_name",
            "assignee_id",
            "assignee",
            "created_by",
        ]
        read_only_fields = ["id", "created_at", "assignee", "project_name", "created_by"]

    def create(self, validated_data):
        task = super().create(validated_data)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            task.created_by_id = request.user.pk
            task.save(update_fields=["created_by_id"])
        return task


class ProjectAdminSerializer(serializers.ModelSerializer):
    lead = UserMiniSerializer(read_only=True)
    manager = UserMiniSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    lead_id = serializers.IntegerField(write_only=True, allow_null=True, required=False)
    manager_id = serializers.IntegerField(write_only=True, allow_null=True, required=False)
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list,
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "created_at",
            "lead",
            "manager",
            "members",
            "lead_id",
            "manager_id",
            "member_ids",
        ]
        read_only_fields = ["id", "created_at", "lead", "manager", "members"]

    def get_members(self, obj):
        qs = obj.members.select_related("user").all()
        return UserMiniSerializer([m.user for m in qs], many=True).data

    def _sync_members(self, project, member_ids, lead_id, manager_id):
        ids = set(member_ids or [])
        if lead_id:
            ids.add(lead_id)
        if manager_id:
            ids.add(manager_id)
        ProjectMember.objects.filter(project=project).exclude(user_id__in=ids).delete()
        for uid in ids:
            if User.objects.filter(pk=uid).exists():
                ProjectMember.objects.get_or_create(project=project, user_id=uid)

    def create(self, validated_data):
        request = self.context["request"]
        member_ids = validated_data.pop("member_ids", []) or []
        lead_id = validated_data.pop("lead_id", None)
        manager_id = validated_data.pop("manager_id", None)
        uid = request.user.pk
        name = validated_data.pop("name")
        description = validated_data.pop("description", "")
        if validated_data:
            raise serializers.ValidationError(f"Unexpected fields: {list(validated_data.keys())}")
        project = Project.objects.create(
            name=name,
            description=description or "",
            created_by_id=uid,
            lead_id=lead_id,
            manager_id=manager_id,
        )
        self._sync_members(project, member_ids, lead_id, manager_id)
        return project

    def update(self, instance, validated_data):
        member_ids_provided = "member_ids" in validated_data
        member_ids = validated_data.pop("member_ids", None) if member_ids_provided else None
        lead_id = validated_data.pop("lead_id", serializers.empty)
        manager_id = validated_data.pop("manager_id", serializers.empty)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if lead_id is not serializers.empty:
            instance.lead_id = lead_id
        if manager_id is not serializers.empty:
            instance.manager_id = manager_id
        instance.save()
        if member_ids_provided:
            self._sync_members(
                instance,
                member_ids or [],
                instance.lead_id,
                instance.manager_id,
            )
        else:
            self._sync_members(
                instance,
                list(instance.members.values_list("user_id", flat=True)),
                instance.lead_id,
                instance.manager_id,
            )
        return instance
