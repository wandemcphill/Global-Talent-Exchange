from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping


@dataclass(frozen=True, slots=True)
class DeviceFingerprintResult:
    fingerprint: str
    source_signals: tuple[str, ...]


@dataclass(slots=True)
class DeviceFingerprintService:
    salt: str = "gtex-device"

    def build(
        self,
        *,
        headers: Mapping[str, str],
        explicit_device_id: str | None = None,
    ) -> DeviceFingerprintResult:
        normalized_headers = {str(key).lower(): str(value).strip() for key, value in headers.items()}
        source_signals: list[str] = []
        parts: list[str] = [self.salt]

        for header_name in (
            "x-device-id",
            "x-client-device-id",
            "x-installation-id",
            "cf-connecting-ip",
            "x-forwarded-for",
            "user-agent",
            "accept-language",
            "x-app-version",
            "host",
        ):
            header_value = normalized_headers.get(header_name)
            if not header_value:
                continue
            parts.append(f"{header_name}={header_value}")
            source_signals.append(header_name)

        if explicit_device_id:
            parts.append(f"explicit_device_id={explicit_device_id.strip()}")
            source_signals.append("explicit_device_id")

        if len(parts) == 1:
            parts.append("fallback=anonymous")
            source_signals.append("fallback")

        digest = sha256("|".join(parts).encode("utf-8")).hexdigest()
        return DeviceFingerprintResult(
            fingerprint=digest,
            source_signals=tuple(source_signals),
        )


__all__ = ["DeviceFingerprintResult", "DeviceFingerprintService"]
