from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CreatorMarketplaceCampaignPayoutType(StrEnum):
    FIXED = "fixed"
    PERFORMANCE = "performance"


class CreatorMarketplaceCampaignPayoutBasis(StrEnum):
    VIEWS = "views"
    ENGAGEMENT = "engagement"
    CONVERSIONS = "conversions"


class CreatorMarketplaceCampaignStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CreatorMarketplaceOfferStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class CreatorMarketplaceCampaign(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_marketplace_campaigns"
    __table_args__ = (
        Index("ix_creator_marketplace_campaigns_brand_id", "brand_id"),
        Index("ix_creator_marketplace_campaigns_status", "status"),
        Index("ix_creator_marketplace_campaigns_title", "title"),
    )

    brand_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    budget: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    target_formats: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    target_audience: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    payout_type: Mapped[CreatorMarketplaceCampaignPayoutType] = mapped_column(
        Enum(
            CreatorMarketplaceCampaignPayoutType,
            name="creator_marketplace_campaign_payout_type",
            native_enum=False,
        ),
        nullable=False,
        default=CreatorMarketplaceCampaignPayoutType.FIXED,
        server_default=CreatorMarketplaceCampaignPayoutType.FIXED.value,
    )
    payout_basis: Mapped[CreatorMarketplaceCampaignPayoutBasis] = mapped_column(
        Enum(
            CreatorMarketplaceCampaignPayoutBasis,
            name="creator_marketplace_campaign_payout_basis",
            native_enum=False,
        ),
        nullable=False,
        default=CreatorMarketplaceCampaignPayoutBasis.VIEWS,
        server_default=CreatorMarketplaceCampaignPayoutBasis.VIEWS.value,
    )
    payout_rate: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=0, server_default="0.0000")
    platform_fee_bps: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1000,
        server_default="1000",
    )
    status: Mapped[CreatorMarketplaceCampaignStatus] = mapped_column(
        Enum(
            CreatorMarketplaceCampaignStatus,
            name="creator_marketplace_campaign_status",
            native_enum=False,
        ),
        nullable=False,
        default=CreatorMarketplaceCampaignStatus.OPEN,
        server_default=CreatorMarketplaceCampaignStatus.OPEN.value,
    )


class CreatorMarketplaceOffer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_marketplace_offers"
    __table_args__ = (
        UniqueConstraint(
            "creator_id",
            "campaign_id",
            name="uq_creator_marketplace_offers_creator_campaign",
        ),
        Index("ix_creator_marketplace_offers_campaign_id", "campaign_id"),
        Index("ix_creator_marketplace_offers_creator_id", "creator_id"),
        Index("ix_creator_marketplace_offers_status", "status"),
    )

    creator_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_marketplace_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    proposed_price: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CreatorMarketplaceOfferStatus] = mapped_column(
        Enum(
            CreatorMarketplaceOfferStatus,
            name="creator_marketplace_offer_status",
            native_enum=False,
        ),
        nullable=False,
        default=CreatorMarketplaceOfferStatus.PENDING,
        server_default=CreatorMarketplaceOfferStatus.PENDING.value,
    )
    match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    match_factors: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class CreatorMarketplaceParticipation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "creator_marketplace_participations"
    __table_args__ = (
        UniqueConstraint(
            "creator_id",
            "campaign_id",
            name="uq_creator_marketplace_participations_creator_campaign",
        ),
        Index("ix_creator_marketplace_participations_campaign_id", "campaign_id"),
        Index("ix_creator_marketplace_participations_creator_id", "creator_id"),
        Index("ix_creator_marketplace_participations_wallet_transaction_id", "wallet_transaction_id"),
    )

    creator_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    campaign_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_marketplace_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    offer_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("creator_marketplace_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    clips_submitted: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    performance_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    gross_payout: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=0, server_default="0.0000")
    payout_earned: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, default=0, server_default="0.0000")
    platform_fee_amount: Mapped[float] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        default=0,
        server_default="0.0000",
    )
    wallet_transaction_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    brand_feedback_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    reputation_score_snapshot: Mapped[float | None] = mapped_column(Float, nullable=True)


class CreatorMarketplaceReputationScore(TimestampMixin, Base):
    __tablename__ = "creator_marketplace_reputation_scores"
    __table_args__ = (
        Index("ix_creator_marketplace_reputation_scores_reputation_score", "reputation_score"),
        Index("ix_creator_marketplace_reputation_scores_updated_at", "updated_at"),
    )

    creator_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("creator_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    delivery_success_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50")
    campaign_performance_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50")
    brand_feedback_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50")
    reputation_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0, server_default="50")
    completed_campaigns: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


__all__ = [
    "CreatorMarketplaceCampaign",
    "CreatorMarketplaceCampaignPayoutBasis",
    "CreatorMarketplaceCampaignPayoutType",
    "CreatorMarketplaceCampaignStatus",
    "CreatorMarketplaceOffer",
    "CreatorMarketplaceOfferStatus",
    "CreatorMarketplaceParticipation",
    "CreatorMarketplaceReputationScore",
]
