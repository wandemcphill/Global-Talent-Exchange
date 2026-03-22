from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.constants import (
    REAL_PLAYER_IMPORT_CURSOR_KEY,
    REAL_PLAYER_IMPORT_ENTITY_TYPE,
    REAL_PLAYER_IMPORT_JOB_NAME,
    SYNC_RUN_STATUS_FAILED,
    SYNC_RUN_STATUS_PARTIAL,
    SYNC_RUN_STATUS_SUCCESS,
)
from app.ingestion.market_profile import PlayerMarketProfileService
from app.ingestion.repository import IngestionRepository, MutationStats
from app.ingestion.schemas import CursorRead, SyncRunRead
from app.providers import ProviderRegistry

from .real_player_import_repository import RealPlayerImportRepository
from .real_player_import_schemas import (
    RealPlayerImportExecutionSummary,
    RealPlayerImportStatusRead,
)

logger = logging.getLogger(__name__)


class RealPlayerImportError(ValueError):
    pass


def _sync_run_read(run) -> SyncRunRead:
    return SyncRunRead(
        id=run.id,
        provider_name=run.provider_name,
        job_name=run.job_name,
        entity_type=run.entity_type,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_ms=run.duration_ms,
        records_seen=run.records_seen,
        inserted_count=run.inserted_count,
        updated_count=run.updated_count,
        skipped_count=run.skipped_count,
        failed_count=run.failed_count,
        scope_value=run.scope_value,
        cursor_value=run.cursor_value,
        error_message=run.error_message,
    )


def _cursor_read(cursor) -> CursorRead:
    return CursorRead(
        id=cursor.id,
        provider_name=cursor.provider_name,
        entity_type=cursor.entity_type,
        cursor_key=cursor.cursor_key,
        cursor_value=cursor.cursor_value,
        checkpoint_at=cursor.checkpoint_at,
        last_run_id=cursor.last_run_id,
    )


class RealPlayerImportService:
    def __init__(
        self,
        session: Session,
        *,
        provider_registry: ProviderRegistry | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.provider_registry = provider_registry or ProviderRegistry()
        self.settings = settings
        self.ingestion_repository = IngestionRepository(
            self.session,
            market_profile_service=(
                PlayerMarketProfileService(settings=settings)
                if settings is not None
                else PlayerMarketProfileService()
            ),
        )
        self.staging_repository = RealPlayerImportRepository(self.session)
        self.logger = logger

    def import_directory(
        self,
        *,
        provider_name: str | None = None,
        batch_size: int | None = None,
        max_pages: int | None = None,
        cursor_key: str | None = None,
        restart: bool = False,
    ) -> RealPlayerImportExecutionSummary:
        config = self._resolve_config(
            provider_name=provider_name,
            batch_size=batch_size,
            max_pages=max_pages,
            cursor_key=cursor_key,
        )
        provider = self.provider_registry.create(config["provider_name"], settings=self.settings)
        current_cursor = None
        if not restart:
            current = self.staging_repository.get_cursor(
                provider_name=config["provider_name"],
                cursor_key=config["cursor_key"],
            )
            current_cursor = current.cursor_value if current is not None else None

        run = self.ingestion_repository.start_sync_run(
            provider_name=config["provider_name"],
            job_name=REAL_PLAYER_IMPORT_JOB_NAME,
            entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
            scope_value=config["cursor_key"],
            metadata_json={
                "batch_size": config["batch_size"],
                "max_pages": config["max_pages"],
                "cursor_key": config["cursor_key"],
                "restart": restart,
                "rate_limit_per_minute": config["rate_limit_per_minute"],
                "timeout_seconds": config["timeout_seconds"],
                "resume_from_cursor": current_cursor,
            },
        )
        pages_processed = 0
        exhausted = False
        stats = MutationStats()
        latest_source_version: str | None = None
        self.logger.info(
            "ingestion.real_players.started provider=%s cursor_key=%s restart=%s batch_size=%s max_pages=%s resume_cursor=%s",
            config["provider_name"],
            config["cursor_key"],
            restart,
            config["batch_size"],
            config["max_pages"],
            current_cursor,
        )
        try:
            while pages_processed < config["max_pages"]:
                page = provider.fetch_player_directory_page(
                    cursor=current_cursor,
                    batch_size=config["batch_size"],
                    timeout_seconds=config["timeout_seconds"],
                    rate_limit_per_minute=config["rate_limit_per_minute"],
                )
                latest_source_version = page.source_version or latest_source_version
                next_cursor = page.next_cursor
                page_stats = self.staging_repository.upsert_staging_records(
                    provider_name=config["provider_name"],
                    items=page.items,
                    source_version=page.source_version,
                    last_import_run_id=run.id,
                    last_import_cursor=next_cursor,
                )
                stats.merge(page_stats)
                if page.items:
                    self.ingestion_repository.store_raw_payloads(
                        provider_name=config["provider_name"],
                        entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
                        payloads=[item.raw_payload for item in page.items],
                        sync_run_id=run.id,
                        external_id_key="provider_player_id",
                    )
                pages_processed += 1
                current_cursor = next_cursor
                exhausted = page.exhausted or next_cursor is None
                run.metadata_json = {
                    **(run.metadata_json or {}),
                    "pages_processed": pages_processed,
                    "exhausted": exhausted,
                    "latest_source_version": latest_source_version,
                    "last_checkpoint_cursor": current_cursor,
                }
                self.session.flush()
                self.ingestion_repository.save_cursor(
                    provider_name=config["provider_name"],
                    entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
                    cursor_key=config["cursor_key"],
                    cursor_value=current_cursor,
                    last_run_id=run.id,
                )
                self.logger.info(
                    "ingestion.real_players.page provider=%s cursor_key=%s page=%s page_records=%s inserted=%s updated=%s skipped=%s next_cursor=%s exhausted=%s",
                    config["provider_name"],
                    config["cursor_key"],
                    pages_processed,
                    page_stats.records_seen,
                    page_stats.inserted_count,
                    page_stats.updated_count,
                    page_stats.skipped_count,
                    current_cursor,
                    exhausted,
                )
                if exhausted:
                    break

            status = SYNC_RUN_STATUS_SUCCESS if exhausted else SYNC_RUN_STATUS_PARTIAL
            completed_run = self.ingestion_repository.finish_sync_run(
                run,
                stats=stats,
                status=status,
                cursor_value=current_cursor,
            )
            self.logger.info(
                "ingestion.real_players.completed provider=%s cursor_key=%s status=%s pages=%s records_seen=%s inserted=%s updated=%s skipped=%s next_cursor=%s",
                config["provider_name"],
                config["cursor_key"],
                status,
                pages_processed,
                stats.records_seen,
                stats.inserted_count,
                stats.updated_count,
                stats.skipped_count,
                current_cursor,
            )
            return RealPlayerImportExecutionSummary(
                run_id=completed_run.id,
                provider_name=completed_run.provider_name,
                job_name=completed_run.job_name,
                entity_type=completed_run.entity_type,
                status=completed_run.status,
                duration_ms=completed_run.duration_ms or 0,
                records_seen=completed_run.records_seen,
                inserted_count=completed_run.inserted_count,
                updated_count=completed_run.updated_count,
                skipped_count=completed_run.skipped_count,
                failed_count=completed_run.failed_count,
                cursor_value=completed_run.cursor_value,
                error_message=completed_run.error_message,
                cursor_key=config["cursor_key"],
                batch_size=config["batch_size"],
                pages_processed=pages_processed,
                next_cursor=current_cursor,
                exhausted=exhausted,
            )
        except NotImplementedError as exc:
            self.ingestion_repository.finish_sync_run(
                run,
                stats=stats,
                status=SYNC_RUN_STATUS_FAILED,
                error_message=str(exc),
                cursor_value=current_cursor,
            )
            raise RealPlayerImportError(str(exc)) from exc
        except Exception as exc:
            failure_status = SYNC_RUN_STATUS_PARTIAL if stats.records_seen > 0 else SYNC_RUN_STATUS_FAILED
            self.ingestion_repository.finish_sync_run(
                run,
                stats=stats,
                status=failure_status,
                error_message=str(exc),
                cursor_value=current_cursor,
            )
            self.logger.exception(
                "ingestion.real_players.failed provider=%s cursor_key=%s status=%s",
                config["provider_name"],
                config["cursor_key"],
                failure_status,
            )
            raise

    def get_status(
        self,
        *,
        provider_name: str | None = None,
        cursor_key: str | None = None,
        recent_run_limit: int = 10,
    ) -> RealPlayerImportStatusRead:
        config = self._resolve_config(provider_name=provider_name, cursor_key=cursor_key)
        recent_runs = self.staging_repository.list_recent_runs(
            provider_name=config["provider_name"],
            limit=recent_run_limit,
        )
        latest_run = recent_runs[0] if recent_runs else None
        cursor = self.staging_repository.get_cursor(
            provider_name=config["provider_name"],
            cursor_key=config["cursor_key"],
        )
        return RealPlayerImportStatusRead(
            provider_name=config["provider_name"],
            cursor_key=config["cursor_key"],
            staged_player_count=self.staging_repository.count_staged_records(provider_name=config["provider_name"]),
            latest_seen_at=self.staging_repository.latest_seen_at(provider_name=config["provider_name"]),
            latest_run=_sync_run_read(latest_run) if latest_run is not None else None,
            cursor=_cursor_read(cursor) if cursor is not None else None,
            recent_runs=[_sync_run_read(run) for run in recent_runs],
        )

    def _resolve_config(
        self,
        *,
        provider_name: str | None = None,
        batch_size: int | None = None,
        max_pages: int | None = None,
        cursor_key: str | None = None,
    ) -> dict[str, str | int]:
        configured = self.settings.real_player_import if self.settings is not None else None
        resolved_provider = provider_name or (configured.provider_name if configured is not None else "mock")
        return {
            "provider_name": resolved_provider,
            "batch_size": batch_size or (configured.batch_size if configured is not None else 250),
            "max_pages": max_pages or (configured.max_pages_per_run if configured is not None else 40),
            "cursor_key": cursor_key or (configured.cursor_key if configured is not None else REAL_PLAYER_IMPORT_CURSOR_KEY),
            "rate_limit_per_minute": configured.rate_limit_per_minute if configured is not None else 120,
            "timeout_seconds": configured.timeout_seconds if configured is not None else 20,
        }
