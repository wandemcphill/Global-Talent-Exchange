"""Repair regen tracking schema drift for missing national regen seeds.

Revision ID: 20260330_0076_regen_tracking_schema_repair
Revises: 20260330_0075_streamer_engine_schema_repair
Create Date: 2026-03-30 09:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260330_0076_regen_tracking_schema_repair"
down_revision = "20260330_0075_streamer_engine_schema_repair"
branch_labels = None
depends_on = None


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _create_index_if_missing(
    bind,
    *,
    table_name: str,
    index_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:
    if index_name not in _index_names(bind, table_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("national_regen_seeds"):
        op.create_table(
            "national_regen_seeds",
            sa.Column("seed_key", sa.String(length=96), nullable=False),
            sa.Column("display_name", sa.String(length=160), nullable=False),
            sa.Column("country_code", sa.String(length=8), nullable=False),
            sa.Column("country_name", sa.String(length=120), nullable=False),
            sa.Column("confederation_code", sa.String(length=16), nullable=True),
            sa.Column(
                "seed_type",
                sa.String(length=40),
                nullable=False,
                server_default="preseeded_national_pool",
            ),
            sa.Column("generation_index", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("primary_position", sa.String(length=40), nullable=False),
            sa.Column(
                "secondary_positions_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
            sa.Column("current_rating", sa.Integer(), nullable=False),
            sa.Column("potential_rating", sa.Integer(), nullable=False),
            sa.Column("growth_curve", sa.Float(), nullable=False, server_default="0.5"),
            sa.Column(
                "personality_seed_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
            sa.Column("rarity_tier", sa.String(length=24), nullable=False, server_default="common"),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="available"),
            sa.Column("preseed_batch", sa.String(length=64), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id", name="pk_national_regen_seeds"),
            sa.UniqueConstraint("seed_key", name="uq_national_regen_seeds_seed_key"),
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("national_regen_seeds"):
        _create_index_if_missing(
            bind,
            table_name="national_regen_seeds",
            index_name="ix_national_regen_seeds_country_code",
            columns=["country_code"],
        )
        _create_index_if_missing(
            bind,
            table_name="national_regen_seeds",
            index_name="ix_national_regen_seeds_seed_type",
            columns=["seed_type"],
        )
        _create_index_if_missing(
            bind,
            table_name="national_regen_seeds",
            index_name="ix_national_regen_seeds_rarity_tier",
            columns=["rarity_tier"],
        )
        _create_index_if_missing(
            bind,
            table_name="national_regen_seeds",
            index_name="ix_national_regen_seeds_status",
            columns=["status"],
        )


def downgrade() -> None:
    return None
