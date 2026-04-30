from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.api_testing.models import ApiEndpoint, ApiSchema, ApiTestCase
from apps.api_testing.services.openapi_parser import import_schema, parse_endpoints
from apps.common.enums import ApiSchemaSourceType, ProjectStatus
from apps.projects.models import Project

MINIMAL_OPENAPI = """
{
  "openapi": "3.0.3",
  "info": {"title": "Pet API"},
  "paths": {
    "/pets": {
      "get": {
        "summary": "List pets",
        "responses": {"200": {"description": "ok"}}
      }
    }
  }
}
"""

MINIMAL_SWAGGER2 = """
{
  "swagger": "2.0",
  "info": {"title": "Legacy API"},
  "paths": {
    "/pets": {
      "post": {
        "summary": "Create pet",
        "parameters": [
          {
            "in": "body",
            "name": "body",
            "schema": {"type": "object", "properties": {"name": {"type": "string"}}}
          }
        ],
        "responses": {"200": {"description": "ok"}}
      }
    }
  }
}
"""

MINIMAL_POSTMAN_COLLECTION = """
{
  "info": {
    "name": "Postman Demo",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Create User",
      "request": {
        "method": "POST",
        "header": [{"key": "Authorization", "value": "Bearer token"}],
        "body": {
          "mode": "raw",
          "raw": "{\\"mobile_phone\\": \\"13800001111\\", \\"type\\": 1}"
        },
        "url": {
          "raw": "{{baseUrl}}/member/register",
          "path": ["member", "register"]
        }
      }
    }
  ]
}
"""


@pytest.mark.django_db
class TestOpenAPIParserService:
    def test_import_schema_and_parse_endpoints(self):
        schema = import_schema(ApiSchemaSourceType.JSON, MINIMAL_OPENAPI)
        assert schema.name == "Pet API"
        endpoint_count = parse_endpoints(schema.id)
        assert endpoint_count == 1
        endpoint = ApiEndpoint.objects.get(schema=schema)
        assert endpoint.path == "/pets"
        assert endpoint.method == "GET"

    def test_import_schema_rejects_invalid_openapi(self):
        with pytest.raises(Exception):
            import_schema(ApiSchemaSourceType.JSON, '{"openapi":"2.0","paths":{}}')

    def test_import_schema_supports_word_content(self):
        word_like_content = (
            "OpenAPI document in word export\n"
            "```json\n"
            '{"openapi":"3.0.3","info":{"title":"Word API"},"paths":{"/w":{"get":{"responses":{"200":{"description":"ok"}}}}}}\n'
            "```"
        )
        schema = import_schema(ApiSchemaSourceType.WORD, word_like_content)
        assert schema.name == "Word API"

    def test_import_schema_supports_pdf_content(self):
        pdf_like_content = (
            "PDF extracted text...\n"
            '{"openapi":"3.0.3","info":{"title":"PDF API"},"paths":{"/p":{"post":{"responses":{"200":{"description":"ok"}}}}}}'
        )
        schema = import_schema(ApiSchemaSourceType.PDF, pdf_like_content)
        assert schema.name == "PDF API"

    def test_import_schema_supports_swagger2(self):
        schema = import_schema(ApiSchemaSourceType.JSON, MINIMAL_SWAGGER2)
        endpoint_count = parse_endpoints(schema.id)
        assert endpoint_count == 1
        endpoint = ApiEndpoint.objects.get(schema=schema)
        assert endpoint.method == "POST"
        assert endpoint.request_schema["content"]["application/json"]["schema"]["type"] == "object"

    def test_import_schema_supports_postman_collection(self):
        schema = import_schema(ApiSchemaSourceType.JSON, MINIMAL_POSTMAN_COLLECTION)
        endpoint_count = parse_endpoints(schema.id)
        assert endpoint_count == 1
        endpoint = ApiEndpoint.objects.get(schema=schema)
        assert endpoint.path == "/member/register"
        assert endpoint.method == "POST"
        assert endpoint.request_schema["content"]["application/json"]["schema"]["type"] == "object"

    def test_parse_endpoints_deduplicates_same_path_method(self):
        project = Project.objects.create(name="P", description="d", status=ProjectStatus.ACTIVE)
        schema = ApiSchema.objects.create(
            project=project,
            name="Dedup Schema",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={
                "openapi": "3.0.3",
                "paths": {
                    "/pets": {
                        "get": {"summary": "list"},
                        "GET": {"summary": "list duplicated by method case"},
                    }
                },
            },
        )
        endpoint_count = parse_endpoints(schema.id)
        assert endpoint_count == 1
        assert ApiEndpoint.objects.filter(schema=schema, path="/pets", method="GET").count() == 1


@pytest.mark.django_db
class TestPhase5API:
    def test_openapi_import_api(self):
        client = APIClient()
        resp = client.post(
            "/api/v1/api-testing/schemas/import",
            {
                "source_type": "json",
                "content": MINIMAL_OPENAPI,
                "new_project_name": "Import Project 1",
            },
            format="json",
        )
        assert resp.status_code == 201
        body = resp.data
        assert body["endpoint_count"] == 1
        assert len(body["endpoint_ids"]) == 1
        assert ApiSchema.objects.filter(pk=body["schema_id"]).exists()

    def test_openapi_import_api_with_json_file_upload(self):
        client = APIClient()
        uploaded = SimpleUploadedFile(
            "openapi.json",
            MINIMAL_OPENAPI.encode("utf-8"),
            content_type="application/json",
        )
        resp = client.post(
            "/api/v1/api-testing/schemas/import",
            {"source_type": "json", "file": uploaded, "new_project_name": "Import Project 2"},
            format="multipart",
        )
        assert resp.status_code == 201
        body = resp.data
        assert body["endpoint_count"] == 1
        assert len(body["endpoint_ids"]) == 1

    def test_openapi_import_api_with_markdown_file_upload(self):
        client = APIClient()
        markdown_content = (
            "# API 文档\n"
            "以下是 OpenAPI JSON:\n"
            "```json\n"
            + MINIMAL_OPENAPI
            + "\n```"
        )
        uploaded = SimpleUploadedFile(
            "api-doc.md",
            markdown_content.encode("utf-8"),
            content_type="text/markdown",
        )
        resp = client.post(
            "/api/v1/api-testing/schemas/import",
            {"source_type": "json", "file": uploaded, "new_project_name": "Import Project 3"},
            format="multipart",
        )
        assert resp.status_code == 201
        body = resp.data
        assert body["endpoint_count"] == 1

    def test_endpoint_list_api(self):
        project = Project.objects.create(name="P", description="d", status=ProjectStatus.ACTIVE)
        schema = ApiSchema.objects.create(
            project=project,
            name="S1",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        endpoint = ApiEndpoint.objects.create(schema=schema, path="/x", method="GET", summary="x")
        client = APIClient()
        resp = client.get(f"/api/v1/api-testing/endpoints/?schema_id={schema.id}")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["id"] == endpoint.id

    def test_project_list_and_create_api(self):
        client = APIClient()
        create_resp = client.post(
            "/api/v1/api-testing/projects",
            {"name": "P-From-ApiTesting", "description": "d"},
            format="json",
        )
        assert create_resp.status_code == 201
        list_resp = client.get("/api/v1/api-testing/projects")
        assert list_resp.status_code == 200
        assert any(item["name"] == "P-From-ApiTesting" for item in list_resp.data)

    def test_endpoint_list_api_deduplicates_imported_endpoints(self):
        project = Project.objects.create(name="P2", description="d2", status=ProjectStatus.ACTIVE)
        schema1 = ApiSchema.objects.create(
            project=project,
            name="S1",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        schema2 = ApiSchema.objects.create(
            project=project,
            name="S2",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        ApiEndpoint.objects.create(schema=schema1, path="/x", method="GET", summary="old")
        latest = ApiEndpoint.objects.create(schema=schema2, path="/x", method="GET", summary="new")

        client = APIClient()
        resp = client.get("/api/v1/api-testing/endpoints/")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["id"] == latest.id

    def test_endpoint_list_api_filters_by_project(self):
        project1 = Project.objects.create(name="P1", description="d1", status=ProjectStatus.ACTIVE)
        project2 = Project.objects.create(name="P2", description="d2", status=ProjectStatus.ACTIVE)
        schema1 = ApiSchema.objects.create(
            project=project1,
            name="S1",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        schema2 = ApiSchema.objects.create(
            project=project2,
            name="S2",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        e1 = ApiEndpoint.objects.create(schema=schema1, path="/p1", method="GET", summary="p1")
        ApiEndpoint.objects.create(schema=schema2, path="/p2", method="GET", summary="p2")
        client = APIClient()
        resp = client.get(f"/api/v1/api-testing/endpoints/?project_id={project1.id}")
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]["id"] == e1.id

    @patch("apps.api_testing.views.generate_cases")
    def test_ai_generate_api(self, mocked_generate_cases):
        project = Project.objects.create(name="P", description="d", status=ProjectStatus.ACTIVE)
        schema = ApiSchema.objects.create(
            project=project,
            name="S1",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        endpoint = ApiEndpoint.objects.create(schema=schema, path="/x", method="POST", summary="x")
        created = ApiTestCase.objects.create(
            project=project,
            endpoint=endpoint,
            title="AI case",
            description="p",
            request_data={"a": 1},
            assertions=[{"status_code": 200}],
            generated_by_ai=True,
        )
        mocked_generate_cases.return_value = [created]

        client = APIClient()
        resp = client.post(
            "/api/v1/api-testing/test-cases/ai-generate",
            {"endpoint_id": endpoint.id, "prompt": "generate"},
            format="json",
        )
        assert resp.status_code == 201
        body = resp.data
        assert body["id"] == created.id
        assert body["generated_by_ai"] is True

    @patch("apps.api_testing.views.generate_cases")
    def test_ai_generate_api_returns_json_error_on_generation_failure(
        self, mocked_generate_cases
    ):
        project = Project.objects.create(name="P", description="d", status=ProjectStatus.ACTIVE)
        schema = ApiSchema.objects.create(
            project=project,
            name="S1",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        endpoint = ApiEndpoint.objects.create(schema=schema, path="/x", method="POST", summary="x")
        mocked_generate_cases.side_effect = Exception("mocked llm failure")

        client = APIClient(HTTP_ACCEPT="application/json")
        resp = client.post(
            "/api/v1/api-testing/test-cases/ai-generate",
            {"endpoint_id": endpoint.id, "prompt": "generate"},
            format="json",
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body["code"] == "BAD_REQUEST"

    @patch("apps.api_testing.views.generate_cases")
    def test_ai_generate_api_batch_by_endpoint_ids(self, mocked_generate_cases):
        project = Project.objects.create(name="P", description="d", status=ProjectStatus.ACTIVE)
        schema = ApiSchema.objects.create(
            project=project,
            name="S1",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        endpoint1 = ApiEndpoint.objects.create(schema=schema, path="/x1", method="POST", summary="x1")
        endpoint2 = ApiEndpoint.objects.create(schema=schema, path="/x2", method="GET", summary="x2")
        case1 = ApiTestCase.objects.create(
            project=project,
            endpoint=endpoint1,
            title="AI case 1",
            description="p",
            request_data={"a": 1},
            assertions=[{"status_code": 200}],
            generated_by_ai=True,
        )
        case2 = ApiTestCase.objects.create(
            project=project,
            endpoint=endpoint2,
            title="AI case 2",
            description="p",
            request_data={"b": 2},
            assertions=[{"status_code": 200}],
            generated_by_ai=True,
        )
        mocked_generate_cases.side_effect = [[case1], [case2]]

        client = APIClient()
        resp = client.post(
            "/api/v1/api-testing/test-cases/ai-generate",
            {"endpoint_ids": [endpoint1.id, endpoint2.id], "prompt": "generate"},
            format="json",
        )
        assert resp.status_code == 201
        body = resp.data
        assert body["created_count"] == 2
        assert len(body["cases"]) == 2

    @patch("apps.api_testing.views.generate_cases")
    def test_ai_generate_api_batch_by_project_id(self, mocked_generate_cases):
        project = Project.objects.create(name="P", description="d", status=ProjectStatus.ACTIVE)
        schema = ApiSchema.objects.create(
            project=project,
            name="S1",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        endpoint1 = ApiEndpoint.objects.create(schema=schema, path="/x1", method="POST", summary="x1")
        endpoint2 = ApiEndpoint.objects.create(schema=schema, path="/x2", method="GET", summary="x2")
        case1 = ApiTestCase.objects.create(
            project=project,
            endpoint=endpoint1,
            title="AI case 1",
            description="p",
            request_data={"a": 1},
            assertions=[{"status_code": 200}],
            generated_by_ai=True,
        )
        case2 = ApiTestCase.objects.create(
            project=project,
            endpoint=endpoint2,
            title="AI case 2",
            description="p",
            request_data={"b": 2},
            assertions=[{"status_code": 200}],
            generated_by_ai=True,
        )
        mocked_generate_cases.side_effect = [[case1], [case2]]

        client = APIClient()
        resp = client.post(
            "/api/v1/api-testing/test-cases/ai-generate",
            {"project_id": project.id, "prompt": "generate"},
            format="json",
        )
        assert resp.status_code == 201
        body = resp.data
        assert body["created_count"] == 2
        assert len(body["cases"]) == 2

    def test_test_case_list_and_detail(self):
        project = Project.objects.create(name="P", description="d", status=ProjectStatus.ACTIVE)
        schema = ApiSchema.objects.create(
            project=project,
            name="S1",
            source_type=ApiSchemaSourceType.JSON,
            raw_content={"openapi": "3.0.3", "paths": {}},
        )
        endpoint = ApiEndpoint.objects.create(schema=schema, path="/x", method="GET", summary="x")
        case = ApiTestCase.objects.create(
            project=project,
            endpoint=endpoint,
            title="C1",
            description="d",
            request_data={"foo": "bar"},
            assertions=[{"status_code": 200}],
            generated_by_ai=False,
        )
        client = APIClient()
        list_resp = client.get(f"/api/v1/api-testing/test-cases/?endpoint={endpoint.id}")
        assert list_resp.status_code == 200
        assert len(list_resp.data) == 1
        detail_resp = client.get(f"/api/v1/api-testing/test-cases/{case.id}/")
        assert detail_resp.status_code == 200
        assert detail_resp.data["request_data"]["foo"] == "bar"

