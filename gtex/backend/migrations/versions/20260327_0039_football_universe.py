"""Add football universe broadcast, fan, identity, and media tables.

Revision ID: 20260327_0039_football_universe
Revises: 20260327_0038_merge_feature_heads
Create Date: 2026-03-27 15:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0039_football_universe"
down_revision = "20260327_0038_merge_feature_heads"
branch_labels = None
depends_on = None


fan_sentiment = sa.Enum(
    "happy",
    "neutral",
    "negative",
    "very_negative",
    name="fan_sentiment",
    native_enum=False,
)
club_philosophy = sa.Enum(
    "youth_development",
    "attacking",
    "defensive",
    "possession",
    "counter_attack",
    name="club_philosophy",
    native_enum=False,
)
media_event_type = sa.Enum(
    "headline",
    "interview",
    "controversy",
    "transfer_news",
    name="media_event_type",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "broadcast_sessions",
        sa.Column("match_id", sa.String(length=120), nullable=False),
        sa.Column("commentators", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("overlay_state", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_broadcast_sessions")),
        sa.UniqueConstraint("match_id", name="uq_broadcast_sessions_match_id"),
    )
    op.create_index("ix_broadcast_sessions_match_id", "broadcast_sessions", ["match_id"], unique=False)

    op.create_table(
        "fan_bases",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("fan_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("loyalty_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("expectation_level", sa.String(length=32), nullable=False, server_default="balanced"),
        sa.Column("sentiment", fan_sentiment, nullable=False, server_default="neutral"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fan_bases")),
        sa.UniqueConstraint("club_id", name="uq_fan_bases_club_id"),
    )
    op.create_index("ix_fan_bases_sentiment", "fan_bases", ["sentiment"], unique=False)
    op.create_index("ix_fan_bases_expectation_level", "fan_bases", ["expectation_level"], unique=False)

    op.create_table(
        "club_identity_profiles",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("philosophy", club_philosophy, nullable=False, server_default="possession"),
        sa.Column("culture_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("tactical_consistency", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("brand_strength", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_club_identity_profiles")),
        sa.UniqueConstraint("club_id", name="uq_club_identity_profiles_club_id"),
    )
    op.create_index("ix_club_identity_profiles_philosophy", "club_identity_profiles", ["philosophy"], unique=False)

    op.create_table(
        "media_events",
        sa.Column("type", media_event_type, nullable=False, server_default="headline"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("impact", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("match_id", sa.String(length=120), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_events")),
    )
    op.create_index("ix_media_events_type", "media_events", ["type"], unique=False)
    op.create_index("ix_media_events_match_id", "media_events", ["match_id"], unique=False)
    op.create_index("ix_media_events_club_id", "media_events", ["club_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_media_events_club_id", table_name="media_events")
    op.drop_index("ix_media_events_match_id", table_name="media_events")
    op.drop_index("ix_media_events_type", table_name="media_events")
    op.drop_table("media_events")

    op.drop_index("ix_club_identity_profiles_philosophy", table_name="club_identity_profiles")
    op.drop_table("club_identity_profiles")

    op.drop_index("ix_fan_bases_expectation_level", table_name="fan_bases")
    op.drop_index("ix_fan_bases_sentiment", table_name="fan_bases")
    op.drop_table("fan_bases")

    op.drop_index("ix_broadcast_sessions_match_id", table_name="broadcast_sessions")
    op.drop_table("broadcast_sessions")
