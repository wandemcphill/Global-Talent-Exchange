from __future__ import annotations

import pytest

from app.providers import FootballDataAdapter, MockFootballProvider, ProviderRegistry


def test_provider_registry_creates_known_providers() -> None:
    registry = ProviderRegistry()

    assert registry.list_provider_names() == ["football_data", "mock"]
    assert isinstance(registry.create("mock"), MockFootballProvider)
    assert isinstance(registry.create("football_data"), FootballDataAdapter)


def test_provider_registry_rejects_unknown_provider() -> None:
    registry = ProviderRegistry()

    with pytest.raises(KeyError):
        registry.create("unknown-provider")
