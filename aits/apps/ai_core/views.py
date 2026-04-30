from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.ai_core.models import LLMProviderConfig, PromptTemplate
from apps.ai_core.serializers import (
    LLMProviderConfigSerializer,
    PromptTemplateSerializer,
)


class LLMProviderConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = LLMProviderConfigSerializer
    queryset = LLMProviderConfig.objects.all().order_by("-id")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        unique_items = []
        seen_provider = set()
        for item in queryset:
            if item.provider in seen_provider:
                continue
            seen_provider.add(item.provider)
            unique_items.append(item)
        serializer = self.get_serializer(unique_items, many=True)
        return Response(serializer.data)


class PromptTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PromptTemplateSerializer
    queryset = PromptTemplate.objects.all().order_by("-id")

    def get_queryset(self):
        queryset = super().get_queryset()
        scene = self.request.query_params.get("scene")
        if scene:
            queryset = queryset.filter(scene=scene)
        return queryset

