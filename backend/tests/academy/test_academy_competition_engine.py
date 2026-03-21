from __future__ import annotations

from datetime import date

from app.academy.models import AcademyAwardsLeaders, AcademyClubRegistrationRequest, AcademySeasonRequest
from app.academy.services import AcademyCompetitionService
from app.academy.services.competition_engine import AcademyCompetitionEngineService
from app.common.enums.fixture_window import FixtureWindow
from app.config.competition_constants import LEAGUE_GROUP_SIZE


def test_academy_competition_engine_preserves_open_window_slot_sequences() -> None:
    projection = AcademyCompetitionService().build_season_projection(_build_request())

    batch = AcademyCompetitionEngineService().build_batch(projection)

    assert len(batch.fixtures) == len(projection.fixtures)
    assert batch.fixtures[0].window == FixtureWindow.ACADEMY_OPEN
    assert batch.fixtures[0].slot_sequence == projection.fixtures[0].window_number
    assert max(fixture.slot_sequence for fixture in batch.fixtures) == 6
    assert batch.dispatch_requests[0].competition_name == "Academy Competition"


def _build_request() -> AcademySeasonRequest:
    clubs = tuple(
        AcademyClubRegistrationRequest(
            club_id=f"club-{index + 1:02d}",
            club_name=f"Academy Club {index + 1:02d}",
            senior_buy_in_tier=(1000, 800, 500, 300, 150, 25)[index % 6],
        )
        for index in range(LEAGUE_GROUP_SIZE)
    )
    return AcademySeasonRequest(
        season_id="academy-engine",
        start_date=date(2026, 1, 1),
        clubs=clubs,
        awards_leaders=AcademyAwardsLeaders(
            top_scorer_club_id="club-01",
            top_assist_club_id="club-02",
        ),
    )
