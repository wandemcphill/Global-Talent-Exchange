"""Backfill encryption for legacy plaintext KYC/bank identifier rows.

Re-assigns each plaintext value on kyc_profiles.nin/bvn,
user_bank_accounts.account_number, and
treasury_withdrawal_requests.bank_account_number so the EncryptedString
TypeDecorator encrypts it and the model validators populate the *_hash blind
indexes. Idempotent: rows already carrying the ``enc:v1:`` prefix are skipped.

Usage:
    python backend/scripts/encrypt_sensitive_fields.py --dry-run
    python backend/scripts/encrypt_sensitive_fields.py
    GTE_DATABASE_URL=... python backend/scripts/encrypt_sensitive_fields.py
"""

from __future__ import annotations

import argparse
import os
from typing import Sequence

from sqlalchemy import select, update

from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.core.field_encryption import ENCRYPTION_PREFIX, blind_index, encrypt_field
from app.models.treasury import KycProfile, TreasuryWithdrawalRequest, UserBankAccount

_BATCH_SIZE = 500

# (model, ((plain_column, hash_column_or_None), ...))
_TARGETS = (
    (KycProfile, (("nin", "nin_hash"), ("bvn", "bvn_hash"))),
    (UserBankAccount, (("account_number", None),)),
    (TreasuryWithdrawalRequest, (("bank_account_number", "bank_account_number_hash"),)),
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


def _legacy_rows(session, model, columns):
    rows = (
        session.execute(select(model).order_by(model.id))
        .scalars()
        .all()
    )
    return [
        row
        for row in rows
        if any(
            getattr(row, column) is not None
            and not getattr(row, column).startswith(ENCRYPTION_PREFIX)
            for column, _hash_column in columns
        )
    ]


def _encrypt_row(session, model, columns, row) -> bool:
    values: dict[str, object] = {}
    for column, hash_column in columns:
        plaintext = getattr(row, column)
        if plaintext is None or plaintext.startswith(ENCRYPTION_PREFIX):
            continue
        values[column] = encrypt_field(plaintext)
        if hash_column:
            values[hash_column] = blind_index(plaintext)
    if not values:
        return False
    session.execute(update(model).where(model.id == row.id).values(**values))
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
        for model, columns in _TARGETS:
            legacy = _legacy_rows(session, model, columns)
            print(f"{model.__tablename__}: {len(legacy)} legacy plaintext row(s)")
            if args.dry_run:
                continue
            for offset in range(0, len(legacy), _BATCH_SIZE):
                batch = legacy[offset : offset + _BATCH_SIZE]
                written = 0
                for row in batch:
                    if _encrypt_row(session, model, columns, row):
                        written += 1
                session.commit()
                total_written += written
                print(f"  encrypted {total_written} row(s) so far...")
        if not args.dry_run:
            print(f"Done. {total_written} row(s) encrypted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
