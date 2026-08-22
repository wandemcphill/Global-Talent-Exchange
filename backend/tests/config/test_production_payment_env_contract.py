from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_production_env_documents_server_side_korapay_webhook_route() -> None:
    content = _read(".env.production.example")

    assert "GTE_KORAPAY_WEBHOOK_SECRET=" in content
    assert "GTE_KORAPAY_REDIRECT_URL=" in content
    assert "GTE_KORAPAY_NOTIFICATION_URL=" in content
    assert "/integrations/payments/korapay/webhook" in content
    assert "/api/v2/payments/korapay/webhook" not in content
    assert "/api/webhooks/korapay" not in content


def test_kubernetes_secret_template_carries_the_same_korapay_contract() -> None:
    content = _read("ops/k8s/base/secret.example.yaml")

    for key in (
        "GTE_KORAPAY_SECRET_KEY:",
        "GTE_KORAPAY_WEBHOOK_SECRET:",
        "GTE_KORAPAY_REDIRECT_URL:",
        "GTE_KORAPAY_NOTIFICATION_URL:",
    ):
        assert key in content

    assert "/integrations/payments/korapay/webhook" in content
    assert "/api/v2/payments/korapay/webhook" not in content
    assert "/api/webhooks/korapay" not in content
