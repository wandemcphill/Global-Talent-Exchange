"""Add broadcast rights and multi-club ownership groups.

Revision ID: 20260327_0045_broadcast_rights_and_ownership_groups
Revises: 20260327_0044_national_team_marketplace_expansion
Create Date: 2026-03-27 23:55:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_0045_broadcast_rights_and_ownership_groups"
down_revision = "20260327_0044_national_team_marketplace_expansion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broadcast_rights",
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("acquisition_price", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("revenue_share_percentage", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("exclusivity", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_broadcast_rights")),
    )
    op.create_index("ix_broadcast_rights_competition_id", "broadcast_rights", ["competition_id"], unique=False)
    op.create_index("ix_broadcast_rights_owner_id", "broadcast_rights", ["owner_id"], unique=False)
    op.create_index("ix_broadcast_rights_exclusivity", "broadcast_rights", ["exclusivity"], unique=False)
    op.create_index("ix_broadcast_rights_start_date", "broadcast_rights", ["start_date"], unique=False)
    op.create_index("ix_broadcast_rights_end_date", "broadcast_rights", ["end_date"], unique=False)

    op.create_table(
        "broadcast_rights_auctions",
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("seller_owner_id", sa.String(length=36), nullable=False),
        sa.Column("reserve_price", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("revenue_share_percentage", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("exclusivity", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="open"),
        sa.Column("winning_right_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winning_right_id"], ["broadcast_rights.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_broadcast_rights_auctions")),
    )
    op.create_index(
        "ix_broadcast_rights_auctions_competition_id",
        "broadcast_rights_auctions",
        ["competition_id"],
        unique=False,
    )
    op.create_index(
        "ix_broadcast_rights_auctions_seller_owner_id",
        "broadcast_rights_auctions",
        ["seller_owner_id"],
        unique=False,
    )
    op.create_index("ix_broadcast_rights_auctions_status", "broadcast_rights_auctions", ["status"], unique=False)

    op.create_table(
        "broadcast_rights_bids",
        sa.Column("auction_id", sa.String(length=36), nullable=False),
        sa.Column("bidder_user_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="submitted"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["auction_id"], ["broadcast_rights_auctions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bidder_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_broadcast_rights_bids")),
        sa.UniqueConstraint("auction_id", "bidder_user_id", name="uq_broadcast_rights_bids_auction_bidder"),
    )
    op.create_index("ix_broadcast_rights_bids_auction_id", "broadcast_rights_bids", ["auction_id"], unique=False)
    op.create_index("ix_broadcast_rights_bids_status", "broadcast_rights_bids", ["status"], unique=False)

    op.create_table(
        "broadcast_access_grants",
        sa.Column("broadcast_right_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("granted_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["broadcast_right_id"], ["broadcast_rights.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_broadcast_access_grants")),
        sa.UniqueConstraint("broadcast_right_id", "user_id", name="uq_broadcast_access_grants_right_user"),
    )
    op.create_index("ix_broadcast_access_grants_user_id", "broadcast_access_grants", ["user_id"], unique=False)

    op.create_table(
        "view_sessions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("match_id", sa.String(length=120), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("paid_amount", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_view_sessions")),
        sa.UniqueConstraint("match_id", "user_id", name="uq_view_sessions_match_user"),
    )
    op.create_index("ix_view_sessions_match_id", "view_sessions", ["match_id"], unique=False)
    op.create_index("ix_view_sessions_competition_id", "view_sessions", ["competition_id"], unique=False)

    op.create_table(
        "broadcast_revenue_distributions",
        sa.Column("match_id", sa.String(length=120), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("broadcast_right_id", sa.String(length=36), nullable=True),
        sa.Column("recipient_type", sa.String(length=24), nullable=False),
        sa.Column("recipient_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("reference_key", sa.String(length=160), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["broadcast_right_id"], ["broadcast_rights.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_broadcast_revenue_distributions")),
        sa.UniqueConstraint("reference_key", name="uq_broadcast_revenue_distributions_reference_key"),
    )
    op.create_index(
        "ix_broadcast_revenue_distributions_match_id",
        "broadcast_revenue_distributions",
        ["match_id"],
        unique=False,
    )
    op.create_index(
        "ix_broadcast_revenue_distributions_recipient_id",
        "broadcast_revenue_distributions",
        ["recipient_id"],
        unique=False,
    )
    op.create_index(
        "ix_broadcast_revenue_distributions_recipient_type",
        "broadcast_revenue_distributions",
        ["recipient_type"],
        unique=False,
    )

    op.create_table(
        "ownership_groups",
        sa.Column("owner_user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("clubs_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("budget_pool", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("reputation_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("philosophy", sa.String(length=120), nullable=True),
        sa.Column("global_brand_strength", sa.Float(), nullable=False, server_default="0"),
        sa.Column("shared_budget_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ownership_groups")),
        sa.UniqueConstraint("owner_user_id", "name", name="uq_ownership_groups_owner_name"),
    )
    op.create_index("ix_ownership_groups_owner_user_id", "ownership_groups", ["owner_user_id"], unique=False)

    op.create_table(
        "ownership_group_clubs",
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["ownership_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ownership_group_clubs")),
        sa.UniqueConstraint("group_id", "club_id", name="uq_ownership_group_clubs_group_club"),
        sa.UniqueConstraint("club_id", name="uq_ownership_group_clubs_club_id"),
    )
    op.create_index("ix_ownership_group_clubs_group_id", "ownership_group_clubs", ["group_id"], unique=False)

    op.create_table(
        "ownership_group_budget_movements",
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("source_club_id", sa.String(length=36), nullable=True),
        sa.Column("target_club_id", sa.String(length=36), nullable=True),
        sa.Column("movement_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
        sa.Column("reference_key", sa.String(length=160), nullable=False),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["ownership_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ownership_group_budget_movements")),
        sa.UniqueConstraint("reference_key", name="uq_ownership_group_budget_movements_reference_key"),
    )
    op.create_index(
        "ix_ownership_group_budget_movements_group_id",
        "ownership_group_budget_movements",
        ["group_id"],
        unique=False,
    )
    op.create_index(
        "ix_ownership_group_budget_movements_movement_type",
        "ownership_group_budget_movements",
        ["movement_type"],
        unique=False,
    )

    op.create_table(
        "ownership_group_events",
        sa.Column("group_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("headline", sa.String(length=255), nullable=False),
        sa.Column("impact_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["group_id"], ["ownership_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ownership_group_events")),
    )
    op.create_index("ix_ownership_group_events_group_id", "ownership_group_events", ["group_id"], unique=False)
    op.create_index("ix_ownership_group_events_event_type", "ownership_group_events", ["event_type"], unique=False)

    with op.batch_alter_table("club_finance_profiles", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column("broadcast_income", sa.Numeric(18, 4), nullable=False, server_default="0.0000")
        )


def downgrade() -> None:
    with op.batch_alter_table("club_finance_profiles", recreate="auto") as batch_op:
        batch_op.drop_column("broadcast_income")

    op.drop_index("ix_ownership_group_events_event_type", table_name="ownership_group_events")
    op.drop_index("ix_ownership_group_events_group_id", table_name="ownership_group_events")
    op.drop_table("ownership_group_events")

    op.drop_index("ix_ownership_group_budget_movements_movement_type", table_name="ownership_group_budget_movements")
    op.drop_index("ix_ownership_group_budget_movements_group_id", table_name="ownership_group_budget_movements")
    op.drop_table("ownership_group_budget_movements")

    op.drop_index("ix_ownership_group_clubs_group_id", table_name="ownership_group_clubs")
    op.drop_table("ownership_group_clubs")

    op.drop_index("ix_ownership_groups_owner_user_id", table_name="ownership_groups")
    op.drop_table("ownership_groups")

    op.drop_index(
        "ix_broadcast_revenue_distributions_recipient_type",
        table_name="broadcast_revenue_distributions",
    )
    op.drop_index(
        "ix_broadcast_revenue_distributions_recipient_id",
        table_name="broadcast_revenue_distributions",
    )
    op.drop_index("ix_broadcast_revenue_distributions_match_id", table_name="broadcast_revenue_distributions")
    op.drop_table("broadcast_revenue_distributions")

    op.drop_index("ix_view_sessions_competition_id", table_name="view_sessions")
    op.drop_index("ix_view_sessions_match_id", table_name="view_sessions")
    op.drop_table("view_sessions")

    op.drop_index("ix_broadcast_access_grants_user_id", table_name="broadcast_access_grants")
    op.drop_table("broadcast_access_grants")

    op.drop_index("ix_broadcast_rights_bids_status", table_name="broadcast_rights_bids")
    op.drop_index("ix_broadcast_rights_bids_auction_id", table_name="broadcast_rights_bids")
    op.drop_table("broadcast_rights_bids")

    op.drop_index("ix_broadcast_rights_auctions_status", table_name="broadcast_rights_auctions")
    op.drop_index("ix_broadcast_rights_auctions_seller_owner_id", table_name="broadcast_rights_auctions")
    op.drop_index("ix_broadcast_rights_auctions_competition_id", table_name="broadcast_rights_auctions")
    op.drop_table("broadcast_rights_auctions")

    op.drop_index("ix_broadcast_rights_end_date", table_name="broadcast_rights")
    op.drop_index("ix_broadcast_rights_start_date", table_name="broadcast_rights")
    op.drop_index("ix_broadcast_rights_exclusivity", table_name="broadcast_rights")
    op.drop_index("ix_broadcast_rights_owner_id", table_name="broadcast_rights")
    op.drop_index("ix_broadcast_rights_competition_id", table_name="broadcast_rights")
    op.drop_table("broadcast_rights")
