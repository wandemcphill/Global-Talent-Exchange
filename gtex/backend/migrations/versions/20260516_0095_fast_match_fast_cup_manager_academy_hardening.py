"""Harden fast match, fast cups, manager hires, and academy promotion.

Revision ID: 20260516_0095_fast_match_fast_cup_manager_academy_hardening
Revises: 20260515_0094_coin_trader_pricing_governance
Create Date: 2026-05-16 09:50:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260516_0095_fast_match_fast_cup_manager_academy_hardening"
down_revision = "20260515_0094_coin_trader_pricing_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fast_match_entitlements",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=64), nullable=True),
        sa.Column("free_match_limit", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("free_matches_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("free_matches_remaining", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("wins_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("has_lost_free_run", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("free_eligibility_exhausted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("charge_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("last_match_id", sa.String(length=80), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "season_id", name="uq_fast_match_entitlements_user_season"),
    )
    op.create_index("ix_fast_match_entitlements_user_id", "fast_match_entitlements", ["user_id"])
    op.create_index("ix_fast_match_entitlements_season_id", "fast_match_entitlements", ["season_id"])
    op.create_index("ix_fast_match_entitlements_last_match_id", "fast_match_entitlements", ["last_match_id"])

    op.create_table(
        "fast_match_settlements",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("entitlement_id", sa.String(length=36), nullable=True),
        sa.Column("result", sa.String(length=24), nullable=False),
        sa.Column("was_free", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("fan_coin_charged", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("settlement_status", sa.String(length=24), nullable=False, server_default="settled"),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("wallet_ledger_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["entitlement_id"], ["fast_match_entitlements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", name="uq_fast_match_settlements_match_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_fast_match_settlements_idempotency_key"),
    )
    op.create_index("ix_fast_match_settlements_user_id", "fast_match_settlements", ["user_id"])
    op.create_index("ix_fast_match_settlements_match_id", "fast_match_settlements", ["match_id"])
    op.create_index("ix_fast_match_settlements_entitlement_id", "fast_match_settlements", ["entitlement_id"])
    op.create_index("ix_fast_match_settlements_settlement_status", "fast_match_settlements", ["settlement_status"])
    op.create_index("ix_fast_match_settlements_idempotency_key", "fast_match_settlements", ["idempotency_key"])

    op.create_table(
        "fast_match_sessions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=80), nullable=False),
        sa.Column("live_match_key", sa.String(length=120), nullable=False),
        sa.Column("opponent_user_id", sa.String(length=80), nullable=True),
        sa.Column("home_club_id", sa.String(length=80), nullable=True),
        sa.Column("away_club_id", sa.String(length=80), nullable=True),
        sa.Column("entitlement_id", sa.String(length=36), nullable=True),
        sa.Column("settlement_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="ready"),
        sa.Column("charge_required_now", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("entry_currency", sa.String(length=16), nullable=False, server_default="credit"),
        sa.Column("fan_coin_entry_fee", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("wallet_ledger_id", sa.String(length=36), nullable=True),
        sa.Column("result", sa.String(length=24), nullable=True),
        sa.Column("viewer_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("simulation_request_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["entitlement_id"], ["fast_match_entitlements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_id"], ["fast_match_settlements.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", name="uq_fast_match_sessions_match_id"),
        sa.UniqueConstraint("live_match_key", name="uq_fast_match_sessions_live_match_key"),
    )
    op.create_index("ix_fast_match_sessions_user_id", "fast_match_sessions", ["user_id"])
    op.create_index("ix_fast_match_sessions_match_id", "fast_match_sessions", ["match_id"])
    op.create_index("ix_fast_match_sessions_live_match_key", "fast_match_sessions", ["live_match_key"])
    op.create_index("ix_fast_match_sessions_opponent_user_id", "fast_match_sessions", ["opponent_user_id"])
    op.create_index("ix_fast_match_sessions_entitlement_id", "fast_match_sessions", ["entitlement_id"])
    op.create_index("ix_fast_match_sessions_settlement_id", "fast_match_sessions", ["settlement_id"])
    op.create_index("ix_fast_match_sessions_status", "fast_match_sessions", ["status"])

    op.create_table(
        "fast_cup_registrations",
        sa.Column("cup_id", sa.String(length=80), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("lineup_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("entry_fee_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("entry_fee_currency", sa.String(length=16), nullable=False, server_default="credit"),
        sa.Column("escrow_status", sa.String(length=24), nullable=False, server_default="none"),
        sa.Column("wallet_ledger_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cup_id", "club_id", name="uq_fast_cup_registrations_cup_club"),
    )
    op.create_index("ix_fast_cup_registrations_cup_id", "fast_cup_registrations", ["cup_id"])
    op.create_index("ix_fast_cup_registrations_user_id", "fast_cup_registrations", ["user_id"])
    op.create_index("ix_fast_cup_registrations_club_id", "fast_cup_registrations", ["club_id"])
    op.create_index("ix_fast_cup_registrations_escrow_status", "fast_cup_registrations", ["escrow_status"])

    op.create_table(
        "fast_cup_payouts",
        sa.Column("cup_id", sa.String(length=80), nullable=False),
        sa.Column("registration_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("finish", sa.String(length=32), nullable=False),
        sa.Column("payout_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("payout_currency", sa.String(length=16), nullable=False, server_default="credit"),
        sa.Column("payout_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("wallet_ledger_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registration_id"], ["fast_cup_registrations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_fast_cup_payouts_idempotency_key"),
        sa.UniqueConstraint("cup_id", "registration_id", "finish", name="uq_fast_cup_payouts_cup_registration_finish"),
    )
    op.create_index("ix_fast_cup_payouts_cup_id", "fast_cup_payouts", ["cup_id"])
    op.create_index("ix_fast_cup_payouts_registration_id", "fast_cup_payouts", ["registration_id"])
    op.create_index("ix_fast_cup_payouts_user_id", "fast_cup_payouts", ["user_id"])
    op.create_index("ix_fast_cup_payouts_club_id", "fast_cup_payouts", ["club_id"])
    op.create_index("ix_fast_cup_payouts_payout_status", "fast_cup_payouts", ["payout_status"])
    op.create_index("ix_fast_cup_payouts_idempotency_key", "fast_cup_payouts", ["idempotency_key"])

    with op.batch_alter_table("manager_contracts") as batch_op:
        batch_op.add_column(sa.Column("payment_unit", sa.String(length=16), nullable=False, server_default="credit"))
        batch_op.add_column(sa.Column("settlement_status", sa.String(length=24), nullable=False, server_default="pending"))
        batch_op.add_column(sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("settlement_metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))


def downgrade() -> None:
    with op.batch_alter_table("manager_contracts") as batch_op:
        batch_op.drop_column("settlement_metadata_json")
        batch_op.drop_column("settled_at")
        batch_op.drop_column("ledger_transaction_id")
        batch_op.drop_column("settlement_status")
        batch_op.drop_column("payment_unit")

    op.drop_index("ix_fast_cup_payouts_idempotency_key", table_name="fast_cup_payouts")
    op.drop_index("ix_fast_cup_payouts_payout_status", table_name="fast_cup_payouts")
    op.drop_index("ix_fast_cup_payouts_club_id", table_name="fast_cup_payouts")
    op.drop_index("ix_fast_cup_payouts_user_id", table_name="fast_cup_payouts")
    op.drop_index("ix_fast_cup_payouts_registration_id", table_name="fast_cup_payouts")
    op.drop_index("ix_fast_cup_payouts_cup_id", table_name="fast_cup_payouts")
    op.drop_table("fast_cup_payouts")

    op.drop_index("ix_fast_cup_registrations_escrow_status", table_name="fast_cup_registrations")
    op.drop_index("ix_fast_cup_registrations_club_id", table_name="fast_cup_registrations")
    op.drop_index("ix_fast_cup_registrations_user_id", table_name="fast_cup_registrations")
    op.drop_index("ix_fast_cup_registrations_cup_id", table_name="fast_cup_registrations")
    op.drop_table("fast_cup_registrations")

    op.drop_index("ix_fast_match_sessions_status", table_name="fast_match_sessions")
    op.drop_index("ix_fast_match_sessions_settlement_id", table_name="fast_match_sessions")
    op.drop_index("ix_fast_match_sessions_entitlement_id", table_name="fast_match_sessions")
    op.drop_index("ix_fast_match_sessions_opponent_user_id", table_name="fast_match_sessions")
    op.drop_index("ix_fast_match_sessions_live_match_key", table_name="fast_match_sessions")
    op.drop_index("ix_fast_match_sessions_match_id", table_name="fast_match_sessions")
    op.drop_index("ix_fast_match_sessions_user_id", table_name="fast_match_sessions")
    op.drop_table("fast_match_sessions")

    op.drop_index("ix_fast_match_settlements_idempotency_key", table_name="fast_match_settlements")
    op.drop_index("ix_fast_match_settlements_settlement_status", table_name="fast_match_settlements")
    op.drop_index("ix_fast_match_settlements_entitlement_id", table_name="fast_match_settlements")
    op.drop_index("ix_fast_match_settlements_match_id", table_name="fast_match_settlements")
    op.drop_index("ix_fast_match_settlements_user_id", table_name="fast_match_settlements")
    op.drop_table("fast_match_settlements")

    op.drop_index("ix_fast_match_entitlements_last_match_id", table_name="fast_match_entitlements")
    op.drop_index("ix_fast_match_entitlements_season_id", table_name="fast_match_entitlements")
    op.drop_index("ix_fast_match_entitlements_user_id", table_name="fast_match_entitlements")
    op.drop_table("fast_match_entitlements")
