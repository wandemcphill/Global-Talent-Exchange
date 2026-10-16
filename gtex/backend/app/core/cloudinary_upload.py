"""Signed Cloudinary uploads for sensitive KYC documents.

KYC files (government ID, selfie, proof of address) are uploaded to Cloudinary as
``type=authenticated`` assets (not publicly reachable by URL) under a ``kyc/`` folder.
Uses a signed REST upload so no extra SDK dependency is required -- only ``httpx``,
which is already a dependency.

Configuration (set on the backend host, e.g. Render):
    CLOUDINARY_CLOUD_NAME   - cloud name (already used for player image URLs)
    CLOUDINARY_API_KEY      - API key
    CLOUDINARY_API_SECRET   - API secret

When any of these are missing, :func:`cloudinary_configured` returns False so callers
can surface a clear "KYC uploads are not configured" error instead of failing opaquely.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass

import httpx

_KYC_FOLDER = "kyc"
_UPLOAD_TIMEOUT_SECONDS = 30.0


class CloudinaryUploadError(RuntimeError):
    """Raised when a KYC document upload cannot be completed."""


@dataclass(frozen=True, slots=True)
class CloudinaryAsset:
    public_id: str
    secure_url: str
    resource_type: str
    bytes_uploaded: int


def _cloud_name() -> str:
    return os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()


def _api_key() -> str:
    return os.environ.get("CLOUDINARY_API_KEY", "").strip()


def _api_secret() -> str:
    return os.environ.get("CLOUDINARY_API_SECRET", "").strip()


def cloudinary_configured() -> bool:
    """True when all credentials required for signed uploads are present."""
    return bool(_cloud_name() and _api_key() and _api_secret())


def _sign(params: dict[str, str], api_secret: str) -> str:
    # Cloudinary signature: sha1 of "k=v&k=v..." (sorted, excluding file/api_key/etc.) + secret.
    to_sign = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{to_sign}{api_secret}".encode()).hexdigest()


def upload_kyc_document(
    content: bytes,
    *,
    user_id: str,
    doc_kind: str,
    filename: str | None = None,
    content_type: str | None = None,
) -> CloudinaryAsset:
    """Upload a single KYC document to Cloudinary and return its stored identifiers.

    ``doc_kind`` is a short slug (e.g. "government_id", "selfie", "proof_of_address")
    used to build a stable-ish public id inside the per-user KYC folder.
    """
    if not content:
        raise CloudinaryUploadError("Document is empty.")
    if not cloudinary_configured():
        raise CloudinaryUploadError(
            "KYC document storage is not configured "
            "(CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET)."
        )

    cloud_name = _cloud_name()
    api_key = _api_key()
    api_secret = _api_secret()
    timestamp = str(int(time.time()))
    folder = f"{_KYC_FOLDER}/{user_id}"
    # image/pdf/etc -> let Cloudinary auto-detect the resource type.
    signed_params = {
        "folder": folder,
        "public_id": f"{doc_kind}_{timestamp}",
        "timestamp": timestamp,
        "type": "authenticated",
    }
    signature = _sign(signed_params, api_secret)
    data = {**signed_params, "api_key": api_key, "signature": signature}
    files = {"file": (filename or f"{doc_kind}.bin", content, content_type or "application/octet-stream")}
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload"

    try:
        response = httpx.post(url, data=data, files=files, timeout=_UPLOAD_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:  # network/transport failure
        raise CloudinaryUploadError(f"KYC upload failed: {exc}") from exc
    if response.status_code >= 400:
        raise CloudinaryUploadError(
            f"KYC upload rejected by storage provider ({response.status_code}): {response.text[:200]}"
        )
    payload = response.json()
    public_id = payload.get("public_id")
    secure_url = payload.get("secure_url") or payload.get("url")
    if not public_id or not secure_url:
        raise CloudinaryUploadError("KYC upload response did not include a stored asset id.")
    return CloudinaryAsset(
        public_id=str(public_id),
        secure_url=str(secure_url),
        resource_type=str(payload.get("resource_type", "image")),
        bytes_uploaded=int(payload.get("bytes", len(content))),
    )
