"""Add GTEX social warfare persistence tables.

Revision ID: 20260329_0073_social_warfare_layer
Revises: 20260329_0072_merge_ticketed_and_legend_heads
Create Date: 2026-03-29 23:58:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0073_social_warfare_layer"
down_revision = "20260329_0072_merge_ticketed_and_legend_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fan_tribes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_id", sa.String(length=80), nullable=False),
        sa.Column("club_name", sa.String(length=160), nullable=True),
        sa.Column("tribe_name", sa.String(length=160), nullable=True),
        sa.Column("members", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rivalry_targets", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("power_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_fan_tribes"),
        sa.UniqueConstraint("club_id", name="uq_fan_tribes_club_id"),
    )
    op.create_index("ix_fan_tribes_club_id", "fan_tribes", ["club_id"], unique=False)
    op.create_index("ix_fan_tribes_power_score", "fan_tribes", ["power_score"], unique=False)

    op.create_table(
        "gtex_match_chat_rooms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("room_key", sa.String(length=128), nullable=False),
        sa.Column("room_title", sa.String(length=180), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("emoji_burst_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("moment_spike_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_match_chat_rooms"),
        sa.UniqueConstraint("match_id", name="uq_gtex_match_chat_rooms_match_id"),
        sa.UniqueConstraint("room_key", name="uq_gtex_match_chat_rooms_room_key"),
    )
    op.create_index("ix_gtex_match_chat_rooms_match_id", "gtex_match_chat_rooms", ["match_id"], unique=False)
    op.create_index(
        "ix_gtex_match_chat_rooms_moment_spike_score",
        "gtex_match_chat_rooms",
        ["moment_spike_score"],
        unique=False,
    )

    op.create_table(
        "gtex_match_chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("fan_profile_id", sa.String(length=36), nullable=True),
        sa.Column("fan_tribe_id", sa.String(length=36), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("emoji", sa.String(length=32), nullable=True),
        sa.Column("intensity", sa.Float(), nullable=False, server_default="1"),
        sa.Column("sentiment", sa.String(length=16), nullable=False, server_default="neutral"),
        sa.Column("spike_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["fan_profile_id"], ["fan_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fan_tribe_id"], ["fan_tribes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["gtex_match_chat_rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_gtex_match_chat_messages"),
    )
    op.create_index("ix_gtex_match_chat_messages_user_id", "gtex_match_chat_messages", ["user_id"], unique=False)
    op.create_index("ix_gtex_match_chat_messages_fan_profile_id", "gtex_match_chat_messages", ["fan_profile_id"], unique=False)
    op.create_index("ix_gtex_match_chat_messages_room_id", "gtex_match_chat_messages", ["room_id"], unique=False)
    op.create_index("ix_gtex_match_chat_messages_match_id", "gtex_match_chat_messages", ["match_id"], unique=False)
    op.create_index(
        "ix_gtex_match_chat_messages_fan_tribe_id",
        "gtex_match_chat_messages",
        ["fan_tribe_id"],
        unique=False,
    )
    op.create_index(
        "ix_gtex_match_chat_messages_sentiment",
        "gtex_match_chat_messages",
        ["sentiment"],
        unique=False,
    )

    op.create_table(
        "narrative_conflicts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=80), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("manager_profile_id", sa.String(length=36), nullable=True),
        sa.Column("conflict_type", sa.String(length=48), nullable=False),
        sa.Column("headline", sa.String(length=220), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("severity", sa.String(length=24), nullable=False, server_default="medium"),
        sa.Column("impact_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("triggers_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("impact_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["manager_profile_id"], ["manager_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_narrative_conflicts"),
        sa.UniqueConstraint("match_id", "conflict_type", name="uq_narrative_conflicts_match_type"),
    )
    op.create_index("ix_narrative_conflicts_match_id", "narrative_conflicts", ["match_id"], unique=False)
    op.create_index("ix_narrative_conflicts_status", "narrative_conflicts", ["status"], unique=False)
    op.create_index("ix_narrative_conflicts_club_id", "narrative_conflicts", ["club_id"], unique=False)
    op.create_index(
        "ix_narrative_conflicts_manager_profile_id",
        "narrative_conflicts",
        ["manager_profile_id"],
        unique=False,
    )

    op.create_table(
        "market_shock_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=80), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("shock_type", sa.String(length=48), nullable=False),
        sa.Column("headline", sa.String(length=220), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("magnitude", sa.Float(), nullable=False, server_default="0"),
        sa.Column("player_price_delta_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fan_sentiment_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("betting_odds_delta_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impact_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_market_shock_events"),
        sa.UniqueConstraint("match_id", "shock_type", name="uq_market_shock_events_match_type"),
    )
    op.create_index("ix_market_shock_events_match_id", "market_shock_events", ["match_id"], unique=False)
    op.create_index("ix_market_shock_events_status", "market_shock_events", ["status"], unique=False)
    op.create_index("ix_market_shock_events_club_id", "market_shock_events", ["club_id"], unique=False)

    op.create_table(
        "mega_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("event_key", sa.String(length=128), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="scheduled"),
        sa.Column("limited_tickets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exclusive_commentary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("global_broadcast", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("hype_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_mega_events"),
        sa.UniqueConstraint("event_key", name="uq_mega_events_event_key"),
    )
    op.create_index("ix_mega_events_match_id", "mega_events", ["match_id"], unique=False)
    op.create_index("ix_mega_events_status", "mega_events", ["status"], unique=False)

    op.create_table(
        "legacy_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("category", sa.String(length=48), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("entity_name", sa.String(length=180), nullable=True),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("season_key", sa.String(length=64), nullable=False, server_default="lifetime"),
        sa.Column("headline", sa.String(length=220), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rank_position", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["match_id"], ["gtex_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_legacy_snapshots"),
        sa.UniqueConstraint("category", "entity_id", name="uq_legacy_snapshots_category_entity"),
    )
    op.create_index("ix_legacy_snapshots_category", "legacy_snapshots", ["category"], unique=False)
    op.create_index("ix_legacy_snapshots_match_id", "legacy_snapshots", ["match_id"], unique=False)
    op.create_index("ix_legacy_snapshots_score", "legacy_snapshots", ["score"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_legacy_snapshots_score", table_name="legacy_snapshots")
    op.drop_index("ix_legacy_snapshots_match_id", table_name="legacy_snapshots")
    op.drop_index("ix_legacy_snapshots_category", table_name="legacy_snapshots")
    op.drop_table("legacy_snapshots")

    op.drop_index("ix_mega_events_status", table_name="mega_events")
    op.drop_index("ix_mega_events_match_id", table_name="mega_events")
    op.drop_table("mega_events")

    op.drop_index("ix_market_shock_events_club_id", table_name="market_shock_events")
    op.drop_index("ix_market_shock_events_status", table_name="market_shock_events")
    op.drop_index("ix_market_shock_events_match_id", table_name="market_shock_events")
    op.drop_table("market_shock_events")

    op.drop_index("ix_narrative_conflicts_manager_profile_id", table_name="narrative_conflicts")
    op.drop_index("ix_narrative_conflicts_club_id", table_name="narrative_conflicts")
    op.drop_index("ix_narrative_conflicts_status", table_name="narrative_conflicts")
    op.drop_index("ix_narrative_conflicts_match_id", table_name="narrative_conflicts")
    op.drop_table("narrative_conflicts")

    op.drop_index("ix_gtex_match_chat_messages_sentiment", table_name="gtex_match_chat_messages")
    op.drop_index("ix_gtex_match_chat_messages_fan_tribe_id", table_name="gtex_match_chat_messages")
    op.drop_index("ix_gtex_match_chat_messages_match_id", table_name="gtex_match_chat_messages")
    op.drop_index("ix_gtex_match_chat_messages_room_id", table_name="gtex_match_chat_messages")
    op.drop_index("ix_gtex_match_chat_messages_fan_profile_id", table_name="gtex_match_chat_messages")
    op.drop_index("ix_gtex_match_chat_messages_user_id", table_name="gtex_match_chat_messages")
    op.drop_table("gtex_match_chat_messages")

    op.drop_index("ix_gtex_match_chat_rooms_moment_spike_score", table_name="gtex_match_chat_rooms")
    op.drop_index("ix_gtex_match_chat_rooms_match_id", table_name="gtex_match_chat_rooms")
    op.drop_table("gtex_match_chat_rooms")

    op.drop_index("ix_fan_tribes_power_score", table_name="fan_tribes")
    op.drop_index("ix_fan_tribes_club_id", table_name="fan_tribes")
    op.drop_table("fan_tribes")
