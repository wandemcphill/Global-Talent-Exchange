from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from .api_sports_adapter import ApiSportsAdapter
from .base import BaseFootballProvider
from .football_data_adapter import FootballDataAdapter
from .mock_provider import MockFootballProvider
from .sportmonks_adapter import SportMonksAdapter

if TYPE_CHECKING:
    from app.core.config import Settings


ProviderFactory = Callable[..., BaseFootballProvider]


@dataclass(slots=True)
class ProviderRegistry:
    factories: dict[str, ProviderFactory] = field(
        default_factory=lambda: {
            "api_sports": ApiSportsAdapter,
            "mock": MockFootballProvider,
            "football_data": FootballDataAdapter,
            "sportmonks": SportMonksAdapter,
        }
    )

    def create(self, provider_name: str, *, settings: Settings | None = None) -> BaseFootballProvider:
        normalized_provider_name = self._normalize_provider_name(provider_name)
        try:
            factory = self.factories[normalized_provider_name]
        except KeyError as exc:
            available = ", ".join(sorted(self.factories))
            raise KeyError(
                f"Unknown ingestion provider '{provider_name}'. Available: {available}."
            ) from exc
        try:
            return factory(settings=settings)
        except TypeError:
            return factory()

    def register(self, provider_name: str, factory: ProviderFactory) -> None:
        self.factories[self._normalize_provider_name(provider_name)] = factory

    def list_provider_names(self) -> list[str]:
        return sorted(self.factories)

    def _normalize_provider_name(self, provider_name: str) -> str:
        normalized = provider_name.strip().lower().replace("-", "_")
        if normalized == "sport_monks":
            return "sportmonks"
        return normalized
