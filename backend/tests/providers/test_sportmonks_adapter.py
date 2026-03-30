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


def test_fetch_player_directory_page_uses_global_player_cursor_flow(monkeypatch) -> None:
    adapter = _adapter()
    def _fake_get(path: str, params: dict[str, object] | None = None, **kwargs):
        assert path == "/players"
        page = int((params or {}).get("page") or 1)
        if page == 1:
            return {
                "data": [
                    {
                        "id": 4237168,
                        "name": "Christos Mandas",
                        "display_name": "Christos Mandas",
                        "common_name": "C. Mandas",
                        "firstname": "Christos",
                        "lastname": "Mandas",
                        "position": {"name": "Goalkeeper"},
                        "detailedposition": {"name": "Goalkeeper"},
                        "date_of_birth": "2001-09-17",
                        "nationality": {"name": "Greece", "iso2": "GR"},
                        "country": {"name": "Greece", "iso2": "GR"},
                        "teams": [
                            {
                                "id": 1,
                                "end": None,
                                "team_id": 52,
                                "team": {
                                    "id": 52,
                                    "name": "AFC Bournemouth",
                                    "last_played_at": "2026-03-25 11:00:00",
                                },
                            }
                        ],
                    }
                ],
                "pagination": {"has_more": True},
            }
        return {
            "data": [
                {
                    "id": 22169325,
                    "name": "James Hill",
                    "display_name": "James Hill",
                    "common_name": "J. Hill",
                    "firstname": "James",
                    "lastname": "Hill",
                    "position": {"name": "Defender"},
                    "detailedposition": {"name": "Centre Back"},
                    "date_of_birth": "2002-01-10",
                    "nationality": {"name": "England", "iso2": "EN"},
                    "country": {"name": "England", "iso2": "EN"},
                    "teams": [
                        {
                            "id": 2,
                            "end": None,
                            "team_id": 52,
                            "team": {
                                "id": 52,
                                "name": "AFC Bournemouth",
                                "last_played_at": "2026-03-25 11:00:00",
                            },
                        }
                    ],
                }
            ],
            "pagination": {"has_more": False},
        }

    monkeypatch.setattr(adapter, "_get", _fake_get)

    first_page = adapter.fetch_player_directory_page(batch_size=1)
    second_page = adapter.fetch_player_directory_page(cursor=first_page.next_cursor, batch_size=1)

    assert len(first_page.items) == 1
    assert first_page.items[0].provider_player_id == "4237168"
    assert first_page.items[0].current_club_name == "AFC Bournemouth"
    assert first_page.items[0].current_competition_name is None
    assert first_page.exhausted is False
    assert first_page.next_cursor == '{"page": 2, "per_page": 1}'
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
