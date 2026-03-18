"""Add club challenge, reaction, identity, and rivalry persistence."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260316_0009a"
down_revision = "20260316_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "club_challenges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("issuing_club_id", sa.String(length=36), nullable=False),
        sa.Column("target_club_id", sa.String(length=36), nullable=True),
        sa.Column("issuing_user_id", sa.String(length=36), nullable=True),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("linked_match_id", sa.String(length=36), nullable=True),
        sa.Column("accepted_club_id", sa.String(length=36), nullable=True),
        sa.Column("winner_club_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("stakes_text", sa.String(length=255), nullable=True),
        sa.Column("visibility", sa.String(length=24), server_default=sa.text("'public'"), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("region_name", sa.String(length=120), nullable=True),
        sa.Column("city_name", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'open'"), nullable=False),
        sa.Column("accept_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["accepted_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["issuing_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issuing_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_match_id"], ["competition_matches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["winner_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_challenges"),
        sa.UniqueConstraint("slug", name="uq_club_challenges_slug"),
    )
    op.create_index(op.f("ix_club_challenges_issuing_club_id"), "club_challenges", ["issuing_club_id"], unique=False)
    op.create_index(op.f("ix_club_challenges_target_club_id"), "club_challenges", ["target_club_id"], unique=False)
    op.create_index(op.f("ix_club_challenges_issuing_user_id"), "club_challenges", ["issuing_user_id"], unique=False)
    op.create_index(op.f("ix_club_challenges_competition_id"), "club_challenges", ["competition_id"], unique=False)
    op.create_index(op.f("ix_club_challenges_linked_match_id"), "club_challenges", ["linked_match_id"], unique=False)
    op.create_index(op.f("ix_club_challenges_accepted_club_id"), "club_challenges", ["accepted_club_id"], unique=False)
    op.create_index(op.f("ix_club_challenges_winner_club_id"), "club_challenges", ["winner_club_id"], unique=False)
    op.create_index(op.f("ix_club_challenges_slug"), "club_challenges", ["slug"], unique=False)
    op.create_index(op.f("ix_club_challenges_visibility"), "club_challenges", ["visibility"], unique=False)
    op.create_index(op.f("ix_club_challenges_country_code"), "club_challenges", ["country_code"], unique=False)
    op.create_index(op.f("ix_club_challenges_region_name"), "club_challenges", ["region_name"], unique=False)
    op.create_index(op.f("ix_club_challenges_city_name"), "club_challenges", ["city_name"], unique=False)
    op.create_index(op.f("ix_club_challenges_status"), "club_challenges", ["status"], unique=False)
    op.create_index(op.f("ix_club_challenges_scheduled_for"), "club_challenges", ["scheduled_for"], unique=False)

    op.create_table(
        "club_challenge_responses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("challenge_id", sa.String(length=36), nullable=False),
        sa.Column("responding_club_id", sa.String(length=36), nullable=False),
        sa.Column("responder_user_id", sa.String(length=36), nullable=True),
        sa.Column("response_type", sa.String(length=24), server_default=sa.text("'accept'"), nullable=False),
        sa.Column("response_status", sa.String(length=24), server_default=sa.text("'recorded'"), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["club_challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responding_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responder_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_challenge_responses"),
        sa.UniqueConstraint("challenge_id", "responding_club_id", name="uq_club_challenge_responses_challenge_club"),
    )
    op.create_index(op.f("ix_club_challenge_responses_challenge_id"), "club_challenge_responses", ["challenge_id"], unique=False)
    op.create_index(op.f("ix_club_challenge_responses_responding_club_id"), "club_challenge_responses", ["responding_club_id"], unique=False)
    op.create_index(op.f("ix_club_challenge_responses_responder_user_id"), "club_challenge_responses", ["responder_user_id"], unique=False)

    op.create_table(
        "club_challenge_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("challenge_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("channel", sa.String(length=32), server_default=sa.text("'share'"), nullable=False),
        sa.Column("link_code", sa.String(length=40), nullable=False),
        sa.Column("vanity_path", sa.String(length=220), nullable=False),
        sa.Column("web_path", sa.String(length=255), nullable=False),
        sa.Column("deep_link_path", sa.String(length=255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("click_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["club_challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_challenge_links"),
        sa.UniqueConstraint("link_code", name="uq_club_challenge_links_link_code"),
        sa.UniqueConstraint("vanity_path", name="uq_club_challenge_links_vanity_path"),
    )
    op.create_index(op.f("ix_club_challenge_links_challenge_id"), "club_challenge_links", ["challenge_id"], unique=False)
    op.create_index(op.f("ix_club_challenge_links_created_by_user_id"), "club_challenge_links", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_club_challenge_links_link_code"), "club_challenge_links", ["link_code"], unique=False)

    op.create_table(
        "club_identity_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("fan_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("reputation_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("media_popularity_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("media_value_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("club_valuation_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rivalry_intensity_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("support_momentum_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sponsorship_potential_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("discoverability_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("challenge_history_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_identity_metrics"),
        sa.UniqueConstraint("club_id", name="uq_club_identity_metrics_club_id"),
    )
    op.create_index(op.f("ix_club_identity_metrics_club_id"), "club_identity_metrics", ["club_id"], unique=False)

    op.create_table(
        "rivalry_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_a_id", sa.String(length=36), nullable=False),
        sa.Column("club_b_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=80), server_default=sa.text("'Emerging rivalry'"), nullable=False),
        sa.Column("intensity_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("regional_derby", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("giant_killer_flag", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("matches_played", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("club_a_wins", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("club_b_wins", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("draws", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("club_a_goals", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("club_b_goals", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("finals_played", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("upset_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("challenge_matches", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("high_view_matches", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("high_gift_matches", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("streak_holder_club_id", sa.String(length=36), nullable=True),
        sa.Column("streak_length", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_match_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notable_moments_json", sa.JSON(), nullable=False),
        sa.Column("narrative_tags_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_a_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_b_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["streak_holder_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_rivalry_profiles"),
        sa.UniqueConstraint("club_a_id", "club_b_id", name="uq_rivalry_profiles_pair"),
    )
    op.create_index(op.f("ix_rivalry_profiles_club_a_id"), "rivalry_profiles", ["club_a_id"], unique=False)
    op.create_index(op.f("ix_rivalry_profiles_club_b_id"), "rivalry_profiles", ["club_b_id"], unique=False)

    op.create_table(
        "rivalry_match_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("rivalry_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("challenge_id", sa.String(length=36), nullable=True),
        sa.Column("home_club_id", sa.String(length=36), nullable=False),
        sa.Column("away_club_id", sa.String(length=36), nullable=False),
        sa.Column("winner_club_id", sa.String(length=36), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=False),
        sa.Column("away_score", sa.Integer(), nullable=False),
        sa.Column("upset_flag", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("final_flag", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("challenge_match_flag", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("high_view_flag", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("high_gift_flag", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("view_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("gift_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("match_weight", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("notable_moments_json", sa.JSON(), nullable=False),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["away_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_id"], ["club_challenges.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["home_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rivalry_id"], ["rivalry_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_rivalry_match_history"),
        sa.UniqueConstraint("rivalry_id", "match_id", name="uq_rivalry_match_history_rivalry_match"),
    )
    op.create_index(op.f("ix_rivalry_match_history_rivalry_id"), "rivalry_match_history", ["rivalry_id"], unique=False)
    op.create_index(op.f("ix_rivalry_match_history_match_id"), "rivalry_match_history", ["match_id"], unique=False)
    op.create_index(op.f("ix_rivalry_match_history_competition_id"), "rivalry_match_history", ["competition_id"], unique=False)
    op.create_index(op.f("ix_rivalry_match_history_challenge_id"), "rivalry_match_history", ["challenge_id"], unique=False)

    op.create_table(
        "match_reaction_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("source_event_id", sa.String(length=36), nullable=True),
        sa.Column("challenge_id", sa.String(length=36), nullable=True),
        sa.Column("rivalry_profile_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("reaction_type", sa.String(length=32), nullable=False),
        sa.Column("reaction_label", sa.String(length=80), nullable=False),
        sa.Column("intensity_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=True),
        sa.Column("happened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["club_challenges.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rivalry_profile_id"], ["rivalry_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_event_id"], ["competition_match_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_match_reaction_events"),
        sa.UniqueConstraint("source_event_id", "reaction_type", name="uq_match_reaction_events_source_type"),
    )
    op.create_index(op.f("ix_match_reaction_events_match_id"), "match_reaction_events", ["match_id"], unique=False)
    op.create_index(op.f("ix_match_reaction_events_competition_id"), "match_reaction_events", ["competition_id"], unique=False)
    op.create_index(op.f("ix_match_reaction_events_source_event_id"), "match_reaction_events", ["source_event_id"], unique=False)
    op.create_index(op.f("ix_match_reaction_events_challenge_id"), "match_reaction_events", ["challenge_id"], unique=False)
    op.create_index(op.f("ix_match_reaction_events_rivalry_profile_id"), "match_reaction_events", ["rivalry_profile_id"], unique=False)
    op.create_index(op.f("ix_match_reaction_events_club_id"), "match_reaction_events", ["club_id"], unique=False)
    op.create_index(op.f("ix_match_reaction_events_reaction_type"), "match_reaction_events", ["reaction_type"], unique=False)

    op.create_table(
        "challenge_share_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("challenge_id", sa.String(length=36), nullable=False),
        sa.Column("link_id", sa.String(length=36), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("source_platform", sa.String(length=48), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["challenge_id"], ["club_challenges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["link_id"], ["club_challenge_links.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_challenge_share_events"),
    )
    op.create_index(op.f("ix_challenge_share_events_challenge_id"), "challenge_share_events", ["challenge_id"], unique=False)
    op.create_index(op.f("ix_challenge_share_events_link_id"), "challenge_share_events", ["link_id"], unique=False)
    op.create_index(op.f("ix_challenge_share_events_actor_user_id"), "challenge_share_events", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_challenge_share_events_event_type"), "challenge_share_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_challenge_share_events_source_platform"), "challenge_share_events", ["source_platform"], unique=False)
    op.create_index(op.f("ix_challenge_share_events_country_code"), "challenge_share_events", ["country_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_challenge_share_events_country_code"), table_name="challenge_share_events")
    op.drop_index(op.f("ix_challenge_share_events_source_platform"), table_name="challenge_share_events")
    op.drop_index(op.f("ix_challenge_share_events_event_type"), table_name="challenge_share_events")
    op.drop_index(op.f("ix_challenge_share_events_actor_user_id"), table_name="challenge_share_events")
    op.drop_index(op.f("ix_challenge_share_events_link_id"), table_name="challenge_share_events")
    op.drop_index(op.f("ix_challenge_share_events_challenge_id"), table_name="challenge_share_events")
    op.drop_table("challenge_share_events")

    op.drop_index(op.f("ix_match_reaction_events_reaction_type"), table_name="match_reaction_events")
    op.drop_index(op.f("ix_match_reaction_events_club_id"), table_name="match_reaction_events")
    op.drop_index(op.f("ix_match_reaction_events_rivalry_profile_id"), table_name="match_reaction_events")
    op.drop_index(op.f("ix_match_reaction_events_challenge_id"), table_name="match_reaction_events")
    op.drop_index(op.f("ix_match_reaction_events_source_event_id"), table_name="match_reaction_events")
    op.drop_index(op.f("ix_match_reaction_events_competition_id"), table_name="match_reaction_events")
    op.drop_index(op.f("ix_match_reaction_events_match_id"), table_name="match_reaction_events")
    op.drop_table("match_reaction_events")

    op.drop_index(op.f("ix_rivalry_match_history_challenge_id"), table_name="rivalry_match_history")
    op.drop_index(op.f("ix_rivalry_match_history_competition_id"), table_name="rivalry_match_history")
    op.drop_index(op.f("ix_rivalry_match_history_match_id"), table_name="rivalry_match_history")
    op.drop_index(op.f("ix_rivalry_match_history_rivalry_id"), table_name="rivalry_match_history")
    op.drop_table("rivalry_match_history")

    op.drop_index(op.f("ix_rivalry_profiles_club_b_id"), table_name="rivalry_profiles")
    op.drop_index(op.f("ix_rivalry_profiles_club_a_id"), table_name="rivalry_profiles")
    op.drop_table("rivalry_profiles")

    op.drop_index(op.f("ix_club_identity_metrics_club_id"), table_name="club_identity_metrics")
    op.drop_table("club_identity_metrics")

    op.drop_index(op.f("ix_club_challenge_links_link_code"), table_name="club_challenge_links")
    op.drop_index(op.f("ix_club_challenge_links_created_by_user_id"), table_name="club_challenge_links")
    op.drop_index(op.f("ix_club_challenge_links_challenge_id"), table_name="club_challenge_links")
    op.drop_table("club_challenge_links")

    op.drop_index(op.f("ix_club_challenge_responses_responder_user_id"), table_name="club_challenge_responses")
    op.drop_index(op.f("ix_club_challenge_responses_responding_club_id"), table_name="club_challenge_responses")
    op.drop_index(op.f("ix_club_challenge_responses_challenge_id"), table_name="club_challenge_responses")
    op.drop_table("club_challenge_responses")

    op.drop_index(op.f("ix_club_challenges_scheduled_for"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_status"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_city_name"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_region_name"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_country_code"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_visibility"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_slug"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_winner_club_id"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_accepted_club_id"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_linked_match_id"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_competition_id"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_issuing_user_id"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_target_club_id"), table_name="club_challenges")
    op.drop_index(op.f("ix_club_challenges_issuing_club_id"), table_name="club_challenges")
    op.drop_table("club_challenges")
