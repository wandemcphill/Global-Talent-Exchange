"""The performance -> form link, including the anti-farming guard."""

from __future__ import annotations

from app.players.form_service import (
    MAX_PERFORMANCES_PER_COMPETITION,
    TREND_FALLING,
    TREND_RISING,
    TREND_STEADY,
    PlayerFormService,
)

from .conftest import add_performance


def test_empty_history_yields_an_empty_window(session, canonical_player):
    window = PlayerFormService(session).build_window(canonical_player.id)

    assert window.has_sample is False
    assert window.matches_counted == 0
    assert window.average_rating is None
    assert window.is_signal_eligible is False


def test_window_averages_recent_eligible_performances(session, canonical_player):
    for index, rating in enumerate([7.0, 8.0, 6.0]):
        add_performance(session, rating=rating, days_ago=index)

    window = PlayerFormService(session).build_window(canonical_player.id)

    assert window.matches_counted == 3
    assert window.average_rating == 7.0
    assert window.is_signal_eligible is True


def test_ineligible_performances_are_excluded_from_form(session, canonical_player):
    add_performance(session, rating=9.9, days_ago=0, eligible=False)
    add_performance(session, rating=7.0, days_ago=1)

    window = PlayerFormService(session).build_window(canonical_player.id)

    assert window.matches_counted == 1
    assert window.average_rating == 7.0


def test_single_competition_cannot_dominate_the_window(session, canonical_player):
    """The anti-farming guard.

    An owner who can stack one competition with favourable fixtures must not be
    able to fill a player's entire form window from it.
    """
    for index in range(6):
        add_performance(session, rating=9.5, days_ago=index, competition_id="farmed-comp")

    window = PlayerFormService(session).build_window(canonical_player.id)

    assert window.matches_counted == MAX_PERFORMANCES_PER_COMPETITION
    assert window.excluded_by_competition_cap == 3
    assert window.competitions_counted == 1


def test_broad_form_across_competitions_fills_the_window(session, canonical_player):
    for index in range(6):
        add_performance(session, rating=8.0, days_ago=index, competition_id=f"comp-{index // 2}")

    window = PlayerFormService(session).build_window(canonical_player.id)

    assert window.matches_counted == 6
    assert window.competitions_counted == 3
    assert window.excluded_by_competition_cap == 0


def test_rising_trajectory_is_detected(session, canonical_player):
    # days_ago 0 is the most recent, so the low ratings are the older half.
    for index, rating in enumerate([8.8, 8.6, 8.4, 6.0, 5.8, 5.6]):
        add_performance(session, rating=rating, days_ago=index, competition_id=f"comp-{index // 2}")

    window = PlayerFormService(session).build_window(canonical_player.id)

    assert window.trend == TREND_RISING
    assert window.trend_delta > 0


def test_falling_trajectory_is_detected(session, canonical_player):
    for index, rating in enumerate([5.6, 5.8, 6.0, 8.4, 8.6, 8.8]):
        add_performance(session, rating=rating, days_ago=index, competition_id=f"comp-{index // 2}")

    window = PlayerFormService(session).build_window(canonical_player.id)

    assert window.trend == TREND_FALLING
    assert window.trend_delta < 0


def test_short_history_reports_steady_rather_than_inventing_a_direction(session, canonical_player):
    add_performance(session, rating=9.0, days_ago=0)
    add_performance(session, rating=5.0, days_ago=1)
    add_performance(session, rating=7.0, days_ago=2)

    window = PlayerFormService(session).build_window(canonical_player.id)

    assert window.trend == TREND_STEADY
    assert window.trend_delta == 0.0


def test_window_is_deterministic(session, canonical_player):
    for index in range(6):
        add_performance(session, rating=7.5, days_ago=index, competition_id=f"comp-{index // 2}")

    service = PlayerFormService(session)
    first = service.build_window(canonical_player.id)
    second = service.build_window(canonical_player.id)

    assert [entry.match_id for entry in first.entries] == [entry.match_id for entry in second.entries]
    assert first.average_rating == second.average_rating


def test_recent_performances_listing_includes_ineligible_rows(session, canonical_player):
    add_performance(session, rating=9.9, days_ago=0, eligible=False)
    add_performance(session, rating=7.0, days_ago=1)

    listed = PlayerFormService(session).list_recent_performances(canonical_player.id)

    assert len(listed) == 2
    assert listed[0].eligible_for_valuation is False
