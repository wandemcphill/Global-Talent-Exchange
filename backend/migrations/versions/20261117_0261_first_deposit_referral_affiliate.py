"""Add first-deposit referral partners, campaigns, payouts, and reward facts.

Revision ID: 20261117_0261_first_deposit_referral_affiliate
Revises: 20261117_0261_admin_referral_partners
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261117_0261_first_deposit_referral_affiliate"
down_revision = "20261117_0261_admin_referral_partners"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("referral_partners") as batch:
        batch.add_column(sa.Column("status", sa.String(length=24), server_default="active", nullable=False))
        batch.add_column(sa.Column("owner_user_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("creator_profile_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("contractual_terms", sa.Text(), nullable=True))
        batch.add_column(sa.Column("payout_destination_label", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("payout_destination_fingerprint", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("payout_currency", sa.String(length=12), server_default="NGN", nullable=False))
    op.create_index("ix_referral_partners_owner_user_id", "referral_partners", ["owner_user_id"])
    op.create_index("ix_referral_partners_creator_profile_id", "referral_partners", ["creator_profile_id"])
    op.create_index(
        "ix_referral_partners_payout_destination_fingerprint", "referral_partners", ["payout_destination_fingerprint"]
    )

    op.create_table(
        "referral_programme_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("settings_key", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("user_bonus_bps", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("referrer_commission_bps", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("hold_days", sa.Integer(), server_default="7", nullable=False),
        sa.Column("payout_weekday", sa.Integer(), server_default="0", nullable=False),
        sa.Column("min_payout_thresholds_json", sa.JSON(), nullable=False),
        sa.Column("eligible_account_types_json", sa.JSON(), nullable=False),
        sa.Column("qualifying_deposit_types_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settings_key", name="uq_referral_programme_settings_settings_key"),
    )

    op.create_table(
        "referral_clicks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("share_code_id", sa.String(length=36), nullable=True),
        sa.Column("campaign_id", sa.String(length=36), nullable=True),
        sa.Column("succeeded", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=64), nullable=True),
        sa.Column("failure_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referral_clicks_share_code_id", "referral_clicks", ["share_code_id"])
    op.create_index("ix_referral_clicks_campaign_id", "referral_clicks", ["campaign_id"])
    op.create_index("ix_referral_clicks_ip_hash", "referral_clicks", ["ip_hash"])

    op.create_table(
        "referral_payout_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("beneficiary_user_id", sa.String(length=36), nullable=True),
        sa.Column("beneficiary_partner_id", sa.String(length=36), nullable=True),
        sa.Column("currency_code", sa.String(length=12), nullable=False),
        sa.Column("total_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="draft", nullable=False),
        sa.Column("payout_method", sa.String(length=32), nullable=False),
        sa.Column("external_reference", sa.String(length=128), nullable=True),
        sa.Column("destination_label", sa.String(length=255), nullable=True),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("confirmed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_referral_payout_batches_idempotency_key"),
    )
    op.create_index(
        "ix_referral_payout_batches_beneficiary_user_id", "referral_payout_batches", ["beneficiary_user_id"]
    )
    op.create_index(
        "ix_referral_payout_batches_beneficiary_partner_id", "referral_payout_batches", ["beneficiary_partner_id"]
    )

    op.create_table(
        "referral_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("partner_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("share_code_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_registrations", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("public_link", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["partner_id"], ["referral_partners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["share_code_id"], ["share_codes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_code_id", name="uq_referral_campaigns_share_code_id"),
    )
    op.create_index("ix_referral_campaigns_partner_id", "referral_campaigns", ["partner_id"])
    op.create_index("ix_referral_campaigns_share_code_id", "referral_campaigns", ["share_code_id"])

    op.create_table(
        "referral_payout_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("reward_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["referral_payout_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reward_id"], ["referral_rewards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reward_id", name="uq_referral_payout_items_reward_id"),
    )
    op.create_index("ix_referral_payout_items_batch_id", "referral_payout_items", ["batch_id"])

    op.create_table(
        "referral_recovery_cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reward_id", sa.String(length=36), nullable=False),
        sa.Column("referred_user_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="open", nullable=False),
        sa.Column("deposit_kind", sa.String(length=32), nullable=True),
        sa.Column("deposit_id", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.ForeignKeyConstraint(["reward_id"], ["referral_rewards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reward_id", "kind", name="uq_referral_recovery_reward_kind"),
    )
    op.create_index("ix_referral_recovery_cases_reward_id", "referral_recovery_cases", ["reward_id"])
    op.create_index("ix_referral_recovery_cases_referred_user_id", "referral_recovery_cases", ["referred_user_id"])

    op.create_table(
        "referral_admin_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=48), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referral_admin_audits_actor_user_id", "referral_admin_audits", ["actor_user_id"])
    op.create_index("ix_referral_admin_audits_action", "referral_admin_audits", ["action"])
    op.create_index("ix_referral_admin_audits_resource_id", "referral_admin_audits", ["resource_id"])

    _add_columns(
        "share_codes",
        [
            sa.Column("referral_partner_id", sa.String(length=36), nullable=True),
            sa.Column("referral_campaign_id", sa.String(length=36), nullable=True),
        ],
    )
    op.create_index("ix_share_codes_referral_partner_id", "share_codes", ["referral_partner_id"])
    op.create_index("ix_share_codes_referral_campaign_id", "share_codes", ["referral_campaign_id"])
    _add_columns(
        "referral_attributions",
        [
            sa.Column("referral_partner_id", sa.String(length=36), nullable=True),
            sa.Column("referral_campaign_id", sa.String(length=36), nullable=True),
            sa.Column("account_type_snapshot", sa.String(length=32), nullable=True),
            sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        ],
    )
    op.create_index("ix_referral_attributions_referral_partner_id", "referral_attributions", ["referral_partner_id"])
    op.create_index("ix_referral_attributions_referral_campaign_id", "referral_attributions", ["referral_campaign_id"])
    _add_columns(
        "referral_rewards",
        [
            sa.Column("referral_partner_id", sa.String(length=36), nullable=True),
            sa.Column("qualifying_amount", sa.Numeric(20, 4), nullable=True),
            sa.Column("qualifying_currency", sa.String(length=12), nullable=True),
            sa.Column("applied_rate_bps", sa.Integer(), nullable=True),
            sa.Column("policy_version", sa.Integer(), nullable=True),
            sa.Column("deposit_kind", sa.String(length=32), nullable=True),
            sa.Column("deposit_id", sa.String(length=64), nullable=True),
            sa.Column("payout_batch_id", sa.String(length=36), nullable=True),
        ],
    )
    op.create_index("ix_referral_rewards_referral_partner_id", "referral_rewards", ["referral_partner_id"])
    op.create_index("ix_referral_rewards_deposit_kind", "referral_rewards", ["deposit_kind"])
    op.create_index("ix_referral_rewards_deposit_id", "referral_rewards", ["deposit_id"])
    op.create_index("ix_referral_rewards_payout_batch_id", "referral_rewards", ["payout_batch_id"])


def downgrade() -> None:
    for index, table in (
        ("ix_referral_rewards_payout_batch_id", "referral_rewards"),
        ("ix_referral_rewards_deposit_id", "referral_rewards"),
        ("ix_referral_rewards_deposit_kind", "referral_rewards"),
        ("ix_referral_rewards_referral_partner_id", "referral_rewards"),
        ("ix_referral_attributions_referral_campaign_id", "referral_attributions"),
        ("ix_referral_attributions_referral_partner_id", "referral_attributions"),
        ("ix_share_codes_referral_campaign_id", "share_codes"),
        ("ix_share_codes_referral_partner_id", "share_codes"),
    ):
        op.drop_index(index, table_name=table)
    _drop_columns(
        "referral_rewards",
        [
            "payout_batch_id",
            "deposit_id",
            "deposit_kind",
            "policy_version",
            "applied_rate_bps",
            "qualifying_currency",
            "qualifying_amount",
            "referral_partner_id",
        ],
    )
    _drop_columns(
        "referral_attributions",
        ["locked_at", "account_type_snapshot", "referral_campaign_id", "referral_partner_id"],
    )
    _drop_columns("share_codes", ["referral_campaign_id", "referral_partner_id"])
    op.drop_index("ix_referral_admin_audits_resource_id", table_name="referral_admin_audits")
    op.drop_index("ix_referral_admin_audits_action", table_name="referral_admin_audits")
    op.drop_index("ix_referral_admin_audits_actor_user_id", table_name="referral_admin_audits")
    op.drop_table("referral_admin_audits")
    op.drop_index("ix_referral_recovery_cases_referred_user_id", table_name="referral_recovery_cases")
    op.drop_index("ix_referral_recovery_cases_reward_id", table_name="referral_recovery_cases")
    op.drop_table("referral_recovery_cases")
    op.drop_index("ix_referral_payout_items_batch_id", table_name="referral_payout_items")
    op.drop_table("referral_payout_items")
    op.drop_index("ix_referral_campaigns_share_code_id", table_name="referral_campaigns")
    op.drop_index("ix_referral_campaigns_partner_id", table_name="referral_campaigns")
    op.drop_table("referral_campaigns")
    op.drop_index("ix_referral_payout_batches_beneficiary_partner_id", table_name="referral_payout_batches")
    op.drop_index("ix_referral_payout_batches_beneficiary_user_id", table_name="referral_payout_batches")
    op.drop_table("referral_payout_batches")
    op.drop_index("ix_referral_clicks_ip_hash", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_campaign_id", table_name="referral_clicks")
    op.drop_index("ix_referral_clicks_share_code_id", table_name="referral_clicks")
    op.drop_table("referral_clicks")
    op.drop_table("referral_programme_settings")
    op.drop_index("ix_referral_partners_payout_destination_fingerprint", table_name="referral_partners")
    op.drop_index("ix_referral_partners_creator_profile_id", table_name="referral_partners")
    op.drop_index("ix_referral_partners_owner_user_id", table_name="referral_partners")
    with op.batch_alter_table("referral_partners") as batch:
        batch.drop_column("payout_currency")
        batch.drop_column("payout_destination_fingerprint")
        batch.drop_column("payout_destination_label")
        batch.drop_column("contractual_terms")
        batch.drop_column("creator_profile_id")
        batch.drop_column("owner_user_id")
        batch.drop_column("status")


def _add_columns(table: str, columns: list[sa.Column]) -> None:
    with op.batch_alter_table(table) as batch:
        for column in columns:
            batch.add_column(column)


def _drop_columns(table: str, names: list[str]) -> None:
    with op.batch_alter_table(table) as batch:
        for name in names:
            batch.drop_column(name)
