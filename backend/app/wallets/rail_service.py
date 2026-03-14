from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.admin_godmode.service import DEFAULT_COMMISSION_SETTINGS
from backend.app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from backend.app.models.base import utcnow
from backend.app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from backend.app.models.market_topup import MarketTopup, MarketTopupStatus
from backend.app.models.risk_ops import RiskSeverity, SystemEventSeverity
from backend.app.models.treasury import PaymentMode, RateDirection, TreasurySettings
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerUnit
from backend.app.risk_ops_engine.service import RiskOpsService
from backend.app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
RISK_AMOUNT_THRESHOLD = Decimal("5000.0000")
RISK_FREQUENCY_THRESHOLD = 3
RISK_WINDOW_HOURS = 24


class WalletRailError(ValueError):
    pass


class WalletRailConflictError(WalletRailError):
    pass


@dataclass(frozen=True, slots=True)
class PurchaseOrderQuote:
    amount_fiat: Decimal
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    currency_code: str
    rate_value: Decimal
    rate_direction: RateDirection
    unit: LedgerUnit
    processor_mode: str
    payout_channel: str
    provider_key: str
    source_scope: str


@dataclass(frozen=True, slots=True)
class MarketTopupQuote:
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    unit: LedgerUnit


@dataclass(slots=True)
class WalletRailService:
    session: Session
    wallet_service: WalletService | None = None
    event_publisher: EventPublisher | None = None

    def __post_init__(self) -> None:
        if self.event_publisher is None:
            self.event_publisher = InMemoryEventPublisher()
        if self.wallet_service is None:
            self.wallet_service = WalletService(event_publisher=self.event_publisher)

    def quote_purchase_order(
        self,
        *,
        settings: TreasurySettings,
        amount: Decimal,
        input_unit: str,
        provider_key: str,
        source_scope: str,
        unit: LedgerUnit,
        processor_mode: str,
        payout_channel: str,
    ) -> PurchaseOrderQuote:
        input_unit = input_unit.strip().lower()
        if input_unit not in {"fiat", "coin"}:
            raise WalletRailError("Input unit must be fiat or coin.")
        if Decimal(amount) <= Decimal("0.0000"):
            raise WalletRailError("Purchase amount must be positive.")
        rate_value = Decimal(settings.deposit_rate_value)
        if rate_value <= Decimal("0.0000"):
            raise WalletRailError("Deposit rate is not configured.")
        amount_fiat, amount_coin = self._compute_amounts(
            amount=Decimal(amount),
            input_unit=input_unit,
            rate_value=rate_value,
            rate_direction=settings.deposit_rate_direction,
        )
        self._enforce_deposit_limits(settings, amount_coin)
        fee_bps = int(self._commission_settings().get("buy_commission_bps", 0) or 0)
        fee_amount = self._normalize_amount(amount_coin * Decimal(fee_bps) / Decimal(10_000))
        net_amount = self._normalize_amount(amount_coin - fee_amount)
        return PurchaseOrderQuote(
            amount_fiat=amount_fiat,
            gross_amount=amount_coin,
            fee_amount=fee_amount,
            net_amount=net_amount,
            currency_code=settings.currency_code,
            rate_value=rate_value,
            rate_direction=settings.deposit_rate_direction,
            unit=unit,
            processor_mode=processor_mode,
            payout_channel=payout_channel,
            provider_key=provider_key,
            source_scope=source_scope,
        )

    def create_purchase_order(
        self,
        *,
        user: User,
        settings: TreasurySettings,
        amount: Decimal,
        input_unit: str,
        provider_key: str,
        source_scope: str,
        unit: LedgerUnit,
        processor_mode: str,
        payout_channel: str,
        provider_reference: str | None = None,
        notes: str | None = None,
    ) -> FancoinPurchaseOrder:
        quote = self.quote_purchase_order(
            settings=settings,
            amount=amount,
            input_unit=input_unit,
            provider_key=provider_key,
            source_scope=source_scope,
            unit=unit,
            processor_mode=processor_mode,
            payout_channel=payout_channel,
        )
        reference = self._generate_reference(prefix="PO", model=FancoinPurchaseOrder)
        status = PurchaseOrderStatus.PROCESSING if processor_mode == "automatic_gateway" else PurchaseOrderStatus.REVIEWING
        order = FancoinPurchaseOrder(
            user_id=user.id,
            reference=reference,
            status=status,
            provider_key=provider_key,
            provider_reference=provider_reference or uuid4().hex,
            unit=unit,
            amount_fiat=quote.amount_fiat,
            gross_amount=quote.gross_amount,
            fee_amount=quote.fee_amount,
            net_amount=quote.net_amount,
            currency_code=quote.currency_code,
            rate_value=quote.rate_value,
            rate_direction=quote.rate_direction,
            processor_mode=processor_mode,
            payout_channel=payout_channel,
            source_scope=source_scope,
            notes=notes,
        )
        self.session.add(order)
        self.session.flush()
        self._flag_purchase_order_risk(order)
        self.event_publisher.publish(
            DomainEvent(
                name="wallet.purchase_order.created",
                payload={
                    "purchase_order_id": order.id,
                    "user_id": user.id,
                    "provider_key": provider_key,
                    "gross_amount": str(order.gross_amount),
                    "fee_amount": str(order.fee_amount),
                    "net_amount": str(order.net_amount),
                },
            )
        )
        return order

    def settle_purchase_order(self, *, order: FancoinPurchaseOrder, actor: User | None = None) -> FancoinPurchaseOrder:
        if order.status == PurchaseOrderStatus.SETTLED and order.ledger_transaction_id:
            return order
        user = self.session.get(User, order.user_id)
        if user is None:
            raise WalletRailError("Purchase order references a missing user.")
        user_account = self.wallet_service.get_user_account(self.session, user, order.unit)
        platform_account = self.wallet_service.ensure_platform_account(self.session, order.unit)
        postings = [
            LedgerPosting(account=user_account, amount=order.net_amount),
            LedgerPosting(account=platform_account, amount=-order.gross_amount),
        ]
        if order.fee_amount > Decimal("0.0000"):
            postings.append(LedgerPosting(account=platform_account, amount=order.fee_amount))
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.DEPOSIT,
            reference=order.reference,
            description=f"FanCoin purchase via {order.provider_key}",
            external_reference=order.provider_reference,
            actor=actor or user,
        )
        order.status = PurchaseOrderStatus.SETTLED
        order.settled_at = utcnow()
        order.ledger_transaction_id = entries[0].transaction_id if entries else order.ledger_transaction_id
        self.session.flush()
        self.event_publisher.publish(
            DomainEvent(
                name="wallet.purchase_order.settled",
                payload={
                    "purchase_order_id": order.id,
                    "user_id": order.user_id,
                    "transaction_id": order.ledger_transaction_id,
                    "net_amount": str(order.net_amount),
                },
            )
        )
        return order

    def mark_purchase_order_failed(self, *, order: FancoinPurchaseOrder, status: PurchaseOrderStatus, notes: str | None = None) -> FancoinPurchaseOrder:
        order.status = status
        order.failed_at = utcnow()
        order.notes = notes or order.notes
        self.session.flush()
        return order

    def reverse_purchase_order(
        self,
        *,
        order: FancoinPurchaseOrder,
        status: PurchaseOrderStatus,
        actor: User | None = None,
        notes: str | None = None,
    ) -> FancoinPurchaseOrder:
        if order.ledger_transaction_id is None:
            order.status = status
            order.notes = notes or order.notes
            order.reversed_at = utcnow()
            self.session.flush()
            return order
        user = self.session.get(User, order.user_id)
        if user is None:
            raise WalletRailError("Purchase order references a missing user.")
        user_account = self.wallet_service.get_user_account(self.session, user, order.unit)
        platform_account = self.wallet_service.ensure_platform_account(self.session, order.unit)
        try:
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(account=user_account, amount=-order.net_amount),
                    LedgerPosting(account=platform_account, amount=order.net_amount),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                reference=f"purchase-reversal:{order.id}",
                description=f"Reverse FanCoin purchase {order.reference}",
                external_reference=order.provider_reference,
                actor=actor,
            )
            order.status = status
            order.notes = notes or order.notes
            order.reversed_at = utcnow()
        except InsufficientBalanceError:
            order.status = PurchaseOrderStatus.DISPUTED
            order.notes = notes or order.notes
            self._create_system_event(
                event_key=f"purchase-order-dispute-{order.id}",
                severity=SystemEventSeverity.CRITICAL,
                title="Purchase order reversal failed",
                body="User balance insufficient to reverse purchase order.",
                subject_type="purchase_order",
                subject_id=order.id,
                metadata={
                    "user_id": order.user_id,
                    "net_amount": str(order.net_amount),
                    "status": status.value,
                },
            )
        self.session.flush()
        return order

    def apply_purchase_order_status(
        self,
        *,
        order: FancoinPurchaseOrder,
        status: PurchaseOrderStatus,
        actor: User | None = None,
        notes: str | None = None,
    ) -> FancoinPurchaseOrder:
        if status in {PurchaseOrderStatus.SETTLED}:
            return self.settle_purchase_order(order=order, actor=actor)
        if status in {PurchaseOrderStatus.REFUNDED, PurchaseOrderStatus.CHARGEBACK, PurchaseOrderStatus.REVERSED}:
            return self.reverse_purchase_order(order=order, status=status, actor=actor, notes=notes)
        if status in {PurchaseOrderStatus.FAILED, PurchaseOrderStatus.REJECTED, PurchaseOrderStatus.CANCELLED, PurchaseOrderStatus.EXPIRED}:
            return self.mark_purchase_order_failed(order=order, status=status, notes=notes)
        order.status = status
        order.notes = notes or order.notes
        if status == PurchaseOrderStatus.REVIEWING:
            order.reviewed_at = utcnow()
        elif status == PurchaseOrderStatus.PROCESSING:
            order.approved_at = utcnow()
        self.session.flush()
        return order

    def list_purchase_orders_for_user(self, *, user: User, limit: int = 50) -> list[FancoinPurchaseOrder]:
        return self.session.scalars(
            select(FancoinPurchaseOrder)
            .where(FancoinPurchaseOrder.user_id == user.id)
            .order_by(FancoinPurchaseOrder.created_at.desc())
            .limit(limit)
        ).all()

    def quote_market_topup(self, *, amount: Decimal, fee_bps: int, unit: LedgerUnit) -> MarketTopupQuote:
        gross_amount = self._normalize_amount(amount)
        if gross_amount <= Decimal("0.0000"):
            raise WalletRailError("Topup amount must be positive.")
        fee_amount = self._normalize_amount(gross_amount * Decimal(fee_bps) / Decimal(10_000))
        net_amount = self._normalize_amount(gross_amount - fee_amount)
        return MarketTopupQuote(
            gross_amount=gross_amount,
            fee_amount=fee_amount,
            net_amount=net_amount,
            unit=unit,
        )

    def create_market_topup(
        self,
        *,
        user: User,
        amount: Decimal,
        fee_bps: int,
        unit: LedgerUnit,
        source_scope: str,
        notes: str | None,
        requested_by: User | None = None,
    ) -> MarketTopup:
        quote = self.quote_market_topup(amount=amount, fee_bps=fee_bps, unit=unit)
        reference = self._generate_reference(prefix="MTU", model=MarketTopup)
        topup = MarketTopup(
            user_id=user.id,
            reference=reference,
            status=MarketTopupStatus.REQUESTED,
            unit=unit,
            gross_amount=quote.gross_amount,
            fee_amount=quote.fee_amount,
            net_amount=quote.net_amount,
            source_scope=source_scope,
            processor_mode="internal_transfer",
            payout_channel="internal",
            notes=notes,
            requested_by_user_id=requested_by.id if requested_by else None,
        )
        self.session.add(topup)
        self.session.flush()
        self._flag_topup_risk(topup)
        self.event_publisher.publish(
            DomainEvent(
                name="wallet.market_topup.requested",
                payload={
                    "market_topup_id": topup.id,
                    "user_id": topup.user_id,
                    "gross_amount": str(topup.gross_amount),
                    "fee_amount": str(topup.fee_amount),
                },
            )
        )
        return topup

    def apply_market_topup_status(
        self,
        *,
        topup: MarketTopup,
        status: MarketTopupStatus,
        actor: User | None = None,
        notes: str | None = None,
    ) -> MarketTopup:
        if status == MarketTopupStatus.SETTLED:
            return self.settle_market_topup(topup=topup, actor=actor)
        topup.status = status
        topup.reviewed_by_user_id = actor.id if actor else topup.reviewed_by_user_id
        topup.reviewed_at = utcnow()
        topup.notes = notes or topup.notes
        if status == MarketTopupStatus.APPROVED:
            topup.approved_at = utcnow()
        elif status == MarketTopupStatus.REJECTED:
            topup.rejected_at = utcnow()
        elif status == MarketTopupStatus.CANCELLED:
            topup.cancelled_at = utcnow()
        elif status == MarketTopupStatus.REVERSED:
            topup.reversed_at = utcnow()
        self.session.flush()
        return topup

    def settle_market_topup(self, *, topup: MarketTopup, actor: User | None = None) -> MarketTopup:
        if topup.ledger_transaction_id and topup.status == MarketTopupStatus.SETTLED:
            return topup
        user = self.session.get(User, topup.user_id)
        if user is None:
            raise WalletRailError("Market topup references a missing user.")
        user_account = self.wallet_service.get_user_account(self.session, user, topup.unit)
        platform_account = self.wallet_service.ensure_platform_account(self.session, topup.unit)
        postings = [
            LedgerPosting(account=user_account, amount=topup.net_amount),
            LedgerPosting(account=platform_account, amount=-topup.gross_amount),
        ]
        if topup.fee_amount > Decimal("0.0000"):
            postings.append(LedgerPosting(account=platform_account, amount=topup.fee_amount))
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            reference=topup.reference,
            description="Market topup credited",
            external_reference=topup.reference,
            actor=actor or user,
        )
        topup.status = MarketTopupStatus.SETTLED
        topup.processed_at = utcnow()
        topup.settled_at = utcnow()
        topup.settled_by_user_id = actor.id if actor else topup.settled_by_user_id
        topup.ledger_transaction_id = entries[0].transaction_id if entries else topup.ledger_transaction_id
        self.session.flush()
        self.event_publisher.publish(
            DomainEvent(
                name="wallet.market_topup.settled",
                payload={
                    "market_topup_id": topup.id,
                    "user_id": topup.user_id,
                    "net_amount": str(topup.net_amount),
                },
            )
        )
        return topup

    def _commission_settings(self) -> dict[str, Any]:
        return dict(DEFAULT_COMMISSION_SETTINGS)

    def _normalize_amount(self, amount: Decimal | int | float | str) -> Decimal:
        return Decimal(str(amount)).quantize(AMOUNT_QUANTUM)

    def _compute_amounts(
        self,
        *,
        amount: Decimal,
        input_unit: str,
        rate_value: Decimal,
        rate_direction: RateDirection,
    ) -> tuple[Decimal, Decimal]:
        input_unit = input_unit.lower()
        amount = Decimal(amount)
        if rate_direction == RateDirection.FIAT_PER_COIN:
            if input_unit == "fiat":
                amount_fiat = amount
                amount_coin = (amount / rate_value).quantize(AMOUNT_QUANTUM)
            else:
                amount_coin = amount
                amount_fiat = (amount * rate_value).quantize(AMOUNT_QUANTUM)
        else:
            if input_unit == "fiat":
                amount_fiat = amount
                amount_coin = (amount * rate_value).quantize(AMOUNT_QUANTUM)
            else:
                amount_coin = amount
                amount_fiat = (amount / rate_value).quantize(AMOUNT_QUANTUM)
        return (
            amount_fiat.quantize(AMOUNT_QUANTUM),
            amount_coin.quantize(AMOUNT_QUANTUM),
        )

    def _enforce_deposit_limits(self, settings: TreasurySettings, amount_coin: Decimal) -> None:
        if settings.min_deposit and amount_coin < Decimal(settings.min_deposit):
            raise WalletRailConflictError("Deposit amount is below the minimum.")
        if settings.max_deposit and amount_coin > Decimal(settings.max_deposit):
            raise WalletRailConflictError("Deposit amount exceeds the maximum.")

    def _generate_reference(self, *, prefix: str, model: type[FancoinPurchaseOrder] | type[MarketTopup]) -> str:
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        for _ in range(10):
            token = uuid4().hex[:6].upper()
            candidate = f"{prefix}-{date_part}-{token}"
            exists = self.session.scalar(select(model).where(model.reference == candidate))
            if exists is None:
                return candidate
        return f"{prefix}-{date_part}-{uuid4().hex[:8].upper()}"

    def _flag_purchase_order_risk(self, order: FancoinPurchaseOrder) -> None:
        amount_signal = Decimal(order.amount_fiat or 0)
        risk_service = RiskOpsService(self.session)
        if amount_signal >= RISK_AMOUNT_THRESHOLD:
            risk_service.create_aml_case(
                actor_user_id=None,
                user_id=order.user_id,
                trigger_source="purchase_order",
                title="Large FanCoin purchase order",
                description="Purchase order exceeded large-value threshold.",
                severity=RiskSeverity.MEDIUM,
                amount_signal=amount_signal,
                country_code=None,
                metadata_json={"purchase_order_id": order.id},
            )
        recent_count = self._recent_order_count(FancoinPurchaseOrder, order.user_id)
        if recent_count >= RISK_FREQUENCY_THRESHOLD:
            self._create_system_event(
                event_key=f"purchase-order-frequency-{order.user_id}-{order.id}",
                severity=SystemEventSeverity.WARNING,
                title="High frequency FanCoin purchase orders",
                body="User has submitted multiple FanCoin purchase orders within 24 hours.",
                subject_type="purchase_order",
                subject_id=order.id,
                metadata={"recent_count": recent_count, "user_id": order.user_id},
            )

    def _flag_topup_risk(self, topup: MarketTopup) -> None:
        amount_signal = Decimal(topup.gross_amount or 0)
        risk_service = RiskOpsService(self.session)
        if amount_signal >= RISK_AMOUNT_THRESHOLD:
            risk_service.create_aml_case(
                actor_user_id=topup.requested_by_user_id,
                user_id=topup.user_id,
                trigger_source="market_topup",
                title="Large market topup",
                description="Market topup exceeded large-value threshold.",
                severity=RiskSeverity.MEDIUM,
                amount_signal=amount_signal,
                country_code=None,
                metadata_json={"market_topup_id": topup.id},
            )
        recent_count = self._recent_order_count(MarketTopup, topup.user_id)
        if recent_count >= RISK_FREQUENCY_THRESHOLD:
            self._create_system_event(
                event_key=f"market-topup-frequency-{topup.user_id}-{topup.id}",
                severity=SystemEventSeverity.WARNING,
                title="High frequency market topups",
                body="User has received multiple market topups within 24 hours.",
                subject_type="market_topup",
                subject_id=topup.id,
                metadata={"recent_count": recent_count, "user_id": topup.user_id},
            )

    def _recent_order_count(self, model, user_id: str) -> int:
        window_start = utcnow() - timedelta(hours=RISK_WINDOW_HOURS)
        count = self.session.scalar(
            select(func.count()).select_from(model).where(
                model.user_id == user_id,
                model.created_at >= window_start,
            )
        )
        return int(count or 0)

    def _create_system_event(
        self,
        *,
        event_key: str,
        severity: SystemEventSeverity,
        title: str,
        body: str,
        subject_type: str,
        subject_id: str,
        metadata: dict[str, Any],
    ) -> None:
        RiskOpsService(self.session).create_system_event(
            actor_user_id=None,
            event_key=event_key,
            event_type="finance_alert",
            severity=severity,
            title=title,
            body=body,
            subject_type=subject_type,
            subject_id=subject_id,
            metadata_json=metadata,
        )

