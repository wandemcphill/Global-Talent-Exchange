"""Add competition treasure chest progression profiles and history.

Revision ID: 20260329_0061_competition_treasure_chest_progression
Revises: 20260329_0061_merge_parallel_heads
Create Date: 2026-03-29 06:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0061_competition_treasure_chest_progression"
down_revision = "20260329_0061_merge_parallel_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "competition_progress_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("resolved_user_id", sa.String(length=36), nullable=True),
        sa.Column("display_name", sa.String(length=160), nullable=True),
        sa.Column("current_title", sa.String(length=64), nullable=True),
        sa.Column("ranking_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_championships", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_podiums", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_competitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_earnings_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_placement", sa.Integer(), nullable=True),
        sa.Column("badges_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("titles_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["resolved_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_competition_progress_profiles_subject_id",
        "competition_progress_profiles",
        ["subject_id"],
        unique=True,
    )
    op.create_index(
        "ix_competition_progress_profiles_resolved_user_id",
        "competition_progress_profiles",
        ["resolved_user_id"],
        unique=False,
    )

    op.create_table(
        "competition_history_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("participant_id", sa.String(length=36), nullable=True),
        sa.Column("reward_id", sa.String(length=36), nullable=True),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("resolved_user_id", sa.String(length=36), nullable=True),
        sa.Column("competition_name", sa.String(length=160), nullable=False),
        sa.Column("placement", sa.Integer(), nullable=True),
        sa.Column("played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("earnings_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="credit"),
        sa.Column("reward_status", sa.String(length=24), nullable=False, server_default="not_rewarded"),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("badge_code", sa.String(length=64), nullable=True),
        sa.Column("title_awarded", sa.String(length=64), nullable=True),
        sa.Column("ranking_points_delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["competition_participants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reward_id"], ["competition_rewards.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "competition_id",
            "subject_id",
            name="uq_competition_history_entries_competition_subject",
        ),
    )
    op.create_index(
        "ix_competition_history_entries_competition_id",
        "competition_history_entries",
        ["competition_id"],
        unique=False,
    )
    op.create_index(
        "ix_competition_history_entries_participant_id",
        "competition_history_entries",
        ["participant_id"],
        unique=False,
    )
    op.create_index(
        "ix_competition_history_entries_reward_id",
        "competition_history_entries",
        ["reward_id"],
        unique=False,
    )
    op.create_index(
        "ix_competition_history_entries_subject_id",
        "competition_history_entries",
        ["subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_competition_history_entries_resolved_user_id",
        "competition_history_entries",
        ["resolved_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_competition_history_entries_ledger_transaction_id",
        "competition_history_entries",
        ["ledger_transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_competition_history_entries_ledger_transaction_id", table_name="competition_history_entries")
    op.drop_index("ix_competition_history_entries_resolved_user_id", table_name="competition_history_entries")
    op.drop_index("ix_competition_history_entries_subject_id", table_name="competition_history_entries")
    op.drop_index("ix_competition_history_entries_reward_id", table_name="competition_history_entries")
    op.drop_index("ix_competition_history_entries_participant_id", table_name="competition_history_entries")
    op.drop_index("ix_competition_history_entries_competition_id", table_name="competition_history_entries")
    op.drop_table("competition_history_entries")

    op.drop_index("ix_competition_progress_profiles_resolved_user_id", table_name="competition_progress_profiles")
    op.drop_index("ix_competition_progress_profiles_subject_id", table_name="competition_progress_profiles")
    op.drop_table("competition_progress_profiles")
