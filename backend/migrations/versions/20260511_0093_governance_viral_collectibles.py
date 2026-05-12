"""Add federation, viral, and card collectible completion tables.

Revision ID: 20260511_0093_governance_viral_collectibles
Revises: 20260511_0092_club_growth_batches_25_27
Create Date: 2026-05-11 13:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260511_0093_governance_viral_collectibles"
down_revision = "20260511_0092_club_growth_batches_25_27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_card_packs",
        sa.Column("pack_key", sa.String(length=96), nullable=False),
        sa.Column("title", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_credits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("cards_per_pack", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("drop_odds_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pack_key", name="uq_player_card_packs_key"),
    )
    op.create_index("ix_player_card_packs_active", "player_card_packs", ["is_active"])
    op.create_index("ix_player_card_packs_pack_key", "player_card_packs", ["pack_key"])

    op.create_table(
        "player_card_pack_openings",
        sa.Column("pack_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="opened"),
        sa.Column("price_credits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("opened_cards_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pack_id"], ["player_card_packs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_card_pack_openings_pack_id", "player_card_pack_openings", ["pack_id"])
    op.create_index("ix_player_card_pack_openings_user_id", "player_card_pack_openings", ["user_id"])

    op.create_table(
        "player_card_upgrade_events",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("source_player_card_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("target_player_card_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("burn_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["target_player_card_id"], ["player_cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_card_upgrade_events_user_id", "player_card_upgrade_events", ["user_id"])

    op.create_table(
        "player_card_burn_events",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reason", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_card_burn_events_player_card_id", "player_card_burn_events", ["player_card_id"])
    op.create_index("ix_player_card_burn_events_user_id", "player_card_burn_events", ["user_id"])

    op.create_table(
        "clip_moderation_events",
        sa.Column("clip_id", sa.String(length=160), nullable=False),
        sa.Column("reporter_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False, server_default="reported"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clip_moderation_events_clip_id", "clip_moderation_events", ["clip_id"])
    op.create_index("ix_clip_moderation_events_status", "clip_moderation_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_clip_moderation_events_status", table_name="clip_moderation_events")
    op.drop_index("ix_clip_moderation_events_clip_id", table_name="clip_moderation_events")
    op.drop_table("clip_moderation_events")

    op.drop_index("ix_player_card_burn_events_user_id", table_name="player_card_burn_events")
    op.drop_index("ix_player_card_burn_events_player_card_id", table_name="player_card_burn_events")
    op.drop_table("player_card_burn_events")

    op.drop_index("ix_player_card_upgrade_events_user_id", table_name="player_card_upgrade_events")
    op.drop_table("player_card_upgrade_events")

    op.drop_index("ix_player_card_pack_openings_user_id", table_name="player_card_pack_openings")
    op.drop_index("ix_player_card_pack_openings_pack_id", table_name="player_card_pack_openings")
    op.drop_table("player_card_pack_openings")

    op.drop_index("ix_player_card_packs_pack_key", table_name="player_card_packs")
    op.drop_index("ix_player_card_packs_active", table_name="player_card_packs")
    op.drop_table("player_card_packs")
