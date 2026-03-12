from __future__ import annotations

from backend.app.config.competition_constants import (
    FINAL_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MIN_MINUTES,
)
from backend.app.match_engine.schemas import MatchEventTimelineView, MatchEventView, MatchPlayerReferenceView
from backend.app.match_engine.simulation.models import MatchEventType, SimulationResult


class MatchCommentaryTimelineGenerator:
    def build(self, result: SimulationResult) -> MatchEventTimelineView:
        presentation_duration_seconds = self._resolve_presentation_duration(result)
        presentation_seconds = self._resolve_presentation_seconds(result, presentation_duration_seconds)
        events = [
            MatchEventView(
                event_id=event.event_id,
                sequence=event.sequence,
                event_type=event.event_type,
                minute=event.minute,
                added_time=event.added_time,
                presentation_second=presentation_seconds[index],
                clock_label=self._clock_label(event.event_type, event.minute, event.added_time, event.metadata),
                team_id=event.team_id,
                team_name=event.team_name,
                primary_player=(
                    MatchPlayerReferenceView(player_id=event.primary_player_id, player_name=event.primary_player_name)
                    if event.primary_player_id is not None and event.primary_player_name is not None
                    else None
                ),
                secondary_player=(
                    MatchPlayerReferenceView(player_id=event.secondary_player_id, player_name=event.secondary_player_name)
                    if event.secondary_player_id is not None and event.secondary_player_name is not None
                    else None
                ),
                home_score=event.home_score,
                away_score=event.away_score,
                commentary=self._commentary_for_event(event, result),
                metadata=event.metadata,
            )
            for index, event in enumerate(result.events)
        ]
        return MatchEventTimelineView(
            match_id=result.match_id,
            status=result.status,
            presentation_duration_seconds=presentation_duration_seconds,
            events=events,
        )

    def _resolve_presentation_duration(self, result: SimulationResult) -> int:
        minimum = MATCH_PRESENTATION_MIN_MINUTES * 60
        standard_maximum = MATCH_PRESENTATION_MAX_MINUTES * 60
        final_maximum = FINAL_PRESENTATION_MAX_MINUTES * 60
        high_impact_events = sum(
            event.event_type
            in {
                MatchEventType.GOAL,
                MatchEventType.RED_CARD,
                MatchEventType.INJURY,
                MatchEventType.PENALTY_GOAL,
                MatchEventType.PENALTY_MISS,
            }
            for event in result.events
        )
        penalty_events = sum(event.event_type in {MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_MISS} for event in result.events)
        duration = minimum + (len(result.events) * 6) + (high_impact_events * 5) + (penalty_events * 3)
        maximum = final_maximum if result.is_final else standard_maximum
        if result.is_final and duration <= standard_maximum and len(result.events) >= 16:
            duration = standard_maximum + ((len(result.events) - 15) * 8)
        return max(minimum, min(maximum, duration))

    def _resolve_presentation_seconds(self, result: SimulationResult, duration: int) -> list[int]:
        events = list(result.events)
        if not events:
            return []
        if len(events) == 1:
            return [0]

        last_clock = max(event.minute + (event.added_time / 10.0) for event in events)
        minimum_gap = 5 if duration > MATCH_PRESENTATION_MAX_MINUTES * 60 else 6
        seconds = [0]
        for event in events[1:-1]:
            raw_second = round(((event.minute + (event.added_time / 10.0)) / max(1.0, last_clock)) * (duration - minimum_gap))
            seconds.append(max(raw_second, seconds[-1] + minimum_gap))
        seconds.append(duration)

        if seconds[-1] > duration:
            scale = duration / seconds[-1]
            rescaled = [0]
            for second in seconds[1:-1]:
                rescaled.append(max(round(second * scale), rescaled[-1] + 1))
            rescaled.append(duration)
            seconds = rescaled
        return seconds

    def _clock_label(
        self,
        event_type: MatchEventType,
        minute: int,
        added_time: int,
        metadata: dict[str, str | int | float | bool | None],
    ) -> str:
        if event_type in {MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_MISS}:
            return f"P{int(metadata['shootout_round'])}"
        if added_time:
            return f"{minute}+{added_time}'"
        return f"{minute}'"

    def _commentary_for_event(self, event, result: SimulationResult) -> str:
        if event.event_type is MatchEventType.KICKOFF:
            return f"{result.home_team_name} and {result.away_team_name} are underway."
        if event.event_type is MatchEventType.HALFTIME:
            return f"Halftime: {result.home_team_name} {event.home_score}-{event.away_score} {result.away_team_name}."
        if event.event_type is MatchEventType.FULLTIME:
            if event.metadata.get("goes_to_penalties"):
                return (
                    f"Fulltime: {result.home_team_name} {event.home_score}-{event.away_score} {result.away_team_name}. "
                    "No extra time here, this goes straight to penalties."
                )
            return f"Fulltime: {result.home_team_name} {event.home_score}-{event.away_score} {result.away_team_name}."
        if event.event_type is MatchEventType.MISSED_CHANCE:
            return f"{event.primary_player_name} wastes a big opening for {event.team_name}."
        if event.event_type is MatchEventType.SAVE:
            return f"{event.primary_player_name} keeps out {event.secondary_player_name} with a sharp stop."
        if event.event_type is MatchEventType.GOAL:
            if event.metadata.get("assisted") and event.secondary_player_name is not None:
                return f"Goal for {event.team_name}. {event.primary_player_name} finishes after a setup from {event.secondary_player_name}."
            return f"Goal for {event.team_name}. {event.primary_player_name} finds the net."
        if event.event_type is MatchEventType.YELLOW_CARD:
            return f"{event.primary_player_name} goes into the book for {event.team_name}."
        if event.event_type is MatchEventType.RED_CARD:
            return f"{event.primary_player_name} is sent off. {event.team_name} drop into {event.metadata.get('fallback_formation')}."
        if event.event_type is MatchEventType.INJURY:
            return f"{event.primary_player_name} pulls up injured for {event.team_name}."
        if event.event_type is MatchEventType.SUBSTITUTION:
            return f"{event.primary_player_name} replaces {event.secondary_player_name} for {event.team_name}."
        if event.event_type is MatchEventType.PENALTY_GOAL:
            return f"{event.primary_player_name} scores in the shootout for {event.team_name}."
        if event.event_type is MatchEventType.PENALTY_MISS:
            if event.secondary_player_name is not None:
                return f"{event.primary_player_name} is denied in the shootout by {event.secondary_player_name}."
            return f"{event.primary_player_name} misses in the shootout for {event.team_name}."
        return f"{event.team_name or 'Match'} event."
