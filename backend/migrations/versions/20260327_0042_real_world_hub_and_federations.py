"""Add real-world projection hub and federation governance tables.

Revision ID: 20260327_0042_real_world_hub_and_federations
Revises: 20260327_0041_merge_transfer_market_and_universe_heads
Create Date: 2026-03-27 20:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0042_real_world_hub_and_federations"
down_revision = "20260327_0041_merge_transfer_market_and_universe_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "real_data_providers",
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("api_endpoint", sa.String(length=255), nullable=False),
        sa.Column("refresh_interval", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("normalization_profile_version", sa.String(length=32), nullable=False, server_default="real_player_v1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_real_data_providers_name"),
    )
    op.create_index("ix_real_data_providers_is_active", "real_data_providers", ["is_active"], unique=False)
    op.create_index("ix_real_data_providers_last_sync_at", "real_data_providers", ["last_sync_at"], unique=False)

    op.create_table(
        "real_world_competitions",
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("external_key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("country_name", sa.String(length=120), nullable=True),
        sa.Column("competition_type", sa.String(length=32), nullable=False, server_default="league"),
        sa.Column("gtex_competition_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["gtex_competition_id"], ["ingestion_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["provider_id"], ["real_data_providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "external_key", name="uq_real_world_competitions_provider_key"),
    )
    op.create_index("ix_real_world_competitions_provider_id", "real_world_competitions", ["provider_id"], unique=False)
    op.create_index("ix_real_world_competitions_name", "real_world_competitions", ["name"], unique=False)

    op.create_table(
        "real_world_clubs",
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("external_key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("country_name", sa.String(length=120), nullable=True),
        sa.Column("gtex_club_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["competition_id"], ["real_world_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["gtex_club_id"], ["ingestion_clubs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["provider_id"], ["real_data_providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "external_key", name="uq_real_world_clubs_provider_key"),
    )
    op.create_index("ix_real_world_clubs_provider_id", "real_world_clubs", ["provider_id"], unique=False)
    op.create_index("ix_real_world_clubs_name", "real_world_clubs", ["name"], unique=False)
    op.create_index("ix_real_world_clubs_competition_id", "real_world_clubs", ["competition_id"], unique=False)

    op.create_table(
        "real_players",
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("external_key", sa.String(length=128), nullable=False),
        sa.Column("gtex_player_id", sa.String(length=36), nullable=True),
        sa.Column("real_club_id", sa.String(length=36), nullable=True),
        sa.Column("real_competition_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("nationality", sa.String(length=120), nullable=True),
        sa.Column("position", sa.String(length=64), nullable=True),
        sa.Column("player_origin", sa.String(length=24), nullable=False, server_default="real_player"),
        sa.Column("real_world_rating", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("normalized_rating", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("attributes_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("injury_status", sa.String(length=64), nullable=True),
        sa.Column("soft_injury_impact", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["gtex_player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["provider_id"], ["real_data_providers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["real_club_id"], ["real_world_clubs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["real_competition_id"], ["real_world_competitions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "external_key", name="uq_real_players_provider_key"),
    )
    op.create_index("ix_real_players_provider_id", "real_players", ["provider_id"], unique=False)
    op.create_index("ix_real_players_gtex_player_id", "real_players", ["gtex_player_id"], unique=False)
    op.create_index("ix_real_players_position", "real_players", ["position"], unique=False)
    op.create_index("ix_real_players_real_world_rating", "real_players", ["real_world_rating"], unique=False)
    op.create_index("ix_real_players_last_updated", "real_players", ["last_updated"], unique=False)

    op.create_table(
        "reality_mode_settings",
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=24), nullable=False, server_default="hybrid"),
        sa.Column("enable_real_world_events", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enable_soft_injuries", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enable_transfer_mirror", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", name="uq_reality_mode_settings_owner_user_id"),
    )

    op.create_table(
        "real_data_sync_jobs",
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entities_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("entities_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("entities_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["provider_id"], ["real_data_providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_real_data_sync_jobs_provider_id", "real_data_sync_jobs", ["provider_id"], unique=False)
    op.create_index("ix_real_data_sync_jobs_status", "real_data_sync_jobs", ["status"], unique=False)
    op.create_index("ix_real_data_sync_jobs_started_at", "real_data_sync_jobs", ["started_at"], unique=False)

    op.create_table(
        "federations",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("structure_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("rules_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("competitions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("members_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("reputation_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("ranking_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("treasury_balance", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("audience_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("default_reality_mode", sa.String(length=24), nullable=False, server_default="hybrid"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_federations_name"),
    )
    op.create_index("ix_federations_owner_user_id", "federations", ["owner_user_id"], unique=False)
    op.create_index("ix_federations_ranking_score", "federations", ["ranking_score"], unique=False)

    op.create_table(
        "federation_leagues",
        sa.Column("federation_id", sa.String(length=36), nullable=False),
        sa.Column("linked_competition_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("competition_type", sa.String(length=24), nullable=False, server_default="league"),
        sa.Column("format", sa.String(length=32), nullable=False),
        sa.Column("divisions_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("promotion_relegation_rules_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("entry_requirements_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("governance_rules_override_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("season_label", sa.String(length=48), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["federation_id"], ["federations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("federation_id", "name", name="uq_federation_leagues_federation_name"),
    )
    op.create_index("ix_federation_leagues_federation_id", "federation_leagues", ["federation_id"], unique=False)
    op.create_index("ix_federation_leagues_linked_competition_id", "federation_leagues", ["linked_competition_id"], unique=False)

    op.create_table(
        "federation_memberships",
        sa.Column("federation_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="member_club"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("entry_requirements_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["federation_id"], ["federations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("federation_id", "club_id", name="uq_federation_memberships_federation_club"),
    )
    op.create_index("ix_federation_memberships_federation_id", "federation_memberships", ["federation_id"], unique=False)
    op.create_index("ix_federation_memberships_status", "federation_memberships", ["status"], unique=False)

    op.create_table(
        "federation_proposals",
        sa.Column("federation_id", sa.String(length=36), nullable=False),
        sa.Column("league_id", sa.String(length=36), nullable=True),
        sa.Column("proposer_user_id", sa.String(length=36), nullable=False),
        sa.Column("proposal_type", sa.String(length=48), nullable=False, server_default="rule_change"),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("voting_starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("voting_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("yes_votes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_votes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("abstain_votes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["federation_id"], ["federations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["league_id"], ["federation_leagues.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proposer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_federation_proposals_federation_id", "federation_proposals", ["federation_id"], unique=False)
    op.create_index("ix_federation_proposals_status", "federation_proposals", ["status"], unique=False)
    op.create_index("ix_federation_proposals_voting_ends_at", "federation_proposals", ["voting_ends_at"], unique=False)

    op.create_table(
        "federation_votes",
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("federation_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("vote_type", sa.String(length=24), nullable=False, server_default="yes"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["federation_id"], ["federations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_id"], ["federation_proposals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "user_id", name="uq_federation_votes_proposal_user"),
    )
    op.create_index("ix_federation_votes_federation_id", "federation_votes", ["federation_id"], unique=False)

    op.create_table(
        "federation_sanctions",
        sa.Column("federation_id", sa.String(length=36), nullable=False),
        sa.Column("league_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("applied_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("sanction_type", sa.String(length=32), nullable=False, server_default="fine"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("fine_amount", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("points_deduction", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("suspension_matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["applied_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["federation_id"], ["federations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["league_id"], ["federation_leagues.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_federation_sanctions_federation_id", "federation_sanctions", ["federation_id"], unique=False)
    op.create_index("ix_federation_sanctions_club_id", "federation_sanctions", ["club_id"], unique=False)
    op.create_index("ix_federation_sanctions_player_id", "federation_sanctions", ["player_id"], unique=False)

    op.create_table(
        "federation_treasury_entries",
        sa.Column("federation_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=120), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("federation_share", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("club_distribution_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["federation_id"], ["federations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("federation_id", "source_type", "source_reference", name="uq_federation_treasury_source"),
    )
    op.create_index("ix_federation_treasury_entries_federation_id", "federation_treasury_entries", ["federation_id"], unique=False)

    op.create_table(
        "federation_narrative_snapshots",
        sa.Column("federation_id", sa.String(length=36), nullable=False),
        sa.Column("narrative_type", sa.String(length=48), nullable=False),
        sa.Column("headline", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["federation_id"], ["federations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_federation_narrative_snapshots_federation_id", "federation_narrative_snapshots", ["federation_id"], unique=False)
    op.create_index("ix_federation_narrative_snapshots_narrative_type", "federation_narrative_snapshots", ["narrative_type"], unique=False)

    op.create_table(
        "federation_rule_audits",
        sa.Column("federation_id", sa.String(length=36), nullable=False),
        sa.Column("league_id", sa.String(length=36), nullable=True),
        sa.Column("action_type", sa.String(length=48), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="passed"),
        sa.Column("violation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("violations_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["federation_id"], ["federations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["league_id"], ["federation_leagues.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_federation_rule_audits_federation_id", "federation_rule_audits", ["federation_id"], unique=False)
    op.create_index("ix_federation_rule_audits_status", "federation_rule_audits", ["status"], unique=False)
    op.create_index("ix_federation_rule_audits_checked_at", "federation_rule_audits", ["checked_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_federation_rule_audits_checked_at", table_name="federation_rule_audits")
    op.drop_index("ix_federation_rule_audits_status", table_name="federation_rule_audits")
    op.drop_index("ix_federation_rule_audits_federation_id", table_name="federation_rule_audits")
    op.drop_table("federation_rule_audits")

    op.drop_index("ix_federation_narrative_snapshots_narrative_type", table_name="federation_narrative_snapshots")
    op.drop_index("ix_federation_narrative_snapshots_federation_id", table_name="federation_narrative_snapshots")
    op.drop_table("federation_narrative_snapshots")

    op.drop_index("ix_federation_treasury_entries_federation_id", table_name="federation_treasury_entries")
    op.drop_table("federation_treasury_entries")

    op.drop_index("ix_federation_sanctions_player_id", table_name="federation_sanctions")
    op.drop_index("ix_federation_sanctions_club_id", table_name="federation_sanctions")
    op.drop_index("ix_federation_sanctions_federation_id", table_name="federation_sanctions")
    op.drop_table("federation_sanctions")

    op.drop_index("ix_federation_votes_federation_id", table_name="federation_votes")
    op.drop_table("federation_votes")

    op.drop_index("ix_federation_proposals_voting_ends_at", table_name="federation_proposals")
    op.drop_index("ix_federation_proposals_status", table_name="federation_proposals")
    op.drop_index("ix_federation_proposals_federation_id", table_name="federation_proposals")
    op.drop_table("federation_proposals")

    op.drop_index("ix_federation_memberships_status", table_name="federation_memberships")
    op.drop_index("ix_federation_memberships_federation_id", table_name="federation_memberships")
    op.drop_table("federation_memberships")

    op.drop_index("ix_federation_leagues_linked_competition_id", table_name="federation_leagues")
    op.drop_index("ix_federation_leagues_federation_id", table_name="federation_leagues")
    op.drop_table("federation_leagues")

    op.drop_index("ix_federations_ranking_score", table_name="federations")
    op.drop_index("ix_federations_owner_user_id", table_name="federations")
    op.drop_table("federations")

    op.drop_index("ix_real_data_sync_jobs_started_at", table_name="real_data_sync_jobs")
    op.drop_index("ix_real_data_sync_jobs_status", table_name="real_data_sync_jobs")
    op.drop_index("ix_real_data_sync_jobs_provider_id", table_name="real_data_sync_jobs")
    op.drop_table("real_data_sync_jobs")

    op.drop_table("reality_mode_settings")

    op.drop_index("ix_real_players_last_updated", table_name="real_players")
    op.drop_index("ix_real_players_real_world_rating", table_name="real_players")
    op.drop_index("ix_real_players_position", table_name="real_players")
    op.drop_index("ix_real_players_gtex_player_id", table_name="real_players")
    op.drop_index("ix_real_players_provider_id", table_name="real_players")
    op.drop_table("real_players")

    op.drop_index("ix_real_world_clubs_competition_id", table_name="real_world_clubs")
    op.drop_index("ix_real_world_clubs_name", table_name="real_world_clubs")
    op.drop_index("ix_real_world_clubs_provider_id", table_name="real_world_clubs")
    op.drop_table("real_world_clubs")

    op.drop_index("ix_real_world_competitions_name", table_name="real_world_competitions")
    op.drop_index("ix_real_world_competitions_provider_id", table_name="real_world_competitions")
    op.drop_table("real_world_competitions")

    op.drop_index("ix_real_data_providers_last_sync_at", table_name="real_data_providers")
    op.drop_index("ix_real_data_providers_is_active", table_name="real_data_providers")
    op.drop_table("real_data_providers")
