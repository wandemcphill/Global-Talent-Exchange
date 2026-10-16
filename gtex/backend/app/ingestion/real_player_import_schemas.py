from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.ingestion.schemas import CursorRead, IngestionBaseModel, SyncExecutionSummary, SyncRunRead


class RealPlayerImportTriggerRequest(IngestionBaseModel):
    provider_name: str | None = None
    batch_size: int | None = Field(default=None, ge=1, le=5000)
    max_pages: int | None = Field(default=None, ge=1, le=1000)
    cursor_key: str | None = None
    restart: bool = False


class RealPlayerImportExecutionSummary(SyncExecutionSummary):
    import_run_id: str | None = None
    cursor_key: str
    batch_size: int
    pages_processed: int = 0
    next_cursor: str | None = None
    exhausted: bool = False


class RealPlayerBulkImportExecutionSummary(IngestionBaseModel):
    run_id: str | None = None
    import_run_id: str | None = None
    provider_name: str
    job_name: str
    entity_type: str
    status: str
    duration_ms: int = 0
    processed_count: int = 0
    records_seen: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    duplicate_skipped_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    cursor_value: str | None = None
    error_message: str | None = None
    cursor_key: str
    batch_size: int
    batches_processed: int = 0
    next_cursor: str | None = None
    exhausted: bool = False
    dry_run: bool = False
    source_path: str
    source_format: str
    source_fingerprint: str


class RealPlayerImportStatusRead(IngestionBaseModel):
    provider_name: str
    cursor_key: str
    staged_player_count: int = 0
    latest_seen_at: datetime | None = None
    latest_run: SyncRunRead | None = None
    cursor: CursorRead | None = None
    recent_runs: list[SyncRunRead] = Field(default_factory=list)
