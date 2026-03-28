from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.viral.ingestion_schemas import ClipEvent
from app.viral.ingestion_schemas import ClipEventType
from app.viral.trust import TrustScoreService

_FAST_SKIP_THRESHOLD_MS = 1_000
_FULL_WATCH_THRESHOLD = 0.92
_FAST_SKIP_PENALTY = 0.3
_FULL_WATCH_BOOST = 0.4


@dataclass(slots=True)
class ClipEventWeightingMiddleware:
    trust_service: TrustScoreService

    def validate_and_weight(
        self,
        *,
        events: Sequence[ClipEvent],
        headers: Mapping[str, str],
        ip_address: str | None,
        session: Session,
    ) -> list[ClipEvent]:
        if not events:
            return []
        users = self._load_users(events=events, session=session)
        weighted_events: list[ClipEvent] = []
        for event in events:
            evaluation = self.trust_service.evaluate_event(
                event,
                headers=headers,
                ip_address=ip_address,
                user=users.get(event.user_id or ""),
            )
            weighted_events.append(
                event.model_copy(update={"trust": self._apply_reaction_weight(event=event, trust=evaluation.trust)})
            )
        return weighted_events

    @staticmethod
    def _load_users(*, events: Sequence[ClipEvent], session: Session) -> dict[str, User]:
        user_ids = sorted({event.user_id for event in events if event.user_id})
        if not user_ids:
            return {}
        stmt = select(User).where(User.id.in_(user_ids))
        return {item.id: item for item in session.scalars(stmt).all()}

    @staticmethod
    def _apply_reaction_weight(*, event: ClipEvent, trust) -> object:
        weighted_event_value = max(float(getattr(trust, "weighted_event_value", 0.0) or 0.0), 0.0)
        if event.event_type is ClipEventType.SCROLL and (event.watch_time_ms or 0) < _FAST_SKIP_THRESHOLD_MS:
            weighted_event_value += _FAST_SKIP_PENALTY
        if _is_full_watch(event):
            weighted_event_value += _FULL_WATCH_BOOST
        return trust.model_copy(update={"weighted_event_value": round(weighted_event_value, 6)})


def _is_full_watch(event: ClipEvent) -> bool:
    if event.event_type is ClipEventType.COMPLETE:
        return True
    if event.watch_time_ms is None or event.video_length_ms is None or event.video_length_ms <= 0:
        return False
    return (event.watch_time_ms / event.video_length_ms) >= _FULL_WATCH_THRESHOLD


__all__ = ["ClipEventWeightingMiddleware"]
