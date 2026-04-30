from unittest.mock import patch

import pytest

from apps.ai_core.models import PromptTemplate
from apps.ai_core.services.graph_workflows import api_case_gen_workflow


class DummyResponse:
    def __init__(self, content):
        self.content = content


class DummyLLM:
    def __init__(self, content):
        self._content = content

    def invoke(self, _payload):
        return DummyResponse(self._content)


@pytest.mark.django_db
def test_api_case_gen_workflow_success_with_mock_llm():
    PromptTemplate.objects.create(
        scene="api_case_gen",
        version=1,
        template_text="Generate robust API test cases",
        is_default=True,
    )
    llm = DummyLLM(
        [
            {
                "title": "Create user successfully",
                "request_data": {"name": "Tom"},
                "assertions": [{"path": "status_code", "equals": 201}],
            }
        ]
    )

    state = api_case_gen_workflow(
        endpoint_schema={"path": "/users", "method": "POST"},
        user_prompt="cover happy path",
        llm_client=llm,
    )

    assert state.get("error") is None
    assert state["validated_cases"]
    assert state["validated_cases"][0]["title"] == "Create user successfully"


@pytest.mark.django_db
def test_api_case_gen_workflow_set_error_when_schema_invalid():
    PromptTemplate.objects.create(
        scene="api_case_gen",
        version=1,
        template_text="Generate robust API test cases",
        is_default=True,
    )
    llm = DummyLLM([{"title": "Missing request_data and assertions"}])

    state = api_case_gen_workflow(
        endpoint_schema={"path": "/users", "method": "POST"},
        user_prompt="invalid output test",
        llm_client=llm,
    )

    assert state["validated_cases"] == []
    assert state.get("error")


@pytest.mark.django_db
def test_api_case_gen_workflow_uses_factory_when_llm_not_provided():
    PromptTemplate.objects.create(
        scene="api_case_gen",
        version=1,
        template_text="Generate robust API test cases",
        is_default=True,
    )
    factory_llm = DummyLLM(
        [
            {
                "title": "Factory generated case",
                "request_data": {"id": 1},
                "assertions": [{"path": "status_code", "equals": 200}],
            }
        ]
    )
    with patch(
        "apps.ai_core.services.graph_workflows.LLMClientFactory.get_active_client",
        return_value=factory_llm,
    ) as mocked_factory:
        state = api_case_gen_workflow(
            endpoint_schema={"path": "/users/{id}", "method": "GET"},
            user_prompt="load case from factory",
        )

    mocked_factory.assert_called_once()
    assert state["error"] is None
    assert len(state["validated_cases"]) == 1


@pytest.mark.django_db
def test_api_case_gen_workflow_accepts_markdown_wrapped_json():
    PromptTemplate.objects.create(
        scene="api_case_gen",
        version=1,
        template_text="Generate robust API test cases",
        is_default=True,
    )
    llm = DummyLLM(
        """这里是生成结果：
```json
[
  {
    "title": "Wrapped JSON case",
    "request_data": {"foo": "bar"},
    "assertions": [{"path": "status_code", "equals": 200}]
  }
]
```"""
    )

    state = api_case_gen_workflow(
        endpoint_schema={"path": "/users", "method": "POST"},
        user_prompt="markdown output",
        llm_client=llm,
    )

    assert state.get("error") is None
    assert len(state["validated_cases"]) == 1
    assert state["validated_cases"][0]["title"] == "Wrapped JSON case"
