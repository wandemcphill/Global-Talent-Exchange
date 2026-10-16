from __future__ import annotations

from backend.scripts.backfill_estimated_market_values import (
    UNKNOWN_LEAGUE,
    _canonical_league_name,
    _gsi_multiplier,
    _nested_number,
)


def test_estimator_canonicalizes_expanded_value_leagues() -> None:
    assert _canonical_league_name("Npfl") == "Nigeria Professional Football League"
    assert _canonical_league_name("Liga Profesional de Fútbol") == "Liga Profesional de Futbol"
    assert _canonical_league_name("Premiership") == "Scottish Premiership"
    assert _canonical_league_name("(missing league)") == UNKNOWN_LEAGUE


def test_nested_number_reads_summary_gsi_payloads() -> None:
    payload = {"real_player_profile": {"global_scouting_index": "67.5"}}

    assert _nested_number(payload, ("real_player_profile", "global_scouting_index")) == 67.5
    assert _nested_number(payload, ("real_player_profile", "missing")) is None


def test_gsi_multiplier_is_bounded() -> None:
    assert _gsi_multiplier(None) == 1.0
    assert _gsi_multiplier(55) == 1.0
    assert _gsi_multiplier(95) == 1.35
    assert _gsi_multiplier(20) == 0.78
