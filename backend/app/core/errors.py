from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ApiError(Exception):
    message: str
    code: str
    status_code: int = status.HTTP_400_BAD_REQUEST
    headers: dict[str, str] | None = None


def error_content(*, message: str, code: str) -> dict[str, Any]:
    return {
        "error": True,
        "message": message,
        "code": code,
    }


def error_response(
    status_code: int,
    *,
    message: str,
    code: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content=error_content(message=message, code=code),
    )


def map_http_exception_code(status_code: int, detail: Any | None = None) -> str:
    if isinstance(detail, dict):
        explicit_code = detail.get("code")
        if isinstance(explicit_code, str) and explicit_code.strip():
            return explicit_code.strip()
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limit_exceeded",
        500: "internal_server_error",
        503: "service_unavailable",
    }
    return mapping.get(status_code, f"http_{status_code}")


def message_from_detail(detail: Any) -> str:
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    if isinstance(detail, dict):
        for key in ("message", "detail", "error"):
            value = detail.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "Request failed."


def format_validation_errors(errors: list[dict[str, Any]]) -> str:
    messages: list[str] = []
    for item in errors:
        location = item.get("loc") or ()
        location_parts = [str(part) for part in location if str(part) not in {"body", "query", "path"}]
        label = ".".join(location_parts) if location_parts else "request"
        detail = str(item.get("msg") or "Invalid value.")
        messages.append(f"{label}: {detail}")
    if not messages:
        return "Request validation failed."
    return "; ".join(messages)


async def handle_api_error(_request: Request, exc: ApiError) -> Response:
    return error_response(
        exc.status_code,
        message=exc.message,
        code=exc.code,
        headers=exc.headers,
    )


async def handle_http_exception(_request: Request, exc: HTTPException) -> Response:
    return error_response(
        exc.status_code,
        message=message_from_detail(exc.detail),
        code=map_http_exception_code(exc.status_code, detail=exc.detail),
        headers=exc.headers,
    )


async def handle_validation_error(_request: Request, exc: RequestValidationError) -> Response:
    return error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        message=format_validation_errors(exc.errors()),
        code="validation_error",
    )


async def handle_unexpected_exception(request: Request, exc: Exception) -> Response:
    logger.exception("api.unhandled_exception path=%s", request.url.path)
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Internal server error.",
        code="internal_server_error",
    )


__all__ = [
    "ApiError",
    "error_content",
    "error_response",
    "format_validation_errors",
    "handle_api_error",
    "handle_http_exception",
    "handle_unexpected_exception",
    "handle_validation_error",
    "map_http_exception_code",
    "message_from_detail",
]
