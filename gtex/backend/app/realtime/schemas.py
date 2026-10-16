from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class RealtimeStatusView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_events: int
    channels: dict[str, int]
    last_event_name: str | None
    last_event_at: datetime | None
    active_wallet_connections: int = 0
    tracked_wallet_streams: int = 0
    active_match_connections: int = 0
    tracked_match_streams: int = 0
    delivered_messages: int = 0


class WalletRealtimeBalanceView(BaseModel):
    unit: str
    available_balance: Decimal
    reserved_balance: Decimal
    total_balance: Decimal


class WalletRealtimeLedgerEntryView(BaseModel):
    entry_id: str
    transaction_id: str
    account_code: str
    amount: Decimal
    unit: str
    reason: str
    source_tag: str
    reference: str | None
    created_at: datetime


class WalletRealtimeFraudCaseView(BaseModel):
    id: str
    case_key: str
    fraud_type: str
    severity: str
    status: str
    confidence_score: Decimal
    created_at: datetime


class WalletGatewaySnapshotView(BaseModel):
    user_id: str
    channel: str
    balances: list[WalletRealtimeBalanceView]
    recent_ledger: list[WalletRealtimeLedgerEntryView]
    risk_overview: dict[str, Any]
    recent_fraud_cases: list[WalletRealtimeFraudCaseView]
    websocket_connections: int
    delivered_messages: int


class WalletGatewayView(BaseModel):
    channel: str
    websocket_path: str
    snapshot: WalletGatewaySnapshotView


class MatchGatewaySnapshotView(BaseModel):
    match_id: str
    channel: str
    latest_cursor: int
    websocket_connections: int
    delivered_messages: int


class MatchGatewayView(BaseModel):
    channel: str
    websocket_path: str
    snapshot: MatchGatewaySnapshotView
