from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from backend.app.core.config import Settings
from backend.app.ingestion.models import Player
from backend.app.matching.models import TradeExecution
from backend.app.models.base import utcnow
from backend.app.models.user import KycStatus, User
from backend.app.models.wallet import LedgerAccount, LedgerEntry, LedgerEntryReason, LedgerUnit, PayoutRequest, PayoutStatus
from backend.app.orders.models import Order, OrderSide, OrderStatus
from backend.app.players.read_models import PlayerSummaryReadModel

AMOUNT_QUANTUM = Decimal("0.0001")
BUYBACK_BAND_CODES = ("a", "b", "c", "d", "e")
LIQUIDITY_TO_PAYOUT_BAND = {
    "entry": "a",
    "growth": "b",
    "premium": "c",
    "bluechip": "d",
    "marquee": "e",
}


class AdminBuybackError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AdminBuybackPreview:
    order_id: str
    player_id: str
    eligible: bool
    reasons: tuple[str, ...]
    message: str
    country: str | None
    fair_value: Decimal
    estimated_p2p_unit_price: Decimal
    estimated_p2p_total: Decimal
    admin_unit_price: Decimal
    admin_total: Decimal
    payout_ratio: Decimal
    liquidity_band: str
    payout_band: str
    p2p_priority_window_hours: int
    p2p_priority_window_ends_at: datetime | None
    minimum_hold_days: int
    minimum_hold_expires_at: datetime | None
    hold_days_remaining: int


@dataclass(frozen=True, slots=True)
class AdminBuybackExecution:
    preview: AdminBuybackPreview
    order: Order
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    executed_at: datetime


class AdminBuybackService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def preview(self, session: Session, *, user: User, order: Order) -> AdminBuybackPreview:
        reasons: list[str] = []
        remaining_quantity = self._normalize_amount(order.remaining_quantity)
        fair_value = self._resolve_fair_value(session, order)
        p2p_unit_price = fair_value
        p2p_total = self._normalize_amount(remaining_quantity * p2p_unit_price)
        liquidity_band = self._resolve_liquidity_band(session, order.player_id, fair_value)
        payout_band = self._resolve_payout_band(liquidity_band)
        payout_ratio = self._normalize_amount(
            self.settings.admin_buyback.band_payouts.get(payout_band, 0.0)
        )
        admin_unit_price = self._normalize_amount(fair_value * payout_ratio)
        admin_total = self._normalize_amount(remaining_quantity * admin_unit_price)
        country = self._resolve_country_signal(session, user)
        window_ends_at = self._p2p_priority_window_ends_at(order)
        minimum_hold_expires_at = self._minimum_hold_expires_at(session, user, order.player_id)
        hold_days_remaining = self._remaining_full_days(minimum_hold_expires_at)

        if order.side is not OrderSide.SELL:
            reasons.append("Admin quick exit is only available for sell orders.")
        if order.status not in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED}:
            reasons.append("Only open sell orders can use admin quick exit.")
        if remaining_quantity <= Decimal("0.0000"):
            reasons.append("This order no longer has any quantity available to sell.")
        if fair_value <= Decimal("0.0000"):
            reasons.append("Fair value is unavailable for this player right now.")
        if country is None or not self._is_country_eligible(country):
            reasons.append("Your country is not eligible for admin fallback liquidity.")
        if user.kyc_status is not KycStatus.VERIFIED:
            reasons.append("KYC verification is required before selling to admin.")
        if not user.is_active:
            reasons.append("Your account is under an integrity hold.")
        if self._has_held_payout(session, user):
            reasons.append("A payout hold must be cleared before admin quick exit can be used.")
        if window_ends_at is not None and self._normalize_datetime(window_ends_at) > utcnow():
            reasons.append(
                f"P2P remains the default path until {self._normalize_datetime(window_ends_at).isoformat()}."
            )
        if minimum_hold_expires_at is None:
            reasons.append("Holding history is unavailable for this position.")
        elif self._normalize_datetime(minimum_hold_expires_at) > utcnow():
            reasons.append(
                f"Holdings must be held for at least {self.settings.admin_buyback.minimum_hold_days} days before admin fallback."
            )
        if self._has_wash_trade_signal(session, user, order.player_id):
            reasons.append("Recent buy and sell activity on this player looks like wash trading.")
        if self._has_recent_admin_reserve_purchase(session, user, order.player_id):
            reasons.append("Recent admin reserve purchases are not eligible for admin quick exit.")

        return AdminBuybackPreview(
            order_id=order.id,
            player_id=order.player_id,
            eligible=not reasons,
            reasons=tuple(reasons),
            message=(
                "P2P listings usually pay more. Admin quick exit is a lower fallback after the priority window ends."
            ),
            country=country,
            fair_value=fair_value,
            estimated_p2p_unit_price=p2p_unit_price,
            estimated_p2p_total=p2p_total,
            admin_unit_price=admin_unit_price,
            admin_total=admin_total,
            payout_ratio=payout_ratio,
            liquidity_band=liquidity_band,
            payout_band=payout_band.upper(),
            p2p_priority_window_hours=self.settings.admin_buyback.p2p_priority_window_hours,
            p2p_priority_window_ends_at=window_ends_at,
            minimum_hold_days=self.settings.admin_buyback.minimum_hold_days,
            minimum_hold_expires_at=minimum_hold_expires_at,
            hold_days_remaining=hold_days_remaining,
        )

    def _resolve_fair_value(self, session: Session, order: Order) -> Decimal:
        summary = session.get(PlayerSummaryReadModel, order.player_id)
        if summary is not None and summary.current_value_credits > 0:
            return self._normalize_amount(summary.current_value_credits)
        return self._normalize_amount(order.max_price)

    def _resolve_liquidity_band(self, session: Session, player_id: str, fair_value: Decimal) -> str:
        summary = session.get(PlayerSummaryReadModel, player_id)
        if summary is not None:
            liquidity_payload = (summary.summary_json or {}).get("liquidity_band")
            if isinstance(liquidity_payload, dict):
                code = str(liquidity_payload.get("code") or liquidity_payload.get("name") or "").strip().lower()
                if code:
                    return code
            if isinstance(liquidity_payload, str) and liquidity_payload.strip():
                return liquidity_payload.strip().lower()

        player = session.get(Player, player_id)
        if player is not None and player.liquidity_band is not None:
            return str(player.liquidity_band.code).strip().lower()

        for band in self.settings.liquidity_bands.bands:
            min_price = Decimal(str(band.min_price_credits))
            max_price = None if band.max_price_credits is None else Decimal(str(band.max_price_credits))
            if fair_value >= min_price and (max_price is None or fair_value <= max_price):
                return band.code.strip().lower()
        return "premium"

    def _resolve_payout_band(self, liquidity_band: str) -> str:
        normalized = liquidity_band.strip().lower()
        configured_codes = [band.code.strip().lower() for band in self.settings.liquidity_bands.bands]
        if normalized in LIQUIDITY_TO_PAYOUT_BAND:
            return LIQUIDITY_TO_PAYOUT_BAND[normalized]
        if normalized in configured_codes:
            index = configured_codes.index(normalized)
            if index < len(BUYBACK_BAND_CODES):
                return BUYBACK_BAND_CODES[index]
        return "c"

    def _resolve_country_signal(self, session: Session, user: User) -> str | None:
        bind = session.get_bind()
        if bind is None:
            return None
        try:
            available_columns = {str(item["name"]).lower() for item in inspect(bind).get_columns("users")}
        except Exception:
            return None
        for column_name in ("nationality", "country", "country_name", "country_code"):
            if column_name not in available_columns:
                continue
            value = session.execute(
                text(f"SELECT {column_name} FROM users WHERE id = :user_id"),
                {"user_id": user.id},
            ).scalar_one_or_none()
            if value is None:
                continue
            candidate = str(value).strip()
            if candidate:
                return candidate
        return None

    def _is_country_eligible(self, country: str) -> bool:
        normalized = country.strip().lower()
        allowed = {
            *{value.strip().lower() for value in self.settings.admin_buyback.nigeria_aliases},
            *{value.strip().lower() for value in self.settings.admin_buyback.african_allowlist},
        }
        return normalized in allowed

    def _has_held_payout(self, session: Session, user: User) -> bool:
        return (
            session.scalar(
                select(PayoutRequest.id)
                .where(
                    PayoutRequest.user_id == user.id,
                    PayoutRequest.status == PayoutStatus.HELD,
                )
                .limit(1)
            )
            is not None
        )

    def _minimum_hold_expires_at(self, session: Session, user: User, player_id: str) -> datetime | None:
        latest_credit_at = session.scalar(
            select(LedgerEntry.created_at)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.code.like(f"position:{user.id}:{player_id}:%"),
                LedgerEntry.unit == LedgerUnit.COIN,
                LedgerEntry.reason == LedgerEntryReason.TRADE_SETTLEMENT,
                LedgerEntry.amount > Decimal("0.0000"),
            )
            .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
            .limit(1)
        )
        if latest_credit_at is None:
            return None
        return self._normalize_datetime(latest_credit_at) + timedelta(
            days=self.settings.admin_buyback.minimum_hold_days
        )

    def _has_wash_trade_signal(self, session: Session, user: User, player_id: str) -> bool:
        cutoff = utcnow() - timedelta(hours=self.settings.admin_buyback.wash_trade_lookback_hours)
        buy_execution = session.scalar(
            select(TradeExecution.id)
            .join(Order, Order.id == TradeExecution.buy_order_id)
            .where(
                Order.user_id == user.id,
                TradeExecution.player_id == player_id,
                TradeExecution.created_at >= cutoff,
            )
            .limit(1)
        )
        sell_execution = session.scalar(
            select(TradeExecution.id)
            .join(Order, Order.id == TradeExecution.sell_order_id)
            .where(
                Order.user_id == user.id,
                TradeExecution.player_id == player_id,
                TradeExecution.created_at >= cutoff,
            )
            .limit(1)
        )
        return buy_execution is not None and sell_execution is not None

    def _has_recent_admin_reserve_purchase(self, session: Session, user: User, player_id: str) -> bool:
        cutoff = utcnow() - timedelta(days=self.settings.admin_buyback.admin_reserve_cooldown_days)
        return (
            session.scalar(
                select(LedgerEntry.id)
                .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
                .where(
                    LedgerAccount.code.like(f"position:{user.id}:{player_id}:%"),
                    LedgerEntry.amount > Decimal("0.0000"),
                    LedgerEntry.created_at >= cutoff,
                    LedgerEntry.external_reference.like("godmode:sell_to_user:%"),
                )
                .limit(1)
            )
            is not None
        )

    def _p2p_priority_window_ends_at(self, order: Order) -> datetime | None:
        if order.created_at is None:
            return None
        return self._normalize_datetime(order.created_at) + timedelta(
            hours=self.settings.admin_buyback.p2p_priority_window_hours
        )

    def _remaining_full_days(self, expires_at: datetime | None) -> int:
        if expires_at is None:
            return 0
        remaining = self._normalize_datetime(expires_at) - utcnow()
        if remaining.total_seconds() <= 0:
            return 0
        return int((remaining.total_seconds() + 86399) // 86400)

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _normalize_amount(value: Decimal | float | int | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)
