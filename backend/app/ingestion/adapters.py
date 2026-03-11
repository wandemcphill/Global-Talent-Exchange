from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .models import CompetitionContext, NormalizedAwardEvent, NormalizedMatchEvent, NormalizedTransferEvent


def _parse_datetime(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now(tz=timezone.utc)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _stage_text(stage: str | None) -> str:
    return (stage or "").replace("_", " ").strip() or "regular season"


def _has_big_moment(
    competition: CompetitionContext,
    stage: str,
    goals: int,
    won_match: bool,
    tags: Sequence[str],
) -> bool:
    lowered_tags = {tag.lower() for tag in tags}
    tagged = any(
        marker in lowered_tags
        for marker in {
            "final-winning-goal",
            "world-cup-final-goal",
            "continental-final-goal",
            "tournament-breakout",
            "iconic-moment",
        }
    )
    final_goal = competition.is_major and "final" in stage.lower() and goals > 0 and won_match
    return tagged or final_goal


@dataclass(slots=True)
class MatchStatsAdapter:
    """Normalizes box-score style provider payloads."""

    provider_name: str = "match_stats"

    def can_handle(self, payload: Mapping[str, Any]) -> bool:
        return "match" in payload and "players" in payload

    def normalize(self, payload: Mapping[str, Any]) -> list[NormalizedMatchEvent]:
        match = payload["match"]
        competition_data = payload.get("competition", {})
        competition = CompetitionContext(
            competition_id=str(competition_data.get("id", competition_data.get("name", "unknown"))),
            name=str(competition_data.get("name", "Unknown Competition")),
            stage=_stage_text(competition_data.get("stage")),
            season=competition_data.get("season"),
            country=competition_data.get("country"),
        )
        occurred_at = _parse_datetime(match.get("kickoff_at"))
        events: list[NormalizedMatchEvent] = []
        for player_line in payload.get("players", []):
            stats = player_line.get("stats", {})
            tags = tuple(str(tag) for tag in player_line.get("tags", ()))
            won_match = bool(player_line.get("won_match", False))
            stage = competition.stage
            goals = int(stats.get("goals", 0))
            events.append(
                NormalizedMatchEvent(
                    source=str(payload.get("provider", self.provider_name)),
                    source_event_id=str(player_line.get("event_id", f"{match['id']}:{player_line['player_id']}")),
                    match_id=str(match["id"]),
                    player_id=str(player_line["player_id"]),
                    player_name=str(player_line.get("player_name", "")),
                    team_id=str(player_line["team_id"]),
                    team_name=str(player_line.get("team_name", "")),
                    opponent_id=str(player_line.get("opponent_id", "unknown")),
                    opponent_name=str(player_line.get("opponent_name", "")),
                    competition=competition,
                    occurred_at=occurred_at,
                    minutes=int(stats.get("minutes", 0)),
                    rating=float(stats.get("rating", 0.0)),
                    goals=goals,
                    assists=int(stats.get("assists", 0)),
                    saves=int(stats.get("saves", 0)),
                    clean_sheet=bool(stats.get("clean_sheet", False)),
                    started=bool(player_line.get("started", False)),
                    won_match=won_match,
                    won_final=bool(player_line.get("won_final", False)),
                    big_moment=_has_big_moment(competition, stage, goals, won_match, tags),
                    tags=tags,
                )
            )
        return events


@dataclass(slots=True)
class MatchAnalyticsAdapter:
    """Normalizes event analytics payloads from a second provider shape."""

    provider_name: str = "match_analytics"

    def can_handle(self, payload: Mapping[str, Any]) -> bool:
        return "fixture_id" in payload and "performances" in payload

    def normalize(self, payload: Mapping[str, Any]) -> list[NormalizedMatchEvent]:
        competition = CompetitionContext(
            competition_id=str(payload.get("competition_id", payload.get("competition_name", "unknown"))),
            name=str(payload.get("competition_name", "Unknown Competition")),
            stage=_stage_text(payload.get("stage")),
            season=payload.get("season"),
            country=payload.get("country"),
        )
        occurred_at = _parse_datetime(payload.get("kickoff"))
        events: list[NormalizedMatchEvent] = []
        for performance in payload.get("performances", []):
            athlete = performance.get("athlete", {})
            club = performance.get("club", {})
            opposition = performance.get("opposition", {})
            tags = tuple(str(tag) for tag in performance.get("moments", ()))
            won_match = bool(performance.get("won", False))
            goals = int(performance.get("goal_count", 0))
            events.append(
                NormalizedMatchEvent(
                    source=str(payload.get("vendor", self.provider_name)),
                    source_event_id=str(performance.get("id", f"{payload['fixture_id']}:{athlete['id']}")),
                    match_id=str(payload["fixture_id"]),
                    player_id=str(athlete["id"]),
                    player_name=str(athlete.get("display_name", "")),
                    team_id=str(club.get("id", "unknown")),
                    team_name=str(club.get("name", "")),
                    opponent_id=str(opposition.get("id", "unknown")),
                    opponent_name=str(opposition.get("name", "")),
                    competition=competition,
                    occurred_at=occurred_at,
                    minutes=int(performance.get("mins", 0)),
                    rating=float(performance.get("match_rating", 0.0)),
                    goals=goals,
                    assists=int(performance.get("assist_count", 0)),
                    saves=int(performance.get("keeper_saves", 0)),
                    clean_sheet=str(performance.get("sheet", "")).lower() == "clean",
                    started=bool(performance.get("started", False)),
                    won_match=won_match,
                    won_final=bool(performance.get("won_final", False)),
                    big_moment=_has_big_moment(competition, competition.stage, goals, won_match, tags),
                    tags=tags,
                )
            )
        return events


@dataclass(slots=True)
class TransferUpdateAdapter:
    provider_name: str = "transfer_updates"

    def can_handle(self, payload: Mapping[str, Any]) -> bool:
        return "transfer" in payload

    def normalize(self, payload: Mapping[str, Any]) -> NormalizedTransferEvent:
        transfer = payload["transfer"]
        player = transfer.get("player", {})
        return NormalizedTransferEvent(
            source=str(payload.get("provider", self.provider_name)),
            source_event_id=str(transfer.get("id", f"{player.get('id', 'unknown')}:{transfer.get('status', 'rumour')}")),
            player_id=str(player.get("id", "unknown")),
            player_name=str(player.get("name", "")),
            occurred_at=_parse_datetime(transfer.get("updated_at")),
            from_club=str(transfer.get("from_club", "")),
            to_club=str(transfer.get("to_club", "")),
            from_competition=transfer.get("from_competition"),
            to_competition=transfer.get("to_competition"),
            reported_fee_eur=float(transfer["reported_fee_eur"]) if transfer.get("reported_fee_eur") is not None else None,
            status=str(transfer.get("status", "rumour")),
        )


@dataclass(slots=True)
class AwardSignalAdapter:
    provider_name: str = "award_signals"

    def can_handle(self, payload: Mapping[str, Any]) -> bool:
        return "award" in payload

    def normalize(self, payload: Mapping[str, Any]) -> NormalizedAwardEvent:
        award = payload["award"]
        player = award.get("player", {})
        return NormalizedAwardEvent(
            source=str(payload.get("provider", self.provider_name)),
            source_event_id=str(award.get("id", f"{player.get('id', 'unknown')}:{award.get('code', 'award')}")),
            player_id=str(player.get("id", "unknown")),
            player_name=str(player.get("name", "")),
            occurred_at=_parse_datetime(award.get("occurred_at")),
            award_code=str(award.get("code", "award")).lower(),
            award_name=str(award.get("name", "Unknown Award")),
            rank=int(award["rank"]) if award.get("rank") is not None else None,
            category=award.get("category"),
        )
