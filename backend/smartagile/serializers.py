from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AssistantChatMessage,
    AssistantChatSession,
    AuthSessionEvent,
    Notification,
)

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "password", "role", "profile_photo"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = validated_data.get("role", "employee")
        user = User(**validated_data)
        user.set_password(password)
        user.is_staff = role == "admin"
        user.is_superuser = user.is_staff
        user.save()
        return user


class AuthSessionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthSessionEvent
        fields = ["id", "event", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "kind",
            "severity",
            "title",
            "body",
            "link",
            "read",
            "created_at",
        ]

    def get_read(self, obj) -> bool:
        return obj.read_at is not None


class SessionUserSerializer(serializers.ModelSerializer):
    """User fields exposed to the client (no password)."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "profile_photo"]


class AssistantChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantChatMessage
        fields = ["id", "role", "content", "result_json", "created_at"]


class AssistantChatSessionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantChatSession
        fields = ["id", "title", "created_at", "updated_at"]


class AssistantChatSessionDetailSerializer(serializers.ModelSerializer):
    messages = AssistantChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantChatSession
        fields = ["id", "title", "created_at", "updated_at", "messages"]


class AssistantUserMessageInSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=16000, trim_whitespace=True, allow_blank=False)
    # Optional perspective from the assistant UI: who/what the user is asking about.
    scope = serializers.ChoiceField(
        choices=["auto", "me", "team", "project"],
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    # Optional project the user has chosen to chat about (team/project perspective).
    project_id = serializers.IntegerField(required=False, allow_null=True)
