from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.core.config import Settings, get_settings
from app.ingestion.real_player_canonical_mapping_service import RealPlayerCanonicalMappingService
from app.ingestion.real_player_identity_matcher import RealPlayerIdentityMatcher
from app.ingestion.real_player_ingestion_service import RealPlayerIngestionService
from app.ingestion.real_player_normalization_service import RealPlayerNormalizationService
from app.ingestion.second_zip_archive_intake import SecondZipArchiveIntakeService
from app.ingestion.second_zip_base_eligibility import (
    SecondZipBaseEligibilityPolicy,
    evaluate_second_zip_players_csv_row,
)
from app.ingestion.second_zip_publish_readiness import SecondZipPublishTier
from app.ingestion.transfermarkt_second_zip import (
    SECOND_ZIP_SOURCE_NAME,
    TransfermarktSecondZipReferenceCatalog,
    map_player_row_to_contract,
    map_player_row_to_source_item,
    normalize_column_name,
    normalize_optional_text,
)
from app.models.base import utcnow
from app.models.real_player_import_batch import (
    RealPlayerImportBatch,
    RealPlayerImportBatchStatus,
    RealPlayerImportRow,
    RealPlayerImportRowStatus,
)
from app.models.real_player_profile import RealPlayerProfile
from app.schemas.real_player_ingestion import RealPlayerIngestionItemResult, RealPlayerIngestionRequest, RealPlayerSeedInput


SECOND_ZIP_SOURCE_TYPE = "2nd_zip_archive"
SECOND_ZIP_METADATA_KEY = "second_zip"
SECOND_ZIP_BATCH_VERSION = "2nd_zip_ops_v1"
SECOND_ZIP_DRY_RUN_MODE = "dry-run"


class SecondZipRealPlayerOpsError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class SecondZipReportCounts:
    total_rows_read: int = 0
    eligible_rows: int = 0
    inserted: int = 0
    updated: int = 0
    duplicate_skipped: int = 0
    mapped_ready: int = 0
    mapped_partial: int = 0
    unresolved: int = 0
    fallback_valued: int = 0
    free_agent_fallback: int = 0
    publish_ready: int = 0
    published: int = 0
    failed: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "total_rows_read": self.total_rows_read,
            "eligible_rows": self.eligible_rows,
            "inserted": self.inserted,
            "updated": self.updated,
            "duplicate_skipped": self.duplicate_skipped,
            "mapped_ready": self.mapped_ready,
            "mapped_partial": self.mapped_partial,
            "unresolved": self.unresolved,
            "fallback_valued": self.fallback_valued,
            "free_agent_fallback": self.free_agent_fallback,
            "publish_ready": self.publish_ready,
            "published": self.published,
            "failed": self.failed,
        }


@dataclass(frozen=True, slots=True)
class SecondZipRunReport:
    run_id: str
    batch_key: str
    status: str
    archive_path: str
    archive_sha256: str
    batch_size: int
    limit: int | None
    read_exhausted: bool
    scope_complete: bool
    next_resume_row_number: int | None
    counts: SecondZipReportCounts
    error_message: str | None = None
    selected_row_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "batch_key": self.batch_key,
            "status": self.status,
            "archive_path": self.archive_path,
            "archive_sha256": self.archive_sha256,
            "batch_size": self.batch_size,
            "limit": self.limit,
            "read_exhausted": self.read_exhausted,
            "scope_complete": self.scope_complete,
            "next_resume_row_number": self.next_resume_row_number,
            "counts": self.counts.to_dict(),
            "error_message": self.error_message,
            "selected_row_count": self.selected_row_count,
        }


@dataclass(frozen=True, slots=True)
class SecondZipCandidate:
    source_row_number: int
    source_row: dict[str, Any]
    seed_input: RealPlayerSeedInput
    eligibility_summary: dict[str, object]


@dataclass(slots=True)
class SecondZipEvaluationResult:
    source_player_key: str
    canonical_name: str
    match_action: str | None
    gtex_player_id: str | None
    row_status: str
    review_status: str
    review_reason: str | None
    normalized_payload_json: dict[str, object]
    validation_errors: list[str] = field(default_factory=list)
    candidate_players: list[dict[str, object]] = field(default_factory=list)
    audit_findings: list[dict[str, object]] = field(default_factory=list)
    mapping_status: str = "partial"
    mapping_summary: dict[str, dict[str, object]] = field(default_factory=dict)
    publish_ready: bool = False
    free_agent_fallback: bool = False
    fallback_valued: bool = False
    pricing_preview_ready: bool = False
    state: str = "failed"


@dataclass(slots=True)
class SecondZipRealPlayerOpsService:
    session_factory: sessionmaker[Session]
    settings: Settings = field(default_factory=get_settings)
    archive_intake: SecondZipArchiveIntakeService = field(default_factory=SecondZipArchiveIntakeService)
    normalization_service: RealPlayerNormalizationService = field(default_factory=RealPlayerNormalizationService)
    identity_matcher: RealPlayerIdentityMatcher = field(default_factory=RealPlayerIdentityMatcher)
    reference_date: date = field(default_factory=lambda: datetime.now(UTC).date())

    def import_archive(
        self,
        *,
        archive_path: str | Path,
        batch_size: int = 1000,
        limit: int | None = None,
    ) -> SecondZipRunReport:
        if batch_size <= 0:
            raise SecondZipRealPlayerOpsError("Batch size must be greater than zero.")
        if limit is not None and limit <= 0:
            raise SecondZipRealPlayerOpsError("Limit must be greater than zero when provided.")

        resolved_archive = Path(archive_path).expanduser().resolve()
        self.archive_intake.validate_archive(resolved_archive)
        archive_sha256 = self._archive_sha256(resolved_archive)
        batch_key = self._batch_key(archive_sha256=archive_sha256, limit=limit)
        provider_job_key = self._provider_job_key(archive_sha256=archive_sha256, limit=limit)

        with self.session_factory() as session:
            batch = session.scalar(
                select(RealPlayerImportBatch)
                .options(selectinload(RealPlayerImportBatch.rows))
                .where(RealPlayerImportBatch.batch_key == batch_key)
            )
            if batch is None:
                batch = self._create_batch(
                    archive_path=resolved_archive,
                    archive_sha256=archive_sha256,
                    batch_key=batch_key,
                    batch_size=batch_size,
                    limit=limit,
                    provider_job_key=provider_job_key,
                )
                session.add(batch)
                session.flush()
            else:
                metadata = self._batch_metadata(batch)
                if self._metadata_archive_sha(metadata) != archive_sha256:
                    raise SecondZipRealPlayerOpsError(
                        f"Run '{batch.id}' already exists for a different archive payload.",
                        status_code=409,
                    )
                if bool(metadata.get("scope_complete")):
                    self._refresh_batch_summary(batch)
                    session.commit()
                    return self._report_from_batch(batch)
                metadata["batch_size"] = batch_size
                batch.metadata_json = metadata
            batch.status = RealPlayerImportBatchStatus.RUNNING.value
            batch.mode = SECOND_ZIP_DRY_RUN_MODE
            batch.error_message = None
            batch.started_at = batch.started_at or utcnow()
            batch.requested_at = utcnow()
            session.commit()

        error_message: str | None = None
        with self.archive_intake.extract_archive(resolved_archive) as extracted:
            lookups = self._load_lookups(extracted.workdir)
            source_rows = self._iter_player_rows(
                extracted.get_path("players.csv"),
                start_row_number=self._next_resume_row_number_from_metadata(self._batch_metadata(batch)),
            )
            try:
                while True:
                    remaining = self._remaining_row_budget(self._batch_metadata(batch))
                    if remaining is not None and remaining <= 0:
                        break
                    current_batch_size = batch_size if remaining is None else min(batch_size, remaining)
                    current_rows = self._take_source_rows(source_rows, current_batch_size)
                    if not current_rows:
                        break
                    batch = self._process_source_rows(
                        batch_id=batch.id,
                        source_rows=current_rows,
                        lookups=lookups,
                    )
                    if len(current_rows) < current_batch_size:
                        break
            except Exception as exc:  # pragma: no cover - exercised via monkeypatched resume test
                error_message = str(exc)

        with self.session_factory() as session:
            batch = self._load_batch(session, batch.id)
            metadata = self._batch_metadata(batch)
            if error_message is None:
                metadata["scope_complete"] = True
                metadata["read_exhausted"] = not bool(source_rows)
                metadata["next_resume_row_number"] = None
                batch.error_message = None
            else:
                metadata["scope_complete"] = False
                metadata["read_exhausted"] = False
                metadata["next_resume_row_number"] = self._next_resume_row_number_from_metadata(metadata)
                batch.error_message = error_message
            batch.metadata_json = metadata
            batch.status = RealPlayerImportBatchStatus.COMPLETED.value if error_message is None else RealPlayerImportBatchStatus.FAILED.value
            self._refresh_batch_summary(batch)
            if error_message is not None:
                batch.status = RealPlayerImportBatchStatus.FAILED.value
            session.commit()
            return self._report_from_batch(batch)

    def resume_run(self, *, run_id: str) -> SecondZipRunReport:
        with self.session_factory() as session:
            batch = self._load_batch(session, run_id)
            metadata = self._batch_metadata(batch)
            archive_path = self._metadata_archive_path(metadata)
            if archive_path is None:
                raise SecondZipRealPlayerOpsError(
                    f"Run '{run_id}' does not record a 2nd.zip archive path.",
                    status_code=409,
                )
            batch_size = int(metadata.get("batch_size") or 1000)
            limit = self._metadata_limit(metadata)
        return self.import_archive(
            archive_path=archive_path,
            batch_size=batch_size,
            limit=limit,
        )

    def repair_run(
        self,
        *,
        run_id: str | None = None,
        state: str | None = None,
    ) -> list[SecondZipRunReport]:
        if not run_id and not state:
            raise SecondZipRealPlayerOpsError("Repair requires either --run-id or --state.")

        with self.session_factory() as session:
            if run_id:
                batches = [self._load_batch(session, run_id)]
            else:
                batches = list(
                    session.scalars(
                        select(RealPlayerImportBatch)
                        .options(selectinload(RealPlayerImportBatch.rows))
                        .where(
                            RealPlayerImportBatch.provider_name == SECOND_ZIP_SOURCE_NAME,
                            RealPlayerImportBatch.source_type == SECOND_ZIP_SOURCE_TYPE,
                        )
                    )
                )

        reports: list[SecondZipRunReport] = []
        for batch in batches:
            target_rows = [
                row
                for row in sorted(batch.rows, key=lambda item: item.row_number)
                if not self._row_is_published(row)
                and self._row_state(row) in {"unresolved", "mapped_partial", "failed"}
                and (state is None or self._row_state(row) == state)
            ]
            if run_id and not target_rows:
                with self.session_factory() as session:
                    current = self._load_batch(session, batch.id)
                    self._refresh_batch_summary(current)
                    session.commit()
                    reports.append(self._report_from_batch(current, selected_row_count=0))
                continue
            if not run_id and not target_rows:
                continue
            reports.append(self._repair_rows(batch_id=batch.id, rows=target_rows))
        return reports

    def publish_run(
        self,
        *,
        run_id: str,
        limit: int | None = None,
        tier: str | None = None,
    ) -> SecondZipRunReport:
        if limit is not None and limit <= 0:
            raise SecondZipRealPlayerOpsError("Publish limit must be greater than zero when provided.")

        with self.session_factory() as session:
            batch = self._load_batch(session, run_id)
            rows = [
                row
                for row in sorted(batch.rows, key=lambda item: item.row_number)
                if self._row_publish_ready(row)
            ]
            if tier:
                try:
                    requested_tier = SecondZipPublishTier(tier)
                except ValueError as exc:
                    raise SecondZipRealPlayerOpsError(
                        f"Unsupported publish tier '{tier}'.",
                    ) from exc
                rows = [
                    row
                    for row in rows
                    if self._row_publish_tier(row) == requested_tier
                ]
            if limit is not None:
                rows = rows[:limit]

        selected_row_count = len(rows)
        for row in rows:
            self._publish_row(batch_id=run_id, batch_key=batch.batch_key, row=row)

        with self.session_factory() as session:
            batch = self._load_batch(session, run_id)
            self._refresh_batch_summary(batch)
            session.commit()
            return self._report_from_batch(batch, selected_row_count=selected_row_count)

    def report_run(self, *, run_id: str) -> SecondZipRunReport:
        with self.session_factory() as session:
            batch = self._load_batch(session, run_id)
            self._refresh_batch_summary(batch)
            session.commit()
            return self._report_from_batch(batch)

    def _repair_rows(self, *, batch_id: str, rows: list[RealPlayerImportRow]) -> SecondZipRunReport:
        candidates = [self._candidate_from_row(row) for row in rows]
        evaluation_by_key = self._evaluate_candidates(candidates)
        with self.session_factory() as session:
            batch = self._load_batch(session, batch_id)
            for candidate in candidates:
                current = session.scalar(
                    select(RealPlayerImportRow).where(
                        RealPlayerImportRow.batch_id == batch.id,
                        RealPlayerImportRow.source_name == candidate.seed_input.source_name,
                        RealPlayerImportRow.source_player_key == candidate.seed_input.source_player_key,
                    )
                )
                if current is None:
                    continue
                evaluation = evaluation_by_key.get((candidate.seed_input.source_name, candidate.seed_input.source_player_key))
                if evaluation is None:
                    continue
                self._apply_evaluation_to_row(
                    row=current,
                    source_row_number=candidate.source_row_number,
                    source_row=candidate.source_row,
                    eligibility_summary=candidate.eligibility_summary,
                    seed_input=candidate.seed_input,
                    evaluation=evaluation,
                )
            self._refresh_batch_summary(batch)
            session.commit()
            return self._report_from_batch(batch, selected_row_count=len(rows))

    def _process_source_rows(
        self,
        *,
        batch_id: str,
        source_rows: list[tuple[int, dict[str, Any]]],
        lookups: dict[str, dict[str, dict[str, Any]]],
    ) -> RealPlayerImportBatch:
        policy = SecondZipBaseEligibilityPolicy(reference_date=self.reference_date)
        candidates: list[SecondZipCandidate] = []
        blocked_rows: list[tuple[int, dict[str, Any], dict[str, object], list[str], str, str]] = []
        duplicate_count = 0
        total_rows_increment = 0
        eligible_rows_increment = 0
        last_read_row_number = 0

        with self.session_factory() as session:
            batch = self._load_batch(session, batch_id)
            seen_source_keys = {
                row.source_player_key.casefold()
                for row in batch.rows
            }

            for source_row_number, source_row in source_rows:
                total_rows_increment += 1
                last_read_row_number = source_row_number
                eligibility = evaluate_second_zip_players_csv_row(source_row, policy=policy)
                eligibility_summary = eligibility.to_dict()
                source_player_key = str(source_row.get("player_id") or f"row-{source_row_number}").strip()
                if eligibility.eligible:
                    eligible_rows_increment += 1
                if source_player_key.casefold() in seen_source_keys:
                    duplicate_count += 1
                    continue
                seen_source_keys.add(source_player_key.casefold())

                if not eligibility.eligible:
                    blocked_rows.append(
                        (
                            source_row_number,
                            source_row,
                            eligibility_summary,
                            list(eligibility.exclusion_reason_codes),
                            source_player_key,
                            "base_ineligible",
                        )
                    )
                    continue

                try:
                    seed_input = self._build_seed_input(source_row=source_row, lookups=lookups)
                except Exception as exc:
                    blocked_rows.append(
                        (
                            source_row_number,
                            source_row,
                            eligibility_summary,
                            [str(exc)],
                            source_player_key,
                            "failed",
                        )
                    )
                    continue
                candidates.append(
                    SecondZipCandidate(
                        source_row_number=source_row_number,
                        source_row=source_row,
                        seed_input=seed_input,
                        eligibility_summary=eligibility_summary,
                    )
                )

        evaluation_by_key = self._evaluate_candidates(candidates)
        with self.session_factory() as session:
            batch = self._load_batch(session, batch_id)
            metadata = self._batch_metadata(batch)
            metadata["total_rows_read"] = int(metadata.get("total_rows_read") or 0) + total_rows_increment
            metadata["eligible_rows"] = int(metadata.get("eligible_rows") or 0) + eligible_rows_increment
            metadata["duplicate_skipped_count"] = int(metadata.get("duplicate_skipped_count") or 0) + duplicate_count
            metadata["last_read_row_number"] = last_read_row_number
            batch.metadata_json = metadata
            for source_row_number, source_row, eligibility_summary, errors, source_player_key, state in blocked_rows:
                row = self._upsert_row(
                    session,
                    batch=batch,
                    source_player_key=source_player_key,
                    canonical_name=str(source_row.get("name") or source_player_key),
                    row_number=source_row_number,
                )
                row_metadata = self._base_row_metadata(
                    source_row_number=source_row_number,
                    source_row=source_row,
                    eligibility_summary=eligibility_summary,
                )
                row_metadata["state"] = state
                row_metadata["publish_ready"] = False
                row_metadata["published"] = False
                row.raw_payload_json = {}
                row.normalized_payload_json = {}
                row.status = (
                    RealPlayerImportRowStatus.SKIPPED.value
                    if state == "base_ineligible"
                    else RealPlayerImportRowStatus.FAILED.value
                )
                row.import_action = state
                row.review_status = "resolved" if state == "base_ineligible" else "needs_review"
                row.review_reason = None if state == "base_ineligible" else "seed_payload_error"
                row.validation_errors_json = list(errors)
                row.candidate_players_json = []
                row.audit_findings_json = [
                    {
                        "finding_type": state,
                        "details": {"reasons": list(errors)},
                    }
                ]
                row.import_metadata_json = self._merged_row_metadata(row, row_metadata)
                row.processed_at = utcnow()

            for candidate in candidates:
                evaluation = evaluation_by_key[(candidate.seed_input.source_name, candidate.seed_input.source_player_key)]
                row = self._upsert_row(
                    session,
                    batch=batch,
                    source_player_key=candidate.seed_input.source_player_key,
                    canonical_name=candidate.seed_input.canonical_name,
                    row_number=candidate.source_row_number,
                )
                self._apply_evaluation_to_row(
                    row=row,
                    source_row_number=candidate.source_row_number,
                    source_row=candidate.source_row,
                    eligibility_summary=candidate.eligibility_summary,
                    seed_input=candidate.seed_input,
                    evaluation=evaluation,
                )

            metadata["read_exhausted"] = False
            metadata["next_resume_row_number"] = self._next_resume_row_number_from_metadata(metadata)
            metadata["last_duplicate_batch_count"] = duplicate_count
            batch.metadata_json = metadata
            self._refresh_batch_summary(batch)
            session.commit()
            return batch

    def _apply_evaluation_to_row(
        self,
        *,
        row: RealPlayerImportRow,
        source_row_number: int,
        source_row: dict[str, Any],
        eligibility_summary: dict[str, object],
        seed_input: RealPlayerSeedInput,
        evaluation: SecondZipEvaluationResult,
    ) -> None:
        metadata = self._base_row_metadata(
            source_row_number=source_row_number,
            source_row=source_row,
            eligibility_summary=eligibility_summary,
        )
        metadata.update(
            {
                "state": evaluation.state,
                "mapping_status": evaluation.mapping_status,
                "mapping_summary": evaluation.mapping_summary,
                "publish_ready": evaluation.publish_ready,
                "published": False,
                "free_agent_fallback": evaluation.free_agent_fallback,
                "fallback_valued": evaluation.fallback_valued,
                "pricing_preview_ready": evaluation.pricing_preview_ready,
                "payload_hash": self._payload_hash(seed_input.model_dump(mode="json")),
            }
        )
        row.row_number = source_row_number
        row.canonical_name = seed_input.canonical_name
        row.raw_payload_json = seed_input.model_dump(mode="json")
        row.normalized_payload_json = dict(evaluation.normalized_payload_json or {})
        row.status = evaluation.row_status
        row.match_action = evaluation.match_action
        row.import_action = "publish_ready" if evaluation.publish_ready else evaluation.state
        row.identity_confidence_score = None
        row.gtex_player_id = evaluation.gtex_player_id
        row.source_link_id = None
        row.real_player_profile_id = None
        row.authoritative_snapshot_id = None
        row.player_import_item_id = seed_input.player_import_item_id
        row.validation_errors_json = list(evaluation.validation_errors)
        row.candidate_players_json = list(evaluation.candidate_players)
        row.audit_findings_json = list(evaluation.audit_findings)
        row.review_status = evaluation.review_status
        row.review_reason = evaluation.review_reason
        row.import_metadata_json = self._merged_row_metadata(row, metadata)
        row.processed_at = utcnow()

    def _evaluate_candidates(self, candidates: list[SecondZipCandidate]) -> dict[tuple[str, str], SecondZipEvaluationResult]:
        if not candidates:
            return {}

        service = self._strict_ingestion_service()
        request = RealPlayerIngestionRequest(
            mode="curated_seed",
            players=[candidate.seed_input for candidate in candidates],
            ingestion_batch_id=f"2ndzip-eval-{uuid4().hex[:12]}",
            ingestion_source_version=f"2ndzip-eval-{uuid4().hex[:8]}",
            as_of=utcnow(),
        )

        with self.session_factory() as session:
            transaction = session.begin()
            try:
                prepared = service._prepare_batch(  # type: ignore[attr-defined]
                    session=session,
                    request=request,
                    ingestion_batch_id=request.ingestion_batch_id or f"2ndzip-eval-{uuid4().hex[:12]}",
                    as_of=request.as_of or utcnow(),
                )
                temp_batch = session.get(RealPlayerImportBatch, prepared.import_batch_id)
                if temp_batch is None:
                    raise SecondZipRealPlayerOpsError("Temporary 2nd.zip evaluation batch was not materialized.")
                rows_by_key = {
                    (row.source_name, row.source_player_key): row
                    for row in temp_batch.rows
                }
                issues_by_key: dict[tuple[str, str], list[Any]] = {}
                for issue in prepared.report.issues:
                    issues_by_key.setdefault((issue.source_name, issue.source_player_key), []).append(issue)
                staged_by_key = {
                    (staged.source_name, staged.source_player_key): staged
                    for staged in prepared.staged_players
                }
                evaluations: dict[tuple[str, str], SecondZipEvaluationResult] = {}
                for candidate in candidates:
                    key = (candidate.seed_input.source_name, candidate.seed_input.source_player_key)
                    row = rows_by_key.get(key)
                    staged = staged_by_key.get(key)
                    evaluations[key] = self._evaluation_result_for_candidate(
                        session=session,
                        candidate=candidate,
                        prepared=prepared,
                        row=row,
                        staged=staged,
                        issue_list=issues_by_key.get(key, []),
                    )
                return evaluations
            finally:
                if transaction.is_active:
                    transaction.rollback()

    def _publish_row(self, *, batch_id: str, batch_key: str, row: RealPlayerImportRow) -> None:
        try:
            result = self._publish_candidate(batch_key=batch_key, row=row)
            with self.session_factory() as session:
                current = self._load_row(session, row.id)
                metadata = self._row_metadata(current)
                metadata["publish_ready"] = False
                metadata["published"] = True
                metadata["published_at"] = utcnow().isoformat()
                metadata["state"] = "published"
                metadata["last_publish_error"] = None
                current.import_metadata_json = self._merged_row_metadata(current, metadata)
                current.status = RealPlayerImportRowStatus.IMPORTED.value
                current.import_action = result.action
                current.review_status = "resolved"
                current.review_reason = None
                current.gtex_player_id = result.gtex_player_id
                current.authoritative_snapshot_id = result.pricing_snapshot_id
                current.processed_at = utcnow()
                current.validation_errors_json = []
                batch = self._load_batch(session, batch_id)
                self._refresh_batch_summary(batch)
                session.commit()
        except Exception as exc:
            with self.session_factory() as session:
                current = self._load_row(session, row.id)
                metadata = self._row_metadata(current)
                metadata["publish_ready"] = False
                metadata["published"] = False
                metadata["state"] = "failed"
                metadata["last_publish_error"] = str(exc)
                current.import_metadata_json = self._merged_row_metadata(current, metadata)
                current.status = RealPlayerImportRowStatus.FAILED.value
                current.import_action = "publish_failed"
                current.review_status = "needs_review"
                current.review_reason = "publish_failed"
                current.validation_errors_json = list(dict.fromkeys([*(current.validation_errors_json or []), str(exc)]))
                batch = self._load_batch(session, batch_id)
                self._refresh_batch_summary(batch)
                session.commit()

    def _publish_candidate(self, *, batch_key: str, row: RealPlayerImportRow) -> RealPlayerIngestionItemResult:
        payload = RealPlayerSeedInput.model_validate(dict(row.raw_payload_json or {}))
        request = RealPlayerIngestionRequest(
            mode="curated_seed",
            players=[payload],
            ingestion_batch_id=f"{batch_key}:publish:{row.row_number}:{uuid4().hex[:8]}",
            ingestion_source_version=f"2ndzip-publish-{uuid4().hex[:8]}",
            as_of=utcnow(),
        )
        report = self._strict_ingestion_service().write_batch(request)
        if len(report.results) != 1:
            raise SecondZipRealPlayerOpsError(
                f"Publish for row {row.row_number} produced {len(report.results)} results; expected exactly one.",
                status_code=409,
            )
        return report.results[0]

    def _strict_ingestion_service(self) -> RealPlayerIngestionService:
        return RealPlayerIngestionService(
            session_factory=self.session_factory,
            settings=self.settings,
            normalization_service=self.normalization_service,
            identity_matcher=self.identity_matcher,
            canonical_mapping_service=RealPlayerCanonicalMappingService(
                settings=self.settings,
                auto_create_missing_entities=False,
            ),
        )

    def _evaluation_result_for_candidate(
        self,
        *,
        session: Session,
        candidate: SecondZipCandidate,
        prepared,
        row: RealPlayerImportRow | None,
        staged,
        issue_list: list[Any],
    ) -> SecondZipEvaluationResult:
        mapping_summary: dict[str, dict[str, object]] = {}
        if staged is not None:
            profile = session.get(RealPlayerProfile, staged.profile_id)
            raw_mapping = None
            if profile is not None and isinstance(profile.metadata_json, dict):
                raw_mapping = profile.metadata_json.get("canonical_mapping")
            if isinstance(raw_mapping, dict):
                mapping_summary = {
                    str(entity): dict(values)
                    for entity, values in raw_mapping.items()
                    if isinstance(values, dict)
                }

        issue_types = {str(issue.issue_type) for issue in issue_list}
        validation_errors = list(row.validation_errors_json or []) if row is not None else []
        candidate_players = list(row.candidate_players_json or []) if row is not None else []
        audit_findings = list(row.audit_findings_json or []) if row is not None else []
        for issue in issue_list:
            if issue.message not in validation_errors:
                validation_errors.append(issue.message)
            audit_findings.append(
                {
                    "finding_type": issue.issue_type,
                    "message": issue.message,
                }
            )

        mapping_status = self._mapping_status(mapping_summary)
        pricing_preview_ready = staged is not None and staged.gtex_player_id in prepared.preview_snapshots
        stable_gtex_player_id = None
        if row is not None and row.match_action in {"matched_existing", "source_link"}:
            stable_gtex_player_id = row.gtex_player_id

        state = "publish_ready"
        row_status = RealPlayerImportRowStatus.MATCHED.value
        review_status = "resolved"
        review_reason = None
        publish_ready = True
        hard_failure_types = {"ambiguous_match", "match_error", "normalization_error", "stage_error", "mode_error"}
        if "missing_pricing_snapshot" in issue_types or any(issue_type in hard_failure_types for issue_type in issue_types):
            state = "failed"
            row_status = RealPlayerImportRowStatus.FAILED.value
            review_status = "needs_review"
            review_reason = next(iter(sorted(issue_types)), "failed")
            publish_ready = False
        elif mapping_status == "unresolved":
            state = "unresolved"
            row_status = RealPlayerImportRowStatus.SKIPPED.value
            review_status = "needs_review"
            review_reason = "unresolved_mapping"
            publish_ready = False
        elif mapping_status == "partial":
            state = "mapped_partial"
            row_status = RealPlayerImportRowStatus.SKIPPED.value
            review_status = "needs_review"
            review_reason = "mapped_partial"
            publish_ready = False
        elif not pricing_preview_ready:
            state = "failed"
            row_status = RealPlayerImportRowStatus.FAILED.value
            review_status = "needs_review"
            review_reason = "missing_pricing_snapshot"
            publish_ready = False

        return SecondZipEvaluationResult(
            source_player_key=candidate.seed_input.source_player_key,
            canonical_name=candidate.seed_input.canonical_name,
            match_action=row.match_action if row is not None else None,
            gtex_player_id=stable_gtex_player_id,
            row_status=row_status,
            review_status=review_status,
            review_reason=review_reason,
            normalized_payload_json=dict(row.normalized_payload_json or {}) if row is not None else {},
            validation_errors=validation_errors,
            candidate_players=candidate_players,
            audit_findings=audit_findings,
            mapping_status=mapping_status,
            mapping_summary=mapping_summary,
            publish_ready=publish_ready,
            free_agent_fallback=self._is_free_agent_fallback(candidate.seed_input, mapping_summary),
            fallback_valued=False,
            pricing_preview_ready=pricing_preview_ready,
            state=state,
        )

    def _load_lookups(self, workdir: Path) -> dict[str, Any]:
        lookups: dict[str, Any] = {
            "clubs": self._csv_lookup(workdir / "clubs.csv", key_field="club_id"),
            "competitions": self._csv_lookup(workdir / "competitions.csv", key_field="competition_id"),
            "countries": self._csv_lookup(workdir / "countries.csv", key_field="country_name"),
        }
        lookups["reference_catalog"] = TransfermarktSecondZipReferenceCatalog.from_rows(
            clubs=lookups["clubs"].values(),
            competitions=lookups["competitions"].values(),
            countries=lookups["countries"].values(),
        )
        return lookups

    def _csv_lookup(self, path: Path, *, key_field: str) -> dict[str, dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for row in self._iter_csv_rows(path):
            key = str(row.get(key_field) or "").strip()
            if key:
                rows[key] = row
        return rows

    def _iter_player_rows(
        self,
        path: Path,
        *,
        start_row_number: int | None,
    ) -> list[tuple[int, dict[str, Any]]]:
        rows: list[tuple[int, dict[str, Any]]] = []
        minimum_row_number = max(int(start_row_number or 1), 1)
        for row_number, row in self._iter_csv_rows(path, include_row_numbers=True):
            if row_number < minimum_row_number:
                continue
            rows.append((row_number, row))
        return rows

    def _take_source_rows(
        self,
        source_rows: list[tuple[int, dict[str, Any]]],
        batch_size: int,
    ) -> list[tuple[int, dict[str, Any]]]:
        if not source_rows:
            return []
        batch = source_rows[:batch_size]
        del source_rows[:batch_size]
        return batch

    def _iter_csv_rows(
        self,
        path: Path,
        *,
        include_row_numbers: bool = False,
    ):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row_number, row in enumerate(reader, start=1):
                normalized = {
                    normalize_column_name(key): normalize_optional_text(value)
                    for key, value in row.items()
                    if key is not None
                }
                if include_row_numbers:
                    yield row_number, normalized
                else:
                    yield normalized

    def _build_seed_input(
        self,
        *,
        source_row: dict[str, Any],
        lookups: dict[str, Any],
    ) -> RealPlayerSeedInput:
        contract = map_player_row_to_contract(source_row)
        clubs = lookups.get("clubs", {})
        competitions = lookups.get("competitions", {})
        reference_catalog = lookups.get("reference_catalog")
        if not isinstance(reference_catalog, TransfermarktSecondZipReferenceCatalog):
            reference_catalog = TransfermarktSecondZipReferenceCatalog.from_rows(
                clubs=clubs.values(),
                competitions=competitions.values(),
                countries=(lookups.get("countries", {}) or {}).values(),
            )
        club_row = clubs.get(str(contract.current_club_id or "").strip()) if contract.current_club_id else None
        competition_id = contract.domestic_competition_id or (
            str(club_row.get("domestic_competition_id") or "").strip()
            if club_row is not None
            else None
        )
        competition_row = competitions.get(str(competition_id or "").strip()) if competition_id else None
        competition_name = (
            str(competition_row.get("name") or "").strip()
            if competition_row is not None
            else None
        ) or contract.domestic_competition_id

        source_item = map_player_row_to_source_item(
            source_row,
            reference_catalog=reference_catalog,
        )
        return RealPlayerSeedInput.model_validate(
            {
                **source_item.raw_payload,
                "current_real_world_league": source_item.current_competition_name or competition_name,
                "current_real_world_league_key": source_item.current_competition_id or competition_id,
                "competition_level": self._competition_level(
                    competition_row=competition_row,
                    competition_id=competition_id,
                ),
                "appearances": 0,
                "minutes_played": 0,
                "goals": 0,
                "assists": 0,
                "clean_sheets": 0,
                "source_last_refreshed_at": utcnow(),
                "player_import_item_id": f"2ndzip:{contract.external_player_id}",
            }
        )

    def _competition_level(
        self,
        *,
        competition_row: dict[str, Any] | None,
        competition_id: str | None,
    ) -> str:
        if competition_row is None:
            if competition_id and competition_id[-1:].isdigit():
                if competition_id.endswith("1"):
                    return "top_flight"
                if competition_id.endswith("2"):
                    return "second_tier"
            return "unknown"
        if str(competition_row.get("is_major_national_league") or "").casefold() == "true":
            return "top_flight"
        competition_type = str(competition_row.get("type") or "").casefold()
        competition_sub_type = str(competition_row.get("sub_type") or "").casefold()
        if "champions" in competition_sub_type or "cup" in competition_sub_type or "international" in competition_type:
            return "continental"
        if competition_id and competition_id[-1:].isdigit():
            if competition_id.endswith("1"):
                return "top_flight"
            if competition_id.endswith("2"):
                return "second_tier"
        return "first_division"

    def _mapping_status(self, mapping_summary: dict[str, dict[str, object]]) -> str:
        statuses = {
            str(details.get("status") or "skipped")
            for details in mapping_summary.values()
            if isinstance(details, dict)
        }
        if "unresolved" in statuses:
            return "unresolved"
        if "skipped" in statuses or not statuses:
            return "partial"
        return "ready"

    def _is_free_agent_fallback(
        self,
        payload: RealPlayerSeedInput,
        mapping_summary: dict[str, dict[str, object]],
    ) -> bool:
        club_summary = mapping_summary.get("club") or {}
        club_status = str(club_summary.get("status") or "")
        return not payload.current_real_world_club or club_status == "skipped"

    def _create_batch(
        self,
        *,
        archive_path: Path,
        archive_sha256: str,
        batch_key: str,
        batch_size: int,
        limit: int | None,
        provider_job_key: str,
    ) -> RealPlayerImportBatch:
        metadata = {
            "version": SECOND_ZIP_BATCH_VERSION,
            "archive_path": str(archive_path),
            "archive_sha256": archive_sha256,
            "batch_size": batch_size,
            "limit": limit,
            "total_rows_read": 0,
            "eligible_rows": 0,
            "duplicate_skipped_count": 0,
            "last_read_row_number": 0,
            "next_resume_row_number": 1,
            "scope_complete": False,
            "read_exhausted": False,
        }
        return RealPlayerImportBatch(
            batch_key=batch_key,
            provider_name=SECOND_ZIP_SOURCE_NAME,
            provider_job_key=provider_job_key,
            source_type=SECOND_ZIP_SOURCE_TYPE,
            mode=SECOND_ZIP_DRY_RUN_MODE,
            status=RealPlayerImportBatchStatus.QUEUED.value,
            requested_at=utcnow(),
            started_at=utcnow(),
            metadata_json=metadata,
            summary_json={},
        )

    def _refresh_batch_summary(self, batch: RealPlayerImportBatch) -> None:
        metadata = self._batch_metadata(batch)
        counts = self._counts_from_batch(batch)
        batch.submitted_row_count = counts.total_rows_read
        batch.normalized_row_count = counts.eligible_rows
        batch.matched_existing_count = sum(
            1
            for row in batch.rows
            if row.match_action in {"matched_existing", "source_link"}
        )
        batch.created_player_count = counts.inserted
        batch.updated_player_count = counts.updated
        batch.skipped_row_count = counts.duplicate_skipped + sum(
            1
            for row in batch.rows
            if self._row_state(row) in {"base_ineligible", "mapped_partial", "unresolved"}
        )
        batch.failed_row_count = counts.failed
        batch.authoritative_snapshot_count = counts.published
        batch.summary_json = {
            **counts.to_dict(),
            "read_exhausted": bool(metadata.get("read_exhausted")),
            "scope_complete": bool(metadata.get("scope_complete")),
            "next_resume_row_number": self._next_resume_row_number_from_metadata(metadata),
        }
        scope_complete = bool(metadata.get("scope_complete"))
        if batch.status != RealPlayerImportBatchStatus.RUNNING.value or scope_complete or batch.error_message:
            if batch.error_message:
                batch.status = RealPlayerImportBatchStatus.FAILED.value
            elif counts.failed or counts.unresolved or counts.mapped_partial:
                batch.status = RealPlayerImportBatchStatus.COMPLETED_WITH_ERRORS.value
            else:
                batch.status = RealPlayerImportBatchStatus.COMPLETED.value
        if bool(metadata.get("scope_complete")) or batch.status == RealPlayerImportBatchStatus.FAILED.value:
            batch.completed_at = utcnow()

    def _counts_from_batch(self, batch: RealPlayerImportBatch) -> SecondZipReportCounts:
        metadata = self._batch_metadata(batch)
        rows = list(batch.rows)
        return SecondZipReportCounts(
            total_rows_read=int(metadata.get("total_rows_read") or 0),
            eligible_rows=int(metadata.get("eligible_rows") or 0),
            inserted=sum(
                1
                for row in rows
                if row.status == RealPlayerImportRowStatus.IMPORTED.value and row.import_action == "created"
            ),
            updated=sum(
                1
                for row in rows
                if row.status == RealPlayerImportRowStatus.IMPORTED.value and row.import_action == "updated"
            ),
            duplicate_skipped=int(metadata.get("duplicate_skipped_count") or 0),
            mapped_ready=sum(1 for row in rows if self._row_mapping_status(row) == "ready"),
            mapped_partial=sum(1 for row in rows if self._row_mapping_status(row) == "partial"),
            unresolved=sum(1 for row in rows if self._row_mapping_status(row) == "unresolved"),
            fallback_valued=sum(1 for row in rows if bool(self._row_metadata(row).get("fallback_valued"))),
            free_agent_fallback=sum(1 for row in rows if bool(self._row_metadata(row).get("free_agent_fallback"))),
            publish_ready=sum(1 for row in rows if self._row_publish_ready(row)),
            published=sum(1 for row in rows if self._row_is_published(row)),
            failed=sum(1 for row in rows if self._row_state(row) == "failed"),
        )

    def _report_from_batch(self, batch: RealPlayerImportBatch, *, selected_row_count: int = 0) -> SecondZipRunReport:
        metadata = self._batch_metadata(batch)
        return SecondZipRunReport(
            run_id=batch.id,
            batch_key=batch.batch_key,
            status=batch.status,
            archive_path=str(metadata.get("archive_path") or ""),
            archive_sha256=str(metadata.get("archive_sha256") or ""),
            batch_size=int(metadata.get("batch_size") or 1000),
            limit=self._metadata_limit(metadata),
            read_exhausted=bool(metadata.get("read_exhausted")),
            scope_complete=bool(metadata.get("scope_complete")),
            next_resume_row_number=self._next_resume_row_number_from_metadata(metadata),
            counts=self._counts_from_batch(batch),
            error_message=batch.error_message,
            selected_row_count=selected_row_count,
        )

    def _candidate_from_row(self, row: RealPlayerImportRow) -> SecondZipCandidate:
        payload = RealPlayerSeedInput.model_validate(dict(row.raw_payload_json or {}))
        metadata = self._row_metadata(row)
        source_row = dict(metadata.get("source_row") or {})
        eligibility_summary = dict(metadata.get("eligibility") or {"eligible": True})
        source_row_number = int(metadata.get("source_row_number") or row.row_number)
        return SecondZipCandidate(
            source_row_number=source_row_number,
            source_row=source_row,
            seed_input=payload,
            eligibility_summary=eligibility_summary,
        )

    def _load_batch(self, session: Session, batch_id: str) -> RealPlayerImportBatch:
        batch = session.scalar(
            select(RealPlayerImportBatch)
            .options(selectinload(RealPlayerImportBatch.rows))
            .where(
                RealPlayerImportBatch.id == batch_id,
                RealPlayerImportBatch.provider_name == SECOND_ZIP_SOURCE_NAME,
                RealPlayerImportBatch.source_type == SECOND_ZIP_SOURCE_TYPE,
            )
        )
        if batch is None:
            raise SecondZipRealPlayerOpsError(f"2nd.zip run '{batch_id}' was not found.", status_code=404)
        return batch

    def _load_row(self, session: Session, row_id: str) -> RealPlayerImportRow:
        row = session.get(RealPlayerImportRow, row_id)
        if row is None:
            raise SecondZipRealPlayerOpsError(f"2nd.zip row '{row_id}' was not found.", status_code=404)
        return row

    def _upsert_row(
        self,
        session: Session,
        *,
        batch: RealPlayerImportBatch,
        source_player_key: str,
        canonical_name: str,
        row_number: int,
    ) -> RealPlayerImportRow:
        row = session.scalar(
            select(RealPlayerImportRow).where(
                RealPlayerImportRow.batch_id == batch.id,
                RealPlayerImportRow.source_name == SECOND_ZIP_SOURCE_NAME,
                RealPlayerImportRow.source_player_key == source_player_key,
            )
        )
        if row is None:
            row = RealPlayerImportRow(
                batch_id=batch.id,
                row_number=row_number,
                source_name=SECOND_ZIP_SOURCE_NAME,
                source_player_key=source_player_key,
                canonical_name=canonical_name,
            )
            session.add(row)
        return row

    def _batch_key(self, *, archive_sha256: str, limit: int | None) -> str:
        scope = f"first-{limit}" if limit is not None else "all"
        return f"2nd-zip-{archive_sha256[:12]}-{scope}"

    def _provider_job_key(self, *, archive_sha256: str, limit: int | None) -> str:
        return f"{archive_sha256[:24]}:{limit if limit is not None else 'all'}"

    def _archive_sha256(self, archive_path: Path) -> str:
        digest = hashlib.sha256()
        with archive_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _payload_hash(self, payload: dict[str, object]) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()

    def _base_row_metadata(
        self,
        *,
        source_row_number: int,
        source_row: dict[str, Any],
        eligibility_summary: dict[str, object],
    ) -> dict[str, object]:
        return {
            "version": SECOND_ZIP_BATCH_VERSION,
            "source_row_number": source_row_number,
            "source_row": dict(source_row),
            "eligibility": dict(eligibility_summary),
            "eligible": bool(eligibility_summary.get("eligible")),
        }

    def _batch_metadata(self, batch: RealPlayerImportBatch) -> dict[str, object]:
        return dict(batch.metadata_json or {})

    def _row_metadata(self, row: RealPlayerImportRow) -> dict[str, object]:
        metadata = dict(row.import_metadata_json or {})
        nested = metadata.get(SECOND_ZIP_METADATA_KEY)
        if isinstance(nested, dict):
            return dict(nested)
        return {}

    def _merged_row_metadata(self, row: RealPlayerImportRow, second_zip_metadata: dict[str, object]) -> dict[str, object]:
        metadata = dict(row.import_metadata_json or {})
        metadata[SECOND_ZIP_METADATA_KEY] = second_zip_metadata
        return metadata

    def _row_mapping_status(self, row: RealPlayerImportRow) -> str:
        return str(self._row_metadata(row).get("mapping_status") or "")

    def _row_publish_ready(self, row: RealPlayerImportRow) -> bool:
        metadata = self._row_metadata(row)
        return bool(metadata.get("publish_ready")) and not bool(metadata.get("published"))

    def _row_publish_tier(self, row: RealPlayerImportRow) -> SecondZipPublishTier:
        metadata = self._row_metadata(row)
        if bool(metadata.get("fallback_valued")) or bool(metadata.get("free_agent_fallback")):
            return SecondZipPublishTier.TIER_2
        if self._row_publish_ready(row) or self._row_is_published(row):
            return SecondZipPublishTier.TIER_1
        return SecondZipPublishTier.TIER_3

    def _row_is_published(self, row: RealPlayerImportRow) -> bool:
        return bool(self._row_metadata(row).get("published")) or row.status == RealPlayerImportRowStatus.IMPORTED.value

    def _row_state(self, row: RealPlayerImportRow) -> str:
        return str(self._row_metadata(row).get("state") or "")

    def _remaining_row_budget(self, metadata: dict[str, object]) -> int | None:
        limit = self._metadata_limit(metadata)
        if limit is None:
            return None
        return max(limit - int(metadata.get("total_rows_read") or 0), 0)

    def _next_resume_row_number_from_metadata(self, metadata: dict[str, object]) -> int | None:
        if bool(metadata.get("scope_complete")):
            return None
        return int(metadata.get("last_read_row_number") or 0) + 1

    def _metadata_limit(self, metadata: dict[str, object]) -> int | None:
        raw_value = metadata.get("limit")
        return int(raw_value) if raw_value is not None else None

    def _metadata_archive_path(self, metadata: dict[str, object]) -> Path | None:
        value = str(metadata.get("archive_path") or "").strip()
        return Path(value) if value else None

    def _metadata_archive_sha(self, metadata: dict[str, object]) -> str:
        return str(metadata.get("archive_sha256") or "")


__all__ = [
    "SECOND_ZIP_BATCH_VERSION",
    "SECOND_ZIP_SOURCE_TYPE",
    "SecondZipRealPlayerOpsError",
    "SecondZipRealPlayerOpsService",
    "SecondZipReportCounts",
    "SecondZipRunReport",
]
