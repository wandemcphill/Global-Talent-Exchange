from app.main import create_app
from fastapi.testclient import TestClient

def test_diagnostics_endpoint_available() -> None:
    app = create_app(run_migration_check=False)
    client = TestClient(app)
    response = client.get('/diagnostics')
    assert response.status_code == 200
    payload = response.json()
    assert 'config_checks' in payload
    assert 'route_count' in payload
    assert payload['status'] in {'ok', 'warning'}


def test_metrics_endpoint_available() -> None:
    app = create_app(run_migration_check=False)
    client = TestClient(app)
    response = client.get('/metrics')
    assert response.status_code == 200
    assert "gtex_http_requests_total" in response.text
    assert "gtex_match_queue_delay_seconds" in response.text
