from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.api_testing.views import (
    AIGenerateApiTestCaseAPIView,
    ApiEndpointViewSet,
    ApiTestingProjectListCreateAPIView,
    ApiTestCaseViewSet,
    OpenAPIImportAPIView,
)

router = DefaultRouter()
router.register(r"endpoints", ApiEndpointViewSet, basename="api-endpoint")
router.register(r"test-cases", ApiTestCaseViewSet, basename="api-test-case")

urlpatterns = [
    path("projects", ApiTestingProjectListCreateAPIView.as_view(), name="api-testing-projects"),
    path("schemas/import", OpenAPIImportAPIView.as_view(), name="api-schema-import"),
    path(
        "test-cases/ai-generate",
        AIGenerateApiTestCaseAPIView.as_view(),
        name="api-test-case-ai-generate",
    ),
    path("", include(router.urls)),
]
