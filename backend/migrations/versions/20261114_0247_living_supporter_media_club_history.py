"""Add persistent supporter, media, and institutional club history tables.

Revision ID: 20261114_0247_living_supporter_media_club_history
Revises: 20261114_0246_autonomous_staff_and_living_club_decisions
Create Date: 2026-11-14 16:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261114_0247_living_supporter_media_club_history"
down_revision = "20261114_0246_autonomous_staff_and_living_club_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "owner_supporter_profiles" not in existing_tables:
        op.create_table(
            "owner_supporter_profiles",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("owner_user_id", sa.String(length=36), nullable=False),
            sa.Column(
                "supporter_culture_label",
                sa.String(length=120),
                nullable=False,
                server_default="Community & Youth Traditionalists",
            ),
            sa.Column("overall_sentiment", sa.Integer(), nullable=False, server_default="65"),
            sa.Column("confidence_in_owner", sa.Integer(), nullable=False, server_default="65"),
            sa.Column("confidence_in_manager", sa.Integer(), nullable=False, server_default="68"),
            sa.Column("loyalty_index", sa.Integer(), nullable=False, server_default="72"),
            sa.Column("matchday_enthusiasm", sa.Integer(), nullable=False, server_default="66"),
            sa.Column("accumulated_frustration", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("consecutive_disappointments", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("consecutive_victories", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("ticket_price_tier", sa.String(length=24), nullable=False, server_default="standard"),
            sa.Column("matchday_experience_rating", sa.Integer(), nullable=False, server_default="62"),
            sa.Column("active_protest_stage", sa.String(length=32), nullable=False, server_default="none"),
            sa.Column("active_campaign_headline", sa.String(length=240), nullable=True),
            sa.Column("attendance_modifier_pct", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("owner_credibility_score", sa.Integer(), nullable=False, server_default="72"),
            sa.Column("expectations_json", sa.JSON(), nullable=False),
            sa.Column("atmosphere_profile_json", sa.JSON(), nullable=False),
            sa.Column("last_reconciled_world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("club_id", name="uq_owner_supporter_profiles_club_id"),
        )
        op.create_index("ix_owner_supporter_profiles_club_id", "owner_supporter_profiles", ["club_id"])
        op.create_index("ix_owner_supporter_profiles_owner_user_id", "owner_supporter_profiles", ["owner_user_id"])

    if "owner_supporter_segments" not in existing_tables:
        op.create_table(
            "owner_supporter_segments",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("segment_key", sa.String(length=40), nullable=False),
            sa.Column("segment_name", sa.String(length=80), nullable=False),
            sa.Column("population_share_pct", sa.Integer(), nullable=False, server_default="16"),
            sa.Column("member_count", sa.Integer(), nullable=False, server_default="200"),
            sa.Column("sentiment", sa.Integer(), nullable=False, server_default="65"),
            sa.Column("loyalty", sa.Integer(), nullable=False, server_default="70"),
            sa.Column("enthusiasm", sa.Integer(), nullable=False, server_default="65"),
            sa.Column("owner_approval", sa.Integer(), nullable=False, server_default="65"),
            sa.Column("scar_tissue", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status_label", sa.String(length=40), nullable=False, server_default="content"),
            sa.Column("priorities_json", sa.JSON(), nullable=False),
            sa.Column("expectations_json", sa.JSON(), nullable=False),
            sa.Column("recent_memory_json", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("club_id", "segment_key", name="uq_owner_supporter_segments_club_segment"),
        )
        op.create_index("ix_owner_supporter_segments_club_id", "owner_supporter_segments", ["club_id"])
        op.create_index("ix_owner_supporter_segments_segment_key", "owner_supporter_segments", ["segment_key"])

    if "owner_supporter_events" not in existing_tables:
        op.create_table(
            "owner_supporter_events",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("event_type", sa.String(length=48), nullable=False),
            sa.Column("trigger_source_type", sa.String(length=48), nullable=False, server_default="club_event"),
            sa.Column("trigger_source_id", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("headline", sa.String(length=240), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("overall_sentiment_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("credibility_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("attendance_impact_pct", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("segment_deltas_json", sa.JSON(), nullable=False),
            sa.Column("contradiction_detected", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("contradiction_reason", sa.String(length=240), nullable=True),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("idempotency_key", name="uq_owner_supporter_events_idempotency"),
        )
        op.create_index("ix_owner_supporter_events_club_id", "owner_supporter_events", ["club_id"])
        op.create_index("ix_owner_supporter_events_world_day", "owner_supporter_events", ["world_day"])
        op.create_index("ix_owner_supporter_events_event_type", "owner_supporter_events", ["event_type"])
        op.create_index("ix_owner_supporter_events_idempotency_key", "owner_supporter_events", ["idempotency_key"])

    if "owner_media_outlets" not in existing_tables:
        op.create_table(
            "owner_media_outlets",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("outlet_key", sa.String(length=64), nullable=False),
            sa.Column("outlet_name", sa.String(length=120), nullable=False),
            sa.Column("journalist_name", sa.String(length=120), nullable=False),
            sa.Column(
                "journalist_role", sa.String(length=80), nullable=False, server_default="Senior Football Correspondent"
            ),
            sa.Column("editorial_focus", sa.String(length=48), nullable=False),
            sa.Column("credibility_tier", sa.String(length=32), nullable=False, server_default="tier_1_authoritative"),
            sa.Column("credibility_score", sa.Integer(), nullable=False, server_default="88"),
            sa.Column("tone_style", sa.String(length=48), nullable=False, server_default="analytical"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("outlet_key", name="uq_owner_media_outlets_outlet_key"),
        )
        op.create_index("ix_owner_media_outlets_outlet_key", "owner_media_outlets", ["outlet_key"])
        op.create_index("ix_owner_media_outlets_editorial_focus", "owner_media_outlets", ["editorial_focus"])

    if "owner_media_stories" not in existing_tables:
        op.create_table(
            "owner_media_stories",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("outlet_key", sa.String(length=64), nullable=False),
            sa.Column("outlet_name", sa.String(length=120), nullable=False),
            sa.Column("journalist_name", sa.String(length=120), nullable=False),
            sa.Column("editorial_focus", sa.String(length=48), nullable=False, server_default="local_club_reporting"),
            sa.Column("credibility_score", sa.Integer(), nullable=False, server_default="85"),
            sa.Column("story_type", sa.String(length=48), nullable=False),
            sa.Column("classification", sa.String(length=32), nullable=False),
            sa.Column("is_confirmed_fact", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("headline", sa.String(length=240), nullable=False),
            sa.Column("subheadline", sa.String(length=320), nullable=False, server_default=""),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("source_type", sa.String(length=48), nullable=False, server_default="club_event"),
            sa.Column("source_id", sa.String(length=128), nullable=False, server_default=""),
            sa.Column("established_facts_json", sa.JSON(), nullable=False),
            sa.Column("grounding_report_json", sa.JSON(), nullable=False),
            sa.Column("reputation_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("supporter_sentiment_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("commercial_attractiveness_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sponsorship_interest_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("leadership_pressure_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("owner_response_json", sa.JSON(), nullable=True),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("idempotency_key", name="uq_owner_media_stories_idempotency"),
        )
        op.create_index("ix_owner_media_stories_club_id", "owner_media_stories", ["club_id"])
        op.create_index("ix_owner_media_stories_world_day", "owner_media_stories", ["world_day"])
        op.create_index("ix_owner_media_stories_story_type", "owner_media_stories", ["story_type"])
        op.create_index("ix_owner_media_stories_classification", "owner_media_stories", ["classification"])
        op.create_index("ix_owner_media_stories_idempotency_key", "owner_media_stories", ["idempotency_key"])

    if "owner_club_history_entries" not in existing_tables:
        op.create_table(
            "owner_club_history_entries",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("season_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("category", sa.String(length=48), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=240), nullable=False),
            sa.Column("narrative_summary", sa.Text(), nullable=False),
            sa.Column("entity_type", sa.String(length=48), nullable=True),
            sa.Column("entity_id", sa.String(length=128), nullable=True),
            sa.Column("entity_name", sa.String(length=160), nullable=True),
            sa.Column("established_facts_json", sa.JSON(), nullable=False),
            sa.Column("is_major_milestone", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("idempotency_key", name="uq_owner_club_history_entries_idempotency"),
        )
        op.create_index("ix_owner_club_history_entries_club_id", "owner_club_history_entries", ["club_id"])
        op.create_index("ix_owner_club_history_entries_category", "owner_club_history_entries", ["category"])
        op.create_index("ix_owner_club_history_entries_world_day", "owner_club_history_entries", ["world_day"])
        op.create_index(
            "ix_owner_club_history_entries_idempotency_key", "owner_club_history_entries", ["idempotency_key"]
        )

    if "owner_club_season_archives" not in existing_tables:
        op.create_table(
            "owner_club_season_archives",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("season_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("season_label", sa.String(length=64), nullable=False, server_default="Season 1"),
            sa.Column("competition_id", sa.String(length=36), nullable=False),
            sa.Column("competition_name", sa.String(length=120), nullable=False),
            sa.Column("competition_format", sa.String(length=24), nullable=False, server_default="league"),
            sa.Column("division_level", sa.Integer(), nullable=False, server_default="4"),
            sa.Column("final_position", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("played", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("won", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("drawn", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("lost", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("goals_for", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("goals_against", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("trophy_won", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("promotion_status", sa.String(length=32), nullable=False, server_default="retained"),
            sa.Column("manager_name", sa.String(length=120), nullable=False, server_default="First-Team Manager"),
            sa.Column("top_scorer_name", sa.String(length=120), nullable=True),
            sa.Column("top_scorer_goals", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("prize_money_gtex", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
            sa.Column("average_attendance", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("narrative_summary", sa.Text(), nullable=False),
            sa.Column("records_snapshot_json", sa.JSON(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("idempotency_key", name="uq_owner_club_season_archives_idempotency"),
        )
        op.create_index("ix_owner_club_season_archives_club_id", "owner_club_season_archives", ["club_id"])
        op.create_index(
            "ix_owner_club_season_archives_competition_id", "owner_club_season_archives", ["competition_id"]
        )

    if "owner_club_managerial_tenures" not in existing_tables:
        op.create_table(
            "owner_club_managerial_tenures",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("manager_id", sa.String(length=64), nullable=False),
            sa.Column("manager_name", sa.String(length=120), nullable=False),
            sa.Column("role", sa.String(length=48), nullable=False, server_default="first_team_manager"),
            sa.Column("tactical_style", sa.String(length=48), nullable=False, server_default="balanced"),
            sa.Column("appointed_world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("departed_world_day", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
            sa.Column("matches_managed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("goals_for", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("goals_against", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("trophies_won", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("departure_reason", sa.String(length=120), nullable=True),
            sa.Column("severance_paid_gtex", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
            sa.Column("honors_json", sa.JSON(), nullable=False),
            sa.Column("tenure_summary", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_owner_club_managerial_tenures_club_id", "owner_club_managerial_tenures", ["club_id"])
        op.create_index("ix_owner_club_managerial_tenures_status", "owner_club_managerial_tenures", ["status"])

    if "owner_club_transfer_records" not in existing_tables:
        op.create_table(
            "owner_club_transfer_records",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("direction", sa.String(length=16), nullable=False),
            sa.Column("transfer_type", sa.String(length=32), nullable=False, server_default="market_signing"),
            sa.Column("player_id", sa.String(length=64), nullable=False),
            sa.Column("player_name", sa.String(length=120), nullable=False),
            sa.Column("position", sa.String(length=16), nullable=False, server_default="MID"),
            sa.Column("age", sa.Integer(), nullable=False, server_default="22"),
            sa.Column("overall_rating", sa.Integer(), nullable=False, server_default="70"),
            sa.Column("fee_gtex", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
            sa.Column("wage_gtex", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0"),
            sa.Column(
                "counterparty_club_name", sa.String(length=120), nullable=False, server_default="GTEX Transfer Market"
            ),
            sa.Column("season_number", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("is_record_signing", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_record_sale", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("narrative_note", sa.String(length=240), nullable=False, server_default=""),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("idempotency_key", name="uq_owner_club_transfer_records_idempotency"),
        )
        op.create_index("ix_owner_club_transfer_records_club_id", "owner_club_transfer_records", ["club_id"])
        op.create_index("ix_owner_club_transfer_records_direction", "owner_club_transfer_records", ["direction"])

    if "owner_club_academy_graduates" not in existing_tables:
        op.create_table(
            "owner_club_academy_graduates",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("player_id", sa.String(length=64), nullable=False),
            sa.Column("player_name", sa.String(length=120), nullable=False),
            sa.Column("position", sa.String(length=16), nullable=False, server_default="MID"),
            sa.Column("intake_world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("promoted_world_day", sa.Integer(), nullable=True),
            sa.Column("debut_world_day", sa.Integer(), nullable=True),
            sa.Column("debut_match_id", sa.String(length=64), nullable=True),
            sa.Column("debut_opponent_name", sa.String(length=120), nullable=True),
            sa.Column("initial_rating", sa.Integer(), nullable=False, server_default="55"),
            sa.Column("current_rating", sa.Integer(), nullable=False, server_default="55"),
            sa.Column("potential_rating", sa.Integer(), nullable=False, server_default="78"),
            sa.Column("first_team_appearances", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("first_team_goals", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="academy_prospect"),
            sa.Column("narrative_note", sa.String(length=240), nullable=False, server_default=""),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("idempotency_key", name="uq_owner_club_academy_graduates_idempotency"),
        )
        op.create_index("ix_owner_club_academy_graduates_club_id", "owner_club_academy_graduates", ["club_id"])
        op.create_index("ix_owner_club_academy_graduates_player_id", "owner_club_academy_graduates", ["player_id"])

    if "owner_club_rivalries" not in existing_tables:
        op.create_table(
            "owner_club_rivalries",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("club_id", sa.String(length=36), nullable=False),
            sa.Column("rival_club_id", sa.String(length=64), nullable=False),
            sa.Column("rival_club_name", sa.String(length=120), nullable=False),
            sa.Column("rivalry_name", sa.String(length=160), nullable=False, server_default="Competitive Fixture"),
            sa.Column("origin_reason", sa.String(length=120), nullable=False, server_default="repeated_encounters"),
            sa.Column("intensity_score", sa.Integer(), nullable=False, server_default="20"),
            sa.Column("rivalry_tier", sa.String(length=32), nullable=False, server_default="emerging"),
            sa.Column("matches_played", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("wins", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("draws", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("losses", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("goals_for", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("goals_against", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_meeting_world_day", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("notable_encounters_json", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("club_id", "rival_club_id", name="uq_owner_club_rivalries_club_rival"),
        )
        op.create_index("ix_owner_club_rivalries_club_id", "owner_club_rivalries", ["club_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table_name in (
        "owner_club_rivalries",
        "owner_club_academy_graduates",
        "owner_club_transfer_records",
        "owner_club_managerial_tenures",
        "owner_club_season_archives",
        "owner_club_history_entries",
        "owner_media_stories",
        "owner_media_outlets",
        "owner_supporter_events",
        "owner_supporter_segments",
        "owner_supporter_profiles",
    ):
        if table_name in existing_tables:
            op.drop_table(table_name)
