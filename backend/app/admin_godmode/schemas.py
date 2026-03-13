from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.models.wallet import PayoutStatus


class AdminAssignmentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_key: str = Field(min_length=1)
    role_name: str = Field(min_length=1)
    permissions: list[str] = Field(default_factory=list)
    is_enabled: bool = True
    notes: str | None = None


class AdminRoleCatalogView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    default_admin_role: str = "god_mode"
    available_roles: dict[str, list[str]] = Field(default_factory=dict)
    assignments: list[AdminAssignmentView] = Field(default_factory=list)


class AdminRoleCatalogUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_admin_role: str = "god_mode"
    available_roles: dict[str, list[str]] = Field(default_factory=dict)
    assignments: list[AdminAssignmentView] = Field(default_factory=list)


class CommissionSettingsView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    buy_commission_bps: int = Field(ge=0, le=5000)
    sell_commission_bps: int = Field(ge=0, le=5000)
    instant_sell_fee_bps: int = Field(ge=0, le=5000)
    withdrawal_fee_bps: int = Field(ge=0, le=5000)
    minimum_withdrawal_fee_credits: Decimal = Field(default=Decimal("0.0000"), ge=0)
    updated_at: datetime | None = None
    updated_by: str | None = None
    reason: str | None = None


class CommissionSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buy_commission_bps: int = Field(ge=0, le=5000)
    sell_commission_bps: int = Field(ge=0, le=5000)
    instant_sell_fee_bps: int = Field(ge=0, le=5000)
    withdrawal_fee_bps: int = Field(ge=0, le=5000)
    minimum_withdrawal_fee_credits: Decimal = Field(default=Decimal("0.0000"), ge=0)
    reason: str = Field(min_length=4, max_length=255)


class PaymentRailView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str = Field(min_length=1)
    deposits_enabled: bool = True
    withdrawals_enabled: bool = True
    is_live: bool = True
    maintenance_message: str | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None


class PaymentRailUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1)
    deposits_enabled: bool = True
    withdrawals_enabled: bool = True
    is_live: bool = True
    maintenance_message: str | None = Field(default=None, max_length=255)


class PaymentRailsPayload(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rails: list[PaymentRailView]
    reason: str | None = None


class PaymentRailsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rails: list[PaymentRailUpdate]
    reason: str = Field(min_length=4, max_length=255)


class CompetitionControlView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prize_pool_topup_pct: Decimal = Field(default=Decimal("0.00"), ge=0, le=500)
    updated_at: datetime | None = None
    updated_by: str | None = None
    reason: str | None = None


class CompetitionControlUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prize_pool_topup_pct: Decimal = Field(default=Decimal("0.00"), ge=0, le=500)
    reason: str = Field(min_length=4, max_length=255)


class WithdrawalControlView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    egame_withdrawals_enabled: bool = False
    trade_withdrawals_enabled: bool = True
    processor_mode: Literal["automatic_gateway", "manual_bank_transfer"] = "manual_bank_transfer"
    deposits_via_bank_transfer: bool = True
    payouts_via_bank_transfer: bool = True
    updated_at: datetime | None = None
    updated_by: str | None = None
    reason: str | None = None


class WithdrawalControlUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    egame_withdrawals_enabled: bool = False
    trade_withdrawals_enabled: bool = True
    processor_mode: Literal["automatic_gateway", "manual_bank_transfer"] = "manual_bank_transfer"
    deposits_via_bank_transfer: bool = True
    payouts_via_bank_transfer: bool = True
    reason: str = Field(min_length=4, max_length=255)


class TreasuryBalanceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    unit: str
    balance: Decimal


class LiquidityInventoryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: str
    balance: Decimal


class LiquidityInterventionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["buy_from_user", "sell_to_user"]
    user_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    quantity: Decimal = Field(gt=0)
    unit_price_credits: Decimal = Field(gt=0)
    reason: str = Field(min_length=4, max_length=255)
    confirmation_text: str = Field(min_length=8, max_length=64)


class LiquidityInterventionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_id: str
    action: str
    user_id: str
    player_id: str
    quantity: Decimal
    unit_price_credits: Decimal
    gross_total_credits: Decimal
    reference_price_credits: Decimal | None = None
    max_allowed_price_credits: Decimal | None = None
    min_allowed_price_credits: Decimal | None = None
    created_at: datetime
    created_by: str
    reason: str


class TreasurySummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    balances: list[TreasuryBalanceView]
    liquidity_inventory: list[LiquidityInventoryView]
    pending_payout_count: int
    processing_payout_count: int
    verified_payment_count: int
    recent_interventions: list[LiquidityInterventionView]


class WithdrawalAdminView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payout_request_id: str
    user_id: str
    username: str | None = None
    amount: Decimal
    fee_amount: Decimal = Field(default=Decimal("0.0000"), ge=0)
    total_debit: Decimal = Field(default=Decimal("0.0000"), ge=0)
    source_scope: Literal["trade", "competition"] = "trade"
    unit: str
    status: PayoutStatus
    destination_reference: str
    notes: str | None = None
    requested_at: datetime
    updated_at: datetime


class WithdrawalStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["reviewing", "held", "processing", "completed", "rejected", "failed"]
    notes: str | None = Field(default=None, max_length=255)


class TreasuryWithdrawalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: Literal["coin", "credit"]
    amount: Decimal = Field(gt=0)
    destination_reference: str = Field(min_length=4, max_length=255)
    reason: str = Field(min_length=4, max_length=255)
    confirmation_text: str = Field(min_length=8, max_length=64)


class TreasuryWithdrawalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    withdrawal_id: str
    unit: str
    amount: Decimal
    destination_reference: str
    reason: str
    created_at: datetime
    created_by: str


class AuditEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_type: str
    actor_user_id: str | None = None
    actor_email: str | None = None
    created_at: datetime
    summary: str
    payload: dict[str, object] = Field(default_factory=dict)


class GodModeProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subject_key: str
    role_name: str
    permissions: list[str]
    can_directly_set_price: bool = False
    can_edit_results: bool = False

    @model_validator(mode="after")
    def validate_integrity_bounds(self) -> "GodModeProfileView":
        if self.can_directly_set_price:
            raise ValueError("Direct price setting is forbidden in god mode.")
        if self.can_edit_results:
            raise ValueError("Competition result editing is forbidden in god mode.")
        return self


class WithdrawalSummaryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_requests: int = 0
    requested_count: int = 0
    reviewing_count: int = 0
    held_count: int = 0
    processing_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    rejected_count: int = 0
    queued_amount: Decimal = Field(default=Decimal("0.0000"), ge=0)
    immediate_eligible_amount: Decimal = Field(default=Decimal("0.0000"), ge=0)
    manager_trade_immediate_eligible_amount: Decimal = Field(default=Decimal("0.0000"), ge=0)


class PaymentRailHealthView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    live_count: int = 0
    deposits_enabled_count: int = 0
    withdrawals_enabled_count: int = 0
    paused_providers: list[str] = Field(default_factory=list)
    maintenance_providers: list[str] = Field(default_factory=list)


class TreasuryDashboardView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    platform_credit_balance: Decimal = Field(default=Decimal("0.0000"))
    platform_coin_balance: Decimal = Field(default=Decimal("0.0000"))
    treasury_withdrawal_sink_credit_balance: Decimal = Field(default=Decimal("0.0000"))
    treasury_withdrawal_sink_coin_balance: Decimal = Field(default=Decimal("0.0000"))
    manager_trade_volume_credits: Decimal = Field(default=Decimal("0.0000"))
    manager_trade_fee_revenue_credits: Decimal = Field(default=Decimal("0.0000"))
    immediate_withdrawable_manager_trade_credits: Decimal = Field(default=Decimal("0.0000"))
    open_manager_listing_count: int = 0
    settled_manager_trade_count: int = 0


class HighRiskActionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    action_key: str
    label: str
    required_permission: str
    requires_reason: bool = True
    requires_confirmation: bool = True
    integrity_note: str


class AuditQueryView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: str | None = None
    event_type: str | None = None
    available_event_types: list[str] = Field(default_factory=list)
    limit: int = 30


class GodModeBootstrapView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile: GodModeProfileView
    commissions: CommissionSettingsView
    payment_rails: list[PaymentRailView]
    withdrawal_controls: WithdrawalControlView = Field(default_factory=WithdrawalControlView)
    competition_controls: CompetitionControlView = Field(default_factory=CompetitionControlView)
    treasury: TreasurySummaryView
    withdrawals: list[WithdrawalAdminView]
    withdrawal_summary: WithdrawalSummaryView = Field(default_factory=WithdrawalSummaryView)
    payment_rail_health: PaymentRailHealthView = Field(default_factory=PaymentRailHealthView)
    treasury_dashboard: TreasuryDashboardView = Field(default_factory=TreasuryDashboardView)
    high_risk_actions: list[HighRiskActionView] = Field(default_factory=list)
    audit_query: AuditQueryView = Field(default_factory=AuditQueryView)
    audit_events: list[AuditEventView]
