"""regen foundation and club geography

Revision ID: 20260315_0004
Revises: 20260315_0003
Create Date: 2026-03-15 17:45:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260315_0004"
down_revision = "20260315_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("club_profiles") as batch_op:
        batch_op.add_column(sa.Column("country_code", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("region_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("city_name", sa.String(length=120), nullable=True))
        batch_op.create_index("ix_club_profiles_country_code", ["country_code"], unique=False)

    op.create_table(
        "regen_profiles",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("linked_unique_card_id", sa.String(length=36), nullable=False),
        sa.Column("generated_for_club_id", sa.String(length=36), nullable=False),
        sa.Column("birth_country_code", sa.String(length=8), nullable=False),
        sa.Column("birth_region", sa.String(length=120), nullable=True),
        sa.Column("birth_city", sa.String(length=120), nullable=True),
        sa.Column("primary_position", sa.String(length=40), nullable=False),
        sa.Column("secondary_positions_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_gsi", sa.Integer(), nullable=False),
        sa.Column("current_ability_range_json", sa.JSON(), nullable=False),
        sa.Column("potential_range_json", sa.JSON(), nullable=False),
        sa.Column("scout_confidence", sa.String(length=32), nullable=False),
        sa.Column("generation_source", sa.String(length=32), nullable=False),
        sa.Column("is_special_lineage", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("club_quality_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["generated_for_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_unique_card_id"], ["player_cards.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("linked_unique_card_id", name="uq_regen_profiles_linked_unique_card_id"),
        sa.UniqueConstraint("player_id", name="uq_regen_profiles_player_id"),
        sa.UniqueConstraint("regen_id", name="uq_regen_profiles_regen_id"),
    )
    op.create_index("ix_regen_profiles_generated_for_club_id", "regen_profiles", ["generated_for_club_id"], unique=False)
    op.create_index("ix_regen_profiles_generation_source", "regen_profiles", ["generation_source"], unique=False)
    op.create_index("ix_regen_profiles_regen_id", "regen_profiles", ["regen_id"], unique=False)

    op.create_table(
        "regen_personality_profiles",
        sa.Column("regen_profile_id", sa.String(length=36), nullable=False),
        sa.Column("temperament", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("leadership", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("ambition", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("loyalty", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("work_rate", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("flair", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("resilience", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("personality_tags_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_profile_id", name="uq_regen_personality_profiles_regen_profile_id"),
    )

    op.create_table(
        "regen_origin_metadata",
        sa.Column("regen_profile_id", sa.String(length=36), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("region_name", sa.String(length=120), nullable=True),
        sa.Column("city_name", sa.String(length=120), nullable=True),
        sa.Column("hometown_club_affinity", sa.String(length=120), nullable=True),
        sa.Column("ethnolinguistic_profile", sa.String(length=80), nullable=True),
        sa.Column("religion_naming_pattern", sa.String(length=80), nullable=True),
        sa.Column("urbanicity", sa.String(length=32), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_profile_id", name="uq_regen_origin_metadata_regen_profile_id"),
    )

    op.create_table(
        "regen_generation_events",
        sa.Column("regen_profile_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("generation_source", sa.String(length=32), nullable=False),
        sa.Column("season_label", sa.String(length=32), nullable=False),
        sa.Column("event_status", sa.String(length=32), nullable=False, server_default="generated"),
        sa.Column("probability_score", sa.Float(), nullable=True),
        sa.Column("quality_roll", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_generation_events_regen_profile_id", "regen_generation_events", ["regen_profile_id"], unique=False)
    op.create_index("ix_regen_generation_events_club_id", "regen_generation_events", ["club_id"], unique=False)
    op.create_index("ix_regen_generation_events_season_label", "regen_generation_events", ["season_label"], unique=False)

    op.create_table(
        "academy_intake_batches",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("season_label", sa.String(length=32), nullable=False),
        sa.Column("intake_size", sa.Integer(), nullable=False),
        sa.Column("academy_quality_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="generated"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "season_label", name="uq_academy_intake_batches_club_season"),
    )
    op.create_index("ix_academy_intake_batches_club_id", "academy_intake_batches", ["club_id"], unique=False)

    op.create_table(
        "academy_candidates",
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("regen_profile_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("nationality_code", sa.String(length=8), nullable=False),
        sa.Column("birth_region", sa.String(length=120), nullable=True),
        sa.Column("birth_city", sa.String(length=120), nullable=True),
        sa.Column("primary_position", sa.String(length=40), nullable=False),
        sa.Column("secondary_position", sa.String(length=40), nullable=True),
        sa.Column("current_ability_range_json", sa.JSON(), nullable=False),
        sa.Column("potential_range_json", sa.JSON(), nullable=False),
        sa.Column("scout_confidence", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="academy_candidate"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["academy_intake_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_profile_id", name="uq_academy_candidates_regen_profile_id"),
    )
    op.create_index("ix_academy_candidates_batch_id", "academy_candidates", ["batch_id"], unique=False)
    op.create_index("ix_academy_candidates_club_id", "academy_candidates", ["club_id"], unique=False)

    op.create_table(
        "regen_visual_profiles",
        sa.Column("regen_profile_id", sa.String(length=36), nullable=False),
        sa.Column("portrait_seed", sa.String(length=64), nullable=False),
        sa.Column("skin_tone", sa.String(length=32), nullable=True),
        sa.Column("hair_profile", sa.String(length=64), nullable=True),
        sa.Column("accessory_profile_json", sa.JSON(), nullable=False),
        sa.Column("kit_style", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["regen_profile_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_profile_id", name="uq_regen_visual_profiles_regen_profile_id"),
    )


def downgrade() -> None:
    op.drop_table("regen_visual_profiles")
    op.drop_index("ix_academy_candidates_club_id", table_name="academy_candidates")
    op.drop_index("ix_academy_candidates_batch_id", table_name="academy_candidates")
    op.drop_table("academy_candidates")
    op.drop_index("ix_academy_intake_batches_club_id", table_name="academy_intake_batches")
    op.drop_table("academy_intake_batches")
    op.drop_index("ix_regen_generation_events_season_label", table_name="regen_generation_events")
    op.drop_index("ix_regen_generation_events_club_id", table_name="regen_generation_events")
    op.drop_index("ix_regen_generation_events_regen_profile_id", table_name="regen_generation_events")
    op.drop_table("regen_generation_events")
    op.drop_table("regen_origin_metadata")
    op.drop_table("regen_personality_profiles")
    op.drop_index("ix_regen_profiles_regen_id", table_name="regen_profiles")
    op.drop_index("ix_regen_profiles_generation_source", table_name="regen_profiles")
    op.drop_index("ix_regen_profiles_generated_for_club_id", table_name="regen_profiles")
    op.drop_table("regen_profiles")

    with op.batch_alter_table("club_profiles") as batch_op:
        batch_op.drop_index("ix_club_profiles_country_code")
        batch_op.drop_column("city_name")
        batch_op.drop_column("region_name")
        batch_op.drop_column("country_code")
