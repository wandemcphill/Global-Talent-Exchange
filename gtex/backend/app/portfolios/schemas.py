from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PortfolioBalanceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: str
    code: str
    unit: str
    balance: Decimal


class PortfolioView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    balances: list[PortfolioBalanceView]
    positions: list[dict]
