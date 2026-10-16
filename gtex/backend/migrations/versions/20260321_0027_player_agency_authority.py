"""Add player agency personality and state tables.

Revision ID: 20260321_0027_player_agency_authority
Revises: 20260318_0026_creator_league_financial_governance
Create Date: 2026-03-21 18:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260321_0027_player_agency_authority"
down_revision = "20260318_0026_creator_league_financial_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "player_personality_profiles",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=True),
        sa.Column("source_scope", sa.String(length=24), nullable=False, server_default="regen"),
        sa.Column("ambition", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("loyalty", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("professionalism", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("greed", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("temperament", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("patience", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("adaptability", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("competitiveness", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("ego", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("development_focus", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("hometown_affinity", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("trophy_hunger", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("media_appetite", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("default_career_target_band", sa.String(length=32), nullable=False, server_default="development-first"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_player_personality_profiles_player_id"),
        sa.UniqueConstraint("regen_profile_id", name="uq_player_personality_profiles_regen_profile_id"),
    )
    op.create_index(
        "ix_player_personality_profiles_target_band",
        "player_personality_profiles",
        ["default_career_target_band"],
        unique=False,
    )

    op.create_table(
        "player_agency_states",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=True),
        sa.Column("current_club_id", sa.String(length=36), nullable=True),
        sa.Column("morale", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("happiness", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("transfer_appetite", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("contract_stance", sa.String(length=32), nullable=False, server_default="balanced"),
        sa.Column("wage_satisfaction", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("playing_time_satisfaction", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("development_satisfaction", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("club_project_belief", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("grievance_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("promise_memory_json", sa.JSON(), nullable=False),
        sa.Column("unmet_expectations_json", sa.JSON(), nullable=False),
        sa.Column("recent_offer_cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transfer_request_status", sa.String(length=32), nullable=False, server_default="no_action"),
        sa.Column("preferred_role_band", sa.String(length=32), nullable=False, server_default="rotation"),
        sa.Column("career_stage", sa.String(length=24), nullable=False, server_default="prospect"),
        sa.Column("career_target_band", sa.String(length=32), nullable=False, server_default="development-first"),
        sa.Column("salary_expectation_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("last_major_decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_contract_decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_transfer_decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_transfer_denial_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_transfer_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_player_agency_states_player_id"),
        sa.UniqueConstraint("regen_profile_id", name="uq_player_agency_states_regen_profile_id"),
    )
    op.create_index(
        "ix_player_agency_states_current_club_id",
        "player_agency_states",
        ["current_club_id"],
        unique=False,
    )
    op.create_index(
        "ix_player_agency_states_transfer_request_status",
        "player_agency_states",
        ["transfer_request_status"],
        unique=False,
    )
    op.create_index(
        "ix_player_agency_states_career_stage",
        "player_agency_states",
        ["career_stage"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_player_agency_states_career_stage", table_name="player_agency_states")
    op.drop_index("ix_player_agency_states_transfer_request_status", table_name="player_agency_states")
    op.drop_index("ix_player_agency_states_current_club_id", table_name="player_agency_states")
    op.drop_table("player_agency_states")
    op.drop_index("ix_player_personality_profiles_target_band", table_name="player_personality_profiles")
    op.drop_table("player_personality_profiles")
