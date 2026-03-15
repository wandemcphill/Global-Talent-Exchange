"""wallet treasury economy rails

Revision ID: 20260314_0037
Revises: 20260314_0036
Create Date: 2026-03-14 19:45:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260314_0037"
down_revision = "20260314_0036"
branch_labels = None
depends_on = None


purchase_order_status = sa.Enum(
    "requested",
    "reviewing",
    "processing",
    "settled",
    "failed",
    "rejected",
    "cancelled",
    "expired",
    "refunded",
    "chargeback",
    "reversed",
    "disputed",
    name="purchase_order_status",
    native_enum=False,
)
market_topup_status = sa.Enum(
    "requested",
    "reviewing",
    "approved",
    "processing",
    "settled",
    "failed",
    "rejected",
    "cancelled",
    "reversed",
    "disputed",
    name="market_topup_status",
    native_enum=False,
)
ledger_unit = sa.Enum("coin", "credit", name="ledger_unit", native_enum=False)
rate_direction = sa.Enum("fiat_per_coin", "coin_per_fiat", name="rate_direction", native_enum=False)


def upgrade() -> None:
    bind = op.get_bind()
    purchase_order_status.create(bind, checkfirst=True)
    market_topup_status.create(bind, checkfirst=True)
    ledger_unit.create(bind, checkfirst=True)
    rate_direction.create(bind, checkfirst=True)

    op.create_table(
        "fancoin_purchase_orders",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("status", purchase_order_status, nullable=False),
        sa.Column("provider_key", sa.String(length=64), nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("provider_event_id", sa.String(length=128), nullable=True),
        sa.Column("unit", ledger_unit, nullable=False),
        sa.Column("amount_fiat", sa.Numeric(20, 4), nullable=False),
        sa.Column("gross_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("fee_amount", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("net_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default="NGN"),
        sa.Column("rate_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("rate_direction", rate_direction, nullable=False),
        sa.Column("processor_mode", sa.String(length=32), nullable=False, server_default="automatic_gateway"),
        sa.Column("payout_channel", sa.String(length=64), nullable=False, server_default="gateway"),
        sa.Column("source_scope", sa.String(length=32), nullable=False, server_default="wallet"),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chargeback_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference", name="uq_fancoin_purchase_order_reference"),
    )
    op.create_index("ix_fancoin_purchase_orders_created_at", "fancoin_purchase_orders", ["created_at"], unique=False)
    op.create_index("ix_fancoin_purchase_orders_status", "fancoin_purchase_orders", ["status"], unique=False)
    op.create_index("ix_fancoin_purchase_orders_user_id", "fancoin_purchase_orders", ["user_id"], unique=False)
    op.create_index("ix_fancoin_purchase_orders_provider_key", "fancoin_purchase_orders", ["provider_key"], unique=False)
    op.create_index("ix_fancoin_purchase_orders_provider_reference", "fancoin_purchase_orders", ["provider_reference"], unique=False)
    op.create_index("ix_fancoin_purchase_orders_provider_event_id", "fancoin_purchase_orders", ["provider_event_id"], unique=False)
    op.create_index("ix_fancoin_purchase_orders_ledger_transaction_id", "fancoin_purchase_orders", ["ledger_transaction_id"], unique=False)

    op.create_table(
        "market_topups",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("status", market_topup_status, nullable=False),
        sa.Column("unit", ledger_unit, nullable=False),
        sa.Column("gross_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("fee_amount", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("net_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("source_scope", sa.String(length=32), nullable=False, server_default="market"),
        sa.Column("processor_mode", sa.String(length=32), nullable=False, server_default="internal_transfer"),
        sa.Column("payout_channel", sa.String(length=64), nullable=False, server_default="internal"),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("requested_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("settled_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference", name="uq_market_topups_reference"),
    )
    op.create_index("ix_market_topups_created_at", "market_topups", ["created_at"], unique=False)
    op.create_index("ix_market_topups_status", "market_topups", ["status"], unique=False)
    op.create_index("ix_market_topups_user_id", "market_topups", ["user_id"], unique=False)
    op.create_index("ix_market_topups_requested_by_user_id", "market_topups", ["requested_by_user_id"], unique=False)
    op.create_index("ix_market_topups_reviewed_by_user_id", "market_topups", ["reviewed_by_user_id"], unique=False)
    op.create_index("ix_market_topups_settled_by_user_id", "market_topups", ["settled_by_user_id"], unique=False)
    op.create_index("ix_market_topups_ledger_transaction_id", "market_topups", ["ledger_transaction_id"], unique=False)

    op.create_table(
        "withdrawal_reviews",
        sa.Column("withdrawal_request_id", sa.String(length=36), nullable=False),
        sa.Column("payout_request_id", sa.String(length=36), nullable=True),
        sa.Column("reviewer_user_id", sa.String(length=36), nullable=True),
        sa.Column("status_from", sa.String(length=32), nullable=False),
        sa.Column("status_to", sa.String(length=32), nullable=False),
        sa.Column("processor_mode", sa.String(length=32), nullable=True),
        sa.Column("payout_channel", sa.String(length=64), nullable=True),
        sa.Column("source_scope", sa.String(length=32), nullable=True),
        sa.Column("gross_amount", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("fee_amount", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("net_amount", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["payout_request_id"], ["payout_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["withdrawal_request_id"], ["treasury_withdrawal_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_withdrawal_reviews_created_at", "withdrawal_reviews", ["created_at"], unique=False)
    op.create_index("ix_withdrawal_reviews_withdrawal_id", "withdrawal_reviews", ["withdrawal_request_id"], unique=False)
    op.create_index("ix_withdrawal_reviews_payout_request_id", "withdrawal_reviews", ["payout_request_id"], unique=False)
    op.create_index("ix_withdrawal_reviews_reviewer_user_id", "withdrawal_reviews", ["reviewer_user_id"], unique=False)

    op.create_table(
        "economy_burn_events",
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=48), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("unit", ledger_unit, nullable=False),
        sa.Column("reason", sa.String(length=128), nullable=False),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_economy_burn_events_created_at", "economy_burn_events", ["created_at"], unique=False)
    op.create_index("ix_economy_burn_events_source", "economy_burn_events", ["source_type", "source_id"], unique=False)
    op.create_index("ix_economy_burn_events_user_id", "economy_burn_events", ["user_id"], unique=False)
    op.create_index("ix_economy_burn_events_ledger_transaction_id", "economy_burn_events", ["ledger_transaction_id"], unique=False)

    op.create_table(
        "revenue_share_rules",
        sa.Column("rule_key", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("platform_share_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("creator_share_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recipient_share_bps", sa.Integer(), nullable=True),
        sa.Column("burn_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_key", name="uq_revenue_share_rule_key"),
    )
    op.create_index("ix_revenue_share_rules_rule_key", "revenue_share_rules", ["rule_key"], unique=False)
    op.create_index("ix_revenue_share_rules_scope", "revenue_share_rules", ["scope"], unique=False)

    op.create_table(
        "gift_combo_rules",
        sa.Column("rule_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("min_combo_count", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("window_seconds", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("bonus_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_key", name="uq_gift_combo_rules_rule_key"),
    )
    op.create_index("ix_gift_combo_rules_rule_key", "gift_combo_rules", ["rule_key"], unique=False)

    op.create_table(
        "gift_combo_events",
        sa.Column("gift_transaction_id", sa.String(length=36), nullable=False),
        sa.Column("sender_user_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=36), nullable=False),
        sa.Column("gift_catalog_item_id", sa.String(length=36), nullable=False),
        sa.Column("combo_rule_id", sa.String(length=36), nullable=True),
        sa.Column("combo_rule_key", sa.String(length=64), nullable=False),
        sa.Column("combo_count", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("bonus_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bonus_amount", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0.0000")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["combo_rule_id"], ["gift_combo_rules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gift_catalog_item_id"], ["gift_catalog.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["gift_transaction_id"], ["gift_transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gift_combo_events_created_at", "gift_combo_events", ["created_at"], unique=False)
    op.create_index("ix_gift_combo_events_sender", "gift_combo_events", ["sender_user_id"], unique=False)
    op.create_index("ix_gift_combo_events_recipient", "gift_combo_events", ["recipient_user_id"], unique=False)
    op.create_index("ix_gift_combo_events_gift_transaction_id", "gift_combo_events", ["gift_transaction_id"], unique=False)
    op.create_index("ix_gift_combo_events_gift_catalog_item_id", "gift_combo_events", ["gift_catalog_item_id"], unique=False)
    op.create_index("ix_gift_combo_events_combo_rule_id", "gift_combo_events", ["combo_rule_id"], unique=False)

    op.add_column(
        "treasury_withdrawal_requests",
        sa.Column("fee_amount", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0.0000")),
    )
    op.add_column(
        "treasury_withdrawal_requests",
        sa.Column("net_amount", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0.0000")),
    )
    op.add_column(
        "treasury_withdrawal_requests",
        sa.Column("processor_mode", sa.String(length=32), nullable=False, server_default="manual_bank_transfer"),
    )
    op.add_column(
        "treasury_withdrawal_requests",
        sa.Column("payout_channel", sa.String(length=64), nullable=False, server_default="bank_transfer"),
    )
    op.add_column(
        "treasury_withdrawal_requests",
        sa.Column("source_scope", sa.String(length=32), nullable=False, server_default="trade"),
    )


def downgrade() -> None:
    op.drop_column("treasury_withdrawal_requests", "source_scope")
    op.drop_column("treasury_withdrawal_requests", "payout_channel")
    op.drop_column("treasury_withdrawal_requests", "processor_mode")
    op.drop_column("treasury_withdrawal_requests", "net_amount")
    op.drop_column("treasury_withdrawal_requests", "fee_amount")

    op.drop_index("ix_gift_combo_events_combo_rule_id", table_name="gift_combo_events")
    op.drop_index("ix_gift_combo_events_gift_catalog_item_id", table_name="gift_combo_events")
    op.drop_index("ix_gift_combo_events_gift_transaction_id", table_name="gift_combo_events")
    op.drop_index("ix_gift_combo_events_recipient", table_name="gift_combo_events")
    op.drop_index("ix_gift_combo_events_sender", table_name="gift_combo_events")
    op.drop_index("ix_gift_combo_events_created_at", table_name="gift_combo_events")
    op.drop_table("gift_combo_events")

    op.drop_index("ix_gift_combo_rules_rule_key", table_name="gift_combo_rules")
    op.drop_table("gift_combo_rules")

    op.drop_index("ix_revenue_share_rules_scope", table_name="revenue_share_rules")
    op.drop_index("ix_revenue_share_rules_rule_key", table_name="revenue_share_rules")
    op.drop_table("revenue_share_rules")

    op.drop_index("ix_economy_burn_events_ledger_transaction_id", table_name="economy_burn_events")
    op.drop_index("ix_economy_burn_events_user_id", table_name="economy_burn_events")
    op.drop_index("ix_economy_burn_events_source", table_name="economy_burn_events")
    op.drop_index("ix_economy_burn_events_created_at", table_name="economy_burn_events")
    op.drop_table("economy_burn_events")

    op.drop_index("ix_withdrawal_reviews_reviewer_user_id", table_name="withdrawal_reviews")
    op.drop_index("ix_withdrawal_reviews_payout_request_id", table_name="withdrawal_reviews")
    op.drop_index("ix_withdrawal_reviews_withdrawal_id", table_name="withdrawal_reviews")
    op.drop_index("ix_withdrawal_reviews_created_at", table_name="withdrawal_reviews")
    op.drop_table("withdrawal_reviews")

    op.drop_index("ix_market_topups_ledger_transaction_id", table_name="market_topups")
    op.drop_index("ix_market_topups_settled_by_user_id", table_name="market_topups")
    op.drop_index("ix_market_topups_reviewed_by_user_id", table_name="market_topups")
    op.drop_index("ix_market_topups_requested_by_user_id", table_name="market_topups")
    op.drop_index("ix_market_topups_user_id", table_name="market_topups")
    op.drop_index("ix_market_topups_status", table_name="market_topups")
    op.drop_index("ix_market_topups_created_at", table_name="market_topups")
    op.drop_table("market_topups")

    op.drop_index("ix_fancoin_purchase_orders_ledger_transaction_id", table_name="fancoin_purchase_orders")
    op.drop_index("ix_fancoin_purchase_orders_provider_event_id", table_name="fancoin_purchase_orders")
    op.drop_index("ix_fancoin_purchase_orders_provider_reference", table_name="fancoin_purchase_orders")
    op.drop_index("ix_fancoin_purchase_orders_provider_key", table_name="fancoin_purchase_orders")
    op.drop_index("ix_fancoin_purchase_orders_user_id", table_name="fancoin_purchase_orders")
    op.drop_index("ix_fancoin_purchase_orders_status", table_name="fancoin_purchase_orders")
    op.drop_index("ix_fancoin_purchase_orders_created_at", table_name="fancoin_purchase_orders")
    op.drop_table("fancoin_purchase_orders")

    bind = op.get_bind()
    market_topup_status.drop(bind, checkfirst=True)
    purchase_order_status.drop(bind, checkfirst=True)
