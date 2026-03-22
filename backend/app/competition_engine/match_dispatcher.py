from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.common.enums.competition_type import CompetitionType
from app.common.schemas.competition import (
    CompetitionDispatchRequest,
    CompetitionEngineBatch,
    ScheduledFixture,
)

from .queue_contracts import (
    BracketAdvancementJob,
    InMemoryQueuePublisher,
    MatchSimulationJob,
    NotificationJob,
    PayoutSettlementJob,
    QueuePublisher,
    QueuedJobRecord,
)


def scale_strength_rating(
    value: int | None,
    *,
    minimum: int,
    maximum: int,
) -> int | None:
    if value is None:
        return None
    if minimum >= maximum:
        return 100
    scaled = 1 + round(((value - minimum) / (maximum - minimum)) * 99)
    return max(1, min(100, scaled))


@dataclass(slots=True, frozen=True)
class MatchDispatchContext:
    is_final: bool = False
    season_id: str | None = None
    competition_name: str | None = None
    stage_name: str | None = None
    scheduled_kickoff_at: datetime | None = None
    simulation_seed: int | None = None
    home_club_name: str | None = None
    away_club_name: str | None = None
    home_strength_rating: int | None = None
    away_strength_rating: int | None = None
    home_user_id: str | None = None
    away_user_id: str | None = None


@dataclass(slots=True)
class MatchDispatcher:
    queue_publisher: QueuePublisher = field(default_factory=InMemoryQueuePublisher)

    def dispatch_request(
        self,
        request: CompetitionDispatchRequest,
    ) -> QueuedJobRecord:
        return self.dispatch_match_simulation(
            request.fixture,
            is_final=request.is_final,
            season_id=request.season_id,
            competition_name=request.competition_name,
            stage_name=request.stage_name,
            scheduled_kickoff_at=request.scheduled_kickoff_at,
            simulation_seed=request.simulation_seed,
            home_club_name=request.home_club_name,
            away_club_name=request.away_club_name,
            home_strength_rating=request.home_strength_rating,
            away_strength_rating=request.away_strength_rating,
            home_user_id=request.home_user_id,
            away_user_id=request.away_user_id,
        )

    def dispatch_requests(
        self,
        requests: tuple[CompetitionDispatchRequest, ...],
    ) -> tuple[QueuedJobRecord, ...]:
        return tuple(self.dispatch_request(request) for request in requests)

    def dispatch_batch(self, batch: CompetitionEngineBatch) -> tuple[QueuedJobRecord, ...]:
        return self.dispatch_requests(batch.dispatch_requests)

    def dispatch_match_simulation(
        self,
        fixture: ScheduledFixture,
        *,
        is_final: bool = False,
        season_id: str | None = None,
        competition_name: str | None = None,
        stage_name: str | None = None,
        scheduled_kickoff_at: datetime | None = None,
        simulation_seed: int | None = None,
        home_club_name: str | None = None,
        away_club_name: str | None = None,
        home_strength_rating: int | None = None,
        away_strength_rating: int | None = None,
        home_user_id: str | None = None,
        away_user_id: str | None = None,
    ) -> QueuedJobRecord:
        job = MatchSimulationJob(
            fixture_id=fixture.fixture_id,
            competition_id=fixture.competition_id,
            competition_type=fixture.competition_type,
            match_date=fixture.match_date,
            window=fixture.window,
            slot_sequence=fixture.slot_sequence,
            season_id=season_id,
            competition_name=competition_name,
            stage_name=stage_name or fixture.stage_name,
            round_number=fixture.round_number,
            scheduled_kickoff_at=scheduled_kickoff_at,
            simulation_seed=simulation_seed,
            home_club_id=fixture.home_club_id,
            home_club_name=home_club_name,
            home_strength_rating=home_strength_rating,
            home_user_id=home_user_id,
            away_club_id=fixture.away_club_id,
            away_club_name=away_club_name,
            away_strength_rating=away_strength_rating,
            away_user_id=away_user_id,
            replay_visibility=fixture.replay_visibility,
            is_cup_match=fixture.is_cup_match,
            allow_penalties=fixture.allow_penalties,
            is_final=is_final,
        )
        return self.queue_publisher.publish(job)

    def dispatch_match_simulations(
        self,
        fixtures: tuple[ScheduledFixture, ...],
        *,
        default_context: MatchDispatchContext | None = None,
        fixture_context_by_id: dict[str, MatchDispatchContext] | None = None,
    ) -> tuple[QueuedJobRecord, ...]:
        shared_context = default_context or MatchDispatchContext()
        fixture_overrides = fixture_context_by_id or {}
        records: list[QueuedJobRecord] = []

        for fixture in fixtures:
            context = fixture_overrides.get(fixture.fixture_id, shared_context)
            records.append(
                self.dispatch_match_simulation(
                    fixture,
                    is_final=context.is_final,
                    season_id=context.season_id,
                    competition_name=context.competition_name,
                    stage_name=context.stage_name,
                    scheduled_kickoff_at=context.scheduled_kickoff_at,
                    simulation_seed=context.simulation_seed,
                    home_club_name=context.home_club_name,
                    away_club_name=context.away_club_name,
                    home_strength_rating=context.home_strength_rating,
                    away_strength_rating=context.away_strength_rating,
                    home_user_id=context.home_user_id,
                    away_user_id=context.away_user_id,
                )
            )

        return tuple(records)

    def dispatch_bracket_advancement(
        self,
        *,
        competition_id: str,
        competition_type: CompetitionType,
        source_fixture_id: str,
        stage_code: str,
        match_date: date,
        winner_club_id: str | None = None,
        home_goals: int | None = None,
        away_goals: int | None = None,
        decided_by_penalties: bool = False,
    ) -> QueuedJobRecord:
        return self.queue_publisher.publish(
            BracketAdvancementJob(
                competition_id=competition_id,
                competition_type=competition_type,
                source_fixture_id=source_fixture_id,
                stage_code=stage_code,
                match_date=match_date,
                winner_club_id=winner_club_id,
                home_goals=home_goals,
                away_goals=away_goals,
                decided_by_penalties=decided_by_penalties,
            )
        )

    def dispatch_payout_settlement(
        self,
        *,
        competition_id: str,
        competition_type: CompetitionType,
        settlement_scope: str,
        settlement_date: date,
        source_fixture_id: str | None = None,
    ) -> QueuedJobRecord:
        return self.queue_publisher.publish(
            PayoutSettlementJob(
                competition_id=competition_id,
                competition_type=competition_type,
                settlement_scope=settlement_scope,
                settlement_date=settlement_date,
                source_fixture_id=source_fixture_id,
            )
        )

    def dispatch_notification(
        self,
        *,
        competition_id: str,
        competition_type: CompetitionType,
        template_key: str,
        audience_key: str,
        resource_id: str,
        payload: dict[str, Any] | None = None,
    ) -> QueuedJobRecord:
        return self.queue_publisher.publish(
            NotificationJob(
                competition_id=competition_id,
                competition_type=competition_type,
                template_key=template_key,
                audience_key=audience_key,
                resource_id=resource_id,
                payload=payload or {},
            )
        )
