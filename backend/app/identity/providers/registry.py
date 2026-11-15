from __future__ import annotations

import os

from app.identity.providers.base import BaseIdentityVerificationAdapter
from app.identity.providers.didit import DIDitVerificationAdapter, IdentityProviderConfigurationError
from app.identity.providers.sandbox import SandboxVerificationAdapter


def get_identity_provider(name: str | None = None) -> BaseIdentityVerificationAdapter:
    """Return the explicitly configured provider without silently downgrading to a fake provider.

    DIDit is the only live integration. Sandbox is available only in test/dev or
    when explicitly enabled for a controlled non-production environment.
    Smile ID must not be advertised as available until its real API and webhook
    verification implementations have been added.
    """
    chosen = (name or os.environ.get("GTE_DEFAULT_IDENTITY_PROVIDER") or "didit").strip().lower()
    startup_profile = os.environ.get("GTE_STARTUP_PROFILE", "").strip().lower()
    sandbox_allowed = (
        startup_profile in {"test", "testing", "development", "dev"}
        or os.environ.get("GTE_KYC_ALLOW_SANDBOX", "").strip().lower() in {"1", "true", "yes"}
    )

    if chosen in {"sandbox", "test"}:
        if not sandbox_allowed:
            raise IdentityProviderConfigurationError(
                "The sandbox identity provider is disabled outside test/development. "
                "Configure DIDit for production KYC."
            )
        return SandboxVerificationAdapter()
    if chosen in {"didit", "did.it"}:
        return DIDitVerificationAdapter()
    if chosen in {"smile_id", "smileid", "smile-id"}:
        raise IdentityProviderConfigurationError(
            "Smile ID has not been connected to its live API. Select DIDit for production verification."
        )
    raise IdentityProviderConfigurationError(
        f"Unsupported identity verification provider '{chosen}'. Configure GTE_DEFAULT_IDENTITY_PROVIDER as didit."
    )
