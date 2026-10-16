from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
import time
from typing import TYPE_CHECKING
from typing import Any

import requests

from app.ingestion.constants import ENV_SPORTMONKS_API_TOKEN, ENV_SPORTMONKS_BASE_URL
from app.ingestion.schemas import ProviderHealthSnapshot, RecentUpdateFeed

from .base import BaseFootballProvider, ProviderConfigurationError
from .import_models import RealPlayerSourceItem, RealPlayerSourcePage

if TYPE_CHECKING:
    from app.core.config import Settings


_NUMBER_RE = re.compile(r"(\d+)")

_STAT_CODE_ALIASES = {
    "appearances": ("appearances",),
    "starts": ("lineups",),
    "minutes": ("minutes-played",),
    "goals": ("goals", "goals-total", "goals-scored"),
    "assists": ("assists", "goal-assists"),
    "yellow_cards": ("yellowcards", "yellow-cards"),
    "red_cards": ("redcards", "red-cards"),
    "clean_sheets": ("cleansheets", "cleansheet", "clean-sheets"),
    "saves": ("saves",),
    "rating": ("rating",),
}

_GLOBAL_DIRECTORY_PAGE_SIZE = 25
_GLOBAL_DIRECTORY_MAX_SOURCE_PAGES_PER_BATCH = 20
_GLOBAL_DIRECTORY_MAX_AGE_YEARS = 40
_GLOBAL_DIRECTORY_MIN_AGE_YEARS = 15
_GLOBAL_DIRECTORY_RECENT_ACTIVITY_DAYS = 730
_GLOBAL_DIRECTORY_PLAYER_TYPE_IDS = {24, 25, 26, 27}


class SportMonksAdapter(BaseFootballProvider):
    name = "sportmonks"

    def __init__(self, *, settings: Settings | None = None) -> None:
        self.base_url = (
            settings.sportmonks_base_url
            if settings is not None
            else os.getenv(ENV_SPORTMONKS_BASE_URL, "https://api.sportmonks.com/v3/football")
        ).rstrip("/")
        self.api_token = settings.sportmonks_api_token if settings is not None else os.getenv(ENV_SPORTMONKS_API_TOKEN)
        self.default_timeout_seconds = settings.provider_timeout_seconds if settings is not None else 30
        self.session = requests.Session()
        self._last_request_started_at = 0.0
        self._request_timeout_override: int | None = None
        self._request_rate_limit_override: int | None = None
        self._team_directory_context_cache: dict[str, dict[str, str | None]] = {}

    def healthcheck(self) -> ProviderHealthSnapshot:
        if not self.api_token:
            return ProviderHealthSnapshot(
                provider_name=self.name,
                ok=False,
                configured=False,
                detail=f"Missing {ENV_SPORTMONKS_API_TOKEN}.",
            )
        started = time.perf_counter()
        try:
            self._get("/players", params={"per_page": 1})
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
            detail="SportMonks reachable.",
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def fetch_countries(self) -> list[dict[str, Any]]:
        return [
            self._transform_country(item)
            for item in self._iterate_pages(
                "/countries",
                params={"per_page": 50},
            )
        ]

    def fetch_competitions(self) -> list[dict[str, Any]]:
        competitions = [
            self._transform_competition(item)
            for item in self._iterate_pages(
                "/leagues",
                params={"include": "country;currentseason", "per_page": 50},
            )
        ]
        return sorted(
            competitions,
            key=lambda item: (
                0 if str(item.get("type") or "").strip().lower() == "league" else 1,
                str(item.get("id") or ""),
            ),
        )

    def fetch_seasons(self, competition_id: str) -> list[dict[str, Any]]:
        response = self._get(f"/leagues/{competition_id}", params={"include": "country;seasons"})
        league = response.get("data") or {}
        seasons = [self._transform_season(item) for item in league.get("seasons") or []]
        return sorted(
            seasons,
            key=lambda item: str(item.get("id") or ""),
        )

    def fetch_clubs(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        resolved_season_id = season_id or self._default_season_id(competition_id)
        if not resolved_season_id:
            return []
        response = self._get(f"/teams/seasons/{resolved_season_id}")
        return [self._transform_club(item) for item in response.get("data") or []]

    def fetch_players(self, club_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        del season_id
        response = self._get(
            f"/squads/teams/{club_id}",
            params={"include": "player.country;player.nationality;player.city;position;detailedPosition"},
        )
        return [self._transform_squad_player(item) for item in response.get("data") or []]

    def fetch_player_stats(
        self,
        player_id: str,
        *,
        season_id: str | None = None,
        competition_id: str | None = None,
        club_id: str | None = None,
    ) -> dict[str, Any]:
        del competition_id
        response = self._get(
            f"/players/{player_id}",
            params={
                "include": "statistics.details.type;teams;position;detailedPosition;country;nationality",
            },
        )
        player = response.get("data") or {}
        statistics = list(player.get("statistics") or [])
        record = self._select_stat_record(statistics, season_id=season_id, club_id=club_id)
        if record is None:
            return {"season": {}, "matches": []}
        return {"season": self._transform_player_statistics(record), "matches": []}

    def fetch_matches(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        resolved_season_id = season_id or self._default_season_id(competition_id)
        if not resolved_season_id:
            return []
        response = self._get(
            f"/seasons/{resolved_season_id}",
            params={
                "include": "league;fixtures.participants;fixtures.state;fixtures.venue;fixtures.round;fixtures.scores"
            },
        )
        season = response.get("data") or {}
        return [
            self._transform_fixture(item, competition_id=competition_id, season_id=resolved_season_id)
            for item in season.get("fixtures") or []
        ]

    def fetch_team_standings(self, competition_id: str, season_id: str | None = None) -> dict[str, Any]:
        resolved_season_id = season_id or self._default_season_id(competition_id)
        if not resolved_season_id:
            return {
                "competition": {"id": competition_id},
                "season": {"id": season_id},
                "standings": [],
            }
        response = self._get(
            f"/standings/seasons/{resolved_season_id}",
            params={"include": "participant;details.type"},
        )
        rows = response.get("data") or []
        return {
            "competition": {"id": competition_id},
            "season": {"id": resolved_season_id},
            "standings": [
                {
                    "type": "total",
                    "table": [self._transform_standing_row(item) for item in rows],
                }
            ],
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
        self._request_timeout_override = timeout_seconds
        self._request_rate_limit_override = rate_limit_per_minute
        try:
            state = self._decode_directory_cursor(cursor, batch_size=batch_size)
            page_number = state["page"]
            per_page = state["per_page"]
            player_index = state["player_index"]
            source_pages_scanned = 0
            items: list[RealPlayerSourceItem] = []

            while len(items) < batch_size and source_pages_scanned < _GLOBAL_DIRECTORY_MAX_SOURCE_PAGES_PER_BATCH:
                response = self._get(
                    "/players",
                    params={
                        "page": page_number,
                        "per_page": per_page,
                        "include": "country;nationality;position;detailedPosition;teams.team;teams.team.country",
                    },
                )
                pagination = response.get("pagination") or {}
                raw_players = list(response.get("data") or [])
                current_index = player_index
                while current_index < len(raw_players) and len(items) < batch_size:
                    raw_player = raw_players[current_index]
                    current_index += 1
                    if not self._is_global_directory_candidate(raw_player):
                        continue
                    items.append(self._build_global_directory_item(raw_player))

                if current_index < len(raw_players):
                    return RealPlayerSourcePage(
                        provider_name=self.name,
                        items=tuple(items),
                        next_cursor=self._encode_directory_cursor(
                            page=page_number,
                            per_page=per_page,
                            player_index=current_index,
                        ),
                        exhausted=False,
                        source_version="sportmonks-v3-global-directory",
                    )

                if not pagination.get("has_more"):
                    return RealPlayerSourcePage(
                        provider_name=self.name,
                        items=tuple(items),
                        next_cursor=None,
                        exhausted=True,
                        source_version="sportmonks-v3-global-directory",
                    )

                page_number += 1
                player_index = 0
                source_pages_scanned += 1

            return RealPlayerSourcePage(
                provider_name=self.name,
                items=tuple(items),
                next_cursor=self._encode_directory_cursor(
                    page=page_number,
                    per_page=per_page,
                    player_index=0,
                ),
                exhausted=False,
                source_version="sportmonks-v3-global-directory",
            )
        finally:
            self._request_timeout_override = None
            self._request_rate_limit_override = None

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_seconds: int | None = None,
        rate_limit_per_minute: int | None = None,
    ) -> dict[str, Any]:
        if not self.api_token:
            raise ProviderConfigurationError(f"{ENV_SPORTMONKS_API_TOKEN} is required for the sportmonks provider.")
        request_params = dict(params or {})
        request_params["api_token"] = self.api_token
        resolved_rate_limit = (
            rate_limit_per_minute if rate_limit_per_minute is not None else self._request_rate_limit_override
        )
        self._throttle(resolved_rate_limit)
        response = self.session.get(
            f"{self.base_url}{path}",
            params=request_params,
            timeout=timeout_seconds or self._request_timeout_override or self.default_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("message") and response.status_code >= 400:
            raise ProviderConfigurationError(str(payload["message"]))
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

    def _iterate_pages(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        page = 1
        results: list[dict[str, Any]] = []
        while True:
            page_params = dict(params or {})
            page_params["page"] = page
            payload = self._get(path, params=page_params)
            results.extend(payload.get("data") or [])
            pagination = payload.get("pagination") or {}
            if not pagination.get("has_more"):
                return results
            page += 1

    def _default_season_id(self, competition_id: str) -> str | None:
        response = self._get(f"/leagues/{competition_id}", params={"include": "currentseason"})
        league = response.get("data") or {}
        current_season = league.get("currentseason") or {}
        season_id = current_season.get("id")
        return str(season_id) if season_id is not None else None

    def _build_unique_club_directory(
        self,
        *,
        timeout_seconds: int | None,
        rate_limit_per_minute: int | None,
    ) -> list[dict[str, str | None]]:
        del timeout_seconds, rate_limit_per_minute
        competitions = self.fetch_competitions()
        clubs_by_id: dict[str, dict[str, str | None]] = {}
        for competition in competitions:
            competition_id = str(competition.get("id") or "").strip()
            season = competition.get("currentSeason") or {}
            season_id = str(season.get("id") or "").strip()
            if not competition_id or not season_id:
                continue
            for club in self.fetch_clubs(competition_id, season_id):
                club_id = str(club.get("id") or "").strip()
                if not club_id or club_id in clubs_by_id:
                    continue
                clubs_by_id[club_id] = {
                    "club_id": club_id,
                    "club_name": self._clean_text(club.get("name")),
                    "competition_id": competition_id,
                    "competition_name": self._clean_text(competition.get("name")),
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
        photo_url = self._clean_text(raw_player.get("image_path") or raw_player.get("imagePath"))
        if photo_url:
            payload["image_path"] = photo_url
            payload["photo_url"] = photo_url
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
            full_name=self._clean_text(
                raw_player.get("displayName") or raw_player.get("name") or raw_player.get("commonName")
            )
            or "Unknown Player",
            first_name=self._clean_text(raw_player.get("firstName")),
            last_name=self._clean_text(raw_player.get("lastName")),
            short_name=self._clean_text(raw_player.get("shortName") or raw_player.get("commonName")),
            display_position=self._clean_text(raw_player.get("detailedPosition") or raw_player.get("position")),
            nationality_name=self._clean_text(raw_player.get("nationality")),
            nationality_code=self._clean_text(raw_player.get("nationalityCode")),
            date_of_birth=self._parse_date(raw_player.get("dateOfBirth")),
            current_club_id=club_context["club_id"],
            current_club_name=club_context["club_name"],
            current_competition_id=club_context["competition_id"],
            current_competition_name=club_context["competition_name"],
            current_season_id=club_context["season_id"],
            metadata_json={"photo_url": photo_url} if photo_url else {},
            raw_payload=payload,
        )

    def _build_global_directory_item(self, raw_player: dict[str, Any]) -> RealPlayerSourceItem:
        team_context = self._select_directory_team_context(raw_player)
        position = raw_player.get("position") or {}
        detailed_position = raw_player.get("detailedposition") or raw_player.get("detailedPosition") or {}
        nationality = raw_player.get("nationality") or {}
        country = raw_player.get("country") or {}
        provider_player_id = str(raw_player.get("id") or "").strip()
        photo_url = self._clean_text(raw_player.get("image_path") or raw_player.get("imagePath"))
        payload = {
            "id": raw_player.get("id"),
            "provider_player_id": provider_player_id,
            "name": self._clean_text(raw_player.get("name")),
            "displayName": self._clean_text(raw_player.get("display_name") or raw_player.get("displayName")),
            "commonName": self._clean_text(raw_player.get("common_name") or raw_player.get("commonName")),
            "firstName": self._clean_text(raw_player.get("firstname") or raw_player.get("firstName")),
            "lastName": self._clean_text(raw_player.get("lastname") or raw_player.get("lastName")),
            "position": self._clean_text(position.get("name")),
            "detailedPosition": self._clean_text(detailed_position.get("name")),
            "dateOfBirth": raw_player.get("date_of_birth") or raw_player.get("dateOfBirth"),
            "nationality": self._clean_text(nationality.get("name") or country.get("name")),
            "nationalityCode": self._clean_text(
                nationality.get("iso2") or nationality.get("iso3") or country.get("iso2") or country.get("iso3")
            ),
            "country": self._clean_text(country.get("name")),
            "height": raw_player.get("height"),
            "weight": raw_player.get("weight"),
            "type_id": raw_player.get("type_id"),
            "image_path": photo_url,
            "photo_url": photo_url,
        }
        if team_context is not None:
            payload["currentClub"] = {
                "id": team_context["club_id"],
                "name": team_context["club_name"],
            }
            if team_context.get("competition_id") or team_context.get("competition_name"):
                payload["currentCompetition"] = {
                    "id": team_context.get("competition_id"),
                    "name": team_context.get("competition_name"),
                }
            if team_context.get("season_id"):
                payload["season"] = {"id": team_context["season_id"]}
        return RealPlayerSourceItem(
            provider_player_id=provider_player_id,
            full_name=self._clean_text(
                raw_player.get("display_name") or raw_player.get("name") or raw_player.get("common_name")
            )
            or "Unknown Player",
            first_name=self._clean_text(raw_player.get("firstname") or raw_player.get("first_name")),
            last_name=self._clean_text(raw_player.get("lastname") or raw_player.get("last_name")),
            short_name=self._clean_text(raw_player.get("common_name") or raw_player.get("display_name")),
            display_position=self._clean_text(detailed_position.get("name") or position.get("name")),
            nationality_name=self._clean_text(nationality.get("name") or country.get("name")),
            nationality_code=self._clean_text(
                nationality.get("iso2") or nationality.get("iso3") or country.get("iso2") or country.get("iso3")
            ),
            date_of_birth=self._parse_date(raw_player.get("date_of_birth") or raw_player.get("dateOfBirth")),
            current_club_id=team_context["club_id"] if team_context is not None else None,
            current_club_name=team_context["club_name"] if team_context is not None else None,
            current_competition_id=team_context["competition_id"] if team_context is not None else None,
            current_competition_name=team_context["competition_name"] if team_context is not None else None,
            current_season_id=team_context["season_id"] if team_context is not None else None,
            metadata_json={"photo_url": photo_url} if photo_url else {},
            raw_payload=payload,
        )

    def _is_global_directory_candidate(self, raw_player: dict[str, Any]) -> bool:
        if self._select_directory_team_context(raw_player) is None:
            return False

        player_type_id = self._int_value(raw_player.get("type_id"))
        position_name = self._clean_text(
            ((raw_player.get("detailedposition") or raw_player.get("detailedPosition") or {}).get("name"))
            or ((raw_player.get("position") or {}).get("name"))
        )
        if player_type_id not in _GLOBAL_DIRECTORY_PLAYER_TYPE_IDS and not position_name:
            return False

        date_of_birth = self._parse_date(raw_player.get("date_of_birth") or raw_player.get("dateOfBirth"))
        if date_of_birth is None:
            return False
        age_years = self._age_on(date_of_birth)
        if (
            age_years is None
            or age_years < _GLOBAL_DIRECTORY_MIN_AGE_YEARS
            or age_years > _GLOBAL_DIRECTORY_MAX_AGE_YEARS
        ):
            return False

        return True

    def _select_directory_team_context(self, raw_player: dict[str, Any]) -> dict[str, str | None] | None:
        memberships = [
            item
            for item in (raw_player.get("teams") or [])
            if self._membership_is_current(item) and self._membership_has_recent_activity(item)
        ]
        if not memberships:
            return None
        selected = max(
            memberships,
            key=lambda item: (
                1 if item.get("end") in (None, "") else 0,
                self._clean_text(((item.get("team") or {}).get("last_played_at"))) or "",
                int(item.get("id") or 0),
            ),
        )
        team = selected.get("team") or {}
        club_id = str(team.get("id") or selected.get("team_id") or "").strip()
        club_name = self._clean_text(team.get("name"))
        team_context = self._load_team_directory_context(club_id)
        if club_id and not any(team_context.values()):
            return None
        if not club_id and not club_name:
            return None
        return {
            "club_id": club_id or None,
            "club_name": club_name or team_context.get("club_name"),
            "competition_id": team_context.get("competition_id"),
            "competition_name": team_context.get("competition_name"),
            "season_id": team_context.get("season_id"),
        }

    def _load_team_directory_context(self, club_id: str | None) -> dict[str, str | None]:
        if not club_id:
            return {
                "club_name": None,
                "competition_id": None,
                "competition_name": None,
                "season_id": None,
            }
        cached = self._team_directory_context_cache.get(club_id)
        if cached is not None:
            return cached
        context = {
            "club_name": None,
            "competition_id": None,
            "competition_name": None,
            "season_id": None,
        }
        try:
            response = self._get(
                f"/teams/{club_id}",
                params={
                    "include": (
                        "country;"
                        "activeseasons;activeseasons.league;activeseasons.league.country;"
                        "latest;latest.league;latest.league.country"
                    )
                },
            )
        except Exception:
            self._team_directory_context_cache[club_id] = context
            return context
        team = response.get("data") or {}
        if not team:
            self._team_directory_context_cache[club_id] = context
            return context
        context["club_name"] = self._clean_text(team.get("name"))
        active_seasons = list(team.get("activeseasons") or [])
        latest_fixtures = list(team.get("latest") or [])
        selected_competition = self._select_team_competition(
            active_seasons=active_seasons,
            fixtures=latest_fixtures,
        )
        if selected_competition is not None:
            context["competition_id"] = selected_competition.get("competition_id")
            context["competition_name"] = selected_competition.get("competition_name")
            context["season_id"] = selected_competition.get("season_id")
        self._team_directory_context_cache[club_id] = context
        return context

    def _select_team_competition(
        self,
        *,
        active_seasons: list[dict[str, Any]],
        fixtures: list[dict[str, Any]],
    ) -> dict[str, str | None] | None:
        selected = self._select_active_season_competition(active_seasons)
        if selected is not None:
            return selected
        return self._select_fixture_competition(fixtures)

    def _select_active_season_competition(
        self,
        active_seasons: list[dict[str, Any]],
    ) -> dict[str, str | None] | None:
        if not active_seasons:
            return None
        selected = sorted(
            active_seasons,
            key=lambda item: (
                0 if bool(item.get("is_current")) else 1,
                0 if str(((item.get("league") or {}).get("sub_type") or "")).strip().lower() == "domestic" else 1,
                0 if str(((item.get("league") or {}).get("type") or "")).strip().lower() == "league" else 1,
                self._clean_text(item.get("starting_at")) or "",
            ),
            reverse=False,
        )[0]
        league = selected.get("league") or {}
        competition_id = str(league.get("id") or selected.get("league_id") or "").strip() or None
        competition_name = self._clean_text(league.get("name"))
        season_id = str(selected.get("id") or "").strip() or None
        if competition_id is None and competition_name is None:
            return None
        return {
            "competition_id": competition_id,
            "competition_name": competition_name,
            "season_id": season_id,
        }

    def _select_fixture_competition(self, fixtures: list[dict[str, Any]]) -> dict[str, str | None] | None:
        if not fixtures:
            return None
        selected = sorted(
            fixtures,
            key=lambda item: (
                0 if str(((item.get("league") or {}).get("sub_type") or "")).strip().lower() == "domestic" else 1,
                0 if str(((item.get("league") or {}).get("type") or "")).strip().lower() == "league" else 1,
                self._clean_text(item.get("starting_at")) or "",
            ),
            reverse=False,
        )[0]
        league = selected.get("league") or {}
        competition_id = str(league.get("id") or selected.get("league_id") or "").strip() or None
        competition_name = self._clean_text(league.get("name"))
        season_id = str(selected.get("season_id") or "").strip() or None
        if competition_id is None and competition_name is None:
            return None
        return {
            "competition_id": competition_id,
            "competition_name": competition_name,
            "season_id": season_id,
        }

    def _membership_is_current(self, membership: dict[str, Any]) -> bool:
        end_date = self._parse_date(membership.get("end"))
        if end_date is None:
            return True
        return end_date >= datetime.now(timezone.utc).date()

    def _membership_has_recent_activity(self, membership: dict[str, Any]) -> bool:
        team = membership.get("team") or {}
        last_played_at = self._parse_date(team.get("last_played_at"))
        if last_played_at is None:
            return False
        return (datetime.now(timezone.utc).date() - last_played_at).days <= _GLOBAL_DIRECTORY_RECENT_ACTIVITY_DAYS

    def _age_on(self, date_of_birth):
        reference_date = datetime.now(timezone.utc).date()
        years = reference_date.year - date_of_birth.year
        if (reference_date.month, reference_date.day) < (date_of_birth.month, date_of_birth.day):
            years -= 1
        return years

    def _transform_country(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": payload.get("id") or payload.get("fifa_name") or payload.get("name"),
            "name": self._clean_text(payload.get("name")),
            "countryCode": self._clean_text(payload.get("iso2")),
            "code": self._clean_text(payload.get("iso3") or payload.get("fifa_name")),
            "flag": payload.get("image_path"),
        }

    def _transform_competition(self, payload: dict[str, Any]) -> dict[str, Any]:
        country = payload.get("country") or {}
        current_season = payload.get("currentseason") or {}
        return {
            "id": payload.get("id"),
            "name": self._clean_text(payload.get("name")),
            "type": self._clean_text(payload.get("type")),
            "area": {
                "id": country.get("id"),
                "name": self._clean_text(country.get("name")),
                "countryCode": self._clean_text(country.get("iso2")),
                "code": self._clean_text(country.get("iso3") or country.get("fifa_name")),
            },
            "currentSeason": self._transform_season(current_season),
            "emblem": payload.get("image_path"),
        }

    def _transform_season(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        if not payload:
            return {"id": None}
        return {
            "id": payload.get("id"),
            "startDate": payload.get("starting_at"),
            "endDate": payload.get("ending_at"),
            "current": bool(payload.get("is_current")),
            "label": self._clean_text(payload.get("name")),
        }

    def _transform_club(self, payload: dict[str, Any]) -> dict[str, Any]:
        country = payload.get("country") or {}
        venue = payload.get("venue") or {}
        return {
            "id": payload.get("id"),
            "name": self._clean_text(payload.get("name")),
            "shortName": self._clean_text(payload.get("name")),
            "tla": self._clean_text(payload.get("short_code")),
            "area": {
                "id": country.get("id"),
                "name": self._clean_text(country.get("name")),
            },
            "founded": payload.get("founded"),
            "venue": self._clean_text(venue.get("name")),
            "crest": payload.get("image_path"),
        }

    def _transform_squad_player(self, payload: dict[str, Any]) -> dict[str, Any]:
        player = payload.get("player") or {}
        country = player.get("country") or {}
        nationality = player.get("nationality") or {}
        return {
            "id": player.get("id"),
            "name": self._clean_text(player.get("name")),
            "displayName": self._clean_text(player.get("display_name")),
            "commonName": self._clean_text(player.get("common_name")),
            "firstName": self._clean_text(player.get("firstname")),
            "lastName": self._clean_text(player.get("lastname")),
            "position": self._clean_text((payload.get("position") or {}).get("name")),
            "detailedPosition": self._clean_text((payload.get("detailedposition") or {}).get("name")),
            "dateOfBirth": player.get("date_of_birth"),
            "nationality": self._clean_text(nationality.get("name")),
            "nationalityCode": self._clean_text(nationality.get("iso2") or nationality.get("iso3")),
            "country": self._clean_text(country.get("name")),
            "height": player.get("height"),
            "weight": player.get("weight"),
            "shirtNumber": payload.get("jersey_number"),
            "imagePath": self._clean_text(player.get("image_path")),
            "photo_url": self._clean_text(player.get("image_path")),
        }

    def _transform_player_statistics(self, payload: dict[str, Any]) -> dict[str, Any]:
        details = payload.get("details") or []
        detail_map = self._detail_map(details)
        return {
            "appearances": self._detail_total(detail_map, *_STAT_CODE_ALIASES["appearances"]),
            "starts": self._detail_total(detail_map, *_STAT_CODE_ALIASES["starts"]),
            "minutes": self._detail_total(detail_map, *_STAT_CODE_ALIASES["minutes"]),
            "goals": self._detail_total(detail_map, *_STAT_CODE_ALIASES["goals"]),
            "assists": self._detail_total(detail_map, *_STAT_CODE_ALIASES["assists"]),
            "yellowCards": self._detail_total(detail_map, *_STAT_CODE_ALIASES["yellow_cards"]),
            "redCards": self._detail_total(detail_map, *_STAT_CODE_ALIASES["red_cards"]),
            "cleanSheets": self._detail_total(detail_map, *_STAT_CODE_ALIASES["clean_sheets"]),
            "saves": self._detail_total(detail_map, *_STAT_CODE_ALIASES["saves"]),
            "averageRating": self._detail_average(detail_map, *_STAT_CODE_ALIASES["rating"]),
        }

    def _transform_fixture(
        self,
        payload: dict[str, Any],
        *,
        competition_id: str,
        season_id: str,
    ) -> dict[str, Any]:
        home = next(
            (item for item in payload.get("participants") or [] if (item.get("meta") or {}).get("location") == "home"),
            {},
        )
        away = next(
            (item for item in payload.get("participants") or [] if (item.get("meta") or {}).get("location") == "away"),
            {},
        )
        winner: dict[str, Any] = {}
        if (home.get("meta") or {}).get("winner") is True:
            winner = {"id": home.get("id")}
        elif (away.get("meta") or {}).get("winner") is True:
            winner = {"id": away.get("id")}
        home_score, away_score = self._fixture_scores(payload.get("scores") or [])
        round_name = self._clean_text((payload.get("round") or {}).get("name"))
        return {
            "id": payload.get("id"),
            "competition": {"id": competition_id},
            "season": {"id": season_id},
            "homeTeam": {"id": home.get("id")},
            "awayTeam": {"id": away.get("id")},
            "winner": winner,
            "utcDate": self._iso_datetime(payload.get("starting_at")),
            "status": self._normalize_match_status(
                (payload.get("state") or {}).get("short_name") or (payload.get("state") or {}).get("developer_name")
            ),
            "stage": round_name,
            "matchday": self._matchday_from_round(round_name),
            "venue": self._clean_text((payload.get("venue") or {}).get("name")),
            "score": {"fullTime": {"home": home_score, "away": away_score}},
        }

    def _transform_standing_row(self, payload: dict[str, Any]) -> dict[str, Any]:
        detail_map = self._detail_map(payload.get("details") or [])
        goals_for = self._detail_total(detail_map, "overall-goals-for")
        goals_against = self._detail_total(detail_map, "overall-goals-against")
        return {
            "position": payload.get("position"),
            "team": {"id": (payload.get("participant") or {}).get("id")},
            "playedGames": self._detail_total(detail_map, "overall-games-played"),
            "won": self._detail_total(detail_map, "overall-won"),
            "draw": self._detail_total(detail_map, "overall-draw"),
            "lost": self._detail_total(detail_map, "overall-lost"),
            "goalsFor": goals_for,
            "goalsAgainst": goals_against,
            "goalDifference": (
                goals_for - goals_against if goals_for is not None and goals_against is not None else None
            ),
            "points": payload.get("points"),
            "form": None,
        }

    def _select_stat_record(
        self,
        records: list[dict[str, Any]],
        *,
        season_id: str | None,
        club_id: str | None,
    ) -> dict[str, Any] | None:
        if not records:
            return None
        filtered = list(records)
        if season_id:
            filtered = [item for item in filtered if str(item.get("season_id") or "") == str(season_id)]
        if club_id:
            team_filtered = [item for item in filtered if str(item.get("team_id") or "") == str(club_id)]
            if team_filtered:
                filtered = team_filtered
        with_values = [item for item in filtered if item.get("has_values")]
        if with_values:
            filtered = with_values
        if not filtered:
            return None
        return sorted(
            filtered,
            key=lambda item: int(item.get("season_id") or 0),
            reverse=True,
        )[0]

    def _detail_map(self, details: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        mapped: dict[str, dict[str, Any]] = {}
        for detail in details:
            stat_type = detail.get("type") or {}
            code = str(stat_type.get("code") or stat_type.get("developer_name") or "").strip().lower()
            if not code:
                continue
            mapped[code] = detail.get("value") or {}
        return mapped

    def _detail_total(self, detail_map: dict[str, dict[str, Any]], *codes: str) -> int | None:
        for code in codes:
            value = detail_map.get(code)
            if not isinstance(value, dict):
                continue
            candidate = value.get("total")
            if candidate is None and len(value) == 1:
                candidate = next(iter(value.values()))
            if candidate is not None:
                return int(candidate)
        return None

    def _detail_average(self, detail_map: dict[str, dict[str, Any]], *codes: str) -> float | None:
        for code in codes:
            value = detail_map.get(code)
            if not isinstance(value, dict):
                continue
            candidate = value.get("average")
            if candidate is None and "total" in value:
                candidate = value.get("total")
            if candidate is not None:
                return float(candidate)
        return None

    def _fixture_scores(self, scores: list[dict[str, Any]]) -> tuple[int | None, int | None]:
        selected = [item for item in scores if str(item.get("description") or "").strip().upper() == "CURRENT"]
        if not selected:
            selected = scores
        home_score = None
        away_score = None
        for score in selected:
            score_payload = score.get("score") or {}
            participant = score_payload.get("participant")
            goals = score_payload.get("goals")
            if participant == "home":
                home_score = goals
            elif participant == "away":
                away_score = goals
        return home_score, away_score

    def _parse_date(self, value: Any):
        if value in (None, ""):
            return None
        text = str(value).strip()
        try:
            return datetime.fromisoformat(text[:10]).date()
        except ValueError:
            return None

    def _iso_datetime(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        text = str(value).strip().replace(" ", "T")
        if text.endswith("Z") or "+" in text:
            return text
        return f"{text}+00:00"

    def _matchday_from_round(self, round_value: Any) -> int | None:
        match = _NUMBER_RE.search(str(round_value or ""))
        return int(match.group(1)) if match else None

    def _normalize_match_status(self, state_value: Any) -> str:
        code = str(state_value or "").strip().upper()
        if code in {"FT", "FULL TIME"}:
            return "FINISHED"
        if code in {"NS", "NOT_STARTED"}:
            return "SCHEDULED"
        if code in {"POSTPONED", "PST"}:
            return "POSTPONED"
        if code in {"CANCELLED", "CANC"}:
            return "CANCELLED"
        if code in {"SUSPENDED", "SUSP"}:
            return "SUSPENDED"
        if code:
            return "LIVE"
        return "SCHEDULED"

    def _clean_text(self, value: Any) -> str | None:
        if value in (None, ""):
            return None
        return " ".join(str(value).strip().split()) or None

    def _decode_directory_cursor(self, cursor: str | None, *, batch_size: int) -> dict[str, int]:
        default_per_page = _GLOBAL_DIRECTORY_PAGE_SIZE
        if not cursor:
            return {"page": 1, "per_page": default_per_page, "player_index": 0}
        try:
            payload = json.loads(cursor)
        except json.JSONDecodeError:
            return {"page": 1, "per_page": default_per_page, "player_index": 0}
        page = payload.get("page")
        per_page = payload.get("per_page")
        player_index = payload.get("player_index")
        return {
            "page": max(1, int(page or 1)),
            "per_page": max(1, min(int(per_page or default_per_page), _GLOBAL_DIRECTORY_PAGE_SIZE)),
            "player_index": max(0, int(player_index or 0)),
        }

    def _encode_directory_cursor(self, *, page: int, per_page: int, player_index: int) -> str:
        return json.dumps({"page": page, "per_page": per_page, "player_index": player_index}, sort_keys=True)

    def _int_value(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
