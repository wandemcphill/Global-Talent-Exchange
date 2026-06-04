from __future__ import annotations

from dataclasses import dataclass

from app.wallets.providers.base import ProviderAdapter
from app.wallets.providers.korapay import KoraPayProviderAdapter


@dataclass(frozen=True, slots=True)
class ProviderRegistration:
    adapter: ProviderAdapter
    is_live: bool
    status: str


_REGISTRY: dict[str, ProviderRegistration] = {
    "korapay": ProviderRegistration(adapter=KoraPayProviderAdapter(), is_live=True, status="live"),
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
