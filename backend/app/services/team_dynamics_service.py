from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.match_engine.schemas import MatchReplayPayloadView
from app.models.player_agency_state import PlayerAgencyState
from app.models.regen import RegenProfile, RegenTeamDynamicsEffect
from app.team_dynamics.models import PlayerRelationship


@dataclass(frozen=True, slots=True)
class TeamDynamicsSnapshot:
    morale_by_player: dict[str, float]
    chemistry_score: float
    average_morale: float
    morale_penalty: float
    chemistry_penalty: float


@dataclass(slots=True)
class TeamDynamicsService:
    session: Session

    def build_snapshot(self, *, club_id: str | None, squad: list[tuple[Player, object]]) -> TeamDynamicsSnapshot:
        players = [player for player, _role in squad]
        if not players:
            return TeamDynamicsSnapshot({}, 55.0, 55.0, 0.0, 0.0)
        player_ids = [player.id for player in players]
        morale_by_player = {player.id: self.player_morale(player.id, fallback=player.morale) for player in players}
        pair_scores: list[float] = []
        relationships = self._relationship_map(player_ids)
        for index, (player, role) in enumerate(squad):
            for teammate, teammate_role in squad[index + 1 :]:
                relationship = relationships.get(self._pair_key(player.id, teammate.id))
                relationship_score = relationship.relationship_score if relationship is not None else 50.0
                tactical_fit = relationship.tactical_fit if relationship is not None else self._default_tactical_fit(role, teammate_role)
                pair_scores.append((relationship_score + tactical_fit) / 2)
        average_morale = mean(morale_by_player.values())
        chemistry_score = mean(pair_scores) if pair_scores else 55.0
        morale_penalty = 0.0
        chemistry_penalty = 0.0
        if club_id is not None:
            penalties = self._club_penalties(club_id=club_id, player_ids=player_ids)
            morale_penalty = penalties["morale_penalty"]
            chemistry_penalty = penalties["chemistry_penalty"]
            average_morale = max(0.0, average_morale - morale_penalty)
            chemistry_score = max(0.0, chemistry_score - chemistry_penalty)
        return TeamDynamicsSnapshot(
            morale_by_player=morale_by_player,
            chemistry_score=chemistry_score,
            average_morale=average_morale,
            morale_penalty=morale_penalty,
            chemistry_penalty=chemistry_penalty,
        )

    def player_morale(self, player_id: str, *, fallback: float | None = None) -> float:
        player = self.session.get(Player, player_id)
        agency_state = self.session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == player_id))
        values = []
        if player is not None:
            values.append(float(player.morale))
        if agency_state is not None:
            values.append(float(agency_state.morale))
        if not values and fallback is not None:
            values.append(float(fallback))
        return max(0.0, min(100.0, mean(values) if values else 50.0))

    def apply_match_outcome(
        self,
        *,
        fixture_id: str,
        match_date: date,
        replay_payload: MatchReplayPayloadView,
    ) -> None:
        player_ids = [item.player_id for item in replay_payload.summary.player_stats]
        players = {
            player.id: player
            for player in self.session.scalars(select(Player).where(Player.id.in_(player_ids))).all()
        }
        for stat in replay_payload.summary.player_stats:
            player = players.get(stat.player_id)
            if player is None:
                continue
            delta = self._morale_delta_for_stat(stat=stat, replay_payload=replay_payload)
            player.morale = max(0.0, min(100.0, float(player.morale) + delta))
            agency_state = self.session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == player.id))
            if agency_state is not None:
                agency_state.morale = max(0.0, min(100.0, float(agency_state.morale) + delta))
                agency_state.happiness = max(0.0, min(100.0, float(agency_state.happiness) + (delta * 0.6)))
        by_team: dict[str, list[str]] = {}
        for stat in replay_payload.summary.player_stats:
            if stat.minutes_played <= 0:
                continue
            by_team.setdefault(stat.team_id, []).append(stat.player_id)
        for team_id, team_player_ids in by_team.items():
            relationship_delta = self._relationship_delta_for_team(team_id=team_id, replay_payload=replay_payload)
            for index, player_id in enumerate(team_player_ids):
                for teammate_id in team_player_ids[index + 1 :]:
                    relationship = self._get_or_create_relationship(player_id, teammate_id)
                    relationship.relationship_score = max(0.0, min(100.0, relationship.relationship_score + relationship_delta))
                    relationship.tactical_fit = max(0.0, min(100.0, relationship.tactical_fit + (relationship_delta * 0.75)))
                    relationship.matches_together += 1
                    relationship.last_match_together_at = datetime.combine(match_date, datetime.min.time(), tzinfo=UTC)
                    relationship.metadata_json = {
                        **dict(relationship.metadata_json or {}),
                        "last_fixture_id": fixture_id,
                    }
        self.session.flush()

    def _morale_delta_for_stat(self, *, stat, replay_payload: MatchReplayPayloadView) -> float:
        delta = 0.0
        if replay_payload.summary.home_score > replay_payload.summary.away_score:
            if stat.team_id == replay_payload.summary.home_stats.team_id:
                delta += 5.0
            else:
                delta -= 4.0
        elif replay_payload.summary.away_score > replay_payload.summary.home_score:
            if stat.team_id == replay_payload.summary.away_stats.team_id:
                delta += 5.0
            else:
                delta -= 4.0
        else:
            delta += 1.0
        if stat.minutes_played >= 60:
            delta += 2.0
        elif stat.minutes_played == 0:
            delta -= 3.0
        if stat.rating is not None:
            if stat.rating >= 8.0:
                delta += 4.0
            elif stat.rating >= 7.0:
                delta += 2.0
            elif stat.rating < 5.5:
                delta -= 3.0
        delta += min(4.0, float((stat.goals * 2) + stat.assists + stat.saves // 3))
        delta -= float(stat.yellow_cards)
        if stat.red_card:
            delta -= 6.0
        if stat.injured:
            delta -= 4.0
        if stat.minutes_played >= 85:
            delta -= 1.0
        return delta

    def _relationship_delta_for_team(self, *, team_id: str, replay_payload: MatchReplayPayloadView) -> float:
        if replay_payload.summary.home_score == replay_payload.summary.away_score:
            return 0.5
        if team_id == replay_payload.summary.winner_team_id:
            return 1.5
        return -1.0

    def _relationship_map(self, player_ids: list[str]) -> dict[tuple[str, str], PlayerRelationship]:
        relationships = list(
            self.session.scalars(
                select(PlayerRelationship).where(
                    PlayerRelationship.player_id.in_(player_ids),
                    PlayerRelationship.teammate_player_id.in_(player_ids),
                )
            ).all()
        )
        return {self._pair_key(item.player_id, item.teammate_player_id): item for item in relationships}

    def _get_or_create_relationship(self, player_id: str, teammate_id: str) -> PlayerRelationship:
        first, second = self._pair_key(player_id, teammate_id)
        relationship = self.session.scalar(
            select(PlayerRelationship).where(
                PlayerRelationship.player_id == first,
                PlayerRelationship.teammate_player_id == second,
            )
        )
        if relationship is None:
            relationship = PlayerRelationship(player_id=first, teammate_player_id=second)
            self.session.add(relationship)
            self.session.flush()
        return relationship

    def _club_penalties(self, *, club_id: str, player_ids: list[str]) -> dict[str, float]:
        regen_profiles = list(
            self.session.scalars(select(RegenProfile).where(RegenProfile.player_id.in_(player_ids))).all()
        )
        regen_ids = [profile.id for profile in regen_profiles]
        if not regen_ids:
            return {"morale_penalty": 0.0, "chemistry_penalty": 0.0}
        effects = list(
            self.session.scalars(
                select(RegenTeamDynamicsEffect).where(
                    RegenTeamDynamicsEffect.club_id == club_id,
                    RegenTeamDynamicsEffect.regen_id.in_(regen_ids),
                    RegenTeamDynamicsEffect.active.is_(True),
                )
            ).all()
        )
        return {
            "morale_penalty": sum(float(item.morale_penalty) for item in effects),
            "chemistry_penalty": sum(float(item.chemistry_penalty) for item in effects),
        }

    @staticmethod
    def _pair_key(player_id: str, teammate_id: str) -> tuple[str, str]:
        return tuple(sorted((player_id, teammate_id)))

    @staticmethod
    def _default_tactical_fit(role, teammate_role) -> float:
        if role == teammate_role:
            return 58.0
        return 52.0


__all__ = ["TeamDynamicsService", "TeamDynamicsSnapshot"]
