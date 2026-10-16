from __future__ import annotations

from app.ingestion.share_market_issuance import issuance_enabled


def test_ingestion_market_issuance_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("GTE_INGESTION_ISSUANCE_ENABLED", raising=False)
    assert issuance_enabled() is False


def test_ingestion_market_issuance_requires_explicit_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("GTE_INGESTION_ISSUANCE_ENABLED", "true")
    assert issuance_enabled() is True

    monkeypatch.setenv("GTE_INGESTION_ISSUANCE_ENABLED", "TRUE")
    assert issuance_enabled() is True

    monkeypatch.setenv("GTE_INGESTION_ISSUANCE_ENABLED", "false")
    assert issuance_enabled() is False
