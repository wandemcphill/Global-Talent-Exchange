from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from backend.app.main import create_app


@pytest.fixture()
def mounted_app(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'gte_module_registration.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    return create_app(engine=engine, run_migration_check=True)


def test_real_app_registers_competition_and_identity_modules(mounted_app) -> None:
    with TestClient(mounted_app):
        openapi_paths = mounted_app.openapi()["paths"]
        registered_modules = set(mounted_app.state.domain_modules)

    assert {
        "leagues",
        "champions_league",
        "academy",
        "world_super_cup",
        "fast_cups",
        "match_engine",
        "canonical_clubs",
        "club_identity",
        "replay_archive",
        "notifications",
    }.issubset(registered_modules)
    assert "/leagues/register" in openapi_paths
    assert "/champions-league/qualification-map" in openapi_paths
    assert "/academy/season-summary" in openapi_paths
    assert "/world-super-cup/countdown" in openapi_paths
    assert "/fast-cups/upcoming" in openapi_paths
    assert "/match-engine/replay" in openapi_paths
    assert "/api/clubs/{club_id}/reputation" in openapi_paths
    assert "/api/clubs/{club_id}/dynasty" in openapi_paths
    assert "/api/clubs/{club_id}/identity" in openapi_paths
    assert "/replays/public/featured" in openapi_paths
    assert "/notifications/me" in openapi_paths


def test_mounted_module_routes_resolve_on_the_real_app(mounted_app) -> None:
    with TestClient(mounted_app) as client:
        world_super_cup_response = client.get("/world-super-cup/countdown")
        fast_cups_response = client.get("/fast-cups/upcoming")
        replay_archive_response = client.get("/replays/public/featured")
        leagues_response = client.post("/leagues/register", json={})
        champions_league_response = client.post("/champions-league/qualification-map", json={})
        academy_response = client.post("/academy/season-summary", json={})
        match_engine_response = client.post("/match-engine/summary", json={})

    assert world_super_cup_response.status_code == 200
    assert fast_cups_response.status_code == 200
    assert replay_archive_response.status_code == 200
    assert leagues_response.status_code == 422
    assert champions_league_response.status_code == 422
    assert academy_response.status_code == 422
    assert match_engine_response.status_code == 422
