from __future__ import annotations

# Both production automatic wallet top-up rails are supported. Provider readiness
# still depends on live credentials and webhook configuration at runtime.
SUPPORTED_TOP_UP_PROVIDER_KEYS: tuple[str, ...] = ("korapay", "paystack")
