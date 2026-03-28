from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.user import User
from app.viral.trust import TrustScoreService, TrustState, build_trust_score_service

SYSTEM_TRUST_ZERO_THRESHOLD = 0.30


@dataclass(frozen=True, slots=True)
class TrustDecision:
    user_id: str | None
    trust_score: float
    weight: float
    blocked: bool
    shadow_banned: bool
    monetization_eligible: bool
    ranking_eligible: bool
    suspicious_flags: tuple[str, ...]
    state: TrustState | None = None


@dataclass(slots=True)
class SharedTrustMiddleware:
    session: Session
    trust_service: TrustScoreService | None = None
    zero_threshold: float = SYSTEM_TRUST_ZERO_THRESHOLD

    def __post_init__(self) -> None:
        if self.trust_service is None:
            self.trust_service = build_trust_score_service()

    def decision_for_user(self, user: User | None) -> TrustDecision:
        if user is None:
            return TrustDecision(
                user_id=None,
                trust_score=1.0,
                weight=1.0,
                blocked=False,
                shadow_banned=False,
                monetization_eligible=True,
                ranking_eligible=True,
                suspicious_flags=(),
                state=None,
            )
        state = self.trust_service.get_user_trust(user=user)
        weight = 0.0 if float(state.trust_score) < float(self.zero_threshold) else 1.0
        return TrustDecision(
            user_id=user.id,
            trust_score=round(float(state.trust_score), 4),
            weight=weight,
            blocked=weight <= 0.0,
            shadow_banned=bool(state.shadow_banned),
            monetization_eligible=bool(state.monetization_eligible),
            ranking_eligible=bool(state.ranking_eligible),
            suspicious_flags=tuple(state.suspicious_flags),
            state=state,
        )

    def decision_for_user_id(self, user_id: str | None) -> TrustDecision:
        resolved_user_id = str(user_id or "").strip()
        if not resolved_user_id:
            return self.decision_for_user(None)
        try:
            user = self.session.get(User, resolved_user_id)
        except Exception:
            user = None
        if not isinstance(user, User):
            return self.decision_for_user(None)
        return self.decision_for_user(user)


__all__ = [
    "SYSTEM_TRUST_ZERO_THRESHOLD",
    "SharedTrustMiddleware",
    "TrustDecision",
]
