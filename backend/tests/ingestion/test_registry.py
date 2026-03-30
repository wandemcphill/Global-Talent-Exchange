from __future__ import annotations

import pytest

from app.providers import (
    ApiSportsAdapter,
    FootballDataAdapter,
    MockFootballProvider,
    ProviderRegistry,
    SportMonksAdapter,
)


def test_provider_registry_creates_known_providers() -> None:
    registry = ProviderRegistry()

    assert registry.list_provider_names() == ["api_sports", "football_data", "mock", "sportmonks"]
    assert isinstance(registry.create("api-sports"), ApiSportsAdapter)
    assert isinstance(registry.create("mock"), MockFootballProvider)
    assert isinstance(registry.create("football_data"), FootballDataAdapter)
    assert isinstance(registry.create("sport-monks"), SportMonksAdapter)


def test_provider_registry_rejects_unknown_provider() -> None:
    registry = ProviderRegistry()

    with pytest.raises(KeyError):
        registry.create("unknown-provider")
