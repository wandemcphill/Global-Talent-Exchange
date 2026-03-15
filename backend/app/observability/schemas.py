from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MediaStorageSnapshot(BaseModel):
    storage_root: str
    highlight_temp_prefix: str
    highlight_archive_prefix: str
    highlight_export_prefix: str
    highlight_temp_ttl_hours: int
    highlight_archive_ttl_days: int
    download_expiry_minutes: int
    download_rate_limit_count: int
    download_rate_limit_window_minutes: int


class SponsorshipSnapshot(BaseModel):
    default_campaign: str
    surfaces: list[str]
    campaign_codes: list[str]


class PaymentMethodSnapshot(BaseModel):
    total_methods: int
    live_methods: int
    providers: list[str]


class ConfigSnapshotView(BaseModel):
    media_storage: MediaStorageSnapshot
    sponsorship: SponsorshipSnapshot
    payments: PaymentMethodSnapshot


class OpsJobResponse(BaseModel):
    result: dict[str, Any]


class AuditFeedItem(BaseModel):
    id: str
    actor_user_id: str | None
    actor_email: str | None = None
    action: str
    target_type: str
    target_id: str | None
    timestamp: datetime
    outcome: str
    detail: str
    metadata_summary: dict[str, Any]
