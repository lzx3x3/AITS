from rest_framework import serializers

from apps.api_testing.models import ApiEndpoint, ApiTestCase
from apps.common.enums import ApiSchemaSourceType


class OpenAPIImportSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=ApiSchemaSourceType.choices)
    content = serializers.CharField(required=False, allow_blank=False)
    url = serializers.URLField(required=False, allow_blank=False)
    file = serializers.FileField(required=False)
    project_id = serializers.IntegerField(min_value=1, required=False)
    new_project_name = serializers.CharField(required=False, allow_blank=False, max_length=255)
    new_project_description = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, attrs):
        source_type = attrs["source_type"]
        content = attrs.get("content")
        url = attrs.get("url")
        uploaded_file = attrs.get("file")
        project_id = attrs.get("project_id")
        new_project_name = attrs.get("new_project_name")

        if source_type in {
            ApiSchemaSourceType.JSON,
            ApiSchemaSourceType.WORD,
            ApiSchemaSourceType.PDF,
        } and not content and not uploaded_file:
            raise serializers.ValidationError(
                {"content": ["This field is required when file is not provided."]}
            )
        if source_type == ApiSchemaSourceType.URL and not url:
            raise serializers.ValidationError({"url": ["This field is required."]})
        if not project_id and not new_project_name:
            raise serializers.ValidationError(
                {"project_id": ["project_id or new_project_name is required."]}
            )
        return attrs


class AICaseGenerateSerializer(serializers.Serializer):
    endpoint_id = serializers.IntegerField(min_value=1, required=False)
    endpoint_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=False,
    )
    project_id = serializers.IntegerField(min_value=1, required=False)
    prompt = serializers.CharField(allow_blank=False)

    def validate(self, attrs):
        endpoint_id = attrs.get("endpoint_id")
        endpoint_ids = attrs.get("endpoint_ids") or []
        project_id = attrs.get("project_id")
        if endpoint_id is None and not endpoint_ids and project_id is None:
            raise serializers.ValidationError(
                {"endpoint_id": ["endpoint_id or endpoint_ids or project_id is required."]}
            )
        if endpoint_id is not None and endpoint_ids:
            endpoint_ids.append(endpoint_id)
            attrs["endpoint_ids"] = endpoint_ids
            attrs.pop("endpoint_id")
        return attrs


class ApiEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiEndpoint
        fields = ("id", "schema", "path", "method", "summary")


class ApiTestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApiTestCase
        fields = (
            "id",
            "project",
            "endpoint",
            "title",
            "description",
            "request_data",
            "assertions",
            "generated_by_ai",
            "created_at",
            "updated_at",
        )
