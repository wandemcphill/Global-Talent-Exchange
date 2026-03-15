from __future__ import annotations

from backend.app.wallets.providers.apple_pay import ApplePayProviderAdapter
from backend.app.wallets.providers.base import ProviderAdapter
from backend.app.wallets.providers.cards import CardsProviderAdapter
from backend.app.wallets.providers.crypto_fiat import CryptoFiatProviderAdapter
from backend.app.wallets.providers.google_pay import GooglePayProviderAdapter
from backend.app.wallets.providers.regional_rails import RegionalRailsProviderAdapter


_REGISTRY: dict[str, ProviderAdapter] = {
    "cards": CardsProviderAdapter(),
    "apple_pay": ApplePayProviderAdapter(),
    "google_pay": GooglePayProviderAdapter(),
    "regional_rails": RegionalRailsProviderAdapter(),
    "crypto_fiat": CryptoFiatProviderAdapter(),
}


def get_provider_adapter(provider_key: str) -> ProviderAdapter:
    normalized = provider_key.strip().lower()
    adapter = _REGISTRY.get(normalized)
    if adapter is None:
        raise KeyError(f"Unknown payment provider '{provider_key}'.")
    return adapter


def list_provider_keys() -> list[str]:
    return sorted(_REGISTRY.keys())


__all__ = ["get_provider_adapter", "list_provider_keys"]
