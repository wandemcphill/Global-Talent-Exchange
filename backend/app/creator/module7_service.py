from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.creator.contracts import (
    CampaignContract,
    CampaignContractResponse,
    CampaignPerformanceContract,
    CampaignStatusUpdateRequest,
    ClipRefContract,
    CreateCampaignContractRequest,
    CreatorCampaignsContractResponse,
    CreatorModerationInboxContractResponse,
    CreatorProfileContract,
    CreatorProfileContractResponse,
    CreatorSettlementContract,
    CreatorSettlementsContractResponse,
    CreatorWalletContractResponse,
    CreatorWithdrawalContractResponse,
    CreatorWithdrawalRequest,
    ModerationInboxItemContract,
    SponsoredClipContract,
    SponsoredClipContractResponse,
    SponsoredClipsContractResponse,
    SubmitClipContractRequest,
    WalletBalanceContract,
    WalletTransactionContract,
)
from app.models.base import generate_uuid, utcnow
from app.models.creator_attention_earnings import CreatorWallet
from app.models.creator_campaign import CreatorCampaign
from app.models.creator_marketplace import (
    CreatorMarketplaceCampaign,
    CreatorMarketplaceCampaignStatus,
    CreatorMarketplaceParticipation,
)
from app.models.creator_monetization import CreatorRevenueSettlement
from app.models.creator_profile import CreatorProfile
from app.models.club_profile import ClubProfile
from app.models.moderation_report import ModerationReport
from app.models.risk_ops import AuditLog
from app.models.sponsored_clip import SponsoredClip
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerEntryReason,
    LedgerTransaction,
    LedgerTransactionType,
    LedgerUnit,
    PayoutRequest,
    PayoutStatus,
)
from app.risk_ops_engine.service import RiskOpsService
from app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
CREATOR_WALLET_UNIT = LedgerUnit.CREDIT
CREATOR_WITHDRAWAL_FEE_BPS = 1000
CREATOR_MINIMUM_WITHDRAWAL_FEE = Decimal("5.0000")
PENDING_PAYOUT_STATUSES = (
    PayoutStatus.REQUESTED,
    PayoutStatus.REVIEWING,
    PayoutStatus.HELD,
    PayoutStatus.PROCESSING,
)
VALID_CLIP_MODERATION_STATUSES = {"pending", "approved", "flagged", "rejected"}
VALID_CAMPAIGN_STATUSES = {"draft", "active", "review", "approved", "rejected", "settled"}

PROFILE_MISSING_REASON = (
    "creator_profile_missing: no CreatorProfile row exists for current user; creator onboarding "
    "and approval backend truth is required before Creator Module 7 contracts can be confirmed."
)
WALLET_BALANCE_UNAVAILABLE_REASON = (
    "creator_wallet_balance_unavailable: no CreatorWallet row or ledger balance projection exists "
    "for current user; backend must sync creator wallet truth before financial values can be shown."
)
WALLET_LEDGER_WITHDRAWAL_UNAVAILABLE_REASON = (
    "creator_wallet_ledger_unavailable: withdrawal requires an existing creator ledger account and "
    "LedgerBalanceProjection; display-only creator earnings cannot authorize payout holds."
)
CLIP_MODERATION_MISSING_REASON = (
    "creator_clip_moderation_status_missing: clip row has no authoritative moderation status; "
    "backend must provide pending, approved, flagged, or rejected."
)
SETTLEMENT_PARTIAL_SOURCE_REASON = (
    "creator_settlement_authority_partial: creator settlements are backed by marketplace participation "
    "payout rows only; no direct CreatorRevenueSettlement-to-creator mapping is mounted."
)
SETTLEMENT_WALLET_TRANSACTION_MISSING_REASON = (
    "creator_settlement_wallet_transaction_missing: creator revenue settlement has a positive creator share "
    "but no wallet transaction reference."
)
SETTLEMENT_FALLBACK_SOURCE_REASON = (
    "creator_settlement_fallback_source: creator marketplace participation payout rows are shown only because "
    "no direct CreatorRevenueSettlement rows are linked to this creator."
)


class CreatorContractBlocked(ValueError):
    def __init__(
        self,
        *,
        code: str,
        reason: str,
        audit_reference: str | None = None,
        status_code: int = 409,
    ) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.audit_reference = audit_reference
        self.status_code = status_code

    def detail(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "state": "blocked",
            "status": "blocked",
            "code": self.code,
            "reason": self.reason,
            "blocked_reason": self.reason,
        }
        if self.audit_reference is not None:
            payload["audit_reference"] = self.audit_reference
        return payload


class CreatorContractNotFound(ValueError):
    pass


@dataclass(slots=True)
class _LedgerSnapshot:
    available: Decimal
    reserved: Decimal
    currency: LedgerUnit
    account: LedgerAccount
    last_synced_at: Any | None


@dataclass(slots=True)
class CreatorModule7ContractService:
    session: Session
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()

    def get_profile(self, *, actor: User) -> CreatorProfileContractResponse:
        profile = self._creator_profile(actor)
        if profile is None:
            return CreatorProfileContractResponse(
                state="blocked",
                status="blocked",
                blocked_reason=PROFILE_MISSING_REASON,
                gap_reasons=(PROFILE_MISSING_REASON,),
            )
        wallet = self._creator_attention_wallet(actor)
        total_reach = wallet.total_impressions if wallet is not None else None
        engagement_rate = None
        if wallet is not None and wallet.total_impressions > 0:
            engagement_rate = self._amount(
                Decimal(wallet.total_likes + wallet.total_shares) / Decimal(wallet.total_impressions)
            )
        return CreatorProfileContractResponse(
            profile=CreatorProfileContract(
                id=profile.id,
                display_name=profile.display_name,
                verification_status=self._verification_status(profile),
                total_reach=total_reach,
                engagement_rate=engagement_rate,
                content_count=self._creator_clip_count(profile=profile, actor=actor),
                joined_at=profile.created_at,
            )
        )

    def list_campaigns(self, *, actor: User) -> CreatorCampaignsContractResponse:
        profile = self._creator_profile(actor)
        if profile is None:
            return CreatorCampaignsContractResponse(
                state="blocked",
                status="blocked",
                blocked_reason=PROFILE_MISSING_REASON,
                gap_reasons=(PROFILE_MISSING_REASON,),
            )
        campaigns = [
            self._creator_campaign_contract(item)
            for item in self.session.scalars(
                select(CreatorCampaign)
                .where(CreatorCampaign.creator_profile_id == profile.id)
                .order_by(CreatorCampaign.updated_at.desc(), CreatorCampaign.created_at.desc())
            ).all()
        ]
        campaigns.extend(self._marketplace_campaign_contracts(profile=profile, actor=actor))
        if not campaigns:
            return CreatorCampaignsContractResponse(
                state="empty",
                status="empty",
                campaigns=(),
                gap_reasons=(SETTLEMENT_PARTIAL_SOURCE_REASON,),
            )
        degraded = any(item.degraded_reason for item in campaigns)
        return CreatorCampaignsContractResponse(
            state="degraded" if degraded else "confirmed",
            status="degraded" if degraded else "confirmed",
            degraded_reason="One or more creator campaigns rely on a partial backend source." if degraded else None,
            campaigns=tuple(campaigns),
            gap_reasons=(SETTLEMENT_PARTIAL_SOURCE_REASON,),
        )

    def get_campaign(self, *, actor: User, campaign_id: str) -> CampaignContractResponse:
        campaign = self._find_campaign_contract(actor=actor, campaign_id=campaign_id)
        if campaign is None:
            raise CreatorContractNotFound("Creator campaign was not found.")
        return CampaignContractResponse(
            state="degraded" if campaign.degraded_reason else "confirmed",
            status="degraded" if campaign.degraded_reason else "confirmed",
            degraded_reason=campaign.degraded_reason,
            campaign=campaign,
            gap_reasons=campaign.gap_reasons,
        )

    def create_campaign(self, *, actor: User, payload: CreateCampaignContractRequest) -> CampaignContractResponse:
        profile = self._require_creator_profile(
            actor=actor,
            action_key="creator.campaign.created",
            resource_type="creator_campaign",
        )
        metadata = {
            "module7_contract": True,
            "sponsor": payload.sponsor,
            "brief": payload.brief,
            "budget": str(payload.budget) if payload.budget is not None else None,
            "currency": payload.currency,
            "status": payload.status,
            "submitted_clips": [],
        }
        campaign = CreatorCampaign(
            creator_profile_id=profile.id,
            name=payload.title,
            starts_at=payload.start_date,
            ends_at=payload.end_date,
            is_active=payload.status in {"active", "review", "approved"},
            metadata_json=metadata,
        )
        self.session.add(campaign)
        self.session.flush()
        audit = self._audit(
            actor=actor,
            action_key="creator.campaign.created",
            resource_type="creator_campaign",
            resource_id=campaign.id,
            detail="Creator campaign created.",
            metadata={
                "after": self._campaign_audit_snapshot(campaign),
                "budget": str(payload.budget) if payload.budget is not None else None,
                "currency": payload.currency,
            },
        )
        updated_metadata = dict(campaign.metadata_json or {})
        updated_metadata["last_audit_reference"] = audit.id
        campaign.metadata_json = updated_metadata
        self.session.flush()
        contract = self._creator_campaign_contract(campaign, audit_reference=audit.id)
        return CampaignContractResponse(campaign=contract, audit_reference=audit.id)

    def update_campaign_status(
        self,
        *,
        actor: User,
        campaign_id: str,
        payload: CampaignStatusUpdateRequest,
    ) -> CampaignContractResponse:
        profile = self._require_creator_profile(
            actor=actor,
            action_key="creator.campaign.status_changed",
            resource_type="creator_campaign",
        )
        campaign = self.session.scalar(
            select(CreatorCampaign).where(
                CreatorCampaign.id == campaign_id,
                CreatorCampaign.creator_profile_id == profile.id,
            )
        )
        if campaign is None:
            audit = self._audit_blocked(
                actor=actor,
                action_key="creator.campaign.status_changed",
                resource_type="creator_campaign",
                resource_id=campaign_id,
                reason=(
                    "creator_campaign_status_source_missing: campaign status changes are only supported for "
                    "creator-owned CreatorCampaign rows in this contract."
                ),
            )
            raise CreatorContractBlocked(
                code="creator_campaign_status_source_missing",
                reason=(
                    "creator_campaign_status_source_missing: campaign status changes are only supported for "
                    "creator-owned CreatorCampaign rows in this contract."
                ),
                audit_reference=audit.id,
            )
        before = self._campaign_audit_snapshot(campaign)
        metadata = dict(campaign.metadata_json or {})
        metadata["status"] = payload.status
        metadata["status_reason"] = payload.reason
        campaign.metadata_json = metadata
        campaign.is_active = payload.status in {"active", "review", "approved"}
        self.session.flush()
        audit = self._audit(
            actor=actor,
            action_key="creator.campaign.status_changed",
            resource_type="creator_campaign",
            resource_id=campaign.id,
            detail="Creator campaign status changed.",
            metadata={
                "before": before,
                "after": self._campaign_audit_snapshot(campaign),
                "reason": payload.reason,
            },
        )
        metadata = dict(campaign.metadata_json or {})
        metadata["last_audit_reference"] = audit.id
        campaign.metadata_json = metadata
        self.session.flush()
        return CampaignContractResponse(
            campaign=self._creator_campaign_contract(campaign, audit_reference=audit.id),
            audit_reference=audit.id,
        )

    def list_clips(self, *, actor: User) -> SponsoredClipsContractResponse:
        profile = self._creator_profile(actor)
        if profile is None:
            return SponsoredClipsContractResponse(
                state="blocked",
                status="blocked",
                blocked_reason=PROFILE_MISSING_REASON,
                gap_reasons=(PROFILE_MISSING_REASON,),
            )
        clips = self._clip_contracts(profile=profile, actor=actor)
        if not clips:
            return SponsoredClipsContractResponse(state="empty", status="empty", clips=())
        degraded = any(clip.state == "degraded" for clip in clips)
        return SponsoredClipsContractResponse(
            state="degraded" if degraded else "confirmed",
            status="degraded" if degraded else "confirmed",
            degraded_reason="One or more sponsored clips have no authoritative moderation status."
            if degraded
            else None,
            gap_reasons=(CLIP_MODERATION_MISSING_REASON,) if degraded else (),
            clips=tuple(clips),
        )

    def get_clip(self, *, actor: User, clip_id: str) -> SponsoredClipContractResponse:
        profile = self._creator_profile(actor)
        if profile is None:
            return SponsoredClipContractResponse(
                state="blocked",
                status="blocked",
                blocked_reason=PROFILE_MISSING_REASON,
                gap_reasons=(PROFILE_MISSING_REASON,),
            )
        for clip in self._clip_contracts(profile=profile, actor=actor):
            if clip.id == clip_id:
                return SponsoredClipContractResponse(
                    state=clip.state,
                    status=clip.state,
                    blocked_reason=clip.blocked_reason,
                    degraded_reason=clip.degraded_reason,
                    gap_reasons=clip.gap_reasons,
                    clip=clip,
                )
        raise CreatorContractNotFound("Creator sponsored clip was not found.")

    def submit_clip(self, *, actor: User, payload: SubmitClipContractRequest) -> SponsoredClipContractResponse:
        profile = self._require_creator_profile(
            actor=actor,
            action_key="creator.clip.submitted",
            resource_type="creator_clip",
        )
        campaign = self.session.scalar(
            select(CreatorCampaign).where(
                CreatorCampaign.id == payload.campaign_id,
                CreatorCampaign.creator_profile_id == profile.id,
            )
        )
        if campaign is None:
            audit = self._audit_blocked(
                actor=actor,
                action_key="creator.clip.submitted",
                resource_type="creator_clip",
                resource_id=payload.campaign_id,
                reason=(
                    "creator_clip_submission_source_missing: clip submission persistence is mounted only for "
                    "creator-owned CreatorCampaign rows."
                ),
            )
            raise CreatorContractBlocked(
                code="creator_clip_submission_source_missing",
                reason=(
                    "creator_clip_submission_source_missing: clip submission persistence is mounted only for "
                    "creator-owned CreatorCampaign rows."
                ),
                audit_reference=audit.id,
            )
        clip_id = generate_uuid()
        submitted_at = utcnow()
        clip_payload = {
            "id": clip_id,
            "clip_id": clip_id,
            "campaign_id": campaign.id,
            "title": payload.title,
            "url": payload.url,
            "thumbnail_url": payload.thumbnail_url,
            "moderation_status": "pending",
            "moderation_note": "Under review",
            "submitted_at": submitted_at.isoformat(),
            "metadata": dict(payload.metadata),
        }
        metadata = dict(campaign.metadata_json or {})
        submitted = list(metadata.get("submitted_clips") or [])
        submitted.append(clip_payload)
        metadata["submitted_clips"] = submitted
        campaign.metadata_json = metadata
        self.session.flush()
        audit = self._audit(
            actor=actor,
            action_key="creator.clip.submitted",
            resource_type="creator_clip",
            resource_id=clip_id,
            detail="Creator sponsored clip submitted.",
            metadata={
                "campaign_id": campaign.id,
                "clip": {
                    "id": clip_id,
                    "title": payload.title,
                    "url": payload.url,
                    "moderation_status": "pending",
                },
            },
        )
        clip_payload["audit_reference"] = audit.id
        metadata = dict(campaign.metadata_json or {})
        submitted = list(metadata.get("submitted_clips") or [])
        submitted[-1] = clip_payload
        metadata["submitted_clips"] = submitted
        campaign.metadata_json = metadata
        self.session.flush()
        return SponsoredClipContractResponse(
            clip=self._clip_from_payload(clip_payload, source="creator_campaign", audit_reference=audit.id),
            audit_reference=audit.id,
        )

    def get_wallet(self, *, actor: User) -> CreatorWalletContractResponse:
        profile = self._creator_profile(actor)
        if profile is None:
            return CreatorWalletContractResponse(
                state="blocked",
                status="blocked",
                blocked_reason=PROFILE_MISSING_REASON,
                gap_reasons=(PROFILE_MISSING_REASON,),
            )
        ledger = self._ledger_snapshot(actor, CREATOR_WALLET_UNIT)
        if ledger is not None:
            return CreatorWalletContractResponse(
                balance=WalletBalanceContract(
                    available=ledger.available,
                    reserved=ledger.reserved,
                    currency=ledger.currency.value,
                    last_synced_at=ledger.last_synced_at,
                ),
                pending_settlements=self._pending_settlement_count(profile=profile, actor=actor),
                recent_transactions=tuple(self._recent_wallet_transactions(ledger.account)),
                withdrawal_available=ledger.available > Decimal("0.0000"),
            )
        creator_wallet = self._creator_attention_wallet(actor)
        if creator_wallet is not None:
            return CreatorWalletContractResponse(
                state="degraded",
                status="degraded",
                degraded_reason=WALLET_LEDGER_WITHDRAWAL_UNAVAILABLE_REASON,
                gap_reasons=(WALLET_LEDGER_WITHDRAWAL_UNAVAILABLE_REASON,),
                balance=WalletBalanceContract(
                    available=self._amount(creator_wallet.available_balance_credit),
                    reserved=None,
                    currency=CREATOR_WALLET_UNIT.value,
                    last_synced_at=creator_wallet.updated_at,
                ),
                pending_settlements=self._pending_settlement_count(profile=profile, actor=actor),
                withdrawal_available=False,
            )
        return CreatorWalletContractResponse(
            state="blocked",
            status="blocked",
            blocked_reason=WALLET_BALANCE_UNAVAILABLE_REASON,
            gap_reasons=(WALLET_BALANCE_UNAVAILABLE_REASON,),
            balance=None,
            pending_settlements=None,
            withdrawal_available=False,
        )

    def list_settlements(self, *, actor: User) -> CreatorSettlementsContractResponse:
        profile = self._creator_profile(actor)
        if profile is None:
            return CreatorSettlementsContractResponse(
                state="blocked",
                status="blocked",
                blocked_reason=PROFILE_MISSING_REASON,
                gap_reasons=(PROFILE_MISSING_REASON,),
            )
        settlements = self._creator_revenue_settlements(profile=profile, actor=actor)
        gap_reasons: tuple[str, ...] = ()
        if not settlements:
            settlements = self._marketplace_settlements(profile)
            gap_reasons = (SETTLEMENT_FALLBACK_SOURCE_REASON,) if settlements else ()
        if not settlements:
            return CreatorSettlementsContractResponse(
                state="empty",
                status="empty",
                settlements=(),
            )
        degraded = any(item.degraded_reason for item in settlements)
        return CreatorSettlementsContractResponse(
            state="degraded" if degraded else "confirmed",
            status="degraded" if degraded else "confirmed",
            degraded_reason=(
                "One or more creator settlements have no wallet transaction reference." if degraded else None
            ),
            gap_reasons=gap_reasons,
            settlements=tuple(settlements),
        )

    def get_moderation_inbox(self, *, actor: User) -> CreatorModerationInboxContractResponse:
        profile = self._creator_profile(actor)
        if profile is None:
            return CreatorModerationInboxContractResponse(
                state="blocked",
                status="blocked",
                blocked_reason=PROFILE_MISSING_REASON,
                gap_reasons=(PROFILE_MISSING_REASON,),
            )
        items: list[ModerationInboxItemContract] = []
        for clip in self._clip_contracts(profile=profile, actor=actor):
            if clip.status in {"pending", "flagged", "rejected"} or clip.status is None:
                items.append(
                    ModerationInboxItemContract(
                        id=f"clip:{clip.id}",
                        item_type="sponsored_clip",
                        item_id=clip.id,
                        status=clip.state,
                        moderation_status=clip.status,
                        reason=clip.blocked_reason or clip.degraded_reason,
                        note=clip.moderation_note,
                        created_at=clip.published_at,
                        source=clip.source,
                    )
                )
        reports = self.session.scalars(
            select(ModerationReport)
            .where(ModerationReport.subject_user_id == actor.id)
            .order_by(ModerationReport.updated_at.desc(), ModerationReport.created_at.desc())
        ).all()
        for report in reports:
            items.append(
                ModerationInboxItemContract(
                    id=report.id,
                    item_type=report.target_type,
                    item_id=report.target_id,
                    status=self._enum_value(report.status),
                    moderation_status=None,
                    reason=report.reason_code,
                    note=report.resolution_note or report.description,
                    created_at=report.created_at,
                    source="moderation_report",
                )
            )
        if not items:
            return CreatorModerationInboxContractResponse(state="empty", status="empty", items=())
        degraded = any(item.status == "degraded" for item in items)
        return CreatorModerationInboxContractResponse(
            state="degraded" if degraded else "confirmed",
            status="degraded" if degraded else "confirmed",
            degraded_reason="One or more moderation inbox items are missing authoritative state." if degraded else None,
            gap_reasons=(CLIP_MODERATION_MISSING_REASON,) if degraded else (),
            items=tuple(items),
        )

    def request_withdrawal(
        self,
        *,
        actor: User,
        payload: CreatorWithdrawalRequest,
    ) -> CreatorWithdrawalContractResponse:
        self._require_creator_profile(
            actor=actor,
            action_key="creator.withdrawal.requested",
            resource_type="creator_withdrawal",
        )
        ledger = self._ledger_snapshot(actor, payload.unit)
        if ledger is None:
            audit = self._audit_blocked(
                actor=actor,
                action_key="creator.withdrawal.requested",
                resource_type="creator_withdrawal",
                resource_id=None,
                reason=WALLET_LEDGER_WITHDRAWAL_UNAVAILABLE_REASON,
            )
            raise CreatorContractBlocked(
                code="creator_wallet_ledger_unavailable",
                reason=WALLET_LEDGER_WITHDRAWAL_UNAVAILABLE_REASON,
                audit_reference=audit.id,
            )
        if ledger.available <= Decimal("0.0000"):
            audit = self._audit_blocked(
                actor=actor,
                action_key="creator.withdrawal.requested",
                resource_type="creator_withdrawal",
                resource_id=ledger.account.id,
                reason="creator_withdrawal_blocked_no_available_balance: WalletBalanceDTO.available must be greater than 0.",
            )
            raise CreatorContractBlocked(
                code="creator_withdrawal_blocked_no_available_balance",
                reason="creator_withdrawal_blocked_no_available_balance: WalletBalanceDTO.available must be greater than 0.",
                audit_reference=audit.id,
            )
        fee_amount = self._withdrawal_fee(payload.amount)
        total_debit = self._amount(payload.amount + fee_amount)
        if ledger.available < total_debit:
            reason = (
                "creator_withdrawal_blocked_insufficient_available_balance: requested amount plus backend withdrawal "
                "fee exceeds WalletBalanceDTO.available."
            )
            audit = self._audit_blocked(
                actor=actor,
                action_key="creator.withdrawal.requested",
                resource_type="creator_withdrawal",
                resource_id=ledger.account.id,
                reason=reason,
                metadata={
                    "available": str(ledger.available),
                    "amount": str(payload.amount),
                    "fee_amount": str(fee_amount),
                    "total_debit": str(total_debit),
                },
            )
            raise CreatorContractBlocked(
                code="creator_withdrawal_blocked_insufficient_available_balance",
                reason=reason,
                audit_reference=audit.id,
            )
        result = self.wallet_service.request_payout(
            self.session,
            user=actor,
            amount=payload.amount,
            unit=payload.unit,
            destination_reference=payload.destination_reference,
            source_scope="user_hosted_gift",
            withdrawal_fee_bps=CREATOR_WITHDRAWAL_FEE_BPS,
            minimum_fee=CREATOR_MINIMUM_WITHDRAWAL_FEE,
            actor=actor,
            notes=payload.notes,
            extra_meta={
                "creator_module_contract": "module7",
                "withdrawal_method": payload.method,
            },
        )
        audit = self._audit(
            actor=actor,
            action_key="creator.withdrawal.requested",
            resource_type="creator_withdrawal",
            resource_id=result.payout_request.id,
            detail="Creator withdrawal requested.",
            metadata={
                "amount": str(payload.amount),
                "fee_amount": str(result.fee_amount),
                "total_debit": str(result.total_debit),
                "method": payload.method,
                "unit": payload.unit.value,
                "payout_request_id": result.payout_request.id,
            },
        )
        return CreatorWithdrawalContractResponse(
            withdrawal_id=result.payout_request.id,
            payout_request_id=result.payout_request.id,
            amount=result.payout_request.amount,
            fee_amount=result.fee_amount,
            total_debit=result.total_debit,
            currency=result.payout_request.unit.value,
            method=payload.method,
            audit_reference=audit.id,
            action_state="completed",
        )

    def _creator_profile(self, actor: User) -> CreatorProfile | None:
        return self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == actor.id))

    def _require_creator_profile(
        self,
        *,
        actor: User,
        action_key: str,
        resource_type: str,
    ) -> CreatorProfile:
        profile = self._creator_profile(actor)
        if profile is not None:
            return profile
        audit = self._audit_blocked(
            actor=actor,
            action_key=action_key,
            resource_type=resource_type,
            resource_id=None,
            reason=PROFILE_MISSING_REASON,
        )
        raise CreatorContractBlocked(
            code="creator_profile_missing",
            reason=PROFILE_MISSING_REASON,
            audit_reference=audit.id,
        )

    def _creator_attention_wallet(self, actor: User) -> CreatorWallet | None:
        return self.session.scalar(select(CreatorWallet).where(CreatorWallet.creator_user_id == actor.id))

    def _creator_campaign_contract(
        self,
        campaign: CreatorCampaign,
        *,
        audit_reference: str | None = None,
    ) -> CampaignContract:
        metadata = dict(campaign.metadata_json or {})
        status = str(metadata.get("status") or ("active" if campaign.is_active else "draft")).strip().lower()
        if status not in VALID_CAMPAIGN_STATUSES:
            status = "active" if campaign.is_active else "draft"
        clips = tuple(
            ClipRefContract(id=str(item.get("id") or item.get("clip_id")), title=item.get("title"))
            for item in self._campaign_submitted_clips(campaign)
            if item.get("id") or item.get("clip_id")
        )
        return CampaignContract(
            id=campaign.id,
            title=campaign.name,
            sponsor=self._clean_optional(metadata.get("sponsor")),
            brief=self._clean_optional(metadata.get("brief")),
            budget=self._optional_amount(metadata.get("budget")),
            currency=self._clean_optional(metadata.get("currency")) or "credit",
            status=status,  # type: ignore[arg-type]
            source="creator_campaign",
            start_date=campaign.starts_at,
            end_date=campaign.ends_at,
            clips=clips,
            performance=self._performance_from_payload(metadata.get("performance")),
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            audit_reference=audit_reference or self._clean_optional(metadata.get("last_audit_reference")),
        )

    def _marketplace_campaign_contracts(self, *, profile: CreatorProfile, actor: User) -> list[CampaignContract]:
        rows = self.session.execute(
            select(CreatorMarketplaceParticipation, CreatorMarketplaceCampaign)
            .join(
                CreatorMarketplaceCampaign, CreatorMarketplaceCampaign.id == CreatorMarketplaceParticipation.campaign_id
            )
            .where(CreatorMarketplaceParticipation.creator_id == profile.id)
            .order_by(CreatorMarketplaceParticipation.updated_at.desc())
        ).all()
        campaigns: list[CampaignContract] = []
        for participation, campaign in rows:
            source_status = self._enum_value(campaign.status)
            status, degraded_reason = self._map_marketplace_status(source_status)
            clips = tuple(
                ClipRefContract(id=str(item.get("id") or item.get("clip_id")), title=item.get("title"))
                for item in list(participation.clips_submitted or [])
                if item.get("id") or item.get("clip_id")
            )
            campaigns.append(
                CampaignContract(
                    id=campaign.id,
                    title=campaign.title,
                    sponsor=self._display_name(self.session.get(User, campaign.brand_id)),
                    budget=self._amount(campaign.budget),
                    currency="credit",
                    status=status,
                    source="creator_marketplace_participation",
                    source_status=source_status,
                    clips=clips,
                    performance=self._performance_from_payload(participation.performance_metrics),
                    created_at=campaign.created_at,
                    updated_at=campaign.updated_at,
                    degraded_reason=degraded_reason,
                    gap_reasons=(degraded_reason,) if degraded_reason else (),
                )
            )
        return campaigns

    def _find_campaign_contract(self, *, actor: User, campaign_id: str) -> CampaignContract | None:
        profile = self._creator_profile(actor)
        if profile is None:
            return None
        creator_campaign = self.session.scalar(
            select(CreatorCampaign).where(
                CreatorCampaign.id == campaign_id,
                CreatorCampaign.creator_profile_id == profile.id,
            )
        )
        if creator_campaign is not None:
            return self._creator_campaign_contract(creator_campaign)
        for campaign in self._marketplace_campaign_contracts(profile=profile, actor=actor):
            if campaign.id == campaign_id:
                return campaign
        return None

    def _campaign_submitted_clips(self, campaign: CreatorCampaign) -> list[dict[str, Any]]:
        payload = (campaign.metadata_json or {}).get("submitted_clips")
        if not isinstance(payload, list):
            return []
        return [dict(item) for item in payload if isinstance(item, dict)]

    def _clip_contracts(self, *, profile: CreatorProfile, actor: User) -> list[SponsoredClipContract]:
        clips: list[SponsoredClipContract] = []
        creator_campaigns = self.session.scalars(
            select(CreatorCampaign).where(CreatorCampaign.creator_profile_id == profile.id)
        ).all()
        for campaign in creator_campaigns:
            for payload in self._campaign_submitted_clips(campaign):
                payload.setdefault("campaign_id", campaign.id)
                clips.append(self._clip_from_payload(payload, source="creator_campaign"))

        participations = self.session.scalars(
            select(CreatorMarketplaceParticipation).where(CreatorMarketplaceParticipation.creator_id == profile.id)
        ).all()
        for participation in participations:
            for payload in list(participation.clips_submitted or []):
                clip_payload = dict(payload)
                clip_payload.setdefault("campaign_id", participation.campaign_id)
                clips.append(self._clip_from_payload(clip_payload, source="creator_marketplace_participation"))

        target_keys = {actor.id, profile.id, profile.handle}
        sponsored_rows = self.session.scalars(select(SponsoredClip).order_by(SponsoredClip.updated_at.desc())).all()
        for row in sponsored_rows:
            target_creators = {str(item) for item in (row.target_creators_json or [])}
            metadata = dict(row.metadata_json or {})
            metadata_targets = {
                str(value)
                for value in (
                    metadata.get("creator_user_id"),
                    metadata.get("creator_id"),
                    metadata.get("creator_profile_id"),
                    metadata.get("creator_handle"),
                )
                if value is not None
            }
            if target_keys.isdisjoint(target_creators | metadata_targets):
                continue
            clips.append(self._clip_from_sponsored_clip(row))
        clips.sort(key=lambda item: (item.published_at is None, item.published_at or utcnow(), item.id), reverse=True)
        return clips

    def _clip_from_payload(
        self,
        payload: dict[str, Any],
        *,
        source: str,
        audit_reference: str | None = None,
    ) -> SponsoredClipContract:
        status = self._clip_status(payload)
        degraded_reason = None if status is not None else CLIP_MODERATION_MISSING_REASON
        return SponsoredClipContract(
            id=str(payload.get("id") or payload.get("clip_id")),
            campaign_id=self._clean_optional(payload.get("campaign_id")),
            title=self._clean_optional(payload.get("title")),
            url=self._clean_optional(payload.get("url") or payload.get("clip_url")),
            thumbnail_url=self._clean_optional(payload.get("thumbnail_url")),
            status=status,  # type: ignore[arg-type]
            moderation_note=self._clean_optional(
                payload.get("moderation_note")
                or self._nested(payload, "metadata", "moderation_note")
                or self._nested(payload, "metadata", "flag_reason")
            ),
            published_at=self._parse_datetime(payload.get("published_at") or payload.get("submitted_at")),
            view_count=self._optional_int(payload.get("view_count") or payload.get("views")),
            engagement_rate=self._optional_amount(payload.get("engagement_rate")),
            source=source,
            state="confirmed" if status is not None else "degraded",
            degraded_reason=degraded_reason,
            audit_reference=audit_reference or self._clean_optional(payload.get("audit_reference")),
            gap_reasons=(CLIP_MODERATION_MISSING_REASON,) if status is None else (),
        )

    def _clip_from_sponsored_clip(self, row: SponsoredClip) -> SponsoredClipContract:
        payload = dict(row.clip_payload_json or {})
        metadata = dict(row.metadata_json or {})
        merged = {
            **payload,
            **metadata,
            "id": row.id,
            "clip_id": payload.get("clip_id") or row.clip_id,
            "campaign_id": metadata.get("campaign_id") or payload.get("campaign_id"),
            "title": payload.get("title") or metadata.get("title"),
            "url": payload.get("url") or payload.get("clip_url") or metadata.get("url"),
            "thumbnail_url": payload.get("thumbnail_url") or metadata.get("thumbnail_url"),
            "view_count": row.impressions_served,
            "published_at": metadata.get("published_at") or row.start_time,
            "metadata": metadata,
        }
        return self._clip_from_payload(merged, source="sponsored_clip")

    def _marketplace_settlements(self, profile: CreatorProfile) -> list[CreatorSettlementContract]:
        rows = self.session.scalars(
            select(CreatorMarketplaceParticipation)
            .where(CreatorMarketplaceParticipation.creator_id == profile.id)
            .order_by(
                CreatorMarketplaceParticipation.updated_at.desc(), CreatorMarketplaceParticipation.created_at.desc()
            )
        ).all()
        settlements: list[CreatorSettlementContract] = []
        for row in rows:
            amount = self._amount(row.payout_earned)
            degraded_reason = None
            if amount > Decimal("0.0000") and not row.wallet_transaction_id:
                degraded_reason = SETTLEMENT_WALLET_TRANSACTION_MISSING_REASON
            settlements.append(
                CreatorSettlementContract(
                    id=row.id,
                    campaign_id=row.campaign_id,
                    amount=amount,
                    currency=CREATOR_WALLET_UNIT.value,
                    status="settled" if row.wallet_transaction_id else "pending",
                    wallet_transaction_id=row.wallet_transaction_id,
                    created_at=row.created_at,
                    degraded_reason=degraded_reason,
                )
            )
        return settlements

    def _creator_revenue_settlements(
        self,
        *,
        profile: CreatorProfile,
        actor: User,
    ) -> list[CreatorSettlementContract]:
        club_ids = {
            item
            for item in self.session.scalars(
                select(ClubProfile.id).where(ClubProfile.owner_user_id.in_((actor.id, profile.user_id)))
            ).all()
            if item
        }
        if not club_ids:
            return []

        rows = self.session.scalars(
            select(CreatorRevenueSettlement)
            .where(
                (CreatorRevenueSettlement.home_club_id.in_(club_ids))
                | (CreatorRevenueSettlement.away_club_id.in_(club_ids))
            )
            .order_by(
                CreatorRevenueSettlement.settled_at.desc().nullslast(),
                CreatorRevenueSettlement.updated_at.desc(),
                CreatorRevenueSettlement.created_at.desc(),
            )
        ).all()
        settlements: list[CreatorSettlementContract] = []
        for row in rows:
            sides: list[tuple[str, Decimal]] = []
            if row.home_club_id in club_ids:
                sides.append(("home", self._amount(row.home_creator_share_coin)))
            if row.away_club_id in club_ids:
                sides.append(("away", self._amount(row.away_creator_share_coin)))
            for side, amount in sides:
                wallet_transaction_id = self._settlement_wallet_transaction_id(row, side=side)
                degraded_reason = (
                    SETTLEMENT_WALLET_TRANSACTION_MISSING_REASON
                    if amount > Decimal("0.0000") and wallet_transaction_id is None
                    else None
                )
                settlements.append(
                    CreatorSettlementContract(
                        id=f"{row.id}:{side}",
                        campaign_id=row.competition_id,
                        amount=amount,
                        currency=CREATOR_WALLET_UNIT.value,
                        status="settled" if row.settled_at is not None else row.review_status,
                        wallet_transaction_id=wallet_transaction_id,
                        created_at=row.settled_at or row.created_at,
                        audit_reference=f"creator_revenue_settlement:{row.id}",
                        degraded_reason=degraded_reason,
                    )
                )
        return settlements

    def _settlement_wallet_transaction_id(self, settlement: CreatorRevenueSettlement, *, side: str) -> str | None:
        metadata = dict(settlement.metadata_json or {})
        candidate_keys = (
            f"{side}_wallet_transaction_id",
            f"{side}_ledger_transaction_id",
            f"{side}_creator_wallet_transaction_id",
            f"{side}_creator_ledger_transaction_id",
            "wallet_transaction_id",
            "ledger_transaction_id",
        )
        for key in candidate_keys:
            candidate = self._clean_optional(metadata.get(key))
            if candidate is not None:
                return candidate
        return None

    def _ledger_snapshot(self, actor: User, unit: LedgerUnit) -> _LedgerSnapshot | None:
        account = self.session.scalar(
            select(LedgerAccount).where(
                LedgerAccount.owner_user_id == actor.id,
                LedgerAccount.unit == unit,
                LedgerAccount.kind == LedgerAccountKind.USER,
            )
        )
        if account is None:
            return None
        projection = self.session.scalar(
            select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id == account.id)
        )
        if projection is None or projection.balance is None:
            return None
        escrow = self.session.scalar(
            select(LedgerAccount).where(
                LedgerAccount.owner_user_id == actor.id,
                LedgerAccount.unit == unit,
                LedgerAccount.kind == LedgerAccountKind.ESCROW,
            )
        )
        reserved = Decimal("0.0000")
        last_synced_at = projection.updated_at
        if escrow is not None:
            escrow_projection = self.session.scalar(
                select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id == escrow.id)
            )
            if escrow_projection is None or escrow_projection.balance is None:
                return None
            reserved = self._amount(escrow_projection.balance)
            last_synced_at = max(last_synced_at, escrow_projection.updated_at)
        return _LedgerSnapshot(
            available=self._amount(projection.balance),
            reserved=reserved,
            currency=unit,
            account=account,
            last_synced_at=last_synced_at,
        )

    def _recent_wallet_transactions(self, account: LedgerAccount) -> list[WalletTransactionContract]:
        rows = self.session.execute(
            select(LedgerEntry, LedgerTransaction)
            .join(LedgerTransaction, LedgerTransaction.id == LedgerEntry.transaction_id)
            .where(LedgerEntry.account_id == account.id)
            .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
            .limit(10)
        ).all()
        transactions: list[WalletTransactionContract] = []
        for entry, transaction in rows:
            amount = self._amount(entry.amount)
            transactions.append(
                WalletTransactionContract(
                    id=entry.id,
                    type=self._transaction_type(entry, amount),
                    amount=abs(amount),
                    currency=entry.unit.value,
                    reference=entry.reference or transaction.reference,
                    created_at=entry.created_at,
                    status=self._enum_value(transaction.status),
                )
            )
        return transactions

    def _pending_settlement_count(self, *, profile: CreatorProfile, actor: User) -> int:
        direct_pending = self._direct_pending_settlement_count(profile=profile, actor=actor)
        marketplace_pending = (
            self.session.scalar(
                select(func.count())
                .select_from(CreatorMarketplaceParticipation)
                .where(
                    CreatorMarketplaceParticipation.creator_id == profile.id,
                    CreatorMarketplaceParticipation.payout_earned > 0,
                    CreatorMarketplaceParticipation.wallet_transaction_id.is_(None),
                )
            )
            or 0
        )
        payout_pending = (
            self.session.scalar(
                select(func.count())
                .select_from(PayoutRequest)
                .where(
                    PayoutRequest.user_id == actor.id,
                    PayoutRequest.unit == CREATOR_WALLET_UNIT,
                    PayoutRequest.status.in_(PENDING_PAYOUT_STATUSES),
                )
            )
            or 0
        )
        return int(direct_pending) + int(marketplace_pending) + int(payout_pending)

    def _direct_pending_settlement_count(self, *, profile: CreatorProfile, actor: User) -> int:
        return sum(
            1
            for item in self._creator_revenue_settlements(profile=profile, actor=actor)
            if item.amount is not None and item.amount > Decimal("0.0000") and item.wallet_transaction_id is None
        )

    def _creator_clip_count(self, *, profile: CreatorProfile, actor: User) -> int:
        return len(self._clip_contracts(profile=profile, actor=actor))

    def _audit(
        self,
        *,
        actor: User,
        action_key: str,
        resource_type: str,
        resource_id: str | None,
        detail: str,
        metadata: dict[str, Any] | None = None,
        outcome: str = "success",
    ) -> AuditLog:
        return RiskOpsService(self.session).log_audit(
            actor_user_id=actor.id,
            action_key=action_key,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            metadata_json=metadata or {},
            outcome=outcome,
        )

    def _audit_blocked(
        self,
        *,
        actor: User,
        action_key: str,
        resource_type: str,
        resource_id: str | None,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        payload = {"blocked_reason": reason}
        if metadata:
            payload.update(metadata)
        return self._audit(
            actor=actor,
            action_key=action_key,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=reason,
            metadata=payload,
            outcome="blocked",
        )

    @staticmethod
    def _campaign_audit_snapshot(campaign: CreatorCampaign) -> dict[str, Any]:
        metadata = dict(campaign.metadata_json or {})
        return {
            "id": campaign.id,
            "name": campaign.name,
            "status": metadata.get("status"),
            "is_active": campaign.is_active,
            "starts_at": campaign.starts_at.isoformat() if campaign.starts_at else None,
            "ends_at": campaign.ends_at.isoformat() if campaign.ends_at else None,
        }

    @staticmethod
    def _verification_status(profile: CreatorProfile) -> str:
        status = CreatorModule7ContractService._enum_value(profile.status)
        if status == "active":
            return "creator.verified"
        if status in {"draft", "paused"}:
            return "creator.pending"
        if status == "suspended":
            return "creator.suspended"
        return "blocked"

    @staticmethod
    def _display_name(user: User | None) -> str | None:
        if user is None:
            return None
        for value in (user.display_name, user.full_name, user.username, user.email):
            if value:
                candidate = str(value).strip()
                if candidate:
                    return candidate
        return user.id

    @staticmethod
    def _map_marketplace_status(source_status: str) -> tuple[str, str | None]:
        mapping = {
            CreatorMarketplaceCampaignStatus.DRAFT.value: "draft",
            CreatorMarketplaceCampaignStatus.OPEN.value: "active",
            CreatorMarketplaceCampaignStatus.ACTIVE.value: "active",
            CreatorMarketplaceCampaignStatus.COMPLETED.value: "settled",
            CreatorMarketplaceCampaignStatus.CANCELLED.value: "rejected",
        }
        mapped = mapping.get(source_status, "review")
        degraded_reason = None
        if source_status in {
            CreatorMarketplaceCampaignStatus.OPEN.value,
            CreatorMarketplaceCampaignStatus.COMPLETED.value,
            CreatorMarketplaceCampaignStatus.CANCELLED.value,
        }:
            degraded_reason = (
                "creator_campaign_status_mapped_from_marketplace: marketplace campaign status differs from "
                "Module 7 CampaignStatus and was mapped for frontend contract compatibility."
            )
        return mapped, degraded_reason

    @staticmethod
    def _clip_status(payload: dict[str, Any]) -> str | None:
        candidates = (
            payload.get("moderation_status"),
            payload.get("status"),
            CreatorModule7ContractService._nested(payload, "metadata", "moderation_status"),
            CreatorModule7ContractService._nested(payload, "metadata", "status"),
            CreatorModule7ContractService._nested(payload, "ads_engine", "moderation_status"),
        )
        for value in candidates:
            if value is None:
                continue
            candidate = str(value).strip().lower()
            if candidate in VALID_CLIP_MODERATION_STATUSES:
                return candidate
        return None

    @staticmethod
    def _transaction_type(entry: LedgerEntry, amount: Decimal) -> str:
        reason = CreatorModule7ContractService._enum_value(entry.reason)
        tx_type = CreatorModule7ContractService._enum_value(entry.transaction_type)
        if reason == LedgerEntryReason.WITHDRAWAL_HOLD.value:
            return "hold"
        if tx_type == LedgerTransactionType.WITHDRAWAL.value:
            return "debit"
        return "credit" if amount >= Decimal("0.0000") else "debit"

    @staticmethod
    def _performance_from_payload(payload: Any) -> CampaignPerformanceContract | None:
        if not isinstance(payload, dict):
            return None
        return CampaignPerformanceContract(
            views=CreatorModule7ContractService._optional_int(payload.get("views")),
            engagement=CreatorModule7ContractService._optional_int(payload.get("engagement")),
            conversions=CreatorModule7ContractService._optional_int(payload.get("conversions")),
            engagement_rate=CreatorModule7ContractService._optional_amount(payload.get("engagement_rate")),
            payout_earned=CreatorModule7ContractService._optional_amount(payload.get("payout_earned")),
        )

    @staticmethod
    def _withdrawal_fee(amount: Decimal) -> Decimal:
        normalized_amount = CreatorModule7ContractService._amount(amount)
        percentage_fee = normalized_amount * Decimal(CREATOR_WITHDRAWAL_FEE_BPS) / Decimal("10000")
        return CreatorModule7ContractService._amount(max(percentage_fee, CREATOR_MINIMUM_WITHDRAWAL_FEE))

    @staticmethod
    def _amount(value: Any) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def _optional_amount(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        return CreatorModule7ContractService._amount(value)

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None or value == "":
            return None
        return int(value)

    @staticmethod
    def _clean_optional(value: Any) -> str | None:
        if value is None:
            return None
        candidate = str(value).strip()
        return candidate or None

    @staticmethod
    def _enum_value(value: Any) -> str:
        return str(getattr(value, "value", value))

    @staticmethod
    def _nested(payload: dict[str, Any], *keys: str) -> Any:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @staticmethod
    def _parse_datetime(value: Any) -> Any | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value
        if isinstance(value, str):
            try:
                return datetime_from_iso(value)
            except ValueError:
                return None
        return None


def datetime_from_iso(value: str) -> Any:
    from datetime import datetime

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    return datetime.fromisoformat(normalized)


__all__ = [
    "CreatorContractBlocked",
    "CreatorContractNotFound",
    "CreatorModule7ContractService",
]
