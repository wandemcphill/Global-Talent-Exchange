from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.common.enums.match_status import MatchStatus
from app.match_engine.schemas import MatchEventView, MatchReplayPayloadView, ReplayEventLogEntryView
from app.match_engine.simulation.models import MatchEventType as EngineMatchEventType
from app.matches.lifecycle import (
    MatchStateTransitionError,
    assert_transition,
    is_terminal,
)
from app.models.competition_match import CompetitionMatch
from app.models.match_event import MatchEvent, MatchEventTeam, MatchEventType
from app.orchestrator.orchestrator_service import OrchestratorService

from .schemas import (
    MatchCommandAcceptedView,
    MatchCompleteRequest,
    MatchAnalysisView,
    MatchKeyMomentView,
    MatchStartRequest,
    MatchMomentumShiftView,
    MatchReplayEventView,
    MatchReplayStatsView,
    MatchReplaySummaryView,
    MatchReplayTeamStatsView,
    MatchReplayView,
)


#: Replay log entries carry the *match engine* event vocabulary
#: (``app.match_engine.simulation.models.MatchEventType``), not the persisted
#: ``app.models.match_event.MatchEventType`` used by the event log tables. Comparing an
#: entry against the persisted enum raised ``AttributeError`` for penalty/red-card
#: members that only exist on the engine enum.
_HIGHLIGHT_ELIGIBLE_ENGINE_EVENTS: frozenset[EngineMatchEventType] = frozenset(
    {
        EngineMatchEventType.GOAL,
        EngineMatchEventType.PENALTY_GOAL,
        EngineMatchEventType.PENALTY_SCORED,
        EngineMatchEventType.RED_CARD,
    }
)


class MatchReplayNotFoundError(LookupError):
    pass


class MatchCommandError(ValueError):
    pass


class MatchCommandNotFoundError(MatchCommandError):
    pass


class MatchCommandStateError(MatchCommandError):
    """Raised when a lifecycle command is illegal for the match's current state."""

    def __init__(self, message: str, *, match_id: str, current_status: str | None) -> None:
        super().__init__(message)
        self.match_id = match_id
        self.current_status = current_status


@dataclass(slots=True)
class LoggedMatchInsights:
    replay: MatchReplayView
    home_analysis: MatchAnalysisView
    away_analysis: MatchAnalysisView


@dataclass(slots=True)
class ReplayService:
    session: Session

    def get_match_replay(self, match_id: str) -> MatchReplayView:
        events = self._events(match_id)
        if not events:
            raise MatchReplayNotFoundError(match_id)
        return MatchReplayView(
            match_id=match_id,
            timeline=[self._event_view(item) for item in events],
            summary=self.generate_summary(events),
        )

    def generate_summary(self, events: Iterable[MatchEvent]) -> MatchReplaySummaryView:
        materialized = list(events)
        tallies = self._stat_tallies(materialized)
        stats = MatchReplayStatsView(
            home=self._team_stats_view(tallies[MatchEventTeam.HOME], tallies[MatchEventTeam.AWAY]),
            away=self._team_stats_view(tallies[MatchEventTeam.AWAY], tallies[MatchEventTeam.HOME]),
        )
        return MatchReplaySummaryView(
            stats=stats,
            key_moments=self._key_moments(materialized),
            momentum_shifts=self._momentum_shifts(materialized),
        )

    def _events(self, match_id: str) -> list[MatchEvent]:
        return list(
            self.session.scalars(
                select(MatchEvent)
                .where(MatchEvent.match_id == match_id)
                .order_by(
                    MatchEvent.minute.asc(),
                    MatchEvent.created_at.asc(),
                    MatchEvent.sequence.asc(),
                    MatchEvent.id.asc(),
                )
            ).all()
        )

    def _event_view(self, event: MatchEvent) -> MatchReplayEventView:
        metadata = dict(event.metadata_json or {})
        return MatchReplayEventView(
            id=event.id,
            match_id=event.match_id,
            sequence=event.sequence,
            minute=event.minute,
            type=event.event_type,
            team=event.team,
            player_id=event.player_id,
            player_name=self._metadata_text(metadata, "player_name"),
            team_name=self._metadata_text(metadata, "team_name"),
            metadata=metadata,
            created_at=event.created_at,
        )

    def _stat_tallies(self, events: list[MatchEvent]) -> dict[MatchEventTeam, dict[str, Any]]:
        tallies: dict[MatchEventTeam, dict[str, Any]] = {
            MatchEventTeam.HOME: self._blank_tally(),
            MatchEventTeam.AWAY: self._blank_tally(),
        }
        for event in events:
            bucket = tallies[event.team]
            metadata = dict(event.metadata_json or {})
            if event.event_type is MatchEventType.GOAL:
                bucket["goals"] += 1
            elif event.event_type is MatchEventType.SHOT:
                bucket["total_shots"] += 1
                if bool(metadata.get("on_target")):
                    bucket["shots_on_target"] += 1
                if bool(metadata.get("big_chance")):
                    bucket["big_chances"] += 1
            elif event.event_type is MatchEventType.CHANCE_CREATED:
                if bool(metadata.get("big_chance")):
                    bucket["big_chances"] += 1
            elif event.event_type is MatchEventType.PASS:
                bucket["passes"] += 1
                if bool(metadata.get("completed", True)):
                    bucket["completed_passes"] += 1
            elif event.event_type is MatchEventType.FOUL:
                bucket["fouls"] += 1
            elif event.event_type is MatchEventType.CARD:
                if str(metadata.get("card_type", "yellow")).lower() == "red":
                    bucket["red_cards"] += 1
                else:
                    bucket["yellow_cards"] += 1
            elif event.event_type is MatchEventType.SUBSTITUTION:
                bucket["substitutions"] += 1
            elif event.event_type is MatchEventType.TACKLE:
                if str(metadata.get("outcome", "")).lower() in {"won", "attack_stopped"}:
                    bucket["won_tackles"] += 1
                bucket["control_score"] += 0.8

            bucket["control_score"] += self._control_weight(event, metadata)
        return tallies

    @staticmethod
    def _blank_tally() -> dict[str, Any]:
        return {
            "goals": 0,
            "total_shots": 0,
            "shots_on_target": 0,
            "big_chances": 0,
            "passes": 0,
            "completed_passes": 0,
            "fouls": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "substitutions": 0,
            "won_tackles": 0,
            "control_score": 1.0,
        }

    @staticmethod
    def _control_weight(event: MatchEvent, metadata: dict[str, Any]) -> float:
        if event.event_type is MatchEventType.PASS:
            return 1.6 if bool(metadata.get("completed", True)) else 0.5
        if event.event_type is MatchEventType.CHANCE_CREATED:
            return 3.2 if bool(metadata.get("big_chance")) else 2.4
        if event.event_type is MatchEventType.SHOT:
            return 1.8 if bool(metadata.get("on_target")) else 1.1
        if event.event_type is MatchEventType.GOAL:
            return 4.6
        if event.event_type is MatchEventType.FORMATION_CHANGE:
            return 0.9
        if event.event_type is MatchEventType.SUBSTITUTION:
            return 0.7
        return 0.2

    def _team_stats_view(self, bucket: dict[str, Any], opponent_bucket: dict[str, Any]) -> MatchReplayTeamStatsView:
        pass_accuracy = 0.0
        if bucket["passes"]:
            pass_accuracy = float(
                (Decimal(bucket["completed_passes"]) * Decimal("100") / Decimal(bucket["passes"]))
                .quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            )
        total_control = float(bucket["control_score"] + opponent_bucket["control_score"])
        possession = 50 if total_control <= 0 else round((float(bucket["control_score"]) / total_control) * 100)
        possession = max(0, min(100, possession))
        return MatchReplayTeamStatsView(
            goals=int(bucket["goals"]),
            possession_estimate=possession,
            total_shots=int(bucket["total_shots"]),
            shots_on_target=int(bucket["shots_on_target"]),
            big_chances=int(bucket["big_chances"]),
            pass_accuracy=pass_accuracy,
            fouls=int(bucket["fouls"]),
            yellow_cards=int(bucket["yellow_cards"]),
            red_cards=int(bucket["red_cards"]),
            substitutions=int(bucket["substitutions"]),
        )

    def _key_moments(self, events: list[MatchEvent]) -> list[MatchKeyMomentView]:
        candidates = []
        for event in events:
            metadata = dict(event.metadata_json or {})
            importance = int(metadata.get("importance", self._default_importance(event, metadata)))
            if importance < 2:
                continue
            candidates.append(
                (
                    -importance,
                    event.minute,
                    event.sequence,
                    MatchKeyMomentView(
                        minute=event.minute,
                        type=event.event_type,
                        team=event.team,
                        headline=self._headline(event, metadata),
                    ),
                )
            )
        candidates.sort(key=lambda item: item[:3])
        return [item[3] for item in candidates[:10]]

    def _momentum_shifts(self, events: list[MatchEvent]) -> list[MatchMomentumShiftView]:
        shifts: list[MatchMomentumShiftView] = []
        running = {MatchEventTeam.HOME: 0.0, MatchEventTeam.AWAY: 0.0}
        current_leader: MatchEventTeam | None = None
        for event in events:
            metadata = dict(event.metadata_json or {})
            running[event.team] += self._momentum_weight(event, metadata)
            opponent = MatchEventTeam.AWAY if event.team is MatchEventTeam.HOME else MatchEventTeam.HOME
            running[opponent] = max(0.0, running[opponent] - (self._momentum_weight(event, metadata) * 0.35))
            new_leader = (
                MatchEventTeam.HOME
                if running[MatchEventTeam.HOME] > running[MatchEventTeam.AWAY]
                else MatchEventTeam.AWAY
            )
            if new_leader is current_leader:
                continue
            if abs(running[MatchEventTeam.HOME] - running[MatchEventTeam.AWAY]) < 2.5:
                continue
            current_leader = new_leader
            shifts.append(
                MatchMomentumShiftView(
                    minute=event.minute,
                    team=new_leader,
                    reason=self._headline(event, metadata),
                )
            )
        return shifts[:8]

    @staticmethod
    def _momentum_weight(event: MatchEvent, metadata: dict[str, Any]) -> float:
        if event.event_type is MatchEventType.GOAL:
            return 5.0
        if event.event_type is MatchEventType.CARD and str(metadata.get("card_type", "")).lower() == "red":
            return 3.8
        if event.event_type is MatchEventType.CHANCE_CREATED:
            return 2.2 if bool(metadata.get("big_chance")) else 1.4
        if event.event_type is MatchEventType.SHOT and bool(metadata.get("on_target")):
            return 1.6
        if event.event_type is MatchEventType.FORMATION_CHANGE:
            return 1.0
        if event.event_type is MatchEventType.SUBSTITUTION:
            return 0.8
        return 0.5

    def _headline(self, event: MatchEvent, metadata: dict[str, Any]) -> str:
        team_name = self._metadata_text(metadata, "team_name") or event.team.value.title()
        player_name = self._metadata_text(metadata, "player_name")
        label = {
            MatchEventType.GOAL: "Goal",
            MatchEventType.SHOT: "Shot",
            MatchEventType.PASS: "Key pass",
            MatchEventType.TACKLE: "Tackle",
            MatchEventType.FOUL: "Foul",
            MatchEventType.CARD: "Card",
            MatchEventType.SUBSTITUTION: "Substitution",
            MatchEventType.FORMATION_CHANGE: "Formation change",
            MatchEventType.CHANCE_CREATED: "Chance created",
        }[event.event_type]
        if player_name:
            return f"{label}: {player_name} ({team_name})"
        return f"{label}: {team_name}"

    @staticmethod
    def _default_importance(event: MatchEvent, metadata: dict[str, Any]) -> int:
        if event.event_type is MatchEventType.GOAL:
            return 5
        if event.event_type is MatchEventType.CARD and str(metadata.get("card_type", "")).lower() == "red":
            return 4
        if event.event_type in {MatchEventType.CHANCE_CREATED, MatchEventType.FORMATION_CHANGE}:
            return 3
        if event.event_type is MatchEventType.SUBSTITUTION:
            return 2
        return 1

    @staticmethod
    def _metadata_text(metadata: dict[str, Any], key: str) -> str | None:
        value = metadata.get(key)
        return str(value) if isinstance(value, str) and value.strip() else None


@dataclass(slots=True)
class AnalysisService:
    session: Session
    replay_service: ReplayService | None = None

    def analyze_match(self, match_id: str, team: MatchEventTeam) -> MatchAnalysisView:
        replay_service = self.replay_service or ReplayService(self.session)
        replay = replay_service.get_match_replay(match_id)
        timeline = replay.timeline
        team_stats = replay.summary.stats.home if team is MatchEventTeam.HOME else replay.summary.stats.away
        opponent_stats = replay.summary.stats.away if team is MatchEventTeam.HOME else replay.summary.stats.home
        opponent = MatchEventTeam.AWAY if team is MatchEventTeam.HOME else MatchEventTeam.HOME
        substitutions = sum(1 for event in timeline if event.team is team and event.type is MatchEventType.SUBSTITUTION)
        late_goals_conceded = any(
            event.team is opponent and event.type is MatchEventType.GOAL and event.minute >= 75
            for event in timeline
        )
        late_chances_conceded = sum(
            1
            for event in timeline
            if event.team is opponent
            and event.minute >= 70
            and event.type in {MatchEventType.CHANCE_CREATED, MatchEventType.SHOT}
        )

        problems: list[str] = []
        if team_stats.total_shots <= 4 or team_stats.big_chances == 0:
            problems.append("Low attacking output")
        if opponent_stats.big_chances >= 3 or opponent_stats.shots_on_target >= 5:
            problems.append("Defensive structure weak")
        if late_chances_conceded >= 3:
            problems.append("Fitness issues affected performance")
        if substitutions == 0 and team_stats.goals < opponent_stats.goals:
            problems.append("No tactical adjustments made")
        if late_goals_conceded:
            problems.append("Late-game concentration drop")
        return MatchAnalysisView(
            match_id=match_id,
            team=team,
            problems=problems,
            suggestions=self.generate_suggestions(problems),
        )

    @staticmethod
    def generate_suggestions(problems: list[str]) -> list[str]:
        mapping = {
            "Low attacking output": "Switch to an attacking formation and increase chance creation through central zones.",
            "Defensive structure weak": "Lower the defensive line and tighten the team shape out of possession.",
            "Fitness issues affected performance": "Adjust training intensity and rotate earlier to protect late-game energy.",
            "No tactical adjustments made": "Use substitutions or a formation tweak earlier when the game state turns against you.",
            "Late-game concentration drop": "Add late-game game-management instructions and protect the central defensive lane.",
        }
        seen: set[str] = set()
        suggestions: list[str] = []
        for problem in problems:
            suggestion = mapping.get(problem)
            if suggestion is None or suggestion in seen:
                continue
            seen.add(suggestion)
            suggestions.append(suggestion)
        return suggestions


@dataclass(slots=True)
class MatchEventLoggerService:
    session: Session

    def persist_official_match(self, *, match_id: str, replay_payload: MatchReplayPayloadView) -> LoggedMatchInsights:
        self.session.execute(delete(MatchEvent).where(MatchEvent.match_id == match_id))
        rows = self._build_rows(match_id=match_id, replay_payload=replay_payload)
        self.session.add_all(rows)
        self.session.flush()
        replay_service = ReplayService(self.session)
        analysis_service = AnalysisService(self.session, replay_service=replay_service)
        return LoggedMatchInsights(
            replay=replay_service.get_match_replay(match_id),
            home_analysis=analysis_service.analyze_match(match_id, MatchEventTeam.HOME),
            away_analysis=analysis_service.analyze_match(match_id, MatchEventTeam.AWAY),
        )

    def _build_rows(self, *, match_id: str, replay_payload: MatchReplayPayloadView) -> list[MatchEvent]:
        rows: list[MatchEvent] = []
        pending_shots: dict[tuple[MatchEventTeam, str | None, int], MatchEvent] = {}
        timeline_events = {item.sequence: item for item in replay_payload.timeline.events}
        sequence = 1
        for item in replay_payload.replay_log:
            timeline_event = timeline_events.get(item.sequence)
            team = self._team_for_source(item, replay_payload)
            if team is None:
                continue
            if item.event_type.name == "DANGEROUS_ATTACK":
                rows.append(
                    self._row(
                        match_id,
                        sequence,
                        item,
                        team,
                        MatchEventType.CHANCE_CREATED,
                        self._chance_metadata(item),
                        replay_payload=replay_payload,
                        timeline_event=timeline_event,
                    )
                )
                sequence += 1
                pass_row = self._derived_pass_row(
                    match_id,
                    sequence,
                    item,
                    team,
                    replay_payload=replay_payload,
                    timeline_event=timeline_event,
                )
                if pass_row is not None:
                    rows.append(pass_row)
                    sequence += 1
                continue
            if item.event_type.name == "SHOT":
                shot_row = self._row(
                    match_id,
                    sequence,
                    item,
                    team,
                    MatchEventType.SHOT,
                    self._shot_metadata(item),
                    replay_payload=replay_payload,
                    timeline_event=timeline_event,
                )
                pending_shots[(team, item.player_id, item.minute)] = shot_row
                rows.append(shot_row)
                sequence += 1
                continue
            if item.event_type.name == "SHOT_ON_TARGET":
                self._update_pending_shot(pending_shots, team=team, player_id=item.player_id, minute=item.minute, on_target=True)
                continue
            if item.event_type.name in {"GOALKEEPER_SAVE", "DOUBLE_SAVE"}:
                self._update_pending_shot(
                    pending_shots,
                    team=self._opponent(team),
                    player_id=item.related_player_id,
                    minute=item.minute,
                    on_target=True,
                    outcome="saved",
                )
                continue
            if item.event_type.name in {"MISSED_CHANCE", "MISSED_BIG_CHANCE", "WOODWORK"}:
                self._update_pending_shot(
                    pending_shots,
                    team=team,
                    player_id=item.player_id,
                    minute=item.minute,
                    on_target=False,
                    outcome="woodwork" if item.event_type.name == "WOODWORK" else "missed",
                    big_chance=item.event_type.name == "MISSED_BIG_CHANCE",
                )
                continue
            if item.event_type.name in {"GOAL", "PENALTY_SCORED", "PENALTY_GOAL"}:
                self._update_pending_shot(
                    pending_shots,
                    team=team,
                    player_id=item.player_id,
                    minute=item.minute,
                    on_target=True,
                    outcome="goal",
                    big_chance=bool((item.payload or {}).get("chance_quality", 0) >= 0.48),
                )
                rows.append(
                    self._row(
                        match_id,
                        sequence,
                        item,
                        team,
                        MatchEventType.GOAL,
                        self._goal_metadata(item),
                        replay_payload=replay_payload,
                        timeline_event=timeline_event,
                    )
                )
                sequence += 1
                if item.event_type.name != "GOAL":
                    rows.append(
                        self._row(
                            match_id,
                            sequence,
                            item,
                            team,
                            MatchEventType.SHOT,
                            self._penalty_shot_metadata(item),
                            replay_payload=replay_payload,
                            timeline_event=timeline_event,
                        )
                    )
                    sequence += 1
                continue
            if item.event_type.name in {"PENALTY_MISSED", "PENALTY_MISS"}:
                rows.append(
                    self._row(
                        match_id,
                        sequence,
                        item,
                        team,
                        MatchEventType.SHOT,
                        self._penalty_shot_metadata(item),
                        replay_payload=replay_payload,
                        timeline_event=timeline_event,
                    )
                )
                sequence += 1
                continue
            if item.event_type.name in {"FOUL", "TACTICAL_FOUL", "PENALTY_AWARDED"}:
                foul_team = self._opponent(team) if item.event_type.name == "PENALTY_AWARDED" else team
                foul_player_id = None if item.event_type.name == "PENALTY_AWARDED" else item.player_id
                rows.append(
                    self._row(
                        match_id,
                        sequence,
                        item,
                        foul_team,
                        MatchEventType.FOUL,
                        self._foul_metadata(item),
                        replay_payload=replay_payload,
                        timeline_event=timeline_event,
                        player_id=foul_player_id,
                    )
                )
                sequence += 1
                tackle_row = self._derived_tackle_row(
                    match_id,
                    sequence,
                    item,
                    foul_team,
                    replay_payload=replay_payload,
                    timeline_event=timeline_event,
                )
                if tackle_row is not None:
                    rows.append(tackle_row)
                    sequence += 1
                continue
            if item.event_type.name in {"YELLOW_CARD", "RED_CARD"}:
                rows.append(
                    self._row(
                        match_id,
                        sequence,
                        item,
                        team,
                        MatchEventType.CARD,
                        self._card_metadata(item),
                        replay_payload=replay_payload,
                        timeline_event=timeline_event,
                    )
                )
                sequence += 1
                continue
            if item.event_type.name == "SUBSTITUTION":
                rows.append(
                    self._row(
                        match_id,
                        sequence,
                        item,
                        team,
                        MatchEventType.SUBSTITUTION,
                        self._substitution_metadata(item),
                        replay_payload=replay_payload,
                        timeline_event=timeline_event,
                    )
                )
                sequence += 1
                continue
            if item.event_type.name == "TACTICAL_CHANGE":
                metadata = self._formation_change_metadata(item)
                if metadata is None:
                    continue
                rows.append(
                    self._row(
                        match_id,
                        sequence,
                        item,
                        team,
                        MatchEventType.FORMATION_CHANGE,
                        metadata,
                        replay_payload=replay_payload,
                        timeline_event=timeline_event,
                    )
                )
                sequence += 1
                continue
            if item.event_type.name == "OFFSIDE":
                tackle_row = self._derived_tackle_row(
                    match_id,
                    sequence,
                    item,
                    self._opponent(team),
                    replay_payload=replay_payload,
                    timeline_event=timeline_event,
                )
                if tackle_row is not None:
                    rows.append(tackle_row)
                    sequence += 1
        return rows

    def _row(
        self,
        match_id: str,
        sequence: int,
        item: ReplayEventLogEntryView,
        team: MatchEventTeam,
        event_type: MatchEventType,
        metadata: dict[str, Any],
        *,
        replay_payload: MatchReplayPayloadView,
        timeline_event: MatchEventView | None = None,
        player_id: str | None = None,
    ) -> MatchEvent:
        payload = dict(item.payload or {})
        team_id, team_name = self._team_identity(team, replay_payload)
        return MatchEvent(
            match_id=match_id,
            sequence=sequence,
            minute=item.minute,
            event_type=event_type,
            team=team,
            player_id=player_id if player_id is not None else item.player_id,
            metadata_json={
                "team_id": team_id,
                "team_name": team_name,
                "player_name": payload.get("player_name"),
                "related_player_id": item.related_player_id,
                "related_player_name": payload.get("related_player_name"),
                "home_score": item.home_score,
                "away_score": item.away_score,
                "source_sequence": item.sequence,
                "source_event_type": item.event_type.value,
                **self._viewer_metadata(item, timeline_event=timeline_event),
                **metadata,
            },
        )

    def _team_for_source(self, item: ReplayEventLogEntryView, replay_payload: MatchReplayPayloadView) -> MatchEventTeam | None:
        if item.team_id == replay_payload.summary.home_stats.team_id:
            return MatchEventTeam.HOME
        if item.team_id == replay_payload.summary.away_stats.team_id:
            return MatchEventTeam.AWAY
        return None

    @staticmethod
    def _opponent(team: MatchEventTeam) -> MatchEventTeam:
        return MatchEventTeam.AWAY if team is MatchEventTeam.HOME else MatchEventTeam.HOME

    @staticmethod
    def _team_identity(team: MatchEventTeam, replay_payload: MatchReplayPayloadView) -> tuple[str, str]:
        if team is MatchEventTeam.HOME:
            return replay_payload.summary.home_stats.team_id, replay_payload.summary.home_stats.team_name
        return replay_payload.summary.away_stats.team_id, replay_payload.summary.away_stats.team_name

    @staticmethod
    def _chance_metadata(item: ReplayEventLogEntryView) -> dict[str, Any]:
        payload = dict(item.payload or {})
        quality = float(payload.get("chance_quality") or payload.get("xg") or 0.0)
        return {
            "importance": int(payload.get("importance", 3)),
            "big_chance": quality >= 0.48,
            "chance_quality": round(quality, 2),
            "creator_player_id": payload.get("creator_player_id"),
            "creator_player_name": payload.get("creator_player_name"),
            "build_up_pattern": payload.get("build_up_pattern"),
        }

    @staticmethod
    def _shot_metadata(item: ReplayEventLogEntryView) -> dict[str, Any]:
        payload = dict(item.payload or {})
        quality = float(payload.get("chance_quality") or payload.get("xg") or 0.0)
        return {
            "importance": int(payload.get("importance", 2)),
            "on_target": False,
            "outcome": "pending",
            "big_chance": quality >= 0.48,
            "xg": round(quality, 2),
        }

    @staticmethod
    def _goal_metadata(item: ReplayEventLogEntryView) -> dict[str, Any]:
        payload = dict(item.payload or {})
        return {
            "importance": 5,
            "penalty": bool(payload.get("penalty", item.event_type.name.startswith("PENALTY"))),
            "assisted": bool(payload.get("assisted") or item.related_player_id is not None),
            "xg": round(float(payload.get("xg") or payload.get("chance_quality") or 0.0), 2),
            "player_name": payload.get("player_name"),
        }

    @staticmethod
    def _penalty_shot_metadata(item: ReplayEventLogEntryView) -> dict[str, Any]:
        payload = dict(item.payload or {})
        outcome = "goal" if item.event_type.name in {"PENALTY_SCORED", "PENALTY_GOAL"} else "missed"
        on_target = outcome == "goal" or str(payload.get("miss_variant", "")).lower() == "save"
        return {
            "importance": int(payload.get("importance", 4)),
            "on_target": on_target,
            "outcome": outcome,
            "big_chance": True,
            "penalty": True,
            "xg": round(float(payload.get("xg") or 0.76), 2),
        }

    @staticmethod
    def _foul_metadata(item: ReplayEventLogEntryView) -> dict[str, Any]:
        payload = dict(item.payload or {})
        return {
            "importance": int(payload.get("importance", 2)),
            "foul_type": "penalty" if item.event_type.name == "PENALTY_AWARDED" else "open_play",
        }

    @staticmethod
    def _card_metadata(item: ReplayEventLogEntryView) -> dict[str, Any]:
        return {
            "importance": 4 if item.event_type.name == "RED_CARD" else 3,
            "card_type": "red" if item.event_type.name == "RED_CARD" else "yellow",
        }

    @staticmethod
    def _substitution_metadata(item: ReplayEventLogEntryView) -> dict[str, Any]:
        payload = dict(item.payload or {})
        return {
            "importance": int(payload.get("importance", 2)),
            "incoming_player_id": item.player_id,
            "incoming_player_name": payload.get("player_name"),
            "outgoing_player_id": item.related_player_id,
            "outgoing_player_name": payload.get("related_player_name"),
            "reason": payload.get("reason"),
        }

    @staticmethod
    def _formation_change_metadata(item: ReplayEventLogEntryView) -> dict[str, Any] | None:
        payload = dict(item.payload or {})
        adjustments = payload.get("adjustments")
        if not isinstance(adjustments, dict) or not adjustments.get("formation"):
            return None
        return {
            "importance": int(payload.get("importance", 3)),
            "formation": adjustments["formation"],
            "adjustments": adjustments,
        }

    def _derived_pass_row(
        self,
        match_id: str,
        sequence: int,
        item: ReplayEventLogEntryView,
        team: MatchEventTeam,
        *,
        replay_payload: MatchReplayPayloadView,
        timeline_event: MatchEventView | None = None,
    ) -> MatchEvent | None:
        payload = dict(item.payload or {})
        creator_player_id = payload.get("creator_player_id")
        if not isinstance(creator_player_id, str) or not creator_player_id:
            return None
        team_id, team_name = self._team_identity(team, replay_payload)
        return MatchEvent(
            match_id=match_id,
            sequence=sequence,
            minute=item.minute,
            event_type=MatchEventType.PASS,
            team=team,
            player_id=creator_player_id,
            metadata_json={
                "team_id": team_id,
                "team_name": team_name,
                "player_name": payload.get("creator_player_name"),
                "target_player_id": item.player_id,
                "target_player_name": payload.get("player_name"),
                "completed": True,
                "importance": 2,
                "source_sequence": item.sequence,
                "source_event_type": item.event_type.value,
                **self._viewer_metadata(item, timeline_event=timeline_event),
            },
        )

    def _derived_tackle_row(
        self,
        match_id: str,
        sequence: int,
        item: ReplayEventLogEntryView,
        team: MatchEventTeam,
        *,
        replay_payload: MatchReplayPayloadView,
        timeline_event: MatchEventView | None = None,
    ) -> MatchEvent | None:
        payload = dict(item.payload or {})
        player_id = item.player_id
        player_name = payload.get("player_name")
        outcome = "foul_conceded"
        if item.event_type.name == "OFFSIDE":
            player_id = payload.get("defensive_actor_id")
            player_name = payload.get("defensive_actor_name")
            outcome = "attack_stopped"
        if not isinstance(player_id, str) or not player_id:
            return None
        team_id, team_name = self._team_identity(team, replay_payload)
        return MatchEvent(
            match_id=match_id,
            sequence=sequence,
            minute=item.minute,
            event_type=MatchEventType.TACKLE,
            team=team,
            player_id=player_id,
            metadata_json={
                "team_id": team_id,
                "team_name": team_name,
                "player_name": player_name,
                "outcome": outcome,
                "importance": 2,
                "source_sequence": item.sequence,
                "source_event_type": item.event_type.value,
                **self._viewer_metadata(item, timeline_event=timeline_event),
            },
        )

    @staticmethod
    def _viewer_metadata(
        item: ReplayEventLogEntryView,
        *,
        timeline_event: MatchEventView | None,
    ) -> dict[str, Any]:
        metadata = dict(timeline_event.metadata) if timeline_event is not None else {}
        render = metadata.get("render")
        commentary_context = metadata.get("commentary_context")
        viewer_payload: dict[str, Any] = {
            "clock_label": timeline_event.clock_label if timeline_event is not None else f"{item.minute}'",
            "presentation_second": timeline_event.presentation_second if timeline_event is not None else None,
            "description": timeline_event.commentary if timeline_event is not None else None,
            "commentary": timeline_event.commentary if timeline_event is not None else None,
            "analyst_commentary": timeline_event.analyst_commentary if timeline_event is not None else None,
            "highlight_eligible": bool(
                metadata.get("render", {}).get("replay", {}).get("eligible", False)
                if isinstance(metadata.get("render"), dict)
                else False
            )
            or item.event_type in _HIGHLIGHT_ELIGIBLE_ENGINE_EVENTS,
        }
        if isinstance(render, dict):
            viewer_payload["render"] = render
        if isinstance(commentary_context, dict):
            viewer_payload["commentary_context"] = commentary_context
        return viewer_payload

    @staticmethod
    def _update_pending_shot(
        pending_shots: dict[tuple[MatchEventTeam, str | None, int], MatchEvent],
        *,
        team: MatchEventTeam,
        player_id: str | None,
        minute: int,
        on_target: bool,
        outcome: str | None = None,
        big_chance: bool | None = None,
    ) -> None:
        row = pending_shots.get((team, player_id, minute))
        if row is None:
            return
        metadata = dict(row.metadata_json or {})
        metadata["on_target"] = on_target
        if outcome is not None:
            metadata["outcome"] = outcome
        if big_chance is not None:
            metadata["big_chance"] = big_chance
        row.metadata_json = metadata


@dataclass(slots=True)
class MatchCommandService:
    session: Session
    orchestrator: OrchestratorService

    def start_match(self, payload: MatchStartRequest) -> MatchCommandAcceptedView:
        match = self.session.get(CompetitionMatch, payload.match_id)
        if match is None:
            match = self._create_match(payload)
            self.session.add(match)
        else:
            self._prepare_existing_match_for_start(match, payload)

        self.session.flush()
        outbox_event = self.orchestrator.start_match(payload.model_dump(mode="json"))
        self.session.commit()
        return MatchCommandAcceptedView(
            match_id=match.id,
            status=self._resolved_status(match),
            command_name="StartMatchCommand",
            outbox_event_id=outbox_event.event_id,
            outbox_event_type=outbox_event.event_type,
            queued_at=outbox_event.occurred_at,
        )

    @staticmethod
    def _resolved_status(match: CompetitionMatch) -> MatchStatus:
        """Read a match status without raising on rows written by other code paths."""
        return MatchStatus.coerce(match.status) or MatchStatus.SCHEDULED

    def complete_match(self, payload: MatchCompleteRequest) -> MatchCommandAcceptedView:
        match = self.session.get(CompetitionMatch, payload.match_id)
        if match is None:
            raise MatchCommandNotFoundError(f"Match {payload.match_id} was not found.")

        now = payload.completed_at or _utcnow()
        current_status = self._resolved_status(match)
        if current_status is MatchStatus.COMPLETED:
            # Settlement already happened. Replaying the same command is a no-op; a
            # command carrying a different result must never silently overwrite a
            # settled scoreline, because standings/payouts have already consumed it.
            if (match.home_score, match.away_score) != (payload.home_score, payload.away_score):
                raise MatchCommandStateError(
                    f"Match {match.id} is already completed "
                    f"{match.home_score}-{match.away_score} and cannot be re-settled "
                    f"as {payload.home_score}-{payload.away_score}.",
                    match_id=match.id,
                    current_status=current_status.value,
                )
            return MatchCommandAcceptedView(
                match_id=match.id,
                status=current_status,
                command_name="CompleteMatchCommand",
                outbox_event_id=self._last_outbox_event_id(match),
                outbox_event_type="CompleteMatchCommand",
                queued_at=match.completed_at or now,
            )
        try:
            assert_transition(current_status, MatchStatus.COMPLETED, match_id=match.id)
        except MatchStateTransitionError as exc:
            raise MatchCommandStateError(
                str(exc),
                match_id=match.id,
                current_status=current_status.value,
            ) from exc
        match.status = MatchStatus.COMPLETED.value
        match.home_score = payload.home_score
        match.away_score = payload.away_score
        match.completed_at = now
        match.decided_by_penalties = payload.decided_by_penalties
        if payload.winner_club_id is not None:
            match.winner_club_id = payload.winner_club_id
        elif payload.home_score > payload.away_score:
            match.winner_club_id = match.home_club_id
        elif payload.away_score > payload.home_score:
            match.winner_club_id = match.away_club_id
        else:
            match.winner_club_id = None
        match.metadata_json = _merge_orchestrator_metadata(
            match.metadata_json,
            key="complete_request",
            payload=payload.model_dump(mode="json"),
            recorded_at=now,
        )

        self.session.flush()
        outbox_event = self.orchestrator.complete_match(payload.model_dump(mode="json"))
        match.metadata_json = _merge_orchestrator_metadata(
            match.metadata_json,
            key="complete_outbox_event_id",
            payload={"outbox_event_id": outbox_event.event_id},
            recorded_at=now,
        )
        self.session.commit()
        return MatchCommandAcceptedView(
            match_id=match.id,
            status=self._resolved_status(match),
            command_name="CompleteMatchCommand",
            outbox_event_id=outbox_event.event_id,
            outbox_event_type=outbox_event.event_type,
            queued_at=outbox_event.occurred_at,
        )

    def _create_match(self, payload: MatchStartRequest) -> CompetitionMatch:
        missing_fields = [
            field_name
            for field_name, value in (
                ("competition_id", payload.competition_id),
                ("round_id", payload.round_id),
                ("home_club_id", payload.home_club_id),
                ("away_club_id", payload.away_club_id),
            )
            if value is None or not str(value).strip()
        ]
        if missing_fields:
            raise MatchCommandError(
                "Missing fields for new match creation: " + ", ".join(sorted(missing_fields)) + "."
            )
        now = payload.scheduled_at or _utcnow()
        match_date = payload.match_date or now.date()
        return CompetitionMatch(
            id=payload.match_id,
            competition_id=str(payload.competition_id),
            round_id=str(payload.round_id),
            round_number=payload.round_number or 1,
            stage=(payload.stage or "league").strip() or "league",
            home_club_id=str(payload.home_club_id),
            away_club_id=str(payload.away_club_id),
            scheduled_at=payload.scheduled_at,
            match_date=match_date,
            window=payload.window,
            slot_sequence=payload.slot_sequence or 1,
            status=MatchStatus.QUEUED.value,
            requires_winner=bool(payload.requires_winner),
            metadata_json=_merge_orchestrator_metadata(
                {},
                key="start_request",
                payload=payload.model_dump(mode="json"),
                recorded_at=_utcnow(),
            ),
        )

    @staticmethod
    def _last_outbox_event_id(match: CompetitionMatch) -> str:
        orchestrator_metadata = dict((match.metadata_json or {}).get("orchestrator") or {})
        recorded = orchestrator_metadata.get("complete_outbox_event_id") or {}
        if isinstance(recorded, dict):
            event_id = str(recorded.get("outbox_event_id") or "").strip()
            if event_id:
                return event_id
        return f"replayed:{match.id}"

    def _prepare_existing_match_for_start(self, match: CompetitionMatch, payload: MatchStartRequest) -> None:
        current_status = self._resolved_status(match)
        if is_terminal(current_status):
            # Guard the destructive reset below: a duplicate or late StartMatchCommand
            # must never clear a settled result while standings keep its points.
            raise MatchCommandStateError(
                f"Match {match.id} is {current_status.value} and cannot be restarted.",
                match_id=match.id,
                current_status=current_status.value,
            )
        try:
            assert_transition(current_status, MatchStatus.QUEUED, match_id=match.id)
        except MatchStateTransitionError as exc:
            raise MatchCommandStateError(
                str(exc),
                match_id=match.id,
                current_status=current_status.value,
            ) from exc
        match.status = MatchStatus.QUEUED.value
        match.home_score = 0
        match.away_score = 0
        match.winner_club_id = None
        match.decided_by_penalties = False
        match.completed_at = None
        if payload.competition_id is not None:
            match.competition_id = payload.competition_id
        if payload.round_id is not None:
            match.round_id = payload.round_id
        if payload.round_number is not None:
            match.round_number = payload.round_number
        if payload.stage is not None:
            match.stage = payload.stage
        if payload.home_club_id is not None:
            match.home_club_id = payload.home_club_id
        if payload.away_club_id is not None:
            match.away_club_id = payload.away_club_id
        if payload.scheduled_at is not None:
            match.scheduled_at = payload.scheduled_at
        if payload.match_date is not None:
            match.match_date = payload.match_date
        elif match.match_date is None and payload.scheduled_at is not None:
            match.match_date = payload.scheduled_at.date()
        if payload.window is not None:
            match.window = payload.window
        if payload.slot_sequence is not None:
            match.slot_sequence = payload.slot_sequence
        if payload.requires_winner is not None:
            match.requires_winner = payload.requires_winner
        match.metadata_json = _merge_orchestrator_metadata(
            match.metadata_json,
            key="start_request",
            payload=payload.model_dump(mode="json"),
            recorded_at=_utcnow(),
        )


def _merge_orchestrator_metadata(
    metadata_json: dict[str, Any] | None,
    *,
    key: str,
    payload: dict[str, Any],
    recorded_at: datetime,
) -> dict[str, Any]:
    metadata = dict(metadata_json or {})
    orchestrator_metadata = dict(metadata.get("orchestrator") or {})
    orchestrator_metadata[key] = payload
    orchestrator_metadata[f"{key}_at"] = recorded_at.isoformat()
    metadata["orchestrator"] = orchestrator_metadata
    return metadata


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
