from __future__ import annotations

from datetime import date

import pytest

from app.ingestion.second_zip_base_eligibility import (
    SECOND_ZIP_MAXIMUM_AGE_YEARS,
    SECOND_ZIP_MINIMUM_LAST_SEASON,
    SecondZipBaseEligibilityPolicy,
    SecondZipBaseExclusionReason,
    derive_age_years,
    evaluate_second_zip_players_csv_row,
    has_date_of_birth,
    has_name,
    has_position,
    has_sub_position,
    is_age_eligible,
    meets_last_season_floor,
    parse_second_zip_players_csv_row,
)


REFERENCE_DATE = date(2026, 3, 23)
POLICY = SecondZipBaseEligibilityPolicy(reference_date=REFERENCE_DATE)


def _row(**overrides: object) -> dict[str, object]:
    row = {
        "player_id": "1",
        "name": "Victor Osimhen",
        "position": "Attack",
        "sub_position": "Centre-Forward",
        "date_of_birth": "1998-12-29 00:00:00",
        "last_season": "2024",
    }
    row.update(overrides)
    return row


def test_base_filter_accepts_row_that_meets_every_required_rule() -> None:
    result = evaluate_second_zip_players_csv_row(_row(), policy=POLICY)

    assert result.eligible is True
    assert result.exclusion_reasons == ()
    assert result.exclusion_reason_codes == ()
    assert result.age_years == 27
    assert result.row.last_season == SECOND_ZIP_MINIMUM_LAST_SEASON


@pytest.mark.parametrize(
    ("field_name", "override_value", "reason", "helper_name"),
    [
        ("name", " ", SecondZipBaseExclusionReason.MISSING_NAME, "name"),
        ("position", "", SecondZipBaseExclusionReason.MISSING_POSITION, "position"),
        ("sub_position", None, SecondZipBaseExclusionReason.MISSING_SUB_POSITION, "sub_position"),
        ("date_of_birth", " ", SecondZipBaseExclusionReason.MISSING_DATE_OF_BIRTH, "date_of_birth"),
    ],
)
def test_base_filter_fails_required_presence_checks(
    field_name: str,
    override_value: object,
    reason: SecondZipBaseExclusionReason,
    helper_name: str,
) -> None:
    parsed = parse_second_zip_players_csv_row(_row(**{field_name: override_value}))
    result = evaluate_second_zip_players_csv_row(parsed, policy=POLICY)

    helper_values = {
        "name": has_name(parsed),
        "position": has_position(parsed),
        "sub_position": has_sub_position(parsed),
        "date_of_birth": has_date_of_birth(parsed),
    }

    assert helper_values[helper_name] is False
    assert result.eligible is False
    assert result.exclusion_reasons == (reason,)


def test_base_filter_reports_invalid_date_of_birth_separately_from_missing() -> None:
    result = evaluate_second_zip_players_csv_row(
        _row(date_of_birth="not-a-date"),
        policy=POLICY,
    )

    assert result.eligible is False
    assert result.exclusion_reasons == (SecondZipBaseExclusionReason.INVALID_DATE_OF_BIRTH,)
    assert result.age_years is None


@pytest.mark.parametrize(
    ("last_season", "expected_eligible", "expected_reasons"),
    [
        ("2024", True, ()),
        ("2023", False, (SecondZipBaseExclusionReason.LAST_SEASON_BEFORE_2024,)),
        ("", False, (SecondZipBaseExclusionReason.MISSING_LAST_SEASON,)),
        ("two-thousand", False, (SecondZipBaseExclusionReason.INVALID_LAST_SEASON,)),
    ],
)
def test_base_filter_applies_last_season_boundary_and_clean_failure_reasons(
    last_season: object,
    expected_eligible: bool,
    expected_reasons: tuple[SecondZipBaseExclusionReason, ...],
) -> None:
    parsed = parse_second_zip_players_csv_row(_row(last_season=last_season))
    result = evaluate_second_zip_players_csv_row(parsed, policy=POLICY)

    assert meets_last_season_floor(parsed, minimum_last_season=SECOND_ZIP_MINIMUM_LAST_SEASON) is expected_eligible
    assert result.eligible is expected_eligible
    assert result.exclusion_reasons == expected_reasons


def test_base_filter_age_boundary_allows_40_and_excludes_41() -> None:
    allowed = parse_second_zip_players_csv_row(_row(date_of_birth="1986-03-23 00:00:00"))
    excluded = parse_second_zip_players_csv_row(_row(date_of_birth="1985-03-22 00:00:00"))

    allowed_result = evaluate_second_zip_players_csv_row(allowed, policy=POLICY)
    excluded_result = evaluate_second_zip_players_csv_row(excluded, policy=POLICY)

    assert derive_age_years(allowed, reference_date=REFERENCE_DATE) == SECOND_ZIP_MAXIMUM_AGE_YEARS
    assert is_age_eligible(allowed, reference_date=REFERENCE_DATE) is True
    assert allowed_result.eligible is True
    assert allowed_result.exclusion_reasons == ()

    assert derive_age_years(excluded, reference_date=REFERENCE_DATE) == SECOND_ZIP_MAXIMUM_AGE_YEARS + 1
    assert is_age_eligible(excluded, reference_date=REFERENCE_DATE) is False
    assert excluded_result.eligible is False
    assert excluded_result.exclusion_reasons == (SecondZipBaseExclusionReason.AGE_OVER_40,)


def test_base_filter_derives_age_from_date_of_birth_only() -> None:
    result = evaluate_second_zip_players_csv_row(
        _row(age="99", date_of_birth="2004-08-12 00:00:00"),
        policy=POLICY,
    )

    assert result.eligible is True
    assert result.age_years == 21


def test_base_filter_collects_multiple_exclusion_reasons_for_same_row() -> None:
    result = evaluate_second_zip_players_csv_row(
        _row(name="", position="", date_of_birth="", last_season="2023"),
        policy=POLICY,
    )

    assert result.eligible is False
    assert result.exclusion_reasons == (
        SecondZipBaseExclusionReason.MISSING_NAME,
        SecondZipBaseExclusionReason.MISSING_POSITION,
        SecondZipBaseExclusionReason.MISSING_DATE_OF_BIRTH,
        SecondZipBaseExclusionReason.LAST_SEASON_BEFORE_2024,
    )
