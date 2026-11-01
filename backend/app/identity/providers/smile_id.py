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


class SmileIDVerificationAdapter(BaseIdentityVerificationAdapter):
    @property
    def provider_name(self) -> str:
        return "smile_id"

    def _get_secret(self) -> str:
        return (
            os.environ.get("GTE_SMILE_ID_WEBHOOK_SECRET")
            or os.environ.get("GTE_KYC_WEBHOOK_SECRET")
            or "smile-id-webhook-test-secret"
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
        session_id = f"smile_job_{reference}"
        handoff_url = f"https://web.smileidentity.com/smart-selfie/{session_id}"
        return VerificationSessionResult(
            provider="smile_id",
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
            normalized_headers.get("smile-signature")
            or normalized_headers.get("x-smile-signature")
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
        partner_params = payload.get("partner_params") or {}
        reference = (
            partner_params.get("job_id")
            or partner_params.get("reference")
            or payload.get("reference")
            or payload.get("SmileJobID")
            or ""
        )
        session_id = payload.get("SmileJobID") or partner_params.get("job_id")
        result_code = str(payload.get("ResultCode") or payload.get("result_code") or "")
        result_text = str(payload.get("ResultText") or payload.get("status") or "").strip().lower()

        # Smile ID ResultCode 1012, 0810 etc. or Approved/Verified text indicates success
        decision = (
            "verified"
            if result_code in {"1012", "0810", "1020"} or "approved" in result_text or "verified" in result_text
            else "rejected"
        )
        rejection_reason = result_text if decision != "verified" else None
        checks = payload.get("Actions") or payload.get("checks") or {}
        if not isinstance(checks, dict):
            checks = {"actions": checks}

        now = datetime.now(timezone.utc)
        fingerprint_raw = json.dumps(
            {
                "provider": "smile_id",
                "reference": str(reference),
                "decision": decision,
                "session_id": str(session_id),
            },
            sort_keys=True,
        )
        evidence_fingerprint = sha256(fingerprint_raw.encode("utf-8")).hexdigest()

        return ProviderWebhookResult(
            provider="smile_id",
            session_id=str(session_id) if session_id else None,
            reference=str(reference),
            decision=decision,
            verification_type=str(payload.get("verification_type") or "full_kyc"),
            verified_at=now,
            checks=checks,
            rejection_reason=rejection_reason,
            evidence_fingerprint=evidence_fingerprint,
            raw_payload=payload,
        )
