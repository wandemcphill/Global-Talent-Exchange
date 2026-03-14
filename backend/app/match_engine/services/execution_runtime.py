from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from math import ceil
from threading import RLock
from typing import Any

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.enums.replay_visibility import ReplayVisibility
from backend.app.common.schemas.competition import ScheduledFixture
from backend.app.competition_engine.match_dispatcher import MatchDispatcher
from backend.app.competition_engine.queue_contracts import (
    BracketAdvancementJob,
    InMemoryQueuePublisher,
    MatchSimulationJob,
    NotificationJob,
    PayoutSettlementJob,
    QueuedJobRecord,
)
from backend.app.core.events import DomainEvent, EventPublisher
from backend.app.leagues.models import LeagueClub, LeagueFixture, LeaguePlayerContribution, LeagueSeasonState
from backend.app.leagues.service import LeagueSeasonLifecycleService
from backend.app.match_engine.schemas import MatchReplayPayloadView
from backend.app.match_engine.services.match_simulation_service import MatchSimulationService
from backend.app.match_engine.services.team_factory import SyntheticSquadFactory
from backend.app.match_engine.simulation.models import MatchEventType
from backend.app.services.player_lifecycle_service import PlayerLifecycleService


@dataclass(slots=True)
class LeagueFixtureExecutionService:
    dispatcher: MatchDispatcher
    event_publisher: EventPublisher
    execution_worker: "LocalMatchExecutionWorker"

    def schedule_fixture(
        self,
        *,
        season_id: str,
        fixture: LeagueFixture,
        clubs: tuple[LeagueClub, ...],
        competition_name: str | None = None,
        club_user_ids: dict[str, str] | None = None,
        simulation_seed: int | None = None,
        reference_at: datetime | None = None,
    ):
        strength_by_club_id = {club.club_id: club.strength_rating for club in clubs}
        user_ids = club_user_ids or {}
        self.execution_worker.register_league_club_users(season_id, club_user_ids=user_ids)

        kickoff_at = _normalize_timestamp(fixture.kickoff_at)
        replay_visibility = ReplayVisibility.COMPETITION
        competition_context = {
            "competition_id": season_id,
            "competition_type": CompetitionType.LEAGUE,
            "competition_name": competition_name or season_id,
            "season_id": season_id,
            "stage_name": f"Round {fixture.round_number}",
            "round_number": fixture.round_number,
            "is_final": False,
            "is_cup_match": False,
            "competition_allows_public": fixture.round_number >= 3,
            "allow_early_round_public": False,
            "replay_visibility": replay_visibility,
        }
        participant_user_ids = [
            user_id
            for user_id in (
                user_ids.get(fixture.home_club_id),
                user_ids.get(fixture.away_club_id),
            )
            if user_id is not None
        ]
        scheduled_fixture = ScheduledFixture(
            fixture_id=fixture.fixture_id,
            competition_id=season_id,
            competition_type=CompetitionType.LEAGUE,
            round_number=fixture.round_number,
            home_club_id=fixture.home_club_id,
            away_club_id=fixture.away_club_id,
            match_date=kickoff_at.date(),
            window=_resolve_league_window(fixture.window_number),
            stage_name=f"Round {fixture.round_number}",
            replay_visibility=replay_visibility,
            is_cup_match=False,
            allow_penalties=False,
        )
        base_payload = {
            "competition_id": season_id,
            "competition_name": competition_name or season_id,
            "fixture_id": fixture.fixture_id,
            "resource_id": fixture.fixture_id,
            "home_club": {
                "club_id": fixture.home_club_id,
                "club_name": fixture.home_club_name,
            },
            "away_club": {
                "club_id": fixture.away_club_id,
                "club_name": fixture.away_club_name,
            },
            "home_club_name": fixture.home_club_name,
            "away_club_name": fixture.away_club_name,
            "scheduled_start": kickoff_at,
            "competition_context": competition_context,
        }
        if participant_user_ids:
            base_payload["user_ids"] = participant_user_ids
        self.event_publisher.publish(
            DomainEvent(
                name="competition.match.scheduled",
                payload={
                    **base_payload,
                },
            )
        )
        self._queue_pre_match_notifications(
            base_payload=base_payload,
            kickoff_at=kickoff_at,
            home_user_id=user_ids.get(fixture.home_club_id),
            away_user_id=user_ids.get(fixture.away_club_id),
            reference_at=reference_at,
            season_id=season_id,
        )
        return self.dispatcher.dispatch_match_simulation(
            scheduled_fixture,
            season_id=season_id,
            competition_name=competition_name or season_id,
            stage_name=f"Round {fixture.round_number}",
            scheduled_kickoff_at=kickoff_at,
            simulation_seed=simulation_seed,
            home_club_name=fixture.home_club_name,
            away_club_name=fixture.away_club_name,
            home_strength_rating=strength_by_club_id.get(fixture.home_club_id),
            away_strength_rating=strength_by_club_id.get(fixture.away_club_id),
            home_user_id=user_ids.get(fixture.home_club_id),
            away_user_id=user_ids.get(fixture.away_club_id),
        )

    def _queue_pre_match_notifications(
        self,
        *,
        base_payload: dict[str, Any],
        kickoff_at: datetime,
        home_user_id: str | None,
        away_user_id: str | None,
        reference_at: datetime | None,
        season_id: str,
    ) -> None:
        if reference_at is None:
            return
        seconds_until_start = int((_normalize_timestamp(kickoff_at) - _normalize_timestamp(reference_at)).total_seconds())
        if seconds_until_start < 0:
            return
        if seconds_until_start <= 60:
            template_key = "match_starts_1m"
        elif seconds_until_start <= 600:
            template_key = "match_starts_10m"
        else:
            return
        for user_id in (home_user_id, away_user_id):
            if user_id is None:
                continue
            self.dispatcher.dispatch_notification(
                competition_id=season_id,
                competition_type=CompetitionType.LEAGUE,
                template_key=template_key,
                audience_key=user_id,
                resource_id=base_payload["resource_id"],
                payload=base_payload,
            )


@dataclass(slots=True)
class LocalMatchExecutionWorker:
    dispatcher: MatchDispatcher
    event_publisher: EventPublisher
    match_service: MatchSimulationService = field(default_factory=MatchSimulationService)
    league_service: LeagueSeasonLifecycleService = field(default_factory=LeagueSeasonLifecycleService)
    team_factory: SyntheticSquadFactory = field(default_factory=SyntheticSquadFactory)
    session_factory: sessionmaker[Session] | None = None
    _completed_match_jobs: set[str] = field(default_factory=set)
    _completed_advancement_jobs: set[str] = field(default_factory=set)
    _completed_notification_jobs: set[str] = field(default_factory=set)
    _completed_settlement_jobs: set[str] = field(default_factory=set)
    _league_club_user_ids: dict[str, dict[str, str]] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def register_league_club_users(self, season_id: str, *, club_user_ids: dict[str, str]) -> None:
        if not club_user_ids:
            return
        with self._lock:
            mapping = self._league_club_user_ids.setdefault(season_id, {})
            mapping.update(club_user_ids)

    def handle_event(self, event: DomainEvent) -> None:
        job_payload = event.payload.get("job_payload")
        if not isinstance(job_payload, dict):
            return
        if event.name == "competition_engine.queue.match_simulation.queued":
            self.execute_match_simulation(MatchSimulationJob.model_validate(job_payload))
        elif event.name == "competition_engine.queue.bracket_advancement.queued":
            self.execute_advancement(BracketAdvancementJob.model_validate(job_payload))
        elif event.name == "competition_engine.queue.notification.queued":
            self.execute_notification(NotificationJob.model_validate(job_payload))
        elif event.name == "competition_engine.queue.payout_settlement.queued":
            self.execute_settlement(PayoutSettlementJob.model_validate(job_payload))

    def execute_match_simulation(self, job: MatchSimulationJob) -> MatchReplayPayloadView | None:
        claim_key = job.idempotency_key or job.fixture_id
        if not self._claim_once(self._completed_match_jobs, claim_key):
            return None
        self._publish_match_lifecycle_event(
            "competition.match.execution.started",
            job,
            extra={
                "claim_key": claim_key,
                "execution_mode": "local_worker",
            },
        )
        try:
            request = self.team_factory.build_request(job)
            replay_payload = self.match_service.build_replay_payload(request)
            self._persist_player_lifecycle_incidents(job, replay_payload)
            self._publish_match_lifecycle_event(
                "competition.match.simulation.completed",
                job,
                replay_payload=replay_payload,
                extra={"execution_mode": "local_worker"},
            )
            self._publish_match_lifecycle_event(
                "competition.match.commentary.generated",
                job,
                replay_payload=replay_payload,
                extra={
                    "commentary_event_count": len(replay_payload.timeline.events),
                    "key_moments": self._build_key_moment_breakdown(replay_payload),
                },
            )
            live_templates = self._queue_live_notifications(job)
            if live_templates:
                self._publish_match_lifecycle_event(
                    "competition.match.notifications.dispatched",
                    job,
                    extra={
                        "notification_phase": "live",
                        "notification_count": len(live_templates),
                        "notification_templates": live_templates,
                    },
                )
            self.event_publisher.publish(
                DomainEvent(
                    name="competition.match.live",
                    payload={
                        **self._countdown_payload(job, include_user_ids=True),
                        "live": True,
                    },
                )
            )
            state = self._apply_competition_result(job, replay_payload)
            self._publish_match_lifecycle_event(
                "competition.match.result.generated",
                job,
                replay_payload=replay_payload,
                state=state,
                extra={
                    "result_status": getattr(replay_payload.summary.status, "value", replay_payload.summary.status),
                },
            )
            if state is not None:
                self._publish_match_lifecycle_event(
                    "competition.match.standings.updated",
                    job,
                    replay_payload=replay_payload,
                    state=state,
                )
            advancement_record = self._queue_advancement(job, replay_payload)
            if advancement_record is not None:
                self._publish_match_lifecycle_event(
                    "competition.match.advancement.dispatched",
                    job,
                    replay_payload=replay_payload,
                    extra={
                        "advancement_idempotency_key": advancement_record.idempotency_key,
                        "stage_code": advancement_record.payload.get("stage_code"),
                    },
                )
            self._publish_match_lifecycle_event(
                "competition.match.replay.prepared",
                job,
                replay_payload=replay_payload,
                state=state,
            )
            self.event_publisher.publish(
                DomainEvent(
                    name="competition.replay.archived",
                    payload=self._build_replay_archive_payload(job, replay_payload),
                )
            )
            result_templates = self._queue_result_notifications(job, replay_payload)
            if result_templates:
                self._publish_match_lifecycle_event(
                    "competition.match.notifications.dispatched",
                    job,
                    replay_payload=replay_payload,
                    extra={
                        "notification_phase": "result",
                        "notification_count": len(result_templates),
                        "notification_templates": result_templates,
                    },
                )
            if state is not None and state.status == "completed":
                transition_templates = self._queue_league_transition_notifications(job, state)
                if transition_templates:
                    self._publish_match_lifecycle_event(
                        "competition.match.notifications.dispatched",
                        job,
                        replay_payload=replay_payload,
                        state=state,
                        extra={
                            "notification_phase": "season_completion",
                            "notification_count": len(transition_templates),
                            "notification_templates": transition_templates,
                        },
                    )
                settlement_record = self.dispatcher.dispatch_payout_settlement(
                    competition_id=job.competition_id,
                    competition_type=job.competition_type,
                    settlement_scope=job.season_id or job.competition_id,
                    settlement_date=job.match_date,
                    source_fixture_id=job.fixture_id,
                )
                self._publish_match_lifecycle_event(
                    "competition.match.settlement.dispatched",
                    job,
                    replay_payload=replay_payload,
                    state=state,
                    extra={
                        "settlement_idempotency_key": settlement_record.idempotency_key,
                        "settlement_scope": job.season_id or job.competition_id,
                    },
                )
            self._publish_match_lifecycle_event(
                "competition.match.execution.completed",
                job,
                replay_payload=replay_payload,
                state=state,
            )
            return replay_payload
        except Exception as exc:
            self._publish_match_lifecycle_event(
                "competition.match.execution.failed",
                job,
                extra={
                    "error_message": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            self._release_claim(self._completed_match_jobs, claim_key)
            raise

    def _persist_player_lifecycle_incidents(
        self,
        job: MatchSimulationJob,
        replay_payload: MatchReplayPayloadView,
    ) -> None:
        if self.session_factory is None:
            return
        session = self.session_factory()
        try:
            PlayerLifecycleService(session).persist_match_incidents(
                fixture_id=job.fixture_id,
                match_date=job.match_date,
                replay_payload=replay_payload,
            )
        finally:
            session.close()

    def execute_advancement(self, job: BracketAdvancementJob) -> None:
        claim_key = job.idempotency_key or job.source_fixture_id
        if not self._claim_once(self._completed_advancement_jobs, claim_key):
            return
        try:
            self.event_publisher.publish(
                DomainEvent(
                    name="competition.match.advancement.requested",
                    payload={
                        "competition_id": job.competition_id,
                        "competition_type": job.competition_type,
                        "fixture_id": job.source_fixture_id,
                        "resource_id": job.source_fixture_id,
                        "stage_code": job.stage_code,
                        "match_date": job.match_date,
                        "winner_club_id": job.winner_club_id,
                        "home_goals": job.home_goals,
                        "away_goals": job.away_goals,
                        "decided_by_penalties": job.decided_by_penalties,
                    },
                )
            )
        except Exception:
            self._release_claim(self._completed_advancement_jobs, claim_key)
            raise

    def execute_notification(self, job: NotificationJob) -> None:
        claim_key = job.idempotency_key or job.resource_id
        if not self._claim_once(self._completed_notification_jobs, claim_key):
            return
        try:
            payload = {
                **job.payload,
                "template_key": job.template_key,
                "competition_id": job.competition_id,
                "resource_id": job.resource_id,
            }
            if job.audience_key != "broadcast":
                payload.setdefault("user_id", job.audience_key)
            self.event_publisher.publish(DomainEvent(name="competition.notification", payload=payload))
        except Exception:
            self._release_claim(self._completed_notification_jobs, claim_key)
            raise

    def execute_settlement(self, job: PayoutSettlementJob) -> None:
        claim_key = job.idempotency_key or job.settlement_scope
        if not self._claim_once(self._completed_settlement_jobs, claim_key):
            return
        try:
            payload: dict[str, Any] = {
                "competition_id": job.competition_id,
                "competition_type": job.competition_type,
                "settlement_scope": job.settlement_scope,
                "settlement_date": job.settlement_date,
                "source_fixture_id": job.source_fixture_id,
            }
            if job.competition_type is CompetitionType.LEAGUE:
                state = self.league_service.get_season_state(job.settlement_scope)
                payload.update(
                    {
                        "status": state.status,
                        "completed_fixture_count": state.completed_fixture_count,
                        "total_fixture_count": state.total_fixture_count,
                        "prize_pool": asdict(state.prize_pool),
                        "champion_prize": asdict(state.champion_prize) if state.champion_prize is not None else None,
                        "top_scorer_award": asdict(state.top_scorer_award),
                        "top_assist_award": asdict(state.top_assist_award),
                    }
                )
            self.event_publisher.publish(
                DomainEvent(name="competition.season.settlement.completed", payload=payload)
            )
        except Exception:
            self._release_claim(self._completed_settlement_jobs, claim_key)
            raise

    def _apply_competition_result(self, job: MatchSimulationJob, replay_payload: MatchReplayPayloadView):
        if job.competition_type is not CompetitionType.LEAGUE or job.season_id is None:
            return None
        state = self.league_service.record_fixture_result(
            season_id=job.season_id,
            fixture_id=job.fixture_id,
            home_goals=replay_payload.summary.home_score,
            away_goals=replay_payload.summary.away_score,
        )
        contributions = tuple(
            LeaguePlayerContribution(
                player_id=player.player_id,
                player_name=player.player_name,
                club_id=player.team_id,
                goals=player.goals,
                assists=player.assists,
            )
            for player in replay_payload.summary.player_stats
            if player.goals or player.assists
        )
        if contributions:
            state = self.league_service.record_player_stats(
                season_id=job.season_id,
                player_contributions=contributions,
            )
        return state

    def _queue_live_notifications(self, job: MatchSimulationJob) -> tuple[str, ...]:
        templates: list[str] = []
        for user_id in (job.home_user_id, job.away_user_id):
            if user_id is None:
                continue
            self.dispatcher.dispatch_notification(
                competition_id=job.competition_id,
                competition_type=job.competition_type,
                template_key="match_live_now",
                audience_key=user_id,
                resource_id=job.fixture_id,
                payload={
                    **self._countdown_payload(job),
                },
            )
            templates.append("match_live_now")
        return tuple(templates)

    def _queue_result_notifications(
        self,
        job: MatchSimulationJob,
        replay_payload: MatchReplayPayloadView,
    ) -> tuple[str, ...]:
        winner_team_id = replay_payload.summary.winner_team_id
        if winner_team_id is None:
            return ()
        base_payload = {
            **self._base_payload(job),
            "home_goals": replay_payload.summary.home_score,
            "away_goals": replay_payload.summary.away_score,
        }
        templates: list[str] = []
        if job.home_user_id is not None:
            template_key = "you_won" if winner_team_id == job.home_club_id else "you_lost"
            self.dispatcher.dispatch_notification(
                competition_id=job.competition_id,
                competition_type=job.competition_type,
                template_key=template_key,
                audience_key=job.home_user_id,
                resource_id=f"{job.fixture_id}:result",
                payload=base_payload,
            )
            templates.append(template_key)
        if job.away_user_id is not None:
            template_key = "you_won" if winner_team_id == job.away_club_id else "you_lost"
            self.dispatcher.dispatch_notification(
                competition_id=job.competition_id,
                competition_type=job.competition_type,
                template_key=template_key,
                audience_key=job.away_user_id,
                resource_id=f"{job.fixture_id}:result",
                payload=base_payload,
            )
            templates.append(template_key)
        return tuple(templates)

    def _queue_league_transition_notifications(
        self,
        job: MatchSimulationJob,
        state: LeagueSeasonState,
    ) -> tuple[str, ...]:
        club_user_ids = self._league_club_user_ids.get(job.season_id or "", {})
        if not club_user_ids:
            return ()
        templates: list[str] = []
        for row in state.standings:
            user_id = club_user_ids.get(row.club_id)
            if user_id is None:
                continue
            base_payload = {
                "competition_id": job.competition_id,
                "competition_name": job.competition_name or job.competition_id,
                "resource_id": state.season_id,
                "club_id": row.club_id,
                "club_name": row.club_name,
            }
            if row.next_season_auto_entry:
                self.dispatcher.dispatch_notification(
                    competition_id=job.competition_id,
                    competition_type=job.competition_type,
                    template_key="qualified",
                    audience_key=user_id,
                    resource_id=f"{state.season_id}:qualified:{row.club_id}",
                    payload=base_payload,
                )
                templates.append("qualified")
            if row.direct_champions_league:
                self.dispatcher.dispatch_notification(
                    competition_id=job.competition_id,
                    competition_type=job.competition_type,
                    template_key="qualified_champions_league",
                    audience_key=user_id,
                    resource_id=f"{state.season_id}:ucl:{row.club_id}",
                    payload=base_payload,
                )
                templates.append("qualified_champions_league")
            if row.champions_league_playoff:
                self.dispatcher.dispatch_notification(
                    competition_id=job.competition_id,
                    competition_type=job.competition_type,
                    template_key="reached_playoff",
                    audience_key=user_id,
                    resource_id=f"{state.season_id}:playoff:{row.club_id}",
                    payload=base_payload,
                )
                templates.append("reached_playoff")
            if row.position == 1:
                self.dispatcher.dispatch_notification(
                    competition_id=job.competition_id,
                    competition_type=job.competition_type,
                    template_key="qualified_world_super_cup",
                    audience_key=user_id,
                    resource_id=f"{state.season_id}:wsc:{row.club_id}",
                    payload=base_payload,
                )
                templates.append("qualified_world_super_cup")
        return tuple(templates)

    def _queue_advancement(
        self,
        job: MatchSimulationJob,
        replay_payload: MatchReplayPayloadView,
    ) -> QueuedJobRecord | None:
        if job.competition_type is CompetitionType.LEAGUE:
            return None
        winner_team_id = replay_payload.summary.winner_team_id
        if winner_team_id is None:
            return None
        return self.dispatcher.dispatch_bracket_advancement(
            competition_id=job.competition_id,
            competition_type=job.competition_type,
            source_fixture_id=job.fixture_id,
            stage_code=job.stage_name or ("final" if job.is_final else "knockout"),
            match_date=job.match_date,
            winner_club_id=winner_team_id,
            home_goals=replay_payload.summary.home_score,
            away_goals=replay_payload.summary.away_score,
            decided_by_penalties=replay_payload.summary.decided_by_penalties,
        )

    def _build_replay_archive_payload(self, job: MatchSimulationJob, replay_payload: MatchReplayPayloadView) -> dict[str, Any]:
        scheduled_start = _resolve_kickoff(job)
        presentation_duration_minutes = max(3, ceil(replay_payload.timeline.presentation_duration_seconds / 60))
        return {
            "replay_id": f"replay:{job.fixture_id}",
            "fixture_id": job.fixture_id,
            "scheduled_start": scheduled_start,
            "started_at": scheduled_start,
            "final_whistle_at": scheduled_start,
            "live": False,
            "home_club": {
                "club_id": job.home_club_id or "home",
                "club_name": job.home_club_name or job.home_club_id or "Home Club",
            },
            "away_club": {
                "club_id": job.away_club_id or "away",
                "club_name": job.away_club_name or job.away_club_id or "Away Club",
            },
            "scoreline": {
                "home_goals": replay_payload.summary.home_score,
                "away_goals": replay_payload.summary.away_score,
            },
            "visual_identity": (
                replay_payload.visual_identity.model_dump(mode="json")
                if replay_payload.visual_identity is not None
                else None
            ),
            "participant_user_ids": [
                user_id
                for user_id in (job.home_user_id, job.away_user_id)
                if user_id is not None
            ],
            "competition_context": {
                "competition_id": job.competition_id,
                "competition_type": job.competition_type,
                "competition_name": job.competition_name or job.competition_id,
                "season_id": job.season_id,
                "stage_name": job.stage_name,
                "round_number": job.round_number,
                "is_final": job.is_final,
                "is_cup_match": job.is_cup_match,
                "competition_allows_public": job.is_final or job.round_number >= 3,
                "allow_early_round_public": False,
                "presentation_duration_minutes": presentation_duration_minutes,
                "replay_visibility": job.replay_visibility,
            },
            "timeline": self._build_replay_timeline(replay_payload),
        }

    def _build_replay_timeline(self, replay_payload: MatchReplayPayloadView) -> list[dict[str, Any]]:
        timeline: list[dict[str, Any]] = []
        for event in replay_payload.timeline.events:
            replay_event_type = self._map_replay_event_type(event.event_type)
            if replay_event_type is None:
                continue
            timeline.append(
                {
                    "event_id": event.event_id,
                    "minute": event.minute,
                    "event_type": replay_event_type,
                    "club_id": event.team_id,
                    "club_name": event.team_name,
                    "player_id": event.primary_player.player_id if event.primary_player is not None else None,
                    "player_name": event.primary_player.player_name if event.primary_player is not None else None,
                    "secondary_player_id": event.secondary_player.player_id if event.secondary_player is not None else None,
                    "secondary_player_name": event.secondary_player.player_name if event.secondary_player is not None else None,
                    "description": event.commentary,
                    "home_score": event.home_score,
                    "away_score": event.away_score,
                    "is_penalty": event.event_type in {MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_MISS},
                }
            )
            if event.event_type is MatchEventType.GOAL and event.secondary_player is not None:
                timeline.append(
                    {
                        "event_id": f"{event.event_id}:assist",
                        "minute": event.minute,
                        "event_type": "assists",
                        "club_id": event.team_id,
                        "club_name": event.team_name,
                        "player_id": event.secondary_player.player_id,
                        "player_name": event.secondary_player.player_name,
                        "secondary_player_id": event.primary_player.player_id if event.primary_player is not None else None,
                        "secondary_player_name": event.primary_player.player_name if event.primary_player is not None else None,
                        "description": f"Assist for {event.primary_player.player_name}" if event.primary_player is not None else "Assist",
                        "home_score": event.home_score,
                        "away_score": event.away_score,
                    }
                )
        return timeline

    @staticmethod
    def _map_replay_event_type(event_type: MatchEventType) -> str | None:
        mapping = {
            MatchEventType.GOAL: "goals",
            MatchEventType.MISSED_CHANCE: "missed_chances",
            MatchEventType.WOODWORK: "missed_chances",
            MatchEventType.DOUBLE_SAVE: "missed_chances",
            MatchEventType.YELLOW_CARD: "yellow_cards",
            MatchEventType.RED_CARD: "red_cards",
            MatchEventType.SUBSTITUTION: "substitutions",
            MatchEventType.INJURY: "injuries",
            MatchEventType.PENALTY_GOAL: "penalties",
            MatchEventType.PENALTY_MISS: "penalties",
        }
        return mapping.get(event_type)

    @staticmethod
    def _base_payload(job: MatchSimulationJob) -> dict[str, Any]:
        return {
            "competition_id": job.competition_id,
            "competition_name": job.competition_name or job.competition_id,
            "fixture_id": job.fixture_id,
            "resource_id": job.fixture_id,
            "home_club_name": job.home_club_name or job.home_club_id or "Home Club",
            "away_club_name": job.away_club_name or job.away_club_id or "Away Club",
        }

    def _countdown_payload(
        self,
        job: MatchSimulationJob,
        *,
        include_user_ids: bool = False,
    ) -> dict[str, Any]:
        payload = {
            **self._base_payload(job),
            "scheduled_start": _resolve_kickoff(job),
            "home_club": {
                "club_id": job.home_club_id or "home",
                "club_name": job.home_club_name or job.home_club_id or "Home Club",
            },
            "away_club": {
                "club_id": job.away_club_id or "away",
                "club_name": job.away_club_name or job.away_club_id or "Away Club",
            },
            "competition_context": {
                "competition_id": job.competition_id,
                "competition_type": job.competition_type,
                "competition_name": job.competition_name or job.competition_id,
                "season_id": job.season_id,
                "stage_name": job.stage_name,
                "round_number": job.round_number,
                "is_final": job.is_final,
                "is_cup_match": job.is_cup_match,
                "competition_allows_public": job.is_final or job.round_number >= 3,
                "allow_early_round_public": False,
                "replay_visibility": job.replay_visibility,
            },
        }
        if include_user_ids:
            user_ids = [
                user_id
                for user_id in (job.home_user_id, job.away_user_id)
                if user_id is not None
            ]
            if user_ids:
                payload["user_ids"] = user_ids
        return payload

    def _publish_match_lifecycle_event(
        self,
        name: str,
        job: MatchSimulationJob,
        *,
        replay_payload: MatchReplayPayloadView | None = None,
        state: LeagueSeasonState | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            **self._countdown_payload(job, include_user_ids=True),
            "execution_source": "local_match_execution_worker",
            "idempotency_key": job.idempotency_key,
            "simulation_seed": job.simulation_seed,
            "match_status": getattr(job.match_status, "value", job.match_status),
        }
        if replay_payload is not None:
            payload.update(self._replay_summary_payload(job, replay_payload))
        if state is not None:
            payload.update(
                {
                    "season_status": getattr(state.status, "value", state.status),
                    "completed_fixture_count": state.completed_fixture_count,
                    "total_fixture_count": state.total_fixture_count,
                    "standings_leader_club_id": state.standings[0].club_id if state.standings else None,
                    "standings_leader_points": state.standings[0].points if state.standings else None,
                }
            )
        if extra:
            payload.update(extra)
        self.event_publisher.publish(DomainEvent(name=name, payload=payload))

    def _replay_summary_payload(
        self,
        job: MatchSimulationJob,
        replay_payload: MatchReplayPayloadView,
    ) -> dict[str, Any]:
        return {
            "replay_id": f"replay:{job.fixture_id}",
            "home_goals": replay_payload.summary.home_score,
            "away_goals": replay_payload.summary.away_score,
            "winner_team_id": replay_payload.summary.winner_team_id,
            "decided_by_penalties": replay_payload.summary.decided_by_penalties,
            "home_penalty_score": replay_payload.summary.home_penalty_score,
            "away_penalty_score": replay_payload.summary.away_penalty_score,
            "presentation_duration_seconds": replay_payload.timeline.presentation_duration_seconds,
            "timeline_event_count": len(replay_payload.timeline.events),
        }

    def _build_key_moment_breakdown(self, replay_payload: MatchReplayPayloadView) -> dict[str, int]:
        breakdown: dict[str, int] = {}
        for event in replay_payload.timeline.events:
            replay_event_type = self._map_replay_event_type(event.event_type)
            if replay_event_type is None:
                continue
            breakdown[replay_event_type] = breakdown.get(replay_event_type, 0) + 1
        return breakdown

    def _claim_once(self, bucket: set[str], key: str) -> bool:
        with self._lock:
            if key in bucket:
                return False
            bucket.add(key)
            return True

    def _release_claim(self, bucket: set[str], key: str) -> None:
        with self._lock:
            bucket.discard(key)


def ensure_local_match_execution_runtime(app: FastAPI) -> LocalMatchExecutionWorker:
    session_factory = getattr(app.state, "session_factory", None)
    queue_publisher = getattr(app.state, "competition_queue_publisher", None)
    if queue_publisher is None:
        queue_publisher = InMemoryQueuePublisher(event_publisher=app.state.event_publisher)
        app.state.competition_queue_publisher = queue_publisher

    dispatcher = getattr(app.state, "match_dispatcher", None)
    if dispatcher is None:
        dispatcher = MatchDispatcher(queue_publisher=queue_publisher)
        app.state.match_dispatcher = dispatcher

    worker = getattr(app.state, "match_execution_worker", None)
    if worker is None:
        worker = LocalMatchExecutionWorker(
            dispatcher=dispatcher,
            event_publisher=app.state.event_publisher,
            session_factory=session_factory,
            team_factory=SyntheticSquadFactory(session_factory=session_factory),
        )
        app.state.match_execution_worker = worker
    else:
        worker.session_factory = session_factory
        worker.team_factory.session_factory = session_factory

    if not getattr(app.state, "_match_execution_worker_subscribed", False):
        app.state.event_publisher.subscribe(worker.handle_event)
        app.state._match_execution_worker_subscribed = True

    if not hasattr(app.state, "league_match_execution"):
        app.state.league_match_execution = LeagueFixtureExecutionService(
            dispatcher=dispatcher,
            event_publisher=app.state.event_publisher,
            execution_worker=worker,
        )
    return worker


def _resolve_league_window(window_number: int) -> FixtureWindow:
    senior_windows = FixtureWindow.senior_windows()
    index = max(1, min(window_number, len(senior_windows))) - 1
    return senior_windows[index]


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _resolve_kickoff(job: MatchSimulationJob) -> datetime:
    if job.scheduled_kickoff_at is not None:
        return _normalize_timestamp(job.scheduled_kickoff_at)
    return datetime(job.match_date.year, job.match_date.month, job.match_date.day, 12, 0, tzinfo=UTC)
