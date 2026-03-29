"""Add ticketed live events tables and merge the 0068 heads.

Revision ID: 20260329_0069_ticketed_live_events_merge_heads
Revises: 20260329_0068_gtex_universe_career_sync, 20260329_0068_platform_experience_and_national_regen_seed
Create Date: 2026-03-29 23:10:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260329_0069_ticketed_live_events_merge_heads"
down_revision = (
    "20260329_0068_gtex_universe_career_sync",
    "20260329_0068_platform_experience_and_national_regen_seed",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stadium_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("stadium_id", sa.String(length=120), nullable=False),
        sa.Column("match_id", sa.String(length=120), nullable=False),
        sa.Column("calendar_event_id", sa.String(length=36), nullable=True),
        sa.Column("source_match_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("venue_name", sa.String(length=160), nullable=False),
        sa.Column("home_club_id", sa.String(length=36), nullable=True),
        sa.Column("away_club_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False, server_default="league"),
        sa.Column("event_status", sa.String(length=24), nullable=False, server_default="on_sale"),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("tier_distribution_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("base_price_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("early_access_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_sales_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sales_close_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("importance_score", sa.Numeric(10, 4), nullable=False, server_default="0.5000"),
        sa.Column("rivalry_score", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
        sa.Column("player_popularity_score", sa.Numeric(10, 4), nullable=False, server_default="0.0000"),
        sa.Column("demand_multiplier", sa.Numeric(10, 4), nullable=False, server_default="1.0000"),
        sa.Column("tickets_sold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tickets_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resale_ticket_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gross_revenue", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("resale_volume", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("platform_cut_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("club_share_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("jackpot_pool_total", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("loyalty_points_distributed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id", name="pk_stadium_events"),
        sa.UniqueConstraint("match_id", name="uq_stadium_events_match_id"),
    )
    op.create_index("ix_stadium_events_stadium_id", "stadium_events", ["stadium_id"], unique=False)
    op.create_index("ix_stadium_events_match_id", "stadium_events", ["match_id"], unique=False)
    op.create_index("ix_stadium_events_calendar_event_id", "stadium_events", ["calendar_event_id"], unique=False)
    op.create_index("ix_stadium_events_source_match_id", "stadium_events", ["source_match_id"], unique=False)
    op.create_index("ix_stadium_events_home_club_id", "stadium_events", ["home_club_id"], unique=False)
    op.create_index("ix_stadium_events_away_club_id", "stadium_events", ["away_club_id"], unique=False)
    op.create_index("ix_stadium_events_event_type", "stadium_events", ["event_type"], unique=False)
    op.create_index("ix_stadium_events_event_status", "stadium_events", ["event_status"], unique=False)
    op.create_index("ix_stadium_events_public_sales_starts_at", "stadium_events", ["public_sales_starts_at"], unique=False)

    op.create_table(
        "stadium_tickets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("seller_user_id", sa.String(length=36), nullable=True),
        sa.Column("match_id", sa.String(length=120), nullable=False),
        sa.Column("seat_tier", sa.String(length=16), nullable=False),
        sa.Column("seat_code", sa.String(length=24), nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=False),
        sa.Column("original_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="sold"),
        sa.Column("resale_listing_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("listed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rewarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("loyalty_points_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exclusive_drop_code", sa.String(length=80), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["event_id"], ["stadium_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_stadium_tickets"),
        sa.UniqueConstraint("match_id", "seat_code", name="uq_stadium_tickets_match_seat"),
    )
    op.create_index("ix_stadium_tickets_event_id_status", "stadium_tickets", ["event_id", "status"], unique=False)
    op.create_index("ix_stadium_tickets_user_id", "stadium_tickets", ["user_id"], unique=False)
    op.create_index("ix_stadium_tickets_match_id", "stadium_tickets", ["match_id"], unique=False)

    op.create_table(
        "ticket_waitlists",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("seat_tier", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ticket_waitlists"),
        sa.UniqueConstraint("match_id", "user_id", name="uq_ticket_waitlists_match_user"),
    )
    op.create_index("ix_ticket_waitlists_match_id_status", "ticket_waitlists", ["match_id", "status"], unique=False)
    op.create_index("ix_ticket_waitlists_user_id", "ticket_waitlists", ["user_id"], unique=False)

    op.create_table(
        "ticket_reactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ticket_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("reaction_type", sa.String(length=16), nullable=False),
        sa.Column("crowd_delta", sa.Numeric(10, 4), nullable=False),
        sa.Column("influence_multiplier", sa.Numeric(10, 4), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["ticket_id"], ["stadium_tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ticket_reactions"),
    )
    op.create_index("ix_ticket_reactions_match_id_created_at", "ticket_reactions", ["match_id", "created_at"], unique=False)
    op.create_index("ix_ticket_reactions_ticket_id", "ticket_reactions", ["ticket_id"], unique=False)
    op.create_index("ix_ticket_reactions_user_id", "ticket_reactions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ticket_reactions_user_id", table_name="ticket_reactions")
    op.drop_index("ix_ticket_reactions_ticket_id", table_name="ticket_reactions")
    op.drop_index("ix_ticket_reactions_match_id_created_at", table_name="ticket_reactions")
    op.drop_table("ticket_reactions")

    op.drop_index("ix_ticket_waitlists_user_id", table_name="ticket_waitlists")
    op.drop_index("ix_ticket_waitlists_match_id_status", table_name="ticket_waitlists")
    op.drop_table("ticket_waitlists")

    op.drop_index("ix_stadium_tickets_match_id", table_name="stadium_tickets")
    op.drop_index("ix_stadium_tickets_user_id", table_name="stadium_tickets")
    op.drop_index("ix_stadium_tickets_event_id_status", table_name="stadium_tickets")
    op.drop_table("stadium_tickets")

    op.drop_index("ix_stadium_events_public_sales_starts_at", table_name="stadium_events")
    op.drop_index("ix_stadium_events_event_status", table_name="stadium_events")
    op.drop_index("ix_stadium_events_event_type", table_name="stadium_events")
    op.drop_index("ix_stadium_events_away_club_id", table_name="stadium_events")
    op.drop_index("ix_stadium_events_home_club_id", table_name="stadium_events")
    op.drop_index("ix_stadium_events_source_match_id", table_name="stadium_events")
    op.drop_index("ix_stadium_events_calendar_event_id", table_name="stadium_events")
    op.drop_index("ix_stadium_events_match_id", table_name="stadium_events")
    op.drop_index("ix_stadium_events_stadium_id", table_name="stadium_events")
    op.drop_table("stadium_events")
