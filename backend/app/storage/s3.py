from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

import httpx

from app.storage.base import ObjectStorage, StorageError, StorageNotFound, StorageObject

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_key(key: str) -> str:
    raw = (key or "").strip().lstrip("/")
    candidate = PurePosixPath(raw)
    if not candidate.parts:
        raise ValueError("Storage key must not be empty.")
    if any(part in {"..", "."} for part in candidate.parts):
        raise ValueError("Storage key contains invalid segments.")
    return candidate.as_posix()


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _hmac_sha256(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = _hmac_sha256(k_date, region_name)
    k_service = _hmac_sha256(k_region, service_name)
    return _hmac_sha256(k_service, "aws4_request")


@dataclass(slots=True)
class S3ObjectStorage(ObjectStorage):
    """Production durable cloud object storage adapter (S3, Cloudflare R2, MinIO, Supabase S3).

    Survives container redeployments and restarts, supports concurrent multi-instance
    access, provides durable backup through provider replication, and maintains stable object keys.
    """

    bucket: str
    endpoint_url: str = "https://s3.amazonaws.com"
    region: str = "us-east-1"
    access_key_id: str | None = None
    secret_access_key: str | None = None
    session_token: str | None = None
    local_cache_root: Path = field(
        default_factory=lambda: Path(os.getenv("GTE_STORAGE_CACHE_ROOT", "/tmp/gtex_storage_cache"))
    )
    timeout_seconds: float = 30.0

    def _sign_headers(
        self,
        *,
        method: str,
        path: str,
        query: str = "",
        headers: dict[str, str] | None = None,
        payload: bytes = b"",
    ) -> dict[str, str]:
        req_headers = dict(headers or {})
        if not self.access_key_id or not self.secret_access_key:
            return req_headers

        now = _utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        endpoint_parsed = httpx.URL(self.endpoint_url)
        host = endpoint_parsed.host
        if endpoint_parsed.port and endpoint_parsed.port not in {80, 443}:
            host = f"{host}:{endpoint_parsed.port}"

        req_headers["host"] = host
        req_headers["x-amz-date"] = amz_date
        payload_hash = hashlib.sha256(payload).hexdigest()
        req_headers["x-amz-content-sha256"] = payload_hash

        if self.session_token:
            req_headers["x-amz-security-token"] = self.session_token

        sorted_headers = sorted((k.lower(), v.strip()) for k, v in req_headers.items())
        canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted_headers)
        signed_headers = ";".join(k for k, _ in sorted_headers)

        canonical_uri = quote(path, safe="/-_.~")
        canonical_query = query

        canonical_request = (
            f"{method.upper()}\n"
            f"{canonical_uri}\n"
            f"{canonical_query}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        string_to_sign = (
            f"{algorithm}\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = _get_signature_key(self.secret_access_key, date_stamp, self.region, "s3")
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization = (
            f"{algorithm} Credential={self.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        req_headers["authorization"] = authorization
        return req_headers

    def _object_url(self, key: str) -> tuple[str, str]:
        normalized = _normalize_key(key)
        base = self.endpoint_url.rstrip("/")
        # Path-style: base / bucket / key
        url = f"{base}/{self.bucket}/{normalized}"
        path = f"/{self.bucket}/{normalized}"
        return url, path

    def put_bytes(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> StorageObject:
        normalized = _normalize_key(key)
        url, path = self._object_url(normalized)
        headers = {
            "content-type": content_type,
            "content-length": str(len(content)),
        }
        if metadata:
            meta_json = json.dumps(metadata, sort_keys=True)
            headers["x-amz-meta-custom-meta"] = quote(meta_json)

        signed_headers = self._sign_headers(method="PUT", path=path, headers=headers, payload=content)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                res = client.put(url, headers=signed_headers, content=content)
            if res.status_code not in {200, 201}:
                raise StorageError(f"Failed to put object to S3: status {res.status_code} - {res.text[:200]}")
        except httpx.HTTPError as ex:
            raise StorageError(f"S3 connection error during put_bytes: {ex}") from ex

        payload_meta = dict(metadata or {})
        payload_meta.setdefault("content_type", content_type)
        payload_meta.setdefault("size_bytes", len(content))
        payload_meta.setdefault("updated_at", _utcnow().isoformat())

        return StorageObject(
            key=normalized,
            size_bytes=len(content),
            content_type=content_type,
            metadata=payload_meta,
            updated_at=_utcnow(),
        )

    def get_bytes(self, *, key: str) -> bytes:
        normalized = _normalize_key(key)
        url, path = self._object_url(normalized)
        signed_headers = self._sign_headers(method="GET", path=path)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                res = client.get(url, headers=signed_headers)
            if res.status_code == 404:
                raise StorageNotFound(f"Storage key not found: {key}")
            if res.status_code != 200:
                raise StorageError(f"Failed to get object from S3: status {res.status_code}")
            return res.content
        except httpx.HTTPError as ex:
            raise StorageError(f"S3 connection error during get_bytes: {ex}") from ex

    def open_file(self, *, key: str) -> Path:
        normalized = _normalize_key(key)
        cache_path = (self.local_cache_root / normalized).resolve()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.get_bytes(key=normalized)
        cache_path.write_bytes(content)
        return cache_path

    def delete(self, *, key: str) -> None:
        normalized = _normalize_key(key)
        url, path = self._object_url(normalized)
        signed_headers = self._sign_headers(method="DELETE", path=path)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                res = client.delete(url, headers=signed_headers)
            if res.status_code not in {200, 204, 404}:
                raise StorageError(f"Failed to delete object from S3: status {res.status_code}")
        except httpx.HTTPError as ex:
            raise StorageError(f"S3 connection error during delete: {ex}") from ex

    def exists(self, *, key: str) -> bool:
        normalized = _normalize_key(key)
        url, path = self._object_url(normalized)
        signed_headers = self._sign_headers(method="HEAD", path=path)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                res = client.head(url, headers=signed_headers)
            return res.status_code == 200
        except httpx.HTTPError:
            return False

    def list_prefix(self, *, prefix: str) -> list[str]:
        # Minimal S3 list-objects-v2 query
        base = self.endpoint_url.rstrip("/")
        query = f"list-type=2&prefix={quote(prefix)}"
        url = f"{base}/{self.bucket}?{query}"
        path = f"/{self.bucket}"
        signed_headers = self._sign_headers(method="GET", path=path, query=query)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                res = client.get(url, headers=signed_headers)
            if res.status_code != 200:
                return []
            import xml.etree.ElementTree as ET

            root = ET.fromstring(res.text)
            keys: list[str] = []
            ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
            for elem in root.findall(".//s3:Contents/s3:Key", ns):
                if elem.text:
                    keys.append(elem.text)
            if not keys:
                for elem in root.findall(".//Key"):
                    if elem.text:
                        keys.append(elem.text)
            return sorted(keys)
        except Exception as ex:
            logger.warning("Could not list S3 prefix %s: %s", prefix, ex)
            return []

    def read_metadata(self, *, key: str) -> dict[str, Any]:
        normalized = _normalize_key(key)
        url, path = self._object_url(normalized)
        signed_headers = self._sign_headers(method="HEAD", path=path)
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                res = client.head(url, headers=signed_headers)
            if res.status_code != 200:
                return {}
            meta_header = res.headers.get("x-amz-meta-custom-meta")
            if meta_header:
                from urllib.parse import unquote

                return json.loads(unquote(meta_header))
            return {
                "content_type": res.headers.get("content-type"),
                "size_bytes": int(res.headers.get("content-length", 0)),
            }
        except Exception:
            return {}


__all__ = ["S3ObjectStorage"]
