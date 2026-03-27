from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.match_engine.schemas import MatchPlayerRatingView
from app.match_engine.simulation.models import MatchEventType, PlayerRole, SimulationResult


@dataclass(slots=True)
class _RatingLedger:
    player_id: str
    player_name: str
    team_id: str
    team_name: str
    role: PlayerRole
    started: bool
    minutes_played: int
    goals: int = 0
    assists: int = 0
    saves: int = 0
    shots_on_target: int = 0
    missed_chances: int = 0
    big_chances_missed: int = 0
    yellow_cards: int = 0
    red_card: bool = False
    injured: bool = False
    key_passes: int = 0
    tackles_won: int = 0
    interceptions: int = 0
    xg: float = 0.0
    xg_faced: float = 0.0


class PositionAwarePlayerRatingEngine:
    def rate(
        self,
        result: SimulationResult,
        *,
        events: Iterable | None = None,
        limit: int | None = None,
    ) -> list[MatchPlayerRatingView]:
        event_list = list(events) if events is not None else None
        if event_list is None or len(event_list) == len(result.events):
            ledgers = self._full_match_ledgers(result)
        else:
            ledgers = self._event_subset_ledgers(result, event_list)

        ratings = self._score_ledgers(result, ledgers)
        ordered = sorted(
            ratings,
            key=lambda item: (
                -item.rating,
                item.team_name,
                item.player_name,
            ),
        )
        if limit is not None:
            return ordered[:limit]
        return ordered

    def _full_match_ledgers(self, result: SimulationResult) -> list[_RatingLedger]:
        return [
            _RatingLedger(
                player_id=player.player_id,
                player_name=player.player_name,
                team_id=player.team_id,
                team_name=player.team_name,
                role=player.role,
                started=player.started,
                minutes_played=player.minutes_played,
                goals=player.goals,
                assists=player.assists,
                saves=player.saves,
                shots_on_target=player.shots_on_target,
                missed_chances=player.missed_chances,
                big_chances_missed=player.big_chances_missed,
                yellow_cards=player.yellow_cards,
                red_card=player.red_card,
                injured=player.injured,
                key_passes=player.key_passes,
                tackles_won=player.tackles_won,
                interceptions=player.interceptions,
                xg=player.xg,
                xg_faced=player.xg_faced,
            )
            for player in result.player_stats
            if player.minutes_played > 0 or player.is_notable()
        ]

    def _event_subset_ledgers(self, result: SimulationResult, events: list) -> list[_RatingLedger]:
        roster = {
            player.player_id: _RatingLedger(
                player_id=player.player_id,
                player_name=player.player_name,
                team_id=player.team_id,
                team_name=player.team_name,
                role=player.role,
                started=player.started,
                minutes_played=min(player.minutes_played, 45),
            )
            for player in result.player_stats
        }
        visible_player_ids: set[str] = set()
        for event in events:
            primary_id = event.primary_player_id
            secondary_id = event.secondary_player_id
            creator_id = self._optional_player_id(event.metadata.get("creator_player_id"))
            defensive_actor_id = self._optional_player_id(event.metadata.get("defensive_actor_id"))
            xg = float(event.metadata.get("xg", event.metadata.get("chance_quality", 0.0)) or 0.0)

            for player_id in (primary_id, secondary_id, creator_id, defensive_actor_id):
                if player_id and player_id in roster:
                    visible_player_ids.add(player_id)

            if primary_id and primary_id in roster:
                ledger = roster[primary_id]
                if event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_SCORED}:
                    ledger.goals += 1
                if event.event_type in {
                    MatchEventType.GOAL,
                    MatchEventType.GOALKEEPER_SAVE,
                    MatchEventType.DOUBLE_SAVE,
                    MatchEventType.MISSED_CHANCE,
                    MatchEventType.MISSED_BIG_CHANCE,
                    MatchEventType.WOODWORK,
                    MatchEventType.PENALTY_SCORED,
                    MatchEventType.PENALTY_MISSED,
                }:
                    ledger.xg += xg
                if event.event_type in {
                    MatchEventType.GOAL,
                    MatchEventType.GOALKEEPER_SAVE,
                    MatchEventType.DOUBLE_SAVE,
                    MatchEventType.PENALTY_SCORED,
                    MatchEventType.PENALTY_MISSED,
                }:
                    ledger.shots_on_target += 1
                if event.event_type in {MatchEventType.GOALKEEPER_SAVE, MatchEventType.DOUBLE_SAVE}:
                    ledger.saves += 1
                if event.event_type in {MatchEventType.MISSED_CHANCE, MatchEventType.MISSED_BIG_CHANCE, MatchEventType.PENALTY_MISSED}:
                    ledger.missed_chances += 1
                if event.event_type in {MatchEventType.MISSED_BIG_CHANCE, MatchEventType.PENALTY_MISSED}:
                    ledger.big_chances_missed += 1
                if event.event_type is MatchEventType.YELLOW_CARD:
                    ledger.yellow_cards += 1
                if event.event_type is MatchEventType.RED_CARD:
                    ledger.red_card = True
                if event.event_type is MatchEventType.INJURY:
                    ledger.injured = True
                if event.event_type in {MatchEventType.GOALKEEPER_SAVE, MatchEventType.DOUBLE_SAVE, MatchEventType.PENALTY_MISSED}:
                    ledger.xg_faced += xg

            if secondary_id and secondary_id in roster:
                secondary_ledger = roster[secondary_id]
                if event.event_type is MatchEventType.GOAL and not bool(event.metadata.get("penalty", False)):
                    secondary_ledger.assists += 1
                if event.event_type in {MatchEventType.GOALKEEPER_SAVE, MatchEventType.DOUBLE_SAVE, MatchEventType.PENALTY_MISSED}:
                    secondary_ledger.xg += xg
                    secondary_ledger.shots_on_target += 1

            if creator_id and creator_id in roster:
                roster[creator_id].key_passes += 1

            if defensive_actor_id and defensive_actor_id in roster:
                roster[defensive_actor_id].interceptions += 1

        return [roster[player_id] for player_id in visible_player_ids if player_id in roster]

    def _score_ledgers(self, result: SimulationResult, ledgers: list[_RatingLedger]) -> list[MatchPlayerRatingView]:
        if not ledgers:
            return []

        team_context = {
            result.home_team_id: {
                "won": result.winner_team_id == result.home_team_id,
                "lost": bool(result.winner_team_id and result.winner_team_id != result.home_team_id),
                "possession": result.home_stats.possession,
                "goals_for": result.home_score,
                "goals_against": result.away_score,
            },
            result.away_team_id: {
                "won": result.winner_team_id == result.away_team_id,
                "lost": bool(result.winner_team_id and result.winner_team_id != result.away_team_id),
                "possession": result.away_stats.possession,
                "goals_for": result.away_score,
                "goals_against": result.home_score,
            },
        }
        scored: list[tuple[_RatingLedger, float, str]] = []
        for ledger in ledgers:
            context = team_context.get(
                ledger.team_id,
                {
                    "won": False,
                    "lost": False,
                    "possession": 50,
                    "goals_for": 0,
                    "goals_against": 0,
                },
            )
            score = 6.0
            minutes_share = max(0.35, min(1.0, ledger.minutes_played / 90.0)) if ledger.minutes_played else 0.35
            clean_sheet = bool(context["goals_against"] == 0 and ledger.minutes_played >= 60)

            if ledger.role is PlayerRole.FORWARD:
                score += ledger.goals * 0.7
                score += ledger.shots_on_target * 0.15
                score += (ledger.goals - ledger.xg) * 0.5
                score -= ledger.big_chances_missed * 0.3
                score += ledger.key_passes * 0.05
            elif ledger.role is PlayerRole.MIDFIELDER:
                score += ledger.assists * 0.5
                score += ledger.key_passes * 0.2
                score += max(-0.25, min(0.35, (float(context["possession"]) - 50.0) * 0.015))
                score += ledger.goals * 0.45
                score += (ledger.goals - ledger.xg) * 0.25
            elif ledger.role is PlayerRole.DEFENDER:
                score += ledger.tackles_won * 0.2
                score += ledger.interceptions * 0.2
                score -= float(context["goals_against"]) * 0.5 * minutes_share
                if clean_sheet:
                    score += 0.7
                score += ledger.key_passes * 0.05
            else:
                score += ledger.saves * 0.3
                score += (ledger.xg_faced - float(context["goals_against"])) * 0.5
                if clean_sheet:
                    score += 1.0

            if context["won"] and ledger.minutes_played >= 30:
                score += 0.5
            elif context["lost"] and ledger.minutes_played >= 30:
                score -= 0.3

            score -= ledger.yellow_cards * 0.15
            if ledger.red_card:
                score -= 0.9
            if ledger.injured:
                score -= 0.15

            summary = self._summary_for_ledger(ledger, clean_sheet=clean_sheet)
            scored.append((ledger, score, summary))

        if scored:
            mvp_index = max(range(len(scored)), key=lambda index: scored[index][1])
            ledger, score, summary = scored[mvp_index]
            scored[mvp_index] = (ledger, score + 1.0, summary if "MVP" in summary else f"{summary}; MVP." if summary else "MVP.")

        views = [
            MatchPlayerRatingView(
                player_id=ledger.player_id,
                player_name=ledger.player_name,
                team_id=ledger.team_id,
                team_name=ledger.team_name,
                rating=round(self._clamp(score, 4.0, 10.0), 2),
                summary=summary or None,
            )
            for ledger, score, summary in scored
        ]
        return views

    def _summary_for_ledger(self, ledger: _RatingLedger, *, clean_sheet: bool) -> str:
        parts: list[str] = []
        if ledger.role is PlayerRole.FORWARD:
            if ledger.goals:
                parts.append(f"{ledger.goals} goal{'s' if ledger.goals != 1 else ''}")
            if ledger.shots_on_target:
                parts.append(f"{ledger.shots_on_target} on target")
            delta = ledger.goals - ledger.xg
            if abs(delta) >= 0.25:
                parts.append(f"{delta:+.1f} vs xG")
            if ledger.big_chances_missed:
                parts.append(f"{ledger.big_chances_missed} big chance missed")
        elif ledger.role is PlayerRole.MIDFIELDER:
            if ledger.assists:
                parts.append(f"{ledger.assists} assist{'s' if ledger.assists != 1 else ''}")
            if ledger.key_passes:
                parts.append(f"{ledger.key_passes} key pass{'es' if ledger.key_passes != 1 else ''}")
            if ledger.goals:
                parts.append(f"{ledger.goals} goal{'s' if ledger.goals != 1 else ''}")
        elif ledger.role is PlayerRole.DEFENDER:
            if ledger.interceptions:
                parts.append(f"{ledger.interceptions} interception{'s' if ledger.interceptions != 1 else ''}")
            if clean_sheet:
                parts.append("clean sheet")
            if ledger.goals:
                parts.append(f"{ledger.goals} goal{'s' if ledger.goals != 1 else ''}")
        else:
            if ledger.saves:
                parts.append(f"{ledger.saves} save{'s' if ledger.saves != 1 else ''}")
            if clean_sheet:
                parts.append("clean sheet")
            if ledger.xg_faced:
                parts.append(f"{ledger.xg_faced:.2f} xG faced")

        if ledger.red_card:
            parts.append("sent off")
        elif ledger.yellow_cards:
            parts.append("booked")
        if ledger.injured:
            parts.append("injury setback")
        if parts:
            return ", ".join(parts[:3])
        return {
            PlayerRole.FORWARD: "kept the attacking line active",
            PlayerRole.MIDFIELDER: "held midfield control",
            PlayerRole.DEFENDER: "protected the back line",
            PlayerRole.GOALKEEPER: "steady goalkeeping shift",
        }[ledger.role]

    def _optional_player_id(self, value: object | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
