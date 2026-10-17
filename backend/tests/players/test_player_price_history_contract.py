from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from app.models.player_token_market import PlayerSharePriceSnapshot
from app.players.router import trigger_player_share_price_snapshot
from app.players.token_schemas import PlayerSharePriceHistoryView


def test_price_snapshot_model_has_unique_player_day_key():
    constraints = PlayerSharePriceSnapshot.__table__.constraints
    unique_keys = {
        tuple(column.name for column in constraint.columns)
        for constraint in constraints
        if getattr(constraint, "name", None) == "uq_player_share_price_snapshots_player_date"
    }
    assert ("player_id", "snapshot_date") in unique_keys


def test_price_history_response_schema_accepts_decimal_points():
    payload = {
        "player_id": "player-1",
        "range": "7d",
        "points": [
            {"at": datetime(2026, 10, 17, tzinfo=timezone.utc), "price": Decimal("0.0250"), "kind": "daily_close"}
        ],
        "open_price": Decimal("0.0250"),
        "current_price": Decimal("0.0260"),
        "high_price": Decimal("0.0260"),
        "low_price": Decimal("0.0250"),
        "change_pct": Decimal("4.00"),
        "trade_count": 1,
    }
    parsed = PlayerSharePriceHistoryView.model_validate(payload)
    assert parsed.points[0].price == Decimal("0.0250")
    assert parsed.trade_count == 1


def test_snapshot_cron_fails_closed_when_secret_is_missing(monkeypatch):
    monkeypatch.delenv("WEBHOOK_CRON_SECRET", raising=False)
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v2/players/markets/price-snapshots/cron",
        "headers": [],
        "query_string": b"",
    })
    with pytest.raises(HTTPException) as error:
        trigger_player_share_price_snapshot(request, BackgroundTasks())
    assert error.value.status_code == 503
