from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event as ThreadEvent, Thread
from time import perf_counter
import traceback
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.legend_layer.service import LegendLayerService
from app.backbone.kafka import KafkaJsonConsumer
from app.models.notification_record import NotificationRecord
from app.models.projections import CompetitionStandingProjection, PlayerStatsProjection, ProjectionEventReceipt
from app.observability.metrics import GTexMetrics
from app.observability.tracing import start_consumer_span
from app.story_feed_engine.service import StoryFeedService


class ProjectionHandler(Protocol):
    projection_name: str

    def apply(self, session: Session, *, envelope: dict[str, Any]) -> None:
        ...


def _event_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    return dict(envelope.get("payload") or {})


def _already_processed(session: Session, *, projection_name: str, event_id: str) -> bool:
    return session.scalar(
        select(ProjectionEventReceipt).where(
            ProjectionEventReceipt.projection_name == projection_name,
            ProjectionEventReceipt.event_id == event_id,
        )
    ) is not None


def _mark_processed(session: Session, *, projection_name: str, envelope: dict[str, Any]) -> None:
    session.add(
        ProjectionEventReceipt(
            projection_name=projection_name,
            event_id=str(envelope.get("event_id")),
            event_type=str(envelope.get("event_type")),
            aggregate_id=str(envelope.get("aggregate_id")) if envelope.get("aggregate_id") is not None else None,
            metadata_json={"topic": envelope.get("topic")},
        )
    )


@dataclass(slots=True)
class StandingsProjectionHandler:
    projection_name: str = "standings_projection"

    def apply(self, session: Session, *, envelope: dict[str, Any]) -> None:
        event_id = str(envelope.get("event_id"))
        if _already_processed(session, projection_name=self.projection_name, event_id=event_id):
            return
        payload = _event_payload(envelope)
        self._apply_team_row(
            session,
            competition_id=str(payload["competition_id"]),
            season_id=_optional_string(payload.get("season_id")),
            competition_type=_optional_string(payload.get("competition_type")),
            fixture_id=_optional_string(payload.get("fixture_id")),
            club_id=str(payload["home_club_id"]),
            club_name=str(payload["home_club_name"]),
            goals_for=int(payload.get("home_goals") or 0),
            goals_against=int(payload.get("away_goals") or 0),
        )
        self._apply_team_row(
            session,
            competition_id=str(payload["competition_id"]),
            season_id=_optional_string(payload.get("season_id")),
            competition_type=_optional_string(payload.get("competition_type")),
            fixture_id=_optional_string(payload.get("fixture_id")),
            club_id=str(payload["away_club_id"]),
            club_name=str(payload["away_club_name"]),
            goals_for=int(payload.get("away_goals") or 0),
            goals_against=int(payload.get("home_goals") or 0),
        )
        _mark_processed(session, projection_name=self.projection_name, envelope=envelope)

    def _apply_team_row(
        self,
        session: Session,
        *,
        competition_id: str,
        season_id: str | None,
        competition_type: str | None,
        fixture_id: str | None,
        club_id: str,
        club_name: str,
        goals_for: int,
        goals_against: int,
    ) -> None:
        row = session.scalar(
            select(CompetitionStandingProjection).where(
                CompetitionStandingProjection.competition_id == competition_id,
                CompetitionStandingProjection.club_id == club_id,
            )
        )
        if row is None:
            row = CompetitionStandingProjection(
                competition_id=competition_id,
                season_id=season_id,
                competition_type=competition_type,
                club_id=club_id,
                club_name=club_name,
            )
            session.add(row)
        row.season_id = season_id
        row.competition_type = competition_type
        row.club_name = club_name
        row.matches_played = _as_int(row.matches_played) + 1
        row.goals_for = _as_int(row.goals_for) + goals_for
        row.goals_against = _as_int(row.goals_against) + goals_against
        row.goal_difference = _as_int(row.goals_for) - _as_int(row.goals_against)
        row.last_fixture_id = fixture_id
        if goals_for > goals_against:
            row.wins = _as_int(row.wins) + 1
            row.points = _as_int(row.points) + 3
        elif goals_for < goals_against:
            row.losses = _as_int(row.losses) + 1
        else:
            row.draws = _as_int(row.draws) + 1
            row.points = _as_int(row.points) + 1


@dataclass(slots=True)
class PlayerStatsProjectionHandler:
    projection_name: str = "player_stats_projection"

    def apply(self, session: Session, *, envelope: dict[str, Any]) -> None:
        event_id = str(envelope.get("event_id"))
        if _already_processed(session, projection_name=self.projection_name, event_id=event_id):
            return
        payload = _event_payload(envelope)
        winner_team_id = _optional_string(payload.get("winner_team_id"))
        home_goals = int(payload.get("home_goals") or 0)
        away_goals = int(payload.get("away_goals") or 0)
        for item in payload.get("player_stats") or []:
            if not isinstance(item, dict):
                continue
            row = session.scalar(
                select(PlayerStatsProjection).where(
                    PlayerStatsProjection.competition_id == str(payload["competition_id"]),
                    PlayerStatsProjection.player_id == str(item["player_id"]),
                )
            )
            if row is None:
                row = PlayerStatsProjection(
                    competition_id=str(payload["competition_id"]),
                    season_id=_optional_string(payload.get("season_id")),
                    competition_type=_optional_string(payload.get("competition_type")),
                    player_id=str(item["player_id"]),
                    player_name=str(item["player_name"]),
                    team_id=str(item["team_id"]),
                    team_name=str(item["team_name"]),
                )
                session.add(row)
            row.season_id = _optional_string(payload.get("season_id"))
            row.competition_type = _optional_string(payload.get("competition_type"))
            row.player_name = str(item["player_name"])
            row.team_id = str(item["team_id"])
            row.team_name = str(item["team_name"])
            row.appearances = _as_int(row.appearances) + 1
            row.starts = _as_int(row.starts) + (1 if bool(item.get("started")) else 0)
            row.minutes_played = _as_int(row.minutes_played) + int(item.get("minutes_played") or 0)
            row.goals = _as_int(row.goals) + int(item.get("goals") or 0)
            row.assists = _as_int(row.assists) + int(item.get("assists") or 0)
            row.saves = _as_int(row.saves) + int(item.get("saves") or 0)
            row.yellow_cards = _as_int(row.yellow_cards) + int(item.get("yellow_cards") or 0)
            row.red_cards = _as_int(row.red_cards) + (1 if bool(item.get("red_card")) else 0)
            row.cumulative_xg = _as_float(row.cumulative_xg) + float(item.get("xg") or 0.0)
            rating = item.get("rating")
            if rating is not None:
                previous_samples = _as_int(row.rating_samples)
                row.rating_samples = previous_samples + 1
                total_rating = (_as_float(row.average_rating) * previous_samples) + float(rating)
                row.average_rating = total_rating / row.rating_samples
            row.last_fixture_id = _optional_string(payload.get("fixture_id"))
            if winner_team_id is None and home_goals == away_goals:
                row.draws = _as_int(row.draws) + 1
            elif winner_team_id == row.team_id:
                row.wins = _as_int(row.wins) + 1
            else:
                row.losses = _as_int(row.losses) + 1
        _mark_processed(session, projection_name=self.projection_name, envelope=envelope)


@dataclass(slots=True)
class MatchFeedProjectionHandler:
    projection_name: str = "match_feed_projection"

    def apply(self, session: Session, *, envelope: dict[str, Any]) -> None:
        event_id = str(envelope.get("event_id"))
        if _already_processed(session, projection_name=self.projection_name, event_id=event_id):
            return
        payload = _event_payload(envelope)
        home_name = str(payload.get("home_club_name") or "Home Club")
        away_name = str(payload.get("away_club_name") or "Away Club")
        body = f"{home_name} {int(payload.get('home_goals') or 0)} - {int(payload.get('away_goals') or 0)} {away_name}"
        StoryFeedService(session).publish(
            story_type="match_completed",
            title=f"{home_name} vs {away_name} finished",
            body=body,
            audience="public",
            subject_type="competition_match",
            subject_id=_optional_string(payload.get("fixture_id")),
            metadata_json={
                "event_id": event_id,
                "competition_id": payload.get("competition_id"),
                "winner_team_id": payload.get("winner_team_id"),
            },
            featured=bool(payload.get("is_final")),
        )
        for user_id in [item for item in payload.get("user_ids") or [] if isinstance(item, str)]:
            session.add(
                NotificationRecord(
                    user_id=user_id,
                    topic="projection_match_feed",
                    template_key="MATCH_FEED_PROJECTED",
                    resource_type="competition_match",
                    resource_id=_optional_string(payload.get("fixture_id")),
                    fixture_id=_optional_string(payload.get("fixture_id")),
                    competition_id=_optional_string(payload.get("competition_id")),
                    message=body[:255],
                    metadata_json={"event_id": event_id},
                )
            )
        _mark_processed(session, projection_name=self.projection_name, envelope=envelope)


@dataclass(slots=True)
class LegendLayerProjectionHandler:
    projection_name: str = "legend_layer_projection"

    def apply(self, session: Session, *, envelope: dict[str, Any]) -> None:
        event_id = str(envelope.get("event_id"))
        if _already_processed(session, projection_name=self.projection_name, event_id=event_id):
            return
        if str(envelope.get("event_type") or "") != "match.completed":
            return
        payload = _event_payload(envelope)
        LegendLayerService(session=session).process_match_completed(payload, event_id=event_id)
        _mark_processed(session, projection_name=self.projection_name, envelope=envelope)


@dataclass(slots=True)
class ProjectionWorkerService:
    session_factory: sessionmaker[Session]
    consumer: KafkaJsonConsumer
    metrics: GTexMetrics | None = None
    handlers: tuple[ProjectionHandler, ...] = field(
        default_factory=lambda: (
            StandingsProjectionHandler(),
            PlayerStatsProjectionHandler(),
            MatchFeedProjectionHandler(),
            LegendLayerProjectionHandler(),
        )
    )
    _stop_event: ThreadEvent = field(default_factory=ThreadEvent)
    _thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-projection-workers", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.consumer.close()

    def poll_once(self) -> int:
        handled = 0
        for message in self.consumer.poll():
            envelope = dict(message.value or {})
            envelope["topic"] = message.topic
            started_at = perf_counter()
            try:
                with start_consumer_span(
                    "queue.consume.projection",
                    carrier=_message_carrier(message),
                    attributes={"messaging.destination.name": message.topic},
                ):
                    with self.session_factory() as session:
                        for handler in self.handlers:
                            handler.apply(session, envelope=envelope)
                        session.commit()
                self.consumer.commit()
                handled += 1
                if self.metrics is not None:
                    self.metrics.record_queue_message(
                        queue_name="projection",
                        job_name="projection",
                        result="processed",
                    )
                    self.metrics.record_worker_job(
                        job_name="projection",
                        result="success",
                        duration_seconds=perf_counter() - started_at,
                    )
            except Exception:
                if self.metrics is not None:
                    self.metrics.record_queue_message(
                        queue_name="projection",
                        job_name="projection",
                        result="error",
                    )
                    self.metrics.record_worker_job(
                        job_name="projection",
                        result="error",
                        duration_seconds=perf_counter() - started_at,
                    )
                raise
        return handled

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                traceback.print_exc()
                self._stop_event.wait(1.0)


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    resolved = str(value).strip()
    return resolved or None


def _as_int(value: Any) -> int:
    return int(value or 0)


def _as_float(value: Any) -> float:
    return float(value or 0.0)


def _message_carrier(message) -> dict[str, str]:
    carrier = {
        str(key): str(value)
        for key, value in dict(message.headers or {}).items()
        if value is not None
    }
    envelope_headers = message.value.get("headers") if isinstance(message.value, dict) else None
    if isinstance(envelope_headers, dict):
        for key, value in envelope_headers.items():
            if value is None:
                continue
            carrier.setdefault(str(key), str(value))
    return carrier


__all__ = [
    "LegendLayerProjectionHandler",
    "MatchFeedProjectionHandler",
    "PlayerStatsProjectionHandler",
    "ProjectionWorkerService",
    "StandingsProjectionHandler",
]
