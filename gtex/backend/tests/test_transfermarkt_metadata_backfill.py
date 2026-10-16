from __future__ import annotations

from backend.scripts.backfill_transfermarkt_market_values import _name_aliases, _normalize_label
from backend.scripts.backfill_transfermarkt_player_metadata import (
    ExistingPlayerCandidate,
    TransfermarktMetadataFact,
    _index_candidates,
    _match_fact,
)


def _candidate(
    player_id: str,
    name: str,
    *,
    club: str = "",
    league: str = "",
    nationality: str = "",
) -> ExistingPlayerCandidate:
    return ExistingPlayerCandidate(
        player_id=player_id,
        name_keys=frozenset(_name_aliases(name)),
        club_labels=frozenset({_normalize_label(club)} if club else set()),
        league_labels=frozenset({_normalize_label(league)} if league else set()),
        nationality_labels=frozenset({_normalize_label(nationality)} if nationality else set()),
        date_of_birth=None,
        full_name=name,
        player=None,  # type: ignore[arg-type]
        summary=None,
        profiles=(),
    )


def _fact(
    name: str,
    *,
    club: str,
    league: str,
    nationality: str | None = None,
) -> TransfermarktMetadataFact:
    return TransfermarktMetadataFact(
        source_player_key="tm-1",
        display_name=name,
        club_name=club,
        club_key="club-1",
        league_name=league,
        league_key="league-1",
        league_country_name="England",
        nationality=nationality,
        date_of_birth=None,
        profile_path="/example/profil/spieler/1",
        raw_payload={},
    )


def test_metadata_match_uses_existing_league_context() -> None:
    candidate = _candidate("p1", "Example Forward", league="Premier League")
    fact = _fact("Example Forward", club="Arsenal FC", league="English Premier League")

    result = _match_fact(fact, _index_candidates([candidate]))

    assert result == (candidate, "name+league")


def test_metadata_match_rejects_ambiguous_same_name_same_league() -> None:
    first = _candidate("p1", "Alex Silva", club="Arsenal", league="Premier League")
    second = _candidate("p2", "Alex Silva", club="Chelsea", league="Premier League")
    fact = _fact("Alex Silva", club="Tottenham Hotspur", league="Premier League")

    result = _match_fact(fact, _index_candidates([first, second]))

    assert result == [first, second]


def test_metadata_match_allows_unique_name_plus_nationality_only_when_enabled() -> None:
    candidate = _candidate("p1", "Rare Exact Name", nationality="Brazil")
    fact = _fact("Rare Exact Name", club="Palmeiras", league="Brazilian Serie A", nationality="Brazil")

    assert _match_fact(fact, _index_candidates([candidate])) is None
    assert _match_fact(
        fact,
        _index_candidates([candidate]),
        allow_unique_name_nationality=True,
    ) == (candidate, "name+unique+nationality")


def test_metadata_alias_match_still_requires_club_context() -> None:
    candidate = _candidate("p1", "A. Adeshina", club="LASK Linz", league="Austrian Bundesliga")
    fact = _fact("Abdulmuiz Adeshina", club="Other Club", league="Austrian Bundesliga")

    result = _match_fact(fact, _index_candidates([candidate]))

    assert result is None


def test_metadata_match_rejects_surname_only_alias_even_with_club_context() -> None:
    candidate = _candidate("p1", "Yusuf Jibrin", club="Kano Pillars", league="Nigeria Professional Football League")
    fact = _fact("Mustapha Jibrin", club="Kano Pillars", league="Nigeria Professional Football League")

    result = _match_fact(fact, _index_candidates([candidate]))

    assert result is None
