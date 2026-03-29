"""Add national team competition entries for lifecycle engine.

Revision ID: 20260329_0062_national_team_competition_engine_entries
Revises: 20260329_0061_competition_treasure_chest_progression
Create Date: 2026-03-29 10:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0062_national_team_competition_engine_entries"
down_revision = "20260329_0061_competition_treasure_chest_progression"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "national_team_competition_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("country_name", sa.String(length=120), nullable=False),
        sa.Column("squad_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("qualified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["competition_id"], ["national_team_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "competition_id",
            "user_id",
            name="uq_national_team_competition_entries_competition_user",
        ),
    )
    op.create_index(
        "ix_national_team_competition_entries_competition_id",
        "national_team_competition_entries",
        ["competition_id"],
        unique=False,
    )
    op.create_index(
        "ix_national_team_competition_entries_country_code",
        "national_team_competition_entries",
        ["country_code"],
        unique=False,
    )
    op.create_index(
        "ix_national_team_competition_entries_locked",
        "national_team_competition_entries",
        ["locked"],
        unique=False,
    )
    op.create_index(
        "ix_national_team_competition_entries_status",
        "national_team_competition_entries",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_national_team_competition_entries_qualified",
        "national_team_competition_entries",
        ["qualified"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_national_team_competition_entries_qualified",
        table_name="national_team_competition_entries",
    )
    op.drop_index(
        "ix_national_team_competition_entries_status",
        table_name="national_team_competition_entries",
    )
    op.drop_index(
        "ix_national_team_competition_entries_locked",
        table_name="national_team_competition_entries",
    )
    op.drop_index(
        "ix_national_team_competition_entries_country_code",
        table_name="national_team_competition_entries",
    )
    op.drop_index(
        "ix_national_team_competition_entries_competition_id",
        table_name="national_team_competition_entries",
    )
    op.drop_table("national_team_competition_entries")
