"""Add legend layer narrative, prestige, and interview tables.

Revision ID: 20260329_0070_legend_layer
Revises: 20260329_0069_merge_platform_and_career_sync_heads
Create Date: 2026-03-29 23:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0070_legend_layer"
down_revision = "20260329_0069_merge_platform_and_career_sync_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("player_personality_profiles") as batch_op:
        batch_op.add_column(sa.Column("aggression", sa.Integer(), nullable=False, server_default="50"))
        batch_op.add_column(sa.Column("confidence", sa.Integer(), nullable=False, server_default="50"))
        batch_op.add_column(sa.Column("consistency", sa.Integer(), nullable=False, server_default="50"))
        batch_op.add_column(sa.Column("clutch_factor", sa.Integer(), nullable=False, server_default="50"))

    op.create_table(
        "news_articles",
        sa.Column("article_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("headline_variants_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("related_match_id", sa.String(length=80), nullable=True),
        sa.Column("related_player_id", sa.String(length=36), nullable=True),
        sa.Column("related_club_id", sa.String(length=36), nullable=True),
        sa.Column("related_user_id", sa.String(length=36), nullable=True),
        sa.Column("trend_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("perception_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_news_articles_article_type", "news_articles", ["article_type"], unique=False)
    op.create_index("ix_news_articles_related_match_id", "news_articles", ["related_match_id"], unique=False)
    op.create_index("ix_news_articles_related_player_id", "news_articles", ["related_player_id"], unique=False)
    op.create_index("ix_news_articles_related_club_id", "news_articles", ["related_club_id"], unique=False)
    op.create_index("ix_news_articles_related_user_id", "news_articles", ["related_user_id"], unique=False)

    op.create_table(
        "player_interviews",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("article_id", sa.String(length=36), nullable=True),
        sa.Column("match_id", sa.String(length=80), nullable=True),
        sa.Column("interview_type", sa.String(length=32), nullable=False, server_default="post_match"),
        sa.Column("sentiment", sa.String(length=24), nullable=False, server_default="composed"),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["article_id"], ["news_articles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_interviews_player_id", "player_interviews", ["player_id"], unique=False)
    op.create_index("ix_player_interviews_article_id", "player_interviews", ["article_id"], unique=False)
    op.create_index("ix_player_interviews_match_id", "player_interviews", ["match_id"], unique=False)

    op.create_table(
        "player_fan_reactions",
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("article_id", sa.String(length=36), nullable=True),
        sa.Column("match_id", sa.String(length=80), nullable=True),
        sa.Column("reaction_type", sa.String(length=24), nullable=False),
        sa.Column("intensity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("headline", sa.String(length=220), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["article_id"], ["news_articles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_fan_reactions_player_id", "player_fan_reactions", ["player_id"], unique=False)
    op.create_index("ix_player_fan_reactions_article_id", "player_fan_reactions", ["article_id"], unique=False)
    op.create_index("ix_player_fan_reactions_match_id", "player_fan_reactions", ["match_id"], unique=False)
    op.create_index("ix_player_fan_reactions_reaction_type", "player_fan_reactions", ["reaction_type"], unique=False)

    op.create_table(
        "prestige_ratings",
        sa.Column("entity_type", sa.String(length=24), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("entity_name", sa.String(length=200), nullable=False),
        sa.Column("scope", sa.String(length=24), nullable=False),
        sa.Column("season_key", sa.String(length=80), nullable=False, server_default="lifetime"),
        sa.Column("prestige_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("trophies", sa.Float(), nullable=False, server_default="0"),
        sa.Column("win_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("player_development", sa.Float(), nullable=False, server_default="0"),
        sa.Column("earnings", sa.Float(), nullable=False, server_default="0"),
        sa.Column("difficulty_modifier", sa.Float(), nullable=False, server_default="0"),
        sa.Column("perception_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("prestige_tier", sa.String(length=24), nullable=False, server_default="Bronze"),
        sa.Column("rank_position", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", "scope", "season_key", name="uq_prestige_ratings_entity_scope"),
    )
    op.create_index("ix_prestige_ratings_entity_type", "prestige_ratings", ["entity_type"], unique=False)
    op.create_index("ix_prestige_ratings_entity_id", "prestige_ratings", ["entity_id"], unique=False)
    op.create_index("ix_prestige_ratings_scope", "prestige_ratings", ["scope"], unique=False)
    op.create_index("ix_prestige_ratings_season_key", "prestige_ratings", ["season_key"], unique=False)
    op.create_index("ix_prestige_ratings_rank_position", "prestige_ratings", ["rank_position"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_prestige_ratings_rank_position", table_name="prestige_ratings")
    op.drop_index("ix_prestige_ratings_season_key", table_name="prestige_ratings")
    op.drop_index("ix_prestige_ratings_scope", table_name="prestige_ratings")
    op.drop_index("ix_prestige_ratings_entity_id", table_name="prestige_ratings")
    op.drop_index("ix_prestige_ratings_entity_type", table_name="prestige_ratings")
    op.drop_table("prestige_ratings")

    op.drop_index("ix_player_fan_reactions_reaction_type", table_name="player_fan_reactions")
    op.drop_index("ix_player_fan_reactions_match_id", table_name="player_fan_reactions")
    op.drop_index("ix_player_fan_reactions_article_id", table_name="player_fan_reactions")
    op.drop_index("ix_player_fan_reactions_player_id", table_name="player_fan_reactions")
    op.drop_table("player_fan_reactions")

    op.drop_index("ix_player_interviews_match_id", table_name="player_interviews")
    op.drop_index("ix_player_interviews_article_id", table_name="player_interviews")
    op.drop_index("ix_player_interviews_player_id", table_name="player_interviews")
    op.drop_table("player_interviews")

    op.drop_index("ix_news_articles_related_user_id", table_name="news_articles")
    op.drop_index("ix_news_articles_related_club_id", table_name="news_articles")
    op.drop_index("ix_news_articles_related_player_id", table_name="news_articles")
    op.drop_index("ix_news_articles_related_match_id", table_name="news_articles")
    op.drop_index("ix_news_articles_article_type", table_name="news_articles")
    op.drop_table("news_articles")

    with op.batch_alter_table("player_personality_profiles") as batch_op:
        batch_op.drop_column("clutch_factor")
        batch_op.drop_column("consistency")
        batch_op.drop_column("confidence")
        batch_op.drop_column("aggression")
