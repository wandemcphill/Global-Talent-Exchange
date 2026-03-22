"""player card marketplace

Revision ID: 20260314_0036b
Revises: 20260314_0036
Create Date: 2026-03-14 18:05:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260314_0036b"
down_revision = "20260314_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_aliases",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("alias", sa.String(length=160), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "alias", name="uq_player_aliases_player_alias"),
    )
    op.create_index("ix_player_aliases_alias", "player_aliases", ["alias"], unique=False)
    op.create_index(op.f("ix_player_aliases_player_id"), "player_aliases", ["player_id"], unique=False)

    op.create_table(
        "player_monikers",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("moniker", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="nickname"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "moniker", name="uq_player_monikers_player_moniker"),
    )
    op.create_index("ix_player_monikers_moniker", "player_monikers", ["moniker"], unique=False)
    op.create_index(op.f("ix_player_monikers_player_id"), "player_monikers", ["player_id"], unique=False)

    op.create_table(
        "player_card_tiers",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("rarity_rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_supply", sa.Integer(), nullable=True),
        sa.Column("supply_multiplier", sa.Numeric(10, 4), nullable=False, server_default="1.0"),
        sa.Column("base_mint_price_credits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("color_hex", sa.String(length=12), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_player_card_tiers_code"),
        sa.UniqueConstraint("name", name="uq_player_card_tiers_name"),
        sa.UniqueConstraint("rarity_rank", name="uq_player_card_tiers_rank"),
    )
    op.create_index(op.f("ix_player_card_tiers_code"), "player_card_tiers", ["code"], unique=False)

    op.create_table(
        "player_cards",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("tier_id", sa.String(length=36), nullable=False),
        sa.Column("edition_code", sa.String(length=64), nullable=False, server_default="base"),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("season_label", sa.String(length=64), nullable=True),
        sa.Column("card_variant", sa.String(length=64), nullable=False, server_default="base"),
        sa.Column("supply_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("supply_available", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tier_id"], ["player_card_tiers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "tier_id", "edition_code", name="uq_player_cards_player_tier_edition"),
    )
    op.create_index("ix_player_cards_player_id", "player_cards", ["player_id"], unique=False)
    op.create_index("ix_player_cards_tier_id", "player_cards", ["tier_id"], unique=False)

    op.create_table(
        "player_card_supply_batches",
        sa.Column("batch_key", sa.String(length=128), nullable=False),
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("tier_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="applied"),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default="csv"),
        sa.Column("source_reference", sa.String(length=120), nullable=True),
        sa.Column("minted_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("assigned_user_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["minted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tier_id"], ["player_card_tiers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_key", name="uq_player_card_supply_batches_key"),
    )
    op.create_index("ix_player_card_supply_batches_player_card_id", "player_card_supply_batches", ["player_card_id"], unique=False)
    op.create_index(op.f("ix_player_card_supply_batches_batch_key"), "player_card_supply_batches", ["batch_key"], unique=False)

    op.create_table(
        "player_card_holdings",
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_acquired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_card_id", "owner_user_id", name="uq_player_card_holdings_card_owner"),
    )
    op.create_index("ix_player_card_holdings_owner_user_id", "player_card_holdings", ["owner_user_id"], unique=False)

    op.create_table(
        "player_card_histories",
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("delta_supply", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delta_available", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_card_histories_player_card_id", "player_card_histories", ["player_card_id"], unique=False)
    op.create_index(op.f("ix_player_card_histories_event_type"), "player_card_histories", ["event_type"], unique=False)

    op.create_table(
        "player_card_owner_history",
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("from_user_id", sa.String(length=36), nullable=True),
        sa.Column("to_user_id", sa.String(length=36), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_card_owner_history_player_card_id", "player_card_owner_history", ["player_card_id"], unique=False)
    op.create_index(op.f("ix_player_card_owner_history_event_type"), "player_card_owner_history", ["event_type"], unique=False)
    op.create_index(op.f("ix_player_card_owner_history_reference_id"), "player_card_owner_history", ["reference_id"], unique=False)

    op.create_table(
        "player_card_effects",
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("effect_type", sa.String(length=64), nullable=False),
        sa.Column("effect_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_card_effects_player_card_id", "player_card_effects", ["player_card_id"], unique=False)

    op.create_table(
        "player_card_form_buffs",
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("buff_type", sa.String(length=64), nullable=False),
        sa.Column("buff_value", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_card_form_buffs_player_card_id", "player_card_form_buffs", ["player_card_id"], unique=False)

    op.create_table(
        "player_card_momentum",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("last_trade_price_credits", sa.Numeric(18, 4), nullable=True),
        sa.Column("momentum_7d_pct", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("momentum_30d_pct", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("trend_direction", sa.String(length=16), nullable=False, server_default="flat"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_player_card_momentum_player_id"),
    )
    op.create_index("ix_player_card_momentum_player_id", "player_card_momentum", ["player_id"], unique=False)

    op.create_table(
        "player_card_listings",
        sa.Column("listing_id", sa.String(length=36), nullable=False),
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("seller_user_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_per_card_credits", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", name="uq_player_card_listings_listing_id"),
    )
    op.create_index("ix_player_card_listings_player_card_id", "player_card_listings", ["player_card_id"], unique=False)
    op.create_index(op.f("ix_player_card_listings_status"), "player_card_listings", ["status"], unique=False)

    op.create_table(
        "player_card_sales",
        sa.Column("sale_id", sa.String(length=36), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("seller_user_id", sa.String(length=36), nullable=False),
        sa.Column("buyer_user_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_per_card_credits", sa.Numeric(18, 4), nullable=False),
        sa.Column("gross_credits", sa.Numeric(18, 4), nullable=False),
        sa.Column("fee_credits", sa.Numeric(18, 4), nullable=False),
        sa.Column("seller_net_credits", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="settled"),
        sa.Column("settlement_reference", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sale_id", name="uq_player_card_sales_sale_id"),
        sa.UniqueConstraint("settlement_reference", name="uq_player_card_sales_settlement"),
    )
    op.create_index("ix_player_card_sales_player_card_id", "player_card_sales", ["player_card_id"], unique=False)
    op.create_index(op.f("ix_player_card_sales_listing_id"), "player_card_sales", ["listing_id"], unique=False)
    op.create_index(op.f("ix_player_card_sales_status"), "player_card_sales", ["status"], unique=False)

    op.create_table(
        "player_card_watchlists",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_card_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "player_id", "player_card_id", name="uq_player_card_watchlists_user_player_card"),
    )
    op.create_index("ix_player_card_watchlists_user_id", "player_card_watchlists", ["user_id"], unique=False)

    op.create_table(
        "player_stats_snapshots",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False, server_default="snapshot"),
        sa.Column("stats_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["competition_id"], ["ingestion_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["ingestion_seasons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_stats_snapshots_player_id", "player_stats_snapshots", ["player_id"], unique=False)

    op.create_table(
        "player_market_value_snapshots",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_trade_price_credits", sa.Numeric(18, 4), nullable=True),
        sa.Column("avg_trade_price_credits", sa.Numeric(18, 4), nullable=True),
        sa.Column("volume_24h", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("listing_floor_price_credits", sa.Numeric(18, 4), nullable=True),
        sa.Column("listing_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_24h_price_credits", sa.Numeric(18, 4), nullable=True),
        sa.Column("low_24h_price_credits", sa.Numeric(18, 4), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_market_value_snapshots_player_id", "player_market_value_snapshots", ["player_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_player_market_value_snapshots_player_id", table_name="player_market_value_snapshots")
    op.drop_table("player_market_value_snapshots")

    op.drop_index("ix_player_stats_snapshots_player_id", table_name="player_stats_snapshots")
    op.drop_table("player_stats_snapshots")

    op.drop_index("ix_player_card_watchlists_user_id", table_name="player_card_watchlists")
    op.drop_table("player_card_watchlists")

    op.drop_index(op.f("ix_player_card_sales_status"), table_name="player_card_sales")
    op.drop_index(op.f("ix_player_card_sales_listing_id"), table_name="player_card_sales")
    op.drop_index("ix_player_card_sales_player_card_id", table_name="player_card_sales")
    op.drop_table("player_card_sales")

    op.drop_index(op.f("ix_player_card_listings_status"), table_name="player_card_listings")
    op.drop_index("ix_player_card_listings_player_card_id", table_name="player_card_listings")
    op.drop_table("player_card_listings")

    op.drop_index("ix_player_card_momentum_player_id", table_name="player_card_momentum")
    op.drop_table("player_card_momentum")

    op.drop_index("ix_player_card_form_buffs_player_card_id", table_name="player_card_form_buffs")
    op.drop_table("player_card_form_buffs")

    op.drop_index("ix_player_card_effects_player_card_id", table_name="player_card_effects")
    op.drop_table("player_card_effects")

    op.drop_index(op.f("ix_player_card_owner_history_reference_id"), table_name="player_card_owner_history")
    op.drop_index(op.f("ix_player_card_owner_history_event_type"), table_name="player_card_owner_history")
    op.drop_index("ix_player_card_owner_history_player_card_id", table_name="player_card_owner_history")
    op.drop_table("player_card_owner_history")

    op.drop_index(op.f("ix_player_card_histories_event_type"), table_name="player_card_histories")
    op.drop_index("ix_player_card_histories_player_card_id", table_name="player_card_histories")
    op.drop_table("player_card_histories")

    op.drop_index("ix_player_card_holdings_owner_user_id", table_name="player_card_holdings")
    op.drop_table("player_card_holdings")

    op.drop_index(op.f("ix_player_card_supply_batches_batch_key"), table_name="player_card_supply_batches")
    op.drop_index("ix_player_card_supply_batches_player_card_id", table_name="player_card_supply_batches")
    op.drop_table("player_card_supply_batches")

    op.drop_index("ix_player_cards_tier_id", table_name="player_cards")
    op.drop_index("ix_player_cards_player_id", table_name="player_cards")
    op.drop_table("player_cards")

    op.drop_index(op.f("ix_player_card_tiers_code"), table_name="player_card_tiers")
    op.drop_table("player_card_tiers")

    op.drop_index(op.f("ix_player_monikers_player_id"), table_name="player_monikers")
    op.drop_index("ix_player_monikers_moniker", table_name="player_monikers")
    op.drop_table("player_monikers")

    op.drop_index(op.f("ix_player_aliases_player_id"), table_name="player_aliases")
    op.drop_index("ix_player_aliases_alias", table_name="player_aliases")
    op.drop_table("player_aliases")
