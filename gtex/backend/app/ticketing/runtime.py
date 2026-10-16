from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.match_engine.schemas import MatchCrowdStateView
from app.ticketing.service import TicketingError, TicketingService


@dataclass(slots=True)
class TicketingRuntime:
    app: FastAPI
    session_factory: sessionmaker[Session] | None = None

    def resolve_attendee_access_for_user_id(
        self,
        *,
        match_id: str,
        user_id: str,
        consume: bool = True,
    ) -> dict[str, Any] | None:
        if self.session_factory is None:
            return None
        with self.session_factory() as session:
            service = TicketingService(session, app=self.app)
            payload = service.resolve_attendee_access(match_id=match_id, user_id=user_id, consume=consume)
            session.commit()
            return payload

    def record_reaction(
        self,
        *,
        match_id: str,
        user_id: str,
        reaction_type: str,
        intensity: float = 1.0,
        source: str = "websocket",
    ) -> dict[str, Any] | None:
        if self.session_factory is None:
            return None
        with self.session_factory() as session:
            try:
                service = TicketingService(session, app=self.app)
                response = service.record_attendance_reaction_by_user_id(
                    user_id=user_id,
                    match_id=match_id,
                    reaction_type=reaction_type,
                    intensity=intensity,
                    source=source,
                )
                session.commit()
                return response.model_dump(mode="json") if response is not None else None
            except TicketingError:
                session.rollback()
                return None

    def crowd_overlay(
        self,
        match_id: str,
        base_crowd: MatchCrowdStateView | None,
    ) -> MatchCrowdStateView | None:
        if self.session_factory is None:
            return base_crowd
        with self.session_factory() as session:
            service = TicketingService(session, app=self.app)
            return service.build_crowd_overlay(match_id=match_id, base_crowd=base_crowd)


def bind_ticketing_runtime(app: FastAPI, _context) -> None:
    runtime = getattr(app.state, "ticketing_runtime", None)
    if runtime is None:
        runtime = TicketingRuntime(app=app, session_factory=getattr(app.state, "session_factory", None))
        app.state.ticketing_runtime = runtime
    else:
        runtime.session_factory = getattr(app.state, "session_factory", runtime.session_factory)
    app.state.stadium_ticket_crowd_overlay_provider = runtime.crowd_overlay
