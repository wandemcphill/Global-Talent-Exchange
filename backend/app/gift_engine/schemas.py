from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class GiftSendRequest(BaseModel):
    recipient_user_id: str = Field(min_length=1, max_length=36)
    gift_key: str = Field(min_length=2, max_length=64)
    quantity: Decimal = Field(default=Decimal('1.0000'), gt=0, le=1000)
    note: str | None = Field(default=None, max_length=500)


class GiftTransactionView(BaseModel):
    id: str
    sender_user_id: str
    recipient_user_id: str
    gift_key: str
    gift_display_name: str
    quantity: Decimal
    unit_price: Decimal
    gross_amount: Decimal
    platform_rake_amount: Decimal
    recipient_net_amount: Decimal
    ledger_unit: str
    ledger_transaction_id: str | None = None
    note: str | None = None
    status: str
    created_at: datetime


class GiftEngineSummaryView(BaseModel):
    sent_total: Decimal
    received_total: Decimal
    rake_total: Decimal
    recent_transactions: list[GiftTransactionView]


class GiftComboEventView(BaseModel):
    id: str
    gift_transaction_id: str
    sender_user_id: str
    recipient_user_id: str
    gift_key: str
    gift_display_name: str
    combo_rule_key: str
    combo_count: int
    window_seconds: int
    bonus_bps: int
    bonus_amount: Decimal
    created_at: datetime


class GiftComboSummaryView(BaseModel):
    total_combos: int
    total_bonus_amount: Decimal
    recent_combos: list[GiftComboEventView]
