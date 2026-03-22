"""Calendar engine smoke placeholders.

These lightweight tests exist so the new module surface is discoverable in the repo.
Runtime execution depends on the project SQLAlchemy/FastAPI test environment.
"""

from app.calendar_engine.schemas import CalendarSeasonCreateRequest, HostedCompetitionLaunchRequest


def test_calendar_engine_schema_smoke() -> None:
    season = CalendarSeasonCreateRequest(
        season_key="gtex-2027",
        title="GTEX 2027",
        starts_on="2027-01-01",
        ends_on="2027-12-31",
    )
    launch = HostedCompetitionLaunchRequest()
    assert season.season_key == "gtex-2027"
    assert launch.preferred_family == "hosted"
