from __future__ import annotations

import os

from app.identity.providers.base import BaseIdentityVerificationAdapter
from app.identity.providers.didit import DIDitVerificationAdapter
from app.identity.providers.sandbox import SandboxVerificationAdapter
from app.identity.providers.smile_id import SmileIDVerificationAdapter

_PROVIDERS: dict[str, type[BaseIdentityVerificationAdapter]] = {
    "didit": DIDitVerificationAdapter,
    "smile_id": SmileIDVerificationAdapter,
    "smileid": SmileIDVerificationAdapter,
    "sandbox": SandboxVerificationAdapter,
}


def get_identity_provider(name: str | None = None) -> BaseIdentityVerificationAdapter:
    chosen = (name or os.environ.get("GTE_DEFAULT_IDENTITY_PROVIDER") or "didit").strip().lower()
    adapter_cls = _PROVIDERS.get(chosen)
    if adapter_cls is None:
        # Fallback to sandbox if requested or unknown in non-strict mode
        if "test" in os.environ.get("GTE_STARTUP_PROFILE", ""):
            return SandboxVerificationAdapter()
        return DIDitVerificationAdapter()
    return adapter_cls()
