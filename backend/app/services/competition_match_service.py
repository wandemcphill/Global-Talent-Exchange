from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.common.enums.match_status import MatchStatus
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_match_event import CompetitionMatchEvent
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_rule_set import CompetitionRuleSet


@dataclass(slots=True)
class CompetitionMatchService:
    session: Session

    def record_event(
        self,
        *,
        competition_id: str,
        match_id: str,
        event_type: str,
        minute: int | None,
        added_time: int | None,
        club_id: str | None,
        player_id: str | None,
        secondary_player_id: str | None,
        card_type: str | None,
        highlight: bool,
        metadata_json: dict,
    ) -> CompetitionMatchEvent:
        event = CompetitionMatchEvent(
            competition_id=competition_id,
            match_id=match_id,
            event_type=event_type,
            minute=minute,
            added_time=added_time,
            club_id=club_id,
            player_id=player_id,
            secondary_player_id=secondary_player_id,
            card_type=card_type,
            highlight=highlight,
            metadata_json=metadata_json,
        )
        self.session.add(event)
        self.session.flush()
        return event

    def complete_match(
        self,
        *,
        match: CompetitionMatch,
        rule_set: CompetitionRuleSet,
        home_score: int,
        away_score: int,
        decided_by_penalties: bool = False,
        winner_club_id: str | None = None,
    ) -> CompetitionMatch:
        if match.status == MatchStatus.COMPLETED.value:
            return match
        match.home_score = home_score
        match.away_score = away_score
        match.decided_by_penalties = decided_by_penalties
        if winner_club_id is None:
            if home_score > away_score:
                winner_club_id = match.home_club_id
            elif away_score > home_score:
                winner_club_id = match.away_club_id
        if match.requires_winner and winner_club_id is None:
            raise ValueError("Match requires a winner but scores are level.")
        match.winner_club_id = winner_club_id
        match.status = MatchStatus.COMPLETED.value
        match.completed_at = datetime.now(timezone.utc)
        self._apply_match_result(match=match, rule_set=rule_set)
        self.session.flush()
        return match

    def _apply_match_result(self, *, match: CompetitionMatch, rule_set: CompetitionRuleSet) -> None:
        if match.stats_applied:
            return
        home = self._participant(match.competition_id, match.home_club_id, match.group_key)
        away = self._participant(match.competition_id, match.away_club_id, match.group_key)
        if home is None or away is None:
            return
        home.played += 1
        away.played += 1
        home.goals_for += match.home_score
        home.goals_against += match.away_score
        away.goals_for += match.away_score
        away.goals_against += match.home_score

        win_points = rule_set.league_win_points or 3
        draw_points = rule_set.league_draw_points or 1
        loss_points = rule_set.league_loss_points or 0

        if match.home_score > match.away_score:
            home.wins += 1
            away.losses += 1
            home.points += win_points
            away.points += loss_points
        elif match.home_score < match.away_score:
            away.wins += 1
            home.losses += 1
            away.points += win_points
            home.points += loss_points
        else:
            home.draws += 1
            away.draws += 1
            home.points += draw_points
            away.points += draw_points

        home.goal_diff = home.goals_for - home.goals_against
        away.goal_diff = away.goals_for - away.goals_against
        match.stats_applied = True

    def standings(
        self,
        *,
        competition_id: str,
        rule_set: CompetitionRuleSet,
        group_key: str | None = None,
    ) -> list[CompetitionParticipant]:
        stmt = select(CompetitionParticipant).where(CompetitionParticipant.competition_id == competition_id)
        if group_key is not None:
            stmt = stmt.where(CompetitionParticipant.group_key == group_key)
        participants = list(self.session.scalars(stmt).all())
        return self._rank_participants(
            competition_id=competition_id,
            participants=participants,
            rule_set=rule_set,
        )

    def _rank_participants(
        self,
        *,
        competition_id: str,
        participants: list[CompetitionParticipant],
        rule_set: CompetitionRuleSet,
    ) -> list[CompetitionParticipant]:
        head_to_head = self._head_to_head_scores(competition_id, participants, rule_set)
        fair_play = self._fair_play_scores(competition_id, participants)

        def sort_key(item: CompetitionParticipant) -> tuple:
            key: list[object] = []
            for rule in rule_set.league_tie_break_order or ["points", "goal_diff", "goals_for"]:
                if rule == "points":
                    key.append(-(item.points or 0))
                elif rule == "goal_diff":
                    key.append(-(item.goal_diff or 0))
                elif rule == "goals_for":
                    key.append(-(item.goals_for or 0))
                elif rule == "head_to_head":
                    stats = head_to_head.get(item.club_id, (0, 0, 0))
                    key.extend([-stats[0], -stats[1], -stats[2]])
                elif rule == "fair_play":
                    key.append(fair_play.get(item.club_id, 0))
            key.append(item.club_id)
            return tuple(key)

        return sorted(participants, key=sort_key)

    def _participant(
        self,
        competition_id: str,
        club_id: str,
        group_key: str | None,
    ) -> CompetitionParticipant | None:
        stmt = select(CompetitionParticipant).where(
            CompetitionParticipant.competition_id == competition_id,
            CompetitionParticipant.club_id == club_id,
        )
        if group_key is not None:
            stmt = stmt.where(CompetitionParticipant.group_key == group_key)
        return self.session.scalar(stmt)

    def _head_to_head_scores(
        self,
        competition_id: str,
        participants: Iterable[CompetitionParticipant],
        rule_set: CompetitionRuleSet,
    ) -> dict[str, tuple[int, int, int]]:
        club_ids = {participant.club_id for participant in participants}
        if len(club_ids) < 2:
            return {}
        matches = list(
            self.session.scalars(
                select(CompetitionMatch).where(
                    CompetitionMatch.competition_id == competition_id,
                    CompetitionMatch.status == MatchStatus.COMPLETED.value,
                    CompetitionMatch.home_club_id.in_(club_ids),
                    CompetitionMatch.away_club_id.in_(club_ids),
                )
            ).all()
        )
        scores: dict[str, list[int]] = {club_id: [0, 0, 0] for club_id in club_ids}
        win_points = rule_set.league_win_points or 3
        draw_points = rule_set.league_draw_points or 1
        loss_points = rule_set.league_loss_points or 0
        for match in matches:
            home = scores[match.home_club_id]
            away = scores[match.away_club_id]
            home[1] += match.home_score - match.away_score
            home[2] += match.home_score
            away[1] += match.away_score - match.home_score
            away[2] += match.away_score
            if match.home_score > match.away_score:
                home[0] += win_points
                away[0] += loss_points
            elif match.home_score < match.away_score:
                away[0] += win_points
                home[0] += loss_points
            else:
                home[0] += draw_points
                away[0] += draw_points
        return {club_id: (values[0], values[1], values[2]) for club_id, values in scores.items()}

    def _fair_play_scores(
        self,
        competition_id: str,
        participants: Iterable[CompetitionParticipant],
    ) -> dict[str, int]:
        club_ids = {participant.club_id for participant in participants}
        if not club_ids:
            return {}
        events = list(
            self.session.scalars(
                select(CompetitionMatchEvent).where(
                    CompetitionMatchEvent.competition_id == competition_id,
                    CompetitionMatchEvent.event_type == "card",
                    CompetitionMatchEvent.club_id.in_(club_ids),
                )
            ).all()
        )
        scores: dict[str, int] = {club_id: 0 for club_id in club_ids}
        for event in events:
            if event.club_id is None:
                continue
            if event.card_type == "red":
                scores[event.club_id] += 3
            elif event.card_type == "yellow":
                scores[event.club_id] += 1
        return scores


__all__ = ["CompetitionMatchService"]
