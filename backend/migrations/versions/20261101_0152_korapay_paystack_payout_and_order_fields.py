"""Add KoraPay and Paystack payout, order tracking, and idempotency fields.

Revision ID: 20261101_0152_korapay_paystack_payout_and_order_fields
Revises: 20261027_0151_owner_world_tick_date
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261101_0152_korapay_paystack_payout_and_order_fields"
down_revision = "20261027_0151_owner_world_tick_date"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "fancoin_purchase_orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("fancoin_purchase_orders")}
        if "idempotency_key" not in columns:
            op.add_column("fancoin_purchase_orders", sa.Column("idempotency_key", sa.String(128), nullable=True))
            op.create_index("ix_fancoin_purchase_orders_idempotency_key", "fancoin_purchase_orders", ["idempotency_key"])
        if "processor_fee" not in columns:
            op.add_column(
                "fancoin_purchase_orders",
                sa.Column("processor_fee", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
            )
        if "purchase_purpose" not in columns:
            op.add_column(
                "fancoin_purchase_orders",
                sa.Column("purchase_purpose", sa.String(64), nullable=False, server_default="wallet_top_up"),
            )
        if "account_type_snapshot" not in columns:
            op.add_column("fancoin_purchase_orders", sa.Column("account_type_snapshot", sa.String(32), nullable=True))

    if "treasury_withdrawal_requests" in tables:
        columns = {column["name"] for column in inspector.get_columns("treasury_withdrawal_requests")}
        if "provider_key" not in columns:
            op.add_column("treasury_withdrawal_requests", sa.Column("provider_key", sa.String(64), nullable=True))
            op.create_index("ix_treasury_withdrawal_provider_key", "treasury_withdrawal_requests", ["provider_key"])
        if "provider_reference" not in columns:
            op.add_column("treasury_withdrawal_requests", sa.Column("provider_reference", sa.String(128), nullable=True))
            op.create_index("ix_treasury_withdrawal_provider_reference", "treasury_withdrawal_requests", ["provider_reference"])
        if "provider_transfer_code" not in columns:
            op.add_column("treasury_withdrawal_requests", sa.Column("provider_transfer_code", sa.String(128), nullable=True))
            op.create_index("ix_treasury_withdrawal_provider_transfer_code", "treasury_withdrawal_requests", ["provider_transfer_code"])
        if "processor_fee" not in columns:
            op.add_column(
                "treasury_withdrawal_requests",
                sa.Column("processor_fee", sa.Numeric(20, 4), nullable=False, server_default="0.0000"),
            )
        if "is_manual_reconciliation" not in columns:
            op.add_column(
                "treasury_withdrawal_requests",
                sa.Column("is_manual_reconciliation", sa.Boolean(), nullable=False, server_default="0"),
            )
        if "failed_at" not in columns:
            op.add_column("treasury_withdrawal_requests", sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))
        if "reversed_at" not in columns:
            op.add_column("treasury_withdrawal_requests", sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True))
        if "failure_reason" not in columns:
            op.add_column("treasury_withdrawal_requests", sa.Column("failure_reason", sa.String(255), nullable=True))
        if "raw_payload" not in columns:
            op.add_column("treasury_withdrawal_requests", sa.Column("raw_payload", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "treasury_withdrawal_requests" in tables:
        columns = {column["name"] for column in inspector.get_columns("treasury_withdrawal_requests")}
        for col in (
            "raw_payload",
            "failure_reason",
            "reversed_at",
            "failed_at",
            "is_manual_reconciliation",
            "processor_fee",
            "provider_transfer_code",
            "provider_reference",
            "provider_key",
        ):
            if col in columns:
                op.drop_column("treasury_withdrawal_requests", col)

    if "fancoin_purchase_orders" in tables:
        columns = {column["name"] for column in inspector.get_columns("fancoin_purchase_orders")}
        for col in ("account_type_snapshot", "purchase_purpose", "processor_fee", "idempotency_key"):
            if col in columns:
                op.drop_column("fancoin_purchase_orders", col)
