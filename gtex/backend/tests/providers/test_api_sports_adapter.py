from __future__ import annotations

from types import SimpleNamespace

from app.providers.api_sports_adapter import ApiSportsAdapter


def _adapter() -> ApiSportsAdapter:
    return ApiSportsAdapter(
        settings=SimpleNamespace(
            api_sports_base_url="https://v3.football.api-sports.io",
            api_sports_api_key="test-api-sports-key",
            provider_timeout_seconds=15,
        )
    )


def test_fetch_matches_transforms_api_sports_fixture_payload(monkeypatch) -> None:
    adapter = _adapter()
    monkeypatch.setattr(
        adapter,
        "_get",
        lambda *args, **kwargs: {
            "response": [
                {
                    "fixture": {
                        "id": 1208021,
                        "date": "2024-08-16T19:00:00+00:00",
                        "venue": {"name": "Old Trafford"},
                        "status": {"short": "FT"},
                    },
                    "league": {
                        "id": 39,
                        "season": 2024,
                        "round": "Regular Season - 1",
                    },
                    "teams": {
                        "home": {"id": 33, "winner": True},
                        "away": {"id": 36, "winner": False},
                    },
                    "score": {"fulltime": {"home": 1, "away": 0}},
                }
            ]
        },
    )

    matches = adapter.fetch_matches("39", "39-2024")

    assert matches == [
        {
            "id": 1208021,
            "competition": {"id": 39},
            "season": {"id": "39-2024"},
            "homeTeam": {"id": 33},
            "awayTeam": {"id": 36},
            "winner": {"id": 33},
            "utcDate": "2024-08-16T19:00:00+00:00",
            "status": "FINISHED",
            "stage": "Regular Season 1",
            "matchday": 1,
            "venue": "Old Trafford",
            "score": {"fullTime": {"home": 1, "away": 0}},
        }
    ]


def test_fetch_team_standings_transforms_api_sports_table(monkeypatch) -> None:
    adapter = _adapter()
    monkeypatch.setattr(
        adapter,
        "_get",
        lambda *args, **kwargs: {
            "response": [
                {
                    "league": {
                        "season": 2024,
                        "standings": [
                            [
                                {
                                    "rank": 1,
                                    "team": {"id": 40},
                                    "points": 84,
                                    "goalsDiff": 45,
                                    "group": "Premier League",
                                    "form": "DLDLW",
                                    "all": {
                                        "played": 38,
                                        "win": 25,
                                        "draw": 9,
                                        "lose": 4,
                                        "goals": {"for": 86, "against": 41},
                                    },
                                }
                            ]
                        ],
                    }
                }
            ]
        },
    )

    standings = adapter.fetch_team_standings("39", "39-2024")

    assert standings == {
        "competition": {"id": "39"},
        "season": {"id": "39-2024"},
        "standings": [
            {
                "type": "premier_league",
                "table": [
                    {
                        "position": 1,
                        "team": {"id": 40},
                        "playedGames": 38,
                        "won": 25,
                        "draw": 9,
                        "lost": 4,
                        "goalsFor": 86,
                        "goalsAgainst": 41,
                        "goalDifference": 45,
                        "points": 84,
                        "form": "DLDLW",
                    }
                ],
            }
        ],
    }
