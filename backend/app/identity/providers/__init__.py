from __future__ import annotations

from app.identity.providers.base import (
    BaseIdentityVerificationAdapter,
    ProviderWebhookResult,
    VerificationSessionResult,
)
from app.identity.providers.didit import DIDitVerificationAdapter
from app.identity.providers.registry import get_identity_provider
from app.identity.providers.sandbox import SandboxVerificationAdapter
from app.identity.providers.smile_id import SmileIDVerificationAdapter

__all__ = [
    "BaseIdentityVerificationAdapter",
    "DIDitVerificationAdapter",
    "ProviderWebhookResult",
    "SandboxVerificationAdapter",
    "SmileIDVerificationAdapter",
    "VerificationSessionResult",
    "get_identity_provider",
]
