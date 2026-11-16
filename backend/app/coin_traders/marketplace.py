from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.coin_traders.governance import CoinTraderPricingGovernanceService
from app.coin_traders.schemas import (
    CoinTradeOrderQuoteRequest,
    CoinTradeOrderQuoteView,
    CoinTradeRatingCreateRequest,
    CoinTradeRatingView,
    CoinTraderAdminAdvertPauseRequest,
    CoinTraderAdminAuditLogView,
    CoinTraderAdminConfigUpdateRequest,
    CoinTraderAdminOverviewView,
    CoinTraderAdvertStatusUpdateRequest,
    CoinTraderAdvertUpsertRequest,
    CoinTraderAdvertView,
    CoinTraderDashboardOrderCountsView,
    CoinTraderDashboardPerformanceView,
    CoinTraderDashboardView,
    CoinTraderMarketReferenceUnitView,
    CoinTraderMarketReferenceView,
    CoinTraderMarketplaceOfferView,
    CoinTraderMarketplaceResponse,
    CoinTraderWalletBalancesView,
)
from app.models.base import utcnow
from app.models.coin_trader import (
    CoinAdvertPricingMode,
    CoinAdvertSide,
    CoinAdvertStatus,
    CoinTradeDirection,
    CoinTradeOrder,
    CoinTradeOrderStatus,
    CoinTradeRating,
    CoinTraderAdvert,
    CoinTraderProfile,
    CoinTraderProfileStatus,
    CoinTraderRate,
)
from app.models.risk_ops import AuditLog, SystemEvent
from app.models.treasury import TreasurySettings
from app.models.user import PublicAccountType, User
from app.models.wallet import LedgerUnit
from app.treasury.service import TreasuryService

NGN_BUY_MIN_COIN = Decimal("200000.00")
NGN_BUY_MIN_CREDIT = Decimal("50000.00")


def _q4(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _q2(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _is_didit_verified(profile: CoinTraderProfile) -> bool:
    return bool(profile.verified_at is not None and (profile.verification_provider or "").strip().lower() == "didit")


def _verification_badge_label(profile: CoinTraderProfile) -> str:
    if _is_didit_verified(profile):
        return "ID Verified"
    if profile.status == CoinTraderProfileStatus.APPROVED.value and profile.verified_at is not None:
        return "Approved by GTEX"
    return "Pending Verification"


@dataclass(slots=True)
class CoinTraderMarketplaceHelper:
    """Modular marketplace, advert, quote, rating, dashboard, and admin analytics logic."""

    service: Any  # CoinTraderService instance

    @property
    def session(self) -> Session:
        return self.service.session

    def get_market_reference(self) -> CoinTraderMarketReferenceView:
        settings = TreasuryService().ensure_settings(self.session)
        return CoinTraderMarketReferenceView(
            fiat_currency="NGN",
            updated_at=utcnow(),
            assets=[
                self._reference_unit_view(LedgerUnit.COIN, settings),
                self._reference_unit_view(LedgerUnit.CREDIT, settings),
            ],
        )

    def _reference_unit_view(self, unit: LedgerUnit, settings: TreasurySettings) -> CoinTraderMarketReferenceUnitView:
        gov = CoinTraderPricingGovernanceService(self.session)
        if unit == LedgerUnit.COIN:
            res = gov.evaluate_values(
                coin_unit=unit,
                buy_rate_fiat=settings.min_trader_buy_rate_fiat,
                sell_rate_fiat=settings.min_trader_sell_rate_fiat,
                settings=settings,
            )
            return CoinTraderMarketReferenceUnitView(
                coin_unit=unit,
                name="GTEX Coin",
                code="GTC",
                direct_buy_rate_fiat=_q4(settings.deposit_rate_value),
                direct_sell_rate_fiat=_q4(settings.withdrawal_rate_value),
                trader_wholesale_rate_fiat=_q4(settings.trader_withdrawal_rate_value),
                min_p2p_buy_fiat=NGN_BUY_MIN_COIN,
                min_trader_buy_rate_fiat=res.min_trader_buy_rate_fiat,
                max_trader_buy_rate_fiat=res.max_trader_buy_rate_fiat,
                min_trader_sell_rate_fiat=res.min_trader_sell_rate_fiat,
                max_trader_sell_rate_fiat=res.max_trader_sell_rate_fiat,
                max_trader_spread_fiat=res.max_trader_spread_fiat,
                platform_fee_fiat=Decimal("0.0000"),
            )
        res = gov.evaluate_values(
            coin_unit=unit,
            buy_rate_fiat=settings.trader_fan_coin_purchase_rate_value,
            sell_rate_fiat=Decimal(settings.trader_fan_coin_purchase_rate_value) + Decimal("0.2500"),
            settings=settings,
        )
        return CoinTraderMarketReferenceUnitView(
            coin_unit=unit,
            name="Fan Coin",
            code="FNC",
            direct_buy_rate_fiat=_q4(settings.fan_coin_deposit_rate_value),
            direct_sell_rate_fiat=None,
            trader_wholesale_rate_fiat=_q4(settings.trader_fan_coin_purchase_rate_value),
            min_p2p_buy_fiat=NGN_BUY_MIN_CREDIT,
            min_trader_buy_rate_fiat=res.min_trader_buy_rate_fiat,
            max_trader_buy_rate_fiat=res.max_trader_buy_rate_fiat,
            min_trader_sell_rate_fiat=res.min_trader_sell_rate_fiat,
            max_trader_sell_rate_fiat=res.max_trader_sell_rate_fiat,
            max_trader_spread_fiat=res.max_trader_spread_fiat,
            platform_fee_fiat=Decimal("0.0000"),
        )

    def resolve_advert_price(
        self, advert: CoinTraderAdvert, *, settings: TreasurySettings | None = None
    ) -> tuple[Decimal, Decimal | None, float | None]:
        settings = settings or TreasuryService().ensure_settings(self.session)
        if advert.coin_unit == LedgerUnit.COIN:
            ref_rate = _q4(
                settings.deposit_rate_value
                if advert.side == CoinAdvertSide.SELL.value
                else settings.withdrawal_rate_value
            )
        else:
            ref_rate = _q4(
                settings.fan_coin_deposit_rate_value
                if advert.side == CoinAdvertSide.SELL.value
                else settings.trader_fan_coin_purchase_rate_value
            )
        if advert.pricing_mode == CoinAdvertPricingMode.FLOATING.value:
            effective = _q4(ref_rate + Decimal(advert.spread_fiat or 0))
        else:
            effective = _q4(advert.price_fiat)
        deviation_pct: float | None = None
        if ref_rate > Decimal("0"):
            deviation_pct = round(float(((effective - ref_rate) / ref_rate) * Decimal("100")), 2)
        return effective, ref_rate, deviation_pct

    def daily_remaining_coin(self, advert: CoinTraderAdvert) -> Decimal | None:
        if advert.daily_limit_coin is None:
            return None
        start_of_day = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        excluded = {
            CoinTradeOrderStatus.CANCELLED.value,
            CoinTradeOrderStatus.EXPIRED.value,
            CoinTradeOrderStatus.REFUNDED.value,
            CoinTradeOrderStatus.ADMIN_REFUNDED.value,
        }
        used = self.session.scalar(
            select(func.coalesce(func.sum(CoinTradeOrder.coin_amount), 0)).where(
                CoinTradeOrder.advert_id == advert.id,
                CoinTradeOrder.created_at >= start_of_day,
                CoinTradeOrder.status.not_in(excluded),
            )
        )
        remaining = _q4(Decimal(advert.daily_limit_coin) - Decimal(used or 0))
        return max(remaining, Decimal("0.0000"))

    def effective_advert_available_coin(self, advert: CoinTraderAdvert, profile: CoinTraderProfile) -> Decimal:
        daily_rem = self.daily_remaining_coin(advert)
        if advert.side == CoinAdvertSide.SELL.value:
            wallet_avail = self.service._trader_available_balance(profile, advert.coin_unit)
            if advert.max_coin_amount and advert.max_coin_amount > Decimal("0"):
                cap = min(wallet_avail, _q4(advert.max_coin_amount))
            else:
                cap = wallet_avail
        else:
            # Trader is buying coins from customers: capacity is capped by advert max / daily limit
            cap = _q4(advert.max_coin_amount) if advert.max_coin_amount > Decimal("0") else Decimal("1000000.0000")
        if daily_rem is not None:
            cap = min(cap, daily_rem)
        return max(_q4(cap), Decimal("0.0000"))

    def to_advert_view(
        self,
        advert: CoinTraderAdvert,
        *,
        profile: CoinTraderProfile | None = None,
        settings: TreasurySettings | None = None,
    ) -> CoinTraderAdvertView:
        profile = profile or self.service._require_profile(advert.trader_profile_id)
        settings = settings or TreasuryService().ensure_settings(self.session)
        effective_price, ref_rate, deviation_pct = self.resolve_advert_price(advert, settings=settings)
        gov = CoinTraderPricingGovernanceService(self.session)
        reasons = gov.evaluate_side(coin_unit=advert.coin_unit, side=advert.side, price=effective_price)
        avail = self.effective_advert_available_coin(advert, profile)
        daily_rem = self.daily_remaining_coin(advert)
        min_fiat = _q2(Decimal(advert.min_coin_amount) * effective_price)
        if advert.side == CoinAdvertSide.SELL.value and advert.fiat_currency.upper() == "NGN":
            floor_fiat = NGN_BUY_MIN_COIN if advert.coin_unit == LedgerUnit.COIN else NGN_BUY_MIN_CREDIT
            min_fiat = max(min_fiat, floor_fiat)
        max_coin_for_fiat = advert.max_coin_amount if advert.max_coin_amount > Decimal("0") else avail
        if advert.side == CoinAdvertSide.SELL.value:
            max_coin_for_fiat = min(max_coin_for_fiat, avail) if max_coin_for_fiat > Decimal("0") else avail
        max_fiat = _q2(Decimal(max_coin_for_fiat) * effective_price)
        return CoinTraderAdvertView(
            id=advert.id,
            trader_profile_id=advert.trader_profile_id,
            coin_unit=advert.coin_unit,
            fiat_currency=advert.fiat_currency,
            side=advert.side,
            pricing_mode=advert.pricing_mode,
            price_fiat=_q4(advert.price_fiat),
            effective_price_fiat=effective_price,
            spread_fiat=_q4(advert.spread_fiat),
            reference_rate_fiat=ref_rate,
            price_deviation_pct=deviation_pct,
            min_coin_amount=_q4(advert.min_coin_amount),
            max_coin_amount=_q4(advert.max_coin_amount),
            min_fiat_amount=min_fiat,
            max_fiat_amount=max_fiat,
            available_coin=avail,
            daily_limit_coin=_q4(advert.daily_limit_coin) if advert.daily_limit_coin is not None else None,
            daily_remaining_coin=daily_rem,
            payment_window_minutes=advert.payment_window_minutes,
            payment_methods=list(advert.payment_methods_json or []),
            terms_text=advert.terms_text,
            status=advert.status,
            admin_paused_reason=advert.admin_paused_reason,
            governance_status="out_of_bounds" if reasons else "compliant",
            governance_reasons=list(reasons),
            updated_at=advert.updated_at,
        )

    def list_marketplace_offers(
        self,
        *,
        coin_unit: LedgerUnit = LedgerUnit.COIN,
        side: str = CoinAdvertSide.SELL.value,
        fiat_currency: str = "NGN",
        fiat_amount: Decimal | None = None,
        payment_method: str | None = None,
        verified_only: bool = False,
        min_completion_rate: float | None = None,
        min_available_coin: Decimal | None = None,
        country_code: str | None = None,
        sort_by: str | None = None,
    ) -> CoinTraderMarketplaceResponse:
        normalized_side = side.lower().strip()
        if normalized_side not in {CoinAdvertSide.SELL.value, CoinAdvertSide.BUY.value}:
            from app.coin_traders.service import CoinTraderValidationError

            raise CoinTraderValidationError("Marketplace side must be 'sell' or 'buy'.")
        settings = TreasuryService().ensure_settings(self.session)
        ref_view = self._reference_unit_view(coin_unit, settings)

        stmt = (
            select(CoinTraderAdvert, CoinTraderProfile)
            .join(CoinTraderProfile, CoinTraderProfile.id == CoinTraderAdvert.trader_profile_id)
            .join(User, User.id == CoinTraderProfile.user_id)
            .where(
                CoinTraderAdvert.coin_unit == coin_unit,
                CoinTraderAdvert.fiat_currency == fiat_currency.upper(),
                CoinTraderAdvert.side == normalized_side,
                CoinTraderAdvert.status == CoinAdvertStatus.ACTIVE.value,
                CoinTraderProfile.status == CoinTraderProfileStatus.APPROVED.value,
                CoinTraderProfile.verified_at.is_not(None),
                CoinTraderProfile.suspended_at.is_(None),
                CoinTraderProfile.frozen_at.is_(None),
                User.account_type == PublicAccountType.COIN_TRADER,
            )
        )
        if country_code:
            stmt = stmt.where(CoinTraderProfile.country_code == country_code.upper())

        rows = list(self.session.execute(stmt).all())
        offers: list[CoinTraderMarketplaceOfferView] = []
        gov = CoinTraderPricingGovernanceService(self.session)
        method_needle = payment_method.strip().lower() if payment_method else None

        for advert, profile in rows:
            if verified_only and not _is_didit_verified(profile):
                continue
            if min_completion_rate is not None and profile.completion_rate < min_completion_rate:
                continue

            effective_price, ref_rate, deviation_pct = self.resolve_advert_price(advert, settings=settings)
            if effective_price <= Decimal("0"):
                continue
            if gov.evaluate_side(coin_unit=coin_unit, side=normalized_side, price=effective_price):
                continue

            avail_coin = self.effective_advert_available_coin(advert, profile)
            if normalized_side == CoinAdvertSide.SELL.value:
                if avail_coin <= Decimal("0") or avail_coin < Decimal(advert.min_coin_amount):
                    continue
            if min_available_coin is not None and avail_coin < min_available_coin:
                continue

            daily_rem = self.daily_remaining_coin(advert)
            if daily_rem is not None and daily_rem <= Decimal("0"):
                continue

            ad_methods = list(advert.payment_methods_json or [])
            if not ad_methods:
                ad_methods = self.service._public_payment_method_labels(list(profile.payment_methods_json or []))
            if method_needle and not any(method_needle in m.lower() for m in ad_methods):
                continue

            min_fiat = _q2(Decimal(advert.min_coin_amount) * effective_price)
            if normalized_side == CoinAdvertSide.SELL.value and fiat_currency.upper() == "NGN":
                floor_fiat = NGN_BUY_MIN_COIN if coin_unit == LedgerUnit.COIN else NGN_BUY_MIN_CREDIT
                min_fiat = max(min_fiat, floor_fiat)
            max_coin_cap = (
                min(Decimal(advert.max_coin_amount), avail_coin)
                if advert.max_coin_amount > Decimal("0")
                else avail_coin
            )
            max_fiat = _q2(max_coin_cap * effective_price)
            if max_fiat > Decimal("0") and max_fiat < min_fiat:
                continue

            if fiat_amount is not None:
                if fiat_amount < min_fiat:
                    continue
                if max_fiat > Decimal("0") and fiat_amount > max_fiat:
                    continue
                needed_coins = fiat_amount / effective_price
                if normalized_side == CoinAdvertSide.SELL.value and avail_coin < needed_coins:
                    continue

            savings_pct: float | None = None
            if normalized_side == CoinAdvertSide.SELL.value and ref_view.direct_buy_rate_fiat > Decimal("0"):
                savings_pct = round(
                    float(((ref_view.direct_buy_rate_fiat - effective_price) / ref_view.direct_buy_rate_fiat) * 100), 2
                )
            elif (
                normalized_side == CoinAdvertSide.BUY.value
                and ref_view.direct_sell_rate_fiat is not None
                and ref_view.direct_sell_rate_fiat > Decimal("0")
            ):
                savings_pct = round(
                    float(((effective_price - ref_view.direct_sell_rate_fiat) / ref_view.direct_sell_rate_fiat) * 100),
                    2,
                )

            offers.append(
                CoinTraderMarketplaceOfferView(
                    advert_id=advert.id,
                    trader_profile_id=profile.id,
                    trader_display_name=profile.display_name,
                    country_code=profile.country_code,
                    trader_tier=profile.tier,
                    is_approved=True,
                    is_didit_verified=_is_didit_verified(profile),
                    verification_badge_label=_verification_badge_label(profile),
                    verified_at=profile.verified_at,
                    is_new_merchant=(profile.completed_orders_count or 0) < 3,
                    completed_orders_count=profile.completed_orders_count or 0,
                    total_orders_count=profile.total_orders_count or 0,
                    completion_rate=round(float(profile.completion_rate or 0.0), 1),
                    average_release_minutes=round(float(profile.average_release_minutes or 0.0), 1),
                    rating=round(float(profile.rating or 0.0), 2),
                    rating_count=profile.rating_count or 0,
                    dispute_score=round(float(profile.dispute_score or 0.0), 1),
                    last_active_at=profile.last_active_at or advert.updated_at,
                    coin_unit=advert.coin_unit,
                    fiat_currency=advert.fiat_currency,
                    side=advert.side,
                    pricing_mode=advert.pricing_mode,
                    price_fiat=effective_price,
                    reference_rate_fiat=ref_rate,
                    price_deviation_pct=deviation_pct,
                    savings_vs_direct_pct=savings_pct,
                    min_coin_amount=_q4(advert.min_coin_amount),
                    max_coin_amount=_q4(advert.max_coin_amount),
                    min_fiat_amount=min_fiat,
                    max_fiat_amount=max_fiat,
                    available_coin=avail_coin,
                    daily_remaining_coin=daily_rem,
                    payment_window_minutes=advert.payment_window_minutes,
                    payment_methods=ad_methods,
                    terms_text=advert.terms_text,
                    platform_fee_fiat=Decimal("0.0000"),
                    updated_at=advert.updated_at,
                )
            )

        effective_sort = sort_by or ("price_asc" if normalized_side == CoinAdvertSide.SELL.value else "price_desc")
        if effective_sort == "price_desc":
            offers.sort(key=lambda o: (-o.price_fiat, -o.completion_rate, -o.completed_orders_count))
        elif effective_sort == "completion_rate":
            offers.sort(key=lambda o: (-o.completion_rate, -o.completed_orders_count, o.price_fiat))
        elif effective_sort == "fastest":
            offers.sort(
                key=lambda o: (
                    0 if o.completed_orders_count > 0 and o.average_release_minutes > 0 else 1,
                    o.average_release_minutes if o.average_release_minutes > 0 else 9999.0,
                    -o.completed_orders_count,
                )
            )
        elif effective_sort == "most_orders":
            offers.sort(key=lambda o: (-o.completed_orders_count, -o.completion_rate, o.price_fiat))
        else:
            offers.sort(key=lambda o: (o.price_fiat, -o.completion_rate, -o.completed_orders_count))

        return CoinTraderMarketplaceResponse(
            coin_unit=coin_unit,
            side=normalized_side,
            fiat_currency=fiat_currency.upper(),
            total=len(offers),
            offers=offers,
            market_reference=ref_view,
        )

    def quote_advert_order(self, payload: CoinTradeOrderQuoteRequest) -> CoinTradeOrderQuoteView:
        from app.coin_traders.service import CoinTraderNotFoundError, CoinTraderValidationError

        advert = self.session.get(CoinTraderAdvert, payload.advert_id)
        if advert is None:
            raise CoinTraderNotFoundError("Coin trader advert was not found.")
        if advert.status != CoinAdvertStatus.ACTIVE.value:
            raise CoinTraderValidationError("This advert is not currently active.")
        profile = self.service._require_approved_profile(advert.trader_profile_id)
        if profile.frozen_at is not None:
            raise CoinTraderValidationError("This coin trader desk is currently frozen.")

        settings = TreasuryService().ensure_settings(self.session)
        effective_price, ref_rate, deviation_pct = self.resolve_advert_price(advert, settings=settings)
        if payload.coin_amount is None and payload.fiat_amount is None:
            raise CoinTraderValidationError("Provide either coin_amount or fiat_amount to generate a quote.")
        if payload.coin_amount is not None:
            coin_amount = _q4(payload.coin_amount)
            fiat_total = _q2(coin_amount * effective_price)
        else:
            fiat_total = _q2(payload.fiat_amount or 0)
            coin_amount = _q4(fiat_total / effective_price)

        avail_coin = self.effective_advert_available_coin(advert, profile)
        min_fiat = _q2(Decimal(advert.min_coin_amount) * effective_price)
        if advert.side == CoinAdvertSide.SELL.value and advert.fiat_currency.upper() == "NGN":
            min_fiat = max(min_fiat, NGN_BUY_MIN_COIN if advert.coin_unit == LedgerUnit.COIN else NGN_BUY_MIN_CREDIT)
        max_coin_cap = (
            min(Decimal(advert.max_coin_amount), avail_coin) if advert.max_coin_amount > Decimal("0") else avail_coin
        )
        max_fiat = _q2(max_coin_cap * effective_price)
        direction = (
            CoinTradeDirection.USER_BUYS.value
            if advert.side == CoinAdvertSide.SELL.value
            else CoinTradeDirection.USER_SELLS.value
        )
        unit_code = "GTC" if advert.coin_unit == LedgerUnit.COIN else "FNC"
        net_label = (
            f"{coin_amount:,.4f} {unit_code}"
            if direction == CoinTradeDirection.USER_BUYS.value
            else f"₦{fiat_total:,.2f}"
        )
        price_warning: str | None = None
        if deviation_pct is not None and abs(deviation_pct) >= 3.0:
            dir_word = "higher" if deviation_pct > 0 else "lower"
            price_warning = f"This price is {abs(deviation_pct):.2f}% {dir_word} than the GTEX reference rate."

        ad_methods = list(advert.payment_methods_json or [])
        if not ad_methods:
            ad_methods = self.service._public_payment_method_labels(list(profile.payment_methods_json or []))

        return CoinTradeOrderQuoteView(
            advert_id=advert.id,
            trader_profile_id=profile.id,
            trader_display_name=profile.display_name,
            direction=direction,
            coin_unit=advert.coin_unit,
            fiat_currency=advert.fiat_currency,
            quoted_rate_fiat=effective_price,
            coin_amount=coin_amount,
            fiat_total=fiat_total,
            fee_coin=Decimal("0.0000"),
            fee_fiat=Decimal("0.0000"),
            net_receive_label=net_label,
            min_coin_amount=_q4(advert.min_coin_amount),
            max_coin_amount=_q4(advert.max_coin_amount),
            min_fiat_amount=min_fiat,
            max_fiat_amount=max_fiat,
            available_coin=avail_coin,
            payment_window_minutes=advert.payment_window_minutes,
            quote_expires_at=utcnow() + timedelta(seconds=60),
            reference_rate_fiat=ref_rate,
            price_deviation_pct=deviation_pct,
            price_warning=price_warning,
            escrow_protection_note=(
                "Coins are locked in GTEX canonical escrow when the order is placed and only release after verified fiat settlement."
            ),
            payment_methods=ad_methods,
            terms_text=advert.terms_text,
        )

    def list_my_adverts(self, *, actor: User) -> list[CoinTraderAdvertView]:
        profile = self.service._require_profile_for_user(actor)
        adverts = list(
            self.session.scalars(
                select(CoinTraderAdvert)
                .where(CoinTraderAdvert.trader_profile_id == profile.id)
                .order_by(CoinTraderAdvert.coin_unit, CoinTraderAdvert.side)
            ).all()
        )
        settings = TreasuryService().ensure_settings(self.session)
        return [self.to_advert_view(a, profile=profile, settings=settings) for a in adverts]

    def upsert_my_advert(self, payload: CoinTraderAdvertUpsertRequest, *, actor: User) -> CoinTraderAdvertView:
        from app.coin_traders.service import CoinTraderValidationError

        profile = self.service._require_approved_profile_for_user(actor)
        if profile.frozen_at is not None or profile.status == CoinTraderProfileStatus.FROZEN.value:
            raise CoinTraderValidationError("Frozen trader desks cannot publish or modify adverts.")
        side = payload.side.value if hasattr(payload.side, "value") else str(payload.side)
        pricing_mode = (
            payload.pricing_mode.value if hasattr(payload.pricing_mode, "value") else str(payload.pricing_mode)
        )
        status_val = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
        if status_val == CoinAdvertStatus.ADMIN_PAUSED.value:
            raise CoinTraderValidationError("Traders cannot set admin_paused status.")
        if payload.max_coin_amount > Decimal("0") and payload.max_coin_amount < payload.min_coin_amount:
            raise CoinTraderValidationError("Maximum order quantity cannot be below minimum order quantity.")

        methods = [m.strip() for m in payload.payment_methods if m and m.strip()]
        if not methods:
            methods = self.service._public_payment_method_labels(list(profile.payment_methods_json or []))
        if status_val == CoinAdvertStatus.ACTIVE.value and not methods:
            raise CoinTraderValidationError("Select at least one accepted payment method before publishing an advert.")

        fiat = payload.fiat_currency.upper()
        advert = self.session.scalar(
            select(CoinTraderAdvert).where(
                CoinTraderAdvert.trader_profile_id == profile.id,
                CoinTraderAdvert.coin_unit == payload.coin_unit,
                CoinTraderAdvert.fiat_currency == fiat,
                CoinTraderAdvert.side == side,
            )
        )
        if (
            advert is not None
            and advert.status == CoinAdvertStatus.ADMIN_PAUSED.value
            and status_val == CoinAdvertStatus.ACTIVE.value
        ):
            raise CoinTraderValidationError(
                "This advert was paused by an administrator and cannot be resumed by the merchant."
            )
        if advert is None:
            advert = CoinTraderAdvert(
                trader_profile_id=profile.id,
                coin_unit=payload.coin_unit,
                fiat_currency=fiat,
                side=side,
                price_fiat=payload.price_fiat,
            )
            self.session.add(advert)

        advert.pricing_mode = pricing_mode
        advert.price_fiat = _q4(payload.price_fiat)
        advert.spread_fiat = _q4(payload.spread_fiat)
        advert.min_coin_amount = _q4(payload.min_coin_amount)
        advert.max_coin_amount = _q4(payload.max_coin_amount)
        advert.daily_limit_coin = _q4(payload.daily_limit_coin) if payload.daily_limit_coin is not None else None
        advert.payment_window_minutes = payload.payment_window_minutes
        advert.payment_methods_json = methods
        advert.terms_text = payload.terms_text.strip() if payload.terms_text else None
        advert.status = status_val

        settings = TreasuryService().ensure_settings(self.session)
        effective_price, _, _ = self.resolve_advert_price(advert, settings=settings)
        gov = CoinTraderPricingGovernanceService(self.session)
        reasons = gov.evaluate_side(coin_unit=advert.coin_unit, side=side, price=effective_price)
        if reasons:
            raise CoinTraderValidationError("; ".join(reasons))

        if status_val == CoinAdvertStatus.ACTIVE.value and side == CoinAdvertSide.SELL.value:
            wallet_avail = self.service._trader_available_balance(profile, advert.coin_unit)
            if wallet_avail <= Decimal("0") or (
                advert.min_coin_amount > Decimal("0") and wallet_avail < advert.min_coin_amount
            ):
                raise CoinTraderValidationError(
                    "Insufficient available wallet inventory to activate this sell advert. Acquire inventory first."
                )

        profile.last_active_at = utcnow()
        self._sync_rate_from_advert(advert, profile, effective_price)
        self.session.commit()
        self.session.refresh(advert)
        return self.to_advert_view(advert, profile=profile, settings=settings)

    def update_my_advert_status(
        self, advert_id: str, payload: CoinTraderAdvertStatusUpdateRequest, *, actor: User
    ) -> CoinTraderAdvertView:
        from app.coin_traders.service import (
            CoinTraderNotFoundError,
            CoinTraderPermissionError,
            CoinTraderValidationError,
        )

        profile = self.service._require_approved_profile_for_user(actor)
        advert = self.session.get(CoinTraderAdvert, advert_id)
        if advert is None:
            raise CoinTraderNotFoundError("Coin trader advert was not found.")
        if advert.trader_profile_id != profile.id:
            raise CoinTraderPermissionError("You do not own this advert.")
        if advert.status == CoinAdvertStatus.ADMIN_PAUSED.value and payload.status == CoinAdvertStatus.ACTIVE.value:
            raise CoinTraderValidationError("Adverts paused by GTEX Compliance can only be resumed by an admin.")
        if payload.status == CoinAdvertStatus.ACTIVE.value:
            if profile.frozen_at is not None or profile.status == CoinTraderProfileStatus.FROZEN.value:
                raise CoinTraderValidationError("Frozen trader desks cannot resume adverts.")
            effective_price, _, _ = self.resolve_advert_price(advert)
            reasons = CoinTraderPricingGovernanceService(self.session).evaluate_side(
                coin_unit=advert.coin_unit, side=advert.side, price=effective_price
            )
            if reasons:
                raise CoinTraderValidationError("; ".join(reasons))
            if advert.side == CoinAdvertSide.SELL.value:
                wallet_avail = self.service._trader_available_balance(profile, advert.coin_unit)
                if wallet_avail <= Decimal("0") or (
                    advert.min_coin_amount > Decimal("0") and wallet_avail < advert.min_coin_amount
                ):
                    raise CoinTraderValidationError(
                        "Insufficient available wallet inventory to activate this sell advert."
                    )

        advert.status = payload.status
        profile.last_active_at = utcnow()
        effective_price, _, _ = self.resolve_advert_price(advert)
        self._sync_rate_from_advert(advert, profile, effective_price)
        self.session.commit()
        self.session.refresh(advert)
        return self.to_advert_view(advert, profile=profile)

    def _sync_rate_from_advert(
        self, advert: CoinTraderAdvert, profile: CoinTraderProfile, effective_price: Decimal
    ) -> None:
        rate = self.session.scalar(
            select(CoinTraderRate).where(
                CoinTraderRate.trader_profile_id == profile.id,
                CoinTraderRate.coin_unit == advert.coin_unit,
                CoinTraderRate.fiat_currency == advert.fiat_currency,
            )
        )
        if rate is None:
            rate = CoinTraderRate(
                trader_profile_id=profile.id,
                coin_unit=advert.coin_unit,
                fiat_currency=advert.fiat_currency,
                buy_rate_fiat=effective_price if advert.side == CoinAdvertSide.BUY.value else Decimal("0.0000"),
                sell_rate_fiat=effective_price if advert.side == CoinAdvertSide.SELL.value else Decimal("0.0000"),
                min_coin_amount=advert.min_coin_amount,
                max_coin_amount=advert.max_coin_amount,
                available_liquidity=self.service._trader_available_balance(profile, advert.coin_unit),
                is_active=advert.status == CoinAdvertStatus.ACTIVE.value,
            )
            self.session.add(rate)
        else:
            if advert.side == CoinAdvertSide.BUY.value:
                rate.buy_rate_fiat = effective_price
            else:
                rate.sell_rate_fiat = effective_price
            rate.min_coin_amount = advert.min_coin_amount
            rate.max_coin_amount = advert.max_coin_amount
            if advert.status == CoinAdvertStatus.ACTIVE.value:
                rate.is_active = True
                rate.available_liquidity = self.service._trader_available_balance(profile, advert.coin_unit)
            else:
                other_active = self.session.scalar(
                    select(CoinTraderAdvert).where(
                        CoinTraderAdvert.trader_profile_id == profile.id,
                        CoinTraderAdvert.coin_unit == advert.coin_unit,
                        CoinTraderAdvert.fiat_currency == advert.fiat_currency,
                        CoinTraderAdvert.id != advert.id,
                        CoinTraderAdvert.status == CoinAdvertStatus.ACTIVE.value,
                    )
                )
                if other_active is None:
                    rate.is_active = False

    def get_merchant_dashboard(self, *, actor: User) -> CoinTraderDashboardView:
        profile = self.service._require_profile_for_user(actor)
        trader_user = self.service._require_user(profile.user_id)
        ws = self.service.wallet_service
        coin_sum = ws.get_wallet_summary(self.session, trader_user, currency=LedgerUnit.COIN)
        credit_sum = ws.get_wallet_summary(self.session, trader_user, currency=LedgerUnit.CREDIT)

        orders = list(
            self.session.scalars(select(CoinTradeOrder).where(CoinTradeOrder.trader_profile_id == profile.id)).all()
        )
        counts = CoinTraderDashboardOrderCountsView(
            new_orders=sum(1 for o in orders if o.status == CoinTradeOrderStatus.CREATED.value),
            awaiting_payment=sum(1 for o in orders if o.status == CoinTradeOrderStatus.PAYMENT_PENDING.value),
            payment_submitted=sum(1 for o in orders if o.status == CoinTradeOrderStatus.PROOF_SUBMITTED.value),
            completed=sum(
                1
                for o in orders
                if o.status in {CoinTradeOrderStatus.RELEASED.value, CoinTradeOrderStatus.ADMIN_RELEASED.value}
            ),
            cancelled=sum(
                1
                for o in orders
                if o.status
                in {
                    CoinTradeOrderStatus.CANCELLED.value,
                    CoinTradeOrderStatus.REFUNDED.value,
                    CoinTradeOrderStatus.ADMIN_REFUNDED.value,
                }
            ),
            expired=sum(1 for o in orders if o.status == CoinTradeOrderStatus.EXPIRED.value),
            disputed=sum(1 for o in orders if o.status == CoinTradeOrderStatus.DISPUTED.value),
        )

        # Compute realised trading margin only where matched buy + sell volume exists for the same asset
        completed_set = {CoinTradeOrderStatus.RELEASED.value, CoinTradeOrderStatus.ADMIN_RELEASED.value}
        completed_orders = [o for o in orders if o.status in completed_set]
        realised_profit: Decimal | None = None
        profit_total = Decimal("0.0000")
        matched_any = False
        for unit in (LedgerUnit.COIN, LedgerUnit.CREDIT):
            buys = [
                o
                for o in completed_orders
                if o.coin_unit == unit and o.direction == CoinTradeDirection.USER_SELLS.value
            ]
            sells = [
                o for o in completed_orders if o.coin_unit == unit and o.direction == CoinTradeDirection.USER_BUYS.value
            ]
            bought_qty = sum((Decimal(o.coin_amount) for o in buys), Decimal("0"))
            sold_qty = sum((Decimal(o.coin_amount) for o in sells), Decimal("0"))
            if bought_qty > Decimal("0") and sold_qty > Decimal("0"):
                avg_buy = sum((Decimal(o.fiat_total) for o in buys), Decimal("0")) / bought_qty
                avg_sell = sum((Decimal(o.fiat_total) for o in sells), Decimal("0")) / sold_qty
                matched_qty = min(bought_qty, sold_qty)
                profit_total += (avg_sell - avg_buy) * matched_qty
                matched_any = True
        if matched_any:
            realised_profit = _q2(profit_total)
            profit_note = "Estimated from matched completed P2P buy and sell orders."
        else:
            profit_note = "Insufficient matched buy/sell P2P cycles to measure realised spread yet."

        adverts = self.list_my_adverts(actor=actor)
        return CoinTraderDashboardView(
            profile=self.service.to_profile_view(profile),
            balances=CoinTraderWalletBalancesView(
                coin_available=_q4(coin_sum.available_balance),
                coin_reserved=_q4(coin_sum.reserved_balance),
                credit_available=_q4(credit_sum.available_balance),
                credit_reserved=_q4(credit_sum.reserved_balance),
            ),
            order_counts=counts,
            performance=CoinTraderDashboardPerformanceView(
                total_volume_fiat=_q2(profile.completed_volume_fiat),
                completed_orders=profile.completed_orders_count or counts.completed,
                total_orders=profile.total_orders_count or len(orders),
                completion_rate=round(float(profile.completion_rate or 0.0), 1),
                average_release_minutes=round(float(profile.average_release_minutes or 0.0), 1),
                rating=round(float(profile.rating or 0.0), 2),
                rating_count=profile.rating_count or 0,
                dispute_score=round(float(profile.dispute_score or 0.0), 1),
                realised_profit_fiat=realised_profit,
                realised_profit_note=profit_note,
            ),
            adverts=adverts,
        )

    def submit_order_rating(
        self, order_id: str, payload: CoinTradeRatingCreateRequest, *, actor: User
    ) -> CoinTradeRatingView:
        from app.coin_traders.service import CoinTraderPermissionError, CoinTraderValidationError

        order = self.service._require_order(order_id)
        if order.user_id != actor.id:
            raise CoinTraderPermissionError("Only the customer who placed the order can rate this merchant.")
        if order.status not in {CoinTradeOrderStatus.RELEASED.value, CoinTradeOrderStatus.ADMIN_RELEASED.value}:
            raise CoinTraderValidationError("You can only rate completed transactions.")
        existing = self.session.scalar(select(CoinTradeRating).where(CoinTradeRating.order_id == order.id))
        if existing is not None:
            raise CoinTraderValidationError("This order has already been rated.")

        rating_row = CoinTradeRating(
            order_id=order.id,
            trader_profile_id=order.trader_profile_id,
            user_id=actor.id,
            score=payload.score,
            comment=payload.comment.strip() if payload.comment else None,
        )
        self.session.add(rating_row)
        self.session.flush()
        profile = self.service._require_profile(order.trader_profile_id)
        self.service._refresh_profile_metrics(profile)
        self.session.commit()
        self.session.refresh(rating_row)
        return CoinTradeRatingView(
            id=rating_row.id,
            order_id=rating_row.order_id,
            trader_profile_id=rating_row.trader_profile_id,
            user_id=rating_row.user_id,
            score=rating_row.score,
            comment=rating_row.comment,
            created_at=rating_row.created_at,
        )

    # --- Admin controls & monitoring ---

    def admin_overview(self) -> CoinTraderAdminOverviewView:
        profiles = list(self.session.scalars(select(CoinTraderProfile)).all())
        adverts = list(self.session.scalars(select(CoinTraderAdvert)).all())
        orders = list(self.session.scalars(select(CoinTradeOrder)).all())
        active_escrow_statuses = {
            CoinTradeOrderStatus.CREATED.value,
            CoinTradeOrderStatus.PAYMENT_PENDING.value,
            CoinTradeOrderStatus.PROOF_SUBMITTED.value,
            CoinTradeOrderStatus.DISPUTED.value,
        }
        completed_statuses = {CoinTradeOrderStatus.RELEASED.value, CoinTradeOrderStatus.ADMIN_RELEASED.value}
        gov_blocks = self.session.scalar(
            select(func.count(SystemEvent.id)).where(SystemEvent.event_type == "coin_trader_pricing_governance")
        )
        return CoinTraderAdminOverviewView(
            total_traders=len(profiles),
            approved_traders=sum(1 for p in profiles if p.status == CoinTraderProfileStatus.APPROVED.value),
            didit_verified_traders=sum(1 for p in profiles if _is_didit_verified(p)),
            suspended_or_frozen_traders=sum(
                1
                for p in profiles
                if p.suspended_at is not None
                or p.frozen_at is not None
                or p.status in {CoinTraderProfileStatus.SUSPENDED.value, CoinTraderProfileStatus.FROZEN.value}
            ),
            active_adverts=sum(1 for a in adverts if a.status == CoinAdvertStatus.ACTIVE.value),
            total_orders=len(orders),
            active_escrow_orders=sum(1 for o in orders if o.status in active_escrow_statuses),
            disputed_orders=sum(1 for o in orders if o.status == CoinTradeOrderStatus.DISPUTED.value),
            completed_volume_fiat=_q2(
                sum((Decimal(o.fiat_total) for o in orders if o.status in completed_statuses), Decimal("0"))
            ),
            total_escrowed_coin=_q4(
                sum(
                    (
                        Decimal(o.coin_amount)
                        for o in orders
                        if o.coin_unit == LedgerUnit.COIN and o.status in active_escrow_statuses
                    ),
                    Decimal("0"),
                )
            ),
            total_escrowed_credit=_q4(
                sum(
                    (
                        Decimal(o.coin_amount)
                        for o in orders
                        if o.coin_unit == LedgerUnit.CREDIT and o.status in active_escrow_statuses
                    ),
                    Decimal("0"),
                )
            ),
            recent_governance_blocks=int(gov_blocks or 0),
        )

    def admin_list_adverts(self, *, status_filter: str | None = None) -> list[CoinTraderAdvertView]:
        stmt = select(CoinTraderAdvert).order_by(CoinTraderAdvert.updated_at.desc())
        if status_filter:
            stmt = stmt.where(CoinTraderAdvert.status == status_filter)
        adverts = list(self.session.scalars(stmt).all())
        settings = TreasuryService().ensure_settings(self.session)
        return [self.to_advert_view(a, settings=settings) for a in adverts]

    def admin_pause_advert(
        self, advert_id: str, payload: CoinTraderAdminAdvertPauseRequest, *, admin: User
    ) -> CoinTraderAdvertView:
        from app.coin_traders.service import CoinTraderNotFoundError

        advert = self.session.get(CoinTraderAdvert, advert_id)
        if advert is None:
            raise CoinTraderNotFoundError("Coin trader advert was not found.")
        advert.status = CoinAdvertStatus.ADMIN_PAUSED.value
        advert.admin_paused_reason = payload.reason.strip()
        profile = self.service._require_profile(advert.trader_profile_id)
        effective_price, _, _ = self.resolve_advert_price(advert)
        self._sync_rate_from_advert(advert, profile, effective_price)
        self.service._write_audit_log(
            actor=admin,
            action_key="coin_trader.advert.admin_pause",
            resource_type="coin_trader_advert",
            resource_id=advert.id,
            detail=f"Admin paused advert {advert.id}: {advert.admin_paused_reason}",
            metadata={"trader_profile_id": profile.id, "reason": advert.admin_paused_reason},
        )
        self.session.commit()
        self.session.refresh(advert)
        return self.to_advert_view(advert, profile=profile)

    def admin_resume_advert(self, advert_id: str, *, admin: User) -> CoinTraderAdvertView:
        from app.coin_traders.service import CoinTraderNotFoundError

        advert = self.session.get(CoinTraderAdvert, advert_id)
        if advert is None:
            raise CoinTraderNotFoundError("Coin trader advert was not found.")
        advert.status = CoinAdvertStatus.ACTIVE.value
        advert.admin_paused_reason = None
        profile = self.service._require_profile(advert.trader_profile_id)
        effective_price, _, _ = self.resolve_advert_price(advert)
        self._sync_rate_from_advert(advert, profile, effective_price)
        self.service._write_audit_log(
            actor=admin,
            action_key="coin_trader.advert.admin_resume",
            resource_type="coin_trader_advert",
            resource_id=advert.id,
            detail=f"Admin resumed advert {advert.id}.",
            metadata={"trader_profile_id": profile.id},
        )
        self.session.commit()
        self.session.refresh(advert)
        return self.to_advert_view(advert, profile=profile)

    def admin_list_audit_logs(self, *, limit: int = 100) -> list[CoinTraderAdminAuditLogView]:
        rows = list(
            self.session.scalars(
                select(AuditLog)
                .where(
                    AuditLog.resource_type.in_(
                        ["coin_trader_profile", "coin_trader_advert", "coin_trade_order", "coin_trader_config"]
                    )
                )
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
            ).all()
        )
        return [
            CoinTraderAdminAuditLogView(
                id=r.id,
                actor_user_id=r.actor_user_id,
                action_key=r.action_key,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                outcome=r.outcome,
                detail=r.detail,
                metadata_json=dict(r.metadata_json or {}),
                created_at=r.created_at,
            )
            for r in rows
        ]

    def admin_update_config(
        self, payload: CoinTraderAdminConfigUpdateRequest, *, admin: User
    ) -> CoinTraderMarketReferenceView:
        settings = TreasuryService().ensure_settings(self.session)
        changed: dict[str, Any] = {}
        for field_name in (
            "deposit_rate_value",
            "withdrawal_rate_value",
            "fan_coin_deposit_rate_value",
            "trader_fan_coin_purchase_rate_value",
            "min_trader_buy_rate_fiat",
            "max_trader_buy_rate_fiat",
            "min_trader_sell_rate_fiat",
            "max_trader_sell_rate_fiat",
            "max_trader_spread_fiat",
            "max_buy_above_withdrawal_fiat",
            "max_sell_below_deposit_fiat",
        ):
            val = getattr(payload, field_name)
            if val is not None:
                old = getattr(settings, field_name)
                setattr(settings, field_name, val)
                changed[field_name] = {"from": str(old), "to": str(val)}
        if changed:
            self.service._write_audit_log(
                actor=admin,
                action_key="coin_trader.config.update",
                resource_type="coin_trader_config",
                resource_id=settings.id,
                detail="Admin updated coin trader marketplace pricing guardrails.",
                metadata={"changes": changed},
            )
            self.session.commit()
        return self.get_market_reference()
