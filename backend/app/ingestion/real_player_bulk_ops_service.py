from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.ingestion.models import Club, Competition, Country
from app.ingestion.real_player_bulk_ops_schemas import (
    RealPlayerBulkImportCommandResult,
    RealPlayerBulkImportRunReport,
)
from app.ingestion.real_player_canonical_mapping_service import (
    CanonicalReferenceResolution,
    RealPlayerCanonicalMappingService,
)
from app.ingestion.real_player_footballsquads_canonical_backfill import (
    FootballsquadsCanonicalBackfillService,
)
from app.ingestion.real_player_identity_normalizer import fold_identity_name
from app.ingestion.real_player_import_models import (
    RealPlayerImportProcessingState,
    RealPlayerImportRun,
    RealPlayerImportRunStatus,
    RealPlayerImportStagingRecord,
)
from app.ingestion.real_player_import_repository import RealPlayerImportRepository
from app.ingestion.real_player_ingestion_service import (
    RealPlayerBatchBlockedError,
    RealPlayerIngestionService,
)
from app.ingestion.real_player_normalization_service import RealPlayerNormalizationService
from app.models.base import utcnow
from app.providers.import_models import RealPlayerSourceItem
from app.schemas.real_player_ingestion import (
    RealPlayerIngestionMode,
    RealPlayerIngestionRequest,
    RealPlayerSeedInput,
)


_UNRESOLVED_PROCESSING_STATES = {
    RealPlayerImportProcessingState.PENDING.value,
    RealPlayerImportProcessingState.NORMALIZED.value,
    RealPlayerImportProcessingState.MAPPED_PARTIAL.value,
}
_FAILED_PROCESSING_STATES = {
    RealPlayerImportProcessingState.ERROR.value,
    RealPlayerImportProcessingState.REJECTED.value,
}
_TOP_FIVE_LEAGUE_KEYS = {
    "premier-league",
    "la-liga",
    "laliga",
    "serie-a",
    "bundesliga",
    "ligue-1",
}
_TOP_CLUB_KEYS = {
    "arsenal",
    "arsenal-fc",
    "barcelona",
    "bayern-munich",
    "chelsea",
    "inter",
    "juventus",
    "liverpool",
    "man-city",
    "manchester-city",
    "paris-saint-germain",
    "psg",
    "real-madrid",
    "real-madrid-cf",
}
_AFRICA_MARKET_REGIONS = {"africa"}
_AFRICA_CONFEDERATIONS = {"CAF"}
_POSITION_FAMILY_FACTORS = {
    "goalkeeper": 0.84,
    "defender": 0.94,
    "midfielder": 1.0,
    "forward": 1.1,
}
_PLAYER_TIER_FACTORS = {
    "watchlist": 0.92,
    "core": 1.0,
    "featured": 1.12,
    "elite": 1.25,
}


class RealPlayerBulkImportOpsError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        self.status_code = status_code
        super().__init__(message)


def _resolution_is_resolved(resolution: CanonicalReferenceResolution | None) -> bool:
    if resolution is None:
        return False
    return resolution.status in {"resolved", "auto_created"} and resolution.canonical_id is not None


@dataclass(slots=True)
class RealPlayerBulkImportOpsService:
    session_factory: sessionmaker[Session]
    settings: Settings = field(default_factory=get_settings)
    normalization_service: RealPlayerNormalizationService = field(default_factory=RealPlayerNormalizationService)
    mapping_service: RealPlayerCanonicalMappingService = field(init=False)
    backfill_service: FootballsquadsCanonicalBackfillService = field(init=False)

    def __post_init__(self) -> None:
        self.mapping_service = RealPlayerCanonicalMappingService(
            settings=self.settings,
            auto_create_missing_entities=False,
        )
        self.backfill_service = FootballsquadsCanonicalBackfillService(settings=self.settings)

    def import_file(
        self,
        *,
        file_path: str,
        provider_name: str,
        batch_size: int = 1000,
    ) -> RealPlayerBulkImportCommandResult:
        resolved_path, rows, file_format, file_hash = self._load_rows_from_file(file_path)
        provider = _required_text(provider_name, label="provider")
        with self.session_factory() as session:
            repository = RealPlayerImportRepository(session)
            run = repository.create_import_run(
                provider_name=provider,
                source_type="bulk_file",
                source_reference=str(resolved_path),
                configured_batch_size=batch_size,
                metadata_json={
                    "file_path": str(resolved_path),
                    "file_format": file_format,
                    "file_sha256": file_hash,
                    "source_row_count": len(rows),
                    "priority_buckets_seen": sorted(
                        {
                            _priority_bucket_for_payload(item)
                            for item in rows
                            if isinstance(item, dict)
                        }
                    ),
                },
            )
            session.commit()
            run_id = run.id

        return self._process_loaded_rows(
            run_id=run_id,
            rows=rows,
            batch_size=batch_size,
            operation="import",
            start_offset=0,
        )

    def resume_import(
        self,
        *,
        run_id: str,
        batch_size: int | None = None,
    ) -> RealPlayerBulkImportCommandResult:
        with self.session_factory() as session:
            run = session.get(RealPlayerImportRun, run_id)
            if run is None:
                raise RealPlayerBulkImportOpsError(
                    f"Real-player bulk import run '{run_id}' was not found.",
                    status_code=404,
                )
            metadata = dict(run.metadata_json or {})
            file_path = _required_text(metadata.get("file_path"), label="stored file_path")
            effective_batch_size = batch_size or max(int(run.configured_batch_size or 0), 1)
            start_offset = _int_or_default(run.resume_cursor, default=run.processed_rows)
            if start_offset < 0:
                start_offset = 0
            repository = RealPlayerImportRepository(session)
            repository.resume_import_run(
                run,
                resume_cursor=str(start_offset),
                configured_batch_size=effective_batch_size,
                metadata_updates={
                    **metadata,
                    "resumed_at": utcnow().isoformat(),
                },
            )
            session.commit()

        _resolved_path, rows, _file_format, _file_hash = self._load_rows_from_file(file_path)
        return self._process_loaded_rows(
            run_id=run_id,
            rows=rows,
            batch_size=effective_batch_size,
            operation="resume",
            start_offset=start_offset,
        )

    def repair_mappings(
        self,
        *,
        run_id: str | None = None,
        state: str | None = None,
    ) -> RealPlayerBulkImportCommandResult:
        if run_id is None and _normalized_state_filter(state) != "unresolved":
            raise RealPlayerBulkImportOpsError(
                "repair_mappings requires --run-id or --state unresolved."
            )

        with self.session_factory() as session:
            records = self._target_records_for_repair(session, run_id=run_id, state=state)
            if not records:
                raise RealPlayerBulkImportOpsError("No staged real-player rows matched the repair target.")

            backfill_report = self.backfill_service.run(session)
            affected_run_ids = {
                record.import_run_id
                for record in records
                if record.import_run_id
            }
            reclassified_rows = 0
            transitioned_ready_rows = 0
            remaining_unresolved_rows = 0

            for record in records:
                before_state = record.processing_state
                after_state = self._reconcile_staging_record(
                    session,
                    record,
                    force=True,
                )
                if after_state != before_state:
                    reclassified_rows += 1
                if before_state != RealPlayerImportProcessingState.MAPPED_READY.value and after_state == RealPlayerImportProcessingState.MAPPED_READY.value:
                    transitioned_ready_rows += 1
                if after_state in _UNRESOLVED_PROCESSING_STATES:
                    remaining_unresolved_rows += 1

            run_report: RealPlayerBulkImportRunReport | None = None
            for affected_run_id in sorted(affected_run_ids):
                run = session.get(RealPlayerImportRun, affected_run_id)
                if run is None:
                    continue
                self._refresh_run_snapshot(session, run)
                self._apply_run_status_after_state_change(run)
                if run_id is not None and affected_run_id == run_id:
                    run_report = self._report_from_run(run)

            session.commit()

        return RealPlayerBulkImportCommandResult(
            operation="repair",
            run=run_report,
            details_json={
                "target_run_id": run_id,
                "target_state": _normalized_state_filter(state) or "run",
                "affected_run_ids": sorted(affected_run_ids),
                "targeted_rows": len(records),
                "reclassified_rows": reclassified_rows,
                "transitioned_ready_rows": transitioned_ready_rows,
                "remaining_unresolved_rows": remaining_unresolved_rows,
                "backfill_resolved_count": backfill_report.resolved_count,
                "backfill_remaining_unresolved_count": backfill_report.remaining_unresolved_count,
                "backfill_resolved_by_entity_type": dict(backfill_report.resolved_counts_by_entity_type),
                "backfill_remaining_unresolved_categories": dict(backfill_report.remaining_unresolved_categories),
            },
        )

    def publish_ready_players(
        self,
        *,
        run_id: str,
        limit: int,
        priority_bucket: str,
        dry_run: bool = False,
    ) -> RealPlayerBulkImportCommandResult:
        priority = _required_text(priority_bucket, label="priority")
        if limit < 1:
            raise RealPlayerBulkImportOpsError("--limit must be greater than zero.")

        with self.session_factory() as session:
            run = session.get(RealPlayerImportRun, run_id)
            if run is None:
                raise RealPlayerBulkImportOpsError(
                    f"Real-player bulk import run '{run_id}' was not found.",
                    status_code=404,
                )
            selected_records = self._select_publish_candidates(
                session,
                run_id=run.id,
                limit=limit,
                priority_bucket=priority,
            )
            if not selected_records:
                raise RealPlayerBulkImportOpsError(
                    f"No publish-ready rows matched run '{run_id}' and priority '{priority}'.",
                    status_code=409,
                )
            run_report = self._report_from_run(run)

        selected_payloads: list[RealPlayerSeedInput] = []
        payload_build_errors: dict[tuple[str, str], str] = {}
        for record in selected_records:
            try:
                selected_payloads.append(self._seed_input_from_staging(record))
            except RealPlayerBulkImportOpsError as exc:
                payload_build_errors[(record.provider_name, record.provider_player_id)] = str(exc)

        validation_issue_keys: set[tuple[str, str]] = set()
        validation_issue_payloads: dict[tuple[str, str], dict[str, object]] = {}
        clean_payloads = list(selected_payloads)
        if selected_payloads:
            validation_request = self._publish_request(
                run_id=run_id,
                sequence=run_report.published_rows + 1,
                payloads=selected_payloads,
            )
            validation_report = RealPlayerIngestionService(
                session_factory=self.session_factory,
                settings=self.settings,
            ).validate(validation_request)
            validation_issue_keys = {
                (issue.source_name, issue.source_player_key)
                for issue in validation_report.issues
            }
            validation_issue_payloads = {
                (issue.source_name, issue.source_player_key): issue.model_dump(mode="json")
                for issue in validation_report.issues
            }
            clean_payloads = [
                payload
                for payload in selected_payloads
                if (payload.source_name, payload.source_player_key) not in validation_issue_keys
            ]

        details = {
            "run_id": run_id,
            "priority_bucket": priority,
            "limit": limit,
            "dry_run": dry_run,
            "selected_rows": len(selected_records),
            "selected_source_keys": [
                f"{record.provider_name}:{record.provider_player_id}"
                for record in selected_records
            ],
            "payload_build_errors": {
                f"{source_name}:{source_player_key}": message
                for (source_name, source_player_key), message in payload_build_errors.items()
            },
            "validation_issue_count": len(validation_issue_keys),
            "validation_issues": {
                f"{source_name}:{source_player_key}": issue_payload
                for (source_name, source_player_key), issue_payload in validation_issue_payloads.items()
            },
            "would_publish_rows": len(clean_payloads),
            "excluded_rows": len(selected_records) - len(clean_payloads),
        }
        if dry_run:
            return RealPlayerBulkImportCommandResult(
                operation="publish",
                run=run_report,
                details_json=details,
            )

        write_report = None
        published_now = 0
        published_batch_id: str | None = None
        if clean_payloads:
            publish_request = self._publish_request(
                run_id=run_id,
                sequence=run_report.published_rows + 1,
                payloads=clean_payloads,
            )
            try:
                write_report = RealPlayerIngestionService(
                    session_factory=self.session_factory,
                    settings=self.settings,
                ).write_batch(publish_request)
            except RealPlayerBatchBlockedError as exc:
                validation_issue_keys |= {
                    (issue.source_name, issue.source_player_key)
                    for issue in exc.report.issues
                }
                validation_issue_payloads.update(
                    {
                        (issue.source_name, issue.source_player_key): issue.model_dump(mode="json")
                        for issue in exc.report.issues
                    }
                )

        with self.session_factory() as session:
            run = session.get(RealPlayerImportRun, run_id)
            if run is None:
                raise RealPlayerBulkImportOpsError(
                    f"Real-player bulk import run '{run_id}' was not found after publish.",
                    status_code=404,
                )
            records = self._records_by_source_key(
                session,
                run_id=run_id,
                source_keys={
                    (record.provider_name, record.provider_player_id)
                    for record in selected_records
                },
            )
            for source_key, message in payload_build_errors.items():
                record = records.get(source_key)
                if record is None:
                    continue
                self._set_processing_state(
                    record,
                    processing_state=RealPlayerImportProcessingState.ERROR.value,
                    error_message=message,
                )

            for source_key, issue_payload in validation_issue_payloads.items():
                record = records.get(source_key)
                if record is None:
                    continue
                processing_state = (
                    RealPlayerImportProcessingState.MAPPED_PARTIAL.value
                    if issue_payload.get("issue_type") == "ambiguous_match"
                    else RealPlayerImportProcessingState.ERROR.value
                )
                self._set_processing_state(
                    record,
                    processing_state=processing_state,
                    error_message=str(issue_payload.get("message") or issue_payload.get("issue_type") or "validation_error"),
                )
                metadata = dict(record.metadata_json or {})
                metadata["last_publish_issue"] = issue_payload
                record.metadata_json = metadata

            if write_report is not None:
                published_batch_id = write_report.ingestion_batch_id
                results_by_source_key = {
                    (result.source_name, result.source_player_key): result
                    for result in write_report.results
                }
                for payload in clean_payloads:
                    source_key = (payload.source_name, payload.source_player_key)
                    record = records.get(source_key)
                    if record is None:
                        continue
                    result = results_by_source_key.get(source_key)
                    if result is None:
                        continue
                    published_now += 1
                    self._set_processing_state(
                        record,
                        processing_state=RealPlayerImportProcessingState.PUBLISHED.value,
                        error_message=None,
                    )
                    metadata = dict(record.metadata_json or {})
                    metadata["published_ingestion_batch_id"] = write_report.ingestion_batch_id
                    metadata["published_at"] = utcnow().isoformat()
                    metadata["published_player_id"] = result.gtex_player_id
                    metadata["published_pricing_snapshot_id"] = result.pricing_snapshot_id
                    record.metadata_json = metadata

            self._refresh_run_snapshot(session, run)
            self._apply_run_status_after_state_change(run)
            session.commit()
            run_report = self._report_from_run(run)

        details.update(
            {
                "published_now": published_now,
                "published_batch_id": published_batch_id,
                "write_batch_id": published_batch_id,
            }
        )
        return RealPlayerBulkImportCommandResult(
            operation="publish",
            run=run_report,
            details_json=details,
        )

    def report_run(self, *, run_id: str) -> RealPlayerBulkImportCommandResult:
        with self.session_factory() as session:
            run = session.get(RealPlayerImportRun, run_id)
            if run is None:
                raise RealPlayerBulkImportOpsError(
                    f"Real-player bulk import run '{run_id}' was not found.",
                    status_code=404,
                )
            snapshot = _snapshot_from_metadata(run.metadata_json or {})
            if snapshot is None:
                self._refresh_run_snapshot(session, run)
                session.commit()
            return RealPlayerBulkImportCommandResult(
                operation="report",
                run=self._report_from_run(run),
                details_json={},
            )

    def _process_loaded_rows(
        self,
        *,
        run_id: str,
        rows: list[dict[str, object]],
        batch_size: int,
        operation: str,
        start_offset: int,
    ) -> RealPlayerBulkImportCommandResult:
        with self.session_factory() as session:
            run = session.get(RealPlayerImportRun, run_id)
            if run is None:
                raise RealPlayerBulkImportOpsError(
                    f"Real-player bulk import run '{run_id}' was not found.",
                    status_code=404,
                )
            start_processed_rows = run.processed_rows
            provider_name = run.provider_name

        offset = max(start_offset, 0)
        batch_count = 0
        while offset < len(rows):
            batch_rows = rows[offset : offset + batch_size]
            try:
                self._process_import_batch(
                    run_id=run_id,
                    provider_name=provider_name,
                    rows=batch_rows,
                    start_row_number=offset + 1,
                    next_offset=offset + len(batch_rows),
                    total_rows=len(rows),
                )
            except Exception as exc:
                return self._finalize_import_command(
                    run_id=run_id,
                    operation=operation,
                    error_message=str(exc),
                    resume_cursor=str(offset),
                    start_processed_rows=start_processed_rows,
                    batch_count=batch_count,
                )
            offset += len(batch_rows)
            batch_count += 1

        return self._finalize_import_command(
            run_id=run_id,
            operation=operation,
            error_message=None,
            resume_cursor=None,
            start_processed_rows=start_processed_rows,
            batch_count=batch_count,
        )

    def _process_import_batch(
        self,
        *,
        run_id: str,
        provider_name: str,
        rows: list[dict[str, object]],
        start_row_number: int,
        next_offset: int,
        total_rows: int,
    ) -> None:
        with self.session_factory() as session:
            run = session.get(RealPlayerImportRun, run_id)
            if run is None:
                raise RealPlayerBulkImportOpsError(
                    f"Real-player bulk import run '{run_id}' was not found.",
                    status_code=404,
                )
            repository = RealPlayerImportRepository(session)
            items: list[RealPlayerSourceItem] = []
            for row_offset, raw_row in enumerate(rows, start=start_row_number):
                items.append(
                    self._source_item_from_raw_row(
                        raw_row,
                        provider_name=provider_name,
                        source_row_number=row_offset,
                    )
                )

            stats = repository.upsert_staging_records(
                provider_name=provider_name,
                items=items,
                source_version=f"bulk-file:{run.id}",
                last_import_run_id=run.id,
                last_import_cursor=None if next_offset >= total_rows else str(next_offset),
                import_run_id=run.id,
                import_batch_key=run.id,
                default_processing_state=RealPlayerImportProcessingState.PENDING.value,
            )
            records = [
                repository.get_staging_record(
                    provider_name=provider_name,
                    provider_player_id=item.provider_player_id,
                )
                for item in items
            ]
            self._reconcile_staging_records(
                session,
                records=[record for record in records if record is not None],
            )
            repository.mark_import_run_progress(
                run,
                stats=stats,
                batch_marker=f"{start_row_number}-{start_row_number + len(rows) - 1}",
                resume_cursor=None if next_offset >= total_rows else str(next_offset),
                metadata_updates={
                    **(run.metadata_json or {}),
                    "source_row_count": total_rows,
                },
            )
            session.commit()

    def _finalize_import_command(
        self,
        *,
        run_id: str,
        operation: str,
        error_message: str | None,
        resume_cursor: str | None,
        start_processed_rows: int,
        batch_count: int,
    ) -> RealPlayerBulkImportCommandResult:
        with self.session_factory() as session:
            run = session.get(RealPlayerImportRun, run_id)
            if run is None:
                raise RealPlayerBulkImportOpsError(
                    f"Real-player bulk import run '{run_id}' was not found.",
                    status_code=404,
                )
            repository = RealPlayerImportRepository(session)
            self._refresh_run_snapshot(session, run)
            if error_message:
                status = (
                    RealPlayerImportRunStatus.PARTIAL.value
                    if run.processed_rows > 0
                    else RealPlayerImportRunStatus.FAILED.value
                )
            else:
                status = self._completion_status(run)
            repository.finish_import_run(
                run,
                status=status,
                error_message=error_message,
                resume_cursor=resume_cursor,
            )
            self._refresh_run_snapshot(session, run)
            session.commit()
            report = self._report_from_run(run)

        return RealPlayerBulkImportCommandResult(
            operation=operation,  # type: ignore[arg-type]
            run=report,
            details_json={
                "rows_processed_this_operation": max(report.processed_rows - start_processed_rows, 0),
                "batch_count": batch_count,
                "resume_cursor": report.resume_cursor,
                "error_message": error_message,
            },
        )

    def _refresh_run_snapshot(self, session: Session, run: RealPlayerImportRun) -> None:
        repository = RealPlayerImportRepository(session)
        repository.refresh_run_state_counts(run)
        rows = list(
            session.scalars(
                select(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.import_run_id == run.id
                )
            )
        )
        distribution = Counter(
            row.processing_state or RealPlayerImportProcessingState.PENDING.value
            for row in rows
        )
        snapshot = {
            "generated_at": utcnow().isoformat(),
            "processing_state_distribution": dict(sorted(distribution.items())),
            "mapped_rows": distribution.get(RealPlayerImportProcessingState.MAPPED_READY.value, 0)
            + distribution.get(RealPlayerImportProcessingState.PUBLISHED.value, 0),
            "mapped_ready_rows": distribution.get(RealPlayerImportProcessingState.MAPPED_READY.value, 0),
            "mapped_partial_rows": distribution.get(RealPlayerImportProcessingState.MAPPED_PARTIAL.value, 0),
            "unresolved_rows": sum(
                distribution.get(state, 0)
                for state in _UNRESOLVED_PROCESSING_STATES
            ),
            "publish_ready_rows": distribution.get(RealPlayerImportProcessingState.MAPPED_READY.value, 0),
            "published_rows": distribution.get(RealPlayerImportProcessingState.PUBLISHED.value, 0),
            "failed_rows": sum(
                distribution.get(state, 0)
                for state in _FAILED_PROCESSING_STATES
            ),
        }
        metadata = dict(run.metadata_json or {})
        metadata["report_snapshot"] = snapshot
        run.metadata_json = metadata

    def _completion_status(self, run: RealPlayerImportRun) -> str:
        if run.resume_cursor:
            return RealPlayerImportRunStatus.PARTIAL.value
        if run.failed_rows or run.unresolved_rows:
            return RealPlayerImportRunStatus.COMPLETED_WITH_ERRORS.value
        return RealPlayerImportRunStatus.COMPLETED.value

    @staticmethod
    def _apply_run_status_after_state_change(run: RealPlayerImportRun) -> None:
        if run.resume_cursor:
            run.status = RealPlayerImportRunStatus.PARTIAL.value
            return
        run.status = (
            RealPlayerImportRunStatus.COMPLETED_WITH_ERRORS.value
            if run.failed_rows or run.unresolved_rows
            else RealPlayerImportRunStatus.COMPLETED.value
        )
        if run.completed_at is None:
            run.completed_at = utcnow()

    def _target_records_for_repair(
        self,
        session: Session,
        *,
        run_id: str | None,
        state: str | None,
    ) -> list[RealPlayerImportStagingRecord]:
        statement = select(RealPlayerImportStagingRecord).order_by(
            RealPlayerImportStagingRecord.created_at.asc(),
            RealPlayerImportStagingRecord.id.asc(),
        )
        if run_id is not None:
            statement = statement.where(RealPlayerImportStagingRecord.import_run_id == run_id)
        normalized_state = _normalized_state_filter(state)
        if normalized_state == "unresolved" or run_id is not None:
            statement = statement.where(
                RealPlayerImportStagingRecord.processing_state.in_(
                    tuple(sorted(_UNRESOLVED_PROCESSING_STATES))
                )
            )
        return list(session.scalars(statement))

    def _select_publish_candidates(
        self,
        session: Session,
        *,
        run_id: str,
        limit: int,
        priority_bucket: str,
    ) -> list[RealPlayerImportStagingRecord]:
        candidates = list(
            session.scalars(
                select(RealPlayerImportStagingRecord)
                .where(
                    RealPlayerImportStagingRecord.import_run_id == run_id,
                    RealPlayerImportStagingRecord.processing_state == RealPlayerImportProcessingState.MAPPED_READY.value,
                )
                .order_by(
                    RealPlayerImportStagingRecord.last_processed_at.asc().nullsfirst(),
                    RealPlayerImportStagingRecord.created_at.asc(),
                    RealPlayerImportStagingRecord.id.asc(),
                )
            )
        )
        filtered = [
            record
            for record in candidates
            if _matches_priority_selector(record.metadata_json, priority_bucket)
        ]
        filtered.sort(
            key=lambda record: (
                -_priority_score_for_metadata(record.metadata_json),
                -_market_value_for_metadata(record.metadata_json),
                record.last_processed_at or datetime.min.replace(tzinfo=UTC),
                record.created_at,
                record.id,
            )
        )
        return filtered[:limit]

    def _records_by_source_key(
        self,
        session: Session,
        *,
        run_id: str,
        source_keys: set[tuple[str, str]],
    ) -> dict[tuple[str, str], RealPlayerImportStagingRecord]:
        rows = list(
            session.scalars(
                select(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.import_run_id == run_id,
                )
            )
        )
        return {
            (row.provider_name, row.provider_player_id): row
            for row in rows
            if (row.provider_name, row.provider_player_id) in source_keys
        }

    def _reconcile_staging_records(
        self,
        session: Session,
        *,
        records: list[RealPlayerImportStagingRecord],
    ) -> None:
        for record in records:
            self._reconcile_staging_record(session, record)

    def _reconcile_staging_record(
        self,
        session: Session,
        record: RealPlayerImportStagingRecord,
        *,
        force: bool = False,
    ) -> str:
        if not force and record.processing_state == RealPlayerImportProcessingState.PUBLISHED.value:
            return record.processing_state

        try:
            payload = self._seed_input_from_staging(record)
            normalized = self.normalization_service.normalize(payload, as_of=datetime.now(UTC))
        except Exception as exc:
            self._set_processing_state(
                record,
                processing_state=RealPlayerImportProcessingState.ERROR.value,
                error_message=f"Normalization failed: {exc}",
            )
            return record.processing_state

        payload_json = payload.model_dump(mode="json")
        country_resolution: CanonicalReferenceResolution | None = None
        if payload.nationality or payload.nationality_code:
            country_resolution = self.mapping_service.resolve_country(
                session,
                source_name=payload.source_name,
                provider_external_id=payload.nationality_code,
                name=payload.nationality,
                sample_payload=payload_json,
            )
        country = country_resolution.entity if _resolution_is_resolved(country_resolution) else None

        competition_resolution: CanonicalReferenceResolution | None = None
        if payload.current_real_world_league or payload.current_real_world_league_key:
            competition_resolution = self.mapping_service.resolve_competition(
                session,
                source_name=payload.source_name,
                provider_external_id=payload.current_real_world_league_key,
                name=payload.current_real_world_league,
                country=None,
                country_code=None,
                country_name=None,
                sample_payload=payload_json,
            )
        competition = competition_resolution.entity if _resolution_is_resolved(competition_resolution) else None

        club_resolution: CanonicalReferenceResolution | None = None
        if payload.current_real_world_club or payload.current_real_world_club_key:
            club_resolution = self.mapping_service.resolve_club(
                session,
                source_name=payload.source_name,
                provider_external_id=payload.current_real_world_club_key,
                name=payload.current_real_world_club,
                country=competition.country if competition is not None else None,
                country_code=None,
                country_name=None,
                competition=competition,
                competition_external_id=payload.current_real_world_league_key,
                competition_name=payload.current_real_world_league,
                sample_payload=payload_json,
            )
        club = club_resolution.entity if _resolution_is_resolved(club_resolution) else None
        if competition is None and club is not None and club.current_competition_id:
            competition = session.get(Competition, club.current_competition_id)

        publish_missing_fields = self._publish_missing_fields(
            payload=payload,
            normalized=normalized,
            country_resolution=country_resolution,
            competition=competition,
            club=club,
        )
        valuation = self._valuation_summary(
            payload=payload,
            normalized=normalized,
            country=country if isinstance(country, Country) else None,
            competition=competition if isinstance(competition, Competition) else None,
            club=club if isinstance(club, Club) else None,
        )
        if valuation["market_value_eur"] is None:
            publish_missing_fields = tuple(dict.fromkeys([*publish_missing_fields, "market_value"]))

        tracked_unresolved_labels = tuple(
            label
            for label, resolution in (
                ("country", country_resolution),
                ("competition", competition_resolution),
                ("club", club_resolution),
            )
            if resolution is not None and resolution.status == "unresolved"
        )
        publish_ready = not publish_missing_fields
        processing_state = (
            RealPlayerImportProcessingState.MAPPED_READY.value
            if publish_ready
            else RealPlayerImportProcessingState.MAPPED_PARTIAL.value
        )
        priority = self._publish_priority_summary(
            normalized=normalized,
            country=country if isinstance(country, Country) else None,
            competition=competition if isinstance(competition, Competition) else None,
            club=club if isinstance(club, Club) else None,
            market_value_eur=float(valuation["market_value_eur"] or 0.0),
            fallback_used=bool(valuation["fallback_used"]),
        )

        self._set_processing_state(
            record,
            processing_state=processing_state,
            error_message=None,
        )
        metadata = dict(record.metadata_json or {})
        metadata["latest_mapping_check_at"] = utcnow().isoformat()
        metadata["mapping"] = {
            "country": country_resolution.metadata() if country_resolution is not None else None,
            "competition": competition_resolution.metadata() if competition_resolution is not None else None,
            "club": club_resolution.metadata() if club_resolution is not None else None,
            "tracked_unresolved_labels": list(tracked_unresolved_labels),
        }
        metadata["normalized_profile"] = {
            "canonical_name": normalized.canonical_name,
            "display_name": normalized.display_name,
            "primary_position": normalized.primary_position,
            "secondary_positions": list(normalized.secondary_positions),
            "normalized_position": normalized.normalized_position,
            "role_label": self._role_label(normalized.normalized_position),
            "age_years": normalized.age_years,
            "competition_level": normalized.competition_level,
            "real_player_tier": normalized.real_player_tier,
            "profile_completeness_score": normalized.profile_completeness_score,
        }
        metadata["publish_contract"] = {
            "staging_minimum": {
                "required_fields": ["source_player_key", "canonical_name"],
                "met": bool(payload.source_player_key and payload.canonical_name),
            },
            "publish_minimum": {
                "required_fields": [
                    "country_mapping",
                    "team_context_mapping",
                    "primary_position",
                    "age_reference",
                    "market_value",
                    "profile_completeness",
                ],
                "missing_fields": list(publish_missing_fields),
                "met": publish_ready,
            },
            "publish_ready": publish_ready,
        }
        metadata["valuation"] = valuation
        metadata["publish_priority"] = priority
        record.metadata_json = metadata
        return record.processing_state

    def _publish_missing_fields(
        self,
        *,
        payload: RealPlayerSeedInput,
        normalized,
        country_resolution: CanonicalReferenceResolution | None,
        competition: Competition | None,
        club: Club | None,
    ) -> tuple[str, ...]:
        missing: list[str] = []
        if not _resolution_is_resolved(country_resolution):
            missing.append("country_mapping")
        if club is None and competition is None:
            missing.append("team_context_mapping")
        if not str(payload.primary_position or "").strip():
            missing.append("primary_position")
        if not any((payload.date_of_birth, payload.birth_year, payload.age)):
            missing.append("age_reference")
        if float(normalized.profile_completeness_score or 0.0) < 0.62:
            missing.append("profile_completeness")
        return tuple(dict.fromkeys(missing))

    def _valuation_summary(
        self,
        *,
        payload: RealPlayerSeedInput,
        normalized,
        country: Country | None,
        competition: Competition | None,
        club: Club | None,
    ) -> dict[str, object]:
        if payload.current_market_reference_value is not None and payload.market_reference_currency == "EUR":
            return {
                "market_value_eur": round(float(payload.current_market_reference_value), 2),
                "source": "source_reference",
                "fallback_used": False,
                "confidence_score": 0.88,
                "reasons": ["source_market_reference"],
            }

        market_value_eur = self._fallback_valuation_eur(
            normalized=normalized,
            country=country,
            competition=competition,
            club=club,
        )
        confidence = 0.38
        if country is not None:
            confidence += 0.10
        if club is not None or competition is not None:
            confidence += 0.10
        confidence += max(float(normalized.profile_completeness_score or 0.0) - 0.55, 0.0) * 0.7
        confidence = min(max(confidence, 0.35), 0.74)
        return {
            "market_value_eur": round(market_value_eur, 2),
            "source": "fallback",
            "fallback_used": True,
            "confidence_score": round(confidence, 4),
            "reasons": ["fallback_market_value"],
            "inputs": {
                "age_years": normalized.age_years,
                "competition_level": normalized.competition_level,
                "normalized_position": normalized.normalized_position,
                "club_strength_score": normalized.club_strength_score,
                "profile_completeness_score": normalized.profile_completeness_score,
            },
        }

    def _fallback_valuation_eur(
        self,
        *,
        normalized,
        country: Country | None,
        competition: Competition | None,
        club: Club | None,
    ) -> float:
        age_base = self._age_band_base_value(normalized.age_years)
        competition_strength = (
            float(competition.competition_strength)
            if competition is not None and competition.competition_strength is not None
            else float(normalized.competition_strength_multiplier)
        )
        competition_factor = min(max(competition_strength, 0.75), 1.3)
        club_strength_source = (
            float(club.popularity_score)
            if club is not None and club.popularity_score is not None
            else float(normalized.club_strength_score)
        )
        club_factor = min(max(0.75 + ((club_strength_source / 100.0) * 0.6), 0.75), 1.35)
        position_factor = _POSITION_FAMILY_FACTORS.get(normalized.normalized_position, 1.0)
        player_tier_factor = _PLAYER_TIER_FACTORS.get(normalized.real_player_tier, 1.0)
        prospect_factor = 1.15 if normalized.age_years is not None and normalized.age_years <= 21 else 1.0
        africa_boost = 1.04 if self._is_africa_relevant(country=country, competition=competition, club=club) else 1.0
        completeness_factor = min(
            max(0.82 + max(float(normalized.profile_completeness_score or 0.0) - 0.55, 0.0) * 1.2, 0.82),
            1.08,
        )
        value = age_base * competition_factor * club_factor * position_factor * player_tier_factor * prospect_factor * africa_boost * completeness_factor
        return max(value, 250_000.0)

    def _publish_priority_summary(
        self,
        *,
        normalized,
        country: Country | None,
        competition: Competition | None,
        club: Club | None,
        market_value_eur: float,
        fallback_used: bool,
    ) -> dict[str, object]:
        score = 0.0
        reasons: list[str] = []
        competition_key = _entity_key(competition.name if competition is not None else normalized.current_real_world_league)
        club_key = _entity_key(club.name if club is not None else normalized.current_real_world_club)
        is_top_five_league = competition_key in _TOP_FIVE_LEAGUE_KEYS
        is_top_club = club_key in _TOP_CLUB_KEYS or bool(
            club is not None and club.popularity_score is not None and float(club.popularity_score) >= 82.0
        )
        is_top_player = market_value_eur >= 18_000_000.0
        is_africa_relevant = self._is_africa_relevant(country=country, competition=competition, club=club)
        is_nigerian = self._is_nigerian(country=country)
        is_wonderkid = bool(
            normalized.age_years is not None
            and normalized.age_years <= 21
            and (
                market_value_eur >= 2_500_000.0
                or normalized.real_player_tier in {"featured", "elite"}
                or is_top_five_league
            )
        )

        if is_top_five_league:
            score += 40.0
            reasons.append("top_5_league")
        if is_top_club:
            score += 28.0
            reasons.append("top_club")
        if is_top_player:
            score += 22.0
            reasons.append("top_player")
        if is_africa_relevant:
            score += 24.0
            reasons.append("africa_relevant")
        if is_nigerian:
            score += 10.0
            reasons.append("nigeria_priority")
        if is_wonderkid:
            score += 26.0
            reasons.append("wonderkid")
        if normalized.real_player_tier in {"elite", "featured"} and "top_player" not in reasons:
            score += 8.0
            reasons.append("high_interest")

        score += min(market_value_eur / 1_000_000.0, 25.0)
        score += min(float(normalized.form_signal or 0.0) / 10.0, 10.0)
        if fallback_used:
            score -= 3.0

        return {
            "bucket": self._derived_priority_bucket(score=score, reasons=reasons),
            "score": round(score, 2),
            "reasons": list(dict.fromkeys(reasons)),
        }

    @staticmethod
    def _derived_priority_bucket(*, score: float, reasons: list[str]) -> str:
        if reasons and (score >= 65.0 or any(reason in {"top_5_league", "top_club", "top_player", "wonderkid"} for reason in reasons)):
            return "high"
        if score >= 35.0:
            return "default"
        return "watchlist"

    @staticmethod
    def _age_band_base_value(age_years: int | None) -> float:
        if age_years is None:
            return 5_000_000.0
        if age_years <= 18:
            return 3_500_000.0
        if age_years <= 21:
            return 6_000_000.0
        if age_years <= 24:
            return 8_500_000.0
        if age_years <= 27:
            return 9_500_000.0
        if age_years <= 30:
            return 7_000_000.0
        return 4_000_000.0

    @staticmethod
    def _role_label(normalized_position: str) -> str:
        return {
            "goalkeeper": "goalkeeper",
            "defender": "defender",
            "midfielder": "midfielder",
            "forward": "attacker",
        }.get(normalized_position, "utility")

    def _is_africa_relevant(
        self,
        *,
        country: Country | None,
        competition: Competition | None,
        club: Club | None,
    ) -> bool:
        countries = [
            country,
            competition.country if competition is not None else None,
            club.country if club is not None else None,
        ]
        for item in countries:
            if item is None:
                continue
            if (item.market_region or "").strip().lower() in _AFRICA_MARKET_REGIONS:
                return True
            if (item.confederation_code or "").strip().upper() in _AFRICA_CONFEDERATIONS:
                return True
        return False

    @staticmethod
    def _is_nigerian(*, country: Country | None) -> bool:
        return bool(country is not None and (country.alpha2_code or "").strip().upper() == "NG")

    def _source_item_from_raw_row(
        self,
        raw_row: dict[str, object],
        *,
        provider_name: str,
        source_row_number: int,
    ) -> RealPlayerSourceItem:
        if not isinstance(raw_row, dict):
            raise RealPlayerBulkImportOpsError(
                f"Malformed bulk import input at row {source_row_number}: expected a JSON object."
            )
        priority_bucket = _priority_bucket_for_payload(raw_row)
        payload = {
            "source_name": provider_name,
            "source_player_key": _required_text(
                _first_value(raw_row, "provider_player_id", "source_player_key", "id"),
                label=f"row {source_row_number} source_player_key",
            ),
            "canonical_name": _required_text(
                _first_value(raw_row, "canonical_name", "full_name", "name", "display_name"),
                label=f"row {source_row_number} canonical_name",
            ),
            "display_name": _first_value(raw_row, "display_name", "full_name", "short_name"),
            "known_aliases": _list_value(raw_row.get("known_aliases")),
            "nationality": _first_value(raw_row, "nationality", "nationality_name"),
            "nationality_code": _first_value(raw_row, "nationality_code"),
            "date_of_birth": _first_value(raw_row, "date_of_birth"),
            "birth_year": raw_row.get("birth_year"),
            "age": raw_row.get("age"),
            "dominant_foot": _first_value(raw_row, "dominant_foot"),
            "primary_position": _first_value(raw_row, "primary_position", "display_position"),
            "secondary_positions": _list_value(raw_row.get("secondary_positions")),
            "current_real_world_club": _first_value(raw_row, "current_real_world_club", "current_club_name"),
            "current_real_world_club_key": _first_value(raw_row, "current_real_world_club_key", "current_club_id"),
            "current_real_world_league": _first_value(raw_row, "current_real_world_league", "current_competition_name"),
            "current_real_world_league_key": _first_value(raw_row, "current_real_world_league_key", "current_competition_id"),
            "competition_level": _first_value(raw_row, "competition_level"),
            "appearances": raw_row.get("appearances"),
            "minutes_played": raw_row.get("minutes_played"),
            "goals": raw_row.get("goals"),
            "assists": raw_row.get("assists"),
            "clean_sheets": raw_row.get("clean_sheets"),
            "injury_status": _first_value(raw_row, "injury_status"),
            "height_cm": raw_row.get("height_cm"),
            "weight_kg": raw_row.get("weight_kg"),
            "current_market_reference_value": _first_value(
                raw_row,
                "current_market_reference_value",
                "rough_market_value",
            ),
            "market_reference_currency": _first_value(
                raw_row,
                "market_reference_currency",
                "rough_market_value_currency",
            )
            or "EUR",
            "source_last_refreshed_at": _first_value(
                raw_row,
                "source_last_refreshed_at",
                "provider_last_updated_at",
            ),
            "real_player_tier": _first_value(raw_row, "real_player_tier"),
        }
        try:
            seed_input = RealPlayerSeedInput.model_validate(payload)
        except Exception as exc:
            raise RealPlayerBulkImportOpsError(
                f"Malformed bulk import input at row {source_row_number}: {exc}"
            ) from exc

        first_name, last_name = _split_name(seed_input.canonical_name)
        metadata = _dict_value(raw_row.get("metadata_json"))
        metadata["priority_bucket"] = priority_bucket
        metadata["source_row_number"] = source_row_number
        raw_payload = seed_input.model_dump(mode="json")
        return RealPlayerSourceItem(
            provider_player_id=seed_input.source_player_key,
            full_name=seed_input.canonical_name,
            first_name=first_name,
            last_name=last_name,
            short_name=seed_input.display_name,
            normalized_name=fold_identity_name(seed_input.canonical_name),
            display_position=seed_input.primary_position,
            nationality_name=seed_input.nationality,
            nationality_code=seed_input.nationality_code,
            date_of_birth=seed_input.date_of_birth,
            age=seed_input.age,
            current_club_id=seed_input.current_real_world_club_key,
            current_club_name=seed_input.current_real_world_club,
            current_competition_id=seed_input.current_real_world_league_key,
            current_competition_name=seed_input.current_real_world_league,
            rough_market_value=seed_input.current_market_reference_value,
            rough_market_value_currency=seed_input.market_reference_currency,
            provider_last_updated_at=seed_input.source_last_refreshed_at,
            metadata_json=metadata,
            raw_payload=raw_payload,
        )

    def _seed_input_from_staging(
        self,
        record: RealPlayerImportStagingRecord,
    ) -> RealPlayerSeedInput:
        payload = dict(record.latest_payload_json or {})
        if not payload:
            raise RealPlayerBulkImportOpsError(
                f"Staging record '{record.provider_name}:{record.provider_player_id}' has no payload."
            )
        try:
            return RealPlayerSeedInput.model_validate(payload)
        except Exception as exc:
            raise RealPlayerBulkImportOpsError(
                f"Staging record '{record.provider_name}:{record.provider_player_id}' is invalid: {exc}"
            ) from exc

    def _publish_request(
        self,
        *,
        run_id: str,
        sequence: int,
        payloads: list[RealPlayerSeedInput],
    ) -> RealPlayerIngestionRequest:
        return RealPlayerIngestionRequest.model_validate(
            {
                "mode": RealPlayerIngestionMode.BATCH_IMPORT.value,
                "ingestion_batch_id": _publish_batch_id(run_id=run_id, sequence=sequence),
                "ingestion_source_version": f"bulk-import-run:{run_id}",
                "as_of": utcnow().isoformat(),
                "players": [payload.model_dump(mode="json") for payload in payloads],
            }
        )

    def _load_rows_from_file(
        self,
        file_path: str,
    ) -> tuple[Path, list[dict[str, object]], str, str]:
        resolved_path = Path(file_path).expanduser().resolve()
        if not resolved_path.exists():
            raise RealPlayerBulkImportOpsError(
                f"Bulk import file '{resolved_path}' does not exist.",
                status_code=404,
            )
        try:
            payload_text = resolved_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise RealPlayerBulkImportOpsError(
                f"Bulk import file '{resolved_path}' is not valid UTF-8: {exc}"
            ) from exc

        file_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        suffix = resolved_path.suffix.lower()
        rows: list[dict[str, object]]
        if suffix in {".jsonl", ".ndjson"}:
            rows = []
            for line_number, line in enumerate(payload_text.splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RealPlayerBulkImportOpsError(
                        f"Malformed JSON on line {line_number} of '{resolved_path}': {exc.msg}"
                    ) from exc
                if not isinstance(payload, dict):
                    raise RealPlayerBulkImportOpsError(
                        f"Malformed JSON on line {line_number} of '{resolved_path}': expected an object."
                    )
                rows.append(payload)
            file_format = "jsonl"
        else:
            try:
                payload = json.loads(payload_text)
            except json.JSONDecodeError as exc:
                raise RealPlayerBulkImportOpsError(
                    f"Malformed JSON in '{resolved_path}': {exc.msg} (line {exc.lineno}, column {exc.colno})."
                ) from exc
            if isinstance(payload, list):
                rows = payload
            elif isinstance(payload, dict):
                candidate = payload.get("players")
                if not isinstance(candidate, list):
                    candidate = payload.get("items")
                if not isinstance(candidate, list):
                    candidate = payload.get("rows")
                if not isinstance(candidate, list):
                    raise RealPlayerBulkImportOpsError(
                        f"Bulk import file '{resolved_path}' must contain a JSON array or an object with players/items/rows."
                    )
                rows = candidate
            else:
                raise RealPlayerBulkImportOpsError(
                    f"Bulk import file '{resolved_path}' must contain a JSON array or object."
                )
            file_format = "json"

        for index, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                raise RealPlayerBulkImportOpsError(
                    f"Malformed bulk import input at row {index}: expected a JSON object."
                )
        return resolved_path, rows, file_format, file_hash

    @staticmethod
    def _report_from_run(run: RealPlayerImportRun) -> RealPlayerBulkImportRunReport:
        snapshot = _snapshot_from_metadata(run.metadata_json or {}) or {}
        distribution = dict(snapshot.get("processing_state_distribution") or {})
        return RealPlayerBulkImportRunReport(
            id=run.id,
            provider_name=run.provider_name,
            source_type=run.source_type,
            source_reference=run.source_reference,
            configured_batch_size=int(run.configured_batch_size or 0),
            total_rows_discovered=int(run.total_rows_discovered or 0),
            processed_rows=int(run.processed_rows or 0),
            inserted_rows=int(run.inserted_rows or 0),
            updated_rows=int(run.updated_rows or 0),
            duplicate_skipped_rows=int(run.duplicate_skipped_rows or 0),
            mapped_rows=_int_snapshot_value(snapshot, "mapped_rows", default=0),
            mapped_ready_rows=_int_snapshot_value(
                snapshot,
                "mapped_ready_rows",
                fallback=snapshot.get("publish_ready_rows"),
                default=int(run.publish_ready_rows or 0),
            ),
            mapped_partial_rows=_int_snapshot_value(snapshot, "mapped_partial_rows", default=0),
            unresolved_rows=_int_snapshot_value(
                snapshot,
                "unresolved_rows",
                default=int(run.unresolved_rows or 0),
            ),
            publish_ready_rows=_int_snapshot_value(
                snapshot,
                "publish_ready_rows",
                default=int(run.publish_ready_rows or 0),
            ),
            published_rows=_int_snapshot_value(
                snapshot,
                "published_rows",
                default=int(run.published_rows or 0),
            ),
            failed_rows=_int_snapshot_value(snapshot, "failed_rows", default=int(run.failed_rows or 0)),
            status=run.status,
            resume_cursor=run.resume_cursor,
            last_successful_batch_marker=run.last_successful_batch_marker,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
            processing_state_distribution=distribution,
            metadata_json=dict(run.metadata_json or {}),
        )

    @staticmethod
    def _set_processing_state(
        record: RealPlayerImportStagingRecord,
        *,
        processing_state: str,
        error_message: str | None,
    ) -> None:
        record.processing_state = processing_state
        record.import_state = "processed"
        record.last_processed_at = utcnow()
        record.error_message = (
            error_message
            if processing_state == RealPlayerImportProcessingState.ERROR.value
            else None
        )
        if processing_state != RealPlayerImportProcessingState.REJECTED.value:
            record.rejection_reason = None


def _first_value(payload: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _int_snapshot_value(
    snapshot: dict[str, object],
    key: str,
    *,
    fallback: object | None = None,
    default: int = 0,
) -> int:
    if key in snapshot and snapshot[key] is not None:
        try:
            return int(snapshot[key])  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default
    if fallback is not None:
        try:
            return int(fallback)
        except (TypeError, ValueError):
            return default
    return default


def _required_text(value: object, *, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RealPlayerBulkImportOpsError(f"Missing required value for {label}.")
    return text


def _list_value(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _dict_value(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _priority_bucket_for_payload(payload: dict[str, object]) -> str:
    metadata = _dict_value(payload.get("metadata_json"))
    candidate = payload.get("priority_bucket") or metadata.get("priority_bucket") or "default"
    return str(candidate).strip() or "default"


def _priority_bucket_for_metadata(metadata_json: object) -> str:
    metadata = _dict_value(metadata_json)
    candidate = metadata.get("priority_bucket") or "default"
    return str(candidate).strip() or "default"


def _publish_priority_for_metadata(metadata_json: object) -> dict[str, object]:
    metadata = _dict_value(metadata_json)
    return _dict_value(metadata.get("publish_priority"))


def _matches_priority_selector(metadata_json: object, selector: str) -> bool:
    requested = str(selector or "").strip().lower()
    if not requested or requested == "all":
        return True
    raw_bucket = _priority_bucket_for_metadata(metadata_json).lower()
    publish_priority = _publish_priority_for_metadata(metadata_json)
    computed_bucket = str(publish_priority.get("bucket") or "").strip().lower()
    reasons = {
        str(item).strip().lower()
        for item in _list_value(publish_priority.get("reasons"))
        if str(item).strip()
    }
    if requested in {"high", "default", "watchlist"}:
        return raw_bucket == requested
    return requested == computed_bucket or requested in reasons


def _priority_score_for_metadata(metadata_json: object) -> float:
    publish_priority = _publish_priority_for_metadata(metadata_json)
    try:
        return float(publish_priority.get("score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _market_value_for_metadata(metadata_json: object) -> float:
    metadata = _dict_value(metadata_json)
    valuation = _dict_value(metadata.get("valuation"))
    try:
        return float(valuation.get("market_value_eur") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _entity_key(value: object) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def _normalized_state_filter(value: str | None) -> str | None:
    cleaned = str(value or "").strip().lower()
    return cleaned or None


def _int_or_default(value: object, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _split_name(value: str) -> tuple[str | None, str | None]:
    parts = [part for part in str(value).split() if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _snapshot_from_metadata(metadata_json: dict[str, object]) -> dict[str, object] | None:
    snapshot = metadata_json.get("report_snapshot")
    if isinstance(snapshot, dict):
        return snapshot
    return None


def _publish_batch_id(*, run_id: str, sequence: int) -> str:
    return f"bulk-run-{run_id[:8]}-p{sequence}"


__all__ = [
    "RealPlayerBulkImportOpsError",
    "RealPlayerBulkImportOpsService",
]
