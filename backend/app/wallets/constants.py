from __future__ import annotations

# KoraPay is the only supported automatic wallet top-up rail in production.
# Paystack is intentionally excluded so stale environment flags cannot expose it.
SUPPORTED_TOP_UP_PROVIDER_KEYS: tuple[str, ...] = ("korapay",)
