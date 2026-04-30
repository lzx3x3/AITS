from __future__ import annotations

import time
from urllib.parse import urljoin

import requests

from apps.api_testing.models import ApiTestCase
from apps.projects.models import Environment


def run_api_case(case_id: int, env_id: int) -> dict:
    started = time.perf_counter()
    case = ApiTestCase.objects.select_related("endpoint").get(pk=case_id)
    env = Environment.objects.get(pk=env_id)

    request_url = urljoin(env.base_url.rstrip("/") + "/", case.endpoint.path.lstrip("/"))
    method = case.endpoint.method.lower()

    try:
        response = requests.request(
            method=method,
            url=request_url,
            json=case.request_data or {},
            timeout=20,
        )
        try:
            body = response.json()
        except ValueError:
            body = response.text
        return {
            "status": "success" if response.ok else "failed",
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "response_data": body,
            "error": None if response.ok else f"HTTP {response.status_code}",
        }
    except requests.RequestException as exc:
        return {
            "status": "failed",
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "response_data": {},
            "error": str(exc),
        }
