from __future__ import annotations

import pytest

from app.regen_universe.expansion_service import (
    RegenUniverseExpansionService,
    RegenUniverseExpansionValidationError,
)
from app.regen_universe.service import RegenUniverseService


class _EmptyScalarResult:
    def __iter__(self):
        return iter(())

    def all(self):
        return []


class _EmptySession:
    def scalars(self, _statement):
        return _EmptyScalarResult()


def test_regen_universe_does_not_generate_fallback_prospects_in_protected_runtime(monkeypatch) -> None:
    monkeypatch.setenv("GTE_APP_ENV", "production")
    service = RegenUniverseService(_EmptySession())

    assert service._discovery_pool(limit=12, age_min=15, age_max=21) == []


def test_youth_tournament_squad_fill_ins_are_blocked_in_protected_runtime(monkeypatch) -> None:
    monkeypatch.setenv("GTE_APP_ENV", "production")
    service = RegenUniverseExpansionService(_EmptySession())

    with pytest.raises(RegenUniverseExpansionValidationError, match="persisted_squads"):
        service._select_tournament_squad([], team_key="strict-live")
