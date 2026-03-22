from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.ingestion.schemas import CursorRead, IngestionBaseModel, SyncExecutionSummary, SyncRunRead


class RealPlayerImportTriggerRequest(IngestionBaseModel):
    provider_name: str | None = None
    batch_size: int | None = Field(default=None, ge=1, le=1000)
    max_pages: int | None = Field(default=None, ge=1, le=1000)
    cursor_key: str | None = None
    restart: bool = False


class RealPlayerImportExecutionSummary(SyncExecutionSummary):
    cursor_key: str
    batch_size: int
    pages_processed: int = 0
    next_cursor: str | None = None
    exhausted: bool = False


class RealPlayerImportStatusRead(IngestionBaseModel):
    provider_name: str
    cursor_key: str
    staged_player_count: int = 0
    latest_seen_at: datetime | None = None
    latest_run: SyncRunRead | None = None
    cursor: CursorRead | None = None
    recent_runs: list[SyncRunRead] = Field(default_factory=list)
