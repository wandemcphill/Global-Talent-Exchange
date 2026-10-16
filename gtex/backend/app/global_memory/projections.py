from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.events import DomainEvent
from app.global_memory.constants import (
    COMPETITION_ADVANCED,
    DYNASTY_UPDATED,
    GLOBAL_MEMORY_PROJECTION,
    MATCH_COMPLETED,
    PLAYER_EVOLVED,
    REGEN_PROMOTED,
)
from app.global_memory.models import (
    GlobalProjectionCheckpoint,
    GlobalRegenEvolution,
    UserDynasty,
)


@dataclass(slots=True)
class GlobalMemoryProjectionService:
    session_factory: sessionmaker[Session]

    def handle_event(self, event: DomainEvent) -> None:
        if event.name not in {
            COMPETITION_ADVANCED,
            DYNASTY_UPDATED,
            MATCH_COMPLETED,
            PLAYER_EVOLVED,
            REGEN_PROMOTED,
        }:
            return
        with self.session_factory() as session:
            if self._already_processed(session, event.event_id):
                return
            if event.name == MATCH_COMPLETED:
                self._project_match_completed(session, payload=event.payload, event_id=event.event_id)
            elif event.name == DYNASTY_UPDATED:
                self._project_dynasty_updated(session, payload=event.payload, event_id=event.event_id)
            elif event.name in {PLAYER_EVOLVED, REGEN_PROMOTED}:
                self._project_player_progress(session, payload=event.payload, event_id=event.event_id)
            session.add(
                GlobalProjectionCheckpoint(
                    projection_name=GLOBAL_MEMORY_PROJECTION,
                    event_id=event.event_id,
                    event_name=event.name,
                    aggregate_id=event.aggregate_id,
                    payload_json=dict(event.payload or {}),
                )
            )
            session.commit()

    def _already_processed(self, session: Session, event_id: str) -> bool:
        return session.scalar(
            select(GlobalProjectionCheckpoint.id).where(
                GlobalProjectionCheckpoint.projection_name == GLOBAL_MEMORY_PROJECTION,
                GlobalProjectionCheckpoint.event_id == event_id,
            )
        ) is not None

    def _project_match_completed(self, session: Session, *, payload: dict[str, Any], event_id: str) -> None:
        winner_user_id = str(payload.get("winner_user_id") or "").strip()
        if not winner_user_id:
            return
        effective_pot = self._minor_amount(payload.get("effective_pot"))
        dynasty = self._ensure_dynasty(session, winner_user_id)
        dynasty.earnings_minor += effective_pot
        dynasty.last_event_id = event_id

    def _project_dynasty_updated(self, session: Session, *, payload: dict[str, Any], event_id: str) -> None:
        user_id = str(payload.get("user_id") or "").strip()
        if not user_id:
            return
        dynasty = self._ensure_dynasty(session, user_id)
        dynasty.last_event_id = event_id
        dynasty.player_development_score += float(payload.get("player_development_delta") or 0.0)
        dynasty.legacy_boost_score += float(payload.get("legacy_boost_delta") or 0.0)

    def _project_player_progress(self, session: Session, *, payload: dict[str, Any], event_id: str) -> None:
        player_id = str(payload.get("player_id") or "").strip()
        if not player_id:
            return
        evolution = session.scalar(
            select(GlobalRegenEvolution).where(GlobalRegenEvolution.player_id == player_id)
        )
        if evolution is None:
            return
        metadata = dict(evolution.metadata_json or {})
        metadata["last_event_id"] = event_id
        metadata["last_event_name"] = str(payload.get("event_name") or "")
        evolution.metadata_json = metadata
        if payload.get("scarcity_tier"):
            evolution.scarcity_tier = str(payload["scarcity_tier"])
        if payload.get("legacy_boost_score") is not None:
            evolution.legacy_boost_score = float(payload["legacy_boost_score"])
        if payload.get("unique_traits"):
            evolution.unique_traits_json = [str(item) for item in list(payload["unique_traits"])]

    def _ensure_dynasty(self, session: Session, user_id: str) -> UserDynasty:
        dynasty = session.scalar(select(UserDynasty).where(UserDynasty.user_id == user_id))
        if dynasty is not None:
            return dynasty
        dynasty = UserDynasty(user_id=user_id)
        session.add(dynasty)
        session.flush()
        return dynasty

    @staticmethod
    def _minor_amount(raw_amount: Any) -> int:
        try:
            return int((Decimal(str(raw_amount or "0")) * Decimal("10000")).quantize(Decimal("1")))
        except Exception:
            return 0


__all__ = ["GlobalMemoryProjectionService"]
