"""Add match replay event logs and manager marketplace tables.

Revision ID: 20260327_0036_match_replay_and_manager_marketplace
Revises: 20260326_0035_merge_parallel_feature_heads
Create Date: 2026-03-27 02:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0036_match_replay_and_manager_marketplace"
down_revision = "20260326_0035_merge_parallel_feature_heads"
branch_labels = None
depends_on = None


match_event_type = sa.Enum(
    "goal",
    "shot",
    "pass",
    "tackle",
    "foul",
    "card",
    "substitution",
    "formation_change",
    "chance_created",
    name="match_event_type",
    native_enum=False,
)
match_event_team = sa.Enum("home", "away", name="match_event_team", native_enum=False)
manager_control_mode = sa.Enum("human", "real_manager", name="manager_control_mode", native_enum=False)
manager_contract_status = sa.Enum("active", "ended", name="manager_contract_status", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "match_events",
        sa.Column("match_id", sa.String(length=120), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=False),
        sa.Column("event_type", match_event_type, nullable=False),
        sa.Column("team", match_event_team, nullable=False),
        sa.Column("player_id", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_events")),
    )
    op.create_index(op.f("ix_match_events_match_id"), "match_events", ["match_id"], unique=False)
    op.create_index(op.f("ix_match_events_sequence"), "match_events", ["sequence"], unique=False)
    op.create_index(op.f("ix_match_events_event_type"), "match_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_match_events_team"), "match_events", ["team"], unique=False)
    op.create_index(op.f("ix_match_events_player_id"), "match_events", ["player_id"], unique=False)
    op.create_index("ix_match_events_match_id_minute_created", "match_events", ["match_id", "minute", "created_at"], unique=False)
    op.create_index("ix_match_events_match_id_sequence", "match_events", ["match_id", "sequence"], unique=False)

    op.create_table(
        "manager_profiles",
        sa.Column("manager_id", sa.String(length=36), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("preferred_style", sa.String(length=64), server_default="balanced", nullable=False),
        sa.Column("control_mode", manager_control_mode, server_default="human", nullable=False),
        sa.Column("matches_managed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("wins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("losses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reputation_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("hourly_fee", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("current_losing_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], name=op.f("fk_manager_profiles_manager_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manager_profiles")),
        sa.UniqueConstraint("manager_id", name="uq_manager_profiles_manager_id"),
    )
    op.create_index(op.f("ix_manager_profiles_manager_id"), "manager_profiles", ["manager_id"], unique=False)

    op.create_table(
        "manager_contracts",
        sa.Column("manager_id", sa.String(length=36), nullable=False),
        sa.Column("club_user_id", sa.String(length=36), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("agreed_fee", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("status", manager_contract_status, server_default="active", nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_user_id"], ["users.id"], name=op.f("fk_manager_contracts_club_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], name=op.f("fk_manager_contracts_manager_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manager_contracts")),
    )
    op.create_index(op.f("ix_manager_contracts_manager_id"), "manager_contracts", ["manager_id"], unique=False)
    op.create_index(op.f("ix_manager_contracts_club_user_id"), "manager_contracts", ["club_user_id"], unique=False)
    op.create_index(op.f("ix_manager_contracts_status"), "manager_contracts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_manager_contracts_status"), table_name="manager_contracts")
    op.drop_index(op.f("ix_manager_contracts_club_user_id"), table_name="manager_contracts")
    op.drop_index(op.f("ix_manager_contracts_manager_id"), table_name="manager_contracts")
    op.drop_table("manager_contracts")

    op.drop_index(op.f("ix_manager_profiles_manager_id"), table_name="manager_profiles")
    op.drop_table("manager_profiles")

    op.drop_index("ix_match_events_match_id_sequence", table_name="match_events")
    op.drop_index("ix_match_events_match_id_minute_created", table_name="match_events")
    op.drop_index(op.f("ix_match_events_player_id"), table_name="match_events")
    op.drop_index(op.f("ix_match_events_team"), table_name="match_events")
    op.drop_index(op.f("ix_match_events_event_type"), table_name="match_events")
    op.drop_index(op.f("ix_match_events_sequence"), table_name="match_events")
    op.drop_index(op.f("ix_match_events_match_id"), table_name="match_events")
    op.drop_table("match_events")
