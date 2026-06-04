from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.competitions.schemas import (
    CompetitionBracketContract,
    CompetitionBracketLifecycleView,
    CompetitionFeedState,
    CompetitionFixturesContract,
    CompetitionStandingsContract,
)
from app.routes.competitions import competition_contract_router
from app.services.competition_orchestrator import get_competition_orchestrator


def _state(status: str, *, reason: str | None = None, missing_data: tuple[str, ...] = ()) -> CompetitionFeedState:
    now = datetime(2026, 6, 3, tzinfo=timezone.utc)
    return CompetitionFeedState(
        status=status,
        reason=reason,
        missing_data=missing_data,
        authoritative=status == "synced",
        generated_at=now,
    )


class _FakeCompetitionOrchestrator:
    def fixtures_contract(self, competition_id: str) -> CompetitionFixturesContract:
        return CompetitionFixturesContract(
            competition_id=competition_id,
            state=_state("synced"),
            status="synced",
            item_count=0,
            total_fixtures=0,
            completed_fixtures=0,
            score_status="pending_results",
            authoritative_scores=False,
            items=(),
        )

    def standings_contract(self, competition_id: str, *, group_key: str | None = None) -> CompetitionStandingsContract:
        return CompetitionStandingsContract(
            competition_id=competition_id,
            state=_state("synced"),
            status="synced",
            item_count=0,
            total_participants=0,
            total_matches=0,
            completed_matches=0,
            standings_complete=False,
            items=(),
        )

    def bracket_contract(self, competition_id: str) -> CompetitionBracketContract:
        now = datetime(2026, 6, 3, tzinfo=timezone.utc)
        return CompetitionBracketContract(
            competition_id=competition_id,
            lifecycle=CompetitionBracketLifecycleView(
                stage="not_started",
                status="blocked",
                bracket_published=False,
                blocked_reason="competition_has_no_bracket",
            ),
            state=_state(
                "blocked",
                reason="competition_has_no_bracket",
                missing_data=("competition_bracket",),
            ),
            status="blocked",
            rounds=(),
            generated_at=now,
            backend_warnings=("No authoritative bracket rounds are mounted for this competition.",),
        )


def test_competition_backend_contract_routes_return_stateful_envelopes() -> None:
    app = FastAPI()
    app.include_router(competition_contract_router)
    app.dependency_overrides[get_competition_orchestrator] = lambda: _FakeCompetitionOrchestrator()

    with TestClient(app) as client:
        fixtures = client.get("/api/competitions/competition-1/fixtures")
        standings = client.get("/api/competitions/competition-1/standings")
        bracket = client.get("/api/competitions/competition-1/bracket")
        rounds = client.get("/api/competitions/competition-1/rounds")

    assert fixtures.status_code == 200, fixtures.text
    fixtures_payload = fixtures.json()
    assert fixtures_payload["status"] == "synced"
    assert fixtures_payload["state"]["authoritative"] is True
    assert fixtures_payload["authoritative_scores"] is False
    assert fixtures_payload["items"] == []

    assert standings.status_code == 200, standings.text
    standings_payload = standings.json()
    assert standings_payload["status"] == "synced"
    assert standings_payload["standings_complete"] is False
    assert standings_payload["items"] == []

    for response in (bracket, rounds):
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["status"] == "blocked"
        assert payload["lifecycle"]["blocked_reason"] == "competition_has_no_bracket"
        assert payload["state"]["missing_data"] == ["competition_bracket"]
        assert payload["rounds"] == []
