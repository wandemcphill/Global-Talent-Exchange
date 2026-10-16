"""Backfill encryption for legacy plaintext KYC/bank identifier rows.

Encrypts each plaintext value on kyc_profiles.nin/bvn,
user_bank_accounts.account_number, and
treasury_withdrawal_requests.bank_account_number (via ``enc:v1:`` Fernet
tokens) and populates the *_hash blind indexes. Withdrawal rows also have
``bank_snapshot_json.account_number`` replaced by a masked
``account_number_masked`` snapshot.

Stored values are read raw (bypassing the EncryptedString decrypt), so rows
already carrying the ``enc:v1:`` prefix are skipped: the script is idempotent
and ``--dry-run`` counts only genuinely legacy rows.

Usage:
    python backend/scripts/encrypt_sensitive_fields.py --dry-run
    python backend/scripts/encrypt_sensitive_fields.py
    GTE_DATABASE_URL=... python backend/scripts/encrypt_sensitive_fields.py
"""

from __future__ import annotations

import argparse
import os
from typing import Sequence

from sqlalchemy import String, select, type_coerce, update

from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.core.field_encryption import ENCRYPTION_PREFIX, blind_index, encrypt_field
from app.models.treasury import KycProfile, TreasuryWithdrawalRequest, UserBankAccount
from app.treasury.service import _mask_account_number

_BATCH_SIZE = 500

# (model, ((plain_column, hash_column_or_None), ...), snapshot_account_number)
_TARGETS = (
    (KycProfile, (("nin", "nin_hash"), ("bvn", "bvn_hash")), False),
    (UserBankAccount, (("account_number", None),), False),
    (
        TreasuryWithdrawalRequest,
        (("bank_account_number", "bank_account_number_hash"),),
        True,
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL") or os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to DATABASE_URL/GTE_DATABASE_URL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report legacy plaintext row counts without writing.",
    )
    return parser


def _iter_raw_batches(session, model, columns, has_snapshot):
    raw_columns = [type_coerce(getattr(model, column), String).label(column) for column, _hash_column in columns]
    extra = [model.bank_snapshot_json] if has_snapshot else []
    last_id = ""
    while True:
        rows = session.execute(
            select(model.id, *raw_columns, *extra).where(model.id > last_id).order_by(model.id).limit(_BATCH_SIZE)
        ).all()
        if not rows:
            return
        last_id = rows[-1][0]
        yield rows


def _row_is_legacy(raw_values, snapshot, has_snapshot) -> bool:
    if any(value is not None and not str(value).startswith(ENCRYPTION_PREFIX) for value in raw_values):
        return True
    if has_snapshot and isinstance(snapshot, dict) and "account_number" in snapshot:
        return True
    return False


def _masked_snapshot(snapshot: dict) -> dict:
    masked = {key: value for key, value in snapshot.items() if key != "account_number"}
    masked["account_number_masked"] = _mask_account_number(snapshot.get("account_number"))
    return masked


def _encrypt_row(session, model, columns, has_snapshot, row) -> bool:
    values: dict[str, object] = {}
    raw_values = row[1 : 1 + len(columns)]
    snapshot = row[1 + len(columns)] if has_snapshot else None
    for (column, hash_column), raw_value in zip(columns, raw_values):
        if raw_value is None or str(raw_value).startswith(ENCRYPTION_PREFIX):
            continue
        values[column] = encrypt_field(str(raw_value))
        if hash_column:
            values[hash_column] = blind_index(str(raw_value))
    if has_snapshot and isinstance(snapshot, dict) and "account_number" in snapshot:
        values["bank_snapshot_json"] = _masked_snapshot(snapshot)
    if not values:
        return False
    session.execute(update(model).where(model.id == row[0]).values(**values))
    return True


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or DATABASE_URL/GTE_DATABASE_URL is required.")

    load_model_modules()
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        total_written = 0
        for model, columns, has_snapshot in _TARGETS:
            legacy_count = 0
            written = 0
            for batch in _iter_raw_batches(session, model, columns, has_snapshot):
                for row in batch:
                    raw_values = row[1 : 1 + len(columns)]
                    snapshot = row[1 + len(columns)] if has_snapshot else None
                    if not _row_is_legacy(raw_values, snapshot, has_snapshot):
                        continue
                    legacy_count += 1
                    if not args.dry_run and _encrypt_row(session, model, columns, has_snapshot, row):
                        written += 1
                if not args.dry_run:
                    session.commit()
            print(f"{model.__tablename__}: {legacy_count} legacy plaintext row(s)")
            if not args.dry_run:
                total_written += written
        if not args.dry_run:
            print(f"Done. {total_written} row(s) encrypted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
