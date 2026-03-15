from __future__ import annotations

from backend.app.wallets.providers.base import GenericProviderAdapter


class GooglePayProviderAdapter(GenericProviderAdapter):
    def __init__(self) -> None:
        super().__init__(key="google_pay", display_name="Google Pay")


__all__ = ["GooglePayProviderAdapter"]
