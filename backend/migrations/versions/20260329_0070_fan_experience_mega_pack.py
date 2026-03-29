"""Add fan experience tables for GTEX fan, ticket, and reaction flows.

Revision ID: 20260329_0070_fan_experience_mega_pack
Revises: 20260329_0069_merge_platform_and_career_sync_heads
Create Date: 2026-03-29 23:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0070_fan_experience_mega_pack"
down_revision = "20260329_0069_merge_platform_and_career_sync_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fan_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("favorite_club_id", sa.String(length=36), nullable=True),
        sa.Column("favorite_club_name", sa.String(length=160), nullable=True),
        sa.Column("favorite_player_id", sa.String(length=36), nullable=True),
        sa.Column("favorite_player_name", sa.String(length=160), nullable=True),
        sa.Column("rival_club_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("loyalty_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reputation_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fan_tier", sa.String(length=16), nullable=False, server_default="Casual"),
        sa.Column("attendance_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attendance_history_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("badges_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_profiles"),
        sa.UniqueConstraint("user_id", name="uq_fan_profiles_user_id"),
    )
    op.create_index("ix_fan_profiles_fan_tier", "fan_profiles", ["fan_tier"], unique=False)
    op.create_index("ix_fan_profiles_favorite_club_id", "fan_profiles", ["favorite_club_id"], unique=False)
    op.create_index("ix_fan_profiles_user_id", "fan_profiles", ["user_id"], unique=False)

    op.create_table(
        "fan_experience_tickets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("fan_profile_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("event_key", sa.String(length=128), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("ticket_tier", sa.String(length=24), nullable=False),
        sa.Column("access_level", sa.String(length=24), nullable=False, server_default="standard"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="purchased"),
        sa.Column("seat_label", sa.String(length=64), nullable=True),
        sa.Column("price_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("discount_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("priority_stream", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("exclusive_commentary_lines_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("loyalty_bonus", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reputation_bonus", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["fan_profile_id"], ["fan_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_experience_tickets"),
        sa.UniqueConstraint("user_id", "event_key", "ticket_tier", name="uq_fan_experience_tickets_user_event_tier"),
    )
    op.create_index("ix_fan_experience_tickets_event_type", "fan_experience_tickets", ["event_type"], unique=False)
    op.create_index("ix_fan_experience_tickets_event_key", "fan_experience_tickets", ["event_key"], unique=False)
    op.create_index("ix_fan_experience_tickets_match_id", "fan_experience_tickets", ["match_id"], unique=False)
    op.create_index("ix_fan_experience_tickets_status", "fan_experience_tickets", ["status"], unique=False)
    op.create_index("ix_fan_experience_tickets_user_id", "fan_experience_tickets", ["user_id"], unique=False)
    op.create_index("ix_fan_experience_tickets_fan_profile_id", "fan_experience_tickets", ["fan_profile_id"], unique=False)

    op.create_table(
        "fan_reactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("fan_profile_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("event_key", sa.String(length=128), nullable=False),
        sa.Column("channel", sa.String(length=24), nullable=False, server_default="match"),
        sa.Column("reaction_type", sa.String(length=24), nullable=False),
        sa.Column("supported_side", sa.String(length=8), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tier_at_reaction", sa.String(length=16), nullable=False, server_default="Casual"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["fan_profile_id"], ["fan_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_reactions"),
    )
    op.create_index("ix_fan_reactions_match_id", "fan_reactions", ["match_id"], unique=False)
    op.create_index("ix_fan_reactions_event_key", "fan_reactions", ["event_key"], unique=False)
    op.create_index("ix_fan_reactions_fan_profile_id", "fan_reactions", ["fan_profile_id"], unique=False)
    op.create_index("ix_fan_reactions_reaction_type", "fan_reactions", ["reaction_type"], unique=False)
    op.create_index("ix_fan_reactions_user_id", "fan_reactions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_fan_reactions_user_id", table_name="fan_reactions")
    op.drop_index("ix_fan_reactions_reaction_type", table_name="fan_reactions")
    op.drop_index("ix_fan_reactions_fan_profile_id", table_name="fan_reactions")
    op.drop_index("ix_fan_reactions_event_key", table_name="fan_reactions")
    op.drop_index("ix_fan_reactions_match_id", table_name="fan_reactions")
    op.drop_table("fan_reactions")

    op.drop_index("ix_fan_experience_tickets_fan_profile_id", table_name="fan_experience_tickets")
    op.drop_index("ix_fan_experience_tickets_user_id", table_name="fan_experience_tickets")
    op.drop_index("ix_fan_experience_tickets_status", table_name="fan_experience_tickets")
    op.drop_index("ix_fan_experience_tickets_match_id", table_name="fan_experience_tickets")
    op.drop_index("ix_fan_experience_tickets_event_key", table_name="fan_experience_tickets")
    op.drop_index("ix_fan_experience_tickets_event_type", table_name="fan_experience_tickets")
    op.drop_table("fan_experience_tickets")

    op.drop_index("ix_fan_profiles_user_id", table_name="fan_profiles")
    op.drop_index("ix_fan_profiles_favorite_club_id", table_name="fan_profiles")
    op.drop_index("ix_fan_profiles_fan_tier", table_name="fan_profiles")
    op.drop_table("fan_profiles")
