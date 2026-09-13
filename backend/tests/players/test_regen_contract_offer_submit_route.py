from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.user import User
from app.schemas.player_lifecycle import RegenContractOfferQuoteRequest
from app.segments.player_lifecycle.regen_contract_offer_routes import (
    submit_regen_contract_offer_endpoint,
)
from app.services.player_lifecycle_service import PlayerLifecycleValidationError


@dataclass
class _FakeSession:
    existing_offer: object | None = None

    def scalar(self, _statement):
        return self.existing_offer

    def get(self, _model, _identifier):
        return None


class _FakeService:
    def __init__(self, *, existing_offer=None, window_status="open") -> None:
        self.session = _FakeSession(existing_offer=existing_offer)
        self.window_status = window_status
        self.created_payload = None
        self.created_window_id = None
        self.created_bid = object()

    def _require_club_profile(self, club_id: str):
        return SimpleNamespace(id=club_id, owner_user_id="owner-1")

    def _require_regen_profile(self, player_id: str):
        return SimpleNamespace(id="regen-1", player_id=player_id)

    def list_transfer_windows(self, *, active_on):
        return [SimpleNamespace(id="window-1", status=self.window_status)]

    def create_bid(self, window_id, payload, *, submitted_on):
        self.created_window_id = window_id
        self.created_payload = payload
        return self.created_bid

    def to_transfer_bid_view(self, bid):
        return {"bid": bid}


def _payload() -> RegenContractOfferQuoteRequest:
    return RegenContractOfferQuoteRequest(
        offering_club_id="club-1",
        offered_salary_fancoin_per_year=Decimal("1200"),
        contract_years=3,
    )


def _user() -> User:
    return SimpleNamespace(id="owner-1")  # type: ignore[return-value]


def test_submit_routes_through_canonical_create_bid_service() -> None:
    service = _FakeService()

    result = submit_regen_contract_offer_endpoint(
        "player-1",
        _payload(),
        service=service,
        current_user=_user(),
    )

    assert result["bid"] is service.created_bid
    assert service.created_window_id == "window-1"
    assert service.created_payload.player_id == "player-1"
    assert service.created_payload.buying_club_id == "club-1"
    assert service.created_payload.selling_club_id is None
    assert service.created_payload.wage_offer_amount == Decimal("1200")
    assert service.created_payload.contract_years == 3


def test_submit_replays_existing_offer_without_creating_another_bid() -> None:
    existing_bid = object()
    existing_offer = SimpleNamespace(
        regen_id="regen-1",
        offering_club_id="club-1",
        offered_salary_fancoin_per_year=Decimal("1200"),
        contract_years=3,
        status="submitted",
        decision_deadline=SimpleNamespace(),
        transfer_bid_id="bid-1",
    )

    class _IdempotentService(_FakeService):
        def __init__(self):
            super().__init__(existing_offer=existing_offer)
            self.session.get = lambda _model, _identifier: existing_bid

    service = _IdempotentService()

    result = submit_regen_contract_offer_endpoint(
        "player-1",
        _payload(),
        service=service,
        current_user=_user(),
    )

    assert result["bid"] is existing_bid
    assert service.created_payload is None


def test_submit_requires_club_owner() -> None:
    service = _FakeService()
    wrong_actor = SimpleNamespace(id="other-user")

    with pytest.raises(PlayerLifecycleValidationError, match="owning club user"):
        submit_regen_contract_offer_endpoint(
            "player-1",
            _payload(),
            service=service,
            current_user=wrong_actor,  # type: ignore[arg-type]
        )
