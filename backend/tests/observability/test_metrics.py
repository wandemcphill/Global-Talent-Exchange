from __future__ import annotations

from datetime import datetime, timedelta, timezone

from prometheus_client.parser import text_string_to_metric_families

from app.core.events import DomainEvent
from app.observability.metrics import GTexMetrics


def _sample_value(samples_by_name: dict[str, list[object]], name: str, **labels: str) -> float:
    for sample in samples_by_name.get(name, []):
        if getattr(sample, "labels", {}) == labels:
            return float(sample.value)
    raise AssertionError(f"Missing sample {name} with labels {labels}")


def test_metrics_capture_economy_and_gameplay_events() -> None:
    metrics = GTexMetrics(runtime_name="test")
    queued_at = datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
    started_at = queued_at + timedelta(seconds=12)

    metrics.handle_event(
        DomainEvent(
            name="wallet.balance.updated",
            payload={
                "account_code": "user:user-1:coin",
                "balance": "12.5",
                "unit": "coin",
            },
        )
    )
    metrics.handle_event(
        DomainEvent(
            name="wallet.balance.updated",
            payload={
                "account_code": "user:user-1:coin:escrow",
                "balance": "2.5",
                "unit": "coin",
            },
        )
    )
    metrics.handle_event(
        DomainEvent(
            name="wallet.balance.updated",
            payload={
                "account_code": "platform:coin:treasury",
                "balance": "40",
                "unit": "coin",
            },
        )
    )
    metrics.handle_event(
        DomainEvent(
            name="wallet.transaction.appended",
            payload={
                "reason": "deposit",
                "entries": [
                    {
                        "account_code": "user:user-2:coin",
                        "amount": "20",
                        "unit": "coin",
                    }
                ],
                "metadata": {},
            },
        )
    )
    metrics.handle_event(
        DomainEvent(
            name="wallet.withdrawal.requested",
            payload={
                "unit": "coin",
                "amount": "15",
            },
        )
    )
    metrics.handle_event(
        DomainEvent(
            name="competition.match.execution.started",
            payload={
                "competition_type": "league",
                "queued_at": queued_at.isoformat(),
            },
            occurred_at=started_at,
        )
    )
    metrics.handle_event(
        DomainEvent(
            name="competition.match.result.generated",
            payload={
                "competition_type": "league",
                "winner_team_id": "club-home",
                "home_club_id": "club-home",
                "away_club_id": "club-away",
                "presentation_duration_seconds": 90,
            },
        )
    )

    rendered = metrics.render_latest().decode("utf-8")
    samples_by_name: dict[str, list[object]] = {}
    for family in text_string_to_metric_families(rendered):
        for sample in family.samples:
            samples_by_name.setdefault(sample.name, []).append(sample)

    assert _sample_value(samples_by_name, "gtex_circulating_supply", unit="coin") == 15.0
    assert (
        _sample_value(
            samples_by_name,
            "gtex_treasury_balance",
            unit="coin",
            account_code="platform:coin:treasury",
        )
        == 40.0
    )
    assert _sample_value(samples_by_name, "gtex_total_deposits_amount", unit="coin") == 20.0
    assert (
        _sample_value(
            samples_by_name,
            "gtex_total_withdrawals_amount",
            unit="coin",
            status="requested",
        )
        == 15.0
    )
    assert _sample_value(samples_by_name, "gtex_match_queue_delay_seconds", competition_type="league") == 12.0
    assert _sample_value(samples_by_name, "gtex_matches_total", competition_type="league", result="home_win") == 1.0


def test_metrics_capture_unity_live_observability_signals() -> None:
    metrics = GTexMetrics(runtime_name="test")

    metrics.record_unity_live_access(action="issue", result="success")
    metrics.record_unity_live_access(action="refresh", result="invalid_token")
    metrics.record_unity_live_payload(transport="http", result="success")
    metrics.record_unity_live_payload(transport="websocket", result="error")
    metrics.record_unity_live_websocket_event(event="accepted", result="success")
    metrics.record_unity_live_websocket_event(event="stale_state", result="detected")
    metrics.record_unity_live_generated_match(result="started")
    metrics.record_unity_live_generated_match(result="missing_stream")

    rendered = metrics.render_latest().decode("utf-8")
    samples_by_name: dict[str, list[object]] = {}
    for family in text_string_to_metric_families(rendered):
        for sample in family.samples:
            samples_by_name.setdefault(sample.name, []).append(sample)

    assert (
        _sample_value(
            samples_by_name,
            "gtex_unity_live_access_total",
            action="issue",
            result="success",
        )
        == 1.0
    )
    assert (
        _sample_value(
            samples_by_name,
            "gtex_unity_live_access_total",
            action="refresh",
            result="invalid_token",
        )
        == 1.0
    )
    assert (
        _sample_value(
            samples_by_name,
            "gtex_unity_live_payload_total",
            transport="http",
            result="success",
        )
        == 1.0
    )
    assert (
        _sample_value(
            samples_by_name,
            "gtex_unity_live_payload_total",
            transport="websocket",
            result="error",
        )
        == 1.0
    )
    assert (
        _sample_value(
            samples_by_name,
            "gtex_unity_live_websocket_events_total",
            event="accepted",
            result="success",
        )
        == 1.0
    )
    assert (
        _sample_value(
            samples_by_name,
            "gtex_unity_live_websocket_events_total",
            event="stale_state",
            result="detected",
        )
        == 1.0
    )
    assert (
        _sample_value(
            samples_by_name,
            "gtex_unity_live_generated_match_total",
            result="started",
        )
        == 1.0
    )
    assert (
        _sample_value(
            samples_by_name,
            "gtex_unity_live_generated_match_total",
            result="missing_stream",
        )
        == 1.0
    )
