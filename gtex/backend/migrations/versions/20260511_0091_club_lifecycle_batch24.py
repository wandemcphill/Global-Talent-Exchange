"""Add Batch 24 club lifecycle and squad registration tables.

Revision ID: 20260511_0091_club_lifecycle_batch24
Revises: 20260511_0090_launch_control_batch34
Create Date: 2026-05-11 10:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260511_0091_club_lifecycle_batch24"
down_revision = "20260511_0090_launch_control_batch34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_lifecycle_states",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("previous_state", sa.String(length=32), nullable=True),
        sa.Column("readiness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("advanced_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["advanced_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", name="uq_club_lifecycle_states_club_id"),
    )
    op.create_index("ix_club_lifecycle_states_club_id", "club_lifecycle_states", ["club_id"])

    op.create_table(
        "club_readiness_statuses",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("readiness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checklist_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("blockers_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("recommended_state", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("competition_eligible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", name="uq_club_readiness_statuses_club_id"),
    )
    op.create_index("ix_club_readiness_statuses_club_id", "club_readiness_statuses", ["club_id"])

    op.create_table(
        "club_squad_registrations",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("season_label", sa.String(length=32), nullable=False, server_default="launch"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("player_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("position_summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["locked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "season_label", name="uq_club_squad_registrations_club_season"),
    )
    op.create_index("ix_club_squad_registrations_club_id", "club_squad_registrations", ["club_id"])

    op.create_table(
        "club_eligibility_flags",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("flag_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="clear"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "flag_key", name="uq_club_eligibility_flags_club_key"),
    )
    op.create_index("ix_club_eligibility_flags_club_id", "club_eligibility_flags", ["club_id"])

    op.create_table(
        "club_operating_statuses",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("operating_state", sa.String(length=32), nullable=False, server_default="setup"),
        sa.Column("dashboard_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", name="uq_club_operating_statuses_club_id"),
    )
    op.create_index("ix_club_operating_statuses_club_id", "club_operating_statuses", ["club_id"])

    op.create_table(
        "club_registration_slots",
        sa.Column("registration_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("position_group", sa.String(length=32), nullable=False),
        sa.Column("slot_status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["registration_id"], ["club_squad_registrations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_id", "player_id", name="uq_club_registration_slots_registration_player"),
    )
    op.create_index("ix_club_registration_slots_club_id", "club_registration_slots", ["club_id"])
    op.create_index("ix_club_registration_slots_player_id", "club_registration_slots", ["player_id"])
    op.create_index("ix_club_registration_slots_registration_id", "club_registration_slots", ["registration_id"])

    op.create_table(
        "club_lifecycle_audit_events",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("previous_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("next_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_club_lifecycle_audit_events_actor_user_id", "club_lifecycle_audit_events", ["actor_user_id"])
    op.create_index("ix_club_lifecycle_audit_events_club_id", "club_lifecycle_audit_events", ["club_id"])


def downgrade() -> None:
    op.drop_index("ix_club_lifecycle_audit_events_club_id", table_name="club_lifecycle_audit_events")
    op.drop_index("ix_club_lifecycle_audit_events_actor_user_id", table_name="club_lifecycle_audit_events")
    op.drop_table("club_lifecycle_audit_events")
    op.drop_index("ix_club_registration_slots_registration_id", table_name="club_registration_slots")
    op.drop_index("ix_club_registration_slots_player_id", table_name="club_registration_slots")
    op.drop_index("ix_club_registration_slots_club_id", table_name="club_registration_slots")
    op.drop_table("club_registration_slots")
    op.drop_index("ix_club_operating_statuses_club_id", table_name="club_operating_statuses")
    op.drop_table("club_operating_statuses")
    op.drop_index("ix_club_eligibility_flags_club_id", table_name="club_eligibility_flags")
    op.drop_table("club_eligibility_flags")
    op.drop_index("ix_club_squad_registrations_club_id", table_name="club_squad_registrations")
    op.drop_table("club_squad_registrations")
    op.drop_index("ix_club_readiness_statuses_club_id", table_name="club_readiness_statuses")
    op.drop_table("club_readiness_statuses")
    op.drop_index("ix_club_lifecycle_states_club_id", table_name="club_lifecycle_states")
    op.drop_table("club_lifecycle_states")
