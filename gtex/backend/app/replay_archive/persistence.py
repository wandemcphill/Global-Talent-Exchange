from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from threading import RLock
from typing import Protocol

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, UniqueConstraint, and_, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.replay_archive.schemas import CountdownView, ReplayArchiveRecord


class ReplayArchiveRecordRow(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "replay_archive_records"
    __table_args__ = (UniqueConstraint("replay_id", "version", name="uq_replay_archive_records_replay_version"),)

    replay_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    fixture_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_whistle_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    live: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    home_club_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    away_club_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    scoreline_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    visual_identity_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    timeline_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    scorers_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    assisters_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    cards_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    injuries_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    substitutions_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    participant_user_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    competition_context_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class ReplayArchiveCountdownRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "replay_archive_countdowns"
    __table_args__ = (UniqueConstraint("fixture_id", name="uq_replay_archive_countdowns_fixture_id"),)

    fixture_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    replay_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    home_club_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    away_club_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    competition_context_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    last_notification_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    next_notification_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReplayArchiveRepository(Protocol):
    def append_record(self, record: ReplayArchiveRecord) -> ReplayArchiveRecord: ...

    def list_latest_records(self) -> list[ReplayArchiveRecord]: ...

    def get_latest_record(self, replay_id: str) -> ReplayArchiveRecord | None: ...

    def upsert_countdown(self, countdown: CountdownView) -> CountdownView: ...

    def get_countdown(self, fixture_id: str) -> CountdownView | None: ...


@dataclass(slots=True)
class InMemoryReplayArchiveRepository:
    _history: list[ReplayArchiveRecord] = field(default_factory=list)
    _latest_by_replay_id: dict[str, ReplayArchiveRecord] = field(default_factory=dict)
    _countdowns: dict[str, CountdownView] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def append_record(self, record: ReplayArchiveRecord) -> ReplayArchiveRecord:
        with self._lock:
            self._history.append(record)
            self._latest_by_replay_id[record.replay_id] = record
        return record

    def list_latest_records(self) -> list[ReplayArchiveRecord]:
        with self._lock:
            return list(self._latest_by_replay_id.values())

    def get_latest_record(self, replay_id: str) -> ReplayArchiveRecord | None:
        with self._lock:
            return self._latest_by_replay_id.get(replay_id)

    def upsert_countdown(self, countdown: CountdownView) -> CountdownView:
        with self._lock:
            self._countdowns[countdown.fixture_id] = countdown
        return countdown

    def get_countdown(self, fixture_id: str) -> CountdownView | None:
        with self._lock:
            return self._countdowns.get(fixture_id)


@dataclass(slots=True)
class DatabaseReplayArchiveRepository:
    session_factory: sessionmaker[Session]

    def append_record(self, record: ReplayArchiveRecord) -> ReplayArchiveRecord:
        row = ReplayArchiveRecordRow(
            replay_id=record.replay_id,
            version=record.version,
            fixture_id=record.fixture_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
            scheduled_start=record.scheduled_start,
            started_at=record.started_at,
            final_whistle_at=record.final_whistle_at,
            live=record.live,
            home_club_json=record.home_club.model_dump(mode="json"),
            away_club_json=record.away_club.model_dump(mode="json"),
            scoreline_json=record.scoreline.model_dump(mode="json"),
            visual_identity_json=(
                record.visual_identity.model_dump(mode="json")
                if record.visual_identity is not None
                else None
            ),
            timeline_json=[event.model_dump(mode="json") for event in record.timeline],
            scorers_json=[event.model_dump(mode="json") for event in record.scorers],
            assisters_json=[event.model_dump(mode="json") for event in record.assisters],
            cards_json=[event.model_dump(mode="json") for event in record.cards],
            injuries_json=[event.model_dump(mode="json") for event in record.injuries],
            substitutions_json=[event.model_dump(mode="json") for event in record.substitutions],
            participant_user_ids_json=list(record.participant_user_ids),
            competition_context_json=record.competition_context.model_dump(mode="json"),
        )
        with self.session_factory() as session:
            session.add(row)
            session.commit()
        return record

    def list_latest_records(self) -> list[ReplayArchiveRecord]:
        latest_versions = (
            select(
                ReplayArchiveRecordRow.replay_id.label("replay_id"),
                func.max(ReplayArchiveRecordRow.version).label("max_version"),
            )
            .group_by(ReplayArchiveRecordRow.replay_id)
            .subquery()
        )
        with self.session_factory() as session:
            rows = session.scalars(
                select(ReplayArchiveRecordRow)
                .join(
                    latest_versions,
                    and_(
                        ReplayArchiveRecordRow.replay_id == latest_versions.c.replay_id,
                        ReplayArchiveRecordRow.version == latest_versions.c.max_version,
                    ),
                )
            ).all()
        return [_record_from_row(row) for row in rows]

    def get_latest_record(self, replay_id: str) -> ReplayArchiveRecord | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(ReplayArchiveRecordRow)
                .where(ReplayArchiveRecordRow.replay_id == replay_id)
                .order_by(ReplayArchiveRecordRow.version.desc())
            )
        if row is None:
            return None
        return _record_from_row(row)

    def upsert_countdown(self, countdown: CountdownView) -> CountdownView:
        with self.session_factory() as session:
            existing = session.scalar(
                select(ReplayArchiveCountdownRow).where(ReplayArchiveCountdownRow.fixture_id == countdown.fixture_id)
            )
            if existing is None:
                existing = ReplayArchiveCountdownRow(
                    fixture_id=countdown.fixture_id,
                    replay_id=countdown.replay_id,
                    scheduled_start=countdown.scheduled_start,
                    state=countdown.state,
                    home_club_json=countdown.home_club.model_dump(mode="json"),
                    away_club_json=countdown.away_club.model_dump(mode="json"),
                    competition_context_json=countdown.competition_context.model_dump(mode="json"),
                    last_notification_key=countdown.last_notification_key,
                    next_notification_key=countdown.next_notification_key,
                    notification_sent_at=countdown.notification_sent_at,
                )
                session.add(existing)
            else:
                existing.replay_id = countdown.replay_id
                existing.scheduled_start = countdown.scheduled_start
                existing.state = countdown.state
                existing.home_club_json = countdown.home_club.model_dump(mode="json")
                existing.away_club_json = countdown.away_club.model_dump(mode="json")
                existing.competition_context_json = countdown.competition_context.model_dump(mode="json")
                existing.last_notification_key = countdown.last_notification_key
                existing.next_notification_key = countdown.next_notification_key
                existing.notification_sent_at = countdown.notification_sent_at
            session.commit()
        return countdown

    def get_countdown(self, fixture_id: str) -> CountdownView | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(ReplayArchiveCountdownRow).where(ReplayArchiveCountdownRow.fixture_id == fixture_id)
            )
        if row is None:
            return None
        return _countdown_from_row(row)


def _record_from_row(row: ReplayArchiveRecordRow) -> ReplayArchiveRecord:
    return ReplayArchiveRecord.model_validate(
        {
            "replay_id": row.replay_id,
            "version": row.version,
            "fixture_id": row.fixture_id,
            "created_at": _ensure_aware(row.created_at),
            "updated_at": _ensure_aware(row.updated_at),
            "scheduled_start": _ensure_aware(row.scheduled_start),
            "started_at": _ensure_aware(row.started_at),
            "final_whistle_at": _ensure_aware(row.final_whistle_at),
            "live": row.live,
            "home_club": row.home_club_json,
            "away_club": row.away_club_json,
            "scoreline": row.scoreline_json,
            "visual_identity": row.visual_identity_json,
            "timeline": row.timeline_json,
            "scorers": row.scorers_json,
            "assisters": row.assisters_json,
            "cards": row.cards_json,
            "injuries": row.injuries_json,
            "substitutions": row.substitutions_json,
            "participant_user_ids": row.participant_user_ids_json,
            "competition_context": row.competition_context_json,
        }
    )


def _countdown_from_row(row: ReplayArchiveCountdownRow) -> CountdownView:
    return CountdownView.model_validate(
        {
            "fixture_id": row.fixture_id,
            "replay_id": row.replay_id,
            "scheduled_start": _ensure_aware(row.scheduled_start),
            "state": row.state,
            "seconds_until_start": 0,
            "home_club": row.home_club_json,
            "away_club": row.away_club_json,
            "competition_context": row.competition_context_json,
            "last_notification_key": row.last_notification_key,
            "next_notification_key": row.next_notification_key,
            "notification_sent_at": _ensure_aware(row.notification_sent_at),
        }
    )


def _ensure_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(timezone.utc)


__all__ = [
    "DatabaseReplayArchiveRepository",
    "InMemoryReplayArchiveRepository",
    "ReplayArchiveCountdownRow",
    "ReplayArchiveRecordRow",
    "ReplayArchiveRepository",
]
