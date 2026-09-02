"""Database-backed source of the matchday valuation overlay.

Kept separate from :mod:`app.value_engine.matchday_signal` so the signal maths stay
pure and independently testable, and separate from the job so the job keeps no
knowledge of how form is stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.players.form_service import PlayerFormService

from .matchday_signal import MatchdayValuationSignal, build_matchday_signal


@dataclass(slots=True)
class MatchdayValuationSignalProvider:
    """Resolves a player's bounded matchday signal, memoised per run.

    A snapshot run touches every player once, so a small cache avoids rebuilding a
    window that has already been computed within the same pass.
    """

    session: Session
    as_of: datetime | None = None
    _cache: dict[str, MatchdayValuationSignal] = field(default_factory=dict, init=False)

    def __call__(self, player_id: str) -> MatchdayValuationSignal | None:
        cached = self._cache.get(player_id)
        if cached is not None:
            return cached
        window = PlayerFormService(self.session).build_window(player_id, as_of=self.as_of)
        if not window.has_sample:
            # No GTEX competition football to speak of. Say nothing rather than
            # attaching a misleading "no effect" audit trail to every real player
            # who has simply never appeared in a GTEX competition.
            return None
        signal = build_matchday_signal(window)
        self._cache[player_id] = signal
        return signal


__all__ = ["MatchdayValuationSignalProvider"]
