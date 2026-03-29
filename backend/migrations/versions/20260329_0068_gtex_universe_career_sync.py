"""Add GTEX manager personality, career mode, and real-world sync tables.

Revision ID: 20260329_0068_gtex_universe_career_sync
Revises: 20260329_0067_broadcast_network_watch_sessions
Create Date: 2026-03-29 22:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0068_gtex_universe_career_sync"
down_revision = "20260329_0067_broadcast_network_watch_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("manager_profiles") as batch_op:
        batch_op.alter_column("manager_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.add_column(sa.Column("gtex_ai_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("name", sa.String(length=120), nullable=True))
        batch_op.add_column(
            sa.Column(
                "tactical_style",
                sa.String(length=24),
                nullable=False,
                server_default="balanced",
            )
        )
        batch_op.add_column(sa.Column("risk_tolerance", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("adaptability", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("ego_level", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(sa.Column("youth_preference", sa.Float(), nullable=False, server_default="0.5"))
        batch_op.add_column(
            sa.Column(
                "discipline_style",
                sa.String(length=24),
                nullable=False,
                server_default="balanced",
            )
        )
        batch_op.add_column(
            sa.Column(
                "formation_preferences_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            )
        )
        batch_op.add_column(
            sa.Column(
                "substitution_logic",
                sa.String(length=64),
                nullable=False,
                server_default="balanced_rotation",
            )
        )
        batch_op.add_column(
            sa.Column(
                "tempo_control",
                sa.String(length=24),
                nullable=False,
                server_default="balanced",
            )
        )
        batch_op.create_foreign_key(
            "fk_manager_profiles_gtex_ai_id_gtex_ai_profiles",
            "gtex_ai_profiles",
            ["gtex_ai_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint("uq_manager_profiles_gtex_ai_id", ["gtex_ai_id"])
    op.create_index("ix_manager_profiles_gtex_ai_id", "manager_profiles", ["gtex_ai_id"], unique=False)

    op.create_table(
        "manager_match_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("manager_profile_id", sa.String(length=36), nullable=False),
        sa.Column("opponent_manager_profile_id", sa.String(length=36), nullable=True),
        sa.Column("source_match_id", sa.String(length=36), nullable=False),
        sa.Column("source_match_type", sa.String(length=32), nullable=False, server_default="gtex"),
        sa.Column("team_side", sa.String(length=8), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("intensity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("rivalry_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tactical_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("narrative_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["manager_profile_id"], ["manager_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opponent_manager_profile_id"], ["manager_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_manager_match_history"),
    )
    op.create_index("ix_manager_match_history_manager_profile_id", "manager_match_history", ["manager_profile_id"], unique=False)
    op.create_index(
        "ix_manager_match_history_opponent_manager_profile_id",
        "manager_match_history",
        ["opponent_manager_profile_id"],
        unique=False,
    )
    op.create_index("ix_manager_match_history_source_match_id", "manager_match_history", ["source_match_id"], unique=False)

    op.create_table(
        "manager_vs_manager_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("manager_a_id", sa.String(length=36), nullable=False),
        sa.Column("manager_b_id", sa.String(length=36), nullable=False),
        sa.Column("meetings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manager_a_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manager_b_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rivalry_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("last_match_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("narrative_tag", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["manager_a_id"], ["manager_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_b_id"], ["manager_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_manager_vs_manager_history"),
        sa.UniqueConstraint("manager_a_id", "manager_b_id", name="uq_manager_vs_manager_history_pair"),
    )
    op.create_index("ix_manager_vs_manager_history_manager_a_id", "manager_vs_manager_history", ["manager_a_id"], unique=False)
    op.create_index("ix_manager_vs_manager_history_manager_b_id", "manager_vs_manager_history", ["manager_b_id"], unique=False)

    op.create_table(
        "career_players",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("current_club", sa.String(length=160), nullable=True),
        sa.Column("current_club_id", sa.String(length=36), nullable=True),
        sa.Column("career_stats", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("growth_rate", sa.Float(), nullable=False, server_default="0.08"),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("training_focus", sa.String(length=64), nullable=False, server_default="balanced"),
        sa.Column("current_form", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("marketability_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("prestige_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legacy_summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["current_club_id"], ["ingestion_clubs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_career_players"),
        sa.UniqueConstraint("user_id", name="uq_career_players_user_id"),
        sa.UniqueConstraint("player_id", name="uq_career_players_player_id"),
    )
    op.create_index("ix_career_players_user_id", "career_players", ["user_id"], unique=False)
    op.create_index("ix_career_players_player_id", "career_players", ["player_id"], unique=False)
    op.create_index("ix_career_players_current_club_id", "career_players", ["current_club_id"], unique=False)
    op.create_index("ix_career_players_status", "career_players", ["status"], unique=False)

    op.create_table(
        "career_training_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("career_player_id", sa.String(length=36), nullable=False),
        sa.Column("focus", sa.String(length=64), nullable=False),
        sa.Column("intensity", sa.String(length=16), nullable=False),
        sa.Column("xp_gained", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("form_gain", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("growth_delta", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["career_player_id"], ["career_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_career_training_sessions"),
    )
    op.create_index("ix_career_training_sessions_career_player_id", "career_training_sessions", ["career_player_id"], unique=False)

    op.create_table(
        "career_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("career_player_id", sa.String(length=36), nullable=False),
        sa.Column("decision_type", sa.String(length=24), nullable=False),
        sa.Column("from_value", sa.String(length=160), nullable=True),
        sa.Column("to_value", sa.String(length=160), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("decision_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["career_player_id"], ["career_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_career_decisions"),
    )
    op.create_index("ix_career_decisions_career_player_id", "career_decisions", ["career_player_id"], unique=False)
    op.create_index("ix_career_decisions_decision_type", "career_decisions", ["decision_type"], unique=False)

    op.create_table(
        "career_legacy_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("career_player_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("legacy_role", sa.String(length=32), nullable=False, server_default="hall_of_fame"),
        sa.Column("summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["career_player_id"], ["career_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_career_legacy_records"),
        sa.UniqueConstraint("career_player_id", name="uq_career_legacy_records_career_player_id"),
    )
    op.create_index("ix_career_legacy_records_career_player_id", "career_legacy_records", ["career_player_id"], unique=False)
    op.create_index("ix_career_legacy_records_user_id", "career_legacy_records", ["user_id"], unique=False)
    op.create_index("ix_career_legacy_records_player_id", "career_legacy_records", ["player_id"], unique=False)

    op.create_table(
        "real_world_entity_mappings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("mapping_type", sa.String(length=16), nullable=False),
        sa.Column("real_entity_id", sa.String(length=36), nullable=False),
        sa.Column("real_entity_key", sa.String(length=160), nullable=False),
        sa.Column("gtex_entity_id", sa.String(length=36), nullable=False),
        sa.Column("gtex_entity_type", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("mapping_source", sa.String(length=64), nullable=False, server_default="heuristic"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_real_world_entity_mappings"),
        sa.UniqueConstraint(
            "mapping_type",
            "real_entity_id",
            "gtex_entity_id",
            name="uq_real_world_entity_mappings_triplet",
        ),
    )
    op.create_index("ix_real_world_entity_mappings_mapping_type", "real_world_entity_mappings", ["mapping_type"], unique=False)
    op.create_index("ix_real_world_entity_mappings_real_entity_id", "real_world_entity_mappings", ["real_entity_id"], unique=False)
    op.create_index("ix_real_world_entity_mappings_real_entity_key", "real_world_entity_mappings", ["real_entity_key"], unique=False)
    op.create_index("ix_real_world_entity_mappings_gtex_entity_id", "real_world_entity_mappings", ["gtex_entity_id"], unique=False)

    op.create_table(
        "real_world_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("home_club_id", sa.String(length=36), nullable=True),
        sa.Column("away_club_id", sa.String(length=36), nullable=True),
        sa.Column("external_key", sa.String(length=128), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False, server_default="fixture"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="scheduled"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("mirror_match_id", sa.String(length=36), nullable=True),
        sa.Column("magnitude_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("influence_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("influence_summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["away_club_id"], ["real_world_clubs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["real_world_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_club_id"], ["real_world_clubs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mirror_match_id"], ["gtex_matches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["provider_id"], ["real_data_providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_real_world_events"),
        sa.UniqueConstraint("provider_id", "external_key", name="uq_real_world_events_provider_key"),
    )
    op.create_index("ix_real_world_events_provider_id", "real_world_events", ["provider_id"], unique=False)
    op.create_index("ix_real_world_events_competition_id", "real_world_events", ["competition_id"], unique=False)
    op.create_index("ix_real_world_events_home_club_id", "real_world_events", ["home_club_id"], unique=False)
    op.create_index("ix_real_world_events_away_club_id", "real_world_events", ["away_club_id"], unique=False)
    op.create_index("ix_real_world_events_status", "real_world_events", ["status"], unique=False)
    op.create_index("ix_real_world_events_scheduled_at", "real_world_events", ["scheduled_at"], unique=False)
    op.create_index("ix_real_world_events_mirror_match_id", "real_world_events", ["mirror_match_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_real_world_events_mirror_match_id", table_name="real_world_events")
    op.drop_index("ix_real_world_events_scheduled_at", table_name="real_world_events")
    op.drop_index("ix_real_world_events_status", table_name="real_world_events")
    op.drop_index("ix_real_world_events_away_club_id", table_name="real_world_events")
    op.drop_index("ix_real_world_events_home_club_id", table_name="real_world_events")
    op.drop_index("ix_real_world_events_competition_id", table_name="real_world_events")
    op.drop_index("ix_real_world_events_provider_id", table_name="real_world_events")
    op.drop_table("real_world_events")

    op.drop_index("ix_real_world_entity_mappings_gtex_entity_id", table_name="real_world_entity_mappings")
    op.drop_index("ix_real_world_entity_mappings_real_entity_key", table_name="real_world_entity_mappings")
    op.drop_index("ix_real_world_entity_mappings_real_entity_id", table_name="real_world_entity_mappings")
    op.drop_index("ix_real_world_entity_mappings_mapping_type", table_name="real_world_entity_mappings")
    op.drop_table("real_world_entity_mappings")

    op.drop_index("ix_career_legacy_records_player_id", table_name="career_legacy_records")
    op.drop_index("ix_career_legacy_records_user_id", table_name="career_legacy_records")
    op.drop_index("ix_career_legacy_records_career_player_id", table_name="career_legacy_records")
    op.drop_table("career_legacy_records")

    op.drop_index("ix_career_decisions_decision_type", table_name="career_decisions")
    op.drop_index("ix_career_decisions_career_player_id", table_name="career_decisions")
    op.drop_table("career_decisions")

    op.drop_index("ix_career_training_sessions_career_player_id", table_name="career_training_sessions")
    op.drop_table("career_training_sessions")

    op.drop_index("ix_career_players_status", table_name="career_players")
    op.drop_index("ix_career_players_current_club_id", table_name="career_players")
    op.drop_index("ix_career_players_player_id", table_name="career_players")
    op.drop_index("ix_career_players_user_id", table_name="career_players")
    op.drop_table("career_players")

    op.drop_index("ix_manager_vs_manager_history_manager_b_id", table_name="manager_vs_manager_history")
    op.drop_index("ix_manager_vs_manager_history_manager_a_id", table_name="manager_vs_manager_history")
    op.drop_table("manager_vs_manager_history")

    op.drop_index("ix_manager_match_history_source_match_id", table_name="manager_match_history")
    op.drop_index("ix_manager_match_history_opponent_manager_profile_id", table_name="manager_match_history")
    op.drop_index("ix_manager_match_history_manager_profile_id", table_name="manager_match_history")
    op.drop_table("manager_match_history")

    op.drop_index("ix_manager_profiles_gtex_ai_id", table_name="manager_profiles")
    with op.batch_alter_table("manager_profiles") as batch_op:
        batch_op.drop_constraint("uq_manager_profiles_gtex_ai_id", type_="unique")
        batch_op.drop_constraint("fk_manager_profiles_gtex_ai_id_gtex_ai_profiles", type_="foreignkey")
        batch_op.drop_column("tempo_control")
        batch_op.drop_column("substitution_logic")
        batch_op.drop_column("formation_preferences_json")
        batch_op.drop_column("discipline_style")
        batch_op.drop_column("youth_preference")
        batch_op.drop_column("ego_level")
        batch_op.drop_column("adaptability")
        batch_op.drop_column("risk_tolerance")
        batch_op.drop_column("tactical_style")
        batch_op.drop_column("name")
        batch_op.drop_column("gtex_ai_id")
        batch_op.alter_column("manager_id", existing_type=sa.String(length=36), nullable=False)
