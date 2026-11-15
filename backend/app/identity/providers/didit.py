from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from typing import Any
from urllib.parse import urlparse

import httpx

from app.identity.providers.base import (
    BaseIdentityVerificationAdapter,
    ProviderWebhookResult,
    VerificationSessionResult,
)


class IdentityProviderConfigurationError(RuntimeError):
    """Raised when a live verification provider is not completely configured."""


class DIDitVerificationAdapter(BaseIdentityVerificationAdapter):
    API_BASE = "https://verification.didit.me/v3"

    @property
    def provider_name(self) -> str:
        return "didit"

    def _api_configuration(self) -> tuple[str, str]:
        api_key = os.environ.get("GTE_DIDIT_API_KEY") or os.environ.get("DIDIT_API_KEY")
        workflow_id = os.environ.get("GTE_DIDIT_WORKFLOW_ID") or os.environ.get("DIDIT_WORKFLOW_ID")
        missing = [
            name for name, value in (
                ("GTE_DIDIT_API_KEY", api_key),
                ("GTE_DIDIT_WORKFLOW_ID", workflow_id),
            ) if not value
        ]
        if missing:
            raise IdentityProviderConfigurationError(
                "DIDit live KYC is not configured. Missing provider credentials: " + ", ".join(missing)
            )
        return api_key.strip(), workflow_id.strip()

    def _webhook_secret(self) -> str:
        webhook_secret = os.environ.get("GTE_DIDIT_WEBHOOK_SECRET") or os.environ.get("DIDIT_WEBHOOK_SECRET")
        if not webhook_secret:
            raise IdentityProviderConfigurationError(
                "DIDit webhook verification is not configured. Add GTE_DIDIT_WEBHOOK_SECRET."
            )
        return webhook_secret.strip()

    def initiate_session(
        self,
        *,
        user_id: str,
        reference: str,
        verification_type: str = "full_kyc",
        callback_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VerificationSessionResult:
        api_key, workflow_id = self._api_configuration()
        safe_metadata = dict(metadata or {})
        contact_details: dict[str, Any] = {}
        if safe_metadata.get("email"):
            contact_details["email"] = str(safe_metadata["email"])
        if safe_metadata.get("phone"):
            contact_details["phone"] = str(safe_metadata["phone"])

        payload: dict[str, Any] = {
            "workflow_id": workflow_id,
            "vendor_data": reference,
            "callback_method": "both",
            "metadata": {
                "gtex_user_id": user_id,
                "gtex_verification_type": verification_type,
                **{
                    key: value for key, value in safe_metadata.items()
                    if key not in {"email", "phone"}
                },
            },
            "language": "en",
        }
        if callback_url:
            payload["callback"] = callback_url
        if contact_details:
            payload["contact_details"] = contact_details

        try:
            response = httpx.post(
                self.API_BASE + "/session/",
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=20.0,
            )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            raise IdentityProviderConfigurationError(
                f"DIDit rejected the KYC session request (HTTP {status_code}). Check the API key and workflow configuration."
            ) from exc
        except (httpx.RequestError, ValueError) as exc:
            raise IdentityProviderConfigurationError(
                "DIDit could not create a live verification session. No verification session was created."
            ) from exc

        session_id = result.get("session_id")
        handoff_url = result.get("url") or result.get("handoff_url")
        parsed_url = urlparse(str(handoff_url or ""))
        if not session_id or parsed_url.scheme != "https" or parsed_url.hostname != "verify.didit.me":
            raise IdentityProviderConfigurationError(
                "DIDit returned an incomplete or unsafe session response. No verification session was recorded."
            )

        return VerificationSessionResult(
            provider=self.provider_name,
            session_id=str(session_id),
            reference=reference,
            handoff_url=str(handoff_url),
            verification_type=verification_type,
            metadata={
                "workflow_id": result.get("workflow_id") or workflow_id,
                "session_status": result.get("status") or "Not Started",
            },
        )

    @staticmethod
    def _shorten_floats(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: DIDitVerificationAdapter._shorten_floats(item) for key, item in value.items()}
        if isinstance(value, list):
            return [DIDitVerificationAdapter._shorten_floats(item) for item in value]
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value

    def verify_webhook_signature(
        self,
        *,
        payload_bytes: bytes,
        headers: dict[str, str],
    ) -> bool:
        webhook_secret = self._webhook_secret()
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False

        normalized_headers = {key.lower(): value for key, value in headers.items()}
        timestamp = normalized_headers.get("x-timestamp")
        if not timestamp:
            return False
        try:
            sent_at = int(timestamp)
        except (TypeError, ValueError):
            return False
        if abs(int(datetime.now(timezone.utc).timestamp()) - sent_at) > 300:
            return False

        secret = webhook_secret.encode("utf-8")
        signature_v2 = normalized_headers.get("x-signature-v2")
        if signature_v2:
            canonical = json.dumps(
                self._shorten_floats(payload),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            expected = hmac.new(secret, canonical, sha256).hexdigest()
            if hmac.compare_digest(expected, signature_v2.strip().lower()):
                return True

        # Raw-body signature is safe to use because this route reads Request.body()
        # before parsing; unlike X-Signature-Simple, it authenticates the full decision.
        raw_signature = normalized_headers.get("x-signature")
        if raw_signature:
            expected = hmac.new(secret, payload_bytes, sha256).hexdigest()
            return hmac.compare_digest(expected, raw_signature.strip().lower())
        return False

    def parse_webhook_payload(
        self,
        *,
        payload: dict[str, Any],
    ) -> ProviderWebhookResult:
        reference = str(payload.get("vendor_data") or "")
        session_id = payload.get("session_id")
        raw_status = str(payload.get("status") or "").strip().lower()
        status_map = {
            "approved": "verified",
            "declined": "rejected",
            "in review": "requires_review",
            "resubmitted": "requires_retry",
            "not started": "pending",
            "in progress": "pending",
            "abandoned": "pending",
            "kyc expired": "requires_retry",
        }
        decision = status_map.get(raw_status, "pending")
        decision_payload = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
        reason = (
            payload.get("rejection_reason")
            or payload.get("reason")
            or decision_payload.get("decline_reasons")
            or decision_payload.get("reason")
        )
        checks: dict[str, Any] = decision_payload
        if not reference or not session_id:
            raise ValueError("DIDit status webhook is missing vendor_data or session_id.")

        timestamp_value = payload.get("created_at") or payload.get("timestamp")
        verified_at = datetime.now(timezone.utc)
        if isinstance(timestamp_value, (int, float)) and timestamp_value > 0:
            verified_at = datetime.fromtimestamp(timestamp_value, tz=timezone.utc)

        fingerprint_payload = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        fingerprint = sha256(fingerprint_payload.encode("utf-8")).hexdigest()

        return ProviderWebhookResult(
            provider=self.provider_name,
            session_id=str(session_id),
            reference=reference,
            decision=decision,
            verification_type=str((payload.get("metadata") or {}).get("gtex_verification_type") or "full_kyc"),
            verified_at=verified_at,
            checks=checks,
            rejection_reason=str(reason) if reason else None,
            evidence_fingerprint=fingerprint,
            raw_payload=payload,
        )
