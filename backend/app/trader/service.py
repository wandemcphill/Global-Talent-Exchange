from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import secrets
import struct
import time

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.market_topup import MarketTopup, MarketTopupStatus
from app.models.risk_ops import AuditLog
from app.models.trader import (
    TraderExperience,
    TraderMarket,
    TraderOrder,
    TraderOrderSide,
    TraderOrderStatus,
    TraderP2POffer,
    TraderP2PStatus,
    TraderProfile,
    TraderSecurity,
    TraderSecurityEvent,
    TraderTrade,
    TraderWatchlist,
)
from app.trader.matching import TraderMatchingEngine
from app.models.user import PublicAccountType, User
from app.models.wallet import LedgerUnit
from app.risk_ops_engine.service import RiskActionBlockedError, RiskOpsService
from app.treasury.service import TreasuryConflictError, TreasuryService
from app.wallets.rail_service import MarketTopupQuote, WalletRailService
from app.wallets.service import WalletService


class TraderAccessError(ValueError):
    pass


class TraderFinancialBalanceUnavailableError(ValueError):
    pass


class TraderMarketNotFoundError(LookupError):
    pass


class TraderResourceNotFoundError(LookupError):
    pass


@dataclass(slots=True)
class TraderService:
    session: Session
    wallet_service: WalletService | None = None

    def assert_trader(self, user: User) -> None:
        if user.account_type != PublicAccountType.COIN_TRADER:
            raise TraderAccessError("Coin trader account access is required.")

    def assert_trader_approved_for_trading(self, user: User) -> TraderProfile:
        self.assert_trader(user)
        profile = self.session.scalar(select(TraderProfile).where(TraderProfile.user_id == user.id))
        if profile is None:
            raise TraderAccessError("Trader profile has not been created.")
        if not self._is_kyc_verified(user):
            profile.status = "pending_kyc"
            self.session.flush()
            raise TraderAccessError("KYC verification is required before coin trading.")
        try:
            RiskOpsService(self.session).assert_trading_allowed(user.id)
        except RiskActionBlockedError as exc:
            profile.status = "pending_review"
            self.session.flush()
            raise TraderAccessError(str(exc)) from exc
        if profile.status not in {"active", "approved"}:
            profile.status = "active"
            self.session.flush()
        return profile

    def ensure_profile(
        self,
        user: User,
        *,
        trading_alias: str,
        preferred_currency: str,
        trading_experience: str,
        interests: list[str],
        wallet_label: str,
    ) -> TraderProfile:
        self.assert_trader(user)
        existing = self.session.scalar(select(TraderProfile).where(TraderProfile.user_id == user.id))
        status = self._profile_status_for_user(user)
        if existing is not None:
            existing.status = status
            self.session.flush()
            return existing
        profile = TraderProfile(
            user_id=user.id,
            trading_alias=trading_alias.strip(),
            preferred_currency=preferred_currency.strip().upper(),
            trading_experience=TraderExperience(trading_experience),
            interests_json=[item.strip() for item in interests if item.strip()],
            wallet_label=wallet_label.strip() or "GTEX Trading Wallet",
            status=status,
        )
        self.session.add(profile)
        self.session.flush()
        return profile

    def ensure_security(
        self,
        user: User,
        *,
        totp_secret: str,
        totp_code: str,
        recovery_phrase_hash: str,
        security_pin_hash: str,
    ) -> TraderSecurity:
        if not verify_totp(totp_secret, totp_code):
            raise TraderAccessError("Invalid authenticator code.")
        existing = self.session.scalar(select(TraderSecurity).where(TraderSecurity.user_id == user.id))
        backup_codes = _generate_backup_codes()
        if existing is not None:
            existing.totp_secret_hash = _hash_secret(totp_secret)
            existing.backup_codes_json = [_hash_secret(code) for code in backup_codes]
            existing.recovery_phrase_hash = recovery_phrase_hash
            existing.security_pin_hash = security_pin_hash
            existing.two_factor_enabled = True
            self.session.flush()
            return existing
        security = TraderSecurity(
            user_id=user.id,
            totp_secret_hash=_hash_secret(totp_secret),
            backup_codes_json=[_hash_secret(code) for code in backup_codes],
            recovery_phrase_hash=recovery_phrase_hash,
            security_pin_hash=security_pin_hash,
            two_factor_enabled=True,
        )
        self.session.add(security)
        self.session.add(
            TraderSecurityEvent(
                user_id=user.id,
                event_type="totp_enabled",
                metadata_json={"backup_code_count": len(backup_codes)},
            )
        )
        self.session.flush()
        security._plain_backup_codes = backup_codes  # type: ignore[attr-defined]
        return security

    def totp_setup(self, user: User) -> dict[str, str]:
        self.assert_trader(user)
        secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
        return {"secret": secret, "account_label": user.email}

    def overview(self, user: User) -> dict[str, object]:
        self.assert_trader(user)
        profile = self.session.scalar(select(TraderProfile).where(TraderProfile.user_id == user.id))
        if profile is None:
            raise TraderAccessError("Trader profile has not been created.")
        profile.status = self._profile_status_for_user(user)
        profile = self.sync_trader_metrics(user)
        markets = self.list_markets()
        wallet_service = self.wallet_service or WalletService()
        summary = wallet_service.get_wallet_summary(self.session, user, currency=LedgerUnit.COIN)
        available_balance = _required_balance_amount(summary.available_balance, "available balance")
        gtex = next((item for item in markets if item.symbol == "GTEX"), markets[0])
        return {
            "profile": profile,
            "portfolio_value": available_balance * Decimal(gtex.price),
            "gtex_coin_price": Decimal(gtex.price),
            "daily_pl": Decimal("0.0000"),
            "wallet_balance": available_balance,
            "market_cap": sum(Decimal(item.market_cap) for item in markets),
            "trading_volume": sum(Decimal(item.volume_24h) for item in markets),
            "trending": markets[:8],
            "top_gainers": sorted(markets, key=lambda item: item.daily_change_percent, reverse=True)[:8],
            "top_losers": sorted(markets, key=lambda item: item.daily_change_percent)[:8],
            "most_traded_fan_coins": [item for item in markets if item.asset_type == "fan_coin"][:8],
            "liquidity_activity": sorted(markets, key=lambda item: item.liquidity_score, reverse=True)[:8],
        }

    def profile(self, user: User) -> TraderProfile:
        self.assert_trader(user)
        profile = self.session.scalar(select(TraderProfile).where(TraderProfile.user_id == user.id))
        if profile is None:
            raise TraderAccessError("Trader profile has not been created.")
        profile.status = self._profile_status_for_user(user)
        self.session.flush()
        return profile

    def balance(self, user: User) -> dict[str, object]:
        self.assert_trader(user)
        profile = self.session.scalar(select(TraderProfile).where(TraderProfile.user_id == user.id))
        if profile is None:
            raise TraderAccessError("Trader profile has not been created.")
        wallet_service = self.wallet_service or WalletService()
        summary = wallet_service.get_wallet_summary(self.session, user, currency=LedgerUnit.COIN)
        available_balance = _required_balance_amount(summary.available_balance, "available balance")
        reserved_balance = _required_balance_amount(summary.reserved_balance, "reserved balance")
        total_balance = _required_balance_amount(summary.total_balance, "total balance")
        return {
            "available": available_balance,
            "reserved": reserved_balance,
            "total": total_balance,
            "currency": LedgerUnit.COIN,
            "last_synced_at": profile.metrics_updated_at,
        }

    def dashboard(self, user: User) -> dict[str, object]:
        profile = self.sync_trader_metrics(user)
        active_orders = self.session.scalar(
            select(func.count())
            .select_from(TraderOrder)
            .where(
                TraderOrder.user_id == user.id,
                TraderOrder.status == TraderOrderStatus.OPEN,
            )
        )
        pending_settlements = self.session.scalar(
            select(func.count())
            .select_from(MarketTopup)
            .where(
                MarketTopup.user_id == user.id,
                MarketTopup.status.in_(
                    [
                        MarketTopupStatus.REQUESTED,
                        MarketTopupStatus.REVIEWING,
                        MarketTopupStatus.APPROVED,
                        MarketTopupStatus.PROCESSING,
                    ]
                ),
            )
        )
        open_disputes = self.session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.actor_user_id == user.id,
                AuditLog.action_key == "trader.dispute.filed",
                AuditLog.outcome.in_(["pending_admin_review", "blocked"]),
            )
        )
        return {
            "balance": self.balance(user),
            "active_orders": int(active_orders or 0),
            "pending_settlements": int(pending_settlements or 0),
            "open_disputes": int(open_disputes or 0),
            "recent_activity": self._recent_activity(user),
            "profile_id": profile.id,
        }

    def list_markets(self) -> list[TraderMarket]:
        markets = list(self.session.scalars(select(TraderMarket).order_by(TraderMarket.symbol.asc())).all())
        if markets:
            return markets
        seed = (
            ("GTEX", "GTEX Coin", "gtex_coin", "1.0000", "1.4500", "250000000.0000", "18500000.0000", 92),
            ("LAGFC", "Lagos United Fan Coin", "fan_coin", "4.1200", "6.2000", "31000000.0000", "2300000.0000", 81),
            ("ACCRA", "Accra Royals Fan Coin", "fan_coin", "2.8400", "-1.3000", "18400000.0000", "1400000.0000", 67),
            ("NAIROBI", "Nairobi Stars Fan Coin", "fan_coin", "3.5100", "3.9000", "22700000.0000", "1800000.0000", 74),
        )
        for symbol, name, asset_type, price, change, cap, volume, liquidity in seed:
            self.session.add(
                TraderMarket(
                    symbol=symbol,
                    display_name=name,
                    asset_type=asset_type,
                    price=Decimal(price),
                    daily_change_percent=Decimal(change),
                    market_cap=Decimal(cap),
                    volume_24h=Decimal(volume),
                    liquidity_score=liquidity,
                )
            )
        self.session.flush()
        return list(self.session.scalars(select(TraderMarket).order_by(TraderMarket.symbol.asc())).all())

    def order_book(self, market_id: str) -> dict[str, object]:
        market = self._require_market(market_id)
        rows = list(
            self.session.scalars(
                select(TraderOrder).where(
                    TraderOrder.market_id == market_id,
                    TraderOrder.status == TraderOrderStatus.OPEN,
                )
            ).all()
        )
        bid_levels = self._aggregate_book_levels(
            [row for row in rows if row.side == TraderOrderSide.BUY],
            fallback_price=Decimal(market.price),
            reverse=True,
        )
        ask_levels = self._aggregate_book_levels(
            [row for row in rows if row.side == TraderOrderSide.SELL],
            fallback_price=Decimal(market.price),
            reverse=False,
        )
        return {
            "market_id": market_id,
            "bids": bid_levels,
            "asks": ask_levels,
            "synced_at": utcnow(),
            "status": "live" if bid_levels or ask_levels else "empty",
        }

    def list_orders(self, user: User, *, status_filter: str | None = None) -> list[TraderOrder]:
        self.assert_trader(user)
        stmt = select(TraderOrder).where(TraderOrder.user_id == user.id)
        if status_filter:
            try:
                status_value = TraderOrderStatus(status_filter)
            except ValueError as exc:
                raise TraderAccessError("Trader order status is not supported.") from exc
            stmt = stmt.where(TraderOrder.status == status_value)
        return list(self.session.scalars(stmt.order_by(TraderOrder.created_at.desc())).all())

    def get_order(self, user: User, *, order_id: str) -> TraderOrder:
        self.assert_trader(user)
        order = self.session.get(TraderOrder, order_id)
        if order is None or order.user_id != user.id:
            raise TraderResourceNotFoundError("Trader order not found.")
        return order

    def cancel_order(self, user: User, *, order_id: str) -> TraderOrder:
        order = self.get_order(user, order_id=order_id)
        if order.status not in {TraderOrderStatus.OPEN, TraderOrderStatus.PARTIALLY_FILLED}:
            raise TraderAccessError("Only open or partially filled trader orders can be cancelled.")
        market = self._require_market(order.market_id)
        self._matching_engine().release_remaining_reservation(user, order, market)
        order.status = TraderOrderStatus.CANCELLED
        self.session.flush()
        order.audit_ref = self._record_audit(
            user,
            action_key="trader.order.cancelled",
            resource_type="trader_order",
            resource_id=order.id,
            detail="Trader order cancelled.",
            metadata_json={"market_id": order.market_id, "side": order.side.value},
        )
        return order

    def quote_order(
        self,
        user: User,
        *,
        market_id: str,
        side: TraderOrderSide,
        amount: Decimal,
        currency: str,
        lock_seconds: int = 30,
    ) -> dict[str, object]:
        self.assert_trader_approved_for_trading(user)
        market = self._require_market(market_id)
        locked_until = utcnow() + timedelta(seconds=lock_seconds)
        audit_ref = self._record_audit(
            user,
            action_key="trader.quote.requested",
            resource_type="trader_quote",
            resource_id=market_id,
            detail="Trader quote requested.",
            metadata_json={
                "market_id": market_id,
                "side": side.value,
                "amount": str(amount),
                "currency": currency,
                "locked_until": locked_until.isoformat(),
                "lock_seconds_remaining": lock_seconds,
            },
        )
        return {
            "id": audit_ref,
            "price": Decimal(market.price),
            "amount": amount,
            "currency": currency,
            "valid_until": locked_until,
            "locked_until": locked_until,
            "lock_seconds_remaining": lock_seconds,
            "audit_ref": audit_ref,
        }

    def place_order(
        self, user: User, *, market_id: str, side: TraderOrderSide, quantity: Decimal, limit_price: Decimal | None
    ) -> TraderOrder:
        self.assert_trader_approved_for_trading(user)
        market = self._require_market(market_id)
        if side is TraderOrderSide.CONVERT:
            raise TraderAccessError("Convert orders are not supported on the matching market.")
        order = TraderOrder(user_id=user.id, market_id=market_id, side=side, quantity=quantity, limit_price=limit_price)
        self.session.add(order)
        self.session.flush()

        engine = self._matching_engine()
        engine.reserve_for_order(user, order, market)
        trades = engine.match(user, order, market)
        if order.status not in {TraderOrderStatus.FILLED} and limit_price is None:
            # Market orders never rest on the book; release any unmatched remainder.
            engine.release_remaining_reservation(user, order, market)
            order.status = (
                TraderOrderStatus.FILLED
                if Decimal(order.filled_quantity) > Decimal("0.0000")
                else TraderOrderStatus.CANCELLED
            )
        self.session.flush()
        self.sync_trader_metrics(user)
        order.audit_ref = self._record_audit(
            user,
            action_key="trader.order.placed",
            resource_type="trader_order",
            resource_id=order.id,
            detail="Trader order placed.",
            metadata_json={
                "market_id": market_id,
                "side": side.value,
                "quantity": str(quantity),
                "limit_price": str(limit_price) if limit_price is not None else None,
                "filled_quantity": str(order.filled_quantity),
                "trade_count": len(trades),
            },
        )
        return order

    def _matching_engine(self) -> "TraderMatchingEngine":
        return TraderMatchingEngine(self.session, self.wallet_service or WalletService())

    def list_trades(self, user: User, *, limit: int = 50) -> list[TraderTrade]:
        self.assert_trader(user)
        stmt = (
            select(TraderTrade)
            .where(or_(TraderTrade.buyer_user_id == user.id, TraderTrade.seller_user_id == user.id))
            .order_by(TraderTrade.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
        return list(self.session.scalars(stmt).all())

    def list_disputes(self, user: User) -> list[dict[str, object]]:
        self.assert_trader(user)
        events = list(
            self.session.scalars(
                select(AuditLog)
                .where(AuditLog.actor_user_id == user.id, AuditLog.action_key == "trader.dispute.filed")
                .order_by(AuditLog.created_at.desc())
            ).all()
        )
        return [self._dispute_from_audit(event) for event in events]

    def get_dispute(self, user: User, *, dispute_id: str) -> dict[str, object]:
        self.assert_trader(user)
        event = self.session.get(AuditLog, dispute_id)
        if event is None or event.actor_user_id != user.id or event.action_key != "trader.dispute.filed":
            raise TraderResourceNotFoundError("Trader dispute not found.")
        return self._dispute_from_audit(event)

    def file_dispute(self, user: User, *, order_id: str, reason: str) -> dict[str, object]:
        order = self.get_order(user, order_id=order_id)
        audit = RiskOpsService(self.session).log_audit(
            actor_user_id=user.id,
            action_key="trader.dispute.filed",
            resource_type="trader_order",
            resource_id=order.id,
            detail="Trader dispute filed for admin review.",
            metadata_json={"order_id": order.id, "reason": reason},
            outcome="pending_admin_review",
        )
        return self._dispute_from_audit(audit)

    def list_settlements(self, user: User) -> list[dict[str, object]]:
        self.assert_trader(user)
        topups = list(
            self.session.scalars(
                select(MarketTopup).where(MarketTopup.user_id == user.id).order_by(MarketTopup.created_at.desc())
            ).all()
        )
        purchases = list(
            self.session.scalars(
                select(FancoinPurchaseOrder)
                .where(FancoinPurchaseOrder.user_id == user.id)
                .order_by(FancoinPurchaseOrder.created_at.desc())
            ).all()
        )
        settlements = [self._settlement_from_topup(row) for row in topups]
        settlements.extend(self._settlement_from_purchase(row) for row in purchases)
        return sorted(settlements, key=lambda item: item.get("initiated_at") or datetime.min, reverse=True)

    def get_settlement(self, user: User, *, settlement_id: str) -> dict[str, object]:
        for item in self.list_settlements(user):
            if item["id"] == settlement_id:
                return item
        raise TraderResourceNotFoundError("Trader settlement not found.")

    def initiate_deposit(
        self,
        user: User,
        *,
        amount: Decimal,
        currency: str,
        method: str,
        proof_attachment_id: str | None = None,
    ) -> dict[str, object]:
        if method not in {"korapay", "manual"}:
            raise TraderAccessError("Trader deposits support KoraPay and manual bank transfer only.")
        profile = self.assert_trader_approved_for_trading(user)
        topup = WalletRailService(self.session).create_market_topup(
            user=user,
            amount=amount,
            fee_bps=0,
            unit=LedgerUnit.COIN,
            source_scope="liquidity",
            notes=f"Trader {method} deposit request.",
            requested_by=user,
        )
        topup.metadata_json = {
            **(topup.metadata_json or {}),
            "trader_profile_id": profile.id,
            "payment_method": method,
            "proof_attachment_id": proof_attachment_id,
            "contract": "trader.deposit",
        }
        self.session.flush()
        audit_ref = self._record_audit(
            user,
            action_key="trader.deposit.requested",
            resource_type="market_topup",
            resource_id=topup.id,
            detail="Trader deposit requested.",
            metadata_json={"amount": str(amount), "currency": currency, "method": method},
        )
        return {
            "id": topup.id,
            "status": topup.status.value,
            "checkout_url": None,
            "audit_ref": audit_ref,
        }

    def request_withdrawal(
        self,
        user: User,
        *,
        amount: Decimal,
        currency: str,
        method: str,
        destination_ref: str,
    ) -> dict[str, object]:
        self.assert_trader(user)
        if method != "manual":
            audit_ref = self._record_audit(
                user,
                action_key="trader.withdrawal.blocked",
                resource_type="trader_withdrawal",
                resource_id=None,
                detail="Trader withdrawal blocked by unsupported payout rail.",
                metadata_json={"amount": str(amount), "currency": currency, "method": method},
            )
            return {"id": audit_ref, "status": "blocked", "audit_ref": audit_ref}
        self.assert_trader_approved_for_trading(user)
        try:
            withdrawal = TreasuryService().create_withdrawal_request(
                self.session,
                user=user,
                amount_coin=amount,
                bank_account_id=destination_ref,
                source_scope="trade",
                notes="Trader manual bank transfer withdrawal.",
            )
        except TreasuryConflictError as exc:
            audit_ref = self._record_audit(
                user,
                action_key="trader.withdrawal.blocked",
                resource_type="trader_withdrawal",
                resource_id=None,
                detail=str(exc),
                metadata_json={"amount": str(amount), "currency": currency, "method": method},
            )
            return {"id": audit_ref, "status": "blocked", "audit_ref": audit_ref}
        audit_ref = self._record_audit(
            user,
            action_key="trader.withdrawal.requested",
            resource_type="treasury_withdrawal",
            resource_id=withdrawal.id,
            detail="Trader withdrawal requested.",
            metadata_json={"amount": str(amount), "currency": currency, "method": method},
        )
        return {"id": withdrawal.id, "status": withdrawal.status.value, "audit_ref": audit_ref}

    def create_p2p_offer(
        self,
        user: User,
        *,
        market_id: str,
        side: TraderOrderSide,
        quantity: Decimal,
        unit_price: Decimal,
        preferred_currency: str,
    ) -> TraderP2POffer:
        self.assert_trader_approved_for_trading(user)
        self._require_market(market_id)
        offer = TraderP2POffer(
            user_id=user.id,
            market_id=market_id,
            side=side,
            quantity=quantity,
            unit_price=unit_price,
            preferred_currency=preferred_currency.strip().upper(),
        )
        self.session.add(offer)
        self.session.flush()
        self.sync_trader_metrics(user)
        offer.audit_ref = self._record_audit(
            user,
            action_key="trader.p2p_offer.created",
            resource_type="trader_p2p_offer",
            resource_id=offer.id,
            detail="Trader P2P offer created.",
            metadata_json={
                "market_id": market_id,
                "side": side.value,
                "quantity": str(quantity),
                "unit_price": str(unit_price),
                "preferred_currency": offer.preferred_currency,
            },
        )
        return offer

    def add_watchlist(self, user: User, *, market_id: str) -> TraderWatchlist:
        self.assert_trader(user)
        self._require_market(market_id)
        existing = self.session.scalar(
            select(TraderWatchlist).where(TraderWatchlist.user_id == user.id, TraderWatchlist.market_id == market_id)
        )
        if existing is not None:
            return existing
        item = TraderWatchlist(user_id=user.id, market_id=market_id)
        self.session.add(item)
        self.session.flush()
        return item

    def quote_wholesale_procurement(
        self,
        user: User,
        *,
        amount: Decimal,
        fee_bps: int = 0,
        unit: LedgerUnit = LedgerUnit.COIN,
    ) -> MarketTopupQuote:
        self.assert_trader_approved_for_trading(user)
        return WalletRailService(self.session).quote_market_topup(amount=amount, fee_bps=fee_bps, unit=unit)

    def request_wholesale_procurement(
        self,
        user: User,
        *,
        amount: Decimal,
        fee_bps: int = 0,
        unit: LedgerUnit = LedgerUnit.COIN,
        notes: str | None = None,
    ) -> MarketTopup:
        profile = self.assert_trader_approved_for_trading(user)
        topup = WalletRailService(self.session).create_market_topup(
            user=user,
            amount=amount,
            fee_bps=fee_bps,
            unit=unit,
            source_scope="liquidity",
            notes=notes,
            requested_by=user,
        )
        topup.metadata_json = {
            **(topup.metadata_json or {}),
            "self_service": True,
            "trader_profile_id": profile.id,
            "procurement_channel": "trader_wholesale",
        }
        self.session.flush()
        self.sync_trader_metrics(user)
        topup.audit_ref = self._record_audit(
            user,
            action_key="trader.procurement.requested",
            resource_type="market_topup",
            resource_id=topup.id,
            detail="Trader wholesale procurement requested.",
            metadata_json={
                "amount": str(amount),
                "fee_bps": fee_bps,
                "unit": unit.value,
                "source_scope": topup.source_scope,
            },
        )
        return topup

    def sync_trader_metrics(self, user: User) -> TraderProfile:
        profile = self.session.scalar(select(TraderProfile).where(TraderProfile.user_id == user.id))
        if profile is None:
            raise TraderAccessError("Trader profile has not been created.")
        wallet_service = self.wallet_service or WalletService()
        summary = wallet_service.get_wallet_summary(self.session, user, currency=LedgerUnit.COIN)
        available_balance = _required_balance_amount(summary.available_balance, "available balance")
        reserved_balance = _required_balance_amount(summary.reserved_balance, "reserved balance")
        total_balance = _required_balance_amount(summary.total_balance, "total balance")
        open_offer_count = self.session.scalar(
            select(func.count())
            .select_from(TraderP2POffer)
            .where(
                TraderP2POffer.user_id == user.id,
                TraderP2POffer.status == TraderP2PStatus.OPEN,
            )
        )
        open_offer_quantity = self.session.scalar(
            select(func.coalesce(func.sum(TraderP2POffer.quantity), Decimal("0.0000"))).where(
                TraderP2POffer.user_id == user.id,
                TraderP2POffer.status == TraderP2PStatus.OPEN,
            )
        ) or Decimal("0.0000")
        pending_procurements = self.session.scalar(
            select(func.count())
            .select_from(MarketTopup)
            .where(
                MarketTopup.user_id == user.id,
                MarketTopup.status.in_(
                    [
                        MarketTopupStatus.REQUESTED,
                        MarketTopupStatus.REVIEWING,
                        MarketTopupStatus.APPROVED,
                        MarketTopupStatus.PROCESSING,
                    ]
                ),
            )
        )
        completion_rate, average_release_seconds, rating_score = self._compute_trader_performance(user)
        profile.liquidity_snapshot_json = {
            "available_coin": str(available_balance),
            "reserved_coin": str(reserved_balance),
            "total_coin": str(total_balance),
            "open_p2p_offers": int(open_offer_count or 0),
            "open_p2p_quantity": str(Decimal(open_offer_quantity)),
            "pending_procurements": int(pending_procurements or 0),
        }
        profile.completion_rate = completion_rate
        profile.average_release_seconds = average_release_seconds
        profile.rating_score = rating_score
        profile.metrics_updated_at = utcnow()
        self.session.flush()
        return profile

    def _require_market(self, market_id: str) -> TraderMarket:
        market = self.session.get(TraderMarket, market_id)
        if market is None:
            raise TraderMarketNotFoundError("Trader market not found.")
        return market

    def _aggregate_book_levels(
        self,
        orders: list[TraderOrder],
        *,
        fallback_price: Decimal,
        reverse: bool,
    ) -> list[dict[str, Decimal]]:
        levels: dict[Decimal, Decimal] = {}
        for order in orders:
            price = Decimal(order.limit_price or fallback_price)
            levels[price] = levels.get(price, Decimal("0.0000")) + Decimal(order.quantity)
        return [
            {"price": price, "quantity": quantity}
            for price, quantity in sorted(levels.items(), key=lambda item: item[0], reverse=reverse)
        ]

    def _recent_activity(self, user: User) -> list[dict[str, object]]:
        audits = list(
            self.session.scalars(
                select(AuditLog)
                .where(AuditLog.actor_user_id == user.id, AuditLog.action_key.like("trader.%"))
                .order_by(AuditLog.created_at.desc())
                .limit(8)
            ).all()
        )
        return [
            {
                "id": audit.id,
                "label": audit.detail,
                "status": audit.outcome,
                "audit_ref": audit.id,
                "created_at": audit.created_at,
            }
            for audit in audits
        ]

    def _dispute_from_audit(self, event: AuditLog) -> dict[str, object]:
        metadata = dict(event.metadata_json or {})
        return {
            "id": event.id,
            "order_id": str(metadata.get("order_id") or event.resource_id or ""),
            "reason": str(metadata.get("reason") or event.detail),
            "status": str(event.outcome or "pending_admin_review"),
            "filed_at": event.created_at,
            "resolved_at": None,
            "resolution": None,
            "audit_ref": event.id,
            "audit_trail": [
                {
                    "id": event.id,
                    "event": event.detail,
                    "actor_id": event.actor_user_id,
                    "audit_ref": event.id,
                    "created_at": event.created_at,
                }
            ],
        }

    def _settlement_from_topup(self, row: MarketTopup) -> dict[str, object]:
        return {
            "id": row.id,
            "order_id": row.id,
            "amount": Decimal(row.net_amount),
            "currency": row.unit.value,
            "status": row.status.value,
            "method": _canonical_payment_method((row.metadata_json or {}).get("payment_method")),
            "initiated_at": row.created_at,
            "confirmed_at": row.settled_at,
            "eta": None if row.settled_at else "Pending treasury settlement.",
            "receipt_ref": row.reference,
            "proof_url": None,
            "audit_ref": self._latest_audit_ref("market_topup", row.id),
        }

    def _settlement_from_purchase(self, row: FancoinPurchaseOrder) -> dict[str, object]:
        return {
            "id": row.id,
            "order_id": row.id,
            "amount": Decimal(row.net_amount),
            "currency": row.unit.value,
            "status": row.status.value,
            "method": _canonical_payment_method(row.provider_key),
            "initiated_at": row.created_at,
            "confirmed_at": row.settled_at,
            "eta": None if row.settled_at else "Pending payment provider settlement.",
            "receipt_ref": row.reference,
            "proof_url": None,
            "audit_ref": self._latest_audit_ref("fancoin_purchase_order", row.id),
        }

    def _latest_audit_ref(self, resource_type: str, resource_id: str) -> str | None:
        event = self.session.scalar(
            select(AuditLog)
            .where(AuditLog.resource_type == resource_type, AuditLog.resource_id == resource_id)
            .order_by(AuditLog.created_at.desc())
        )
        return None if event is None else event.id

    def _profile_status_for_user(self, user: User) -> str:
        if not self._is_kyc_verified(user):
            return "pending_kyc"
        try:
            RiskOpsService(self.session).assert_trading_allowed(user.id)
        except RiskActionBlockedError:
            return "pending_review"
        return "active"

    def _is_kyc_verified(self, user: User) -> bool:
        return getattr(user.kyc_status, "value", str(user.kyc_status)) == "verified"

    def _compute_trader_performance(self, user: User) -> tuple[Decimal, Decimal, Decimal]:
        purchase_terminal = [
            PurchaseOrderStatus.SETTLED,
            PurchaseOrderStatus.REFUNDED,
            PurchaseOrderStatus.CHARGEBACK,
            PurchaseOrderStatus.REVERSED,
            PurchaseOrderStatus.DISPUTED,
            PurchaseOrderStatus.FAILED,
            PurchaseOrderStatus.REJECTED,
            PurchaseOrderStatus.CANCELLED,
            PurchaseOrderStatus.EXPIRED,
        ]
        topup_terminal = [
            MarketTopupStatus.SETTLED,
            MarketTopupStatus.FAILED,
            MarketTopupStatus.REJECTED,
            MarketTopupStatus.CANCELLED,
            MarketTopupStatus.REVERSED,
            MarketTopupStatus.DISPUTED,
        ]
        purchase_total = (
            self.session.scalar(
                select(func.count())
                .select_from(FancoinPurchaseOrder)
                .where(
                    FancoinPurchaseOrder.user_id == user.id,
                    FancoinPurchaseOrder.status.in_(purchase_terminal),
                )
            )
            or 0
        )
        topup_total = (
            self.session.scalar(
                select(func.count())
                .select_from(MarketTopup)
                .where(
                    MarketTopup.user_id == user.id,
                    MarketTopup.status.in_(topup_terminal),
                )
            )
            or 0
        )
        successful_total = (
            self.session.scalar(
                select(func.count())
                .select_from(FancoinPurchaseOrder)
                .where(
                    FancoinPurchaseOrder.user_id == user.id,
                    FancoinPurchaseOrder.status == PurchaseOrderStatus.SETTLED,
                )
            )
            or 0
        ) + (
            self.session.scalar(
                select(func.count())
                .select_from(MarketTopup)
                .where(
                    MarketTopup.user_id == user.id,
                    MarketTopup.status == MarketTopupStatus.SETTLED,
                )
            )
            or 0
        )
        total = int(purchase_total or 0) + int(topup_total or 0)
        completion_rate = (
            (Decimal(successful_total) / Decimal(total)).quantize(Decimal("0.0001")) if total else Decimal("0.0000")
        )
        release_seconds = self._settlement_release_seconds(user)
        average_release_seconds = (
            (sum(release_seconds, Decimal("0.0000")) / Decimal(len(release_seconds))).quantize(Decimal("0.0001"))
            if release_seconds
            else Decimal("0.0000")
        )
        disputed_total = (
            self.session.scalar(
                select(func.count())
                .select_from(FancoinPurchaseOrder)
                .where(
                    FancoinPurchaseOrder.user_id == user.id,
                    FancoinPurchaseOrder.status == PurchaseOrderStatus.DISPUTED,
                )
            )
            or 0
        ) + (
            self.session.scalar(
                select(func.count())
                .select_from(MarketTopup)
                .where(
                    MarketTopup.user_id == user.id,
                    MarketTopup.status == MarketTopupStatus.DISPUTED,
                )
            )
            or 0
        )
        if total == 0:
            return completion_rate, average_release_seconds, Decimal("0.0000")
        speed_bonus = Decimal("0.5000") if average_release_seconds <= Decimal("3600.0000") else Decimal("0.2500")
        dispute_penalty = (Decimal(disputed_total) / Decimal(total) * Decimal("2.0000")).quantize(Decimal("0.0001"))
        rating_score = Decimal("3.0000") + (completion_rate * Decimal("2.0000")) + speed_bonus - dispute_penalty
        rating_score = min(Decimal("5.0000"), max(Decimal("0.0000"), rating_score)).quantize(Decimal("0.0001"))
        return completion_rate, average_release_seconds, rating_score

    def _settlement_release_seconds(self, user: User) -> list[Decimal]:
        seconds: list[Decimal] = []
        purchase_rows = self.session.scalars(
            select(FancoinPurchaseOrder).where(
                FancoinPurchaseOrder.user_id == user.id,
                FancoinPurchaseOrder.status == PurchaseOrderStatus.SETTLED,
                FancoinPurchaseOrder.settled_at.is_not(None),
            )
        ).all()
        topup_rows = self.session.scalars(
            select(MarketTopup).where(
                MarketTopup.user_id == user.id,
                MarketTopup.status == MarketTopupStatus.SETTLED,
                MarketTopup.settled_at.is_not(None),
            )
        ).all()
        for row in [*purchase_rows, *topup_rows]:
            seconds.append(_seconds_between(row.created_at, row.settled_at))
        return seconds

    def _record_audit(
        self,
        user: User,
        *,
        action_key: str,
        resource_type: str,
        resource_id: str | None,
        detail: str,
        metadata_json: dict[str, object | None],
    ) -> str:
        audit = RiskOpsService(self.session).log_audit(
            actor_user_id=user.id,
            action_key=action_key,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            metadata_json=metadata_json,
        )
        return audit.id


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def _generate_backup_codes() -> list[str]:
    return [secrets.token_urlsafe(9) for _ in range(8)]


def _seconds_between(start: datetime, end: datetime | None) -> Decimal:
    if end is None:
        return Decimal("0.0000")
    normalized_start = start
    normalized_end = end
    if normalized_start.tzinfo is None:
        normalized_start = normalized_start.replace(tzinfo=timezone.utc)
    if normalized_end.tzinfo is None:
        normalized_end = normalized_end.replace(tzinfo=timezone.utc)
    return Decimal(str(max(0.0, (normalized_end - normalized_start).total_seconds()))).quantize(Decimal("0.0001"))


def _required_balance_amount(value: object, label: str) -> Decimal:
    if value is None:
        raise TraderFinancialBalanceUnavailableError("Balance data unavailable - sync in progress.")
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TraderFinancialBalanceUnavailableError(f"Trader {label} is unavailable - sync in progress.") from exc
    if not amount.is_finite():
        raise TraderFinancialBalanceUnavailableError(f"Trader {label} is unavailable - sync in progress.")
    return amount


def _canonical_payment_method(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower().replace("-", "_")
    if normalized in {"korapay", "kora_pay"}:
        return "korapay"
    if normalized in {"manual", "manual_bank_transfer", "bank_transfer"}:
        return "manual"
    return None


def verify_totp(secret: str, code: str, *, now: int | None = None, window: int = 1) -> bool:
    candidate = code.strip().replace(" ", "")
    if not candidate.isdigit():
        return False
    timestamp = int(now or time.time())
    try:
        for offset in range(-window, window + 1):
            if hmac.compare_digest(_totp(secret, timestamp // 30 + offset), candidate.zfill(6)):
                return True
    except (ValueError, binascii.Error):
        return False
    return False


def _totp(secret: str, counter: int) -> str:
    padding = "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode((secret + padding).upper(), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 1_000_000:06d}"
