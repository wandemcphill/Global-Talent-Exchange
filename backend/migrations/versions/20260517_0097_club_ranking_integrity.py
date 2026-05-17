"""Add club ranking integrity ledger.

Revision ID: 20260517_0097_club_ranking_integrity
Revises: 20260516_0096_competition_os_wallet_ranking_search
Create Date: 2026-05-17 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260517_0097_club_ranking_integrity"
down_revision = "20260516_0096_competition_os_wallet_ranking_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_ranking_events",
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("event_kind", sa.String(length=32), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("opponent_club_id", sa.String(length=36), nullable=True),
        sa.Column("result", sa.String(length=24), nullable=False, server_default="unknown"),
        sa.Column("base_points", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("opponent_strength_multiplier", sa.Numeric(8, 4), nullable=False, server_default="1"),
        sa.Column("competition_size_multiplier", sa.Numeric(8, 4), nullable=False, server_default="1"),
        sa.Column("competition_tier_multiplier", sa.Numeric(8, 4), nullable=False, server_default="1"),
        sa.Column("stage_multiplier", sa.Numeric(8, 4), nullable=False, server_default="1"),
        sa.Column("anti_farm_multiplier", sa.Numeric(8, 4), nullable=False, server_default="1"),
        sa.Column("placement_bonus", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("raw_points_delta", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("final_points_delta", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("integrity_status", sa.String(length=24), nullable=False, server_default="clean"),
        sa.Column("reason", sa.String(length=255), nullable=False, server_default="ranked_result"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key", name="uq_club_ranking_events_event_key"),
    )
    op.create_index("ix_club_ranking_events_club_created", "club_ranking_events", ["club_id", "created_at"])
    op.create_index("ix_club_ranking_events_competition", "club_ranking_events", ["competition_id"])
    op.create_index("ix_club_ranking_events_event_kind", "club_ranking_events", ["event_kind"])
    op.create_index("ix_club_ranking_events_match", "club_ranking_events", ["match_id"])
    op.create_index("ix_club_ranking_events_opponent_club_id", "club_ranking_events", ["opponent_club_id"])
    op.create_index("ix_club_ranking_events_status", "club_ranking_events", ["integrity_status"])

    op.create_table(
        "competition_integrity_scores",
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("unique_participants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repeated_pair_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forfeit_rate", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("suspicious_owner_links", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Numeric(8, 2), nullable=False, server_default="100"),
        sa.Column("ranking_weight", sa.Numeric(8, 4), nullable=False, server_default="1"),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competition_id", name="uq_competition_integrity_scores_competition"),
    )
    op.create_index(
        "ix_competition_integrity_scores_competition_id", "competition_integrity_scores", ["competition_id"]
    )
    op.create_index("ix_competition_integrity_scores_review", "competition_integrity_scores", ["review_required"])

    op.create_table(
        "club_ranking_abuse_flags",
        sa.Column("flag_key", sa.String(length=180), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flag_key", name="uq_club_ranking_abuse_flags_flag_key"),
    )
    op.create_index("ix_club_ranking_abuse_flags_club_status", "club_ranking_abuse_flags", ["club_id", "status"])
    op.create_index("ix_club_ranking_abuse_flags_competition", "club_ranking_abuse_flags", ["competition_id"])
    op.create_index("ix_club_ranking_abuse_flags_match_id", "club_ranking_abuse_flags", ["match_id"])
    op.create_index("ix_club_ranking_abuse_flags_type", "club_ranking_abuse_flags", ["flag_type"])
    op.create_index("ix_club_ranking_abuse_flags_user_id", "club_ranking_abuse_flags", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_club_ranking_abuse_flags_user_id", table_name="club_ranking_abuse_flags")
    op.drop_index("ix_club_ranking_abuse_flags_type", table_name="club_ranking_abuse_flags")
    op.drop_index("ix_club_ranking_abuse_flags_match_id", table_name="club_ranking_abuse_flags")
    op.drop_index("ix_club_ranking_abuse_flags_competition", table_name="club_ranking_abuse_flags")
    op.drop_index("ix_club_ranking_abuse_flags_club_status", table_name="club_ranking_abuse_flags")
    op.drop_table("club_ranking_abuse_flags")

    op.drop_index("ix_competition_integrity_scores_review", table_name="competition_integrity_scores")
    op.drop_index("ix_competition_integrity_scores_competition_id", table_name="competition_integrity_scores")
    op.drop_table("competition_integrity_scores")

    op.drop_index("ix_club_ranking_events_status", table_name="club_ranking_events")
    op.drop_index("ix_club_ranking_events_opponent_club_id", table_name="club_ranking_events")
    op.drop_index("ix_club_ranking_events_match", table_name="club_ranking_events")
    op.drop_index("ix_club_ranking_events_event_kind", table_name="club_ranking_events")
    op.drop_index("ix_club_ranking_events_competition", table_name="club_ranking_events")
    op.drop_index("ix_club_ranking_events_club_created", table_name="club_ranking_events")
    op.drop_table("club_ranking_events")
