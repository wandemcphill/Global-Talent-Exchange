from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import hmac
import json
import os
from typing import Any

from app.identity.providers.base import (
    BaseIdentityVerificationAdapter,
    ProviderWebhookResult,
    VerificationSessionResult,
)


class DIDitVerificationAdapter(BaseIdentityVerificationAdapter):
    @property
    def provider_name(self) -> str:
        return "didit"

    def _get_secret(self) -> str:
        return (
            os.environ.get("GTE_DIDIT_WEBHOOK_SECRET")
            or os.environ.get("GTE_KYC_WEBHOOK_SECRET")
            or "didit-webhook-test-secret"
        )

    def initiate_session(
        self,
        *,
        user_id: str,
        reference: str,
        verification_type: str = "full_kyc",
        callback_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VerificationSessionResult:
        session_id = f"didit_sess_{reference}"
        handoff_url = f"https://verify.didit.me/v1/session/{session_id}"
        return VerificationSessionResult(
            provider="didit",
            session_id=session_id,
            reference=reference,
            handoff_url=handoff_url,
            verification_type=verification_type,
            metadata={
                "user_id": user_id,
                "callback_url": callback_url,
                **(metadata or {}),
            },
        )

    def verify_webhook_signature(
        self,
        *,
        payload_bytes: bytes,
        headers: dict[str, str],
    ) -> bool:
        normalized_headers = {k.lower(): v for k, v in headers.items()}
        signature = (
            normalized_headers.get("x-didit-signature")
            or normalized_headers.get("didit-signature")
            or normalized_headers.get("x-signature")
        )
        if not signature:
            return False
        secret = self._get_secret().encode("utf-8")
        computed = hmac.new(secret, payload_bytes, sha256).hexdigest()
        return hmac.compare_digest(computed.lower(), signature.strip().lower())

    def parse_webhook_payload(
        self,
        *,
        payload: dict[str, Any],
    ) -> ProviderWebhookResult:
        reference = (
            payload.get("vendor_data")
            or payload.get("reference")
            or payload.get("session_id")
            or ""
        )
        session_id = payload.get("session_id") or payload.get("id")
        raw_status = str(payload.get("status") or payload.get("decision") or "").strip().lower()
        decision = "verified" if raw_status in {"approved", "verified", "passed", "success"} else "rejected"
        rejection_reason = payload.get("rejection_reason") or payload.get("reason") if decision != "verified" else None
        checks = payload.get("checks") or payload.get("features") or {}
        if not isinstance(checks, dict):
            checks = {"summary": str(checks)}

        now = datetime.now(timezone.utc)
        fingerprint_raw = json.dumps(
            {
                "provider": "didit",
                "reference": str(reference),
                "decision": decision,
                "session_id": str(session_id),
            },
            sort_keys=True,
        )
        evidence_fingerprint = sha256(fingerprint_raw.encode("utf-8")).hexdigest()

        return ProviderWebhookResult(
            provider="didit",
            session_id=str(session_id) if session_id else None,
            reference=str(reference),
            decision=decision,
            verification_type=str(payload.get("verification_type") or "full_kyc"),
            verified_at=now,
            checks=checks,
            rejection_reason=str(rejection_reason) if rejection_reason else None,
            evidence_fingerprint=evidence_fingerprint,
            raw_payload=payload,
        )
