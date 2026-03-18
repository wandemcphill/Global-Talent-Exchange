"""card loans starter rentals sponsor offers and highlight share exports

Revision ID: 20260316_0010
Revises: 20260316_0008
Create Date: 2026-03-16 13:20:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260316_0010"
down_revision = "20260316_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "card_loan_listings",
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("total_slots", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("available_slots", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("loan_fee_credits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="coin"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_restrictions_json", sa.JSON(), nullable=False),
        sa.Column("terms_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_loan_listings_owner_user_id", "card_loan_listings", ["owner_user_id"], unique=False)
    op.create_index("ix_card_loan_listings_player_card_id", "card_loan_listings", ["player_card_id"], unique=False)
    op.create_index("ix_card_loan_listings_status", "card_loan_listings", ["status"], unique=False)

    op.create_table(
        "card_loan_contracts",
        sa.Column("listing_id", sa.String(length=36), nullable=False),
        sa.Column("player_card_id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("borrower_user_id", sa.String(length=36), nullable=False),
        sa.Column("loan_fee_credits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="coin"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("borrowed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("usage_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["borrower_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["card_loan_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_card_id"], ["player_cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_card_loan_contracts_borrower_user_id", "card_loan_contracts", ["borrower_user_id"], unique=False)
    op.create_index("ix_card_loan_contracts_due_at", "card_loan_contracts", ["due_at"], unique=False)
    op.create_index("ix_card_loan_contracts_listing_id", "card_loan_contracts", ["listing_id"], unique=False)
    op.create_index("ix_card_loan_contracts_status", "card_loan_contracts", ["status"], unique=False)

    op.create_table(
        "starter_squad_rentals",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("rental_fee_credits", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="credit"),
        sa.Column("term_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_team_count", sa.Integer(), nullable=False, server_default="18"),
        sa.Column("academy_count", sa.Integer(), nullable=False, server_default="18"),
        sa.Column("is_non_tradable", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("roster_json", sa.JSON(), nullable=False),
        sa.Column("academy_roster_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_starter_squad_rentals_status", "starter_squad_rentals", ["status"], unique=False)
    op.create_index("ix_starter_squad_rentals_user_id", "starter_squad_rentals", ["user_id"], unique=False)

    op.create_table(
        "sponsor_offers",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("offer_name", sa.String(length=120), nullable=False),
        sa.Column("sponsor_name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="club"),
        sa.Column("base_value_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("default_duration_months", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("approved_surfaces_json", sa.JSON(), nullable=False),
        sa.Column("creative_url", sa.String(length=255), nullable=True),
        sa.Column("category_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_sponsor_offers_code"),
    )
    op.create_index("ix_sponsor_offers_category", "sponsor_offers", ["category"], unique=False)
    op.create_index(op.f("ix_sponsor_offers_code"), "sponsor_offers", ["code"], unique=False)

    op.create_table(
        "sponsor_offer_rules",
        sa.Column("sponsor_offer_id", sa.String(length=36), nullable=False),
        sa.Column("min_fan_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_reputation_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_club_valuation", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("min_media_popularity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_competition_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_rivalry_visibility", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("required_prestige_tier", sa.String(length=32), nullable=True),
        sa.Column("competition_allowlist_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["sponsor_offer_id"], ["sponsor_offers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sponsor_offer_rules_sponsor_offer_id", "sponsor_offer_rules", ["sponsor_offer_id"], unique=False)

    op.create_table(
        "club_sponsors",
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("sponsor_offer_id", sa.String(length=36), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=True),
        sa.Column("sponsor_name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="club"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("contract_value_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=12), nullable=False, server_default="USD"),
        sa.Column("duration_months", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_surfaces_json", sa.JSON(), nullable=False),
        sa.Column("creative_url", sa.String(length=255), nullable=True),
        sa.Column("analytics_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["club_sponsorship_contracts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sponsor_offer_id"], ["sponsor_offers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_club_sponsors_club_id", "club_sponsors", ["club_id"], unique=False)
    op.create_index("ix_club_sponsors_sponsor_offer_id", "club_sponsors", ["sponsor_offer_id"], unique=False)
    op.create_index("ix_club_sponsors_status", "club_sponsors", ["status"], unique=False)

    op.create_table(
        "highlight_share_templates",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("overlay_defaults_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_highlight_share_templates_code"),
    )
    op.create_index("ix_highlight_share_templates_aspect_ratio", "highlight_share_templates", ["aspect_ratio"], unique=False)
    op.create_index(op.f("ix_highlight_share_templates_code"), "highlight_share_templates", ["code"], unique=False)

    op.create_table(
        "highlight_share_exports",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=True),
        sa.Column("match_key", sa.String(length=120), nullable=False),
        sa.Column("source_storage_key", sa.String(length=255), nullable=False),
        sa.Column("export_storage_key", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="generated"),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("watermark_label", sa.String(length=80), nullable=True),
        sa.Column("share_title", sa.String(length=160), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["template_id"], ["highlight_share_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_highlight_share_exports_match_key", "highlight_share_exports", ["match_key"], unique=False)
    op.create_index("ix_highlight_share_exports_status", "highlight_share_exports", ["status"], unique=False)
    op.create_index("ix_highlight_share_exports_user_id", "highlight_share_exports", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_highlight_share_exports_user_id", table_name="highlight_share_exports")
    op.drop_index("ix_highlight_share_exports_status", table_name="highlight_share_exports")
    op.drop_index("ix_highlight_share_exports_match_key", table_name="highlight_share_exports")
    op.drop_table("highlight_share_exports")

    op.drop_index(op.f("ix_highlight_share_templates_code"), table_name="highlight_share_templates")
    op.drop_index("ix_highlight_share_templates_aspect_ratio", table_name="highlight_share_templates")
    op.drop_table("highlight_share_templates")

    op.drop_index("ix_club_sponsors_status", table_name="club_sponsors")
    op.drop_index("ix_club_sponsors_sponsor_offer_id", table_name="club_sponsors")
    op.drop_index("ix_club_sponsors_club_id", table_name="club_sponsors")
    op.drop_table("club_sponsors")

    op.drop_index("ix_sponsor_offer_rules_sponsor_offer_id", table_name="sponsor_offer_rules")
    op.drop_table("sponsor_offer_rules")

    op.drop_index(op.f("ix_sponsor_offers_code"), table_name="sponsor_offers")
    op.drop_index("ix_sponsor_offers_category", table_name="sponsor_offers")
    op.drop_table("sponsor_offers")

    op.drop_index("ix_starter_squad_rentals_user_id", table_name="starter_squad_rentals")
    op.drop_index("ix_starter_squad_rentals_status", table_name="starter_squad_rentals")
    op.drop_table("starter_squad_rentals")

    op.drop_index("ix_card_loan_contracts_status", table_name="card_loan_contracts")
    op.drop_index("ix_card_loan_contracts_listing_id", table_name="card_loan_contracts")
    op.drop_index("ix_card_loan_contracts_due_at", table_name="card_loan_contracts")
    op.drop_index("ix_card_loan_contracts_borrower_user_id", table_name="card_loan_contracts")
    op.drop_table("card_loan_contracts")

    op.drop_index("ix_card_loan_listings_status", table_name="card_loan_listings")
    op.drop_index("ix_card_loan_listings_player_card_id", table_name="card_loan_listings")
    op.drop_index("ix_card_loan_listings_owner_user_id", table_name="card_loan_listings")
    op.drop_table("card_loan_listings")
