"""Add treasury MVP stack tables and user onboarding fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260313_0019"
down_revision = "20260313_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    kyc_status_old = sa.Enum("unverified", "pending", "verified", "rejected", name="kyc_status", native_enum=False)
    kyc_status_transition = sa.Enum(
        "unverified",
        "pending",
        "verified",
        "partial_verified_no_id",
        "fully_verified",
        "rejected",
        name="kyc_status",
        native_enum=False,
    )
    kyc_status_new = sa.Enum(
        "unverified",
        "pending",
        "partial_verified_no_id",
        "fully_verified",
        "rejected",
        name="kyc_status",
        native_enum=False,
    )
    rate_direction = sa.Enum("fiat_per_coin", "coin_per_fiat", name="rate_direction", native_enum=False)
    payment_mode = sa.Enum("manual", "automatic", name="payment_mode", native_enum=False)
    deposit_status = sa.Enum(
        "awaiting_payment",
        "payment_submitted",
        "under_review",
        "confirmed",
        "rejected",
        "expired",
        "disputed",
        name="deposit_status",
        native_enum=False,
    )
    treasury_withdrawal_status = sa.Enum(
        "draft",
        "pending_kyc",
        "pending_review",
        "approved",
        "rejected",
        "processing",
        "paid",
        "disputed",
        "cancelled",
        name="treasury_withdrawal_status",
        native_enum=False,
    )
    dispute_status = sa.Enum(
        "open",
        "awaiting_user",
        "awaiting_admin",
        "resolved",
        "closed",
        name="dispute_status",
        native_enum=False,
    )
    ledger_unit = sa.Enum("coin", "credit", name="ledger_unit", native_enum=False)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("full_name", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("phone_number", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("age_confirmed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_users_phone_number", ["phone_number"], unique=False)
        batch_op.alter_column("kyc_status", existing_type=kyc_status_old, type_=kyc_status_transition)

    op.execute(sa.text("UPDATE users SET kyc_status = 'fully_verified' WHERE kyc_status = 'verified'"))

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("kyc_status", existing_type=kyc_status_transition, type_=kyc_status_new)

    op.create_table(
        "attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_attachments_created_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_attachments"),
    )
    op.create_index("ix_attachments_created_by_user_id", "attachments", ["created_by_user_id"], unique=False)

    op.create_table(
        "treasury_bank_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default=sa.text("'NGN'")),
        sa.Column("bank_name", sa.String(length=120), nullable=False),
        sa.Column("account_number", sa.String(length=32), nullable=False),
        sa.Column("account_name", sa.String(length=120), nullable=False),
        sa.Column("bank_code", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_treasury_bank_accounts"),
    )

    op.create_table(
        "treasury_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("settings_key", sa.String(length=32), nullable=False, server_default=sa.text("'default'")),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default=sa.text("'NGN'")),
        sa.Column("deposit_rate_value", sa.Numeric(20, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("deposit_rate_direction", rate_direction, nullable=False),
        sa.Column("withdrawal_rate_value", sa.Numeric(20, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("withdrawal_rate_direction", rate_direction, nullable=False),
        sa.Column("min_deposit", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("max_deposit", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("min_withdrawal", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("max_withdrawal", sa.Numeric(20, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("deposit_mode", payment_mode, nullable=False, server_default=sa.text("'manual'")),
        sa.Column("withdrawal_mode", payment_mode, nullable=False, server_default=sa.text("'manual'")),
        sa.Column("maintenance_message", sa.String(length=255), nullable=True),
        sa.Column("whatsapp_number", sa.String(length=32), nullable=True),
        sa.Column("active_bank_account_id", sa.String(length=36), nullable=True),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["active_bank_account_id"], ["treasury_bank_accounts.id"], name="fk_treasury_settings_active_bank_account_id_treasury_bank_accounts", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], name="fk_treasury_settings_updated_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_treasury_settings"),
        sa.UniqueConstraint("settings_key", name="uq_treasury_settings_key"),
    )
    op.create_index(
        "ix_treasury_settings_active_bank_account_id",
        "treasury_settings",
        ["active_bank_account_id"],
        unique=False,
    )

    op.create_table(
        "deposit_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("status", deposit_status, nullable=False),
        sa.Column("amount_fiat", sa.Numeric(20, 4), nullable=False),
        sa.Column("amount_coin", sa.Numeric(20, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default=sa.text("'NGN'")),
        sa.Column("rate_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("rate_direction", rate_direction, nullable=False),
        sa.Column("bank_name", sa.String(length=120), nullable=False),
        sa.Column("bank_account_number", sa.String(length=32), nullable=False),
        sa.Column("bank_account_name", sa.String(length=120), nullable=False),
        sa.Column("bank_code", sa.String(length=32), nullable=True),
        sa.Column("bank_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("payer_name", sa.String(length=120), nullable=True),
        sa.Column("sender_bank", sa.String(length=120), nullable=True),
        sa.Column("transfer_reference", sa.String(length=128), nullable=True),
        sa.Column("proof_attachment_id", sa.String(length=36), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_user_id", sa.String(length=36), nullable=True),
        sa.Column("admin_notes", sa.String(length=255), nullable=True),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], name="fk_deposit_requests_admin_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proof_attachment_id"], ["attachments.id"], name="fk_deposit_requests_proof_attachment_id_attachments", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_deposit_requests_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_deposit_requests"),
        sa.UniqueConstraint("reference", name="uq_deposit_requests_reference"),
    )
    op.create_index("ix_deposit_requests_user_id", "deposit_requests", ["user_id"], unique=False)
    op.create_index("ix_deposit_requests_reference", "deposit_requests", ["reference"], unique=False)
    op.create_index("ix_deposit_requests_status", "deposit_requests", ["status"], unique=False)
    op.create_index("ix_deposit_requests_created_at", "deposit_requests", ["created_at"], unique=False)
    op.create_index("ix_deposit_requests_payer_name", "deposit_requests", ["payer_name"], unique=False)
    op.create_index("ix_deposit_requests_sender_bank", "deposit_requests", ["sender_bank"], unique=False)
    op.create_index("ix_deposit_requests_transfer_reference", "deposit_requests", ["transfer_reference"], unique=False)
    op.create_index("ix_deposit_requests_admin_user_id", "deposit_requests", ["admin_user_id"], unique=False)
    op.create_index("ix_deposit_requests_ledger_transaction_id", "deposit_requests", ["ledger_transaction_id"], unique=False)

    op.create_table(
        "user_bank_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default=sa.text("'NGN'")),
        sa.Column("bank_name", sa.String(length=120), nullable=False),
        sa.Column("account_number", sa.String(length=32), nullable=False),
        sa.Column("account_name", sa.String(length=120), nullable=False),
        sa.Column("bank_code", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_bank_accounts_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_user_bank_accounts"),
    )
    op.create_index("ix_user_bank_accounts_user_id", "user_bank_accounts", ["user_id"], unique=False)

    op.create_table(
        "kyc_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("status", kyc_status_new, nullable=False, server_default=sa.text("'unverified'")),
        sa.Column("nin", sa.String(length=32), nullable=True),
        sa.Column("bvn", sa.String(length=32), nullable=True),
        sa.Column("address_line1", sa.String(length=255), nullable=True),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True, server_default=sa.text("'Nigeria'")),
        sa.Column("id_document_attachment_id", sa.String(length=36), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_user_id", sa.String(length=36), nullable=True),
        sa.Column("rejection_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["id_document_attachment_id"], ["attachments.id"], name="fk_kyc_profiles_id_document_attachment_id_attachments", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], name="fk_kyc_profiles_reviewer_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_kyc_profiles_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_kyc_profiles"),
        sa.UniqueConstraint("user_id", name="uq_kyc_profiles_user_id"),
    )
    op.create_index("ix_kyc_profiles_user_id", "kyc_profiles", ["user_id"], unique=False)
    op.create_index("ix_kyc_profiles_status", "kyc_profiles", ["status"], unique=False)
    op.create_index("ix_kyc_profiles_nin", "kyc_profiles", ["nin"], unique=False)
    op.create_index("ix_kyc_profiles_bvn", "kyc_profiles", ["bvn"], unique=False)

    op.create_table(
        "treasury_withdrawal_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("payout_request_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("status", treasury_withdrawal_status, nullable=False, server_default=sa.text("'pending_review'")),
        sa.Column("unit", ledger_unit, nullable=False),
        sa.Column("amount_coin", sa.Numeric(20, 4), nullable=False),
        sa.Column("amount_fiat", sa.Numeric(20, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=8), nullable=False, server_default=sa.text("'NGN'")),
        sa.Column("rate_value", sa.Numeric(20, 6), nullable=False),
        sa.Column("rate_direction", rate_direction, nullable=False),
        sa.Column("bank_name", sa.String(length=120), nullable=False),
        sa.Column("bank_account_number", sa.String(length=32), nullable=False),
        sa.Column("bank_account_name", sa.String(length=120), nullable=False),
        sa.Column("bank_code", sa.String(length=32), nullable=True),
        sa.Column("bank_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("kyc_status_snapshot", sa.String(length=32), nullable=False, server_default=sa.text("'unverified'")),
        sa.Column("kyc_tier_snapshot", sa.String(length=32), nullable=False, server_default=sa.text("'unverified'")),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_user_id", sa.String(length=36), nullable=True),
        sa.Column("admin_notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], name="fk_treasury_withdrawal_requests_admin_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payout_request_id"], ["payout_requests.id"], name="fk_treasury_withdrawal_requests_payout_request_id_payout_requests", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_treasury_withdrawal_requests_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_treasury_withdrawal_requests"),
        sa.UniqueConstraint("reference", name="uq_treasury_withdrawal_reference"),
        sa.UniqueConstraint("payout_request_id", name="uq_treasury_withdrawal_payout_request"),
    )
    op.create_index("ix_treasury_withdrawal_requests_user_id", "treasury_withdrawal_requests", ["user_id"], unique=False)
    op.create_index("ix_treasury_withdrawal_requests_reference", "treasury_withdrawal_requests", ["reference"], unique=False)
    op.create_index("ix_treasury_withdrawal_status", "treasury_withdrawal_requests", ["status"], unique=False)
    op.create_index("ix_treasury_withdrawal_created_at", "treasury_withdrawal_requests", ["created_at"], unique=False)
    op.create_index("ix_treasury_withdrawal_requests_admin_user_id", "treasury_withdrawal_requests", ["admin_user_id"], unique=False)
    op.create_index("ix_treasury_withdrawal_requests_payout_request_id", "treasury_withdrawal_requests", ["payout_request_id"], unique=False)

    op.create_table(
        "treasury_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_email", sa.String(length=320), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_treasury_audit_events"),
    )
    op.create_index("ix_treasury_audit_events_event_type", "treasury_audit_events", ["event_type"], unique=False)
    op.create_index("ix_treasury_audit_events_actor_user_id", "treasury_audit_events", ["actor_user_id"], unique=False)
    op.create_index("ix_treasury_audit_events_resource_type", "treasury_audit_events", ["resource_type"], unique=False)
    op.create_index("ix_treasury_audit_events_resource_id", "treasury_audit_events", ["resource_id"], unique=False)

    op.create_table(
        "disputes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("admin_user_id", sa.String(length=36), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=False),
        sa.Column("status", dispute_status, nullable=False, server_default=sa.text("'open'")),
        sa.Column("subject", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], name="fk_disputes_admin_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_disputes_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_disputes"),
    )
    op.create_index("ix_disputes_status", "disputes", ["status"], unique=False)
    op.create_index("ix_disputes_user_id", "disputes", ["user_id"], unique=False)
    op.create_index("ix_disputes_reference", "disputes", ["reference"], unique=False)
    op.create_index("ix_disputes_resource", "disputes", ["resource_type", "resource_id"], unique=False)
    op.create_index("ix_disputes_created_at", "disputes", ["created_at"], unique=False)

    op.create_table(
        "dispute_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dispute_id", sa.String(length=36), nullable=False),
        sa.Column("sender_user_id", sa.String(length=36), nullable=True),
        sa.Column("sender_role", sa.String(length=32), nullable=False, server_default=sa.text("'user'")),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("attachment_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"], name="fk_dispute_messages_attachment_id_attachments", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dispute_id"], ["disputes.id"], name="fk_dispute_messages_dispute_id_disputes", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], name="fk_dispute_messages_sender_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_dispute_messages"),
    )
    op.create_index("ix_dispute_messages_dispute_id", "dispute_messages", ["dispute_id"], unique=False)
    op.create_index("ix_dispute_messages_created_at", "dispute_messages", ["created_at"], unique=False)

    op.create_table(
        "notification_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("template_key", sa.String(length=64), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("fixture_id", sa.String(length=64), nullable=True),
        sa.Column("competition_id", sa.String(length=64), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_notification_records_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_notification_records"),
    )
    op.create_index("ix_notification_records_user_id", "notification_records", ["user_id"], unique=False)
    op.create_index("ix_notification_records_created_at", "notification_records", ["created_at"], unique=False)
    op.create_index("ix_notification_records_read_at", "notification_records", ["read_at"], unique=False)
    op.create_index("ix_notification_records_topic", "notification_records", ["topic"], unique=False)
    op.create_index("ix_notification_records_resource_type", "notification_records", ["resource_type"], unique=False)
    op.create_index("ix_notification_records_resource_id", "notification_records", ["resource_id"], unique=False)

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_analytics_events_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_analytics_events"),
    )
    op.create_index("ix_analytics_events_name", "analytics_events", ["name"], unique=False)
    op.create_index("ix_analytics_events_user_id", "analytics_events", ["user_id"], unique=False)
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analytics_events_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_user_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_name", table_name="analytics_events")
    op.drop_table("analytics_events")

    op.drop_index("ix_notification_records_resource_id", table_name="notification_records")
    op.drop_index("ix_notification_records_resource_type", table_name="notification_records")
    op.drop_index("ix_notification_records_topic", table_name="notification_records")
    op.drop_index("ix_notification_records_read_at", table_name="notification_records")
    op.drop_index("ix_notification_records_created_at", table_name="notification_records")
    op.drop_index("ix_notification_records_user_id", table_name="notification_records")
    op.drop_table("notification_records")

    op.drop_index("ix_dispute_messages_created_at", table_name="dispute_messages")
    op.drop_index("ix_dispute_messages_dispute_id", table_name="dispute_messages")
    op.drop_table("dispute_messages")

    op.drop_index("ix_disputes_created_at", table_name="disputes")
    op.drop_index("ix_disputes_resource", table_name="disputes")
    op.drop_index("ix_disputes_reference", table_name="disputes")
    op.drop_index("ix_disputes_user_id", table_name="disputes")
    op.drop_index("ix_disputes_status", table_name="disputes")
    op.drop_table("disputes")

    op.drop_index("ix_treasury_audit_events_resource_id", table_name="treasury_audit_events")
    op.drop_index("ix_treasury_audit_events_resource_type", table_name="treasury_audit_events")
    op.drop_index("ix_treasury_audit_events_actor_user_id", table_name="treasury_audit_events")
    op.drop_index("ix_treasury_audit_events_event_type", table_name="treasury_audit_events")
    op.drop_table("treasury_audit_events")

    op.drop_index("ix_treasury_withdrawal_requests_payout_request_id", table_name="treasury_withdrawal_requests")
    op.drop_index("ix_treasury_withdrawal_requests_admin_user_id", table_name="treasury_withdrawal_requests")
    op.drop_index("ix_treasury_withdrawal_created_at", table_name="treasury_withdrawal_requests")
    op.drop_index("ix_treasury_withdrawal_status", table_name="treasury_withdrawal_requests")
    op.drop_index("ix_treasury_withdrawal_requests_reference", table_name="treasury_withdrawal_requests")
    op.drop_index("ix_treasury_withdrawal_requests_user_id", table_name="treasury_withdrawal_requests")
    op.drop_table("treasury_withdrawal_requests")

    op.drop_index("ix_kyc_profiles_bvn", table_name="kyc_profiles")
    op.drop_index("ix_kyc_profiles_nin", table_name="kyc_profiles")
    op.drop_index("ix_kyc_profiles_status", table_name="kyc_profiles")
    op.drop_index("ix_kyc_profiles_user_id", table_name="kyc_profiles")
    op.drop_table("kyc_profiles")

    op.drop_index("ix_user_bank_accounts_user_id", table_name="user_bank_accounts")
    op.drop_table("user_bank_accounts")

    op.drop_index("ix_deposit_requests_ledger_transaction_id", table_name="deposit_requests")
    op.drop_index("ix_deposit_requests_admin_user_id", table_name="deposit_requests")
    op.drop_index("ix_deposit_requests_transfer_reference", table_name="deposit_requests")
    op.drop_index("ix_deposit_requests_sender_bank", table_name="deposit_requests")
    op.drop_index("ix_deposit_requests_payer_name", table_name="deposit_requests")
    op.drop_index("ix_deposit_requests_created_at", table_name="deposit_requests")
    op.drop_index("ix_deposit_requests_status", table_name="deposit_requests")
    op.drop_index("ix_deposit_requests_reference", table_name="deposit_requests")
    op.drop_index("ix_deposit_requests_user_id", table_name="deposit_requests")
    op.drop_table("deposit_requests")

    op.drop_index("ix_treasury_settings_active_bank_account_id", table_name="treasury_settings")
    op.drop_table("treasury_settings")
    op.drop_table("treasury_bank_accounts")

    op.drop_index("ix_attachments_created_by_user_id", table_name="attachments")
    op.drop_table("attachments")

    kyc_status_old = sa.Enum("unverified", "pending", "verified", "rejected", name="kyc_status", native_enum=False)
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("kyc_status", existing_type=sa.Enum(
            "unverified",
            "pending",
            "partial_verified_no_id",
            "fully_verified",
            "rejected",
            name="kyc_status",
            native_enum=False,
        ), type_=kyc_status_old)
        batch_op.drop_index("ix_users_phone_number")
        batch_op.drop_column("age_confirmed_at")
        batch_op.drop_column("phone_number")
        batch_op.drop_column("full_name")
