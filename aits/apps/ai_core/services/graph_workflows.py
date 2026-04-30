from __future__ import annotations

import json
from typing import Any, TypedDict

from apps.ai_core.services.llm_provider import LLMClientFactory
from apps.ai_core.services.prompt_manager import PromptManager


class ApiCaseItem(TypedDict):
    title: str
    request_data: dict[str, Any]
    assertions: list[Any]


class ApiCaseGenState(TypedDict, total=False):
    endpoint_schema: dict[str, Any]
    user_prompt: str
    normalized_input: dict[str, Any]
    llm_raw_output: Any
    validated_cases: list[ApiCaseItem]
    error: str | None


class WebScriptItem(TypedDict):
    title: str
    script: str
    notes: str


class WebScriptGenState(TypedDict, total=False):
    requirement_text: str
    normalized_input: dict[str, Any]
    llm_raw_output: Any
    generated_script: WebScriptItem | None
    error: str | None


def _parse_llm_json_payload(raw_output: str):
    text = raw_output.strip()
    if not text:
        raise json.JSONDecodeError("empty payload", text, 0)

    fence_marker = "```"
    if fence_marker in text:
        parts = text.split(fence_marker)
        for part in parts:
            candidate = part.strip()
            if not candidate:
                continue
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            if not candidate:
                continue
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[idx:])
            return parsed
        except json.JSONDecodeError:
            continue

    return json.loads(text)


def _normalize_input(state: ApiCaseGenState) -> ApiCaseGenState:
    endpoint_schema = state.get("endpoint_schema") or {}
    user_prompt = (state.get("user_prompt") or "").strip()
    state["normalized_input"] = {
        "endpoint_schema": endpoint_schema,
        "user_prompt": user_prompt,
    }
    return state


def _generate(state: ApiCaseGenState, llm_client: Any | None = None) -> ApiCaseGenState:
    prompt_template = PromptManager.get_prompt("api_case_gen")
    normalized_input = state.get("normalized_input", {})
    payload = {
        "instruction": prompt_template,
        "endpoint_schema": normalized_input.get("endpoint_schema", {}),
        "user_prompt": normalized_input.get("user_prompt", ""),
        "output_schema": {"title": "string", "request_data": "object", "assertions": "array"},
    }
    client = llm_client or LLMClientFactory.get_active_client()
    response = client.invoke(json.dumps(payload, ensure_ascii=False))
    state["llm_raw_output"] = getattr(response, "content", response)
    return state


def _validate_output(state: ApiCaseGenState) -> ApiCaseGenState:
    raw_output = state.get("llm_raw_output")
    state["validated_cases"] = []
    state["error"] = None

    if isinstance(raw_output, str):
        try:
            raw_output = _parse_llm_json_payload(raw_output)
        except json.JSONDecodeError:
            state["error"] = "LLM output is not valid JSON."
            return state

    if isinstance(raw_output, dict):
        raw_output = [raw_output]

    if not isinstance(raw_output, list):
        state["error"] = "LLM output must be a case object or a list of case objects."
        return state

    validated_cases: list[ApiCaseItem] = []
    for idx, item in enumerate(raw_output):
        if not isinstance(item, dict):
            state["error"] = f"Case at index {idx} is not an object."
            return state
        title = item.get("title")
        request_data = item.get("request_data")
        assertions = item.get("assertions")
        if not isinstance(title, str) or not title.strip():
            state["error"] = f"Case at index {idx} missing valid 'title'."
            return state
        if not isinstance(request_data, dict):
            state["error"] = f"Case at index {idx} missing valid 'request_data' object."
            return state
        if not isinstance(assertions, list):
            state["error"] = f"Case at index {idx} missing valid 'assertions' list."
            return state

        validated_cases.append(
            {
                "title": title.strip(),
                "request_data": request_data,
                "assertions": assertions,
            }
        )

    if not validated_cases:
        state["error"] = "No valid cases generated."
        return state

    state["validated_cases"] = validated_cases
    return state


def api_case_gen_workflow(
    endpoint_schema: dict[str, Any],
    user_prompt: str,
    llm_client: Any | None = None,
) -> ApiCaseGenState:
    state: ApiCaseGenState = {
        "endpoint_schema": endpoint_schema,
        "user_prompt": user_prompt,
    }
    state = _normalize_input(state)
    state = _generate(state, llm_client=llm_client)
    state = _validate_output(state)
    return state


def _normalize_web_input(state: WebScriptGenState) -> WebScriptGenState:
    requirement_text = (state.get("requirement_text") or "").strip()
    state["normalized_input"] = {"requirement_text": requirement_text}
    return state


def _generate_web_script(
    state: WebScriptGenState, llm_client: Any | None = None
) -> WebScriptGenState:
    prompt_template = PromptManager.get_prompt("web_script_gen")
    normalized_input = state.get("normalized_input", {})
    payload = {
        "instruction": prompt_template,
        "requirement_text": normalized_input.get("requirement_text", ""),
        "output_schema": {"title": "string", "script": "string", "notes": "string"},
    }
    client = llm_client or LLMClientFactory.get_active_client()
    response = client.invoke(json.dumps(payload, ensure_ascii=False))
    state["llm_raw_output"] = getattr(response, "content", response)
    return state


def _basic_check_web_script(state: WebScriptGenState) -> WebScriptGenState:
    raw_output = state.get("llm_raw_output")
    state["generated_script"] = None
    state["error"] = None

    if isinstance(raw_output, str):
        try:
            raw_output = _parse_llm_json_payload(raw_output)
        except json.JSONDecodeError:
            state["error"] = "LLM output is not valid JSON."
            return state

    if not isinstance(raw_output, dict):
        state["error"] = "LLM output must be an object."
        return state

    title = raw_output.get("title")
    script = raw_output.get("script")
    notes = raw_output.get("notes", "")
    if not isinstance(title, str) or not title.strip():
        state["error"] = "Missing valid 'title'."
        return state
    if not isinstance(script, str) or not script.strip():
        state["error"] = "Missing valid 'script'."
        return state
    if not isinstance(notes, str):
        state["error"] = "Missing valid 'notes'."
        return state

    # MVP basic quality gate from task: include page.goto and expect.
    lowered_script = script.lower()
    if "page.goto" not in lowered_script or "expect" not in lowered_script:
        state["error"] = "Generated script must contain 'page.goto' and 'expect'."
        return state

    state["generated_script"] = {
        "title": title.strip(),
        "script": script,
        "notes": notes,
    }
    return state


def web_script_gen_workflow(
    requirement_text: str, llm_client: Any | None = None
) -> WebScriptGenState:
    state: WebScriptGenState = {"requirement_text": requirement_text}
    state = _normalize_web_input(state)
    state = _generate_web_script(state, llm_client=llm_client)
    state = _basic_check_web_script(state)
    return state
