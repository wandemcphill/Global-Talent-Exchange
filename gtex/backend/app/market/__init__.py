from __future__ import annotations

from importlib import import_module

__all__ = [
    "Listing",
    "ListingStatus",
    "ListingType",
    "MarketConflictError",
    "MarketEngine",
    "MarketError",
    "MarketNotFoundError",
    "MarketPermissionError",
    "MarketValidationError",
    "Offer",
    "OfferStatus",
    "TradeIntent",
    "TradeIntentDirection",
    "TradeIntentStatus",
]


def __getattr__(name: str):
    if name in {"Listing", "ListingStatus", "ListingType", "Offer", "OfferStatus", "TradeIntent", "TradeIntentDirection", "TradeIntentStatus"}:
        module = import_module("app.market.models")
        return getattr(module, name)
    if name in {"MarketConflictError", "MarketEngine", "MarketError", "MarketNotFoundError", "MarketPermissionError", "MarketValidationError"}:
        module = import_module("app.market.service")
        return getattr(module, name)
    raise AttributeError(name)
