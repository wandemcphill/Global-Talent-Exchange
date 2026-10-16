from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, load_settings
from app.core.database import create_database_engine
from app.ingestion.real_player_identity_audit import (
    RealPlayerAuditFinding,
    RealPlayerIdentityAuditReport,
    RealPlayerIdentityAuditService,
)
from app.ingestion.real_player_identity_matcher import AmbiguousRealPlayerMatchError, RealPlayerIdentityMatcher
from app.ingestion.real_player_ingestion_service import RealPlayerIngestionError, RealPlayerIngestionService, RealPlayerPricingError
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest


_PLAYER_ID_LIST_RE = re.compile(r"\[(.*)\]")


@dataclass(frozen=True, slots=True)
class RealPlayerBatchPreflightRow:
    source_name: str
    source_player_key: str
    canonical_name: str
    resolved_action: str
    gtex_player_id: str | None
    confidence_score: float
    audit_status: str
    candidate_ids: tuple[str, ...] = ()

    @property
    def source_key(self) -> str:
        return f"{self.source_name}:{self.source_player_key}"

    def to_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "source_player_key": self.source_player_key,
            "canonical_name": self.canonical_name,
            "resolved_action": self.resolved_action,
            "gtex_player_id": self.gtex_player_id,
            "confidence_score": self.confidence_score,
            "audit_status": self.audit_status,
            "candidate_ids": list(self.candidate_ids),
        }


@dataclass(frozen=True, slots=True)
class RealPlayerBatchExecutionRow:
    source_name: str
    source_player_key: str
    canonical_name: str
    resolved_action: str
    gtex_player_id: str | None
    confidence_score: float
    pricing_snapshot_id: str | None
    pricing_status: str
    audit_status: str
    commit_status: str

    @property
    def source_key(self) -> str:
        return f"{self.source_name}:{self.source_player_key}"

    def to_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "source_player_key": self.source_player_key,
            "canonical_name": self.canonical_name,
            "resolved_action": self.resolved_action,
            "gtex_player_id": self.gtex_player_id,
            "confidence_score": self.confidence_score,
            "pricing_snapshot_id": self.pricing_snapshot_id,
            "pricing_status": self.pricing_status,
            "audit_status": self.audit_status,
            "commit_status": self.commit_status,
        }


@dataclass(frozen=True, slots=True)
class RealPlayerBatchRunReport:
    runner_mode: str
    request_mode: str
    database_url: str
    batch_path: str
    ingestion_batch_id: str | None
    preflight_rows: tuple[RealPlayerBatchPreflightRow, ...]
    execution_rows: tuple[RealPlayerBatchExecutionRow, ...]
    duplicate_findings: tuple[RealPlayerAuditFinding, ...] = ()
    ambiguous_findings: tuple[RealPlayerAuditFinding, ...] = ()
    pricing_findings: tuple[RealPlayerAuditFinding, ...] = ()
    stability_findings: tuple[RealPlayerAuditFinding, ...] = ()
    error_message: str | None = None

    @property
    def ambiguous_matches(self) -> int:
        return len(self.ambiguous_findings)

    @property
    def missing_pricing_snapshots(self) -> int:
        return len(self.pricing_findings)

    @property
    def hard_failures(self) -> int:
        base = len(self.duplicate_findings) + len(self.ambiguous_findings) + len(self.pricing_findings) + len(self.stability_findings)
        return base if self.error_message is None else max(base, 1)

    @property
    def verdict(self) -> str:
        if self.ambiguous_matches or self.missing_pricing_snapshots or self.hard_failures:
            return "fail"
        return "pass"

    def to_dict(self) -> dict[str, object]:
        return {
            "runner_mode": self.runner_mode,
            "request_mode": self.request_mode,
            "database_url": self.database_url,
            "batch_path": self.batch_path,
            "ingestion_batch_id": self.ingestion_batch_id,
            "ambiguous_matches": self.ambiguous_matches,
            "missing_pricing_snapshots": self.missing_pricing_snapshots,
            "hard_failures": self.hard_failures,
            "verdict": self.verdict,
            "error_message": self.error_message,
            "preflight_rows": [row.to_dict() for row in self.preflight_rows],
            "execution_rows": [row.to_dict() for row in self.execution_rows],
            "duplicate_findings": [finding.to_dict() for finding in self.duplicate_findings],
            "ambiguous_findings": [finding.to_dict() for finding in self.ambiguous_findings],
            "pricing_findings": [finding.to_dict() for finding in self.pricing_findings],
            "stability_findings": [finding.to_dict() for finding in self.stability_findings],
        }


@dataclass(slots=True)
class RealPlayerBatchRunner:
    database_url: str
    batch_path: str | Path
    settings: Settings | None = None
    identity_matcher: RealPlayerIdentityMatcher = field(default_factory=RealPlayerIdentityMatcher)
    audit_service: RealPlayerIdentityAuditService = field(default_factory=RealPlayerIdentityAuditService)

    def load_request(self, *, mode: str) -> RealPlayerIngestionRequest:
        payload = json.loads(Path(self.batch_path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Real-player batch file must contain a JSON object.")
        request_payload = dict(payload)
        request_payload["mode"] = request_payload.get("mode") or "curated_seed"
        if mode == "write" and request_payload["mode"] == "dry_run":
            request_payload["mode"] = "curated_seed"
        if "as_of" not in request_payload:
            request_payload["as_of"] = datetime.now(UTC).isoformat()
        return RealPlayerIngestionRequest.model_validate(request_payload)

    def run(self, *, mode: str) -> RealPlayerBatchRunReport:
        request = self.load_request(mode=mode)
        resolved_settings = self.settings or load_settings(environ={**os.environ, "GTE_DATABASE_URL": self.database_url})
        engine = create_database_engine(self.database_url)
        default_session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        preflight_rows: list[RealPlayerBatchPreflightRow] = []

        if mode == "write":
            try:
                baseline = self._capture_baseline(default_session_factory)
                preflight_rows, duplicate_findings, ambiguous_findings = self._run_preflight(default_session_factory, request)
                if duplicate_findings or ambiguous_findings:
                    return RealPlayerBatchRunReport(
                        runner_mode=mode,
                        request_mode=request.mode,
                        database_url=self.database_url,
                        batch_path=str(Path(self.batch_path).resolve()),
                        ingestion_batch_id=request.ingestion_batch_id,
                        preflight_rows=tuple(preflight_rows),
                        execution_rows=(),
                        duplicate_findings=tuple(duplicate_findings),
                        ambiguous_findings=tuple(ambiguous_findings),
                    )

                service = RealPlayerIngestionService(
                    session_factory=default_session_factory,
                    settings=resolved_settings,
                )
                result = service.ingest(request)
                persisted_audit = self._run_persisted_audit(engine, ingestion_batch_id=result.ingestion_batch_id, baseline=baseline)
                committed_rows = self._build_execution_rows(
                    request=request,
                    result=result,
                    audit_report=persisted_audit,
                    commit_status="committed",
                )
                return RealPlayerBatchRunReport(
                    runner_mode=mode,
                    request_mode=request.mode,
                    database_url=self.database_url,
                    batch_path=str(Path(self.batch_path).resolve()),
                    ingestion_batch_id=result.ingestion_batch_id,
                    preflight_rows=tuple(preflight_rows),
                    execution_rows=committed_rows,
                    duplicate_findings=persisted_audit.duplicate_findings,
                    ambiguous_findings=persisted_audit.ambiguous_findings,
                    pricing_findings=persisted_audit.pricing_findings,
                    stability_findings=persisted_audit.stability_findings,
                )
            except AmbiguousRealPlayerMatchError as exc:
                return RealPlayerBatchRunReport(
                    runner_mode=mode,
                    request_mode=request.mode,
                    database_url=self.database_url,
                    batch_path=str(Path(self.batch_path).resolve()),
                    ingestion_batch_id=request.ingestion_batch_id,
                    preflight_rows=tuple(preflight_rows),
                    execution_rows=(),
                    ambiguous_findings=(
                        RealPlayerAuditFinding(
                            finding_type="ambiguous_match",
                            normalized_key=exc.canonical_name,
                            candidate_ids=tuple(candidate.player_id for candidate in exc.candidates),
                            required_action="Resolve the identity ambiguity before running the write batch.",
                            details={"reason": exc.reason},
                        ),
                    ),
                    error_message=str(exc),
                )
            except RealPlayerPricingError as exc:
                return RealPlayerBatchRunReport(
                    runner_mode=mode,
                    request_mode=request.mode,
                    database_url=self.database_url,
                    batch_path=str(Path(self.batch_path).resolve()),
                    ingestion_batch_id=request.ingestion_batch_id,
                    preflight_rows=tuple(preflight_rows),
                    execution_rows=(),
                    pricing_findings=self._pricing_findings_from_error(exc),
                    error_message=str(exc),
                )
            except RealPlayerIngestionError as exc:
                return RealPlayerBatchRunReport(
                    runner_mode=mode,
                    request_mode=request.mode,
                    database_url=self.database_url,
                    batch_path=str(Path(self.batch_path).resolve()),
                    ingestion_batch_id=request.ingestion_batch_id,
                    preflight_rows=tuple(preflight_rows),
                    execution_rows=(),
                    error_message=str(exc),
                )
            except Exception as exc:
                return RealPlayerBatchRunReport(
                    runner_mode=mode,
                    request_mode=request.mode,
                    database_url=self.database_url,
                    batch_path=str(Path(self.batch_path).resolve()),
                    ingestion_batch_id=request.ingestion_batch_id,
                    preflight_rows=tuple(preflight_rows),
                    execution_rows=(),
                    error_message=str(exc),
                )
            finally:
                engine.dispose()

        connection = engine.connect()
        outer_transaction = connection.begin()
        bound_session_factory = sessionmaker(
            bind=connection,
            autoflush=False,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            baseline = self._capture_baseline(bound_session_factory)
            preflight_rows, duplicate_findings, ambiguous_findings = self._run_preflight(bound_session_factory, request)
            if duplicate_findings or ambiguous_findings:
                outer_transaction.rollback()
                return RealPlayerBatchRunReport(
                    runner_mode=mode,
                    request_mode=request.mode,
                    database_url=self.database_url,
                    batch_path=str(Path(self.batch_path).resolve()),
                    ingestion_batch_id=request.ingestion_batch_id,
                    preflight_rows=tuple(preflight_rows),
                    execution_rows=(),
                    duplicate_findings=tuple(duplicate_findings),
                    ambiguous_findings=tuple(ambiguous_findings),
                )

            service = RealPlayerIngestionService(
                session_factory=bound_session_factory,
                settings=resolved_settings,
            )
            result = service.ingest(request)
            audit_report = self._run_batch_audit(
                bound_session_factory,
                ingestion_batch_id=result.ingestion_batch_id,
                baseline=baseline,
            )
            execution_rows = self._build_execution_rows(
                request=request,
                result=result,
                audit_report=audit_report,
                commit_status="rolled_back",
            )
            outer_transaction.rollback()
            return RealPlayerBatchRunReport(
                runner_mode=mode,
                request_mode=request.mode,
                database_url=self.database_url,
                batch_path=str(Path(self.batch_path).resolve()),
                ingestion_batch_id=result.ingestion_batch_id,
                preflight_rows=tuple(preflight_rows),
                execution_rows=execution_rows,
                duplicate_findings=audit_report.duplicate_findings,
                ambiguous_findings=audit_report.ambiguous_findings,
                pricing_findings=audit_report.pricing_findings,
                stability_findings=audit_report.stability_findings,
            )
        except AmbiguousRealPlayerMatchError as exc:
            if outer_transaction.is_active:
                outer_transaction.rollback()
            return RealPlayerBatchRunReport(
                runner_mode=mode,
                request_mode=request.mode,
                database_url=self.database_url,
                batch_path=str(Path(self.batch_path).resolve()),
                ingestion_batch_id=request.ingestion_batch_id,
                preflight_rows=tuple(preflight_rows),
                execution_rows=(),
                ambiguous_findings=(
                    RealPlayerAuditFinding(
                        finding_type="ambiguous_match",
                        normalized_key=exc.canonical_name,
                        candidate_ids=tuple(candidate.player_id for candidate in exc.candidates),
                        required_action="Resolve the identity ambiguity before running the write batch.",
                        details={"reason": exc.reason},
                    ),
                ),
                error_message=str(exc),
            )
        except RealPlayerPricingError as exc:
            if outer_transaction.is_active:
                outer_transaction.rollback()
            return RealPlayerBatchRunReport(
                runner_mode=mode,
                request_mode=request.mode,
                database_url=self.database_url,
                batch_path=str(Path(self.batch_path).resolve()),
                ingestion_batch_id=request.ingestion_batch_id,
                preflight_rows=tuple(preflight_rows),
                execution_rows=(),
                pricing_findings=self._pricing_findings_from_error(exc),
                error_message=str(exc),
            )
        except RealPlayerIngestionError as exc:
            if outer_transaction.is_active:
                outer_transaction.rollback()
            return RealPlayerBatchRunReport(
                runner_mode=mode,
                request_mode=request.mode,
                database_url=self.database_url,
                batch_path=str(Path(self.batch_path).resolve()),
                ingestion_batch_id=request.ingestion_batch_id,
                preflight_rows=tuple(preflight_rows),
                execution_rows=(),
                error_message=str(exc),
            )
        except Exception as exc:
            if outer_transaction.is_active:
                outer_transaction.rollback()
            return RealPlayerBatchRunReport(
                runner_mode=mode,
                request_mode=request.mode,
                database_url=self.database_url,
                batch_path=str(Path(self.batch_path).resolve()),
                ingestion_batch_id=request.ingestion_batch_id,
                preflight_rows=tuple(preflight_rows),
                execution_rows=(),
                error_message=str(exc),
            )
        finally:
            connection.close()
            engine.dispose()

    def _capture_baseline(self, session_factory: sessionmaker[Session]):
        with session_factory() as session:
            return self.audit_service.capture_surface_baseline(session)

    def _run_preflight(
        self,
        session_factory: sessionmaker[Session],
        request: RealPlayerIngestionRequest,
    ) -> tuple[list[RealPlayerBatchPreflightRow], tuple[RealPlayerAuditFinding, ...], tuple[RealPlayerAuditFinding, ...]]:
        duplicate_findings = self.audit_service.detect_payload_collisions(request.players)
        preflight_rows: list[RealPlayerBatchPreflightRow] = []
        ambiguous_findings: list[RealPlayerAuditFinding] = []
        with session_factory() as session:
            for payload in sorted(request.players, key=lambda item: (item.source_name, item.source_player_key)):
                try:
                    match = self.identity_matcher.match(session, payload)
                    preflight_rows.append(
                        RealPlayerBatchPreflightRow(
                            source_name=payload.source_name,
                            source_player_key=payload.source_player_key,
                            canonical_name=payload.canonical_name,
                            resolved_action=match.action,
                            gtex_player_id=match.player_id,
                            confidence_score=match.confidence_score,
                            audit_status="pass",
                            candidate_ids=tuple(candidate.player_id for candidate in match.candidates),
                        )
                    )
                except AmbiguousRealPlayerMatchError as exc:
                    ambiguous_findings.append(
                        RealPlayerAuditFinding(
                            finding_type="ambiguous_match",
                            normalized_key=f"{payload.source_name}:{payload.source_player_key}",
                            source_keys=(f"{payload.source_name}:{payload.source_player_key}",),
                            candidate_ids=tuple(candidate.player_id for candidate in exc.candidates),
                            required_action="Resolve the identity ambiguity before running the write batch.",
                            details={"reason": exc.reason, "canonical_name": payload.canonical_name},
                        )
                    )
                    preflight_rows.append(
                        RealPlayerBatchPreflightRow(
                            source_name=payload.source_name,
                            source_player_key=payload.source_player_key,
                            canonical_name=payload.canonical_name,
                            resolved_action="ambiguous",
                            gtex_player_id=None,
                            confidence_score=0.0,
                            audit_status="fail",
                            candidate_ids=tuple(candidate.player_id for candidate in exc.candidates),
                        )
                    )
        return preflight_rows, duplicate_findings, tuple(ambiguous_findings)

    def _run_batch_audit(self, session_factory: sessionmaker[Session], *, ingestion_batch_id: str, baseline) -> RealPlayerIdentityAuditReport:
        with session_factory() as session:
            return self.audit_service.audit_batch(
                session,
                ingestion_batch_id=ingestion_batch_id,
                baseline=baseline,
            )

    def _run_persisted_audit(self, engine: Engine, *, ingestion_batch_id: str, baseline) -> RealPlayerIdentityAuditReport:
        session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        with session_factory() as session:
            return self.audit_service.audit_batch(
                session,
                ingestion_batch_id=ingestion_batch_id,
                baseline=baseline,
            )

    def _build_execution_rows(
        self,
        *,
        request: RealPlayerIngestionRequest,
        result,
        audit_report: RealPlayerIdentityAuditReport,
        commit_status: str,
    ) -> tuple[RealPlayerBatchExecutionRow, ...]:
        names_by_source_key = {
            f"{player.source_name}:{player.source_player_key}": player.canonical_name
            for player in request.players
        }
        failing_source_keys = {
            source_key
            for finding in (*audit_report.duplicate_findings, *audit_report.pricing_findings)
            for source_key in finding.source_keys
        }
        rows = []
        for item in result.results:
            source_key = f"{item.source_name}:{item.source_player_key}"
            rows.append(
                RealPlayerBatchExecutionRow(
                    source_name=item.source_name,
                    source_player_key=item.source_player_key,
                    canonical_name=names_by_source_key[source_key],
                    resolved_action=item.action,
                    gtex_player_id=item.gtex_player_id,
                    confidence_score=item.identity_confidence_score,
                    pricing_snapshot_id=item.pricing_snapshot_id,
                    pricing_status="present" if item.pricing_snapshot_id else "missing",
                    audit_status="fail" if source_key in failing_source_keys else "pass",
                    commit_status=commit_status,
                )
            )
        return tuple(rows)

    def _pricing_findings_from_error(self, exc: RealPlayerPricingError) -> tuple[RealPlayerAuditFinding, ...]:
        message = str(exc)
        match = _PLAYER_ID_LIST_RE.search(message)
        candidate_ids: tuple[str, ...] = ()
        if match is not None and match.group(1).strip():
            candidate_ids = tuple(token.strip().strip("'\"") for token in match.group(1).split(",") if token.strip())
        return (
            RealPlayerAuditFinding(
                finding_type="missing_authoritative_pricing",
                normalized_key="authoritative_pricing",
                candidate_ids=candidate_ids,
                required_action="Fix the authoritative pricing snapshot gap before running the write batch.",
            ),
        )


__all__ = [
    "RealPlayerBatchExecutionRow",
    "RealPlayerBatchPreflightRow",
    "RealPlayerBatchRunReport",
    "RealPlayerBatchRunner",
]
