from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from .base import BaseFootballProvider
from .football_data_adapter import FootballDataAdapter
from .mock_provider import MockFootballProvider

if TYPE_CHECKING:
    from app.core.config import Settings


ProviderFactory = Callable[..., BaseFootballProvider]


@dataclass(slots=True)
class ProviderRegistry:
    factories: dict[str, ProviderFactory] = field(
        default_factory=lambda: {
            "mock": MockFootballProvider,
            "football_data": FootballDataAdapter,
        }
    )

    def create(self, provider_name: str, *, settings: Settings | None = None) -> BaseFootballProvider:
        try:
            factory = self.factories[provider_name]
        except KeyError as exc:
            available = ", ".join(sorted(self.factories))
            raise KeyError(f"Unknown ingestion provider '{provider_name}'. Available: {available}.") from exc
        try:
            return factory(settings=settings)
        except TypeError:
            return factory()

    def register(self, provider_name: str, factory: ProviderFactory) -> None:
        self.factories[provider_name] = factory

    def list_provider_names(self) -> list[str]:
        return sorted(self.factories)
