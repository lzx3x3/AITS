from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.test import APIClient

from apps.common.enums import MemberRole, ProjectStatus
from apps.common.exceptions import custom_exception_handler
from apps.projects.models import Environment, Project, ProjectMember
from apps.projects.serializers import EnvironmentSerializer, ProjectCreateSerializer

User = get_user_model()


@pytest.mark.django_db
class TestProjectCreateSerializer:
    def test_missing_name_invalid(self):
        s = ProjectCreateSerializer(data={"description": "x"})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_missing_description_invalid(self):
        s = ProjectCreateSerializer(data={"name": "P1"})
        assert not s.is_valid()
        assert "description" in s.errors

    def test_valid_with_blank_description(self):
        s = ProjectCreateSerializer(data={"name": "P1", "description": ""})
        assert s.is_valid(), s.errors


@pytest.mark.django_db
class TestEnvironmentSerializer:
    def test_invalid_base_url(self):
        project = Project.objects.create(
            name="P",
            description="d",
            status=ProjectStatus.ACTIVE,
        )
        s = EnvironmentSerializer(
            data={
                "project": project.pk,
                "name": "dev",
                "base_url": "not-a-valid-url",
                "variables": {},
            }
        )
        assert not s.is_valid()
        assert "base_url" in s.errors


@pytest.mark.django_db
class TestProjectAPI:
    def test_list_empty(self):
        client = APIClient()
        r = client.get("/api/v1/projects/")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_returns_at_most_one(self):
        Project.objects.create(name="A", description="", status=ProjectStatus.ACTIVE)
        Project.objects.create(name="B", description="", status=ProjectStatus.ACTIVE)
        client = APIClient()
        r = client.get("/api/v1/projects/")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["name"] == "A"

    def test_retrieve_and_update(self):
        p = Project.objects.create(name="P1", description="d", status=ProjectStatus.ACTIVE)
        client = APIClient()
        r = client.get(f"/api/v1/projects/{p.pk}/")
        assert r.status_code == 200
        assert r.json()["name"] == "P1"
        r2 = client.patch(
            f"/api/v1/projects/{p.pk}/",
            {"name": "P1x", "description": "d2"},
            format="json",
        )
        assert r2.status_code == 200
        p.refresh_from_db()
        assert p.name == "P1x"


@pytest.mark.django_db
class TestEnvironmentAPI:
    def test_crud_and_invalid_url(self):
        p = Project.objects.create(name="P", description="", status=ProjectStatus.ACTIVE)
        client = APIClient()
        r = client.post(
            "/api/v1/environments/",
            {
                "project": p.pk,
                "name": "dev",
                "base_url": "https://example.com",
                "variables": {"k": "v"},
            },
            format="json",
        )
        assert r.status_code == 201
        env_id = r.json()["id"]
        r_bad = client.post(
            "/api/v1/environments/",
            {
                "project": p.pk,
                "name": "bad",
                "base_url": "not-url",
                "variables": {},
            },
            format="json",
        )
        assert r_bad.status_code == 400
        body = r_bad.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert "base_url" in body["details"]

        r_list = client.get("/api/v1/environments/")
        assert r_list.status_code == 200
        assert len(r_list.json()) >= 1

        r_get = client.get(f"/api/v1/environments/{env_id}/")
        assert r_get.status_code == 200
        r_patch = client.patch(
            f"/api/v1/environments/{env_id}/",
            {"name": "dev2"},
            format="json",
        )
        assert r_patch.status_code == 200
        r_del = client.delete(f"/api/v1/environments/{env_id}/")
        assert r_del.status_code == 204
        assert not Environment.objects.filter(pk=env_id).exists()


@pytest.mark.django_db
class TestProjectMemberAPI:
    def test_list_with_user_and_filter(self):
        p = Project.objects.create(name="P", description="", status=ProjectStatus.ACTIVE)
        u = User.objects.create_user(username="u1", password="x", email="u1@example.com")
        ProjectMember.objects.create(project=p, user=u, role=MemberRole.OWNER)
        client = APIClient()
        r = client.get("/api/v1/project-members/")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["user"]["username"] == "u1"
        assert data[0]["role"] == "owner"
        r2 = client.get(f"/api/v1/project-members/?project={p.pk}")
        assert r2.status_code == 200
        assert len(r2.json()) == 1


@pytest.mark.django_db
def test_exception_handler_validation_shape():
    context = {"view": MagicMock(), "request": MagicMock()}
    exc = ValidationError({"name": ["This field is required."]})
    resp = custom_exception_handler(exc, context)
    assert resp.status_code == 400
    assert resp.data["code"] == "VALIDATION_ERROR"
    assert "name" in resp.data["details"]
    assert "message" in resp.data


@pytest.mark.django_db
def test_exception_handler_not_found_shape():
    context = {"view": MagicMock(), "request": MagicMock()}
    exc = NotFound()
    resp = custom_exception_handler(exc, context)
    assert resp.status_code == 404
    assert resp.data["code"] == "NOT_FOUND"
    assert resp.data["message"]


def test_exception_handler_500_shape():
    context = {"view": MagicMock(), "request": MagicMock()}
    exc = APIException(detail="boom")
    resp = custom_exception_handler(exc, context)
    assert resp.status_code == 500
    assert resp.data["code"] == "INTERNAL_ERROR"


@pytest.mark.django_db
def test_project_404_unified_format():
    client = APIClient()
    r = client.get("/api/v1/projects/99999/")
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "NOT_FOUND"
    assert "message" in body
    assert "details" in body
