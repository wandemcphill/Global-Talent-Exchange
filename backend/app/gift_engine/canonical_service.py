from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.gift_engine.service import GiftEngineError, GiftEngineService as LegacyGiftEngineService
from app.models.economic_conversion import (
    EconomicConversion,
    EconomicConversionStatus,
    EconomicConversionType,
)
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting


class CanonicalGiftEngineService(LegacyGiftEngineService):
    """Compatibility adapter that converts every gifted FanCoin amount into GTEX Coin."""

    def send_gift(self, *, sender: User, **kwargs: Any):  # type: ignore[override]
        transaction = super().send_gift(sender=sender, **kwargs)
        if transaction.economic_conversion_id:
            return transaction

        recipient = self.session.get(User, transaction.recipient_user_id)
        if recipient is None:
            raise GiftEngineError("Gift conversion recipient no longer exists.")

        destination_amount = Decimal(transaction.recipient_net_amount).quantize(
            Decimal("0.0001")
        )
        if destination_amount <= Decimal("0"):
            raise GiftEngineError("Gift conversion requires a positive recipient amount.")

        conversion_key = f"gift-recipient-conversion:{transaction.id}"
        conversion = self.session.scalar(
            select(EconomicConversion).where(
                EconomicConversion.conversion_key == conversion_key
            )
        )
        if conversion is not None:
            self._mark_transaction_converted(transaction, conversion)
            return transaction

        source_account = self.wallet_service.get_user_account(
            self.session, recipient, LedgerUnit.CREDIT
        )
        destination_account = self.wallet_service.get_user_account(
            self.session, recipient, LedgerUnit.COIN
        )
        platform_credit_bridge = self.wallet_service.ensure_named_system_account(
            self.session,
            code="platform:credit:gift_conversion_bridge",
            label="Platform FanCoin Gift Conversion Bridge",
            unit=LedgerUnit.CREDIT,
            allow_negative=False,
        )
        platform_coin_account = self.wallet_service.ensure_platform_account(
            self.session, LedgerUnit.COIN
        )

        if self.wallet_service.get_balance(self.session, source_account) < destination_amount:
            raise GiftEngineError(
                "Gift recipient FanCoin balance is insufficient for conversion."
            )

        conversion = EconomicConversion(
            conversion_key=conversion_key,
            conversion_type=EconomicConversionType.FANCOIN_GIFT,
            status=EconomicConversionStatus.PENDING,
            source_user_id=recipient.id,
            recipient_user_id=recipient.id,
            gift_transaction_id=transaction.id,
            source_unit=LedgerUnit.CREDIT,
            destination_unit=LedgerUnit.COIN,
            source_amount=destination_amount,
            platform_fee_amount=Decimal("0.0000"),
            destination_amount=destination_amount,
            conversion_rate=Decimal("1"),
            fee_rule_key="gift_recipient_conversion",
            fee_rule_version="1",
            idempotency_key=conversion_key,
            metadata_json={
                "gift_transaction_id": transaction.id,
                "semantics": "gifted_fancoin_becomes_withdrawable_gtex_coin",
                "conversion_fee_already_applied": True,
            },
        )
        self.session.add(conversion)
        self.session.flush()

        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=source_account,
                    amount=-destination_amount,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                ),
                LedgerPosting(
                    account=platform_credit_bridge,
                    amount=destination_amount,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                ),
                LedgerPosting(
                    account=platform_coin_account,
                    amount=-destination_amount,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                ),
                LedgerPosting(
                    account=destination_account,
                    amount=destination_amount,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
            transaction_type=LedgerTransactionType.CONVERSION,
            reference=f"conversion:{conversion.id}",
            external_reference=conversion_key,
            idempotency_key=conversion_key,
            actor=sender,
            metadata={
                "conversion_id": conversion.id,
                "conversion_type": conversion.conversion_type.value,
                "gift_transaction_id": transaction.id,
            },
        )
        transaction_id = entries[0].transaction_id if entries else None
        conversion.source_ledger_transaction_id = transaction_id
        conversion.destination_ledger_transaction_id = transaction_id
        conversion.status = EconomicConversionStatus.SETTLED
        self._mark_transaction_converted(transaction, conversion)
        self.session.flush()
        return transaction

    @staticmethod
    def _mark_transaction_converted(
        transaction: Any, conversion: EconomicConversion
    ) -> None:
        transaction.economic_conversion_id = conversion.id
        transaction.source_ledger_unit = LedgerUnit.CREDIT
        transaction.destination_ledger_unit = LedgerUnit.COIN
        transaction.ledger_unit = LedgerUnit.COIN
        transaction.conversion_rate = Decimal("1")
        transaction.metadata_json = {
            **(transaction.metadata_json or {}),
            "currency_semantics": "fan_coin_gift_converted_to_gtex_coin",
            "source_ledger_unit": LedgerUnit.CREDIT.value,
            "destination_ledger_unit": LedgerUnit.COIN.value,
            "conversion_id": conversion.id,
        }


GiftEngineService = CanonicalGiftEngineService

__all__ = ["CanonicalGiftEngineService", "GiftEngineError", "GiftEngineService"]
