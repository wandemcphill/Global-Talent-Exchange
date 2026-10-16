from app.main import create_app
from fastapi.testclient import TestClient


def test_health_endpoint_reports_dependency_checks_and_runtime_mode() -> None:
    app = create_app(run_migration_check=False)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checks"]["api"]["status"] == "ok"
    assert payload["checks"]["database"]["status"] == "ok"
    assert payload["checks"]["redis"]["status"] == "skipped"
    assert payload["checks"]["kafka"]["status"] == "skipped"
    assert payload["runtime_mode"] == "degraded"
    assert any("Redis is not configured" in reason for reason in payload["mode_reasons"])
    assert any("Kafka brokers are not configured" in reason for reason in payload["mode_reasons"])
    assert "Redis is not configured" in payload["dependency_issues"]["redis"]
    assert "Kafka brokers are not configured" in payload["dependency_issues"]["kafka"]


def test_diagnostics_endpoint_surfaces_config_and_dependency_issues() -> None:
    app = create_app(run_migration_check=False)
    client = TestClient(app)
    response = client.get("/diagnostics")
    assert response.status_code == 200
    payload = response.json()
    assert "config_checks" in payload
    assert "config_issues" in payload
    assert "dependency_checks" in payload
    assert "dependency_issues" in payload
    assert "route_count" in payload
    assert payload["dependency_checks"]["kafka"]["status"] == "skipped"
    assert payload["runtime_mode"] == "degraded"
    assert "Redis is not configured" in payload["dependency_issues"]["redis"]
    assert "Kafka brokers are not configured" in payload["dependency_issues"]["kafka"]
    missing_config_checks = {name for name, is_present in payload["config_checks"].items() if not is_present}
    assert set(payload["config_issues"]) == missing_config_checks
    for name, issue in payload["config_issues"].items():
        assert name in missing_config_checks
        assert issue
    assert payload["status"] in {"ok", "warning"}


def test_metrics_endpoint_available() -> None:
    app = create_app(run_migration_check=False)
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "gtex_http_requests_total" in response.text
    assert "gtex_match_queue_delay_seconds" in response.text
