from __future__ import annotations

from app.wallets.providers.base import GenericProviderAdapter


class ApplePayProviderAdapter(GenericProviderAdapter):
    def __init__(self) -> None:
        super().__init__(key="apple_pay", display_name="Apple Pay")


__all__ = ["ApplePayProviderAdapter"]
