from __future__ import annotations

from collections import Counter

from fastapi import FastAPI
from fastapi.routing import APIWebSocketRoute

from app.live_matches.router import router as live_matches_router
from app.realtime.router import router as realtime_router


def _websocket_paths(app: FastAPI) -> tuple[str, ...]:
    return tuple(route.path for route in app.router.routes if isinstance(route, APIWebSocketRoute))


def test_realtime_and_live_match_websocket_routes_do_not_collide() -> None:
    app = FastAPI()
    app.include_router(realtime_router)
    app.include_router(live_matches_router)

    websocket_paths = _websocket_paths(app)
    path_counts = Counter(websocket_paths)

    assert sorted(path for path, count in path_counts.items() if count > 1) == []
    assert path_counts["/api/matches/{match_id}/stream"] == 1
    assert path_counts["/matches/{match_id}/stream"] == 1
    assert path_counts["/realtime/matches/{match_id}/stream"] == 1
    assert path_counts["/ws/match/{match_id}"] == 1
