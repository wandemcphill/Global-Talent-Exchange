"""Helpers for ingestion table DDL inside the foundation migration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


def upgrade_ingestion_tables() -> None:
    op.create_table(
        "ingestion_countries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("alpha2_code", sa.String(length=4), nullable=True),
        sa.Column("alpha3_code", sa.String(length=4), nullable=True),
        sa.Column("flag_url", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_countries"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_countries_provider_external_id"),
    )
    op.create_index("ix_ingestion_countries_alpha2_code", "ingestion_countries", ["alpha2_code"], unique=False)
    op.create_index("ix_ingestion_countries_alpha3_code", "ingestion_countries", ["alpha3_code"], unique=False)

    op.create_table(
        "ingestion_competitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("country_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=True),
        sa.Column("competition_type", sa.String(length=32), server_default=sa.text("'league'"), nullable=False),
        sa.Column("gender", sa.String(length=32), nullable=True),
        sa.Column("emblem_url", sa.String(length=255), nullable=True),
        sa.Column("is_major", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("current_season_external_id", sa.String(length=128), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["ingestion_countries.id"], name="fk_ingestion_competitions_country_id_ingestion_countries", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_competitions"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_competitions_provider_external_id"),
    )
    op.create_index("ix_ingestion_competitions_slug", "ingestion_competitions", ["slug"], unique=False)
    op.create_index("ix_ingestion_competitions_code", "ingestion_competitions", ["code"], unique=False)

    op.create_table(
        "ingestion_seasons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("year_start", sa.Integer(), nullable=True),
        sa.Column("year_end", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("current_matchday", sa.Integer(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["ingestion_competitions.id"], name="fk_ingestion_seasons_competition_id_ingestion_competitions", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_seasons"),
        sa.UniqueConstraint("competition_id", "label", name="uq_ingestion_seasons_competition_label"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_seasons_provider_external_id"),
    )
    op.create_index("ix_ingestion_seasons_competition_id", "ingestion_seasons", ["competition_id"], unique=False)

    op.create_table(
        "ingestion_clubs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("country_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("short_name", sa.String(length=80), nullable=True),
        sa.Column("code", sa.String(length=16), nullable=True),
        sa.Column("founded_year", sa.Integer(), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("venue", sa.String(length=160), nullable=True),
        sa.Column("crest_url", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["ingestion_countries.id"], name="fk_ingestion_clubs_country_id_ingestion_countries", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_clubs"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_clubs_provider_external_id"),
    )
    op.create_index("ix_ingestion_clubs_slug", "ingestion_clubs", ["slug"], unique=False)
    op.create_index("ix_ingestion_clubs_name", "ingestion_clubs", ["name"], unique=False)

    op.create_table(
        "ingestion_players",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("country_id", sa.String(length=36), nullable=True),
        sa.Column("current_club_id", sa.String(length=36), nullable=True),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("first_name", sa.String(length=80), nullable=True),
        sa.Column("last_name", sa.String(length=80), nullable=True),
        sa.Column("short_name", sa.String(length=80), nullable=True),
        sa.Column("position", sa.String(length=64), nullable=True),
        sa.Column("normalized_position", sa.String(length=32), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Integer(), nullable=True),
        sa.Column("preferred_foot", sa.String(length=16), nullable=True),
        sa.Column("shirt_number", sa.Integer(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["ingestion_countries.id"], name="fk_ingestion_players_country_id_ingestion_countries", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["current_club_id"], ["ingestion_clubs.id"], name="fk_ingestion_players_current_club_id_ingestion_clubs", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_players"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_players_provider_external_id"),
    )
    op.create_index("ix_ingestion_players_full_name", "ingestion_players", ["full_name"], unique=False)
    op.create_index("ix_ingestion_players_normalized_position", "ingestion_players", ["normalized_position"], unique=False)

    op.create_table(
        "ingestion_player_club_tenures",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("squad_number", sa.Integer(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_ingestion_player_club_tenures_player_id_ingestion_players", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["ingestion_clubs.id"], name="fk_ingestion_player_club_tenures_club_id_ingestion_clubs", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["ingestion_seasons.id"], name="fk_ingestion_player_club_tenures_season_id_ingestion_seasons", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_player_club_tenures"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_tenures_provider_external_id"),
    )
    op.create_index("ix_ingestion_tenures_player_id", "ingestion_player_club_tenures", ["player_id"], unique=False)
    op.create_index("ix_ingestion_tenures_club_id", "ingestion_player_club_tenures", ["club_id"], unique=False)

    op.create_table(
        "ingestion_matches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("home_club_id", sa.String(length=36), nullable=False),
        sa.Column("away_club_id", sa.String(length=36), nullable=False),
        sa.Column("winner_club_id", sa.String(length=36), nullable=True),
        sa.Column("venue", sa.String(length=160), nullable=True),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'scheduled'"), nullable=False),
        sa.Column("stage", sa.String(length=64), nullable=True),
        sa.Column("matchday", sa.Integer(), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("last_provider_update_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["ingestion_competitions.id"], name="fk_ingestion_matches_competition_id_ingestion_competitions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["ingestion_seasons.id"], name="fk_ingestion_matches_season_id_ingestion_seasons", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_club_id"], ["ingestion_clubs.id"], name="fk_ingestion_matches_home_club_id_ingestion_clubs", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["away_club_id"], ["ingestion_clubs.id"], name="fk_ingestion_matches_away_club_id_ingestion_clubs", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["winner_club_id"], ["ingestion_clubs.id"], name="fk_ingestion_matches_winner_club_id_ingestion_clubs", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_matches"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_matches_provider_external_id"),
    )
    op.create_index("ix_ingestion_matches_competition_id", "ingestion_matches", ["competition_id"], unique=False)
    op.create_index("ix_ingestion_matches_season_id", "ingestion_matches", ["season_id"], unique=False)
    op.create_index("ix_ingestion_matches_kickoff_at", "ingestion_matches", ["kickoff_at"], unique=False)

    op.create_table(
        "ingestion_team_standings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("standing_type", sa.String(length=32), server_default=sa.text("'total'"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("played", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("won", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("drawn", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lost", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("goals_for", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("goals_against", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("goal_difference", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("form", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["ingestion_competitions.id"], name="fk_ing_team_standings_competition", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["ingestion_seasons.id"], name="fk_ingestion_team_standings_season_id_ingestion_seasons", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["ingestion_clubs.id"], name="fk_ingestion_team_standings_club_id_ingestion_clubs", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_team_standings"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_standings_provider_external_id"),
        sa.UniqueConstraint("competition_id", "season_id", "club_id", "standing_type", name="uq_ingestion_standings_competition_season_club_type"),
    )
    op.create_index("ix_ingestion_standings_position", "ingestion_team_standings", ["position"], unique=False)

    op.create_table(
        "ingestion_player_match_stats",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("appearances", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("starts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("saves", sa.Integer(), nullable=True),
        sa.Column("clean_sheet", sa.Boolean(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("raw_position", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_ingestion_player_match_stats_player_id_ingestion_players", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["ingestion_matches.id"], name="fk_ingestion_player_match_stats_match_id_ingestion_matches", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["ingestion_clubs.id"], name="fk_ingestion_player_match_stats_club_id_ingestion_clubs", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["ingestion_competitions.id"], name="fk_ing_pmatch_stats_competition", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["season_id"], ["ingestion_seasons.id"], name="fk_ingestion_player_match_stats_season_id_ingestion_seasons", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_player_match_stats"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_player_match_stats_provider_external_id"),
        sa.UniqueConstraint("player_id", "match_id", name="uq_ingestion_player_match_stats_player_match"),
    )
    op.create_index("ix_ingestion_player_match_stats_match_id", "ingestion_player_match_stats", ["match_id"], unique=False)

    op.create_table(
        "ingestion_player_season_stats",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("appearances", sa.Integer(), nullable=True),
        sa.Column("starts", sa.Integer(), nullable=True),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("goals", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("yellow_cards", sa.Integer(), nullable=True),
        sa.Column("red_cards", sa.Integer(), nullable=True),
        sa.Column("clean_sheets", sa.Integer(), nullable=True),
        sa.Column("saves", sa.Integer(), nullable=True),
        sa.Column("average_rating", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_ingestion_player_season_stats_player_id_ingestion_players", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["ingestion_clubs.id"], name="fk_ingestion_player_season_stats_club_id_ingestion_clubs", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["ingestion_competitions.id"], name="fk_ing_pseason_stats_competition", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["season_id"], ["ingestion_seasons.id"], name="fk_ingestion_player_season_stats_season_id_ingestion_seasons", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_player_season_stats"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_player_season_stats_provider_external_id"),
        sa.UniqueConstraint("player_id", "season_id", "competition_id", name="uq_ingestion_player_season_stats_player_scope"),
    )
    op.create_index("ix_ingestion_player_season_stats_season_id", "ingestion_player_season_stats", ["season_id"], unique=False)

    op.create_table(
        "ingestion_injury_statuses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("expected_return_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_ingestion_injury_statuses_player_id_ingestion_players", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["ingestion_clubs.id"], name="fk_ingestion_injury_statuses_club_id_ingestion_clubs", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_injury_statuses"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_injuries_provider_external_id"),
    )

    op.create_table(
        "ingestion_market_signals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_ingestion_market_signals_player_id_ingestion_players", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_market_signals"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_market_signals_provider_external_id"),
    )
    op.create_index("ix_ingestion_market_signals_signal_type", "ingestion_market_signals", ["signal_type"], unique=False)

    op.create_table(
        "ingestion_provider_sync_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("job_name", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("scope_value", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("records_seen", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("inserted_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("updated_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cursor_value", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_provider_sync_runs"),
    )
    op.create_index("ix_ingestion_sync_runs_provider_status", "ingestion_provider_sync_runs", ["provider_name", "status"], unique=False)
    op.create_index("ix_ingestion_sync_runs_started_at", "ingestion_provider_sync_runs", ["started_at"], unique=False)

    op.create_table(
        "ingestion_provider_sync_cursors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("cursor_key", sa.String(length=64), server_default=sa.text("'default'"), nullable=False),
        sa.Column("cursor_value", sa.String(length=255), nullable=True),
        sa.Column("checkpoint_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["last_run_id"], ["ingestion_provider_sync_runs.id"], name="fk_ing_sync_cursors_last_run", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_provider_sync_cursors"),
        sa.UniqueConstraint("provider_name", "entity_type", "cursor_key", name="uq_ingestion_sync_cursors_provider_entity_key"),
    )

    op.create_table(
        "ingestion_provider_raw_payloads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=True),
        sa.Column("sync_run_id", sa.String(length=36), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_provider_raw_payloads"),
        sa.ForeignKeyConstraint(["sync_run_id"], ["ingestion_provider_sync_runs.id"], name="fk_ing_raw_payloads_sync_run", ondelete="SET NULL"),
        sa.UniqueConstraint("provider_name", "entity_type", "payload_hash", name="uq_ingestion_raw_payload_provider_hash"),
    )
    op.create_index("ix_ingestion_raw_payloads_external_id", "ingestion_provider_raw_payloads", ["provider_external_id"], unique=False)
    op.create_index("ix_ingestion_raw_payloads_received_at", "ingestion_provider_raw_payloads", ["received_at"], unique=False)

    op.create_table(
        "ingestion_job_locks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lock_key", sa.String(length=128), nullable=False),
        sa.Column("owner_token", sa.String(length=128), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_job_locks"),
        sa.UniqueConstraint("lock_key", name="uq_ingestion_job_locks_lock_key"),
    )
    op.create_index("ix_ingestion_job_locks_expires_at", "ingestion_job_locks", ["expires_at"], unique=False)


def downgrade_ingestion_tables() -> None:
    op.drop_index("ix_ingestion_job_locks_expires_at", table_name="ingestion_job_locks")
    op.drop_table("ingestion_job_locks")

    op.drop_index("ix_ingestion_raw_payloads_received_at", table_name="ingestion_provider_raw_payloads")
    op.drop_index("ix_ingestion_raw_payloads_external_id", table_name="ingestion_provider_raw_payloads")
    op.drop_table("ingestion_provider_raw_payloads")

    op.drop_table("ingestion_provider_sync_cursors")

    op.drop_index("ix_ingestion_sync_runs_started_at", table_name="ingestion_provider_sync_runs")
    op.drop_index("ix_ingestion_sync_runs_provider_status", table_name="ingestion_provider_sync_runs")
    op.drop_table("ingestion_provider_sync_runs")

    op.drop_index("ix_ingestion_market_signals_signal_type", table_name="ingestion_market_signals")
    op.drop_table("ingestion_market_signals")

    op.drop_table("ingestion_injury_statuses")

    op.drop_index("ix_ingestion_player_season_stats_season_id", table_name="ingestion_player_season_stats")
    op.drop_table("ingestion_player_season_stats")

    op.drop_index("ix_ingestion_player_match_stats_match_id", table_name="ingestion_player_match_stats")
    op.drop_table("ingestion_player_match_stats")

    op.drop_index("ix_ingestion_standings_position", table_name="ingestion_team_standings")
    op.drop_table("ingestion_team_standings")

    op.drop_index("ix_ingestion_matches_kickoff_at", table_name="ingestion_matches")
    op.drop_index("ix_ingestion_matches_season_id", table_name="ingestion_matches")
    op.drop_index("ix_ingestion_matches_competition_id", table_name="ingestion_matches")
    op.drop_table("ingestion_matches")

    op.drop_index("ix_ingestion_tenures_club_id", table_name="ingestion_player_club_tenures")
    op.drop_index("ix_ingestion_tenures_player_id", table_name="ingestion_player_club_tenures")
    op.drop_table("ingestion_player_club_tenures")

    op.drop_index("ix_ingestion_players_normalized_position", table_name="ingestion_players")
    op.drop_index("ix_ingestion_players_full_name", table_name="ingestion_players")
    op.drop_table("ingestion_players")

    op.drop_index("ix_ingestion_clubs_name", table_name="ingestion_clubs")
    op.drop_index("ix_ingestion_clubs_slug", table_name="ingestion_clubs")
    op.drop_table("ingestion_clubs")

    op.drop_index("ix_ingestion_seasons_competition_id", table_name="ingestion_seasons")
    op.drop_table("ingestion_seasons")

    op.drop_index("ix_ingestion_competitions_code", table_name="ingestion_competitions")
    op.drop_index("ix_ingestion_competitions_slug", table_name="ingestion_competitions")
    op.drop_table("ingestion_competitions")

    op.drop_index("ix_ingestion_countries_alpha3_code", table_name="ingestion_countries")
    op.drop_index("ix_ingestion_countries_alpha2_code", table_name="ingestion_countries")
    op.drop_table("ingestion_countries")
