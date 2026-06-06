from __future__ import annotations

import json
from datetime import datetime, timezone
import os
import time
from typing import TYPE_CHECKING
from typing import Any

from app.ingestion.constants import ENV_FOOTBALL_DATA_API_KEY, ENV_FOOTBALL_DATA_BASE_URL
from app.ingestion.schemas import ProviderHealthSnapshot, RecentUpdateFeed

from .base import BaseFootballProvider, ProviderConfigurationError
from .import_models import RealPlayerSourceItem, RealPlayerSourcePage

if TYPE_CHECKING:
    from app.core.config import Settings


class FootballDataAdapter(BaseFootballProvider):
    name = "football_data"

    def __init__(self, *, settings: Settings | None = None) -> None:
        import requests

        self.base_url = (
            settings.football_data_base_url
            if settings is not None
            else os.getenv(ENV_FOOTBALL_DATA_BASE_URL, "https://api.football-data.org/v4")
        ).rstrip("/")
        self.api_key = settings.football_data_api_key if settings is not None else os.getenv(ENV_FOOTBALL_DATA_API_KEY)
        self.default_timeout_seconds = settings.provider_timeout_seconds if settings is not None else 30
        self.session = requests.Session()
        self._last_request_started_at = 0.0
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
            team = self._get(
                f"/teams/{club_context['club_id']}",
                timeout_seconds=timeout_seconds,
                rate_limit_per_minute=rate_limit_per_minute,
            )
            squad = team.get("squad", [])
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
                    source_version="football-data-v4",
                )
            club_index += 1
            player_index = 0

        return RealPlayerSourcePage(
            provider_name=self.name,
            items=tuple(items),
            next_cursor=None,
            exhausted=True,
            source_version="football-data-v4",
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
            raise ProviderConfigurationError(f"{ENV_FOOTBALL_DATA_API_KEY} is required for the football_data provider.")
        self._throttle(rate_limit_per_minute)
        response = self.session.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=timeout_seconds or self.default_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def _season_param(self, season_id: str | None) -> int | None:
        if not season_id:
            return None
        digits = "".join(character for character in season_id if character.isdigit())
        if len(digits) >= 4:
            return int(digits[:4])
        return None

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
            "/competitions",
            timeout_seconds=timeout_seconds,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        competitions = sorted(
            response.get("competitions", []),
            key=lambda item: str(item.get("id") or ""),
        )
        clubs_by_id: dict[str, dict[str, str | None]] = {}
        for competition in competitions:
            competition_id = str(competition.get("id") or "").strip()
            if not competition_id:
                continue
            competition_name = str(competition.get("name") or "").strip() or None
            season_id = str(((competition.get("currentSeason") or {}).get("id")) or "").strip() or None
            params: dict[str, Any] = {}
            season_param = self._season_param(season_id)
            if season_param is not None:
                params["season"] = season_param
            clubs_response = self._get(
                f"/competitions/{competition_id}/teams",
                params=params or None,
                timeout_seconds=timeout_seconds,
                rate_limit_per_minute=rate_limit_per_minute,
            )
            for club in clubs_response.get("teams", []):
                club_id = str(club.get("id") or "").strip()
                if not club_id or club_id in clubs_by_id:
                    continue
                clubs_by_id[club_id] = {
                    "club_id": club_id,
                    "club_name": str(club.get("name") or "").strip() or None,
                    "competition_id": competition_id,
                    "competition_name": competition_name,
                    "season_id": season_id,
                }
        return [clubs_by_id[club_id] for club_id in sorted(clubs_by_id)]

    def _build_directory_item(
        self,
        raw_player: dict[str, Any],
        *,
        club_context: dict[str, str | None],
    ) -> RealPlayerSourceItem:
        birth_date = str(raw_player.get("dateOfBirth") or "").strip()
        nationality_name = str(raw_player.get("nationality") or "").strip() or None
        club_name = club_context["club_name"]
        club_id = club_context["club_id"]
        competition_id = club_context["competition_id"]
        competition_name = club_context["competition_name"]
        season_id = club_context["season_id"]
        payload = dict(raw_player)
        payload["provider_player_id"] = str(raw_player.get("id") or "").strip()
        payload["currentClub"] = {"id": club_id, "name": club_name}
        payload["currentCompetition"] = {"id": competition_id, "name": competition_name}
        payload["season"] = {"id": season_id}
        return RealPlayerSourceItem(
            provider_player_id=str(raw_player.get("id") or "").strip(),
            full_name=str(raw_player.get("name") or "").strip(),
            first_name=str(raw_player.get("firstName") or "").strip() or None,
            last_name=str(raw_player.get("lastName") or "").strip() or None,
            short_name=str(raw_player.get("shortName") or "").strip() or None,
            display_position=str(raw_player.get("position") or "").strip() or None,
            nationality_name=nationality_name,
            date_of_birth=datetime.fromisoformat(birth_date).date() if birth_date else None,
            current_club_id=club_id,
            current_club_name=club_name,
            current_competition_id=competition_id,
            current_competition_name=competition_name,
            current_season_id=season_id,
            raw_payload=payload,
        )

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
