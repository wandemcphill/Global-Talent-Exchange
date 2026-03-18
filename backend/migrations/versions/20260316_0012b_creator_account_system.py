"""creator application provisioning and creator-card isolation

Revision ID: 20260316_0012b
Revises: 20260316_0011
Create Date: 2026-03-16 16:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260316_0012b"
down_revision = "20260316_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "creator_applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("requested_handle", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=24), nullable=False),
        sa.Column("follower_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("social_links_json", sa.JSON(), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_creator_applications_user_id"),
    )
    op.create_index("ix_creator_applications_user_id", "creator_applications", ["user_id"], unique=False)
    op.create_index("ix_creator_applications_status", "creator_applications", ["status"], unique=False)
    op.create_index("ix_creator_applications_requested_handle", "creator_applications", ["requested_handle"], unique=False)
    op.create_index("ix_creator_applications_platform", "creator_applications", ["platform"], unique=False)

    op.create_table(
        "creator_squads",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("first_team_limit", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("academy_limit", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("total_limit", sa.Integer(), nullable=False, server_default="55"),
        sa.Column("first_team_json", sa.JSON(), nullable=False),
        sa.Column("academy_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_id", name="uq_creator_squads_club_id"),
        sa.UniqueConstraint("creator_profile_id", name="uq_creator_squads_creator_profile_id"),
    )
    op.create_index("ix_creator_squads_club_id", "creator_squads", ["club_id"], unique=False)
    op.create_index("ix_creator_squads_creator_profile_id", "creator_squads", ["creator_profile_id"], unique=False)

    op.create_table(
        "creator_regens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("primary_position", sa.String(length=40), nullable=False),
        sa.Column("secondary_positions_json", sa.JSON(), nullable=False),
        sa.Column("current_gsi", sa.Integer(), nullable=False),
        sa.Column("potential_maximum", sa.Integer(), nullable=False),
        sa.Column("squad_bucket", sa.String(length=24), nullable=False, server_default="first_team"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("creator_profile_id", name="uq_creator_regens_creator_profile_id"),
    )
    op.create_index("ix_creator_regens_club_id", "creator_regens", ["club_id"], unique=False)
    op.create_index("ix_creator_regens_creator_profile_id", "creator_regens", ["creator_profile_id"], unique=False)

    op.create_table(
        "creator_club_provisioning",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("application_id", sa.String(length=36), nullable=False),
        sa.Column("creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("stadium_id", sa.String(length=36), nullable=False),
        sa.Column("creator_squad_id", sa.String(length=36), nullable=False),
        sa.Column("creator_regen_id", sa.String(length=36), nullable=False),
        sa.Column("provision_status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["creator_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_regen_id"], ["creator_regens.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_squad_id"], ["creator_squads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stadium_id"], ["club_stadiums.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", name="uq_creator_club_provisioning_application_id"),
        sa.UniqueConstraint("creator_profile_id", name="uq_creator_club_provisioning_creator_profile_id"),
        sa.UniqueConstraint("club_id", name="uq_creator_club_provisioning_club_id"),
        sa.UniqueConstraint("stadium_id", name="uq_creator_club_provisioning_stadium_id"),
        sa.UniqueConstraint("creator_squad_id", name="uq_creator_club_provisioning_creator_squad_id"),
        sa.UniqueConstraint("creator_regen_id", name="uq_creator_club_provisioning_creator_regen_id"),
    )
    op.create_index("ix_creator_club_provisioning_club_id", "creator_club_provisioning", ["club_id"], unique=False)
    op.create_index("ix_creator_club_provisioning_creator_profile_id", "creator_club_provisioning", ["creator_profile_id"], unique=False)

    op.create_table(
        "creator_cards",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("owner_creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["owner_creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_creator_cards_player_id"),
    )
    op.create_index("ix_creator_cards_owner_creator_profile_id", "creator_cards", ["owner_creator_profile_id"], unique=False)

    op.create_table(
        "creator_card_listings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creator_card_id", sa.String(length=36), nullable=False),
        sa.Column("seller_creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("price_credits", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["creator_card_id"], ["creator_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creator_card_listings_creator_card_id", "creator_card_listings", ["creator_card_id"], unique=False)
    op.create_index("ix_creator_card_listings_seller_creator_profile_id", "creator_card_listings", ["seller_creator_profile_id"], unique=False)
    op.create_index("ix_creator_card_listings_status", "creator_card_listings", ["status"], unique=False)

    op.create_table(
        "creator_card_sales",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creator_card_id", sa.String(length=36), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("seller_creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("buyer_creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("price_credits", sa.Numeric(18, 4), nullable=False),
        sa.Column("settlement_reference", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="settled"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["buyer_creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_card_id"], ["creator_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["creator_card_listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seller_creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settlement_reference", name="uq_creator_card_sales_settlement_reference"),
    )
    op.create_index("ix_creator_card_sales_creator_card_id", "creator_card_sales", ["creator_card_id"], unique=False)
    op.create_index("ix_creator_card_sales_buyer_creator_profile_id", "creator_card_sales", ["buyer_creator_profile_id"], unique=False)

    op.create_table(
        "creator_card_swaps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("proposer_creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("counterparty_creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("proposer_card_id", sa.String(length=36), nullable=False),
        sa.Column("counterparty_card_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="executed"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["counterparty_card_id"], ["creator_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["counterparty_creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposer_card_id"], ["creator_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposer_creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creator_card_swaps_proposer_creator_profile_id", "creator_card_swaps", ["proposer_creator_profile_id"], unique=False)
    op.create_index("ix_creator_card_swaps_counterparty_creator_profile_id", "creator_card_swaps", ["counterparty_creator_profile_id"], unique=False)
    op.create_index("ix_creator_card_swaps_status", "creator_card_swaps", ["status"], unique=False)

    op.create_table(
        "creator_card_loans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("creator_card_id", sa.String(length=36), nullable=False),
        sa.Column("lender_creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("borrower_creator_profile_id", sa.String(length=36), nullable=False),
        sa.Column("loan_fee_credits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["borrower_creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_card_id"], ["creator_cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lender_creator_profile_id"], ["creator_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creator_card_loans_creator_card_id", "creator_card_loans", ["creator_card_id"], unique=False)
    op.create_index("ix_creator_card_loans_lender_creator_profile_id", "creator_card_loans", ["lender_creator_profile_id"], unique=False)
    op.create_index("ix_creator_card_loans_borrower_creator_profile_id", "creator_card_loans", ["borrower_creator_profile_id"], unique=False)
    op.create_index("ix_creator_card_loans_status", "creator_card_loans", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_creator_card_loans_status", table_name="creator_card_loans")
    op.drop_index("ix_creator_card_loans_borrower_creator_profile_id", table_name="creator_card_loans")
    op.drop_index("ix_creator_card_loans_lender_creator_profile_id", table_name="creator_card_loans")
    op.drop_index("ix_creator_card_loans_creator_card_id", table_name="creator_card_loans")
    op.drop_table("creator_card_loans")

    op.drop_index("ix_creator_card_swaps_status", table_name="creator_card_swaps")
    op.drop_index("ix_creator_card_swaps_counterparty_creator_profile_id", table_name="creator_card_swaps")
    op.drop_index("ix_creator_card_swaps_proposer_creator_profile_id", table_name="creator_card_swaps")
    op.drop_table("creator_card_swaps")

    op.drop_index("ix_creator_card_sales_buyer_creator_profile_id", table_name="creator_card_sales")
    op.drop_index("ix_creator_card_sales_creator_card_id", table_name="creator_card_sales")
    op.drop_table("creator_card_sales")

    op.drop_index("ix_creator_card_listings_status", table_name="creator_card_listings")
    op.drop_index("ix_creator_card_listings_seller_creator_profile_id", table_name="creator_card_listings")
    op.drop_index("ix_creator_card_listings_creator_card_id", table_name="creator_card_listings")
    op.drop_table("creator_card_listings")

    op.drop_index("ix_creator_cards_owner_creator_profile_id", table_name="creator_cards")
    op.drop_table("creator_cards")

    op.drop_index("ix_creator_club_provisioning_creator_profile_id", table_name="creator_club_provisioning")
    op.drop_index("ix_creator_club_provisioning_club_id", table_name="creator_club_provisioning")
    op.drop_table("creator_club_provisioning")

    op.drop_index("ix_creator_regens_creator_profile_id", table_name="creator_regens")
    op.drop_index("ix_creator_regens_club_id", table_name="creator_regens")
    op.drop_table("creator_regens")

    op.drop_index("ix_creator_squads_creator_profile_id", table_name="creator_squads")
    op.drop_index("ix_creator_squads_club_id", table_name="creator_squads")
    op.drop_table("creator_squads")

    op.drop_index("ix_creator_applications_platform", table_name="creator_applications")
    op.drop_index("ix_creator_applications_requested_handle", table_name="creator_applications")
    op.drop_index("ix_creator_applications_status", table_name="creator_applications")
    op.drop_index("ix_creator_applications_user_id", table_name="creator_applications")
    op.drop_table("creator_applications")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("phone_verified_at")
        batch_op.drop_column("email_verified_at")
