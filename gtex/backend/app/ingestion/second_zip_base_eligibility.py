from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any, Iterable, Mapping

from app.ingestion.normalizers import clean_name, parse_date

SECOND_ZIP_MINIMUM_LAST_SEASON = 2024
SECOND_ZIP_MAXIMUM_AGE_YEARS = 40


def _normalize_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = clean_name(str(value))
    if normalized is None or normalized.casefold() == "null":
        return None
    return normalized


def _parse_last_season(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class SecondZipPlayersCsvRow:
    raw_payload: dict[str, Any]
    name: str | None
    position: str | None
    sub_position: str | None
    date_of_birth_text: str | None
    date_of_birth: date | None
    last_season_text: str | None
    last_season: int | None


class SecondZipBaseExclusionReason(StrEnum):
    MISSING_NAME = "missing_name"
    MISSING_POSITION = "missing_position"
    MISSING_SUB_POSITION = "missing_sub_position"
    MISSING_DATE_OF_BIRTH = "missing_date_of_birth"
    INVALID_DATE_OF_BIRTH = "invalid_date_of_birth"
    MISSING_LAST_SEASON = "missing_last_season"
    INVALID_LAST_SEASON = "invalid_last_season"
    LAST_SEASON_BEFORE_2024 = "last_season_before_2024"
    AGE_OVER_40 = "age_over_40"


@dataclass(frozen=True, slots=True)
class SecondZipBaseEligibilityPolicy:
    reference_date: date
    minimum_last_season: int = SECOND_ZIP_MINIMUM_LAST_SEASON
    maximum_age_years: int = SECOND_ZIP_MAXIMUM_AGE_YEARS


@dataclass(frozen=True, slots=True)
class SecondZipBaseEligibilityResult:
    row: SecondZipPlayersCsvRow
    eligible: bool
    age_years: int | None
    exclusion_reasons: tuple[SecondZipBaseExclusionReason, ...] = ()

    @property
    def exclusion_reason_codes(self) -> tuple[str, ...]:
        return tuple(reason.value for reason in self.exclusion_reasons)

    def to_dict(self) -> dict[str, object]:
        return {
            "eligible": self.eligible,
            "exclusion_reasons": list(self.exclusion_reason_codes),
            "age_years": self.age_years,
            "name": self.row.name,
            "position": self.row.position,
            "sub_position": self.row.sub_position,
            "date_of_birth": self.row.date_of_birth.isoformat() if self.row.date_of_birth is not None else None,
            "last_season": self.row.last_season,
        }


def parse_second_zip_players_csv_row(raw_payload: Mapping[str, Any]) -> SecondZipPlayersCsvRow:
    date_of_birth_text = _normalize_text(raw_payload.get("date_of_birth"))
    last_season_text = _normalize_text(raw_payload.get("last_season"))
    return SecondZipPlayersCsvRow(
        raw_payload=dict(raw_payload),
        name=_normalize_text(raw_payload.get("name")),
        position=_normalize_text(raw_payload.get("position")),
        sub_position=_normalize_text(raw_payload.get("sub_position")),
        date_of_birth_text=date_of_birth_text,
        date_of_birth=parse_date(date_of_birth_text),
        last_season_text=last_season_text,
        last_season=_parse_last_season(last_season_text),
    )


def has_name(row: SecondZipPlayersCsvRow) -> bool:
    return row.name is not None


def has_position(row: SecondZipPlayersCsvRow) -> bool:
    return row.position is not None


def has_sub_position(row: SecondZipPlayersCsvRow) -> bool:
    return row.sub_position is not None


def has_date_of_birth(row: SecondZipPlayersCsvRow) -> bool:
    return row.date_of_birth_text is not None


def has_last_season(row: SecondZipPlayersCsvRow) -> bool:
    return row.last_season_text is not None


def meets_last_season_floor(
    row: SecondZipPlayersCsvRow,
    *,
    minimum_last_season: int = SECOND_ZIP_MINIMUM_LAST_SEASON,
) -> bool:
    return row.last_season is not None and row.last_season >= minimum_last_season


def derive_age_years(row: SecondZipPlayersCsvRow, *, reference_date: date) -> int | None:
    if row.date_of_birth is None:
        return None
    age_years = reference_date.year - row.date_of_birth.year
    if (reference_date.month, reference_date.day) < (row.date_of_birth.month, row.date_of_birth.day):
        age_years -= 1
    return age_years


def is_age_eligible(
    row: SecondZipPlayersCsvRow,
    *,
    reference_date: date,
    maximum_age_years: int = SECOND_ZIP_MAXIMUM_AGE_YEARS,
) -> bool:
    age_years = derive_age_years(row, reference_date=reference_date)
    return age_years is not None and 0 <= age_years <= maximum_age_years


def evaluate_second_zip_players_csv_row(
    raw_payload: Mapping[str, Any] | SecondZipPlayersCsvRow,
    *,
    policy: SecondZipBaseEligibilityPolicy,
) -> SecondZipBaseEligibilityResult:
    row = (
        raw_payload
        if isinstance(raw_payload, SecondZipPlayersCsvRow)
        else parse_second_zip_players_csv_row(raw_payload)
    )
    exclusion_reasons: list[SecondZipBaseExclusionReason] = []

    if not has_name(row):
        exclusion_reasons.append(SecondZipBaseExclusionReason.MISSING_NAME)
    if not has_position(row):
        exclusion_reasons.append(SecondZipBaseExclusionReason.MISSING_POSITION)
    if not has_sub_position(row):
        exclusion_reasons.append(SecondZipBaseExclusionReason.MISSING_SUB_POSITION)

    if not has_date_of_birth(row):
        exclusion_reasons.append(SecondZipBaseExclusionReason.MISSING_DATE_OF_BIRTH)
    elif row.date_of_birth is None:
        exclusion_reasons.append(SecondZipBaseExclusionReason.INVALID_DATE_OF_BIRTH)

    if not has_last_season(row):
        exclusion_reasons.append(SecondZipBaseExclusionReason.MISSING_LAST_SEASON)
    elif row.last_season is None:
        exclusion_reasons.append(SecondZipBaseExclusionReason.INVALID_LAST_SEASON)
    elif not meets_last_season_floor(row, minimum_last_season=policy.minimum_last_season):
        exclusion_reasons.append(SecondZipBaseExclusionReason.LAST_SEASON_BEFORE_2024)

    age_years = derive_age_years(row, reference_date=policy.reference_date)
    if age_years is not None and age_years < 0:
        exclusion_reasons.append(SecondZipBaseExclusionReason.INVALID_DATE_OF_BIRTH)
    elif age_years is not None and age_years > policy.maximum_age_years:
        exclusion_reasons.append(SecondZipBaseExclusionReason.AGE_OVER_40)

    return SecondZipBaseEligibilityResult(
        row=row,
        eligible=not exclusion_reasons,
        age_years=age_years,
        exclusion_reasons=tuple(dict.fromkeys(exclusion_reasons)),
    )


def evaluate_second_zip_players_csv_rows(
    rows: Iterable[Mapping[str, Any] | SecondZipPlayersCsvRow],
    *,
    policy: SecondZipBaseEligibilityPolicy,
) -> tuple[SecondZipBaseEligibilityResult, ...]:
    return tuple(
        evaluate_second_zip_players_csv_row(row, policy=policy)
        for row in rows
    )


__all__ = [
    "SECOND_ZIP_MAXIMUM_AGE_YEARS",
    "SECOND_ZIP_MINIMUM_LAST_SEASON",
    "SecondZipBaseEligibilityPolicy",
    "SecondZipBaseEligibilityResult",
    "SecondZipBaseExclusionReason",
    "SecondZipPlayersCsvRow",
    "derive_age_years",
    "evaluate_second_zip_players_csv_row",
    "evaluate_second_zip_players_csv_rows",
    "has_date_of_birth",
    "has_last_season",
    "has_name",
    "has_position",
    "has_sub_position",
    "is_age_eligible",
    "meets_last_season_floor",
    "parse_second_zip_players_csv_row",
]
