from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re
from typing import Any

from sqlalchemy import inspect, or_, select, table, column
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.matching.models import TradeExecution
from backend.app.models.user import KycStatus, User
from backend.app.models.wallet import LedgerAccount, LedgerEntry, LedgerEntryReason, PayoutRequest, PayoutStatus
from backend.app.orders.models import Order, OrderSide, OrderStatus
from backend.app.players.read_models import PlayerSummaryReadModel
from backend.app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
NON_ALPHANUMERIC_RE = re.compile(r"[^a-z0-9]+")
BUYBACK_BAND_SEQUENCE = ("A", "B", "C", "D", "E")


@dataclass(frozen=True, slots=True)
class AdminBuybackPreview:
    order_id: str
    player_id: str
    remaining_quantity: Decimal
    country: str | None
    liquidity_band_code: str | None
    liquidity_band_name: str | None
    buyback_band: str
    payout_ratio: Decimal
    fair_value_unit_price: Decimal
    fair_value_total: Decimal
    expected_p2p_unit_price: Decimal
    expected_p2p_total: Decimal
    admin_unit_price: Decimal
    admin_total: Decimal
    p2p_priority_ends_at: datetime
    country_eligible: bool
    kyc_eligible: bool
    priority_window_satisfied: bool
    minimum_hold_satisfied: bool
    integrity_clear: bool
    wash_trade_clear: bool
    reserve_cooldown_clear: bool
    eligible: bool
    reasons: tuple[str, ...]
    message: str


@dataclass(frozen=True, slots=True)
class AdminBuybackExecution:
    preview: AdminBuybackPreview
    execution_id: str
    settled_at: datetime


class AdminBuybackError(ValueError):
    pass


class AdminBuybackService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        wallet_service: WalletService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.wallet_service = wallet_service or WalletService()

    def preview(
        self,
        session: Session,
        *,
        user: User,
        order: Order,
        now: datetime | None = None,
    ) -> AdminBuybackPreview:
        current_time = self._ensure_utc(now or datetime.now(timezone.utc))
        order_created_at = self._ensure_utc(order.created_at)
        remaining_quantity = self._normalize_amount(order.remaining_quantity)
        country = self._load_user_country(session, user)
        reference_price = self._reference_price(session, order)
        liquidity_band_code, liquidity_band_name = self._resolve_liquidity_band(session, order, reference_price)
        buyback_band = self._buyback_band_for_liquidity_code(liquidity_band_code)
        payout_ratio = self._normalize_amount(
            self.settings.admin_buyback.band_payouts.get(buyback_band.lower(), 0.45)
        )
        fair_value_total = self._normalize_amount(reference_price * remaining_quantity)
        admin_unit_price = self._normalize_amount(reference_price * payout_ratio)
        admin_total = self._normalize_amount(admin_unit_price * remaining_quantity)
        p2p_priority_ends_at = order_created_at + timedelta(
            hours=self.settings.admin_buyback.p2p_priority_window_hours
        )
        country_eligible = self._country_is_eligible(country)
        kyc_eligible = user.kyc_status == KycStatus.VERIFIED
        priority_window_satisfied = current_time >= p2p_priority_ends_at
        minimum_hold_satisfied = not self._has_recent_position_credit(
            session,
            user=user,
            player_id=order.player_id,
            current_time=current_time,
        )
        integrity_clear = not self._has_integrity_hold(session, user=user)
        wash_trade_clear = not self._has_obvious_wash_trade_flag(
            session,
            user=user,
            order=order,
            current_time=current_time,
        )
        reserve_cooldown_clear = not self._has_recent_admin_reserve_purchase(
            session,
            user=user,
            player_id=order.player_id,
            current_time=current_time,
        )

        reasons: list[str] = []
        if order.side != OrderSide.SELL:
            reasons.append("Admin quick-exit is available only for sell orders.")
        if order.status not in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED}:
            reasons.append("Only open or partially filled sell orders can use admin quick-exit.")
        if remaining_quantity <= Decimal("0.0000"):
            reasons.append("This sell order has no remaining quantity for admin quick-exit.")
        if reference_price <= Decimal("0.0000"):
            reasons.append("Fair value is unavailable for this player right now, so admin quick-exit is disabled.")
        if not country_eligible:
            reasons.append(
                "Admin quick-exit is limited to Nigeria and the configured African-country allowlist."
            )
        if not kyc_eligible:
            reasons.append("KYC must be verified before admin quick-exit is enabled.")
        if not priority_window_satisfied:
            reasons.append(
                f"P2P remains the priority until {self._format_dt(p2p_priority_ends_at)}."
            )
        if not minimum_hold_satisfied:
            reasons.append(
                f"Admin quick-exit unlocks only after a {self.settings.admin_buyback.minimum_hold_days}-day hold period."
            )
        if not integrity_clear:
            reasons.append("An integrity or payout hold is active on this account.")
        if not wash_trade_clear:
            reasons.append("Recent two-way trading activity on this player blocks admin quick-exit for now.")
        if not reserve_cooldown_clear:
            reasons.append("Recent inventory bought directly from admin reserve cannot be sold back immediately.")

        eligible = not reasons
        message = self._message_for_preview(
            eligible=eligible,
            reasons=tuple(reasons),
            admin_total=admin_total,
            fair_value_total=fair_value_total,
            p2p_priority_ends_at=p2p_priority_ends_at,
            priority_window_satisfied=priority_window_satisfied,
        )
        return AdminBuybackPreview(
            order_id=order.id,
            player_id=order.player_id,
            remaining_quantity=remaining_quantity,
            country=country,
            liquidity_band_code=liquidity_band_code,
            liquidity_band_name=liquidity_band_name,
            buyback_band=buyback_band,
            payout_ratio=payout_ratio,
            fair_value_unit_price=reference_price,
            fair_value_total=fair_value_total,
            expected_p2p_unit_price=reference_price,
            expected_p2p_total=fair_value_total,
            admin_unit_price=admin_unit_price,
            admin_total=admin_total,
            p2p_priority_ends_at=p2p_priority_ends_at,
            country_eligible=country_eligible,
            kyc_eligible=kyc_eligible,
            priority_window_satisfied=priority_window_satisfied,
            minimum_hold_satisfied=minimum_hold_satisfied,
            integrity_clear=integrity_clear,
            wash_trade_clear=wash_trade_clear,
            reserve_cooldown_clear=reserve_cooldown_clear,
            eligible=eligible,
            reasons=tuple(reasons),
            message=message,
        )

    def _country_is_eligible(self, country: str | None) -> bool:
        normalized = self._normalize_country(country)
        if normalized is None:
            return False
        nigeria_aliases = {self._normalize_country(item) for item in self.settings.admin_buyback.nigeria_aliases}
        allowlist = {self._normalize_country(item) for item in self.settings.admin_buyback.african_allowlist}
        normalized_nigeria_aliases = {item for item in nigeria_aliases if item is not None}
        normalized_allowlist = {item for item in allowlist if item is not None}
        return normalized in normalized_nigeria_aliases or normalized in normalized_allowlist

    def _reference_price(self, session: Session, order: Order) -> Decimal:
        summary = session.get(PlayerSummaryReadModel, order.player_id)
        if summary is not None and (summary.current_value_credits or 0) > 0:
            return self._normalize_amount(summary.current_value_credits)
        if order.max_price is not None and order.max_price > Decimal("0.0000"):
            return self._normalize_amount(order.max_price)
        return Decimal("0.0000")

    def _resolve_liquidity_band(
        self,
        session: Session,
        order: Order,
        reference_price: Decimal,
    ) -> tuple[str | None, str | None]:
        summary = session.get(PlayerSummaryReadModel, order.player_id)
        liquidity_band = ((summary.summary_json if summary is not None else {}) or {}).get("liquidity_band") or {}
        code = str(liquidity_band.get("code") or "").strip() or None
        name = str(liquidity_band.get("name") or "").strip() or None
        if code is not None:
            return code, name

        reference_value = float(reference_price)
        for band in self.settings.liquidity_bands.bands:
            upper_bound = band.max_price_credits
            if reference_value < band.min_price_credits:
                continue
            if upper_bound is None or reference_value <= upper_bound:
                return band.code, band.name
        return None, None

    def _buyback_band_for_liquidity_code(self, liquidity_band_code: str | None) -> str:
        normalized_code = (liquidity_band_code or "").strip().lower()
        ordered_codes = [band.code.strip().lower() for band in self.settings.liquidity_bands.bands]
        if normalized_code in ordered_codes:
            index = ordered_codes.index(normalized_code)
            if index < len(BUYBACK_BAND_SEQUENCE):
                return BUYBACK_BAND_SEQUENCE[index]
        known_codes = {
            "entry": "A",
            "growth": "B",
            "premium": "C",
            "bluechip": "D",
            "marquee": "E",
        }
        return known_codes.get(normalized_code, "C")

    def _has_recent_position_credit(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        current_time: datetime,
    ) -> bool:
        cutoff = current_time - timedelta(days=self.settings.admin_buyback.minimum_hold_days)
        position_code = self.wallet_service._position_account_code(user.id, player_id)
        recent_credit = session.scalar(
            select(LedgerEntry.id)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.code == position_code,
                LedgerEntry.reason == LedgerEntryReason.TRADE_SETTLEMENT,
                LedgerEntry.amount > Decimal("0.0000"),
                LedgerEntry.created_at >= cutoff,
            )
            .limit(1)
        )
        return recent_credit is not None

    def _has_integrity_hold(self, session: Session, *, user: User) -> bool:
        if not user.is_active:
            return True
        held_request = session.scalar(
            select(PayoutRequest.id)
            .where(
                PayoutRequest.user_id == user.id,
                PayoutRequest.status == PayoutStatus.HELD,
            )
            .limit(1)
        )
        return held_request is not None

    def _has_obvious_wash_trade_flag(
        self,
        session: Session,
        *,
        user: User,
        order: Order,
        current_time: datetime,
    ) -> bool:
        cutoff = current_time - timedelta(hours=self.settings.admin_buyback.wash_trade_lookback_hours)
        rows = session.execute(
            select(Order.side)
            .join(
                TradeExecution,
                or_(
                    TradeExecution.buy_order_id == Order.id,
                    TradeExecution.sell_order_id == Order.id,
                ),
            )
            .where(
                Order.user_id == user.id,
                Order.player_id == order.player_id,
                TradeExecution.created_at >= cutoff,
            )
            .distinct()
        ).all()
        sides = {row[0] for row in rows}
        return OrderSide.BUY in sides and OrderSide.SELL in sides

    def _has_recent_admin_reserve_purchase(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        current_time: datetime,
    ) -> bool:
        cooldown_days = self.settings.admin_buyback.admin_reserve_cooldown_days
        if cooldown_days <= 0:
            return False
        cutoff = current_time - timedelta(days=cooldown_days)
        position_code = self.wallet_service._position_account_code(user.id, player_id)
        recent_inventory_purchase = session.scalar(
            select(LedgerEntry.id)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.code == position_code,
                LedgerEntry.amount > Decimal("0.0000"),
                LedgerEntry.reason == LedgerEntryReason.TRADE_SETTLEMENT,
                LedgerEntry.created_at >= cutoff,
                LedgerEntry.external_reference.like("godmode:sell_to_user:%"),
            )
            .limit(1)
        )
        return recent_inventory_purchase is not None

    def _load_user_country(self, session: Session, user: User) -> str | None:
        bind = session.get_bind()
        inspector = inspect(bind)
        column_names = {str(item["name"]) for item in inspector.get_columns("users")}
        if "nationality" not in column_names:
            return None
        users_table = table("users", column("id"), column("nationality"))
        return session.scalar(select(users_table.c.nationality).where(users_table.c.id == user.id))

    @staticmethod
    def _normalize_country(value: str | None) -> str | None:
        if value is None:
            return None
        candidate = NON_ALPHANUMERIC_RE.sub("", value.strip().lower())
        return candidate or None

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _format_dt(value: datetime) -> str:
        return AdminBuybackService._ensure_utc(value).strftime("%Y-%m-%d %H:%M UTC")

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _message_for_preview(
        self,
        *,
        eligible: bool,
        reasons: tuple[str, ...],
        admin_total: Decimal,
        fair_value_total: Decimal,
        p2p_priority_ends_at: datetime,
        priority_window_satisfied: bool,
    ) -> str:
        if eligible:
            return (
                f"P2P usually pays more. Admin quick-exit is available now at {admin_total} credits, "
                f"below the fair-value estimate of {fair_value_total} credits."
            )
        if not priority_window_satisfied:
            return (
                f"P2P is still the priority path. Admin quick-exit unlocks after "
                f"{self._format_dt(p2p_priority_ends_at)} if the order is still unsold."
            )
        if reasons:
            return reasons[0]
        return "Admin quick-exit is unavailable for this sell order."
