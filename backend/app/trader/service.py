from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import hmac
import secrets
import struct
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.trader import (
    TraderExperience,
    TraderMarket,
    TraderOrder,
    TraderOrderSide,
    TraderP2POffer,
    TraderProfile,
    TraderSecurity,
    TraderSecurityEvent,
    TraderWatchlist,
)
from app.models.user import PublicAccountType, User
from app.models.wallet import LedgerUnit
from app.wallets.service import WalletService


class TraderAccessError(ValueError):
    pass


class TraderMarketNotFoundError(LookupError):
    pass


@dataclass(slots=True)
class TraderService:
    session: Session
    wallet_service: WalletService | None = None

    def assert_trader(self, user: User) -> None:
        if user.account_type != PublicAccountType.COIN_TRADER:
            raise TraderAccessError("Coin trader account access is required.")

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
        existing = self.session.scalar(select(TraderProfile).where(TraderProfile.user_id == user.id))
        if existing is not None:
            return existing
        profile = TraderProfile(
            user_id=user.id,
            trading_alias=trading_alias.strip(),
            preferred_currency=preferred_currency.strip().upper(),
            trading_experience=TraderExperience(trading_experience),
            interests_json=[item.strip() for item in interests if item.strip()],
            wallet_label=wallet_label.strip() or "GTEX Trading Wallet",
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
        if existing is not None:
            was_enabled = existing.two_factor_enabled
            existing.totp_secret_hash = _hash_secret(totp_secret)
            existing.recovery_phrase_hash = recovery_phrase_hash
            existing.security_pin_hash = security_pin_hash
            existing.two_factor_enabled = True
            if not was_enabled:
                backup_codes = _generate_backup_codes()
                existing.backup_codes_json = [_hash_secret(code) for code in backup_codes]
                existing._plain_backup_codes = backup_codes  # type: ignore[attr-defined]
            elif hasattr(existing, "_plain_backup_codes"):
                delattr(existing, "_plain_backup_codes")
            event_type = "totp_updated" if was_enabled else "totp_enabled"
            self.session.add(
                TraderSecurityEvent(
                    user_id=user.id,
                    event_type=event_type,
                    metadata_json={"backup_code_count": len(existing.backup_codes_json or [])},
                )
            )
            self.session.flush()
            return existing
        backup_codes = _generate_backup_codes()
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

    def security_summary(self, user: User) -> dict[str, object]:
        self.assert_trader(user)
        security = self.session.scalar(select(TraderSecurity).where(TraderSecurity.user_id == user.id))
        events = list(
            self.session.scalars(
                select(TraderSecurityEvent)
                .where(TraderSecurityEvent.user_id == user.id)
                .order_by(TraderSecurityEvent.created_at.desc())
                .limit(10)
            ).all()
        )
        return {
            "two_factor_enabled": bool(security.two_factor_enabled) if security is not None else False,
            "backup_code_count": len(security.backup_codes_json or []) if security is not None else 0,
            "recent_events": events,
        }

    def verify_totp_setup(
        self,
        user: User,
        *,
        totp_secret: str,
        totp_code: str,
        recovery_phrase_hash: str,
        security_pin_hash: str,
    ) -> dict[str, object]:
        self.assert_trader(user)
        security = self.ensure_security(
            user,
            totp_secret=totp_secret,
            totp_code=totp_code,
            recovery_phrase_hash=recovery_phrase_hash,
            security_pin_hash=security_pin_hash,
        )
        events = list(
            self.session.scalars(
                select(TraderSecurityEvent)
                .where(TraderSecurityEvent.user_id == user.id)
                .order_by(TraderSecurityEvent.created_at.desc())
                .limit(10)
            ).all()
        )
        return {
            "two_factor_enabled": bool(security.two_factor_enabled),
            "backup_code_count": len(security.backup_codes_json or []),
            "backup_codes": list(getattr(security, "_plain_backup_codes", [])),
            "recent_events": events,
        }

    def totp_setup(self, user: User) -> dict[str, str]:
        self.assert_trader(user)
        secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
        return {"secret": secret, "account_label": user.email}

    def overview(self, user: User) -> dict[str, object]:
        self.assert_trader(user)
        profile = self.session.scalar(select(TraderProfile).where(TraderProfile.user_id == user.id))
        if profile is None:
            raise TraderAccessError("Trader profile has not been created.")
        markets = self.list_markets()
        wallet_service = self.wallet_service or WalletService()
        summary = wallet_service.get_wallet_summary(self.session, user, currency=LedgerUnit.COIN)
        gtex = next((item for item in markets if item.symbol == "GTEX"), markets[0])
        return {
            "profile": profile,
            "portfolio_value": Decimal(summary.available_balance) * Decimal(gtex.price),
            "gtex_coin_price": Decimal(gtex.price),
            "daily_pl": Decimal("0.0000"),
            "wallet_balance": Decimal(summary.available_balance),
            "market_cap": sum(Decimal(item.market_cap) for item in markets),
            "trading_volume": sum(Decimal(item.volume_24h) for item in markets),
            "trending": markets[:8],
            "top_gainers": sorted(markets, key=lambda item: item.daily_change_percent, reverse=True)[:8],
            "top_losers": sorted(markets, key=lambda item: item.daily_change_percent)[:8],
            "most_traded_fan_coins": [item for item in markets if item.asset_type == "fan_coin"][:8],
            "liquidity_activity": sorted(markets, key=lambda item: item.liquidity_score, reverse=True)[:8],
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

    def place_order(self, user: User, *, market_id: str, side: TraderOrderSide, quantity: Decimal, limit_price: Decimal | None) -> TraderOrder:
        self.assert_trader(user)
        self._require_market(market_id)
        order = TraderOrder(user_id=user.id, market_id=market_id, side=side, quantity=quantity, limit_price=limit_price)
        self.session.add(order)
        self.session.flush()
        return order

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
        self.assert_trader(user)
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

    def _require_market(self, market_id: str) -> TraderMarket:
        market = self.session.get(TraderMarket, market_id)
        if market is None:
            raise TraderMarketNotFoundError("Trader market not found.")
        return market


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def _generate_backup_codes() -> list[str]:
    return [secrets.token_urlsafe(9) for _ in range(8)]


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
