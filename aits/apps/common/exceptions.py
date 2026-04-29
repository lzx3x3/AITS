from rest_framework.views import exception_handler as drf_exception_handler


def _status_to_code(status_code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        500: "INTERNAL_ERROR",
    }
    return mapping.get(status_code, f"HTTP_{status_code}")


def _extract_message(data, status_code: int) -> str:
    if not isinstance(data, dict):
        return str(data)
    if "detail" in data and len(data) == 1:
        d = data["detail"]
        if isinstance(d, list) and d:
            return str(d[0])
        return str(d)
    if "non_field_errors" in data and data["non_field_errors"]:
        return str(data["non_field_errors"][0])
    if status_code == 400:
        return "Validation failed"
    if status_code == 404:
        return "Not found"
    return "Request error"


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    status_code = response.status_code
    raw = response.data
    if isinstance(raw, dict):
        details = raw
    else:
        details = {"detail": raw}

    message = _extract_message(details, status_code)
    code = _status_to_code(status_code)
    if status_code == 400 and isinstance(raw, dict) and set(raw.keys()) != {"detail"}:
        code = "VALIDATION_ERROR"

    response.data = {"code": code, "message": message, "details": details}
    return response
