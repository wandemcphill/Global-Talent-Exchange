"""Add club_match_plans (owner-chosen formation + starting XI).

Revision ID: 20260628_0105_club_match_plans
Revises: 20260628_0104_club_squad_tier_memberships
Create Date: 2026-06-28 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260628_0105_club_match_plans"
down_revision = "20260628_0104_club_squad_tier_memberships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_match_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "club_id",
            sa.String(length=36),
            sa.ForeignKey("club_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("formation", sa.String(length=16), nullable=False, server_default="4-3-3"),
        sa.Column("starter_player_ids_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("bench_player_ids_json", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "updated_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("club_id", name="uq_club_match_plan_club"),
    )


def downgrade() -> None:
    op.drop_table("club_match_plans")
