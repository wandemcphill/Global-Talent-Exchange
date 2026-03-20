"""Add Thread D creator fan engagement tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0015"
down_revision = "20260316_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    chat_room_status = sa.Enum("scheduled", "open", "closed", "archived", name="creatormatchchatroomstatus")
    chat_visibility = sa.Enum("visible", "flagged", "hidden", name="creatormatchchatmessagevisibility")
    advice_type = sa.Enum("substitution", "formation_change", "tactical_adjustment", name="creatortacticaladvicetype")
    advice_status = sa.Enum("active", "archived", name="creatortacticaladvicestatus")
    fan_comp_status = sa.Enum("active", "closed", name="creatorfancompetitionstatus")
    rivalry_surface = sa.Enum("homepage_promotion", "notification", name="creatorrivalrysignalsurface")
    rivalry_status = sa.Enum("active", "inactive", name="creatorrivalrysignalstatus")

    op.create_table(
        "creator_match_chat_rooms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("room_key", sa.String(length=160), nullable=False),
        sa.Column("status", chat_room_status, nullable=False),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("layout_hints_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_match_chat_rooms"),
        sa.UniqueConstraint("match_id", name="uq_creator_match_chat_rooms_match_id"),
        sa.UniqueConstraint("room_key", name="uq_creator_match_chat_rooms_room_key"),
    )

    op.create_table(
        "creator_match_chat_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("author_user_id", sa.String(length=36), nullable=False),
        sa.Column("supported_club_id", sa.String(length=36), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visibility", chat_visibility, nullable=False),
        sa.Column("visibility_priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("shareholder", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("season_pass_holder", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("paying_viewer", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["creator_match_chat_rooms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supported_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_match_chat_messages"),
    )

    op.create_table(
        "creator_match_tactical_advice",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("author_user_id", sa.String(length=36), nullable=False),
        sa.Column("supported_club_id", sa.String(length=36), nullable=True),
        sa.Column("advice_type", advice_type, nullable=False),
        sa.Column("suggestion_text", sa.String(length=255), nullable=False),
        sa.Column("visibility_priority", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", advice_status, nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supported_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_match_tactical_advice"),
    )

    op.create_table(
        "creator_club_follows",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=48), server_default=sa.text("'creator_match'"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_club_follows"),
        sa.UniqueConstraint("club_id", "user_id", name="uq_creator_club_follows_club_user"),
    )

    op.create_table(
        "creator_fan_groups",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("identity_label", sa.String(length=120), nullable=True),
        sa.Column("is_official", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_fan_groups"),
        sa.UniqueConstraint("club_id", "slug", name="uq_creator_fan_groups_club_slug"),
    )

    op.create_table(
        "creator_fan_group_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("member_role", sa.String(length=32), server_default=sa.text("'member'"), nullable=False),
        sa.Column("fan_identity_label", sa.String(length=120), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["creator_fan_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_fan_group_memberships"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_creator_fan_group_memberships_group_user"),
    )

    op.create_table(
        "creator_fan_competitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("status", fan_comp_status, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_fan_competitions"),
    )

    op.create_table(
        "creator_fan_competition_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("fan_competition_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("fan_group_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["fan_competition_id"], ["creator_fan_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fan_group_id"], ["creator_fan_groups.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_fan_competition_entries"),
        sa.UniqueConstraint("fan_competition_id", "user_id", name="uq_creator_fan_competition_entries_competition_user"),
    )

    op.create_table(
        "creator_fan_wall_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("event_kind", sa.String(length=48), nullable=False),
        sa.Column("headline", sa.String(length=180), nullable=False),
        sa.Column("body", sa.String(length=255), nullable=True),
        sa.Column("reference_type", sa.String(length=48), nullable=True),
        sa.Column("reference_id", sa.String(length=36), nullable=True),
        sa.Column("prominence", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_fan_wall_events"),
    )

    op.create_table(
        "creator_rivalry_signal_outputs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("home_club_id", sa.String(length=36), nullable=False),
        sa.Column("away_club_id", sa.String(length=36), nullable=False),
        sa.Column("club_social_rivalry_id", sa.String(length=36), nullable=True),
        sa.Column("surface", rivalry_surface, nullable=False),
        sa.Column("signal_status", rivalry_status, nullable=False),
        sa.Column("score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("headline", sa.String(length=180), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("target_user_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rationale_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["home_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["away_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_rivalry_signal_outputs"),
        sa.UniqueConstraint("match_id", "surface", name="uq_creator_rivalry_signal_outputs_match_surface"),
    )


def downgrade() -> None:
    op.drop_table("creator_rivalry_signal_outputs")
    op.drop_table("creator_fan_wall_events")
    op.drop_table("creator_fan_competition_entries")
    op.drop_table("creator_fan_competitions")
    op.drop_table("creator_fan_group_memberships")
    op.drop_table("creator_fan_groups")
    op.drop_table("creator_club_follows")
    op.drop_table("creator_match_tactical_advice")
    op.drop_table("creator_match_chat_messages")
    op.drop_table("creator_match_chat_rooms")
