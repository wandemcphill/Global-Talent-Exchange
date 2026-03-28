from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.services.team_factory import SyntheticSquadFactory

if TYPE_CHECKING:
    from app.match_engine.services.execution_runtime import (
        LeagueFixtureExecutionService,
        LocalMatchExecutionWorker,
        ensure_local_match_execution_runtime,
    )


def __getattr__(name: str) -> Any:
    if name in {
        "LeagueFixtureExecutionService",
        "LocalMatchExecutionWorker",
        "ensure_local_match_execution_runtime",
    }:
        from app.match_engine.services.execution_runtime import (
            LeagueFixtureExecutionService,
            LocalMatchExecutionWorker,
            ensure_local_match_execution_runtime,
        )

        exported = {
            "LeagueFixtureExecutionService": LeagueFixtureExecutionService,
            "LocalMatchExecutionWorker": LocalMatchExecutionWorker,
            "ensure_local_match_execution_runtime": ensure_local_match_execution_runtime,
        }
        return exported[name]
    raise AttributeError(name)


__all__ = [
    "LeagueFixtureExecutionService",
    "LocalMatchExecutionWorker",
    "MatchSimulationService",
    "SyntheticSquadFactory",
    "ensure_local_match_execution_runtime",
]
