from __future__ import annotations

import inspect
import json
import logging
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.datastructures import DefaultPlaceholder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute, APIWebSocketRoute
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import (
    ApiError,
    error_response,
    format_validation_errors,
    handle_api_error,
    handle_http_exception,
    handle_unexpected_exception,
    handle_validation_error,
    map_http_exception_code,
    message_from_detail,
)

logger = logging.getLogger(__name__)

API_VERSION_PREFIX = "/api/v2"
LEGACY_API_VERSION_PREFIX = "/api/v1"
API_VERSION_HEADER_NAME = "X-API-Version"
API_VERSION_HEADER_VALUE = "2"
API_CONTRACT_PATH = Path(__file__).resolve().parents[3] / "shared" / "api_contract.json"
_ALIAS_EXCLUDED_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/metrics",
    "/health",
    "/ready",
    "/version",
    "/tts",
)
_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
_ERROR_COMPONENT_NAME = "ApiContractErrorResponse"
_FASTAPI_ADD_API_ROUTE_PARAMS = set(inspect.signature(FastAPI.add_api_route).parameters)
_ERROR_DESCRIPTIONS = {
    "400": "Bad request.",
    "401": "Unauthorized.",
    "403": "Forbidden.",
    "404": "Not found.",
    "409": "Conflict.",
    "422": "Validation error.",
    "500": "Internal server error.",
}
_RESERVED_VERSIONED_FINGERPRINTS: set[tuple[str, tuple[str, ...]]] | None = None


def install_api_contracts(app: FastAPI) -> None:
    if getattr(app.state, "api_contracts_installed", False):
        return
    app.state.api_contract_alias_priorities = {}
    app.state.api_contract_alias_routes = {}
    _install_contract_guard_middleware(app)
    _install_exception_handlers(app)
    _install_envelope_middleware(app)
    _install_openapi_transform(app)
    app.state.api_contracts_installed = True


def register_versioned_route_aliases(app: FastAPI, routes: Iterable[object]) -> None:
    alias_priorities = getattr(app.state, "api_contract_alias_priorities", None)
    if alias_priorities is None:
        app.state.api_contract_alias_priorities = {}
        alias_priorities = app.state.api_contract_alias_priorities
    alias_routes = getattr(app.state, "api_contract_alias_routes", None)
    if alias_routes is None:
        app.state.api_contract_alias_routes = {}
        alias_routes = app.state.api_contract_alias_routes

    reserved_fingerprints = _reserved_versioned_fingerprints()
    candidates: list[tuple[int, object, str]] = []
    for route in routes:
        path = getattr(route, "path", None)
        if not isinstance(path, str):
            continue
        versioned_path = build_versioned_path(path)
        if versioned_path is None:
            continue
        candidates.append((_route_alias_priority(path), route, versioned_path))

    for priority, route, versioned_path in sorted(candidates, key=lambda item: (item[0], item[2])):
        if isinstance(route, APIRoute):
            fingerprint = (versioned_path, tuple(sorted(route.methods or ())))
        elif isinstance(route, APIWebSocketRoute):
            fingerprint = (versioned_path, ("WEBSOCKET",))
        else:
            continue
        if fingerprint in reserved_fingerprints:
            continue

        current_priority = alias_priorities.get(fingerprint)
        if current_priority is not None and current_priority <= priority:
            continue
        if current_priority is not None and current_priority > priority:
            existing_route = alias_routes.pop(fingerprint, None)
            if existing_route is not None:
                try:
                    app.router.routes.remove(existing_route)
                except ValueError:
                    pass

        if isinstance(route, APIRoute):
            alias_route = _clone_api_route(app, route=route, versioned_path=versioned_path)
        else:
            alias_route = _clone_websocket_route(app, route=route, versioned_path=versioned_path)

        alias_routes[fingerprint] = alias_route
        alias_priorities[fingerprint] = priority

    if candidates:
        app.openapi_schema = None


def build_versioned_path(path: str) -> str | None:
    if path.startswith(API_VERSION_PREFIX):
        return None
    if path == "/":
        return None
    if any(_path_matches_prefix(path, prefix) for prefix in _ALIAS_EXCLUDED_PREFIXES):
        return None
    if path == "/api":
        return API_VERSION_PREFIX
    if path.startswith("/api/"):
        return f"{API_VERSION_PREFIX}{path[4:]}"
    return f"{API_VERSION_PREFIX}{path}"


def _clone_api_route(app: FastAPI, *, route: APIRoute, versioned_path: str) -> APIRoute:
    route_kwargs: dict[str, Any] = {
        "response_model": route.response_model,
        "status_code": route.status_code,
        "tags": list(route.tags or ()),
        "dependencies": list(route.dependencies or ()),
        "summary": route.summary,
        "description": route.description,
        "response_description": route.response_description,
        "responses": deepcopy(route.responses),
        "deprecated": route.deprecated,
        "methods": route.methods,
        "operation_id": _versioned_operation_id(route),
        "response_model_include": route.response_model_include,
        "response_model_exclude": route.response_model_exclude,
        "response_model_by_alias": route.response_model_by_alias,
        "response_model_exclude_unset": route.response_model_exclude_unset,
        "response_model_exclude_defaults": route.response_model_exclude_defaults,
        "response_model_exclude_none": route.response_model_exclude_none,
        "include_in_schema": route.include_in_schema,
        "name": f"v1_{route.name}",
        "openapi_extra": deepcopy(route.openapi_extra),
    }
    if "callbacks" in _FASTAPI_ADD_API_ROUTE_PARAMS:
        route_kwargs["callbacks"] = list(route.callbacks or ())
    if not isinstance(route.response_class, DefaultPlaceholder):
        route_kwargs["response_class"] = route.response_class

    app.add_api_route(versioned_path, route.endpoint, **route_kwargs)
    return app.router.routes[-1]


def _clone_websocket_route(app: FastAPI, *, route: APIWebSocketRoute, versioned_path: str) -> APIWebSocketRoute:
    app.add_api_websocket_route(
        versioned_path,
        route.endpoint,
        name=f"v1_{route.name}",
        dependencies=list(route.dependencies or ()),
    )
    return app.router.routes[-1]


def _route_alias_priority(path: str) -> int:
    if path == "/api" or path.startswith("/api/"):
        return 0
    return 1


def _versioned_operation_id(route: APIRoute) -> str | None:
    if route.operation_id:
        return f"v1_{route.operation_id}"
    return None


def _install_exception_handlers(app: FastAPI) -> None:
    if getattr(app.state, "api_contract_exception_handlers_installed", False):
        return
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_exception)
    app.state.api_contract_exception_handlers_installed = True


async def _handle_http_exception(request: Request, exc: HTTPException) -> Response:
    return await handle_http_exception(request, exc)


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> Response:
    return await handle_validation_error(request, exc)


async def _handle_unexpected_exception(request: Request, exc: Exception) -> Response:
    return await handle_unexpected_exception(request, exc)


def _error_response(
    status_code: int,
    *,
    message: str,
    code: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return error_response(status_code, message=message, code=code, headers=headers)


class ApiContractEnvelopeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if not _is_versioned_request(request):
            return response
        if (
            request.method == "HEAD"
            or response.status_code >= 400
            or response.status_code == status.HTTP_304_NOT_MODIFIED
        ):
            return response
        if not _is_json_response(response):
            return response

        body = await _read_response_body(response)
        if not body:
            payload = None
        else:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return _rebuild_response(response, body)

        normalized = _normalize_success_payload(payload)
        status_code = response.status_code if response.status_code != status.HTTP_204_NO_CONTENT else status.HTTP_200_OK
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return JSONResponse(
            status_code=status_code,
            content=normalized,
            headers=headers,
            background=response.background,
        )


def _install_envelope_middleware(app: FastAPI) -> None:
    if getattr(app.state, "api_contract_envelope_middleware_installed", False):
        return
    app.add_middleware(ApiContractEnvelopeMiddleware)
    app.state.api_contract_envelope_middleware_installed = True


class ApiContractGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if _is_contract_exempt_path(path):
            return await call_next(request)

        if is_explicitly_deprecated_route(path):
            _log_rejected_request(request, route=path, reason="explicit_deprecated")
            return _error_response(
                status.HTTP_410_GONE,
                message="This endpoint is no longer supported. Use the latest API.",
                code="DEPRECATED_ROUTE",
            )

        contract = load_api_contract()
        canonical_path = resolve_contract_path(path)
        if canonical_path is None:
            if _is_contract_managed_path(path):
                _log_contract_observation(request, route=path, reason="not_in_contract")
            return await call_next(request)

        if path != canonical_path:
            _log_contract_observation(
                request,
                route=path,
                reason="non_canonical_alias",
                canonical_route=canonical_path,
            )
            return await call_next(request)

        if path.startswith(API_VERSION_PREFIX):
            header_value = str(request.headers.get(API_VERSION_HEADER_NAME, "")).strip()
            if header_value != str(contract["version_header"]["value"]).strip():
                _log_contract_observation(request, route=path, reason="missing_version_header")

        return await call_next(request)


def _install_contract_guard_middleware(app: FastAPI) -> None:
    if getattr(app.state, "api_contract_guard_middleware_installed", False):
        return
    app.add_middleware(ApiContractGuardMiddleware)
    app.state.api_contract_guard_middleware_installed = True


async def _read_response_body(response: Response) -> bytes:
    body = getattr(response, "body", None)
    if isinstance(body, bytes):
        return body
    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
    return b"".join(chunks)


def _rebuild_response(response: Response, body: bytes) -> Response:
    headers = dict(response.headers)
    headers.pop("content-length", None)
    return Response(
        content=body,
        status_code=response.status_code,
        headers=headers,
        media_type=response.media_type,
        background=response.background,
    )


def _is_json_response(response: Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    return "application/json" in content_type or content_type.endswith("+json")


def _normalize_success_payload(payload: Any) -> dict[str, Any]:
    if _is_contract_envelope(payload):
        success = bool(payload.get("success"))
        if success:
            return {
                "success": True,
                "data": payload.get("data"),
            }
        error = payload.get("error")
        if isinstance(error, dict):
            return {
                "success": False,
                "error": _error_message_from_detail(error),
                "code": str(error.get("code") or payload.get("code") or "unknown_error"),
            }
        return {
            "success": False,
            "error": _error_message_from_detail(payload),
            "code": str(payload.get("code") or "unknown_error"),
        }
    return {
        "success": True,
        "data": payload,
    }


def _is_contract_envelope(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if not isinstance(payload.get("success"), bool):
        return False
    keys = set(payload.keys())
    return keys.issubset({"success", "data", "error", "code"})


def _install_openapi_transform(app: FastAPI) -> None:
    if getattr(app.state, "api_contract_openapi_installed", False):
        return
    original_openapi = app.openapi

    def _contract_openapi():
        schema = original_openapi()
        if schema.get("x-api-contract-version") == "v1-envelope":
            return schema
        _apply_versioned_contract_schema(schema)
        schema["x-api-contract-version"] = "v1-envelope"
        return schema

    app.openapi = _contract_openapi
    app.state.api_contract_openapi_installed = True


def _apply_versioned_contract_schema(schema: dict[str, Any]) -> None:
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    components[_ERROR_COMPONENT_NAME] = {
        "type": "object",
        "required": ["error", "message", "code"],
        "properties": {
            "error": {
                "type": "boolean",
                "enum": [True],
            },
            "message": {
                "type": "string",
                "example": "Authentication credentials were not provided.",
            },
            "code": {
                "type": "string",
                "example": "unauthorized",
            },
        },
    }

    paths = schema.get("paths", {})
    for path, path_item in paths.items():
        if not path.startswith(API_VERSION_PREFIX):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            _wrap_success_responses(schema, operation)
            _install_error_responses(operation)


def _wrap_success_responses(schema: dict[str, Any], operation: dict[str, Any]) -> None:
    responses = operation.setdefault("responses", {})
    operation_id = operation.get("operationId", "versioned_operation")
    components = schema.setdefault("components", {}).setdefault("schemas", {})

    for status_code, response in responses.items():
        if not str(status_code).startswith("2") or not isinstance(response, dict):
            continue
        content = response.setdefault("content", {}).setdefault("application/json", {})
        original_schema = deepcopy(content.get("schema") or {"nullable": True})
        component_name = _response_component_name(operation_id, str(status_code))
        components[component_name] = {
            "type": "object",
            "required": ["success", "data"],
            "properties": {
                "success": {
                    "type": "boolean",
                    "enum": [True],
                },
                "data": original_schema,
            },
        }
        content["schema"] = {"$ref": f"#/components/schemas/{component_name}"}


def _install_error_responses(operation: dict[str, Any]) -> None:
    responses = operation.setdefault("responses", {})
    for status_code, description in _ERROR_DESCRIPTIONS.items():
        response = responses.setdefault(status_code, {"description": description})
        response["description"] = description
        content = response.setdefault("content", {}).setdefault("application/json", {})
        content["schema"] = {"$ref": f"#/components/schemas/{_ERROR_COMPONENT_NAME}"}


def _response_component_name(operation_id: str, status_code: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", operation_id).strip("_")
    return f"ApiContract{normalized}{status_code}Response"


def _reserved_versioned_fingerprints() -> set[tuple[str, tuple[str, ...]]]:
    global _RESERVED_VERSIONED_FINGERPRINTS
    if _RESERVED_VERSIONED_FINGERPRINTS is not None:
        return _RESERVED_VERSIONED_FINGERPRINTS
    try:
        from app.api_v1.router import router as api_v1_router
    except Exception:
        _RESERVED_VERSIONED_FINGERPRINTS = set()
        return _RESERVED_VERSIONED_FINGERPRINTS

    fingerprints: set[tuple[str, tuple[str, ...]]] = set()
    for route in api_v1_router.routes:
        if isinstance(route, APIRoute):
            fingerprints.add((route.path, tuple(sorted(route.methods or ()))))
        elif isinstance(route, APIWebSocketRoute):
            fingerprints.add((route.path, ("WEBSOCKET",)))
    _RESERVED_VERSIONED_FINGERPRINTS = fingerprints
    return _RESERVED_VERSIONED_FINGERPRINTS


def _path_matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


@lru_cache
def load_api_contract() -> dict[str, Any]:
    return json.loads(API_CONTRACT_PATH.read_text(encoding="utf-8"))


@lru_cache
def _contract_alias_patterns() -> tuple[tuple[re.Pattern[str], str], ...]:
    contract = load_api_contract()
    patterns: list[tuple[re.Pattern[str], str]] = []
    seen: set[tuple[str, str]] = set()
    for alias, canonical in _flatten_contract_aliases(contract).items():
        signature = (alias, canonical)
        if signature in seen:
            continue
        seen.add(signature)
        patterns.append((_path_pattern(alias), canonical))
    return tuple(patterns)


def resolve_contract_path(path: str) -> str | None:
    normalized = path if path.startswith("/") else f"/{path}"
    for pattern, canonical in _contract_alias_patterns():
        if pattern.fullmatch(normalized):
            return canonical
    return None


def _flatten_contract_aliases(contract: dict[str, Any]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for route_entries in (contract.get("routes") or {}).values():
        for entry in route_entries.values():
            canonical = str(entry["canonical_path"])
            aliases[canonical] = canonical
            for alias in entry.get("aliases", ()):
                aliases[str(alias)] = canonical
    for entry in (contract.get("websockets") or {}).values():
        canonical = str(entry["canonical_path"])
        aliases[canonical] = canonical
        for alias in entry.get("aliases", ()):
            aliases[str(alias)] = canonical
    for alias, canonical in (contract.get("deprecated_aliases") or {}).items():
        aliases[str(alias)] = str(canonical)
    return aliases


def _path_pattern(path: str) -> re.Pattern[str]:
    escaped = re.escape(path)
    pattern = re.sub(r"\\\{[^}]+\\\}", r"[^/]+", escaped)
    return re.compile(pattern)


def _is_contract_exempt_path(path: str) -> bool:
    contract = load_api_contract()
    if path in set(contract.get("public_exempt_paths") or ()):
        return True
    for prefix in contract.get("public_exempt_prefixes") or ():
        if _path_matches_prefix(path, str(prefix)):
            return True
    return False


def _is_contract_managed_path(path: str) -> bool:
    managed_prefixes = ("/api", "/auth", "/ws")
    return any(_path_matches_prefix(path, prefix) for prefix in managed_prefixes)


@lru_cache
def _explicit_deprecated_route_patterns() -> tuple[re.Pattern[str], ...]:
    contract = load_api_contract()
    explicit_paths = contract.get("explicit_deprecated_paths") or contract.get("deprecated_routes") or ()
    return tuple(_path_pattern(str(path)) for path in explicit_paths)


def is_explicitly_deprecated_route(path: str) -> bool:
    normalized = path if path.startswith("/") else f"/{path}"
    return any(pattern.fullmatch(normalized) for pattern in _explicit_deprecated_route_patterns())


def _log_rejected_request(request: Request, *, route: str, reason: str) -> None:
    logger.warning(
        "api_contract.rejected route=%s reason=%s method=%s source=%s at=%s",
        route,
        reason,
        request.method,
        request.headers.get("X-Client-Platform")
        or request.headers.get("X-App-Platform")
        or request.headers.get("user-agent", "unknown"),
        request.headers.get("X-Request-Started-At", "unknown"),
    )


def _log_contract_observation(
    request: Request,
    *,
    route: str,
    reason: str,
    canonical_route: str | None = None,
) -> None:
    logger.warning(
        "api_contract.observed route=%s canonical_route=%s reason=%s method=%s source=%s at=%s",
        route,
        canonical_route,
        reason,
        request.method,
        request.headers.get("X-Client-Platform")
        or request.headers.get("X-App-Platform")
        or request.headers.get("user-agent", "unknown"),
        request.headers.get("X-Request-Started-At", "unknown"),
    )


def _is_versioned_request(request: Request) -> bool:
    return _path_matches_prefix(request.url.path, API_VERSION_PREFIX)


def _error_message_from_detail(detail: Any) -> str:
    if isinstance(detail, list):
        return format_validation_errors(detail)
    return message_from_detail(detail)


def _error_code_for_status(status_code: int, *, detail: Any | None = None) -> str:
    return map_http_exception_code(status_code, detail=detail)


def _format_validation_errors(errors: list[Any]) -> str:
    formatted_errors: list[dict[str, Any]] = []
    for error in errors[:3]:
        if isinstance(error, dict):
            formatted_errors.append(error)
        else:
            formatted_errors.append({"loc": ("request",), "msg": str(error)})
    return format_validation_errors(formatted_errors)


def _format_validation_location(location: Any) -> str | None:
    if not isinstance(location, (list, tuple)):
        return None
    parts = [str(item) for item in location if str(item).lower() not in {"body", "query", "path", "header", "response"}]
    if not parts:
        return None
    return ".".join(parts)
