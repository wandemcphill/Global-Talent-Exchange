from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import logging
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, Request

from app.core.cache import CacheBackend, NullCacheBackend

logger = logging.getLogger(__name__)


def normalize_query_params(request: Request) -> str:
    items: list[tuple[str, str]] = []
    for key, value in sorted(request.query_params.multi_items()):
        normalized_key = str(key).strip().lower()
        normalized_value = " ".join(str(value).strip().split())
        items.append((normalized_key, normalized_value))
    return urlencode(items, doseq=True)


@dataclass(slots=True)
class NamespacedResponseCache:
    backend: CacheBackend
    key_prefix: str = "gte:api_cache"

    def get_json(
        self,
        *,
        namespace: str,
        route: str,
        request: Request,
        scope_key: str | None = None,
    ) -> Any | None:
        key = self.build_key(namespace=namespace, route=route, request=request, scope_key=scope_key)
        raw_value = self.backend.get(key)
        if raw_value is None:
            return None
        try:
            return json.loads(raw_value)
        except json.JSONDecodeError:
            logger.warning("response_cache.decode_failed namespace=%s route=%s", namespace, route)
            return None

    def set_json(
        self,
        *,
        namespace: str,
        route: str,
        request: Request,
        payload: Any,
        ttl_seconds: int,
        scope_key: str | None = None,
    ) -> None:
        key = self.build_key(namespace=namespace, route=route, request=request, scope_key=scope_key)
        self.backend.set(key, json.dumps(payload, default=str), ttl_seconds)

    def invalidate(self, namespace: str) -> int:
        version_key = self._version_key(namespace)
        next_version = self.backend.increment(version_key, 1)
        return next_version or 1

    def build_key(
        self,
        *,
        namespace: str,
        route: str,
        request: Request,
        scope_key: str | None = None,
    ) -> str:
        version = self._version(namespace)
        normalized_query = normalize_query_params(request)
        digest = sha256(normalized_query.encode("utf-8")).hexdigest()[:24]
        resolved_scope = (scope_key or "global").strip() or "global"
        return f"{self.key_prefix}:{namespace}:v{version}:{route}:{resolved_scope}:{digest}"

    def _version(self, namespace: str) -> int:
        raw_value = self.backend.get(self._version_key(namespace))
        if raw_value is None:
            return 1
        try:
            return max(1, int(raw_value))
        except (TypeError, ValueError):
            return 1

    def _version_key(self, namespace: str) -> str:
        return f"{self.key_prefix}:{namespace}:version"


def get_response_cache(app: FastAPI) -> NamespacedResponseCache:
    cached = getattr(app.state, "response_cache", None)
    if cached is None:
        backend = getattr(app.state, "cache_backend", None)
        cached = NamespacedResponseCache(backend=backend or NullCacheBackend())
        app.state.response_cache = cached
    return cached


__all__ = ["NamespacedResponseCache", "get_response_cache", "normalize_query_params"]
