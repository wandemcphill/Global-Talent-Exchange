"""Rebuild public identity, compliance, club lifecycle, and trader schema.

Revision ID: 20260518_0090_identity_trader_rebuild
Revises: 20260501_0089_national_team_rental_owners
Create Date: 2026-05-18 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260518_0090_identity_trader_rebuild"
down_revision = "20260501_0089_national_team_rental_owners"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "account_type",
                sa.Enum("user", "creator", "coin_trader", name="public_account_type", native_enum=False),
                nullable=False,
                server_default="user",
            )
        )
        batch_op.create_index("ix_users_account_type", ["account_type"], unique=False)

    with op.batch_alter_table("club_profiles") as batch_op:
        batch_op.add_column(
            sa.Column(
                "club_type",
                sa.Enum("academy", "professional", "community", "street_team", name="club_type", native_enum=False),
                nullable=False,
                server_default="community",
            )
        )
        batch_op.add_column(
            sa.Column(
                "lifecycle_status",
                sa.Enum("active", "archived_generated", name="club_lifecycle_status", native_enum=False),
                nullable=False,
                server_default="active",
            )
        )
        batch_op.create_index("ix_club_profiles_lifecycle_status", ["lifecycle_status"], unique=False)

    op.execute(
        "UPDATE club_profiles SET lifecycle_status = 'archived_generated' "
        "WHERE club_name LIKE '% FC' AND (home_venue_name LIKE '% Arena' OR description LIKE 'Creator club provisioned for %')"
    )

    with op.batch_alter_table("kyc_profiles") as batch_op:
        batch_op.add_column(sa.Column("government_id_attachment_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("selfie_attachment_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("proof_of_address_attachment_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("country_confirmation", sa.String(length=120), nullable=True))

    op.execute(
        """
        UPDATE kyc_profiles
        SET status = CASE
            WHEN status = 'unverified' THEN 'pending'
            WHEN status = 'pending' THEN 'under_review'
            WHEN status IN ('partial_verified_no_id', 'fully_verified') THEN 'verified'
            ELSE status
        END
        WHERE status IN ('unverified', 'pending', 'partial_verified_no_id', 'fully_verified')
        """
    )
    op.execute(
        """
        UPDATE users
        SET kyc_status = CASE
            WHEN kyc_status = 'unverified' THEN 'pending'
            WHEN kyc_status = 'pending' THEN 'under_review'
            WHEN kyc_status IN ('partial_verified_no_id', 'fully_verified') THEN 'verified'
            ELSE kyc_status
        END
        WHERE kyc_status IN ('unverified', 'pending', 'partial_verified_no_id', 'fully_verified')
        """
    )

    with op.batch_alter_table("creator_club_provisioning") as batch_op:
        batch_op.alter_column("club_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.alter_column("stadium_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.alter_column("creator_squad_id", existing_type=sa.String(length=36), nullable=True)
        batch_op.alter_column("creator_regen_id", existing_type=sa.String(length=36), nullable=True)

    op.create_table(
        "trader_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("trading_alias", sa.String(length=120), nullable=False),
        sa.Column("preferred_currency", sa.String(length=12), server_default="USD", nullable=False),
        sa.Column(
            "trading_experience",
            sa.Enum("beginner", "intermediate", "professional", name="trader_experience", native_enum=False),
            server_default="beginner",
            nullable=False,
        ),
        sa.Column("interests_json", sa.JSON(), nullable=False),
        sa.Column("wallet_label", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), server_default="active", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trading_alias", name="uq_trader_profiles_trading_alias"),
        sa.UniqueConstraint("user_id", name="uq_trader_profiles_user_id"),
    )
    op.create_index("ix_trader_profiles_user_id", "trader_profiles", ["user_id"], unique=False)

    op.create_table(
        "trader_security",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("totp_secret_hash", sa.String(length=255), nullable=False),
        sa.Column("two_factor_enabled", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("backup_codes_json", sa.JSON(), nullable=False),
        sa.Column("recovery_phrase_hash", sa.String(length=255), nullable=False),
        sa.Column("security_pin_hash", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_trader_security_user_id"),
    )
    op.create_index("ix_trader_security_user_id", "trader_security", ["user_id"], unique=False)

    op.create_table(
        "trader_markets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("asset_type", sa.String(length=24), server_default="gtex_coin", nullable=False),
        sa.Column("price", sa.Numeric(18, 4), nullable=False),
        sa.Column("daily_change_percent", sa.Numeric(8, 4), nullable=False),
        sa.Column("market_cap", sa.Numeric(18, 4), nullable=False),
        sa.Column("volume_24h", sa.Numeric(18, 4), nullable=False),
        sa.Column("liquidity_score", sa.Integer(), server_default="50", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", name="uq_trader_markets_symbol"),
    )
    op.create_index("ix_trader_markets_symbol", "trader_markets", ["symbol"], unique=False)

    op.create_table(
        "trader_price_ticks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_id", sa.String(length=36), nullable=False),
        sa.Column("open_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("high_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("low_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("volume", sa.Numeric(18, 4), nullable=False),
        sa.Column("timeframe", sa.String(length=12), server_default="1h", nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["trader_markets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trader_price_ticks_market_created", "trader_price_ticks", ["market_id", "created_at"], unique=False)

    op.create_table(
        "trader_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("market_id", sa.String(length=36), nullable=False),
        sa.Column("side", sa.Enum("buy", "sell", "convert", name="trader_order_side", native_enum=False), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "filled", "cancelled", name="trader_order_status", native_enum=False),
            server_default="open",
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("limit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["trader_markets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trader_orders_user_status", "trader_orders", ["user_id", "status"], unique=False)

    op.create_table(
        "trader_p2p_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("market_id", sa.String(length=36), nullable=False),
        sa.Column("side", sa.Enum("buy", "sell", "convert", name="trader_p2p_side", native_enum=False), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "matched", "cancelled", name="trader_p2p_status", native_enum=False),
            server_default="open",
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("preferred_currency", sa.String(length=12), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["trader_markets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trader_p2p_offers_user_status", "trader_p2p_offers", ["user_id", "status"], unique=False)

    op.create_table(
        "trader_watchlists",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("market_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["trader_markets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "market_id", name="uq_trader_watchlists_user_market"),
    )
    op.create_index("ix_trader_watchlists_user_id", "trader_watchlists", ["user_id"], unique=False)

    op.create_table(
        "trader_security_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trader_security_events_user_created", "trader_security_events", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_trader_security_events_user_created", table_name="trader_security_events")
    op.drop_table("trader_security_events")
    op.drop_index("ix_trader_watchlists_user_id", table_name="trader_watchlists")
    op.drop_table("trader_watchlists")
    op.drop_index("ix_trader_p2p_offers_user_status", table_name="trader_p2p_offers")
    op.drop_table("trader_p2p_offers")
    op.drop_index("ix_trader_orders_user_status", table_name="trader_orders")
    op.drop_table("trader_orders")
    op.drop_index("ix_trader_price_ticks_market_created", table_name="trader_price_ticks")
    op.drop_table("trader_price_ticks")
    op.drop_index("ix_trader_markets_symbol", table_name="trader_markets")
    op.drop_table("trader_markets")
    op.drop_index("ix_trader_security_user_id", table_name="trader_security")
    op.drop_table("trader_security")
    op.drop_index("ix_trader_profiles_user_id", table_name="trader_profiles")
    op.drop_table("trader_profiles")

    with op.batch_alter_table("creator_club_provisioning") as batch_op:
        batch_op.alter_column("creator_regen_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.alter_column("creator_squad_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.alter_column("stadium_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.alter_column("club_id", existing_type=sa.String(length=36), nullable=False)

    with op.batch_alter_table("kyc_profiles") as batch_op:
        batch_op.drop_column("country_confirmation")
        batch_op.drop_column("proof_of_address_attachment_id")
        batch_op.drop_column("selfie_attachment_id")
        batch_op.drop_column("government_id_attachment_id")

    with op.batch_alter_table("club_profiles") as batch_op:
        batch_op.drop_index("ix_club_profiles_lifecycle_status")
        batch_op.drop_column("lifecycle_status")
        batch_op.drop_column("club_type")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_account_type")
        batch_op.drop_column("account_type")
