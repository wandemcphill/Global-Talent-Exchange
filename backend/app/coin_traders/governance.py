from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.base import generate_uuid
from app.models.coin_trader import CoinTraderProfile, CoinTraderRate
from app.models.risk_ops import SystemEventSeverity
from app.models.treasury import TreasurySettings
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.risk_ops_engine.service import RiskOpsService
from app.treasury.service import TreasuryService


@dataclass(frozen=True, slots=True)
class CoinTraderGovernanceResult:
    spread_fiat: Decimal
    treasury_deposit_rate_fiat: Decimal | None
    treasury_withdrawal_rate_fiat: Decimal | None
    min_trader_buy_rate_fiat: Decimal | None
    max_trader_buy_rate_fiat: Decimal | None
    min_trader_sell_rate_fiat: Decimal | None
    max_trader_sell_rate_fiat: Decimal | None
    max_trader_spread_fiat: Decimal | None
    governance_status: str
    governance_reasons: tuple[str, ...]

    @property
    def is_blocked(self) -> bool:
        return self.governance_status in {"out_of_bounds", "arbitrage_risk"}


class CoinTraderPricingGovernanceService:
    """Treasury guardrails for GTEX Coin OTC trader pricing."""

    def __init__(self, session: Session, treasury_service: TreasuryService | None = None) -> None:
        self.session = session
        self.treasury_service = treasury_service or TreasuryService()

    def evaluate_values(
        self,
        *,
        coin_unit: LedgerUnit,
        buy_rate_fiat: Decimal,
        sell_rate_fiat: Decimal,
        settings: TreasurySettings | None = None,
    ) -> CoinTraderGovernanceResult:
        normalized_unit = self._ledger_unit(coin_unit)
        spread = self._amount(Decimal(sell_rate_fiat) - Decimal(buy_rate_fiat))
        if normalized_unit != LedgerUnit.COIN:
            return CoinTraderGovernanceResult(
                spread_fiat=spread,
                treasury_deposit_rate_fiat=None,
                treasury_withdrawal_rate_fiat=None,
                min_trader_buy_rate_fiat=None,
                max_trader_buy_rate_fiat=None,
                min_trader_sell_rate_fiat=None,
                max_trader_sell_rate_fiat=None,
                max_trader_spread_fiat=None,
                governance_status="compliant",
                governance_reasons=(),
            )

        settings = settings or self.treasury_service.ensure_settings(self.session)
        deposit_rate = self._amount(settings.deposit_rate_value)
        withdrawal_rate = self._amount(settings.withdrawal_rate_value)
        reasons: list[str] = []
        arbitrage_reasons: list[str] = []

        min_buy = self._amount(settings.min_trader_buy_rate_fiat)
        max_buy = self._amount(settings.max_trader_buy_rate_fiat)
        min_sell = self._amount(settings.min_trader_sell_rate_fiat)
        max_sell = self._amount(settings.max_trader_sell_rate_fiat)
        max_spread = self._amount(settings.max_trader_spread_fiat)
        buy_rate = self._amount(buy_rate_fiat)
        sell_rate = self._amount(sell_rate_fiat)

        if buy_rate < min_buy:
            reasons.append(f"Trader buy rate {buy_rate} is below minimum {min_buy}.")
        if buy_rate > max_buy:
            reasons.append(f"Trader buy rate {buy_rate} is above maximum {max_buy}.")
        if sell_rate < min_sell:
            reasons.append(f"Trader sell rate {sell_rate} is below minimum {min_sell}.")
        if sell_rate > max_sell:
            reasons.append(f"Trader sell rate {sell_rate} is above maximum {max_sell}.")
        if spread < Decimal("0.0000"):
            reasons.append("Trader sell rate cannot be below trader buy rate.")
        if spread > max_spread:
            reasons.append(f"Trader spread {spread} exceeds maximum {max_spread}.")

        sell_floor = deposit_rate - self._amount(settings.max_sell_below_deposit_fiat)
        buy_ceiling = withdrawal_rate + self._amount(settings.max_buy_above_withdrawal_fiat)
        if sell_rate < sell_floor:
            arbitrage_reasons.append(
                f"Trader sell rate {sell_rate} undercuts treasury deposit reference {deposit_rate}."
            )
        if buy_rate > buy_ceiling:
            arbitrage_reasons.append(
                f"Trader buy rate {buy_rate} exceeds treasury withdrawal reference {withdrawal_rate}."
            )

        all_reasons = tuple(reasons + arbitrage_reasons)
        status = "compliant"
        if arbitrage_reasons:
            status = "arbitrage_risk"
        elif reasons:
            status = "out_of_bounds"

        return CoinTraderGovernanceResult(
            spread_fiat=spread,
            treasury_deposit_rate_fiat=deposit_rate,
            treasury_withdrawal_rate_fiat=withdrawal_rate,
            min_trader_buy_rate_fiat=min_buy,
            max_trader_buy_rate_fiat=max_buy,
            min_trader_sell_rate_fiat=min_sell,
            max_trader_sell_rate_fiat=max_sell,
            max_trader_spread_fiat=max_spread,
            governance_status=status,
            governance_reasons=all_reasons,
        )

    def evaluate_rate(self, rate: CoinTraderRate) -> CoinTraderGovernanceResult:
        return self.evaluate_values(
            coin_unit=rate.coin_unit,
            buy_rate_fiat=rate.buy_rate_fiat,
            sell_rate_fiat=rate.sell_rate_fiat,
        )

    def block_if_invalid(
        self,
        *,
        result: CoinTraderGovernanceResult,
        actor: User | None,
        trader_profile: CoinTraderProfile | None,
        proposed_rate_payload: dict[str, object],
        action: str,
    ) -> None:
        if not result.is_blocked:
            return
        self.flag_blocked_rate(
            result=result,
            actor=actor,
            trader_profile=trader_profile,
            proposed_rate_payload=proposed_rate_payload,
            action=action,
        )
        self.session.commit()
        raise ValueError("; ".join(result.governance_reasons) or "Trader rate violates treasury guardrails.")

    def flag_blocked_rate(
        self,
        *,
        result: CoinTraderGovernanceResult,
        actor: User | None,
        trader_profile: CoinTraderProfile | None,
        proposed_rate_payload: dict[str, object],
        action: str,
    ) -> None:
        RiskOpsService(self.session).create_system_event(
            actor_user_id=actor.id if actor is not None else None,
            event_key=f"coin-trader-rate-{action}-{generate_uuid()}",
            event_type="coin_trader_pricing_governance",
            severity=SystemEventSeverity.WARNING,
            title="Coin trader rate blocked",
            body="A coin trader rate was blocked by treasury pricing guardrails.",
            subject_type="coin_trader_profile",
            subject_id=trader_profile.id if trader_profile is not None else None,
            metadata_json={
                "action": action,
                "status": result.governance_status,
                "reasons": list(result.governance_reasons),
                "spread_fiat": str(result.spread_fiat),
                "treasury_deposit_rate_fiat": (
                    str(result.treasury_deposit_rate_fiat) if result.treasury_deposit_rate_fiat is not None else None
                ),
                "treasury_withdrawal_rate_fiat": (
                    str(result.treasury_withdrawal_rate_fiat)
                    if result.treasury_withdrawal_rate_fiat is not None
                    else None
                ),
                "proposed_rate": proposed_rate_payload,
            },
        )

    @staticmethod
    def _amount(value: Decimal | int | str | float) -> Decimal:
        return Decimal(str(value or "0")).quantize(Decimal("0.0001"))

    @staticmethod
    def _ledger_unit(value: LedgerUnit | str) -> LedgerUnit:
        if isinstance(value, LedgerUnit):
            return value
        return LedgerUnit(str(value))
