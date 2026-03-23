from __future__ import annotations

"""Temporary compatibility shim for the legacy provider-directory import surface."""

import logging
from pathlib import Path
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.constants import (
    REAL_PLAYER_FILE_IMPORT_JOB_NAME,
    REAL_PLAYER_IMPORT_CURSOR_KEY,
    REAL_PLAYER_IMPORT_ENTITY_TYPE,
    REAL_PLAYER_IMPORT_JOB_NAME,
    SYNC_RUN_STATUS_FAILED,
    SYNC_RUN_STATUS_PARTIAL,
    SYNC_RUN_STATUS_SUCCESS,
)
from app.ingestion.market_profile import PlayerMarketProfileService
from app.ingestion.models import ProviderSyncRun
from app.ingestion.real_player_import_models import RealPlayerImportRun, RealPlayerImportRunStatus
from app.ingestion.repository import IngestionRepository, MutationStats
from app.ingestion.schemas import CursorRead, SyncRunRead
from app.providers import ProviderRegistry

from .real_player_import_repository import RealPlayerImportRepository, StagingSimulationState
from .real_player_import_schemas import (
    RealPlayerBulkImportExecutionSummary,
    RealPlayerImportExecutionSummary,
    RealPlayerImportStatusRead,
)
from .real_player_import_sources import (
    RealPlayerImportRowFailure,
    RealPlayerImportSourceError,
    RealPlayerImportSourceFile,
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
        source_reference = self._source_reference(
            provider_name=config["provider_name"],
            cursor_key=config["cursor_key"],
        )
        import_run = self.staging_repository.get_resumable_import_run(
            provider_name=config["provider_name"],
            source_type="provider_directory",
            source_reference=source_reference,
        )
        run_metadata = {
            "cursor_key": config["cursor_key"],
            "max_pages": config["max_pages"],
            "rate_limit_per_minute": config["rate_limit_per_minute"],
            "timeout_seconds": config["timeout_seconds"],
            "source_reference": source_reference,
            "attempt_count": 1,
            "pages_processed_current_attempt": 0,
            "attempted_restart": restart,
        }
        if import_run is None or restart:
            import_run = self.staging_repository.create_import_run(
                provider_name=config["provider_name"],
                source_type="provider_directory",
                source_reference=source_reference,
                configured_batch_size=config["batch_size"],
                provider_sync_run_id=run.id,
                resume_cursor=current_cursor,
                metadata_json=run_metadata,
            )
        else:
            previous_attempts = int((import_run.metadata_json or {}).get("attempt_count") or 1)
            self.staging_repository.resume_import_run(
                import_run,
                provider_sync_run_id=run.id,
                resume_cursor=current_cursor,
                configured_batch_size=config["batch_size"],
                metadata_updates={
                    **run_metadata,
                    "attempt_count": previous_attempts + 1,
                },
            )

        self.session.commit()

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
                total_pages_processed = int((import_run.metadata_json or {}).get("pages_processed_total") or 0) + 1
                batch_marker = f"page:{total_pages_processed}"
                page_stats = self.staging_repository.upsert_staging_records(
                    provider_name=config["provider_name"],
                    items=page.items,
                    source_version=page.source_version,
                    import_run_id=import_run.id,
                    import_batch_key=batch_marker,
                    last_import_run_id=run.id,
                    last_import_cursor=next_cursor,
                )
                stats.merge(page_stats)
                batch_summary = {
                    "batch_marker": batch_marker,
                    "batch_type": "provider_page",
                    "records_seen": page_stats.records_seen,
                    "inserted_count": page_stats.inserted_count,
                    "updated_count": page_stats.updated_count,
                    "duplicate_skipped_count": page_stats.skipped_count,
                    "failed_count": page_stats.failed_count,
                    "next_cursor": next_cursor,
                }
                self.staging_repository.mark_import_run_progress(
                    import_run,
                    stats=page_stats,
                    batch_marker=batch_marker,
                    resume_cursor=next_cursor,
                    metadata_updates=self._import_run_metadata_updates(
                        import_run,
                        batch_summary=batch_summary,
                        extra_updates={
                            "latest_source_version": latest_source_version,
                            "pages_processed_total": total_pages_processed,
                            "pages_processed_current_attempt": pages_processed + 1,
                        },
                    ),
                )
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
                self._mark_sync_run_progress(
                    run,
                    stats=stats,
                    cursor_value=current_cursor,
                    metadata_updates={
                        "pages_processed": pages_processed,
                        "exhausted": exhausted,
                        "latest_source_version": latest_source_version,
                        "last_checkpoint_cursor": current_cursor,
                        "last_batch_summary": batch_summary,
                    },
                )
                self.ingestion_repository.save_cursor(
                    provider_name=config["provider_name"],
                    entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
                    cursor_key=config["cursor_key"],
                    cursor_value=current_cursor,
                    last_run_id=run.id,
                )
                self.session.commit()
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
            self.staging_repository.refresh_run_state_counts(import_run)
            self.staging_repository.finish_import_run(
                import_run,
                status=self._import_run_status(exhausted=exhausted, failed_rows=stats.failed_count),
                resume_cursor=current_cursor,
                metadata_updates=self._import_run_metadata_updates(
                    import_run,
                    extra_updates={
                        "exhausted": exhausted,
                        "latest_source_version": latest_source_version,
                        "last_checkpoint_cursor": current_cursor,
                    },
                ),
            )
            completed_run = self.ingestion_repository.finish_sync_run(
                run,
                stats=stats,
                status=status,
                cursor_value=current_cursor,
            )
            self.session.commit()
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
                import_run_id=import_run.id,
                cursor_key=config["cursor_key"],
                batch_size=config["batch_size"],
                pages_processed=pages_processed,
                next_cursor=current_cursor,
                exhausted=exhausted,
            )
        except NotImplementedError as exc:
            self._finalize_failed_runs(
                run_id=run.id,
                import_run_id=import_run.id,
                stats=stats,
                sync_status=SYNC_RUN_STATUS_FAILED,
                error_message=str(exc),
                current_cursor=current_cursor,
            )
            raise RealPlayerImportError(str(exc)) from exc
        except Exception as exc:
            failure_status = SYNC_RUN_STATUS_PARTIAL if stats.records_seen > 0 else SYNC_RUN_STATUS_FAILED
            self._finalize_failed_runs(
                run_id=run.id,
                import_run_id=import_run.id,
                stats=stats,
                sync_status=failure_status,
                error_message=str(exc),
                current_cursor=current_cursor,
                metadata_updates={
                    "latest_source_version": latest_source_version,
                    "last_checkpoint_cursor": current_cursor,
                },
            )
            self.logger.exception(
                "ingestion.real_players.failed provider=%s cursor_key=%s status=%s",
                config["provider_name"],
                config["cursor_key"],
                failure_status,
            )
            raise

    def import_source_file(
        self,
        *,
        source_path: str | Path,
        provider_name: str | None = None,
        batch_size: int | None = None,
        cursor_key: str | None = None,
        source_format: str | None = None,
        restart: bool = False,
        dry_run: bool = False,
    ) -> RealPlayerBulkImportExecutionSummary:
        config = self._resolve_config(provider_name=provider_name, batch_size=batch_size)
        try:
            source = RealPlayerImportSourceFile.load(
                provider_name=config["provider_name"],
                source_path=source_path,
                source_format=source_format,
            )
        except RealPlayerImportSourceError as exc:
            raise RealPlayerImportError(str(exc)) from exc

        resolved_cursor_key = cursor_key or self._file_cursor_key(
            provider_name=config["provider_name"],
            source_fingerprint=source.source_fingerprint,
        )
        if dry_run:
            return self._dry_run_source_file(
                provider_name=config["provider_name"],
                source=source,
                batch_size=config["batch_size"],
                cursor_key=resolved_cursor_key,
            )

        current_cursor = None
        if not restart:
            current = self.staging_repository.get_cursor(
                provider_name=config["provider_name"],
                cursor_key=resolved_cursor_key,
            )
            current_cursor = current.cursor_value if current is not None else None

        run = self.ingestion_repository.start_sync_run(
            provider_name=config["provider_name"],
            job_name=REAL_PLAYER_FILE_IMPORT_JOB_NAME,
            entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
            scope_value=resolved_cursor_key,
            metadata_json={
                "batch_size": config["batch_size"],
                "cursor_key": resolved_cursor_key,
                "restart": restart,
                "resume_from_cursor": current_cursor,
                "source_format": source.source_format,
                "source_path": str(source.path),
                "source_fingerprint": source.source_fingerprint,
                "source_version": source.source_version,
                "source_row_count": source.total_rows,
            },
        )
        source_reference = self._file_source_reference(
            source_format=source.source_format,
            source_fingerprint=source.source_fingerprint,
        )
        import_run = self.staging_repository.get_resumable_import_run(
            provider_name=config["provider_name"],
            source_type="source_file",
            source_reference=source_reference,
        )
        run_metadata = {
            "cursor_key": resolved_cursor_key,
            "source_reference": source_reference,
            "source_path": str(source.path),
            "source_format": source.source_format,
            "source_fingerprint": source.source_fingerprint,
            "source_version": source.source_version,
            "source_row_count": source.total_rows,
            "attempt_count": 1,
            "batches_processed_current_attempt": 0,
            "attempted_restart": restart,
        }
        stats = MutationStats()
        if import_run is None or restart:
            import_run = self.staging_repository.create_import_run(
                provider_name=config["provider_name"],
                source_type="source_file",
                source_reference=source_reference,
                configured_batch_size=config["batch_size"],
                provider_sync_run_id=run.id,
                resume_cursor=current_cursor,
                metadata_json=run_metadata,
            )
        else:
            previous_attempts = int((import_run.metadata_json or {}).get("attempt_count") or 1)
            self.staging_repository.resume_import_run(
                import_run,
                provider_sync_run_id=run.id,
                resume_cursor=current_cursor,
                configured_batch_size=config["batch_size"],
                metadata_updates={
                    **run_metadata,
                    "attempt_count": previous_attempts + 1,
                },
            )

        if restart:
            current_cursor = None
            self.ingestion_repository.save_cursor(
                provider_name=config["provider_name"],
                entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
                cursor_key=resolved_cursor_key,
                cursor_value=None,
                last_run_id=run.id,
            )
        self.session.commit()

        batches_processed = 0
        exhausted = source.total_rows == 0
        last_failed_batch: dict[str, Any] | None = None
        self.logger.info(
            "ingestion.real_players.file.started provider=%s source=%s format=%s batch_size=%s cursor_key=%s restart=%s resume_cursor=%s dry_run=%s",
            config["provider_name"],
            source.path,
            source.source_format,
            config["batch_size"],
            resolved_cursor_key,
            restart,
            current_cursor,
            dry_run,
        )
        try:
            for batch in source.iter_batches(start_cursor=current_cursor, batch_size=config["batch_size"]):
                total_batches_processed = int((import_run.metadata_json or {}).get("batches_processed_total") or 0) + 1
                batch_marker = f"batch:{total_batches_processed}"
                last_failed_batch = {
                    "batch_marker": batch_marker,
                    "start_offset": batch.start_offset,
                    "end_offset": batch.end_offset,
                    "row_count": batch.raw_row_count,
                    "next_cursor": batch.next_cursor,
                }
                upsert_stats = self.staging_repository.upsert_staging_records(
                    provider_name=config["provider_name"],
                    items=batch.items,
                    source_version=source.source_version,
                    import_run_id=import_run.id,
                    import_batch_key=batch_marker,
                    last_import_run_id=run.id,
                    last_import_cursor=batch.next_cursor,
                )
                batch_stats = self._combine_batch_stats(
                    raw_row_count=batch.raw_row_count,
                    row_failures=batch.failures,
                    upsert_stats=upsert_stats,
                )
                stats.merge(batch_stats)
                if batch.items:
                    self.ingestion_repository.store_raw_payloads(
                        provider_name=config["provider_name"],
                        entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
                        payloads=[item.raw_payload for item in batch.items],
                        sync_run_id=run.id,
                        external_id_key="provider_player_id",
                    )

                batches_processed += 1
                current_cursor = batch.next_cursor
                exhausted = batch.exhausted
                batch_summary = {
                    "batch_marker": batch_marker,
                    "batch_type": "source_file",
                    "start_offset": batch.start_offset,
                    "end_offset": batch.end_offset,
                    "records_seen": batch_stats.records_seen,
                    "normalized_items": len(batch.items),
                    "failed_rows": len(batch.failures),
                    "inserted_count": batch_stats.inserted_count,
                    "updated_count": batch_stats.updated_count,
                    "duplicate_skipped_count": batch_stats.skipped_count,
                    "next_cursor": batch.next_cursor,
                }
                if batch.failures:
                    batch_summary["failed_row_samples"] = self._failure_samples(batch.failures)
                self.staging_repository.mark_import_run_progress(
                    import_run,
                    stats=batch_stats,
                    batch_marker=batch_marker,
                    resume_cursor=current_cursor,
                    metadata_updates=self._import_run_metadata_updates(
                        import_run,
                        batch_summary=batch_summary,
                        extra_updates={
                            "batches_processed_total": total_batches_processed,
                            "batches_processed_current_attempt": batches_processed,
                            "source_path": str(source.path),
                            "source_format": source.source_format,
                            "source_fingerprint": source.source_fingerprint,
                            "source_version": source.source_version,
                            "source_row_count": source.total_rows,
                            "last_checkpoint_cursor": current_cursor,
                            "exhausted": exhausted,
                        },
                    ),
                )
                self._mark_sync_run_progress(
                    run,
                    stats=stats,
                    cursor_value=current_cursor,
                    metadata_updates={
                        "source_path": str(source.path),
                        "source_format": source.source_format,
                        "source_fingerprint": source.source_fingerprint,
                        "source_version": source.source_version,
                        "source_row_count": source.total_rows,
                        "batches_processed": batches_processed,
                        "last_checkpoint_cursor": current_cursor,
                        "last_batch_summary": batch_summary,
                        "exhausted": exhausted,
                    },
                )
                self.ingestion_repository.save_cursor(
                    provider_name=config["provider_name"],
                    entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
                    cursor_key=resolved_cursor_key,
                    cursor_value=current_cursor,
                    last_run_id=run.id,
                )
                self.session.commit()
                last_failed_batch = None
                self.logger.info(
                    "ingestion.real_players.file.batch provider=%s source=%s batch=%s records=%s inserted=%s updated=%s skipped=%s failed=%s next_cursor=%s exhausted=%s",
                    config["provider_name"],
                    source.path.name,
                    batch_marker,
                    batch_stats.records_seen,
                    batch_stats.inserted_count,
                    batch_stats.updated_count,
                    batch_stats.skipped_count,
                    batch_stats.failed_count,
                    current_cursor,
                    exhausted,
                )

            self.staging_repository.refresh_run_state_counts(import_run)
            self.staging_repository.finish_import_run(
                import_run,
                status=self._import_run_status(exhausted=True, failed_rows=stats.failed_count),
                resume_cursor=current_cursor,
                metadata_updates=self._import_run_metadata_updates(
                    import_run,
                    extra_updates={
                        "source_path": str(source.path),
                        "source_format": source.source_format,
                        "source_fingerprint": source.source_fingerprint,
                        "source_version": source.source_version,
                        "source_row_count": source.total_rows,
                        "last_checkpoint_cursor": current_cursor,
                        "exhausted": exhausted,
                    },
                ),
            )
            completed_run = self.ingestion_repository.finish_sync_run(
                run,
                stats=stats,
                status=SYNC_RUN_STATUS_SUCCESS,
                cursor_value=current_cursor,
            )
            self.session.commit()
            self.logger.info(
                "ingestion.real_players.file.completed provider=%s source=%s batches=%s records_seen=%s inserted=%s updated=%s skipped=%s failed=%s",
                config["provider_name"],
                source.path,
                batches_processed,
                stats.records_seen,
                stats.inserted_count,
                stats.updated_count,
                stats.skipped_count,
                stats.failed_count,
            )
            return RealPlayerBulkImportExecutionSummary(
                run_id=completed_run.id,
                import_run_id=import_run.id,
                provider_name=completed_run.provider_name,
                job_name=completed_run.job_name,
                entity_type=completed_run.entity_type,
                status=completed_run.status,
                duration_ms=completed_run.duration_ms or 0,
                processed_count=completed_run.records_seen,
                records_seen=completed_run.records_seen,
                inserted_count=completed_run.inserted_count,
                updated_count=completed_run.updated_count,
                duplicate_skipped_count=completed_run.skipped_count,
                skipped_count=completed_run.skipped_count,
                failed_count=completed_run.failed_count,
                cursor_value=completed_run.cursor_value,
                error_message=completed_run.error_message,
                cursor_key=resolved_cursor_key,
                batch_size=config["batch_size"],
                batches_processed=batches_processed,
                next_cursor=current_cursor,
                exhausted=exhausted,
                dry_run=False,
                source_path=str(source.path),
                source_format=source.source_format,
                source_fingerprint=source.source_fingerprint,
            )
        except Exception as exc:
            failure_status = SYNC_RUN_STATUS_PARTIAL if stats.records_seen > 0 else SYNC_RUN_STATUS_FAILED
            failure_metadata = dict(last_failed_batch or {})
            failure_metadata["error_message"] = str(exc)
            self._finalize_failed_runs(
                run_id=run.id,
                import_run_id=import_run.id,
                stats=stats,
                sync_status=failure_status,
                error_message=str(exc),
                current_cursor=current_cursor,
                metadata_updates=self._import_run_metadata_updates(
                    import_run,
                    failed_batch=failure_metadata if failure_metadata else None,
                    extra_updates={
                        "source_path": str(source.path),
                        "source_format": source.source_format,
                        "source_fingerprint": source.source_fingerprint,
                        "source_version": source.source_version,
                        "source_row_count": source.total_rows,
                        "last_checkpoint_cursor": current_cursor,
                    },
                ),
            )
            self.logger.exception(
                "ingestion.real_players.file.failed provider=%s source=%s cursor_key=%s status=%s",
                config["provider_name"],
                source.path,
                resolved_cursor_key,
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

    def _dry_run_source_file(
        self,
        *,
        provider_name: str,
        source: RealPlayerImportSourceFile,
        batch_size: int,
        cursor_key: str,
    ) -> RealPlayerBulkImportExecutionSummary:
        started_at = time.monotonic()
        simulation_state = StagingSimulationState()
        stats = MutationStats()
        batches_processed = 0
        current_cursor: str | None = None
        exhausted = source.total_rows == 0

        for batch in source.iter_batches(start_cursor=None, batch_size=batch_size):
            upsert_stats = self.staging_repository.simulate_upsert_staging_records(
                provider_name=provider_name,
                items=batch.items,
                simulation_state=simulation_state,
            )
            batch_stats = self._combine_batch_stats(
                raw_row_count=batch.raw_row_count,
                row_failures=batch.failures,
                upsert_stats=upsert_stats,
            )
            stats.merge(batch_stats)
            batches_processed += 1
            current_cursor = batch.next_cursor
            exhausted = batch.exhausted

        duration_ms = int((time.monotonic() - started_at) * 1000)
        return RealPlayerBulkImportExecutionSummary(
            run_id=None,
            import_run_id=None,
            provider_name=provider_name,
            job_name=REAL_PLAYER_FILE_IMPORT_JOB_NAME,
            entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
            status="dry_run",
            duration_ms=duration_ms,
            processed_count=stats.records_seen,
            records_seen=stats.records_seen,
            inserted_count=stats.inserted_count,
            updated_count=stats.updated_count,
            duplicate_skipped_count=stats.skipped_count,
            skipped_count=stats.skipped_count,
            failed_count=stats.failed_count,
            cursor_value=current_cursor,
            error_message=None,
            cursor_key=cursor_key,
            batch_size=batch_size,
            batches_processed=batches_processed,
            next_cursor=current_cursor,
            exhausted=exhausted,
            dry_run=True,
            source_path=str(source.path),
            source_format=source.source_format,
            source_fingerprint=source.source_fingerprint,
        )

    def _combine_batch_stats(
        self,
        *,
        raw_row_count: int,
        row_failures: tuple[RealPlayerImportRowFailure, ...],
        upsert_stats: MutationStats,
    ) -> MutationStats:
        combined = MutationStats(
            records_seen=raw_row_count,
            inserted_count=upsert_stats.inserted_count,
            updated_count=upsert_stats.updated_count,
            skipped_count=upsert_stats.skipped_count,
            failed_count=upsert_stats.failed_count + len(row_failures),
        )
        combined.touched_ids.update(upsert_stats.touched_ids)
        return combined

    def _mark_sync_run_progress(
        self,
        run: ProviderSyncRun,
        *,
        stats: MutationStats,
        cursor_value: str | None,
        metadata_updates: dict[str, object] | None = None,
    ) -> None:
        run.records_seen = stats.records_seen
        run.inserted_count = stats.inserted_count
        run.updated_count = stats.updated_count
        run.skipped_count = stats.skipped_count
        run.failed_count = stats.failed_count
        run.cursor_value = cursor_value
        run.metadata_json = {
            **(run.metadata_json or {}),
            **(metadata_updates or {}),
        }
        self.session.flush()

    def _finalize_failed_runs(
        self,
        *,
        run_id: str,
        import_run_id: str | None,
        stats: MutationStats,
        sync_status: str,
        error_message: str,
        current_cursor: str | None,
        metadata_updates: dict[str, object] | None = None,
    ) -> None:
        self.session.rollback()
        run = self.session.get(ProviderSyncRun, run_id)
        import_run = self.session.get(RealPlayerImportRun, import_run_id) if import_run_id else None
        if import_run is not None:
            self.staging_repository.refresh_run_state_counts(import_run)
            self.staging_repository.finish_import_run(
                import_run,
                status=RealPlayerImportRunStatus.FAILED.value,
                error_message=error_message,
                resume_cursor=current_cursor,
                metadata_updates=metadata_updates,
            )
        if run is not None:
            self.ingestion_repository.finish_sync_run(
                run,
                stats=stats,
                status=sync_status,
                error_message=error_message,
                cursor_value=current_cursor,
            )
        self.session.commit()

    def _import_run_metadata_updates(
        self,
        import_run,
        *,
        batch_summary: dict[str, object] | None = None,
        failed_batch: dict[str, object] | None = None,
        extra_updates: dict[str, object] | None = None,
    ) -> dict[str, object]:
        metadata = dict(import_run.metadata_json or {})
        if batch_summary is not None:
            batch_summaries = list(metadata.get("batch_summaries") or [])
            batch_summaries.append(batch_summary)
            metadata["batch_summaries"] = batch_summaries[-50:]
            metadata["last_batch_summary"] = batch_summary
        if failed_batch is not None:
            failure_history = list(metadata.get("failure_history") or [])
            failure_history.append(failed_batch)
            metadata["failure_history"] = failure_history[-20:]
            metadata["last_failed_batch"] = failed_batch
        metadata.update(extra_updates or {})
        return metadata

    @staticmethod
    def _failure_samples(
        failures: tuple[RealPlayerImportRowFailure, ...],
        *,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        samples: list[dict[str, object]] = []
        for failure in failures[:limit]:
            samples.append(
                {
                    "row_number": failure.row_number,
                    "error_message": failure.error_message,
                    "source_player_key": failure.source_player_key,
                    "canonical_name": failure.canonical_name,
                }
            )
        return samples

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
        resolved_batch_size = batch_size or (configured.batch_size if configured is not None else 1000)
        return {
            "provider_name": resolved_provider,
            "batch_size": min(5000, max(1, resolved_batch_size)),
            "max_pages": max_pages or (configured.max_pages_per_run if configured is not None else 40),
            "cursor_key": cursor_key or (configured.cursor_key if configured is not None else REAL_PLAYER_IMPORT_CURSOR_KEY),
            "rate_limit_per_minute": configured.rate_limit_per_minute if configured is not None else 120,
            "timeout_seconds": configured.timeout_seconds if configured is not None else 20,
        }

    @staticmethod
    def _source_reference(*, provider_name: str, cursor_key: str) -> str:
        return f"provider_directory:{provider_name}:{cursor_key}"

    @staticmethod
    def _file_source_reference(*, source_format: str, source_fingerprint: str) -> str:
        return f"source_file:{source_format}:{source_fingerprint}"

    @staticmethod
    def _file_cursor_key(*, provider_name: str, source_fingerprint: str) -> str:
        return f"rp-file-{provider_name[:16]}-{source_fingerprint[:16]}"

    @staticmethod
    def _import_run_status(*, exhausted: bool, failed_rows: int) -> str:
        if not exhausted:
            return RealPlayerImportRunStatus.PARTIAL.value
        if failed_rows > 0:
            return RealPlayerImportRunStatus.COMPLETED_WITH_ERRORS.value
        return RealPlayerImportRunStatus.COMPLETED.value
