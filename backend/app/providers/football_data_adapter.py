from __future__ import annotations

from datetime import datetime, timezone
import os
import time
from typing import Any

import requests

from app.ingestion.constants import ENV_FOOTBALL_DATA_API_KEY, ENV_FOOTBALL_DATA_BASE_URL
from app.ingestion.schemas import ProviderHealthSnapshot, RecentUpdateFeed

from .base import BaseFootballProvider, ProviderConfigurationError


class FootballDataAdapter(BaseFootballProvider):
    name = "football_data"

    def __init__(self) -> None:
        self.base_url = os.getenv(ENV_FOOTBALL_DATA_BASE_URL, "https://api.football-data.org/v4").rstrip("/")
        self.api_key = os.getenv(ENV_FOOTBALL_DATA_API_KEY)
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"X-Auth-Token": self.api_key})

    def healthcheck(self) -> ProviderHealthSnapshot:
        if not self.api_key:
            return ProviderHealthSnapshot(
                provider_name=self.name,
                ok=False,
                configured=False,
                detail=f"Missing {ENV_FOOTBALL_DATA_API_KEY}.",
            )
        started = time.perf_counter()
        try:
            self._get("/competitions")
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
            detail="football-data.org reachable.",
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def fetch_countries(self) -> list[dict[str, Any]]:
        response = self._get("/areas")
        return response.get("areas", [])

    def fetch_competitions(self) -> list[dict[str, Any]]:
        response = self._get("/competitions")
        return response.get("competitions", [])

    def fetch_seasons(self, competition_id: str) -> list[dict[str, Any]]:
        competition = self._get(f"/competitions/{competition_id}")
        current_season = competition.get("currentSeason")
        return [current_season] if current_season else []

    def fetch_clubs(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        season_param = self._season_param(season_id)
        if season_param is not None:
            params["season"] = season_param
        response = self._get(f"/competitions/{competition_id}/teams", params=params)
        return response.get("teams", [])

    def fetch_players(self, club_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        team = self._get(f"/teams/{club_id}")
        return team.get("squad", [])

    def fetch_player_stats(
        self,
        player_id: str,
        *,
        season_id: str | None = None,
        competition_id: str | None = None,
        club_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if competition_id:
            params["competitions"] = competition_id
        # football-data exposes aggregated person match stats on the matches subresource.
        # TODO: derive explicit season windows once provider entitlement and season mapping are finalized.
        response = self._get(f"/persons/{player_id}/matches", params=params)
        aggregations = response.get("aggregations", {})
        season_summary = {
            "appearances": aggregations.get("matchesOnPitch"),
            "starts": aggregations.get("startingXI"),
            "minutes": aggregations.get("minutesPlayed"),
            "goals": aggregations.get("goals"),
            "assists": aggregations.get("assists"),
            "yellowCards": aggregations.get("yellowCards"),
            "redCards": aggregations.get("redCards"),
        }
        matches = [
            {
                "id": f"{player_id}:{match.get('id')}",
                "matchId": match.get("id"),
                "minutes": None,
                "goals": None,
                "assists": None,
                "rating": None,
                "position": response.get("person", {}).get("position"),
                "started": None,
            }
            for match in response.get("matches", [])
        ]
        return {"season": season_summary, "matches": matches}

    def fetch_matches(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        season_param = self._season_param(season_id)
        if season_param is not None:
            params["season"] = season_param
        response = self._get(f"/competitions/{competition_id}/matches", params=params)
        return response.get("matches", [])

    def fetch_team_standings(self, competition_id: str, season_id: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        season_param = self._season_param(season_id)
        if season_param is not None:
            params["season"] = season_param
        return self._get(f"/competitions/{competition_id}/standings", params=params)

    def fetch_recent_updates(self, cursor: str | None) -> RecentUpdateFeed:
        # TODO: football-data does not expose a first-class "updated since" cursor for all entities.
        # Keep the adapter contract stable and let the service fall back to scheduled scoped refreshes.
        now = datetime.now(timezone.utc).isoformat()
        return RecentUpdateFeed(provider_name=self.name, cursor_value=cursor, next_cursor=now, updates=[])

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderConfigurationError(f"{ENV_FOOTBALL_DATA_API_KEY} is required for the football_data provider.")
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _season_param(self, season_id: str | None) -> int | None:
        if not season_id:
            return None
        digits = "".join(character for character in season_id if character.isdigit())
        if len(digits) >= 4:
            return int(digits[:4])
        return None
