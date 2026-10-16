"""Add club_squad_tier_memberships (first_team / u21 / reserve rostering).

Revision ID: 20260628_0104_club_squad_tier_memberships
Revises: 20260628_0103_player_secondary_positions
Create Date: 2026-06-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260628_0104_club_squad_tier_memberships"
down_revision = "20260628_0103_player_secondary_positions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_squad_tier_memberships",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "club_id",
            sa.String(length=36),
            sa.ForeignKey("club_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            sa.String(length=36),
            sa.ForeignKey("ingestion_players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tier", sa.String(length=16), nullable=False, server_default="reserve"),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("joined_club_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("joined_tier_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("club_id", "player_id", "status", name="uq_squad_tier_club_player_status"),
    )
    op.create_index(
        "ix_squad_tier_club_tier_status",
        "club_squad_tier_memberships",
        ["club_id", "tier", "status"],
    )
    op.create_index(
        "ix_squad_tier_status_evaluated",
        "club_squad_tier_memberships",
        ["status", "last_evaluated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_squad_tier_status_evaluated", table_name="club_squad_tier_memberships")
    op.drop_index("ix_squad_tier_club_tier_status", table_name="club_squad_tier_memberships")
    op.drop_table("club_squad_tier_memberships")
