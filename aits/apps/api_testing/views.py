from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from apps.api_testing.models import ApiEndpoint, ApiTestCase
from apps.api_testing.serializers import (
    AICaseGenerateSerializer,
    ApiEndpointSerializer,
    ApiTestCaseSerializer,
    OpenAPIImportSerializer,
)
from apps.api_testing.services.case_generator import generate_cases
from apps.api_testing.services.openapi_parser import (
    import_schema,
    parse_endpoints,
    _read_openapi_from_uploaded_file,
)
from apps.common.enums import ProjectStatus
from apps.projects.models import Project
from apps.projects.serializers import ProjectListSerializer


class OpenAPIImportAPIView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        serializer = OpenAPIImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        project_id = payload.get("project_id")
        new_project_name = payload.get("new_project_name")
        new_project_description = payload.get("new_project_description", "")
        if project_id:
            project = Project.objects.filter(pk=project_id).first()
            if project is None:
                raise ValidationError("Project not found.")
        else:
            project = Project.objects.create(
                name=new_project_name,
                description=new_project_description,
                status=ProjectStatus.ACTIVE,
            )
        uploaded_file = payload.get("file")
        source = payload["source_type"]
        if uploaded_file is not None:
            filename = (getattr(uploaded_file, "name", "") or "").lower()
            if filename.endswith(".pdf"):
                source = "pdf"
            elif filename.endswith(".docx") or filename.endswith(".md") or filename.endswith(".txt"):
                source = "word"
            elif filename.endswith(".json"):
                source = "json"
        if uploaded_file is not None:
            content_or_url = _read_openapi_from_uploaded_file(
                source, uploaded_file
            )
        else:
            content_or_url = payload.get("content") or payload.get("url") or ""
        schema = import_schema(
            source=source,
            content_or_url=content_or_url,
            project=project,
        )
        endpoint_count = parse_endpoints(schema.id)
        endpoint_ids = list(
            ApiEndpoint.objects.filter(schema_id=schema.id)
            .order_by("id")
            .values_list("id", flat=True)
        )
        return Response(
            {
                "schema_id": schema.id,
                "endpoint_count": endpoint_count,
                "endpoint_ids": endpoint_ids,
            },
            status=status.HTTP_201_CREATED,
        )


class AIGenerateApiTestCaseAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AICaseGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        endpoint_ids = serializer.validated_data.get("endpoint_ids")
        if not endpoint_ids and serializer.validated_data.get("project_id"):
            endpoint_ids = list(
                ApiEndpoint.objects.filter(schema__project_id=serializer.validated_data["project_id"])
                .order_by("id")
                .values_list("id", flat=True)
            )
            if not endpoint_ids:
                raise ValidationError("No endpoints found for selected project.")
        if not endpoint_ids:
            endpoint_ids = [serializer.validated_data["endpoint_id"]]

        all_cases = []
        try:
            for endpoint_id in endpoint_ids:
                cases = generate_cases(
                    endpoint_id=endpoint_id,
                    prompt=serializer.validated_data["prompt"],
                )
                all_cases.extend(cases)
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError(f"AI generation failed: {exc}") from exc
        if len(all_cases) == 1:
            data = ApiTestCaseSerializer(all_cases[0]).data
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(
            {
                "created_count": len(all_cases),
                "cases": ApiTestCaseSerializer(all_cases, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ApiEndpointViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = ApiEndpointSerializer
    queryset = ApiEndpoint.objects.select_related("schema").all().order_by("-id")

    def get_queryset(self):
        queryset = super().get_queryset()
        schema_id = self.request.query_params.get("schema_id")
        project_id = self.request.query_params.get("project_id")
        if schema_id:
            queryset = queryset.filter(schema_id=schema_id)
        if project_id:
            queryset = queryset.filter(schema__project_id=project_id)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        unique_items = []
        seen_keys = set()
        for item in queryset:
            key = (item.path, item.method.upper())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            unique_items.append(item)
        serializer = self.get_serializer(unique_items, many=True)
        return Response(serializer.data)


class ApiTestingProjectListCreateAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        projects = Project.objects.all().order_by("-id")
        return Response(ProjectListSerializer(projects, many=True).data)

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        description = str(request.data.get("description") or "")
        if not name:
            raise ValidationError({"name": ["This field is required."]})
        project = Project.objects.create(
            name=name,
            description=description,
            status=ProjectStatus.ACTIVE,
        )
        return Response(ProjectListSerializer(project).data, status=status.HTTP_201_CREATED)


class ApiTestCaseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = ApiTestCaseSerializer
    queryset = ApiTestCase.objects.select_related("endpoint", "project").all().order_by("-id")

    def get_queryset(self):
        queryset = super().get_queryset()
        endpoint_id = self.request.query_params.get("endpoint")
        project_id = self.request.query_params.get("project")
        if endpoint_id:
            queryset = queryset.filter(endpoint_id=endpoint_id)
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

