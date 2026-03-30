"""Add economy governor, FX pricing, and player token-market tables.

Revision ID: 20260327_0051_economy_governor_player_tokens_and_fx
Revises: 20260327_0050_admin_finance_control_tower
Create Date: 2026-03-27 22:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0051_economy_governor_player_tokens_and_fx"
down_revision = "20260327_0050_admin_finance_control_tower"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "economy_governor_policies",
        sa.Column("policy_key", sa.String(length=32), nullable=False, server_default="default"),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="auto"),
        sa.Column("tournament_entry_multiplier", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
        sa.Column("match_view_cost_multiplier", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
        sa.Column("reward_payout_multiplier", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
        sa.Column("conversion_bonus_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("burn_bonus_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_metrics_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_actions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_economy_governor_policies")),
        sa.UniqueConstraint("policy_key", name="uq_economy_governor_policy_key"),
    )

    op.create_table(
        "fx_rates",
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("rate_to_naira", sa.Numeric(20, 6), nullable=False, server_default="1.000000"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fx_rates")),
        sa.UniqueConstraint("currency", name="uq_fx_rates_currency"),
    )
    op.create_index(op.f("ix_fx_rates_currency"), "fx_rates", ["currency"], unique=False)

    op.create_table(
        "regional_pricing_rules",
        sa.Column("region_code", sa.String(length=16), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("price_multiplier", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
        sa.Column("withdrawal_limit_multiplier", sa.Numeric(12, 4), nullable=False, server_default="1.0000"),
        sa.Column("kyc_tier_label", sa.String(length=32), nullable=False, server_default="standard"),
        sa.Column("tax_tracking_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("compliance_note", sa.String(length=255), nullable=True),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_regional_pricing_rules")),
        sa.UniqueConstraint("region_code", name="uq_regional_pricing_rules_region_code"),
    )
    op.create_index(op.f("ix_regional_pricing_rules_region_code"), "regional_pricing_rules", ["region_code"], unique=False)

    op.create_table(
        "player_share_markets",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("total_shares", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("circulating_shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("share_price_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("revenue_distributed_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_player_share_markets")),
        sa.UniqueConstraint("player_id", name="uq_player_share_markets_player_id"),
    )
    op.create_index(op.f("ix_player_share_markets_player_id"), "player_share_markets", ["player_id"], unique=False)

    op.create_table(
        "player_share_holdings",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_cost_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("dividends_earned_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_player_share_holdings")),
        sa.UniqueConstraint("user_id", "player_id", name="uq_player_share_holdings_user_player"),
    )
    op.create_index(op.f("ix_player_share_holdings_player_id"), "player_share_holdings", ["player_id"], unique=False)
    op.create_index(op.f("ix_player_share_holdings_user_id"), "player_share_holdings", ["user_id"], unique=False)

    op.create_table(
        "player_share_events",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("share_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_per_share_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("gross_amount_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_player_share_events")),
    )
    op.create_index(op.f("ix_player_share_events_event_type"), "player_share_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_player_share_events_player_id"), "player_share_events", ["player_id"], unique=False)
    op.create_index(op.f("ix_player_share_events_user_id"), "player_share_events", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_player_share_events_user_id"), table_name="player_share_events")
    op.drop_index(op.f("ix_player_share_events_player_id"), table_name="player_share_events")
    op.drop_index(op.f("ix_player_share_events_event_type"), table_name="player_share_events")
    op.drop_table("player_share_events")

    op.drop_index(op.f("ix_player_share_holdings_user_id"), table_name="player_share_holdings")
    op.drop_index(op.f("ix_player_share_holdings_player_id"), table_name="player_share_holdings")
    op.drop_table("player_share_holdings")

    op.drop_index(op.f("ix_player_share_markets_player_id"), table_name="player_share_markets")
    op.drop_table("player_share_markets")

    op.drop_index(op.f("ix_regional_pricing_rules_region_code"), table_name="regional_pricing_rules")
    op.drop_table("regional_pricing_rules")

    op.drop_index(op.f("ix_fx_rates_currency"), table_name="fx_rates")
    op.drop_table("fx_rates")

    op.drop_table("economy_governor_policies")
