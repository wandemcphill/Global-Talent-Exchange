from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.models.transfer_window import TransferWindow
from backend.tests.players.test_player_share_market_routes import _seed_imported_real_player

PREFIX = "full-journey-20260915"


def _ok(response, code=200):
    assert response.status_code == code, response.text
    return response.json()

# ...
