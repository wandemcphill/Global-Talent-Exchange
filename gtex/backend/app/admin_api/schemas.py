from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.admin_godmode.schemas import (
    CompetitionControlView,
    PaymentRailHealthView,
    PaymentRailView,
    TreasuryDashboardView,
    TreasurySummaryView,
    WithdrawalSummaryView,
)
from app.manager_market.schemas import CompetitionAdminView
from app.operations_readiness.schemas import OperationsReadinessQueue


class AdminPaymentRailsCanonicalView(BaseModel):
    rails: list[PaymentRailView]
    reason: str | None = None
    health: PaymentRailHealthView


class AdminTreasuryCanonicalView(BaseModel):
    summary: TreasurySummaryView
    dashboard: TreasuryDashboardView
    withdrawals: WithdrawalSummaryView


class AdminQueueJobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    queue_name: str
    job_name: str
    idempotency_key: str
    aggregate_id: str | None = None
    partition_key: str | None = None
    status: str
    published_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminQueuesCanonicalView(BaseModel):
    generated_at: datetime
    totals: dict[str, int | float]
    operations_queues: list[OperationsReadinessQueue]
    jobs: list[AdminQueueJobView]


class AdminSettlementLedgerEntryView(BaseModel):
    id: str
    transaction_id: str
    amount: Decimal
    unit: str
    reason: str
    transaction_type: str
    source_tag: str
    reference: str | None = None
    external_reference: str | None = None
    description: str | None = None
    created_at: datetime


class AdminSettlementsCanonicalView(BaseModel):
    order_status_counts: dict[str, int]
    ledger_reason_counts: dict[str, int]
    recent_entries: list[AdminSettlementLedgerEntryView]


class AdminCompetitionsCanonicalView(BaseModel):
    controls: CompetitionControlView
    manager_competitions: list[CompetitionAdminView]


__all__ = [
    "AdminCompetitionsCanonicalView",
    "AdminPaymentRailsCanonicalView",
    "AdminQueueJobView",
    "AdminQueuesCanonicalView",
    "AdminSettlementLedgerEntryView",
    "AdminSettlementsCanonicalView",
    "AdminTreasuryCanonicalView",
]
