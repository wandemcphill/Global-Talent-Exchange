from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
import time
from typing import TYPE_CHECKING
from typing import Any

from app.ingestion.constants import ENV_API_SPORTS_API_KEY, ENV_API_SPORTS_BASE_URL
from app.ingestion.schemas import ProviderHealthSnapshot, RecentUpdateFeed

from .base import BaseFootballProvider, ProviderConfigurationError
from .import_models import RealPlayerSourceItem, RealPlayerSourcePage

if TYPE_CHECKING:
    from app.core.config import Settings


_SEASON_DIGIT_RE = re.compile(r"(\d{4})")
_NUMBER_RE = re.compile(r"(\d+)")


class ApiSportsAdapter(BaseFootballProvider):
    name = "api_sports"

    def __init__(self, *, settings: Settings | None = None) -> None:
        import requests

        self.base_url = (
            settings.api_sports_base_url
            if settings is not None
            else os.getenv(ENV_API_SPORTS_BASE_URL, "https://v3.football.api-sports.io")
        ).rstrip("/")
        self.api_key = settings.api_sports_api_key if settings is not None else os.getenv(ENV_API_SPORTS_API_KEY)
        self.default_timeout_seconds = settings.provider_timeout_seconds if settings is not None else 30
        self.session = requests.Session()
        self._last_request_started_at = 0.0
        if self.api_key:
            self.session.headers.update({"x-apisports-key": self.api_key})

    def healthcheck(self) -> ProviderHealthSnapshot:
        if not self.api_key:
            return ProviderHealthSnapshot(
                provider_name=self.name,
                ok=False,
                configured=False,
                detail=f"Missing {ENV_API_SPORTS_API_KEY}.",
            )
        started = time.perf_counter()
        try:
            self._get("/status")
        except Exception as exc:  # pragma: no cover - network-dependent
            return ProviderHealthSnapshot(
                provider_name=self.name,
                ok=False,
                configured=True,
                detail=str(exc),
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
        return ProviderHealthSnapshot(
            provider_name=self.name,
            ok=True,
            configured=True,
            detail="API-Sports reachable.",
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def fetch_countries(self) -> list[dict[str, Any]]:
        response = self._get("/countries")
        return [self._transform_country(item) for item in response.get("response", [])]

    def fetch_competitions(self) -> list[dict[str, Any]]:
        response = self._get("/leagues", params={"current": "true"})
        competitions = [self._transform_competition(item) for item in response.get("response", [])]
        return sorted(competitions, key=lambda item: str(item.get("id") or ""))

    def fetch_seasons(self, competition_id: str) -> list[dict[str, Any]]:
        response = self._get("/leagues", params={"id": competition_id})
        records = response.get("response", [])
        if not records:
            return []
        league = records[0].get("league") or {}
        seasons = records[0].get("seasons") or []
        transformed = [self._transform_season(item, competition_id=competition_id) for item in seasons]
        return sorted(
            transformed,
            key=lambda item: (
                item.get("year") or 0,
                str(league.get("id") or ""),
            ),
        )

    def fetch_clubs(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"league": competition_id}
        season_year = self._season_year(season_id)
        if season_year is not None:
            params["season"] = season_year
        response = self._get("/teams", params=params)
        return [self._transform_club(item) for item in response.get("response", [])]

    def fetch_players(self, club_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        del season_id
        response = self._get("/players/squads", params={"team": club_id})
        records = response.get("response", [])
        if not records:
            return []
        team = records[0].get("team") or {}
        return [self._transform_player(item, team=team) for item in records[0].get("players", [])]

    def fetch_player_stats(
        self,
        player_id: str,
        *,
        season_id: str | None = None,
        competition_id: str | None = None,
        club_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"id": player_id}
        season_year = self._season_year(season_id)
        if season_year is not None:
            params["season"] = season_year
        if competition_id:
            params["league"] = competition_id
        if club_id:
            params["team"] = club_id
        response = self._get("/players", params=params)
        records = response.get("response", [])
        if not records:
            return {"season": {}, "matches": []}
        record = records[0]
        all_statistics = list(record.get("statistics") or [])
        statistics = list(all_statistics)
        if competition_id:
            statistics = [
                item for item in statistics if str(((item.get("league") or {}).get("id")) or "") == str(competition_id)
            ]
        if club_id:
            statistics = [item for item in statistics if str(((item.get("team") or {}).get("id")) or "") == str(club_id)]
        summary_source = statistics[0] if statistics else (all_statistics[0] if all_statistics else {})
        season_summary = {
            "appearances": (summary_source.get("games") or {}).get("appearences"),
            "starts": (summary_source.get("games") or {}).get("lineups"),
            "minutes": (summary_source.get("games") or {}).get("minutes"),
            "goals": (summary_source.get("goals") or {}).get("total"),
            "assists": (summary_source.get("goals") or {}).get("assists"),
            "yellowCards": (summary_source.get("cards") or {}).get("yellow"),
            "redCards": (summary_source.get("cards") or {}).get("red"),
            "saves": (summary_source.get("goals") or {}).get("saves"),
            "averageRating": (summary_source.get("games") or {}).get("rating"),
        }
        return {"season": season_summary, "matches": []}

    def fetch_matches(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"league": competition_id}
        season_year = self._season_year(season_id)
        if season_year is not None:
            params["season"] = season_year
        response = self._get("/fixtures", params=params)
        return [self._transform_match(item) for item in response.get("response", [])]

    def fetch_team_standings(self, competition_id: str, season_id: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"league": competition_id}
        season_year = self._season_year(season_id)
        if season_year is not None:
            params["season"] = season_year
        response = self._get("/standings", params=params)
        records = response.get("response", [])
        if not records:
            return {
                "competition": {"id": competition_id},
                "season": {"id": season_id},
                "standings": [],
            }
        league = records[0].get("league") or {}
        standing_groups: list[dict[str, Any]] = []
        for index, table in enumerate(league.get("standings") or [], start=1):
            if not table:
                continue
            group_name = self._clean_text(((table[0] or {}).get("group")) or "")
            standing_type = "total" if len(league.get("standings") or []) == 1 else f"group_{index}"
            if group_name:
                standing_type = group_name.lower().replace(" ", "_")
            standing_groups.append(
                {
                    "type": standing_type,
                    "table": [self._transform_standing_row(item) for item in table],
                }
            )
        return {
            "competition": {"id": competition_id},
            "season": {"id": season_id or self._season_id(competition_id, league.get("season"))},
            "standings": standing_groups,
        }

    def fetch_recent_updates(self, cursor: str | None) -> RecentUpdateFeed:
        now = datetime.now(timezone.utc).isoformat()
        return RecentUpdateFeed(provider_name=self.name, cursor_value=cursor, next_cursor=now, updates=[])

    def fetch_player_directory_page(
        self,
        *,
        cursor: str | None = None,
        batch_size: int = 100,
        timeout_seconds: int | None = None,
        rate_limit_per_minute: int | None = None,
    ) -> RealPlayerSourcePage:
        clubs = self._build_unique_club_directory(
            timeout_seconds=timeout_seconds,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        state = self._decode_directory_cursor(cursor)
        club_index = state["club_index"]
        player_index = state["player_index"]
        items: list[RealPlayerSourceItem] = []

        while club_index < len(clubs) and len(items) < batch_size:
            club_context = clubs[club_index]
            squad = self.fetch_players(str(club_context["club_id"]), season_id=str(club_context.get("season_id") or ""))
            while player_index < len(squad) and len(items) < batch_size:
                raw_player = squad[player_index]
                items.append(self._build_directory_item(raw_player, club_context=club_context))
                player_index += 1
            if player_index < len(squad):
                return RealPlayerSourcePage(
                    provider_name=self.name,
                    items=tuple(items),
                    next_cursor=self._encode_directory_cursor(club_index=club_index, player_index=player_index),
                    exhausted=False,
                    source_version="api-sports-v3",
                )
            club_index += 1
            player_index = 0

        return RealPlayerSourcePage(
            provider_name=self.name,
            items=tuple(items),
            next_cursor=None,
            exhausted=True,
            source_version="api-sports-v3",
        )

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_seconds: int | None = None,
        rate_limit_per_minute: int | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderConfigurationError(f"{ENV_API_SPORTS_API_KEY} is required for the api_sports provider.")
        self._throttle(rate_limit_per_minute)
        response = self.session.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=timeout_seconds or self.default_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        errors = payload.get("errors")
        if isinstance(errors, dict) and errors:
            raise ProviderConfigurationError(json.dumps(errors, sort_keys=True))
        return payload

    def _throttle(self, rate_limit_per_minute: int | None) -> None:
        if rate_limit_per_minute is None or rate_limit_per_minute <= 0:
            return
        min_interval_seconds = 60.0 / rate_limit_per_minute
        now = time.monotonic()
        elapsed = now - self._last_request_started_at
        if self._last_request_started_at and elapsed < min_interval_seconds:
            time.sleep(min_interval_seconds - elapsed)
        self._last_request_started_at = time.monotonic()

    def _build_unique_club_directory(
        self,
        *,
        timeout_seconds: int | None,
        rate_limit_per_minute: int | None,
    ) -> list[dict[str, str | None]]:
        response = self._get(
            "/leagues",
            params={"current": "true"},
            timeout_seconds=timeout_seconds,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        competitions = sorted(
            response.get("response", []),
            key=lambda item: str(((item.get("league") or {}).get("id")) or ""),
        )
        clubs_by_id: dict[str, dict[str, str | None]] = {}
        for competition in competitions:
            season = self._current_season(competition.get("seasons") or [])
            coverage = (season.get("coverage") or {}) if season else {}
            if not bool(coverage.get("players")):
                continue
            league = competition.get("league") or {}
            country = competition.get("country") or {}
            competition_id = str(league.get("id") or "").strip()
            if not competition_id:
                continue
            season_id = self._season_id(competition_id, season.get("year") if season else None)
            team_params: dict[str, Any] = {"league": competition_id}
            if season and season.get("year") is not None:
                team_params["season"] = season.get("year")
            clubs_response = self._get(
                "/teams",
                params=team_params,
                timeout_seconds=timeout_seconds,
                rate_limit_per_minute=rate_limit_per_minute,
            )
            for club in clubs_response.get("response", []):
                team = club.get("team") or {}
                club_id = str(team.get("id") or "").strip()
                if not club_id or club_id in clubs_by_id:
                    continue
                clubs_by_id[club_id] = {
                    "club_id": club_id,
                    "club_name": self._clean_text(team.get("name")),
                    "competition_id": competition_id,
                    "competition_name": self._clean_text(league.get("name")),
                    "country_name": self._clean_text(country.get("name")),
                    "season_id": season_id,
                }
        return [clubs_by_id[club_id] for club_id in sorted(clubs_by_id)]

    def _build_directory_item(
        self,
        raw_player: dict[str, Any],
        *,
        club_context: dict[str, str | None],
    ) -> RealPlayerSourceItem:
        payload = dict(raw_player)
        payload["provider_player_id"] = str(raw_player.get("id") or "").strip()
        payload["currentClub"] = {
            "id": club_context["club_id"],
            "name": club_context["club_name"],
        }
        payload["currentCompetition"] = {
            "id": club_context["competition_id"],
            "name": club_context["competition_name"],
        }
        payload["season"] = {"id": club_context["season_id"]}
        return RealPlayerSourceItem(
            provider_player_id=str(raw_player.get("id") or "").strip(),
            full_name=self._clean_text(raw_player.get("name")) or "Unknown Player",
            display_position=self._clean_text(raw_player.get("position")),
            age=int(raw_player["age"]) if raw_player.get("age") is not None else None,
            current_club_id=club_context["club_id"],
            current_club_name=club_context["club_name"],
            current_competition_id=club_context["competition_id"],
            current_competition_name=club_context["competition_name"],
            current_season_id=club_context["season_id"],
            raw_payload=payload,
        )

    def _transform_country(self, payload: dict[str, Any]) -> dict[str, Any]:
        code = self._clean_text(payload.get("code"))
        name = self._clean_text(payload.get("name")) or "Unknown Country"
        return {
            "id": code or name,
            "name": name,
            "countryCode": code,
            "code": code,
            "flag": payload.get("flag"),
        }

    def _transform_competition(self, payload: dict[str, Any]) -> dict[str, Any]:
        league = payload.get("league") or {}
        country = payload.get("country") or {}
        current_season = self._current_season(payload.get("seasons") or [])
        return {
            "id": league.get("id"),
            "name": self._clean_text(league.get("name")),
            "type": self._clean_text(league.get("type")),
            "area": {
                "id": self._clean_text(country.get("code")) or self._clean_text(country.get("name")),
                "name": self._clean_text(country.get("name")),
                "countryCode": self._clean_text(country.get("code")),
                "code": self._clean_text(country.get("code")),
            },
            "currentSeason": self._transform_season(current_season, competition_id=str(league.get("id") or "")),
            "emblem": league.get("logo"),
        }

    def _transform_season(self, payload: dict[str, Any] | None, *, competition_id: str) -> dict[str, Any]:
        if not payload:
            return {"id": None}
        season_year = payload.get("year")
        return {
            "id": self._season_id(competition_id, season_year),
            "year": season_year,
            "startDate": payload.get("start"),
            "endDate": payload.get("end"),
            "current": bool(payload.get("current")),
            "currentMatchday": None,
        }

    def _transform_club(self, payload: dict[str, Any]) -> dict[str, Any]:
        team = payload.get("team") or {}
        venue = payload.get("venue") or {}
        country_name = self._clean_text(team.get("country"))
        return {
            "id": team.get("id"),
            "name": self._clean_text(team.get("name")),
            "shortName": self._clean_text(team.get("name")),
            "tla": self._clean_text(team.get("code")),
            "area": {
                "id": country_name,
                "name": country_name,
            },
            "founded": team.get("founded"),
            "venue": self._clean_text(venue.get("name")),
            "crest": team.get("logo"),
        }

    def _transform_player(self, payload: dict[str, Any], *, team: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": payload.get("id"),
            "name": self._clean_text(payload.get("name")),
            "position": self._clean_text(payload.get("position")),
            "shirtNumber": payload.get("number"),
            "age": payload.get("age"),
            "currentTeamId": team.get("id"),
            "photo": payload.get("photo"),
        }

    def _transform_match(self, payload: dict[str, Any]) -> dict[str, Any]:
        fixture = payload.get("fixture") or {}
        league = payload.get("league") or {}
        teams = payload.get("teams") or {}
        home_team = teams.get("home") or {}
        away_team = teams.get("away") or {}
        winner: dict[str, Any] = {}
        if home_team.get("winner") is True:
            winner = {"id": home_team.get("id")}
        elif away_team.get("winner") is True:
            winner = {"id": away_team.get("id")}
        score = payload.get("score") or {}
        fulltime = score.get("fulltime") or {}
        return {
            "id": fixture.get("id"),
            "competition": {"id": league.get("id")},
            "season": {"id": self._season_id(str(league.get("id") or ""), league.get("season"))},
            "homeTeam": {"id": home_team.get("id")},
            "awayTeam": {"id": away_team.get("id")},
            "winner": winner,
            "utcDate": fixture.get("date"),
            "status": self._normalize_match_status((fixture.get("status") or {}).get("short")),
            "stage": self._clean_text(league.get("round")),
            "matchday": self._matchday_from_round(league.get("round")),
            "venue": self._clean_text((fixture.get("venue") or {}).get("name")),
            "score": {
                "fullTime": {
                    "home": fulltime.get("home"),
                    "away": fulltime.get("away"),
                }
            },
        }

    def _transform_standing_row(self, payload: dict[str, Any]) -> dict[str, Any]:
        overall = payload.get("all") or {}
        goals = overall.get("goals") or {}
        return {
            "position": payload.get("rank"),
            "team": {"id": (payload.get("team") or {}).get("id")},
            "playedGames": overall.get("played"),
            "won": overall.get("win"),
            "draw": overall.get("draw"),
            "lost": overall.get("lose"),
            "goalsFor": goals.get("for"),
            "goalsAgainst": goals.get("against"),
            "goalDifference": payload.get("goalsDiff"),
            "points": payload.get("points"),
            "form": self._clean_text(payload.get("form")),
        }

    def _current_season(self, seasons: list[dict[str, Any]]) -> dict[str, Any]:
        for season in seasons:
            if season.get("current"):
                return season
        return seasons[0] if seasons else {}

    def _season_year(self, season_id: str | None) -> int | None:
        if not season_id:
            return None
        match = _SEASON_DIGIT_RE.search(str(season_id))
        return int(match.group(1)) if match else None

    def _season_id(self, competition_id: str, season_year: Any) -> str | None:
        if season_year in (None, ""):
            return None
        return f"{competition_id}-{season_year}"

    def _matchday_from_round(self, round_value: Any) -> int | None:
        match = _NUMBER_RE.search(str(round_value or ""))
        return int(match.group(1)) if match else None

    def _normalize_match_status(self, short_status: Any) -> str:
        code = str(short_status or "").strip().upper()
        if code in {"FT", "AET", "PEN"}:
            return "FINISHED"
        if code in {"NS", "TBD"}:
            return "SCHEDULED"
        if code in {"PST"}:
            return "POSTPONED"
        if code in {"CANC", "ABD", "AWD", "WO"}:
            return "CANCELLED"
        if code in {"INT", "SUSP"}:
            return "SUSPENDED"
        if code:
            return "LIVE"
        return "SCHEDULED"

    def _clean_text(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        text = str(value).replace("-", " ").strip()
        return " ".join(text.split()) or None

    def _decode_directory_cursor(self, cursor: str | None) -> dict[str, int]:
        if not cursor:
            return {"club_index": 0, "player_index": 0}
        try:
            payload = json.loads(cursor)
        except json.JSONDecodeError:
            return {"club_index": 0, "player_index": 0}
        return {
            "club_index": max(0, int(payload.get("club_index", 0))),
            "player_index": max(0, int(payload.get("player_index", 0))),
        }

    def _encode_directory_cursor(self, *, club_index: int, player_index: int) -> str:
        return json.dumps({"club_index": club_index, "player_index": player_index}, sort_keys=True)
