from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from app.fast_cups.models.domain import (
    ClubCompetitionWindow,
    FastCup,
    FastCupBracket,
    FastCupDivision,
    FastCupEntrant,
    FastCupResultSummary,
    FastCupStateError,
    FastCupStatus,
    RegistrationCountdown,
)
from app.fast_cups.repositories.base import FastCupRepository
from app.fast_cups.repositories.database import DatabaseFastCupRepository
from app.fast_cups.repositories.memory import InMemoryFastCupRepository
from app.fast_cups.services.bracket import FastCupBracketService
from app.fast_cups.services.countdown import RegistrationCountdownService
from app.fast_cups.services.creation import RecurringFastCupCreationService
from app.fast_cups.services.payouts import FastCupRewardPayoutService
from app.fast_cups.services.registration import FastCupRegistrationService


class FastCupEcosystemService:
    def __init__(
        self,
        *,
        repository: FastCupRepository | None = None,
        creation_service: RecurringFastCupCreationService | None = None,
        registration_service: FastCupRegistrationService | None = None,
        bracket_service: FastCupBracketService | None = None,
        countdown_service: RegistrationCountdownService | None = None,
        reward_service: FastCupRewardPayoutService | None = None,
    ) -> None:
        self.repository = repository or InMemoryFastCupRepository()
        self.creation_service = creation_service or RecurringFastCupCreationService(self.repository)
        self.registration_service = registration_service or FastCupRegistrationService()
        self.bracket_service = bracket_service or FastCupBracketService()
        self.countdown_service = countdown_service or RegistrationCountdownService()
        self.reward_service = reward_service or FastCupRewardPayoutService()

    def list_upcoming_cups(
        self,
        *,
        now: datetime,
        division: FastCupDivision | None = None,
        size: int | None = None,
        horizon_intervals: int = 4,
    ) -> tuple[FastCup, ...]:
        current_time = _normalize_timestamp(now)
        self.creation_service.ensure_upcoming_cups(now=current_time, horizon_intervals=horizon_intervals)
        return self.repository.list_upcoming(now=current_time, division=division, size=size)

    def join_cup(
        self,
        *,
        cup_id: str,
        entrant: FastCupEntrant,
        existing_windows: tuple[ClubCompetitionWindow, ...] = (),
        now: datetime,
    ) -> FastCup:
        cup = self.repository.get(cup_id)
        updated = self.registration_service.join_cup(
            cup=cup,
            entrant=entrant,
            existing_windows=existing_windows,
            now=_normalize_timestamp(now),
        )
        return self.repository.save(updated)

    def get_bracket(self, *, cup_id: str) -> FastCupBracket:
        cup = self.repository.get(cup_id)
        if len(cup.entrants) != cup.size:
            raise FastCupStateError("Bracket is unavailable until the fast cup reaches capacity.")
        if cup.result_summary is not None and cup.bracket is not None:
            return cup.bracket
        if cup.bracket is None:
            seeded_bracket = self.bracket_service.build_seeded_bracket(cup)
            cup = self.repository.save(replace(cup, bracket=seeded_bracket, status=FastCupStatus.READY))
        return cup.bracket

    def get_countdown(self, *, cup_id: str, now: datetime) -> RegistrationCountdown:
        cup = self.repository.get(cup_id)
        return self.countdown_service.build(cup=cup, now=_normalize_timestamp(now))

    def get_result_summary(self, *, cup_id: str, now: datetime) -> FastCupResultSummary:
        current_time = _normalize_timestamp(now)
        cup = self.repository.get(cup_id)
        if cup.result_summary is not None:
            return cup.result_summary
        if len(cup.entrants) != cup.size:
            raise FastCupStateError("Result summary is unavailable until the fast cup reaches capacity.")
        if current_time < cup.slot.kickoff_at:
            raise FastCupStateError("Result summary is unavailable before kickoff.")
        bracket = self.bracket_service.simulate_bracket(cup)
        result_summary = self.reward_service.build_result_summary(
            cup=cup,
            bracket=bracket,
            concluded_at=min(current_time, cup.slot.expected_completion_at),
        )
        updated = replace(cup, bracket=bracket, result_summary=result_summary, status=FastCupStatus.COMPLETED)
        self.repository.save(updated)
        return result_summary


def build_default_fast_cup_ecosystem() -> FastCupEcosystemService:
    repository = InMemoryFastCupRepository()
    return FastCupEcosystemService(repository=repository)


def build_fast_cup_ecosystem_for_session(
    session_factory: sessionmaker[Session] | None,
) -> FastCupEcosystemService:
    if session_factory is None:
        return build_default_fast_cup_ecosystem()
    return FastCupEcosystemService(repository=DatabaseFastCupRepository(session_factory))


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
