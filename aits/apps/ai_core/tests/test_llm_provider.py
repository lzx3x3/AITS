import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.ai_core.models import LLMProviderConfig
from apps.ai_core.services.llm_provider import (
    LLMClientFactory,
    NoActiveProviderError,
    UnsupportedProviderError,
)
from apps.common.enums import LlmProvider


@pytest.mark.django_db
def test_get_active_client_raises_when_no_active_provider():
    with pytest.raises(NoActiveProviderError):
        LLMClientFactory.get_active_client()


@pytest.mark.django_db
def test_get_active_client_raises_when_api_key_empty():
    LLMProviderConfig.objects.create(
        name="openai-empty-key",
        provider=LlmProvider.OPENAI,
        model_name="gpt-4o-mini",
        api_key_encrypted="",
        is_active=True,
    )
    with pytest.raises(ImproperlyConfigured):
        LLMClientFactory.get_active_client()


@pytest.mark.django_db
def test_get_active_client_openai():
    expected_client = object()
    chat_ctor = Mock(return_value=expected_client)
    fake_module = SimpleNamespace(ChatOpenAI=chat_ctor)
    with patch.dict(sys.modules, {"langchain_openai": fake_module}):
        LLMProviderConfig.objects.create(
            name="openai-active",
            provider=LlmProvider.OPENAI,
            model_name="gpt-4o-mini",
            api_base="https://api.openai.com/v1",
            api_key_encrypted="test-openai-key",
            is_active=True,
        )

        client = LLMClientFactory.get_active_client()

        assert client is expected_client
        chat_ctor.assert_called_once_with(
            model="gpt-4o-mini",
            api_key="test-openai-key",
            base_url="https://api.openai.com/v1",
        )


@pytest.mark.django_db
def test_get_active_client_anthropic():
    expected_client = object()
    chat_ctor = Mock(return_value=expected_client)
    fake_module = SimpleNamespace(ChatAnthropic=chat_ctor)
    with patch.dict(sys.modules, {"langchain_anthropic": fake_module}):
        LLMProviderConfig.objects.create(
            name="anthropic-active",
            provider=LlmProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet-latest",
            api_base="https://api.anthropic.com",
            api_key_encrypted="test-anthropic-key",
            is_active=True,
        )

        client = LLMClientFactory.get_active_client()

        assert client is expected_client
        chat_ctor.assert_called_once_with(
            model="claude-3-5-sonnet-latest",
            api_key="test-anthropic-key",
            base_url="https://api.anthropic.com",
        )


@pytest.mark.django_db
def test_get_active_client_raises_for_unsupported_provider():
    LLMProviderConfig.objects.create(
        name="unsupported-active",
        provider=LlmProvider.OTHER,
        model_name="gpt-4o",
        api_key_encrypted="test-key",
        is_active=True,
    )
    with pytest.raises(UnsupportedProviderError):
        LLMClientFactory.get_active_client()
