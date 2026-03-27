from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.live_matches.schemas import MatchHighlightSummaryView
from app.match_engine.schemas import MatchReplayPayloadView
from app.models.highlight_event import HighlightEvent


@dataclass(frozen=True, slots=True)
class _HighlightSourceEvent:
    minute: int
    event_type: str
    team_name: str | None
    player_name: str | None
    description: str | None
    home_score: int
    away_score: int


class SmartHighlightService:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self.session_factory = session_factory

    def list_highlights(self, match_id: str, *, limit: int = 10) -> list[MatchHighlightSummaryView]:
        if self.session_factory is None:
            return []
        with self.session_factory() as session:
            rows = list(
                session.scalars(
                    select(HighlightEvent)
                    .where(HighlightEvent.match_id == match_id)
                    .order_by(HighlightEvent.importance_score.desc(), HighlightEvent.minute.desc(), HighlightEvent.created_at.asc())
                    .limit(limit)
                ).all()
            )
        return [
            MatchHighlightSummaryView(
                minute=row.minute,
                type=row.type,
                description=row.description,
            )
            for row in rows
        ]

    def persist_from_replay_payload(
        self,
        match_id: str,
        replay_payload: MatchReplayPayloadView,
        *,
        session: Session | None = None,
    ) -> list[MatchHighlightSummaryView]:
        source_events = [
            _HighlightSourceEvent(
                minute=event.minute,
                event_type=event.event_type.value,
                team_name=event.team_name,
                player_name=event.primary_player.player_name if event.primary_player is not None else None,
                description=event.commentary,
                home_score=event.home_score,
                away_score=event.away_score,
            )
            for event in replay_payload.timeline.events
        ]
        return self._replace_highlights(match_id, source_events, session=session)

    def persist_from_archive_timeline(
        self,
        match_id: str,
        timeline: Iterable[object],
        *,
        session: Session | None = None,
    ) -> list[MatchHighlightSummaryView]:
        source_events: list[_HighlightSourceEvent] = []
        for item in timeline:
            minute = getattr(item, "minute", None)
            event_type = getattr(item, "event_type", None)
            if not isinstance(minute, int) or not isinstance(event_type, str):
                continue
            source_events.append(
                _HighlightSourceEvent(
                    minute=minute,
                    event_type=event_type,
                    team_name=getattr(item, "club_name", None),
                    player_name=getattr(item, "player_name", None),
                    description=getattr(item, "description", None),
                    home_score=int(getattr(item, "home_score", 0) or 0),
                    away_score=int(getattr(item, "away_score", 0) or 0),
                )
            )
        return self._replace_highlights(match_id, source_events, session=session)

    def _replace_highlights(
        self,
        match_id: str,
        source_events: list[_HighlightSourceEvent],
        *,
        session: Session | None = None,
    ) -> list[MatchHighlightSummaryView]:
        highlights = self._detect_highlights(source_events)[:10]
        if session is not None:
            self._store_highlights(session, match_id, highlights)
        elif self.session_factory is not None:
            with self.session_factory() as managed_session:
                self._store_highlights(managed_session, match_id, highlights)
                managed_session.commit()
        return [
            MatchHighlightSummaryView(
                minute=minute,
                type=highlight_type,
                description=description,
            )
            for minute, highlight_type, _importance, description, _metadata in highlights
        ]

    @staticmethod
    def _store_highlights(
        session: Session,
        match_id: str,
        highlights: list[tuple[int, str, float, str, dict[str, object]]],
    ) -> None:
        session.execute(delete(HighlightEvent).where(HighlightEvent.match_id == match_id))
        for minute, highlight_type, importance, description, metadata in highlights:
            session.add(
                HighlightEvent(
                    match_id=match_id,
                    minute=minute,
                    type=highlight_type,
                    importance_score=importance,
                    description=description,
                    metadata_json=metadata,
                )
            )

    def _detect_highlights(
        self,
        source_events: list[_HighlightSourceEvent],
    ) -> list[tuple[int, str, float, str, dict[str, object]]]:
        detected: list[tuple[int, str, float, str, dict[str, object]]] = []
        previous_home = 0
        previous_away = 0
        for event in source_events:
            normalized = event.event_type.lower()
            if normalized in {"goal", "penalty_goal", "penalty_scored", "goals", "penalties"}:
                scored_side = None
                if event.home_score > previous_home:
                    scored_side = "home"
                elif event.away_score > previous_away:
                    scored_side = "away"
                importance = 1.0
                highlight_type = "goal"
                if event.minute > 85:
                    importance += 2.0
                    highlight_type = "last_minute_goal"
                if scored_side == "home" and previous_home < previous_away and event.home_score > event.away_score:
                    importance += 2.5
                    highlight_type = "comeback_moment"
                elif scored_side == "away" and previous_away < previous_home and event.away_score > event.home_score:
                    importance += 2.5
                    highlight_type = "comeback_moment"
                detected.append(
                    (
                        event.minute,
                        highlight_type,
                        importance,
                        self._goal_description(event, highlight_type=highlight_type),
                        {"team_name": event.team_name, "player_name": event.player_name},
                    )
                )
            elif normalized in {"red_card", "red_cards"}:
                detected.append(
                    (
                        event.minute,
                        "red_card",
                        1.5,
                        self._red_card_description(event),
                        {"team_name": event.team_name, "player_name": event.player_name},
                    )
                )
            elif normalized in {
                "missed_big_chance",
                "missed_chance",
                "missed_chances",
                "shot_on_target",
                "woodwork",
                "double_save",
            }:
                detected.append(
                    (
                        event.minute,
                        "big_chance",
                        0.9,
                        self._big_chance_description(event),
                        {"team_name": event.team_name, "player_name": event.player_name},
                    )
                )
            previous_home = event.home_score
            previous_away = event.away_score
        detected.sort(key=lambda item: (item[2], item[0]), reverse=True)
        return detected

    @staticmethod
    def _goal_description(event: _HighlightSourceEvent, *, highlight_type: str) -> str:
        player = event.player_name or "Unknown scorer"
        team = event.team_name or "Unknown team"
        prefix = f"{event.minute}' "
        if highlight_type == "comeback_moment":
            return f"{prefix}Comeback moment for {team} through {player}."
        if highlight_type == "last_minute_goal":
            return f"{prefix}Last-minute goal by {player} for {team}."
        return f"{prefix}Goal by {player} for {team}."

    @staticmethod
    def _red_card_description(event: _HighlightSourceEvent) -> str:
        player = event.player_name or "A player"
        team = event.team_name or "Unknown team"
        return f"{event.minute}' Red card for {player} of {team}."

    @staticmethod
    def _big_chance_description(event: _HighlightSourceEvent) -> str:
        team = event.team_name or "Unknown team"
        if event.description:
            return f"{event.minute}' Big chance for {team}: {event.description}"
        player = event.player_name or "Attacker"
        return f"{event.minute}' Big chance for {team} involving {player}."


__all__ = ["SmartHighlightService"]
