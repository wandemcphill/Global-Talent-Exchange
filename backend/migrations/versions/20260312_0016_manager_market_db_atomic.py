"""Move manager market state into database-backed tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260312_0016"
down_revision = "20260312_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manager_catalog_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("manager_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("rarity", sa.String(length=32), nullable=False),
        sa.Column("mentality", sa.String(length=64), nullable=False),
        sa.Column("tactics", sa.JSON(), nullable=False),
        sa.Column("traits", sa.JSON(), nullable=False),
        sa.Column("substitution_tendency", sa.String(length=64), nullable=False),
        sa.Column("philosophy_summary", sa.Text(), nullable=False),
        sa.Column("club_associations", sa.JSON(), nullable=False),
        sa.Column("supply_total", sa.Integer(), nullable=False),
        sa.Column("supply_available", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_manager_catalog_entries"),
        sa.UniqueConstraint("manager_id", name="uq_manager_catalog_entries_manager_id"),
    )
    op.create_index("ix_manager_catalog_entries_manager_id", "manager_catalog_entries", ["manager_id"], unique=False)
    op.create_index("ix_manager_catalog_entries_display_name", "manager_catalog_entries", ["display_name"], unique=False)
    op.create_index("ix_manager_catalog_entries_rarity", "manager_catalog_entries", ["rarity"], unique=False)
    op.create_index("ix_manager_catalog_entries_mentality", "manager_catalog_entries", ["mentality"], unique=False)

    op.create_table(
        "manager_holdings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("manager_id", sa.String(length=120), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("acquired_at", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["manager_id"], ["manager_catalog_entries.manager_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_manager_holdings"),
        sa.UniqueConstraint("asset_id", name="uq_manager_holdings_asset_id"),
    )
    op.create_index("ix_manager_holdings_asset_id", "manager_holdings", ["asset_id"], unique=False)
    op.create_index("ix_manager_holdings_manager_id", "manager_holdings", ["manager_id"], unique=False)
    op.create_index("ix_manager_holdings_owner_user_id", "manager_holdings", ["owner_user_id"], unique=False)
    op.create_index("ix_manager_holdings_status", "manager_holdings", ["status"], unique=False)

    op.create_table(
        "manager_trade_listings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("seller_user_id", sa.String(length=36), nullable=False),
        sa.Column("seller_name", sa.String(length=160), nullable=False),
        sa.Column("asking_price_credits", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["manager_holdings.asset_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_manager_trade_listings"),
        sa.UniqueConstraint("listing_id", name="uq_manager_trade_listings_listing_id"),
        sa.UniqueConstraint("asset_id", "status", name="uq_manager_trade_listings_asset_status"),
    )
    op.create_index("ix_manager_trade_listings_listing_id", "manager_trade_listings", ["listing_id"], unique=False)
    op.create_index("ix_manager_trade_listings_asset_id", "manager_trade_listings", ["asset_id"], unique=False)
    op.create_index("ix_manager_trade_listings_seller_user_id", "manager_trade_listings", ["seller_user_id"], unique=False)
    op.create_index("ix_manager_trade_listings_status", "manager_trade_listings", ["status"], unique=False)

    op.create_table(
        "manager_trade_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("trade_id", sa.String(length=36), nullable=False),
        sa.Column("mode", sa.String(length=24), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("proposer_asset_id", sa.String(length=36), nullable=True),
        sa.Column("requested_asset_id", sa.String(length=36), nullable=True),
        sa.Column("gross_credits", sa.String(length=64), nullable=False),
        sa.Column("fee_credits", sa.String(length=64), nullable=False),
        sa.Column("seller_net_credits", sa.String(length=64), nullable=False),
        sa.Column("settlement_reference", sa.String(length=128), nullable=False),
        sa.Column("settlement_status", sa.String(length=24), nullable=False),
        sa.Column("immediate_withdrawal_eligible", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_manager_trade_records"),
        sa.UniqueConstraint("trade_id", name="uq_manager_trade_records_trade_id"),
        sa.UniqueConstraint("settlement_reference", name="uq_manager_trade_records_settlement_reference"),
    )
    op.create_index("ix_manager_trade_records_trade_id", "manager_trade_records", ["trade_id"], unique=False)
    op.create_index("ix_manager_trade_records_listing_id", "manager_trade_records", ["listing_id"], unique=False)
    op.create_index("ix_manager_trade_records_proposer_asset_id", "manager_trade_records", ["proposer_asset_id"], unique=False)
    op.create_index("ix_manager_trade_records_requested_asset_id", "manager_trade_records", ["requested_asset_id"], unique=False)
    op.create_index("ix_manager_trade_records_settlement_reference", "manager_trade_records", ["settlement_reference"], unique=False)
    op.create_index("ix_manager_trade_records_settlement_status", "manager_trade_records", ["settlement_status"], unique=False)

    op.create_table(
        "manager_settlement_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("reference", sa.String(length=128), nullable=False),
        sa.Column("trade_id", sa.String(length=36), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("mode", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("gross_credits", sa.String(length=64), nullable=False),
        sa.Column("fee_credits", sa.String(length=64), nullable=False),
        sa.Column("seller_net_credits", sa.String(length=64), nullable=False),
        sa.Column("eligible_immediately", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("settled_by_user_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["settled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_manager_settlement_records"),
        sa.UniqueConstraint("reference", name="uq_manager_settlement_records_reference"),
    )
    op.create_index("ix_manager_settlement_records_reference", "manager_settlement_records", ["reference"], unique=False)
    op.create_index("ix_manager_settlement_records_trade_id", "manager_settlement_records", ["trade_id"], unique=False)
    op.create_index("ix_manager_settlement_records_listing_id", "manager_settlement_records", ["listing_id"], unique=False)
    op.create_index("ix_manager_settlement_records_status", "manager_settlement_records", ["status"], unique=False)
    op.create_index("ix_manager_settlement_records_settled_by_user_id", "manager_settlement_records", ["settled_by_user_id"], unique=False)

    op.create_table(
        "manager_team_assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("main_manager_asset_id", sa.String(length=36), nullable=True),
        sa.Column("academy_manager_asset_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["main_manager_asset_id"], ["manager_holdings.asset_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["academy_manager_asset_id"], ["manager_holdings.asset_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_manager_team_assignments"),
        sa.UniqueConstraint("user_id", name="uq_manager_team_assignments_user_id"),
    )
    op.create_index("ix_manager_team_assignments_user_id", "manager_team_assignments", ["user_id"], unique=False)

    op.create_table(
        "manager_competition_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("minimum_viable_participants", sa.Integer(), nullable=False),
        sa.Column("geo_locked_regions", sa.JSON(), nullable=False),
        sa.Column("allow_fallback_fill", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("fallback_source_regions", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_manager_competition_settings"),
        sa.UniqueConstraint("code", name="uq_manager_competition_settings_code"),
    )
    op.create_index("ix_manager_competition_settings_code", "manager_competition_settings", ["code"], unique=False)

    op.create_table(
        "manager_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("actor_email", sa.String(length=320), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_manager_audit_logs"),
        sa.UniqueConstraint("event_id", name="uq_manager_audit_logs_event_id"),
    )
    op.create_index("ix_manager_audit_logs_event_id", "manager_audit_logs", ["event_id"], unique=False)
    op.create_index("ix_manager_audit_logs_event_type", "manager_audit_logs", ["event_type"], unique=False)
    op.create_index("ix_manager_audit_logs_actor_user_id", "manager_audit_logs", ["actor_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_manager_audit_logs_actor_user_id", table_name="manager_audit_logs")
    op.drop_index("ix_manager_audit_logs_event_type", table_name="manager_audit_logs")
    op.drop_index("ix_manager_audit_logs_event_id", table_name="manager_audit_logs")
    op.drop_table("manager_audit_logs")

    op.drop_index("ix_manager_competition_settings_code", table_name="manager_competition_settings")
    op.drop_table("manager_competition_settings")

    op.drop_index("ix_manager_team_assignments_user_id", table_name="manager_team_assignments")
    op.drop_table("manager_team_assignments")

    op.drop_index("ix_manager_settlement_records_settled_by_user_id", table_name="manager_settlement_records")
    op.drop_index("ix_manager_settlement_records_status", table_name="manager_settlement_records")
    op.drop_index("ix_manager_settlement_records_listing_id", table_name="manager_settlement_records")
    op.drop_index("ix_manager_settlement_records_trade_id", table_name="manager_settlement_records")
    op.drop_index("ix_manager_settlement_records_reference", table_name="manager_settlement_records")
    op.drop_table("manager_settlement_records")

    op.drop_index("ix_manager_trade_records_settlement_status", table_name="manager_trade_records")
    op.drop_index("ix_manager_trade_records_settlement_reference", table_name="manager_trade_records")
    op.drop_index("ix_manager_trade_records_requested_asset_id", table_name="manager_trade_records")
    op.drop_index("ix_manager_trade_records_proposer_asset_id", table_name="manager_trade_records")
    op.drop_index("ix_manager_trade_records_listing_id", table_name="manager_trade_records")
    op.drop_index("ix_manager_trade_records_trade_id", table_name="manager_trade_records")
    op.drop_table("manager_trade_records")

    op.drop_index("ix_manager_trade_listings_status", table_name="manager_trade_listings")
    op.drop_index("ix_manager_trade_listings_seller_user_id", table_name="manager_trade_listings")
    op.drop_index("ix_manager_trade_listings_asset_id", table_name="manager_trade_listings")
    op.drop_index("ix_manager_trade_listings_listing_id", table_name="manager_trade_listings")
    op.drop_table("manager_trade_listings")

    op.drop_index("ix_manager_holdings_status", table_name="manager_holdings")
    op.drop_index("ix_manager_holdings_owner_user_id", table_name="manager_holdings")
    op.drop_index("ix_manager_holdings_manager_id", table_name="manager_holdings")
    op.drop_index("ix_manager_holdings_asset_id", table_name="manager_holdings")
    op.drop_table("manager_holdings")

    op.drop_index("ix_manager_catalog_entries_mentality", table_name="manager_catalog_entries")
    op.drop_index("ix_manager_catalog_entries_rarity", table_name="manager_catalog_entries")
    op.drop_index("ix_manager_catalog_entries_display_name", table_name="manager_catalog_entries")
    op.drop_index("ix_manager_catalog_entries_manager_id", table_name="manager_catalog_entries")
    op.drop_table("manager_catalog_entries")
