from __future__ import annotations

from datetime import datetime, timedelta, timezone

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


def test_invite_generation_listing_and_join_flow() -> None:
    with _client() as client:
        created = client.post(
            "/api/competitions",
            json={
                "name": "Invite Only League",
                "format": "league",
                "visibility": "invite_only",
                "entry_fee": "10.00",
                "currency": "credit",
                "capacity": 10,
                "creator_id": "host-11",
            },
        ).json()
        competition_id = created["id"]
        client.post(f"/api/competitions/{competition_id}/publish", json={"open_for_join": True})

        invite_response = client.post(
            f"/api/competitions/{competition_id}/invites",
            json={
                "issued_by": "host-11",
                "max_uses": 2,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "note": "Alpha clubs",
            },
        )
        assert invite_response.status_code == 201
        invite = invite_response.json()
        invite_code = invite["invite_code"]
        assert invite["issued_by"] == "host-11"
        assert invite["max_uses"] == 2
        assert invite["uses"] == 0

        invites_response = client.get(f"/api/competitions/{competition_id}/invites")
        assert invites_response.status_code == 200
        assert invites_response.json() == {
            "competition_id": competition_id,
            "invites": [invite],
        }

        blocked_join = client.post(
            f"/api/competitions/{competition_id}/join",
            json={"user_id": "club-x"},
        )
        assert blocked_join.status_code == 409
        assert blocked_join.json() == {"detail": "invite_required"}

        detail_response = client.get(
            f"/api/competitions/{competition_id}",
            params={"viewer_id": "club-y", "invite_code": invite_code},
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["join_eligibility"] == {
            "eligible": True,
            "reason": None,
            "requires_invite": False,
        }

        join_response = client.post(
            f"/api/competitions/{competition_id}/join",
            json={"user_id": "club-y", "invite_code": invite_code},
        )
        assert join_response.status_code == 200
        joined = join_response.json()
        assert joined["participant_count"] == 1

        refreshed_invites = client.get(f"/api/competitions/{competition_id}/invites").json()["invites"]
        assert refreshed_invites[0]["uses"] == 1


def test_only_creator_can_issue_invites() -> None:
    with _client() as client:
        created = client.post(
            "/api/competitions",
            json={
                "name": "Restricted Cup",
                "format": "cup",
                "visibility": "invite_only",
                "entry_fee": "0.00",
                "currency": "credit",
                "capacity": 8,
                "creator_id": "host-22",
            },
        ).json()
        competition_id = created["id"]

        forbidden_response = client.post(
            f"/api/competitions/{competition_id}/invites",
            json={"issued_by": "host-23", "max_uses": 1},
        )
        assert forbidden_response.status_code == 403
        assert forbidden_response.json() == {"detail": "invite_forbidden"}
