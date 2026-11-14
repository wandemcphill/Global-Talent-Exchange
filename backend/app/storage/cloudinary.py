from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import logging
import os
from pathlib import Path, PurePosixPath
import re
import time
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.storage.base import ObjectStorage, StorageError, StorageNotFound, StorageObject

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


COMMERCIAL_FOLDER_BY_ASSET_KIND: dict[str, str] = {
    "logo": "gtex/commercial/brands/logos",
    "brand_image": "gtex/commercial/brands/creatives",
    "brand_video": "gtex/commercial/brands/videos",
    "music_audio": "gtex/commercial/music/audio",
    "music_artwork": "gtex/commercial/music/artwork",
}

COMMERCIAL_RESOURCE_TYPE_BY_ASSET_KIND: dict[str, str] = {
    "logo": "image",
    "brand_image": "image",
    "music_artwork": "image",
    "brand_video": "video",
    "music_audio": "video",  # Cloudinary treats audio files (MP3, WAV, OGG, M4A, AAC) as 'video' resource_type
}


def sign_cloudinary_params(params: dict[str, Any], api_secret: str) -> str:
    """Create a Cloudinary SHA-1 request signature over sorted non-empty parameters.

    Never log ``api_secret`` or the raw signature string in production logs.
    """
    filtered = {
        str(k): str(v)
        for k, v in params.items()
        if v is not None and str(v) != "" and k not in {"file", "cloud_name", "resource_type", "api_key", "signature"}
    }
    to_sign = "&".join(f"{key}={filtered[key]}" for key in sorted(filtered))
    return hashlib.sha1(f"{to_sign}{api_secret}".encode("utf-8")).hexdigest()  # nosec B324


def sanitize_workspace_segment(workspace_id: str | None) -> str:
    raw = (workspace_id or "global").strip()
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_-")
    return (cleaned or "global")[:64]


def resolve_commercial_cloudinary_folder(asset_kind: str, workspace_id: str | None = None) -> str:
    base_folder = COMMERCIAL_FOLDER_BY_ASSET_KIND.get(asset_kind, "gtex/commercial/brands/creatives")
    ws_segment = sanitize_workspace_segment(workspace_id)
    return f"{base_folder}/{ws_segment}"


def resolve_commercial_resource_type(
    asset_kind: str | None = None,
    *,
    content_type: str | None = None,
    key: str | None = None,
) -> str:
    """Resolve the canonical Cloudinary resource_type ('image' or 'video').

    Cloudinary requires audio assets (MP3, WAV, OGG, M4A, AAC) to use resource_type='video'.
    """
    if asset_kind and asset_kind in COMMERCIAL_RESOURCE_TYPE_BY_ASSET_KIND:
        return COMMERCIAL_RESOURCE_TYPE_BY_ASSET_KIND[asset_kind]
    if content_type:
        lowered = content_type.lower().strip()
        if lowered.startswith(("video/", "audio/")):
            return "video"
        if lowered.startswith("image/"):
            return "image"
    if key:
        lowered_key = key.lower()
        if (
            "/videos/" in lowered_key
            or "/music/audio/" in lowered_key
            or "/brand_video/" in lowered_key
            or "/music_audio/" in lowered_key
        ):
            return "video"
        if lowered_key.endswith((".mp4", ".webm", ".mp3", ".wav", ".ogg", ".m4a", ".aac")):
            return "video"
    return "image"


def generate_commercial_public_id(asset_kind: str, workspace_id: str | None = None) -> tuple[str, str, str]:
    """Generate (folder, leaf_public_id, full_public_id) with an unpredictable unique identifier."""
    folder = resolve_commercial_cloudinary_folder(asset_kind, workspace_id)
    kind_slug = re.sub(r"[^a-z0-9_]+", "_", (asset_kind or "asset").lower()).strip("_") or "asset"
    leaf_id = f"{kind_slug}_{uuid4().hex}"
    full_public_id = f"{folder}/{leaf_id}"
    return folder, leaf_id, full_public_id


def _normalize_public_id(key: str) -> str:
    raw = (key or "").strip().lstrip("/")
    if not raw:
        raise ValueError("Cloudinary public_id / storage key must not be empty.")
    candidate = PurePosixPath(raw)
    if any(part in {"..", "."} for part in candidate.parts):
        raise ValueError("Cloudinary public_id contains invalid path traversal segments.")
    return candidate.as_posix()


def _escape_context_value(value: str) -> str:
    cleaned = str(value or "").replace("|", "_").replace("=", "_")
    return re.sub(r"[\r\n\t]+", " ", cleaned).strip()[:200]


@dataclass(slots=True)
class CloudinaryObjectStorage(ObjectStorage):
    """Production Cloudinary media storage adapter for the GTEX Commercial Advertising Network.

    Uses signed server-side REST calls over httpx without exposing API secrets to the browser.
    """

    cloud_name: str
    api_key: str
    api_secret: str
    api_base_url: str = "https://api.cloudinary.com/v1_1"
    delivery_base_url: str = "https://res.cloudinary.com"
    local_cache_root: Path = field(
        default_factory=lambda: Path(os.getenv("GTE_STORAGE_CACHE_ROOT", "/tmp/gtex_cloudinary_cache"))
    )
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("GTE_CLOUDINARY_TIMEOUT_SECONDS", "120.0")))
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> "CloudinaryObjectStorage":
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
        api_key = os.getenv("CLOUDINARY_API_KEY", "").strip()
        api_secret = os.getenv("CLOUDINARY_API_SECRET", "").strip()
        if not (cloud_name and api_key and api_secret):
            cloudinary_url = os.getenv("CLOUDINARY_URL", "").strip()
            if cloudinary_url.startswith("cloudinary://"):
                from urllib.parse import urlsplit

                parsed = urlsplit(cloudinary_url)
                cloud_name = cloud_name or (parsed.hostname or "").strip()
                api_key = api_key or (parsed.username or "").strip()
                api_secret = api_secret or (parsed.password or "").strip()
        return cls(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
        )

    def is_configured(self) -> bool:
        return bool(
            self.cloud_name
            and self.cloud_name.strip()
            and self.api_key
            and self.api_key.strip()
            and self.api_secret
            and self.api_secret.strip()
        )

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise StorageError(
                "Cloudinary storage is not configured. Required environment variables: "
                "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET."
            )

    def build_delivery_url(
        self,
        public_id: str,
        *,
        resource_type: str = "image",
        delivery_type: str = "upload",
        version: int | str | None = None,
        fmt: str | None = None,
        format_ext: str | None = None,
        signed: bool = False,
    ) -> str:
        """Construct a canonical HTTPS Cloudinary CDN delivery URL."""
        self._require_configured()
        normalized_id = _normalize_public_id(public_id)
        res_type = resource_type if resource_type in {"image", "video", "raw"} else "image"
        deliv_type = delivery_type if delivery_type in {"upload", "authenticated", "private"} else "upload"
        resolved_fmt = fmt or format_ext

        path_target = normalized_id
        if resolved_fmt and not path_target.lower().endswith(f".{resolved_fmt.lower()}"):
            path_target = f"{path_target}.{resolved_fmt.lower()}"

        encoded_target = "/".join(quote(segment, safe="-_.") for segment in path_target.split("/"))
        version_segment = f"/v{version}" if version else ""

        sig_segment = ""
        if signed or deliv_type in {"authenticated", "private"}:
            # Cloudinary signed delivery URL token: s--<8_char_base64url_sha1>-- over path_target + api_secret
            import base64

            to_sign = f"{path_target}{self.api_secret}".encode("utf-8")
            digest = hashlib.sha1(to_sign).digest()  # nosec B324
            short_sig = base64.urlsafe_b64encode(digest).decode("ascii")[:8]
            sig_segment = f"/s--{short_sig}--"

        base = self.delivery_base_url.rstrip("/")
        return f"{base}/{self.cloud_name}/{res_type}/{deliv_type}{sig_segment}{version_segment}/{encoded_target}"

    def put_bytes(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, Any] | None = None,
        resource_type: str | None = None,
        max_retries: int | None = None,
    ) -> StorageObject:
        self._require_configured()
        if not content:
            raise StorageError("Cannot upload empty media content to Cloudinary.")

        meta = dict(metadata or {})
        asset_kind = str(meta.get("asset_kind") or "").strip() or None
        workspace_id = str(meta.get("workspace_id") or "").strip() or None
        original_filename = str(meta.get("original_filename") or "upload.bin").strip()
        delivery_type = str(meta.get("delivery_type") or "authenticated").strip()
        if delivery_type not in {"upload", "authenticated", "private"}:
            delivery_type = "authenticated"

        resolved_resource_type = (
            (resource_type or "").strip()
            or str(meta.get("resource_type") or "").strip()
            or resolve_commercial_resource_type(
                asset_kind,
                content_type=content_type,
                key=key,
            )
        )
        retries = self.max_retries if max_retries is None else max(0, int(max_retries))

        normalized_key = _normalize_public_id(key)
        # Split folder and leaf public_id so Cloudinary stores the exact folder hierarchy
        if "/" in normalized_key:
            folder, leaf_public_id = normalized_key.rsplit("/", 1)
        elif asset_kind:
            folder = resolve_commercial_cloudinary_folder(asset_kind, workspace_id)
            leaf_public_id = normalized_key
        else:
            folder = "gtex/commercial/brands/creatives/global"
            leaf_public_id = normalized_key

        # Remove file extension from public_id leaf if present so Cloudinary doesn't double-extension
        leaf_stem = re.sub(
            r"\.(png|jpg|jpeg|webp|mp4|webm|mp3|wav|ogg|m4a|aac|bin)$", "", leaf_public_id, flags=re.IGNORECASE
        )
        leaf_public_id = leaf_stem or leaf_public_id

        timestamp = str(int(time.time()))
        context_pairs: list[str] = []
        if original_filename:
            context_pairs.append(f"original_filename={_escape_context_value(original_filename)}")
        if workspace_id:
            context_pairs.append(f"workspace_id={_escape_context_value(workspace_id)}")
        if asset_kind:
            context_pairs.append(f"asset_kind={_escape_context_value(asset_kind)}")
        if meta.get("sha256"):
            context_pairs.append(f"sha256={_escape_context_value(str(meta['sha256']))}")

        signed_params: dict[str, str] = {
            "folder": folder,
            "overwrite": "true",
            "public_id": leaf_public_id,
            "timestamp": timestamp,
            "unique_filename": "false",
            "use_filename": "false",
        }
        if delivery_type != "upload":
            signed_params["type"] = delivery_type
        if context_pairs:
            signed_params["context"] = "|".join(context_pairs)

        signature = sign_cloudinary_params(signed_params, self.api_secret)
        form_data = {
            **signed_params,
            "api_key": self.api_key,
            "signature": signature,
        }
        upload_url = f"{self.api_base_url.rstrip('/')}/{self.cloud_name}/{resolved_resource_type}/upload"

        last_error: Exception | None = None
        response: httpx.Response | None = None
        for attempt in range(retries + 1):
            try:
                response = httpx.post(
                    upload_url,
                    data=form_data,
                    files={"file": (original_filename or f"{leaf_public_id}.bin", content, content_type)},
                    timeout=self.timeout_seconds,
                )
                if response.status_code < 500:
                    break
                last_error = StorageError(f"Cloudinary upload returned transient status {response.status_code}.")
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "Cloudinary upload transport error on attempt %d/%d for folder %s",
                    attempt + 1,
                    retries + 1,
                    folder,
                )
            if attempt < retries:
                time.sleep(0.05 * (attempt + 1))

        if response is None:
            raise StorageError("Cloudinary upload failed due to network transport error.") from last_error

        if response.status_code >= 400:
            logger.error(
                "Cloudinary rejected media upload (status=%s, resource_type=%s, folder=%s)",
                response.status_code,
                resolved_resource_type,
                folder,
            )
            raise StorageError(f"Cloudinary rejected media upload with status {response.status_code}.")

        try:
            payload = response.json()
        except ValueError as exc:
            raise StorageError("Cloudinary upload returned invalid JSON response.") from exc

        public_id = str(payload.get("public_id") or f"{folder}/{leaf_public_id}").strip()
        secure_url = str(payload.get("secure_url") or payload.get("url") or "").strip()
        returned_resource_type = str(payload.get("resource_type") or resolved_resource_type).strip()
        version = payload.get("version")
        fmt = payload.get("format")

        if not secure_url:
            secure_url = self.build_delivery_url(
                public_id,
                resource_type=returned_resource_type,
                delivery_type=delivery_type,
                version=version,
                fmt=fmt,
            )

        bytes_uploaded = int(payload.get("bytes") or len(content))
        now = _utcnow()
        result_meta: dict[str, Any] = {
            **meta,
            "storage_provider": "cloudinary",
            "cloudinary_public_id": public_id,
            "cloudinary_asset_id": payload.get("asset_id"),
            "cloudinary_version": version,
            "resource_type": returned_resource_type,
            "delivery_type": str(payload.get("type") or delivery_type),
            "secure_url": secure_url,
            "format": fmt,
            "bytes": bytes_uploaded,
            "width": payload.get("width"),
            "height": payload.get("height"),
            "duration": payload.get("duration"),
            "etag": payload.get("etag"),
            "original_filename": original_filename,
            "folder": folder,
            "content_type": content_type,
            "updated_at": now.isoformat(),
        }

        return StorageObject(
            key=public_id,
            size_bytes=bytes_uploaded,
            content_type=content_type,
            metadata=result_meta,
            updated_at=now,
        )

    def get_bytes(
        self,
        *,
        key: str,
        resource_type: str | None = None,
        delivery_url: str | None = None,
    ) -> bytes:
        self._require_configured()
        normalized = _normalize_public_id(key)
        resolved_type = resource_type or resolve_commercial_resource_type(key=normalized)
        target_url = delivery_url or self.build_delivery_url(normalized, resource_type=resolved_type)
        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
                res = client.get(target_url)
            if res.status_code == 404:
                raise StorageNotFound(f"Cloudinary asset not found: {normalized}")
            if res.status_code != 200:
                raise StorageError(f"Failed to retrieve Cloudinary asset (status {res.status_code}).")
            return res.content
        except httpx.HTTPError as exc:
            raise StorageError("Network error while retrieving asset from Cloudinary CDN.") from exc

    def open_file(self, *, key: str) -> Path:
        normalized = _normalize_public_id(key)
        cache_path = (self.local_cache_root / normalized).resolve()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.get_bytes(key=normalized)
        cache_path.write_bytes(content)
        return cache_path

    def delete(
        self,
        *,
        key: str,
        resource_type: str | None = None,
        delivery_type: str = "upload",
    ) -> None:
        self._require_configured()
        normalized = _normalize_public_id(key)
        resolved_type = resource_type or resolve_commercial_resource_type(key=normalized)
        timestamp = str(int(time.time()))
        signed_params: dict[str, str] = {
            "invalidate": "true",
            "public_id": normalized,
            "timestamp": timestamp,
        }
        if delivery_type and delivery_type != "upload":
            signed_params["type"] = delivery_type

        signature = sign_cloudinary_params(signed_params, self.api_secret)
        data = {
            **signed_params,
            "api_key": self.api_key,
            "signature": signature,
        }
        destroy_url = f"{self.api_base_url.rstrip('/')}/{self.cloud_name}/{resolved_type}/destroy"
        try:
            res = httpx.post(destroy_url, data=data, timeout=self.timeout_seconds)
            if res.status_code >= 400:
                raise StorageError(f"Cloudinary destroy failed with status {res.status_code}.")
            payload = res.json()
            result_status = str(payload.get("result") or "").lower()
            if result_status not in {"ok", "not found"}:
                raise StorageError(f"Cloudinary destroy returned unexpected result '{result_status}'.")
        except httpx.HTTPError as exc:
            raise StorageError("Cloudinary network error during asset deletion.") from exc

    def revoke_public_delivery(
        self,
        *,
        key: str,
        resource_type: str | None = None,
        delivery_type: str = "authenticated",
        fmt: str | None = None,
    ) -> dict[str, Any]:
        """Revoke any previously distributed Cloudinary CDN URL for this asset.

        Uses Cloudinary's signed ``rename`` endpoint with ``invalidate=true`` to rotate
        the asset's ``public_id`` and purge the old URL from the CDN edge cache while
        keeping the asset intact under the rotated key for workspace/admin preview or
        future campaign reactivation.
        """
        self._require_configured()
        normalized = _normalize_public_id(key)
        resolved_type = resource_type or resolve_commercial_resource_type(key=normalized)
        deliv_type = delivery_type if delivery_type in {"upload", "authenticated", "private"} else "authenticated"
        base_key = re.sub(r"_rev[0-9a-f]{8}$", "", normalized)
        new_public_id = f"{base_key}_rev{uuid4().hex[:8]}"
        timestamp = str(int(time.time()))

        signed_params: dict[str, str] = {
            "from_public_id": normalized,
            "invalidate": "true",
            "overwrite": "true",
            "timestamp": timestamp,
            "to_public_id": new_public_id,
        }
        if deliv_type != "upload":
            signed_params["type"] = deliv_type

        signature = sign_cloudinary_params(signed_params, self.api_secret)
        data = {
            **signed_params,
            "api_key": self.api_key,
            "signature": signature,
        }
        rename_url = f"{self.api_base_url.rstrip('/')}/{self.cloud_name}/{resolved_type}/rename"
        try:
            res = httpx.post(rename_url, data=data, timeout=self.timeout_seconds)
            if res.status_code >= 400:
                raise StorageError(f"Cloudinary rename/invalidate failed with status {res.status_code}.")
            payload = res.json() if res.content else {}
        except httpx.HTTPError as exc:
            raise StorageError("Cloudinary network error during URL revocation.") from exc

        returned_public_id = str(payload.get("public_id") or new_public_id).strip()
        returned_version = payload.get("version")
        returned_fmt = payload.get("format") or fmt
        returned_delivery_type = str(payload.get("type") or deliv_type).strip()
        new_secure_url = str(payload.get("secure_url") or "").strip()
        if not new_secure_url:
            new_secure_url = self.build_delivery_url(
                returned_public_id,
                resource_type=resolved_type,
                delivery_type=returned_delivery_type,
                version=returned_version,
                fmt=returned_fmt,
                signed=True,
            )
        return {
            "previous_public_id": normalized,
            "new_public_id": returned_public_id,
            "secure_url": new_secure_url,
            "version": returned_version,
            "format": returned_fmt,
            "delivery_type": returned_delivery_type,
            "cdn_invalidated": True,
            "revoked_at": _utcnow().isoformat(),
        }

    def exists(
        self,
        *,
        key: str,
        resource_type: str | None = None,
        delivery_url: str | None = None,
    ) -> bool:
        self._require_configured()
        normalized = _normalize_public_id(key)
        resolved_type = resource_type or resolve_commercial_resource_type(key=normalized)
        target_url = delivery_url or self.build_delivery_url(normalized, resource_type=resolved_type)
        try:
            with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
                res = client.head(target_url)
            return res.status_code == 200
        except httpx.HTTPError:
            return False

    def list_prefix(
        self,
        *,
        prefix: str,
        resource_type: str | None = None,
        max_results: int = 500,
    ) -> list[str]:
        """List Cloudinary public_ids under a given prefix via the Admin Resources API."""
        self._require_configured()
        normalized_prefix = _normalize_public_id(prefix) if prefix.strip("/") else "gtex/commercial"
        resource_types = [resource_type] if resource_type else ["image", "video"]
        found_keys: list[str] = []

        for rtype in resource_types:
            for dtype in ("authenticated", "upload"):
                url = f"{self.api_base_url.rstrip('/')}/{self.cloud_name}/resources/{rtype}/{dtype}"
                params = {"prefix": normalized_prefix, "max_results": str(min(max_results, 500))}
                try:
                    with httpx.Client(timeout=self.timeout_seconds, auth=(self.api_key, self.api_secret)) as client:
                        res = client.get(url, params=params)
                    if res.status_code != 200:
                        continue
                    payload = res.json()
                    for item in payload.get("resources") or []:
                        pub_id = item.get("public_id")
                        if pub_id:
                            found_keys.append(str(pub_id))
                except Exception as exc:
                    logger.warning(
                        "Could not list Cloudinary resources for prefix %s (%s/%s): %s",
                        normalized_prefix,
                        rtype,
                        dtype,
                        exc,
                    )

        return sorted(set(found_keys))

    def read_metadata(
        self,
        *,
        key: str,
        resource_type: str | None = None,
        delivery_type: str | None = None,
    ) -> dict[str, Any]:
        self._require_configured()
        normalized = _normalize_public_id(key)
        resolved_type = resource_type or resolve_commercial_resource_type(key=normalized)
        encoded_id = "/".join(quote(segment, safe="-_.") for segment in normalized.split("/"))
        dtypes = [delivery_type] if delivery_type else ["authenticated", "upload"]
        for dtype in dtypes:
            url = f"{self.api_base_url.rstrip('/')}/{self.cloud_name}/resources/{resolved_type}/{dtype}/{encoded_id}"
            try:
                with httpx.Client(timeout=self.timeout_seconds, auth=(self.api_key, self.api_secret)) as client:
                    res = client.get(url)
                if res.status_code != 200:
                    continue
                payload = res.json()
                return {
                    "public_id": payload.get("public_id"),
                    "asset_id": payload.get("asset_id"),
                    "resource_type": payload.get("resource_type"),
                    "delivery_type": payload.get("type") or dtype,
                    "format": payload.get("format"),
                    "version": payload.get("version"),
                    "bytes": payload.get("bytes"),
                    "width": payload.get("width"),
                    "height": payload.get("height"),
                    "secure_url": payload.get("secure_url"),
                    "created_at": payload.get("created_at"),
                    "context": payload.get("context"),
                }
            except Exception:
                continue
        return {}


__all__ = [
    "COMMERCIAL_FOLDER_BY_ASSET_KIND",
    "COMMERCIAL_RESOURCE_TYPE_BY_ASSET_KIND",
    "CloudinaryObjectStorage",
    "generate_commercial_public_id",
    "resolve_commercial_cloudinary_folder",
    "resolve_commercial_resource_type",
    "sanitize_workspace_segment",
    "sign_cloudinary_params",
]
