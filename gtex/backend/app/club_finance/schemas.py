from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.club_finance.models import SponsorTier
from app.common.schemas.base import CommonSchema


class ClubFinanceTransactionView(CommonSchema):
    id: str
    transaction_type: str
    amount: Decimal
    reference_key: str
    metadata_json: dict[str, object]
    created_at: datetime


class ClubFinanceView(CommonSchema):
    id: str
    user_id: str
    balance: Decimal
    weekly_wages: Decimal
    sponsorship_income: Decimal
    match_income: Decimal
    broadcast_income: Decimal
    transfer_profit: Decimal
    expenses: Decimal
    transfers_blocked: bool
    forced_sale_required: bool
    forced_sale_player_id: str | None = None
    last_weekly_cycle_on: date | None = None
    recent_transactions: list[ClubFinanceTransactionView]
    created_at: datetime
    updated_at: datetime


class SponsorView(CommonSchema):
    id: str
    name: str
    tier: SponsorTier
    payout: Decimal
    requirements_json: dict[str, object]
    active: bool
    requirements_met: bool
    metrics_json: dict[str, object]
    created_at: datetime
    updated_at: datetime
