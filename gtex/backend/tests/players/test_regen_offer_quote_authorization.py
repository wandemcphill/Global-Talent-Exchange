from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import get_current_user, get_session
from app.ingestion.models import Player
from app.models.regen import CurrencyConversionQuote
from app.models.user import User
from app.routes.player_lifecycle import router
from tests.players.test_player_lifecycle import (
    add_window,
    fund_wallet,
    seed_base_context,
    seed_regen_context,
)


def _client(session, *, user_id: str) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def _session_override():
        yield session

    def _current_user_override() -> User:
        user = session.get(User, user_id)
        assert user is not None
        return user

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user] = _current_user_override
    return TestClient(app)


def _prepare_free_agent(session) -> dict[str, str]:
    context = seed_base_context(session)
    add_window(
        session,
        window_id="window-regen-quote",
        opens_on=date(2026, 1, 1),
        closes_on=date(2026, 12, 31),
    )
    regen = seed_regen_context(
        session,
        player_id=context["player_id"],
        generated_for_club_id=context["club_profile_id"],
        generated_at=datetime(2025, 1, 1),
    )
    state = dict(regen.metadata_json or {})
    career_state = dict(state.get("career_state") or {})
    career_state.update(
        {
            "contract_currency": "FanCoin",
            "transfer_listed": False,
            "free_agent": True,
            "free_agent_since": "2026-09-01",
            "previous_club_id": context["club_profile_id"],
            "retired": False,
        }
    )
    state["career_state"] = career_state
    regen.metadata_json = state
    player = session.get(Player, context["player_id"])
    assert player is not None
    player.current_club_profile_id = None
    fund_wallet(
        session,
        user_id="user-owner",
        coin=Decimal("1000.0000"),
        credit=Decimal("500000.0000"),
    )
    session.commit()
    return context


def test_regen_offer_quote_rejects_non_owner_before_persisting_quote(lifecycle_session) -> None:
    context = _prepare_free_agent(lifecycle_session)
    attacker = User(
        id="user-attacker",
        email="attacker@example.com",
        username="attacker",
        display_name="Attacker",
        password_hash="x",
    )
    lifecycle_session.add(attacker)
    lifecycle_session.commit()

    payload = {
        "offering_club_id": context["buyer_profile_id"],
        "offered_salary_fancoin_per_year": "1200.0000",
        "contract_years": 3,
    }

    with _client(lifecycle_session, user_id="user-attacker") as client:
        response = client.post(
            f"/api/players/{context['player_id']}/regen/contract-offers/quote",
            json=payload,
        )

    assert response.status_code == 403
    assert lifecycle_session.scalars(
        select(CurrencyConversionQuote).where(CurrencyConversionQuote.regen_id == "regen-db-player-1")
    ).all() == []
