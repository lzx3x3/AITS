from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.projects.views import ProjectMemberViewSet

router = DefaultRouter()
router.register(r"", ProjectMemberViewSet, basename="projectmember")

urlpatterns = [
    path("", include(router.urls)),
]
