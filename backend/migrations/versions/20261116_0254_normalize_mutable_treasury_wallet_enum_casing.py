"""Normalize mutable treasury, wallet, and user enum columns to canonical values.

Revision ID: 20261116_0254_normalize_mutable_treasury_wallet_enum_casing
Revises: 20261116_0252_user_point_accounts_and_ledger
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261116_0254_normalize_mutable_treasury_wallet_enum_casing"
down_revision = "20261116_0252_user_point_accounts_and_ledger"
branch_labels = None
depends_on = None

# Append-only ledger_entries is intentionally excluded because production enforces
# trg_ledger_entries_append_only; CaseInsensitiveStrEnum handles legacy uppercase rows on read.
_MUTABLE_LOWERCASE_UPDATES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "treasury_settings",
        ("deposit_mode", "withdrawal_mode", "deposit_rate_direction", "withdrawal_rate_direction"),
    ),
    ("deposit_requests", ("status", "rate_direction")),
    ("treasury_withdrawal_requests", ("status", "unit", "rate_direction")),
    ("fancoin_purchase_orders", ("status", "unit", "rate_direction")),
    ("wallets", ("unit", "kind")),
    ("transactions", ("status", "reason", "source_tag")),
    ("ledger_balance_projections", ("unit",)),
    ("payment_events", ("provider", "unit", "status")),
    ("payout_requests", ("unit", "status")),
    ("kyc_profiles", ("status",)),
    ("users", ("account_type", "kyc_status")),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table_name, columns in _MUTABLE_LOWERCASE_UPDATES:
        if table_name not in existing_tables:
            continue
        table_cols = {col["name"] for col in inspector.get_columns(table_name)}
        present = [col for col in columns if col in table_cols]
        if not present:
            continue
        assignments = ", ".join(f"{col} = LOWER({col})" for col in present)
        changed_guard = " OR ".join(f"{col} <> LOWER({col})" for col in present)
        op.execute(sa.text(f"UPDATE {table_name} SET {assignments} WHERE {changed_guard}"))

    for kyc_table, kyc_col in (("users", "kyc_status"), ("kyc_profiles", "status")):
        if kyc_table not in existing_tables:
            continue
        table_cols = {col["name"] for col in inspector.get_columns(kyc_table)}
        if kyc_col not in table_cols:
            continue
        op.execute(sa.text(f"UPDATE {kyc_table} SET {kyc_col} = 'pending' WHERE LOWER({kyc_col}) = 'unverified'"))
        op.execute(
            sa.text(
                f"UPDATE {kyc_table} SET {kyc_col} = 'verified' "
                f"WHERE LOWER({kyc_col}) IN ('partial_verified_no_id', 'fully_verified')"
            )
        )


def downgrade() -> None:
    # Data normalization to canonical StrEnum values is safe and non-destructive.
    pass
