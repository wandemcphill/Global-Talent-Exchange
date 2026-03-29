"""Add commentary personalities and club DAO tables.

Revision ID: 20260329_0065_commentary_personalities_and_club_dao
Revises: 20260329_0064_gtex_unified_economy
Create Date: 2026-03-29 13:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0065_commentary_personalities_and_club_dao"
down_revision = "20260329_0064_gtex_unified_economy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commentator_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("style", sa.String(length=24), nullable=False),
        sa.Column("tone_intensity", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("catchphrases", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("bias_rules", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("voice_config", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_commentator_profiles"),
        sa.UniqueConstraint("name", name="uq_commentator_profiles_name"),
    )
    op.create_index("ix_commentator_profiles_name", "commentator_profiles", ["name"], unique=False)
    op.create_index("ix_commentator_profiles_style", "commentator_profiles", ["style"], unique=False)

    op.create_table(
        "commentary_profile_selections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("selection_key", sa.String(length=80), nullable=False, server_default="default"),
        sa.Column("match_id", sa.String(length=80), nullable=True),
        sa.Column("primary_profile_id", sa.String(length=36), nullable=False),
        sa.Column("secondary_profile_id", sa.String(length=36), nullable=True),
        sa.Column("dual_mode", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("voice_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("language", sa.String(length=12), nullable=False, server_default="en"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["primary_profile_id"], ["commentator_profiles.id"], name="fk_commentary_profile_selections_primary_profile_id_commentator_profiles", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["secondary_profile_id"], ["commentator_profiles.id"], name="fk_commentary_profile_selections_secondary_profile_id_commentator_profiles", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_commentary_profile_selections_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_commentary_profile_selections"),
        sa.UniqueConstraint("user_id", "selection_key", name="uq_commentary_profile_selections_user_key"),
    )
    op.create_index("ix_commentary_profile_selections_user_id", "commentary_profile_selections", ["user_id"], unique=False)
    op.create_index("ix_commentary_profile_selections_match_id", "commentary_profile_selections", ["match_id"], unique=False)
    op.create_index("ix_commentary_profile_selections_primary_profile_id", "commentary_profile_selections", ["primary_profile_id"], unique=False)
    op.create_index("ix_commentary_profile_selections_secondary_profile_id", "commentary_profile_selections", ["secondary_profile_id"], unique=False)

    op.create_table(
        "club_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("total_supply", sa.Integer(), nullable=False, server_default="1000000"),
        sa.Column("circulating_supply", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("holder_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price", sa.Numeric(18, 4), nullable=False, server_default="1.0000"),
        sa.Column("governance_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("performance_score", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
        sa.Column("win_rate", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
        sa.Column("fan_demand_score", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
        sa.Column("treasury_balance_snapshot", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], name="fk_club_tokens_club_id_club_profiles", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_tokens"),
        sa.UniqueConstraint("club_id", name="uq_club_tokens_club_id"),
    )
    op.create_index("ix_club_tokens_club_id", "club_tokens", ["club_id"], unique=False)

    op.create_table(
        "club_holdings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("tokens_owned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_price", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("reward_tokens_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], name="fk_club_holdings_club_id_club_profiles", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_club_holdings_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_holdings"),
        sa.UniqueConstraint("user_id", "club_id", name="uq_club_holdings_user_club"),
    )
    op.create_index("ix_club_holdings_user_id", "club_holdings", ["user_id"], unique=False)
    op.create_index("ix_club_holdings_club_id", "club_holdings", ["club_id"], unique=False)

    op.create_table(
        "club_treasuries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("balance_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("lifetime_inflow_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("lifetime_outflow_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("winnings_pool_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("sponsorship_pool_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("entry_fee_pool_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("reserve_ratio_bps", sa.Integer(), nullable=False, server_default="1500"),
        sa.Column("profit_share_bps", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("governance_budget_ratio_bps", sa.Integer(), nullable=False, server_default="2500"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], name="fk_club_treasuries_club_id_club_profiles", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_treasuries"),
        sa.UniqueConstraint("club_id", name="uq_club_treasuries_club_id"),
    )
    op.create_index("ix_club_treasuries_club_id", "club_treasuries", ["club_id"], unique=False)

    op.create_table(
        "club_treasury_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("treasury_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=True),
        sa.Column("reference_key", sa.String(length=160), nullable=False),
        sa.Column("entry_type", sa.String(length=48), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("amount_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("balance_after_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], name="fk_club_treasury_entries_club_id_club_profiles", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_id"], ["governance_proposals.id"], name="fk_club_treasury_entries_proposal_id_governance_proposals", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["treasury_id"], ["club_treasuries.id"], name="fk_club_treasury_entries_treasury_id_club_treasuries", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_treasury_entries"),
        sa.UniqueConstraint("reference_key", name="uq_club_treasury_entries_reference_key"),
    )
    op.create_index("ix_club_treasury_entries_treasury_id", "club_treasury_entries", ["treasury_id"], unique=False)
    op.create_index("ix_club_treasury_entries_club_id", "club_treasury_entries", ["club_id"], unique=False)
    op.create_index("ix_club_treasury_entries_proposal_id", "club_treasury_entries", ["proposal_id"], unique=False)
    op.create_index("ix_club_treasury_entries_reference_key", "club_treasury_entries", ["reference_key"], unique=False)
    op.create_index("ix_club_treasury_entries_entry_type", "club_treasury_entries", ["entry_type"], unique=False)

    op.create_table(
        "club_governance_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("formation", sa.String(length=16), nullable=False, server_default="4-3-3"),
        sa.Column("playstyle", sa.String(length=64), nullable=False, server_default="balanced"),
        sa.Column("budget_rules_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("transfer_policy_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("fan_mandate_summary", sa.Text(), nullable=True),
        sa.Column("active_proposal_id", sa.String(length=36), nullable=True),
        sa.Column("last_executed_proposal_id", sa.String(length=36), nullable=True),
        sa.Column("last_executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["active_proposal_id"], ["governance_proposals.id"], name="fk_club_governance_states_active_proposal_id_governance_proposals", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], name="fk_club_governance_states_club_id_club_profiles", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_executed_proposal_id"], ["governance_proposals.id"], name="fk_club_governance_states_last_executed_proposal_id_governance_proposals", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_governance_states"),
        sa.UniqueConstraint("club_id", name="uq_club_governance_states_club_id"),
    )
    op.create_index("ix_club_governance_states_club_id", "club_governance_states", ["club_id"], unique=False)
    op.create_index("ix_club_governance_states_active_proposal_id", "club_governance_states", ["active_proposal_id"], unique=False)
    op.create_index("ix_club_governance_states_last_executed_proposal_id", "club_governance_states", ["last_executed_proposal_id"], unique=False)

    op.create_table(
        "club_dividend_distributions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("treasury_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("reference_key", sa.String(length=160), nullable=False),
        sa.Column("gross_amount_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("tokens_snapshot", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], name="fk_club_dividend_distributions_club_id_club_profiles", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["treasury_id"], ["club_treasuries.id"], name="fk_club_dividend_distributions_treasury_id_club_treasuries", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_club_dividend_distributions_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_dividend_distributions"),
        sa.UniqueConstraint("reference_key", "user_id", name="uq_club_dividend_distributions_reference_user"),
    )
    op.create_index("ix_club_dividend_distributions_treasury_id", "club_dividend_distributions", ["treasury_id"], unique=False)
    op.create_index("ix_club_dividend_distributions_club_id", "club_dividend_distributions", ["club_id"], unique=False)
    op.create_index("ix_club_dividend_distributions_user_id", "club_dividend_distributions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_club_dividend_distributions_user_id", table_name="club_dividend_distributions")
    op.drop_index("ix_club_dividend_distributions_club_id", table_name="club_dividend_distributions")
    op.drop_index("ix_club_dividend_distributions_treasury_id", table_name="club_dividend_distributions")
    op.drop_table("club_dividend_distributions")

    op.drop_index("ix_club_governance_states_last_executed_proposal_id", table_name="club_governance_states")
    op.drop_index("ix_club_governance_states_active_proposal_id", table_name="club_governance_states")
    op.drop_index("ix_club_governance_states_club_id", table_name="club_governance_states")
    op.drop_table("club_governance_states")

    op.drop_index("ix_club_treasury_entries_entry_type", table_name="club_treasury_entries")
    op.drop_index("ix_club_treasury_entries_reference_key", table_name="club_treasury_entries")
    op.drop_index("ix_club_treasury_entries_proposal_id", table_name="club_treasury_entries")
    op.drop_index("ix_club_treasury_entries_club_id", table_name="club_treasury_entries")
    op.drop_index("ix_club_treasury_entries_treasury_id", table_name="club_treasury_entries")
    op.drop_table("club_treasury_entries")

    op.drop_index("ix_club_treasuries_club_id", table_name="club_treasuries")
    op.drop_table("club_treasuries")

    op.drop_index("ix_club_holdings_club_id", table_name="club_holdings")
    op.drop_index("ix_club_holdings_user_id", table_name="club_holdings")
    op.drop_table("club_holdings")

    op.drop_index("ix_club_tokens_club_id", table_name="club_tokens")
    op.drop_table("club_tokens")

    op.drop_index("ix_commentary_profile_selections_secondary_profile_id", table_name="commentary_profile_selections")
    op.drop_index("ix_commentary_profile_selections_primary_profile_id", table_name="commentary_profile_selections")
    op.drop_index("ix_commentary_profile_selections_match_id", table_name="commentary_profile_selections")
    op.drop_index("ix_commentary_profile_selections_user_id", table_name="commentary_profile_selections")
    op.drop_table("commentary_profile_selections")

    op.drop_index("ix_commentator_profiles_style", table_name="commentator_profiles")
    op.drop_index("ix_commentator_profiles_name", table_name="commentator_profiles")
    op.drop_table("commentator_profiles")
