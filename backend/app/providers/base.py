from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.app.ingestion.schemas import ProviderHealthSnapshot, RecentUpdateFeed


class ProviderConfigurationError(RuntimeError):
    pass


class BaseFootballProvider(ABC):
    name: str

    @abstractmethod
    def healthcheck(self) -> ProviderHealthSnapshot:
        raise NotImplementedError

    @abstractmethod
    def fetch_countries(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_competitions(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_seasons(self, competition_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_clubs(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_players(self, club_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_player_stats(
        self,
        player_id: str,
        *,
        season_id: str | None = None,
        competition_id: str | None = None,
        club_id: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_matches(self, competition_id: str, season_id: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def fetch_team_standings(self, competition_id: str, season_id: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_recent_updates(self, cursor: str | None) -> RecentUpdateFeed:
        raise NotImplementedError
