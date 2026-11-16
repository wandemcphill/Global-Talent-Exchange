"""Regression coverage for StrEnum values stored by treasury, wallet, and user models."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects.postgresql import dialect as pg_dialect
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
from sqlalchemy.sql.sqltypes import Enum as SqlAlchemyEnum

from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.treasury import (
    DepositRequest,
    DepositStatus,
    KycProfile,
    PaymentMode,
    RateDirection,
    TreasurySettings,
    TreasuryWithdrawalRequest,
    TreasuryWithdrawalStatus,
)
from app.models.user import KycStatus, PublicAccountType, User
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerTransaction,
    LedgerTransactionStatus,
    LedgerTransactionType,
    LedgerUnit,
    PaymentEvent,
    PaymentProvider,
    PaymentStatus,
    PayoutRequest,
    PayoutStatus,
)
from app.treasury.service import TreasuryService


def _assert_database_enum_values(column, enum_class) -> None:
    enum_type = column.type
    assert isinstance(enum_type, SqlAlchemyEnum)

    expected_values = [member.value for member in enum_class]
    assert enum_type.enums == expected_values

    for dialect_cls in (sqlite_dialect, pg_dialect):
        result_processor = enum_type.result_processor(dialect_cls(), None)
        assert result_processor is not None
        for member_name, member in enum_class.__members__.items():
            # Canonical lowercase .value, legacy uppercase .name, and mixed casing all read cleanly.
            assert result_processor(member.value) is member
            assert result_processor(member_name) is member
            assert result_processor(member.value.upper()) is member
            assert result_processor(member.value.capitalize()) is member

        bind_processor = enum_type.bind_processor(dialect_cls())
        assert bind_processor is not None
        for member in enum_class:
            assert bind_processor(member) == member.value


def test_treasury_model_enums_read_values_stored_by_migrations() -> None:
    mappings = (
        (TreasurySettings, "deposit_rate_direction", RateDirection),
        (TreasurySettings, "withdrawal_rate_direction", RateDirection),
        (TreasurySettings, "deposit_mode", PaymentMode),
        (TreasurySettings, "withdrawal_mode", PaymentMode),
        (DepositRequest, "status", DepositStatus),
        (DepositRequest, "rate_direction", RateDirection),
        (KycProfile, "status", KycStatus),
        (TreasuryWithdrawalRequest, "status", TreasuryWithdrawalStatus),
        (TreasuryWithdrawalRequest, "unit", LedgerUnit),
        (TreasuryWithdrawalRequest, "rate_direction", RateDirection),
    )

    for model, column_name, enum_class in mappings:
        _assert_database_enum_values(model.__table__.c[column_name], enum_class)


def test_fan_coin_purchase_order_and_wallet_enums_read_stored_values() -> None:
    mappings = (
        (FancoinPurchaseOrder, "status", PurchaseOrderStatus),
        (FancoinPurchaseOrder, "unit", LedgerUnit),
        (FancoinPurchaseOrder, "rate_direction", RateDirection),
        (LedgerAccount, "unit", LedgerUnit),
        (LedgerAccount, "kind", LedgerAccountKind),
        (LedgerTransaction, "status", LedgerTransactionStatus),
        (LedgerTransaction, "reason", LedgerEntryReason),
        (LedgerTransaction, "source_tag", LedgerSourceTag),
        (LedgerEntry, "unit", LedgerUnit),
        (LedgerEntry, "source_tag", LedgerSourceTag),
        (LedgerEntry, "reason", LedgerEntryReason),
        (LedgerEntry, "transaction_type", LedgerTransactionType),
        (LedgerBalanceProjection, "unit", LedgerUnit),
        (PaymentEvent, "provider", PaymentProvider),
        (PaymentEvent, "unit", LedgerUnit),
        (PaymentEvent, "status", PaymentStatus),
        (PayoutRequest, "unit", LedgerUnit),
        (PayoutRequest, "status", PayoutStatus),
        (User, "account_type", PublicAccountType),
        (User, "kyc_status", KycStatus),
    )

    for model, column_name, enum_class in mappings:
        _assert_database_enum_values(model.__table__.c[column_name], enum_class)


def test_control_center_and_orm_tolerate_mixed_case_persisted_enum_rows(
    client,
    app_session_factory,
    bootstrap_admin_headers,
) -> None:
    # Seed the default row first, then simulate the exact production mixed-case state:
    # lowercase direction from migration 0253 alongside legacy uppercase MANUAL modes,
    # plus legacy uppercase ledger_entries rows.
    with app_session_factory() as session:
        settings = TreasuryService().ensure_settings(session)
        session.commit()
        settings_id = settings.id

        session.execute(
            text(
                "UPDATE treasury_settings "
                "SET deposit_mode = 'MANUAL', withdrawal_mode = 'MANUAL', "
                "deposit_rate_direction = 'fiat_per_coin', withdrawal_rate_direction = 'fiat_per_coin' "
                "WHERE id = :sid"
            ),
            {"sid": settings_id},
        )

        account_id = str(uuid4())
        tx_id = str(uuid4())
        entry_id = str(uuid4())
        session.execute(
            text(
                "INSERT INTO wallets (id, owner_user_id, code, label, unit, kind, allow_negative, is_active) "
                "VALUES (:id, NULL, :code, 'Legacy System', 'COIN', 'SYSTEM', 0, 1)"
            ),
            {"id": account_id, "code": f"legacy:{account_id}"},
        )
        session.execute(
            text(
                "INSERT INTO transactions (id, status, reason, source_tag, metadata_json) "
                "VALUES (:id, 'COMMITTED', 'ADJUSTMENT', 'MARKET_TOPUP', '{}')"
            ),
            {"id": tx_id},
        )
        session.execute(
            text(
                "INSERT INTO ledger_entries (id, transaction_id, account_id, amount, unit, source_tag, reason, transaction_type) "
                "VALUES (:id, :tx_id, :acct_id, 100.0000, 'COIN', 'MARKET_TOPUP', 'ADJUSTMENT', 'ADJUSTMENT')"
            ),
            {"id": entry_id, "tx_id": tx_id, "acct_id": account_id},
        )
        session.commit()

    with app_session_factory() as session:
        loaded_settings = TreasuryService().ensure_settings(session)
        assert loaded_settings.deposit_mode is PaymentMode.MANUAL
        assert loaded_settings.withdrawal_mode is PaymentMode.MANUAL
        assert loaded_settings.deposit_rate_direction is RateDirection.FIAT_PER_COIN

        loaded_entry = session.scalar(select(LedgerEntry).where(LedgerEntry.id == entry_id))
        assert loaded_entry is not None
        assert loaded_entry.unit is LedgerUnit.COIN
        assert loaded_entry.source_tag is LedgerSourceTag.MARKET_TOPUP
        assert loaded_entry.reason is LedgerEntryReason.ADJUSTMENT
        assert loaded_entry.transaction_type is LedgerTransactionType.ADJUSTMENT

    response = client.get("/api/owner/control-center", headers=bootstrap_admin_headers)
    assert response.status_code == 200, response.text
    assert "economy" in response.json()


def test_migration_0254_normalizes_mutable_enum_casing() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "migrations"
        / "versions"
        / "20261116_0254_normalize_mutable_treasury_wallet_enum_casing.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0254", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE treasury_settings ("
                "id TEXT PRIMARY KEY, "
                "deposit_mode TEXT NOT NULL, "
                "withdrawal_mode TEXT NOT NULL, "
                "deposit_rate_direction TEXT NOT NULL, "
                "withdrawal_rate_direction TEXT NOT NULL)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE users ("
                "id TEXT PRIMARY KEY, "
                "role TEXT NOT NULL, "
                "account_type TEXT NOT NULL, "
                "kyc_status TEXT NOT NULL)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO treasury_settings VALUES "
                "('ts-1', 'MANUAL', 'AUTOMATIC', 'fiat_per_coin', 'FIAT_PER_COIN')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO users VALUES "
                "('u-1', 'SUPER_ADMIN', 'USER', 'UNVERIFIED'), "
                "('u-2', 'USER', 'COIN_TRADER', 'FULLY_VERIFIED')"
            )
        )

        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            migration.upgrade()

        ts_row = conn.execute(
            text(
                "SELECT deposit_mode, withdrawal_mode, deposit_rate_direction, withdrawal_rate_direction "
                "FROM treasury_settings WHERE id = 'ts-1'"
            )
        ).one()
        assert tuple(ts_row) == ("manual", "automatic", "fiat_per_coin", "fiat_per_coin")

        user_rows = conn.execute(text("SELECT id, role, account_type, kyc_status FROM users ORDER BY id")).all()
        assert [tuple(r) for r in user_rows] == [
            ("u-1", "SUPER_ADMIN", "user", "pending"),
            ("u-2", "USER", "coin_trader", "verified"),
        ]
    engine.dispose()
