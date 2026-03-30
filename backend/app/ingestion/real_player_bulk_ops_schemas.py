from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RealPlayerBulkImportRunReport(BaseModel):
    id: str
    provider_name: str
    source_type: str
    source_reference: str | None = None
    configured_batch_size: int
    total_rows_discovered: int
    processed_rows: int
    inserted_rows: int
    updated_rows: int
    duplicate_skipped_rows: int
    mapped_rows: int
    mapped_ready_rows: int
    mapped_partial_rows: int
    unresolved_rows: int
    publish_ready_rows: int
    published_rows: int
    failed_rows: int
    status: str
    resume_cursor: str | None = None
    last_successful_batch_marker: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    processing_state_distribution: dict[str, int] = Field(default_factory=dict)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RealPlayerBulkImportCommandResult(BaseModel):
    operation: Literal["import", "resume", "repair", "publish", "report"]
    run: RealPlayerBulkImportRunReport | None = None
    details_json: dict[str, object] = Field(default_factory=dict)


class RealPlayerBulkPublishJobTriggerRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    run_id: str = Field(min_length=1)
    batch_limit: int = Field(default=100, ge=1, le=500)
    priority_bucket: str = Field(default="all", min_length=1, max_length=32)
    max_batches: int = Field(default=100, ge=1, le=1000)
    stop_on_error: bool = False
    repair_before_publish: bool = False


class RealPlayerBulkPublishJobView(BaseModel):
    job_id: str
    run_id: str
    status: Literal["queued", "running", "completed", "completed_partial", "failed"]
    requested_by_user_id: str | None = None
    priority_bucket: str
    batch_limit: int
    max_batches: int
    stop_on_error: bool
    repair_before_publish: bool
    active: bool
    created_at: datetime
    started_at: datetime | None = None
    heartbeat_at: datetime | None = None
    completed_at: datetime | None = None
    last_error: str | None = None
    batches_attempted: int
    total_selected_rows: int
    total_published_rows: int
    total_excluded_rows: int
    total_validation_issue_count: int
    latest_write_batch_id: str | None = None
    last_result: RealPlayerBulkImportCommandResult | None = None
    last_run: RealPlayerBulkImportRunReport | None = None
    details_json: dict[str, object] = Field(default_factory=dict)


__all__ = [
    "RealPlayerBulkImportCommandResult",
    "RealPlayerBulkImportRunReport",
    "RealPlayerBulkPublishJobTriggerRequest",
    "RealPlayerBulkPublishJobView",
]
