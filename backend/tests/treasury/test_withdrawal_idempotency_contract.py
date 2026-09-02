from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.treasury.schemas import WithdrawalRequestCreate


def test_withdrawal_requires_idempotency_key() -> None:
    with pytest.raises(ValidationError, match="idempotency_key"):
        WithdrawalRequestCreate(amount_coin=Decimal("25.0000"))


def test_withdrawal_rejects_blank_idempotency_key() -> None:
    with pytest.raises(ValidationError, match="idempotency_key"):
        WithdrawalRequestCreate(amount_coin=Decimal("25.0000"), idempotency_key="   ")


def test_withdrawal_normalizes_idempotency_key() -> None:
    payload = WithdrawalRequestCreate(
        amount_coin=Decimal("25.0000"),
        idempotency_key="  withdrawal-001  ",
    )
    assert payload.idempotency_key == "withdrawal-001"
