from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import tempfile

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker, selectinload

from app.core.config import Settings, get_settings
from app.ingestion.real_player_batch_runner import RealPlayerBatchRunReport, RealPlayerBatchRunner
from app.ingestion.real_player_identity_audit import RealPlayerAuditFinding, RealPlayerIdentityAuditService
from app.ingestion.real_player_import_ops_schemas import (
    RealPlayerImportBatchDetailView,
    RealPlayerImportBatchIssueView,
    RealPlayerImportBatchResumeRequest,
    RealPlayerImportBatchRunRequest,
    RealPlayerImportBatchSummaryView,
    RealPlayerImportRowStatusView,
    RealPlayerImportValuationIssueView,
    RealPlayerImportValuationStatusView,
)
from app.ingestion.real_player_normalization_service import RealPlayerNormalizationService
from app.ingestion.second_zip_staged_import import (
    SECOND_ZIP_SOURCE_TYPE,
    SecondZipStagedImportBuilder,
    SecondZipStagedImportError,
)
from app.models.base import utcnow
from app.models.real_player_import_batch import (
    RealPlayerImportBatch,
    RealPlayerImportBatchStatus,
    RealPlayerImportRow,
    RealPlayerImportRowStatus,
)
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest


class RealPlayerImportOpsError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RealPlayerImportSourceLoadResult:
    source_path: Path
    request: RealPlayerIngestionRequest
    manifest_hash: str
    provider_name: str | None = None
    source_metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class RealPlayerImportOpsService:
    session_factory: sessionmaker[Session]
    database_url: str
    settings: Settings = field(default_factory=get_settings)
    normalization_service: RealPlayerNormalizationService = field(default_factory=RealPlayerNormalizationService)
    audit_service: RealPlayerIdentityAuditService = field(default_factory=RealPlayerIdentityAuditService)
    second_zip_builder: SecondZipStagedImportBuilder = field(default_factory=SecondZipStagedImportBuilder)

    def list_batches(
        self,
        *,
        limit: int = 20,
        batch_status: str | None = None,
        provider_name: str | None = None,
        batch_key: str | None = None,
    ) -> list[RealPlayerImportBatchSummaryView]:
        with self.session_factory() as session:
            statement = select(RealPlayerImportBatch).order_by(
                RealPlayerImportBatch.requested_at.desc(),
                RealPlayerImportBatch.created_at.desc(),
            )
            if batch_status:
                statement = statement.where(RealPlayerImportBatch.status == batch_status)
            if provider_name:
                statement = statement.where(RealPlayerImportBatch.provider_name == provider_name)
            if batch_key:
                statement = statement.where(RealPlayerImportBatch.batch_key == batch_key)
            batches = list(session.scalars(statement.limit(limit)))
            return [self._batch_summary_view(batch) for batch in batches]

    def get_batch(self, batch_id: str, *, include_rows: bool = False) -> RealPlayerImportBatchDetailView:
        with self.session_factory() as session:
            batch = self._load_batch(session, batch_id=batch_id, include_rows=include_rows)
            return self._batch_detail_view(batch, include_rows=include_rows)

    def run_batch(
        self,
        *,
        actor_user_id: str | None,
        payload: RealPlayerImportBatchRunRequest,
    ) -> RealPlayerImportBatchDetailView:
        load_result = self._load_source_request(payload.manifest_path, source_type=payload.source_type)
        manifest_path = load_result.source_path
        manifest_request = load_result.request
        manifest_hash = load_result.manifest_hash
        source_metadata = load_result.source_metadata
        provider_name = load_result.provider_name or payload.provider_name or self._provider_name_from_request(manifest_request)
        requested_batch_key = payload.batch_key or manifest_request.ingestion_batch_id or self._default_batch_key(manifest_hash)
        batch_id: str | None = None
        request: RealPlayerIngestionRequest | None = None
        work_request: RealPlayerIngestionRequest | None = None

        with self.session_factory() as session:
            existing = self._find_existing_batch(
                session,
                batch_key=requested_batch_key,
                provider_name=provider_name,
                source_type=payload.source_type,
                manifest_hash=manifest_hash,
            )
            if existing is not None and existing.status == RealPlayerImportBatchStatus.RUNNING.value:
                raise RealPlayerImportOpsError(
                    f"Real-player import batch '{existing.batch_key}' is already running.",
                    status_code=409,
                )

            if existing is not None and not payload.restart:
                existing_manifest_hash = self._manifest_hash_from_batch(existing)
                if existing.batch_key == requested_batch_key and existing_manifest_hash not in {"", manifest_hash}:
                    raise RealPlayerImportOpsError(
                        (
                            f"Real-player import batch '{requested_batch_key}' already exists for a different manifest. "
                            "Use restart explicitly."
                        ),
                        status_code=409,
                    )

            batch_key = existing.batch_key if existing is not None else requested_batch_key
            request = manifest_request.model_copy(update={"ingestion_batch_id": batch_key})

            if existing is not None and not payload.restart:
                work_request = self._request_from_batch(existing, pending_only=True)
                if not work_request.players:
                    self._record_noop_attempt(
                        session,
                        batch=existing,
                        actor_user_id=actor_user_id,
                        runner_mode=payload.mode,
                        request=request,
                        manifest_path=manifest_path,
                        manifest_hash=manifest_hash,
                        source_metadata=source_metadata,
                        reason="idempotent_rerun",
                    )
                    batch_id = existing.id
                    session.commit()
                    return self.get_batch(batch_id, include_rows=False)

                batch = self._prepare_existing_batch(
                    session,
                    batch=existing,
                    actor_user_id=actor_user_id,
                    runner_mode=payload.mode,
                    request=request,
                    manifest_path=manifest_path,
                    manifest_hash=manifest_hash,
                    source_metadata=source_metadata,
                )
            else:
                work_request = request
                batch = self._prepare_batch(
                    session,
                    batch_key=batch_key,
                    actor_user_id=actor_user_id,
                    provider_name=provider_name,
                    provider_job_key=payload.provider_job_key,
                    source_type=payload.source_type,
                    runner_mode=payload.mode,
                    manifest_path=manifest_path,
                    manifest_hash=manifest_hash,
                    source_metadata=source_metadata,
                    request=request,
                    restart=payload.restart,
                )
            batch_id = batch.id
            session.commit()

        assert request is not None
        assert work_request is not None
        report = self._run_report(request=work_request, runner_mode=payload.mode)
        with self.session_factory() as session:
            batch = self._load_batch(session, batch_id=batch_id, include_rows=True)
            self._apply_report(session, batch=batch, request=request, report=report)
            session.commit()

        return self.get_batch(batch_id, include_rows=False)

    def resume_batch(
        self,
        *,
        batch_id: str,
        actor_user_id: str | None,
        payload: RealPlayerImportBatchResumeRequest,
    ) -> RealPlayerImportBatchDetailView:
        with self.session_factory() as session:
            batch = self._load_batch(session, batch_id=batch_id, include_rows=True)
            if batch.status == RealPlayerImportBatchStatus.RUNNING.value:
                raise RealPlayerImportOpsError(
                    f"Real-player import batch '{batch_id}' is already running.",
                    status_code=409,
                )
            request = self._request_from_batch(batch)
            work_request = self._request_from_batch(batch, pending_only=True)
            runner_mode = payload.mode or batch.mode
            if not work_request.players:
                self._record_noop_attempt(
                    session,
                    batch=batch,
                    actor_user_id=actor_user_id,
                    runner_mode=runner_mode,
                    request=request,
                    manifest_path=self._manifest_path_from_batch(batch),
                    manifest_hash=self._manifest_hash_from_batch(batch),
                    source_metadata=None,
                    reason="resume_noop",
                )
                session.commit()
                return self.get_batch(batch_id, include_rows=False)
            batch = self._prepare_existing_batch(
                session,
                batch=batch,
                actor_user_id=actor_user_id,
                runner_mode=runner_mode,
                request=request,
                manifest_path=self._manifest_path_from_batch(batch),
                manifest_hash=self._manifest_hash_from_batch(batch),
                source_metadata=None,
            )
            session.commit()

        report = self._run_report(request=work_request, runner_mode=runner_mode)
        with self.session_factory() as session:
            batch = self._load_batch(session, batch_id=batch_id, include_rows=True)
            self._apply_report(session, batch=batch, request=request, report=report)
            session.commit()

        return self.get_batch(batch_id, include_rows=False)

    def list_unresolved_issues(
        self,
        *,
        batch_id: str,
        issue_type: str | None = None,
        unresolved_only: bool = True,
    ) -> list[RealPlayerImportBatchIssueView]:
        with self.session_factory() as session:
            batch = self._load_batch(session, batch_id=batch_id, include_rows=True)
            issues: list[RealPlayerImportBatchIssueView] = []
            for row in sorted(batch.rows, key=lambda item: item.row_number):
                if unresolved_only and row.review_status == "resolved" and row.status != RealPlayerImportRowStatus.FAILED.value:
                    continue

                findings = row.audit_findings_json or []
                matched_finding = False
                for finding in findings:
                    finding_type = str(finding.get("finding_type") or "review")
                    if issue_type and finding_type != issue_type:
                        continue
                    matched_finding = True
                    issues.append(
                        RealPlayerImportBatchIssueView(
                            row_id=row.id,
                            row_number=row.row_number,
                            source_name=row.source_name,
                            source_player_key=row.source_player_key,
                            canonical_name=row.canonical_name,
                            row_status=row.status,
                            review_status=row.review_status,
                            review_reason=row.review_reason,
                            issue_type=finding_type,
                            required_action=finding.get("required_action"),
                            gtex_player_id=row.gtex_player_id,
                            validation_errors=list(row.validation_errors_json or []),
                            candidate_players=list(row.candidate_players_json or []),
                            details_json=dict(finding.get("details") or {}),
                        )
                    )
                if matched_finding:
                    continue
                if issue_type and issue_type != "validation_error":
                    continue
                if row.validation_errors_json:
                    issues.append(
                        RealPlayerImportBatchIssueView(
                            row_id=row.id,
                            row_number=row.row_number,
                            source_name=row.source_name,
                            source_player_key=row.source_player_key,
                            canonical_name=row.canonical_name,
                            row_status=row.status,
                            review_status=row.review_status,
                            review_reason=row.review_reason,
                            issue_type="validation_error",
                            required_action=row.review_reason,
                            gtex_player_id=row.gtex_player_id,
                            validation_errors=list(row.validation_errors_json or []),
                            candidate_players=list(row.candidate_players_json or []),
                            details_json={},
                        )
                    )
            return issues

    def get_valuation_status(self, *, batch_id: str) -> RealPlayerImportValuationStatusView:
        with self.session_factory() as session:
            batch = self._load_batch(session, batch_id=batch_id, include_rows=True)
            imported_rows = [row for row in batch.rows if row.status == RealPlayerImportRowStatus.IMPORTED.value]
            tracked_snapshot_count = sum(1 for row in batch.rows if row.authoritative_snapshot_id)
            tracked_missing_count = sum(1 for row in imported_rows if not row.authoritative_snapshot_id)

            persisted_target_player_count = 0
            persisted_pricing_issue_count = 0
            persisted_stability_issue_count = 0
            audit_clean: bool | None = None
            issues: list[RealPlayerImportValuationIssueView] = []
            if batch.batch_key and batch.status in {
                RealPlayerImportBatchStatus.COMPLETED.value,
                RealPlayerImportBatchStatus.COMPLETED_WITH_ERRORS.value,
                RealPlayerImportBatchStatus.FAILED.value,
            } and (imported_rows or tracked_snapshot_count):
                audit_report = self.audit_service.audit_batch(
                    session,
                    ingestion_batch_id=batch.batch_key,
                    baseline=None,
                )
                persisted_target_player_count = len(audit_report.target_player_ids)
                persisted_pricing_issue_count = audit_report.missing_pricing_count
                persisted_stability_issue_count = audit_report.stability_count
                audit_clean = audit_report.is_clean()
                issues = self._valuation_issue_views(batch=batch, audit_findings=audit_report.pricing_findings)

            return RealPlayerImportValuationStatusView(
                batch_id=batch.id,
                batch_key=batch.batch_key,
                batch_status=batch.status,
                total_rows=len(batch.rows),
                imported_row_count=len(imported_rows),
                tracked_authoritative_snapshot_count=tracked_snapshot_count,
                tracked_missing_authoritative_snapshot_count=tracked_missing_count,
                persisted_target_player_count=persisted_target_player_count,
                persisted_pricing_issue_count=persisted_pricing_issue_count,
                persisted_stability_issue_count=persisted_stability_issue_count,
                audit_clean=audit_clean,
                issues=issues,
            )

    def _prepare_batch(
        self,
        session: Session,
        *,
        batch_key: str,
        actor_user_id: str | None,
        provider_name: str,
        provider_job_key: str | None,
        source_type: str,
        runner_mode: str,
        manifest_path: Path,
        manifest_hash: str,
        source_metadata: dict[str, object] | None,
        request: RealPlayerIngestionRequest,
        restart: bool,
    ) -> RealPlayerImportBatch:
        existing = session.scalar(
            select(RealPlayerImportBatch)
            .options(selectinload(RealPlayerImportBatch.rows))
            .where(RealPlayerImportBatch.batch_key == batch_key)
        )
        if existing is not None and existing.status == RealPlayerImportBatchStatus.RUNNING.value:
            raise RealPlayerImportOpsError(
                f"Real-player import batch '{batch_key}' is already running.",
                status_code=409,
            )
        if existing is not None and not restart:
            raise RealPlayerImportOpsError(
                f"Real-player import batch '{batch_key}' already exists. Use resume or restart explicitly.",
                status_code=409,
            )

        now = utcnow()
        metadata = self._metadata_payload(
            request=request,
            runner_mode=runner_mode,
            provider_name=provider_name,
            provider_job_key=provider_job_key,
            source_type=source_type,
            manifest_path=manifest_path,
            manifest_hash=manifest_hash,
            source_metadata=source_metadata,
            previous_metadata=existing.metadata_json if existing is not None else None,
        )
        batch = existing or RealPlayerImportBatch(batch_key=batch_key)
        batch.provider_name = provider_name
        batch.provider_job_key = provider_job_key
        batch.source_type = source_type
        batch.mode = runner_mode
        batch.status = RealPlayerImportBatchStatus.RUNNING.value
        batch.requested_by_user_id = actor_user_id
        batch.requested_at = now
        batch.started_at = now
        batch.completed_at = None
        batch.submitted_row_count = len(request.players)
        batch.normalized_row_count = 0
        batch.matched_existing_count = 0
        batch.created_player_count = 0
        batch.updated_player_count = 0
        batch.skipped_row_count = 0
        batch.failed_row_count = 0
        batch.authoritative_snapshot_count = 0
        batch.metadata_json = metadata
        batch.summary_json = {}
        batch.error_message = None
        if existing is None:
            session.add(batch)
            session.flush()

        self._replace_rows(session, batch=batch, request=request, runner_mode=runner_mode)
        return batch

    def _prepare_existing_batch(
        self,
        session: Session,
        *,
        batch: RealPlayerImportBatch,
        actor_user_id: str | None,
        runner_mode: str,
        request: RealPlayerIngestionRequest,
        manifest_path: Path | None,
        manifest_hash: str,
        source_metadata: dict[str, object] | None,
    ) -> RealPlayerImportBatch:
        now = utcnow()
        resume_state = self._resume_state(batch.rows)
        metadata = self._metadata_payload(
            request=request,
            runner_mode=runner_mode,
            provider_name=batch.provider_name,
            provider_job_key=batch.provider_job_key,
            source_type=batch.source_type,
            manifest_path=manifest_path,
            manifest_hash=manifest_hash,
            source_metadata=source_metadata,
            previous_metadata=batch.metadata_json,
        )
        metadata.update(resume_state)
        batch.mode = runner_mode
        batch.status = RealPlayerImportBatchStatus.RUNNING.value
        batch.requested_by_user_id = actor_user_id
        batch.requested_at = now
        batch.started_at = now
        batch.completed_at = None
        batch.submitted_row_count = len(batch.rows)
        batch.normalized_row_count = 0
        batch.matched_existing_count = 0
        batch.created_player_count = 0
        batch.updated_player_count = 0
        batch.skipped_row_count = 0
        batch.failed_row_count = 0
        batch.authoritative_snapshot_count = 0
        batch.metadata_json = metadata
        batch.summary_json = {}
        batch.error_message = None
        for row in batch.rows:
            if self._row_is_completed(row):
                continue
            self._reset_row_for_retry(row=row, runner_mode=runner_mode)
        session.flush()
        return batch

    def _replace_rows(
        self,
        session: Session,
        *,
        batch: RealPlayerImportBatch,
        request: RealPlayerIngestionRequest,
        runner_mode: str,
    ) -> None:
        session.execute(delete(RealPlayerImportRow).where(RealPlayerImportRow.batch_id == batch.id))
        as_of = request.as_of or datetime.now(UTC)
        for row_number, payload in enumerate(request.players, start=1):
            normalized = self.normalization_service.normalize(payload, as_of=as_of)
            identity = normalized.identity
            row = RealPlayerImportRow(
                batch_id=batch.id,
                row_number=row_number,
                source_name=payload.source_name,
                source_player_key=payload.source_player_key,
                canonical_name=payload.canonical_name,
                status=RealPlayerImportRowStatus.PENDING.value,
                normalized_full_name=identity.normalized_full_name,
                normalized_display_name=identity.normalized_display_name,
                name_token_signature=identity.name_token_signature,
                exact_identity_key=identity.exact_identity_key,
                name_birthyear_club_key=identity.name_birthyear_club_key,
                name_birthyear_nationality_key=identity.name_birthyear_nationality_key,
                normalized_nationality=identity.normalized_nationality,
                nationality_code=identity.nationality_code,
                primary_position_key=identity.primary_position_key,
                secondary_position_keys_json=list(identity.secondary_position_keys),
                position_family=identity.position_family,
                dominant_foot=identity.dominant_foot,
                height_cm=identity.height_cm,
                club_reference_key=identity.club_reference_key,
                league_reference_key=identity.league_reference_key,
                raw_payload_json=payload.model_dump(mode="json"),
                normalized_payload_json={
                    **identity.to_dict(),
                    "competition_level": normalized.competition_level,
                    "real_player_tier": normalized.real_player_tier,
                },
                import_metadata_json={"runner_mode": runner_mode},
                validation_errors_json=[],
                candidate_players_json=[],
                review_status="pending",
                review_reason=None,
                audit_findings_json=[],
            )
            session.add(row)
        session.flush()

    def _apply_report(
        self,
        session: Session,
        *,
        batch: RealPlayerImportBatch,
        request: RealPlayerIngestionRequest,
        report: RealPlayerBatchRunReport,
    ) -> None:
        rows = list(session.scalars(select(RealPlayerImportRow).where(RealPlayerImportRow.batch_id == batch.id)))
        rows_by_source_key = {
            f"{row.source_name}:{row.source_player_key}": row
            for row in rows
        }
        batch_findings: list[dict[str, object]] = []
        executed_source_keys = {
            f"{execution.source_name}:{execution.source_player_key}"
            for execution in report.execution_rows
        }

        for preflight in report.preflight_rows:
            source_key = f"{preflight.source_name}:{preflight.source_player_key}"
            row = rows_by_source_key.get(source_key)
            if row is None:
                continue
            row.match_action = preflight.resolved_action
            row.identity_confidence_score = preflight.confidence_score
            row.gtex_player_id = preflight.gtex_player_id
            row.candidate_players_json = [
                {"player_id": candidate_id}
                for candidate_id in preflight.candidate_ids
            ]
            row.import_metadata_json = {
                **(row.import_metadata_json or {}),
                "preflight_audit_status": preflight.audit_status,
            }
            if preflight.audit_status == "fail":
                row.status = RealPlayerImportRowStatus.FAILED.value
                row.review_status = "needs_review"
                row.review_reason = row.review_reason or preflight.resolved_action
            else:
                row.status = RealPlayerImportRowStatus.MATCHED.value
                row.review_status = "resolved"
                row.review_reason = None

        for execution in report.execution_rows:
            source_key = f"{execution.source_name}:{execution.source_player_key}"
            row = rows_by_source_key.get(source_key)
            if row is None:
                continue
            row.import_action = execution.resolved_action
            row.gtex_player_id = execution.gtex_player_id
            row.identity_confidence_score = execution.confidence_score
            row.authoritative_snapshot_id = execution.pricing_snapshot_id
            row.processed_at = utcnow()
            row.import_metadata_json = {
                **(row.import_metadata_json or {}),
                "pricing_status": execution.pricing_status,
                "execution_audit_status": execution.audit_status,
                "commit_status": execution.commit_status,
            }
            if execution.commit_status == "committed" and execution.audit_status == "pass":
                row.status = RealPlayerImportRowStatus.IMPORTED.value
                row.review_status = "resolved"
                row.review_reason = None
            elif execution.commit_status == "rolled_back" and execution.audit_status == "pass":
                row.status = RealPlayerImportRowStatus.MATCHED.value
                row.review_status = "resolved"
                row.review_reason = None
            else:
                row.status = RealPlayerImportRowStatus.FAILED.value
                row.review_status = "needs_review"
                row.review_reason = row.review_reason or execution.audit_status

        for finding in (
            *report.duplicate_findings,
            *report.ambiguous_findings,
            *report.pricing_findings,
            *report.stability_findings,
        ):
            matched_rows = self._rows_for_finding(rows_by_source_key=rows_by_source_key, rows=rows, finding=finding)
            if not matched_rows:
                batch_findings.append(finding.to_dict())
                continue
            for row in matched_rows:
                self._append_finding(row, finding)

        for row in rows:
            source_key = f"{row.source_name}:{row.source_player_key}"
            if report.error_message and row.status == RealPlayerImportRowStatus.MATCHED.value and source_key not in executed_source_keys:
                row.status = RealPlayerImportRowStatus.PENDING.value
                row.review_status = "pending"
                row.review_reason = "resume_pending"
                row.import_metadata_json = {
                    **(row.import_metadata_json or {}),
                    "resume_required": True,
                }
            if row.review_status == "pending":
                row.review_status = "resolved" if row.status != RealPlayerImportRowStatus.FAILED.value else "needs_review"
            if row.review_status == "needs_review" and not row.review_reason:
                row.review_reason = "manual_review"

        source_duplicate_skipped_count = self._source_duplicate_skipped_count(batch.metadata_json)
        source_row_count = int((batch.metadata_json or {}).get("source_row_count") or len(rows))
        source_eligible_row_count = int((batch.metadata_json or {}).get("source_eligible_row_count") or len(rows))
        source_filtered_row_count = int((batch.metadata_json or {}).get("source_filtered_row_count") or 0)
        duplicate_skipped_count = (
            source_duplicate_skipped_count
            + int((batch.metadata_json or {}).get("preserved_completed_row_count") or 0)
        )
        pending_row_count = sum(
            1
            for row in rows
            if row.status == RealPlayerImportRowStatus.PENDING.value
        )
        batch_status = self._batch_status_from_rows(report=report, rows=rows, pending_row_count=pending_row_count)
        resume_state = self._resume_state(rows)
        batch.completed_at = utcnow()
        batch.normalized_row_count = len(rows)
        batch.matched_existing_count = sum(
            1
            for row in rows
            if row.match_action in {"source_link", "matched_existing"}
        )
        batch.created_player_count = sum(
            1
            for row in rows
            if row.status == RealPlayerImportRowStatus.IMPORTED.value and row.import_action == "created"
        )
        batch.updated_player_count = sum(
            1
            for row in rows
            if row.status == RealPlayerImportRowStatus.IMPORTED.value and row.import_action == "updated"
        )
        batch.skipped_row_count = duplicate_skipped_count + sum(
            1
            for row in rows
            if row.status == RealPlayerImportRowStatus.SKIPPED.value
        )
        batch.failed_row_count = sum(
            1
            for row in rows
            if row.status == RealPlayerImportRowStatus.FAILED.value
        )
        batch.authoritative_snapshot_count = sum(1 for row in rows if row.authoritative_snapshot_id)
        batch.error_message = report.error_message
        batch.summary_json = {
            "verdict": report.verdict,
            "runner_mode": report.runner_mode,
            "request_mode": report.request_mode,
            "ingestion_batch_id": report.ingestion_batch_id,
            "ambiguous_matches": report.ambiguous_matches,
            "missing_pricing_snapshots": report.missing_pricing_snapshots,
            "hard_failures": report.hard_failures,
            "preflight_row_count": len(report.preflight_rows),
            "execution_row_count": len(report.execution_rows),
            "duplicate_finding_count": len(report.duplicate_findings),
            "ambiguous_finding_count": len(report.ambiguous_findings),
            "pricing_finding_count": len(report.pricing_findings),
            "stability_finding_count": len(report.stability_findings),
            "source_row_count": source_row_count,
            "source_eligible_row_count": source_eligible_row_count,
            "source_filtered_row_count": source_filtered_row_count,
            "duplicate_skipped_count": duplicate_skipped_count,
            "source_duplicate_skipped_count": source_duplicate_skipped_count,
            "pending_row_count": pending_row_count,
            "resume_from_row_number": resume_state["resume_from_row_number"],
            "last_successful_row_number": resume_state["last_successful_row_number"],
            "batch_findings": batch_findings,
        }
        batch.metadata_json = self._record_attempt_outcome(
            {
                **dict(batch.metadata_json or {}),
                **resume_state,
            },
            mode=report.runner_mode,
            verdict=report.verdict,
            status=batch_status,
            error_message=report.error_message,
        )
        batch.status = batch_status
        session.flush()

    def _run_report(self, *, request: RealPlayerIngestionRequest, runner_mode: str) -> RealPlayerBatchRunReport:
        payload = request.model_dump(mode="json")
        handle, path_str = tempfile.mkstemp(prefix="gtex-real-player-batch-", suffix=".json")
        temp_path = Path(path_str)
        try:
            with open(handle, "w", encoding="utf-8", closefd=True) as file_handle:
                json.dump(payload, file_handle, indent=2, sort_keys=True)
            return RealPlayerBatchRunner(
                database_url=self.database_url,
                batch_path=temp_path,
                settings=self.settings,
            ).run(mode=runner_mode)
        finally:
            temp_path.unlink(missing_ok=True)

    def _load_source_request(
        self,
        manifest_path: str,
        *,
        source_type: str,
    ) -> RealPlayerImportSourceLoadResult:
        if source_type == SECOND_ZIP_SOURCE_TYPE:
            return self._load_second_zip_request(manifest_path)
        return self._load_manifest_request(manifest_path)

    def _load_manifest_request(self, manifest_path: str) -> RealPlayerImportSourceLoadResult:
        resolved_path = Path(manifest_path).expanduser().resolve()
        if not resolved_path.exists():
            raise RealPlayerImportOpsError(f"Manifest path '{resolved_path}' does not exist.", status_code=404)
        payload_text = resolved_path.read_text(encoding="utf-8")
        payload = json.loads(payload_text)
        if not isinstance(payload, dict):
            raise RealPlayerImportOpsError("Real-player manifest must contain a JSON object.")
        request = RealPlayerIngestionRequest.model_validate(payload)
        manifest_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        return RealPlayerImportSourceLoadResult(
            source_path=resolved_path,
            request=request,
            manifest_hash=manifest_hash,
        )

    def _load_second_zip_request(self, archive_path: str) -> RealPlayerImportSourceLoadResult:
        try:
            build_result = self.second_zip_builder.build_request(archive_path)
        except SecondZipStagedImportError as exc:
            raise RealPlayerImportOpsError(str(exc)) from exc
        return RealPlayerImportSourceLoadResult(
            source_path=build_result.archive_path,
            request=build_result.request,
            manifest_hash=build_result.archive_sha256,
            provider_name=build_result.provider_name,
            source_metadata=build_result.metadata_json,
        )

    def _request_from_batch(
        self,
        batch: RealPlayerImportBatch,
        *,
        pending_only: bool = False,
    ) -> RealPlayerIngestionRequest:
        metadata = dict(batch.metadata_json or {})
        rows = sorted(batch.rows, key=lambda item: item.row_number)
        if pending_only:
            rows = [row for row in rows if not self._row_is_completed(row)]
        payload: dict[str, object] = {
            "mode": metadata.get("request_mode") or "curated_seed",
            "players": [
                dict(row.raw_payload_json or {})
                for row in rows
            ],
            "ingestion_batch_id": batch.batch_key,
            "ingestion_source_version": metadata.get("ingestion_source_version"),
            "as_of": metadata.get("as_of"),
        }
        if metadata.get("lookback_days") is not None:
            payload["lookback_days"] = metadata["lookback_days"]
        return RealPlayerIngestionRequest.model_validate(payload)

    def _load_batch(self, session: Session, *, batch_id: str, include_rows: bool) -> RealPlayerImportBatch:
        statement = select(RealPlayerImportBatch).where(RealPlayerImportBatch.id == batch_id)
        if include_rows:
            statement = statement.options(selectinload(RealPlayerImportBatch.rows))
        batch = session.scalar(statement)
        if batch is None:
            raise RealPlayerImportOpsError(f"Real-player import batch '{batch_id}' was not found.", status_code=404)
        return batch

    def _provider_name_from_request(self, request: RealPlayerIngestionRequest) -> str:
        providers = {player.source_name for player in request.players}
        if len(providers) == 1:
            return next(iter(providers))
        return "mixed-real-player-manifest"

    def _find_existing_batch(
        self,
        session: Session,
        *,
        batch_key: str,
        provider_name: str,
        source_type: str,
        manifest_hash: str,
    ) -> RealPlayerImportBatch | None:
        statement = (
            select(RealPlayerImportBatch)
            .options(selectinload(RealPlayerImportBatch.rows))
            .where(RealPlayerImportBatch.batch_key == batch_key)
        )
        existing = session.scalar(statement)
        if existing is not None:
            return existing

        statement = (
            select(RealPlayerImportBatch)
            .options(selectinload(RealPlayerImportBatch.rows))
            .where(
                RealPlayerImportBatch.provider_name == provider_name,
                RealPlayerImportBatch.source_type == source_type,
            )
            .order_by(RealPlayerImportBatch.requested_at.desc(), RealPlayerImportBatch.created_at.desc())
        )
        for candidate in session.scalars(statement):
            if self._manifest_hash_from_batch(candidate) == manifest_hash:
                return candidate
        return None

    @staticmethod
    def _default_batch_key(manifest_hash: str) -> str:
        return f"real-player-{manifest_hash[:16]}"

    def _metadata_payload(
        self,
        *,
        request: RealPlayerIngestionRequest,
        runner_mode: str,
        provider_name: str,
        provider_job_key: str | None,
        source_type: str,
        manifest_path: Path | None,
        manifest_hash: str,
        source_metadata: dict[str, object] | None,
        previous_metadata: dict[str, object] | None,
    ) -> dict[str, object]:
        previous = dict(previous_metadata or {})
        history = list(previous.get("attempt_history") or [])
        attempt_count = int(previous.get("attempt_count") or 0) + 1
        metadata = {
            "provider_name": provider_name,
            "provider_job_key": provider_job_key,
            "source_type": source_type,
            "runner_mode": runner_mode,
            "request_mode": request.mode,
            "ingestion_source_version": request.ingestion_source_version,
            "as_of": (request.as_of or datetime.now(UTC)).isoformat(),
            "lookback_days": request.lookback_days,
            "manifest_path": str(manifest_path) if manifest_path is not None else previous.get("manifest_path"),
            "manifest_sha256": manifest_hash or previous.get("manifest_sha256"),
            "attempt_count": attempt_count,
            "attempt_history": history,
        }
        for key, value in previous.items():
            if key.startswith("source_") and key not in metadata:
                metadata[key] = value
        if source_metadata:
            metadata.update(source_metadata)
        return metadata

    @staticmethod
    def _manifest_hash_from_batch(batch: RealPlayerImportBatch) -> str:
        return str((batch.metadata_json or {}).get("manifest_sha256") or "")

    @staticmethod
    def _manifest_path_from_batch(batch: RealPlayerImportBatch) -> Path | None:
        manifest_path = str((batch.metadata_json or {}).get("manifest_path") or "").strip()
        return Path(manifest_path) if manifest_path else None

    @staticmethod
    def _row_is_completed(row: RealPlayerImportRow) -> bool:
        return row.status in {
            RealPlayerImportRowStatus.IMPORTED.value,
            RealPlayerImportRowStatus.SKIPPED.value,
        }

    def _resume_state(self, rows: list[RealPlayerImportRow]) -> dict[str, object]:
        sorted_rows = sorted(rows, key=lambda item: item.row_number)
        completed_rows = [row for row in sorted_rows if self._row_is_completed(row)]
        pending_rows = [row for row in sorted_rows if not self._row_is_completed(row)]
        return {
            "preserved_completed_row_count": len(completed_rows),
            "pending_row_count": len(pending_rows),
            "resume_from_row_number": pending_rows[0].row_number if pending_rows else None,
            "last_successful_row_number": completed_rows[-1].row_number if completed_rows else None,
        }

    @staticmethod
    def _source_duplicate_skipped_count(metadata: dict[str, object] | None) -> int:
        return int((metadata or {}).get("source_duplicate_skipped_count") or 0)

    @staticmethod
    def _reset_row_for_retry(*, row: RealPlayerImportRow, runner_mode: str) -> None:
        row.status = RealPlayerImportRowStatus.PENDING.value
        row.match_action = None
        row.import_action = None
        row.identity_confidence_score = None
        row.gtex_player_id = None
        row.source_link_id = None
        row.real_player_profile_id = None
        row.authoritative_snapshot_id = None
        row.player_import_item_id = None
        row.processed_at = None
        row.validation_errors_json = []
        row.candidate_players_json = []
        row.audit_findings_json = []
        row.review_status = "pending"
        row.review_reason = None
        row.import_metadata_json = {"runner_mode": runner_mode}

    def _record_noop_attempt(
        self,
        session: Session,
        *,
        batch: RealPlayerImportBatch,
        actor_user_id: str | None,
        runner_mode: str,
        request: RealPlayerIngestionRequest,
        manifest_path: Path | None,
        manifest_hash: str,
        source_metadata: dict[str, object] | None,
        reason: str,
    ) -> None:
        rows = sorted(batch.rows, key=lambda item: item.row_number)
        resume_state = self._resume_state(rows)
        now = utcnow()
        metadata = self._metadata_payload(
            request=request,
            runner_mode=runner_mode,
            provider_name=batch.provider_name,
            provider_job_key=batch.provider_job_key,
            source_type=batch.source_type,
            manifest_path=manifest_path,
            manifest_hash=manifest_hash,
            source_metadata=source_metadata,
            previous_metadata=batch.metadata_json,
        )
        metadata.update(resume_state)
        source_duplicate_skipped_count = self._source_duplicate_skipped_count(metadata)
        source_row_count = int(metadata.get("source_row_count") or len(rows))
        source_eligible_row_count = int(metadata.get("source_eligible_row_count") or len(rows))
        source_filtered_row_count = int(metadata.get("source_filtered_row_count") or 0)
        batch.mode = runner_mode
        batch.status = RealPlayerImportBatchStatus.COMPLETED.value
        batch.requested_by_user_id = actor_user_id
        batch.requested_at = now
        batch.started_at = now
        batch.completed_at = now
        batch.submitted_row_count = len(rows)
        batch.normalized_row_count = len(rows)
        batch.matched_existing_count = sum(
            1
            for row in rows
            if row.match_action in {"source_link", "matched_existing"}
        )
        batch.created_player_count = sum(
            1
            for row in rows
            if row.status == RealPlayerImportRowStatus.IMPORTED.value and row.import_action == "created"
        )
        batch.updated_player_count = sum(
            1
            for row in rows
            if row.status == RealPlayerImportRowStatus.IMPORTED.value and row.import_action == "updated"
        )
        batch.skipped_row_count = source_duplicate_skipped_count + int(resume_state["preserved_completed_row_count"])
        batch.failed_row_count = sum(
            1
            for row in rows
            if row.status == RealPlayerImportRowStatus.FAILED.value
        )
        batch.authoritative_snapshot_count = sum(1 for row in rows if row.authoritative_snapshot_id)
        batch.error_message = None
        batch.summary_json = {
            "verdict": "pass",
            "runner_mode": runner_mode,
            "request_mode": request.mode,
            "ingestion_batch_id": batch.batch_key,
            "ambiguous_matches": 0,
            "missing_pricing_snapshots": 0,
            "hard_failures": 0,
            "preflight_row_count": 0,
            "execution_row_count": 0,
            "duplicate_finding_count": 0,
            "ambiguous_finding_count": 0,
            "pricing_finding_count": 0,
            "stability_finding_count": 0,
            "source_row_count": source_row_count,
            "source_eligible_row_count": source_eligible_row_count,
            "source_filtered_row_count": source_filtered_row_count,
            "duplicate_skipped_count": source_duplicate_skipped_count + int(resume_state["preserved_completed_row_count"]),
            "source_duplicate_skipped_count": source_duplicate_skipped_count,
            "pending_row_count": 0,
            "resume_from_row_number": None,
            "last_successful_row_number": resume_state["last_successful_row_number"],
            "batch_findings": [],
            "noop_reason": reason,
        }
        batch.metadata_json = self._record_attempt_outcome(
            metadata,
            mode=runner_mode,
            verdict="pass",
            status=RealPlayerImportBatchStatus.COMPLETED.value,
            error_message=None,
        )
        session.flush()

    @staticmethod
    def _record_attempt_outcome(
        metadata: dict[str, object] | None,
        *,
        mode: str,
        verdict: str,
        status: str,
        error_message: str | None,
    ) -> dict[str, object]:
        payload = dict(metadata or {})
        history = list(payload.get("attempt_history") or [])
        history.append(
            {
                "mode": mode,
                "verdict": verdict,
                "status": status,
                "completed_at": utcnow().isoformat(),
                "error_message": error_message,
            }
        )
        payload["attempt_history"] = history[-10:]
        payload["last_outcome"] = history[-1]
        return payload

    def _rows_for_finding(
        self,
        *,
        rows_by_source_key: dict[str, RealPlayerImportRow],
        rows: list[RealPlayerImportRow],
        finding: RealPlayerAuditFinding,
    ) -> list[RealPlayerImportRow]:
        matched_rows: list[RealPlayerImportRow] = []
        for source_key in finding.source_keys:
            row = rows_by_source_key.get(source_key)
            if row is not None and row not in matched_rows:
                matched_rows.append(row)
        if matched_rows:
            return matched_rows

        candidate_ids = set(finding.gtex_player_ids) | set(finding.candidate_ids)
        if candidate_ids:
            for row in rows:
                if row.gtex_player_id in candidate_ids and row not in matched_rows:
                    matched_rows.append(row)
        return matched_rows

    @staticmethod
    def _append_finding(row: RealPlayerImportRow, finding: RealPlayerAuditFinding) -> None:
        findings = list(row.audit_findings_json or [])
        payload = finding.to_dict()
        if payload not in findings:
            findings.append(payload)
        row.audit_findings_json = findings
        row.review_status = "needs_review"
        row.review_reason = row.review_reason or finding.finding_type
        row.status = RealPlayerImportRowStatus.FAILED.value

    @staticmethod
    def _batch_status_from_report(report: RealPlayerBatchRunReport) -> str:
        if report.verdict == "pass":
            return RealPlayerImportBatchStatus.COMPLETED.value
        if report.error_message and not any(
            (
                report.preflight_rows,
                report.execution_rows,
                report.duplicate_findings,
                report.ambiguous_findings,
                report.pricing_findings,
                report.stability_findings,
            )
        ):
            return RealPlayerImportBatchStatus.FAILED.value
        return RealPlayerImportBatchStatus.COMPLETED_WITH_ERRORS.value

    def _batch_status_from_rows(
        self,
        *,
        report: RealPlayerBatchRunReport,
        rows: list[RealPlayerImportRow],
        pending_row_count: int,
    ) -> str:
        if pending_row_count:
            imported_row_count = sum(
                1
                for row in rows
                if row.status == RealPlayerImportRowStatus.IMPORTED.value
            )
            failed_row_count = sum(
                1
                for row in rows
                if row.status == RealPlayerImportRowStatus.FAILED.value
            )
            if imported_row_count or failed_row_count:
                return RealPlayerImportBatchStatus.COMPLETED_WITH_ERRORS.value
            return RealPlayerImportBatchStatus.FAILED.value
        return self._batch_status_from_report(report)

    def _batch_summary_view(self, batch: RealPlayerImportBatch) -> RealPlayerImportBatchSummaryView:
        return RealPlayerImportBatchSummaryView(
            id=batch.id,
            batch_key=batch.batch_key,
            provider_name=batch.provider_name,
            provider_job_key=batch.provider_job_key,
            source_type=batch.source_type,
            mode=batch.mode,
            status=batch.status,
            requested_by_user_id=batch.requested_by_user_id,
            requested_at=batch.requested_at,
            started_at=batch.started_at,
            completed_at=batch.completed_at,
            submitted_row_count=batch.submitted_row_count,
            normalized_row_count=batch.normalized_row_count,
            matched_existing_count=batch.matched_existing_count,
            created_player_count=batch.created_player_count,
            updated_player_count=batch.updated_player_count,
            skipped_row_count=batch.skipped_row_count,
            failed_row_count=batch.failed_row_count,
            authoritative_snapshot_count=batch.authoritative_snapshot_count,
            metadata_json=dict(batch.metadata_json or {}),
            summary_json=dict(batch.summary_json or {}),
            error_message=batch.error_message,
        )

    def _batch_detail_view(
        self,
        batch: RealPlayerImportBatch,
        *,
        include_rows: bool,
    ) -> RealPlayerImportBatchDetailView:
        summary = self._batch_summary_view(batch)
        rows = []
        if include_rows:
            rows = [
                self._row_status_view(row)
                for row in sorted(batch.rows, key=lambda item: item.row_number)
            ]
        return RealPlayerImportBatchDetailView(**summary.model_dump(), rows=rows)

    @staticmethod
    def _row_status_view(row: RealPlayerImportRow) -> RealPlayerImportRowStatusView:
        return RealPlayerImportRowStatusView(
            id=row.id,
            row_number=row.row_number,
            source_name=row.source_name,
            source_player_key=row.source_player_key,
            canonical_name=row.canonical_name,
            status=row.status,
            match_action=row.match_action,
            import_action=row.import_action,
            identity_confidence_score=row.identity_confidence_score,
            gtex_player_id=row.gtex_player_id,
            authoritative_snapshot_id=row.authoritative_snapshot_id,
            processed_at=row.processed_at,
            review_status=row.review_status,
            review_reason=row.review_reason,
            validation_errors_json=list(row.validation_errors_json or []),
            candidate_players_json=list(row.candidate_players_json or []),
            audit_findings_json=list(row.audit_findings_json or []),
            normalized_payload_json=dict(row.normalized_payload_json or {}),
            import_metadata_json=dict(row.import_metadata_json or {}),
        )

    def _valuation_issue_views(
        self,
        *,
        batch: RealPlayerImportBatch,
        audit_findings: tuple[RealPlayerAuditFinding, ...],
    ) -> list[RealPlayerImportValuationIssueView]:
        rows_by_source_key = {
            f"{row.source_name}:{row.source_player_key}": row
            for row in batch.rows
        }
        issues: list[RealPlayerImportValuationIssueView] = []
        for finding in audit_findings:
            matched_rows = self._rows_for_finding(
                rows_by_source_key=rows_by_source_key,
                rows=list(batch.rows),
                finding=finding,
            )
            if not matched_rows:
                issues.append(
                    RealPlayerImportValuationIssueView(
                        source_name="batch",
                        source_player_key=batch.batch_key,
                        canonical_name="batch",
                        gtex_player_id=None,
                        pricing_snapshot_id=None,
                        issue_type=finding.finding_type,
                        required_action=finding.required_action,
                        details_json=dict(finding.details),
                    )
                )
                continue
            for row in matched_rows:
                issues.append(
                    RealPlayerImportValuationIssueView(
                        source_name=row.source_name,
                        source_player_key=row.source_player_key,
                        canonical_name=row.canonical_name,
                        gtex_player_id=row.gtex_player_id,
                        pricing_snapshot_id=row.authoritative_snapshot_id,
                        issue_type=finding.finding_type,
                        required_action=finding.required_action,
                        details_json=dict(finding.details),
                    )
                )
        return issues


__all__ = ["RealPlayerImportOpsError", "RealPlayerImportOpsService"]
