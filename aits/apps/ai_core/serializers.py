from rest_framework import serializers

from apps.ai_core.models import LLMProviderConfig, PromptTemplate


class LLMProviderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMProviderConfig
        fields = (
            "id",
            "name",
            "provider",
            "model_name",
            "api_base",
            "api_key_encrypted",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class PromptTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptTemplate
        fields = (
            "id",
            "scene",
            "version",
            "template_text",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
