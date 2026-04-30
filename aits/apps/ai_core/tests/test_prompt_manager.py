import pytest

from apps.ai_core.models import PromptTemplate
from apps.ai_core.services.prompt_manager import PromptManager, PromptNotFoundError


@pytest.mark.django_db
def test_get_prompt_returns_default_when_version_missing():
    PromptTemplate.objects.create(
        scene="api_case_gen",
        version=1,
        template_text="default prompt",
        is_default=True,
    )
    PromptTemplate.objects.create(
        scene="api_case_gen",
        version=2,
        template_text="non default prompt",
        is_default=False,
    )

    result = PromptManager.get_prompt("api_case_gen")

    assert result == "default prompt"


@pytest.mark.django_db
def test_get_prompt_returns_specific_version():
    PromptTemplate.objects.create(
        scene="web_script_gen",
        version=1,
        template_text="v1 prompt",
        is_default=True,
    )
    PromptTemplate.objects.create(
        scene="web_script_gen",
        version=2,
        template_text="v2 prompt",
        is_default=False,
    )

    result = PromptManager.get_prompt("web_script_gen", version=2)

    assert result == "v2 prompt"


@pytest.mark.django_db
def test_get_prompt_raises_when_default_missing():
    PromptTemplate.objects.create(
        scene="missing_default_scene",
        version=1,
        template_text="not default",
        is_default=False,
    )

    with pytest.raises(PromptNotFoundError):
        PromptManager.get_prompt("missing_default_scene")


@pytest.mark.django_db
def test_get_prompt_raises_when_version_missing():
    PromptTemplate.objects.create(
        scene="api_case_gen",
        version=1,
        template_text="v1",
        is_default=True,
    )

    with pytest.raises(PromptNotFoundError):
        PromptManager.get_prompt("api_case_gen", version=9)
