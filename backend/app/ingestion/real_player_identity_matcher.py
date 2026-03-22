from __future__ import annotations

from .real_player_dedupe_service import (
    AmbiguousRealPlayerMatchError,
    RealPlayerDedupeService,
    RealPlayerMatchCandidate,
    RealPlayerMatchResult,
)


class RealPlayerIdentityMatcher(RealPlayerDedupeService):
    """Compatibility wrapper for existing imports."""


__all__ = [
    "AmbiguousRealPlayerMatchError",
    "RealPlayerIdentityMatcher",
    "RealPlayerMatchCandidate",
    "RealPlayerMatchResult",
]
