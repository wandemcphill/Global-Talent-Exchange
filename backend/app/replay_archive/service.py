from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI

from backend.app.common.enums.replay_visibility import ReplayVisibility
from backend.app.core.events import DomainEvent
from backend.app.replay_archive.persistence import (
    DatabaseReplayArchiveRepository,
    InMemoryReplayArchiveRepository,
    ReplayArchiveRepository,
)
from backend.app.replay_archive.policy import SpectatorVisibilityPolicyService
from backend.app.replay_archive.schemas import (
    CompetitionContextView,
    CountdownUpdatePayload,
    CountdownView,
    ReplayArchiveIngest,
    ReplayArchiveRecord,
    ReplayClubView,
    ReplayMomentView,
    ReplayScoreline,
    ReplaySummaryView,
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


MATCH_COUNTDOWN_TEMPLATE_KEYS = {
    "match_starts_10m": 10,
    "match_starts_1m": 1,
    "match_live_now": 0,
}


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_optional(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _normalize_timestamp(value)


@dataclass(slots=True)
class ReplayArchiveService:
    spectator_policy: SpectatorVisibilityPolicyService
    repository: ReplayArchiveRepository

    def handle_event(self, event: DomainEvent) -> None:
        try:
            if event.name in {"competition.replay.archived", "competition.match.replay_ready"}:
                self.store_replay(event.payload, stored_at=event.occurred_at)
                return
            if event.name in {"competition.match.scheduled", "competition.match.live", "competition.match.countdown"}:
                self.record_countdown(event.payload, recorded_at=event.occurred_at)
                return
            if event.name == "competition.notification":
                template_key = event.payload.get("template_key")
                if template_key in MATCH_COUNTDOWN_TEMPLATE_KEYS:
                    payload = dict(event.payload)
                    payload.setdefault("live", template_key == "match_live_now")
                    payload["last_notification_key"] = template_key
                    self.record_countdown(payload, recorded_at=event.occurred_at)
        except ValueError:
            return

    def store_replay(
        self,
        payload: ReplayArchiveIngest | dict[str, Any],
        *,
        stored_at: datetime | None = None,
    ) -> ReplayArchiveRecord:
        ingest = payload if isinstance(payload, ReplayArchiveIngest) else ReplayArchiveIngest.model_validate(payload)
        stored_timestamp = _normalize_timestamp(stored_at or utcnow())
        replay_id = ingest.replay_id or f"replay:{ingest.fixture_id}"
        decision = self.spectator_policy.resolve(
            replay_visibility=ingest.competition_context.replay_visibility,
            round_number=ingest.competition_context.round_number,
            stage_name=ingest.competition_context.stage_name,
            is_final=ingest.competition_context.is_final,
            competition_allows_public=ingest.competition_context.competition_allows_public,
            allow_early_round_public=ingest.competition_context.allow_early_round_public,
        )

        previous = self.repository.get_latest_record(replay_id)
        version = 1 if previous is None else previous.version + 1
        created_at = stored_timestamp if previous is None else previous.created_at
        context = ingest.competition_context.model_copy(
            update={
                "resolved_visibility": decision.resolved_visibility,
                "public_metadata_visible": decision.public_metadata_visible,
                "featured_public": decision.featured_public,
            }
        )
        record = ReplayArchiveRecord(
            replay_id=replay_id,
            version=version,
            fixture_id=ingest.fixture_id,
            created_at=created_at,
            updated_at=stored_timestamp,
            scheduled_start=_normalize_timestamp(ingest.scheduled_start),
            started_at=_normalize_optional(ingest.started_at),
            final_whistle_at=_normalize_optional(ingest.final_whistle_at),
            live=ingest.live,
            home_club=ingest.home_club,
            away_club=ingest.away_club,
            scoreline=ingest.scoreline,
            visual_identity=ingest.visual_identity,
            timeline=ingest.timeline,
            scorers=self._filter_timeline(ingest.timeline, event_types={"goals"}),
            assisters=self._filter_timeline(ingest.timeline, event_types={"assists"}),
            cards=self._filter_timeline(ingest.timeline, event_types={"yellow_cards", "red_cards"}),
            injuries=self._filter_timeline(ingest.timeline, event_types={"injuries"}),
            substitutions=self._filter_timeline(ingest.timeline, event_types={"substitutions"}),
            participant_user_ids=tuple(dict.fromkeys(ingest.participant_user_ids)),
            competition_context=context,
        )
        self.repository.append_record(record)
        self.repository.upsert_countdown(self._build_countdown_from_replay(record, last_notification_key=None))
        return record

    def record_countdown(
        self,
        payload: CountdownUpdatePayload | dict[str, Any],
        *,
        recorded_at: datetime | None = None,
    ) -> CountdownView:
        update = payload if isinstance(payload, CountdownUpdatePayload) else CountdownUpdatePayload.model_validate(payload)
        decision = self.spectator_policy.resolve(
            replay_visibility=update.competition_context.replay_visibility,
            round_number=update.competition_context.round_number,
            stage_name=update.competition_context.stage_name,
            is_final=update.competition_context.is_final,
            competition_allows_public=update.competition_context.competition_allows_public,
            allow_early_round_public=update.competition_context.allow_early_round_public,
        )
        updated_context = update.competition_context.model_copy(
            update={
                "resolved_visibility": decision.resolved_visibility,
                "public_metadata_visible": decision.public_metadata_visible,
                "featured_public": decision.featured_public,
            }
        )
        timestamp = _normalize_timestamp(recorded_at or utcnow())
        notification_sent_at = None
        if update.last_notification_key:
            notification_sent_at = _normalize_timestamp(update.notification_sent_at or timestamp)
        countdown = self._build_countdown(
            fixture_id=update.fixture_id,
            replay_id=update.replay_id,
            scheduled_start=_normalize_timestamp(update.scheduled_start),
            home_club=update.home_club,
            away_club=update.away_club,
            competition_context=updated_context,
            live=update.live,
            completed=update.completed,
            last_notification_key=update.last_notification_key,
            notification_sent_at=notification_sent_at,
        )
        self.repository.upsert_countdown(countdown)
        return countdown

    def list_for_user(self, user_id: str, *, limit: int = 20) -> list[ReplaySummaryView]:
        records = self.repository.list_latest_records()
        visible = [self._to_summary(record) for record in records if self._can_access(record, user_id=user_id)]
        visible.sort(key=lambda item: item.scheduled_start, reverse=True)
        return visible[:limit]

    def get_for_user(self, replay_id: str, *, user_id: str) -> ReplayArchiveRecord | None:
        record = self.repository.get_latest_record(replay_id)
        if record is None or not self._can_access(record, user_id=user_id):
            return None
        return record

    def list_featured_public(self, *, limit: int = 20) -> list[ReplaySummaryView]:
        records = self.repository.list_latest_records()
        featured = [
            self._to_summary(record)
            for record in records
            if record.competition_context.public_metadata_visible and record.competition_context.featured_public
        ]
        featured.sort(
            key=lambda item: (
                item.competition_context.is_final,
                item.live,
                item.scheduled_start,
            ),
            reverse=True,
        )
        return featured[:limit]

    def get_public_countdown(self, fixture_id: str) -> CountdownView | None:
        countdown = self.repository.get_countdown(fixture_id)
        if countdown is None or not countdown.competition_context.public_metadata_visible:
            return None
        return self._refresh_countdown(countdown)

    def _can_access(self, record: ReplayArchiveRecord, *, user_id: str) -> bool:
        if user_id in record.participant_user_ids:
            return True
        return record.competition_context.resolved_visibility in {
            ReplayVisibility.COMPETITION,
            ReplayVisibility.PUBLIC,
        }

    @staticmethod
    def _filter_timeline(
        timeline: tuple[ReplayMomentView, ...],
        *,
        event_types: set[str],
    ) -> tuple[ReplayMomentView, ...]:
        return tuple(event for event in timeline if event.event_type in event_types)

    def _build_countdown_from_replay(
        self,
        record: ReplayArchiveRecord,
        *,
        last_notification_key: str | None,
    ) -> CountdownView:
        return self._build_countdown(
            fixture_id=record.fixture_id,
            replay_id=record.replay_id,
            scheduled_start=record.scheduled_start,
            home_club=record.home_club,
            away_club=record.away_club,
            competition_context=record.competition_context,
            live=record.live,
            completed=record.final_whistle_at is not None and not record.live,
            last_notification_key=last_notification_key,
            notification_sent_at=None,
        )

    def _build_countdown(
        self,
        *,
        fixture_id: str,
        replay_id: str | None,
        scheduled_start: datetime,
        home_club: ReplayClubView,
        away_club: ReplayClubView,
        competition_context: CompetitionContextView,
        live: bool,
        completed: bool,
        last_notification_key: str | None,
        notification_sent_at: datetime | None,
    ) -> CountdownView:
        normalized_start = _normalize_timestamp(scheduled_start)
        state = "complete" if completed else "live" if live else "scheduled"
        seconds_until_start = int((normalized_start - utcnow()).total_seconds())
        next_notification_key = self._next_notification_key(
            seconds_until_start,
            state=state,
            last_notification_key=last_notification_key,
        )
        return CountdownView(
            fixture_id=fixture_id,
            replay_id=replay_id,
            scheduled_start=normalized_start,
            state=state,
            seconds_until_start=seconds_until_start,
            home_club=home_club,
            away_club=away_club,
            competition_context=competition_context,
            last_notification_key=last_notification_key,
            next_notification_key=next_notification_key,
            notification_sent_at=_normalize_optional(notification_sent_at),
        )

    def _refresh_countdown(self, countdown: CountdownView) -> CountdownView:
        updated = countdown.model_copy(
            update={
                "seconds_until_start": int((countdown.scheduled_start - utcnow()).total_seconds()),
            }
        )
        updated = updated.model_copy(
            update={
                "next_notification_key": self._next_notification_key(
                    updated.seconds_until_start,
                    state=updated.state,
                    last_notification_key=updated.last_notification_key,
                )
            }
        )
        self.repository.upsert_countdown(updated)
        return updated

    @staticmethod
    def _next_notification_key(
        seconds_until_start: int,
        *,
        state: str,
        last_notification_key: str | None,
    ) -> str | None:
        if state != "scheduled":
            return None
        if seconds_until_start >= 600 and last_notification_key != "match_starts_10m":
            return "match_starts_10m"
        if seconds_until_start >= 60 and last_notification_key != "match_starts_1m":
            return "match_starts_1m"
        if seconds_until_start < 60 and last_notification_key != "match_live_now":
            return "match_live_now"
        return None

    @staticmethod
    def _to_summary(record: ReplayArchiveRecord) -> ReplaySummaryView:
        return ReplaySummaryView(
            replay_id=record.replay_id,
            fixture_id=record.fixture_id,
            scheduled_start=record.scheduled_start,
            started_at=record.started_at,
            final_whistle_at=record.final_whistle_at,
            live=record.live,
            home_club=record.home_club,
            away_club=record.away_club,
            scoreline=record.scoreline,
            competition_context=record.competition_context,
        )


def ensure_replay_archive(app: FastAPI) -> ReplayArchiveService:
    replay_archive = getattr(app.state, "replay_archive", None)
    if replay_archive is None:
        spectator_policy = getattr(app.state, "spectator_visibility_policy", None)
        if spectator_policy is None:
            spectator_policy = SpectatorVisibilityPolicyService()
            app.state.spectator_visibility_policy = spectator_policy
        session_factory = getattr(app.state, "session_factory", None)
        repository: ReplayArchiveRepository
        if session_factory is not None:
            repository = DatabaseReplayArchiveRepository(session_factory=session_factory)
        else:
            repository = InMemoryReplayArchiveRepository()
        replay_archive = ReplayArchiveService(spectator_policy=spectator_policy, repository=repository)
        app.state.replay_archive = replay_archive
    if hasattr(app.state, "event_publisher") and not getattr(app.state, "_replay_archive_subscribed", False):
        app.state.event_publisher.subscribe(replay_archive.handle_event)
        app.state._replay_archive_subscribed = True
    if hasattr(app.state, "event_publisher"):
        from backend.app.match_engine.services import ensure_local_match_execution_runtime

        ensure_local_match_execution_runtime(app)
    return replay_archive
