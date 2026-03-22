"""Base backend foundation for auth, users, and append-only ledger."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from backend.migrations.ingestion_tables import downgrade_ingestion_tables, upgrade_ingestion_tables

revision = "20260311_0001"
down_revision = None
branch_labels = None
depends_on = None

user_role = sa.Enum("user", "admin", name="user_role", native_enum=False)
kyc_status = sa.Enum("unverified", "pending", "verified", "rejected", name="kyc_status", native_enum=False)
ledger_unit = sa.Enum("coin", "credit", name="ledger_unit", native_enum=False)
ledger_account_kind = sa.Enum("user", "system", "escrow", name="ledger_account_kind", native_enum=False)
ledger_entry_reason = sa.Enum(
    "deposit",
    "withdrawal_hold",
    "withdrawal_settlement",
    "adjustment",
    "trade_settlement",
    "competition_entry",
    "competition_reward",
    name="ledger_entry_reason",
    native_enum=False,
)
payment_provider = sa.Enum("monnify", "flutterwave", "paystack", name="payment_provider", native_enum=False)
payment_status = sa.Enum("pending", "verified", "failed", "reversed", name="payment_status", native_enum=False)
payout_status = sa.Enum(
    "requested",
    "reviewing",
    "held",
    "processing",
    "completed",
    "rejected",
    "failed",
    name="payout_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("kyc_status", kyc_status, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)

    op.create_table(
        "ledger_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("unit", ledger_unit, nullable=False),
        sa.Column("kind", ledger_account_kind, nullable=False),
        sa.Column("allow_negative", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], name="fk_ledger_accounts_owner_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_accounts"),
        sa.UniqueConstraint("code", name="uq_ledger_accounts_code"),
        sa.UniqueConstraint("owner_user_id", "unit", "kind", name="uq_ledger_accounts_owner_unit_kind"),
    )
    op.create_index("ix_ledger_accounts_code", "ledger_accounts", ["code"], unique=False)
    op.create_index("ix_ledger_accounts_owner_user_id", "ledger_accounts", ["owner_user_id"], unique=False)

    op.create_table(
        "payment_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("provider", payment_provider, nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=False),
        sa.Column("provider_event_id", sa.String(length=128), nullable=True),
        sa.Column("pack_code", sa.String(length=64), nullable=True),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("unit", ledger_unit, nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_payment_events_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_payment_events"),
        sa.UniqueConstraint("provider_reference", name="uq_payment_events_provider_reference"),
    )
    op.create_index("ix_payment_events_user_id", "payment_events", ["user_id"], unique=False)
    op.create_index("ix_payment_events_provider_reference", "payment_events", ["provider_reference"], unique=False)
    op.create_index("ix_payment_events_provider_event_id", "payment_events", ["provider_event_id"], unique=False)
    op.create_index("ix_payment_events_ledger_transaction_id", "payment_events", ["ledger_transaction_id"], unique=False)

    op.create_table(
        "payout_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("unit", ledger_unit, nullable=False),
        sa.Column("status", payout_status, nullable=False),
        sa.Column("destination_reference", sa.String(length=255), nullable=False),
        sa.Column("hold_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("settlement_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["ledger_accounts.id"], name="fk_payout_requests_account_id_ledger_accounts", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_payout_requests_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_payout_requests"),
    )
    op.create_index("ix_payout_requests_user_id", "payout_requests", ["user_id"], unique=False)
    op.create_index("ix_payout_requests_account_id", "payout_requests", ["account_id"], unique=False)
    op.create_index("ix_payout_requests_hold_transaction_id", "payout_requests", ["hold_transaction_id"], unique=False)
    op.create_index("ix_payout_requests_settlement_transaction_id", "payout_requests", ["settlement_transaction_id"], unique=False)

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("transaction_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("unit", ledger_unit, nullable=False),
        sa.Column("reason", ledger_entry_reason, nullable=False),
        sa.Column("reference", sa.String(length=128), nullable=True),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["ledger_accounts.id"], name="fk_ledger_entries_account_id_ledger_accounts", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_ledger_entries_created_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ledger_entries"),
    )
    op.create_index("ix_ledger_entries_transaction_id", "ledger_entries", ["transaction_id"], unique=False)
    op.create_index("ix_ledger_entries_account_id", "ledger_entries", ["account_id"], unique=False)
    op.create_index("ix_ledger_entries_reference", "ledger_entries", ["reference"], unique=False)
    op.create_index("ix_ledger_entries_external_reference", "ledger_entries", ["external_reference"], unique=False)

    upgrade_ingestion_tables()


def downgrade() -> None:
    downgrade_ingestion_tables()

    op.drop_index("ix_ledger_entries_external_reference", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_reference", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_account_id", table_name="ledger_entries")
    op.drop_index("ix_ledger_entries_transaction_id", table_name="ledger_entries")
    op.drop_table("ledger_entries")

    op.drop_index("ix_payout_requests_settlement_transaction_id", table_name="payout_requests")
    op.drop_index("ix_payout_requests_hold_transaction_id", table_name="payout_requests")
    op.drop_index("ix_payout_requests_account_id", table_name="payout_requests")
    op.drop_index("ix_payout_requests_user_id", table_name="payout_requests")
    op.drop_table("payout_requests")

    op.drop_index("ix_payment_events_ledger_transaction_id", table_name="payment_events")
    op.drop_index("ix_payment_events_provider_event_id", table_name="payment_events")
    op.drop_index("ix_payment_events_provider_reference", table_name="payment_events")
    op.drop_index("ix_payment_events_user_id", table_name="payment_events")
    op.drop_table("payment_events")

    op.drop_index("ix_ledger_accounts_owner_user_id", table_name="ledger_accounts")
    op.drop_index("ix_ledger_accounts_code", table_name="ledger_accounts")
    op.drop_table("ledger_accounts")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
