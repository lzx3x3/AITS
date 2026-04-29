from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.projects.views import EnvironmentViewSet

router = DefaultRouter()
router.register(r"", EnvironmentViewSet, basename="environment")

urlpatterns = [
    path("", include(router.urls)),
]
