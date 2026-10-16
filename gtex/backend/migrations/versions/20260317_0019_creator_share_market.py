"""Add creator club fan-share market tables and settlement signals."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260317_0019_creator_share_market"
down_revision = "20260317_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_club_share_market_controls",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("control_key", sa.String(length=32), server_default=sa.text("'default'"), nullable=False),
        sa.Column("max_shares_per_club", sa.Integer(), server_default=sa.text("10000"), nullable=False),
        sa.Column("max_shares_per_fan", sa.Integer(), server_default=sa.text("250"), nullable=False),
        sa.Column("shareholder_revenue_share_bps", sa.Integer(), server_default=sa.text("2000"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_creator_club_share_market_controls"),
        sa.UniqueConstraint("control_key", name="uq_creator_club_share_market_controls_control_key"),
    )

    op.create_table(
        "creator_club_share_markets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("issued_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'active'"), nullable=False),
        sa.Column("share_price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("max_shares_issued", sa.Integer(), nullable=False),
        sa.Column("shares_sold", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_shares_per_fan", sa.Integer(), nullable=False),
        sa.Column("creator_controlled_shares", sa.Integer(), nullable=False),
        sa.Column("shareholder_revenue_share_bps", sa.Integer(), nullable=False),
        sa.Column("total_purchase_volume_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("total_revenue_distributed_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_club_share_markets"),
        sa.UniqueConstraint("club_id", name="uq_creator_club_share_markets_club_id"),
    )
    op.create_index("ix_creator_club_share_markets_club_id", "creator_club_share_markets", ["club_id"], unique=False)
    op.create_index("ix_creator_club_share_markets_creator_user_id", "creator_club_share_markets", ["creator_user_id"], unique=False)
    op.create_index("ix_creator_club_share_markets_issued_by_user_id", "creator_club_share_markets", ["issued_by_user_id"], unique=False)

    op.create_table(
        "creator_club_share_holdings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("market_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("share_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_spent_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("revenue_earned_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["creator_club_share_markets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_club_share_holdings"),
        sa.UniqueConstraint("club_id", "user_id", name="uq_creator_club_share_holdings_club_user"),
    )
    op.create_index("ix_creator_club_share_holdings_market_id", "creator_club_share_holdings", ["market_id"], unique=False)
    op.create_index("ix_creator_club_share_holdings_club_id", "creator_club_share_holdings", ["club_id"], unique=False)
    op.create_index("ix_creator_club_share_holdings_user_id", "creator_club_share_holdings", ["user_id"], unique=False)

    op.create_table(
        "creator_club_share_purchases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("market_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("share_count", sa.Integer(), nullable=False),
        sa.Column("share_price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_price_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["creator_club_share_markets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_club_share_purchases"),
    )
    op.create_index("ix_creator_club_share_purchases_market_id", "creator_club_share_purchases", ["market_id"], unique=False)
    op.create_index("ix_creator_club_share_purchases_club_id", "creator_club_share_purchases", ["club_id"], unique=False)
    op.create_index("ix_creator_club_share_purchases_creator_user_id", "creator_club_share_purchases", ["creator_user_id"], unique=False)
    op.create_index("ix_creator_club_share_purchases_user_id", "creator_club_share_purchases", ["user_id"], unique=False)
    op.create_index("ix_creator_club_share_purchases_ledger_transaction_id", "creator_club_share_purchases", ["ledger_transaction_id"], unique=False)

    op.create_table(
        "creator_club_share_distributions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("market_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("creator_user_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("source_reference_id", sa.String(length=36), nullable=False),
        sa.Column("season_id", sa.String(length=36), nullable=True),
        sa.Column("competition_id", sa.String(length=36), nullable=True),
        sa.Column("match_id", sa.String(length=36), nullable=True),
        sa.Column("eligible_revenue_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("shareholder_pool_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("creator_retained_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("shareholder_revenue_share_bps", sa.Integer(), nullable=False),
        sa.Column("distributed_share_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("recipient_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'settled'"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["creator_club_share_markets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["creator_league_seasons.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["competition_id"], ["user_competitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["match_id"], ["competition_matches.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_club_share_distributions"),
        sa.UniqueConstraint(
            "club_id",
            "source_type",
            "source_reference_id",
            name="uq_creator_club_share_distributions_club_source_ref",
        ),
    )
    op.create_index("ix_creator_club_share_distributions_market_id", "creator_club_share_distributions", ["market_id"], unique=False)
    op.create_index("ix_creator_club_share_distributions_club_id", "creator_club_share_distributions", ["club_id"], unique=False)
    op.create_index("ix_creator_club_share_distributions_creator_user_id", "creator_club_share_distributions", ["creator_user_id"], unique=False)
    op.create_index("ix_creator_club_share_distributions_source_type", "creator_club_share_distributions", ["source_type"], unique=False)
    op.create_index("ix_creator_club_share_distributions_source_reference_id", "creator_club_share_distributions", ["source_reference_id"], unique=False)
    op.create_index("ix_creator_club_share_distributions_season_id", "creator_club_share_distributions", ["season_id"], unique=False)
    op.create_index("ix_creator_club_share_distributions_competition_id", "creator_club_share_distributions", ["competition_id"], unique=False)
    op.create_index("ix_creator_club_share_distributions_match_id", "creator_club_share_distributions", ["match_id"], unique=False)

    op.create_table(
        "creator_club_share_payouts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("distribution_id", sa.String(length=36), nullable=False),
        sa.Column("holding_id", sa.String(length=36), nullable=True),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("share_count", sa.Integer(), nullable=False),
        sa.Column("payout_coin", sa.Numeric(18, 4), nullable=False),
        sa.Column("ownership_bps", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ledger_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["distribution_id"], ["creator_club_share_distributions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["holding_id"], ["creator_club_share_holdings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_creator_club_share_payouts"),
        sa.UniqueConstraint("distribution_id", "user_id", name="uq_creator_club_share_payouts_distribution_user"),
    )
    op.create_index("ix_creator_club_share_payouts_distribution_id", "creator_club_share_payouts", ["distribution_id"], unique=False)
    op.create_index("ix_creator_club_share_payouts_holding_id", "creator_club_share_payouts", ["holding_id"], unique=False)
    op.create_index("ix_creator_club_share_payouts_club_id", "creator_club_share_payouts", ["club_id"], unique=False)
    op.create_index("ix_creator_club_share_payouts_user_id", "creator_club_share_payouts", ["user_id"], unique=False)
    op.create_index("ix_creator_club_share_payouts_ledger_transaction_id", "creator_club_share_payouts", ["ledger_transaction_id"], unique=False)

    with op.batch_alter_table("creator_revenue_settlements") as batch_op:
        batch_op.add_column(sa.Column("shareholder_match_video_distribution_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("shareholder_gift_distribution_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("shareholder_ticket_sales_distribution_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))
        batch_op.add_column(sa.Column("shareholder_total_distribution_coin", sa.Numeric(18, 4), server_default=sa.text("0.0000"), nullable=False))

    old_qualification_type = sa.Enum("invite", "playoffs", "season_pass", "top_gifter", name="streamertournamentqualificationtype")
    new_qualification_type = sa.Enum("invite", "playoffs", "season_pass", "shareholder", "top_gifter", name="streamertournamentqualificationtype")
    with op.batch_alter_table("streamer_tournament_entries") as batch_op:
        batch_op.alter_column(
            "qualification_source",
            existing_type=old_qualification_type,
            type_=new_qualification_type,
            existing_nullable=False,
        )


def downgrade() -> None:
    old_qualification_type = sa.Enum("invite", "playoffs", "season_pass", "top_gifter", name="streamertournamentqualificationtype")
    new_qualification_type = sa.Enum("invite", "playoffs", "season_pass", "shareholder", "top_gifter", name="streamertournamentqualificationtype")
    with op.batch_alter_table("streamer_tournament_entries") as batch_op:
        batch_op.alter_column(
            "qualification_source",
            existing_type=new_qualification_type,
            type_=old_qualification_type,
            existing_nullable=False,
        )

    with op.batch_alter_table("creator_revenue_settlements") as batch_op:
        batch_op.drop_column("shareholder_total_distribution_coin")
        batch_op.drop_column("shareholder_ticket_sales_distribution_coin")
        batch_op.drop_column("shareholder_gift_distribution_coin")
        batch_op.drop_column("shareholder_match_video_distribution_coin")

    op.drop_index("ix_creator_club_share_payouts_ledger_transaction_id", table_name="creator_club_share_payouts")
    op.drop_index("ix_creator_club_share_payouts_user_id", table_name="creator_club_share_payouts")
    op.drop_index("ix_creator_club_share_payouts_club_id", table_name="creator_club_share_payouts")
    op.drop_index("ix_creator_club_share_payouts_holding_id", table_name="creator_club_share_payouts")
    op.drop_index("ix_creator_club_share_payouts_distribution_id", table_name="creator_club_share_payouts")
    op.drop_table("creator_club_share_payouts")

    op.drop_index("ix_creator_club_share_distributions_match_id", table_name="creator_club_share_distributions")
    op.drop_index("ix_creator_club_share_distributions_competition_id", table_name="creator_club_share_distributions")
    op.drop_index("ix_creator_club_share_distributions_season_id", table_name="creator_club_share_distributions")
    op.drop_index("ix_creator_club_share_distributions_source_reference_id", table_name="creator_club_share_distributions")
    op.drop_index("ix_creator_club_share_distributions_source_type", table_name="creator_club_share_distributions")
    op.drop_index("ix_creator_club_share_distributions_creator_user_id", table_name="creator_club_share_distributions")
    op.drop_index("ix_creator_club_share_distributions_club_id", table_name="creator_club_share_distributions")
    op.drop_index("ix_creator_club_share_distributions_market_id", table_name="creator_club_share_distributions")
    op.drop_table("creator_club_share_distributions")

    op.drop_index("ix_creator_club_share_purchases_ledger_transaction_id", table_name="creator_club_share_purchases")
    op.drop_index("ix_creator_club_share_purchases_user_id", table_name="creator_club_share_purchases")
    op.drop_index("ix_creator_club_share_purchases_creator_user_id", table_name="creator_club_share_purchases")
    op.drop_index("ix_creator_club_share_purchases_club_id", table_name="creator_club_share_purchases")
    op.drop_index("ix_creator_club_share_purchases_market_id", table_name="creator_club_share_purchases")
    op.drop_table("creator_club_share_purchases")

    op.drop_index("ix_creator_club_share_holdings_user_id", table_name="creator_club_share_holdings")
    op.drop_index("ix_creator_club_share_holdings_club_id", table_name="creator_club_share_holdings")
    op.drop_index("ix_creator_club_share_holdings_market_id", table_name="creator_club_share_holdings")
    op.drop_table("creator_club_share_holdings")

    op.drop_index("ix_creator_club_share_markets_issued_by_user_id", table_name="creator_club_share_markets")
    op.drop_index("ix_creator_club_share_markets_creator_user_id", table_name="creator_club_share_markets")
    op.drop_index("ix_creator_club_share_markets_club_id", table_name="creator_club_share_markets")
    op.drop_table("creator_club_share_markets")

    op.drop_table("creator_club_share_market_controls")
