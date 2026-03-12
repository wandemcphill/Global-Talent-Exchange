from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PortfolioHoldingView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="ApiPortfolioHoldingView",
        json_schema_extra={
            "example": {
                "player_id": "player-123",
                "quantity": "2.0000",
                "average_cost": "10.0000",
                "current_price": "12.0000",
                "market_value": "24.0000",
                "unrealized_pl": "4.0000",
                "unrealized_pl_percent": "20.0000",
            }
        },
    )

    player_id: str
    quantity: Decimal
    average_cost: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pl: Decimal
    unrealized_pl_percent: Decimal


class PortfolioView(BaseModel):
    model_config = ConfigDict(
        title="ApiPortfolioView",
        json_schema_extra={
            "example": {
                "holdings": [
                    {
                        "player_id": "player-123",
                        "quantity": "2.0000",
                        "average_cost": "10.0000",
                        "current_price": "12.0000",
                        "market_value": "24.0000",
                        "unrealized_pl": "4.0000",
                        "unrealized_pl_percent": "20.0000",
                    }
                ]
            }
        },
    )

    holdings: list[PortfolioHoldingView]


class PortfolioSummaryView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="ApiPortfolioSummaryView",
        json_schema_extra={
            "example": {
                "total_market_value": "24.0000",
                "cash_balance": "80.0000",
                "total_equity": "104.0000",
                "unrealized_pl_total": "4.0000",
                "realized_pl_total": "0.0000",
            }
        },
    )

    total_market_value: Decimal
    cash_balance: Decimal
    total_equity: Decimal
    unrealized_pl_total: Decimal
    realized_pl_total: Decimal
