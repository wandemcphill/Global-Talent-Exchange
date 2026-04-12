from __future__ import annotations

from dataclasses import dataclass

from app.wallets.providers.apple_pay import ApplePayProviderAdapter
from app.wallets.providers.base import ProviderAdapter
from app.wallets.providers.cards import CardsProviderAdapter
from app.wallets.providers.crypto_fiat import CryptoFiatProviderAdapter
from app.wallets.providers.google_pay import GooglePayProviderAdapter
from app.wallets.providers.korapay import KoraPayProviderAdapter
from app.wallets.providers.paystack import PaystackProviderAdapter
from app.wallets.providers.regional_rails import RegionalRailsProviderAdapter


@dataclass(frozen=True, slots=True)
class ProviderRegistration:
    adapter: ProviderAdapter
    is_live: bool
    status: str


_REGISTRY: dict[str, ProviderRegistration] = {
    "cards": ProviderRegistration(adapter=CardsProviderAdapter(), is_live=False, status="stubbed"),
    "apple_pay": ProviderRegistration(adapter=ApplePayProviderAdapter(), is_live=False, status="stubbed"),
    "google_pay": ProviderRegistration(adapter=GooglePayProviderAdapter(), is_live=False, status="stubbed"),
    "korapay": ProviderRegistration(adapter=KoraPayProviderAdapter(), is_live=True, status="live"),
    "paystack": ProviderRegistration(adapter=PaystackProviderAdapter(), is_live=True, status="live"),
    "regional_rails": ProviderRegistration(adapter=RegionalRailsProviderAdapter(), is_live=False, status="stubbed"),
    "crypto_fiat": ProviderRegistration(adapter=CryptoFiatProviderAdapter(), is_live=False, status="stubbed"),
}


def get_provider_adapter(provider_key: str) -> ProviderAdapter:
    normalized = provider_key.strip().lower()
    registration = _REGISTRY.get(normalized)
    if registration is None:
        raise KeyError(f"Unknown payment provider '{provider_key}'.")
    return registration.adapter


def get_live_provider_adapter(provider_key: str) -> ProviderAdapter:
    normalized = provider_key.strip().lower()
    registration = _REGISTRY.get(normalized)
    if registration is None:
        raise KeyError(f"Unknown payment provider '{provider_key}'.")
    if not registration.is_live:
        raise KeyError(f"Payment provider '{provider_key}' is not currently available.")
    return registration.adapter


def list_provider_keys(*, live_only: bool = False) -> list[str]:
    keys = (key for key, registration in _REGISTRY.items() if not live_only or registration.is_live)
    return sorted(keys)


__all__ = ["ProviderRegistration", "get_provider_adapter", "get_live_provider_adapter", "list_provider_keys"]
