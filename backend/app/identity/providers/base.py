from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class VerificationSessionResult:
    provider: str
    session_id: str
    reference: str
    handoff_url: str | None
    verification_type: str
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderWebhookResult:
    provider: str
    session_id: str | None
    reference: str
    decision: str  # "verified", "rejected", "requires_retry", "pending"
    verification_type: str
    verified_at: datetime
    checks: dict[str, Any] = field(default_factory=dict)
    rejection_reason: str | None = None
    evidence_fingerprint: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class BaseIdentityVerificationAdapter(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def initiate_session(
        self,
        *,
        user_id: str,
        reference: str,
        verification_type: str = "full_kyc",
        callback_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> VerificationSessionResult:
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        *,
        payload_bytes: bytes,
        headers: dict[str, str],
    ) -> bool:
        pass

    @abstractmethod
    def parse_webhook_payload(
        self,
        *,
        payload: dict[str, Any],
    ) -> ProviderWebhookResult:
        pass
