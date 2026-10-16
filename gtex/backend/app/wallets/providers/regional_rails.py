from __future__ import annotations

from app.wallets.providers.base import GenericProviderAdapter


class RegionalRailsProviderAdapter(GenericProviderAdapter):
    def __init__(self) -> None:
        super().__init__(key="regional_rails", display_name="Regional Rails")


__all__ = ["RegionalRailsProviderAdapter"]
