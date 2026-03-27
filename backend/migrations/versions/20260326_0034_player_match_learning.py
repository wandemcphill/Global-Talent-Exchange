"""Add adaptive player match learning tables.

Revision ID: 20260326_0034_player_match_learning
Revises: 20260324_0033_merge_auth_email_and_bulk_import_heads
Create Date: 2026-03-26 22:55:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0034_player_match_learning"
down_revision = "20260324_0033_merge_auth_email_and_bulk_import_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_player_events",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_player_events_user_created_at",
        "user_player_events",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_player_events_player_created_at",
        "user_player_events",
        ["player_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_player_events_event_type_created_at",
        "user_player_events",
        ["event_type", "created_at"],
        unique=False,
    )

    op.create_table(
        "player_features_snapshot",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.String(length=64), nullable=True),
        sa.Column("country", sa.String(length=128), nullable=True),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("dominant_foot", sa.String(length=16), nullable=True),
        sa.Column("is_free_agent", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("current_club_name", sa.String(length=160), nullable=True),
        sa.Column("secondary_positions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("player_id"),
    )

    op.create_table(
        "match_weights",
        sa.Column("factor", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("factor", name="uq_match_weights_factor"),
    )
    op.create_index("ix_match_weights_factor", "match_weights", ["factor"], unique=False)

    match_weights = sa.table(
        "match_weights",
        sa.column("id", sa.String(length=36)),
        sa.column("factor", sa.String(length=64)),
        sa.column("weight", sa.Float()),
        sa.column("metadata_json", sa.JSON()),
    )
    op.bulk_insert(
        match_weights,
        [
            {
                "id": "match-weight-position-history",
                "factor": "history_position_bonus",
                "weight": 0.10,
                "metadata_json": {"source": "migration_seed"},
            },
            {
                "id": "match-weight-country-history",
                "factor": "history_country_bonus",
                "weight": 0.05,
                "metadata_json": {"source": "migration_seed"},
            },
            {
                "id": "match-weight-foot-history",
                "factor": "history_foot_bonus",
                "weight": 0.03,
                "metadata_json": {"source": "migration_seed"},
            },
            {
                "id": "match-weight-free-agent-history",
                "factor": "history_free_agent_bonus",
                "weight": 0.02,
                "metadata_json": {"source": "migration_seed"},
            },
            {
                "id": "match-weight-adaptive-cap",
                "factor": "max_adaptive_bonus",
                "weight": 0.20,
                "metadata_json": {"source": "migration_seed"},
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_match_weights_factor", table_name="match_weights")
    op.drop_table("match_weights")
    op.drop_table("player_features_snapshot")
    op.drop_index("ix_user_player_events_event_type_created_at", table_name="user_player_events")
    op.drop_index("ix_user_player_events_player_created_at", table_name="user_player_events")
    op.drop_index("ix_user_player_events_user_created_at", table_name="user_player_events")
    op.drop_table("user_player_events")
