from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PlayerAlias(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_aliases"
    __table_args__ = (
        UniqueConstraint("player_id", "alias", name="uq_player_aliases_player_alias"),
        Index("ix_player_aliases_alias", "alias"),
    )

    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(160), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual", server_default="manual")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerMoniker(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_monikers"
    __table_args__ = (
        UniqueConstraint("player_id", "moniker", name="uq_player_monikers_player_moniker"),
        Index("ix_player_monikers_moniker", "moniker"),
    )

    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False, index=True)
    moniker: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="nickname", server_default="nickname")
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardTier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_card_tiers"
    __table_args__ = (
        UniqueConstraint("code", name="uq_player_card_tiers_code"),
        UniqueConstraint("name", name="uq_player_card_tiers_name"),
        UniqueConstraint("rarity_rank", name="uq_player_card_tiers_rank"),
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    rarity_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    max_supply: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supply_multiplier: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=1.0, server_default="1.0")
    base_mint_price_credits: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    color_hex: Mapped[str | None] = mapped_column(String(12), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_cards"
    __table_args__ = (
        UniqueConstraint("player_id", "tier_id", "edition_code", name="uq_player_cards_player_tier_edition"),
        Index("ix_player_cards_player_id", "player_id"),
        Index("ix_player_cards_tier_id", "tier_id"),
    )

    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False)
    tier_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_card_tiers.id", ondelete="RESTRICT"), nullable=False)
    edition_code: Mapped[str] = mapped_column(String(64), nullable=False, default="base", server_default="base")
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    season_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    card_variant: Mapped[str] = mapped_column(String(64), nullable=False, default="base", server_default="base")
    supply_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    supply_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardSupplyBatch(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_card_supply_batches"
    __table_args__ = (
        UniqueConstraint("batch_key", name="uq_player_card_supply_batches_key"),
        Index("ix_player_card_supply_batches_player_card_id", "player_card_id"),
    )

    batch_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False)
    tier_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_card_tiers.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="applied", server_default="applied")
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="csv", server_default="csv")
    source_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    minted_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardHolding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_card_holdings"
    __table_args__ = (
        UniqueConstraint("player_card_id", "owner_user_id", name="uq_player_card_holdings_card_owner"),
        Index("ix_player_card_holdings_owner_user_id", "owner_user_id"),
    )

    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quantity_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    quantity_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_acquired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardHistory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_card_histories"
    __table_args__ = (Index("ix_player_card_histories_player_card_id", "player_card_id"),)

    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    delta_supply: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    delta_available: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardOwnerHistory(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_card_owner_history"
    __table_args__ = (Index("ix_player_card_owner_history_player_card_id", "player_card_id"),)

    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    from_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    to_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reference_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardEffect(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_card_effects"
    __table_args__ = (Index("ix_player_card_effects_player_card_id", "player_card_id"),)

    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    effect_type: Mapped[str] = mapped_column(String(64), nullable=False)
    effect_value: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardFormBuff(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_card_form_buffs"
    __table_args__ = (Index("ix_player_card_form_buffs_player_card_id", "player_card_id"),)

    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    buff_type: Mapped[str] = mapped_column(String(64), nullable=False)
    buff_value: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardMomentum(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_card_momentum"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_card_momentum_player_id"),
        Index("ix_player_card_momentum_player_id", "player_id"),
    )

    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False)
    last_trade_price_credits: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    momentum_7d_pct: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0, server_default="0")
    momentum_30d_pct: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0, server_default="0")
    trend_direction: Mapped[str] = mapped_column(String(16), nullable=False, default="flat", server_default="flat")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardListing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_card_listings"
    __table_args__ = (
        Index("ix_player_card_listings_player_card_id", "player_card_id"),
        Index("ix_player_card_listings_status_price", "status", "price_per_card_credits"),
        Index("ix_player_card_listings_status_negotiable", "status", "is_negotiable"),
    )

    listing_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    seller_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_card_credits: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", server_default="open", index=True)
    is_negotiable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    integrity_context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardSale(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_card_sales"
    __table_args__ = (
        UniqueConstraint("settlement_reference", name="uq_player_card_sales_settlement"),
        Index("ix_player_card_sales_player_card_id", "player_card_id"),
    )

    sale_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    listing_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    player_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=False)
    seller_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    buyer_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_card_credits: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    gross_credits: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    fee_credits: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    seller_net_credits: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="settled", server_default="settled", index=True)
    settlement_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    integrity_flags_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerCardWatchlist(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_card_watchlists"
    __table_args__ = (
        UniqueConstraint("user_id", "player_id", "player_card_id", name="uq_player_card_watchlists_user_player_card"),
        Index("ix_player_card_watchlists_user_id", "user_id"),
    )

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False)
    player_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("player_cards.id", ondelete="CASCADE"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerStatsSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_stats_snapshots"
    __table_args__ = (Index("ix_player_stats_snapshots_player_id", "player_id"),)

    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    competition_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ingestion_competitions.id", ondelete="SET NULL"), nullable=True)
    season_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ingestion_seasons.id", ondelete="SET NULL"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="snapshot", server_default="snapshot")
    stats_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerMarketValueSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "player_market_value_snapshots"
    __table_args__ = (Index("ix_player_market_value_snapshots_player_id", "player_id"),)

    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("ingestion_players.id", ondelete="CASCADE"), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_trade_price_credits: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    avg_trade_price_credits: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    volume_24h: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    listing_floor_price_credits: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    listing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    high_24h_price_credits: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    low_24h_price_credits: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
