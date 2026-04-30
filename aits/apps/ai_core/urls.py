from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.ai_core.views import LLMProviderConfigViewSet, PromptTemplateViewSet

router = DefaultRouter()
router.register(r"providers", LLMProviderConfigViewSet, basename="llm-provider")
router.register(r"prompts", PromptTemplateViewSet, basename="prompt-template")

urlpatterns = [
    path("", include(router.urls)),
]
