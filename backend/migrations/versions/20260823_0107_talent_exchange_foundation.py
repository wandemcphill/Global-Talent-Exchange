"""Global Talent Exchange foundation: profiles, ranking lineage, signals,
verification ladder, scout shortlists and moderation audit.

Additive only. No existing table is altered and no economic table is touched:
`value_engine` remains the pricing authority and this migration introduces no
write path into it.

Revision ID: 20260823_0107_talent_exchange_foundation
Revises: 20260724_0106_player_potential
Create Date: 2026-08-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260823_0107_talent_exchange_foundation"
down_revision = "20260724_0106_player_potential"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "talent_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "player_id",
            sa.String(length=36),
            sa.ForeignKey("ingestion_players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("headline", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("position_code", sa.String(length=8), nullable=True),
        sa.Column("secondary_positions_json", sa.JSON(), nullable=False),
        sa.Column("tactical_roles_json", sa.JSON(), nullable=False),
        sa.Column("preferred_foot", sa.String(length=8), nullable=True),
        sa.Column("position_index", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("tactical_role_index", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("signal_index", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("age_years", sa.Integer(), nullable=True),
        sa.Column("nationality_code", sa.String(length=8), nullable=True),
        sa.Column("nationality_name", sa.String(length=96), nullable=True),
        sa.Column("location_country_code", sa.String(length=8), nullable=True),
        sa.Column("location_region", sa.String(length=120), nullable=True),
        sa.Column("location_city", sa.String(length=120), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Integer(), nullable=True),
        sa.Column("technical_attributes_json", sa.JSON(), nullable=False),
        sa.Column("tactical_attributes_json", sa.JSON(), nullable=False),
        sa.Column("physical_attributes_json", sa.JSON(), nullable=False),
        sa.Column("availability_status", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("availability_note", sa.String(length=240), nullable=True),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("experience_years", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("current_club_name", sa.String(length=160), nullable=True),
        sa.Column("current_competition_name", sa.String(length=160), nullable=True),
        sa.Column("verification_tier", sa.String(length=32), nullable=False, server_default="unverified"),
        sa.Column("verification_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visibility_state", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("moderation_state", sa.String(length=32), nullable=False, server_default="clear"),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("featured_rank", sa.Integer(), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("form_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("consistency_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("competition_level_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("ranking_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("ranking_sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ranking_computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ranking_config_version", sa.String(length=32), nullable=True),
        sa.Column("ranking_inputs_digest", sa.String(length=64), nullable=True),
        sa.Column("active_signal_codes_json", sa.JSON(), nullable=False),
        sa.Column("portfolio_json", sa.JSON(), nullable=False),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("suspension_reason", sa.String(length=240), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("player_id", name="uq_talent_profiles_player_id"),
    )
    op.create_index("ix_talent_profiles_display_name", "talent_profiles", ["display_name"])
    op.create_index("ix_talent_profiles_featured", "talent_profiles", ["is_featured", "featured_rank"])
    op.create_index("ix_talent_profiles_moderation_state", "talent_profiles", ["moderation_state"])
    op.create_index("ix_talent_profiles_owner_user_id", "talent_profiles", ["owner_user_id"])
    op.create_index("ix_talent_profiles_visibility_age", "talent_profiles", ["visibility_state", "age_years"])
    op.create_index(
        "ix_talent_profiles_visibility_availability",
        "talent_profiles",
        ["visibility_state", "availability_status"],
    )
    op.create_index(
        "ix_talent_profiles_visibility_country",
        "talent_profiles",
        ["visibility_state", "nationality_code"],
    )
    op.create_index(
        "ix_talent_profiles_visibility_position",
        "talent_profiles",
        ["visibility_state", "position_code"],
    )
    op.create_index(
        "ix_talent_profiles_visibility_score",
        "talent_profiles",
        ["visibility_state", "composite_score"],
    )
    op.create_index(
        "ix_talent_profiles_visibility_verification",
        "talent_profiles",
        ["visibility_state", "verification_tier"],
    )

    op.create_table(
        "talent_ranking_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "profile_id",
            sa.String(length=36),
            sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            sa.String(length=36),
            sa.ForeignKey("ingestion_players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("config_version", sa.String(length=32), nullable=False),
        sa.Column("composite_score", sa.Float(), nullable=False),
        sa.Column("base_score", sa.Float(), nullable=False),
        sa.Column("adjustments_total", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("components_json", sa.JSON(), nullable=False),
        sa.Column("adjustments_json", sa.JSON(), nullable=False),
        sa.Column("signals_json", sa.JSON(), nullable=False),
        sa.Column("inputs_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "player_id",
            "as_of",
            "config_version",
            name="uq_talent_ranking_snapshots_player_asof_config",
        ),
    )
    op.create_index("ix_talent_ranking_snapshots_as_of", "talent_ranking_snapshots", ["as_of"])
    op.create_index("ix_talent_ranking_snapshots_inputs_digest", "talent_ranking_snapshots", ["inputs_digest"])
    op.create_index("ix_talent_ranking_snapshots_profile_id", "talent_ranking_snapshots", ["profile_id"])

    op.create_table(
        "talent_signal_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "profile_id",
            sa.String(length=36),
            sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            sa.String(length=36),
            sa.ForeignKey("ingestion_players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("signal_code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("polarity", sa.String(length=16), nullable=False, server_default="positive"),
        sa.Column("strength", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("config_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("player_id", "signal_code", "as_of", name="uq_talent_signal_records_player_code_asof"),
    )
    op.create_index("ix_talent_signal_records_as_of", "talent_signal_records", ["as_of"])
    op.create_index("ix_talent_signal_records_code", "talent_signal_records", ["signal_code"])
    op.create_index("ix_talent_signal_records_profile_id", "talent_signal_records", ["profile_id"])

    op.create_table(
        "talent_verification_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "profile_id",
            sa.String(length=36),
            sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            sa.String(length=36),
            sa.ForeignKey("ingestion_players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False, server_default="granted"),
        sa.Column("evidence_kind", sa.String(length=64), nullable=True),
        sa.Column("evidence_reference", sa.String(length=120), nullable=True),
        sa.Column(
            "decided_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_talent_verification_records_decision", "talent_verification_records", ["decision"])
    op.create_index(
        "ix_talent_verification_records_player_tier",
        "talent_verification_records",
        ["player_id", "tier"],
    )
    op.create_index("ix_talent_verification_records_profile_id", "talent_verification_records", ["profile_id"])

    op.create_table(
        "talent_shortlists",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=400), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_user_id", "name", name="uq_talent_shortlists_owner_name"),
    )
    op.create_index("ix_talent_shortlists_club_id", "talent_shortlists", ["club_id"])
    op.create_index("ix_talent_shortlists_owner_user_id", "talent_shortlists", ["owner_user_id"])

    op.create_table(
        "talent_shortlist_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "shortlist_id",
            sa.String(length=36),
            sa.ForeignKey("talent_shortlists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            sa.String(length=36),
            sa.ForeignKey("ingestion_players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "added_by_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="watching"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("score_at_add", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("shortlist_id", "player_id", name="uq_talent_shortlist_entries_list_player"),
    )
    op.create_index("ix_talent_shortlist_entries_player_id", "talent_shortlist_entries", ["player_id"])
    op.create_index("ix_talent_shortlist_entries_status", "talent_shortlist_entries", ["status"])

    op.create_table(
        "talent_moderation_actions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "profile_id",
            sa.String(length=36),
            sa.ForeignKey("talent_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column(
            "actor_user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column("reason", sa.String(length=400), nullable=True),
        sa.Column("before_json", sa.JSON(), nullable=False),
        sa.Column("after_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_talent_moderation_actions_action", "talent_moderation_actions", ["action"])
    op.create_index("ix_talent_moderation_actions_actor", "talent_moderation_actions", ["actor_user_id"])
    op.create_index("ix_talent_moderation_actions_player_id", "talent_moderation_actions", ["player_id"])
    op.create_index("ix_talent_moderation_actions_profile_id", "talent_moderation_actions", ["profile_id"])


def downgrade() -> None:
    for index_name, table_name in (
        ("ix_talent_moderation_actions_profile_id", "talent_moderation_actions"),
        ("ix_talent_moderation_actions_player_id", "talent_moderation_actions"),
        ("ix_talent_moderation_actions_actor", "talent_moderation_actions"),
        ("ix_talent_moderation_actions_action", "talent_moderation_actions"),
        ("ix_talent_shortlist_entries_status", "talent_shortlist_entries"),
        ("ix_talent_shortlist_entries_player_id", "talent_shortlist_entries"),
        ("ix_talent_shortlists_owner_user_id", "talent_shortlists"),
        ("ix_talent_shortlists_club_id", "talent_shortlists"),
        ("ix_talent_verification_records_profile_id", "talent_verification_records"),
        ("ix_talent_verification_records_player_tier", "talent_verification_records"),
        ("ix_talent_verification_records_decision", "talent_verification_records"),
        ("ix_talent_signal_records_profile_id", "talent_signal_records"),
        ("ix_talent_signal_records_code", "talent_signal_records"),
        ("ix_talent_signal_records_as_of", "talent_signal_records"),
        ("ix_talent_ranking_snapshots_profile_id", "talent_ranking_snapshots"),
        ("ix_talent_ranking_snapshots_inputs_digest", "talent_ranking_snapshots"),
        ("ix_talent_ranking_snapshots_as_of", "talent_ranking_snapshots"),
        ("ix_talent_profiles_visibility_verification", "talent_profiles"),
        ("ix_talent_profiles_visibility_score", "talent_profiles"),
        ("ix_talent_profiles_visibility_position", "talent_profiles"),
        ("ix_talent_profiles_visibility_country", "talent_profiles"),
        ("ix_talent_profiles_visibility_availability", "talent_profiles"),
        ("ix_talent_profiles_visibility_age", "talent_profiles"),
        ("ix_talent_profiles_owner_user_id", "talent_profiles"),
        ("ix_talent_profiles_moderation_state", "talent_profiles"),
        ("ix_talent_profiles_featured", "talent_profiles"),
        ("ix_talent_profiles_display_name", "talent_profiles"),
    ):
        op.drop_index(index_name, table_name=table_name)

    op.drop_table("talent_moderation_actions")
    op.drop_table("talent_shortlist_entries")
    op.drop_table("talent_shortlists")
    op.drop_table("talent_verification_records")
    op.drop_table("talent_signal_records")
    op.drop_table("talent_ranking_snapshots")
    op.drop_table("talent_profiles")
