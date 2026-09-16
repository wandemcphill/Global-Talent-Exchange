"""Add legendary player registry tables and player linkage.

Revision ID: 20260915_0124_legendary_player_registry
Revises: 20260914_0123_jackpot_database_guards
Create Date: 2026-09-15 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260915_0124_legendary_player_registry"
down_revision = "20260914_0123_jackpot_database_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legendary_player_profiles",
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("primary_position", sa.String(length=40), nullable=False),
        sa.Column("secondary_positions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("preferred_foot", sa.String(length=16), nullable=False, server_default="right"),
        sa.Column("historical_height_cm", sa.Integer(), nullable=False),
        sa.Column("gtex_height_cm", sa.Integer(), nullable=False),
        sa.Column("signature_traits_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("signature_role", sa.String(length=80), nullable=True),
        sa.Column("technical_profile_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("physical_profile_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("mental_profile_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("era", sa.String(length=64), nullable=False),
        sa.Column("legendary_classification", sa.String(length=40), nullable=False, server_default="icon"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_searchable", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_tradable", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_rentable", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_national_team_eligible", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("portrait_metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_legendary_player_profiles_slug"),
    )
    op.create_index("ix_legendary_player_profiles_slug", "legendary_player_profiles", ["slug"], unique=False)
    op.create_index(
        "ix_legendary_player_profiles_country_code", "legendary_player_profiles", ["country_code"], unique=False
    )
    op.create_index(
        "ix_legendary_player_profiles_primary_position", "legendary_player_profiles", ["primary_position"], unique=False
    )
    op.create_index(
        "ix_legendary_player_profiles_legendary_classification",
        "legendary_player_profiles",
        ["legendary_classification"],
        unique=False,
    )
    op.create_index("ix_legendary_player_profiles_era", "legendary_player_profiles", ["era"], unique=False)
    op.create_index(
        "ix_legendary_player_profiles_status", "legendary_player_profiles", ["is_active", "is_searchable"], unique=False
    )

    with op.batch_alter_table("ingestion_players") as batch_op:
        batch_op.add_column(sa.Column("legendary_profile_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_ingestion_players_legendary_profile_id",
            "legendary_player_profiles",
            ["legendary_profile_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_ingestion_players_legendary_profile_id", ["legendary_profile_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("ingestion_players") as batch_op:
        batch_op.drop_index("ix_ingestion_players_legendary_profile_id")
        batch_op.drop_constraint("fk_ingestion_players_legendary_profile_id", type_="foreignkey")
        batch_op.drop_column("legendary_profile_id")

    op.drop_index("ix_legendary_player_profiles_status", table_name="legendary_player_profiles")
    op.drop_index("ix_legendary_player_profiles_era", table_name="legendary_player_profiles")
    op.drop_index("ix_legendary_player_profiles_legendary_classification", table_name="legendary_player_profiles")
    op.drop_index("ix_legendary_player_profiles_primary_position", table_name="legendary_player_profiles")
    op.drop_index("ix_legendary_player_profiles_country_code", table_name="legendary_player_profiles")
    op.drop_index("ix_legendary_player_profiles_slug", table_name="legendary_player_profiles")
    op.drop_table("legendary_player_profiles")
