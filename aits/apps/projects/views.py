from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.projects.models import Environment, Project, ProjectMember
from apps.projects.serializers import (
    EnvironmentSerializer,
    ProjectCreateSerializer,
    ProjectListSerializer,
    ProjectMemberSerializer,
)


class ProjectViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """MVP：单项目；list 仅返回首个项目；不提供 create/delete。"""

    permission_classes = [AllowAny]
    queryset = Project.objects.all().order_by("id")

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return ProjectListSerializer
        return ProjectCreateSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())[:1]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class EnvironmentViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = EnvironmentSerializer
    queryset = Environment.objects.all().order_by("-id")


class ProjectMemberViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """只读成员列表；支持 ?project=<id> 过滤。"""

    permission_classes = [AllowAny]
    serializer_class = ProjectMemberSerializer
    queryset = ProjectMember.objects.select_related("user").all().order_by("id")

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get("project")
        if project_id is not None:
            qs = qs.filter(project_id=project_id)
        return qs
