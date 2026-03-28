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


class AlertFeedItem(BaseModel):
    alert_id: str
    event_name: str
    severity: str
    alert_type: str
    title: str
    body: str
    user_id: str | None
    created_at: datetime
    metadata: dict[str, Any]


class AlertSnapshotView(BaseModel):
    total_alerts: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
    recent_alerts: list[AlertFeedItem]


class TransactionStreamDashboardView(BaseModel):
    kafka_enabled: bool
    outbox_relay_enabled: bool
    topic_prefix: str
    pending_outbox_events: int
    processed_outbox_events: int
    recent_transactions_24h: int
    recent_transactions_by_reason: dict[str, int]
    latest_transaction_at: datetime | None


class RealtimeOperationsView(BaseModel):
    total_events: int
    channels: dict[str, int]
    active_wallet_connections: int
    tracked_wallet_streams: int
    delivered_messages: int


class FraudMonitoringView(BaseModel):
    open_fraud_cases: int
    high_severity_open_fraud_cases: int
    critical_system_events: int
    recent_alert_counts: dict[str, int]


class MonitoringDashboardView(BaseModel):
    transaction_stream: TransactionStreamDashboardView
    realtime: RealtimeOperationsView
    fraud: FraudMonitoringView
    alerts: AlertSnapshotView
