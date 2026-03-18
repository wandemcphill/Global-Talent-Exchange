"""Add football world culture and narrative scaffolding."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0021_football_world_simulation"
down_revision = "20260317_0020_club_sale_market"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "football_culture_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("culture_key", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("scope_type", sa.String(length=32), server_default=sa.text("'archetype'"), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("region_name", sa.String(length=120), nullable=True),
        sa.Column("city_name", sa.String(length=120), nullable=True),
        sa.Column("play_style_summary", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("supporter_traits_json", sa.JSON(), nullable=False),
        sa.Column("rivalry_themes_json", sa.JSON(), nullable=False),
        sa.Column("talent_archetypes_json", sa.JSON(), nullable=False),
        sa.Column("climate_notes", sa.String(length=255), server_default=sa.text("''"), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_football_culture_profiles"),
        sa.UniqueConstraint("culture_key", name="uq_football_culture_profiles_culture_key"),
    )
    op.create_index("ix_football_culture_profiles_active_scope", "football_culture_profiles", ["active", "scope_type"], unique=False)
    op.create_index("ix_football_culture_profiles_city_name", "football_culture_profiles", ["city_name"], unique=False)
    op.create_index("ix_football_culture_profiles_country_code", "football_culture_profiles", ["country_code"], unique=False)
    op.create_index("ix_football_culture_profiles_culture_key", "football_culture_profiles", ["culture_key"], unique=False)
    op.create_index("ix_football_culture_profiles_region_name", "football_culture_profiles", ["region_name"], unique=False)

    op.create_table(
        "club_world_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("culture_profile_id", sa.String(length=36), nullable=True),
        sa.Column("narrative_phase", sa.String(length=48), server_default=sa.text("'establishing_identity'"), nullable=False),
        sa.Column("supporter_mood", sa.String(length=48), server_default=sa.text("'hopeful'"), nullable=False),
        sa.Column("derby_heat_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("global_appeal_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("identity_keywords_json", sa.JSON(), nullable=False),
        sa.Column("transfer_identity_tags_json", sa.JSON(), nullable=False),
        sa.Column("fan_culture_tags_json", sa.JSON(), nullable=False),
        sa.Column("world_flags_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["culture_profile_id"], ["football_culture_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_world_profiles"),
        sa.UniqueConstraint("club_id", name="uq_club_world_profiles_club_id"),
    )
    op.create_index("ix_club_world_profiles_club_id", "club_world_profiles", ["club_id"], unique=False)
    op.create_index("ix_club_world_profiles_culture_profile_id", "club_world_profiles", ["culture_profile_id"], unique=False)

    op.create_table(
        "world_narrative_arcs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("scope_type", sa.String(length=32), server_default=sa.text("'global'"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("arc_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'active'"), nullable=False),
        sa.Column("visibility", sa.String(length=24), server_default=sa.text("'public'"), nullable=False),
        sa.Column("headline", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("importance_score", sa.Integer(), server_default=sa.text("50"), nullable=False),
        sa.Column("simulation_horizon", sa.String(length=32), server_default=sa.text("'seasonal'"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("impact_vectors_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_world_narrative_arcs"),
        sa.UniqueConstraint("slug", name="uq_world_narrative_arcs_slug"),
    )
    op.create_index("ix_world_narrative_arcs_club_id", "world_narrative_arcs", ["club_id"], unique=False)
    op.create_index("ix_world_narrative_arcs_club_status", "world_narrative_arcs", ["club_id", "status"], unique=False)
    op.create_index("ix_world_narrative_arcs_competition_id", "world_narrative_arcs", ["competition_id"], unique=False)
    op.create_index("ix_world_narrative_arcs_competition_status", "world_narrative_arcs", ["competition_id", "status"], unique=False)
    op.create_index("ix_world_narrative_arcs_slug", "world_narrative_arcs", ["slug"], unique=False)
    op.create_index("ix_world_narrative_arcs_status", "world_narrative_arcs", ["status"], unique=False)
    op.create_index("ix_world_narrative_arcs_visibility", "world_narrative_arcs", ["visibility"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_world_narrative_arcs_visibility", table_name="world_narrative_arcs")
    op.drop_index("ix_world_narrative_arcs_status", table_name="world_narrative_arcs")
    op.drop_index("ix_world_narrative_arcs_slug", table_name="world_narrative_arcs")
    op.drop_index("ix_world_narrative_arcs_competition_status", table_name="world_narrative_arcs")
    op.drop_index("ix_world_narrative_arcs_competition_id", table_name="world_narrative_arcs")
    op.drop_index("ix_world_narrative_arcs_club_status", table_name="world_narrative_arcs")
    op.drop_index("ix_world_narrative_arcs_club_id", table_name="world_narrative_arcs")
    op.drop_table("world_narrative_arcs")

    op.drop_index("ix_club_world_profiles_culture_profile_id", table_name="club_world_profiles")
    op.drop_index("ix_club_world_profiles_club_id", table_name="club_world_profiles")
    op.drop_table("club_world_profiles")

    op.drop_index("ix_football_culture_profiles_region_name", table_name="football_culture_profiles")
    op.drop_index("ix_football_culture_profiles_culture_key", table_name="football_culture_profiles")
    op.drop_index("ix_football_culture_profiles_country_code", table_name="football_culture_profiles")
    op.drop_index("ix_football_culture_profiles_city_name", table_name="football_culture_profiles")
    op.drop_index("ix_football_culture_profiles_active_scope", table_name="football_culture_profiles")
    op.drop_table("football_culture_profiles")
