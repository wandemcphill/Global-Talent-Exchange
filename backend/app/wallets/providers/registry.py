from __future__

from dataclasses import dataclass
import os

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


def get_provider_registration(provider_key: str) -> ProviderRegistration:
    normalized = provider_key.strip().lower()
    registration = _REGISTRY.get(normalized)
    if registration is None:
        raise KeyError(f"Unknown payment provider '{provider_key}'.")
    return registration


def list_provider_keys(*, live_only: bool = False) -> list[str]:
    keys = (key for key, registration in _REGISTRY.items() if not live_only or registration.is_live)
    return sorted(keys)


def list_provider_registrations(*, live_only: bool = False) -> dict[str, ProviderRegistration]:
    return {
        key: registration for key, registration in sorted(_REGISTRY.items()) if not live_only or registration.is_live
    }


def provider_secret_configured(provider_key: str) -> bool:
    normalized = provider_key.strip().lower()
    env_names = {
        "paystack": ("GTE_PAYSTACK_SECRET_KEY", "PAYSTACK_SECRET_KEY"),
        "korapay": (
            "GTE_KORAPAY_SECRET_KEY",
            "KORAPAY_SECRET_KEY",
            "GTE_KORAPAY_PRIVATE_KEY",
            "KORAPAY_PRIVATE_KEY",
        ),
    }.get(normalized, ())
    return any((os.getenv(name) or "").strip() for name in env_names)


def provider_webhook_secret_configured(provider_key: str) -> bool:
    normalized = provider_key.strip().lower()
    env_names = {
        "paystack": ("GTE_PAYSTACK_WEBHOOK_SECRET", "PAYSTACK_WEBHOOK_SECRET", "GTE_PAYSTACK_SECRET_KEY", "PAYSTACK_SECRET_KEY"),
        "korapay": (
            "GTE_KORAPAY_WEBHOOK_SECRET",
            "KORAPAY_WEBHOOK_SECRET",
            "GTE_KORAPAY_ENCRYPTION_KEY",
            "KORAPAY_ENCRYPTION_KEY",
        ),
    }.get(normalized, (f"GTE_{normalized.upper()}_WEBHOOK_SECRET",))
    return any((os.getenv(name) or "").strip() for name in env_names)


def provider_live_deposit_ready(provider_key: str) -> bool:
    normalized = provider_key.strip().lower()
    registration = get_provider_registration(normalized)
    if not registration.is_live:
        return False
    if normalized == "paystack":
        return provider_secret_configured(normalized) and provider_webhook_secret_configured(normalized)
    if normalized == "korapay":
        return provider_secret_configured(normalized) and provider_webhook_secret_configured(normalized)
    return provider_secret_configured(normalized)


def is_production_environment() -> bool:
    environment = (os.getenv("GTE_APP_ENV") or os.getenv("APP_ENV") or "development").strip().lower()
    return environment in {"production", "prod", "release"}


def paystack_enabled() -> bool:
    return provider_secret_configured("paystack")


def provider_runtime_status(
    provider_key: str,
    *,
    gateway_enabled: bool = True,
    enabled_providers: set[str] | None = None,
) -> str:
    normalized = provider_key.strip().lower()
    registration = get_provider_registration(normalized)
    if not registration.is_live:
        return registration.status
    if not gateway_enabled:
        return "blocked"
    if enabled_providers is not None and normalized not in {item.strip().lower() for item in enabled_providers}:
        return "blocked"
    if provider_live_deposit_ready(normalized):
        return "ready"
    return "unavailable"


def provider_runtime_statuses(
    *,
    gateway_enabled: bool = True,
    enabled_providers: set[str] | None = None,
    include_stubbed: bool = True,
) -> dict[str, str]:
    return {
        key: provider_runtime_status(
            key,
            gateway_enabled=gateway_enabled,
            enabled_providers=enabled_providers,
        )
        for key, registration in list_provider_registrations().items()
        if include_stubbed or registration.is_live
    }


__all__ = [
    "ProviderRegistration",
    "get_provider_adapter",
    "get_live_provider_adapter",
    "paystack_enabled",
    "get_provider_registration",
    "is_production_environment",
    "list_provider_keys",
    "list_provider_registrations",
    "provider_live_deposit_ready",
    "provider_runtime_status",
    "provider_runtime_statuses",
    "provider_secret_configured",
    "provider_webhook_secret_configured",
]
