from __future__ import annotations

from enum import StrEnum


class AcademyProgramType(StrEnum):
    FUNDAMENTALS = "fundamentals"
    ELITE_DEVELOPMENT = "elite_development"
    TACTICAL_PROGRAM = "tactical_program"
    PHYSICAL_PROGRAM = "physical_program"
    FINISHING_SCHOOL = "finishing_school"
    GOALKEEPER_PROGRAM = "goalkeeper_program"


__all__ = ["AcademyProgramType"]
