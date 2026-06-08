from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import hmac
from io import StringIO
from hashlib import sha256
import json
import logging
import os
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.economy.governor_service import EconomyGovernorService
from app.models.competition_reward_pool import CompetitionRewardPool
from app.models.creator_monetization import CreatorRevenueSettlement
from app.models.economy_burn_event import EconomyBurnEvent
from app.models.economy_daily_stat import EconomyDailyStat
from app.models.event_backbone import EventOutbox
from app.models.fancoin_purchase_order import FancoinPurchaseOrder, PurchaseOrderStatus
from app.models.player_cards import PlayerCardMomentum
from app.models.reward_settlement import RewardSettlement
from app.models.risk_ops import (
    AmlCase,
    FraudCase,
    RiskAction,
    RiskSignal,
    SystemEvent,
    SystemEventSeverity,
)
from app.models.treasury import (
    DepositRequest,
    DepositStatus,
    KycProfile,
    TreasuryAuditEvent,
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
from app.wallets.rail_service import WalletRailService
from app.wallets.service import WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
logger = logging.getLogger(__name__)
CANONICAL_CASH_RAIL_METHODS: dict[str, str] = {
    "bank_transfer_manual": "Manual bank transfer",
    "korapay": "KoraPay",
}
PAYMENT_QUEUE_PENDING_DEPOSIT_STATUSES = (
    DepositStatus.PAYMENT_SUBMITTED,
    DepositStatus.UNDER_REVIEW,
    DepositStatus.DISPUTED,
)
PAYMENT_QUEUE_APPROVED_DEPOSIT_STATUSES = (DepositStatus.CONFIRMED,)
PAYMENT_QUEUE_REJECTED_DEPOSIT_STATUSES = (DepositStatus.REJECTED,)
PAYMENT_QUEUE_TABS = ("pending", "approved", "rejected", "bids")
PAYMENT_QUEUE_BID_ACTION_REASONS = {
    "approve": "admin_payment_queue_approve_requested",
    "reject": "admin_payment_queue_reject_requested",
    "counter": "admin_payment_queue_counter_requested",
}
PAYMENT_QUEUE_ACTION_LABELS = {
    "review": "Mark under review",
    "approve": "Approve",
    "reject": "Reject",
    "reinstate": "Reinstate",
    "counter": "Counter",
}
ADMIN_EXPORT_EVENT_REQUESTED = "admin.export.requested"
ADMIN_EXPORT_EVENT_READY = "admin.export.ready"
ADMIN_EXPORT_EVENT_BLOCKED = "admin.export.blocked"
ADMIN_EXPORT_EVENT_FAILED = "admin.export.failed"
ADMIN_BULK_ACTION_EVENT_REQUESTED = "admin.bulk_action.requested"
ADMIN_BULK_ACTION_EVENT_COMPLETED = "admin.bulk_action.completed"
ADMIN_EXPORT_BLOCKED_REASON = (
    "Admin finance export artifact generation is not configured; no finance export download was generated."
)
ADMIN_EXPORT_DOWNLOAD_BASE = "/api/v2/admin/finance/exports"
ADMIN_EXPORT_TYPES = {
    "treasury",
    "payment_proofs",
    "withdrawals",
    "settlements",
    "fraud",
    "audit_logs",
    "payment_queue",
}
ADMIN_BULK_RESOURCE_TYPES = {
    "deposit": "deposit_request",
    "payment_proof": "deposit_request",
    "withdrawal": "treasury_withdrawal",
}
ADMIN_EXPORT_GENERATOR_BLOCKED_REASONS: dict[str, str] = {}
ADMIN_EXPORT_DEFAULT_LIMIT = 500
ADMIN_EXPORT_MAX_LIMIT = 1000


def _zero() -> Decimal:
    return Decimal("0.0000")


class AdminExportBlockedError(ValueError):
    pass


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
        if normalized_provider == "korapay":
            return self._verify_korapay_webhook(payload=payload, headers=normalized_headers)
        raise ValueError("Unsupported payment webhook provider.")

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
            "payment_signature_verification_enabled": any(
                bool(self._provider_secret(provider)) for provider in ("korapay",)
            ),
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

    def get_admin_payment_queue(
        self,
        *,
        actor: User | None = None,
        tab: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        normalized_tab = self._normalize_payment_queue_tab(tab)
        sections = {
            "pending": self._deposit_queue_section(
                key="pending",
                label="Pending",
                statuses=PAYMENT_QUEUE_PENDING_DEPOSIT_STATUSES,
                include_items=normalized_tab in {None, "pending"},
                q=q,
                limit=limit,
                offset=offset,
                actor=actor,
            ),
            "approved": self._deposit_queue_section(
                key="approved",
                label="Approved",
                statuses=PAYMENT_QUEUE_APPROVED_DEPOSIT_STATUSES,
                include_items=normalized_tab in {None, "approved"},
                q=q,
                limit=limit,
                offset=offset,
                actor=actor,
            ),
            "rejected": self._deposit_queue_section(
                key="rejected",
                label="Rejected",
                statuses=PAYMENT_QUEUE_REJECTED_DEPOSIT_STATUSES,
                include_items=normalized_tab in {None, "rejected"},
                q=q,
                limit=limit,
                offset=offset,
                actor=actor,
            ),
            "bids": self._transfer_bid_queue_section(
                include_items=normalized_tab in {None, "bids"},
                q=q,
                limit=limit,
                offset=offset,
            ),
        }
        return {
            "generated_at": datetime.now(timezone.utc),
            "tabs": [
                {
                    "key": key,
                    "label": sections[key]["label"],
                    "total": sections[key]["total"],
                    "action_state": sections[key].get("action_state", "enabled"),
                }
                for key in PAYMENT_QUEUE_TABS
            ],
            "sections": sections,
            **sections,
        }

    def review_payment_queue_deposit(
        self,
        *,
        actor: User,
        deposit_id: str,
        admin_notes: str,
    ) -> dict[str, object]:
        deposit = self.treasury_service.mark_deposit_under_review(
            self.session,
            actor=actor,
            deposit_request_id=deposit_id,
            admin_notes=admin_notes,
        )
        return self._payment_queue_action_result(
            action="review",
            item_type="deposit",
            item=self._serialize_deposit_queue_item(deposit, "pending", actor=actor),
            business_state_changed=True,
            wallet_state_changed=False,
        )

    def approve_payment_queue_deposit(
        self,
        *,
        actor: User,
        deposit_id: str,
        admin_notes: str,
    ) -> dict[str, object]:
        deposit = self.treasury_service.confirm_deposit(
            self.session,
            actor=actor,
            deposit_request_id=deposit_id,
            admin_notes=admin_notes,
        )
        return self._payment_queue_action_result(
            action="approve",
            item_type="deposit",
            item=self._serialize_deposit_queue_item(deposit, "approved", actor=actor),
            business_state_changed=True,
            wallet_state_changed=True,
        )

    def reject_payment_queue_deposit(
        self,
        *,
        actor: User,
        deposit_id: str,
        admin_notes: str,
    ) -> dict[str, object]:
        deposit = self.treasury_service.reject_deposit(
            self.session,
            actor=actor,
            deposit_request_id=deposit_id,
            admin_notes=admin_notes,
        )
        return self._payment_queue_action_result(
            action="reject",
            item_type="deposit",
            item=self._serialize_deposit_queue_item(deposit, "rejected", actor=actor),
            business_state_changed=True,
            wallet_state_changed=False,
        )

    def reinstate_payment_queue_deposit(
        self,
        *,
        actor: User,
        deposit_id: str,
        admin_notes: str,
    ) -> dict[str, object]:
        deposit = self.treasury_service.mark_deposit_under_review(
            self.session,
            actor=actor,
            deposit_request_id=deposit_id,
            admin_notes=admin_notes,
        )
        return self._payment_queue_action_result(
            action="reinstate",
            item_type="deposit",
            item=self._serialize_deposit_queue_item(deposit, "pending", actor=actor),
            business_state_changed=True,
            wallet_state_changed=False,
        )

    def approve_payment_queue_withdrawal(
        self,
        *,
        actor: User,
        withdrawal_id: str,
        admin_notes: str,
    ) -> dict[str, object]:
        return self._review_payment_queue_withdrawal(
            actor=actor,
            withdrawal_id=withdrawal_id,
            action="approve",
            next_status=TreasuryWithdrawalStatus.APPROVED,
            admin_notes=admin_notes,
        )

    def reject_payment_queue_withdrawal(
        self,
        *,
        actor: User,
        withdrawal_id: str,
        admin_notes: str,
    ) -> dict[str, object]:
        return self._review_payment_queue_withdrawal(
            actor=actor,
            withdrawal_id=withdrawal_id,
            action="reject",
            next_status=TreasuryWithdrawalStatus.REJECTED,
            admin_notes=admin_notes,
        )

    def reinstate_payment_queue_withdrawal(
        self,
        *,
        actor: User,
        withdrawal_id: str,
        admin_notes: str,
    ) -> dict[str, object]:
        withdrawal = self.session.get(TreasuryWithdrawalRequest, withdrawal_id)
        if withdrawal is None:
            raise ValueError("Withdrawal request was not found.")
        if withdrawal.status in {
            TreasuryWithdrawalStatus.REJECTED,
            TreasuryWithdrawalStatus.CANCELLED,
            TreasuryWithdrawalStatus.PAID,
        }:
            raise ValueError("Rejected, cancelled, or paid withdrawals cannot be reinstated after funds move.")
        return self._review_payment_queue_withdrawal(
            actor=actor,
            withdrawal_id=withdrawal_id,
            action="reinstate",
            next_status=TreasuryWithdrawalStatus.PENDING_REVIEW,
            admin_notes=admin_notes,
        )

    def record_payment_queue_bid_action(
        self,
        *,
        actor: User,
        window_id: str,
        bid_id: str,
        action: str,
        admin_notes: str,
    ) -> dict[str, object]:
        normalized_action = action.strip().lower()
        if normalized_action not in PAYMENT_QUEUE_BID_ACTION_REASONS:
            raise ValueError("Bid action must be approve, reject, or counter.")

        from app.schemas.player_lifecycle import AdminTransferBidReviewActionRequest
        from app.services.player_lifecycle_service import (
            PlayerLifecycleNotFoundError,
            PlayerLifecycleService,
            PlayerLifecycleValidationError,
        )

        try:
            response = PlayerLifecycleService(self.session).record_admin_transfer_bid_review_action(
                window_id,
                bid_id,
                AdminTransferBidReviewActionRequest(
                    action="escalate",
                    reason=PAYMENT_QUEUE_BID_ACTION_REASONS[normalized_action],
                    notes=admin_notes,
                    escalation_state=f"{normalized_action}_requested",
                ),
                actor=actor,
            )
        except (PlayerLifecycleNotFoundError, PlayerLifecycleValidationError) as exc:
            raise ValueError(str(exc)) from exc

        payload = response.model_dump(mode="json")
        payload.update(
            {
                "action": normalized_action,
                "item_type": "transfer_bid",
                "audit_reference": f"transfer-bid:{bid_id}",
                "blocked_reason": (
                    "Transfer bid business mutations stay outside the admin payment queue; "
                    "this endpoint records the operator request for audit review only."
                ),
            }
        )
        return payload

    def acquire_admin_lock(
        self,
        *,
        actor: User,
        resource_type: str,
        resource_id: str,
        ttl_seconds: int = 600,
    ) -> dict[str, object]:
        return self.treasury_service.acquire_admin_lock(
            self.session,
            actor=actor,
            resource_type=resource_type,
            resource_id=resource_id,
            ttl_seconds=ttl_seconds,
        )

    def release_admin_lock(
        self,
        *,
        actor: User,
        resource_type: str,
        resource_id: str,
    ) -> dict[str, object]:
        return self.treasury_service.release_admin_lock(
            self.session,
            actor=actor,
            resource_type=resource_type,
            resource_id=resource_id,
        )

    def get_admin_lock_state(
        self,
        *,
        actor: User | None,
        resource_type: str,
        resource_id: str,
    ) -> dict[str, object]:
        return self.treasury_service.get_admin_lock_state(
            self.session,
            actor=actor,
            resource_type=resource_type,
            resource_id=resource_id,
        )

    def request_admin_export(
        self,
        *,
        actor: User,
        export_type: str,
        export_format: str,
        filters: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        normalized_type = export_type.strip().lower()
        normalized_format = export_format.strip().lower()
        if normalized_type not in ADMIN_EXPORT_TYPES:
            raise ValueError("Export type is not supported by the admin finance export queue.")
        if normalized_format not in {"csv", "json"}:
            raise ValueError("Export format must be csv or json.")
        normalized_filters = self._normalize_export_filters(filters or {})
        normalized_idempotency_key = self._normalize_export_idempotency_key(idempotency_key)
        request_fingerprint = self._admin_export_request_fingerprint(
            export_type=normalized_type,
            export_format=normalized_format,
            filters=normalized_filters,
        )
        if normalized_idempotency_key is not None:
            existing_event = self._find_idempotent_admin_export_request(
                actor=actor,
                idempotency_key=normalized_idempotency_key,
            )
            if existing_event is not None:
                existing_payload = dict(existing_event.payload or {})
                if existing_payload.get("request_fingerprint") != request_fingerprint:
                    raise ValueError("Idempotency key already used for a different admin export request.")
                status_payload = self.get_admin_export_status(
                    export_id=str(existing_payload.get("export_id") or existing_event.resource_id)
                )
                status_payload["enqueue_required"] = False
                return status_payload
        requested_at = datetime.now(timezone.utc)
        export_id = f"EXPORT-{requested_at.strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
        payload = {
            "export_id": export_id,
            "status": "queued",
            "export_type": normalized_type,
            "format": normalized_format,
            "filters": normalized_filters,
            "idempotency_key": normalized_idempotency_key,
            "request_fingerprint": request_fingerprint,
            "admin_user_id": actor.id,
            "admin_email": actor.email,
            "requested_at": requested_at.isoformat(),
            "completed_at": None,
            "download_url": None,
            "blocked_reason": None,
            "failure_reason": None,
            "worker_status": "queued",
            "occurred_at": requested_at.isoformat(),
            "backend_authored": True,
        }
        payload = self._json_export_payload(payload)
        audit = self.treasury_service._audit(
            self.session,
            actor=actor,
            event_type=ADMIN_EXPORT_EVENT_REQUESTED,
            resource_type="admin_export",
            resource_id=export_id,
            summary=f"Queued admin export {export_id}.",
            payload=payload,
        )
        payload["audit_reference"] = audit.id
        payload["requested_audit_reference"] = audit.id
        payload["audit"] = self._audit_event_payload(audit)
        status_payload = self._admin_export_status_from_payload(export_id=export_id, event=audit, payload=payload)
        status_payload["enqueue_required"] = True
        return status_payload

    def complete_admin_export(
        self,
        *,
        actor: User,
        export_id: str,
    ) -> dict[str, object]:
        current = self.get_admin_export_status(export_id=export_id)
        if current["status"] in {"ready", "blocked", "failed"}:
            return current
        completed_at = datetime.now(timezone.utc)
        persisted_current = {
            key: value
            for key, value in current.items()
            if key not in {"artifact", "audit", "audit_reference", "enqueue_required"}
        }
        try:
            artifact = self._build_admin_export_artifact(
                export_id=export_id,
                export_type=str(persisted_current.get("export_type") or ""),
                export_format=str(persisted_current.get("format") or "csv"),
                filters=dict(persisted_current.get("filters") or {}),
                generated_at=completed_at,
            )
            payload = {
                **persisted_current,
                "status": "ready",
                "completed_at": completed_at.isoformat(),
                "download_url": f"{ADMIN_EXPORT_DOWNLOAD_BASE}/{export_id}/download",
                "blocked_reason": None,
                "failure_reason": None,
                "artifact": artifact,
                "worker_status": "completed",
                "occurred_at": completed_at.isoformat(),
                "backend_authored": True,
            }
            event_type = ADMIN_EXPORT_EVENT_READY
            summary = f"Prepared admin export {export_id}."
        except AdminExportBlockedError as exc:
            payload = {
                **persisted_current,
                "status": "blocked",
                "completed_at": completed_at.isoformat(),
                "download_url": None,
                "blocked_reason": str(exc) or ADMIN_EXPORT_BLOCKED_REASON,
                "failure_reason": None,
                "blocked_at": completed_at.isoformat(),
                "worker_status": "blocked",
                "occurred_at": completed_at.isoformat(),
                "backend_authored": True,
            }
            event_type = ADMIN_EXPORT_EVENT_BLOCKED
            summary = f"Blocked admin export {export_id}: {payload['blocked_reason']}"
        except Exception as exc:
            logger.exception("admin_finance.export.worker_failed export_id=%s", export_id)
            failure_reason = str(exc).strip() or exc.__class__.__name__
            payload = {
                **persisted_current,
                "status": "failed",
                "completed_at": completed_at.isoformat(),
                "download_url": None,
                "blocked_reason": None,
                "failure_reason": failure_reason[:500],
                "failed_at": completed_at.isoformat(),
                "worker_status": "failed",
                "occurred_at": completed_at.isoformat(),
                "backend_authored": True,
            }
            event_type = ADMIN_EXPORT_EVENT_FAILED
            summary = f"Failed admin export {export_id}: {payload['failure_reason']}"
        payload = self._json_export_payload(payload)
        audit = self.treasury_service._audit(
            self.session,
            actor=actor,
            event_type=event_type,
            resource_type="admin_export",
            resource_id=export_id,
            summary=summary[:255],
            payload=payload,
        )
        payload["audit_reference"] = audit.id
        payload["audit"] = self._audit_event_payload(audit)
        self._publish_admin_export_outbox_event(
            event_type=event_type,
            export_id=export_id,
            audit=audit,
            payload=payload,
        )
        return self._admin_export_status_from_payload(export_id=export_id, event=audit, payload=payload)

    def fail_admin_export(
        self,
        *,
        actor: User,
        export_id: str,
        failure_reason: str,
    ) -> dict[str, object]:
        current = self.get_admin_export_status(export_id=export_id)
        if current["status"] in {"ready", "blocked", "failed"}:
            return current
        failed_at = datetime.now(timezone.utc)
        persisted_current = {
            key: value
            for key, value in current.items()
            if key not in {"artifact", "audit", "audit_reference", "enqueue_required"}
        }
        payload = {
            **persisted_current,
            "status": "failed",
            "completed_at": failed_at.isoformat(),
            "download_url": None,
            "blocked_reason": None,
            "failure_reason": (failure_reason.strip() or "Admin finance export worker failed.")[:500],
            "failed_at": failed_at.isoformat(),
            "worker_status": "failed",
            "occurred_at": failed_at.isoformat(),
            "backend_authored": True,
        }
        payload = self._json_export_payload(payload)
        audit = self.treasury_service._audit(
            self.session,
            actor=actor,
            event_type=ADMIN_EXPORT_EVENT_FAILED,
            resource_type="admin_export",
            resource_id=export_id,
            summary=f"Failed admin export {export_id}: {payload['failure_reason']}"[:255],
            payload=payload,
        )
        payload["audit_reference"] = audit.id
        payload["audit"] = self._audit_event_payload(audit)
        self._publish_admin_export_outbox_event(
            event_type=ADMIN_EXPORT_EVENT_FAILED,
            export_id=export_id,
            audit=audit,
            payload=payload,
        )
        return self._admin_export_status_from_payload(export_id=export_id, event=audit, payload=payload)

    def get_admin_export_status(self, *, export_id: str) -> dict[str, object]:
        event = self._latest_control_event(
            resource_type="admin_export",
            resource_id=export_id,
            event_types=(
                ADMIN_EXPORT_EVENT_FAILED,
                ADMIN_EXPORT_EVENT_BLOCKED,
                ADMIN_EXPORT_EVENT_READY,
                ADMIN_EXPORT_EVENT_REQUESTED,
            ),
        )
        if event is None:
            raise ValueError("Export request was not found.")
        payload = dict(event.payload or {})
        payload["audit_reference"] = event.id
        payload["audit"] = self._audit_event_payload(event)
        return self._admin_export_status_from_payload(export_id=export_id, event=event, payload=payload)

    def get_admin_export_artifact(self, *, export_id: str) -> dict[str, object]:
        event = self._latest_control_event(
            resource_type="admin_export",
            resource_id=export_id,
            event_types=(ADMIN_EXPORT_EVENT_READY,),
        )
        if event is None:
            raise ValueError("Export artifact was not found.")
        payload = dict(event.payload or {})
        if str(payload.get("status") or "") != "ready":
            raise ValueError("Export artifact is not ready.")
        artifact = dict(payload.get("artifact") or {})
        content = artifact.get("content")
        if not isinstance(content, str):
            raise ValueError("Export artifact content is missing.")
        return artifact

    def _admin_export_status_from_payload(
        self,
        *,
        export_id: str,
        event: TreasuryAuditEvent,
        payload: dict[str, object],
    ) -> dict[str, object]:
        artifact_payload = dict(payload.get("artifact") or {})
        artifact = None
        if artifact_payload:
            artifact = {key: value for key, value in artifact_payload.items() if key not in {"content"}}
        return {
            "export_id": str(payload.get("export_id") or export_id),
            "status": str(payload.get("status") or "queued"),
            "export_type": str(payload.get("export_type") or "unknown"),
            "format": str(payload.get("format") or "csv"),
            "filters": dict(payload.get("filters") or {}),
            "requested_at": payload.get("requested_at") or event.created_at,
            "completed_at": payload.get("completed_at"),
            "download_url": payload.get("download_url"),
            "blocked_reason": payload.get("blocked_reason"),
            "failure_reason": payload.get("failure_reason"),
            "audit_reference": event.id,
            "requested_audit_reference": payload.get("requested_audit_reference") or event.id,
            "audit": payload["audit"],
            "artifact": artifact,
            "idempotency_key": payload.get("idempotency_key"),
            "request_fingerprint": payload.get("request_fingerprint"),
            "admin_user_id": payload.get("admin_user_id"),
            "admin_email": payload.get("admin_email"),
            "worker_status": payload.get("worker_status"),
            "backend_authored": payload.get("backend_authored") is not False,
        }

    def _build_admin_export_artifact(
        self,
        *,
        export_id: str,
        export_type: str,
        export_format: str,
        filters: dict[str, object],
        generated_at: datetime,
    ) -> dict[str, object]:
        rows, fieldnames = self._admin_export_rows(export_type=export_type, filters=filters)
        filename = f"{export_id.lower()}-{export_type}.{export_format}"
        if export_format == "json":
            content = json.dumps(
                {
                    "export_id": export_id,
                    "export_type": export_type,
                    "generated_at": generated_at.isoformat(),
                    "filters": filters,
                    "row_count": len(rows),
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
            content_type = "application/json"
        else:
            content = self._render_csv_export(rows=rows, fieldnames=fieldnames)
            content_type = "text/csv"
        return {
            "filename": filename,
            "content_type": content_type,
            "encoding": "utf-8",
            "size_bytes": len(content.encode("utf-8")),
            "row_count": len(rows),
            "fieldnames": fieldnames,
            "content": content,
        }

    def _admin_export_rows(
        self,
        *,
        export_type: str,
        filters: dict[str, object],
    ) -> tuple[list[dict[str, object]], list[str]]:
        if export_type in ADMIN_EXPORT_GENERATOR_BLOCKED_REASONS:
            raise AdminExportBlockedError(ADMIN_EXPORT_GENERATOR_BLOCKED_REASONS[export_type])
        if export_type == "settlements":
            return self._settlement_export_rows(filters)
        if export_type == "fraud":
            return self._fraud_export_rows(filters)
        if export_type == "withdrawals":
            return self._withdrawal_export_rows(filters)
        if export_type == "payment_proofs":
            return self._payment_proof_export_rows(filters)
        if export_type == "payment_queue":
            return self._payment_queue_export_rows(filters)
        if export_type == "treasury":
            return self._treasury_export_rows(filters)
        if export_type == "audit_logs":
            return self._audit_log_export_rows(filters)
        raise AdminExportBlockedError(ADMIN_EXPORT_BLOCKED_REASON)

    def _withdrawal_export_rows(self, filters: dict[str, object]) -> tuple[list[dict[str, object]], list[str]]:
        fieldnames = [
            "id",
            "reference",
            "status",
            "user_id",
            "user_email",
            "gross_amount",
            "amount_coin",
            "amount_fiat",
            "fee_amount",
            "net_amount",
            "total_debit",
            "currency_code",
            "source_scope",
            "processor_mode",
            "payout_channel",
            "created_at",
            "reviewed_at",
            "approved_at",
            "processed_at",
            "paid_at",
            "rejected_at",
            "admin_notes",
        ]
        query = select(TreasuryWithdrawalRequest, User).join(User, TreasuryWithdrawalRequest.user_id == User.id)
        status_filter = str(filters.get("status") or "").strip().lower()
        if status_filter:
            query = query.where(TreasuryWithdrawalRequest.status == status_filter)
        rows = self.session.execute(
            query.order_by(TreasuryWithdrawalRequest.created_at.desc()).limit(self._export_limit(filters))
        ).all()
        return [
            self._export_row(
                {
                    "id": withdrawal.id,
                    "reference": withdrawal.reference,
                    "status": self._enum_value(withdrawal.status),
                    "user_id": withdrawal.user_id,
                    "user_email": user.email,
                    "gross_amount": withdrawal.amount_coin,
                    "amount_coin": withdrawal.amount_coin,
                    "amount_fiat": withdrawal.amount_fiat,
                    "fee_amount": withdrawal.fee_amount,
                    "net_amount": withdrawal.net_amount,
                    "total_debit": withdrawal.total_debit,
                    "currency_code": withdrawal.currency_code,
                    "source_scope": withdrawal.source_scope,
                    "processor_mode": withdrawal.processor_mode,
                    "payout_channel": withdrawal.payout_channel,
                    "created_at": withdrawal.created_at,
                    "reviewed_at": withdrawal.reviewed_at,
                    "approved_at": withdrawal.approved_at,
                    "processed_at": withdrawal.processed_at,
                    "paid_at": withdrawal.paid_at,
                    "rejected_at": withdrawal.rejected_at,
                    "admin_notes": withdrawal.admin_notes,
                },
                fieldnames,
            )
            for withdrawal, user in rows
        ], fieldnames

    def _payment_proof_export_rows(self, filters: dict[str, object]) -> tuple[list[dict[str, object]], list[str]]:
        fieldnames = [
            "id",
            "reference",
            "status",
            "user_id",
            "user_email",
            "amount_fiat",
            "amount_coin",
            "currency_code",
            "payer_name",
            "sender_bank",
            "transfer_reference",
            "proof_attachment_id",
            "created_at",
            "submitted_at",
            "reviewed_at",
            "confirmed_at",
            "rejected_at",
            "admin_notes",
        ]
        query = select(DepositRequest, User).join(User, DepositRequest.user_id == User.id)
        status_filter = str(filters.get("status") or "").strip().lower()
        if status_filter:
            query = query.where(DepositRequest.status == status_filter)
        if filters.get("with_proof_only") is not False:
            query = query.where(DepositRequest.proof_attachment_id.is_not(None))
        rows = self.session.execute(
            query.order_by(DepositRequest.created_at.desc()).limit(self._export_limit(filters))
        ).all()
        return [
            self._export_row(
                {
                    "id": deposit.id,
                    "reference": deposit.reference,
                    "status": self._enum_value(deposit.status),
                    "user_id": deposit.user_id,
                    "user_email": user.email,
                    "amount_fiat": deposit.amount_fiat,
                    "amount_coin": deposit.amount_coin,
                    "currency_code": deposit.currency_code,
                    "payer_name": deposit.payer_name,
                    "sender_bank": deposit.sender_bank,
                    "transfer_reference": deposit.transfer_reference,
                    "proof_attachment_id": deposit.proof_attachment_id,
                    "created_at": deposit.created_at,
                    "submitted_at": deposit.submitted_at,
                    "reviewed_at": deposit.reviewed_at,
                    "confirmed_at": deposit.confirmed_at,
                    "rejected_at": deposit.rejected_at,
                    "admin_notes": deposit.admin_notes,
                },
                fieldnames,
            )
            for deposit, user in rows
        ], fieldnames

    def _payment_queue_export_rows(self, filters: dict[str, object]) -> tuple[list[dict[str, object]], list[str]]:
        fieldnames = [
            "item_type",
            "id",
            "reference",
            "status",
            "queue",
            "user_id",
            "user_email",
            "amount_fiat",
            "amount_coin",
            "gross_amount",
            "fee_amount",
            "net_amount",
            "total_debit",
            "currency_code",
            "created_at",
            "submitted_at",
            "reviewed_at",
            "completed_at",
            "admin_notes",
        ]
        limit = self._export_limit(filters)
        status_filter = str(filters.get("status") or "").strip().lower()
        rows: list[dict[str, object]] = []

        deposit_query = select(DepositRequest, User).join(User, DepositRequest.user_id == User.id)
        if status_filter:
            deposit_query = deposit_query.where(DepositRequest.status == status_filter)
        for deposit, user in self.session.execute(
            deposit_query.order_by(DepositRequest.created_at.desc()).limit(limit)
        ).all():
            rows.append(
                self._export_row(
                    {
                        "item_type": "deposit",
                        "id": deposit.id,
                        "reference": deposit.reference,
                        "status": self._enum_value(deposit.status),
                        "queue": self._deposit_export_queue(deposit.status),
                        "user_id": deposit.user_id,
                        "user_email": user.email,
                        "amount_fiat": deposit.amount_fiat,
                        "amount_coin": deposit.amount_coin,
                        "gross_amount": None,
                        "fee_amount": None,
                        "net_amount": None,
                        "total_debit": None,
                        "currency_code": deposit.currency_code,
                        "created_at": deposit.created_at,
                        "submitted_at": deposit.submitted_at,
                        "reviewed_at": deposit.reviewed_at,
                        "completed_at": deposit.confirmed_at or deposit.rejected_at,
                        "admin_notes": deposit.admin_notes,
                    },
                    fieldnames,
                )
            )

        withdrawal_query = select(TreasuryWithdrawalRequest, User).join(
            User, TreasuryWithdrawalRequest.user_id == User.id
        )
        if status_filter:
            withdrawal_query = withdrawal_query.where(TreasuryWithdrawalRequest.status == status_filter)
        for withdrawal, user in self.session.execute(
            withdrawal_query.order_by(TreasuryWithdrawalRequest.created_at.desc()).limit(limit)
        ).all():
            rows.append(
                self._export_row(
                    {
                        "item_type": "withdrawal",
                        "id": withdrawal.id,
                        "reference": withdrawal.reference,
                        "status": self._enum_value(withdrawal.status),
                        "queue": self._withdrawal_export_queue(withdrawal.status),
                        "user_id": withdrawal.user_id,
                        "user_email": user.email,
                        "amount_fiat": withdrawal.amount_fiat,
                        "amount_coin": withdrawal.amount_coin,
                        "gross_amount": withdrawal.amount_coin,
                        "fee_amount": withdrawal.fee_amount,
                        "net_amount": withdrawal.net_amount,
                        "total_debit": withdrawal.total_debit,
                        "currency_code": withdrawal.currency_code,
                        "created_at": withdrawal.created_at,
                        "submitted_at": None,
                        "reviewed_at": withdrawal.reviewed_at,
                        "completed_at": withdrawal.paid_at or withdrawal.rejected_at or withdrawal.cancelled_at,
                        "admin_notes": withdrawal.admin_notes,
                    },
                    fieldnames,
                )
            )
        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows[:limit], fieldnames

    def _treasury_export_rows(self, filters: dict[str, object]) -> tuple[list[dict[str, object]], list[str]]:
        del filters
        fieldnames = [
            "generated_at",
            "pending_payment_events",
            "settled_purchase_orders_missing_ledger",
            "settled_payment_events_missing_ledger",
            "confirmed_deposits_missing_ledger",
            "duplicate_provider_references",
            "pending_purchase_orders",
            "pending_withdrawals",
            "pending_kyc",
            "liquidity_status",
        ]
        reconciliation = self.payment_reconciliation_summary(issue_limit=1)
        row = {
            **reconciliation,
            "pending_purchase_orders": self._count_pending_purchase_orders(),
            "pending_withdrawals": self._count_pending_withdrawals(),
            "pending_kyc": self._count_pending_kyc(),
            "liquidity_status": self._liquidity_status(),
        }
        return [self._export_row(row, fieldnames)], fieldnames

    def _settlement_export_rows(self, filters: dict[str, object]) -> tuple[list[dict[str, object]], list[str]]:
        fieldnames = [
            "source",
            "id",
            "status",
            "user_id",
            "user_email",
            "competition_key",
            "competition_id",
            "match_id",
            "season_id",
            "reward_source",
            "title",
            "gross_amount",
            "platform_fee_amount",
            "net_amount",
            "ledger_unit",
            "ledger_transaction_id",
            "settled_by_user_id",
            "home_club_id",
            "away_club_id",
            "total_revenue_coin",
            "total_creator_share_coin",
            "home_creator_share_coin",
            "away_creator_share_coin",
            "total_platform_share_coin",
            "reviewed_by_user_id",
            "reviewed_at",
            "review_note",
            "settled_at",
            "note",
            "created_at",
            "updated_at",
        ]
        rows: list[dict[str, object]] = []
        query = select(RewardSettlement, User).join(User, RewardSettlement.user_id == User.id)
        status_filter = str(filters.get("status") or "").strip().lower()
        if status_filter:
            query = query.where(RewardSettlement.status == status_filter)
        competition_key = str(filters.get("competition_key") or "").strip()
        if competition_key:
            query = query.where(RewardSettlement.competition_key == competition_key)
        reward_source = str(filters.get("reward_source") or "").strip()
        if reward_source:
            query = query.where(RewardSettlement.reward_source == reward_source)
        reward_rows = self.session.execute(
            query.order_by(RewardSettlement.created_at.desc()).limit(self._export_limit(filters))
        ).all()
        for settlement, user in reward_rows:
            rows.append(
                self._export_row(
                    {
                        "source": "reward_settlement",
                        "id": settlement.id,
                        "status": self._enum_value(settlement.status),
                        "user_id": settlement.user_id,
                        "user_email": user.email,
                        "competition_key": settlement.competition_key,
                        "reward_source": settlement.reward_source,
                        "title": settlement.title,
                        "gross_amount": settlement.gross_amount,
                        "platform_fee_amount": settlement.platform_fee_amount,
                        "net_amount": settlement.net_amount,
                        "ledger_unit": settlement.ledger_unit,
                        "ledger_transaction_id": settlement.ledger_transaction_id,
                        "settled_by_user_id": settlement.settled_by_user_id,
                        "note": settlement.note,
                        "created_at": settlement.created_at,
                        "updated_at": settlement.updated_at,
                    },
                    fieldnames,
                )
            )

        creator_query = select(CreatorRevenueSettlement)
        review_status_filter = (
            str(filters.get("review_status") or filters.get("creator_review_status") or "").strip().lower()
        )
        if review_status_filter:
            creator_query = creator_query.where(CreatorRevenueSettlement.review_status == review_status_filter)
        competition_id = str(filters.get("competition_id") or "").strip()
        if competition_id:
            creator_query = creator_query.where(CreatorRevenueSettlement.competition_id == competition_id)
        match_id = str(filters.get("match_id") or "").strip()
        if match_id:
            creator_query = creator_query.where(CreatorRevenueSettlement.match_id == match_id)
        season_id = str(filters.get("season_id") or "").strip()
        if season_id:
            creator_query = creator_query.where(CreatorRevenueSettlement.season_id == season_id)
        club_id = str(filters.get("club_id") or "").strip()
        if club_id:
            creator_query = creator_query.where(
                (CreatorRevenueSettlement.home_club_id == club_id) | (CreatorRevenueSettlement.away_club_id == club_id)
            )
        creator_rows = self.session.scalars(
            creator_query.order_by(
                CreatorRevenueSettlement.settled_at.desc().nullslast(),
                CreatorRevenueSettlement.updated_at.desc(),
                CreatorRevenueSettlement.created_at.desc(),
            ).limit(self._export_limit(filters))
        ).all()
        for settlement in creator_rows:
            rows.append(
                self._export_row(
                    {
                        "source": "creator_revenue_settlement",
                        "id": settlement.id,
                        "status": settlement.review_status,
                        "competition_id": settlement.competition_id,
                        "match_id": settlement.match_id,
                        "season_id": settlement.season_id,
                        "title": f"Creator revenue settlement {settlement.match_id}",
                        "gross_amount": settlement.total_revenue_coin,
                        "platform_fee_amount": settlement.total_platform_share_coin,
                        "net_amount": settlement.total_creator_share_coin,
                        "ledger_unit": LedgerUnit.COIN,
                        "home_club_id": settlement.home_club_id,
                        "away_club_id": settlement.away_club_id,
                        "total_revenue_coin": settlement.total_revenue_coin,
                        "total_creator_share_coin": settlement.total_creator_share_coin,
                        "home_creator_share_coin": settlement.home_creator_share_coin,
                        "away_creator_share_coin": settlement.away_creator_share_coin,
                        "total_platform_share_coin": settlement.total_platform_share_coin,
                        "reviewed_by_user_id": settlement.reviewed_by_user_id,
                        "reviewed_at": settlement.reviewed_at,
                        "review_note": settlement.review_note,
                        "settled_at": settlement.settled_at,
                        "note": settlement.review_note,
                        "created_at": settlement.created_at,
                        "updated_at": settlement.updated_at,
                    },
                    fieldnames,
                )
            )
        return rows, fieldnames

    def _fraud_export_rows(self, filters: dict[str, object]) -> tuple[list[dict[str, object]], list[str]]:
        fieldnames = [
            "source",
            "id",
            "case_key",
            "type",
            "status",
            "severity",
            "user_id",
            "user_email",
            "title",
            "description",
            "confidence_score",
            "amount_signal",
            "subject_type",
            "subject_id",
            "action_type",
            "signal_type",
            "signal_value",
            "metadata_json",
            "created_at",
            "updated_at",
        ]
        limit = self._export_limit(filters)
        status_filter = str(filters.get("status") or "").strip().lower()
        severity_filter = str(filters.get("severity") or "").strip().lower()
        rows: list[dict[str, object]] = []

        fraud_query = select(FraudCase, User).outerjoin(User, FraudCase.user_id == User.id)
        if status_filter:
            fraud_query = fraud_query.where(FraudCase.status == status_filter)
        if severity_filter:
            fraud_query = fraud_query.where(FraudCase.severity == severity_filter)
        for case, user in self.session.execute(fraud_query.order_by(FraudCase.created_at.desc()).limit(limit)).all():
            rows.append(
                self._export_row(
                    {
                        "source": "fraud_case",
                        "id": case.id,
                        "case_key": case.case_key,
                        "type": case.fraud_type,
                        "status": case.status,
                        "severity": case.severity,
                        "user_id": case.user_id,
                        "user_email": None if user is None else user.email,
                        "title": case.title,
                        "description": case.description,
                        "confidence_score": case.confidence_score,
                        "metadata_json": case.metadata_json,
                        "created_at": case.created_at,
                        "updated_at": case.updated_at,
                    },
                    fieldnames,
                )
            )

        aml_query = select(AmlCase, User).outerjoin(User, AmlCase.user_id == User.id)
        if status_filter:
            aml_query = aml_query.where(AmlCase.status == status_filter)
        if severity_filter:
            aml_query = aml_query.where(AmlCase.severity == severity_filter)
        for case, user in self.session.execute(aml_query.order_by(AmlCase.created_at.desc()).limit(limit)).all():
            rows.append(
                self._export_row(
                    {
                        "source": "aml_case",
                        "id": case.id,
                        "case_key": case.case_key,
                        "type": case.trigger_source,
                        "status": case.status,
                        "severity": case.severity,
                        "user_id": case.user_id,
                        "user_email": None if user is None else user.email,
                        "title": case.title,
                        "description": case.description,
                        "amount_signal": case.amount_signal,
                        "metadata_json": case.metadata_json,
                        "created_at": case.created_at,
                        "updated_at": case.updated_at,
                    },
                    fieldnames,
                )
            )

        action_query = select(RiskAction, User).join(User, RiskAction.user_id == User.id)
        if status_filter:
            action_query = action_query.where(RiskAction.status == status_filter)
        for action, user in self.session.execute(
            action_query.order_by(RiskAction.created_at.desc()).limit(limit)
        ).all():
            rows.append(
                self._export_row(
                    {
                        "source": "risk_action",
                        "id": action.id,
                        "case_key": action.source_rule_key,
                        "type": action.action_type,
                        "status": action.status,
                        "user_id": action.user_id,
                        "user_email": user.email,
                        "title": action.reason,
                        "action_type": action.action_type,
                        "metadata_json": action.metadata_json,
                        "created_at": action.created_at,
                        "updated_at": action.updated_at,
                    },
                    fieldnames,
                )
            )

        signal_query = select(RiskSignal, User).outerjoin(User, RiskSignal.user_id == User.id)
        for signal, user in self.session.execute(
            signal_query.order_by(RiskSignal.created_at.desc()).limit(limit)
        ).all():
            rows.append(
                self._export_row(
                    {
                        "source": "risk_signal",
                        "id": signal.id,
                        "case_key": signal.signal_key,
                        "type": signal.source,
                        "status": "recorded",
                        "user_id": signal.user_id,
                        "user_email": None if user is None else user.email,
                        "confidence_score": signal.confidence_score,
                        "signal_type": signal.signal_type,
                        "signal_value": signal.signal_value or signal.device_id or signal.ip_address,
                        "metadata_json": signal.metadata_json,
                        "created_at": signal.created_at,
                        "updated_at": signal.updated_at,
                    },
                    fieldnames,
                )
            )

        event_query = select(SystemEvent).where(
            or_(
                SystemEvent.event_type.ilike("%fraud%"),
                SystemEvent.event_type.ilike("%aml%"),
                SystemEvent.event_type.ilike("%dispute%"),
                SystemEvent.subject_type.in_(["fraud_case", "aml_case", "deposit_request", "treasury_withdrawal"]),
            )
        )
        if severity_filter:
            event_query = event_query.where(SystemEvent.severity == severity_filter)
        for event in self.session.scalars(event_query.order_by(SystemEvent.created_at.desc()).limit(limit)).all():
            rows.append(
                self._export_row(
                    {
                        "source": "system_event",
                        "id": event.id,
                        "case_key": event.event_key,
                        "type": event.event_type,
                        "status": "recorded",
                        "severity": event.severity,
                        "user_id": event.created_by_user_id,
                        "title": event.title,
                        "description": event.body,
                        "subject_type": event.subject_type,
                        "subject_id": event.subject_id,
                        "metadata_json": event.metadata_json,
                        "created_at": event.created_at,
                        "updated_at": event.updated_at,
                    },
                    fieldnames,
                )
            )

        deposit_query = (
            select(DepositRequest, User)
            .join(User, DepositRequest.user_id == User.id)
            .where(DepositRequest.status == DepositStatus.DISPUTED)
        )
        for deposit, user in self.session.execute(
            deposit_query.order_by(DepositRequest.created_at.desc()).limit(limit)
        ).all():
            rows.append(
                self._export_row(
                    {
                        "source": "deposit_dispute",
                        "id": deposit.id,
                        "case_key": deposit.reference,
                        "type": "deposit_dispute",
                        "status": deposit.status,
                        "severity": "high",
                        "user_id": deposit.user_id,
                        "user_email": user.email,
                        "title": "Disputed deposit",
                        "description": deposit.admin_notes,
                        "subject_type": "deposit_request",
                        "subject_id": deposit.id,
                        "metadata_json": {
                            "amount_fiat": self._export_value(deposit.amount_fiat),
                            "amount_coin": self._export_value(deposit.amount_coin),
                            "transfer_reference": deposit.transfer_reference,
                        },
                        "created_at": deposit.created_at,
                        "updated_at": deposit.updated_at,
                    },
                    fieldnames,
                )
            )

        withdrawal_query = (
            select(TreasuryWithdrawalRequest, User)
            .join(User, TreasuryWithdrawalRequest.user_id == User.id)
            .where(TreasuryWithdrawalRequest.status == TreasuryWithdrawalStatus.DISPUTED)
        )
        for withdrawal, user in self.session.execute(
            withdrawal_query.order_by(TreasuryWithdrawalRequest.created_at.desc()).limit(limit)
        ).all():
            rows.append(
                self._export_row(
                    {
                        "source": "withdrawal_dispute",
                        "id": withdrawal.id,
                        "case_key": withdrawal.reference,
                        "type": "withdrawal_dispute",
                        "status": withdrawal.status,
                        "severity": "critical",
                        "user_id": withdrawal.user_id,
                        "user_email": user.email,
                        "title": "Disputed withdrawal",
                        "description": withdrawal.admin_notes,
                        "subject_type": "treasury_withdrawal",
                        "subject_id": withdrawal.id,
                        "metadata_json": {
                            "amount_fiat": self._export_value(withdrawal.amount_fiat),
                            "amount_coin": self._export_value(withdrawal.amount_coin),
                            "net_amount": self._export_value(withdrawal.net_amount),
                        },
                        "created_at": withdrawal.created_at,
                        "updated_at": withdrawal.updated_at,
                    },
                    fieldnames,
                )
            )

        rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
        return rows[:limit], fieldnames

    def _audit_log_export_rows(self, filters: dict[str, object]) -> tuple[list[dict[str, object]], list[str]]:
        fieldnames = [
            "id",
            "event_type",
            "actor_user_id",
            "actor_email",
            "resource_type",
            "resource_id",
            "summary",
            "created_at",
        ]
        query = select(TreasuryAuditEvent)
        event_type = str(filters.get("event_type") or "").strip()
        resource_type = str(filters.get("resource_type") or "").strip()
        if event_type:
            query = query.where(TreasuryAuditEvent.event_type == event_type)
        if resource_type:
            query = query.where(TreasuryAuditEvent.resource_type == resource_type)
        events = self.session.scalars(
            query.order_by(TreasuryAuditEvent.created_at.desc()).limit(self._export_limit(filters))
        ).all()
        return [
            self._export_row(
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "actor_user_id": event.actor_user_id,
                    "actor_email": event.actor_email,
                    "resource_type": event.resource_type,
                    "resource_id": event.resource_id,
                    "summary": event.summary,
                    "created_at": event.created_at,
                },
                fieldnames,
            )
            for event in events
        ], fieldnames

    @staticmethod
    def _normalize_export_filters(filters: dict[str, object]) -> dict[str, object]:
        normalized = {str(key): AdminFinanceService._export_value(value) for key, value in dict(filters).items()}
        raw_limit = normalized.get("limit", ADMIN_EXPORT_DEFAULT_LIMIT)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = ADMIN_EXPORT_DEFAULT_LIMIT
        normalized["limit"] = max(1, min(ADMIN_EXPORT_MAX_LIMIT, limit))
        return normalized

    def _find_idempotent_admin_export_request(
        self,
        *,
        actor: User,
        idempotency_key: str,
    ) -> TreasuryAuditEvent | None:
        events = self.session.scalars(
            select(TreasuryAuditEvent)
            .where(
                TreasuryAuditEvent.resource_type == "admin_export",
                TreasuryAuditEvent.event_type == ADMIN_EXPORT_EVENT_REQUESTED,
                TreasuryAuditEvent.actor_user_id == actor.id,
            )
            .order_by(TreasuryAuditEvent.created_at.desc())
            .limit(200)
        ).all()
        for event in events:
            payload = dict(event.payload or {})
            if payload.get("idempotency_key") == idempotency_key:
                return event
        return None

    @staticmethod
    def _normalize_export_idempotency_key(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        if len(normalized) > 160:
            raise ValueError("Admin export idempotency key must be at most 160 characters.")
        return normalized

    @staticmethod
    def _admin_export_request_fingerprint(
        *,
        export_type: str,
        export_format: str,
        filters: dict[str, object],
    ) -> str:
        return json.dumps(
            {
                "export_type": export_type,
                "format": export_format,
                "filters": AdminFinanceService._json_export_payload(filters),
            },
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _publish_admin_export_outbox_event(
        self,
        *,
        event_type: str,
        export_id: str,
        audit: TreasuryAuditEvent,
        payload: dict[str, object],
    ) -> EventOutbox:
        event_payload = {key: value for key, value in payload.items() if key != "artifact"}
        artifact_payload = payload.get("artifact")
        if isinstance(artifact_payload, dict):
            event_payload["artifact"] = {key: value for key, value in artifact_payload.items() if key != "content"}
        outbox_event = EventOutbox(
            event_id=str(uuid4()),
            event_type=event_type,
            aggregate_type="admin_export",
            aggregate_id=export_id,
            partition_key=export_id,
            producer="admin_finance",
            occurred_at=audit.created_at,
            payload_json=self._json_export_payload(event_payload),
            headers_json={
                "audit_reference": audit.id,
                "treasury_audit_event_id": audit.id,
            },
        )
        self.session.add(outbox_event)
        self.session.flush()
        return outbox_event

    @staticmethod
    def _json_export_payload(payload: dict[str, object]) -> dict[str, object]:
        return {str(key): AdminFinanceService._export_value(value) for key, value in payload.items()}

    @staticmethod
    def _export_limit(filters: dict[str, object]) -> int:
        try:
            return max(1, min(ADMIN_EXPORT_MAX_LIMIT, int(filters.get("limit") or ADMIN_EXPORT_DEFAULT_LIMIT)))
        except (TypeError, ValueError):
            return ADMIN_EXPORT_DEFAULT_LIMIT

    @staticmethod
    def _export_row(values: dict[str, object], fieldnames: list[str]) -> dict[str, object]:
        return {field: AdminFinanceService._export_value(values.get(field)) for field in fieldnames}

    @staticmethod
    def _export_value(value: object) -> object:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if hasattr(value, "value"):
            return str(value.value)
        if isinstance(value, dict):
            return {str(key): AdminFinanceService._export_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [AdminFinanceService._export_value(item) for item in value]
        return value

    @staticmethod
    def _render_csv_export(*, rows: list[dict[str, object]], fieldnames: list[str]) -> str:
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: AdminFinanceService._csv_export_value(row.get(field)) for field in fieldnames})
        return buffer.getvalue()

    @staticmethod
    def _csv_export_value(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(AdminFinanceService._export_value(value), ensure_ascii=False, sort_keys=True)
        return str(value)

    @staticmethod
    def _deposit_export_queue(status_value: object) -> str:
        status_text = AdminFinanceService._enum_value(status_value)
        if status_text in {status.value for status in PAYMENT_QUEUE_APPROVED_DEPOSIT_STATUSES}:
            return "approved"
        if status_text in {status.value for status in PAYMENT_QUEUE_REJECTED_DEPOSIT_STATUSES}:
            return "rejected"
        return "pending"

    @staticmethod
    def _withdrawal_export_queue(status_value: object) -> str:
        status_text = AdminFinanceService._enum_value(status_value)
        if status_text == TreasuryWithdrawalStatus.APPROVED.value:
            return "approved"
        if status_text == TreasuryWithdrawalStatus.REJECTED.value:
            return "rejected"
        return "pending"

    def request_admin_bulk_action(
        self,
        *,
        actor: User,
        item_type: str,
        action: str,
        item_ids: list[str],
        admin_notes: str,
    ) -> dict[str, object]:
        normalized_item_type = item_type.strip().lower()
        normalized_action = action.strip().lower()
        resource_type = ADMIN_BULK_RESOURCE_TYPES.get(normalized_item_type)
        if resource_type is None:
            raise ValueError("Bulk action item type is not supported by admin finance.")
        if normalized_action not in PAYMENT_QUEUE_ACTION_LABELS:
            raise ValueError("Bulk action must be review, approve, reject, reinstate, or counter.")
        requested_at = datetime.now(timezone.utc)
        unique_item_ids = list(dict.fromkeys(str(item_id).strip() for item_id in item_ids if str(item_id).strip()))
        if not unique_item_ids:
            raise ValueError("At least one item_id is required.")
        blocked_ids = [
            item_id
            for item_id in unique_item_ids
            if self.treasury_service.get_admin_lock_state(
                self.session,
                actor=actor,
                resource_type=resource_type,
                resource_id=item_id,
            )["state"]
            == "locked_by_other"
        ]
        queued_ids = [item_id for item_id in unique_item_ids if item_id not in set(blocked_ids)]
        bulk_action_id = f"BULK-{requested_at.strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
        status = "queued" if queued_ids else "blocked"
        blocked_reason = None
        if blocked_ids:
            blocked_reason = "Some items are locked by another admin and were excluded from this bulk action."
        payload = {
            "bulk_action_id": bulk_action_id,
            "status": status,
            "item_type": normalized_item_type,
            "action": normalized_action,
            "item_ids": queued_ids,
            "blocked_item_ids": blocked_ids,
            "queued_count": len(queued_ids),
            "blocked_count": len(blocked_ids),
            "admin_notes": admin_notes,
            "requested_at": requested_at.isoformat(),
            "completed_at": None,
            "blocked_reason": blocked_reason,
            "occurred_at": requested_at.isoformat(),
        }
        audit = self.treasury_service._audit(
            self.session,
            actor=actor,
            event_type=ADMIN_BULK_ACTION_EVENT_REQUESTED,
            resource_type="admin_bulk_action",
            resource_id=bulk_action_id,
            summary=f"Queued admin bulk action {bulk_action_id}.",
            payload=payload,
        )
        payload["audit_reference"] = audit.id
        payload["audit"] = self._audit_event_payload(audit)
        return payload

    def get_admin_bulk_action_status(self, *, bulk_action_id: str) -> dict[str, object]:
        event = self._latest_control_event(
            resource_type="admin_bulk_action",
            resource_id=bulk_action_id,
            event_types=(ADMIN_BULK_ACTION_EVENT_COMPLETED, ADMIN_BULK_ACTION_EVENT_REQUESTED),
        )
        if event is None:
            raise ValueError("Bulk action request was not found.")
        payload = dict(event.payload or {})
        payload["audit_reference"] = event.id
        payload["audit"] = self._audit_event_payload(event)
        return {
            "bulk_action_id": str(payload.get("bulk_action_id") or bulk_action_id),
            "status": str(payload.get("status") or "queued"),
            "item_type": str(payload.get("item_type") or "unknown"),
            "action": str(payload.get("action") or "unknown"),
            "item_ids": list(payload.get("item_ids") or []),
            "queued_count": int(payload.get("queued_count") or 0),
            "blocked_count": int(payload.get("blocked_count") or 0),
            "requested_at": payload.get("requested_at") or event.created_at,
            "completed_at": payload.get("completed_at"),
            "audit_reference": event.id,
            "audit": payload["audit"],
            "blocked_reason": payload.get("blocked_reason"),
        }

    def governor_snapshot(self) -> dict[str, object]:
        return EconomyGovernorService(self.session).snapshot()

    def _normalize_payment_queue_tab(self, tab: str | None) -> str | None:
        if tab is None or not tab.strip():
            return None
        normalized = tab.strip().lower()
        if normalized not in PAYMENT_QUEUE_TABS:
            raise ValueError("Payment queue tab must be pending, approved, rejected, or bids.")
        return normalized

    def _deposit_queue_section(
        self,
        *,
        key: str,
        label: str,
        statuses: tuple[DepositStatus, ...],
        include_items: bool,
        q: str | None,
        limit: int,
        offset: int,
        actor: User | None,
    ) -> dict[str, object]:
        query = (
            select(DepositRequest, User)
            .join(User, DepositRequest.user_id == User.id)
            .where(DepositRequest.status.in_(statuses))
        )
        if q and q.strip():
            like = f"%{q.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(DepositRequest.reference).ilike(like),
                    func.lower(DepositRequest.payer_name).ilike(like),
                    func.lower(DepositRequest.sender_bank).ilike(like),
                    func.lower(DepositRequest.transfer_reference).ilike(like),
                    func.lower(User.email).ilike(like),
                    func.lower(User.full_name).ilike(like),
                    func.lower(User.phone_number).ilike(like),
                )
            )
        total = int(self.session.scalar(select(func.count()).select_from(query.subquery())) or 0)
        rows = []
        if include_items:
            rows = self.session.execute(
                query.order_by(DepositRequest.created_at.desc()).limit(limit).offset(offset)
            ).all()
        return {
            "key": key,
            "label": label,
            "item_type": "deposit",
            "statuses": [status.value for status in statuses],
            "items": [
                self._serialize_deposit_queue_item(deposit, key, user=user, actor=actor) for deposit, user in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
            "action_state": "enabled",
        }

    def _transfer_bid_queue_section(
        self,
        *,
        include_items: bool,
        q: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, object]:
        from app.services.player_lifecycle_service import PlayerLifecycleService

        queue = PlayerLifecycleService(self.session).list_admin_transfer_bid_reviews(
            q=q,
            limit=limit,
            offset=offset if include_items else 0,
        )
        items = [self._serialize_transfer_bid_queue_item(item) for item in queue.items] if include_items else []
        return {
            "key": "bids",
            "label": "Bids",
            "item_type": "transfer_bid",
            "statuses": [],
            "items": items,
            "total": queue.total,
            "limit": limit,
            "offset": offset,
            "action_state": "audit_only",
            "blocked_reason": (
                "Transfer bid approve, reject, and counter requests are audit-only in the admin payment queue."
            ),
        }

    def _serialize_deposit_queue_item(
        self,
        deposit: DepositRequest,
        queue_key: str,
        *,
        user: User | None = None,
        actor: User | None = None,
    ) -> dict[str, object]:
        user = user or self.session.get(User, deposit.user_id)
        available_actions: tuple[str, ...]
        if queue_key == "pending":
            available_actions = (
                ("review",) if deposit.status == DepositStatus.DISPUTED else ("review", "approve", "reject")
            )
        elif queue_key == "rejected":
            available_actions = ("reinstate",)
        else:
            available_actions = tuple()
        admin_user = self.session.get(User, deposit.admin_user_id) if deposit.admin_user_id else None
        action_endpoints = self._deposit_action_endpoints(deposit.id, available_actions)
        audit = self._queue_audit(
            resource_type="deposit_request",
            resource_id=deposit.id,
            reference=f"deposit:{deposit.id}",
        )
        lock_state = self.treasury_service.get_admin_lock_state(
            self.session,
            actor=actor,
            resource_type="deposit_request",
            resource_id=deposit.id,
        )
        timestamps = self._deposit_timestamps(deposit)
        return {
            "id": deposit.id,
            "type": "deposit",
            "queue": queue_key,
            "reference": deposit.reference,
            "status": self._enum_value(deposit.status),
            "amount_fiat": self._amount(deposit.amount_fiat),
            "amount_coin": self._amount(deposit.amount_coin),
            "currency_code": deposit.currency_code,
            "payer_name": deposit.payer_name,
            "sender_bank": deposit.sender_bank,
            "transfer_reference": deposit.transfer_reference,
            "proof_attachment_id": deposit.proof_attachment_id,
            "created_at": deposit.created_at,
            "submitted_at": deposit.submitted_at,
            "reviewed_at": deposit.reviewed_at,
            "confirmed_at": deposit.confirmed_at,
            "rejected_at": deposit.rejected_at,
            "admin_notes": deposit.admin_notes,
            "user_id": deposit.user_id,
            "user_email": user.email if user is not None else "",
            "user_full_name": user.full_name if user is not None else None,
            "user_phone_number": user.phone_number if user is not None else None,
            "audit_reference": f"deposit:{deposit.id}",
            "severity": self._deposit_queue_severity(deposit),
            "timestamps": timestamps,
            "actor": self._queue_actor_payload(user=user, admin_user=admin_user),
            "escalation": self._deposit_escalation(deposit, available_actions),
            "audit": audit,
            "lock_state": lock_state,
            "action_state": lock_state.get("action_state", "enabled"),
            "blocked_reason": lock_state.get("blocked_reason"),
            "notes": {
                "admin": deposit.admin_notes,
                "user": None,
            },
            "proof_attachment_ids": [deposit.proof_attachment_id] if deposit.proof_attachment_id else [],
            "available_actions": available_actions,
            "action_endpoints": action_endpoints,
            "action_controls": self._queue_action_controls(
                item_type="deposit",
                action_endpoints=action_endpoints,
                business_state_actions=available_actions,
                wallet_state_actions=("approve",),
                lock_state=lock_state,
            ),
        }

    @staticmethod
    def _deposit_action_endpoints(deposit_id: str, actions: tuple[str, ...]) -> dict[str, str]:
        return {action: f"/api/v2/admin/finance/payment-queue/deposits/{deposit_id}/{action}" for action in actions}

    @staticmethod
    def _withdrawal_action_endpoints(withdrawal_id: str, actions: tuple[str, ...]) -> dict[str, str]:
        return {
            action: f"/api/v2/admin/finance/payment-queue/withdrawals/{withdrawal_id}/{action}" for action in actions
        }

    @staticmethod
    def _bid_action_endpoints(window_id: str, bid_id: str) -> dict[str, str]:
        return {
            action: f"/api/v2/admin/finance/payment-queue/bids/windows/{window_id}/bids/{bid_id}/{action}"
            for action in PAYMENT_QUEUE_BID_ACTION_REASONS
        }

    def _serialize_transfer_bid_queue_item(self, bid: object) -> dict[str, object]:
        payload = bid.model_dump(mode="json") if hasattr(bid, "model_dump") else dict(bid)
        bid_id = str(payload.get("id") or "")
        window_id = str(payload.get("window_id") or "")
        action_endpoints = self._bid_action_endpoints(window_id, bid_id)
        audit_reference = str(payload.get("audit_reference") or f"transfer-bid:{bid_id}")
        audit_trail = list(payload.get("audit_trail") or [])
        last_audit_event = audit_trail[0] if audit_trail else None
        payload.update(
            {
                "type": "transfer_bid",
                "queue": "bids",
                "audit_reference": audit_reference,
                "available_actions": tuple(PAYMENT_QUEUE_BID_ACTION_REASONS),
                "action_endpoints": action_endpoints,
                "action_controls": self._queue_action_controls(
                    item_type="transfer_bid",
                    action_endpoints=action_endpoints,
                    business_state_actions=tuple(),
                    wallet_state_actions=tuple(),
                ),
                "business_action_state": "audit_only",
                "timestamps": {
                    "created_at": payload.get("created_at"),
                    "updated_at": payload.get("updated_at"),
                    "submitted_at": payload.get("updated_at"),
                },
                "actor": {
                    "user": None,
                    "admin": None,
                },
                "escalation": {
                    "state": payload.get("escalation_state") or "read_only",
                    "requires_action": True,
                    "is_escalated": payload.get("severity") in {"high", "critical"},
                },
                "audit": {
                    "reference": audit_reference,
                    "resource_type": "transfer_bid",
                    "resource_id": bid_id,
                    "event_count": len(audit_trail),
                    "last_event_type": None if last_audit_event is None else last_audit_event.get("event_type"),
                    "last_event_at": None if last_audit_event is None else last_audit_event.get("updated_at"),
                    "last_actor_email": None,
                    "trail": audit_trail,
                },
                "notes": {
                    "admin": None,
                    "user": payload.get("notes"),
                },
            }
        )
        return payload

    def _review_payment_queue_withdrawal(
        self,
        *,
        actor: User,
        withdrawal_id: str,
        action: str,
        next_status: TreasuryWithdrawalStatus,
        admin_notes: str,
    ) -> dict[str, object]:
        withdrawal = self.treasury_service.review_withdrawal_status(
            self.session,
            actor=actor,
            withdrawal_id=withdrawal_id,
            status=next_status,
            admin_notes=admin_notes,
        )
        return self._payment_queue_action_result(
            action=action,
            item_type="withdrawal",
            item=self._serialize_withdrawal_queue_item(withdrawal, actor=actor),
            business_state_changed=True,
            wallet_state_changed=next_status == TreasuryWithdrawalStatus.REJECTED,
        )

    def _serialize_withdrawal_queue_item(
        self,
        withdrawal: TreasuryWithdrawalRequest,
        *,
        actor: User | None = None,
    ) -> dict[str, object]:
        user = self.session.get(User, withdrawal.user_id)
        admin_user = self.session.get(User, withdrawal.admin_user_id) if withdrawal.admin_user_id else None
        if withdrawal.status == TreasuryWithdrawalStatus.PENDING_REVIEW:
            queue_key = "pending"
        elif withdrawal.status == TreasuryWithdrawalStatus.APPROVED:
            queue_key = "approved"
        elif withdrawal.status == TreasuryWithdrawalStatus.REJECTED:
            queue_key = "rejected"
        else:
            queue_key = "pending"
        available_actions = {
            "pending": ("approve", "reject"),
            "approved": ("reinstate", "reject"),
            "rejected": tuple(),
        }.get(queue_key, tuple())
        action_endpoints = self._withdrawal_action_endpoints(withdrawal.id, available_actions)
        audit = self._queue_audit(
            resource_type="treasury_withdrawal",
            resource_id=withdrawal.id,
            reference=f"withdrawal:{withdrawal.id}",
        )
        lock_state = self.treasury_service.get_admin_lock_state(
            self.session,
            actor=actor,
            resource_type="treasury_withdrawal",
            resource_id=withdrawal.id,
        )
        return {
            "id": withdrawal.id,
            "type": "withdrawal",
            "queue": queue_key,
            "reference": withdrawal.reference,
            "status": self._enum_value(withdrawal.status),
            "amount_coin": self._amount(withdrawal.amount_coin),
            "amount_fiat": self._amount(withdrawal.amount_fiat),
            "fee_amount": self._amount(withdrawal.fee_amount),
            "total_debit": self._amount(withdrawal.total_debit),
            "net_amount": self._amount(withdrawal.net_amount),
            "source_scope": withdrawal.source_scope,
            "processor_mode": withdrawal.processor_mode,
            "payout_channel": withdrawal.payout_channel,
            "currency_code": withdrawal.currency_code,
            "bank_name": withdrawal.bank_name,
            "bank_account_number": withdrawal.bank_account_number,
            "bank_account_name": withdrawal.bank_account_name,
            "created_at": withdrawal.created_at,
            "reviewed_at": withdrawal.reviewed_at,
            "approved_at": withdrawal.approved_at,
            "processed_at": withdrawal.processed_at,
            "paid_at": withdrawal.paid_at,
            "rejected_at": withdrawal.rejected_at,
            "cancelled_at": withdrawal.cancelled_at,
            "admin_notes": withdrawal.admin_notes,
            "user_id": withdrawal.user_id,
            "user_email": user.email if user is not None else "",
            "user_full_name": user.full_name if user is not None else None,
            "user_phone_number": user.phone_number if user is not None else None,
            "audit_reference": f"withdrawal:{withdrawal.id}",
            "severity": self._withdrawal_queue_severity(withdrawal),
            "timestamps": self._withdrawal_timestamps(withdrawal),
            "actor": self._queue_actor_payload(user=user, admin_user=admin_user),
            "escalation": self._withdrawal_escalation(withdrawal, available_actions),
            "audit": audit,
            "lock_state": lock_state,
            "action_state": lock_state.get("action_state", "enabled"),
            "blocked_reason": lock_state.get("blocked_reason"),
            "notes": {
                "admin": withdrawal.admin_notes,
                "user": withdrawal.notes,
            },
            "available_actions": available_actions,
            "action_endpoints": action_endpoints,
            "action_controls": self._queue_action_controls(
                item_type="withdrawal",
                action_endpoints=action_endpoints,
                business_state_actions=available_actions,
                wallet_state_actions=("reject",),
                lock_state=lock_state,
            ),
        }

    def _queue_audit(
        self, *, resource_type: str, resource_id: str, reference: str, limit: int = 8
    ) -> dict[str, object]:
        events = self.session.scalars(
            select(TreasuryAuditEvent)
            .where(
                TreasuryAuditEvent.resource_type == resource_type,
                TreasuryAuditEvent.resource_id == resource_id,
            )
            .order_by(TreasuryAuditEvent.created_at.desc(), TreasuryAuditEvent.id.desc())
            .limit(limit)
        ).all()
        last_event = events[0] if events else None
        return {
            "reference": reference,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "event_count": len(events),
            "last_event_type": None if last_event is None else last_event.event_type,
            "last_event_at": None if last_event is None else last_event.created_at,
            "last_actor_email": None if last_event is None else last_event.actor_email,
            "trail": [
                {
                    "id": event.id,
                    "event_type": event.event_type,
                    "actor_user_id": event.actor_user_id,
                    "actor_email": event.actor_email,
                    "summary": event.summary,
                    "payload": event.payload,
                    "created_at": event.created_at,
                }
                for event in events
            ],
        }

    def _latest_control_event(
        self,
        *,
        resource_type: str,
        resource_id: str,
        event_types: tuple[str, ...],
    ) -> TreasuryAuditEvent | None:
        events = self.session.scalars(
            select(TreasuryAuditEvent)
            .where(
                TreasuryAuditEvent.resource_type == resource_type,
                TreasuryAuditEvent.resource_id == resource_id,
                TreasuryAuditEvent.event_type.in_(list(event_types)),
            )
            .order_by(TreasuryAuditEvent.created_at.desc())
            .limit(20)
        ).all()
        if not events:
            return None
        return sorted(
            events,
            key=lambda event: (
                self._parse_control_datetime((event.payload or {}).get("occurred_at"))
                or event.created_at
                or datetime.min.replace(tzinfo=timezone.utc)
            ),
            reverse=True,
        )[0]

    @staticmethod
    def _parse_control_datetime(value: object) -> datetime | None:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str) and value.strip():
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def _audit_event_payload(event: TreasuryAuditEvent) -> dict[str, object]:
        return {
            "id": event.id,
            "event_type": event.event_type,
            "actor_user_id": event.actor_user_id,
            "actor_email": event.actor_email,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "summary": event.summary,
            "created_at": event.created_at,
        }

    @staticmethod
    def _queue_action_controls(
        *,
        item_type: str,
        action_endpoints: dict[str, str],
        business_state_actions: tuple[str, ...],
        wallet_state_actions: tuple[str, ...],
        lock_state: dict[str, object] | None = None,
    ) -> dict[str, dict[str, object]]:
        blocked_reason = None if lock_state is None else lock_state.get("blocked_reason")
        is_blocked = (None if lock_state is None else lock_state.get("state")) == "locked_by_other"
        return {
            action: {
                "label": PAYMENT_QUEUE_ACTION_LABELS.get(action, action.replace("_", " ").title()),
                "method": "POST",
                "endpoint": endpoint,
                "item_type": item_type,
                "enabled": not is_blocked,
                "action_state": "blocked" if is_blocked else "enabled",
                "disabled_reason": blocked_reason if is_blocked else None,
                "requires_admin_notes": True,
                "auditable": True,
                "business_state_changes": action in business_state_actions,
                "wallet_state_changes": action in wallet_state_actions,
            }
            for action, endpoint in action_endpoints.items()
        }

    @staticmethod
    def _queue_actor_payload(*, user: User | None, admin_user: User | None) -> dict[str, object]:
        return {
            "user": AdminFinanceService._queue_actor_identity(user),
            "admin": AdminFinanceService._queue_actor_identity(admin_user),
        }

    @staticmethod
    def _queue_actor_identity(user: User | None) -> dict[str, object] | None:
        if user is None:
            return None
        role = getattr(user, "role", None)
        return {
            "id": user.id,
            "email": user.email,
            "full_name": getattr(user, "full_name", None),
            "phone_number": getattr(user, "phone_number", None),
            "role": role.value if hasattr(role, "value") else role,
        }

    @staticmethod
    def _deposit_timestamps(deposit: DepositRequest) -> dict[str, object]:
        return {
            "created_at": deposit.created_at,
            "updated_at": getattr(deposit, "updated_at", None),
            "submitted_at": deposit.submitted_at,
            "reviewed_at": deposit.reviewed_at,
            "confirmed_at": deposit.confirmed_at,
            "rejected_at": deposit.rejected_at,
            "expires_at": deposit.expires_at,
        }

    @staticmethod
    def _withdrawal_timestamps(withdrawal: TreasuryWithdrawalRequest) -> dict[str, object]:
        return {
            "created_at": withdrawal.created_at,
            "updated_at": getattr(withdrawal, "updated_at", None),
            "reviewed_at": withdrawal.reviewed_at,
            "approved_at": withdrawal.approved_at,
            "processed_at": withdrawal.processed_at,
            "paid_at": withdrawal.paid_at,
            "rejected_at": withdrawal.rejected_at,
            "cancelled_at": withdrawal.cancelled_at,
        }

    @staticmethod
    def _deposit_queue_severity(deposit: DepositRequest) -> str:
        status = deposit.status.value if hasattr(deposit.status, "value") else str(deposit.status)
        if status == DepositStatus.DISPUTED.value:
            return "high"
        if status in {DepositStatus.PAYMENT_SUBMITTED.value, DepositStatus.UNDER_REVIEW.value}:
            return "medium"
        return "low"

    @staticmethod
    def _withdrawal_queue_severity(withdrawal: TreasuryWithdrawalRequest) -> str:
        status = withdrawal.status.value if hasattr(withdrawal.status, "value") else str(withdrawal.status)
        if status == TreasuryWithdrawalStatus.DISPUTED.value:
            return "critical"
        if status in {TreasuryWithdrawalStatus.APPROVED.value, TreasuryWithdrawalStatus.PROCESSING.value}:
            return "high"
        if status == TreasuryWithdrawalStatus.PENDING_REVIEW.value:
            return "medium"
        return "low"

    def _deposit_escalation(self, deposit: DepositRequest, available_actions: tuple[str, ...]) -> dict[str, object]:
        status = self._enum_value(deposit.status)
        state_by_status = {
            DepositStatus.PAYMENT_SUBMITTED.value: "awaiting_admin_review",
            DepositStatus.UNDER_REVIEW.value: "under_review",
            DepositStatus.DISPUTED.value: "disputed",
            DepositStatus.CONFIRMED.value: "approved",
            DepositStatus.REJECTED.value: "rejected",
        }
        severity = self._deposit_queue_severity(deposit)
        return {
            "state": state_by_status.get(status, "read_only"),
            "requires_action": bool(available_actions),
            "is_escalated": severity in {"high", "critical"},
        }

    def _withdrawal_escalation(
        self, withdrawal: TreasuryWithdrawalRequest, available_actions: tuple[str, ...]
    ) -> dict[str, object]:
        status = self._enum_value(withdrawal.status)
        state_by_status = {
            TreasuryWithdrawalStatus.PENDING_REVIEW.value: "awaiting_admin_review",
            TreasuryWithdrawalStatus.APPROVED.value: "approved_for_processing",
            TreasuryWithdrawalStatus.PROCESSING.value: "processing",
            TreasuryWithdrawalStatus.DISPUTED.value: "disputed",
            TreasuryWithdrawalStatus.REJECTED.value: "rejected",
            TreasuryWithdrawalStatus.PAID.value: "paid",
            TreasuryWithdrawalStatus.CANCELLED.value: "cancelled",
        }
        severity = self._withdrawal_queue_severity(withdrawal)
        return {
            "state": state_by_status.get(status, "read_only"),
            "requires_action": bool(available_actions),
            "is_escalated": severity in {"high", "critical"},
        }

    @staticmethod
    def _payment_queue_action_result(
        *,
        action: str,
        item_type: str,
        item: dict[str, object],
        business_state_changed: bool,
        wallet_state_changed: bool,
    ) -> dict[str, object]:
        return {
            "action": action,
            "item_type": item_type,
            "action_state": "completed",
            "business_state_changed": business_state_changed,
            "wallet_state_changed": wallet_state_changed,
            "audit_reference": item.get("audit_reference"),
            "audit": item.get("audit"),
            "notes": item.get("notes"),
            "item": item,
        }

    @staticmethod
    def _enum_value(value: object) -> str:
        return str(value.value if hasattr(value, "value") else value)

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
        for name in (
            f"GTE_{normalized_provider}_WEBHOOK_SECRET",
            f"{normalized_provider}_WEBHOOK_SECRET",
        ):
            secret = os.getenv(name)
            if secret and secret.strip():
                return secret.strip()
        return None

    @staticmethod
    def _signature_optional(provider_key: str) -> bool:
        raw_value = os.getenv(f"GTE_{provider_key.strip().upper()}_WEBHOOK_SIGNATURE_OPTIONAL", "")
        return raw_value.strip().lower() in {"true", "1", "yes"}

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
        return {
            "payment_methods": self._canonical_cash_rail_payment_methods(),
            "deposit_mode": (
                settings.deposit_mode.value if hasattr(settings.deposit_mode, "value") else str(settings.deposit_mode)
            ),
            "withdrawal_mode": "manual",
            "currency_code": settings.currency_code,
            "min_withdrawal": self._amount(settings.min_withdrawal),
            "max_withdrawal": self._amount(settings.max_withdrawal),
            "pending_purchase_orders": self._count_pending_purchase_orders(),
            "pending_withdrawals": self._count_pending_withdrawals(),
            "pending_kyc": self._count_pending_kyc(),
            "automatic_deposits_enabled": getattr(settings.deposit_mode, "value", str(settings.deposit_mode))
            in {"automatic", "hybrid"},
            "automatic_withdrawals_enabled": False,
        }

    def _canonical_cash_rail_payment_methods(self) -> list[str]:
        if self.settings is None:
            return []
        seen_method_keys = {
            str(method.method_key).strip().lower()
            for method in PaymentGatewayService(session=self.session, settings=self.settings).list_methods()
        }
        return [
            display_name
            for method_key, display_name in CANONICAL_CASH_RAIL_METHODS.items()
            if method_key in seen_method_keys
        ]

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
