"""Pure-python unit test for SyntheticSquadFactory._resolve_lineup fallback.

The review request says 'TeamFactory' but the actual class is SyntheticSquadFactory
(/app/gtex/backend/app/match_engine/services/team_factory.py).
"""
import os
import sys
from dataclasses import dataclass, field

# Point to gtex backend
GTEX_BACKEND = "/app/gtex/backend"
if GTEX_BACKEND not in sys.path:
    sys.path.insert(0, GTEX_BACKEND)

import pytest


@dataclass
class _StubSeasonStat:
    average_rating: float | None = 7.0
    goals: int = 0
    assists: int = 0


@dataclass
class _StubPlayer:
    id: str
    full_name: str
    position: str
    normalized_position: str | None = None
    market_value_eur: float = 1_000_000.0
    season_stats: list = field(default_factory=lambda: [_StubSeasonStat(7.0)])


def _make_players(positions: list[str]) -> list[_StubPlayer]:
    return [
        _StubPlayer(id=f"p{i}", full_name=f"Player {i}", position=pos, normalized_position=pos)
        for i, pos in enumerate(positions)
    ]


def _factory():
    from app.match_engine.services.team_factory import SyntheticSquadFactory
    return SyntheticSquadFactory()


def test_resolve_lineup_falls_back_to_ai_coach_no_gk():
    """11 forwards -> no formation satisfies role-fit; must fallback to _ai_coach_auto_draft."""
    factory = _factory()
    players = _make_players(["ST"] * 11)
    starters, bench, formation = factory._resolve_lineup(None, "team-x", players, None)
    assert len(starters) == 11
    assert len(bench) == 0  # exactly 11 eligible, nothing left over
    assert isinstance(formation, str) and "-" in formation


def test_resolve_lineup_falls_back_with_bench_up_to_7():
    factory = _factory()
    # 18 forwards -> fallback picks 11 starters, 7 on bench
    players = _make_players(["ST"] * 18)
    starters, bench, _ = factory._resolve_lineup(None, "team-x", players, None)
    assert len(starters) == 11
    assert len(bench) == 7


def test_resolve_lineup_raises_when_fewer_than_11():
    factory = _factory()
    players = _make_players(["ST"] * 10)
    from app.services.player_lifecycle_service import PlayerLifecycleValidationError
    with pytest.raises(PlayerLifecycleValidationError):
        factory._resolve_lineup(None, "team-x", players, None)


def test_resolve_lineup_normal_mixed_squad_does_not_crash():
    factory = _factory()
    positions = (
        ["GK"]
        + ["CB", "LB", "RB", "CB"]
        + ["CM", "CM", "CM"]
        + ["ST", "LW", "RW"]
        + ["CB", "CM", "ST"]
    )
    players = _make_players(positions)
    starters, bench, formation = factory._resolve_lineup(None, "team-x", players, None)
    assert len(starters) == 11
    assert len(bench) <= 7
    assert formation
