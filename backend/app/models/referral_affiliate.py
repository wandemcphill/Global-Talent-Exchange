from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ReferralPartner(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """External promoter or a GTEX user/creator acting as an affiliate partner.

    A partner does not need a GTEX login. ``owner_user_id`` and
    ``creator_profile_id`` are set only when the promoter already has one.
    """

    __tablename__ = "referral_partners"

    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    social_handle: Mapped[str | None] = mapped_column(String(120), nullable=True)
    campaign_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    payout_method: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", server_default="manual")
    payout_destination_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    creator_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contractual_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    payout_destination_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payout_destination_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payout_currency: Mapped[str] = mapped_column(String(12), nullable=False, default="NGN", server_default="NGN")
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ReferralCampaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referral_campaigns"
    __table_args__ = (UniqueConstraint("share_code_id", name="uq_referral_campaigns_share_code_id"),)

    partner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("referral_partners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    share_code_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("share_codes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_registrations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_link: Mapped[str] = mapped_column(String(255), nullable=False)


class ReferralProgrammeSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versioned programme policy. Rewards snapshot the version that created them."""

    __tablename__ = "referral_programme_settings"

    settings_key: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, default="default")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    user_bonus_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    referrer_commission_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=1000, server_default="1000")
    hold_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, server_default="7")
    payout_weekday: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    min_payout_thresholds_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    eligible_account_types_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    qualifying_deposit_types_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ReferralClick(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "referral_clicks"

    share_code_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    campaign_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ReferralPayoutBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referral_payout_batches"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_referral_payout_batches_idempotency_key"),)

    beneficiary_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    beneficiary_partner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", server_default="draft")
    payout_method: Mapped[str] = mapped_column(String(32), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    destination_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ledger_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confirmed_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReferralPayoutItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "referral_payout_items"
    __table_args__ = (UniqueConstraint("reward_id", name="uq_referral_payout_items_reward_id"),)

    batch_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("referral_payout_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reward_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("referral_rewards.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False)


class ReferralRecoveryCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referral_recovery_cases"
    __table_args__ = (UniqueConstraint("reward_id", "kind", name="uq_referral_recovery_reward_kind"),)

    reward_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("referral_rewards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referred_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open")
    deposit_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deposit_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReferralAdminAudit(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "referral_admin_audits"

    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(48), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
