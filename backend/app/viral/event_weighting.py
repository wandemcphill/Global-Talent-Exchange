from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.viral.ingestion_schemas import ClipEvent
from app.viral.trust import TrustScoreService


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
            weighted_events.append(event.model_copy(update={"trust": evaluation.trust}))
        return weighted_events

    @staticmethod
    def _load_users(*, events: Sequence[ClipEvent], session: Session) -> dict[str, User]:
        user_ids = sorted({event.user_id for event in events if event.user_id})
        if not user_ids:
            return {}
        stmt = select(User).where(User.id.in_(user_ids))
        return {item.id: item for item in session.scalars(stmt).all()}


__all__ = ["ClipEventWeightingMiddleware"]
