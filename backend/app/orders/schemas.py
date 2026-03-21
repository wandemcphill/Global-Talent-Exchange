from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.wallet import LedgerUnit
from backend.app.orders.models import OrderSide, OrderStatus


class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(
        title="OrderCreateRequest",
        json_schema_extra={
            "example": {
                "player_id": "player-123",
                "side": "buy",
                "quantity": "5.0000",
                "max_price": "12.5000",
            }
        },
    )

    player_id: str = Field(min_length=1, max_length=36)
    side: OrderSide
    quantity: Decimal
    max_price: Decimal | None = None

    @field_validator("player_id")
    @classmethod
    def validate_player_id(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("Player id is required.")
        return candidate

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Quantity must be positive.")
        return value

    @field_validator("max_price")
    @classmethod
    def validate_max_price(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("Max price must be positive.")
        return value


class OrderBookLevelView(BaseModel):
    model_config = ConfigDict(
        title="OrderBookLevelView",
        json_schema_extra={"example": {"price": "12.5000", "quantity": "8.0000", "order_count": 2}},
    )

    price: Decimal
    quantity: Decimal
    order_count: int


class OrderBookView(BaseModel):
    model_config = ConfigDict(
        title="OrderBookView",
        json_schema_extra={
            "example": {
                "player_id": "player-123",
                "bids": [{"price": "12.5000", "quantity": "8.0000", "order_count": 2}],
                "asks": [{"price": "13.0000", "quantity": "4.0000", "order_count": 1}],
                "generated_at": "2026-03-11T12:00:00Z",
            }
        },
    )

    player_id: str
    bids: list[OrderBookLevelView]
    asks: list[OrderBookLevelView]
    generated_at: datetime


class OrderExecutionView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="OrderExecutionView",
        json_schema_extra={
            "example": {
                "id": "exec-123",
                "buy_order_id": "ord-buy-123",
                "sell_order_id": "ord-sell-123",
                "maker_order_id": "ord-sell-123",
                "taker_order_id": "ord-buy-123",
                "quantity": "5.0000",
                "price": "5.0000",
                "notional": "25.0000",
                "created_at": "2026-03-11T12:00:00Z",
            }
        },
    )

    id: str
    buy_order_id: str
    sell_order_id: str
    maker_order_id: str
    taker_order_id: str
    quantity: Decimal
    price: Decimal
    notional: Decimal
    created_at: datetime


class OrderExecutionSummaryView(BaseModel):
    model_config = ConfigDict(
        title="OrderExecutionSummaryView",
        json_schema_extra={
            "example": {
                "execution_count": 1,
                "total_notional": "25.0000",
                "average_price": "5.0000",
                "last_executed_at": "2026-03-11T12:00:00Z",
                "executions": [
                    {
                        "id": "exec-123",
                        "buy_order_id": "ord-buy-123",
                        "sell_order_id": "ord-sell-123",
                        "maker_order_id": "ord-sell-123",
                        "taker_order_id": "ord-buy-123",
                        "quantity": "5.0000",
                        "price": "5.0000",
                        "notional": "25.0000",
                        "created_at": "2026-03-11T12:00:00Z",
                    }
                ],
            }
        },
    )

    execution_count: int
    total_notional: Decimal
    average_price: Decimal | None
    last_executed_at: datetime | None
    executions: list[OrderExecutionView]


class OrderView(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        title="OrderView",
        json_schema_extra={
            "example": {
                "id": "ord-123",
                "user_id": "user-123",
                "player_id": "player-123",
                "side": "buy",
                "quantity": "5.0000",
                "filled_quantity": "0.0000",
                "remaining_quantity": "5.0000",
                "max_price": "12.5000",
                "currency": "credit",
                "reserved_amount": "62.5000",
                "status": "open",
                "hold_transaction_id": "txn-123",
                "created_at": "2026-03-11T12:00:00Z",
                "updated_at": "2026-03-11T12:00:00Z",
                "execution_summary": {
                    "execution_count": 0,
                    "total_notional": "0.0000",
                    "average_price": None,
                    "last_executed_at": None,
                    "executions": [],
                },
            }
        },
    )

    id: str
    user_id: str
    player_id: str
    side: OrderSide
    quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    max_price: Decimal | None
    currency: LedgerUnit
    reserved_amount: Decimal
    status: OrderStatus
    hold_transaction_id: str | None
    created_at: datetime
    updated_at: datetime
    execution_summary: OrderExecutionSummaryView


class OrderAcceptedView(OrderView):
    model_config = ConfigDict(
        title="OrderAcceptedView",
        json_schema_extra=OrderView.model_config.get("json_schema_extra"),
    )


class OrderListView(BaseModel):
    model_config = ConfigDict(
        title="OrderListView",
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "ord-123",
                        "user_id": "user-123",
                        "player_id": "player-123",
                        "side": "buy",
                        "quantity": "5.0000",
                        "filled_quantity": "0.0000",
                        "remaining_quantity": "5.0000",
                        "max_price": "12.5000",
                        "currency": "credit",
                        "reserved_amount": "62.5000",
                        "status": "open",
                        "hold_transaction_id": "txn-123",
                        "created_at": "2026-03-11T12:00:00Z",
                        "updated_at": "2026-03-11T12:00:00Z",
                        "execution_summary": {
                            "execution_count": 0,
                            "total_notional": "0.0000",
                            "average_price": None,
                            "last_executed_at": None,
                            "executions": [],
                        },
                    }
                ],
                "limit": 20,
                "offset": 0,
                "total": 1,
            }
        },
    )

    items: list[OrderView]
    limit: int
    offset: int
    total: int


class AdminBuybackPreviewView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: str
    player_id: str
    eligible: bool
    reasons: list[str]
    message: str
    country: str | None
    fair_value: Decimal
    estimated_p2p_unit_price: Decimal
    estimated_p2p_total: Decimal
    admin_unit_price: Decimal
    admin_total: Decimal
    payout_ratio: Decimal
    liquidity_band: str
    payout_band: str
    p2p_priority_window_hours: int
    p2p_priority_window_ends_at: datetime | None
    minimum_hold_days: int
    minimum_hold_expires_at: datetime | None
    hold_days_remaining: int


class AdminBuybackExecutionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    preview: AdminBuybackPreviewView
    order: OrderView
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    executed_at: datetime
