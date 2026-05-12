from __future__ import annotations

from backend.scripts.backfill_transfermarkt_market_values import (
    ExistingPlayerCandidate,
    TransfermarktValueFact,
    _equivalent_labels,
    _labels_match,
    _match_fact,
    _name_aliases,
    _normalize_label,
    _normalize_name,
    _select_value_competitions,
    _index_candidates,
)


def _candidate(
    player_id: str,
    name: str,
    *,
    club: str,
    league: str,
) -> ExistingPlayerCandidate:
    return ExistingPlayerCandidate(
        player_id=player_id,
        name_keys=frozenset(_name_aliases(name)),
        club_labels=frozenset({_normalize_label(club)}),
        league_labels=frozenset({_normalize_label(league)}),
        full_name=name,
        current_value_eur=None,
        player=None,  # type: ignore[arg-type]
        summary=None,
    )


def test_labels_match_abbreviated_club_names_safely() -> None:
    assert _labels_match(_normalize_label("PSV Eindhoven"), _normalize_label("PSV"))
    assert _labels_match(_normalize_label("FC Bayern Munich"), _normalize_label("Bayern Munich"))
    assert not _labels_match(_normalize_label("United FC"), _normalize_label("City FC"))


def test_match_fact_requires_name_plus_existing_context() -> None:
    candidate = _candidate("p1", "Joey Veerman", club="PSV", league="Eredivisie")
    fact = TransfermarktValueFact(
        source_player_key="111",
        display_name="Joey Veerman",
        club_name="PSV Eindhoven",
        league_name="Eredivisie",
        value_eur=24_000_000.0,
        raw_payload={},
    )

    result = _match_fact(fact, {_normalize_name("Joey Veerman"): [candidate]})

    assert result == (candidate, "name+club")


def test_match_fact_rejects_ambiguous_same_name_same_league() -> None:
    first = _candidate("p1", "Alex Silva", club="Ajax", league="Eredivisie")
    second = _candidate("p2", "Alex Silva", club="PSV", league="Eredivisie")
    fact = TransfermarktValueFact(
        source_player_key="222",
        display_name="Alex Silva",
        club_name="Feyenoord",
        league_name="Eredivisie",
        value_eur=1_000_000.0,
        raw_payload={},
    )

    result = _match_fact(fact, {_normalize_name("Alex Silva"): [first, second]})

    assert result == [first, second]


def test_value_competition_selector_includes_top_leagues() -> None:
    selected = _select_value_competitions(["Premier League", "Serie A", "La Liga", "Ligue 1"])

    assert [spec.competition_code for spec in selected] == ["GB1", "ES1", "IT1", "FR1"]


def test_value_competition_selector_includes_expanded_context_leagues() -> None:
    selected = _select_value_competitions(
        ["Austrian Bundesliga", "Swiss Super League", "Danish Superliga", "Turkish Super Lig"]
    )

    assert [spec.competition_code for spec in selected] == ["A1", "C1", "DK1", "TR1"]


def test_league_aliases_bridge_provider_label_variants() -> None:
    assert "argentinian primera division" in _equivalent_labels(_normalize_label("Liga Profesional de Fútbol"))
    assert "czech first league" in _equivalent_labels(_normalize_label("Chance Liga"))
    assert "portuguese primeira liga" in _equivalent_labels(_normalize_label("Liga Portugal"))
    assert "austrian bundesliga" in _equivalent_labels(_normalize_label("Admiral Bundesliga"))
    assert "danish superliga" in _equivalent_labels(_normalize_label("3F Superliga"))


def test_match_fact_uses_league_aliases_for_safe_unique_match() -> None:
    candidate = _candidate("p1", "Example Forward", club="Somewhere FC", league="Liga Profesional de Fútbol")
    fact = TransfermarktValueFact(
        source_player_key="333",
        display_name="Example Forward",
        club_name="Other Club",
        league_name="Argentinian Primera Division",
        value_eur=2_000_000.0,
        raw_payload={},
    )

    result = _match_fact(fact, {_normalize_name("Example Forward"): [candidate]})

    assert result == (candidate, "name+league")


def test_match_fact_uses_initial_last_name_alias_with_club_context() -> None:
    candidate = _candidate("p1", "A. Adeshina", club="LASK Linz", league="Admiral Bundesliga")
    fact = TransfermarktValueFact(
        source_player_key="444",
        display_name="Abdulmuiz Adeshina",
        club_name="LASK",
        league_name="Admiral Bundesliga",
        value_eur=350_000.0,
        raw_payload={},
    )

    result = _match_fact(fact, _index_candidates([candidate]))

    assert result == (candidate, "name_alias+club")


def test_match_fact_rejects_alias_match_without_club_context() -> None:
    candidate = _candidate("p1", "A. Adeshina", club="LASK Linz", league="Admiral Bundesliga")
    fact = TransfermarktValueFact(
        source_player_key="445",
        display_name="Abdulmuiz Adeshina",
        club_name="Other Club",
        league_name="Admiral Bundesliga",
        value_eur=350_000.0,
        raw_payload={},
    )

    result = _match_fact(fact, _index_candidates([candidate]))

    assert result is None
