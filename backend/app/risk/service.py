from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntry, LedgerEntryReason, LedgerUnit
from backend.app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal("0.0001")


class TradeSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class RiskValidationError(ValueError):
    pass


class NonPositiveQuantityError(RiskValidationError):
    pass


class InvalidPriceError(RiskValidationError):
    pass


class InsufficientCashError(RiskValidationError):
    pass


class InsufficientHoldingsError(RiskValidationError):
    pass


class DuplicateSettlementError(RiskValidationError):
    pass


class RiskControlService:
    def __init__(self, wallet_service: WalletService | None = None) -> None:
        self.wallet_service = wallet_service or WalletService()

    def validate_trade(
        self,
        session: Session,
        user: User,
        *,
        player_id: str,
        side: TradeSide | str,
        quantity: Decimal,
        price: Decimal,
        use_reserved_balance: bool = False,
    ) -> tuple[TradeSide, Decimal, Decimal, Decimal]:
        normalized_side = TradeSide(str(side).lower())
        normalized_quantity = self._normalize_amount(quantity)
        normalized_price = self._normalize_amount(price)
        if normalized_quantity <= Decimal("0.0000"):
            raise NonPositiveQuantityError("Quantity must be positive.")
        if normalized_price <= Decimal("0.0000"):
            raise InvalidPriceError("Price must be positive.")

        gross_amount = self._normalize_amount(normalized_quantity * normalized_price)
        if normalized_side is TradeSide.BUY:
            available_balance = (
                self.wallet_service.get_reserved_cash_balance(session, user)
                if use_reserved_balance
                else self.wallet_service.get_wallet_summary(session, user, currency=LedgerUnit.COIN).available_balance
            )
            if available_balance < gross_amount:
                raise InsufficientCashError(
                    f"Buy quantity {normalized_quantity} exceeds available cash at price {normalized_price}."
                )
        else:
            available_units = (
                self.wallet_service.get_reserved_position_quantity(session, user, player_id)
                if use_reserved_balance
                else self.wallet_service.get_available_position_quantity(session, user, player_id)
            )
            if available_units < normalized_quantity:
                raise InsufficientHoldingsError(
                    f"Sell quantity {normalized_quantity} exceeds owned quantity for player {player_id}."
                )

        return normalized_side, normalized_quantity, normalized_price, gross_amount

    def ensure_execution_not_settled(self, session: Session, execution_id: str) -> None:
        existing_entry = session.scalar(
            select(LedgerEntry.id)
            .where(
                LedgerEntry.reason == LedgerEntryReason.TRADE_SETTLEMENT,
                LedgerEntry.external_reference == execution_id,
            )
            .limit(1)
        )
        if existing_entry is not None:
            raise DuplicateSettlementError(f"Execution {execution_id} has already been settled.")

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)
