"""Add fan wars and Nations Cup tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0022_fan_wars_nations_cup"
down_revision = "20260317_0021_football_world_simulation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fan_war_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("profile_type", sa.String(length=24), nullable=False),
        sa.Column("entity_key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("country_name", sa.String(length=120), nullable=True),
        sa.Column("tagline", sa.String(length=255), nullable=True),
        sa.Column("scoring_config_json", sa.JSON(), nullable=False),
        sa.Column("rivalry_profile_ids_json", sa.JSON(), nullable=False),
        sa.Column("prestige_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_war_profiles"),
        sa.UniqueConstraint("entity_key", name="uq_fan_war_profiles_entity_key"),
        sa.UniqueConstraint("slug", name="uq_fan_war_profiles_slug"),
    )

    op.create_table(
        "country_creator_assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("represented_country_code", sa.String(length=8), nullable=False),
        sa.Column("represented_country_name", sa.String(length=120), nullable=False),
        sa.Column("eligible_country_codes_json", sa.JSON(), nullable=False),
        sa.Column("assignment_rule", sa.String(length=48), server_default=sa.text("'admin_approved'"), nullable=False),
        sa.Column("allow_admin_override", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("assigned_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_country_creator_assignments"),
        sa.UniqueConstraint("creator_profile_id", name="uq_country_creator_assignments_creator_profile_id"),
    )

    op.create_table(
        "nations_cup_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("assignment_id", sa.String(length=36), nullable=True),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("country_name", sa.String(length=120), nullable=False),
        sa.Column("seed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("group_key", sa.String(length=24), nullable=True),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'qualified'"), nullable=False),
        sa.Column("fan_energy_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("country_prestige_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("creator_prestige_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("fanbase_prestige_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("advanced_to_knockout", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("record_summary_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["assignment_id"], ["country_creator_assignments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_nations_cup_entries"),
        sa.UniqueConstraint("competition_id", "country_code", name="uq_nations_cup_entries_competition_country"),
        sa.UniqueConstraint("competition_id", "creator_profile_id", name="uq_nations_cup_entries_competition_creator"),
    )

    op.create_table(
        "fan_war_points",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("nations_cup_entry_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=48), nullable=False),
        sa.Column("source_ref", sa.String(length=120), nullable=True),
        sa.Column("base_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("bonus_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("weighted_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("engagement_units", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("spend_amount_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("quality_multiplier_bps", sa.Integer(), server_default=sa.text("10000"), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("dedupe_key", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["nations_cup_entry_id"], ["nations_cup_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["profile_id"], ["fan_war_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_fan_war_points"),
        sa.UniqueConstraint("profile_id", "dedupe_key", name="uq_fan_war_points_profile_dedupe_key"),
    )

    op.create_table(
        "nations_cup_fan_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=36), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("watch_actions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("gift_actions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("prediction_actions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("tournament_actions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("creator_support_actions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("club_support_actions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("watch_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("gift_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("prediction_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("tournament_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("creator_support_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("club_support_points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_energy", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("contribution_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("unique_supporter_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entry_id"], ["nations_cup_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_nations_cup_fan_metrics"),
        sa.UniqueConstraint("competition_id", "entry_id", name="uq_nations_cup_fan_metrics_competition_entry"),
    )

    op.create_table(
        "fanbase_rankings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("board_type", sa.String(length=24), nullable=False),
        sa.Column("period_type", sa.String(length=24), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("profile_type", sa.String(length=24), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("points_total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("event_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("unique_supporters", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("movement", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["fan_war_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_fanbase_rankings"),
        sa.UniqueConstraint("board_type", "period_type", "window_start", "profile_id", name="uq_fanbase_rankings_window_profile"),
    )


def downgrade() -> None:
    op.drop_table("fanbase_rankings")
    op.drop_table("nations_cup_fan_metrics")
    op.drop_table("fan_war_points")
    op.drop_table("nations_cup_entries")
    op.drop_table("country_creator_assignments")
    op.drop_table("fan_war_profiles")
