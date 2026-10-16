"""Add creator league financial governance controls and settlement review fields."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260318_0026_creator_league_financial_governance"
down_revision = "20260318_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("creator_league_configs") as batch_op:
        batch_op.add_column(
            sa.Column("broadcast_purchases_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"))
        )
        batch_op.add_column(
            sa.Column("season_pass_sales_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"))
        )
        batch_op.add_column(
            sa.Column("match_gifting_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"))
        )
        batch_op.add_column(
            sa.Column("settlement_review_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"))
        )
        batch_op.add_column(
            sa.Column(
                "settlement_review_total_revenue_coin",
                sa.Numeric(18, 4),
                nullable=False,
                server_default="250.0000",
            )
        )
        batch_op.add_column(
            sa.Column(
                "settlement_review_creator_share_coin",
                sa.Numeric(18, 4),
                nullable=False,
                server_default="150.0000",
            )
        )
        batch_op.add_column(
            sa.Column(
                "settlement_review_platform_share_coin",
                sa.Numeric(18, 4),
                nullable=False,
                server_default="150.0000",
            )
        )
        batch_op.add_column(
            sa.Column(
                "settlement_review_shareholder_distribution_coin",
                sa.Numeric(18, 4),
                nullable=False,
                server_default="75.0000",
            )
        )

    with op.batch_alter_table("creator_club_share_market_controls") as batch_op:
        batch_op.add_column(sa.Column("issuance_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        batch_op.add_column(sa.Column("purchase_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        batch_op.add_column(
            sa.Column(
                "max_primary_purchase_value_coin",
                sa.Numeric(18, 4),
                nullable=False,
                server_default="2500.0000",
            )
        )

    with op.batch_alter_table("creator_stadium_controls") as batch_op:
        batch_op.add_column(sa.Column("ticket_sales_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        batch_op.add_column(
            sa.Column(
                "max_placement_price_coin",
                sa.Numeric(18, 4),
                nullable=False,
                server_default="250.0000",
            )
        )

    with op.batch_alter_table("creator_revenue_settlements") as batch_op:
        batch_op.add_column(
            sa.Column("review_status", sa.String(length=24), nullable=False, server_default="approved")
        )
        batch_op.add_column(
            sa.Column("review_reason_codes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )
        batch_op.add_column(
            sa.Column("policy_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
        )
        batch_op.add_column(sa.Column("reviewed_by_user_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("review_note", sa.String(length=255), nullable=True))
        batch_op.create_foreign_key(
            "fk_creator_revenue_settlements_reviewed_by_user_id_users",
            "users",
            ["reviewed_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_creator_revenue_settlements_review_status",
        "creator_revenue_settlements",
        ["review_status"],
        unique=False,
    )
    op.create_index(
        "ix_creator_revenue_settlements_reviewed_by_user_id",
        "creator_revenue_settlements",
        ["reviewed_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_creator_revenue_settlements_reviewed_by_user_id", table_name="creator_revenue_settlements")
    op.drop_index("ix_creator_revenue_settlements_review_status", table_name="creator_revenue_settlements")

    with op.batch_alter_table("creator_revenue_settlements") as batch_op:
        batch_op.drop_constraint("fk_creator_revenue_settlements_reviewed_by_user_id_users", type_="foreignkey")
        batch_op.drop_column("review_note")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by_user_id")
        batch_op.drop_column("policy_snapshot_json")
        batch_op.drop_column("review_reason_codes_json")
        batch_op.drop_column("review_status")

    with op.batch_alter_table("creator_stadium_controls") as batch_op:
        batch_op.drop_column("max_placement_price_coin")
        batch_op.drop_column("ticket_sales_enabled")

    with op.batch_alter_table("creator_club_share_market_controls") as batch_op:
        batch_op.drop_column("max_primary_purchase_value_coin")
        batch_op.drop_column("purchase_enabled")
        batch_op.drop_column("issuance_enabled")

    with op.batch_alter_table("creator_league_configs") as batch_op:
        batch_op.drop_column("settlement_review_shareholder_distribution_coin")
        batch_op.drop_column("settlement_review_platform_share_coin")
        batch_op.drop_column("settlement_review_creator_share_coin")
        batch_op.drop_column("settlement_review_total_revenue_coin")
        batch_op.drop_column("settlement_review_enabled")
        batch_op.drop_column("match_gifting_enabled")
        batch_op.drop_column("season_pass_sales_enabled")
        batch_op.drop_column("broadcast_purchases_enabled")
