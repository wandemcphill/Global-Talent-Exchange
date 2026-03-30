from __future__ import annotations

from types import SimpleNamespace

from app.providers.sportmonks_adapter import SportMonksAdapter


def _adapter() -> SportMonksAdapter:
    return SportMonksAdapter(
        settings=SimpleNamespace(
            sportmonks_base_url="https://api.sportmonks.com/v3/football",
            sportmonks_api_token="test-sportmonks-token",
            provider_timeout_seconds=15,
        )
    )


def test_fetch_player_directory_page_uses_club_backed_cursor_flow(monkeypatch) -> None:
    adapter = _adapter()
    monkeypatch.setattr(
        adapter,
        "_build_unique_club_directory",
        lambda **kwargs: [
            {
                "club_id": "52",
                "club_name": "AFC Bournemouth",
                "competition_id": "8",
                "competition_name": "Premier League",
                "season_id": "21646",
            }
        ],
    )
    monkeypatch.setattr(
        adapter,
        "fetch_players",
        lambda club_id: [
            {
                "id": 4237168,
                "name": "Christos Mandas",
                "displayName": "Christos Mandas",
                "commonName": "C. Mandas",
                "firstName": "Christos",
                "lastName": "Mandas",
                "position": "Goalkeeper",
                "detailedPosition": "Goalkeeper",
                "dateOfBirth": "2001-09-17",
                "nationality": "Greece",
                "nationalityCode": "GR",
                "country": "Greece",
                "height": 189,
                "weight": 83,
                "shirtNumber": 29,
            },
            {
                "id": 22169325,
                "name": "James Hill",
                "displayName": "James Hill",
                "commonName": "J. Hill",
                "firstName": "James",
                "lastName": "Hill",
                "position": "Defender",
                "detailedPosition": "Centre Back",
                "dateOfBirth": "2002-01-10",
                "nationality": "England",
                "nationalityCode": "EN",
                "country": "England",
                "height": 184,
                "weight": 73,
                "shirtNumber": 23,
            },
        ],
    )

    first_page = adapter.fetch_player_directory_page(batch_size=1)
    second_page = adapter.fetch_player_directory_page(cursor=first_page.next_cursor, batch_size=1)

    assert len(first_page.items) == 1
    assert first_page.items[0].provider_player_id == "4237168"
    assert first_page.items[0].current_club_name == "AFC Bournemouth"
    assert first_page.items[0].current_competition_name == "Premier League"
    assert first_page.exhausted is False
    assert second_page.items[0].provider_player_id == "22169325"
    assert second_page.exhausted is True


def test_fetch_player_stats_maps_sportmonks_stat_details(monkeypatch) -> None:
    adapter = _adapter()
    monkeypatch.setattr(
        adapter,
        "_get",
        lambda *args, **kwargs: {
            "data": {
                "statistics": [
                    {
                        "id": 625405358,
                        "player_id": 4237168,
                        "team_id": 52,
                        "season_id": 21646,
                        "has_values": True,
                        "details": [
                            {"type": {"code": "appearances"}, "value": {"total": 9}},
                            {"type": {"code": "lineups"}, "value": {"total": 8}},
                            {"type": {"code": "minutes-played"}, "value": {"total": 721}},
                            {"type": {"code": "goals"}, "value": {"total": 0}},
                            {"type": {"code": "assists"}, "value": {"total": 0}},
                            {"type": {"code": "saves"}, "value": {"total": 23}},
                            {"type": {"code": "cleansheets"}, "value": {"total": 4}},
                            {"type": {"code": "rating"}, "value": {"average": 7.08}},
                        ],
                    }
                ]
            }
        },
    )

    stats = adapter.fetch_player_stats("4237168", season_id="21646", club_id="52")

    assert stats == {
        "season": {
            "appearances": 9,
            "starts": 8,
            "minutes": 721,
            "goals": 0,
            "assists": 0,
            "yellowCards": None,
            "redCards": None,
            "cleanSheets": 4,
            "saves": 23,
            "averageRating": 7.08,
        },
        "matches": [],
    }
