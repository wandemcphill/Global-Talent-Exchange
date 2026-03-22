from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ManagerCatalogEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_catalog_entries"
    __table_args__ = (
        UniqueConstraint("manager_id", name="uq_manager_catalog_entries_manager_id"),
    )

    manager_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    rarity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    mentality: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tactics: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    traits: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    substitution_tendency: Mapped[str] = mapped_column(String(64), nullable=False)
    philosophy_summary: Mapped[str] = mapped_column(Text, nullable=False)
    club_associations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    supply_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supply_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ManagerHolding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_holdings"

    asset_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    manager_id: Mapped[str] = mapped_column(
        String(120),
        ForeignKey("manager_catalog_entries.manager_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="owned", index=True)
    acquired_at: Mapped[str] = mapped_column(String(64), nullable=False)


class ManagerTradeListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_trade_listings"
    __table_args__ = (
        UniqueConstraint("asset_id", "status", name="uq_manager_trade_listings_asset_status"),
    )

    listing_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    asset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("manager_holdings.asset_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seller_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seller_name: Mapped[str] = mapped_column(String(160), nullable=False)
    asking_price_credits: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", index=True)


class ManagerTradeRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "manager_trade_records"

    trade_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    mode: Mapped[str] = mapped_column(String(24), nullable=False)
    listing_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    proposer_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    requested_asset_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    gross_credits: Mapped[str] = mapped_column(String(64), nullable=False)
    fee_credits: Mapped[str] = mapped_column(String(64), nullable=False)
    seller_net_credits: Mapped[str] = mapped_column(String(64), nullable=False)
    settlement_reference: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    settlement_status: Mapped[str] = mapped_column(String(24), nullable=False, default="settled", index=True)
    immediate_withdrawal_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")


class ManagerSettlementRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "manager_settlement_records"
    __table_args__ = (
        UniqueConstraint("reference", name="uq_manager_settlement_records_reference"),
    )

    reference: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    trade_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    listing_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="settled", index=True)
    gross_credits: Mapped[str] = mapped_column(String(64), nullable=False)
    fee_credits: Mapped[str] = mapped_column(String(64), nullable=False)
    seller_net_credits: Mapped[str] = mapped_column(String(64), nullable=False)
    eligible_immediately: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    settled_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)


class ManagerTeamAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_team_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_manager_team_assignments_user_id"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    main_manager_asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manager_holdings.asset_id", ondelete="SET NULL"), nullable=True)
    academy_manager_asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("manager_holdings.asset_id", ondelete="SET NULL"), nullable=True)


class ManagerCompetitionSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manager_competition_settings"
    __table_args__ = (
        UniqueConstraint("code", name="uq_manager_competition_settings_code"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    minimum_viable_participants: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    geo_locked_regions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allow_fallback_fill: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    fallback_source_regions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class ManagerAuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "manager_audit_logs"

    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(320), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
