from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.app.world_super_cup.models import (
    GroupStanding,
    KnockoutBracket,
    KnockoutMatch,
    KnockoutRound,
    QualifiedClub,
    TrophyCeremonyMetadata,
)
from backend.app.world_super_cup.services.match_resolution import resolve_seeded_score


@dataclass(slots=True)
class KnockoutService:
    def build_bracket(
        self,
        tables: tuple[GroupStanding, ...],
        tournament_start: datetime,
        ceremony: TrophyCeremonyMetadata,
    ) -> KnockoutBracket:
        grouped = self._group_positions(tables)
        round_of_16_pairings = (
            ("A", 1, "B", 2),
            ("C", 1, "D", 2),
            ("E", 1, "F", 2),
            ("G", 1, "H", 2),
            ("B", 1, "A", 2),
            ("D", 1, "C", 2),
            ("F", 1, "E", 2),
            ("H", 1, "G", 2),
        )
        round_of_16 = self._play_round(
            round_name="round_of_16",
            pairings=[
                (grouped[left_group][left_position], grouped[right_group][right_position])
                for left_group, left_position, right_group, right_position in round_of_16_pairings
            ],
            kickoff_at=tournament_start + timedelta(days=2),
            venue_prefix="Knockout Arena",
        )
        quarterfinal = self._play_round(
            round_name="quarterfinal",
            pairings=self._pair_winners(round_of_16.matches),
            kickoff_at=tournament_start + timedelta(days=2, hours=4),
            venue_prefix="Quarterfinal Hub",
        )
        semifinal = self._play_round(
            round_name="semifinal",
            pairings=self._pair_winners(quarterfinal.matches),
            kickoff_at=tournament_start + timedelta(days=2, hours=8),
            venue_prefix="Semifinal Hub",
        )
        final = self._play_round(
            round_name="final",
            pairings=self._pair_winners(semifinal.matches),
            kickoff_at=tournament_start + timedelta(days=2, hours=12),
            venue_prefix="Final Arena",
        )
        final_match = final.matches[0]
        champion = final_match.winner
        runner_up = final_match.away_club if final_match.winner == final_match.home_club else final_match.home_club
        return KnockoutBracket(
            rounds=(round_of_16, quarterfinal, semifinal, final),
            champion=champion,
            runner_up=runner_up,
            ceremony=ceremony,
        )

    def _group_positions(
        self,
        tables: tuple[GroupStanding, ...],
    ) -> dict[str, dict[int, QualifiedClub]]:
        grouped: dict[str, dict[int, QualifiedClub]] = {}
        for row in tables:
            grouped.setdefault(row.group_name, {})[row.position] = row.club
        return grouped

    def _pair_winners(
        self,
        matches: tuple[KnockoutMatch, ...],
    ) -> list[tuple[QualifiedClub, QualifiedClub]]:
        winners = [match.winner for match in matches if match.winner is not None]
        return [(winners[index], winners[index + 1]) for index in range(0, len(winners), 2)]

    def _play_round(
        self,
        *,
        round_name: str,
        pairings: list[tuple[QualifiedClub, QualifiedClub]],
        kickoff_at: datetime,
        venue_prefix: str,
    ) -> KnockoutRound:
        matches: list[KnockoutMatch] = []
        for index, (home_club, away_club) in enumerate(pairings, start=1):
            home_score, away_score, decided_by = resolve_seeded_score(
                home_club.coefficient_points,
                away_club.coefficient_points,
                allow_draw=False,
            )
            winner = home_club if home_score > away_score else away_club
            if home_score == away_score:
                winner = home_club if home_club.coefficient_points >= away_club.coefficient_points else away_club
            matches.append(
                KnockoutMatch(
                    match_id=f"{round_name}-{index}",
                    round_name=round_name,
                    home_club=home_club,
                    away_club=away_club,
                    kickoff_at=kickoff_at + timedelta(minutes=(index - 1) * 20),
                    venue=f"{venue_prefix} {index}",
                    winner=winner,
                    decided_by=decided_by,
                    home_score=home_score,
                    away_score=away_score,
                )
            )
        return KnockoutRound(round_name=round_name, matches=tuple(matches))
