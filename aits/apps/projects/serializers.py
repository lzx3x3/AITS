from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.projects.models import Environment, Project, ProjectMember

User = get_user_model()


class ProjectListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("id", "name", "status", "created_at")
        read_only_fields = fields


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("name", "description")
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "description": {"required": True, "allow_blank": True},
        }


class EnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Environment
        fields = (
            "id",
            "project",
            "name",
            "base_url",
            "variables",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_base_url(self, value: str) -> str:
        from django.core.validators import URLValidator
        from django.core.exceptions import ValidationError as DjangoValidationError

        validator = URLValidator()
        try:
            validator(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages) from e
        return value


class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)

    class Meta:
        model = ProjectMember
        fields = ("id", "project", "user", "role", "created_at", "updated_at")
        read_only_fields = ("id", "project", "user", "role", "created_at", "updated_at")
