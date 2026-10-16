"""Add platform experience state and national regen seeds.

Revision ID: 20260329_0068_platform_experience_and_national_regen_seed
Revises: 20260329_0067_broadcast_network_watch_sessions
Create Date: 2026-03-29 22:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0068_platform_experience_and_national_regen_seed"
down_revision = "20260329_0067_broadcast_network_watch_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "national_regen_seeds",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("seed_key", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("country_name", sa.String(length=120), nullable=False),
        sa.Column("confederation_code", sa.String(length=16), nullable=True),
        sa.Column("seed_type", sa.String(length=48), nullable=False, server_default="preseeded_national_pool"),
        sa.Column("generation_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("primary_position", sa.String(length=16), nullable=False),
        sa.Column("secondary_positions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("current_rating", sa.Integer(), nullable=False),
        sa.Column("potential_rating", sa.Integer(), nullable=False),
        sa.Column("growth_curve", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("personality_seed_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("rarity_tier", sa.String(length=24), nullable=False, server_default="common"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="available"),
        sa.Column("preseed_batch", sa.String(length=48), nullable=False, server_default="system_start"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_national_regen_seeds"),
        sa.UniqueConstraint("seed_key", name="uq_national_regen_seeds_seed_key"),
    )
    op.create_index("ix_national_regen_seeds_country_code", "national_regen_seeds", ["country_code"], unique=False)
    op.create_index("ix_national_regen_seeds_rarity_tier", "national_regen_seeds", ["rarity_tier"], unique=False)
    op.create_index("ix_national_regen_seeds_seed_type", "national_regen_seeds", ["seed_type"], unique=False)

    op.create_table(
        "platform_experience_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("device_name", sa.String(length=120), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="mobile"),
        sa.Column("current_match_id", sa.String(length=120), nullable=True),
        sa.Column("current_channel_id", sa.String(length=48), nullable=True),
        sa.Column("resume_position_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("commentary_cursor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_watch_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("watch_history_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_platform_experience_states"),
        sa.UniqueConstraint("user_id", "device_id", name="uq_platform_experience_states_user_device"),
    )
    op.create_index("ix_platform_experience_states_user_id", "platform_experience_states", ["user_id"], unique=False)
    op.create_index("ix_platform_experience_states_mode", "platform_experience_states", ["mode"], unique=False)
    op.create_index("ix_platform_experience_states_last_watch_at", "platform_experience_states", ["last_watch_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_platform_experience_states_last_watch_at", table_name="platform_experience_states")
    op.drop_index("ix_platform_experience_states_mode", table_name="platform_experience_states")
    op.drop_index("ix_platform_experience_states_user_id", table_name="platform_experience_states")
    op.drop_table("platform_experience_states")

    op.drop_index("ix_national_regen_seeds_seed_type", table_name="national_regen_seeds")
    op.drop_index("ix_national_regen_seeds_rarity_tier", table_name="national_regen_seeds")
    op.drop_index("ix_national_regen_seeds_country_code", table_name="national_regen_seeds")
    op.drop_table("national_regen_seeds")
