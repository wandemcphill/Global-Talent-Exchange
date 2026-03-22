"""Add ledger source tags, gift scope, and user region profiles."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260315_0002"
down_revision = "20260311_0001"
branch_labels = None
depends_on = None

ledger_source_tag = sa.Enum(
    "fancoin_purchase",
    "market_topup",
    "platform_competition_reward",
    "national_competition_reward",
    "gtex_platform_gift_income",
    "user_hosted_gift_income_fancoin",
    "match_view_revenue",
    "hosting_fee_spend",
    "user_competition_entry_spend",
    "video_view_spend",
    "stadium_upgrade_spend",
    "cosmetic_spend",
    "player_card_sale",
    "player_card_purchase",
    "trading_fee_burn",
    "gift_rake_burn",
    "withdrawal_fee_burn",
    "promo_pool_credit",
    "admin_adjustment",
    "highlight_download_spend",
    name="ledger_source_tag",
    native_enum=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    ledger_source_tag.create(bind, checkfirst=True)
    ledger_entry_columns = {
        column["name"] for column in inspector.get_columns("ledger_entries")
    }
    if "source_tag" not in ledger_entry_columns:
        op.add_column(
            "ledger_entries",
            sa.Column(
                "source_tag",
                ledger_source_tag,
                nullable=False,
                server_default="admin_adjustment",
            ),
        )
    if "gift_transactions" in existing_tables:
        gift_transaction_columns = {
            column["name"] for column in inspector.get_columns("gift_transactions")
        }
        if "source_scope" not in gift_transaction_columns:
            op.add_column(
                "gift_transactions",
                sa.Column(
                    "source_scope",
                    sa.String(length=32),
                    nullable=False,
                    server_default="user_hosted",
                ),
            )
    op.create_table(
        "user_region_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("region_code", sa.String(length=8), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("change_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("permanent_locked", sa.Boolean(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_region_profiles_user_id"),
    )
    op.create_index("ix_user_region_profiles_user_id", "user_region_profiles", ["user_id"])
    op.create_index("ix_user_region_profiles_region_code", "user_region_profiles", ["region_code"])


def downgrade() -> None:
    op.drop_index("ix_user_region_profiles_region_code", table_name="user_region_profiles")
    op.drop_index("ix_user_region_profiles_user_id", table_name="user_region_profiles")
    op.drop_table("user_region_profiles")
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "gift_transactions" in existing_tables:
        gift_transaction_columns = {
            column["name"] for column in inspector.get_columns("gift_transactions")
        }
        if "source_scope" in gift_transaction_columns:
            op.drop_column("gift_transactions", "source_scope")
    ledger_entry_columns = {
        column["name"] for column in inspector.get_columns("ledger_entries")
    }
    if "source_tag" in ledger_entry_columns:
        op.drop_column("ledger_entries", "source_tag")
    ledger_source_tag.drop(bind, checkfirst=True)
