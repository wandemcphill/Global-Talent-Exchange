from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.economy.currency_policy import CurrencyPolicyError, FANCOIN, GTEX_COIN
from app.economy.economic_policy import resolve_economic_policy
from app.models.economic_conversion import (
    EconomicConversion,
    EconomicConversionStatus,
    EconomicConversionType,
)
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType
from app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
GIFT_CONVERSION_BRIDGE_COIN_CODE = "platform:coin:gift_conversion_bridge"


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
        destination_coin_amount: Decimal,
        burn_fancoin: Decimal = Decimal("0.0000"),
        conversion_key: str,
        gift_transaction_id: str | None = None,
        fee_rule_key: str | None = None,
        fee_rule_version: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> EconomicConversion:
        gross = self._normalize(gross_fancoin)
        fee = self._normalize(platform_fee_fancoin)
        destination = self._normalize(destination_coin_amount)
        burn = self._normalize(burn_fancoin)
        if gross <= Decimal("0"):
            raise EconomicConversionError("FanCoin conversion amount must be positive.")
        if fee < Decimal("0") or burn < Decimal("0") or destination <= Decimal("0"):
            raise EconomicConversionError(
                "FanCoin gift conversion amounts must be non-negative with a positive destination."
            )
        if fee + burn + destination != gross:
            raise EconomicConversionError("FanCoin gift conversion legs must reconcile exactly to the gross amount.")
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

        if FANCOIN is GTEX_COIN:
            raise CurrencyPolicyError("FanCoin and GTEX Coin must remain distinct economic units.")

        policy = resolve_economic_policy(self.session)
        if fee_rule_key is None:
            fee_rule_key = policy.rule.rule_key
        if fee_rule_version is None or fee_rule_version == "1":
            fee_rule_version = policy.policy_version

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
        bridge_coin = self.wallet_service.ensure_named_system_account(
            self.session,
            code=GIFT_CONVERSION_BRIDGE_COIN_CODE,
            label="Platform GTEX Coin Gift Conversion Bridge",
            unit=GTEX_COIN,
            allow_negative=True,
        )
        platform_fancoin_revenue = self.wallet_service.ensure_named_system_account(
            self.session,
            code="platform:credit:gift_conversion_fee_revenue",
            label="Platform FanCoin Gift Conversion Fee Revenue",
            unit=FANCOIN,
            allow_negative=False,
        )
        burn_account = None
        if burn > Decimal("0"):
            burn_account = self.wallet_service.ensure_platform_burn_account(self.session, FANCOIN)

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
            metadata_json={
                **(metadata or {}),
                "burn_amount": str(burn),
                "coin_bridge_account_code": GIFT_CONVERSION_BRIDGE_COIN_CODE,
                "conversion_authority": "fan_coin_gift_conversion",
                "policy_rule_key": fee_rule_key,
                "policy_version": fee_rule_version,
                "policy_effective_at": policy.effective_at.isoformat(),
            },
        )
        self.session.add(conversion)
        self.session.flush()

        postings = [
            LedgerPosting(account=source_account, amount=-gross, source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME),
            LedgerPosting(
                account=platform_fancoin_revenue, amount=fee, source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME
            ),
            LedgerPosting(
                account=bridge_fancoin, amount=destination, source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME
            ),
            LedgerPosting(
                account=bridge_coin, amount=-destination, source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME
            ),
            LedgerPosting(
                account=recipient_account, amount=destination, source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME
            ),
        ]
        if burn_account is not None:
            postings.append(LedgerPosting(account=burn_account, amount=burn, source_tag=LedgerSourceTag.GIFT_RAKE_BURN))

        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
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
                "burn_amount": str(burn),
                "destination_amount": str(destination),
                "coin_bridge_account_code": GIFT_CONVERSION_BRIDGE_COIN_CODE,
                "policy_rule_key": fee_rule_key,
                "policy_version": fee_rule_version,
                "policy_effective_at": policy.effective_at.isoformat(),
            },
        )

        transaction_id = entries[0].transaction_id if entries else None
        conversion.source_ledger_transaction_id = transaction_id
        conversion.destination_ledger_transaction_id = transaction_id
        conversion.status = EconomicConversionStatus.SETTLED
        self.session.flush()
        return conversion

    def reverse(
        self,
        *,
        conversion: EconomicConversion,
        actor: User | None = None,
        note: str | None = None,
    ) -> EconomicConversion:
        """Compensate a settled FanCoin->GTEX Coin gift with an exact inverse.

        A gift is two balanced currency legs, so its reversal must be too. The
        sender is made whole in the FanCoin they actually spent; the recipient's
        GTEX Coin, the platform FanCoin fee, the burn and both bridge legs are
        each unwound by the same amount they were posted. Reversing in a single
        unit would hand the sender withdrawable Coin for a non-withdrawable
        FanCoin debit and mint unfunded value.
        """
        if conversion.status is EconomicConversionStatus.REVERSED:
            return conversion
        if conversion.status is not EconomicConversionStatus.SETTLED:
            raise EconomicConversionError("Only a settled gift conversion can be reversed.")

        gross = self._normalize(conversion.source_amount)
        fee = self._normalize(conversion.platform_fee_amount)
        destination = self._normalize(conversion.destination_amount)
        burn = self._normalize((conversion.metadata_json or {}).get("burn_amount") or 0)
        if fee + burn + destination != gross:
            raise EconomicConversionError(
                "Stored gift conversion legs do not reconcile to the gross amount; refusing to reverse."
            )
        if conversion.source_unit is not FANCOIN or conversion.destination_unit is not GTEX_COIN:
            raise EconomicConversionError("Only FanCoin->GTEX Coin gift conversions can be reversed here.")

        source_user = self.session.get(User, conversion.source_user_id)
        recipient_user = self.session.get(User, conversion.recipient_user_id)
        if source_user is None or recipient_user is None:
            raise EconomicConversionError("Gift conversion reversal references a missing user.")

        source_account = self.wallet_service.get_user_account(self.session, source_user, FANCOIN)
        recipient_account = self.wallet_service.get_user_account(self.session, recipient_user, GTEX_COIN)
        bridge_fancoin = self.wallet_service.ensure_named_system_account(
            self.session,
            code="platform:credit:gift_conversion_bridge",
            label="Platform FanCoin Gift Conversion Bridge",
            unit=FANCOIN,
            allow_negative=False,
        )
        bridge_coin = self.wallet_service.ensure_named_system_account(
            self.session,
            code=GIFT_CONVERSION_BRIDGE_COIN_CODE,
            label="Platform GTEX Coin Gift Conversion Bridge",
            unit=GTEX_COIN,
            allow_negative=True,
        )
        platform_fancoin_revenue = self.wallet_service.ensure_named_system_account(
            self.session,
            code="platform:credit:gift_conversion_fee_revenue",
            label="Platform FanCoin Gift Conversion Fee Revenue",
            unit=FANCOIN,
            allow_negative=False,
        )

        postings = [
            LedgerPosting(account=source_account, amount=gross, source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME),
            LedgerPosting(
                account=bridge_fancoin, amount=-destination, source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME
            ),
            LedgerPosting(
                account=bridge_coin, amount=destination, source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME
            ),
            LedgerPosting(
                account=recipient_account, amount=-destination, source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME
            ),
        ]
        if fee > Decimal("0"):
            postings.append(
                LedgerPosting(
                    account=platform_fancoin_revenue,
                    amount=-fee,
                    source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
                )
            )
        if burn > Decimal("0"):
            postings.append(
                LedgerPosting(
                    account=self.wallet_service.ensure_platform_burn_account(self.session, FANCOIN),
                    amount=-burn,
                    source_tag=LedgerSourceTag.GIFT_RAKE_BURN,
                )
            )

        reversal_key = f"fan-gift-conversion-reversal:{conversion.id}"
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.GTEX_PLATFORM_GIFT_INCOME,
            transaction_type=LedgerTransactionType.CONVERSION,
            reference=f"conversion-reversal:{conversion.id}",
            external_reference=reversal_key,
            idempotency_key=reversal_key,
            actor=actor,
            metadata={
                "conversion_id": conversion.id,
                "conversion_type": conversion.conversion_type.value,
                "reversal_of_ledger_transaction_id": conversion.source_ledger_transaction_id,
                "source_unit": FANCOIN.value,
                "destination_unit": GTEX_COIN.value,
                "source_amount": str(gross),
                "platform_fee_amount": str(fee),
                "burn_amount": str(burn),
                "destination_amount": str(destination),
                "coin_bridge_account_code": GIFT_CONVERSION_BRIDGE_COIN_CODE,
                "policy_rule_key": conversion.fee_rule_key,
                "policy_version": conversion.fee_rule_version,
                "note": note or "",
            },
        )

        conversion.status = EconomicConversionStatus.REVERSED
        conversion.metadata_json = {
            **(conversion.metadata_json or {}),
            "reversal_ledger_transaction_id": entries[0].transaction_id if entries else None,
            "reversed_by_user_id": actor.id if actor is not None else None,
            "reversal_note": note or "",
        }
        self.session.flush()
        return conversion

    @staticmethod
    def _normalize(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)


__all__ = [
    "EconomicConversionError",
    "FanCoinGiftConversionService",
    "GIFT_CONVERSION_BRIDGE_COIN_CODE",
]
