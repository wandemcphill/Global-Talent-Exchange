from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine

from app.main import create_app
from app.manager_duels.service import ensure_manager_duel_service
from app.models.manager_duel import ManagerDuelProfile


class FakeCacheBackend:
    enabled = True

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = value

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.values.pop(key, None)

    def ping(self) -> bool:
        return True


def test_manager_duel_leaderboard_uses_cached_global_snapshot(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'manager_duel_service.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)

    with TestClient(app):
        cache_backend = FakeCacheBackend()
        app.state.cache_backend = cache_backend
        with app.state.session_factory() as session:
            session.add_all(
                [
                    ManagerDuelProfile(
                        manager_key="manager:one",
                        manager_id="manager-1",
                        display_name="Manager One",
                        source_type="catalog",
                        owner_user_id=None,
                        reputation_score=128.5,
                        duel_wins=8,
                        duel_draws=1,
                        duel_losses=2,
                        matches_played=11,
                    ),
                    ManagerDuelProfile(
                        manager_key="manager:two",
                        manager_id="manager-2",
                        display_name="Manager Two",
                        source_type="catalog",
                        owner_user_id=None,
                        reputation_score=111.0,
                        duel_wins=6,
                        duel_draws=3,
                        duel_losses=2,
                        matches_played=11,
                    ),
                ]
            )
            session.commit()

        service = ensure_manager_duel_service(app)
        first = service.get_leaderboard(limit=2)

        monkeypatch.setattr(
            service,
            "_load_leaderboard_entries",
            lambda **_kwargs: pytest.fail("expected cached leaderboard lookup"),
        )

        second = service.get_leaderboard(limit=2)

        assert [item.manager_id for item in first] == ["manager-1", "manager-2"]
        assert [item.manager_id for item in second] == ["manager-1", "manager-2"]
        assert "leaderboard:global:entries" in cache_backend.values

    engine.dispose()
