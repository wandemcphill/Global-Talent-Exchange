"""Backfill encryption for legacy plaintext KYC/bank identifier rows.

Encrypts each plaintext value on kyc_profiles.nin/bvn,
user_bank_accounts.account_number, and
treasury_withdrawal_requests.bank_account_number (via ``enc:v1:`` Fernet
tokens) and populates the *_hash blind indexes. Withdrawal rows also have
``bank_snapshot_json.account_number`` replaced by a masked
``account_number_masked`` snapshot.

Stored values are read raw (bypassing the EncryptedString decrypt). Rows that
already carry the ``enc:v1:`` prefix keep that ciphertext. A missing or stale
blind index is rewritten from the decrypted plaintext, so rotating
``GTE_AUTH_SECRET`` and re-running this script repairs exact-match search
without re-encrypting. The script is idempotent. ``--dry-run`` reports rows
that still need a write.

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
from app.core.field_encryption import ENCRYPTION_PREFIX, blind_index, decrypt_field, encrypt_field
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
        help="Report rows that still need encryption or index repair without writing.",
    )
    return parser


def _iter_raw_batches(session, model, columns, has_snapshot):
    selected = [model.id]
    for column, hash_column in columns:
        # Coerce away EncryptedString so legacy plaintext and ciphertext are
        # both returned unchanged. Decrypting here would hide rows that still
        # need encryption.
        selected.append(type_coerce(getattr(model, column), String).label(column))
        if hash_column:
            selected.append(getattr(model, hash_column).label(hash_column))
    if has_snapshot:
        selected.append(model.bank_snapshot_json)
    last_id = ""
    while True:
        rows = session.execute(
            select(*selected).where(model.id > last_id).order_by(model.id).limit(_BATCH_SIZE)
        ).mappings().all()
        if not rows:
            return
        last_id = rows[-1]["id"]
        yield rows


def _masked_snapshot(snapshot: dict) -> dict:
    masked = {key: value for key, value in snapshot.items() if key != "account_number"}
    masked["account_number_masked"] = _mask_account_number(snapshot.get("account_number"))
    return masked


def _row_changes(columns, row, has_snapshot) -> tuple[bool, bool, dict[str, object]]:
    """Return (legacy_plaintext, stale_index, column updates).

    Ciphertext is never rewritten. A stale blind index is replaced with the
    HMAC of the decrypted identifier so auth-secret rotation can be repaired
    by re-running the script.
    """
    values: dict[str, object] = {}
    legacy = False
    stale = False
    for column, hash_column in columns:
        raw_value = row[column]
        if raw_value is None or not str(raw_value).startswith(ENCRYPTION_PREFIX):
            if raw_value is not None:
                legacy = True
                plaintext = str(raw_value)
                values[column] = encrypt_field(plaintext)
                if hash_column:
                    values[hash_column] = blind_index(plaintext)
            elif hash_column and row[hash_column] is not None:
                stale = True
                values[hash_column] = None
            continue
        if not hash_column:
            continue
        expected = blind_index(decrypt_field(str(raw_value)))
        if row[hash_column] != expected:
            stale = True
            values[hash_column] = expected
    if has_snapshot:
        snapshot = row["bank_snapshot_json"]
        if isinstance(snapshot, dict) and "account_number" in snapshot:
            legacy = True
            values["bank_snapshot_json"] = _masked_snapshot(snapshot)
    return legacy, stale, values


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
            stale_count = 0
            written = 0
            for batch in _iter_raw_batches(session, model, columns, has_snapshot):
                for row in batch:
                    legacy, stale, values = _row_changes(columns, row, has_snapshot)
                    if not legacy and not stale:
                        continue
                    legacy_count += int(legacy)
                    stale_count += int(stale)
                    if args.dry_run or not values:
                        continue
                    session.execute(update(model).where(model.id == row["id"]).values(**values))
                    written += 1
                if not args.dry_run:
                    session.commit()
            print(
                f"{model.__tablename__}: {legacy_count} legacy plaintext row(s), "
                f"{stale_count} stale blind index row(s)"
            )
            if not args.dry_run:
                total_written += written
        if not args.dry_run:
            print(f"Done. {total_written} row(s) updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
