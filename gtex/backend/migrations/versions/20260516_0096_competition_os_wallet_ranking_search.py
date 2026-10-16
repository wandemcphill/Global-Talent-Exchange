"""Add competition OS wallet, ranking, and search fields.

Revision ID: 20260516_0096_competition_os_wallet_ranking_search
Revises: 20260516_0095_fast_match_fast_cup_manager_academy_hardening
Create Date: 2026-05-16 15:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260516_0096_competition_os_wallet_ranking_search"
down_revision = "20260516_0095_fast_match_fast_cup_manager_academy_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_competitions") as batch_op:
        batch_op.add_column(sa.Column("is_ranked", sa.Boolean(), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("registration_deadline", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("competition_mode", sa.String(length=32), nullable=False, server_default="competition"))
        batch_op.add_column(sa.Column("prize_mode", sa.String(length=32), nullable=False, server_default="entry_funded"))
        batch_op.add_column(sa.Column("payout_mode", sa.String(length=32), nullable=False, server_default="winner_takes_all"))
        batch_op.add_column(sa.Column("host_funded_prize_total_minor", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("host_funding_required_minor", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("host_funding_escrowed_minor", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("host_platform_fee_minor", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("fixed_prizes_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("eligibility_rules_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("ranking_policy_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("featured", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("manual_approval_required", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("online_now", sa.Boolean(), nullable=False, server_default="0"))
        batch_op.create_index("ix_user_competitions_ranked_status", ["is_ranked", "status"])
        batch_op.create_index("ix_user_competitions_mode_status", ["competition_mode", "status"])
        batch_op.create_index("ix_user_competitions_prize_mode", ["prize_mode"])
        batch_op.create_index("ix_user_competitions_registration_deadline", ["registration_deadline"])
        batch_op.create_index("ix_user_competitions_featured_status", ["featured", "status"])

    with op.batch_alter_table("competition_participants") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("entry_fee_currency", sa.String(length=12), nullable=False, server_default="credit"))
        batch_op.add_column(sa.Column("escrow_status", sa.String(length=24), nullable=False, server_default="none"))
        batch_op.add_column(sa.Column("wallet_ledger_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("payout_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_competition_participants_user_id", ["user_id"])
        batch_op.create_index("ix_competition_participants_escrow_status", ["escrow_status"])
        batch_op.create_index("ix_competition_participants_wallet_ledger_id", ["wallet_ledger_id"])

    op.create_table(
        "competition_escrows",
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="credit"),
        sa.Column("escrow_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("ledger_id", sa.String(length=36), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payout_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competition_id", "user_id", "club_id", name="uq_competition_escrows_entry"),
    )
    op.create_index("ix_competition_escrows_competition_id", "competition_escrows", ["competition_id"])
    op.create_index("ix_competition_escrows_user_id", "competition_escrows", ["user_id"])
    op.create_index("ix_competition_escrows_club_id", "competition_escrows", ["club_id"])
    op.create_index("ix_competition_escrows_escrow_status", "competition_escrows", ["escrow_status"])
    op.create_index("ix_competition_escrows_ledger_id", "competition_escrows", ["ledger_id"])
    op.create_index("ix_competition_escrows_payout_id", "competition_escrows", ["payout_id"])

    with op.batch_alter_table("competition_rewards") as batch_op:
        batch_op.add_column(sa.Column("payout_idempotency_key", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("payout_source", sa.String(length=32), nullable=False, server_default="competition_escrow"))
        batch_op.add_column(sa.Column("escrow_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_competition_rewards_payout_idempotency_key", ["payout_idempotency_key"], unique=True)
        batch_op.create_index("ix_competition_rewards_escrow_id", ["escrow_id"])


def downgrade() -> None:
    with op.batch_alter_table("competition_rewards") as batch_op:
        batch_op.drop_index("ix_competition_rewards_escrow_id")
        batch_op.drop_index("ix_competition_rewards_payout_idempotency_key")
        batch_op.drop_column("escrow_id")
        batch_op.drop_column("payout_source")
        batch_op.drop_column("payout_idempotency_key")

    op.drop_index("ix_competition_escrows_payout_id", table_name="competition_escrows")
    op.drop_index("ix_competition_escrows_ledger_id", table_name="competition_escrows")
    op.drop_index("ix_competition_escrows_escrow_status", table_name="competition_escrows")
    op.drop_index("ix_competition_escrows_club_id", table_name="competition_escrows")
    op.drop_index("ix_competition_escrows_user_id", table_name="competition_escrows")
    op.drop_index("ix_competition_escrows_competition_id", table_name="competition_escrows")
    op.drop_table("competition_escrows")

    with op.batch_alter_table("competition_participants") as batch_op:
        batch_op.drop_index("ix_competition_participants_wallet_ledger_id")
        batch_op.drop_index("ix_competition_participants_escrow_status")
        batch_op.drop_index("ix_competition_participants_user_id")
        batch_op.drop_column("payout_id")
        batch_op.drop_column("refunded_at")
        batch_op.drop_column("wallet_ledger_id")
        batch_op.drop_column("escrow_status")
        batch_op.drop_column("entry_fee_currency")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("user_competitions") as batch_op:
        batch_op.drop_index("ix_user_competitions_featured_status")
        batch_op.drop_index("ix_user_competitions_registration_deadline")
        batch_op.drop_index("ix_user_competitions_prize_mode")
        batch_op.drop_index("ix_user_competitions_mode_status")
        batch_op.drop_index("ix_user_competitions_ranked_status")
        batch_op.drop_column("online_now")
        batch_op.drop_column("manual_approval_required")
        batch_op.drop_column("featured")
        batch_op.drop_column("ranking_policy_json")
        batch_op.drop_column("eligibility_rules_json")
        batch_op.drop_column("fixed_prizes_json")
        batch_op.drop_column("host_platform_fee_minor")
        batch_op.drop_column("host_funding_escrowed_minor")
        batch_op.drop_column("host_funding_required_minor")
        batch_op.drop_column("host_funded_prize_total_minor")
        batch_op.drop_column("payout_mode")
        batch_op.drop_column("prize_mode")
        batch_op.drop_column("competition_mode")
        batch_op.drop_column("registration_deadline")
        batch_op.drop_column("is_ranked")
