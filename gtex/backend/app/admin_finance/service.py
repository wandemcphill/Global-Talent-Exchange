from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hmac
from hashlib import sha256, sha512
import json
import logging
import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.economy.governor_service import EconomyGovernorService
from app.models.competition_reward_pool import CompetitionRewardPool
from app.models.economy_burn_event import EconomyBurnEvent
from app.models.economy_daily_stat import EconomyDailyStat
from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.player_cards import PlayerCardMomentum
from app.models.risk_ops import SystemEvent, SystemEventSeverity
from app.models.treasury import (
    DepositRequest,
    DepositStatus,
    KycProfile,
    TreasuryWithdrawalRequest,
    TreasuryWithdrawalStatus,
)
from app.models.user import KycStatus, User
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntry,
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerUnit,
    PaymentEvent,
    PaymentStatus,
)
from app.services.payment_gateway_service import PaymentGatewayService
from app.treasury.service import TreasuryService
from app.wallets.providers.base import ProviderEventType
from app.wallets.providers.korapay import KoraPayProviderAdapter
from app.wallets.providers.paystack import PaystackProviderAdapter
from app.wallets.rail_service import WalletRailService
from app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
logger = logging.getLogger(__name__)


def _zero() -> Decimal:
    return Decimal("0.0000")


@dataclass(slots=True)
class AdminFinanceService:
    session: Session
    settings: object | None = None
    wallet_service: WalletService | None = None
    treasury_service: TreasuryService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()
        if self.treasury_service is None:
            self.treasury_service = TreasuryService(wallet_service=self.wallet_service)

    def get_control_tower_snapshot(
        self,
        *,
        history_days: int = 30,
        transaction_limit: int = 12,
    ) -> dict[str, object]:
        today = datetime.now(timezone.utc).date()
        history = [
            self.refresh_daily_stat(today - timedelta(days=offset)) for offset in range(history_days - 1, -1, -1)
        ]
        today_stat = history[-1]
        gtex_ratio = self._ratio(today_stat.gtex_burned, today_stat.gtex_minted)
        fan_ratio = self._ratio(today_stat.fan_burned, today_stat.fan_minted)
        inflation_risk = self._classify_inflation_risk(
            gtex_minted=today_stat.gtex_minted,
            gtex_burned=today_stat.gtex_burned,
            fan_minted=today_stat.fan_minted,
            fan_burned=today_stat.fan_burned,
        )
        projection = self.simulate(days=30, config={})
        return {
            "generated_at": datetime.now(timezone.utc),
            "gtex_supply": today_stat.gtex_supply,
            "fan_supply": today_stat.fan_supply,
            "daily_revenue_naira": today_stat.revenue_naira,
            "marketplace_fee_amount": today_stat.marketplace_fee_amount,
            "fan_coin_burned_today": today_stat.fan_burned,
            "gtex_minted_today": today_stat.gtex_minted,
            "gtex_burned_today": today_stat.gtex_burned,
            "fan_minted_today": today_stat.fan_minted,
            "fan_burned_today": today_stat.fan_burned,
            "gtex_burn_mint_ratio": gtex_ratio,
            "fan_burn_mint_ratio": fan_ratio,
            "inflation_risk": inflation_risk,
            "liquidity_status": self._liquidity_status(),
            "user_spend_trend": self._user_spend_trend(history),
            "avg_spend_per_match": self._average_match_spend(today_stat),
            "pending_purchase_orders": self._count_pending_purchase_orders(),
            "pending_withdrawals": self._count_pending_withdrawals(),
            "pending_kyc": self._count_pending_kyc(),
            "history": history,
            "top_transactions": self._list_large_transactions(limit=transaction_limit),
            "alerts": self._build_alerts(today_stat=today_stat, inflation_risk=inflation_risk),
            "player_price_trends": self._player_price_trends(),
            "tournament_pool_sizes": self._tournament_pool_sizes(),
            "cash_rails": self._cash_rail_summary(),
            "projection": projection["summary"],
        }

    def refresh_daily_stat(self, stat_date: date) -> EconomyDailyStat:
        start = datetime.combine(stat_date, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        row = self.session.get(EconomyDailyStat, stat_date)
        if row is None:
            row = EconomyDailyStat(date=stat_date)
            self.session.add(row)

        row.gtex_minted = self._sum_user_credits(unit=LedgerUnit.COIN, start=start, end=end)
        row.gtex_burned = self._sum_burn_account(unit=LedgerUnit.COIN, start=start, end=end)
        row.fan_minted = self._sum_user_credits(unit=LedgerUnit.CREDIT, start=start, end=end)
        row.fan_burned = self._sum_burn_events(start=start, end=end)
        row.revenue_naira = self._sum_revenue_naira(start=start, end=end)
        row.marketplace_fee_amount = self._sum_marketplace_fee_amount(start=start, end=end)
        row.match_spend_amount = self._sum_match_spend(start=start, end=end)
        row.tournament_pool_amount = self._sum_tournament_pool_amount(start=start, end=end)
        row.gtex_supply = self._supply_as_of(unit=LedgerUnit.COIN, end=end)
        row.fan_supply = self._supply_as_of(unit=LedgerUnit.CREDIT, end=end)
        row.metadata_json = {
            "match_entry_count": self._count_match_entries(start=start, end=end),
            "pending_purchase_orders": self._count_pending_purchase_orders(),
            "pending_withdrawals": self._count_pending_withdrawals(),
        }
        self.session.flush()
        return row

    def simulate(self, *, days: int, config: dict[str, object]) -> dict[str, object]:
        config_values = {
            "daily_active_users": int(config.get("daily_active_users", 100_000) or 100_000),
            "avg_matches_per_user": self._amount(config.get("avg_matches_per_user", "5.0000")),
            "fan_spend_per_match": self._amount(config.get("fan_spend_per_match", "10.0000")),
            "fan_mint_per_match": self._amount(config.get("fan_mint_per_match", "0.0000")),
            "gtex_purchase_rate": self._amount(config.get("gtex_purchase_rate", "0.0200")),
            "gtex_purchase_amount": self._amount(config.get("gtex_purchase_amount", "1.0000")),
            "tournament_entry_gtex": self._amount(config.get("tournament_entry_gtex", "2.0000")),
            "tournament_participation_rate": self._amount(config.get("tournament_participation_rate", "0.1200")),
            "gtex_reward_payout_per_match": self._amount(config.get("gtex_reward_payout_per_match", "0.0000")),
        }
        gtex_supply = self._supply_as_of(unit=LedgerUnit.COIN, end=None)
        fan_supply = self._supply_as_of(unit=LedgerUnit.CREDIT, end=None)
        starting_gtex_supply = gtex_supply
        starting_fan_supply = fan_supply
        points: list[dict[str, object]] = []
        for day in range(1, max(1, int(days)) + 1):
            matches = Decimal(config_values["daily_active_users"]) * config_values["avg_matches_per_user"]
            participants = Decimal(config_values["daily_active_users"]) * config_values["tournament_participation_rate"]
            gtex_minted = (
                Decimal(config_values["daily_active_users"])
                * config_values["gtex_purchase_rate"]
                * config_values["gtex_purchase_amount"]
            )
            gtex_burned = participants * config_values["tournament_entry_gtex"]
            fan_minted = matches * config_values["fan_mint_per_match"]
            fan_burned = matches * config_values["fan_spend_per_match"]
            gtex_reward = matches * config_values["gtex_reward_payout_per_match"]

            gtex_supply = self._amount(gtex_supply + gtex_minted + gtex_reward - gtex_burned)
            fan_supply = self._amount(fan_supply + fan_minted - fan_burned)
            risk = self._classify_inflation_risk(
                gtex_minted=self._amount(gtex_minted + gtex_reward),
                gtex_burned=self._amount(gtex_burned),
                fan_minted=self._amount(fan_minted),
                fan_burned=self._amount(fan_burned),
            )
            points.append(
                {
                    "day": day,
                    "gtex_supply": gtex_supply,
                    "fan_supply": fan_supply,
                    "gtex_minted": self._amount(gtex_minted + gtex_reward),
                    "gtex_burned": self._amount(gtex_burned),
                    "fan_minted": self._amount(fan_minted),
                    "fan_burned": self._amount(fan_burned),
                    "gtex_burn_mint_ratio": self._ratio(
                        self._amount(gtex_burned), self._amount(gtex_minted + gtex_reward)
                    ),
                    "fan_burn_mint_ratio": self._ratio(self._amount(fan_burned), self._amount(fan_minted)),
                    "inflation_risk": risk,
                }
            )

        recommendations: list[str] = []
        summary_risk = points[-1]["inflation_risk"]
        if summary_risk == "HIGH":
            recommendations.append("Increase tournament entry fees or reduce GTex reward emissions.")
            recommendations.append("Increase Fan Coin burn sinks before the next content cycle.")
        elif summary_risk == "MEDIUM":
            recommendations.append("Monitor mint velocity and stage a burn-focused event within 7 days.")
        else:
            recommendations.append("Economy remains stable under the simulated assumptions.")
        return {
            "days": max(1, int(days)),
            "starting_gtex_supply": starting_gtex_supply,
            "starting_fan_supply": starting_fan_supply,
            "summary": {
                "days": max(1, int(days)),
                "ending_gtex_supply": gtex_supply,
                "ending_fan_supply": fan_supply,
                "gtex_burn_mint_ratio": points[-1]["gtex_burn_mint_ratio"],
                "fan_burn_mint_ratio": points[-1]["fan_burn_mint_ratio"],
                "inflation_risk": summary_risk,
                "recommendations": recommendations,
            },
            "projections": points,
        }

    def handle_paystack_webhook(
        self,
        payload: dict[str, object],
        *,
        raw_body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, object]:
        signature_verified = self.verify_provider_webhook(
            provider_key="paystack",
            payload=payload,
            raw_body=raw_body,
            headers=headers,
        )
        adapter = PaystackProviderAdapter()
        event = adapter.parse_webhook(payload, headers=None)
        if event is None:
            return {"status": "ignored", "provider": "paystack", "signature_verified": signature_verified}

        return self._handle_provider_event(event=event, provider="paystack", signature_verified=signature_verified)

    def handle_korapay_webhook(
        self,
        payload: dict[str, object],
        *,
        raw_body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, object]:
        signature_verified = self.verify_provider_webhook(
            provider_key="korapay",
            payload=payload,
            raw_body=raw_body,
            headers=headers,
        )
        adapter = KoraPayProviderAdapter()
        event = adapter.parse_webhook(payload, headers=None)
        if event is None:
            return {"status": "ignored", "provider": "korapay", "signature_verified": signature_verified}

        return self._handle_provider_event(event=event, provider="korapay", signature_verified=signature_verified)

    def verify_provider_webhook(
        self,
        *,
        provider_key: str,
        payload: dict[str, object],
        raw_body: bytes | None,
        headers: dict[str, str] | None,
    ) -> bool:
        normalized_provider = provider_key.strip().lower()
        normalized_headers = {str(key).lower(): str(value).strip() for key, value in (headers or {}).items()}
        if normalized_provider == "paystack":
            return self._verify_paystack_webhook(raw_body=raw_body, headers=normalized_headers)
        if normalized_provider == "korapay":
            return self._verify_korapay_webhook(payload=payload, headers=normalized_headers)
        return False

    def wallet_protection_summary(
        self,
        *,
        frozen_wallet_account_count: int = 0,
        active_wallet_transaction_locks: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        rows = self.session.execute(
            select(
                FancoinPurchaseOrder.provider_key,
                FancoinPurchaseOrder.provider_reference,
                func.count(FancoinPurchaseOrder.id),
            )
            .where(FancoinPurchaseOrder.provider_reference.is_not(None))
            .group_by(FancoinPurchaseOrder.provider_key, FancoinPurchaseOrder.provider_reference)
            .having(func.count(FancoinPurchaseOrder.id) > 1)
            .order_by(func.count(FancoinPurchaseOrder.id).desc(), FancoinPurchaseOrder.provider_reference.asc())
            .limit(10)
        ).all()
        duplicate_candidates: list[dict[str, object]] = []
        for provider_key, provider_reference, occurrence_count in rows:
            order_ids = list(
                self.session.scalars(
                    select(FancoinPurchaseOrder.id)
                    .where(
                        FancoinPurchaseOrder.provider_key == provider_key,
                        FancoinPurchaseOrder.provider_reference == provider_reference,
                    )
                    .order_by(FancoinPurchaseOrder.created_at.asc())
                ).all()
            )
            duplicate_candidates.append(
                {
                    "provider_key": str(provider_key),
                    "provider_reference": str(provider_reference),
                    "occurrence_count": int(occurrence_count or 0),
                    "order_ids": order_ids,
                }
            )
        return {
            "generated_at": datetime.now(timezone.utc),
            "frozen_wallet_account_count": int(frozen_wallet_account_count),
            "banned_account_count": self.count_banned_accounts(),
            "pending_purchase_orders": self._count_pending_purchase_orders(),
            "pending_withdrawals": self._count_pending_withdrawals(),
            "active_wallet_transaction_lock_count": len(active_wallet_transaction_locks or []),
            "payment_signature_verification_enabled": bool(self._provider_secret("korapay")),
            "active_wallet_transaction_locks": list(active_wallet_transaction_locks or []),
            "duplicate_deposit_candidates": duplicate_candidates,
        }

    def count_banned_accounts(self) -> int:
        count = self.session.scalar(select(func.count(User.id)).where(User.is_active.is_(False)))
        return int(count or 0)

    def payment_reconciliation_summary(self, *, issue_limit: int = 25) -> dict[str, object]:
        issues: list[dict[str, object]] = []
        settled_purchase_order_rows = self.session.scalars(
            select(FancoinPurchaseOrder)
            .where(
                FancoinPurchaseOrder.status == PurchaseOrderStatus.SETTLED,
                FancoinPurchaseOrder.ledger_transaction_id.is_(None),
            )
            .order_by(FancoinPurchaseOrder.updated_at.desc(), FancoinPurchaseOrder.created_at.desc())
            .limit(issue_limit)
        ).all()
        for item in settled_purchase_order_rows:
            issues.append(
                {
                    "issue_type": "settled_purchase_order_missing_ledger",
                    "resource_id": item.id,
                    "reference": item.reference,
                    "detail": "Purchase order is settled but has no linked ledger transaction.",
                }
            )

        settled_payment_event_rows = self.session.scalars(
            select(PaymentEvent)
            .where(
                PaymentEvent.status == PaymentStatus.VERIFIED,
                PaymentEvent.ledger_transaction_id.is_(None),
            )
            .order_by(PaymentEvent.updated_at.desc(), PaymentEvent.created_at.desc())
            .limit(issue_limit)
        ).all()
        for item in settled_payment_event_rows:
            issues.append(
                {
                    "issue_type": "verified_payment_event_missing_ledger",
                    "resource_id": item.id,
                    "reference": item.provider_reference,
                    "detail": "Payment event is verified but has no linked ledger transaction.",
                }
            )

        confirmed_deposit_rows = self.session.scalars(
            select(DepositRequest)
            .where(
                DepositRequest.status == DepositStatus.CONFIRMED,
                DepositRequest.ledger_transaction_id.is_(None),
            )
            .order_by(DepositRequest.updated_at.desc(), DepositRequest.created_at.desc())
            .limit(issue_limit)
        ).all()
        for item in confirmed_deposit_rows:
            issues.append(
                {
                    "issue_type": "confirmed_deposit_missing_ledger",
                    "resource_id": item.id,
                    "reference": item.reference,
                    "detail": "Deposit request is confirmed but has no linked ledger transaction.",
                }
            )

        duplicate_reference_groups = self.session.execute(
            select(
                FancoinPurchaseOrder.provider_key,
                FancoinPurchaseOrder.provider_reference,
                func.count(FancoinPurchaseOrder.id),
            )
            .where(FancoinPurchaseOrder.provider_reference.is_not(None))
            .group_by(FancoinPurchaseOrder.provider_key, FancoinPurchaseOrder.provider_reference)
            .having(func.count(FancoinPurchaseOrder.id) > 1)
            .order_by(func.count(FancoinPurchaseOrder.id).desc())
            .limit(issue_limit)
        ).all()
        for provider_key, provider_reference, occurrence_count in duplicate_reference_groups:
            issues.append(
                {
                    "issue_type": "duplicate_provider_reference",
                    "resource_id": f"{provider_key}:{provider_reference}",
                    "reference": str(provider_reference),
                    "detail": f"Provider reference appears on {int(occurrence_count or 0)} purchase orders.",
                }
            )

        return {
            "generated_at": datetime.now(timezone.utc),
            "pending_payment_events": int(
                self.session.scalar(
                    select(func.count()).select_from(PaymentEvent).where(PaymentEvent.status == PaymentStatus.PENDING)
                )
                or 0
            ),
            "settled_purchase_orders_missing_ledger": int(
                self.session.scalar(
                    select(func.count())
                    .select_from(FancoinPurchaseOrder)
                    .where(
                        FancoinPurchaseOrder.status == PurchaseOrderStatus.SETTLED,
                        FancoinPurchaseOrder.ledger_transaction_id.is_(None),
                    )
                )
                or 0
            ),
            "settled_payment_events_missing_ledger": int(
                self.session.scalar(
                    select(func.count())
                    .select_from(PaymentEvent)
                    .where(
                        PaymentEvent.status == PaymentStatus.VERIFIED,
                        PaymentEvent.ledger_transaction_id.is_(None),
                    )
                )
                or 0
            ),
            "confirmed_deposits_missing_ledger": int(
                self.session.scalar(
                    select(func.count())
                    .select_from(DepositRequest)
                    .where(
                        DepositRequest.status == DepositStatus.CONFIRMED,
                        DepositRequest.ledger_transaction_id.is_(None),
                    )
                )
                or 0
            ),
            "duplicate_provider_references": len(duplicate_reference_groups),
            "issues": issues[:issue_limit],
        }

    def governor_snapshot(self) -> dict[str, object]:
        return EconomyGovernorService(self.session).snapshot()

    def _handle_provider_event(
        self,
        *,
        event,
        provider: str,
        signature_verified: bool,
    ) -> dict[str, object]:
        if event.event_type in {
            ProviderEventType.CREATED,
            ProviderEventType.AUTHORIZED,
            ProviderEventType.PENDING,
            ProviderEventType.CAPTURED,
            ProviderEventType.SETTLED,
            ProviderEventType.FAILED,
            ProviderEventType.CANCELLED,
            ProviderEventType.REFUNDED,
            ProviderEventType.CHARGEBACK,
            ProviderEventType.REVERSED,
            ProviderEventType.DISPUTED,
        }:
            rail_service = WalletRailService(self.session, wallet_service=self.wallet_service)
            order = rail_service.handle_provider_event(event=event)
            return {
                "status": "ok" if order is not None else "ignored",
                "provider": provider,
                "purchase_order_id": None if order is None else order.id,
                "order_status": None if order is None else order.status.value,
                "reference": event.provider_reference,
                "signature_verified": signature_verified,
            }

        return {
            "status": "ignored",
            "provider": provider,
            "reference": event.provider_reference,
            "signature_verified": signature_verified,
        }

    def _verify_paystack_webhook(self, *, raw_body: bytes | None, headers: dict[str, str]) -> bool:
        secret = self._provider_secret("paystack")
        if not secret:
            if self._signature_optional("paystack"):
                logger.warning(
                    "Paystack webhook received without GTE_PAYSTACK_WEBHOOK_SECRET. "
                    "Continuing without signature verification because "
                    "GTE_PAYSTACK_WEBHOOK_SIGNATURE_OPTIONAL=true."
                )
                return False
            raise ValueError("Paystack webhook cannot be verified: GTE_PAYSTACK_WEBHOOK_SECRET is not configured.")
        signature = headers.get("x-paystack-signature")
        if not signature:
            raise ValueError("Paystack webhook signature header (x-paystack-signature) is missing.")
        if raw_body is None:
            raise ValueError("Paystack webhook raw body is missing.")
        expected = hmac.new(secret.encode("utf-8"), raw_body, sha512).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Paystack webhook signature is invalid.")
        return True

    def _verify_korapay_webhook(self, *, payload: dict[str, object], headers: dict[str, str]) -> bool:
        secret = self._provider_secret("korapay")
        if not secret:
            if self._signature_optional("korapay"):
                logger.warning(
                    "KoraPay webhook received without GTE_KORAPAY_WEBHOOK_SECRET. "
                    "Continuing without signature verification because "
                    "GTE_KORAPAY_WEBHOOK_SIGNATURE_OPTIONAL=true."
                )
                return False
            raise ValueError("KoraPay webhook cannot be verified: GTE_KORAPAY_WEBHOOK_SECRET is not configured.")
        signature = headers.get("x-korapay-signature")
        data = payload.get("data")
        if not signature:
            raise ValueError("KoraPay webhook signature header (x-korapay-signature) is missing.")
        if not isinstance(data, dict):
            raise ValueError("KoraPay webhook payload.data is missing or invalid.")
        canonical_payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), canonical_payload, sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ValueError("KoraPay webhook signature is invalid.")
        return True

    @staticmethod
    def _provider_secret(provider_key: str) -> str | None:
        normalized_provider = provider_key.strip().upper()
        env_names = [
            f"GTE_{normalized_provider}_WEBHOOK_SECRET",
            f"{normalized_provider}_WEBHOOK_SECRET",
        ]
        if normalized_provider == "KORAPAY":
            env_names.extend(
                [
                    "GTE_KORAPAY_ENCRYPTION_KEY",
                    "KORAPAY_ENCRYPTION_KEY",
                ]
            )
        for name in env_names:
            secret = os.getenv(name)
            if secret and secret.strip():
                return secret.strip()
        return None

    def _signature_optional(self, provider_key: str) -> bool:
        if self._is_protected_environment():
            return False
        raw_value = os.getenv(f"GTE_{provider_key.strip().upper()}_WEBHOOK_SIGNATURE_OPTIONAL", "")
        return raw_value.strip().lower() in {"true", "1", "yes"}

    def _is_protected_environment(self) -> bool:
        settings_env = getattr(self.settings, "app_env", None)
        environment = (
            (settings_env or os.getenv("GTE_APP_ENV") or os.getenv("APP_ENV") or "development").strip().lower()
        )
        return environment in {"production", "prod", "staging", "release"}

    def _sum_user_credits(self, *, unit: LedgerUnit, start: datetime, end: datetime) -> Decimal:
        amount = self.session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.kind.in_([LedgerAccountKind.USER, LedgerAccountKind.ESCROW]),
                LedgerAccount.unit == unit,
                LedgerEntry.amount > 0,
                LedgerEntry.created_at >= start,
                LedgerEntry.created_at < end,
            )
        )
        return self._amount(amount)

    def _sum_burn_account(self, *, unit: LedgerUnit, start: datetime, end: datetime) -> Decimal:
        amount = self.session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.code == f"platform:{unit.value}:burn",
                LedgerEntry.amount > 0,
                LedgerEntry.created_at >= start,
                LedgerEntry.created_at < end,
            )
        )
        return self._amount(amount)

    def _sum_burn_events(self, *, start: datetime, end: datetime) -> Decimal:
        amount = self.session.scalar(
            select(func.coalesce(func.sum(EconomyBurnEvent.amount), 0)).where(
                EconomyBurnEvent.unit == LedgerUnit.CREDIT,
                EconomyBurnEvent.created_at >= start,
                EconomyBurnEvent.created_at < end,
            )
        )
        return self._amount(amount)

    def _sum_revenue_naira(self, *, start: datetime, end: datetime) -> Decimal:
        purchase_orders = self.session.scalar(
            select(func.coalesce(func.sum(FancoinPurchaseOrder.amount_fiat), 0)).where(
                FancoinPurchaseOrder.status == PurchaseOrderStatus.SETTLED,
                FancoinPurchaseOrder.settled_at >= start,
                FancoinPurchaseOrder.settled_at < end,
            )
        )
        manual_deposits = self.session.scalar(
            select(func.coalesce(func.sum(DepositRequest.amount_fiat), 0)).where(
                DepositRequest.status == DepositStatus.CONFIRMED,
                DepositRequest.confirmed_at >= start,
                DepositRequest.confirmed_at < end,
            )
        )
        return self._amount(purchase_orders) + self._amount(manual_deposits)

    def _sum_marketplace_fee_amount(self, *, start: datetime, end: datetime) -> Decimal:
        amount = self.session.scalar(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.kind == LedgerAccountKind.SYSTEM,
                LedgerEntry.amount > 0,
                LedgerEntry.created_at >= start,
                LedgerEntry.created_at < end,
                LedgerEntry.source_tag.in_(
                    [
                        LedgerSourceTag.CLUB_SALE_PLATFORM_FEE,
                        LedgerSourceTag.PLAYER_CARD_SALE,
                        LedgerSourceTag.PLAYER_CARD_PURCHASE,
                    ]
                ),
            )
        )
        return self._amount(amount)

    def _sum_match_spend(self, *, start: datetime, end: datetime) -> Decimal:
        amount = self.session.scalar(
            select(func.coalesce(func.sum(func.abs(LedgerEntry.amount)), 0))
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.kind == LedgerAccountKind.USER,
                LedgerEntry.reason == LedgerEntryReason.COMPETITION_ENTRY,
                LedgerEntry.amount < 0,
                LedgerEntry.created_at >= start,
                LedgerEntry.created_at < end,
            )
        )
        return self._amount(amount)

    def _count_match_entries(self, *, start: datetime, end: datetime) -> int:
        count = self.session.scalar(
            select(func.count(LedgerEntry.id))
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.kind == LedgerAccountKind.USER,
                LedgerEntry.reason == LedgerEntryReason.COMPETITION_ENTRY,
                LedgerEntry.amount < 0,
                LedgerEntry.created_at >= start,
                LedgerEntry.created_at < end,
            )
        )
        return int(count or 0)

    def _sum_tournament_pool_amount(self, *, start: datetime, end: datetime) -> Decimal:
        amount_minor = self.session.scalar(
            select(func.coalesce(func.sum(CompetitionRewardPool.amount_minor), 0)).where(
                CompetitionRewardPool.updated_at >= start,
                CompetitionRewardPool.updated_at < end,
            )
        )
        return self._amount(Decimal(amount_minor or 0) / Decimal("100.0000"))

    def _supply_as_of(self, *, unit: LedgerUnit, end: datetime | None) -> Decimal:
        statement = (
            select(func.coalesce(func.sum(LedgerEntry.amount), 0))
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(
                LedgerAccount.kind.in_([LedgerAccountKind.USER, LedgerAccountKind.ESCROW]),
                LedgerAccount.unit == unit,
            )
        )
        if end is not None:
            statement = statement.where(LedgerEntry.created_at < end)
        return self._amount(self.session.scalar(statement))

    def _list_large_transactions(self, *, limit: int) -> list[dict[str, object]]:
        rows = self.session.execute(
            select(LedgerEntry, LedgerAccount)
            .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
            .where(func.abs(LedgerEntry.amount) >= Decimal("250.0000"))
            .order_by(LedgerEntry.created_at.desc())
            .limit(limit)
        ).all()
        return [
            {
                "transaction_id": entry.transaction_id,
                "reference": entry.reference,
                "account_code": account.code,
                "unit": entry.unit.value if hasattr(entry.unit, "value") else str(entry.unit),
                "amount": self._amount(entry.amount),
                "reason": entry.reason.value if hasattr(entry.reason, "value") else str(entry.reason),
                "source_tag": entry.source_tag.value if hasattr(entry.source_tag, "value") else str(entry.source_tag),
                "created_at": entry.created_at,
            }
            for entry, account in rows
        ]

    def _build_alerts(self, *, today_stat: EconomyDailyStat, inflation_risk: str) -> list[dict[str, object]]:
        alerts: list[dict[str, object]] = []
        if inflation_risk == "HIGH":
            alerts.append(
                {
                    "level": "critical",
                    "title": "Inflation risk high",
                    "message": "Minting is materially ahead of burn across the economy today.",
                    "metric_key": "inflation_risk",
                    "created_at": datetime.now(timezone.utc),
                }
            )
        elif inflation_risk == "MEDIUM":
            alerts.append(
                {
                    "level": "warning",
                    "title": "Inflation watch",
                    "message": "Minting is ahead of burn and should be monitored before the next reward cycle.",
                    "metric_key": "inflation_risk",
                    "created_at": datetime.now(timezone.utc),
                }
            )
        if today_stat.revenue_naira <= _zero():
            alerts.append(
                {
                    "level": "warning",
                    "title": "Revenue is flat",
                    "message": "No NGN revenue has been recorded today across settled purchase orders.",
                    "metric_key": "daily_revenue_naira",
                    "created_at": datetime.now(timezone.utc),
                }
            )
        system_events = self.session.scalars(
            select(SystemEvent)
            .where(
                SystemEvent.severity.in_(
                    [SystemEventSeverity.WARNING, SystemEventSeverity.ERROR, SystemEventSeverity.CRITICAL]
                ),
                SystemEvent.subject_type.in_(["purchase_order", "treasury_withdrawal"]),
            )
            .order_by(SystemEvent.created_at.desc())
            .limit(4)
        ).all()
        alerts.extend(
            {
                "level": event.severity.value if hasattr(event.severity, "value") else str(event.severity),
                "title": event.title,
                "message": event.body,
                "metric_key": event.subject_type or "system_event",
                "created_at": event.created_at,
            }
            for event in system_events
        )
        return alerts

    def _player_price_trends(self) -> list[dict[str, object]]:
        rows = self.session.scalars(
            select(PlayerCardMomentum)
            .order_by(func.abs(PlayerCardMomentum.momentum_7d_pct).desc(), PlayerCardMomentum.updated_at.desc())
            .limit(6)
        ).all()
        return [
            {
                "player_id": row.player_id,
                "trend_direction": row.trend_direction,
                "momentum_7d_pct": self._amount(row.momentum_7d_pct),
                "momentum_30d_pct": self._amount(row.momentum_30d_pct),
                "last_trade_price_credits": (
                    None if row.last_trade_price_credits is None else self._amount(row.last_trade_price_credits)
                ),
            }
            for row in rows
        ]

    def _tournament_pool_sizes(self) -> list[dict[str, object]]:
        rows = self.session.scalars(
            select(CompetitionRewardPool)
            .order_by(CompetitionRewardPool.amount_minor.desc(), CompetitionRewardPool.updated_at.desc())
            .limit(6)
        ).all()
        return [
            {
                "competition_id": row.competition_id,
                "pool_type": row.pool_type,
                "currency": row.currency,
                "amount": self._amount(Decimal(row.amount_minor) / Decimal("100.0000")),
                "status": row.status,
            }
            for row in rows
        ]

    def _cash_rail_summary(self) -> dict[str, object]:
        settings = self.treasury_service.ensure_settings(self.session)
        methods: list[str] = []
        if self.settings is not None:
            methods = [
                method.display_name
                for method in PaymentGatewayService(session=self.session, settings=self.settings).list_methods()
            ]
        return {
            "payment_methods": methods,
            "deposit_mode": (
                settings.deposit_mode.value if hasattr(settings.deposit_mode, "value") else str(settings.deposit_mode)
            ),
            "withdrawal_mode": (
                settings.withdrawal_mode.value
                if hasattr(settings.withdrawal_mode, "value")
                else str(settings.withdrawal_mode)
            ),
            "currency_code": settings.currency_code,
            "min_withdrawal": self._amount(settings.min_withdrawal),
            "max_withdrawal": self._amount(settings.max_withdrawal),
            "pending_purchase_orders": self._count_pending_purchase_orders(),
            "pending_withdrawals": self._count_pending_withdrawals(),
            "pending_kyc": self._count_pending_kyc(),
            "automatic_deposits_enabled": getattr(settings.deposit_mode, "value", str(settings.deposit_mode))
            in {"automatic", "hybrid"},
            "automatic_withdrawals_enabled": getattr(settings.withdrawal_mode, "value", str(settings.withdrawal_mode))
            in {"automatic", "hybrid"},
        }

    def _count_pending_purchase_orders(self) -> int:
        count = self.session.scalar(
            select(func.count(FancoinPurchaseOrder.id)).where(
                FancoinPurchaseOrder.status.in_(
                    [PurchaseOrderStatus.REQUESTED, PurchaseOrderStatus.REVIEWING, PurchaseOrderStatus.PROCESSING]
                )
            )
        )
        return int(count or 0)

    def _count_pending_withdrawals(self) -> int:
        count = self.session.scalar(
            select(func.count(TreasuryWithdrawalRequest.id)).where(
                TreasuryWithdrawalRequest.status.in_(
                    [
                        TreasuryWithdrawalStatus.PENDING_REVIEW,
                        TreasuryWithdrawalStatus.APPROVED,
                        TreasuryWithdrawalStatus.PROCESSING,
                    ]
                )
            )
        )
        return int(count or 0)

    def _count_pending_kyc(self) -> int:
        count = self.session.scalar(
            select(func.count(KycProfile.id)).where(KycProfile.status.in_([KycStatus.PENDING, KycStatus.UNDER_REVIEW]))
        )
        return int(count or 0)

    def _liquidity_status(self) -> str:
        settings = self.treasury_service.ensure_settings(self.session)
        pending_payout_fiat = self.session.scalar(
            select(func.coalesce(func.sum(TreasuryWithdrawalRequest.amount_fiat), 0)).where(
                TreasuryWithdrawalRequest.status.in_(
                    [
                        TreasuryWithdrawalStatus.PENDING_REVIEW,
                        TreasuryWithdrawalStatus.APPROVED,
                        TreasuryWithdrawalStatus.PROCESSING,
                    ]
                )
            )
        )
        recent_revenue = self.session.scalar(
            select(func.coalesce(func.sum(FancoinPurchaseOrder.amount_fiat), 0)).where(
                FancoinPurchaseOrder.status == PurchaseOrderStatus.SETTLED,
                FancoinPurchaseOrder.settled_at >= datetime.now(timezone.utc) - timedelta(days=7),
            )
        )
        recent_manual_deposits = self.session.scalar(
            select(func.coalesce(func.sum(DepositRequest.amount_fiat), 0)).where(
                DepositRequest.status == DepositStatus.CONFIRMED,
                DepositRequest.confirmed_at >= datetime.now(timezone.utc) - timedelta(days=7),
            )
        )
        net = self._amount(recent_revenue) + self._amount(recent_manual_deposits) - self._amount(pending_payout_fiat)
        if net >= self._amount(settings.min_withdrawal or 0):
            return "HEALTHY"
        if net >= _zero():
            return "WATCH"
        return "TIGHT"

    def _user_spend_trend(self, history: list[EconomyDailyStat]) -> str:
        if len(history) < 14:
            return "FLAT"
        trailing = sum((self._amount(item.match_spend_amount) for item in history[-7:]), _zero())
        baseline = sum((self._amount(item.match_spend_amount) for item in history[-14:-7]), _zero())
        if trailing > baseline * Decimal("1.0500"):
            return "UP"
        if trailing < baseline * Decimal("0.9500"):
            return "DOWN"
        return "FLAT"

    def _average_match_spend(self, current_day: EconomyDailyStat) -> Decimal:
        count = int((current_day.metadata_json or {}).get("match_entry_count", 0) or 0)
        if count <= 0:
            return _zero()
        return self._amount(Decimal(current_day.match_spend_amount) / Decimal(count))

    def _ratio(self, burned: Decimal, minted: Decimal) -> Decimal | None:
        burned = self._amount(burned)
        minted = self._amount(minted)
        if minted <= _zero():
            return None
        return self._amount(burned / minted)

    def _classify_inflation_risk(
        self,
        *,
        gtex_minted: Decimal,
        gtex_burned: Decimal,
        fan_minted: Decimal,
        fan_burned: Decimal,
    ) -> str:
        risk_scores = [
            self._risk_score(self._amount(gtex_minted), self._amount(gtex_burned)),
            self._risk_score(self._amount(fan_minted), self._amount(fan_burned)),
        ]
        highest = max(risk_scores)
        if highest >= 2:
            return "HIGH"
        if highest == 1:
            return "MEDIUM"
        return "LOW"

    def _risk_score(self, minted: Decimal, burned: Decimal) -> int:
        if minted <= _zero():
            return 0
        if burned <= _zero():
            return 2
        if minted > burned * Decimal("2.0000"):
            return 2
        if minted > burned * Decimal("1.1000"):
            return 1
        return 0

    @staticmethod
    def _amount(value: object | None) -> Decimal:
        if value is None:
            return _zero()
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)


__all__ = ["AdminFinanceService"]
