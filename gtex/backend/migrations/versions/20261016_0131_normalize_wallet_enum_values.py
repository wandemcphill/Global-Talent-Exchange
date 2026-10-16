"""Normalize wallet-ledger enum columns to the lowercase values the models read.

Revision ID: 20261016_0131_normalize_wallet_enum_values
Revises: 20261016_0130_owner_console_foundation

Older writers persisted enum names (COIN, USER, COMMITTED); the models use
values_callable and only accept the lowercase values, so reads raised LookupError. ledger_entries is append-only (trigger), so its
legacy rows stay as written and the model reads them case-insensitively.
"""

from __future__ import annotations

from alembic import op

revision = "20261016_0131_normalize_wallet_enum_values"
down_revision = "20261016_0130_owner_console_foundation"
branch_labels = None
depends_on = None

_COLUMNS = {
    "wallets": ("unit", "kind"),
    "ledger_balance_projections": ("unit",),
    "transactions": ("status", "reason", "source_tag"),
    "payment_events": ("provider", "unit", "status"),
    "payout_requests": ("unit", "status"),
}


def upgrade() -> None:
    for table, columns in _COLUMNS.items():
        for column in columns:
            op.execute(f'UPDATE "{table}" SET "{column}" = lower("{column}") WHERE "{column}" <> lower("{column}")')


def downgrade() -> None:
    pass
