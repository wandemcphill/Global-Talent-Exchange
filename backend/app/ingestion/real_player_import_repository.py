from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
import hashlib
import json
from typing import Any, Sequence

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.ingestion.constants import REAL_PLAYER_IMPORT_ENTITY_TYPE
from app.ingestion.models import ProviderSyncCursor, ProviderSyncRun
from app.ingestion.real_player_identity_normalizer import fold_identity_name
from app.ingestion.repository import MutationStats
from app.models.base import utcnow
from app.providers.import_models import RealPlayerSourceItem

from .real_player_import_models import (
    RealPlayerImportProcessingState,
    RealPlayerImportRun,
    RealPlayerImportRunStatus,
    RealPlayerImportStagingRecord,
)


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


@dataclass(slots=True)
class StagingSimulationState:
    payload_hashes_by_provider_id: dict[str, str | None] = field(default_factory=dict)
    loaded_provider_ids: set[str] = field(default_factory=set)


class RealPlayerImportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _load_existing_staging_records(
        self,
        *,
        provider_name: str,
        provider_player_ids: Sequence[str],
    ) -> dict[str, RealPlayerImportStagingRecord]:
        if not provider_player_ids:
            return {}
        existing_records = self.session.scalars(
            select(RealPlayerImportStagingRecord).where(
                RealPlayerImportStagingRecord.provider_name == provider_name,
                RealPlayerImportStagingRecord.provider_player_id.in_(provider_player_ids),
            )
        )
        return {
            record.provider_player_id: record
            for record in existing_records
        }

    def get_resumable_import_run(
        self,
        *,
        provider_name: str,
        source_type: str,
        source_reference: str | None,
    ) -> RealPlayerImportRun | None:
        return self.session.scalar(
            select(RealPlayerImportRun)
            .where(
                RealPlayerImportRun.provider_name == provider_name,
                RealPlayerImportRun.source_type == source_type,
                RealPlayerImportRun.source_reference == source_reference,
                RealPlayerImportRun.status.in_(
                    (
                        RealPlayerImportRunStatus.PARTIAL.value,
                        RealPlayerImportRunStatus.FAILED.value,
                        RealPlayerImportRunStatus.RUNNING.value,
                    )
                ),
            )
            .order_by(RealPlayerImportRun.started_at.desc(), RealPlayerImportRun.created_at.desc())
            .limit(1)
        )

    def create_import_run(
        self,
        *,
        provider_name: str,
        source_type: str,
        source_reference: str | None,
        configured_batch_size: int,
        provider_sync_run_id: str | None = None,
        resume_cursor: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> RealPlayerImportRun:
        run = RealPlayerImportRun(
            provider_name=provider_name,
            source_type=source_type,
            source_reference=source_reference,
            provider_sync_run_id=provider_sync_run_id,
            configured_batch_size=configured_batch_size,
            status=RealPlayerImportRunStatus.RUNNING.value,
            resume_cursor=resume_cursor,
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(run)
        self.session.flush()
        return run

    def resume_import_run(
        self,
        run: RealPlayerImportRun,
        *,
        provider_sync_run_id: str | None = None,
        resume_cursor: str | None = None,
        configured_batch_size: int | None = None,
        metadata_updates: dict[str, object] | None = None,
    ) -> RealPlayerImportRun:
        metadata = dict(run.metadata_json or {})
        metadata.update(metadata_updates or {})
        run.provider_sync_run_id = provider_sync_run_id
        run.resume_cursor = resume_cursor
        run.configured_batch_size = configured_batch_size or run.configured_batch_size
        run.status = RealPlayerImportRunStatus.RUNNING.value
        run.error_message = None
        run.completed_at = None
        run.metadata_json = metadata
        self.session.flush()
        return run

    def upsert_staging_records(
        self,
        *,
        provider_name: str,
        items: Sequence[RealPlayerSourceItem],
        source_version: str | None,
        last_import_run_id: str,
        last_import_cursor: str | None,
        import_run_id: str | None = None,
        import_batch_key: str | None = None,
        default_processing_state: str | None = None,
    ) -> MutationStats:
        stats = MutationStats(records_seen=len(items))
        if not items:
            return stats

        player_ids = [item.provider_player_id for item in items]
        existing_by_provider_id = self._load_existing_staging_records(
            provider_name=provider_name,
            provider_player_ids=player_ids,
        )
        observed_at = utcnow()
        processing_state = default_processing_state or RealPlayerImportProcessingState.PENDING.value

        for item in items:
            payload_hash = _payload_hash(item.raw_payload)
            record = existing_by_provider_id.get(item.provider_player_id)
            if record is None:
                record = RealPlayerImportStagingRecord(
                    provider_name=provider_name,
                    provider_player_id=item.provider_player_id,
                    import_run_id=import_run_id,
                    import_batch_key=import_batch_key,
                    provider_club_id=item.current_club_id,
                    provider_club_name=item.current_club_name,
                    provider_competition_id=item.current_competition_id,
                    provider_competition_name=item.current_competition_name,
                    provider_season_id=item.current_season_id,
                    full_name=item.full_name,
                    normalized_name=item.normalized_name or fold_identity_name(item.full_name),
                    first_name=item.first_name,
                    last_name=item.last_name,
                    short_name=item.short_name,
                    display_position=item.display_position,
                    nationality_name=item.nationality_name,
                    nationality_code=item.nationality_code,
                    date_of_birth=item.date_of_birth,
                    age=item.age or _age_from_date_of_birth(item.date_of_birth, observed_at.date()),
                    rough_market_value=item.rough_market_value,
                    rough_market_value_currency=item.rough_market_value_currency,
                    provider_last_updated_at=item.provider_last_updated_at,
                    source_version=source_version,
                    last_import_cursor=last_import_cursor,
                    processing_state=processing_state,
                    source_payload_hash=payload_hash,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                    last_import_run_id=last_import_run_id,
                    latest_payload_json=item.raw_payload,
                    metadata_json=dict(item.metadata_json),
                )
                self.session.add(record)
                existing_by_provider_id[item.provider_player_id] = record
                stats.inserted_count += 1
                continue

            if record.source_payload_hash == payload_hash:
                record.import_run_id = import_run_id or record.import_run_id
                record.import_batch_key = import_batch_key or record.import_batch_key
                record.last_import_run_id = last_import_run_id
                record.last_import_cursor = last_import_cursor
                record.last_seen_at = observed_at
                stats.skipped_count += 1
                continue

            preserved_processing_state = record.processing_state
            record.provider_club_id = item.current_club_id
            record.provider_club_name = item.current_club_name
            record.provider_competition_id = item.current_competition_id
            record.provider_competition_name = item.current_competition_name
            record.provider_season_id = item.current_season_id
            record.full_name = item.full_name
            record.normalized_name = item.normalized_name or fold_identity_name(item.full_name)
            record.first_name = item.first_name
            record.last_name = item.last_name
            record.short_name = item.short_name
            record.display_position = item.display_position
            record.nationality_name = item.nationality_name
            record.nationality_code = item.nationality_code
            record.date_of_birth = item.date_of_birth
            record.age = item.age or _age_from_date_of_birth(item.date_of_birth, observed_at.date())
            record.rough_market_value = item.rough_market_value
            record.rough_market_value_currency = item.rough_market_value_currency
            record.provider_last_updated_at = item.provider_last_updated_at
            record.source_version = source_version
            record.last_import_cursor = last_import_cursor
            record.source_payload_hash = payload_hash
            record.last_seen_at = observed_at
            record.import_run_id = import_run_id or record.import_run_id
            record.import_batch_key = import_batch_key or record.import_batch_key
            record.last_import_run_id = last_import_run_id
            record.latest_payload_json = item.raw_payload
            record.metadata_json = dict(item.metadata_json)
            record.processing_state = preserved_processing_state or processing_state
            if record.processing_state != RealPlayerImportProcessingState.ERROR.value:
                record.error_message = None
            if record.processing_state != RealPlayerImportProcessingState.REJECTED.value:
                record.rejection_reason = None
            stats.updated_count += 1

        self.session.flush()
        return stats

    def simulate_upsert_staging_records(
        self,
        *,
        provider_name: str,
        items: Sequence[RealPlayerSourceItem],
        simulation_state: StagingSimulationState | None = None,
    ) -> MutationStats:
        stats = MutationStats(records_seen=len(items))
        if not items:
            return stats

        state = simulation_state or StagingSimulationState()
        player_ids = {item.provider_player_id for item in items}
        missing_player_ids = player_ids - state.loaded_provider_ids
        if missing_player_ids:
            existing_by_provider_id = self._load_existing_staging_records(
                provider_name=provider_name,
                provider_player_ids=list(missing_player_ids),
            )
            for provider_player_id in missing_player_ids:
                record = existing_by_provider_id.get(provider_player_id)
                state.payload_hashes_by_provider_id[provider_player_id] = (
                    record.source_payload_hash if record is not None else None
                )
            state.loaded_provider_ids.update(missing_player_ids)

        for item in items:
            payload_hash = _payload_hash(item.raw_payload)
            current_hash = state.payload_hashes_by_provider_id.get(item.provider_player_id)
            if current_hash is None:
                state.payload_hashes_by_provider_id[item.provider_player_id] = payload_hash
                stats.inserted_count += 1
                continue
            if current_hash == payload_hash:
                stats.skipped_count += 1
                continue
            state.payload_hashes_by_provider_id[item.provider_player_id] = payload_hash
            stats.updated_count += 1

        return stats

    def mark_import_run_progress(
        self,
        run: RealPlayerImportRun,
        *,
        stats: MutationStats,
        batch_marker: str | None,
        resume_cursor: str | None,
        metadata_updates: dict[str, object] | None = None,
    ) -> RealPlayerImportRun:
        metadata = dict(run.metadata_json or {})
        metadata.update(metadata_updates or {})
        run.total_rows_discovered += stats.records_seen
        run.processed_rows += stats.records_seen
        run.inserted_rows += stats.inserted_count
        run.updated_rows += stats.updated_count
        run.duplicate_skipped_rows += stats.skipped_count
        run.failed_rows += stats.failed_count
        run.resume_cursor = resume_cursor
        run.last_successful_batch_marker = batch_marker
        run.metadata_json = metadata
        self.session.flush()
        return run

    def get_staging_record(
        self,
        *,
        provider_name: str,
        provider_player_id: str,
    ) -> RealPlayerImportStagingRecord | None:
        return self.session.scalar(
            select(RealPlayerImportStagingRecord).where(
                RealPlayerImportStagingRecord.provider_name == provider_name,
                RealPlayerImportStagingRecord.provider_player_id == provider_player_id,
            )
        )

    def set_processing_state(
        self,
        *,
        provider_name: str,
        provider_player_id: str,
        processing_state: str,
        error_message: str | None = None,
        rejection_reason: str | None = None,
        import_run_id: str | None = None,
    ) -> RealPlayerImportStagingRecord:
        record = self.get_staging_record(
            provider_name=provider_name,
            provider_player_id=provider_player_id,
        )
        if record is None:
            raise LookupError(
                f"Staging record '{provider_name}:{provider_player_id}' was not found."
            )

        record.processing_state = processing_state
        record.import_state = "processed"
        record.last_processed_at = utcnow()
        record.import_run_id = import_run_id or record.import_run_id
        record.error_message = error_message if processing_state == RealPlayerImportProcessingState.ERROR.value else None
        record.rejection_reason = (
            rejection_reason if processing_state == RealPlayerImportProcessingState.REJECTED.value else None
        )
        self.session.flush()

        if record.import_run_id:
            run = self.session.get(RealPlayerImportRun, record.import_run_id)
            if run is not None:
                self.refresh_run_state_counts(run)
        return record

    def refresh_run_state_counts(self, run: RealPlayerImportRun) -> RealPlayerImportRun:
        counts = self.session.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                RealPlayerImportStagingRecord.processing_state.in_(
                                    (
                                        RealPlayerImportProcessingState.PENDING.value,
                                        RealPlayerImportProcessingState.NORMALIZED.value,
                                        RealPlayerImportProcessingState.MAPPED_PARTIAL.value,
                                    )
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                RealPlayerImportStagingRecord.processing_state
                                == RealPlayerImportProcessingState.MAPPED_READY.value,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                RealPlayerImportStagingRecord.processing_state
                                == RealPlayerImportProcessingState.PUBLISHED.value,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                RealPlayerImportStagingRecord.processing_state.in_(
                                    (
                                        RealPlayerImportProcessingState.REJECTED.value,
                                        RealPlayerImportProcessingState.ERROR.value,
                                    )
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            ).where(RealPlayerImportStagingRecord.import_run_id == run.id)
        ).one()

        run.unresolved_rows = int(counts[0] or 0)
        run.publish_ready_rows = int(counts[1] or 0)
        run.published_rows = int(counts[2] or 0)
        staged_failures = int(counts[3] or 0)
        run.failed_rows = max(run.failed_rows, staged_failures)
        self.session.flush()
        return run

    def finish_import_run(
        self,
        run: RealPlayerImportRun,
        *,
        status: str,
        error_message: str | None = None,
        resume_cursor: str | None = None,
        metadata_updates: dict[str, object] | None = None,
    ) -> RealPlayerImportRun:
        metadata = dict(run.metadata_json or {})
        metadata.update(metadata_updates or {})
        run.status = status
        run.error_message = error_message
        run.resume_cursor = resume_cursor
        run.metadata_json = metadata
        if status in {
            RealPlayerImportRunStatus.COMPLETED.value,
            RealPlayerImportRunStatus.COMPLETED_WITH_ERRORS.value,
            RealPlayerImportRunStatus.FAILED.value,
            RealPlayerImportRunStatus.CANCELLED.value,
        }:
            run.completed_at = utcnow()
        self.session.flush()
        return run

    def list_recent_runs(self, *, provider_name: str, limit: int = 10) -> list[ProviderSyncRun]:
        statement = (
            select(ProviderSyncRun)
            .where(
                ProviderSyncRun.provider_name == provider_name,
                ProviderSyncRun.entity_type == REAL_PLAYER_IMPORT_ENTITY_TYPE,
            )
            .order_by(ProviderSyncRun.started_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def get_latest_run(self, *, provider_name: str) -> ProviderSyncRun | None:
        statement = (
            select(ProviderSyncRun)
            .where(
                ProviderSyncRun.provider_name == provider_name,
                ProviderSyncRun.entity_type == REAL_PLAYER_IMPORT_ENTITY_TYPE,
            )
            .order_by(ProviderSyncRun.started_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_cursor(self, *, provider_name: str, cursor_key: str) -> ProviderSyncCursor | None:
        return self.session.scalar(
            select(ProviderSyncCursor).where(
                ProviderSyncCursor.provider_name == provider_name,
                ProviderSyncCursor.entity_type == REAL_PLAYER_IMPORT_ENTITY_TYPE,
                ProviderSyncCursor.cursor_key == cursor_key,
            )
        )

    def count_staged_records(self, *, provider_name: str) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == provider_name
                )
            )
            or 0
        )

    def latest_seen_at(self, *, provider_name: str) -> datetime | None:
        return self.session.scalar(
            select(func.max(RealPlayerImportStagingRecord.last_seen_at)).where(
                RealPlayerImportStagingRecord.provider_name == provider_name
            )
        )


def _age_from_date_of_birth(date_of_birth: date | None, as_of: date) -> int | None:
    if date_of_birth is None:
        return None
    age = as_of.year - date_of_birth.year
    if (as_of.month, as_of.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return max(age, 0)
