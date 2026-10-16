"""Extend transfer market into Transfer Hub listings and offers.

Revision ID: 20260510_0090_transfer_hub_terms
Revises: 20260501_0089_national_team_rental_owners
Create Date: 2026-05-10 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260510_0090_transfer_hub_terms"
down_revision = "20260501_0089_national_team_rental_owners"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transfer_listings") as batch_op:
        batch_op.add_column(sa.Column("listing_type", sa.String(length=32), nullable=False, server_default="transfer"))
        batch_op.add_column(sa.Column("asset_type", sa.String(length=32), nullable=False, server_default="real_player"))
        batch_op.add_column(sa.Column("visibility", sa.String(length=32), nullable=False, server_default="public"))
        batch_op.add_column(sa.Column("salary_amount", sa.Numeric(18, 4), nullable=True))
        batch_op.add_column(sa.Column("contract_years_remaining", sa.Numeric(5, 2), nullable=True))
        batch_op.add_column(sa.Column("buy_clause_amount", sa.Numeric(18, 4), nullable=True))
        batch_op.add_column(sa.Column("loan_terms_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("swap_terms_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("availability_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.create_index("ix_transfer_listings_listing_type", "transfer_listings", ["listing_type"], unique=False)
    op.create_index("ix_transfer_listings_asset_type", "transfer_listings", ["asset_type"], unique=False)
    op.create_index("ix_transfer_listings_visibility", "transfer_listings", ["visibility"], unique=False)

    op.create_table(
        "transfer_hub_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=False),
        sa.Column("offer_type", sa.String(length=32), nullable=False, server_default="transfer"),
        sa.Column("seller_club_id", sa.String(length=36), nullable=False),
        sa.Column("bidder_club_id", sa.String(length=36), nullable=False),
        sa.Column("cash_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("offered_player_ids_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("loan_terms_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("swap_terms_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("conditional_terms_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("sell_on_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["bidder_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["transfer_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_transfer_hub_offers_idempotency_key"),
    )
    op.create_index("ix_transfer_hub_offers_listing_id", "transfer_hub_offers", ["listing_id"], unique=False)
    op.create_index("ix_transfer_hub_offers_seller_club_id", "transfer_hub_offers", ["seller_club_id"], unique=False)
    op.create_index("ix_transfer_hub_offers_bidder_club_id", "transfer_hub_offers", ["bidder_club_id"], unique=False)
    op.create_index("ix_transfer_hub_offers_status", "transfer_hub_offers", ["status"], unique=False)
    op.create_index("ix_transfer_hub_offers_expires_at", "transfer_hub_offers", ["expires_at"], unique=False)

    op.create_table(
        "transfer_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("current_club_id", sa.String(length=36), nullable=True),
        sa.Column("requested_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("preferred_leagues_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("preferred_clubs_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("reasons_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["current_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transfer_requests_player_id", "transfer_requests", ["player_id"], unique=False)
    op.create_index("ix_transfer_requests_current_club_id", "transfer_requests", ["current_club_id"], unique=False)
    op.create_index("ix_transfer_requests_requested_by_user_id", "transfer_requests", ["requested_by_user_id"], unique=False)
    op.create_index("ix_transfer_requests_status", "transfer_requests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transfer_requests_status", table_name="transfer_requests")
    op.drop_index("ix_transfer_requests_requested_by_user_id", table_name="transfer_requests")
    op.drop_index("ix_transfer_requests_current_club_id", table_name="transfer_requests")
    op.drop_index("ix_transfer_requests_player_id", table_name="transfer_requests")
    op.drop_table("transfer_requests")

    op.drop_index("ix_transfer_hub_offers_expires_at", table_name="transfer_hub_offers")
    op.drop_index("ix_transfer_hub_offers_status", table_name="transfer_hub_offers")
    op.drop_index("ix_transfer_hub_offers_bidder_club_id", table_name="transfer_hub_offers")
    op.drop_index("ix_transfer_hub_offers_seller_club_id", table_name="transfer_hub_offers")
    op.drop_index("ix_transfer_hub_offers_listing_id", table_name="transfer_hub_offers")
    op.drop_table("transfer_hub_offers")

    op.drop_index("ix_transfer_listings_visibility", table_name="transfer_listings")
    op.drop_index("ix_transfer_listings_asset_type", table_name="transfer_listings")
    op.drop_index("ix_transfer_listings_listing_type", table_name="transfer_listings")
    with op.batch_alter_table("transfer_listings") as batch_op:
        batch_op.drop_column("availability_json")
        batch_op.drop_column("swap_terms_json")
        batch_op.drop_column("loan_terms_json")
        batch_op.drop_column("buy_clause_amount")
        batch_op.drop_column("contract_years_remaining")
        batch_op.drop_column("salary_amount")
        batch_op.drop_column("visibility")
        batch_op.drop_column("asset_type")
        batch_op.drop_column("listing_type")
