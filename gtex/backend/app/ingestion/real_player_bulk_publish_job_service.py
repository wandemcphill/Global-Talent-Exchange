from __future__ import annotations

from dataclasses import dataclass, field
import logging
from threading import Lock, Thread

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.ingestion.real_player_bulk_ops_schemas import (
    RealPlayerBulkImportCommandResult,
    RealPlayerBulkImportRunReport,
    RealPlayerBulkPublishJobTriggerRequest,
    RealPlayerBulkPublishJobView,
)
from app.ingestion.real_player_bulk_ops_service import (
    RealPlayerBulkImportOpsError,
    RealPlayerBulkImportOpsService,
)
from app.models.base import generate_uuid, utcnow

logger = logging.getLogger(__name__)


class RealPlayerBulkPublishJobError(ValueError):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        self.status_code = status_code
        super().__init__(message)


@dataclass
class _RealPlayerBulkPublishJobState:
    job_id: str
    run_id: str
    requested_by_user_id: str | None
    priority_bucket: str
    batch_limit: int
    max_batches: int
    stop_on_error: bool
    repair_before_publish: bool
    created_at: object = field(default_factory=utcnow)
    started_at: object | None = None
    heartbeat_at: object | None = None
    completed_at: object | None = None
    status: str = "queued"
    active: bool = False
    last_error: str | None = None
    batches_attempted: int = 0
    total_selected_rows: int = 0
    total_published_rows: int = 0
    total_excluded_rows: int = 0
    total_validation_issue_count: int = 0
    latest_write_batch_id: str | None = None
    last_result: RealPlayerBulkImportCommandResult | None = None
    last_run: RealPlayerBulkImportRunReport | None = None
    details_json: dict[str, object] = field(default_factory=dict)
    worker_thread: Thread | None = None

    def to_view(self) -> RealPlayerBulkPublishJobView:
        return RealPlayerBulkPublishJobView(
            job_id=self.job_id,
            run_id=self.run_id,
            status=self.status,
            requested_by_user_id=self.requested_by_user_id,
            priority_bucket=self.priority_bucket,
            batch_limit=self.batch_limit,
            max_batches=self.max_batches,
            stop_on_error=self.stop_on_error,
            repair_before_publish=self.repair_before_publish,
            active=self.active,
            created_at=self.created_at,
            started_at=self.started_at,
            heartbeat_at=self.heartbeat_at,
            completed_at=self.completed_at,
            last_error=self.last_error,
            batches_attempted=self.batches_attempted,
            total_selected_rows=self.total_selected_rows,
            total_published_rows=self.total_published_rows,
            total_excluded_rows=self.total_excluded_rows,
            total_validation_issue_count=self.total_validation_issue_count,
            latest_write_batch_id=self.latest_write_batch_id,
            last_result=self.last_result,
            last_run=self.last_run,
            details_json=dict(self.details_json or {}),
        )


@dataclass(slots=True)
class RealPlayerBulkPublishJobRegistry:
    session_factory: sessionmaker[Session]
    settings: Settings = field(default_factory=get_settings)
    _lock: Lock = field(default_factory=Lock, init=False)
    _jobs: dict[str, _RealPlayerBulkPublishJobState] = field(default_factory=dict, init=False)
    _active_jobs_by_run: dict[str, str] = field(default_factory=dict, init=False)

    def start_job(
        self,
        *,
        actor_user_id: str | None,
        payload: RealPlayerBulkPublishJobTriggerRequest,
    ) -> RealPlayerBulkPublishJobView:
        report = self._new_service().report_run(run_id=payload.run_id)
        job_state = _RealPlayerBulkPublishJobState(
            job_id=generate_uuid(),
            run_id=payload.run_id,
            requested_by_user_id=actor_user_id,
            priority_bucket=payload.priority_bucket,
            batch_limit=payload.batch_limit,
            max_batches=payload.max_batches,
            stop_on_error=payload.stop_on_error,
            repair_before_publish=payload.repair_before_publish,
            last_result=report,
            last_run=report.run,
            details_json={
                "requested_at": utcnow().isoformat(),
                "initial_publish_ready_rows": report.run.publish_ready_rows if report.run is not None else None,
                "initial_unresolved_rows": report.run.unresolved_rows if report.run is not None else None,
            },
        )
        job_thread = Thread(
            target=self._run_job,
            kwargs={"job_id": job_state.job_id},
            name=f"gtex-real-player-publish-{job_state.job_id[:8]}",
            daemon=True,
        )
        job_state.worker_thread = job_thread

        with self._lock:
            active_job_id = self._active_jobs_by_run.get(payload.run_id)
            if active_job_id is not None:
                raise RealPlayerBulkPublishJobError(
                    f"Real-player publish job '{active_job_id}' is already active for run '{payload.run_id}'.",
                    status_code=409,
                )
            self._jobs[job_state.job_id] = job_state
            self._active_jobs_by_run[payload.run_id] = job_state.job_id

        logger.info(
            "ingestion.real_players.publish_job.queued job_id=%s run_id=%s batch_limit=%s max_batches=%s priority=%s",
            job_state.job_id,
            job_state.run_id,
            job_state.batch_limit,
            job_state.max_batches,
            job_state.priority_bucket,
        )
        job_thread.start()
        return job_state.to_view()

    def list_jobs(
        self,
        *,
        run_id: str | None = None,
        active_only: bool = False,
        limit: int = 20,
    ) -> list[RealPlayerBulkPublishJobView]:
        if limit < 1:
            raise RealPlayerBulkPublishJobError("limit must be greater than zero.")
        with self._lock:
            jobs = [
                job.to_view()
                for job in self._jobs.values()
                if (run_id is None or job.run_id == run_id) and (not active_only or job.active)
            ]
        jobs.sort(key=lambda item: item.created_at, reverse=True)
        return jobs[:limit]

    def get_job(self, *, job_id: str) -> RealPlayerBulkPublishJobView:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise RealPlayerBulkPublishJobError(
                    f"Real-player publish job '{job_id}' was not found.",
                    status_code=404,
                )
            return job.to_view()

    def shutdown(self, *, timeout: float = 1.0) -> None:
        with self._lock:
            threads = [job.worker_thread for job in self._jobs.values() if job.worker_thread is not None and job.worker_thread.is_alive()]
        for thread in threads:
            thread.join(timeout=timeout)

    def _run_job(self, *, job_id: str) -> None:
        try:
            self._mark_running(job_id)
            service = self._new_service()
            run_id, batch_limit, priority_bucket, max_batches, stop_on_error, repair_before_publish = self._job_config(job_id)
            if repair_before_publish:
                self._run_optional_repair(job_id=job_id, service=service, run_id=run_id)

            while True:
                current_view = self.get_job(job_id=job_id)
                if current_view.batches_attempted >= current_view.max_batches:
                    final_report = service.report_run(run_id=run_id)
                    completion_status = "completed_partial"
                    if final_report.run is not None and final_report.run.publish_ready_rows == 0:
                        completion_status = "completed"
                    self._complete_job(
                        job_id,
                        status=completion_status,
                        last_result=final_report,
                        last_run=final_report.run,
                        details_updates={
                            "stop_reason": "max_batches_reached",
                            "max_batches_reached": True,
                        },
                    )
                    return

                try:
                    result = service.publish_ready_players(
                        run_id=run_id,
                        limit=batch_limit,
                        priority_bucket=priority_bucket,
                    )
                except RealPlayerBulkImportOpsError as exc:
                    if exc.status_code == 409 and "No publish-ready rows matched" in str(exc):
                        final_report = service.report_run(run_id=run_id)
                        self._complete_job(
                            job_id,
                            status="completed",
                            last_result=final_report,
                            last_run=final_report.run,
                            details_updates={"stop_reason": "publish_ready_exhausted"},
                        )
                        return
                    raise

                should_stop = self._record_publish_result(
                    job_id=job_id,
                    result=result,
                    stop_on_error=stop_on_error,
                )
                if should_stop:
                    return
        except RealPlayerBulkPublishJobError:
            raise
        except Exception as exc:
            logger.exception("ingestion.real_players.publish_job.failed job_id=%s", job_id)
            self._fail_job(job_id, error_message=str(exc))

    def _run_optional_repair(
        self,
        *,
        job_id: str,
        service: RealPlayerBulkImportOpsService,
        run_id: str,
    ) -> None:
        try:
            repair_result = service.repair_mappings(run_id=run_id)
        except RealPlayerBulkImportOpsError as exc:
            if "No staged real-player rows matched" not in str(exc):
                raise
            repair_result = None
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.heartbeat_at = utcnow()
            details = dict(job.details_json or {})
            details["repair_before_publish"] = (
                repair_result.model_dump(mode="json")
                if repair_result is not None
                else {"status": "noop"}
            )
            if repair_result is not None:
                job.last_result = repair_result
                job.last_run = repair_result.run
            job.details_json = details

    def _record_publish_result(
        self,
        *,
        job_id: str,
        result: RealPlayerBulkImportCommandResult,
        stop_on_error: bool,
    ) -> bool:
        selected_rows = int(result.details_json.get("selected_rows") or 0)
        published_now = int(result.details_json.get("published_now") or 0)
        excluded_rows = int(result.details_json.get("excluded_rows") or 0)
        validation_issue_count = int(result.details_json.get("validation_issue_count") or 0)
        payload_build_error_count = len(dict(result.details_json.get("payload_build_errors") or {}))
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return True
            job.batches_attempted += 1
            job.total_selected_rows += selected_rows
            job.total_published_rows += published_now
            job.total_excluded_rows += excluded_rows
            job.total_validation_issue_count += validation_issue_count
            job.heartbeat_at = utcnow()
            job.last_result = result
            job.last_run = result.run
            latest_batch_id = result.details_json.get("write_batch_id") or result.details_json.get("published_batch_id")
            if isinstance(latest_batch_id, str) and latest_batch_id.strip():
                job.latest_write_batch_id = latest_batch_id
            details = dict(job.details_json or {})
            details["last_batch"] = result.details_json
            if result.run is not None:
                details["remaining_publish_ready_rows"] = result.run.publish_ready_rows
                details["remaining_unresolved_rows"] = result.run.unresolved_rows
                details["published_rows"] = result.run.published_rows
            job.details_json = details

        if result.run is not None and result.run.publish_ready_rows == 0:
            self._complete_job(
                job_id,
                status="completed",
                last_result=result,
                last_run=result.run,
                details_updates={"stop_reason": "publish_ready_exhausted"},
            )
            return True

        if stop_on_error and (excluded_rows > 0 or validation_issue_count > 0 or payload_build_error_count > 0):
            self._complete_job(
                job_id,
                status="completed_partial",
                last_result=result,
                last_run=result.run,
                details_updates={"stop_reason": "stop_on_error"},
            )
            return True

        if selected_rows > 0 and published_now == 0 and excluded_rows == 0:
            self._complete_job(
                job_id,
                status="completed_partial",
                last_result=result,
                last_run=result.run,
                details_updates={"stop_reason": "no_progress_detected"},
            )
            return True

        return False

    def _mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise RealPlayerBulkPublishJobError(
                    f"Real-player publish job '{job_id}' was not found.",
                    status_code=404,
                )
            now = utcnow()
            job.status = "running"
            job.active = True
            job.started_at = now
            job.heartbeat_at = now

    def _complete_job(
        self,
        job_id: str,
        *,
        status: str,
        last_result: RealPlayerBulkImportCommandResult | None,
        last_run: RealPlayerBulkImportRunReport | None,
        details_updates: dict[str, object] | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            job.active = False
            job.completed_at = utcnow()
            job.heartbeat_at = job.completed_at
            if last_result is not None:
                job.last_result = last_result
            if last_run is not None:
                job.last_run = last_run
            details = dict(job.details_json or {})
            details.update(details_updates or {})
            job.details_json = details
            active_job_id = self._active_jobs_by_run.get(job.run_id)
            if active_job_id == job.job_id:
                self._active_jobs_by_run.pop(job.run_id, None)
        logger.info(
            "ingestion.real_players.publish_job.completed job_id=%s status=%s",
            job_id,
            status,
        )

    def _fail_job(self, job_id: str, *, error_message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "failed"
            job.active = False
            job.last_error = error_message
            job.completed_at = utcnow()
            job.heartbeat_at = job.completed_at
            details = dict(job.details_json or {})
            details["stop_reason"] = "exception"
            job.details_json = details
            active_job_id = self._active_jobs_by_run.get(job.run_id)
            if active_job_id == job.job_id:
                self._active_jobs_by_run.pop(job.run_id, None)

    def _job_config(self, job_id: str) -> tuple[str, int, str, int, bool, bool]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise RealPlayerBulkPublishJobError(
                    f"Real-player publish job '{job_id}' was not found.",
                    status_code=404,
                )
            return (
                job.run_id,
                job.batch_limit,
                job.priority_bucket,
                job.max_batches,
                job.stop_on_error,
                job.repair_before_publish,
            )

    def _new_service(self) -> RealPlayerBulkImportOpsService:
        return RealPlayerBulkImportOpsService(
            session_factory=self.session_factory,
            settings=self.settings,
        )


__all__ = [
    "RealPlayerBulkPublishJobError",
    "RealPlayerBulkPublishJobRegistry",
]
