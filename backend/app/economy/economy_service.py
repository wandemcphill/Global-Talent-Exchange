from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.admin_engine.service import AdminEngineService
from app.economy.pricing_engine import PricingEngine, ServicePriceQuote
from app.models.base import generate_uuid
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal('0.0001')


class EconomyServiceError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FeeQuote:
    gross_amount: Decimal
    fee_bps: int
    fee_amount: Decimal
    net_amount: Decimal
    unit: LedgerUnit


@dataclass(frozen=True, slots=True)
class MatchEntryQuote:
    service_key: str | None
    pricing: ServicePriceQuote | None
    payment_unit: LedgerUnit
    gross_amount: Decimal
    fee_bps: int
    fee_amount: Decimal
    net_amount: Decimal


@dataclass(frozen=True, slots=True)
class MatchEntryPaymentResult:
    transaction_id: str
    reference: str
    payment_unit: LedgerUnit
    gross_amount: Decimal
    fee_bps: int
    fee_amount: Decimal
    net_amount: Decimal
    destination_account_code: str
    fee_account_code: str | None
    treasury_amount: Decimal = Decimal("0.0000")
    treasury_account_code: str | None = None
    service_key: str | None = None


@dataclass(frozen=True, slots=True)
class MarketplaceSettlementQuote:
    gross_amount: Decimal
    fee_bps: int
    fee_amount: Decimal
    seller_net_amount: Decimal
    unit: LedgerUnit


@dataclass(frozen=True, slots=True)
class MarketplaceSettlementResult:
    transaction_id: str
    reference: str
    unit: LedgerUnit
    gross_amount: Decimal
    fee_bps: int
    fee_amount: Decimal
    seller_net_amount: Decimal
    buyer_account_code: str
    seller_account_code: str
    fee_account_code: str | None


@dataclass(slots=True)
class EconomyService:
    session: Session
    wallet_service: WalletService | None = None
    pricing_engine: PricingEngine | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()
        if self.pricing_engine is None:
            self.pricing_engine = PricingEngine(self.session, wallet_service=self.wallet_service)

    def quote_conversion(self, *, amount: Decimal, source_unit: LedgerUnit):
        return self.wallet_service.quote_conversion(source_unit=source_unit, amount=amount)

    def quote_match_entry(
        self,
        *,
        payment_unit: LedgerUnit,
        service_key: str | None = None,
        gross_amount: Decimal | None = None,
        quantity: int | Decimal = 1,
        fee_bps: int | None = None,
    ) -> MatchEntryQuote:
        pricing = self._resolve_price_quote(
            service_key=service_key,
            gross_amount=gross_amount,
            quantity=quantity,
        )
        resolved_fee_bps = self._resolve_match_entry_fee_bps(fee_bps)
        fee = self._build_fee_quote(
            gross_amount=pricing.amount_for_unit(payment_unit) if pricing is not None else gross_amount,
            unit=payment_unit,
            fee_bps=resolved_fee_bps,
        )
        return MatchEntryQuote(
            service_key=service_key,
            pricing=pricing,
            payment_unit=payment_unit,
            gross_amount=fee.gross_amount,
            fee_bps=fee.fee_bps,
            fee_amount=fee.fee_amount,
            net_amount=fee.net_amount,
        )

    def collect_match_entry(
        self,
        *,
        user: User,
        payment_unit: LedgerUnit,
        service_key: str | None = None,
        gross_amount: Decimal | None = None,
        quantity: int | Decimal = 1,
        destination_account: LedgerAccount | None = None,
        fee_account: LedgerAccount | None = None,
        fee_bps: int | None = None,
        treasury_account: LedgerAccount | None = None,
        treasury_share_bps: int = 0,
        reference: str | None = None,
        external_reference: str | None = None,
        description: str | None = None,
        source_tag: LedgerSourceTag = LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
        fee_source_tag: LedgerSourceTag | None = None,
        actor: User | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MatchEntryPaymentResult:
        quote = self.quote_match_entry(
            payment_unit=payment_unit,
            service_key=service_key,
            gross_amount=gross_amount,
            quantity=quantity,
            fee_bps=fee_bps,
        )
        resolved_reference = reference or f'match-entry:{generate_uuid()}'
        resolved_external_reference = external_reference or resolved_reference
        user_account = self.wallet_service.get_user_account(self.session, user, payment_unit)
        resolved_destination = destination_account or self.wallet_service.ensure_match_pool_account(self.session, payment_unit)
        resolved_fee_account = fee_account or self.wallet_service.ensure_match_fee_account(self.session, payment_unit)
        resolved_fee_tag = fee_source_tag or source_tag
        resolved_treasury_share_bps = max(0, min(10_000, int(treasury_share_bps or 0)))
        treasury_amount = self._normalize_amount(
            quote.gross_amount * Decimal(resolved_treasury_share_bps) / Decimal("10000")
        )
        if treasury_amount > quote.net_amount:
            raise EconomyServiceError("Treasury share cannot exceed the post-fee match entry amount.")
        destination_amount = self._normalize_amount(quote.net_amount - treasury_amount)
        resolved_treasury_account = (
            treasury_account or self.wallet_service.ensure_treasury_account(self.session, payment_unit)
            if treasury_amount > Decimal("0.0000")
            else None
        )

        postings = [
            LedgerPosting(
                account=user_account,
                amount=-quote.gross_amount,
                source_tag=source_tag,
                transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
            ),
        ]
        if destination_amount > Decimal('0.0000'):
            postings.append(
                LedgerPosting(
                    account=resolved_destination,
                    amount=destination_amount,
                    source_tag=source_tag,
                    transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                )
            )
        if treasury_amount > Decimal("0.0000") and resolved_treasury_account is not None:
            postings.append(
                LedgerPosting(
                    account=resolved_treasury_account,
                    amount=treasury_amount,
                    source_tag=source_tag,
                    transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                )
            )
        if quote.fee_amount > Decimal('0.0000'):
            postings.append(
                LedgerPosting(
                    account=resolved_fee_account,
                    amount=quote.fee_amount,
                    source_tag=resolved_fee_tag,
                    transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
                )
            )

        metadata_payload = dict(metadata or {})
        metadata_payload.setdefault(
            'match_entry',
            {
                'service_key': service_key,
                'quantity': str(quantity),
                'payment_unit': payment_unit.value,
                'gross_amount': str(quote.gross_amount),
                'fee_bps': quote.fee_bps,
                'fee_amount': str(quote.fee_amount),
                'net_amount': str(quote.net_amount),
                'treasury_share_bps': resolved_treasury_share_bps,
                'treasury_amount': str(treasury_amount),
                'destination_amount': str(destination_amount),
            },
        )
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.COMPETITION_ENTRY,
            source_tag=source_tag,
            reference=resolved_reference,
            external_reference=resolved_external_reference,
            description=description or 'Match entry payment',
            actor=actor or user,
            idempotency_key=idempotency_key,
            transaction_type=LedgerTransactionType.MATCH_ENTRY_FEE,
            metadata=metadata_payload,
        )
        return MatchEntryPaymentResult(
            transaction_id=entries[0].transaction_id,
            reference=resolved_reference,
            payment_unit=payment_unit,
            gross_amount=quote.gross_amount,
            fee_bps=quote.fee_bps,
            fee_amount=quote.fee_amount,
            net_amount=quote.net_amount,
            destination_account_code=resolved_destination.code,
            fee_account_code=resolved_fee_account.code if quote.fee_amount > Decimal('0.0000') else None,
            treasury_amount=treasury_amount,
            treasury_account_code=resolved_treasury_account.code if resolved_treasury_account is not None else None,
            service_key=service_key,
        )

    def quote_marketplace_settlement(
        self,
        *,
        gross_amount: Decimal,
        unit: LedgerUnit,
        fee_bps: int | None = None,
    ) -> MarketplaceSettlementQuote:
        resolved_fee_bps = self._resolve_marketplace_fee_bps(fee_bps)
        fee = self._build_fee_quote(
            gross_amount=gross_amount,
            unit=unit,
            fee_bps=resolved_fee_bps,
        )
        return MarketplaceSettlementQuote(
            gross_amount=fee.gross_amount,
            fee_bps=fee.fee_bps,
            fee_amount=fee.fee_amount,
            seller_net_amount=fee.net_amount,
            unit=fee.unit,
        )

    def settle_marketplace_transaction(
        self,
        *,
        buyer: User,
        seller: User,
        gross_amount: Decimal,
        unit: LedgerUnit,
        reference: str | None = None,
        external_reference: str | None = None,
        description: str | None = None,
        buyer_source_tag: LedgerSourceTag,
        seller_source_tag: LedgerSourceTag,
        fee_source_tag: LedgerSourceTag = LedgerSourceTag.TRADING_FEE_BURN,
        fee_bps: int | None = None,
        fee_account: LedgerAccount | None = None,
        burn_fee: bool = False,
        actor: User | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MarketplaceSettlementResult:
        quote = self.quote_marketplace_settlement(
            gross_amount=gross_amount,
            unit=unit,
            fee_bps=fee_bps,
        )
        resolved_reference = reference or f'marketplace:{generate_uuid()}'
        resolved_external_reference = external_reference or resolved_reference
        buyer_account = self.wallet_service.get_user_account(self.session, buyer, unit)
        seller_account = self.wallet_service.get_user_account(self.session, seller, unit)
        if fee_account is not None:
            resolved_fee_account = fee_account
        elif burn_fee:
            resolved_fee_account = self.wallet_service.ensure_platform_burn_account(self.session, unit)
        else:
            resolved_fee_account = self.wallet_service.ensure_trade_fee_account(self.session, unit)

        postings = [
            LedgerPosting(
                account=buyer_account,
                amount=-quote.gross_amount,
                source_tag=buyer_source_tag,
                transaction_type=LedgerTransactionType.TRADE_BUY,
            ),
            LedgerPosting(
                account=seller_account,
                amount=quote.seller_net_amount,
                source_tag=seller_source_tag,
                transaction_type=LedgerTransactionType.TRADE_SELL,
            ),
        ]
        if quote.fee_amount > Decimal('0.0000'):
            postings.append(
                LedgerPosting(
                    account=resolved_fee_account,
                    amount=quote.fee_amount,
                    source_tag=fee_source_tag,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                )
            )

        metadata_payload = dict(metadata or {})
        metadata_payload.setdefault(
            'marketplace',
            {
                'gross_amount': str(quote.gross_amount),
                'fee_bps': quote.fee_bps,
                'fee_amount': str(quote.fee_amount),
                'seller_net_amount': str(quote.seller_net_amount),
                'unit': unit.value,
            },
        )
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=self.wallet_service.trade_settlement_reason,
            reference=resolved_reference,
            external_reference=resolved_external_reference,
            description=description or 'Marketplace settlement',
            actor=actor or buyer,
            idempotency_key=idempotency_key,
            metadata=metadata_payload,
        )
        return MarketplaceSettlementResult(
            transaction_id=entries[0].transaction_id,
            reference=resolved_reference,
            unit=unit,
            gross_amount=quote.gross_amount,
            fee_bps=quote.fee_bps,
            fee_amount=quote.fee_amount,
            seller_net_amount=quote.seller_net_amount,
            buyer_account_code=buyer_account.code,
            seller_account_code=seller_account.code,
            fee_account_code=resolved_fee_account.code if quote.fee_amount > Decimal('0.0000') else None,
        )

    def _resolve_price_quote(
        self,
        *,
        service_key: str | None,
        gross_amount: Decimal | None,
        quantity: int | Decimal,
    ) -> ServicePriceQuote | None:
        if service_key is not None and gross_amount is not None:
            raise EconomyServiceError('Provide either service_key or gross_amount, not both.')
        if service_key is None and gross_amount is None:
            raise EconomyServiceError('A service_key or gross_amount is required.')
        if service_key is not None:
            return self.pricing_engine.quote_service(service_key, quantity=quantity)
        multiplier = Decimal(str(quantity))
        if multiplier != Decimal('1'):
            raise EconomyServiceError('Quantity is only supported when service_key pricing is used.')
        return None

    def _resolve_match_entry_fee_bps(self, fee_bps: int | None) -> int:
        if fee_bps is not None:
            return self._validate_fee_bps(fee_bps)
        rule = AdminEngineService(self.session).get_active_reward_rule()
        return self._validate_fee_bps(rule.competition_platform_fee_bps if rule is not None else 1000)

    def _resolve_marketplace_fee_bps(self, fee_bps: int | None) -> int:
        if fee_bps is not None:
            return self._validate_fee_bps(fee_bps)
        rule = AdminEngineService(self.session).get_active_reward_rule()
        return self._validate_fee_bps(rule.trading_fee_bps if rule is not None else 2000)

    def _build_fee_quote(
        self,
        *,
        gross_amount: Decimal | int | float | str | None,
        unit: LedgerUnit,
        fee_bps: int,
    ) -> FeeQuote:
        gross = self._normalize_amount(gross_amount)
        if gross <= Decimal('0.0000'):
            raise EconomyServiceError('Gross amount must be positive.')
        resolved_fee_bps = self._validate_fee_bps(fee_bps)
        fee_amount = self._normalize_amount(gross * Decimal(resolved_fee_bps) / Decimal(10_000))
        net_amount = self._normalize_amount(gross - fee_amount)
        if net_amount < Decimal('0.0000'):
            raise EconomyServiceError('Fee amount cannot exceed the gross amount.')
        return FeeQuote(
            gross_amount=gross,
            fee_bps=resolved_fee_bps,
            fee_amount=fee_amount,
            net_amount=net_amount,
            unit=unit,
        )

    @staticmethod
    def _validate_fee_bps(value: int) -> int:
        resolved = int(value)
        if not 0 <= resolved <= 10_000:
            raise EconomyServiceError('Fee bps must be between 0 and 10,000.')
        return resolved

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            value = Decimal('0.0000')
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)
