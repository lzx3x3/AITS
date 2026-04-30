from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError

from apps.ai_core.services.llm_provider import (
    NoActiveProviderError,
    UnsupportedProviderError,
)
from apps.ai_core.services.graph_workflows import api_case_gen_workflow
from apps.ai_core.services.prompt_manager import PromptNotFoundError
from apps.api_testing.models import ApiEndpoint, ApiTestCase


def generate_cases(endpoint_id: int, prompt: str) -> list[ApiTestCase]:
    endpoint = (
        ApiEndpoint.objects.select_related("schema__project").filter(pk=endpoint_id).first()
    )
    if endpoint is None:
        raise ValidationError("Endpoint not found.")

    try:
        state = api_case_gen_workflow(
            endpoint_schema={
                "path": endpoint.path,
                "method": endpoint.method,
                "summary": endpoint.summary,
                "request_schema": endpoint.request_schema,
                "response_schema": endpoint.response_schema,
            },
            user_prompt=prompt,
        )
    except PromptNotFoundError as exc:
        raise ValidationError(
            "AI prompt template is missing for scene 'api_case_gen'."
        ) from exc
    except (NoActiveProviderError, UnsupportedProviderError, ImproperlyConfigured) as exc:
        raise ValidationError(f"AI provider configuration error: {exc}") from exc
    except Exception as exc:
        raise ValidationError(f"AI generation failed: {exc}") from exc
    if state.get("error"):
        raise ValidationError(state["error"])

    validated_cases = state.get("validated_cases") or []
    if not validated_cases:
        raise ValidationError("No valid API test cases generated.")

    created_cases = []
    for item in validated_cases:
        created_cases.append(
            ApiTestCase.objects.create(
                project=endpoint.schema.project,
                endpoint=endpoint,
                title=item["title"],
                description=prompt,
                request_data=item["request_data"],
                assertions=item["assertions"],
                generated_by_ai=True,
            )
        )
    return created_cases
