from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routes.competitions import router as competitions_router
from backend.app.services.competition_orchestrator import CompetitionOrchestrator, get_competition_orchestrator


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(competitions_router)
    orchestrator = CompetitionOrchestrator()
    app.dependency_overrides[get_competition_orchestrator] = lambda: orchestrator
    return TestClient(app)


def test_financial_summary_exposes_transparent_pool_breakdown() -> None:
    with _client() as client:
        created = client.post(
            "/api/competitions",
            json={
                "name": "Transparent League",
                "format": "league",
                "visibility": "public",
                "entry_fee": "20.00",
                "currency": "credit",
                "capacity": 10,
                "creator_id": "host-5",
                "platform_fee_pct": "0.10",
                "host_fee_pct": "0.05",
                "payout_structure": [
                    {"place": 1, "percent": "0.50"},
                    {"place": 2, "percent": "0.30"},
                    {"place": 3, "percent": "0.20"},
                ],
            },
        ).json()
        competition_id = created["id"]
        client.post(f"/api/competitions/{competition_id}/publish", json={"open_for_join": True})
        client.post(f"/api/competitions/{competition_id}/join", json={"user_id": "club-1"})
        client.post(f"/api/competitions/{competition_id}/join", json={"user_id": "club-2"})

        financials_response = client.get(f"/api/competitions/{competition_id}/financials")
        assert financials_response.status_code == 200
        financials = financials_response.json()
        assert financials == {
            "competition_id": competition_id,
            "participant_count": 2,
            "entry_fee": "20.00",
            "gross_pool": "40.0000",
            "platform_fee_pct": "0.10",
            "platform_fee_amount": "4.0000",
            "host_fee_pct": "0.05",
            "host_fee_amount": "2.0000",
            "prize_pool": "34.0000",
            "payout_structure": [
                {"place": 1, "percent": "0.50", "amount": "17.0000"},
                {"place": 2, "percent": "0.30", "amount": "10.2000"},
                {"place": 3, "percent": "0.20", "amount": "6.8000"},
            ],
            "currency": "credit",
        }


def test_summary_and_detail_keep_financial_fields_visible() -> None:
    with _client() as client:
        created = client.post(
            "/api/competitions",
            json={
                "name": "Free Discovery Cup",
                "format": "cup",
                "visibility": "public",
                "entry_fee": "0.00",
                "currency": "credit",
                "capacity": 8,
                "creator_id": "host-7",
            },
        ).json()
        competition_id = created["id"]
        detail_response = client.get(f"/api/competitions/{competition_id}")
        summary_response = client.get(f"/api/competitions/{competition_id}/summary")

        assert detail_response.status_code == 200
        assert summary_response.status_code == 200
        required_fields = {
            "name",
            "creator_id",
            "format",
            "visibility",
            "participant_count",
            "entry_fee",
            "platform_fee_pct",
            "host_fee_pct",
            "prize_pool",
            "payout_structure",
            "status",
            "join_eligibility",
            "rules_summary",
        }
        for payload in (detail_response.json(), summary_response.json()):
            assert required_fields.issubset(payload.keys())
