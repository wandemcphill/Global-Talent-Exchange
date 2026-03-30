"""Repair runtime schema drift on databases shipped behind migration head.

Revision ID: 20260330_0074_player_share_market_schema_repair
Revises: 20260329_0073_social_warfare_layer
Create Date: 2026-03-30 08:40:00.000000
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260330_0074_player_share_market_schema_repair"
down_revision = "20260329_0073_social_warfare_layer"
branch_labels = None
depends_on = None

PLAYER_SHARE_DEFAULT_TOTAL_SHARES = 1000
PLAYER_SHARE_DEFAULT_PRICE = Decimal("0.0750")
PLAYER_SHARE_MIN_PRICE = Decimal("0.0500")
PLAYER_SHARE_MAX_PRICE = Decimal("5.0000")


def _index_names(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _create_index_if_missing(
    bind,
    *,
    table_name: str,
    index_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:
    if index_name not in _index_names(bind, table_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _drop_index_if_exists(bind, *, table_name: str, index_name: str) -> None:
    if index_name in _index_names(bind, table_name):
        op.drop_index(index_name, table_name=table_name)


def _derive_market_price(reference_value: object) -> Decimal:
    try:
        normalized = Decimal(str(reference_value))
    except (InvalidOperation, TypeError, ValueError):
        return PLAYER_SHARE_DEFAULT_PRICE
    if normalized <= Decimal("0"):
        return PLAYER_SHARE_DEFAULT_PRICE
    scaled = (normalized / Decimal("100000000")).quantize(Decimal("0.0001"))
    if scaled < PLAYER_SHARE_MIN_PRICE:
        return PLAYER_SHARE_MIN_PRICE
    if scaled > PLAYER_SHARE_MAX_PRICE:
        return PLAYER_SHARE_MAX_PRICE
    return scaled


def _backfill_player_share_markets(bind) -> None:
    inspector = sa.inspect(bind)
    required_tables = {
        "ingestion_players",
        "real_player_profiles",
        "player_share_markets",
        "player_share_events",
    }
    if not required_tables.issubset(set(inspector.get_table_names())):
        return

    rows = bind.execute(
        sa.text(
            """
            SELECT
                p.id AS player_id,
                COALESCE(p.canonical_display_name, p.full_name, r.canonical_name) AS player_name,
                COALESCE(r.current_market_reference_value, p.current_market_reference_value, p.market_value_eur) AS reference_value
            FROM ingestion_players AS p
            JOIN real_player_profiles AS r
                ON r.gtex_player_id = p.id
            LEFT JOIN player_share_markets AS m
                ON m.player_id = p.id
            WHERE p.is_real_player = :is_real_player
              AND m.id IS NULL
            ORDER BY p.updated_at DESC, p.created_at DESC
            """
        ),
        {"is_real_player": True},
    ).mappings().all()
    if not rows:
        return

    markets_table = sa.table(
        "player_share_markets",
        sa.column("id", sa.String(length=36)),
        sa.column("player_id", sa.String(length=36)),
        sa.column("total_shares", sa.Integer()),
        sa.column("circulating_shares", sa.Integer()),
        sa.column("share_price_coin", sa.Numeric(18, 4)),
        sa.column("status", sa.String(length=24)),
        sa.column("revenue_distributed_coin", sa.Numeric(18, 4)),
        sa.column("metadata_json", sa.JSON()),
    )
    events_table = sa.table(
        "player_share_events",
        sa.column("id", sa.String(length=36)),
        sa.column("player_id", sa.String(length=36)),
        sa.column("user_id", sa.String(length=36)),
        sa.column("actor_user_id", sa.String(length=36)),
        sa.column("event_type", sa.String(length=32)),
        sa.column("share_delta", sa.Integer()),
        sa.column("price_per_share_coin", sa.Numeric(18, 4)),
        sa.column("gross_amount_coin", sa.Numeric(18, 4)),
        sa.column("metadata_json", sa.JSON()),
    )

    market_rows: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    for row in rows:
        price = _derive_market_price(row["reference_value"])
        market_rows.append(
            {
                "id": str(uuid.uuid4()),
                "player_id": str(row["player_id"]),
                "total_shares": PLAYER_SHARE_DEFAULT_TOTAL_SHARES,
                "circulating_shares": 0,
                "share_price_coin": price,
                "status": "active",
                "revenue_distributed_coin": Decimal("0.0000"),
                "metadata_json": {
                    "player_name": str(row["player_name"] or ""),
                    "backfilled_by_migration": revision,
                    "pricing_strategy": "default_seeded_market",
                },
            }
        )
        event_rows.append(
            {
                "id": str(uuid.uuid4()),
                "player_id": str(row["player_id"]),
                "user_id": None,
                "actor_user_id": None,
                "event_type": "issue",
                "share_delta": 0,
                "price_per_share_coin": price,
                "gross_amount_coin": Decimal("0.0000"),
                "metadata_json": {
                    "backfilled_by_migration": revision,
                    "status": "active",
                    "total_shares": PLAYER_SHARE_DEFAULT_TOTAL_SHARES,
                },
            }
        )

    op.bulk_insert(markets_table, market_rows)
    op.bulk_insert(events_table, event_rows)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("player_share_markets"):
        op.create_table(
            "player_share_markets",
            sa.Column("player_id", sa.String(length=36), nullable=False),
            sa.Column("total_shares", sa.Integer(), nullable=False, server_default="1000"),
            sa.Column("circulating_shares", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("share_price_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
            sa.Column("revenue_distributed_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_player_share_markets")),
            sa.UniqueConstraint("player_id", name="uq_player_share_markets_player_id"),
        )

    if not inspector.has_table("player_share_holdings"):
        op.create_table(
            "player_share_holdings",
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("player_id", sa.String(length=36), nullable=False),
            sa.Column("share_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("average_cost_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
            sa.Column("dividends_earned_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_player_share_holdings")),
            sa.UniqueConstraint("user_id", "player_id", name="uq_player_share_holdings_user_player"),
        )

    if not inspector.has_table("player_share_events"):
        op.create_table(
            "player_share_events",
            sa.Column("player_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=True),
            sa.Column("actor_user_id", sa.String(length=36), nullable=True),
            sa.Column("event_type", sa.String(length=32), nullable=False),
            sa.Column("share_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("price_per_share_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
            sa.Column("gross_amount_coin", sa.Numeric(18, 4), nullable=False, server_default="0.0000"),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_player_share_events")),
        )

    inspector = sa.inspect(bind)
    existing_indexes = {
        table_name: {index["name"] for index in inspector.get_indexes(table_name)}
        for table_name in ("player_share_markets", "player_share_holdings", "player_share_events")
        if inspector.has_table(table_name)
    }

    if op.f("ix_player_share_markets_player_id") not in existing_indexes.get("player_share_markets", set()):
        op.create_index(op.f("ix_player_share_markets_player_id"), "player_share_markets", ["player_id"], unique=False)

    if op.f("ix_player_share_holdings_player_id") not in existing_indexes.get("player_share_holdings", set()):
        op.create_index(op.f("ix_player_share_holdings_player_id"), "player_share_holdings", ["player_id"], unique=False)

    if op.f("ix_player_share_holdings_user_id") not in existing_indexes.get("player_share_holdings", set()):
        op.create_index(op.f("ix_player_share_holdings_user_id"), "player_share_holdings", ["user_id"], unique=False)

    if op.f("ix_player_share_events_event_type") not in existing_indexes.get("player_share_events", set()):
        op.create_index(op.f("ix_player_share_events_event_type"), "player_share_events", ["event_type"], unique=False)

    if op.f("ix_player_share_events_player_id") not in existing_indexes.get("player_share_events", set()):
        op.create_index(op.f("ix_player_share_events_player_id"), "player_share_events", ["player_id"], unique=False)

    if op.f("ix_player_share_events_user_id") not in existing_indexes.get("player_share_events", set()):
        op.create_index(op.f("ix_player_share_events_user_id"), "player_share_events", ["user_id"], unique=False)

    if inspector.has_table("wallets"):
        _create_index_if_missing(
            bind,
            table_name="wallets",
            index_name="ix_wallets_owner_user_id",
            columns=["owner_user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="wallets",
            index_name="ix_wallets_code",
            columns=["code"],
            unique=True,
        )
        _drop_index_if_exists(bind, table_name="wallets", index_name="ix_ledger_accounts_owner_user_id")
        _drop_index_if_exists(bind, table_name="wallets", index_name="ix_ledger_accounts_code")

    if inspector.has_table("gtex_jackpot_rounds"):
        _create_index_if_missing(
            bind,
            table_name="gtex_jackpot_rounds",
            index_name="ix_gtex_jackpot_rounds_triggered_at",
            columns=["triggered_at"],
        )
        _create_index_if_missing(
            bind,
            table_name="gtex_jackpot_rounds",
            index_name="ix_gtex_jackpot_rounds_winning_user_id",
            columns=["winning_user_id"],
        )

    if inspector.has_table("national_regen_seeds"):
        _create_index_if_missing(
            bind,
            table_name="national_regen_seeds",
            index_name="ix_national_regen_seeds_status",
            columns=["status"],
        )

    _backfill_player_share_markets(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("national_regen_seeds"):
        _drop_index_if_exists(bind, table_name="national_regen_seeds", index_name="ix_national_regen_seeds_status")

    if inspector.has_table("gtex_jackpot_rounds"):
        _drop_index_if_exists(bind, table_name="gtex_jackpot_rounds", index_name="ix_gtex_jackpot_rounds_winning_user_id")
        _drop_index_if_exists(bind, table_name="gtex_jackpot_rounds", index_name="ix_gtex_jackpot_rounds_triggered_at")

    if inspector.has_table("wallets"):
        _drop_index_if_exists(bind, table_name="wallets", index_name="ix_wallets_code")
        _drop_index_if_exists(bind, table_name="wallets", index_name="ix_wallets_owner_user_id")
        _create_index_if_missing(
            bind,
            table_name="wallets",
            index_name="ix_ledger_accounts_owner_user_id",
            columns=["owner_user_id"],
        )
        _create_index_if_missing(
            bind,
            table_name="wallets",
            index_name="ix_ledger_accounts_code",
            columns=["code"],
        )
