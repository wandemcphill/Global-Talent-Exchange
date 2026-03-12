from __future__ import annotations

from datetime import date, datetime, time, timezone, tzinfo
from enum import StrEnum


class FixtureWindow(StrEnum):
    SENIOR_1 = "senior_1"
    SENIOR_2 = "senior_2"
    SENIOR_3 = "senior_3"
    SENIOR_4 = "senior_4"
    SENIOR_5 = "senior_5"
    SENIOR_6 = "senior_6"
    ACADEMY_OPEN = "academy_open"
    FAST_CUP_OPEN = "fast_cup_open"

    @classmethod
    def senior_windows(cls) -> tuple["FixtureWindow", ...]:
        return (
            cls.SENIOR_1,
            cls.SENIOR_2,
            cls.SENIOR_3,
            cls.SENIOR_4,
            cls.SENIOR_5,
            cls.SENIOR_6,
        )

    @classmethod
    def open_windows(cls) -> tuple["FixtureWindow", ...]:
        return (
            cls.ACADEMY_OPEN,
            cls.FAST_CUP_OPEN,
        )

    @property
    def is_senior(self) -> bool:
        return self in self.senior_windows()

    @property
    def display_sequence(self) -> int:
        if self.is_senior:
            return self.senior_windows().index(self) + 1
        return 1

    @property
    def kickoff_hour(self) -> int:
        return {
            FixtureWindow.SENIOR_1: 9,
            FixtureWindow.SENIOR_2: 11,
            FixtureWindow.SENIOR_3: 13,
            FixtureWindow.SENIOR_4: 15,
            FixtureWindow.SENIOR_5: 17,
            FixtureWindow.SENIOR_6: 19,
            FixtureWindow.ACADEMY_OPEN: 9,
            FixtureWindow.FAST_CUP_OPEN: 9,
        }[self]

    @property
    def kickoff_time(self) -> time:
        return time(hour=self.kickoff_hour)

    def kickoff_at(self, match_date: date, *, tzinfo: tzinfo | None = timezone.utc) -> datetime:
        if tzinfo is None:
            return datetime.combine(match_date, self.kickoff_time)
        return datetime.combine(match_date, self.kickoff_time, tzinfo=tzinfo)

    @property
    def supports_slot_sequence(self) -> bool:
        return not self.is_senior

    @classmethod
    def from_display_sequence(cls, sequence: int) -> "FixtureWindow":
        if sequence < 1 or sequence > len(cls.senior_windows()):
            raise ValueError(f"Unsupported fixture window sequence: {sequence}")
        return cls.senior_windows()[sequence - 1]
