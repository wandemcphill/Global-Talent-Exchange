from __future__ import annotations

from datetime import datetime, timezone
from threading import Event
import time

import pytest
from sqlalchemy.orm import sessionmaker

from app.ingestion.real_player_bulk_ops_schemas import (
    RealPlayerBulkImportCommandResult,
    RealPlayerBulkImportRunReport,
    RealPlayerBulkPublishJobTriggerRequest,
)
from app.ingestion.real_player_bulk_ops_service import RealPlayerBulkImportOpsError
from app.ingestion.real_player_bulk_publish_job_service import (
    RealPlayerBulkPublishJobError,
    RealPlayerBulkPublishJobRegistry,
)


def _run_report(*, publish_ready_rows: int, published_rows: int = 0, unresolved_rows: int = 0) -> RealPlayerBulkImportRunReport:
    now = datetime(2026, 3, 30, 12, 0, tzinfo=timezone.utc)
    return RealPlayerBulkImportRunReport(
        id="run-1",
        provider_name="sportmonks",
        source_type="provider_sync",
        source_reference="sportmonks:players",
        configured_batch_size=100,
        total_rows_discovered=500,
        processed_rows=500,
        inserted_rows=500,
        updated_rows=0,
        duplicate_skipped_rows=0,
        mapped_rows=publish_ready_rows + published_rows,
        mapped_ready_rows=publish_ready_rows,
        mapped_partial_rows=unresolved_rows,
        unresolved_rows=unresolved_rows,
        publish_ready_rows=publish_ready_rows,
        published_rows=published_rows,
        failed_rows=0,
        status="partial" if publish_ready_rows > 0 else "completed",
        resume_cursor=None,
        last_successful_batch_marker=None,
        started_at=now,
        completed_at=None,
        error_message=None,
        processing_state_distribution={},
        metadata_json={},
    )


def _publish_result(
    *,
    publish_ready_rows: int,
    published_rows: int,
    selected_rows: int,
    published_now: int,
    excluded_rows: int = 0,
    validation_issue_count: int = 0,
    write_batch_id: str | None = None,
) -> RealPlayerBulkImportCommandResult:
    details = {
        "selected_rows": selected_rows,
        "selected_source_keys": [f"sportmonks:player-{index}" for index in range(selected_rows)],
        "payload_build_errors": {},
        "validation_issue_count": validation_issue_count,
        "validation_issues": {},
        "would_publish_rows": selected_rows - excluded_rows,
        "excluded_rows": excluded_rows,
        "published_now": published_now,
        "published_batch_id": write_batch_id,
        "write_batch_id": write_batch_id,
    }
    return RealPlayerBulkImportCommandResult(
        operation="publish",
        run=_run_report(
            publish_ready_rows=publish_ready_rows,
            published_rows=published_rows,
        ),
        details_json=details,
    )


class _StubBulkOpsService:
    def __init__(self, results: list[RealPlayerBulkImportCommandResult]) -> None:
        self.results = list(results)
        self.publish_calls: list[tuple[str, int, str]] = []
        self.report_calls: list[str] = []

    def report_run(self, *, run_id: str) -> RealPlayerBulkImportCommandResult:
        self.report_calls.append(run_id)
        publish_ready_rows = self.results[0].run.publish_ready_rows if self.results else 0
        published_rows = 0 if not self.results else max((result.run.published_rows for result in self.results), default=0)
        return RealPlayerBulkImportCommandResult(
            operation="report",
            run=_run_report(
                publish_ready_rows=publish_ready_rows,
                published_rows=published_rows,
            ),
            details_json={},
        )

    def repair_mappings(self, *, run_id: str) -> RealPlayerBulkImportCommandResult:
        return RealPlayerBulkImportCommandResult(
            operation="repair",
            run=_run_report(publish_ready_rows=0),
            details_json={"run_id": run_id},
        )

    def publish_ready_players(self, *, run_id: str, limit: int, priority_bucket: str) -> RealPlayerBulkImportCommandResult:
        self.publish_calls.append((run_id, limit, priority_bucket))
        if self.results:
            return self.results.pop(0)
        raise RealPlayerBulkImportOpsError(
            f"No publish-ready rows matched run '{run_id}' and priority '{priority_bucket}'.",
            status_code=409,
        )


class _BlockingBulkOpsService(_StubBulkOpsService):
    def __init__(self, *, started: Event, release: Event) -> None:
        super().__init__(
            [
                _publish_result(
                    publish_ready_rows=0,
                    published_rows=10,
                    selected_rows=10,
                    published_now=10,
                    write_batch_id="batch-1",
                )
            ]
        )
        self.started = started
        self.release = release

    def publish_ready_players(self, *, run_id: str, limit: int, priority_bucket: str) -> RealPlayerBulkImportCommandResult:
        self.started.set()
        if not self.release.wait(timeout=5.0):
            raise AssertionError("Timed out waiting to release the blocked publish job.")
        return super().publish_ready_players(run_id=run_id, limit=limit, priority_bucket=priority_bucket)


class _StubPublishJobRegistry(RealPlayerBulkPublishJobRegistry):
    __slots__ = ("_stub_service",)

    def __init__(self, stub_service) -> None:
        super().__init__(session_factory=sessionmaker(), settings=None)  # type: ignore[arg-type]
        self._stub_service = stub_service

    def _new_service(self):
        return self._stub_service


def _wait_for_job_completion(
    registry: RealPlayerBulkPublishJobRegistry,
    job_id: str,
    *,
    timeout_seconds: float = 5.0,
):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job = registry.get_job(job_id=job_id)
        if not job.active and job.status in {"completed", "completed_partial", "failed"}:
            return job
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for publish job '{job_id}' to complete.")


def test_publish_job_registry_runs_batches_until_publish_ready_is_exhausted() -> None:
    registry = _StubPublishJobRegistry(
        _StubBulkOpsService(
            [
                _publish_result(
                    publish_ready_rows=100,
                    published_rows=100,
                    selected_rows=100,
                    published_now=100,
                    write_batch_id="batch-1",
                ),
                _publish_result(
                    publish_ready_rows=0,
                    published_rows=150,
                    selected_rows=50,
                    published_now=50,
                    write_batch_id="batch-2",
                ),
            ]
        )
    )

    queued = registry.start_job(
        actor_user_id="admin-1",
        payload=RealPlayerBulkPublishJobTriggerRequest(
            run_id="run-1",
            batch_limit=100,
            priority_bucket="all",
            max_batches=10,
        ),
    )
    completed = _wait_for_job_completion(registry, queued.job_id)

    assert completed.status == "completed"
    assert completed.batches_attempted == 2
    assert completed.total_selected_rows == 150
    assert completed.total_published_rows == 150
    assert completed.latest_write_batch_id == "batch-2"
    assert completed.last_run is not None
    assert completed.last_run.publish_ready_rows == 0
    assert completed.details_json["stop_reason"] == "publish_ready_exhausted"


def test_publish_job_registry_rejects_duplicate_active_run() -> None:
    started = Event()
    release = Event()
    registry = _StubPublishJobRegistry(
        _BlockingBulkOpsService(
            started=started,
            release=release,
        )
    )

    first = registry.start_job(
        actor_user_id="admin-1",
        payload=RealPlayerBulkPublishJobTriggerRequest(
            run_id="run-1",
            batch_limit=50,
            priority_bucket="all",
            max_batches=10,
        ),
    )
    assert started.wait(timeout=2.0)

    with pytest.raises(RealPlayerBulkPublishJobError) as exc_info:
        registry.start_job(
            actor_user_id="admin-2",
            payload=RealPlayerBulkPublishJobTriggerRequest(
                run_id="run-1",
                batch_limit=50,
                priority_bucket="all",
                max_batches=10,
            ),
        )

    assert exc_info.value.status_code == 409
    assert first.run_id in str(exc_info.value)

    release.set()
    completed = _wait_for_job_completion(registry, first.job_id)
    assert completed.status == "completed"
