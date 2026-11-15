from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.identity.providers import get_identity_provider
from app.models.coin_trader import CoinTraderProfile, CoinTraderProfileStatus, IdentityVerificationRecord
from app.models.risk_ops import AuditLog
from app.models.user import PublicAccountType, User


class IdentityVerificationError(ValueError):
    pass


class IdentityWebhookSignatureError(IdentityVerificationError):
    pass


class IdentitySessionNotFoundError(IdentityVerificationError):
    pass


IdentityVerificationNotFoundError = IdentitySessionNotFoundError
IdentityVerificationSignatureError = IdentityWebhookSignatureError


class IdentityVerificationValidationError(IdentityVerificationError):
    pass


class IdentityVerificationPermissionError(IdentityVerificationError):
    pass


class IdentityVerificationIdempotencyError(IdentityVerificationError):
    pass


@dataclass(slots=True)
class IdentityVerificationService:
    session: Session

    def initiate_trader_verification(
        self,
        *,
        actor: User,
        provider_name: str | None = None,
        verification_type: str = "full_kyc",
        callback_url: str | None = None,
    ) -> IdentityVerificationRecord:
        if actor.account_type != PublicAccountType.COIN_TRADER:
            raise IdentityVerificationPermissionError(
                "Identity verification on this path is reserved for Coin Trader accounts."
            )
        normalized_type = verification_type.strip().lower()
        if normalized_type not in {"full_kyc", "government_id", "document_and_selfie"}:
            raise IdentityVerificationValidationError("Unsupported trader verification type.")

        profile = self.session.scalar(select(CoinTraderProfile).where(CoinTraderProfile.user_id == actor.id))
        if profile is None:
            profile = CoinTraderProfile(
                user_id=actor.id,
                display_name=actor.display_name or actor.username,
                status=CoinTraderProfileStatus.APPLIED.value,
                tier="bronze",
                terms_json={"kyc_required": True},
                payment_methods_json=[],
                bank_accounts_json=[],
                metadata_json={"created_via": "verification_initiation"},
            )
            self.session.add(profile)
            self.session.flush()

        adapter = get_identity_provider(provider_name)
        now = datetime.now(timezone.utc)
        reference = f"gtex-kyc-{uuid4().hex}"
        session_result = adapter.initiate_session(
            user_id=actor.id,
            reference=reference,
            verification_type=normalized_type,
            callback_url=callback_url,
            metadata={
                "trader_profile_id": profile.id,
                "email": actor.email,
                "phone": getattr(actor, "phone_number", None),
            },
        )

        record = IdentityVerificationRecord(
            user_id=actor.id,
            trader_profile_id=profile.id,
            verification_domain="coin_trader",
            provider=adapter.provider_name,
            provider_session_id=session_result.session_id,
            provider_reference=reference,
            verification_type=normalized_type,
            status="pending",
            decision="pending",
            checks_summary_json={},
            idempotency_key=reference,
            initiated_at=now,
            expires_at=session_result.expires_at,
            history_json=[
                {
                    "action": "initiated",
                    "status": "pending",
                    "timestamp": now.isoformat(),
                    "provider": adapter.provider_name,
                    "session_id": session_result.session_id,
                }
            ],
            metadata_json={
                "handoff_url": session_result.handoff_url,
                **session_result.metadata,
            },
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_latest_trader_verification(self, *, actor: User) -> IdentityVerificationRecord | None:
        return self.session.scalar(
            select(IdentityVerificationRecord)
            .where(
                IdentityVerificationRecord.user_id == actor.id,
                IdentityVerificationRecord.verification_domain == "coin_trader",
            )
            .order_by(IdentityVerificationRecord.created_at.desc())
            .limit(1)
        )

    def process_provider_webhook(
        self,
        *,
        provider_name: str,
        payload_bytes: bytes,
        headers: dict[str, str],
    ) -> dict[str, object]:
        adapter = get_identity_provider(provider_name)
        if not adapter.verify_webhook_signature(payload_bytes=payload_bytes, headers=headers):
            raise IdentityWebhookSignatureError("Invalid provider webhook signature.")

        try:
            payload_dict = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IdentityVerificationValidationError("Invalid webhook JSON payload.") from exc
        if not isinstance(payload_dict, dict):
            raise IdentityVerificationValidationError("Provider webhook must be a JSON object.")

        webhook_result = adapter.parse_webhook_payload(payload=payload_dict)
        if not webhook_result.reference and not webhook_result.session_id:
            raise IdentityVerificationValidationError("Provider webhook is missing its verification reference.")

        match_conditions = []
        if webhook_result.reference:
            match_conditions.append(IdentityVerificationRecord.provider_reference == webhook_result.reference)
            match_conditions.append(IdentityVerificationRecord.idempotency_key == webhook_result.reference)
        if webhook_result.session_id:
            match_conditions.append(IdentityVerificationRecord.provider_session_id == webhook_result.session_id)

        record = self.session.scalar(
            select(IdentityVerificationRecord).where(
                IdentityVerificationRecord.provider == adapter.provider_name,
                IdentityVerificationRecord.verification_domain == "coin_trader",
                *([match_conditions[0] | match_conditions[1] | match_conditions[2]]
                  if len(match_conditions) == 3 else
                  [match_conditions[0] | match_conditions[1]]
                  if len(match_conditions) == 2 else
                  [match_conditions[0]])
            )
        )
        if record is None:
            raise IdentitySessionNotFoundError(
                "No pending GTEX verification session matches this provider event."
            )

        now = datetime.now(timezone.utc)
        fingerprint = webhook_result.evidence_fingerprint
        if record.status == "verified" or (
            fingerprint and record.evidence_fingerprint == fingerprint
        ):
            return {
                "status": "idempotent_duplicate",
                "provider": adapter.provider_name,
                "session_id": record.provider_session_id,
                "decision": record.decision or record.status,
                "idempotent": True,
                "user_id": record.user_id,
                "reference": record.provider_reference,
            }

        decision = str(webhook_result.decision or "pending").strip().lower()
        record.provider_session_id = webhook_result.session_id or record.provider_session_id
        record.checks_summary_json = webhook_result.checks if isinstance(webhook_result.checks, dict) else {}
        record.evidence_fingerprint = fingerprint
        record.decision = decision
        if webhook_result.reference:
            record.provider_reference = webhook_result.reference

        if decision in {"pending", "requires_review", "requires_retry", "in_review"}:
            # Provider "In Review" is not a failed verification and must never
            # approve or reject a trader before the final provider decision.
            record.status = "pending"
            record.history_json = [
                *list(record.history_json or []),
                {
                    "action": "provider_update",
                    "status": "pending",
                    "decision": decision,
                    "timestamp": now.isoformat(),
                    "provider": adapter.provider_name,
                },
            ]
            self.session.commit()
            return {
                "status": "pending",
                "provider": adapter.provider_name,
                "session_id": record.provider_session_id,
                "decision": decision,
                "idempotent": False,
                "user_id": record.user_id,
                "reference": record.provider_reference,
            }

        if decision == "verified":
            verified_at = webhook_result.verified_at or now
            record.status = "verified"
            record.decision = "verified"
            record.verified_at = verified_at
            record.rejection_reason = None
            record.history_json = [
                *list(record.history_json or []),
                {
                    "action": "webhook_verified",
                    "status": "verified",
                    "timestamp": verified_at.isoformat(),
                    "provider": adapter.provider_name,
                },
            ]

            profile = (
                self.session.get(CoinTraderProfile, record.trader_profile_id)
                if record.trader_profile_id
                else None
            )
            if profile is None:
                profile = self.session.scalar(
                    select(CoinTraderProfile).where(CoinTraderProfile.user_id == record.user_id)
                )
            if profile is None:
                raise IdentityVerificationError("Coin Trader profile is missing for the verified session.")

            profile.status = CoinTraderProfileStatus.APPROVED.value
            profile.verification_level = "fully_verified"
            profile.verified_at = verified_at
            profile.verification_provider = adapter.provider_name
            profile.verification_reference = record.provider_reference
            profile.approved_at = verified_at
            profile.rejected_at = None
            profile.frozen_at = None
            profile.suspended_at = None

            from app.identity.compliance_service import IdentityComplianceService, VerificationEvidence

            user = self.session.get(User, record.user_id)
            if user is None:
                raise IdentityVerificationError("The user tied to this verification session no longer exists.")
            checks = webhook_result.checks if isinstance(webhook_result.checks, dict) else {}
            IdentityComplianceService(self.session).verify(
                user=user,
                evidence=VerificationEvidence(
                    provider=adapter.provider_name,
                    provider_subject=record.provider_reference or record.user_id,
                    decision="verified",
                    verified_at=verified_at,
                    checks=checks,
                    reference=record.provider_reference,
                ),
                actor_user_id=None,
            )

            self.session.add(
                AuditLog(
                    actor_user_id=None,
                    action_key="identity.coin_trader.activated",
                    resource_type="coin_trader_profile",
                    resource_id=profile.id,
                    outcome="success",
                    detail=f"Coin trader activated from an authoritative {adapter.provider_name} verification result.",
                    metadata_json={
                        "provider": adapter.provider_name,
                        "reference": record.provider_reference,
                        "session_id": record.provider_session_id,
                        "verified_at": verified_at.isoformat(),
                        "fingerprint": record.evidence_fingerprint,
                        "checks": checks,
                    },
                )
            )
            self.session.commit()
            return {
                "status": "success",
                "provider": adapter.provider_name,
                "session_id": record.provider_session_id,
                "decision": "verified",
                "idempotent": False,
                "user_id": record.user_id,
                "reference": record.provider_reference,
                "verified_at": verified_at.isoformat(),
            }

        if decision != "rejected":
            raise IdentityVerificationValidationError(
                f"Unsupported provider decision '{decision}'. Trader status was not changed."
            )

        record.status = "rejected"
        record.decision = "rejected"
        record.rejection_reason = webhook_result.rejection_reason or "Identity verification checks failed."
        record.history_json = [
            *list(record.history_json or []),
            {
                "action": "webhook_rejected",
                "status": "rejected",
                "timestamp": now.isoformat(),
                "reason": record.rejection_reason,
                "provider": adapter.provider_name,
            },
        ]
        profile = (
            self.session.get(CoinTraderProfile, record.trader_profile_id)
            if record.trader_profile_id
            else None
        )
        if profile is not None:
            profile.status = CoinTraderProfileStatus.REJECTED.value
            profile.rejected_at = now

        self.session.add(
            AuditLog(
                actor_user_id=None,
                action_key="identity.coin_trader.rejected",
                resource_type="coin_trader_profile",
                resource_id=profile.id if profile else record.user_id,
                outcome="failure",
                detail=f"Coin trader verification failed from {adapter.provider_name}: {record.rejection_reason}",
                metadata_json={
                    "provider": adapter.provider_name,
                    "reference": record.provider_reference,
                    "rejection_reason": record.rejection_reason,
                },
            )
        )
        self.session.commit()
        return {
            "status": "rejected",
            "provider": adapter.provider_name,
            "session_id": record.provider_session_id,
            "decision": "rejected",
            "idempotent": False,
            "user_id": record.user_id,
            "reference": record.provider_reference,
            "reason": record.rejection_reason,
        }

    def list_verification_records(
        self,
        *,
        user_id: str | None = None,
        domain: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[IdentityVerificationRecord]:
        stmt = select(IdentityVerificationRecord).order_by(IdentityVerificationRecord.created_at.desc())
        if user_id:
            stmt = stmt.where(IdentityVerificationRecord.user_id == user_id)
        if domain:
            stmt = stmt.where(IdentityVerificationRecord.verification_domain == domain)
        if status:
            stmt = stmt.where(IdentityVerificationRecord.status == status)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.scalars(stmt).all())
