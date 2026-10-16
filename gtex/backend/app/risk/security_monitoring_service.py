from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from hashlib import sha1
import os
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.events import DomainEvent
from app.models.base import utcnow
from app.models.risk_ops import FraudCase, RiskSeverity, RiskSignal, RiskSignalType
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerEntry,
    LedgerEntryReason,
)
from app.risk_ops_engine.service import RiskOpsService
from app.wallets.service import TRADE_BUY_SOURCE_TAGS, TRADE_SELL_SOURCE_TAGS


@dataclass(slots=True)
class SecurityMonitoringService:
    session_factory: sessionmaker[Session]
    rapid_trade_window_minutes: int = field(default_factory=lambda: _env_int("GTE_RAPID_TRADE_WINDOW_MINUTES", 10))
    rapid_trade_entry_threshold: int = field(default_factory=lambda: _env_int("GTE_RAPID_TRADE_ENTRY_THRESHOLD", 4))
    rapid_trade_direction_changes: int = field(default_factory=lambda: _env_int("GTE_RAPID_TRADE_DIRECTION_CHANGES", 3))
    abnormal_profit_window_hours: int = field(default_factory=lambda: _env_int("GTE_ABNORMAL_PROFIT_WINDOW_HOURS", 24))
    abnormal_profit_min_amount: Decimal = field(
        default_factory=lambda: _env_decimal("GTE_ABNORMAL_PROFIT_MIN_AMOUNT", "1500.0000")
    )
    abnormal_profit_min_multiple: Decimal = field(
        default_factory=lambda: _env_decimal("GTE_ABNORMAL_PROFIT_MIN_MULTIPLE", "2.50")
    )
    multi_account_window_days: int = field(default_factory=lambda: _env_int("GTE_MULTI_ACCOUNT_WINDOW_DAYS", 30))
    shared_ip_account_threshold: int = field(default_factory=lambda: _env_int("GTE_SHARED_IP_ACCOUNT_THRESHOLD", 3))

    def handle_event(self, event: DomainEvent) -> None:
        if event.name == "wallet.transaction.appended":
            self._handle_wallet_transaction_event(event)
            return
        if event.name == "wallet.withdrawal.requested":
            self._handle_withdrawal_request_event(event)
            return
        if event.name == "market.offer.accepted":
            self._handle_market_offer_accepted_event(event)

    def record_login_attempt(
        self,
        *,
        email: str,
        success: bool,
        user_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
        device_id: str | None,
        path: str,
        failure_reason: str | None = None,
    ) -> None:
        normalized_email = str(email or "").strip().lower()
        if not normalized_email:
            normalized_email = "unknown"
        with self.session_factory() as session:
            risk_ops = RiskOpsService(session)
            risk_ops.log_audit(
                actor_user_id=user_id if success else None,
                action_key="auth.login.attempt",
                resource_type="auth_session",
                resource_id=None,
                detail="Login attempt processed.",
                metadata_json={
                    "email": normalized_email,
                    "path": path,
                    "ip_address": _clean(ip_address),
                    "user_agent": _clean(user_agent),
                    "device_id": _clean(device_id),
                    "success": success,
                    "failure_reason": _clean(failure_reason),
                },
                outcome="success" if success else "failed",
            )
            if success and user_id:
                self._record_login_signals(
                    session,
                    risk_ops=risk_ops,
                    user_id=user_id,
                    device_id=device_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    path=path,
                )
                self._flag_multi_account_activity(
                    session,
                    risk_ops=risk_ops,
                    user_id=user_id,
                    device_id=device_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            session.commit()

    def _handle_wallet_transaction_event(self, event: DomainEvent) -> None:
        payload = dict(event.payload or {})
        with self.session_factory() as session:
            risk_ops = RiskOpsService(session)
            reason = str(payload.get("reason") or "").strip().lower()
            actor_user_id = _clean_user_id(payload.get("created_by_user_id"))
            owner_user_ids = sorted(
                {
                    str(candidate).strip()
                    for candidate in (payload.get("owner_user_ids") or [])
                    if str(candidate).strip()
                }
            )
            if not actor_user_id and len(owner_user_ids) == 1:
                actor_user_id = owner_user_ids[0]
            risk_ops.log_audit(
                actor_user_id=actor_user_id,
                action_key="trade.executed" if reason == LedgerEntryReason.TRADE_SETTLEMENT.value else "wallet.transaction.recorded",
                resource_type="trade" if reason == LedgerEntryReason.TRADE_SETTLEMENT.value else "ledger_transaction",
                resource_id=str(payload.get("transaction_id") or "") or None,
                detail="Trade settlement recorded." if reason == LedgerEntryReason.TRADE_SETTLEMENT.value else "Wallet transaction recorded.",
                metadata_json={
                    "transaction_id": payload.get("transaction_id"),
                    "reason": reason,
                    "source_tag": payload.get("source_tag"),
                    "reference": payload.get("reference"),
                    "external_reference": payload.get("external_reference"),
                    "owner_user_ids": owner_user_ids,
                    "entry_count": len(payload.get("entries") or []),
                    "units": list(payload.get("units") or []),
                },
            )
            if reason == LedgerEntryReason.TRADE_SETTLEMENT.value:
                for user_id in owner_user_ids:
                    self._flag_rapid_trading_loop(session, risk_ops=risk_ops, user_id=user_id)
                    self._flag_abnormal_profit(session, risk_ops=risk_ops, user_id=user_id)
            session.commit()

    def _handle_withdrawal_request_event(self, event: DomainEvent) -> None:
        payload = dict(event.payload or {})
        user_id = _clean_user_id(payload.get("user_id"))
        with self.session_factory() as session:
            RiskOpsService(session).log_audit(
                actor_user_id=user_id,
                action_key="wallet.withdrawal.requested",
                resource_type="payout_request",
                resource_id=str(payload.get("payout_request_id") or "") or None,
                detail="Wallet withdrawal requested.",
                metadata_json={
                    "user_id": user_id,
                    "source_scope": payload.get("source_scope"),
                    "unit": payload.get("unit"),
                    "amount": payload.get("amount"),
                    "fee_amount": payload.get("fee_amount"),
                    "total_debit": payload.get("total_debit"),
                },
            )
            session.commit()

    def _handle_market_offer_accepted_event(self, event: DomainEvent) -> None:
        payload = dict(event.payload or {})
        with self.session_factory() as session:
            RiskOpsService(session).log_audit(
                actor_user_id=_clean_user_id(payload.get("seller_user_id")),
                action_key="trade.offer.accepted",
                resource_type="market_offer",
                resource_id=str(payload.get("offer_id") or "") or None,
                detail="Market offer accepted.",
                metadata_json={
                    "asset_id": payload.get("asset_id"),
                    "seller_user_id": payload.get("seller_user_id"),
                    "buyer_user_id": payload.get("buyer_user_id"),
                    "listing_id": payload.get("listing_id"),
                    "execution_id": payload.get("execution_id"),
                },
            )
            session.commit()

    def _record_login_signals(
        self,
        session: Session,
        *,
        risk_ops: RiskOpsService,
        user_id: str,
        device_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
        path: str,
    ) -> None:
        metadata = {
            "path": path,
            "user_agent": _clean(user_agent),
        }
        if device_id:
            risk_ops.ingest_signal(
                actor_user_id=user_id,
                user_id=user_id,
                signal_type=RiskSignalType.DEVICE_ID,
                signal_key="auth.login.device",
                signal_value=device_id,
                device_id=device_id,
                ip_address=ip_address,
                source="auth.login",
                confidence_score=Decimal("88.00"),
                metadata_json=metadata,
            )
        if ip_address:
            risk_ops.ingest_signal(
                actor_user_id=user_id,
                user_id=user_id,
                signal_type=RiskSignalType.IP_ADDRESS,
                signal_key="auth.login.ip",
                signal_value=ip_address,
                device_id=device_id,
                ip_address=ip_address,
                source="auth.login",
                confidence_score=Decimal("62.00"),
                metadata_json=metadata,
            )

    def _flag_multi_account_activity(
        self,
        session: Session,
        *,
        risk_ops: RiskOpsService,
        user_id: str,
        device_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        cutoff = utcnow() - timedelta(days=self.multi_account_window_days)
        if device_id:
            device_user_ids = sorted(
                {
                    str(candidate).strip()
                    for candidate in session.scalars(
                        select(RiskSignal.user_id).where(
                            RiskSignal.signal_type == RiskSignalType.DEVICE_ID,
                            RiskSignal.device_id == device_id,
                            RiskSignal.user_id.is_not(None),
                            RiskSignal.created_at >= cutoff,
                        )
                    ).all()
                    if isinstance(candidate, str) and candidate.strip()
                }
            )
            if len(device_user_ids) >= 2:
                for clustered_user_id in device_user_ids:
                    self._create_or_update_multi_account_case(
                        risk_ops=risk_ops,
                        user_id=clustered_user_id,
                        case_key=f"multi-account-device:{clustered_user_id}:{device_id}",
                        severity=RiskSeverity.HIGH,
                        confidence_score=Decimal("92.00"),
                        metadata_json={
                            "rule_key": "shared_device_cluster",
                            "device_id": device_id,
                            "linked_user_ids": device_user_ids,
                        },
                    )
        if ip_address:
            ip_signals = session.scalars(
                select(RiskSignal).where(
                    RiskSignal.signal_type == RiskSignalType.IP_ADDRESS,
                    RiskSignal.ip_address == ip_address,
                    RiskSignal.user_id.is_not(None),
                    RiskSignal.created_at >= cutoff,
                )
            ).all()
            ip_user_ids = sorted(
                {
                    signal.user_id
                    for signal in ip_signals
                    if signal.user_id
                    and (
                        not user_agent
                        or str((signal.metadata_json or {}).get("user_agent") or "").strip() == str(user_agent).strip()
                    )
                }
            )
            if len(ip_user_ids) >= self.shared_ip_account_threshold:
                user_agent_fingerprint = sha1(str(user_agent or "").encode("utf-8")).hexdigest()[:12]
                for clustered_user_id in ip_user_ids:
                    self._create_or_update_multi_account_case(
                        risk_ops=risk_ops,
                        user_id=clustered_user_id,
                        case_key=f"multi-account-ip:{clustered_user_id}:{ip_address}:{user_agent_fingerprint}",
                        severity=RiskSeverity.MEDIUM,
                        confidence_score=Decimal("78.00"),
                        metadata_json={
                            "rule_key": "shared_ip_cluster",
                            "ip_address": ip_address,
                            "linked_user_ids": ip_user_ids,
                            "user_agent": _clean(user_agent),
                        },
                    )

    def _create_or_update_multi_account_case(
        self,
        *,
        risk_ops: RiskOpsService,
        user_id: str,
        case_key: str,
        severity: RiskSeverity,
        confidence_score: Decimal,
        metadata_json: dict[str, Any],
    ) -> FraudCase:
        case, _created = risk_ops.create_or_update_fraud_case(
            actor_user_id=None,
            user_id=user_id,
            fraud_type="multi_account_activity",
            title="Potential multi-account activity detected",
            description="Login telemetry linked this account to a shared device or network cluster.",
            severity=severity,
            confidence_score=confidence_score,
            metadata_json=metadata_json,
            case_key=case_key,
        )
        return case

    def _flag_rapid_trading_loop(
        self,
        session: Session,
        *,
        risk_ops: RiskOpsService,
        user_id: str,
    ) -> None:
        recent_entries = self._load_trade_entries(
            session,
            user_id=user_id,
            since=utcnow() - timedelta(minutes=self.rapid_trade_window_minutes),
        )
        if len(recent_entries) < self.rapid_trade_entry_threshold:
            return
        by_asset: dict[str, list[LedgerEntry]] = defaultdict(list)
        for entry in recent_entries:
            by_asset[self._trade_asset_key(entry.reference)].append(entry)
        for asset_key, entries in by_asset.items():
            if len(entries) < self.rapid_trade_entry_threshold:
                continue
            directions = [self._trade_direction(entry) for entry in entries]
            buy_count = sum(1 for direction in directions if direction == "buy")
            sell_count = sum(1 for direction in directions if direction == "sell")
            direction_changes = sum(
                1
                for index in range(1, len(directions))
                if directions[index] != directions[index - 1]
            )
            if (
                buy_count
                and sell_count
                and direction_changes >= self.rapid_trade_direction_changes
            ):
                risk_ops.ingest_signal(
                    actor_user_id=None,
                    user_id=user_id,
                    signal_type=RiskSignalType.TRANSACTION_PATTERN,
                    signal_key="rapid_trading_loop",
                    signal_value=asset_key,
                    source="trade_surveillance",
                    confidence_score=Decimal("82.00"),
                    metadata_json={
                        "asset_key": asset_key,
                        "window_minutes": self.rapid_trade_window_minutes,
                        "trade_entry_count": len(entries),
                        "buy_count": buy_count,
                        "sell_count": sell_count,
                        "direction_changes": direction_changes,
                    },
                )
                risk_ops.create_or_update_fraud_case(
                    actor_user_id=None,
                    user_id=user_id,
                    fraud_type="rapid_trading_loop",
                    title="Rapid trading loop detected",
                    description="Alternating buy and sell activity crossed the rapid-loop threshold for the same trade target.",
                    severity=RiskSeverity.HIGH,
                    confidence_score=Decimal("82.00"),
                    metadata_json={
                        "asset_key": asset_key,
                        "window_minutes": self.rapid_trade_window_minutes,
                        "trade_entry_count": len(entries),
                        "buy_count": buy_count,
                        "sell_count": sell_count,
                        "direction_changes": direction_changes,
                        "references": [entry.reference for entry in entries[-4:]],
                    },
                    case_key=f"rapid-trading-loop:{user_id}:{asset_key}",
                )
                return

    def _flag_abnormal_profit(
        self,
        session: Session,
        *,
        risk_ops: RiskOpsService,
        user_id: str,
    ) -> None:
        trade_entries = self._load_trade_entries(
            session,
            user_id=user_id,
            since=utcnow() - timedelta(hours=self.abnormal_profit_window_hours),
        )
        if not trade_entries:
            return
        total_buys = sum(
            (abs(Decimal(entry.amount)) for entry in trade_entries if self._trade_direction(entry) == "buy"),
            start=Decimal("0.0000"),
        )
        total_sells = sum(
            (Decimal(entry.amount) for entry in trade_entries if self._trade_direction(entry) == "sell"),
            start=Decimal("0.0000"),
        )
        profit = total_sells - total_buys
        if profit < self.abnormal_profit_min_amount:
            return
        if total_buys > Decimal("0.0000"):
            if total_sells < total_buys * self.abnormal_profit_min_multiple:
                return
            profit_multiple = (total_sells / total_buys).quantize(Decimal("0.01"))
        else:
            profit_multiple = Decimal("999.99")
        risk_ops.ingest_signal(
            actor_user_id=None,
            user_id=user_id,
            signal_type=RiskSignalType.TRANSACTION_PATTERN,
            signal_key="abnormal_profit",
            signal_value=str(profit),
            source="trade_surveillance",
            confidence_score=Decimal("86.00"),
            metadata_json={
                "window_hours": self.abnormal_profit_window_hours,
                "total_buys": str(total_buys),
                "total_sells": str(total_sells),
                "profit": str(profit),
                "profit_multiple": str(profit_multiple),
            },
        )
        risk_ops.create_or_update_fraud_case(
            actor_user_id=None,
            user_id=user_id,
            fraud_type="abnormal_profit",
            title="Abnormal realized trade profit detected",
            description="Realized trade proceeds exceeded the configured profit thresholds and were flagged for review.",
            severity=RiskSeverity.HIGH,
            confidence_score=Decimal("86.00"),
            metadata_json={
                "window_hours": self.abnormal_profit_window_hours,
                "total_buys": str(total_buys),
                "total_sells": str(total_sells),
                "profit": str(profit),
                "profit_multiple": str(profit_multiple),
            },
            case_key=f"abnormal-profit:{user_id}",
        )

    def _load_trade_entries(
        self,
        session: Session,
        *,
        user_id: str,
        since,
    ) -> list[LedgerEntry]:
        return list(
            session.scalars(
                select(LedgerEntry)
                .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
                .where(
                    LedgerAccount.owner_user_id == user_id,
                    LedgerAccount.kind == LedgerAccountKind.USER,
                    LedgerEntry.reason == LedgerEntryReason.TRADE_SETTLEMENT,
                    LedgerEntry.created_at >= since,
                )
                .order_by(LedgerEntry.created_at.asc(), LedgerEntry.id.asc())
            ).all()
        )

    def _trade_direction(self, entry: LedgerEntry) -> str:
        if entry.source_tag in TRADE_BUY_SOURCE_TAGS or Decimal(entry.amount) < Decimal("0.0000"):
            return "buy"
        if entry.source_tag in TRADE_SELL_SOURCE_TAGS or Decimal(entry.amount) > Decimal("0.0000"):
            return "sell"
        return "unknown"

    def _trade_asset_key(self, reference: str | None) -> str:
        candidate = str(reference or "").strip().lower()
        if not candidate:
            return "unknown"
        if ":" not in candidate:
            return candidate[:80]
        parts = candidate.split(":")
        if len(parts) >= 2 and parts[0] in {"gtex-market-buy", "gtex-market-sell", "player-share-buy", "player-share-sell"}:
            return parts[1][:80]
        return candidate[:80]


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate or None


def _clean_user_id(value: Any) -> str | None:
    candidate = _clean(value)
    if candidate is None:
        return None
    return candidate[:36]


def _env_decimal(name: str, default: str) -> Decimal:
    try:
        return Decimal(str(os.getenv(name, default)).strip())
    except Exception:
        return Decimal(default)


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(str(os.getenv(name, str(default))).strip()))
    except Exception:
        return default


__all__ = ["SecurityMonitoringService"]
