from django.db import models

from apps.common.enums import LlmProvider
from apps.common.models import TimeStampedModel


class LLMProviderConfig(TimeStampedModel):
    name = models.CharField(max_length=128)
    provider = models.CharField(max_length=64, choices=LlmProvider.choices)
    model_name = models.CharField(max_length=128)
    api_base = models.URLField(max_length=512, blank=True)
    api_key_encrypted = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class PromptTemplate(TimeStampedModel):
    scene = models.CharField(max_length=64)
    version = models.PositiveIntegerField(default=1)
    template_text = models.TextField()
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["scene", "-version"]

    def __str__(self) -> str:
        return f"{self.scene}@{self.version}"
