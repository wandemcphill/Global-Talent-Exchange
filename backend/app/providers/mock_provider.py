from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.ingestion.normalizers import normalize_recent_update_feed
from app.ingestion.schemas import ProviderHealthSnapshot, RecentUpdateFeed

from .base import BaseFootballProvider


class MockFootballProvider(BaseFootballProvider):
    name = "mock"

    def __init__(self) -> None:
        self._countries = [
            {"id": "ENG", "name": " England ", "countryCode": "GB", "code": "ENG"},
            {"id": "ESP", "name": "Spain", "countryCode": "ES", "code": "ESP"},
        ]
        self._competitions = [
            {
                "id": "PL",
                "name": " Premier League ",
                "code": "PL",
                "type": "LEAGUE",
                "area": {"id": "ENG", "name": "England", "countryCode": "GB", "code": "ENG"},
                "currentSeason": {
                    "id": "PL-2025",
                    "startDate": "2025-08-15",
                    "endDate": "2026-05-24",
                    "current": True,
                    "currentMatchday": 28,
                },
            },
            {
                "id": "UCL",
                "name": "UEFA Club Championship",
                "code": "UCL",
                "type": "CUP",
                "area": {"id": "EUR", "name": "Europe", "countryCode": "EU", "code": "EUR"},
                "currentSeason": {
                    "id": "UCL-2025",
                    "startDate": "2025-09-16",
                    "endDate": "2026-05-30",
                    "current": True,
                    "currentMatchday": 12,
                },
            },
        ]
        self._seasons = {
            "PL": [
                {"id": "PL-2025", "startDate": "2025-08-15", "endDate": "2026-05-24", "current": True, "currentMatchday": 28},
            ],
            "UCL": [
                {"id": "UCL-2025", "startDate": "2025-09-16", "endDate": "2026-05-30", "current": True, "currentMatchday": 12},
            ],
        }
        self._clubs = {
            ("PL", "PL-2025"): [
                {
                    "id": "ARS",
                    "name": "Arsenal FC",
                    "shortName": "Arsenal",
                    "tla": "ARS",
                    "area": {"id": "ENG", "name": "England"},
                    "founded": 1886,
                    "venue": "Emirates Stadium",
                    "website": "https://www.arsenal.com",
                },
                {
                    "id": "MCI",
                    "name": "Man City",
                    "shortName": "City",
                    "tla": "MCI",
                    "area": {"id": "ENG", "name": "England"},
                    "founded": 1880,
                    "venue": "Etihad Stadium",
                    "website": "https://www.mancity.com",
                },
            ],
            ("UCL", "UCL-2025"): [
                {
                    "id": "RMA",
                    "name": "Real Madrid CF",
                    "shortName": "Real Madrid",
                    "tla": "RMA",
                    "area": {"id": "ESP", "name": "Spain"},
                    "founded": 1902,
                    "venue": "Santiago Bernabeu",
                    "website": "https://www.realmadrid.com",
                },
                {
                    "id": "ARS",
                    "name": "Arsenal FC",
                    "shortName": "Arsenal",
                    "tla": "ARS",
                    "area": {"id": "ENG", "name": "England"},
                    "founded": 1886,
                    "venue": "Emirates Stadium",
                    "website": "https://www.arsenal.com",
                },
            ],
        }
        self._players = {
            "ARS": [
                {
                    "id": "p-saka",
                    "name": " Bukayo  Saka ",
                    "firstName": "Bukayo",
                    "lastName": "Saka",
                    "shortName": "Saka",
                    "position": "Right Winger",
                    "dateOfBirth": "2001-09-05",
                    "nationality": "England",
                    "height": "178 cm",
                    "weight": "72 kg",
                    "preferredFoot": "left",
                    "shirtNumber": 7,
                },
                {
                    "id": "p-raya",
                    "name": "David Raya",
                    "position": "Goalkeeper",
                    "dateOfBirth": "1995-09-15",
                    "nationality": "Spain",
                    "height": "183 cm",
                    "preferredFoot": "right",
                    "shirtNumber": 22,
                },
            ],
            "MCI": [
                {
                    "id": "p-foden",
                    "name": "Phil Foden",
                    "position": "Attacking Midfield",
                    "dateOfBirth": "2000-05-28",
                    "nationality": "England",
                    "height": "171 cm",
                    "shirtNumber": 47,
                }
            ],
            "RMA": [
                {
                    "id": "p-bellingham",
                    "name": "Jude Bellingham",
                    "position": "Midfielder",
                    "dateOfBirth": "2003-06-29",
                    "nationality": "England",
                    "height": "186 cm",
                    "shirtNumber": 5,
                }
            ],
        }
        self._matches = {
            ("PL", "PL-2025"): [
                {
                    "id": "pl-match-1",
                    "competition": {"id": "PL"},
                    "season": {"id": "PL-2025"},
                    "homeTeam": {"id": "ARS"},
                    "awayTeam": {"id": "MCI"},
                    "winner": {"id": "ARS"},
                    "utcDate": "2026-03-08T16:30:00Z",
                    "status": "FINISHED",
                    "stage": "REGULAR_SEASON",
                    "matchday": 28,
                    "venue": "Emirates Stadium",
                    "score": {"fullTime": {"home": 2, "away": 1}},
                    "lastUpdated": "2026-03-08T18:35:00Z",
                }
            ],
            ("UCL", "UCL-2025"): [
                {
                    "id": "ucl-match-1",
                    "competition": {"id": "UCL"},
                    "season": {"id": "UCL-2025"},
                    "homeTeam": {"id": "RMA"},
                    "awayTeam": {"id": "ARS"},
                    "winner": {"id": "RMA"},
                    "utcDate": "2026-03-10T20:00:00Z",
                    "status": "FINISHED",
                    "stage": "FINAL",
                    "matchday": 12,
                    "venue": "Santiago Bernabeu",
                    "score": {"fullTime": {"home": 3, "away": 2}},
                    "lastUpdated": "2026-03-10T22:10:00Z",
                }
            ],
        }
        self._standings = {
            ("PL", "PL-2025"): {
                "competition": {"id": "PL"},
                "season": {"id": "PL-2025"},
                "standings": [
                    {
                        "type": "TOTAL",
                        "table": [
                            {"position": 1, "team": {"id": "ARS"}, "playedGames": 28, "won": 20, "draw": 5, "lost": 3, "goalsFor": 60, "goalsAgainst": 25, "goalDifference": 35, "points": 65, "form": "WWDWW"},
                            {"position": 2, "team": {"id": "MCI"}, "playedGames": 28, "won": 19, "draw": 4, "lost": 5, "goalsFor": 58, "goalsAgainst": 28, "goalDifference": 30, "points": 61, "form": "WLWWW"},
                        ],
                    }
                ],
            }
        }
        self._player_stats = {
            "p-saka": {
                "season": {"appearances": 26, "starts": 25, "minutes": 2180, "goals": 14, "assists": 9, "yellowCards": 3, "redCards": 0, "averageRating": 7.84},
                "matches": [
                    {"id": "p-saka:pl-match-1", "matchId": "pl-match-1", "minutes": 90, "goals": 1, "assists": 1, "rating": 8.7, "position": "Right Winger", "started": True},
                    {"id": "p-saka:ucl-match-1", "matchId": "ucl-match-1", "minutes": 90, "goals": 1, "assists": 0, "rating": 8.4, "position": "Right Winger", "started": True},
                ],
            },
            "p-raya": {
                "season": {"appearances": 24, "starts": 24, "minutes": 2160, "goals": 0, "assists": 0, "cleanSheets": 11, "saves": 74, "averageRating": 7.2},
                "matches": [
                    {"id": "p-raya:pl-match-1", "matchId": "pl-match-1", "minutes": 90, "saves": 5, "cleanSheet": False, "rating": 7.5, "position": "Goalkeeper", "started": True},
                ],
            },
            "p-foden": {
                "season": {"appearances": 25, "starts": 21, "minutes": 1880, "goals": 11, "assists": 7, "averageRating": 7.61},
                "matches": [
                    {"id": "p-foden:pl-match-1", "matchId": "pl-match-1", "minutes": 90, "goals": 1, "assists": 0, "rating": 8.0, "position": "Attacking Midfield", "started": True},
                ],
            },
            "p-bellingham": {
                "season": {"appearances": 22, "starts": 22, "minutes": 1980, "goals": 9, "assists": 6, "averageRating": 7.9},
                "matches": [
                    {"id": "p-bellingham:ucl-match-1", "matchId": "ucl-match-1", "minutes": 90, "goals": 1, "assists": 1, "rating": 8.9, "position": "Midfielder", "started": True},
                ],
            },
        }
        self._recent_updates = {
            "cursor": "2026-03-10T22:10:00Z",
            "next_cursor": "2026-03-11T00:00:00Z",
            "updates": [
                {"entity_type": "competition", "id": "PL", "seasonId": "PL-2025"},
                {"entity_type": "club", "id": "ARS", "seasonId": "PL-2025", "competitionId": "PL"},
                {"entity_type": "player", "id": "p-saka", "clubId": "ARS", "seasonId": "PL-2025", "competitionId": "PL"},
            ],
        }

    def healthcheck(self) -> ProviderHealthSnapshot:
        return ProviderHealthSnapshot(provider_name=self.name, ok=True, detail="Mock provider ready.", latency_ms=1)

    def fetch_countries(self) -> list[dict[str, Any]]:
        return deepcopy(self._countries)

    def fetch_competitions(self) -> list[dict[str, Any]]:
        return deepcopy(self._competitions)

    def fetch_seasons(self, competition_id: str) -> list[dict[str, Any]]:
        return deepcopy(self._seasons.get(competition_id, []))

    def fetch_clubs(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        return deepcopy(self._clubs.get((competition_id, season_id), []))

    def fetch_players(self, club_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        return deepcopy(self._players.get(club_id, []))

    def fetch_player_stats(
        self,
        player_id: str,
        *,
        season_id: str | None = None,
        competition_id: str | None = None,
        club_id: str | None = None,
    ) -> dict[str, Any]:
        return deepcopy(self._player_stats.get(player_id, {"season": {}, "matches": []}))

    def fetch_matches(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        return deepcopy(self._matches.get((competition_id, season_id), []))

    def fetch_team_standings(self, competition_id: str, season_id: str | None = None) -> dict[str, Any]:
        return deepcopy(
            self._standings.get(
                (competition_id, season_id),
                {"competition": {"id": competition_id}, "season": {"id": season_id}, "standings": []},
            )
        )

    def fetch_recent_updates(self, cursor: str | None) -> RecentUpdateFeed:
        payload = deepcopy(self._recent_updates)
        if cursor and cursor >= payload["next_cursor"]:
            payload["updates"] = []
            payload["cursor"] = cursor
        return normalize_recent_update_feed(self.name, payload)
