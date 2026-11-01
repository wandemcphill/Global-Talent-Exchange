"""Add creator profile URL and selfie attachment fields, coin trader verification columns, and identity verification records table.

Revision ID: 20261101_0153_account_types_creator_and_trader_kyc
Revises: 20261101_0152_korapay_paystack_payout_and_order_fields
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261101_0153_account_types_creator_and_trader_kyc"
down_revision = "20261101_0152_korapay_paystack_payout_and_order_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # 1. creator_applications updates
    if "creator_applications" in tables:
        columns = {c["name"] for c in inspector.get_columns("creator_applications")}
        if "profile_url" not in columns:
            op.add_column("creator_applications", sa.Column("profile_url", sa.String(512), nullable=True))
        if "selfie_attachment_id" not in columns:
            op.add_column(
                "creator_applications",
                sa.Column(
                    "selfie_attachment_id",
                    sa.String(36),
                    sa.ForeignKey("attachments.id", ondelete="SET NULL"),
                    nullable=True,
                ),
            )
        if "decision_history_json" not in columns:
            op.add_column(
                "creator_applications",
                sa.Column("decision_history_json", sa.JSON(), nullable=False, server_default="[]"),
            )

    # 2. coin_trader_profiles updates
    if "coin_trader_profiles" in tables:
        columns = {c["name"] for c in inspector.get_columns("coin_trader_profiles")}
        if "verified_at" not in columns:
            op.add_column("coin_trader_profiles", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
        if "verification_provider" not in columns:
            op.add_column("coin_trader_profiles", sa.Column("verification_provider", sa.String(32), nullable=True))
        if "verification_reference" not in columns:
            op.add_column("coin_trader_profiles", sa.Column("verification_reference", sa.String(128), nullable=True))
            op.create_index(
                "ix_coin_trader_profiles_verification_ref",
                "coin_trader_profiles",
                ["verification_reference"],
                unique=False,
            )
        if "suspended_at" not in columns:
            op.add_column("coin_trader_profiles", sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))

    # 3. identity_verification_records table
    if "identity_verification_records" not in tables:
        op.create_table(
            "identity_verification_records",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("trader_profile_id", sa.String(length=36), nullable=True),
            sa.Column("verification_domain", sa.String(length=32), nullable=False, server_default="coin_trader"),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("provider_session_id", sa.String(length=128), nullable=True),
            sa.Column("provider_reference", sa.String(length=128), nullable=True),
            sa.Column("verification_type", sa.String(length=32), nullable=False, server_default="full_kyc"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="initiated"),
            sa.Column("decision", sa.String(length=32), nullable=True),
            sa.Column("rejection_reason", sa.String(length=500), nullable=True),
            sa.Column("checks_summary_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("evidence_fingerprint", sa.String(length=64), nullable=True),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True),
            sa.Column("history_json", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["trader_profile_id"], ["coin_trader_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_identity_verification_records_user_id",
            "identity_verification_records",
            ["user_id"],
            unique=False,
        )
        op.create_index(
            "ix_identity_verification_records_provider_ref",
            "identity_verification_records",
            ["provider", "provider_reference"],
            unique=False,
        )
        op.create_index(
            "ix_identity_verification_records_idempotency",
            "identity_verification_records",
            ["idempotency_key"],
            unique=False,
        )
        op.create_index(
            "ix_identity_verification_records_status",
            "identity_verification_records",
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "identity_verification_records" in tables:
        op.drop_index("ix_identity_verification_records_status", table_name="identity_verification_records")
        op.drop_index("ix_identity_verification_records_idempotency", table_name="identity_verification_records")
        op.drop_index("ix_identity_verification_records_provider_ref", table_name="identity_verification_records")
        op.drop_index("ix_identity_verification_records_user_id", table_name="identity_verification_records")
        op.drop_table("identity_verification_records")

    if "coin_trader_profiles" in tables:
        columns = {c["name"] for c in inspector.get_columns("coin_trader_profiles")}
        indexes = {i["name"] for i in inspector.get_indexes("coin_trader_profiles")}
        if "ix_coin_trader_profiles_verification_ref" in indexes:
            op.drop_index("ix_coin_trader_profiles_verification_ref", table_name="coin_trader_profiles")
        for col in ["suspended_at", "verification_reference", "verification_provider", "verified_at"]:
            if col in columns:
                op.drop_column("coin_trader_profiles", col)

    if "creator_applications" in tables:
        columns = {c["name"] for c in inspector.get_columns("creator_applications")}
        for col in ["decision_history_json", "selfie_attachment_id", "profile_url"]:
            if col in columns:
                op.drop_column("creator_applications", col)
