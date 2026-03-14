"""Add policy document management and country feature policies."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260314_0020"
down_revision = "20260313_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_policy_documents"),
    )
    op.create_index("ix_policy_documents_document_key", "policy_documents", ["document_key"], unique=True)

    op.create_table(
        "policy_document_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("policy_document_id", sa.String(length=36), nullable=False),
        sa.Column("version_label", sa.String(length=32), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["policy_document_id"], ["policy_documents.id"], name="fk_policy_document_versions_policy_document_id_policy_documents", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_policy_document_versions"),
        sa.UniqueConstraint("policy_document_id", "version_label", name="uq_policy_document_versions_document_version"),
    )
    op.create_index("ix_policy_document_versions_policy_document_id", "policy_document_versions", ["policy_document_id"], unique=False)
    op.create_index("ix_policy_document_versions_published_at", "policy_document_versions", ["published_at"], unique=False)

    op.create_table(
        "policy_acceptance_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("policy_document_version_id", sa.String(length=36), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["policy_document_version_id"], ["policy_document_versions.id"], name="fk_policy_acceptance_records_policy_document_version_id_policy_document_versions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_policy_acceptance_records_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_policy_acceptance_records"),
        sa.UniqueConstraint("user_id", "policy_document_version_id", name="uq_policy_acceptance_records_user_version"),
    )
    op.create_index("ix_policy_acceptance_records_user_id", "policy_acceptance_records", ["user_id"], unique=False)
    op.create_index("ix_policy_acceptance_records_policy_document_version_id", "policy_acceptance_records", ["policy_document_version_id"], unique=False)
    op.create_index("ix_policy_acceptance_records_accepted_at", "policy_acceptance_records", ["accepted_at"], unique=False)

    op.create_table(
        "country_feature_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("bucket_type", sa.String(length=32), nullable=False, server_default=sa.text("'default'")),
        sa.Column("deposits_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("market_trading_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("platform_reward_withdrawals_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("user_hosted_gift_withdrawals_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("gtex_competition_gift_withdrawals_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("national_reward_withdrawals_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("one_time_region_change_after_days", sa.Integer(), nullable=False, server_default=sa.text("180")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="pk_country_feature_policies"),
        sa.UniqueConstraint("country_code", "bucket_type", name="uq_country_feature_policies_country_bucket"),
    )
    op.create_index("ix_country_feature_policies_country_code", "country_feature_policies", ["country_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_country_feature_policies_country_code", table_name="country_feature_policies")
    op.drop_table("country_feature_policies")

    op.drop_index("ix_policy_acceptance_records_accepted_at", table_name="policy_acceptance_records")
    op.drop_index("ix_policy_acceptance_records_policy_document_version_id", table_name="policy_acceptance_records")
    op.drop_index("ix_policy_acceptance_records_user_id", table_name="policy_acceptance_records")
    op.drop_table("policy_acceptance_records")

    op.drop_index("ix_policy_document_versions_published_at", table_name="policy_document_versions")
    op.drop_index("ix_policy_document_versions_policy_document_id", table_name="policy_document_versions")
    op.drop_table("policy_document_versions")

    op.drop_index("ix_policy_documents_document_key", table_name="policy_documents")
    op.drop_table("policy_documents")
