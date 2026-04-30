import pytest
from rest_framework.test import APIClient

from apps.ai_core.models import LLMProviderConfig
from apps.common.enums import LlmProvider


@pytest.mark.django_db
def test_llm_provider_config_crud():
    client = APIClient(HTTP_ACCEPT="application/json")
    base_url = "/api/v1/ai/providers/"

    create_resp = client.post(
        base_url,
        {
            "name": "openai-prod",
            "provider": LlmProvider.OPENAI,
            "model_name": "gpt-4o-mini",
            "api_base": "https://api.openai.com/v1",
            "api_key_encrypted": "k1",
            "is_active": True,
        },
        format="json",
    )
    assert create_resp.status_code == 201
    provider_id = create_resp.json()["id"]

    list_resp = client.get(base_url)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    detail_resp = client.get(f"{base_url}{provider_id}/")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["name"] == "openai-prod"

    update_resp = client.patch(
        f"{base_url}{provider_id}/",
        {"is_active": False},
        format="json",
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_active"] is False
    assert LLMProviderConfig.objects.get(pk=provider_id).is_active is False

    delete_resp = client.delete(f"{base_url}{provider_id}/")
    assert delete_resp.status_code == 204
    assert not LLMProviderConfig.objects.filter(pk=provider_id).exists()


@pytest.mark.django_db
def test_llm_provider_config_validation_error_shape():
    client = APIClient(HTTP_ACCEPT="application/json")
    resp = client.post(
        "/api/v1/ai/providers/",
        {
            "name": "",
            "provider": LlmProvider.ANTHROPIC,
            "model_name": "",
            "api_key_encrypted": "",
            "is_active": True,
        },
        format="json",
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "details" in body


@pytest.mark.django_db
def test_llm_provider_list_is_deduplicated_by_provider():
    client = APIClient(HTTP_ACCEPT="application/json")
    base_url = "/api/v1/ai/providers/"

    client.post(
        base_url,
        {
            "name": "openai-old",
            "provider": LlmProvider.OPENAI,
            "model_name": "gpt-4o-mini",
            "api_key_encrypted": "k1",
            "is_active": True,
        },
        format="json",
    )
    client.post(
        base_url,
        {
            "name": "openai-new",
            "provider": LlmProvider.OPENAI,
            "model_name": "gpt-4.1-mini",
            "api_key_encrypted": "k2",
            "is_active": True,
        },
        format="json",
    )
    client.post(
        base_url,
        {
            "name": "anthropic-main",
            "provider": LlmProvider.ANTHROPIC,
            "model_name": "claude-3-5-sonnet-latest",
            "api_key_encrypted": "k3",
            "is_active": True,
        },
        format="json",
    )

    list_resp = client.get(base_url)
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) == 2

    by_provider = {item["provider"]: item for item in items}
    assert by_provider[LlmProvider.OPENAI]["name"] == "openai-new"
    assert by_provider[LlmProvider.ANTHROPIC]["name"] == "anthropic-main"
