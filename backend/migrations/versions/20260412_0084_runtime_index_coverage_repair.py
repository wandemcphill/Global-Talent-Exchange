"""Repair missing runtime index coverage surfaced by migration-integrity checks.

Revision ID: 20260412_0084_runtime_index_coverage_repair
Revises: 20260410_0083_admin_runtime_state
Create Date: 2026-04-12 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260412_0084_runtime_index_coverage_repair"
down_revision = "20260410_0083_admin_runtime_state"
branch_labels = None
depends_on = None

INDEX_SPECS: tuple[tuple[str, str, list[str]], ...] = (
    ("economy_burn_events", "ix_economy_burn_events_source_id", ["source_id"]),
    ("spending_control_audit_events", "ix_spending_control_audit_events_control_scope", ["control_scope"]),
    ("ticket_waitlists", "ix_ticket_waitlists_match_id", ["match_id"]),
    ("country_creator_assignments", "ix_country_creator_assignments_assigned_by_user_id", ["assigned_by_user_id"]),
    ("country_creator_assignments", "ix_country_creator_assignments_club_id", ["club_id"]),
    ("country_creator_assignments", "ix_country_creator_assignments_country_code", ["represented_country_code"]),
    ("country_creator_assignments", "ix_country_creator_assignments_creator_user_id", ["creator_user_id"]),
    ("creator_club_follows", "ix_creator_club_follows_club_id", ["club_id"]),
    ("creator_club_follows", "ix_creator_club_follows_user_id", ["user_id"]),
    ("creator_fan_groups", "ix_creator_fan_groups_club_id", ["club_id"]),
    ("creator_fan_groups", "ix_creator_fan_groups_created_by_user_id", ["created_by_user_id"]),
    ("creator_fan_groups", "ix_creator_fan_groups_slug", ["slug"]),
    ("fan_war_profiles", "ix_fan_war_profiles_club_id", ["club_id"]),
    ("fan_war_profiles", "ix_fan_war_profiles_country_code", ["country_code"]),
    ("fan_war_profiles", "ix_fan_war_profiles_creator_profile_id", ["creator_profile_id"]),
    ("fan_war_profiles", "ix_fan_war_profiles_profile_type", ["profile_type"]),
    ("gtex_league_standings", "ix_gtex_league_standings_ai_id", ["ai_id"]),
    ("gtex_league_standings", "ix_gtex_league_standings_user_id", ["user_id"]),
    ("gtex_matches", "ix_gtex_matches_away_ai_id", ["away_ai_id"]),
    ("gtex_matches", "ix_gtex_matches_away_user_id", ["away_user_id"]),
    ("gtex_matches", "ix_gtex_matches_home_ai_id", ["home_ai_id"]),
    ("gtex_matches", "ix_gtex_matches_home_user_id", ["home_user_id"]),
    ("gtex_matches", "ix_gtex_matches_queued_at", ["queued_at"]),
    ("gtex_matches", "ix_gtex_matches_requested_by_user_id", ["requested_by_user_id"]),
    ("gtex_matches", "ix_gtex_matches_winner_ai_id", ["winner_ai_id"]),
    ("gtex_matches", "ix_gtex_matches_winner_user_id", ["winner_user_id"]),
    ("ticket_reactions", "ix_ticket_reactions_match_id", ["match_id"]),
    ("creator_fan_competitions", "ix_creator_fan_competitions_club_id", ["club_id"]),
    ("creator_fan_competitions", "ix_creator_fan_competitions_created_by_user_id", ["created_by_user_id"]),
    ("creator_fan_competitions", "ix_creator_fan_competitions_match_id", ["match_id"]),
    ("creator_fan_group_memberships", "ix_creator_fan_group_memberships_club_id", ["club_id"]),
    ("creator_fan_group_memberships", "ix_creator_fan_group_memberships_group_id", ["group_id"]),
    ("creator_fan_group_memberships", "ix_creator_fan_group_memberships_user_id", ["user_id"]),
    ("creator_fan_wall_events", "ix_creator_fan_wall_events_actor_user_id", ["actor_user_id"]),
    ("creator_fan_wall_events", "ix_creator_fan_wall_events_club_id", ["club_id"]),
    ("creator_fan_wall_events", "ix_creator_fan_wall_events_event_kind", ["event_kind"]),
    ("creator_fan_wall_events", "ix_creator_fan_wall_events_match_id", ["match_id"]),
    ("creator_match_chat_rooms", "ix_creator_match_chat_rooms_competition_id", ["competition_id"]),
    ("creator_match_chat_rooms", "ix_creator_match_chat_rooms_season_id", ["season_id"]),
    ("creator_match_tactical_advice", "ix_creator_match_tactical_advice_author_user_id", ["author_user_id"]),
    ("creator_match_tactical_advice", "ix_creator_match_tactical_advice_competition_id", ["competition_id"]),
    ("creator_match_tactical_advice", "ix_creator_match_tactical_advice_match_id", ["match_id"]),
    ("creator_match_tactical_advice", "ix_creator_match_tactical_advice_season_id", ["season_id"]),
    ("creator_match_tactical_advice", "ix_creator_match_tactical_advice_supported_club_id", ["supported_club_id"]),
    ("creator_rivalry_signal_outputs", "ix_creator_rivalry_signal_outputs_away_club_id", ["away_club_id"]),
    ("creator_rivalry_signal_outputs", "ix_creator_rivalry_signal_outputs_club_social_rivalry_id", ["club_social_rivalry_id"]),
    ("creator_rivalry_signal_outputs", "ix_creator_rivalry_signal_outputs_home_club_id", ["home_club_id"]),
    ("creator_rivalry_signal_outputs", "ix_creator_rivalry_signal_outputs_match_id", ["match_id"]),
    ("fan_prediction_fixtures", "ix_fan_prediction_fixtures_away_club_id", ["away_club_id"]),
    ("fan_prediction_fixtures", "ix_fan_prediction_fixtures_competition_id", ["competition_id"]),
    ("fan_prediction_fixtures", "ix_fan_prediction_fixtures_created_by_user_id", ["created_by_user_id"]),
    ("fan_prediction_fixtures", "ix_fan_prediction_fixtures_home_club_id", ["home_club_id"]),
    ("fan_prediction_fixtures", "ix_fan_prediction_fixtures_locks_at", ["locks_at"]),
    ("fan_prediction_fixtures", "ix_fan_prediction_fixtures_opens_at", ["opens_at"]),
    ("fan_prediction_fixtures", "ix_fan_prediction_fixtures_season_id", ["season_id"]),
    ("fan_prediction_fixtures", "ix_fan_prediction_fixtures_settled_at", ["settled_at"]),
    ("fanbase_rankings", "ix_fanbase_rankings_lookup", ["board_type", "period_type", "window_start"]),
    ("fanbase_rankings", "ix_fanbase_rankings_profile_id", ["profile_id"]),
    ("gtex_match_queue_entries", "ix_gtex_match_queue_entries_league_id", ["league_id"]),
    ("gtex_match_queue_entries", "ix_gtex_match_queue_entries_match_id", ["match_id"]),
    ("nations_cup_entries", "ix_nations_cup_entries_assignment_id", ["assignment_id"]),
    ("nations_cup_entries", "ix_nations_cup_entries_club_id", ["club_id"]),
    ("nations_cup_entries", "ix_nations_cup_entries_competition_id", ["competition_id"]),
    ("nations_cup_entries", "ix_nations_cup_entries_competition_status", ["competition_id", "status"]),
    ("nations_cup_entries", "ix_nations_cup_entries_country_code", ["country_code"]),
    ("nations_cup_entries", "ix_nations_cup_entries_creator_profile_id", ["creator_profile_id"]),
    ("nations_cup_entries", "ix_nations_cup_entries_creator_user_id", ["creator_user_id"]),
    ("nations_cup_entries", "ix_nations_cup_entries_group_key", ["group_key"]),
    ("creator_fan_competition_entries", "ix_creator_fan_competition_entries_club_id", ["club_id"]),
    ("creator_fan_competition_entries", "ix_creator_fan_competition_entries_fan_competition_id", ["fan_competition_id"]),
    ("creator_fan_competition_entries", "ix_creator_fan_competition_entries_fan_group_id", ["fan_group_id"]),
    ("creator_fan_competition_entries", "ix_creator_fan_competition_entries_user_id", ["user_id"]),
    ("creator_match_chat_messages", "ix_creator_match_chat_messages_author_user_id", ["author_user_id"]),
    ("creator_match_chat_messages", "ix_creator_match_chat_messages_room_id", ["room_id"]),
    ("creator_match_chat_messages", "ix_creator_match_chat_messages_supported_club_id", ["supported_club_id"]),
    ("fan_prediction_outcomes", "ix_fan_prediction_outcomes_first_goal_scorer_player_id", ["first_goal_scorer_player_id"]),
    ("fan_prediction_outcomes", "ix_fan_prediction_outcomes_match_id", ["match_id"]),
    ("fan_prediction_outcomes", "ix_fan_prediction_outcomes_mvp_player_id", ["mvp_player_id"]),
    ("fan_prediction_outcomes", "ix_fan_prediction_outcomes_settled_by_user_id", ["settled_by_user_id"]),
    ("fan_prediction_outcomes", "ix_fan_prediction_outcomes_winner_club_id", ["winner_club_id"]),
    ("fan_prediction_submissions", "ix_fan_prediction_submissions_fan_group_id", ["fan_group_id"]),
    ("fan_prediction_submissions", "ix_fan_prediction_submissions_fan_segment_club_id", ["fan_segment_club_id"]),
    ("fan_prediction_submissions", "ix_fan_prediction_submissions_first_goal_scorer_player_id", ["first_goal_scorer_player_id"]),
    ("fan_prediction_submissions", "ix_fan_prediction_submissions_fixture_id", ["fixture_id"]),
    ("fan_prediction_submissions", "ix_fan_prediction_submissions_leaderboard_week_start", ["leaderboard_week_start"]),
    ("fan_prediction_submissions", "ix_fan_prediction_submissions_mvp_player_id", ["mvp_player_id"]),
    ("fan_prediction_submissions", "ix_fan_prediction_submissions_settled_at", ["settled_at"]),
    ("fan_prediction_submissions", "ix_fan_prediction_submissions_user_id", ["user_id"]),
    ("fan_prediction_submissions", "ix_fan_prediction_submissions_winner_club_id", ["winner_club_id"]),
    ("fan_war_points", "ix_fan_war_points_actor_user_id", ["actor_user_id"]),
    ("fan_war_points", "ix_fan_war_points_awarded_at", ["awarded_at"]),
    ("fan_war_points", "ix_fan_war_points_competition_id", ["competition_id"]),
    ("fan_war_points", "ix_fan_war_points_match_id", ["match_id"]),
    ("fan_war_points", "ix_fan_war_points_nations_cup_entry_id", ["nations_cup_entry_id"]),
    ("fan_war_points", "ix_fan_war_points_profile_id", ["profile_id"]),
    ("fan_war_points", "ix_fan_war_points_source_type", ["source_type"]),
    ("nations_cup_fan_metrics", "ix_nations_cup_fan_metrics_competition_id", ["competition_id"]),
    ("nations_cup_fan_metrics", "ix_nations_cup_fan_metrics_country_code", ["country_code"]),
    ("nations_cup_fan_metrics", "ix_nations_cup_fan_metrics_creator_profile_id", ["creator_profile_id"]),
    ("nations_cup_fan_metrics", "ix_nations_cup_fan_metrics_entry_id", ["entry_id"]),
    ("fan_prediction_reward_grants", "ix_fan_prediction_reward_grants_awarded_by_user_id", ["awarded_by_user_id"]),
    ("fan_prediction_reward_grants", "ix_fan_prediction_reward_grants_club_id", ["club_id"]),
    ("fan_prediction_reward_grants", "ix_fan_prediction_reward_grants_fixture_id", ["fixture_id"]),
    ("fan_prediction_reward_grants", "ix_fan_prediction_reward_grants_promo_pool_reference", ["promo_pool_reference"]),
    ("fan_prediction_reward_grants", "ix_fan_prediction_reward_grants_reward_settlement_id", ["reward_settlement_id"]),
    ("fan_prediction_reward_grants", "ix_fan_prediction_reward_grants_submission_id", ["submission_id"]),
    ("fan_prediction_reward_grants", "ix_fan_prediction_reward_grants_user_id", ["user_id"]),
    ("fan_prediction_reward_grants", "ix_fan_prediction_reward_grants_week_start", ["week_start"]),
    ("fan_prediction_token_ledger", "ix_fan_prediction_token_ledger_created_by_user_id", ["created_by_user_id"]),
    ("fan_prediction_token_ledger", "ix_fan_prediction_token_ledger_effective_date", ["effective_date"]),
    ("fan_prediction_token_ledger", "ix_fan_prediction_token_ledger_reference", ["reference"]),
    ("fan_prediction_token_ledger", "ix_fan_prediction_token_ledger_season_pass_id", ["season_pass_id"]),
    ("fan_prediction_token_ledger", "ix_fan_prediction_token_ledger_submission_id", ["submission_id"]),
    ("fan_prediction_token_ledger", "ix_fan_prediction_token_ledger_user_id", ["user_id"]),
)


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _indexed_column_sets(bind, table_name: str) -> set[tuple[str, ...]]:
    return {tuple(index.get("column_names") or ()) for index in sa.inspect(bind).get_indexes(table_name)}


def _unique_column_sets(bind, table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(constraint.get("column_names") or ())
        for constraint in sa.inspect(bind).get_unique_constraints(table_name)
    }


def _create_index_if_missing(bind, *, table_name: str, index_name: str, columns: list[str]) -> None:
    column_tuple = tuple(columns)
    if index_name in _index_names(bind, table_name):
        return
    if column_tuple in _indexed_column_sets(bind, table_name):
        return
    if column_tuple in _unique_column_sets(bind, table_name):
        return
    op.create_index(index_name, table_name, columns, unique=False)


def _drop_index_if_present(bind, *, table_name: str, index_name: str) -> None:
    if index_name in _index_names(bind, table_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, index_name, columns in INDEX_SPECS:
        if not inspector.has_table(table_name):
            continue
        _create_index_if_missing(
            bind,
            table_name=table_name,
            index_name=index_name,
            columns=columns,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, index_name, _columns in reversed(INDEX_SPECS):
        if not inspector.has_table(table_name):
            continue
        _drop_index_if_present(
            bind,
            table_name=table_name,
            index_name=index_name,
        )
