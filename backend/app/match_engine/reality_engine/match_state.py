from __future__ import annotations

from dataclasses import dataclass

from app.match_engine.simulation.models import TeamRuntimeState


@dataclass(slots=True)
class MatchState:
    minute: int
    possession_side: str
    home: TeamRuntimeState
    away: TeamRuntimeState
    stage_pressure: float = 0.0
    rivalry_intensity: float = 0.0

    def team(self, side: str) -> TeamRuntimeState:
        return self.home if side == "home" else self.away

    def opponent(self, side: str) -> TeamRuntimeState:
        return self.away if side == "home" else self.home

    def attacking_team(self) -> TeamRuntimeState:
        return self.team(self.possession_side)

    def defending_team(self) -> TeamRuntimeState:
        return self.opponent(self.possession_side)

    def score_delta(self, side: str) -> int:
        team = self.team(side)
        opponent = self.opponent(side)
        return team.stats.goals - opponent.stats.goals
