from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RealizedPLRowView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    player_id: str
    occurred_at: datetime
    quantity: Decimal
    execution_price: Decimal
    gross_proceeds: Decimal
    fee: Decimal
    cost_basis: Decimal
    realized_pl: Decimal
    transaction_id: str
    idempotency_reference: str | None = None


class RealizedPLView(BaseModel):
    model_config = ConfigDict(title="ApiRealizedPLView")

    total: Decimal
    available: bool
    rows: list[RealizedPLRowView]
    unavailable_reason: str | None = None
