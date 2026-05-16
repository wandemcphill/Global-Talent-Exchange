from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.economy.governor_service import EconomyGovernorService
from app.models.economy_config import ServicePricingRule
from app.models.wallet import LedgerUnit
from app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal('0.0001')


class PricingEngineError(ValueError):
    pass


class ServicePricingRuleNotFoundError(PricingEngineError):
    pass


@dataclass(frozen=True, slots=True)
class ServicePriceQuote:
    service_key: str
    title: str
    description: str | None
    gtex_amount: Decimal
    fancoin_amount: Decimal
    active: bool

    def amount_for_unit(self, unit: LedgerUnit) -> Decimal:
        if unit == LedgerUnit.COIN:
            return self.gtex_amount
        if unit == LedgerUnit.CREDIT:
            return self.fancoin_amount
        raise PricingEngineError(f'Unsupported ledger unit: {unit!s}')


class PricingEngine:
    def __init__(self, session: Session, *, wallet_service: WalletService | None = None) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService()

    def get_service_rule(self, service_key: str, *, active_only: bool = True) -> ServicePricingRule:
        statement = select(ServicePricingRule).where(ServicePricingRule.service_key == service_key)
        if active_only:
            statement = statement.where(ServicePricingRule.active.is_(True))
        rule = self.session.scalar(statement)
        if rule is None:
            raise ServicePricingRuleNotFoundError(f'Service pricing rule was not found for {service_key}.')
        return rule

    def quote_service(
        self,
        service_key: str,
        *,
        quantity: int | Decimal = 1,
        active_only: bool = True,
    ) -> ServicePriceQuote:
        quantity_multiplier = Decimal(str(quantity))
        if quantity_multiplier <= Decimal('0.0000'):
            raise PricingEngineError('Quoted quantity must be positive.')

        rule = self.get_service_rule(service_key, active_only=active_only)
        gtex_amount = self._normalize_amount(rule.price_coin)
        fancoin_amount = self._normalize_amount(rule.price_fancoin_equivalent)
        if gtex_amount <= Decimal('0.0000') and fancoin_amount <= Decimal('0.0000'):
            raise PricingEngineError(f'Service pricing rule {service_key} does not define a GTex or Fan Coin price.')

        if gtex_amount <= Decimal('0.0000') and fancoin_amount > Decimal('0.0000'):
            gtex_amount = Decimal('0.0000')
        if fancoin_amount <= Decimal('0.0000'):
            fancoin_amount = self.wallet_service.quote_conversion(
                source_unit=LedgerUnit.COIN,
                amount=gtex_amount,
            ).target_amount

        governor_multiplier = EconomyGovernorService(
            self.session,
            wallet_service=self.wallet_service,
        ).pricing_multiplier_for_service(service_key)

        return ServicePriceQuote(
            service_key=rule.service_key,
            title=rule.title,
            description=rule.description,
            gtex_amount=self._normalize_amount(gtex_amount * governor_multiplier * quantity_multiplier),
            fancoin_amount=self._normalize_amount(fancoin_amount * governor_multiplier * quantity_multiplier),
            active=bool(rule.active),
        )

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            value = Decimal('0.0000')
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)
