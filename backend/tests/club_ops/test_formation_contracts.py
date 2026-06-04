from __future__ import annotations

from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.schemas.club_ops_requests import (
    CreateAcademyPlayerRequest,
    CreateAcademyProgramRequest,
    UpdateAcademyPlayerRequest,
)


_POSITIONS = ("GK", "LB", "LCB", "RCB", "RB", "DM", "CM", "AM", "LW", "RW", "ST")


def test_frontend_active_formation_returns_not_found_when_no_backend_active_formation(club_ops_client) -> None:
    response = club_ops_client.get("/api/v2/clubs/club-api/formation/active")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["state"] in {"empty", "not_found"}
    assert detail["club_id"] == "club-api"
    assert detail["code"] == "formation_active_not_found"


def test_frontend_formations_list_returns_empty_storage_contract(club_ops_client) -> None:
    response = club_ops_client.get("/api/v2/clubs/club-api/formations")

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "empty"
    assert body["formations"] == []
    assert body["items"] == []


def test_frontend_formation_draft_route_persists_backend_owned_draft(
    club_ops_client,
    club_ops_services,
) -> None:
    player_ids = _seed_promoted_players(club_ops_services, "club-api")

    response = club_ops_client.post(
        "/api/v2/clubs/club-api/formations/draft",
        json=_draft_payload(player_ids),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    formation = body["formation"]
    assert body["state"] == "draft"
    assert formation["state"] == "draft"
    assert formation["status"] == "draft"
    assert formation["name"] == "Final rehearsal XI"
    assert formation["scheme"] == "4-3-3"
    assert formation["chemistry_score"] == 100
    assert len(formation["slots"]) == 11
    assert formation["slots"][0]["assigned_player_id"] == player_ids[0]
    assert formation["created_at"]
    assert formation["updated_at"]
    assert formation["audit_ref"].startswith(f"formation:{formation['id']}:draft_saved")
    assert formation["audit_trail"][0]["action"] == "club_formation.draft_saved"
    assert formation["can_save_draft"] is True
    assert formation["can_publish"] is True


def test_frontend_formation_publish_blocks_without_backend_selection_ready_source(club_ops_client) -> None:
    draft_response = club_ops_client.post(
        "/api/v2/clubs/club-api/formations/draft",
        json=_draft_payload(tuple(f"player-{index}" for index in range(11))),
    )
    assert draft_response.status_code == 200, draft_response.text
    formation_id = draft_response.json()["formation"]["id"]

    response = club_ops_client.post(f"/api/v2/clubs/club-api/formations/{formation_id}/publish")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["state"] == "blocked"
    assert detail["code"] == "formation_publish_blocked"
    assert "No backend selection-ready squad source" in " ".join(detail["blockers"])


def test_frontend_formation_publish_detail_history_and_restore_use_backend_contract(
    club_ops_client,
    club_ops_services,
) -> None:
    player_ids = _seed_promoted_players(club_ops_services, "club-api")
    draft_response = club_ops_client.post(
        "/api/v2/clubs/club-api/formations/draft",
        json=_draft_payload(player_ids),
    )
    formation_id = draft_response.json()["formation"]["id"]

    publish_response = club_ops_client.post(f"/api/v2/clubs/club-api/formations/{formation_id}/publish")

    assert publish_response.status_code == 200, publish_response.text
    published = publish_response.json()["formation"]
    assert published["state"] == "published"
    assert published["published_at"]
    assert published["published_by"] == "club-user-1"
    assert published["audit_ref"].startswith(f"formation:{formation_id}:published")
    assert published["audit_trail"][-1]["action"] == "club_formation.published"

    active_response = club_ops_client.get("/api/v2/clubs/club-api/formation/active")
    assert active_response.status_code == 200
    assert active_response.json()["formation"]["id"] == formation_id

    detail_response = club_ops_client.get(f"/api/v2/formations/{formation_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["formation"]["id"] == formation_id

    history_response = club_ops_client.get("/api/v2/clubs/club-api/formations")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["state"] == "ready"
    assert history["formations"][0]["id"] == formation_id
    assert history["items"][0]["status"] == "published"

    restore_response = club_ops_client.post(f"/api/v2/clubs/club-api/formations/{formation_id}/restore")
    assert restore_response.status_code == 200, restore_response.text
    restored = restore_response.json()["formation"]
    assert restored["state"] == "draft"
    assert restored["id"] != formation_id
    assert restored["audit_trail"][0]["action"] == "club_formation.restored"


def test_club_hub_legacy_formation_routes_are_service_adapters(
    club_ops_client,
    club_ops_services,
) -> None:
    player_ids = _seed_promoted_players(club_ops_services, "club-api")
    draft_response = club_ops_client.patch(
        "/api/v2/clubs/club-api/formation/draft",
        json=_draft_payload(player_ids),
    )
    assert draft_response.status_code == 200, draft_response.text
    formation_id = draft_response.json()["id"]

    publish_response = club_ops_client.post(
        "/api/v2/clubs/club-api/formation/publish",
        json={"formation_id": formation_id},
    )
    assert publish_response.status_code == 200, publish_response.text
    assert publish_response.json()["state"] == "published"

    active_response = club_ops_client.get("/api/v2/clubs/club-api/formation")
    assert active_response.status_code == 200
    assert active_response.json()["id"] == formation_id


def _seed_promoted_players(
    club_ops_services: dict[str, object],
    club_id: str,
    *,
    count: int = 11,
) -> tuple[str, ...]:
    academy = club_ops_services["academy"]
    program = academy.create_program(
        club_id,
        payload=CreateAcademyProgramRequest(
            name="First-team pathway",
            program_type="elite_development",
            budget_minor=0,
            focus_attributes=("technical", "tactical"),
        ),
    )
    player_ids: list[str] = []
    for index in range(count):
        player = academy.create_player(
            club_id,
            payload=CreateAcademyPlayerRequest(
                program_id=program.id,
                display_name=f"Selection Ready {index + 1}",
                age=18,
                primary_position=_POSITIONS[index % len(_POSITIONS)],
            ),
        )
        promoted = academy.update_player(
            club_id,
            player.id,
            payload=UpdateAcademyPlayerRequest(
                status=AcademyPlayerStatus.PROMOTED,
                attendance_score=95,
                coach_assessment=95,
                completed_cycles_delta=1,
            ),
        )
        player_ids.append(promoted.id)
    return tuple(player_ids)


def _draft_payload(player_ids: tuple[str, ...]) -> dict[str, object]:
    return {
        "name": "Final rehearsal XI",
        "scheme": "4-3-3",
        "slots": [
            {
                "slot_id": f"slot-{index + 1}",
                "position": _POSITIONS[index],
                "assigned_player_id": player_id,
                "x": round((index % 4) / 4, 2),
                "y": round(index / 10, 2),
                "role": "balanced",
                "filled": True,
            }
            for index, player_id in enumerate(player_ids)
        ],
    }
