"""Regression coverage for StrEnum values stored by treasury and wallet models."""

from sqlalchemy.dialects.sqlite import dialect
from sqlalchemy.sql.sqltypes import Enum as SqlAlchemyEnum

from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.treasury import (
    DepositRequest,
    DepositStatus,
    PaymentMode,
    RateDirection,
    TreasurySettings,
    TreasuryWithdrawalRequest,
    TreasuryWithdrawalStatus,
)
from app.models.wallet import LedgerUnit


def _assert_database_enum_values(column, enum_class) -> None:
    enum_type = column.type
    assert isinstance(enum_type, SqlAlchemyEnum)

    expected_values = [member.value for member in enum_class]
    assert enum_type.enums == expected_values

    # The production DB stores the StrEnum .value (lowercase), not the
    # Python member name (uppercase). Exercise the actual SQLAlchemy reader.
    result_processor = enum_type.result_processor(dialect(), None)
    assert result_processor is not None
    for member in enum_class:
        assert result_processor(member.value) is member


def test_treasury_model_enums_read_values_stored_by_migrations() -> None:
    mappings = (
        (TreasurySettings, "deposit_rate_direction", RateDirection),
        (TreasurySettings, "withdrawal_rate_direction", RateDirection),
        (TreasurySettings, "deposit_mode", PaymentMode),
        (TreasurySettings, "withdrawal_mode", PaymentMode),
        (DepositRequest, "status", DepositStatus),
        (DepositRequest, "rate_direction", RateDirection),
        (TreasuryWithdrawalRequest, "status", TreasuryWithdrawalStatus),
        (TreasuryWithdrawalRequest, "unit", LedgerUnit),
        (TreasuryWithdrawalRequest, "rate_direction", RateDirection),
    )

    for model, column_name, enum_class in mappings:
        _assert_database_enum_values(model.__table__.c[column_name], enum_class)


def test_fan_coin_purchase_order_enums_read_stored_values() -> None:
    mappings = (
        (FancoinPurchaseOrder, "status", PurchaseOrderStatus),
        (FancoinPurchaseOrder, "unit", LedgerUnit),
        (FancoinPurchaseOrder, "rate_direction", RateDirection),
    )

    for model, column_name, enum_class in mappings:
        _assert_database_enum_values(model.__table__.c[column_name], enum_class)
