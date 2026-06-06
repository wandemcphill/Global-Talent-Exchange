from __future__ import annotations

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from prometheus_client.parser import text_string_to_metric_families

from app.observability.metrics import GTexMetrics
from app.observability.middleware import ObservabilityMiddleware


def _samples_by_name(metrics: GTexMetrics) -> dict[str, list[object]]:
    rendered = metrics.render_latest().decode("utf-8")
    samples: dict[str, list[object]] = {}
    for family in text_string_to_metric_families(rendered):
        for sample in family.samples:
            samples.setdefault(sample.name, []).append(sample)
    return samples


def _sample_value(samples_by_name: dict[str, list[object]], name: str, **labels: str) -> float:
    for sample in samples_by_name.get(name, []):
        if getattr(sample, "labels", {}) == labels:
            return float(sample.value)
    raise AssertionError(f"Missing sample {name} with labels {labels}")


def test_metrics_capture_runtime_probe_and_boot_thresholds() -> None:
    metrics = GTexMetrics(runtime_name="test")

    metrics.record_runtime_probe(
        probe="health",
        status_code=200,
        duration_seconds=1.25,
        slow_threshold_seconds=1.0,
    )
    metrics.record_runtime_probe(
        probe="ready",
        status_code=503,
        duration_seconds=0.5,
        slow_threshold_seconds=2.5,
    )
    metrics.record_boot_phase(
        phase="schema_check",
        result="success",
        duration_seconds=3.5,
        threshold_seconds=2.0,
    )
    metrics.record_boot_phase(
        phase="outbox_relay",
        result="skipped",
        duration_seconds=0.1,
        threshold_seconds=1.0,
    )

    samples = _samples_by_name(metrics)

    assert (
        _sample_value(samples, "gtex_runtime_probe_total", probe="health", result="ok", status_code="200") == 1.0
    )
    assert (
        _sample_value(samples, "gtex_runtime_probe_total", probe="ready", result="error", status_code="503") == 1.0
    )
    assert (
        _sample_value(
            samples,
            "gtex_runtime_probe_duration_seconds_count",
            probe="health",
            result="ok",
            status_code="200",
        )
        == 1.0
    )
    assert _sample_value(samples, "gtex_runtime_probe_slow_total", probe="health", threshold_seconds="1") == 1.0
    assert (
        _sample_value(
            samples,
            "gtex_boot_phase_duration_seconds_count",
            phase="schema_check",
            result="success",
        )
        == 1.0
    )
    assert (
        _sample_value(
            samples,
            "gtex_boot_phase_slow_total",
            phase="schema_check",
            result="success",
            threshold_seconds="2",
        )
        == 1.0
    )


def test_observability_middleware_records_probes_outside_http_request_totals() -> None:
    metrics = GTexMetrics(runtime_name="test")
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware, metrics=metrics)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> Response:
        return Response(status_code=503)

    @app.get("/example")
    def example() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        assert client.get("/example").status_code == 200

    samples = _samples_by_name(metrics)

    assert (
        _sample_value(samples, "gtex_runtime_probe_total", probe="health", result="ok", status_code="200") == 1.0
    )
    assert (
        _sample_value(samples, "gtex_runtime_probe_total", probe="ready", result="error", status_code="503") == 1.0
    )
    assert (
        _sample_value(
            samples,
            "gtex_http_requests_total",
            method="GET",
            route="/example",
            status_code="200",
        )
        == 1.0
    )
    health_http_samples = [
        sample
        for sample in samples.get("gtex_http_requests_total", [])
        if getattr(sample, "labels", {}).get("route") == "/health"
    ]
    ready_http_samples = [
        sample
        for sample in samples.get("gtex_http_requests_total", [])
        if getattr(sample, "labels", {}).get("route") == "/ready"
    ]
    assert health_http_samples == []
    assert ready_http_samples == []
