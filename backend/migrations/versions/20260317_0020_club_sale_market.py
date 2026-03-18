"""Add club sale market tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0020_club_sale_market"
down_revision = "20260317_0019_creator_share_market"
branch_labels = None
depends_on = None

listing_status = sa.Enum(
    "active",
    "under_offer",
    "cancelled",
    "transferred",
    "expired",
    name="club_sale_listing_status",
    native_enum=False,
)
inquiry_status = sa.Enum(
    "open",
    "responded",
    "closed",
    "archived",
    "rejected",
    "closed_on_transfer",
    "withdrawn",
    name="club_sale_inquiry_status",
    native_enum=False,
)
offer_status = sa.Enum(
    "pending",
    "countered",
    "accepted",
    "rejected",
    "withdrawn",
    "superseded",
    "closed",
    "executed",
    "expired",
    name="club_sale_offer_status",
    native_enum=False,
)
transfer_status = sa.Enum(
    "pending",
    "settled",
    "cancelled",
    "failed",
    name="club_sale_transfer_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "club_valuation_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("computed_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("version_key", sa.String(length=48), server_default=sa.text("'club_sale_v1'"), nullable=False),
        sa.Column("total_value_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("first_team_value_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("reserve_squad_value_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("u19_squad_value_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("academy_value_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("stadium_value_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("paid_enhancements_value_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_improvements_value_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["computed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_valuation_snapshots"),
    )
    op.create_index("ix_club_valuation_snapshots_club_id", "club_valuation_snapshots", ["club_id"], unique=False)
    op.create_index("ix_club_valuation_snapshots_computed_by_user_id", "club_valuation_snapshots", ["computed_by_user_id"], unique=False)

    op.create_table(
        "club_sale_listings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("listing_id", sa.String(length=48), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("seller_user_id", sa.String(length=36), nullable=False),
        sa.Column("visibility", sa.String(length=24), server_default=sa.text("'public'"), nullable=False),
        sa.Column("status", listing_status, server_default=sa.text("'active'"), nullable=False),
        sa.Column("currency", sa.String(length=12), server_default=sa.text("'coin'"), nullable=False),
        sa.Column("asking_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("valuation_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("system_valuation_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("valuation_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("valuation_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["valuation_snapshot_id"], ["club_valuation_snapshots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_club_sale_listings"),
        sa.UniqueConstraint("listing_id", name="uq_club_sale_listings_listing_id"),
    )
    op.create_index("ix_club_sale_listings_club_status", "club_sale_listings", ["club_id", "status"], unique=False)
    op.create_index("ix_club_sale_listings_status_visibility", "club_sale_listings", ["status", "visibility"], unique=False)
    op.create_index("ix_club_sale_listings_seller_status", "club_sale_listings", ["seller_user_id", "status"], unique=False)

    op.create_table(
        "club_sale_inquiries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("inquiry_id", sa.String(length=48), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("seller_user_id", sa.String(length=36), nullable=False),
        sa.Column("buyer_user_id", sa.String(length=36), nullable=False),
        sa.Column("status", inquiry_status, server_default=sa.text("'open'"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("response_message", sa.Text(), nullable=True),
        sa.Column("responded_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["club_sale_listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seller_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_sale_inquiries"),
        sa.UniqueConstraint("inquiry_id", name="uq_club_sale_inquiries_inquiry_id"),
    )
    op.create_index("ix_club_sale_inquiries_club_status", "club_sale_inquiries", ["club_id", "status"], unique=False)
    op.create_index("ix_club_sale_inquiries_buyer_status", "club_sale_inquiries", ["buyer_user_id", "status"], unique=False)
    op.create_index("ix_club_sale_inquiries_seller_status", "club_sale_inquiries", ["seller_user_id", "status"], unique=False)

    op.create_table(
        "club_sale_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("offer_id", sa.String(length=48), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("inquiry_id", sa.String(length=36), nullable=True),
        sa.Column("parent_offer_id", sa.String(length=36), nullable=True),
        sa.Column("seller_user_id", sa.String(length=36), nullable=False),
        sa.Column("buyer_user_id", sa.String(length=36), nullable=False),
        sa.Column("proposer_user_id", sa.String(length=36), nullable=False),
        sa.Column("counterparty_user_id", sa.String(length=36), nullable=False),
        sa.Column("offer_type", sa.String(length=24), server_default=sa.text("'offer'"), nullable=False),
        sa.Column("status", offer_status, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("currency", sa.String(length=12), server_default=sa.text("'coin'"), nullable=False),
        sa.Column("offered_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("responded_message", sa.Text(), nullable=True),
        sa.Column("responded_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["club_sale_listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inquiry_id"], ["club_sale_inquiries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_offer_id"], ["club_sale_offers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seller_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["counterparty_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["responded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_sale_offers"),
        sa.UniqueConstraint("offer_id", name="uq_club_sale_offers_offer_id"),
    )
    op.create_index("ix_club_sale_offers_club_status", "club_sale_offers", ["club_id", "status"], unique=False)
    op.create_index("ix_club_sale_offers_buyer_status", "club_sale_offers", ["buyer_user_id", "status"], unique=False)
    op.create_index("ix_club_sale_offers_counterparty_status", "club_sale_offers", ["counterparty_user_id", "status"], unique=False)

    op.create_table(
        "club_sale_transfers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("transfer_id", sa.String(length=48), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("valuation_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("seller_user_id", sa.String(length=36), nullable=False),
        sa.Column("buyer_user_id", sa.String(length=36), nullable=False),
        sa.Column("currency", sa.String(length=12), server_default=sa.text("'coin'"), nullable=False),
        sa.Column("executed_sale_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("platform_fee_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("seller_net_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("status", transfer_status, server_default=sa.text("'settled'"), nullable=False),
        sa.Column("platform_fee_bps", sa.Integer(), server_default=sa.text("1000"), nullable=False),
        sa.Column("settlement_reference", sa.String(length=128), nullable=False),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["club_sale_listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["offer_id"], ["club_sale_offers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["valuation_snapshot_id"], ["club_valuation_snapshots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["seller_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_club_sale_transfers"),
        sa.UniqueConstraint("transfer_id", name="uq_club_sale_transfers_transfer_id"),
        sa.UniqueConstraint("offer_id", name="uq_club_sale_transfers_offer_id"),
        sa.UniqueConstraint("settlement_reference", name="uq_club_sale_transfers_settlement_reference"),
    )
    op.create_index("ix_club_sale_transfers_club_id", "club_sale_transfers", ["club_id"], unique=False)
    op.create_index("ix_club_sale_transfers_listing_id", "club_sale_transfers", ["listing_id"], unique=False)
    op.create_index("ix_club_sale_transfers_offer_id", "club_sale_transfers", ["offer_id"], unique=False)
    op.create_index("ix_club_sale_transfers_valuation_snapshot_id", "club_sale_transfers", ["valuation_snapshot_id"], unique=False)
    op.create_index("ix_club_sale_transfers_seller_user_id", "club_sale_transfers", ["seller_user_id"], unique=False)
    op.create_index("ix_club_sale_transfers_buyer_user_id", "club_sale_transfers", ["buyer_user_id"], unique=False)
    op.create_index("ix_club_sale_transfers_status", "club_sale_transfers", ["status"], unique=False)
    op.create_index("ix_club_sale_transfers_ledger_transaction_id", "club_sale_transfers", ["ledger_transaction_id"], unique=False)

    op.create_table(
        "club_sale_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("listing_id", sa.String(length=36), nullable=True),
        sa.Column("inquiry_id", sa.String(length=36), nullable=True),
        sa.Column("offer_id", sa.String(length=36), nullable=True),
        sa.Column("transfer_id", sa.String(length=36), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("status_from", sa.String(length=32), nullable=True),
        sa.Column("status_to", sa.String(length=32), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["club_sale_listings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inquiry_id"], ["club_sale_inquiries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["offer_id"], ["club_sale_offers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["transfer_id"], ["club_sale_transfers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_club_sale_audit_events"),
    )
    op.create_index("ix_club_sale_audit_events_club_action", "club_sale_audit_events", ["club_id", "action"], unique=False)
    op.create_index("ix_club_sale_audit_events_actor_user_id", "club_sale_audit_events", ["actor_user_id"], unique=False)
    op.create_index("ix_club_sale_audit_events_listing_id", "club_sale_audit_events", ["listing_id"], unique=False)
    op.create_index("ix_club_sale_audit_events_inquiry_id", "club_sale_audit_events", ["inquiry_id"], unique=False)
    op.create_index("ix_club_sale_audit_events_offer_id", "club_sale_audit_events", ["offer_id"], unique=False)
    op.create_index("ix_club_sale_audit_events_transfer_id", "club_sale_audit_events", ["transfer_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_club_sale_audit_events_transfer_id", table_name="club_sale_audit_events")
    op.drop_index("ix_club_sale_audit_events_offer_id", table_name="club_sale_audit_events")
    op.drop_index("ix_club_sale_audit_events_inquiry_id", table_name="club_sale_audit_events")
    op.drop_index("ix_club_sale_audit_events_listing_id", table_name="club_sale_audit_events")
    op.drop_index("ix_club_sale_audit_events_actor_user_id", table_name="club_sale_audit_events")
    op.drop_index("ix_club_sale_audit_events_club_action", table_name="club_sale_audit_events")
    op.drop_table("club_sale_audit_events")

    op.drop_index("ix_club_sale_transfers_ledger_transaction_id", table_name="club_sale_transfers")
    op.drop_index("ix_club_sale_transfers_status", table_name="club_sale_transfers")
    op.drop_index("ix_club_sale_transfers_buyer_user_id", table_name="club_sale_transfers")
    op.drop_index("ix_club_sale_transfers_seller_user_id", table_name="club_sale_transfers")
    op.drop_index("ix_club_sale_transfers_valuation_snapshot_id", table_name="club_sale_transfers")
    op.drop_index("ix_club_sale_transfers_offer_id", table_name="club_sale_transfers")
    op.drop_index("ix_club_sale_transfers_listing_id", table_name="club_sale_transfers")
    op.drop_index("ix_club_sale_transfers_club_id", table_name="club_sale_transfers")
    op.drop_table("club_sale_transfers")

    op.drop_index("ix_club_sale_offers_counterparty_status", table_name="club_sale_offers")
    op.drop_index("ix_club_sale_offers_buyer_status", table_name="club_sale_offers")
    op.drop_index("ix_club_sale_offers_club_status", table_name="club_sale_offers")
    op.drop_table("club_sale_offers")

    op.drop_index("ix_club_sale_inquiries_seller_status", table_name="club_sale_inquiries")
    op.drop_index("ix_club_sale_inquiries_buyer_status", table_name="club_sale_inquiries")
    op.drop_index("ix_club_sale_inquiries_club_status", table_name="club_sale_inquiries")
    op.drop_table("club_sale_inquiries")

    op.drop_index("ix_club_sale_listings_seller_status", table_name="club_sale_listings")
    op.drop_index("ix_club_sale_listings_status_visibility", table_name="club_sale_listings")
    op.drop_index("ix_club_sale_listings_club_status", table_name="club_sale_listings")
    op.drop_table("club_sale_listings")

    op.drop_index("ix_club_valuation_snapshots_computed_by_user_id", table_name="club_valuation_snapshots")
    op.drop_index("ix_club_valuation_snapshots_club_id", table_name="club_valuation_snapshots")
    op.drop_table("club_valuation_snapshots")
