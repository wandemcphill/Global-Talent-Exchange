from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import get_current_user, get_session
from app.models.base import Base
from app.models.regen import CurrencyConversionQuote, RegenContractOffer
from app.models.transfer_bid import TransferBid
from app.models.user import User
from app.routes.player_lifecycle import router
from app.segments.player_lifecycle.segment_player_lifecycle import router as lifecycle_router
from app.services.player_lifecycle_service import PlayerLifecycleService
from tests.players.test_player_lifecycle import add_window, seed_base_context, seed_regen_context


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
    window = add_window(
        session,
        window_id="window-regen-submit",
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
    player = session.get(__import__("app.ingestion.models", fromlist=["Player"]).Player, context["player_id"])
    assert player is not None
    player.current_club_profile_id = None
    session.commit()
    return {**context, "window_id": window.id}


def test_authenticated_regen_offer_submission_is_idempotent(lifecycle_session) -> None:
    context = _prepare_free_agent(lifecycle_session)
    payload = {
        "offering_club_id": context["buyer_profile_id"],
        "offered_salary_fancoin_per_year": "1200.0000",
        "contract_years": 3,
    }

    with _client(lifecycle_session, user_id="user-owner") as client:
        first = client.post(f"/api/players/{context['player_id']}/regen/contract-offers/submit", json=payload)
        second = client.post(f"/api/players/{context['player_id']}/regen/contract-offers/submit", json=payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert len(lifecycle_session.scalars(select(TransferBid).where(TransferBid.player_id == context["player_id"])).all()) == 1
    assert len(lifecycle_session.scalars(select(RegenContractOffer).where(RegenContractOffer.regen_id == "regen-db-player-1")).all()) == 1
    assert len(lifecycle_session.scalars(select(CurrencyConversionQuote).where(CurrencyConversionQuote.regen_id == "regen-db-player-1")).all()) == 1


def test_regen_offer_submission_rejects_non_owner(lifecycle_session) -> None:
    context = _prepare_free_agent(lifecycle_session)
    unauthorized = User(
        id="user-attacker",
        email="attacker@example.com",
        username="attacker",
        display_name="Attacker",
        password_hash="x",
    )
    lifecycle_session.add(unauthorized)
    lifecycle_session.commit()

    payload = {
        "offering_club_id": context["buyer_profile_id"],
        "offered_salary_fancoin_per_year": "1200.0000",
        "contract_years": 3,
    }

    with _client(lifecycle_session, user_id="user-attacker") as client:
        response = client.post(f"/api/players/{context['player_id']}/regen/contract-offers/submit", json=payload)

    assert response.status_code == 403
    assert lifecycle_session.scalars(select(TransferBid).where(TransferBid.player_id == context["player_id"])).all() == []


# Keep the router imported through the production route module. This assertion
# prevents a future test cleanup from silently switching back to only the
# legacy segment router.
def test_submission_router_is_composed_into_canonical_player_lifecycle_router() -> None:
    assert router is lifecycle_router
