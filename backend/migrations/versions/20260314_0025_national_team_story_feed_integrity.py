"""Add national team engine, story feed, and integrity engine."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260314_0025"
down_revision = "20260314_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "national_team_competitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("season_label", sa.String(length=64), nullable=False),
        sa.Column("region_type", sa.String(length=32), nullable=False, server_default=sa.text("'global'")),
        sa.Column("age_band", sa.String(length=16), nullable=False, server_default=sa.text("'senior'")),
        sa.Column("format_type", sa.String(length=32), nullable=False, server_default=sa.text("'cup'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_national_team_competitions_created_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_national_team_competitions"),
        sa.UniqueConstraint("key", name="uq_national_team_competitions_key"),
    )
    op.create_index("ix_national_team_competitions_key", "national_team_competitions", ["key"], unique=False)

    op.create_table(
        "national_team_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("country_code", sa.String(length=8), nullable=False),
        sa.Column("country_name", sa.String(length=120), nullable=False),
        sa.Column("manager_user_id", sa.String(length=36), nullable=True),
        sa.Column("squad_size", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["competition_id"], ["national_team_competitions.id"], name="fk_national_team_entries_competition_id_national_team_competitions", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_user_id"], ["users.id"], name="fk_national_team_entries_manager_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_national_team_entries"),
        sa.UniqueConstraint("competition_id", "country_code", name="uq_national_team_entries_competition_country"),
    )
    op.create_index("ix_national_team_entries_competition_id", "national_team_entries", ["competition_id"], unique=False)
    op.create_index("ix_national_team_entries_country_code", "national_team_entries", ["country_code"], unique=False)
    op.create_index("ix_national_team_entries_manager_user_id", "national_team_entries", ["manager_user_id"], unique=False)

    op.create_table(
        "national_team_squad_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=False),
        sa.Column("shirt_number", sa.Integer(), nullable=True),
        sa.Column("role_label", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'selected'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["entry_id"], ["national_team_entries.id"], name="fk_national_team_squad_members_entry_id_national_team_entries", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_national_team_squad_members_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_national_team_squad_members"),
        sa.UniqueConstraint("entry_id", "user_id", name="uq_national_team_squad_members_entry_user"),
    )
    op.create_index("ix_national_team_squad_members_entry_id", "national_team_squad_members", ["entry_id"], unique=False)
    op.create_index("ix_national_team_squad_members_user_id", "national_team_squad_members", ["user_id"], unique=False)

    op.create_table(
        "national_team_manager_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entry_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("action_type", sa.String(length=32), nullable=False, server_default=sa.text("'appointed'")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["entry_id"], ["national_team_entries.id"], name="fk_national_team_manager_history_entry_id_national_team_entries", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_national_team_manager_history_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_national_team_manager_history"),
    )
    op.create_index("ix_national_team_manager_history_entry_id", "national_team_manager_history", ["entry_id"], unique=False)
    op.create_index("ix_national_team_manager_history_user_id", "national_team_manager_history", ["user_id"], unique=False)

    op.create_table(
        "story_feed_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("story_type", sa.String(length=48), nullable=False),
        sa.Column("audience", sa.String(length=32), nullable=False, server_default=sa.text("'public'")),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("subject_type", sa.String(length=48), nullable=True),
        sa.Column("subject_id", sa.String(length=64), nullable=True),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("published_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["published_by_user_id"], ["users.id"], name="fk_story_feed_items_published_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_story_feed_items"),
    )
    op.create_index("ix_story_feed_items_story_type", "story_feed_items", ["story_type"], unique=False)
    op.create_index("ix_story_feed_items_subject_type", "story_feed_items", ["subject_type"], unique=False)
    op.create_index("ix_story_feed_items_subject_id", "story_feed_items", ["subject_id"], unique=False)
    op.create_index("ix_story_feed_items_country_code", "story_feed_items", ["country_code"], unique=False)

    op.create_table(
        "integrity_scores",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("score", sa.Numeric(10, 2), nullable=False, server_default=sa.text("100.00")),
        sa.Column("risk_level", sa.String(length=16), nullable=False, server_default=sa.text("'low'")),
        sa.Column("incident_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_integrity_scores_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_integrity_scores"),
        sa.UniqueConstraint("user_id", name="uq_integrity_scores_user_id"),
    )
    op.create_index("ix_integrity_scores_user_id", "integrity_scores", ["user_id"], unique=False)

    op.create_table(
        "integrity_incidents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("incident_type", sa.String(length=48), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("score_delta", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("detected_by", sa.String(length=32), nullable=False, server_default=sa.text("'rules_engine'")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'open'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("resolved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], name="fk_integrity_incidents_resolved_by_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_integrity_incidents_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_integrity_incidents"),
    )
    op.create_index("ix_integrity_incidents_user_id", "integrity_incidents", ["user_id"], unique=False)
    op.create_index("ix_integrity_incidents_incident_type", "integrity_incidents", ["incident_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_integrity_incidents_incident_type", table_name="integrity_incidents")
    op.drop_index("ix_integrity_incidents_user_id", table_name="integrity_incidents")
    op.drop_table("integrity_incidents")

    op.drop_index("ix_integrity_scores_user_id", table_name="integrity_scores")
    op.drop_table("integrity_scores")

    op.drop_index("ix_story_feed_items_country_code", table_name="story_feed_items")
    op.drop_index("ix_story_feed_items_subject_id", table_name="story_feed_items")
    op.drop_index("ix_story_feed_items_subject_type", table_name="story_feed_items")
    op.drop_index("ix_story_feed_items_story_type", table_name="story_feed_items")
    op.drop_table("story_feed_items")

    op.drop_index("ix_national_team_manager_history_user_id", table_name="national_team_manager_history")
    op.drop_index("ix_national_team_manager_history_entry_id", table_name="national_team_manager_history")
    op.drop_table("national_team_manager_history")

    op.drop_index("ix_national_team_squad_members_user_id", table_name="national_team_squad_members")
    op.drop_index("ix_national_team_squad_members_entry_id", table_name="national_team_squad_members")
    op.drop_table("national_team_squad_members")

    op.drop_index("ix_national_team_entries_manager_user_id", table_name="national_team_entries")
    op.drop_index("ix_national_team_entries_country_code", table_name="national_team_entries")
    op.drop_index("ix_national_team_entries_competition_id", table_name="national_team_entries")
    op.drop_table("national_team_entries")

    op.drop_index("ix_national_team_competitions_key", table_name="national_team_competitions")
    op.drop_table("national_team_competitions")
