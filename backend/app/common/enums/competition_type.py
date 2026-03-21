from __future__ import annotations

from enum import StrEnum


class CompetitionType(StrEnum):
    LEAGUE = "league"
    CHAMPIONS_LEAGUE = "champions_league"
    WORLD_SUPER_CUP = "world_super_cup"
    ACADEMY = "academy"
    FAST_CUP = "fast_cup"

    @property
    def uses_senior_windows(self) -> bool:
        return self in {
            CompetitionType.LEAGUE,
            CompetitionType.CHAMPIONS_LEAGUE,
            CompetitionType.WORLD_SUPER_CUP,
        }

    @property
    def remains_active_during_world_super_cup(self) -> bool:
        return self in {CompetitionType.ACADEMY, CompetitionType.FAST_CUP}

    @property
    def default_fixture_windows(self) -> tuple["FixtureWindow", ...]:
        from app.common.enums.fixture_window import FixtureWindow
        from app.config.competition_constants import LEAGUE_MATCH_WINDOWS_PER_DAY

        if self.uses_senior_windows:
            return FixtureWindow.senior_windows()[:LEAGUE_MATCH_WINDOWS_PER_DAY]
        if self is CompetitionType.ACADEMY:
            return (FixtureWindow.ACADEMY_OPEN,)
        return (FixtureWindow.FAST_CUP_OPEN,)
