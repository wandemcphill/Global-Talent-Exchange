from __future__ import annotations

from backend.app.wallets.providers.base import GenericProviderAdapter


class CardsProviderAdapter(GenericProviderAdapter):
    def __init__(self) -> None:
        super().__init__(key="cards", display_name="Cards")


__all__ = ["CardsProviderAdapter"]
