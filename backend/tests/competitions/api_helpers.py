from __future__ import annotations

from collections.abc import Mapping
from typing import Any

API_VERSION_HEADERS = {"X-API-Version": "2"}


def api_v2_path(path: str) -> str:
    if path.startswith("/api/v2/"):
        return path
    if path.startswith("/api/"):
        return f"/api/v2{path[4:]}"
    return path


def api_headers(headers: Mapping[str, str] | None = None) -> dict[str, str]:
    merged = dict(headers or {})
    merged.update(API_VERSION_HEADERS)
    return merged


def api_payload(response) -> Any:  # noqa: ANN001 - FastAPI test response.
    payload = response.json()
    if isinstance(payload, dict) and payload.get("success") is True and "data" in payload:
        return payload["data"]
    return payload


def api_error_detail(response) -> Any:  # noqa: ANN001 - FastAPI test response.
    payload = response.json()
    if not isinstance(payload, dict):
        return payload
    return payload.get("detail") or payload.get("message") or payload.get("error")
