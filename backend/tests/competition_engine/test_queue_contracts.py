from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.replay_visibility import ReplayVisibility
from app.competition_engine.queue_contracts import (
    InMemoryQueuePublisher,
    MatchSimulationJob,
)


def test_match_simulation_job_validates_supported_payload_rules() -> None:
    job = MatchSimulationJob(
        fixture_id="fixture-1",
        competition_id="fast-cup-alpha",
        competition_type=CompetitionType.FAST_CUP,
        match_date=date(2026, 5, 2),
        window=FixtureWindow.FAST_CUP_OPEN,
        replay_visibility=ReplayVisibility.PUBLIC,
        is_cup_match=True,
        allow_penalties=True,
        key_moments=(
            "goals",
            "assists",
            "missed_chances",
            "yellow_cards",
            "red_cards",
            "substitutions",
            "injuries",
            "penalties",
        ),
    )

    assert job.idempotency_key == "match-simulation:fixture-1:2026-05-02:fast_cup_open:1"

    with pytest.raises(ValidationError, match="Penalty shootouts"):
        MatchSimulationJob(
            fixture_id="fixture-2",
            competition_id="league-alpha",
            competition_type=CompetitionType.LEAGUE,
            match_date=date(2026, 5, 2),
            window=FixtureWindow.SENIOR_1,
            allow_penalties=True,
        )

    with pytest.raises(ValidationError, match="Unsupported match moments"):
        MatchSimulationJob(
            fixture_id="fixture-3",
            competition_id="league-alpha",
            competition_type=CompetitionType.LEAGUE,
            match_date=date(2026, 5, 2),
            window=FixtureWindow.SENIOR_1,
            key_moments=("goals", "extra_time"),
        )


def test_queue_publisher_is_idempotent_by_job_key() -> None:
    publisher = InMemoryQueuePublisher()
    job = MatchSimulationJob(
        fixture_id="fixture-4",
        competition_id="academy-alpha",
        competition_type=CompetitionType.ACADEMY,
        match_date=date(2026, 5, 3),
        window=FixtureWindow.ACADEMY_OPEN,
    )

    first = publisher.publish(job)
    second = publisher.publish(job)

    assert first.idempotency_key == second.idempotency_key
    assert len(publisher.list_published()) == 1
