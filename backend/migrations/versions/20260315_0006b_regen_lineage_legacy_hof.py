"""regen lineage, awards, hall of fame, and legacy records

Revision ID: 20260315_0006b
Revises: 20260315_0005
Create Date: 2026-03-15 23:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260315_0006b"
down_revision = "20260315_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regen_lineage_profiles",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), nullable=False),
        sa.Column("related_legend_type", sa.String(length=64), nullable=False),
        sa.Column("related_legend_ref_id", sa.String(length=64), nullable=False),
        sa.Column("lineage_country_code", sa.String(length=8), nullable=False),
        sa.Column("lineage_hometown_code", sa.String(length=120), nullable=True),
        sa.Column("is_owner_son", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_retired_regen_lineage", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_real_legend_lineage", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_celebrity_lineage", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_celebrity_licensed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("lineage_tier", sa.String(length=32), nullable=False, server_default="rare"),
        sa.Column("narrative_text", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_id", name="uq_regen_lineage_profiles_regen_id"),
    )
    op.create_index(
        "ix_regen_lineage_profiles_relationship_type",
        "regen_lineage_profiles",
        ["relationship_type"],
        unique=False,
    )
    op.create_index(
        "ix_regen_lineage_profiles_related_legend_type",
        "regen_lineage_profiles",
        ["related_legend_type"],
        unique=False,
    )

    op.create_table(
        "regen_relationship_tags",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), nullable=True),
        sa.Column("related_entity_type", sa.String(length=64), nullable=True),
        sa.Column("related_entity_id", sa.String(length=64), nullable=True),
        sa.Column("display_text", sa.String(length=180), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_relationship_tags_regen_id", "regen_relationship_tags", ["regen_id"], unique=False)
    op.create_index("ix_regen_relationship_tags_tag", "regen_relationship_tags", ["tag"], unique=False)

    op.create_table(
        "regen_awards",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("award_code", sa.String(length=80), nullable=False),
        sa.Column("award_name", sa.String(length=180), nullable=False),
        sa.Column("award_category", sa.String(length=80), nullable=True),
        sa.Column("season_label", sa.String(length=32), nullable=True),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("source_scope", sa.String(length=48), nullable=False, server_default="gtex"),
        sa.Column("impact_score", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_awards_regen_id", "regen_awards", ["regen_id"], unique=False)
    op.create_index("ix_regen_awards_award_code", "regen_awards", ["award_code"], unique=False)
    op.create_index("ix_regen_awards_awarded_at", "regen_awards", ["awarded_at"], unique=False)

    op.create_table(
        "club_hall_of_fame_entries",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("entry_category", sa.String(length=64), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("regen_id", sa.String(length=36), nullable=True),
        sa.Column("entry_label", sa.String(length=180), nullable=False),
        sa.Column("entry_rank", sa.Integer(), nullable=True),
        sa.Column("stat_line_json", sa.JSON(), nullable=False),
        sa.Column("era_label", sa.String(length=64), nullable=True),
        sa.Column("inducted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_scope", sa.String(length=48), nullable=False, server_default="manual"),
        sa.Column("narrative_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_club_hall_of_fame_entries_club_id",
        "club_hall_of_fame_entries",
        ["club_id"],
        unique=False,
    )
    op.create_index(
        "ix_club_hall_of_fame_entries_category",
        "club_hall_of_fame_entries",
        ["entry_category"],
        unique=False,
    )
    op.create_index(
        "ix_club_hall_of_fame_entries_player_id",
        "club_hall_of_fame_entries",
        ["player_id"],
        unique=False,
    )
    op.create_index(
        "ix_club_hall_of_fame_entries_regen_id",
        "club_hall_of_fame_entries",
        ["regen_id"],
        unique=False,
    )

    op.create_table(
        "regen_discovery_badges",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("badge_code", sa.String(length=80), nullable=False),
        sa.Column("badge_name", sa.String(length=180), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "regen_id",
            "club_id",
            "badge_code",
            name="uq_regen_discovery_badges_regen_club_code",
        ),
    )
    op.create_index(
        "ix_regen_discovery_badges_regen_id",
        "regen_discovery_badges",
        ["regen_id"],
        unique=False,
    )
    op.create_index(
        "ix_regen_discovery_badges_badge_code",
        "regen_discovery_badges",
        ["badge_code"],
        unique=False,
    )

    op.create_table(
        "regen_twins_group",
        sa.Column("twins_group_key", sa.String(length=64), nullable=False),
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("season_label", sa.String(length=32), nullable=False),
        sa.Column("visual_seed", sa.String(length=64), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_twins_group_key", "regen_twins_group", ["twins_group_key"], unique=False)
    op.create_index("ix_regen_twins_group_regen_id", "regen_twins_group", ["regen_id"], unique=False)

    op.create_table(
        "regen_legacy_records",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("retired_on", sa.Date(), nullable=True),
        sa.Column("appearances_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goals_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assists_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("awards_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("seasons_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("legacy_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("legacy_tier", sa.String(length=32), nullable=False, server_default="standard"),
        sa.Column("is_legend", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("narrative_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_id", name="uq_regen_legacy_records_regen_id"),
    )
    op.create_index("ix_regen_legacy_records_player_id", "regen_legacy_records", ["player_id"], unique=False)
    op.create_index("ix_regen_legacy_records_is_legend", "regen_legacy_records", ["is_legend"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_regen_legacy_records_is_legend", table_name="regen_legacy_records")
    op.drop_index("ix_regen_legacy_records_player_id", table_name="regen_legacy_records")
    op.drop_table("regen_legacy_records")
    op.drop_index("ix_regen_twins_group_regen_id", table_name="regen_twins_group")
    op.drop_index("ix_regen_twins_group_key", table_name="regen_twins_group")
    op.drop_table("regen_twins_group")
    op.drop_index("ix_regen_discovery_badges_badge_code", table_name="regen_discovery_badges")
    op.drop_index("ix_regen_discovery_badges_regen_id", table_name="regen_discovery_badges")
    op.drop_table("regen_discovery_badges")
    op.drop_index("ix_club_hall_of_fame_entries_regen_id", table_name="club_hall_of_fame_entries")
    op.drop_index("ix_club_hall_of_fame_entries_player_id", table_name="club_hall_of_fame_entries")
    op.drop_index("ix_club_hall_of_fame_entries_category", table_name="club_hall_of_fame_entries")
    op.drop_index("ix_club_hall_of_fame_entries_club_id", table_name="club_hall_of_fame_entries")
    op.drop_table("club_hall_of_fame_entries")
    op.drop_index("ix_regen_awards_awarded_at", table_name="regen_awards")
    op.drop_index("ix_regen_awards_award_code", table_name="regen_awards")
    op.drop_index("ix_regen_awards_regen_id", table_name="regen_awards")
    op.drop_table("regen_awards")
    op.drop_index("ix_regen_relationship_tags_tag", table_name="regen_relationship_tags")
    op.drop_index("ix_regen_relationship_tags_regen_id", table_name="regen_relationship_tags")
    op.drop_table("regen_relationship_tags")
    op.drop_index("ix_regen_lineage_profiles_related_legend_type", table_name="regen_lineage_profiles")
    op.drop_index("ix_regen_lineage_profiles_relationship_type", table_name="regen_lineage_profiles")
    op.drop_table("regen_lineage_profiles")
