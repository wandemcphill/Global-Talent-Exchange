"""Add transfer market auctions, coach layers, and negotiation tables.

Revision ID: 20260327_0039_transfer_market_layers
Revises: 20260327_0038_merge_feature_heads
Create Date: 2026-03-27 18:40:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0039_transfer_market_layers"
down_revision = "20260327_0038_merge_feature_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transfer_listings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("window_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("selling_club_id", sa.String(length=36), nullable=False),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("current_highest_bid", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("highest_bidder_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default=sa.text("'open'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reserve_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("bid_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("watchlist_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("anti_sniping_extension_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_bid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["highest_bidder_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selling_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["window_id"], ["transfer_windows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transfer_listings_window_id", "transfer_listings", ["window_id"], unique=False)
    op.create_index("ix_transfer_listings_player_id", "transfer_listings", ["player_id"], unique=False)
    op.create_index("ix_transfer_listings_selling_club_id", "transfer_listings", ["selling_club_id"], unique=False)
    op.create_index("ix_transfer_listings_highest_bidder_id", "transfer_listings", ["highest_bidder_id"], unique=False)
    op.create_index("ix_transfer_listings_status", "transfer_listings", ["status"], unique=False)
    op.create_index("ix_transfer_listings_expires_at", "transfer_listings", ["expires_at"], unique=False)

    op.create_table(
        "transfer_listing_bids",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("listing_id", sa.String(length=36), nullable=False),
        sa.Column("bidder_club_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["bidder_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["transfer_listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transfer_listing_bids_listing_id", "transfer_listing_bids", ["listing_id"], unique=False)
    op.create_index("ix_transfer_listing_bids_bidder_club_id", "transfer_listing_bids", ["bidder_club_id"], unique=False)
    op.create_index("ix_transfer_listing_bids_timestamp", "transfer_listing_bids", ["timestamp"], unique=False)

    op.create_table(
        "player_decision_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("preferred_leagues_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("preferred_play_style", sa.String(length=64), nullable=True),
        sa.Column("wage_expectation_amount", sa.Numeric(18, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("ambition_level", sa.Integer(), nullable=False, server_default=sa.text("50")),
        sa.Column("happiness", sa.Float(), nullable=False, server_default=sa.text("50.0")),
        sa.Column("loyalty", sa.Float(), nullable=False, server_default=sa.text("50.0")),
        sa.Column("ambition", sa.Float(), nullable=False, server_default=sa.text("50.0")),
        sa.Column("frustration", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_player_decision_profiles_player_id"),
    )
    op.create_index("ix_player_decision_profiles_player_id", "player_decision_profiles", ["player_id"], unique=False)

    op.create_table(
        "coach_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("personality_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("tactical_philosophy", sa.String(length=64), nullable=False, server_default=sa.text("'balanced'")),
        sa.Column("authority_level", sa.Float(), nullable=False, server_default=sa.text("50.0")),
        sa.Column("transfer_preference", sa.String(length=64), nullable=False, server_default=sa.text("'balanced'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", name="uq_coach_profiles_club_id"),
    )
    op.create_index("ix_coach_profiles_club_id", "coach_profiles", ["club_id"], unique=False)

    op.create_table(
        "coach_demands",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("coach_profile_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("need", sa.String(length=80), nullable=False),
        sa.Column("urgency", sa.String(length=16), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["coach_profile_id"], ["coach_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coach_demands_coach_profile_id", "coach_demands", ["coach_profile_id"], unique=False)
    op.create_index("ix_coach_demands_club_id", "coach_demands", ["club_id"], unique=False)

    op.create_table(
        "player_coach_relationships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("relationship_score", sa.Float(), nullable=False, server_default=sa.text("50.0")),
        sa.Column("integration_success_modifier", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("conflict_level", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "club_id", name="uq_player_coach_relationships_player_club"),
    )
    op.create_index("ix_player_coach_relationships_player_id", "player_coach_relationships", ["player_id"], unique=False)
    op.create_index("ix_player_coach_relationships_club_id", "player_coach_relationships", ["club_id"], unique=False)

    op.create_table(
        "club_team_dynamics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("leaders_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("cliques_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("morale_groups_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("chemistry_risk", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", name="uq_club_team_dynamics_club_id"),
    )
    op.create_index("ix_club_team_dynamics_club_id", "club_team_dynamics", ["club_id"], unique=False)

    op.create_table(
        "market_watchlist_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default=sa.text("'scouting'")),
        sa.Column("discovery_score", sa.Float(), nullable=False, server_default=sa.text("50.0")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", "player_id", name="uq_market_watchlist_entries_club_player"),
    )
    op.create_index("ix_market_watchlist_entries_club_id", "market_watchlist_entries", ["club_id"], unique=False)
    op.create_index("ix_market_watchlist_entries_player_id", "market_watchlist_entries", ["player_id"], unique=False)

    op.create_table(
        "transfer_negotiations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("listing_id", sa.String(length=36), nullable=False),
        sa.Column("winning_bid_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("selling_club_id", sa.String(length=36), nullable=False),
        sa.Column("bidder_club_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'awaiting_contract_offer'")),
        sa.Column("wage_offer_amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("contract_years", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("expected_role", sa.String(length=40), nullable=True),
        sa.Column("agent_response", sa.String(length=32), nullable=True),
        sa.Column("coach_stance", sa.String(length=16), nullable=True),
        sa.Column("coach_reason", sa.Text(), nullable=True),
        sa.Column("player_decision_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("coach_opinion_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("clauses_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("concerns_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("decision_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_transfer_bid_id", sa.String(length=36), nullable=True),
        sa.Column("player_contract_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["bidder_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lifecycle_transfer_bid_id"], ["transfer_bids.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["listing_id"], ["transfer_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_contract_id"], ["player_contracts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selling_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winning_bid_id"], ["transfer_listing_bids.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", name="uq_transfer_negotiations_listing_id"),
    )
    op.create_index("ix_transfer_negotiations_listing_id", "transfer_negotiations", ["listing_id"], unique=False)
    op.create_index("ix_transfer_negotiations_winning_bid_id", "transfer_negotiations", ["winning_bid_id"], unique=False)
    op.create_index("ix_transfer_negotiations_player_id", "transfer_negotiations", ["player_id"], unique=False)
    op.create_index("ix_transfer_negotiations_selling_club_id", "transfer_negotiations", ["selling_club_id"], unique=False)
    op.create_index("ix_transfer_negotiations_bidder_club_id", "transfer_negotiations", ["bidder_club_id"], unique=False)
    op.create_index("ix_transfer_negotiations_status", "transfer_negotiations", ["status"], unique=False)
    op.create_index("ix_transfer_negotiations_decision_due_at", "transfer_negotiations", ["decision_due_at"], unique=False)
    op.create_index("ix_transfer_negotiations_lifecycle_transfer_bid_id", "transfer_negotiations", ["lifecycle_transfer_bid_id"], unique=False)
    op.create_index("ix_transfer_negotiations_player_contract_id", "transfer_negotiations", ["player_contract_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transfer_negotiations_player_contract_id", table_name="transfer_negotiations")
    op.drop_index("ix_transfer_negotiations_lifecycle_transfer_bid_id", table_name="transfer_negotiations")
    op.drop_index("ix_transfer_negotiations_decision_due_at", table_name="transfer_negotiations")
    op.drop_index("ix_transfer_negotiations_status", table_name="transfer_negotiations")
    op.drop_index("ix_transfer_negotiations_bidder_club_id", table_name="transfer_negotiations")
    op.drop_index("ix_transfer_negotiations_selling_club_id", table_name="transfer_negotiations")
    op.drop_index("ix_transfer_negotiations_player_id", table_name="transfer_negotiations")
    op.drop_index("ix_transfer_negotiations_winning_bid_id", table_name="transfer_negotiations")
    op.drop_index("ix_transfer_negotiations_listing_id", table_name="transfer_negotiations")
    op.drop_table("transfer_negotiations")

    op.drop_index("ix_market_watchlist_entries_player_id", table_name="market_watchlist_entries")
    op.drop_index("ix_market_watchlist_entries_club_id", table_name="market_watchlist_entries")
    op.drop_table("market_watchlist_entries")

    op.drop_index("ix_club_team_dynamics_club_id", table_name="club_team_dynamics")
    op.drop_table("club_team_dynamics")

    op.drop_index("ix_player_coach_relationships_club_id", table_name="player_coach_relationships")
    op.drop_index("ix_player_coach_relationships_player_id", table_name="player_coach_relationships")
    op.drop_table("player_coach_relationships")

    op.drop_index("ix_coach_demands_club_id", table_name="coach_demands")
    op.drop_index("ix_coach_demands_coach_profile_id", table_name="coach_demands")
    op.drop_table("coach_demands")

    op.drop_index("ix_coach_profiles_club_id", table_name="coach_profiles")
    op.drop_table("coach_profiles")

    op.drop_index("ix_player_decision_profiles_player_id", table_name="player_decision_profiles")
    op.drop_table("player_decision_profiles")

    op.drop_index("ix_transfer_listing_bids_timestamp", table_name="transfer_listing_bids")
    op.drop_index("ix_transfer_listing_bids_bidder_club_id", table_name="transfer_listing_bids")
    op.drop_index("ix_transfer_listing_bids_listing_id", table_name="transfer_listing_bids")
    op.drop_table("transfer_listing_bids")

    op.drop_index("ix_transfer_listings_expires_at", table_name="transfer_listings")
    op.drop_index("ix_transfer_listings_status", table_name="transfer_listings")
    op.drop_index("ix_transfer_listings_highest_bidder_id", table_name="transfer_listings")
    op.drop_index("ix_transfer_listings_selling_club_id", table_name="transfer_listings")
    op.drop_index("ix_transfer_listings_player_id", table_name="transfer_listings")
    op.drop_index("ix_transfer_listings_window_id", table_name="transfer_listings")
    op.drop_table("transfer_listings")
