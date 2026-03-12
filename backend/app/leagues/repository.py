from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime
from threading import RLock
from typing import Protocol

from sqlalchemy import DateTime, JSON, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from backend.app.competitions.models.league_events import LeagueSeasonEvent
from backend.app.competitions.models.league_events import (
    LeagueClubOptOutEvent,
    LeagueFixtureCompletedEvent,
    LeaguePlayerStatsRecordedEvent,
    LeagueRegisteredClubEventData,
    LeagueSeasonRegisteredEvent,
)
from backend.app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class LeagueEventRepository(Protocol):
    def append(self, event: LeagueSeasonEvent) -> None: ...

    def list_events(self, season_id: str) -> tuple[LeagueSeasonEvent, ...]: ...


class LeagueEventRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "league_event_records"

    season_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class DatabaseLeagueEventRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def append(self, event: LeagueSeasonEvent) -> None:
        with self._session_factory() as session:
            session.add(
                LeagueEventRecord(
                    season_id=event.season_id,
                    event_type=type(event).__name__,
                    recorded_at=_event_recorded_at(event),
                    payload_json=_serialize_event(event),
                )
            )
            session.commit()

    def list_events(self, season_id: str) -> tuple[LeagueSeasonEvent, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(LeagueEventRecord)
                .where(LeagueEventRecord.season_id == season_id)
                .order_by(LeagueEventRecord.recorded_at.asc(), LeagueEventRecord.created_at.asc(), LeagueEventRecord.id.asc())
            ).all()
        return tuple(_deserialize_event(row.event_type, row.payload_json) for row in rows)


class InMemoryLeagueEventRepository:
    def __init__(self) -> None:
        self._events: dict[str, list[LeagueSeasonEvent]] = defaultdict(list)
        self._lock = RLock()

    def append(self, event: LeagueSeasonEvent) -> None:
        with self._lock:
            self._events[event.season_id].append(event)

    def list_events(self, season_id: str) -> tuple[LeagueSeasonEvent, ...]:
        with self._lock:
            return tuple(self._events.get(season_id, ()))

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


_league_event_repository = InMemoryLeagueEventRepository()


def get_league_event_repository() -> LeagueEventRepository:
    return _league_event_repository


def _event_recorded_at(event: LeagueSeasonEvent) -> datetime:
    if isinstance(event, LeagueSeasonRegisteredEvent):
        return event.registered_at
    return event.recorded_at


def _serialize_event(event: LeagueSeasonEvent) -> dict[str, object]:
    payload = asdict(event)
    return _normalize_value(payload)


def _normalize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_normalize_value(item) for item in value]
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_value(item) for key, item in value.items()}
    return value


def _deserialize_event(event_type: str, payload: dict[str, object]) -> LeagueSeasonEvent:
    if event_type == "LeagueSeasonRegisteredEvent":
        return LeagueSeasonRegisteredEvent(
            season_id=str(payload["season_id"]),
            buy_in_tier=int(payload["buy_in_tier"]),
            season_start=date.fromisoformat(str(payload["season_start"])),
            registered_at=datetime.fromisoformat(str(payload["registered_at"])),
            clubs=tuple(
                LeagueRegisteredClubEventData(
                    club_id=str(club["club_id"]),
                    club_name=str(club["club_name"]),
                    strength_rating=int(club.get("strength_rating", 0)),
                )
                for club in payload.get("clubs", [])
            ),
        )
    if event_type == "LeagueFixtureCompletedEvent":
        return LeagueFixtureCompletedEvent(
            season_id=str(payload["season_id"]),
            fixture_id=str(payload["fixture_id"]),
            home_goals=int(payload["home_goals"]),
            away_goals=int(payload["away_goals"]),
            recorded_at=datetime.fromisoformat(str(payload["recorded_at"])),
        )
    if event_type == "LeagueClubOptOutEvent":
        return LeagueClubOptOutEvent(
            season_id=str(payload["season_id"]),
            club_id=str(payload["club_id"]),
            recorded_at=datetime.fromisoformat(str(payload["recorded_at"])),
        )
    if event_type == "LeaguePlayerStatsRecordedEvent":
        return LeaguePlayerStatsRecordedEvent(
            season_id=str(payload["season_id"]),
            player_id=str(payload["player_id"]),
            player_name=str(payload["player_name"]),
            club_id=str(payload["club_id"]),
            goals=int(payload["goals"]),
            assists=int(payload["assists"]),
            recorded_at=datetime.fromisoformat(str(payload["recorded_at"])),
        )
    raise ValueError(f"Unsupported league event type: {event_type}")


__all__ = [
    "DatabaseLeagueEventRepository",
    "InMemoryLeagueEventRepository",
    "LeagueEventRecord",
    "LeagueEventRepository",
    "get_league_event_repository",
]
