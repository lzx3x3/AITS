from __future__ import annotations

import json
from io import BytesIO

import requests
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.api_testing.models import ApiEndpoint, ApiSchema
from apps.common.enums import ApiSchemaSourceType, ProjectStatus
from apps.projects.models import Project

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def _is_supported_api_spec(candidate: object) -> bool:
    if not isinstance(candidate, dict):
        return False
    openapi_version = candidate.get("openapi")
    if isinstance(openapi_version, str) and openapi_version.startswith("3."):
        return True
    swagger_version = candidate.get("swagger")
    if isinstance(swagger_version, str) and swagger_version.startswith("2."):
        return True
    info = candidate.get("info")
    schema = info.get("schema") if isinstance(info, dict) else ""
    return isinstance(schema, str) and "schema.getpostman.com" in schema


def _extract_json_object(raw_text: str) -> dict:
    stripped = raw_text.strip()
    if stripped.startswith("{"):
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
        raise ValidationError("JSON content must be an object.")

    decoder = json.JSONDecoder()
    best_candidate = None
    for idx, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(stripped[idx:])
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        if _is_supported_api_spec(parsed):
            return parsed
        if best_candidate is None:
            best_candidate = parsed
    if best_candidate is not None:
        return best_candidate

    start = stripped.find("{")
    if start < 0:
        raise ValidationError("No JSON object found in content.")

    depth = 0
    in_string = False
    escaped = False
    for idx, char in enumerate(stripped[start:], start=start):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(stripped[start : idx + 1])

    raise ValidationError("No complete JSON object found in content.")


def _read_openapi_from_uploaded_file(source: str, uploaded_file) -> str:
    content = uploaded_file.read()
    if not content:
        raise ValidationError("Uploaded file is empty.")
    filename = (getattr(uploaded_file, "name", "") or "").lower()

    if source == ApiSchemaSourceType.JSON:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("JSON file must be UTF-8 encoded.") from exc

    if source == ApiSchemaSourceType.WORD:
        if filename.endswith(".docx"):
            try:
                from docx import Document
            except ImportError as exc:
                raise ValidationError("python-docx is required to parse Word files.") from exc
            document = Document(BytesIO(content))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("Text/Markdown file must be UTF-8 encoded.") from exc

    if source == ApiSchemaSourceType.PDF:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValidationError("pypdf is required to parse PDF files.") from exc
        reader = PdfReader(BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    raise ValidationError("Unsupported source type for file upload.")


def _get_or_create_mvp_project() -> Project:
    project = Project.objects.order_by("id").first()
    if project is not None:
        return project
    return Project.objects.create(
        name="MVP Project",
        description="Auto-created default project for API schema import.",
        status=ProjectStatus.ACTIVE,
    )


def _ensure_openapi3(raw_data: object) -> dict:
    if not isinstance(raw_data, dict):
        raise ValidationError("OpenAPI document must be a JSON object.")

    openapi_version = raw_data.get("openapi")
    if isinstance(openapi_version, str) and openapi_version.startswith("3."):
        paths = raw_data.get("paths")
        if not isinstance(paths, dict):
            raise ValidationError("OpenAPI document requires a 'paths' object.")
        return raw_data

    swagger_version = raw_data.get("swagger")
    if isinstance(swagger_version, str) and swagger_version.startswith("2."):
        return _convert_swagger2_to_openapi3(raw_data)

    info = raw_data.get("info")
    postman_schema = info.get("schema") if isinstance(info, dict) else ""
    if isinstance(postman_schema, str) and "schema.getpostman.com" in postman_schema:
        return _convert_postman_collection_to_openapi3(raw_data)

    raise ValidationError("Only OpenAPI 3.x documents are supported.")


def _convert_swagger2_to_openapi3(raw_data: dict) -> dict:
    paths = raw_data.get("paths")
    if not isinstance(paths, dict):
        raise ValidationError("Swagger/OpenAPI document requires a 'paths' object.")

    converted_paths = {}
    for path, operation_map in paths.items():
        if not isinstance(path, str) or not isinstance(operation_map, dict):
            continue
        converted_ops = {}
        for method, operation in operation_map.items():
            if not isinstance(operation, dict):
                continue
            new_operation = dict(operation)
            parameters = operation.get("parameters")
            if isinstance(parameters, list):
                body_param = next(
                    (
                        item
                        for item in parameters
                        if isinstance(item, dict) and item.get("in") == "body"
                    ),
                    None,
                )
                if body_param and "requestBody" not in new_operation:
                    schema = body_param.get("schema")
                    new_operation["requestBody"] = (
                        {"content": {"application/json": {"schema": schema}}}
                        if isinstance(schema, dict)
                        else {}
                    )
            converted_ops[method] = new_operation
        converted_paths[path] = converted_ops

    return {
        "openapi": "3.0.0",
        "info": raw_data.get("info") if isinstance(raw_data.get("info"), dict) else {},
        "paths": converted_paths,
    }


def _postman_items_to_paths(items: list, paths: dict) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        children = item.get("item")
        if isinstance(children, list):
            _postman_items_to_paths(children, paths)
            continue

        request = item.get("request")
        if not isinstance(request, dict):
            continue
        method = str(request.get("method") or "GET").lower()
        if method not in HTTP_METHODS:
            continue

        url_data = request.get("url")
        path = ""
        if isinstance(url_data, dict):
            url_path = url_data.get("path")
            if isinstance(url_path, list) and url_path:
                path = "/" + "/".join(str(part).strip("/") for part in url_path if part)
            elif isinstance(url_data.get("raw"), str):
                raw = url_data["raw"]
                if "/" in raw:
                    tail = raw.split("://", 1)[-1]
                    tail = tail.split("/", 1)[-1] if "/" in tail else ""
                    path = "/" + tail.split("?", 1)[0].strip("/")
        elif isinstance(url_data, str):
            raw = url_data
            if "/" in raw:
                tail = raw.split("://", 1)[-1]
                tail = tail.split("/", 1)[-1] if "/" in tail else ""
                path = "/" + tail.split("?", 1)[0].strip("/")
        if not path:
            continue

        operation = {
            "summary": str(item.get("name") or request.get("description") or ""),
            "responses": {"200": {"description": "Success"}},
        }

        headers = request.get("header")
        if isinstance(headers, list):
            header_params = []
            for h in headers:
                if not isinstance(h, dict):
                    continue
                key = h.get("key")
                if not key:
                    continue
                header_params.append(
                    {
                        "name": str(key),
                        "in": "header",
                        "schema": {"type": "string"},
                    }
                )
            if header_params:
                operation["parameters"] = header_params

        body = request.get("body")
        if isinstance(body, dict) and body.get("mode") == "raw":
            raw_body = body.get("raw")
            if isinstance(raw_body, str) and raw_body.strip():
                try:
                    sample = json.loads(raw_body)
                    if isinstance(sample, dict):
                        props = {}
                        for k, v in sample.items():
                            if isinstance(v, bool):
                                p_type = "boolean"
                            elif isinstance(v, int):
                                p_type = "integer"
                            elif isinstance(v, float):
                                p_type = "number"
                            elif isinstance(v, list):
                                p_type = "array"
                            elif isinstance(v, dict):
                                p_type = "object"
                            else:
                                p_type = "string"
                            props[str(k)] = {"type": p_type}
                        operation["requestBody"] = {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": props}
                                }
                            }
                        }
                except json.JSONDecodeError:
                    operation["requestBody"] = {
                        "content": {"text/plain": {"schema": {"type": "string"}}}
                    }

        paths.setdefault(path, {})
        paths[path][method] = operation


def _convert_postman_collection_to_openapi3(raw_data: dict) -> dict:
    info = raw_data.get("info") if isinstance(raw_data.get("info"), dict) else {}
    title = str(info.get("name") or "Imported Postman Collection")
    items = raw_data.get("item")
    if not isinstance(items, list):
        raise ValidationError("Postman collection requires an 'item' array.")

    paths: dict = {}
    _postman_items_to_paths(items, paths)
    if not paths:
        raise ValidationError("No API requests found in Postman collection.")

    return {
        "openapi": "3.0.0",
        "info": {"title": title, "version": "1.0.0"},
        "paths": paths,
    }


def import_schema(source: str, content_or_url: str, project: Project | None = None) -> ApiSchema:
    if source not in {
        ApiSchemaSourceType.JSON,
        ApiSchemaSourceType.URL,
        ApiSchemaSourceType.WORD,
        ApiSchemaSourceType.PDF,
    }:
        raise ValidationError("source must be one of 'json', 'url', 'word', 'pdf'.")
    if not content_or_url:
        raise ValidationError("content_or_url cannot be empty.")

    if source == ApiSchemaSourceType.URL:
        try:
            response = requests.get(content_or_url, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ValidationError(f"Failed to fetch OpenAPI URL: {exc}") from exc
        try:
            raw_data = response.json()
        except ValueError as exc:
            raise ValidationError("URL response is not valid JSON.") from exc
    elif source == ApiSchemaSourceType.JSON:
        try:
            raw_data = json.loads(content_or_url)
        except json.JSONDecodeError as exc:
            raise ValidationError("content is not valid JSON.") from exc
    else:
        try:
            raw_data = _extract_json_object(content_or_url)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValidationError(
                "word/pdf content must contain a valid OpenAPI JSON object."
            ) from exc

    raw_data = _ensure_openapi3(raw_data)
    info = raw_data.get("info") if isinstance(raw_data.get("info"), dict) else {}
    schema_name = str(info.get("title") or "Imported OpenAPI Schema")

    return ApiSchema.objects.create(
        project=project or _get_or_create_mvp_project(),
        name=schema_name,
        source_type=source,
        raw_content=raw_data,
        version=1,
    )


@transaction.atomic
def parse_endpoints(schema_id: int) -> int:
    schema = ApiSchema.objects.get(pk=schema_id)
    raw_paths = schema.raw_content.get("paths", {})
    if not isinstance(raw_paths, dict):
        raise ValidationError("Schema paths are invalid.")

    schema.endpoints.all().delete()
    to_create: list[ApiEndpoint] = []
    seen_pairs: set[tuple[str, str]] = set()

    for path, operation_map in raw_paths.items():
        if not isinstance(path, str) or not isinstance(operation_map, dict):
            continue
        for method, operation in operation_map.items():
            method_normalized = str(method).lower()
            if method_normalized not in HTTP_METHODS:
                continue
            dedupe_key = (path, method_normalized.upper())
            if dedupe_key in seen_pairs:
                continue
            seen_pairs.add(dedupe_key)
            op = operation if isinstance(operation, dict) else {}
            to_create.append(
                ApiEndpoint(
                    schema=schema,
                    path=path,
                    method=method_normalized.upper(),
                    summary=str(op.get("summary") or ""),
                    request_schema=op.get("requestBody", {}) if isinstance(op, dict) else {},
                    response_schema=op.get("responses", {}) if isinstance(op, dict) else {},
                )
            )

    ApiEndpoint.objects.bulk_create(to_create)
    return len(to_create)
