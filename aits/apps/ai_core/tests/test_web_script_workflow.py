from unittest.mock import patch

import pytest

from apps.ai_core.models import PromptTemplate
from apps.ai_core.services.graph_workflows import web_script_gen_workflow


class DummyResponse:
    def __init__(self, content):
        self.content = content


class DummyLLM:
    def __init__(self, content):
        self._content = content

    def invoke(self, _payload):
        return DummyResponse(self._content)


@pytest.mark.django_db
def test_web_script_gen_workflow_success():
    PromptTemplate.objects.create(
        scene="web_script_gen",
        version=1,
        template_text="Generate playwright script",
        is_default=True,
    )
    llm = DummyLLM(
        {
            "title": "Login success case",
            "script": "await page.goto('https://example.com'); expect(true).toBeTruthy();",
            "notes": "basic happy path",
        }
    )

    state = web_script_gen_workflow("login flow", llm_client=llm)

    assert state.get("error") is None
    assert state["generated_script"] is not None
    assert state["generated_script"]["title"] == "Login success case"


@pytest.mark.django_db
def test_web_script_gen_workflow_fails_basic_check():
    PromptTemplate.objects.create(
        scene="web_script_gen",
        version=1,
        template_text="Generate playwright script",
        is_default=True,
    )
    llm = DummyLLM(
        {
            "title": "Bad script",
            "script": "console.log('no playwright keyword')",
            "notes": "",
        }
    )

    state = web_script_gen_workflow("broken flow", llm_client=llm)

    assert state.get("generated_script") is None
    assert state.get("error")


@pytest.mark.django_db
def test_web_script_gen_workflow_uses_factory():
    PromptTemplate.objects.create(
        scene="web_script_gen",
        version=1,
        template_text="Generate playwright script",
        is_default=True,
    )
    factory_llm = DummyLLM(
        {
            "title": "Factory web script",
            "script": "await page.goto('https://example.com'); expect(1).toBe(1);",
            "notes": "from factory",
        }
    )
    with patch(
        "apps.ai_core.services.graph_workflows.LLMClientFactory.get_active_client",
        return_value=factory_llm,
    ) as mocked_factory:
        state = web_script_gen_workflow("use factory")

    mocked_factory.assert_called_once()
    assert state.get("error") is None
    assert state["generated_script"] is not None
