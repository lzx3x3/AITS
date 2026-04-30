import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_prompt_template_crud_and_scene_filter():
    client = APIClient(HTTP_ACCEPT="application/json")
    base_url = "/api/v1/ai/prompts/"

    r1 = client.post(
        base_url,
        {
            "scene": "api_case_gen",
            "version": 1,
            "template_text": "prompt-v1",
            "is_default": True,
        },
        format="json",
    )
    assert r1.status_code == 201
    prompt_1_id = r1.json()["id"]

    r2 = client.post(
        base_url,
        {
            "scene": "api_case_gen",
            "version": 2,
            "template_text": "prompt-v2",
            "is_default": False,
        },
        format="json",
    )
    assert r2.status_code == 201
    prompt_2_id = r2.json()["id"]

    r3 = client.post(
        base_url,
        {
            "scene": "web_script_gen",
            "version": 1,
            "template_text": "web-prompt-v1",
            "is_default": True,
        },
        format="json",
    )
    assert r3.status_code == 201

    list_resp = client.get(base_url)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 3

    filter_resp = client.get(f"{base_url}?scene=api_case_gen")
    assert filter_resp.status_code == 200
    filter_data = filter_resp.json()
    assert len(filter_data) == 2
    assert {item["version"] for item in filter_data} == {1, 2}

    detail_resp = client.get(f"{base_url}{prompt_1_id}/")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["scene"] == "api_case_gen"

    patch_resp = client.patch(
        f"{base_url}{prompt_2_id}/",
        {"is_default": True},
        format="json",
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_default"] is True

    delete_resp = client.delete(f"{base_url}{prompt_1_id}/")
    assert delete_resp.status_code == 204


@pytest.mark.django_db
def test_prompt_template_validation_error_shape():
    client = APIClient(HTTP_ACCEPT="application/json")
    resp = client.post(
        "/api/v1/ai/prompts/",
        {
            "scene": "",
            "version": 1,
            "template_text": "",
            "is_default": False,
        },
        format="json",
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "details" in body
