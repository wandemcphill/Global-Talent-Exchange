from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.ingestion.router as ingestion_router_module
from app.auth.dependencies import get_current_admin
from app.ingestion.real_player_bulk_ops_schemas import RealPlayerBulkPublishJobView
from app.ingestion.real_player_import_ops_schemas import (
    RealPlayerImportBatchDetailView,
    RealPlayerImportBatchIssueView,
)
from app.ingestion.router import (
    get_real_player_bulk_publish_job_registry,
    get_real_player_import_ops_service,
    router as ingestion_router,
)


class _StubRealPlayerImportOpsService:
    def __init__(self) -> None:
        now = datetime(2026, 3, 22, 12, 0, tzinfo=timezone.utc)
        self.batch = RealPlayerImportBatchDetailView(
            id="batch-1",
            batch_key="router-batch",
            provider_name="curated-feed",
            provider_job_key=None,
            source_type="json_manifest",
            mode="write",
            status="completed_with_errors",
            requested_by_user_id="admin-1",
            requested_at=now,
            started_at=now,
            completed_at=now,
            submitted_row_count=1,
            normalized_row_count=1,
            matched_existing_count=0,
            created_player_count=0,
            updated_player_count=0,
            skipped_row_count=0,
            failed_row_count=1,
            authoritative_snapshot_count=0,
            metadata_json={"manifest_path": "C:/tmp/router.json"},
            summary_json={"verdict": "fail"},
            error_message=None,
            rows=[],
        )
        self.issue = RealPlayerImportBatchIssueView(
            row_id="row-1",
            row_number=1,
            source_name="curated-feed",
            source_player_key="bassey-001",
            canonical_name="Calvin Bassey",
            row_status="failed",
            review_status="needs_review",
            review_reason="ambiguous_match",
            issue_type="ambiguous_match",
            required_action="Resolve the identity ambiguity before running the write batch.",
            gtex_player_id=None,
            validation_errors=[],
            candidate_players=[{"player_id": "candidate-1"}],
            details_json={"reason": "ambiguous_candidates"},
        )
        self.run_payload = None
        self.resume_payload = None
        self.resume_batch_id = None

    def run_batch(self, *, actor_user_id: str | None, payload):
        assert actor_user_id == "admin-1"
        self.run_payload = payload
        return self.batch

    def resume_batch(self, *, batch_id: str, actor_user_id: str | None, payload):
        assert actor_user_id == "admin-1"
        self.resume_batch_id = batch_id
        self.resume_payload = payload
        return self.batch

    def get_batch(self, batch_id: str, *, include_rows: bool = False):
        assert batch_id == "batch-1"
        assert include_rows is False
        return self.batch

    def list_unresolved_issues(self, *, batch_id: str, issue_type: str | None = None, unresolved_only: bool = True):
        assert batch_id == "batch-1"
        assert issue_type is None
        assert unresolved_only is True
        return [self.issue]

    def get_valuation_status(self, *, batch_id: str):
        raise AssertionError("valuation status is not part of this router smoke test")


class _StubRealPlayerBulkPublishJobRegistry:
    def __init__(self) -> None:
        now = datetime(2026, 3, 30, 14, 0, tzinfo=timezone.utc)
        self.job = RealPlayerBulkPublishJobView(
            job_id="job-1",
            run_id="run-1",
            status="running",
            requested_by_user_id="admin-1",
            priority_bucket="all",
            batch_limit=100,
            max_batches=100,
            stop_on_error=False,
            repair_before_publish=False,
            active=True,
            created_at=now,
            started_at=now,
            heartbeat_at=now,
            completed_at=None,
            last_error=None,
            batches_attempted=1,
            total_selected_rows=100,
            total_published_rows=100,
            total_excluded_rows=0,
            total_validation_issue_count=0,
            latest_write_batch_id="bulk-run-1-p1",
            last_result=None,
            last_run=None,
            details_json={"stop_reason": None},
        )
        self.start_payload = None

    def start_job(self, *, actor_user_id: str | None, payload):
        assert actor_user_id == "admin-1"
        self.start_payload = payload
        return self.job

    def list_jobs(self, *, run_id: str | None = None, active_only: bool = False, limit: int = 20):
        assert run_id in {None, "run-1"}
        assert active_only in {False, True}
        assert limit == 20
        return [self.job]

    def get_job(self, *, job_id: str):
        assert job_id == "job-1"
        return self.job


def test_admin_real_player_batch_routes_expose_run_resume_status_and_issue_endpoints(monkeypatch) -> None:
    service = _StubRealPlayerImportOpsService()
    publish_jobs = _StubRealPlayerBulkPublishJobRegistry()
    app = FastAPI()
    app.include_router(ingestion_router)
    app.dependency_overrides[get_current_admin] = lambda: SimpleNamespace(id="admin-1")
    app.dependency_overrides[get_real_player_import_ops_service] = lambda: service
    app.dependency_overrides[get_real_player_bulk_publish_job_registry] = lambda: publish_jobs
    monkeypatch.setattr(
        ingestion_router_module,
        "_require_manager_catalog_permission",
        lambda request, actor: None,
    )

    with TestClient(app) as client:
        run_response = client.post(
            "/internal/ingestion/real-players/batches",
            json={
                "manifest_path": "C:/tmp/router.json",
                "mode": "write",
            },
        )
        assert run_response.status_code == 202, run_response.text
        assert run_response.json()["batch_key"] == "router-batch"
        assert service.run_payload.mode == "write"

        resume_response = client.post(
            "/internal/ingestion/real-players/batches/batch-1/resume",
            json={"mode": "dry-run"},
        )
        assert resume_response.status_code == 200, resume_response.text
        assert service.resume_batch_id == "batch-1"
        assert service.resume_payload.mode == "dry-run"

        status_response = client.get("/internal/ingestion/real-players/batches/batch-1")
        assert status_response.status_code == 200, status_response.text
        assert status_response.json()["failed_row_count"] == 1

        issues_response = client.get("/internal/ingestion/real-players/batches/batch-1/issues")
        assert issues_response.status_code == 200, issues_response.text
        issues = issues_response.json()
        assert [item["issue_type"] for item in issues] == ["ambiguous_match"]

        publish_response = client.post(
            "/internal/ingestion/real-players/publish-jobs",
            json={"run_id": "run-1"},
        )
        assert publish_response.status_code == 202, publish_response.text
        assert publish_response.json()["job_id"] == "job-1"
        assert publish_jobs.start_payload.run_id == "run-1"

        publish_jobs_response = client.get("/internal/ingestion/real-players/publish-jobs")
        assert publish_jobs_response.status_code == 200, publish_jobs_response.text
        assert publish_jobs_response.json()[0]["job_id"] == "job-1"

        publish_job_response = client.get("/internal/ingestion/real-players/publish-jobs/job-1")
        assert publish_job_response.status_code == 200, publish_job_response.text
        assert publish_job_response.json()["latest_write_batch_id"] == "bulk-run-1-p1"
