"""Back Coin Trader liquidity transfers with non-negative market pools.

Revision ID: 20260914_0122_coin_trader_liquidity_backing
Revises: 20260913_0121_gift_profile_club_identity

The Coin Trader admin issue/redeem rail moves value through the platform
liquidity pool accounts. Those pools must not be allowed to go negative,
otherwise an authorized admin can create Coin without an existing ledger
balance behind the transfer.
"""

from __future__ import annotations

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "20260914_0122_coin_trader_liquidity_backing"
down_revision = "20260913_0121_gift_profile_club_identity"
branch_labels = None
depends_on = None

LIQUIDITY_ACCOUNTS = (
    ("coin", "Platform Coin Liquidity Pool"),
    ("credit", "Platform Credit Liquidity Pool"),
)


def upgrade() -> None:
    wallets = sa.table(
        "wallets",
        sa.column("id", sa.String(length=36)),
        sa.column("code", sa.String(length=120)),
        sa.column("label", sa.String(length=120)),
        sa.column("unit", sa.String(length=32)),
        sa.column("kind", sa.String(length=32)),
        sa.column("allow_negative", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )

    connection = op.get_bind()
    existing_codes = {
        row[0]
        for row in connection.execute(
            sa.select(wallets.c.code).where(
                wallets.c.code.in_([f"platform:{unit}:liquidity_pool" for unit, _ in LIQUIDITY_ACCOUNTS])
            )
        ).fetchall()
    }

    # Harden existing liquidity pools first. This is intentionally independent
    # of the application helper's historical allow_negative default so deployed
    # accounts are safe as soon as this migration commits.
    connection.execute(
        sa.update(wallets)
        .where(wallets.c.code.in_([f"platform:{unit}:liquidity_pool" for unit, _ in LIQUIDITY_ACCOUNTS]))
        .values(allow_negative=False)
    )

    missing_rows = [
        {
            "id": str(uuid4()),
            "code": f"platform:{unit}:liquidity_pool",
            "label": label,
            "unit": unit,
            "kind": "system",
            "allow_negative": False,
            "is_active": True,
        }
        for unit, label in LIQUIDITY_ACCOUNTS
        if f"platform:{unit}:liquidity_pool" not in existing_codes
    ]
    if missing_rows:
        op.bulk_insert(wallets, missing_rows)


def downgrade() -> None:
    wallets = sa.table(
        "wallets",
        sa.column("code", sa.String(length=120)),
        sa.column("allow_negative", sa.Boolean()),
    )
    op.execute(
        sa.update(wallets)
        .where(wallets.c.code.in_([f"platform:{unit}:liquidity_pool" for unit, _ in LIQUIDITY_ACCOUNTS]))
        .values(allow_negative=True)
    )
