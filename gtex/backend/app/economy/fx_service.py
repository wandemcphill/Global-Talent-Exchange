from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fx_pricing import FxRate, RegionalPricingRule
from app.models.user import User

AMOUNT_QUANTUM = Decimal("0.0001")
BASE_GTEX_NAIRA_PRICE = Decimal("1000.0000")

DEFAULT_FX_RATES: tuple[dict[str, Any], ...] = (
    {"currency": "NGN", "rate_to_naira": Decimal("1.000000")},
    {"currency": "GBP", "rate_to_naira": Decimal("1538.461538")},
    {"currency": "USD", "rate_to_naira": Decimal("1500.000000")},
    {"currency": "EUR", "rate_to_naira": Decimal("1666.666667")},
)

DEFAULT_REGIONAL_RULES: tuple[dict[str, Any], ...] = (
    {
        "region_code": "NIGERIA",
        "label": "Nigeria",
        "price_multiplier": Decimal("1.0000"),
        "withdrawal_limit_multiplier": Decimal("1.0000"),
        "kyc_tier_label": "standard",
        "tax_tracking_required": False,
        "compliance_note": "Default local market pricing.",
    },
    {
        "region_code": "AFRICA",
        "label": "Africa",
        "price_multiplier": Decimal("0.9500"),
        "withdrawal_limit_multiplier": Decimal("0.9000"),
        "kyc_tier_label": "enhanced",
        "tax_tracking_required": True,
        "compliance_note": "Slight discount with regional compliance review.",
    },
    {
        "region_code": "EUROPE",
        "label": "Europe",
        "price_multiplier": Decimal("1.1500"),
        "withdrawal_limit_multiplier": Decimal("1.2000"),
        "kyc_tier_label": "enhanced",
        "tax_tracking_required": True,
        "compliance_note": "Premium pricing with tax ledger requirements.",
    },
    {
        "region_code": "ASIA",
        "label": "Asia",
        "price_multiplier": Decimal("0.9000"),
        "withdrawal_limit_multiplier": Decimal("0.9500"),
        "kyc_tier_label": "enhanced",
        "tax_tracking_required": True,
        "compliance_note": "PPP-adjusted pricing with regional tax tracking.",
    },
    {
        "region_code": "GLOBAL",
        "label": "Global",
        "price_multiplier": Decimal("1.0000"),
        "withdrawal_limit_multiplier": Decimal("1.0000"),
        "kyc_tier_label": "standard",
        "tax_tracking_required": False,
        "compliance_note": "Fallback policy for unclassified regions.",
    },
)


class FxPricingError(ValueError):
    pass


class FxPricingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def seed_defaults(self) -> None:
        existing_currencies = {item.currency for item in self.session.scalars(select(FxRate)).all()}
        for payload in DEFAULT_FX_RATES:
            if payload["currency"] in existing_currencies:
                continue
            self.session.add(FxRate(**payload))

        existing_regions = {item.region_code for item in self.session.scalars(select(RegionalPricingRule)).all()}
        for payload in DEFAULT_REGIONAL_RULES:
            if payload["region_code"] in existing_regions:
                continue
            self.session.add(RegionalPricingRule(**payload))
        self.session.flush()

    def list_fx_rates(self) -> list[FxRate]:
        self.seed_defaults()
        return list(self.session.scalars(select(FxRate).order_by(FxRate.currency.asc())).all())

    def upsert_fx_rate(self, *, actor: User, currency: str, rate_to_naira: Decimal) -> FxRate:
        normalized_currency = currency.strip().upper()
        record = self.session.scalar(select(FxRate).where(FxRate.currency == normalized_currency))
        if record is None:
            record = FxRate(currency=normalized_currency)
            self.session.add(record)
        record.rate_to_naira = self._amount(rate_to_naira, places="0.000001")
        record.updated_by_user_id = actor.id
        self.session.flush()
        return record

    def list_regional_rules(self) -> list[RegionalPricingRule]:
        self.seed_defaults()
        return list(
            self.session.scalars(
                select(RegionalPricingRule).order_by(RegionalPricingRule.region_code.asc())
            ).all()
        )

    def upsert_regional_rule(
        self,
        *,
        actor: User,
        region_code: str,
        label: str,
        price_multiplier: Decimal,
        withdrawal_limit_multiplier: Decimal,
        kyc_tier_label: str,
        tax_tracking_required: bool,
        compliance_note: str | None,
    ) -> RegionalPricingRule:
        normalized_region = region_code.strip().upper()
        record = self.session.scalar(
            select(RegionalPricingRule).where(RegionalPricingRule.region_code == normalized_region)
        )
        if record is None:
            record = RegionalPricingRule(region_code=normalized_region)
            self.session.add(record)
        record.label = label.strip()
        record.price_multiplier = self._amount(price_multiplier)
        record.withdrawal_limit_multiplier = self._amount(withdrawal_limit_multiplier)
        record.kyc_tier_label = kyc_tier_label.strip()
        record.tax_tracking_required = bool(tax_tracking_required)
        record.compliance_note = compliance_note.strip() if compliance_note else None
        record.updated_by_user_id = actor.id
        self.session.flush()
        return record

    def quote_gtex_price(
        self,
        *,
        gtex_amount: Decimal,
        currency: str,
        region_code: str | None = None,
    ) -> dict[str, Any]:
        self.seed_defaults()
        normalized_currency = currency.strip().upper()
        fx_rate = self.session.scalar(select(FxRate).where(FxRate.currency == normalized_currency))
        if fx_rate is None or not fx_rate.is_active:
            raise FxPricingError(f"FX rate for {normalized_currency} is not configured.")
        normalized_region = (region_code or "GLOBAL").strip().upper()
        region_rule = self.session.scalar(
            select(RegionalPricingRule).where(RegionalPricingRule.region_code == normalized_region)
        )
        if region_rule is None:
            region_rule = self.session.scalar(
                select(RegionalPricingRule).where(RegionalPricingRule.region_code == "GLOBAL")
            )
        amount = self._amount(gtex_amount)
        naira_value = self._amount(amount * BASE_GTEX_NAIRA_PRICE)
        base_quote = self._amount(naira_value / Decimal(fx_rate.rate_to_naira), places="0.000001")
        multiplier = self._amount(region_rule.price_multiplier if region_rule is not None else Decimal("1.0000"))
        final_quote = self._amount(base_quote * multiplier, places="0.000001")
        return {
            "gtex_amount": amount,
            "currency": normalized_currency,
            "region_code": normalized_region,
            "rate_to_naira": self._amount(fx_rate.rate_to_naira, places="0.000001"),
            "base_gtex_naira_price": BASE_GTEX_NAIRA_PRICE,
            "naira_value": naira_value,
            "base_quote": base_quote,
            "price_multiplier": multiplier,
            "final_quote": final_quote,
            "kyc_tier_label": None if region_rule is None else region_rule.kyc_tier_label,
            "withdrawal_limit_multiplier": None if region_rule is None else self._amount(region_rule.withdrawal_limit_multiplier),
            "tax_tracking_required": False if region_rule is None else bool(region_rule.tax_tracking_required),
            "compliance_note": None if region_rule is None else region_rule.compliance_note,
        }

    @staticmethod
    def _amount(value: Decimal | str | int | float | None, *, places: str = "0.0000") -> Decimal:
        return Decimal(str(value or "0")).quantize(Decimal(places))


__all__ = ["BASE_GTEX_NAIRA_PRICE", "FxPricingError", "FxPricingService"]
