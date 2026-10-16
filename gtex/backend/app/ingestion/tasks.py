from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.cache.redis_helpers import build_cache_backend
from app.ingestion.constants import DEFAULT_PROVIDER_NAME
from app.ingestion.service import IngestionService


def _run_with_session(session_factory, operation: Callable[[IngestionService], Any], *, cache_backend=None) -> Any:
    with session_factory() as session:
        service = IngestionService(session, cache_backend=cache_backend or build_cache_backend())
        result = operation(service)
        session.commit()
        return result


def run_bootstrap_sync(session_factory, *, provider_name: str = DEFAULT_PROVIDER_NAME, competition_external_id: str | None = None, season_external_id: str | None = None, cache_backend=None):
    return _run_with_session(
        session_factory,
        lambda service: service.bootstrap_sync(
            provider_name=provider_name,
            competition_external_id=competition_external_id,
            season_external_id=season_external_id,
        ),
        cache_backend=cache_backend,
    )


def run_incremental_sync(session_factory, *, provider_name: str = DEFAULT_PROVIDER_NAME, cursor_key: str = "default", cache_backend=None):
    return _run_with_session(
        session_factory,
        lambda service: service.sync_incremental(provider_name=provider_name, cursor_key=cursor_key),
        cache_backend=cache_backend,
    )


def run_competition_refresh(session_factory, *, provider_name: str = DEFAULT_PROVIDER_NAME, competition_external_id: str, season_external_id: str | None = None, cache_backend=None):
    return _run_with_session(
        session_factory,
        lambda service: service.refresh_competition(
            provider_name=provider_name,
            competition_external_id=competition_external_id,
            season_external_id=season_external_id,
        ),
        cache_backend=cache_backend,
    )


def run_club_refresh(session_factory, *, provider_name: str = DEFAULT_PROVIDER_NAME, club_external_id: str, competition_external_id: str | None = None, season_external_id: str | None = None, cache_backend=None):
    return _run_with_session(
        session_factory,
        lambda service: service.refresh_club(
            provider_name=provider_name,
            club_external_id=club_external_id,
            competition_external_id=competition_external_id,
            season_external_id=season_external_id,
        ),
        cache_backend=cache_backend,
    )


def run_player_refresh(session_factory, *, provider_name: str = DEFAULT_PROVIDER_NAME, player_external_id: str, club_external_id: str | None = None, competition_external_id: str | None = None, season_external_id: str | None = None, cache_backend=None):
    return _run_with_session(
        session_factory,
        lambda service: service.refresh_player(
            provider_name=provider_name,
            player_external_id=player_external_id,
            club_external_id=club_external_id,
            competition_external_id=competition_external_id,
            season_external_id=season_external_id,
        ),
        cache_backend=cache_backend,
    )
