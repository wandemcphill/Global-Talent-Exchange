from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.economy.currency_policy import GTEX_COIN, FANCOIN, CurrencyPolicyError
from app.models.economic_conversion import (
    EconomicConversion,
    EconomicConversionStatus,
    EconomicConversionType,
)
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType
from app.wallets.service import LedgerPosting, WalletService


AMOUNT_QUANTUM = Decimal("0.0001")


class EconomicConversionError(ValueError):
    """Raised when a cross-currency economic conversion cannot be settled."""


@dataclass(slots=True)
class FanCoinGiftConversionService:
    session: Session
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()

    def convert(
        self,
        *,
        source_user_id: str,
        recipient_user_id: str,
        gross_fancoin: Decimal,
        platform_fee_fancoin: Decimal,
        conversion_key: str,
        gift_transaction_id: str | None = None,
        fee_rule_key: str | None = None,
        fee_rule_version: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> EconomicConversion:
        gross = self._normalize(gross_fancoin)
        fee = self._normalize(platform_fee_fancoin)
        destination = self._normalize(gross - fee)
        if gross <= Decimal("0"):
            raise EconomicConversionError("FanCoin conversion amount must be positive.")
        if fee < Decimal("0") or fee > gross:
            raise EconomicConversionError("FanCoin conversion fee must be between zero and the gross amount.")
        if source_user_id == recipient_user_id:
            raise EconomicConversionError("Economic gift conversion requires distinct source and recipient users.")

        existing = self.session.scalar(
            select(EconomicConversion).where(EconomicConversion.conversion_key == conversion_key)
        )
        if existing is not None:
            return existing
        if idempotency_key:
            existing = self.session.scalar(
                select(EconomicConversion).where(EconomicConversion.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return existing

        if destination <= Decimal("0"):
            raise EconomicConversionError("FanCoin gift conversion produces no GTEX Coin destination amount.")
        if FANCOIN is GTEX_COIN:
            raise CurrencyPolicyError("FanCoin and GTEX Coin must remain distinct economic units.")

        source_user = self.session.get(User, source_user_id)
        recipient_user = self.session.get(User, recipient_user_id)
        if source_user is None or recipient_user is None:
            raise EconomicConversionError("Gift conversion references a missing user.")
        if not source_user.is_active or not recipient_user.is_active:
            raise EconomicConversionError("Gift conversion requires active users.")

        source_account = self.wallet_service.get_user_account(self.session, source_user, FANCOIN)
        recipient_account = self.wallet_service.get_user_account(self.session, recipient_user, GTEX_COIN)
        source_available = self.wallet_service.get_balance(self.session, source_account)
        if source_available < gross:
            raise EconomicConversionError("Insufficient FanCoin balance for gift conversion.")

        bridge_fancoin = self.wallet_service.ensure_named_system_account(
            self.session,
            code="platform:credit:gift_conversion_bridge",
            label="Platform FanCoin Gift Conversion Bridge",
            unit=FANCOIN,
            allow_negative=False,
        )
        bridge_coin = self.wallet_service.ensure_platform_account(self.session, GTEX_COIN)
        platform_fancoin_revenue = self.wallet_service.ensure_named_system_account(
            self.session,
            code="platform:credit:gift_conversion_fee_revenue",
            label="Platform FanCoin Gift Conversion Fee Revenue",
            unit=FANCOIN,
            allow_negative=False,
        )

        conversion = EconomicConversion(
            conversion_key=conversion_key,
            conversion_type=EconomicConversionType.FANCOIN_GIFT,
            status=EconomicConversionStatus.PENDING,
            source_user_id=source_user_id,
            recipient_user_id=recipient_user_id,
            gift_transaction_id=gift_transaction_id,
            source_unit=FANCOIN,
            destination_unit=GTEX_COIN,
            source_amount=gross,
            platform_fee_amount=fee,
            destination_amount=destination,
            conversion_rate=Decimal("1"),
            fee_rule_key=fee_rule_key,
            fee_rule_version=fee_rule_version,
            idempotency_key=idempotency_key,
            metadata_json=metadata or {},
        )
        self.session.add(conversion)
        self.session.flush()

        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=source_account,
                    amount=-gross,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                ),
                LedgerPosting(
                    account=platform_fancoin_revenue,
                    amount=fee,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                ),
                LedgerPosting(
                    account=bridge_fancoin,
                    amount=destination,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                ),
                LedgerPosting(
                    account=bridge_coin,
                    amount=-destination,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                ),
                LedgerPosting(
                    account=recipient_account,
                    amount=destination,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
            transaction_type=LedgerTransactionType.CONVERSION,
            reference=f"conversion:{conversion.id}",
            external_reference=conversion_key,
            idempotency_key=idempotency_key or f"fan-gift-conversion:{conversion.id}",
            actor=source_user,
            metadata={
                "conversion_id": conversion.id,
                "conversion_type": conversion.conversion_type.value,
                "source_unit": FANCOIN.value,
                "destination_unit": GTEX_COIN.value,
                "source_amount": str(gross),
                "platform_fee_amount": str(fee),
                "destination_amount": str(destination),
            },
        )

        transaction_id = entries[0].transaction_id if entries else None
        conversion.source_ledger_transaction_id = transaction_id
        conversion.destination_ledger_transaction_id = transaction_id
        conversion.status = EconomicConversionStatus.SETTLED
        self.session.flush()
        return conversion

    @staticmethod
    def _normalize(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)


__all__ = ["EconomicConversionError", "FanCoinGiftConversionService"]
