from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from backend.app.models.wallet import LedgerUnit


class RewardSettlementRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    competition_key: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=160)
    gross_amount: Decimal = Field(gt=0)
    reward_source: str = Field(default='gtex_promotional_pool', min_length=2, max_length=64)
    note: str | None = Field(default=None, max_length=500)


class RewardSettlementView(BaseModel):
    id: str
    user_id: str
    competition_key: str
    reward_source: str
    title: str
    gross_amount: Decimal
    platform_fee_amount: Decimal
    net_amount: Decimal
    ledger_unit: str
    ledger_transaction_id: str | None = None
    status: str
    note: str | None = None
    created_at: datetime


class RewardEngineSummaryView(BaseModel):
    total_rewards: Decimal
    total_platform_fee: Decimal
    settlements: list[RewardSettlementView]


class PromoPoolCreditRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    unit: LedgerUnit = LedgerUnit.COIN
    reference: str | None = Field(default=None, max_length=64)
    note: str | None = Field(default=None, max_length=255)


class PromoPoolCreditView(BaseModel):
    transaction_id: str | None
    amount: Decimal
    unit: LedgerUnit
    reference: str
