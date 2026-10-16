from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.app.club_identity.trophies.repository import InMemoryTrophyRepository
from backend.app.club_identity.trophies.router import get_trophy_cabinet_service, router
from backend.app.club_identity.trophies.service import TrophyCabinetService


@pytest.fixture()
def trophy_api() -> tuple[TestClient, TrophyCabinetService]:
    service = TrophyCabinetService(repository=InMemoryTrophyRepository())
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="league_title",
        season_label="2026",
        final_result_summary="Won league by 6 points",
        earned_at=datetime(2026, 5, 21, tzinfo=timezone.utc),
        captain_name="Ayo Captain",
        top_performer_name="Bola Striker",
        award_reference="league-2026",
    )
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="world_super_cup",
        season_label="2027",
        final_result_summary="Beat Cosmos FC 2-0",
        earned_at=datetime(2027, 8, 11, tzinfo=timezone.utc),
        award_reference="wsc-2027",
    )
    service.award_trophy(
        club_id="club-beta",
        club_name="Beta United",
        trophy_type="fast_cup",
        season_label="2027",
        final_result_summary="Won fast cup final",
        earned_at=datetime(2027, 2, 11, tzinfo=timezone.utc),
        award_reference="fast-2027",
    )
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="academy_champions_league",
        season_label="2027",
        final_result_summary="Academy final 1-0",
        earned_at=datetime(2027, 4, 30, tzinfo=timezone.utc),
        award_reference="academy-ucl-2027",
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_trophy_cabinet_service] = lambda: service
    with TestClient(app) as client:
        yield client, service


def test_trophy_cabinet_and_timeline_api_shapes(trophy_api) -> None:
    client, _ = trophy_api

    cabinet_response = client.get("/api/clubs/club-alpha/trophy-cabinet")
    timeline_response = client.get("/api/clubs/club-alpha/honors-timeline")

    assert cabinet_response.status_code == 200
    cabinet_payload = cabinet_response.json()
    assert set(cabinet_payload) == {
        "club_id",
        "club_name",
        "total_honors_count",
        "major_honors_count",
        "elite_honors_count",
        "senior_honors_count",
        "academy_honors_count",
        "trophies_by_category",
        "trophies_by_season",
        "recent_honors",
        "historic_honors_timeline",
        "summary_outputs",
    }
    assert set(cabinet_payload["recent_honors"][0]) == {
        "trophy_win_id",
        "club_id",
        "club_name",
        "trophy_type",
        "trophy_name",
        "season_label",
        "competition_region",
        "competition_tier",
        "final_result_summary",
        "earned_at",
        "captain_name",
        "top_performer_name",
        "team_scope",
        "is_major_honor",
        "is_elite_honor",
    }
    assert "1x GTEX World Super Cup Winner" in cabinet_payload["summary_outputs"]

    assert timeline_response.status_code == 200
    timeline_payload = timeline_response.json()
    assert set(timeline_payload) == {"club_id", "club_name", "honors"}
    assert [item["trophy_type"] for item in timeline_payload["honors"][:2]] == [
        "world_super_cup",
        "academy_champions_league",
    ]


def test_season_honors_and_leaderboard_api_outputs(trophy_api) -> None:
    client, _ = trophy_api

    archive_response = client.get("/api/clubs/club-alpha/season-honors")
    leaderboard_response = client.get("/api/leaderboards/trophies")
    academy_leaderboard_response = client.get("/api/leaderboards/trophies", params={"team_scope": "academy"})

    assert archive_response.status_code == 200
    archive_payload = archive_response.json()
    assert set(archive_payload) == {"club_id", "club_name", "season_records"}
    assert set(archive_payload["season_records"][0]) == {
        "snapshot_id",
        "club_id",
        "club_name",
        "season_label",
        "team_scope",
        "honors",
        "total_honors_count",
        "major_honors_count",
        "elite_honors_count",
        "recorded_at",
    }
    assert {record["team_scope"] for record in archive_payload["season_records"]} == {"senior", "academy"}

    assert leaderboard_response.status_code == 200
    leaderboard_payload = leaderboard_response.json()
    assert set(leaderboard_payload) == {"entries"}
    assert leaderboard_payload["entries"][0]["club_id"] == "club-alpha"
    assert leaderboard_payload["entries"][0]["major_honors_count"] == 3

    assert academy_leaderboard_response.status_code == 200
    academy_payload = academy_leaderboard_response.json()
    assert len(academy_payload["entries"]) == 1
    assert academy_payload["entries"][0]["academy_honors_count"] == 1


def test_unknown_club_returns_not_found(trophy_api) -> None:
    client, _ = trophy_api

    response = client.get("/api/clubs/unknown-club/trophy-cabinet")

    assert response.status_code == 404
    assert response.json()["detail"] == "No trophy honors recorded for club unknown-club"
