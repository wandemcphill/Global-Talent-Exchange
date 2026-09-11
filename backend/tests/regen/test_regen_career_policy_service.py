from __future__ import annotations

from types import SimpleNamespace

from app.regen_career.policy_service import RegenCareerPolicyService


def test_willingness_is_bounded_and_personality_driven() -> None:
    assert RegenCareerPolicyService._willingness_from_personality(
        {"ambition": 1.0, "resilience": 1.0, "loyalty": 1.0}
    ) == 1.0
    assert RegenCareerPolicyService._willingness_from_personality(
        {"ambition": 0.0, "resilience": 0.0, "loyalty": 0.0}
    ) == 0.0


def test_generation_season_can_be_read_from_generation_event() -> None:
    service = object.__new__(RegenCareerPolicyService)
    event = SimpleNamespace(
        season_label="Season 17",
        metadata_json={},
        created_at=None,
        id="event-1",
    )
    service.session = SimpleNamespace(
        scalars=lambda statement: SimpleNamespace(all=lambda: [event])
    )

    assert service._generation_season_number("regen-profile") == 17


def test_generation_season_failure_keeps_age_unknown_instead_of_guessing() -> None:
    service = object.__new__(RegenCareerPolicyService)
    service.session = SimpleNamespace(
        scalars=lambda statement: SimpleNamespace(all=lambda: [])
    )

    try:
        service._generation_season_number("regen-profile")
    except ValueError as exc:
        assert "generation season is unavailable" in str(exc)
    else:
        raise AssertionError("Missing generation season must not be guessed")
