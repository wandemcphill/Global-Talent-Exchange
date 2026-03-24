from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import hashlib
import logging
from pathlib import Path
from zipfile import ZipFile

from sqlalchemy.orm import Session

from app.ingestion.constants import (
    REAL_PLAYER_IMPORT_ENTITY_TYPE,
    REAL_PLAYER_IMPORT_JOB_NAME,
    SYNC_RUN_STATUS_FAILED,
    SYNC_RUN_STATUS_PARTIAL,
    SYNC_RUN_STATUS_SUCCESS,
)
from app.ingestion.models import ProviderSyncRun
from app.ingestion.repository import IngestionRepository, MutationStats
from app.providers.import_models import RealPlayerSourceItem

from .real_player_import_repository import RealPlayerImportRepository
from .second_zip_archive_intake import SecondZipArchiveIntakeService
from .second_zip_base_eligibility import (
    SecondZipBaseEligibilityPolicy,
    SecondZipBaseEligibilityResult,
    evaluate_second_zip_players_csv_row,
)
from .transfermarkt_second_zip import (
    SECOND_ZIP_SOURCE_NAME,
    TransfermarktSecondZipError,
    TransfermarktSecondZipReferenceCatalog,
    TransfermarktSecondZipReader,
    map_player_row_to_contract,
    map_player_row_to_source_item,
)

logger = logging.getLogger(__name__)

SECOND_ZIP_STAGED_IMPORT_DEFAULT_BATCH_SIZE = 1000
SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE = "players.csv"


@dataclass(frozen=True, slots=True)
class SecondZipStagedImportSummary:
    run_id: str
    provider_name: str
    archive_path: Path
    source_file: str
    source_version: str
    batch_size: int
    batches_processed: int
    status: str
    total_rows_read: int
    eligible_rows: int
    inserted_count: int
    updated_count: int
    duplicate_skipped_count: int
    failed_count: int
    processed_count: int


@dataclass(slots=True)
class SecondZipStagedIngestService:
    session: Session
    archive_intake_service: SecondZipArchiveIntakeService = field(default_factory=SecondZipArchiveIntakeService)
    ingestion_repository: IngestionRepository = field(init=False)
    staging_repository: RealPlayerImportRepository = field(init=False)
    logger: logging.Logger = field(init=False, default=logger)

    def __post_init__(self) -> None:
        self.ingestion_repository = IngestionRepository(self.session)
        self.staging_repository = RealPlayerImportRepository(self.session)

    def import_players_csv(
        self,
        archive_path: str | Path,
        *,
        batch_size: int = SECOND_ZIP_STAGED_IMPORT_DEFAULT_BATCH_SIZE,
        provider_name: str = SECOND_ZIP_SOURCE_NAME,
        reference_date: date | None = None,
    ) -> SecondZipStagedImportSummary:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1.")

        inspection = self.archive_intake_service.validate_archive(archive_path)
        resolved_archive_path = inspection.archive_path
        source_version = self._players_csv_source_version(resolved_archive_path)
        policy = SecondZipBaseEligibilityPolicy(reference_date=reference_date or date.today())
        reference_catalog = TransfermarktSecondZipReader(resolved_archive_path).build_reference_catalog()

        run = self.ingestion_repository.start_sync_run(
            provider_name=provider_name,
            job_name=REAL_PLAYER_IMPORT_JOB_NAME,
            entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
            scope_value=SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE,
            metadata_json={
                "archive_path": str(resolved_archive_path),
                "batch_size": batch_size,
                "source_file": SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE,
                "source_version": source_version,
                "reference_date": policy.reference_date.isoformat(),
            },
        )
        run_id = run.id
        self.session.commit()

        total_rows_read = 0
        eligible_rows = 0
        batches_processed = 0
        stats = MutationStats()
        pending_items: list[RealPlayerSourceItem] = []

        try:
            with self.archive_intake_service.open_csv_rows(
                resolved_archive_path,
                SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE,
            ) as rows:
                for row_number, raw_row in enumerate(rows, start=1):
                    total_rows_read += 1
                    eligibility = evaluate_second_zip_players_csv_row(raw_row, policy=policy)
                    if not eligibility.eligible:
                        continue

                    eligible_rows += 1
                    try:
                        pending_items.append(
                            self._build_source_item(
                                raw_row=raw_row,
                                row_number=row_number,
                                archive_path=resolved_archive_path,
                                eligibility=eligibility,
                                reference_catalog=reference_catalog,
                            )
                        )
                    except (TransfermarktSecondZipError, ValueError) as exc:
                        stats.records_seen += 1
                        stats.failed_count += 1
                        self.logger.warning(
                            "ingestion.second_zip.row_failed provider=%s row=%s source_file=%s error=%s",
                            provider_name,
                            row_number,
                            SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE,
                            exc,
                        )
                        continue

                    if len(pending_items) >= batch_size:
                        stats.merge(
                            self._flush_batch(
                                provider_name=provider_name,
                                items=pending_items,
                                source_version=source_version,
                                run_id=run_id,
                                last_import_cursor=str(total_rows_read),
                            )
                        )
                        batches_processed += 1
                        pending_items.clear()
                        self._persist_run_progress(
                            run_id=run_id,
                            batch_size=batch_size,
                            source_version=source_version,
                            resolved_archive_path=resolved_archive_path,
                            total_rows_read=total_rows_read,
                            eligible_rows=eligible_rows,
                            batches_processed=batches_processed,
                            stats=stats,
                        )
                        self.session.commit()

            if pending_items:
                stats.merge(
                    self._flush_batch(
                        provider_name=provider_name,
                        items=pending_items,
                        source_version=source_version,
                        run_id=run_id,
                        last_import_cursor=str(total_rows_read),
                    )
                )
                batches_processed += 1
                pending_items.clear()
                self._persist_run_progress(
                    run_id=run_id,
                    batch_size=batch_size,
                    source_version=source_version,
                    resolved_archive_path=resolved_archive_path,
                    total_rows_read=total_rows_read,
                    eligible_rows=eligible_rows,
                    batches_processed=batches_processed,
                    stats=stats,
                )
                self.session.commit()

            status = SYNC_RUN_STATUS_SUCCESS if stats.failed_count == 0 else SYNC_RUN_STATUS_PARTIAL
            completed_run = self.ingestion_repository.finish_sync_run(
                self._require_run(run_id),
                stats=stats,
                status=status,
            )
            self._persist_run_progress(
                run_id=run_id,
                batch_size=batch_size,
                source_version=source_version,
                resolved_archive_path=resolved_archive_path,
                total_rows_read=total_rows_read,
                eligible_rows=eligible_rows,
                batches_processed=batches_processed,
                stats=stats,
                status=completed_run.status,
            )
            self.session.commit()
            return self._summary(
                completed_run=completed_run,
                resolved_archive_path=resolved_archive_path,
                source_version=source_version,
                batch_size=batch_size,
                batches_processed=batches_processed,
                total_rows_read=total_rows_read,
                eligible_rows=eligible_rows,
                stats=stats,
            )
        except Exception as exc:
            self.session.rollback()
            failure_status = SYNC_RUN_STATUS_PARTIAL if stats.records_seen > 0 else SYNC_RUN_STATUS_FAILED
            run = self.session.get(ProviderSyncRun, run_id)
            if run is not None:
                completed_run = self.ingestion_repository.finish_sync_run(
                    run,
                    stats=stats,
                    status=failure_status,
                    error_message=str(exc),
                )
                self._persist_run_progress(
                    run_id=run_id,
                    batch_size=batch_size,
                    source_version=source_version,
                    resolved_archive_path=resolved_archive_path,
                    total_rows_read=total_rows_read,
                    eligible_rows=eligible_rows,
                    batches_processed=batches_processed,
                    stats=stats,
                    status=completed_run.status,
                )
                self.session.commit()
            raise

    def _build_source_item(
        self,
        *,
        raw_row: dict[str, str | None],
        row_number: int,
        archive_path: Path,
        eligibility: SecondZipBaseEligibilityResult,
        reference_catalog: TransfermarktSecondZipReferenceCatalog,
    ) -> RealPlayerSourceItem:
        contract = map_player_row_to_contract(raw_row)
        mapped_item = map_player_row_to_source_item(
            raw_row,
            reference_catalog=reference_catalog,
        )
        mapping = dict(mapped_item.metadata_json.get("mapping") or {})
        competition_mapping = dict(mapping.get("competition") or {})
        resolved_competition_name = (
            mapped_item.current_competition_name
            if str(competition_mapping.get("status") or "").casefold() == "mapped"
            else None
        )
        return RealPlayerSourceItem(
            provider_player_id=mapped_item.provider_player_id,
            full_name=mapped_item.full_name,
            first_name=mapped_item.first_name,
            last_name=mapped_item.last_name,
            short_name=mapped_item.short_name,
            display_position=mapped_item.display_position,
            nationality_name=mapped_item.nationality_name,
            nationality_code=mapped_item.nationality_code,
            date_of_birth=mapped_item.date_of_birth,
            current_club_id=mapped_item.current_club_id,
            current_club_name=mapped_item.current_club_name,
            current_competition_id=mapped_item.current_competition_id,
            current_competition_name=resolved_competition_name,
            current_season_id=str(contract.last_season) if contract.last_season is not None else None,
            provider_last_updated_at=mapped_item.provider_last_updated_at,
            metadata_json={
                **dict(mapped_item.metadata_json),
                "archive_name": archive_path.name,
                "eligibility": eligibility.to_dict(),
                "source_file": SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE,
                "source_name": SECOND_ZIP_SOURCE_NAME,
                "source_player_id": contract.external_player_id,
                "source_row_number": row_number,
            },
            raw_payload=dict(contract.raw_payload),
        )

    def _flush_batch(
        self,
        *,
        provider_name: str,
        items: list[RealPlayerSourceItem],
        source_version: str,
        run_id: str,
        last_import_cursor: str,
    ) -> MutationStats:
        try:
            return self._stage_items(
                provider_name=provider_name,
                items=items,
                source_version=source_version,
                run_id=run_id,
                last_import_cursor=last_import_cursor,
            )
        except Exception:
            self.session.rollback()
            self.logger.exception(
                "ingestion.second_zip.batch_failed provider=%s batch_size=%s run_id=%s",
                provider_name,
                len(items),
                run_id,
            )
            aggregate = MutationStats()
            for item in items:
                try:
                    aggregate.merge(
                        self._stage_items(
                            provider_name=provider_name,
                            items=[item],
                            source_version=source_version,
                            run_id=run_id,
                            last_import_cursor=last_import_cursor,
                        )
                    )
                except Exception:
                    self.session.rollback()
                    aggregate.records_seen += 1
                    aggregate.failed_count += 1
                    self.logger.exception(
                        "ingestion.second_zip.item_failed provider=%s source_player_id=%s run_id=%s",
                        provider_name,
                        item.provider_player_id,
                        run_id,
                    )
            return aggregate

    def _stage_items(
        self,
        *,
        provider_name: str,
        items: list[RealPlayerSourceItem],
        source_version: str,
        run_id: str,
        last_import_cursor: str,
    ) -> MutationStats:
        stats = self.staging_repository.upsert_staging_records(
            provider_name=provider_name,
            items=items,
            source_version=source_version,
            last_import_run_id=run_id,
            last_import_cursor=last_import_cursor,
        )
        self.ingestion_repository.store_raw_payloads(
            provider_name=provider_name,
            entity_type=REAL_PLAYER_IMPORT_ENTITY_TYPE,
            payloads=[item.raw_payload for item in items],
            sync_run_id=run_id,
            external_id_key="player_id",
        )
        self.session.commit()
        return stats

    def _persist_run_progress(
        self,
        *,
        run_id: str,
        batch_size: int,
        source_version: str,
        resolved_archive_path: Path,
        total_rows_read: int,
        eligible_rows: int,
        batches_processed: int,
        stats: MutationStats,
        status: str | None = None,
    ) -> None:
        run = self._require_run(run_id)
        run.metadata_json = {
            **(run.metadata_json or {}),
            "archive_path": str(resolved_archive_path),
            "batch_size": batch_size,
            "batches_processed": batches_processed,
            "duplicate_skipped_count": stats.skipped_count,
            "eligible_rows": eligible_rows,
            "failed_count": stats.failed_count,
            "inserted_count": stats.inserted_count,
            "processed_count": stats.records_seen,
            "source_file": SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE,
            "source_version": source_version,
            "status": status or run.status,
            "total_rows_read": total_rows_read,
            "updated_count": stats.updated_count,
        }
        self.session.flush()

    def _players_csv_source_version(self, archive_path: Path) -> str:
        digest = hashlib.sha256()
        with ZipFile(archive_path) as archive:
            with archive.open(SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE, mode="r") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        return digest.hexdigest()

    def _require_run(self, run_id: str) -> ProviderSyncRun:
        run = self.session.get(ProviderSyncRun, run_id)
        if run is None:
            raise RuntimeError(f"Sync run '{run_id}' was not found.")
        return run

    def _summary(
        self,
        *,
        completed_run: ProviderSyncRun,
        resolved_archive_path: Path,
        source_version: str,
        batch_size: int,
        batches_processed: int,
        total_rows_read: int,
        eligible_rows: int,
        stats: MutationStats,
    ) -> SecondZipStagedImportSummary:
        return SecondZipStagedImportSummary(
            run_id=completed_run.id,
            provider_name=completed_run.provider_name,
            archive_path=resolved_archive_path,
            source_file=SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE,
            source_version=source_version,
            batch_size=batch_size,
            batches_processed=batches_processed,
            status=completed_run.status,
            total_rows_read=total_rows_read,
            eligible_rows=eligible_rows,
            inserted_count=stats.inserted_count,
            updated_count=stats.updated_count,
            duplicate_skipped_count=stats.skipped_count,
            failed_count=stats.failed_count,
            processed_count=stats.records_seen,
        )


__all__ = [
    "SECOND_ZIP_STAGED_IMPORT_DEFAULT_BATCH_SIZE",
    "SECOND_ZIP_STAGED_IMPORT_SOURCE_FILE",
    "SecondZipStagedImportSummary",
    "SecondZipStagedIngestService",
]
