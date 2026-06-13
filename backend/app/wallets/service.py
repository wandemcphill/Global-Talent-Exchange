from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
import json
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cache import HotPathCache
from app.core.cache import CacheBackend, NullCacheBackend
from app.core.event_backbone import (
    build_outbox_event,
    defer_event_publish_until_commit,
    defer_session_callback_until_commit,
)
from app.core.events import DomainEvent, EventPublisher, InMemoryEventPublisher
from app.models.base import generate_uuid, utcnow
from app.models.user import User
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerEntryReason,
    LedgerTransactionType,
    LedgerSourceTag,
    LedgerTransaction,
    LedgerTransactionStatus,
    LedgerUnit,
    PaymentEvent,
    PaymentProvider,
    PaymentStatus,
    PayoutRequest,
    PayoutStatus,
)

AMOUNT_QUANTUM = Decimal("0.0001")
COIN_TO_CREDIT_RATE = Decimal("100.0000")
WITHDRAWAL_FEE_BPS = 1000
WITHDRAWAL_MINIMUM_FEE = Decimal("0.0000")


def resolve_withdrawal_fee_bps() -> int:
    try:
        from app.core.config import get_settings

        return int(get_settings().withdrawal_fee_bps)
    except Exception:
        return WITHDRAWAL_FEE_BPS


def resolve_withdrawal_minimum_fee() -> Decimal:
    try:
        from app.core.config import get_settings

        return Decimal(get_settings().withdrawal_minimum_fee)
    except Exception:
        return WITHDRAWAL_MINIMUM_FEE
DEFAULT_BALANCE_CACHE_TTL_SECONDS = 300
DEFAULT_WALLET_SUMMARY_CACHE_TTL_SECONDS = 60
BALANCE_UNAVAILABLE_MESSAGE = "Balance data unavailable — sync in progress."
TRADE_BUY_SOURCE_TAGS = frozenset(
    {
        LedgerSourceTag.PLAYER_CARD_PURCHASE,
        LedgerSourceTag.PLAYER_SHARE_PURCHASE,
        LedgerSourceTag.CLUB_SALE_PURCHASE,
    }
)
TRADE_SELL_SOURCE_TAGS = frozenset(
    {
        LedgerSourceTag.PLAYER_CARD_SALE,
        LedgerSourceTag.PLAYER_SHARE_SALE,
        LedgerSourceTag.CLUB_SALE_SALE,
    }
)
WALLET_RESERVATION_METADATA_KEY = "wallet_reservation"
TRANSFER_BID_RESERVATION_KIND = "transfer_bid"


class LedgerError(ValueError):
    pass


class InsufficientBalanceError(LedgerError):
    pass


class WalletBalanceUnavailableError(LedgerError):
    pass


class UnbalancedTransactionError(LedgerError):
    pass


@dataclass(frozen=True, slots=True)
class LedgerPosting:
    account: LedgerAccount
    amount: Decimal
    source_tag: LedgerSourceTag | None = None
    transaction_type: LedgerTransactionType | None = None


class WalletLockReason(str):
    code: str
    label: str
    amount: Decimal
    currency: LedgerUnit
    source: str
    reference: str | None

    def __new__(
        cls,
        *,
        code: str,
        label: str,
        amount: Decimal,
        currency: LedgerUnit,
        source: str = "wallet",
        reference: str | None = None,
    ) -> WalletLockReason:
        normalized_amount = Decimal(amount).quantize(AMOUNT_QUANTUM)
        value = f"{label}: {normalized_amount} {currency.value}"
        instance = str.__new__(cls, value)
        instance.code = code
        instance.label = label
        instance.amount = normalized_amount
        instance.currency = currency
        instance.source = source
        instance.reference = reference
        return instance

    @property
    def message(self) -> str:
        return str(self)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "label": self.label,
            "amount": self.amount,
            "currency": self.currency.value,
            "source": self.source,
            "message": self.message,
        }
        if self.reference is not None:
            payload["reference"] = self.reference
        return payload


@dataclass(frozen=True, slots=True)
class WalletSummary:
    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal
    currency: LedgerUnit
    locked_balance: Decimal = Decimal("0.0000")
    pending_withdrawal_balance: Decimal = Decimal("0.0000")
    lock_reasons: tuple[WalletLockReason, ...] = ()


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    user_id: str
    currency: LedgerUnit
    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal
    holdings: list[dict[str, Decimal | str]]


@dataclass(frozen=True, slots=True)
class WalletLedgerPage:
    page: int
    page_size: int
    total: int
    items: list[LedgerEntry]


@dataclass(frozen=True, slots=True)
class WithdrawalRequestResult:
    payout_request: PayoutRequest
    gross_amount: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    total_debit: Decimal
    source_scope: str


@dataclass(frozen=True, slots=True)
class WalletConversionQuote:
    source_unit: LedgerUnit
    source_amount: Decimal
    target_unit: LedgerUnit
    target_amount: Decimal
    rate: Decimal


@dataclass(frozen=True, slots=True)
class WalletConversionResult:
    transaction_id: str
    reference: str
    source_unit: LedgerUnit
    source_amount: Decimal
    target_unit: LedgerUnit
    target_amount: Decimal


class WalletService:
    def __init__(
        self,
        event_publisher: EventPublisher | None = None,
        *,
        cache_backend: CacheBackend | None = None,
        balance_cache_ttl_seconds: int = DEFAULT_BALANCE_CACHE_TTL_SECONDS,
        wallet_summary_cache_ttl_seconds: int = DEFAULT_WALLET_SUMMARY_CACHE_TTL_SECONDS,
    ) -> None:
        self.event_publisher = event_publisher or InMemoryEventPublisher()
        self.cache_backend = cache_backend or NullCacheBackend()
        self.hot_cache = HotPathCache(self.cache_backend)
        self.balance_cache_ttl_seconds = max(1, int(balance_cache_ttl_seconds))
        self.wallet_summary_cache_ttl_seconds = max(1, int(wallet_summary_cache_ttl_seconds))
        self.trade_settlement_reason = LedgerEntryReason.TRADE_SETTLEMENT

    def _stage_domain_event(
        self,
        session: Session,
        *,
        event: DomainEvent,
        durable: bool = False,
    ) -> None:
        if durable:
            session.add(build_outbox_event(domain_event=event))
            session.flush()
        defer_event_publish_until_commit(session, publisher=self.event_publisher, event=event)

    def _cache_balance_after_commit(
        self,
        session: Session,
        *,
        account: LedgerAccount,
        balance: Decimal,
    ) -> None:
        defer_session_callback_until_commit(
            session,
            callback=lambda account_id=account.id, account_code=account.code, owner_user_id=account.owner_user_id, unit=account.unit.value, balance_value=str(
                balance
            ): self._write_cached_balance(
                account_id=account_id,
                account_code=account_code,
                owner_user_id=owner_user_id,
                unit=unit,
                balance=balance_value,
            ),
        )

    def _read_cached_balance(self, account: LedgerAccount) -> Decimal | None:
        cached_value = self.cache_backend.get(self._balance_cache_key(account.id))
        if cached_value is None:
            return None
        try:
            payload = json.loads(cached_value)
        except json.JSONDecodeError:
            return None
        balance = payload.get("balance")
        if balance is None:
            raise WalletBalanceUnavailableError(BALANCE_UNAVAILABLE_MESSAGE)
        return self._normalize_amount(balance)

    def _write_cached_balance(
        self,
        *,
        account_id: str,
        account_code: str,
        owner_user_id: str | None,
        unit: str,
        balance: str,
    ) -> None:
        self.cache_backend.set(
            self._balance_cache_key(account_id),
            json.dumps(
                {
                    "account_id": account_id,
                    "account_code": account_code,
                    "owner_user_id": owner_user_id,
                    "unit": unit,
                    "balance": balance,
                }
            ),
            self.balance_cache_ttl_seconds,
        )

    def _prime_balance_cache(
        self,
        session: Session,
        *,
        account: LedgerAccount,
        balance: Decimal,
    ) -> None:
        if self._session_has_pending_state(session):
            self._cache_balance_after_commit(session, account=account, balance=balance)
            return
        self._write_cached_balance(
            account_id=account.id,
            account_code=account.code,
            owner_user_id=account.owner_user_id,
            unit=account.unit.value,
            balance=str(balance),
        )

    def _read_cached_wallet_summary(self, *, user_id: str, currency: LedgerUnit) -> WalletSummary | None:
        payload = self.hot_cache.get_wallet_summary(user_id=user_id, currency=currency.value)
        if payload is None:
            return None
        for field_name in ("balance", "locked", "total"):
            if field_name not in payload or payload[field_name] is None:
                raise WalletBalanceUnavailableError(BALANCE_UNAVAILABLE_MESSAGE)
        pending_withdrawal_value = payload.get(
            "pending_withdrawal_balance", payload.get("pending_withdrawals", "0.0000")
        )
        if pending_withdrawal_value is None:
            raise WalletBalanceUnavailableError(BALANCE_UNAVAILABLE_MESSAGE)
        try:
            available_balance = self._normalize_amount(payload.get("balance"))
            reserved_balance = self._normalize_amount(payload.get("locked"))
            total_balance = self._normalize_amount(payload.get("total"))
            pending_withdrawal_balance = self._normalize_amount(pending_withdrawal_value)
        except (TypeError, ValueError):
            return None
        cached_lock_reasons = payload.get("lock_reasons")
        if reserved_balance > Decimal("0.0000") and cached_lock_reasons is None:
            return None
        lock_reasons = self._coerce_cached_lock_reasons(cached_lock_reasons, currency=currency)
        if reserved_balance > Decimal("0.0000") and lock_reasons is None:
            return None
        return WalletSummary(
            available_balance=available_balance,
            reserved_balance=reserved_balance,
            total_balance=total_balance,
            currency=currency,
            locked_balance=reserved_balance,
            pending_withdrawal_balance=pending_withdrawal_balance,
            lock_reasons=lock_reasons or (),
        )

    def _coerce_cached_lock_reasons(
        self, value: object, *, currency: LedgerUnit
    ) -> tuple[WalletLockReason, ...] | None:
        if value is None:
            return ()
        if not isinstance(value, list):
            return None
        reasons: list[WalletLockReason] = []
        for item in value:
            if not isinstance(item, dict):
                return None
            try:
                amount = self._normalize_amount(item.get("amount", "0.0000"))
            except (TypeError, ValueError):
                return None
            label = str(item.get("label") or item.get("message") or "").strip()
            code = str(item.get("code") or "").strip()
            if not label or not code:
                return None
            item_currency = str(item.get("currency") or currency.value)
            try:
                resolved_currency = LedgerUnit(item_currency)
            except ValueError:
                resolved_currency = currency
            reasons.append(
                WalletLockReason(
                    code=code,
                    label=label,
                    amount=amount,
                    currency=resolved_currency,
                    source=str(item.get("source") or "wallet").strip() or "wallet",
                    reference=str(item["reference"]).strip() if item.get("reference") is not None else None,
                )
            )
        return tuple(reasons)

    def _write_cached_wallet_summary(
        self,
        *,
        user_id: str,
        currency: LedgerUnit,
        available_balance: Decimal,
        reserved_balance: Decimal,
        pending_withdrawal_balance: Decimal | None = None,
        lock_reasons: tuple[WalletLockReason, ...] | list[WalletLockReason] | None = None,
    ) -> None:
        total_balance = self._normalize_amount(available_balance + reserved_balance)
        payload = {
            "user_id": user_id,
            "currency": currency.value,
            "balance": str(available_balance),
            "locked": str(reserved_balance),
            "total": str(total_balance),
        }
        if pending_withdrawal_balance is not None:
            payload["pending_withdrawal_balance"] = str(self._normalize_amount(pending_withdrawal_balance))
        if lock_reasons is not None:
            payload["lock_reasons"] = [item.to_dict() for item in lock_reasons]
        self.hot_cache.set_wallet_summary(
            user_id=user_id,
            currency=currency.value,
            payload=payload,
            ttl_seconds=self.wallet_summary_cache_ttl_seconds,
        )

    def _prime_wallet_summary_cache(
        self,
        session: Session,
        *,
        user_id: str,
        currency: LedgerUnit,
        available_balance: Decimal,
        reserved_balance: Decimal,
        pending_withdrawal_balance: Decimal | None = None,
        lock_reasons: tuple[WalletLockReason, ...] | list[WalletLockReason] | None = None,
        defer_until_commit: bool = False,
    ) -> None:
        if defer_until_commit or self._session_has_pending_state(session):
            defer_session_callback_until_commit(
                session,
                callback=lambda resolved_user_id=user_id, resolved_currency=currency, resolved_available=str(
                    available_balance
                ), resolved_reserved=str(reserved_balance), resolved_pending=(
                    str(pending_withdrawal_balance) if pending_withdrawal_balance is not None else None
                ), resolved_lock_reasons=(
                    tuple(lock_reasons) if lock_reasons is not None else None
                ): self._write_cached_wallet_summary(
                    user_id=resolved_user_id,
                    currency=resolved_currency,
                    available_balance=self._normalize_amount(resolved_available),
                    reserved_balance=self._normalize_amount(resolved_reserved),
                    pending_withdrawal_balance=(
                        self._normalize_amount(resolved_pending) if resolved_pending is not None else None
                    ),
                    lock_reasons=resolved_lock_reasons,
                ),
            )
            return
        self._write_cached_wallet_summary(
            user_id=user_id,
            currency=currency,
            available_balance=available_balance,
            reserved_balance=reserved_balance,
            pending_withdrawal_balance=pending_withdrawal_balance,
            lock_reasons=lock_reasons,
        )

    def _prime_impacted_wallet_summary_caches(
        self,
        session: Session,
        *,
        accounts: dict[str, LedgerAccount],
        defer_until_commit: bool = False,
    ) -> None:
        impacted_pairs = {
            (account.owner_user_id, account.unit)
            for account in accounts.values()
            if account.owner_user_id is not None and account.kind in {LedgerAccountKind.USER, LedgerAccountKind.ESCROW}
        }
        for owner_user_id, unit in impacted_pairs:
            available_account = session.scalar(
                select(LedgerAccount).where(
                    LedgerAccount.owner_user_id == owner_user_id,
                    LedgerAccount.unit == unit,
                    LedgerAccount.kind == LedgerAccountKind.USER,
                )
            )
            escrow_account = session.scalar(
                select(LedgerAccount).where(
                    LedgerAccount.owner_user_id == owner_user_id,
                    LedgerAccount.unit == unit,
                    LedgerAccount.kind == LedgerAccountKind.ESCROW,
                )
            )
            if defer_until_commit:
                available_balance = (
                    self._normalize_amount(self._get_or_build_balance_projection(session, available_account).balance)
                    if available_account is not None
                    else Decimal("0.0000")
                )
                reserved_balance = (
                    self._normalize_amount(self._get_or_build_balance_projection(session, escrow_account).balance)
                    if escrow_account is not None
                    else Decimal("0.0000")
                )
            else:
                available_balance = (
                    self.get_balance(session, available_account) if available_account is not None else Decimal("0.0000")
                )
                reserved_balance = (
                    self.get_balance(session, escrow_account) if escrow_account is not None else Decimal("0.0000")
                )
            self._prime_wallet_summary_cache(
                session,
                user_id=owner_user_id,
                currency=unit,
                available_balance=available_balance,
                reserved_balance=reserved_balance,
                defer_until_commit=defer_until_commit,
            )

    def ensure_default_accounts(self, session: Session, user: User) -> dict[LedgerUnit, LedgerAccount]:
        accounts: dict[LedgerUnit, LedgerAccount] = {}
        for unit, label in ((LedgerUnit.COIN, "GTEX Coin"), (LedgerUnit.CREDIT, "Fan Coin")):
            code = self._user_account_code(user.id, unit)
            account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
            if account is None:
                account = LedgerAccount(
                    owner_user_id=user.id,
                    code=code,
                    label=label,
                    unit=unit,
                    kind=LedgerAccountKind.USER,
                )
                session.add(account)
                session.flush()
            accounts[unit] = account
        return accounts

    def list_accounts_for_user(self, session: Session, user: User) -> list[LedgerAccount]:
        accounts = session.scalars(
            select(LedgerAccount)
            .where(
                LedgerAccount.owner_user_id == user.id,
                LedgerAccount.code.like(f"user:{user.id}:%"),
            )
            .order_by(LedgerAccount.unit.asc(), LedgerAccount.created_at.asc())
        ).all()
        if not accounts:
            self.ensure_default_accounts(session, user)
            accounts = session.scalars(
                select(LedgerAccount)
                .where(
                    LedgerAccount.owner_user_id == user.id,
                    LedgerAccount.code.like(f"user:{user.id}:%"),
                )
                .order_by(LedgerAccount.unit.asc(), LedgerAccount.created_at.asc())
            ).all()
        return accounts

    def get_user_account(self, session: Session, user: User, unit: LedgerUnit) -> LedgerAccount:
        code = self._user_account_code(user.id, unit)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = self.ensure_default_accounts(session, user)[unit]
        return account

    def get_user_escrow_account(self, session: Session, user: User, unit: LedgerUnit) -> LedgerAccount:
        code = self._user_escrow_account_code(user.id, unit)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                owner_user_id=user.id,
                code=code,
                label=f"{unit.value.capitalize()} Escrow",
                unit=unit,
                kind=LedgerAccountKind.ESCROW,
            )
            session.add(account)
            session.flush()
        return account

    def _ensure_system_account(
        self,
        session: Session,
        *,
        code: str,
        label: str,
        unit: LedgerUnit,
        allow_negative: bool,
    ) -> LedgerAccount:
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=label,
                unit=unit,
                kind=LedgerAccountKind.SYSTEM,
                allow_negative=allow_negative,
            )
            session.add(account)
            session.flush()
        return account

    def ensure_platform_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:clearing",
            label=f"Platform {unit.value.capitalize()} Clearing",
            unit=unit,
            allow_negative=True,
        )

    def ensure_deposit_clearing_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:deposit_clearing",
            label=f"Platform {unit.value.capitalize()} Deposit Clearing",
            unit=unit,
            allow_negative=True,
        )

    def ensure_treasury_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:treasury",
            label=f"Platform {unit.value.capitalize()} Treasury",
            unit=unit,
            allow_negative=False,
        )

    def ensure_named_system_account(
        self,
        session: Session,
        *,
        code: str,
        label: str,
        unit: LedgerUnit,
        allow_negative: bool = False,
    ) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=code,
            label=label,
            unit=unit,
            allow_negative=allow_negative,
        )

    def ensure_club_treasury_account(
        self, session: Session, club_id: str, unit: LedgerUnit = LedgerUnit.COIN
    ) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"club:{club_id}:{unit.value}:treasury",
            label=f"Club {club_id} {unit.value.capitalize()} Treasury",
            unit=unit,
            allow_negative=False,
        )

    def ensure_rewards_pool_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:rewards_pool",
            label=f"Platform {unit.value.capitalize()} Rewards Pool",
            unit=unit,
            allow_negative=False,
        )

    def ensure_creator_clip_revenue_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:creator_clip_revenue",
            label=f"Platform {unit.value.capitalize()} Creator Clip Revenue",
            unit=unit,
            allow_negative=True,
        )

    def ensure_liquidity_pool_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:liquidity_pool",
            label=f"Platform {unit.value.capitalize()} Liquidity Pool",
            unit=unit,
            allow_negative=True,
        )

    def ensure_operations_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:operations",
            label=f"Platform {unit.value.capitalize()} Operations",
            unit=unit,
            allow_negative=True,
        )

    def ensure_match_pool_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:match_pool",
            label=f"Platform {unit.value.capitalize()} Match Pool",
            unit=unit,
            allow_negative=False,
        )

    def ensure_match_fee_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:match_fee_revenue",
            label=f"Platform {unit.value.capitalize()} Match Fee Revenue",
            unit=unit,
            allow_negative=False,
        )

    def ensure_betting_pool_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:betting_pool",
            label=f"Platform {unit.value.capitalize()} Betting Pool",
            unit=unit,
            allow_negative=True,
        )

    def ensure_trade_fee_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:trade_fee_revenue",
            label=f"Platform {unit.value.capitalize()} Trade Fee Revenue",
            unit=unit,
            allow_negative=False,
        )

    def ensure_market_liquidity_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self.ensure_liquidity_pool_account(session, unit)

    def ensure_withdrawal_clearing_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:withdrawal_clearing",
            label=f"Platform {unit.value.capitalize()} Withdrawal Clearing",
            unit=unit,
            allow_negative=False,
        )

    def ensure_lottery_pool_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:lottery_pool",
            label=f"Platform {unit.value.capitalize()} Lottery Pool",
            unit=unit,
            allow_negative=False,
        )

    def ensure_platform_burn_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=f"platform:{unit.value}:burn",
            label=f"Platform {unit.value.capitalize()} Burn",
            unit=unit,
            allow_negative=False,
        )

    def ensure_promo_pool_account(self, session: Session, unit: LedgerUnit) -> LedgerAccount:
        code = f"platform:{unit.value}:promo_pool"
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"Platform {unit.value.capitalize()} Promo Pool",
                unit=unit,
                kind=LedgerAccountKind.SYSTEM,
                allow_negative=False,
            )
            session.add(account)
            session.flush()
        return account

    def get_position_account(self, session: Session, user: User, player_id: str) -> LedgerAccount:
        code = self._position_account_code(user.id, player_id)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"Player {player_id} Position",
                unit=LedgerUnit.COIN,
                kind=LedgerAccountKind.USER,
            )
            session.add(account)
            session.flush()
        return account

    def get_position_escrow_account(self, session: Session, user: User, player_id: str) -> LedgerAccount:
        code = self._position_escrow_account_code(user.id, player_id)
        account = session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f"Player {player_id} Position Escrow",
                unit=LedgerUnit.COIN,
                kind=LedgerAccountKind.ESCROW,
            )
            session.add(account)
            session.flush()
        return account

    def ensure_platform_position_account(self, session: Session, player_id: str) -> LedgerAccount:
        return self._ensure_system_account(
            session,
            code=self._platform_position_account_code(player_id),
            label=f"Platform {player_id} Inventory",
            unit=LedgerUnit.COIN,
            allow_negative=True,
        )

    def create_payment_event(
        self,
        session: Session,
        *,
        user: User,
        provider: PaymentProvider | str,
        provider_reference: str,
        amount: Decimal,
        pack_code: str | None = None,
    ) -> PaymentEvent:
        normalized_provider = PaymentProvider(provider)
        event = PaymentEvent(
            user_id=user.id,
            provider=normalized_provider,
            provider_reference=provider_reference.strip(),
            pack_code=pack_code,
            amount=self._normalize_amount(amount),
            unit=LedgerUnit.COIN,
            status=PaymentStatus.PENDING,
            raw_payload={},
        )
        session.add(event)
        try:
            session.flush()
        except IntegrityError as exc:
            raise LedgerError("Provider reference already exists.") from exc
        self._stage_domain_event(
            session,
            event=DomainEvent(
                name="wallet.payment.created",
                payload={
                    "payment_event_id": event.id,
                    "user_id": user.id,
                    "provider": normalized_provider.value,
                    "amount": str(event.amount),
                },
                aggregate_id=event.id,
                aggregate_type="payment_event",
                producer="wallet_service",
                partition_key=user.id,
            ),
            durable=True,
        )
        return event

    def verify_payment_event(
        self, session: Session, payment_event: PaymentEvent, *, actor: User | None = None
    ) -> PaymentEvent:
        if payment_event.status == PaymentStatus.VERIFIED and payment_event.ledger_transaction_id is not None:
            raise LedgerError("Only pending payment events can be verified.")
        if payment_event.ledger_transaction_id is not None and payment_event.status != PaymentStatus.VERIFIED:
            raise LedgerError("Payment event is already linked to a processed ledger transaction.")
        if payment_event.status != PaymentStatus.PENDING:
            raise LedgerError("Only pending payment events can be verified.")

        user = session.get(User, payment_event.user_id)
        if user is None:
            raise LedgerError("Payment event references a missing user.")

        user_account = self.get_user_account(session, user, payment_event.unit)
        treasury_account = self.ensure_treasury_account(session, payment_event.unit)
        operations_account = self.ensure_operations_account(session, payment_event.unit)
        source_tag = (
            LedgerSourceTag.MARKET_TOPUP if payment_event.unit == LedgerUnit.COIN else LedgerSourceTag.FANCOIN_PURCHASE
        )
        entries = self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=payment_event.amount),
                LedgerPosting(account=treasury_account, amount=payment_event.amount),
                LedgerPosting(account=operations_account, amount=-(payment_event.amount * Decimal("2.0000"))),
            ],
            reason=LedgerEntryReason.DEPOSIT,
            source_tag=source_tag,
            reference=payment_event.provider_reference,
            description=f"Verified {PaymentProvider(payment_event.provider).value} deposit",
            external_reference=payment_event.provider_reference,
            actor=actor,
            idempotency_key=f"payment-event:{payment_event.id}:verify",
            transaction_type=LedgerTransactionType.DEPOSIT,
            metadata={
                "payment_event_id": payment_event.id,
                "provider": PaymentProvider(payment_event.provider).value,
            },
        )
        payment_event.status = PaymentStatus.VERIFIED
        payment_event.verified_at = utcnow()
        payment_event.processed_at = utcnow()
        payment_event.ledger_transaction_id = entries[0].transaction_id
        session.flush()
        self._stage_domain_event(
            session,
            event=DomainEvent(
                name="wallet.payment.verified",
                payload={
                    "payment_event_id": payment_event.id,
                    "user_id": user.id,
                    "transaction_id": payment_event.ledger_transaction_id,
                    "amount": str(payment_event.amount),
                },
                aggregate_id=payment_event.id,
                aggregate_type="payment_event",
                producer="wallet_service",
                partition_key=user.id,
            ),
            durable=True,
        )
        return payment_event

    def quote_conversion(self, *, source_unit: LedgerUnit, amount: Decimal) -> WalletConversionQuote:
        normalized_amount = self._normalize_amount(amount)
        if normalized_amount <= Decimal("0.0000"):
            raise LedgerError("Conversion amount must be positive.")
        if source_unit == LedgerUnit.COIN:
            target_unit = LedgerUnit.CREDIT
            target_amount = self._normalize_amount(normalized_amount * COIN_TO_CREDIT_RATE)
            rate = COIN_TO_CREDIT_RATE
        elif source_unit == LedgerUnit.CREDIT:
            raise LedgerError("Fan Coin cannot be converted into GTEX Coin.")
        else:
            raise LedgerError(f"Unsupported conversion source unit: {source_unit!s}")
        return WalletConversionQuote(
            source_unit=source_unit,
            source_amount=normalized_amount,
            target_unit=target_unit,
            target_amount=target_amount,
            rate=rate,
        )

    def convert_wallet_units(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        source_unit: LedgerUnit,
        actor: User | None = None,
        reference: str | None = None,
        idempotency_key: str | None = None,
    ) -> WalletConversionResult:
        quote = self.quote_conversion(source_unit=source_unit, amount=amount)
        source_account = self.get_user_account(session, user, quote.source_unit)
        target_account = self.get_user_account(session, user, quote.target_unit)
        source_platform_account = self.ensure_platform_account(session, quote.source_unit)
        target_platform_account = self.ensure_platform_account(session, quote.target_unit)
        resolved_reference = reference or f"wallet-conversion:{generate_uuid()}"
        description = (
            f"Converted {quote.source_amount} {quote.source_unit.value} "
            f"to {quote.target_amount} {quote.target_unit.value}"
        )
        entries = self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=source_account, amount=-quote.source_amount),
                LedgerPosting(account=source_platform_account, amount=quote.source_amount),
                LedgerPosting(account=target_platform_account, amount=-quote.target_amount),
                LedgerPosting(account=target_account, amount=quote.target_amount),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=resolved_reference,
            description=description,
            external_reference=resolved_reference,
            actor=actor or user,
            idempotency_key=idempotency_key,
            transaction_type=LedgerTransactionType.CONVERSION,
            metadata={
                "conversion": {
                    "source_unit": quote.source_unit.value,
                    "source_amount": str(quote.source_amount),
                    "target_unit": quote.target_unit.value,
                    "target_amount": str(quote.target_amount),
                    "rate": str(quote.rate),
                }
            },
        )
        transaction_id = entries[0].transaction_id
        self._stage_domain_event(
            session,
            event=DomainEvent(
                name="wallet.conversion.completed",
                payload={
                    "transaction_id": transaction_id,
                    "user_id": user.id,
                    "reference": resolved_reference,
                    "source_unit": quote.source_unit.value,
                    "source_amount": str(quote.source_amount),
                    "target_unit": quote.target_unit.value,
                    "target_amount": str(quote.target_amount),
                    "rate": str(quote.rate),
                },
                aggregate_id=transaction_id,
                aggregate_type="ledger_transaction",
                producer="wallet_service",
                partition_key=user.id,
            ),
            durable=True,
        )
        return WalletConversionResult(
            transaction_id=transaction_id,
            reference=resolved_reference,
            source_unit=quote.source_unit,
            source_amount=quote.source_amount,
            target_unit=quote.target_unit,
            target_amount=quote.target_amount,
        )

    def competition_reward_balance(self, session: Session, user: User, unit: LedgerUnit = LedgerUnit.COIN) -> Decimal:
        account = self.get_user_account(session, user, unit)
        reward_total = session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.account_id == account.id,
                LedgerEntry.reason == LedgerEntryReason.COMPETITION_REWARD,
                LedgerEntry.amount > 0,
            )
        )
        return self._normalize_amount(reward_total)

    def competition_reward_withdrawable_balance(
        self, session: Session, user: User, unit: LedgerUnit = LedgerUnit.COIN
    ) -> Decimal:
        rewards_total = self.competition_reward_balance(session, user, unit)
        requests = session.scalars(
            select(PayoutRequest).where(PayoutRequest.user_id == user.id, PayoutRequest.unit == unit)
        ).all()
        reserved_or_paid = Decimal("0.0000")
        for request in requests:
            meta = self._parse_payout_meta(request.notes)
            if meta.get("source_scope") != "competition":
                continue
            if request.status in {PayoutStatus.REJECTED, PayoutStatus.FAILED}:
                continue
            reserved_or_paid += self._payout_total_debit(request)
        remaining = rewards_total - reserved_or_paid
        if remaining < Decimal("0.0000"):
            remaining = Decimal("0.0000")
        return self._normalize_amount(remaining)

    def list_payout_requests_for_user(self, session: Session, user: User) -> list[PayoutRequest]:
        return session.scalars(
            select(PayoutRequest).where(PayoutRequest.user_id == user.id).order_by(PayoutRequest.created_at.desc())
        ).all()

    def request_payout(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        destination_reference: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_scope: str = "trade",
        withdrawal_fee_bps: int = WITHDRAWAL_FEE_BPS,
        minimum_fee: Decimal = WITHDRAWAL_MINIMUM_FEE,
        actor: User | None = None,
        notes: str | None = None,
        extra_meta: dict[str, object] | None = None,
    ) -> WithdrawalRequestResult:
        gross_amount = self._normalize_amount(amount)
        if gross_amount <= Decimal("0.0000"):
            raise LedgerError("Withdrawal amount must be positive.")
        if source_scope not in {"trade", "competition", "user_hosted_gift", "gtex_competition_gift", "national_reward"}:
            raise LedgerError(
                "Withdrawal source must be trade, competition, user_hosted_gift, gtex_competition_gift, or national_reward."
            )

        user_account = self.get_user_account(session, user, unit)
        escrow_account = self.get_user_escrow_account(session, user, unit)
        net_tag = LedgerSourceTag.ADMIN_ADJUSTMENT
        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN
        fee_amount = self._withdrawal_fee_for_gross(
            gross_amount,
            fee_bps=withdrawal_fee_bps,
            minimum_fee=minimum_fee,
        )
        net_amount = self._normalize_amount(gross_amount - fee_amount)
        total_debit = gross_amount
        available_balance = self.get_balance(session, user_account)
        if available_balance < total_debit:
            raise InsufficientBalanceError("Available balance is lower than the requested withdrawal.")
        if source_scope == "competition":
            reward_balance = self.competition_reward_withdrawable_balance(session, user, unit)
            if reward_balance < total_debit:
                raise InsufficientBalanceError(
                    "Competition reward balance is lower than the requested e-game withdrawal."
                )

        reference = f"payout-request:{generate_uuid()}"
        postings = [
            LedgerPosting(account=user_account, amount=-net_amount, source_tag=net_tag),
            LedgerPosting(account=escrow_account, amount=net_amount, source_tag=net_tag),
        ]
        if fee_amount > Decimal("0.0000"):
            postings.extend(
                [
                    LedgerPosting(account=user_account, amount=-fee_amount, source_tag=fee_tag),
                    LedgerPosting(account=escrow_account, amount=fee_amount, source_tag=fee_tag),
                ]
            )
        entries = self.append_transaction(
            session,
            postings=postings,
            reason=LedgerEntryReason.WITHDRAWAL_HOLD,
            source_tag=net_tag,
            reference=reference,
            description=f"Withdrawal hold for {source_scope} payout to {destination_reference}",
            external_reference=reference,
            actor=actor or user,
            transaction_type=LedgerTransactionType.WITHDRAWAL,
            metadata={
                "withdrawal": {
                    "source_scope": source_scope,
                    "destination_reference": destination_reference.strip(),
                    "gross_amount": str(gross_amount),
                    "fee_amount": str(fee_amount),
                    "net_amount": str(net_amount),
                    "total_debit": str(total_debit),
                    "fee_bps": withdrawal_fee_bps,
                }
            },
        )
        meta = {
            "source_scope": source_scope,
            "gross_amount": str(gross_amount),
            "fee_amount": str(fee_amount),
            "net_amount": str(net_amount),
            "total_debit": str(total_debit),
            "requested_gross_amount": str(gross_amount),
            "requested_net_amount": str(net_amount),
            "fee_bps": withdrawal_fee_bps,
            "destination_reference": destination_reference,
            "user_notes": notes or "",
        }
        if extra_meta:
            meta.update(extra_meta)
        payout_request = PayoutRequest(
            user_id=user.id,
            account_id=user_account.id,
            amount=net_amount,
            unit=unit,
            status=PayoutStatus.REQUESTED,
            destination_reference=destination_reference.strip(),
            hold_transaction_id=entries[0].transaction_id if entries else None,
            notes=json.dumps(meta, sort_keys=True),
        )
        session.add(payout_request)
        session.flush()
        self._stage_domain_event(
            session,
            event=DomainEvent(
                name="wallet.withdrawal.requested",
                payload={
                    "payout_request_id": payout_request.id,
                    "user_id": user.id,
                    "source_scope": source_scope,
                    "unit": unit.value,
                    "amount": str(net_amount),
                    "gross_amount": str(gross_amount),
                    "fee_amount": str(fee_amount),
                    "net_amount": str(net_amount),
                    "total_debit": str(total_debit),
                    "fee_bps": withdrawal_fee_bps,
                },
                aggregate_id=payout_request.id,
                aggregate_type="payout_request",
                producer="wallet_service",
                partition_key=user.id,
            ),
            durable=True,
        )
        return WithdrawalRequestResult(
            payout_request=payout_request,
            gross_amount=gross_amount,
            fee_amount=fee_amount,
            net_amount=net_amount,
            total_debit=total_debit,
            source_scope=source_scope,
        )

    def complete_payout_request(
        self, session: Session, payout_request: PayoutRequest, *, actor: User | None = None
    ) -> PayoutRequest:
        if payout_request.settlement_transaction_id is not None:
            return payout_request
        user = session.get(User, payout_request.user_id)
        if user is None:
            raise LedgerError("Payout request references a missing user.")
        escrow_account = self.get_user_escrow_account(session, user, payout_request.unit)
        platform_account = self.ensure_withdrawal_clearing_account(session, payout_request.unit)
        meta = self._parse_payout_meta(payout_request.notes)
        net_amount = self._normalize_amount(payout_request.amount)
        total_debit = self._normalize_amount(meta.get("total_debit", net_amount))
        fee_amount = self._normalize_amount(meta.get("fee_amount", total_debit - net_amount))
        net_tag = LedgerSourceTag.ADMIN_ADJUSTMENT
        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN
        if fee_amount < Decimal("0.0000"):
            fee_amount = Decimal("0.0000")
        reference = f"payout-settlement:{payout_request.id}"
        postings = [
            LedgerPosting(account=escrow_account, amount=-net_amount, source_tag=net_tag),
            LedgerPosting(account=platform_account, amount=net_amount, source_tag=net_tag),
        ]
        if fee_amount > Decimal("0.0000"):
            postings.extend(
                [
                    LedgerPosting(account=escrow_account, amount=-fee_amount, source_tag=fee_tag),
                    LedgerPosting(account=platform_account, amount=fee_amount, source_tag=fee_tag),
                ]
            )
        entries = self.append_transaction(
            session,
            postings=postings,
            reason=LedgerEntryReason.WITHDRAWAL_SETTLEMENT,
            source_tag=net_tag,
            reference=reference,
            description=f"Withdrawal settled to {payout_request.destination_reference}",
            external_reference=reference,
            actor=actor,
            idempotency_key=f"payout:{payout_request.id}:settle",
            transaction_type=LedgerTransactionType.WITHDRAWAL,
            metadata={
                "withdrawal": {
                    "payout_request_id": payout_request.id,
                    "action": "settle",
                    "gross_amount": str(total_debit),
                    "fee_amount": str(fee_amount),
                    "net_amount": str(net_amount),
                    "total_debit": str(total_debit),
                }
            },
        )
        payout_request.settlement_transaction_id = entries[0].transaction_id if entries else None
        return payout_request

    def release_payout_request(
        self,
        session: Session,
        payout_request: PayoutRequest,
        *,
        actor: User | None = None,
        failure_reason: str | None = None,
    ) -> PayoutRequest:
        if payout_request.settlement_transaction_id is not None:
            return payout_request
        user = session.get(User, payout_request.user_id)
        if user is None:
            raise LedgerError("Payout request references a missing user.")
        escrow_account = self.get_user_escrow_account(session, user, payout_request.unit)
        user_account = self.get_user_account(session, user, payout_request.unit)
        meta = self._parse_payout_meta(payout_request.notes)
        net_amount = self._normalize_amount(payout_request.amount)
        total_debit = self._normalize_amount(meta.get("total_debit", net_amount))
        fee_amount = self._normalize_amount(meta.get("fee_amount", total_debit - net_amount))
        net_tag = LedgerSourceTag.ADMIN_ADJUSTMENT
        fee_tag = LedgerSourceTag.WITHDRAWAL_FEE_BURN
        if fee_amount < Decimal("0.0000"):
            fee_amount = Decimal("0.0000")
        reference = f"payout-release:{payout_request.id}"
        postings = [
            LedgerPosting(account=escrow_account, amount=-net_amount, source_tag=net_tag),
            LedgerPosting(account=user_account, amount=net_amount, source_tag=net_tag),
        ]
        if fee_amount > Decimal("0.0000"):
            postings.extend(
                [
                    LedgerPosting(account=escrow_account, amount=-fee_amount, source_tag=fee_tag),
                    LedgerPosting(account=user_account, amount=fee_amount, source_tag=fee_tag),
                ]
            )
        entries = self.append_transaction(
            session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=net_tag,
            reference=reference,
            description=f"Withdrawal released back to user after {failure_reason or 'cancel'}",
            external_reference=reference,
            actor=actor,
            idempotency_key=f"payout:{payout_request.id}:release",
            transaction_type=LedgerTransactionType.WITHDRAWAL,
            metadata={
                "withdrawal": {
                    "payout_request_id": payout_request.id,
                    "action": "release",
                    "failure_reason": failure_reason or "",
                    "gross_amount": str(total_debit),
                    "fee_amount": str(fee_amount),
                    "net_amount": str(net_amount),
                    "total_debit": str(total_debit),
                }
            },
        )
        payout_request.settlement_transaction_id = entries[0].transaction_id if entries else None
        return payout_request

    def _parse_payout_meta(self, notes: str | None) -> dict[str, object]:
        raw = (notes or "").strip()
        if not raw:
            return {}
        if raw.startswith("{"):
            try:
                value = json.loads(raw)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                return {"raw_notes": raw}
        return {"raw_notes": raw}

    def _payout_total_debit(self, payout_request: PayoutRequest) -> Decimal:
        meta = self._parse_payout_meta(payout_request.notes)
        try:
            if meta.get("total_debit") is not None:
                return self._normalize_amount(meta.get("total_debit"))
            fee_amount = self._normalize_amount(meta.get("fee_amount", Decimal("0.0000")))
        except (TypeError, ValueError):
            fee_amount = Decimal("0.0000")
        return self._normalize_amount(Decimal(payout_request.amount or 0) + fee_amount)

    def _withdrawal_fee_for_gross(
        self,
        gross_amount: Decimal,
        *,
        fee_bps: int | None = None,
        minimum_fee: Decimal | None = None,
    ) -> Decimal:
        resolved_fee_bps = resolve_withdrawal_fee_bps() if fee_bps is None else int(fee_bps)
        resolved_minimum_fee = resolve_withdrawal_minimum_fee() if minimum_fee is None else Decimal(str(minimum_fee))
        fee = gross_amount * Decimal(resolved_fee_bps) / Decimal(10_000)
        return self._normalize_amount(max(fee, resolved_minimum_fee))

    def _transfer_bid_reservation_metadata(
        self,
        *,
        action: str,
        transfer_bid_id: str,
        amount: Decimal,
        unit: LedgerUnit,
        player_id: str | None = None,
        buying_club_id: str | None = None,
        selling_club_id: str | None = None,
        release_reason: str | None = None,
        reserved_amount: Decimal | None = None,
        available_amount: Decimal | None = None,
        settlement_account_id: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = dict(extra_metadata or {})
        reservation: dict[str, Any] = {
            "kind": TRANSFER_BID_RESERVATION_KIND,
            "key": self._transfer_bid_reservation_key(transfer_bid_id),
            "transfer_bid_id": transfer_bid_id,
            "action": self._normalize_reservation_token(action),
            "amount": str(self._normalize_amount(amount)),
            "unit": unit.value,
            "lock_reason": "Transfer bid reservations",
        }
        optional_values = {
            "player_id": player_id,
            "buying_club_id": buying_club_id,
            "selling_club_id": selling_club_id,
            "release_reason": release_reason,
            "reserved_amount": str(self._normalize_amount(reserved_amount)) if reserved_amount is not None else None,
            "available_amount": str(self._normalize_amount(available_amount)) if available_amount is not None else None,
            "settlement_account_id": settlement_account_id,
        }
        for key, value in optional_values.items():
            if value is not None:
                reservation[key] = value
        metadata[WALLET_RESERVATION_METADATA_KEY] = reservation
        return metadata

    @staticmethod
    def _transfer_bid_reservation_key(transfer_bid_id: str) -> str:
        return f"transfer_bid:{transfer_bid_id.strip()}"

    @staticmethod
    def _normalize_reservation_token(value: str | None) -> str:
        candidate = (value or "unspecified").strip().lower().replace(" ", "_").replace("-", "_")
        return candidate or "unspecified"

    def _infer_transaction_type(
        self,
        *,
        posting: LedgerPosting,
        reason: LedgerEntryReason,
        transaction_source_tag: LedgerSourceTag,
        metadata: dict[str, Any],
    ) -> LedgerTransactionType:
        source_tag = posting.source_tag or transaction_source_tag

        if reason == LedgerEntryReason.DEPOSIT:
            return LedgerTransactionType.DEPOSIT
        if reason in {LedgerEntryReason.WITHDRAWAL_HOLD, LedgerEntryReason.WITHDRAWAL_SETTLEMENT}:
            return LedgerTransactionType.WITHDRAWAL
        if reason == LedgerEntryReason.COMPETITION_ENTRY:
            return LedgerTransactionType.MATCH_ENTRY_FEE
        if reason == LedgerEntryReason.COMPETITION_REWARD:
            reward_source = ""
            if isinstance(metadata.get("reward_source"), str):
                reward_source = str(metadata.get("reward_source") or "")
            elif isinstance(metadata.get("reward"), dict):
                reward_source = str((metadata.get("reward") or {}).get("reward_source") or "")
            if "lottery" in reward_source.lower():
                return LedgerTransactionType.LOTTERY_REWARD
            return LedgerTransactionType.MATCH_REWARD
        if reason == LedgerEntryReason.TRADE_SETTLEMENT:
            if source_tag in TRADE_SELL_SOURCE_TAGS:
                return LedgerTransactionType.TRADE_SELL
            if source_tag in TRADE_BUY_SOURCE_TAGS or source_tag == LedgerSourceTag.TRADING_FEE_BURN:
                return LedgerTransactionType.TRADE_BUY
            if posting.account.kind == LedgerAccountKind.USER:
                return (
                    LedgerTransactionType.TRADE_BUY
                    if posting.amount < Decimal("0.0000")
                    else LedgerTransactionType.TRADE_SELL
                )
        if source_tag == LedgerSourceTag.PROMO_POOL_CREDIT:
            return LedgerTransactionType.PROMO_POOL_CREDIT
        if "conversion" in metadata:
            return LedgerTransactionType.CONVERSION
        return LedgerTransactionType.ADJUSTMENT

    def get_adaptive_overview(self, session: Session, user: User) -> dict[str, object]:
        summary = self.get_wallet_summary(session, user, currency=LedgerUnit.COIN)
        requested_statuses = {
            PayoutStatus.REQUESTED,
            PayoutStatus.REVIEWING,
            PayoutStatus.HELD,
            PayoutStatus.PROCESSING,
        }
        pending_withdrawals = (
            session.scalar(
                select(func.count())
                .select_from(PayoutRequest)
                .where(
                    PayoutRequest.user_id == user.id,
                    PayoutRequest.status.in_(tuple(requested_statuses)),
                )
            )
            or 0
        )
        provider_status = {provider.value: "available" for provider in PaymentProvider}
        insights: list[dict[str, str]] = []
        if summary.available_balance <= Decimal("0.0000"):
            insights.append(
                {
                    "label": "Liquidity posture",
                    "value": "Wallet is empty. Deposit or complete a sale to unlock actions.",
                    "tone": "warning",
                }
            )
        elif summary.reserved_balance > summary.available_balance:
            insights.append(
                {
                    "label": "Reserved pressure",
                    "value": "Reserved commitments are heavier than free balance. Review open market and withdrawal holds.",
                    "tone": "warning",
                }
            )
        else:
            insights.append(
                {
                    "label": "Withdrawal readiness",
                    "value": "Withdrawable balance is healthy relative to current holds.",
                    "tone": "success",
                }
            )
        if pending_withdrawals:
            insights.append(
                {
                    "label": "Withdrawal queue",
                    "value": f"{pending_withdrawals} payout request(s) still moving through review or processing.",
                    "tone": "info",
                }
            )
        return {
            "available_balance": summary.available_balance,
            "reserved_balance": summary.reserved_balance,
            "locked_balance": summary.locked_balance,
            "pending_withdrawal_balance": summary.pending_withdrawal_balance,
            "lock_reasons": [reason.to_dict() for reason in summary.lock_reasons],
            "total_balance": summary.total_balance,
            "currency": summary.currency,
            "withdrawable_balance": summary.available_balance,
            "pending_withdrawals": int(pending_withdrawals),
            "payment_provider_status": provider_status,
            "insights": insights,
        }

    def append_transaction(
        self,
        session: Session,
        *,
        postings: list[LedgerPosting],
        reason: LedgerEntryReason,
        source_tag: LedgerSourceTag | None = None,
        transaction_type: LedgerTransactionType | None = None,
        reference: str | None = None,
        description: str | None = None,
        external_reference: str | None = None,
        actor: User | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[LedgerEntry]:
        if len(postings) < 2:
            raise UnbalancedTransactionError("Ledger transactions require at least two postings.")

        normalized_postings: list[LedgerPosting] = []
        total_by_unit: dict[LedgerUnit, Decimal] = defaultdict(lambda: Decimal("0.0000"))
        delta_by_account: dict[str, Decimal] = defaultdict(lambda: Decimal("0.0000"))
        accounts_by_id: dict[str, LedgerAccount] = {}
        for posting in postings:
            amount = self._normalize_amount(posting.amount)
            if amount == Decimal("0.0000"):
                raise LedgerError("Zero-value ledger entries are not allowed.")
            if not posting.account.is_active:
                raise LedgerError(f"Ledger account {posting.account.code} is inactive.")
            normalized_postings.append(
                LedgerPosting(
                    account=posting.account,
                    amount=amount,
                    source_tag=posting.source_tag,
                    transaction_type=posting.transaction_type,
                )
            )
            accounts_by_id[posting.account.id] = posting.account
            total_by_unit[posting.account.unit] += amount
            delta_by_account[posting.account.id] += amount

        unbalanced_units = {unit: total for unit, total in total_by_unit.items() if total != Decimal("0.0000")}
        if unbalanced_units:
            raise UnbalancedTransactionError("Ledger transactions must net to zero within each ledger unit.")

        normalized_idempotency_key = self._normalize_idempotency_key(idempotency_key)
        if normalized_idempotency_key is not None:
            existing_entries = self._resolve_idempotent_entries(session, normalized_idempotency_key)
            if existing_entries is not None:
                return existing_entries

        balance_projections = self._load_balance_projections(
            session,
            list(accounts_by_id.values()),
            for_update=True,
        )
        balance_transitions: dict[str, dict[str, Any]] = {}
        for account_id, delta in delta_by_account.items():
            account = accounts_by_id[account_id]
            before_balance = self._normalize_amount(balance_projections[account_id].balance)
            projected_balance = self._normalize_amount(before_balance + delta)
            balance_transitions[account_id] = {
                "account_id": account.id,
                "account_code": account.code,
                "owner_user_id": account.owner_user_id,
                "unit": account.unit.value,
                "before_balance": str(before_balance),
                "delta": str(delta),
                "after_balance": str(projected_balance),
            }
            if projected_balance < Decimal("0.0000") and not account.allow_negative:
                raise InsufficientBalanceError(f"Account {account.code} does not have enough balance.")

        transaction_source_tag = source_tag or next(
            (posting.source_tag for posting in normalized_postings if posting.source_tag is not None),
            LedgerSourceTag.ADMIN_ADJUSTMENT,
        )
        transaction_record = LedgerTransaction(
            status=LedgerTransactionStatus.PENDING,
            reason=reason,
            source_tag=transaction_source_tag,
            reference=reference,
            external_reference=external_reference,
            description=description,
            idempotency_key=normalized_idempotency_key,
            metadata_json=dict(metadata or {}),
            created_by_user_id=actor.id if actor is not None else None,
        )
        transaction_header_savepoint = session.begin_nested()
        try:
            session.add(transaction_record)
            session.flush()
        except IntegrityError as exc:
            transaction_header_savepoint.rollback()
            if normalized_idempotency_key is not None:
                existing_entries = self._resolve_idempotent_entries(session, normalized_idempotency_key)
                if existing_entries is not None:
                    return existing_entries
                raise LedgerError("Ledger idempotency key is already in use.") from exc
            raise
        else:
            transaction_header_savepoint.commit()

        entries: list[LedgerEntry] = []
        for posting in normalized_postings:
            resolved_tag = posting.source_tag or source_tag or LedgerSourceTag.ADMIN_ADJUSTMENT
            resolved_transaction_type = (
                posting.transaction_type
                or transaction_type
                or self._infer_transaction_type(
                    posting=posting,
                    reason=reason,
                    transaction_source_tag=transaction_source_tag,
                    metadata=transaction_record.metadata_json,
                )
            )
            entries.append(
                LedgerEntry(
                    transaction_id=transaction_record.id,
                    account_id=posting.account.id,
                    created_by_user_id=actor.id if actor is not None else None,
                    amount=posting.amount,
                    unit=posting.account.unit,
                    source_tag=resolved_tag,
                    reason=reason,
                    transaction_type=resolved_transaction_type,
                    reference=reference,
                    external_reference=external_reference,
                    description=description,
                )
            )
        session.add_all(entries)
        session.flush()
        updated_balances: dict[str, Decimal] = {}
        for account_id, delta in delta_by_account.items():
            account = accounts_by_id[account_id]
            projection = balance_projections[account_id]
            projection.owner_user_id = account.owner_user_id
            projection.unit = account.unit
            projection.balance = self._normalize_amount(projection.balance + delta)
            projection.last_transaction_id = transaction_record.id
            updated_balances[account_id] = projection.balance
        transaction_record.status = LedgerTransactionStatus.COMMITTED
        transaction_record.committed_at = utcnow()
        session.flush()
        owner_user_ids = sorted(
            {
                owner_user_id
                for owner_user_id in (account.owner_user_id for account in accounts_by_id.values())
                if owner_user_id
            }
        )
        transaction_event = DomainEvent(
            name="wallet.transaction.appended",
            payload={
                "transaction_id": transaction_record.id,
                "reason": reason.value,
                "source_tag": transaction_source_tag.value,
                "reference": reference,
                "external_reference": external_reference,
                "account_ids": [posting.account.id for posting in normalized_postings],
                "owner_user_ids": owner_user_ids,
                "created_by_user_id": actor.id if actor is not None else None,
                "units": sorted(unit.value for unit in total_by_unit),
                "idempotency_key": normalized_idempotency_key,
                "metadata": dict(transaction_record.metadata_json or {}),
                "entries": [
                    {
                        "entry_id": entry.id,
                        "account_id": entry.account_id,
                        "account_code": entry.account.code if entry.account is not None else None,
                        "account_kind": entry.account.kind.value if entry.account is not None else None,
                        "owner_user_id": entry.account.owner_user_id if entry.account is not None else None,
                        "amount": str(entry.amount),
                        "direction": "credit" if entry.amount > 0 else "debit",
                        "unit": entry.unit.value if hasattr(entry.unit, "value") else str(entry.unit),
                        "reason": entry.reason.value,
                        "source_tag": entry.source_tag.value,
                        "reference": entry.reference,
                        "external_reference": entry.external_reference,
                    }
                    for entry in entries
                ],
            },
            aggregate_id=transaction_record.id,
            aggregate_type="ledger_transaction",
            producer="wallet_service",
            partition_key=owner_user_ids[0] if owner_user_ids else transaction_record.id,
            headers={"delivery_mode": "durable"},
        )
        self._stage_domain_event(session, event=transaction_event, durable=True)
        for entry in entries:
            event_name = "wallet_credit_applied" if entry.amount > 0 else "wallet_debit_applied"
            self._stage_domain_event(
                session,
                event=DomainEvent(
                    name=event_name,
                    payload={
                        "transaction_id": entry.transaction_id,
                        "entry_id": entry.id,
                        "account_id": entry.account_id,
                        "account_code": entry.account.code if entry.account else None,
                        "account_kind": entry.account.kind.value if entry.account else None,
                        "owner_user_id": entry.account.owner_user_id if entry.account else None,
                        "amount": str(entry.amount),
                        "unit": entry.unit.value if hasattr(entry.unit, "value") else str(entry.unit),
                        "reason": entry.reason.value,
                        "source_tag": entry.source_tag.value,
                        "reference": entry.reference,
                        "external_reference": entry.external_reference,
                    },
                    aggregate_id=entry.id,
                    aggregate_type="ledger_entry",
                    producer="wallet_service",
                    partition_key=(
                        entry.account.owner_user_id
                        if entry.account and entry.account.owner_user_id
                        else entry.account_id
                    ),
                ),
            )
        for account_id, balance in updated_balances.items():
            account = accounts_by_id[account_id]
            self._cache_balance_after_commit(session, account=account, balance=balance)
            self._stage_domain_event(
                session,
                event=DomainEvent(
                    name="wallet.balance.updated",
                    payload={
                        "transaction_id": transaction_record.id,
                        "account_id": account.id,
                        "account_code": account.code,
                        "owner_user_id": account.owner_user_id,
                        "balance": str(balance),
                        "unit": account.unit.value,
                    },
                    aggregate_id=account.id,
                    aggregate_type="ledger_account",
                    producer="wallet_service",
                    partition_key=account.owner_user_id or account.id,
                ),
            )
        from app.risk_ops_engine.service import RiskOpsService

        RiskOpsService(session).log_audit(
            actor_user_id=actor.id if actor is not None else None,
            action_key="wallet.transaction.recorded",
            resource_type="ledger_transaction",
            resource_id=transaction_record.id,
            detail=f"Wallet transaction recorded for {reason.value}.",
            metadata_json={
                "transaction_id": transaction_record.id,
                "reason": reason.value,
                "source_tag": transaction_source_tag.value,
                "reference": reference,
                "external_reference": external_reference,
                "idempotency_key": normalized_idempotency_key,
                "balance_transitions": list(balance_transitions.values()),
                "entries": [
                    {
                        "entry_id": entry.id,
                        "account_id": entry.account_id,
                        "account_code": entry.account.code if entry.account is not None else None,
                        "owner_user_id": entry.account.owner_user_id if entry.account is not None else None,
                        "amount": str(entry.amount),
                        "unit": entry.unit.value if hasattr(entry.unit, "value") else str(entry.unit),
                        "transaction_type": (
                            entry.transaction_type.value
                            if hasattr(entry.transaction_type, "value")
                            else str(entry.transaction_type)
                        ),
                        "source_tag": (
                            entry.source_tag.value if hasattr(entry.source_tag, "value") else str(entry.source_tag)
                        ),
                    }
                    for entry in entries
                ],
                "metadata": dict(transaction_record.metadata_json or {}),
            },
        )
        self._prime_impacted_wallet_summary_caches(session, accounts=accounts_by_id, defer_until_commit=True)
        return entries

    def get_balance(self, session: Session, account: LedgerAccount) -> Decimal:
        if not self._session_has_pending_state(session):
            cached_balance = self._read_cached_balance(account)
            if cached_balance is not None:
                return cached_balance
        projection = self._get_or_build_balance_projection(session, account)
        balance = self._normalize_amount(projection.balance)
        self._prime_balance_cache(session, account=account, balance=balance)
        return balance

    def get_wallet_summary(
        self, session: Session, user: User, *, currency: LedgerUnit = LedgerUnit.CREDIT
    ) -> WalletSummary:
        if not self._session_has_pending_state(session):
            cached_summary = self._read_cached_wallet_summary(user_id=user.id, currency=currency)
            if cached_summary is not None:
                return cached_summary
        available_account = self.get_user_account(session, user, currency)
        reserved_balance = self._get_user_account_balance_by_kind(session, user, currency, LedgerAccountKind.ESCROW)
        available_balance = self.get_balance(session, available_account)
        pending_withdrawal_balance = self._pending_withdrawal_balance(session, user=user, currency=currency)
        lock_reasons = self._wallet_lock_reasons(
            session,
            user=user,
            currency=currency,
            reserved_balance=reserved_balance,
        )
        summary = WalletSummary(
            available_balance=available_balance,
            reserved_balance=reserved_balance,
            total_balance=self._normalize_amount(available_balance + reserved_balance),
            currency=currency,
            locked_balance=reserved_balance,
            pending_withdrawal_balance=pending_withdrawal_balance,
            lock_reasons=lock_reasons,
        )
        self._prime_wallet_summary_cache(
            session,
            user_id=user.id,
            currency=currency,
            available_balance=summary.available_balance,
            reserved_balance=summary.reserved_balance,
            pending_withdrawal_balance=summary.pending_withdrawal_balance,
            lock_reasons=summary.lock_reasons,
        )
        return summary

    def _pending_withdrawal_balance(self, session: Session, *, user: User, currency: LedgerUnit) -> Decimal:
        pending_statuses = (
            PayoutStatus.REQUESTED,
            PayoutStatus.REVIEWING,
            PayoutStatus.HELD,
            PayoutStatus.PROCESSING,
        )
        requests = session.scalars(
            select(PayoutRequest).where(
                PayoutRequest.user_id == user.id,
                PayoutRequest.unit == currency,
                PayoutRequest.status.in_(pending_statuses),
            )
        ).all()
        amount = sum((self._payout_total_debit(request) for request in requests), Decimal("0.0000"))
        return self._normalize_amount(amount)

    def _wallet_lock_reasons(
        self,
        session: Session,
        *,
        user: User,
        currency: LedgerUnit,
        reserved_balance: Decimal,
    ) -> tuple[WalletLockReason, ...]:
        normalized_reserved = self._normalize_amount(reserved_balance)
        if normalized_reserved <= Decimal("0.0000"):
            return ()

        escrow_account = session.scalar(
            select(LedgerAccount).where(
                LedgerAccount.owner_user_id == user.id,
                LedgerAccount.unit == currency,
                LedgerAccount.kind == LedgerAccountKind.ESCROW,
            )
        )
        if escrow_account is None:
            return (
                self._format_lock_reason(
                    code="escrow_commitment",
                    label="Escrow commitments",
                    amount=normalized_reserved,
                    currency=currency,
                    source="escrow",
                ),
            )

        bucket_amounts: dict[str, Decimal] = defaultdict(lambda: Decimal("0.0000"))
        bucket_details: dict[str, tuple[str, str, str, str | None]] = {}
        rows = session.execute(
            select(
                LedgerEntry.amount,
                LedgerEntry.reason,
                LedgerEntry.reference,
                LedgerTransaction.metadata_json,
            )
            .join(LedgerTransaction, LedgerTransaction.id == LedgerEntry.transaction_id)
            .where(LedgerEntry.account_id == escrow_account.id)
            .order_by(LedgerEntry.created_at.asc(), LedgerEntry.id.asc())
        ).all()
        for amount, reason, reference, metadata in rows:
            bucket = self._wallet_lock_bucket(
                metadata if isinstance(metadata, dict) else {},
                reference=reference,
                reason=reason,
            )
            if bucket is None:
                continue
            bucket_key, code, label, source, reference = bucket
            bucket_amounts[bucket_key] += self._normalize_amount(amount)
            bucket_details.setdefault(bucket_key, (code, label, source, reference))

        reasons: list[WalletLockReason] = []
        remaining_reserved = normalized_reserved
        for bucket_key in sorted(bucket_amounts):
            amount = min(self._normalize_amount(bucket_amounts[bucket_key]), remaining_reserved)
            if amount <= Decimal("0.0000"):
                continue
            code, label, source, reference = bucket_details[bucket_key]
            reasons.append(
                self._format_lock_reason(
                    code=code,
                    label=label,
                    amount=amount,
                    currency=currency,
                    source=source,
                    reference=reference,
                )
            )
            remaining_reserved = self._normalize_amount(remaining_reserved - amount)
            if remaining_reserved <= Decimal("0.0000"):
                break

        if remaining_reserved > Decimal("0.0000"):
            reasons.append(
                self._format_lock_reason(
                    code="escrow_commitment",
                    label="Escrow commitments",
                    amount=remaining_reserved,
                    currency=currency,
                    source="escrow",
                )
            )
        return tuple(reasons)

    def _wallet_lock_bucket(
        self,
        metadata: dict[str, Any],
        *,
        reference: str | None,
        reason: LedgerEntryReason,
    ) -> tuple[str, str, str, str, str | None] | None:
        reservation = metadata.get(WALLET_RESERVATION_METADATA_KEY)
        if isinstance(reservation, dict):
            kind = str(reservation.get("kind") or "wallet").strip().lower() or "wallet"
            key = str(
                reservation.get("key")
                or reservation.get("reservation_id")
                or reservation.get("transfer_bid_id")
                or reference
                or kind
            )
            label = str(reservation.get("lock_reason") or "").strip()
            if not label:
                label = "Transfer bid reservations" if kind == TRANSFER_BID_RESERVATION_KIND else "Wallet reservations"
            code = "transfer_bid_reservation" if kind == TRANSFER_BID_RESERVATION_KIND else f"{kind}_reservation"
            return f"{code}:{key}", code, label, kind, key

        if isinstance(metadata.get("withdrawal"), dict) or (reference or "").startswith("payout-"):
            return "withdrawal_hold:payout", "withdrawal_hold", "Withdrawal holds", "withdrawal", reference
        reason_value = reason.value if hasattr(reason, "value") else str(reason)
        if reason_value == LedgerEntryReason.WITHDRAWAL_HOLD.value:
            return "wallet_hold:ledger", "wallet_hold", "Wallet holds", "wallet", reference
        return None

    def _format_lock_reason(
        self,
        *,
        code: str,
        label: str,
        amount: Decimal,
        currency: LedgerUnit,
        source: str,
        reference: str | None = None,
    ) -> WalletLockReason:
        return WalletLockReason(
            code=code,
            label=label,
            amount=self._normalize_amount(amount),
            currency=currency,
            source=source,
            reference=reference,
        )

    def build_portfolio_snapshot(self, session: Session, user: User) -> PortfolioSnapshot:
        from app.portfolio.service import PortfolioService

        portfolio_snapshot = PortfolioService(wallet_service=self).build_for_user(session, user)
        summary = self.get_wallet_summary(session, user, currency=portfolio_snapshot.cash_unit)
        return PortfolioSnapshot(
            user_id=user.id,
            currency=summary.currency,
            available_balance=summary.available_balance,
            reserved_balance=summary.reserved_balance,
            total_balance=summary.total_balance,
            holdings=[asdict(holding) for holding in portfolio_snapshot.holdings],
        )

    def list_ledger_entries_for_user(
        self,
        session: Session,
        user: User,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> WalletLedgerPage:
        total = session.scalar(
            select(func.count(LedgerEntry.id))
            .select_from(LedgerEntry)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                or_(
                    LedgerAccount.owner_user_id == user.id,
                    LedgerAccount.code.like(f"position:{user.id}:%"),
                )
            )
        )
        items = session.scalars(
            select(LedgerEntry)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                or_(
                    LedgerAccount.owner_user_id == user.id,
                    LedgerAccount.code.like(f"position:{user.id}:%"),
                )
            )
            .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return WalletLedgerPage(
            page=page,
            page_size=page_size,
            total=int(total or 0),
            items=items,
        )

    def reserve_order_funds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[LedgerEntry]:
        reserved_amount = self._normalize_amount(amount)
        if reserved_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        escrow_account = self.get_user_escrow_account(session, user, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=available_account, amount=-reserved_amount),
                LedgerPosting(account=escrow_account, amount=reserved_amount),
            ],
            reason=LedgerEntryReason.WITHDRAWAL_HOLD,
            source_tag=source_tag,
            reference=reference,
            description=description,
            actor=user,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

    def release_reserved_funds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[LedgerEntry]:
        released_amount = self._normalize_amount(amount)
        if released_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        escrow_account = self.get_user_escrow_account(session, user, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-released_amount),
                LedgerPosting(account=available_account, amount=released_amount),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=source_tag,
            reference=reference,
            description=description,
            actor=user,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

    def settle_reserved_funds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        settled_amount = self._normalize_amount(amount)
        if settled_amount <= Decimal("0.0000"):
            return []

        escrow_account = self.get_user_escrow_account(session, user, unit)
        platform_account = self.ensure_market_liquidity_account(session, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-settled_amount),
                LedgerPosting(account=platform_account, amount=settled_amount),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def settle_available_funds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        settled_amount = self._normalize_amount(amount)
        if settled_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        platform_account = self.ensure_market_liquidity_account(session, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=available_account, amount=-settled_amount),
                LedgerPosting(account=platform_account, amount=settled_amount),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def credit_trade_proceeds(
        self,
        session: Session,
        *,
        user: User,
        amount: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        unit: LedgerUnit = LedgerUnit.COIN,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        credited_amount = self._normalize_amount(amount)
        if credited_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        platform_account = self.ensure_market_liquidity_account(session, unit)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=available_account, amount=credited_amount),
                LedgerPosting(account=platform_account, amount=-credited_amount),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def reserve_transfer_bid_funds(
        self,
        session: Session,
        *,
        user: User,
        transfer_bid_id: str,
        amount: Decimal,
        reference: str | None = None,
        description: str | None = None,
        unit: LedgerUnit = LedgerUnit.COIN,
        player_id: str | None = None,
        buying_club_id: str | None = None,
        selling_club_id: str | None = None,
        source_tag: LedgerSourceTag | None = None,
        actor: User | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[LedgerEntry]:
        reserved_amount = self._normalize_amount(amount)
        if reserved_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        escrow_account = self.get_user_escrow_account(session, user, unit)
        resolved_reference = reference or f"transfer-bid:{transfer_bid_id}:reserve"
        reservation_metadata = self._transfer_bid_reservation_metadata(
            action="reserve",
            transfer_bid_id=transfer_bid_id,
            amount=reserved_amount,
            unit=unit,
            player_id=player_id,
            buying_club_id=buying_club_id,
            selling_club_id=selling_club_id,
            extra_metadata=metadata,
        )
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=available_account,
                    amount=-reserved_amount,
                    source_tag=source_tag,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                ),
                LedgerPosting(
                    account=escrow_account,
                    amount=reserved_amount,
                    source_tag=source_tag,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                ),
            ],
            reason=LedgerEntryReason.WITHDRAWAL_HOLD,
            source_tag=source_tag,
            reference=resolved_reference,
            description=description or f"Reserved transfer bid funds for {transfer_bid_id}",
            external_reference=resolved_reference,
            actor=actor or user,
            idempotency_key=idempotency_key or f"transfer-bid:{transfer_bid_id}:reserve",
            metadata=reservation_metadata,
        )

    def reserve_transfer_bid_reservation(self, *args: Any, **kwargs: Any) -> list[LedgerEntry]:
        return self.reserve_transfer_bid_funds(*args, **kwargs)

    def release_transfer_bid_reservation(
        self,
        session: Session,
        *,
        user: User,
        transfer_bid_id: str,
        amount: Decimal | None = None,
        release_reason: str = "released",
        reference: str | None = None,
        description: str | None = None,
        unit: LedgerUnit = LedgerUnit.COIN,
        player_id: str | None = None,
        buying_club_id: str | None = None,
        selling_club_id: str | None = None,
        source_tag: LedgerSourceTag | None = None,
        actor: User | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[LedgerEntry]:
        active_reserved = self.get_transfer_bid_reserved_amount(
            session,
            user=user,
            transfer_bid_id=transfer_bid_id,
            unit=unit,
        )
        requested_amount = active_reserved if amount is None else self._normalize_amount(amount)
        released_amount = min(requested_amount, active_reserved)
        if released_amount <= Decimal("0.0000"):
            return []

        available_account = self.get_user_account(session, user, unit)
        escrow_account = self.get_user_escrow_account(session, user, unit)
        normalized_reason = self._normalize_reservation_token(release_reason)
        resolved_reference = reference or f"transfer-bid:{transfer_bid_id}:release:{normalized_reason}"
        reservation_metadata = self._transfer_bid_reservation_metadata(
            action="release",
            transfer_bid_id=transfer_bid_id,
            amount=released_amount,
            unit=unit,
            player_id=player_id,
            buying_club_id=buying_club_id,
            selling_club_id=selling_club_id,
            release_reason=normalized_reason,
            extra_metadata=metadata,
        )
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(
                    account=escrow_account,
                    amount=-released_amount,
                    source_tag=source_tag,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                ),
                LedgerPosting(
                    account=available_account,
                    amount=released_amount,
                    source_tag=source_tag,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                ),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=source_tag,
            reference=resolved_reference,
            description=description or f"Released transfer bid funds for {transfer_bid_id}",
            external_reference=resolved_reference,
            actor=actor or user,
            idempotency_key=idempotency_key or f"transfer-bid:{transfer_bid_id}:release:{normalized_reason}",
            metadata=reservation_metadata,
        )

    def release_transfer_bid_funds(self, *args: Any, **kwargs: Any) -> list[LedgerEntry]:
        return self.release_transfer_bid_reservation(*args, **kwargs)

    def settle_transfer_bid_reservation(
        self,
        session: Session,
        *,
        user: User,
        transfer_bid_id: str,
        amount: Decimal,
        reference: str | None = None,
        description: str | None = None,
        external_reference: str | None = None,
        unit: LedgerUnit = LedgerUnit.COIN,
        seller_user: User | None = None,
        settlement_account: LedgerAccount | None = None,
        player_id: str | None = None,
        buying_club_id: str | None = None,
        selling_club_id: str | None = None,
        source_tag: LedgerSourceTag | None = None,
        actor: User | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, Any] | None = None,
        require_full_reservation: bool = False,
    ) -> list[LedgerEntry]:
        settled_amount = self._normalize_amount(amount)
        if settled_amount <= Decimal("0.0000"):
            return []

        active_reserved = self.get_transfer_bid_reserved_amount(
            session,
            user=user,
            transfer_bid_id=transfer_bid_id,
            unit=unit,
        )
        if require_full_reservation and active_reserved < settled_amount:
            raise InsufficientBalanceError(
                "Transfer bid settlement requires the full amount to be held in escrow."
            )
        reserved_settlement = min(settled_amount, active_reserved)
        available_settlement = self._normalize_amount(settled_amount - reserved_settlement)
        postings: list[LedgerPosting] = []
        if reserved_settlement > Decimal("0.0000"):
            escrow_account = self.get_user_escrow_account(session, user, unit)
            postings.append(
                LedgerPosting(
                    account=escrow_account,
                    amount=-reserved_settlement,
                    source_tag=source_tag,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                )
            )
        if available_settlement > Decimal("0.0000"):
            available_account = self.get_user_account(session, user, unit)
            postings.append(
                LedgerPosting(
                    account=available_account,
                    amount=-available_settlement,
                    source_tag=source_tag,
                    transaction_type=LedgerTransactionType.TRADE_BUY,
                )
            )

        destination_account = settlement_account
        if destination_account is None and seller_user is not None:
            destination_account = self.get_user_account(session, seller_user, unit)
        if destination_account is None:
            destination_account = self.ensure_market_liquidity_account(session, unit)
        postings.append(
            LedgerPosting(
                account=destination_account,
                amount=settled_amount,
                source_tag=source_tag,
                transaction_type=(
                    LedgerTransactionType.TRADE_SELL
                    if destination_account.kind == LedgerAccountKind.USER and destination_account.owner_user_id != user.id
                    else LedgerTransactionType.TRADE_BUY
                ),
            )
        )

        resolved_reference = reference or f"transfer-bid:{transfer_bid_id}:settle"
        reservation_metadata = self._transfer_bid_reservation_metadata(
            action="settle",
            transfer_bid_id=transfer_bid_id,
            amount=settled_amount,
            unit=unit,
            player_id=player_id,
            buying_club_id=buying_club_id,
            selling_club_id=selling_club_id,
            reserved_amount=reserved_settlement,
            available_amount=available_settlement,
            settlement_account_id=destination_account.id,
            extra_metadata=metadata,
        )
        return self.append_transaction(
            session,
            postings=postings,
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=resolved_reference,
            description=description or f"Settled transfer bid funds for {transfer_bid_id}",
            external_reference=external_reference or resolved_reference,
            actor=actor or user,
            idempotency_key=idempotency_key or f"transfer-bid:{transfer_bid_id}:settle",
            metadata=reservation_metadata,
        )

    def settle_transfer_bid_funds(self, *args: Any, **kwargs: Any) -> list[LedgerEntry]:
        return self.settle_transfer_bid_reservation(*args, **kwargs)

    def replace_transfer_bid_reservation(
        self,
        session: Session,
        *,
        user: User,
        transfer_bid_id: str,
        replacement_amount: Decimal | None = None,
        unit: LedgerUnit = LedgerUnit.COIN,
        release_reason: str = "counter_replaced",
        **kwargs: Any,
    ) -> list[LedgerEntry]:
        entries: list[LedgerEntry] = []
        shared_kwargs = dict(kwargs)
        shared_kwargs.pop("idempotency_key", None)
        raw_amount = replacement_amount if replacement_amount is not None else shared_kwargs.pop("amount", None)
        if raw_amount is None:
            raise LedgerError("Replacement transfer bid reservation amount is required.")
        shared_kwargs.pop("amount", None)
        entries.extend(
            self.release_transfer_bid_reservation(
                session,
                user=user,
                transfer_bid_id=transfer_bid_id,
                unit=unit,
                release_reason=release_reason,
                **shared_kwargs,
            )
        )
        entries.extend(
            self.reserve_transfer_bid_funds(
                session,
                user=user,
                transfer_bid_id=transfer_bid_id,
                amount=raw_amount,
                unit=unit,
                idempotency_key=f"transfer-bid:{transfer_bid_id}:reserve:{self._normalize_amount(raw_amount)}",
                **shared_kwargs,
            )
        )
        return entries

    def get_transfer_bid_reserved_amount(
        self,
        session: Session,
        *,
        user: User,
        transfer_bid_id: str,
        unit: LedgerUnit = LedgerUnit.COIN,
    ) -> Decimal:
        return self.get_wallet_reservation_balance(
            session,
            user=user,
            reservation_kind=TRANSFER_BID_RESERVATION_KIND,
            reservation_key=self._transfer_bid_reservation_key(transfer_bid_id),
            unit=unit,
        )

    def get_wallet_reservation_balance(
        self,
        session: Session,
        *,
        user: User,
        reservation_kind: str,
        reservation_key: str,
        unit: LedgerUnit = LedgerUnit.COIN,
    ) -> Decimal:
        escrow_account = session.scalar(
            select(LedgerAccount).where(LedgerAccount.code == self._user_escrow_account_code(user.id, unit))
        )
        if escrow_account is None:
            return Decimal("0.0000")
        rows = session.execute(
            select(LedgerEntry.amount, LedgerTransaction.metadata_json)
            .join(LedgerTransaction, LedgerTransaction.id == LedgerEntry.transaction_id)
            .where(LedgerEntry.account_id == escrow_account.id)
        ).all()
        normalized_kind = reservation_kind.strip().lower()
        normalized_key = reservation_key.strip()
        balance = Decimal("0.0000")
        for amount, metadata in rows:
            reservation = (metadata or {}).get(WALLET_RESERVATION_METADATA_KEY) if isinstance(metadata, dict) else None
            if not isinstance(reservation, dict):
                continue
            kind = str(reservation.get("kind") or "").strip().lower()
            key = str(reservation.get("key") or reservation.get("reservation_id") or "").strip()
            if kind == normalized_kind and key == normalized_key:
                balance += self._normalize_amount(amount)
        if balance < Decimal("0.0000"):
            return Decimal("0.0000")
        return self._normalize_amount(balance)

    def reserve_position_units(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        quantity: Decimal,
        reference: str,
        description: str,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        reserved_quantity = self._normalize_amount(quantity)
        if reserved_quantity <= Decimal("0.0000"):
            return []

        position_account = self.get_position_account(session, user, player_id)
        escrow_account = self.get_position_escrow_account(session, user, player_id)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=position_account, amount=-reserved_quantity),
                LedgerPosting(account=escrow_account, amount=reserved_quantity),
            ],
            reason=LedgerEntryReason.WITHDRAWAL_HOLD,
            source_tag=source_tag,
            reference=reference,
            description=description,
            actor=user,
        )

    def release_reserved_position_units(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        quantity: Decimal,
        reference: str,
        description: str,
    ) -> list[LedgerEntry]:
        released_quantity = self._normalize_amount(quantity)
        if released_quantity <= Decimal("0.0000"):
            return []

        position_account = self.get_position_account(session, user, player_id)
        escrow_account = self.get_position_escrow_account(session, user, player_id)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-released_quantity),
                LedgerPosting(account=position_account, amount=released_quantity),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference=reference,
            description=description,
            actor=user,
        )

    def settle_reserved_position_units(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        quantity: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        settled_quantity = self._normalize_amount(quantity)
        if settled_quantity <= Decimal("0.0000"):
            return []

        escrow_account = self.get_position_escrow_account(session, user, player_id)
        platform_account = self.ensure_platform_position_account(session, player_id)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=escrow_account, amount=-settled_quantity),
                LedgerPosting(account=platform_account, amount=settled_quantity),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def settle_available_position_units(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        quantity: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        settled_quantity = self._normalize_amount(quantity)
        if settled_quantity <= Decimal("0.0000"):
            return []

        available_account = self.get_position_account(session, user, player_id)
        platform_account = self.ensure_platform_position_account(session, player_id)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=available_account, amount=-settled_quantity),
                LedgerPosting(account=platform_account, amount=settled_quantity),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def credit_position_units(
        self,
        session: Session,
        *,
        user: User,
        player_id: str,
        quantity: Decimal,
        reference: str,
        description: str,
        external_reference: str,
        source_tag: LedgerSourceTag | None = None,
    ) -> list[LedgerEntry]:
        credited_quantity = self._normalize_amount(quantity)
        if credited_quantity <= Decimal("0.0000"):
            return []

        position_account = self.get_position_account(session, user, player_id)
        platform_account = self.ensure_platform_position_account(session, player_id)
        return self.append_transaction(
            session,
            postings=[
                LedgerPosting(account=position_account, amount=credited_quantity),
                LedgerPosting(account=platform_account, amount=-credited_quantity),
            ],
            reason=self.trade_settlement_reason,
            source_tag=source_tag,
            reference=reference,
            description=description,
            external_reference=external_reference,
            actor=user,
        )

    def get_available_position_quantity(self, session: Session, user: User, player_id: str) -> Decimal:
        account = session.scalar(
            select(LedgerAccount).where(LedgerAccount.code == self._position_account_code(user.id, player_id))
        )
        if account is None:
            return Decimal("0.0000")
        return self.get_balance(session, account)

    def get_reserved_position_quantity(self, session: Session, user: User, player_id: str) -> Decimal:
        account = session.scalar(
            select(LedgerAccount).where(LedgerAccount.code == self._position_escrow_account_code(user.id, player_id))
        )
        if account is None:
            return Decimal("0.0000")
        return self.get_balance(session, account)

    def get_position_quantity(self, session: Session, user: User, player_id: str) -> Decimal:
        return self._normalize_amount(
            self.get_available_position_quantity(session, user, player_id)
            + self.get_reserved_position_quantity(session, user, player_id)
        )

    def get_reserved_cash_balance(
        self,
        session: Session,
        user: User,
        *,
        unit: LedgerUnit = LedgerUnit.COIN,
    ) -> Decimal:
        escrow_account = session.scalar(
            select(LedgerAccount).where(LedgerAccount.code == self._user_escrow_account_code(user.id, unit))
        )
        if escrow_account is None:
            return Decimal("0.0000")
        return self.get_balance(session, escrow_account)

    def _list_transaction_entries(self, session: Session, transaction_id: str) -> list[LedgerEntry]:
        return session.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.transaction_id == transaction_id)
            .order_by(LedgerEntry.created_at.asc(), LedgerEntry.id.asc())
        ).all()

    def _resolve_idempotent_entries(self, session: Session, idempotency_key: str) -> list[LedgerEntry] | None:
        transaction_record = session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == idempotency_key)
        )
        if transaction_record is None:
            return None
        if transaction_record.status == LedgerTransactionStatus.COMMITTED:
            return self._list_transaction_entries(session, transaction_record.id)
        raise LedgerError(
            f"Ledger transaction with idempotency key '{idempotency_key}' is already {transaction_record.status.value}."
        )

    def _load_balance_projections(
        self,
        session: Session,
        accounts: list[LedgerAccount],
        *,
        for_update: bool = False,
    ) -> dict[str, LedgerBalanceProjection]:
        if not accounts:
            return {}
        unique_accounts: dict[str, LedgerAccount] = {}
        for account in accounts:
            unique_accounts.setdefault(account.id, account)
        account_ids = list(unique_accounts)
        projections = {
            pending.account_id: pending
            for pending in session.new
            if isinstance(pending, LedgerBalanceProjection) and pending.account_id in account_ids
        }
        statement = select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id.in_(account_ids))
        if for_update and self._supports_row_locks(session):
            statement = statement.with_for_update()
        for projection in session.scalars(statement).all():
            projections.setdefault(projection.account_id, projection)
        for account in unique_accounts.values():
            if account.id not in projections:
                projections[account.id] = self._build_balance_projection(session, account)
        return projections

    def _get_or_build_balance_projection(self, session: Session, account: LedgerAccount) -> LedgerBalanceProjection:
        projections = self._load_balance_projections(session, [account])
        return projections[account.id]

    def _build_balance_projection(self, session: Session, account: LedgerAccount) -> LedgerBalanceProjection:
        for pending in session.new:
            if isinstance(pending, LedgerBalanceProjection) and pending.account_id == account.id:
                return pending
        existing = session.scalar(
            select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id == account.id)
        )
        if existing is not None:
            return existing
        ledger_sum = session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(LedgerEntry.account_id == account.id)
        )
        projection = LedgerBalanceProjection(
            account_id=account.id,
            owner_user_id=account.owner_user_id,
            unit=account.unit,
            balance=self._normalize_amount(ledger_sum),
        )
        session.add(projection)
        return projection

    @staticmethod
    def _balance_cache_key(account_id: str) -> str:
        return f"wallet:balance:{account_id}"

    @staticmethod
    def _wallet_summary_cache_key(user_id: str, currency: LedgerUnit) -> str:
        return HotPathCache.wallet_key(user_id, currency.value)

    @staticmethod
    def _session_has_pending_state(session: Session) -> bool:
        return bool(session.new or session.dirty or session.deleted)

    @staticmethod
    def _normalize_idempotency_key(value: str | None) -> str | None:
        if value is None:
            return None
        candidate = value.strip()
        return candidate or None

    @staticmethod
    def _supports_row_locks(session: Session) -> bool:
        bind = session.get_bind()
        if bind is None:
            return False
        return bind.dialect.name != "sqlite"

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _user_account_code(user_id: str, unit: LedgerUnit) -> str:
        return f"user:{user_id}:{unit.value}"

    @staticmethod
    def _position_account_code(user_id: str, player_id: str) -> str:
        return f"position:{user_id}:{player_id}:available"

    @staticmethod
    def _position_escrow_account_code(user_id: str, player_id: str) -> str:
        return f"position:{user_id}:{player_id}:escrow"

    @staticmethod
    def _platform_position_account_code(player_id: str) -> str:
        return f"platform:position:{player_id}:inventory"

    def _get_user_account_balance_by_kind(
        self,
        session: Session,
        user: User,
        unit: LedgerUnit,
        kind: LedgerAccountKind,
    ) -> Decimal:
        account = session.scalar(
            select(LedgerAccount).where(
                LedgerAccount.owner_user_id == user.id,
                LedgerAccount.unit == unit,
                LedgerAccount.kind == kind,
            )
        )
        if account is None:
            return Decimal("0.0000")
        return self.get_balance(session, account)

    @staticmethod
    def _user_escrow_account_code(user_id: str, unit: LedgerUnit) -> str:
        return f"user:{user_id}:{unit.value}:escrow"
