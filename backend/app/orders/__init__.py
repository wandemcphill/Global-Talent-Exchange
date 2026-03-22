from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.orders.models import Order, OrderSide, OrderStatus
    from app.orders.service import OrderNotFoundError, OrderPlacementError, OrderService, PlayerNotFoundError

__all__ = [
    "Order",
    "OrderNotFoundError",
    "OrderPlacementError",
    "OrderService",
    "OrderSide",
    "OrderStatus",
    "PlayerNotFoundError",
]


def __getattr__(name: str):
    if name in {"Order", "OrderSide", "OrderStatus"}:
        from app.orders import models

        return getattr(models, name)
    if name in {"OrderNotFoundError", "OrderPlacementError", "OrderService", "PlayerNotFoundError"}:
        from app.orders import service

        return getattr(service, name)
    raise AttributeError(f"module 'app.orders' has no attribute {name!r}")
