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
from app.models.user import KycStatus, PublicAccountType, User


class IdentityVerificationError(ValueError):
    pass


class IdentityWebhookSignatureError(IdentityVerificationError):
    pass


class IdentitySessionNotFoundError(IdentityVerificationError):
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
            raise IdentityVerificationError("Identity verification on this path is reserved for Coin Trader accounts.")

        profile = self.session.scalar(
            select(CoinTraderProfile).where(CoinTraderProfile.user_id == actor.id)
        )
        if profile is None:
            # Auto-create basic profile if trader signed up but profile not initialized
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
        reference = f"kyc_trader_{uuid4().hex[:16]}"
        session_result = adapter.initiate_session(
            user_id=actor.id,
            reference=reference,
            verification_type=verification_type,
            callback_url=callback_url,
            metadata={"trader_profile_id": profile.id},
        )

        record = IdentityVerificationRecord(
            user_id=actor.id,
            trader_profile_id=profile.id,
            verification_domain="coin_trader",
            provider=adapter.provider_name,
            provider_session_id=session_result.session_id,
            provider_reference=reference,
            verification_type=verification_type,
            status="pending",
            decision=None,
            checks_summary_json={},
            idempotency_key=reference,
            initiated_at=now,
            history_json=[
                {
                    "action": "initiated",
                    "status": "pending",
                    "timestamp": now.isoformat(),
                    "provider": adapter.provider_name,
                    "session_id": session_result.session_id,
                }
            ],
            metadata_json={"handoff_url": session_result.handoff_url, **session_result.metadata},
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
        except Exception as exc:
            raise IdentityVerificationError("Invalid webhook JSON payload.") from exc

        webhook_result = adapter.parse_webhook_payload(payload=payload_dict)
        now = datetime.now(timezone.utc)

        # Lookup by provider_reference or provider_session_id
        record = self.session.scalar(
            select(IdentityVerificationRecord).where(
                (IdentityVerificationRecord.provider_reference == webhook_result.reference)
                | (IdentityVerificationRecord.provider_session_id == webhook_result.session_id)
                | (IdentityVerificationRecord.idempotency_key == webhook_result.reference)
            )
        )
        if record is None:
            # If no existing record matching reference, check if user_id or partner params specified
            user_id = payload_dict.get("user_id") or (payload_dict.get("metadata") or {}).get("user_id")
            if user_id:
                record = self.session.scalar(
                    select(IdentityVerificationRecord)
                    .where(IdentityVerificationRecord.user_id == user_id)
                    .order_by(IdentityVerificationRecord.created_at.desc())
                    .limit(1)
                )

        if record is None:
            raise IdentitySessionNotFoundError(
                f"No matching verification record found for reference '{webhook_result.reference}'."
            )

        # Idempotency check: duplicate webhooks do not repeat side effects
        if record.status == "verified":
            return {
                "status": "already_processed",
                "decision": "verified",
                "reference": record.provider_reference,
                "verified_at": record.verified_at.isoformat() if record.verified_at else None,
            }

        # Status transition
        record.provider_session_id = webhook_result.session_id or record.provider_session_id
        record.checks_summary_json = webhook_result.checks
        record.evidence_fingerprint = webhook_result.evidence_fingerprint

        if webhook_result.decision == "verified":
            record.status = "verified"
            record.decision = "verified"
            record.verified_at = webhook_result.verified_at or now
            record.rejection_reason = None
            record.history_json = [
                *list(record.history_json or []),
                {
                    "action": "webhook_verified",
                    "status": "verified",
                    "timestamp": record.verified_at.isoformat(),
                    "provider": adapter.provider_name,
                },
            ]

            # Activate the CoinTraderProfile automatically
            profile = self.session.get(CoinTraderProfile, record.trader_profile_id) if record.trader_profile_id else None
            if profile is None:
                profile = self.session.scalar(
                    select(CoinTraderProfile).where(CoinTraderProfile.user_id == record.user_id)
                )
            if profile is not None:
                profile.status = CoinTraderProfileStatus.APPROVED.value
                profile.verification_level = "fully_verified"
                profile.verified_at = record.verified_at
                profile.verification_provider = adapter.provider_name
                profile.verification_reference = record.provider_reference
                profile.approved_at = record.verified_at
                profile.rejected_at = None
                profile.frozen_at = None
                profile.suspended_at = None

            # Update User KYC status
            user = self.session.get(User, record.user_id)
            if user is not None:
                user.kyc_status = KycStatus.VERIFIED

            # Immutable audit log
            self.session.add(
                AuditLog(
                    actor_user_id=None,
                    action_key="identity.coin_trader.activated",
                    resource_type="coin_trader_profile",
                    resource_id=profile.id if profile else record.user_id,
                    outcome="success",
                    detail=f"Coin trader activated automatically from {adapter.provider_name} verified webhook result.",
                    metadata_json={
                        "provider": adapter.provider_name,
                        "reference": record.provider_reference,
                        "session_id": record.provider_session_id,
                        "verified_at": record.verified_at.isoformat(),
                        "fingerprint": record.evidence_fingerprint,
                        "checks": webhook_result.checks,
                    },
                )
            )
            self.session.commit()
            return {
                "status": "success",
                "decision": "verified",
                "reference": record.provider_reference,
                "verified_at": record.verified_at.isoformat(),
            }
        else:
            record.status = "rejected"
            record.decision = webhook_result.decision
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
            profile = self.session.get(CoinTraderProfile, record.trader_profile_id) if record.trader_profile_id else None
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
                "decision": "rejected",
                "reference": record.provider_reference,
                "reason": record.rejection_reason,
            }

    def list_verification_records(self, *, status_filter: str | None = None) -> list[IdentityVerificationRecord]:
        stmt = select(IdentityVerificationRecord).order_by(IdentityVerificationRecord.created_at.desc())
        if status_filter:
            stmt = stmt.where(IdentityVerificationRecord.status == status_filter)
        return list(self.session.scalars(stmt).all())
