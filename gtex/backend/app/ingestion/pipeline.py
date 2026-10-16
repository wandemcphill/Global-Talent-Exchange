from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .adapters import IngestionAdapterRegistry
from .models import NormalizedMatchEvent, PlayerEventWindow


@dataclass(slots=True)
class NormalizedMatchEventPipeline:
    adapter_registry: IngestionAdapterRegistry = field(default_factory=IngestionAdapterRegistry.default)

    def process(self, payloads: Iterable[Mapping[str, object]]) -> list[NormalizedMatchEvent]:
        normalized: list[NormalizedMatchEvent] = []
        for payload in payloads:
            adapter = self.adapter_registry.resolve(payload)
            normalized.extend(adapter.normalize(payload))
        deduped = {event.dedupe_key: event for event in normalized}
        return sorted(deduped.values(), key=lambda event: (event.occurred_at, event.player_id, event.match_id))

    def build_player_windows(self, events: Iterable[NormalizedMatchEvent]) -> dict[str, PlayerEventWindow]:
        grouped: dict[str, list[NormalizedMatchEvent]] = {}
        for event in events:
            grouped.setdefault(event.player_id, []).append(event)

        windows: dict[str, PlayerEventWindow] = {}
        for player_id, player_events in grouped.items():
            total_minutes = sum(event.minutes for event in player_events)
            total_goals = sum(event.goals for event in player_events)
            total_assists = sum(event.assists for event in player_events)
            average_rating = (
                sum(event.rating for event in player_events) / len(player_events) if player_events else 0.0
            )
            windows[player_id] = PlayerEventWindow(
                player_id=player_id,
                player_name=player_events[0].player_name if player_events else "",
                events=tuple(sorted(player_events, key=lambda event: event.occurred_at)),
                total_minutes=total_minutes,
                total_goals=total_goals,
                total_assists=total_assists,
                average_rating=average_rating,
                big_moment_count=sum(1 for event in player_events if event.big_moment),
            )
        return windows
