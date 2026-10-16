from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RealPlayerImportBatchRunRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    manifest_path: str = Field(min_length=1)
    mode: Literal["dry-run", "write"] = "dry-run"
    provider_name: str | None = Field(default=None, min_length=2, max_length=64)
    provider_job_key: str | None = Field(default=None, min_length=1, max_length=128)
    source_type: str = Field(default="json_manifest", min_length=2, max_length=32)
    batch_key: str | None = Field(default=None, min_length=2, max_length=64)
    restart: bool = False


class RealPlayerImportBatchResumeRequest(BaseModel):
    mode: Literal["dry-run", "write"] | None = None


class RealPlayerImportBatchSummaryView(BaseModel):
    id: str
    batch_key: str
    provider_name: str
    provider_job_key: str | None = None
    source_type: str
    mode: str
    status: str
    requested_by_user_id: str | None = None
    requested_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    submitted_row_count: int
    normalized_row_count: int
    matched_existing_count: int
    created_player_count: int
    updated_player_count: int
    skipped_row_count: int
    failed_row_count: int
    authoritative_snapshot_count: int
    metadata_json: dict[str, object] = Field(default_factory=dict)
    summary_json: dict[str, object] = Field(default_factory=dict)
    error_message: str | None = None


class RealPlayerImportRowStatusView(BaseModel):
    id: str
    row_number: int
    source_name: str
    source_player_key: str
    canonical_name: str
    status: str
    match_action: str | None = None
    import_action: str | None = None
    identity_confidence_score: float | None = None
    gtex_player_id: str | None = None
    authoritative_snapshot_id: str | None = None
    processed_at: datetime | None = None
    review_status: str
    review_reason: str | None = None
    validation_errors_json: list[str] = Field(default_factory=list)
    candidate_players_json: list[dict[str, object]] = Field(default_factory=list)
    audit_findings_json: list[dict[str, object]] = Field(default_factory=list)
    normalized_payload_json: dict[str, object] = Field(default_factory=dict)
    import_metadata_json: dict[str, object] = Field(default_factory=dict)


class RealPlayerImportBatchDetailView(RealPlayerImportBatchSummaryView):
    rows: list[RealPlayerImportRowStatusView] = Field(default_factory=list)


class RealPlayerImportBatchIssueView(BaseModel):
    row_id: str
    row_number: int
    source_name: str
    source_player_key: str
    canonical_name: str
    row_status: str
    review_status: str
    review_reason: str | None = None
    issue_type: str
    required_action: str | None = None
    gtex_player_id: str | None = None
    validation_errors: list[str] = Field(default_factory=list)
    candidate_players: list[dict[str, object]] = Field(default_factory=list)
    details_json: dict[str, object] = Field(default_factory=dict)


class RealPlayerImportValuationIssueView(BaseModel):
    source_name: str
    source_player_key: str
    canonical_name: str
    gtex_player_id: str | None = None
    pricing_snapshot_id: str | None = None
    issue_type: str
    required_action: str | None = None
    details_json: dict[str, object] = Field(default_factory=dict)


class RealPlayerImportValuationStatusView(BaseModel):
    batch_id: str
    batch_key: str
    batch_status: str
    total_rows: int
    imported_row_count: int
    tracked_authoritative_snapshot_count: int
    tracked_missing_authoritative_snapshot_count: int
    persisted_target_player_count: int
    persisted_pricing_issue_count: int
    persisted_stability_issue_count: int
    audit_clean: bool | None = None
    issues: list[RealPlayerImportValuationIssueView] = Field(default_factory=list)


__all__ = [
    "RealPlayerImportBatchDetailView",
    "RealPlayerImportBatchIssueView",
    "RealPlayerImportBatchResumeRequest",
    "RealPlayerImportBatchRunRequest",
    "RealPlayerImportBatchSummaryView",
    "RealPlayerImportRowStatusView",
    "RealPlayerImportValuationIssueView",
    "RealPlayerImportValuationStatusView",
]
