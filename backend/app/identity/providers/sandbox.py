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


class SandboxVerificationAdapter(BaseIdentityVerificationAdapter):
    @property
    def provider_name(self) -> str:
        return "sandbox"

    def _get_secret(self) -> str:
        return (
            os.environ.get("GTE_SANDBOX_WEBHOOK_SECRET")
            or os.environ.get("GTE_KYC_WEBHOOK_SECRET")
            or "sandbox-secret"
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
        session_id = f"sandbox_sess_{reference}"
        handoff_url = f"https://sandbox.gtex.local/kyc/{session_id}"
        return VerificationSessionResult(
            provider="sandbox",
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
            normalized_headers.get("x-gtex-signature")
            or normalized_headers.get("x-signature")
            or normalized_headers.get("x-sandbox-signature")
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
        reference = payload.get("reference") or payload.get("session_id") or ""
        session_id = payload.get("session_id")
        raw_decision = str(payload.get("decision") or payload.get("status") or "").strip().lower()
        decision = "verified" if raw_decision in {"verified", "approved", "success"} else "rejected"
        rejection_reason = payload.get("rejection_reason") or payload.get("reason") if decision != "verified" else None
        checks = payload.get("checks") or {
            "government_id": True,
            "bvn_verified": True,
            "selfie_liveness": True,
            "facial_match": True,
        }

        now = datetime.now(timezone.utc)
        fingerprint_raw = json.dumps(
            {
                "provider": "sandbox",
                "reference": str(reference),
                "decision": decision,
                "session_id": str(session_id),
            },
            sort_keys=True,
        )
        evidence_fingerprint = sha256(fingerprint_raw.encode("utf-8")).hexdigest()

        return ProviderWebhookResult(
            provider="sandbox",
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
