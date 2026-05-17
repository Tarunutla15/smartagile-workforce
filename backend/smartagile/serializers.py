from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AssistantChatMessage, AssistantChatSession, AuthSessionEvent

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
