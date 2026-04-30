from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ImproperlyConfigured

from apps.ai_core.models import LLMProviderConfig
from apps.common.enums import LlmProvider


class NoActiveProviderError(ImproperlyConfigured):
    """Raised when no active LLM provider exists."""


class UnsupportedProviderError(ImproperlyConfigured):
    """Raised when provider type is unsupported."""


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    provider: str
    model_name: str
    api_base: str
    api_key: str


class LLMClientFactory:
    OPENAI_COMPATIBLE_PROVIDERS = {
        LlmProvider.OPENAI,
        LlmProvider.AZURE,
        LlmProvider.QWEN,
        LlmProvider.DEEPSEEK,
        LlmProvider.GLM,
        LlmProvider.MINIMAX,
    }

    @staticmethod
    def _build_runtime_config(record: LLMProviderConfig) -> ProviderRuntimeConfig:
        if not record.api_key_encrypted:
            raise ImproperlyConfigured(
                f"LLM provider '{record.name}' has empty api_key_encrypted."
            )
        return ProviderRuntimeConfig(
            provider=record.provider,
            model_name=record.model_name,
            api_base=record.api_base,
            api_key=record.api_key_encrypted,
        )

    @classmethod
    def get_active_client(cls):
        record = (
            LLMProviderConfig.objects.filter(is_active=True)
            .order_by("-updated_at", "-id")
            .first()
        )
        if record is None:
            raise NoActiveProviderError(
                "No active LLM provider configuration found. "
                "Create one LLMProviderConfig with is_active=True."
            )

        cfg = cls._build_runtime_config(record)
        if cfg.provider in cls.OPENAI_COMPATIBLE_PROVIDERS:
            from langchain_openai import ChatOpenAI

            kwargs = {
                "model": cfg.model_name,
                "api_key": cfg.api_key,
            }
            if cfg.api_base:
                kwargs["base_url"] = cfg.api_base
            return ChatOpenAI(**kwargs)

        if cfg.provider == LlmProvider.ANTHROPIC:
            from langchain_anthropic import ChatAnthropic

            kwargs = {
                "model": cfg.model_name,
                "api_key": cfg.api_key,
            }
            if cfg.api_base:
                kwargs["base_url"] = cfg.api_base
            return ChatAnthropic(**kwargs)

        raise UnsupportedProviderError(
            f"Unsupported LLM provider: {cfg.provider}. "
            "Supported providers: openai-compatible providers and anthropic."
        )
