from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.security import TokenError, decode_access_token
from app.core.errors import error_response

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_DANGEROUS_PATH_RE = re.compile(r"(?i)(?:\.\./|\.\.\\|<\s*script\b|javascript:)")
_INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("script_tag", re.compile(r"(?is)<\s*script\b")),
    ("inline_event_handler", re.compile(r"(?is)\bon(?:error|load|click|mouseover|focus)\s*=")),
    ("javascript_url", re.compile(r"(?is)javascript\s*:")),
    ("sql_union_select", re.compile(r"(?is)\bunion\b\s+(?:all\s+)?\bselect\b")),
    (
        "sql_tautology",
        re.compile(r"""(?is)\b(?:or|and)\b\s+['"]?[a-z0-9_]+['"]?\s*=\s*['"]?[a-z0-9_]+['"]?(?:\s*(?:--|#|/\*))?"""),
    ),
    ("sql_drop_table", re.compile(r"(?is)\bdrop\b\s+\btable\b")),
    ("sql_information_schema", re.compile(r"(?is)\binformation_schema\b")),
    ("sql_xp_cmdshell", re.compile(r"(?is)\bxp_cmdshell\b")),
    ("nosql_where", re.compile(r"(?is)(?:^|[{\[,])\s*['\"]?\$where['\"]?\s*:")),
)
_SIGNATURE_HEADER_NAMES = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-korapay-signature",
        "x-signature",
        "x-signature-sha256",
    }
)
_TEXTUAL_CONTENT_TYPES = (
    "application/json",
    "application/x-www-form-urlencoded",
    "text/plain",
)
_BODY_PRESERVING_PATH_SUFFIXES = ("/webhook",)
_MAX_AUDIT_SNIPPET_LENGTH = 160


def extract_access_token_subject(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "").strip()
    if not authorization:
        return None
    try:
        scheme, token = authorization.split(" ", maxsplit=1)
    except ValueError:
        return None
    if scheme.lower() != "bearer":
        return None
    try:
        payload = decode_access_token(token.strip())
    except TokenError:
        return None
    subject = payload.get("sub")
    return str(subject).strip() if isinstance(subject, str) and subject.strip() else None


def extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    client_host = str(request.client.host) if request.client is not None and request.client.host else ""
    if forwarded and _is_trusted_forwarding_peer(client_host):
        return forwarded.split(",", 1)[0].strip()
    if client_host:
        return client_host
    return "unknown"


def _is_trusted_forwarding_peer(host: str) -> bool:
    candidate = host.strip().lower()
    if candidate in {"127.0.0.1", "::1", "localhost"}:
        return True
    if candidate.startswith(("10.", "192.168.")):
        return True
    if candidate.startswith("172."):
        parts = candidate.split(".")
        if len(parts) >= 2 and parts[1].isdigit():
            return 16 <= int(parts[1]) <= 31
    return False


@dataclass(frozen=True, slots=True)
class SuspiciousInputError(ValueError):
    location: str
    reason: str
    snippet: str | None = None

    def detail(self) -> str:
        return f"Suspicious input blocked in {self.location}: {self.reason}."


def sanitize_text_input(
    value: str,
    *,
    location: str,
    inspect_for_injection: bool = True,
) -> str:
    cleaned = _CONTROL_CHAR_RE.sub("", value)
    if inspect_for_injection:
        for reason, pattern in _INJECTION_PATTERNS:
            if pattern.search(cleaned):
                raise SuspiciousInputError(
                    location=location,
                    reason=reason,
                    snippet=_snippet(cleaned),
                )
    return cleaned


def sanitize_input_structure(
    value: Any,
    *,
    location: str,
) -> Any:
    if isinstance(value, str):
        return sanitize_text_input(value, location=location)
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            sanitized_key = sanitize_text_input(str(key), location=f"{location}.key")
            sanitized[sanitized_key] = sanitize_input_structure(
                item,
                location=f"{location}.{sanitized_key}",
            )
        return sanitized
    if isinstance(value, list):
        return [sanitize_input_structure(item, location=f"{location}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, tuple):
        return tuple(
            sanitize_input_structure(item, location=f"{location}[{index}]") for index, item in enumerate(value)
        )
    return value


class RequestHardeningMiddleware(BaseHTTPMiddleware):
    EXEMPT_PREFIXES = ("/health", "/ready", "/version", "/docs", "/redoc", "/openapi.json")

    async def dispatch(self, request: Request, call_next):
        try:
            self._sanitize_path(request)
            self._sanitize_query_string(request)
            self._sanitize_headers(request)
            await self._sanitize_body(request)
        except SuspiciousInputError as exc:
            self._audit_blocked_request(request, exc)
            return error_response(
                422,
                message=exc.detail(),
                code="validation_error",
            )
        return await call_next(request)

    def _sanitize_path(self, request: Request) -> None:
        path = request.url.path or "/"
        if path.startswith(self.EXEMPT_PREFIXES):
            return
        if _DANGEROUS_PATH_RE.search(path):
            raise SuspiciousInputError(
                location="path",
                reason="dangerous_path_pattern",
                snippet=_snippet(path),
            )

    def _sanitize_query_string(self, request: Request) -> None:
        raw_query = request.scope.get("query_string", b"")
        if not raw_query:
            return
        parsed = parse_qsl(raw_query.decode("utf-8", errors="ignore"), keep_blank_values=True)
        sanitized_pairs = []
        modified = False
        for key, value in parsed:
            clean_key = sanitize_text_input(key, location=f"query.{key or 'key'}")
            clean_value = sanitize_text_input(value, location=f"query.{clean_key or 'value'}")
            if clean_key != key or clean_value != value:
                modified = True
            sanitized_pairs.append((clean_key, clean_value))
        if modified:
            request.scope["query_string"] = urlencode(sanitized_pairs, doseq=True).encode("utf-8")

    def _sanitize_headers(self, request: Request) -> None:
        headers = list(request.scope.get("headers") or [])
        if not headers:
            return
        sanitized_headers: list[tuple[bytes, bytes]] = []
        modified = False
        for raw_name, raw_value in headers:
            name = raw_name.decode("latin-1", errors="ignore")
            value = raw_value.decode("latin-1", errors="ignore")
            lower_name = name.lower()
            inspect_for_injection = lower_name not in _SIGNATURE_HEADER_NAMES
            clean_value = sanitize_text_input(
                value,
                location=f"header.{lower_name}",
                inspect_for_injection=inspect_for_injection,
            )
            if clean_value != value:
                modified = True
            sanitized_headers.append((raw_name, clean_value.encode("latin-1", errors="ignore")))
        if modified:
            request.scope["headers"] = sanitized_headers

    async def _sanitize_body(self, request: Request) -> None:
        path = request.url.path or "/"
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if not content_type or not any(content_type.startswith(prefix) for prefix in _TEXTUAL_CONTENT_TYPES):
            return
        raw_body = await request.body()
        if not raw_body:
            return
        if path.endswith(_BODY_PRESERVING_PATH_SUFFIXES):
            sanitize_text_input(
                raw_body.decode("utf-8", errors="ignore"),
                location="body.raw",
            )
            return
        updated_body = raw_body
        if content_type == "application/json":
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except json.JSONDecodeError:
                sanitize_text_input(raw_body.decode("utf-8", errors="ignore"), location="body.raw")
                return
            sanitized_payload = sanitize_input_structure(payload, location="body")
            serialized = json.dumps(sanitized_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            if serialized != raw_body:
                updated_body = serialized
        elif content_type == "application/x-www-form-urlencoded":
            parsed = parse_qsl(raw_body.decode("utf-8", errors="ignore"), keep_blank_values=True)
            sanitized_pairs = []
            for key, value in parsed:
                sanitized_pairs.append(
                    (
                        sanitize_text_input(key, location=f"body.{key or 'key'}"),
                        sanitize_text_input(value, location=f"body.{key or 'value'}"),
                    )
                )
            updated_body = urlencode(sanitized_pairs, doseq=True).encode("utf-8")
        else:
            sanitized_text = sanitize_text_input(
                raw_body.decode("utf-8", errors="ignore"),
                location="body.raw",
            )
            updated_body = sanitized_text.encode("utf-8")
        if updated_body != raw_body:
            self._replace_request_body(request, updated_body)

    def _replace_request_body(self, request: Request, body: bytes) -> None:
        request._body = body

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive
        updated_headers: list[tuple[bytes, bytes]] = []
        content_length_updated = False
        for raw_name, raw_value in list(request.scope.get("headers") or []):
            if raw_name.lower() == b"content-length":
                updated_headers.append((raw_name, str(len(body)).encode("ascii")))
                content_length_updated = True
            else:
                updated_headers.append((raw_name, raw_value))
        if not content_length_updated:
            updated_headers.append((b"content-length", str(len(body)).encode("ascii")))
        request.scope["headers"] = updated_headers

    def _audit_blocked_request(self, request: Request, error: SuspiciousInputError) -> None:
        from app.risk_ops_engine.service import RiskOpsService

        session_factory = getattr(request.app.state, "session_factory", None)
        if session_factory is None:
            return
        actor_user_id = extract_access_token_subject(request)
        with session_factory() as session:
            RiskOpsService(session).log_audit(
                actor_user_id=actor_user_id,
                action_key="security.input.blocked",
                resource_type="http_request",
                resource_id=None,
                detail=f"Blocked suspicious request input at {error.location}.",
                metadata_json={
                    "location": error.location,
                    "reason": error.reason,
                    "snippet": error.snippet,
                    "path": request.url.path,
                    "method": request.method.upper(),
                    "client_ip": extract_client_ip(request),
                },
                outcome="blocked",
            )
            session.commit()


def _snippet(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = " ".join(value.split())
    if not trimmed:
        return None
    return trimmed[:_MAX_AUDIT_SNIPPET_LENGTH]


__all__ = [
    "RequestHardeningMiddleware",
    "SuspiciousInputError",
    "extract_access_token_subject",
    "extract_client_ip",
    "sanitize_input_structure",
    "sanitize_text_input",
]
