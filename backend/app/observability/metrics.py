from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import logging
from threading import RLock
from typing import Any

from fastapi import Response
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        GCCollector,
        Gauge,
        Histogram,
        PlatformCollector,
        ProcessCollector,
        generate_latest,
        start_http_server,
    )

    _PROMETHEUS_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    class CollectorRegistry:  # type: ignore[override]
        pass

    class _MetricStub:
        def labels(self, *args: Any, **kwargs: Any) -> "_MetricStub":
            return self

        def inc(self, amount: float = 1.0) -> None:
            return None

        def dec(self, amount: float = 1.0) -> None:
            return None

        def observe(self, value: float) -> None:
            return None

        def set(self, value: float) -> None:
            return None

        def set_function(self, fn) -> None:
            return None

    def Counter(*args: Any, **kwargs: Any) -> _MetricStub:  # type: ignore[override]
        return _MetricStub()

    def Gauge(*args: Any, **kwargs: Any) -> _MetricStub:  # type: ignore[override]
        return _MetricStub()

    def Histogram(*args: Any, **kwargs: Any) -> _MetricStub:  # type: ignore[override]
        return _MetricStub()

    def GCCollector(*args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        return None

    def PlatformCollector(*args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        return None

    def ProcessCollector(*args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        return None

    def generate_latest(registry: Any) -> bytes:  # type: ignore[override]
        return b""

    def start_http_server(*args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        return None

    _PROMETHEUS_AVAILABLE = False

try:
    import psutil
except Exception:  # pragma: no cover - optional dependency
    psutil = None
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.events import DomainEvent
from app.models.treasury import DepositRequest, DepositStatus, TreasuryWithdrawalRequest, TreasuryWithdrawalStatus
from app.models.wallet import LedgerAccount, LedgerBalanceProjection

logger = logging.getLogger(__name__)

HTTP_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
MATCH_DURATION_BUCKETS = (15, 30, 45, 60, 90, 120, 180, 240, 300, 600, 900)
WORKER_DURATION_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120)


def _parse_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _parse_datetime(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        return value
    candidate = str(value).strip()
    if not candidate:
        return None
    return datetime.fromisoformat(candidate.replace("Z", "+00:00"))


def _enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


@dataclass
class GTexMetrics:
    runtime_name: str
    session_factory: sessionmaker[Session] | None = None
    registry: CollectorRegistry = field(default_factory=CollectorRegistry)
    _started_server: bool = False
    _balances: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)
    _process: Any | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        GCCollector(registry=self.registry)
        PlatformCollector(registry=self.registry)
        try:
            ProcessCollector(registry=self.registry)
        except Exception:
            logger.exception("observability.metrics.process_collector_failed")

        self.domain_events_total = Counter(
            "gtex_domain_events_total",
            "Total domain events observed by the runtime.",
            ("event_name",),
            registry=self.registry,
        )
        self.http_requests_total = Counter(
            "gtex_http_requests_total",
            "Total HTTP requests handled by the API.",
            ("method", "route", "status_code"),
            registry=self.registry,
        )
        self.http_request_duration_seconds = Histogram(
            "gtex_http_request_duration_seconds",
            "HTTP request latency in seconds.",
            ("method", "route", "status_code"),
            buckets=HTTP_LATENCY_BUCKETS,
            registry=self.registry,
        )
        self.http_requests_in_progress = Gauge(
            "gtex_http_requests_in_progress",
            "HTTP requests currently being processed.",
            registry=self.registry,
        )
        self.matches_total = Counter(
            "gtex_matches_total",
            "Completed matches grouped by competition and outcome.",
            ("competition_type", "result"),
            registry=self.registry,
        )
        self.match_duration_seconds = Histogram(
            "gtex_match_duration_seconds",
            "Rendered match duration in seconds.",
            ("competition_type",),
            buckets=MATCH_DURATION_BUCKETS,
            registry=self.registry,
        )
        self.match_queue_delay_seconds = Gauge(
            "gtex_match_queue_delay_seconds",
            "Observed delay between queueing and match execution start.",
            ("competition_type",),
            registry=self.registry,
        )
        self.match_queue_delay_observed_seconds = Histogram(
            "gtex_match_queue_delay_observed_seconds",
            "Distribution of queue delays for match execution.",
            ("competition_type",),
            buckets=HTTP_LATENCY_BUCKETS + MATCH_DURATION_BUCKETS,
            registry=self.registry,
        )
        self.queue_messages_total = Counter(
            "gtex_queue_messages_total",
            "Queue messages handled by runtime and outcome.",
            ("queue_name", "job_name", "result"),
            registry=self.registry,
        )
        self.worker_jobs_total = Counter(
            "gtex_worker_jobs_total",
            "Worker jobs processed by runtime and outcome.",
            ("job_name", "result"),
            registry=self.registry,
        )
        self.worker_job_duration_seconds = Histogram(
            "gtex_worker_job_duration_seconds",
            "Worker job execution duration in seconds.",
            ("job_name", "result"),
            buckets=WORKER_DURATION_BUCKETS,
            registry=self.registry,
        )
        self.feed_refresh_total = Counter(
            "gtex_feed_refresh_total",
            "Feed refresh requests handled by feed name and outcome.",
            ("feed_name", "result"),
            registry=self.registry,
        )
        self.feed_refresh_duration_seconds = Histogram(
            "gtex_feed_refresh_duration_seconds",
            "Feed refresh latency in seconds.",
            ("feed_name", "result"),
            buckets=WORKER_DURATION_BUCKETS,
            registry=self.registry,
        )
        self.creator_earnings_events_total = Counter(
            "gtex_creator_earnings_events_total",
            "Committed creator earnings events by type and outcome.",
            ("event_type", "result"),
            registry=self.registry,
        )
        self.creator_earnings_credit_total = Counter(
            "gtex_creator_earnings_credit_total",
            "Committed creator earnings credit throughput by event type.",
            ("event_type",),
            registry=self.registry,
        )
        self.dead_letters_total = Counter(
            "gtex_dead_letters_total",
            "Dead-lettered event count by consumer and event type.",
            ("consumer_name", "event_type"),
            registry=self.registry,
        )
        self.outbox_relay_total = Counter(
            "gtex_outbox_relay_total",
            "Outbox relay publish outcomes.",
            ("result",),
            registry=self.registry,
        )
        self.total_deposits_amount = Gauge(
            "gtex_total_deposits_amount",
            "Lifetime confirmed deposits tracked by the control tower.",
            ("unit",),
            registry=self.registry,
        )
        self.total_withdrawals_amount = Gauge(
            "gtex_total_withdrawals_amount",
            "Lifetime withdrawals tracked by status.",
            ("unit", "status"),
            registry=self.registry,
        )
        self.withdrawal_transitions_total = Counter(
            "gtex_withdrawal_transitions_total",
            "Withdrawal lifecycle transitions observed by status.",
            ("status",),
            registry=self.registry,
        )
        self.circulating_supply = Gauge(
            "gtex_circulating_supply",
            "User-held GTex in circulation, including user escrow balances.",
            ("unit",),
            registry=self.registry,
        )
        self.treasury_balance = Gauge(
            "gtex_treasury_balance",
            "Treasury ledger balance by account code and unit.",
            ("unit", "account_code"),
            registry=self.registry,
        )
        self.worker_cpu_percent = Gauge(
            "gtex_worker_cpu_percent",
            "Current process CPU utilization percentage.",
            ("runtime",),
            registry=self.registry,
        )
        self._process = psutil.Process() if psutil is not None else None
        if self._process is not None:
            self._process.cpu_percent(interval=None)
        self.worker_cpu_percent.labels(self.runtime_name).set_function(self._read_cpu_percent)

        for status in ("requested", "paid", "failed"):
            self.total_withdrawals_amount.labels("coin", status).set(0)

    def _read_cpu_percent(self) -> float:
        if self._process is None:
            return 0.0
        try:
            return float(self._process.cpu_percent(interval=None))
        except Exception:
            return 0.0

    def render_latest(self) -> bytes:
        return generate_latest(self.registry)

    def metrics_response(self) -> Response:
        return Response(content=self.render_latest(), media_type=CONTENT_TYPE_LATEST)

    def start_http_server(self, port: int) -> None:
        if self._started_server or port <= 0:
            return
        start_http_server(port, addr="0.0.0.0", registry=self.registry)
        self._started_server = True
        logger.info("observability.metrics.server_started runtime=%s port=%s", self.runtime_name, port)

    def refresh_from_database(self) -> None:
        if self.session_factory is None:
            return
        try:
            with self.session_factory() as session:
                self._refresh_balances(session)
                self._refresh_lifetime_totals(session)
        except Exception:
            logger.exception("observability.metrics.refresh_failed runtime=%s", self.runtime_name)

    def _refresh_balances(self, session: Session) -> None:
        rows = session.execute(
            select(
                LedgerAccount.code,
                LedgerAccount.unit,
                LedgerBalanceProjection.balance,
            ).join(
                LedgerBalanceProjection,
                LedgerBalanceProjection.account_id == LedgerAccount.id,
            )
        ).all()
        with self._lock:
            self._balances.clear()
            for code, unit, balance in rows:
                self._balances[(str(code), _enum_value(unit))] = _parse_decimal(balance)
            self._update_balance_gauges_locked()

    def _refresh_lifetime_totals(self, session: Session) -> None:
        confirmed_deposits = session.scalar(
            select(func.coalesce(func.sum(DepositRequest.amount_coin), 0)).where(
                DepositRequest.status == DepositStatus.CONFIRMED
            )
        )
        self.total_deposits_amount.labels("coin").set(float(_parse_decimal(confirmed_deposits)))

        withdrawal_rows = session.execute(
            select(
                TreasuryWithdrawalRequest.status,
                func.coalesce(func.sum(TreasuryWithdrawalRequest.amount_coin), 0),
            ).group_by(TreasuryWithdrawalRequest.status)
        ).all()
        status_totals = {str(_enum_value(status)): _parse_decimal(total) for status, total in withdrawal_rows}
        self.total_withdrawals_amount.labels("coin", "requested").set(float(sum(status_totals.values(), Decimal("0"))))
        self.total_withdrawals_amount.labels("coin", "paid").set(
            float(status_totals.get(TreasuryWithdrawalStatus.PAID.value, Decimal("0")))
        )
        failed_total = (
            status_totals.get(TreasuryWithdrawalStatus.REJECTED.value, Decimal("0"))
            + status_totals.get(TreasuryWithdrawalStatus.CANCELLED.value, Decimal("0"))
        )
        self.total_withdrawals_amount.labels("coin", "failed").set(float(failed_total))

    def record_http_request(self, *, method: str, route: str, status_code: int, duration_seconds: float) -> None:
        status_code_label = str(status_code)
        self.http_requests_total.labels(method.upper(), route, status_code_label).inc()
        self.http_request_duration_seconds.labels(method.upper(), route, status_code_label).observe(duration_seconds)

    def record_queue_message(self, *, queue_name: str, job_name: str, result: str) -> None:
        self.queue_messages_total.labels(queue_name, job_name, result).inc()

    def record_worker_job(self, *, job_name: str, result: str, duration_seconds: float) -> None:
        self.worker_jobs_total.labels(job_name, result).inc()
        self.worker_job_duration_seconds.labels(job_name, result).observe(duration_seconds)

    def record_feed_refresh(self, *, feed_name: str, result: str, duration_seconds: float) -> None:
        self.feed_refresh_total.labels(feed_name, result).inc()
        self.feed_refresh_duration_seconds.labels(feed_name, result).observe(max(float(duration_seconds), 0.0))

    def record_creator_earnings(
        self,
        *,
        event_type: str,
        result: str,
        earnings_delta_credit: Decimal | float,
    ) -> None:
        self.creator_earnings_events_total.labels(event_type, result).inc()
        credit_value = float(_parse_decimal(earnings_delta_credit))
        if credit_value > 0:
            self.creator_earnings_credit_total.labels(event_type).inc(credit_value)

    def record_dead_letter(self, *, consumer_name: str, event_type: str) -> None:
        self.dead_letters_total.labels(consumer_name, event_type).inc()

    def record_outbox_relay(self, *, result: str) -> None:
        self.outbox_relay_total.labels(result).inc()

    def record_queue_delay(self, *, competition_type: str, delay_seconds: float) -> None:
        normalized_delay = max(0.0, float(delay_seconds))
        self.match_queue_delay_seconds.labels(competition_type).set(normalized_delay)
        self.match_queue_delay_observed_seconds.labels(competition_type).observe(normalized_delay)

    def handle_event(self, event: DomainEvent) -> None:
        self.domain_events_total.labels(event.name).inc()
        payload = dict(event.payload or {})
        if event.name == "wallet.balance.updated":
            self._handle_balance_update(payload)
        elif event.name == "wallet.transaction.appended":
            self._handle_wallet_transaction(payload)
        elif event.name == "wallet.withdrawal.requested":
            self._handle_withdrawal_requested(payload)
        elif event.name == "competition_engine.queue.match_simulation.queued":
            self.record_queue_message(queue_name="match_simulation", job_name="match_simulation", result="queued")
        elif event.name == "competition.match.execution.started":
            self._handle_match_execution_started(event, payload)
        elif event.name == "competition.match.result.generated":
            self._handle_match_result(payload)

    def _handle_balance_update(self, payload: Mapping[str, Any]) -> None:
        account_code = str(payload.get("account_code") or "").strip()
        unit = str(payload.get("unit") or "").strip() or "coin"
        if not account_code:
            return
        balance = _parse_decimal(payload.get("balance"))
        with self._lock:
            self._balances[(account_code, unit)] = balance
            self._update_balance_gauges_locked()

    def _update_balance_gauges_locked(self) -> None:
        circulating_by_unit: dict[str, Decimal] = {}
        treasury_by_account: dict[tuple[str, str], Decimal] = {}
        for (account_code, unit), balance in self._balances.items():
            if account_code.startswith("user:"):
                circulating_by_unit[unit] = circulating_by_unit.get(unit, Decimal("0")) + balance
            if account_code.endswith(":treasury"):
                treasury_by_account[(unit, account_code)] = balance

        for unit, total in circulating_by_unit.items():
            self.circulating_supply.labels(unit).set(float(total))
        for (unit, account_code), balance in treasury_by_account.items():
            self.treasury_balance.labels(unit, account_code).set(float(balance))

    def _handle_wallet_transaction(self, payload: Mapping[str, Any]) -> None:
        reason = str(payload.get("reason") or "").strip().lower()
        entries = payload.get("entries") or []
        metadata = payload.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        if reason == "deposit":
            for unit, amount in self._positive_user_credits(entries).items():
                self.total_deposits_amount.labels(unit).inc(float(amount))
        withdrawal_meta = metadata.get("withdrawal") if isinstance(metadata.get("withdrawal"), dict) else {}
        action = str(withdrawal_meta.get("action") or "").strip().lower()
        fee_amount = _parse_decimal(withdrawal_meta.get("fee_amount"))
        total_debit = _parse_decimal(withdrawal_meta.get("total_debit"))
        net_amount = total_debit - fee_amount if total_debit >= fee_amount else Decimal("0")
        unit = self._event_unit(entries, fallback="coin")
        if reason == "withdrawal_settlement" or action == "settle":
            self.total_withdrawals_amount.labels(unit, "paid").inc(float(net_amount))
            self.withdrawal_transitions_total.labels("paid").inc()
        elif action == "release":
            self.total_withdrawals_amount.labels(unit, "failed").inc(float(net_amount))
            self.withdrawal_transitions_total.labels("failed").inc()

    def _handle_withdrawal_requested(self, payload: Mapping[str, Any]) -> None:
        unit = str(payload.get("unit") or "coin").strip().lower() or "coin"
        amount = _parse_decimal(payload.get("amount"))
        self.total_withdrawals_amount.labels(unit, "requested").inc(float(amount))
        self.withdrawal_transitions_total.labels("requested").inc()

    def _handle_match_execution_started(self, event: DomainEvent, payload: Mapping[str, Any]) -> None:
        competition_type = self._competition_type(payload)
        queued_at = _parse_datetime(payload.get("queued_at"))
        if queued_at is None:
            return
        delay_seconds = (event.occurred_at - queued_at).total_seconds()
        self.record_queue_delay(competition_type=competition_type, delay_seconds=delay_seconds)

    def _handle_match_result(self, payload: Mapping[str, Any]) -> None:
        competition_type = self._competition_type(payload)
        duration_seconds = float(payload.get("presentation_duration_seconds") or 0.0)
        if duration_seconds > 0:
            self.match_duration_seconds.labels(competition_type).observe(duration_seconds)
        winner_team_id = str(payload.get("winner_team_id") or "").strip() or None
        home_club_id = str(
            payload.get("home_club_id")
            or ((payload.get("home_club") or {}) if isinstance(payload.get("home_club"), dict) else {}).get("club_id")
            or ""
        ).strip()
        away_club_id = str(
            payload.get("away_club_id")
            or ((payload.get("away_club") or {}) if isinstance(payload.get("away_club"), dict) else {}).get("club_id")
            or ""
        ).strip()
        if winner_team_id is None:
            result = "draw"
        elif winner_team_id == home_club_id:
            result = "home_win"
        elif winner_team_id == away_club_id:
            result = "away_win"
        else:
            result = "unknown"
        self.matches_total.labels(competition_type, result).inc()

    @staticmethod
    def _event_unit(entries: Any, *, fallback: str) -> str:
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                unit = str(entry.get("unit") or "").strip().lower()
                if unit:
                    return unit
        return fallback

    @staticmethod
    def _positive_user_credits(entries: Any) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        if not isinstance(entries, list):
            return totals
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            account_code = str(entry.get("account_code") or "").strip()
            amount = _parse_decimal(entry.get("amount"))
            if amount <= 0 or not account_code.startswith("user:") or account_code.endswith(":escrow"):
                continue
            unit = str(entry.get("unit") or "coin").strip().lower() or "coin"
            totals[unit] = totals.get(unit, Decimal("0")) + amount
        return totals

    @staticmethod
    def _competition_type(payload: Mapping[str, Any]) -> str:
        raw = payload.get("competition_type")
        return str(_enum_value(raw) if raw is not None else "unknown").strip().lower() or "unknown"
