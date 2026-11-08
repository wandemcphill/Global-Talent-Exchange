from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.modules import (
    _strip_api_prefix,
    _with_api_alias,
    _with_api_only,
)


def test_strip_api_prefix_normalizes_paths() -> None:
    assert _strip_api_prefix("/api/players/123/career") == "/players/123/career"
    assert _strip_api_prefix("/api/v2/players/123/career") == "/players/123/career"
    assert _strip_api_prefix("/players/123/career") == "/players/123/career"
    assert _strip_api_prefix("/api") == ""
    assert _strip_api_prefix("/api/") == ""
    assert _strip_api_prefix("/api/v2") == ""
    assert _strip_api_prefix("/api/v2/") == ""
    assert _strip_api_prefix("/api_keys") == "/api_keys"
    assert _strip_api_prefix("/apidocs") == "/apidocs"


def test_with_api_alias_prevents_prefix_doubling() -> None:
    subrouter = APIRouter()

    @subrouter.get("/api/players/{player_id}/career")
    def get_career(player_id: str) -> dict[str, str]:
        return {"player_id": player_id}

    @subrouter.get("/stats")
    def get_stats() -> dict[str, str]:
        return {"status": "ok"}

    wrapped = _with_api_alias(subrouter)
    paths = [route.path for route in wrapped.routes]

    # Verify no doubled prefixes
    assert not any("/api/api" in p for p in paths), f"Doubled /api/api found: {paths}"
    assert not any("/api/v2/api" in p for p in paths), f"Doubled /api/v2/api found: {paths}"

    # Verify clean single prefixes exist
    assert "/api/players/{player_id}/career" in paths
    assert "/api/v2/players/{player_id}/career" in paths
    assert "/players/{player_id}/career" in paths

    assert "/api/stats" in paths
    assert "/api/v2/stats" in paths
    assert "/stats" in paths

    app = FastAPI()
    app.include_router(wrapped)
    client = TestClient(app)

    # All three paths must resolve cleanly
    res_bare = client.get("/players/p1/career")
    assert res_bare.status_code == 200
    assert res_bare.json() == {"player_id": "p1"}

    res_api = client.get("/api/players/p2/career")
    assert res_api.status_code == 200
    assert res_api.json() == {"player_id": "p2"}

    res_v2 = client.get("/api/v2/players/p3/career")
    assert res_v2.status_code == 200
    assert res_v2.json() == {"player_id": "p3"}

    # Doubled prefix must return 404
    assert client.get("/api/api/players/p1/career").status_code == 404
    assert client.get("/api/v2/api/players/p1/career").status_code == 404


def test_with_api_only_prevents_prefix_doubling() -> None:
    subrouter = APIRouter()

    @subrouter.get("/api/items/{item_id}")
    def get_item(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    wrapped = _with_api_only(subrouter)
    paths = [route.path for route in wrapped.routes]

    assert not any("/api/api" in p for p in paths)
    assert not any("/api/v2/api" in p for p in paths)

    assert "/api/items/{item_id}" in paths
    assert "/api/v2/items/{item_id}" in paths
    assert "/items/{item_id}" not in paths

    app = FastAPI()
    app.include_router(wrapped)
    client = TestClient(app)

    assert client.get("/api/items/42").status_code == 200
    assert client.get("/api/v2/items/42").status_code == 200
    assert client.get("/items/42").status_code == 404
    assert client.get("/api/api/items/42").status_code == 404
