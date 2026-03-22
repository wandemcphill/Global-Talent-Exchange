from __future__ import annotations

from dataclasses import dataclass, field

from app.cache.redis_helpers import build_cache_backend
from app.core.jobs import BackgroundJobBackend, InlineJobBackend
from app.ingestion.constants import DEFAULT_PROVIDER_NAME
from app.ingestion.locks import IngestionLockManager, LockAcquisitionError
from app.ingestion.tasks import (
    run_bootstrap_sync,
    run_club_refresh,
    run_competition_refresh,
    run_incremental_sync,
    run_player_refresh,
)
from app.models.base import utcnow


@dataclass(slots=True)
class IngestionJobRunner:
    session_factory: object
    cache_backend: object = field(default_factory=build_cache_backend)
    provider_name: str = DEFAULT_PROVIDER_NAME
    value_snapshot_runner: object | None = None
    job_backend: BackgroundJobBackend = field(default_factory=InlineJobBackend)

    def nightly_full_sync(self):
        return self._run_locked(
            "ingestion:nightly_full_sync",
            lambda: run_bootstrap_sync(
                self.session_factory,
                provider_name=self.provider_name,
                cache_backend=self.cache_backend,
            ),
        )

    def hourly_incremental_sync(self, *, cursor_key: str = "default"):
        return self._run_locked(
            f"ingestion:hourly_incremental_sync:{cursor_key}",
            lambda: run_incremental_sync(
                self.session_factory,
                provider_name=self.provider_name,
                cursor_key=cursor_key,
                cache_backend=self.cache_backend,
            ),
        )

    def refresh_competition(self, competition_external_id: str, *, season_external_id: str | None = None):
        return self._run_locked(
            f"ingestion:competition:{competition_external_id}",
            lambda: run_competition_refresh(
                self.session_factory,
                provider_name=self.provider_name,
                competition_external_id=competition_external_id,
                season_external_id=season_external_id,
                cache_backend=self.cache_backend,
            ),
        )

    def refresh_club(self, club_external_id: str, *, competition_external_id: str | None = None, season_external_id: str | None = None):
        return self._run_locked(
            f"ingestion:club:{club_external_id}",
            lambda: run_club_refresh(
                self.session_factory,
                provider_name=self.provider_name,
                club_external_id=club_external_id,
                competition_external_id=competition_external_id,
                season_external_id=season_external_id,
                cache_backend=self.cache_backend,
            ),
        )

    def refresh_player(self, player_external_id: str, *, club_external_id: str | None = None, competition_external_id: str | None = None, season_external_id: str | None = None):
        return self._run_locked(
            f"ingestion:player:{player_external_id}",
            lambda: run_player_refresh(
                self.session_factory,
                provider_name=self.provider_name,
                player_external_id=player_external_id,
                club_external_id=club_external_id,
                competition_external_id=competition_external_id,
                season_external_id=season_external_id,
                cache_backend=self.cache_backend,
            ),
        )

    def _run_locked(self, lock_key: str, operation):
        def execute():
            with self.session_factory() as session:
                lock_manager = IngestionLockManager(session)
                handle = lock_manager.acquire(lock_key)
                if not handle.acquired:
                    raise LockAcquisitionError(f"Another ingestion worker already owns '{lock_key}'.")
                try:
                    result = operation()
                    self._run_value_snapshots()
                    return result
                finally:
                    lock_manager.release(handle)

        execution = self.job_backend.run(f"ingestion.{lock_key}", execute)
        return execution.result

    def _run_value_snapshots(self) -> None:
        if self.value_snapshot_runner is None:
            return
        run = getattr(self.value_snapshot_runner, "run", None)
        if callable(run):
            run(as_of=utcnow())
