from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


__all__ = [
    "RealPlayerBulkImportCommandResult",
    "RealPlayerBulkImportRunReport",
]
