"""Add player face and commentary event persistence.

Revision ID: 20260327_0039_face_and_commentary_systems
Revises: 20260327_0038_merge_feature_heads
Create Date: 2026-03-27 16:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0039_face_and_commentary_systems"
down_revision = "20260327_0038_merge_feature_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_faces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("avatar_seed", sa.String(length=128), nullable=False),
        sa.Column("facial_features", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("hairstyle", sa.String(length=64), nullable=True),
        sa.Column("skin_tone", sa.String(length=32), nullable=True),
        sa.Column("accessories", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_player_faces_player_id"),
    )
    op.create_index("ix_player_faces_player_id", "player_faces", ["player_id"], unique=False)
    op.create_index("ix_player_faces_avatar_seed", "player_faces", ["avatar_seed"], unique=False)
    op.create_index("ix_player_faces_generated_at", "player_faces", ["generated_at"], unique=False)

    op.create_table(
        "commentary_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=120), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("generated_line", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commentary_events_match_id", "commentary_events", ["match_id"], unique=False)
    op.create_index("ix_commentary_events_minute", "commentary_events", ["minute"], unique=False)
    op.create_index("ix_commentary_events_match_id_minute", "commentary_events", ["match_id", "minute"], unique=False)
    op.create_index("ix_commentary_events_match_id_event_type", "commentary_events", ["match_id", "event_type"], unique=False)
    op.create_index("ix_commentary_events_created_at", "commentary_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_commentary_events_created_at", table_name="commentary_events")
    op.drop_index("ix_commentary_events_match_id_event_type", table_name="commentary_events")
    op.drop_index("ix_commentary_events_match_id_minute", table_name="commentary_events")
    op.drop_index("ix_commentary_events_minute", table_name="commentary_events")
    op.drop_index("ix_commentary_events_match_id", table_name="commentary_events")
    op.drop_table("commentary_events")

    op.drop_index("ix_player_faces_generated_at", table_name="player_faces")
    op.drop_index("ix_player_faces_avatar_seed", table_name="player_faces")
    op.drop_index("ix_player_faces_player_id", table_name="player_faces")
    op.drop_table("player_faces")
