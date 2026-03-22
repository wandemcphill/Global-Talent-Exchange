from __future__ import annotations

from app.match_engine.schemas import ReplayEventLogEntryView
from app.match_engine.simulation.models import SimulationResult


class ReplayEventLogBuilder:
    def build(self, result: SimulationResult) -> list[ReplayEventLogEntryView]:
        return [
            ReplayEventLogEntryView(
                sequence=event.sequence,
                event_type=event.event_type,
                minute=event.minute,
                added_time=event.added_time,
                team_id=event.team_id,
                team_name=event.team_name,
                player_id=event.primary_player_id,
                related_player_id=event.secondary_player_id,
                home_score=event.home_score,
                away_score=event.away_score,
                payload=event.metadata,
            )
            for event in result.events
        ]
