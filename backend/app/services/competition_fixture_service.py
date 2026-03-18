from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Iterable

from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.common.schemas.competition import CompetitionSchedulePlan
from backend.app.models.competition import Competition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_playoff import CompetitionPlayoff
from backend.app.models.competition_round import CompetitionRound
from backend.app.models.competition_rule_set import CompetitionRuleSet
from backend.app.models.base import generate_uuid


@dataclass(slots=True)
class FixtureBuildResult:
    rounds: list[CompetitionRound]
    matches: list[CompetitionMatch]
    playoffs: list[CompetitionPlayoff]


@dataclass(slots=True)
class CompetitionFixtureService:
    def build_initial_fixtures(
        self,
        *,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        participants: Iterable[CompetitionParticipant],
        schedule_plan: CompetitionSchedulePlan | None,
    ) -> FixtureBuildResult:
        participant_list = list(participants)
        if rule_set.group_stage_enabled:
            return self._build_group_stage(
                competition=competition,
                rule_set=rule_set,
                participants=participant_list,
                schedule_plan=schedule_plan,
            )
        if competition.format == CompetitionFormat.LEAGUE.value:
            return self._build_league_rounds(
                competition=competition,
                rule_set=rule_set,
                participants=participant_list,
                schedule_plan=schedule_plan,
            )
        return self._build_knockout_round(
            competition=competition,
            rule_set=rule_set,
            participants=participant_list,
            schedule_plan=schedule_plan,
            round_number=1,
            stage="knockout",
        )

    def build_next_knockout_round(
        self,
        *,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        winners: Iterable[CompetitionParticipant],
        schedule_plan: CompetitionSchedulePlan | None,
        round_number: int,
        stage: str,
    ) -> FixtureBuildResult:
        return self._build_knockout_round(
            competition=competition,
            rule_set=rule_set,
            participants=list(winners),
            schedule_plan=schedule_plan,
            round_number=round_number,
            stage=stage,
        )

    def _build_league_rounds(
        self,
        *,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        participants: list[CompetitionParticipant],
        schedule_plan: CompetitionSchedulePlan | None,
    ) -> FixtureBuildResult:
        clubs = [participant.club_id for participant in sorted(participants, key=lambda item: item.seed or 9999)]
        rounds = self._round_robin_pairings(clubs)
        if rule_set.league_home_away:
            rounds = rounds + [[(away, home) for home, away in matchups] for matchups in rounds]

        round_slots = self._round_slots(competition.id, len(rounds), schedule_plan)
        built_rounds: list[CompetitionRound] = []
        matches: list[CompetitionMatch] = []
        for round_number, matchups in enumerate(rounds, start=1):
            match_date, window, slot_sequence = round_slots.get(round_number, (None, None, 1))
            round_entry = CompetitionRound(
                id=generate_uuid(),
                competition_id=competition.id,
                round_number=round_number,
                stage="league",
                status="scheduled",
                starts_at=window.kickoff_at(match_date) if match_date and window else None,
                metadata_json={},
            )
            built_rounds.append(round_entry)
            for home_id, away_id in matchups:
                matches.append(
                    CompetitionMatch(
                        id=generate_uuid(),
                        competition_id=competition.id,
                        round_id=round_entry.id,
                        round_number=round_number,
                        stage="league",
                        home_club_id=home_id,
                        away_club_id=away_id,
                        match_date=match_date,
                        window=window.value if window else None,
                        slot_sequence=slot_sequence,
                        requires_winner=False,
                        status="scheduled",
                    )
                )
        return FixtureBuildResult(rounds=built_rounds, matches=matches, playoffs=[])

    def _build_group_stage(
        self,
        *,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        participants: list[CompetitionParticipant],
        schedule_plan: CompetitionSchedulePlan | None,
    ) -> FixtureBuildResult:
        clubs = [participant.club_id for participant in sorted(participants, key=lambda item: item.seed or 9999)]
        group_size = rule_set.group_size or max(2, min(4, len(clubs)))
        group_count = rule_set.group_count or int(math.ceil(len(clubs) / group_size))
        groups = [clubs[index::group_count] for index in range(group_count)]

        round_slots = self._round_slots(competition.id, group_size - 1, schedule_plan)
        built_rounds: list[CompetitionRound] = []
        matches: list[CompetitionMatch] = []

        for group_index, group_clubs in enumerate(groups, start=1):
            group_key = f"g{group_index:02d}"
            group_rounds = self._round_robin_pairings(group_clubs)
            if rule_set.league_home_away:
                group_rounds = group_rounds + [[(away, home) for home, away in matchups] for matchups in group_rounds]
            for round_number, matchups in enumerate(group_rounds, start=1):
                match_date, window, slot_sequence = round_slots.get(round_number, (None, None, 1))
                round_entry = CompetitionRound(
                    id=generate_uuid(),
                    competition_id=competition.id,
                    round_number=round_number,
                    stage="group",
                    group_key=group_key,
                    status="scheduled",
                    starts_at=window.kickoff_at(match_date) if match_date and window else None,
                    metadata_json={},
                )
                built_rounds.append(round_entry)
                for home_id, away_id in matchups:
                    matches.append(
                        CompetitionMatch(
                            id=generate_uuid(),
                            competition_id=competition.id,
                            round_id=round_entry.id,
                            round_number=round_number,
                            stage="group",
                            group_key=group_key,
                            home_club_id=home_id,
                            away_club_id=away_id,
                            match_date=match_date,
                            window=window.value if window else None,
                            slot_sequence=slot_sequence,
                            requires_winner=False,
                            status="scheduled",
                        )
                    )
        return FixtureBuildResult(rounds=built_rounds, matches=matches, playoffs=[])

    def _build_knockout_round(
        self,
        *,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        participants: list[CompetitionParticipant],
        schedule_plan: CompetitionSchedulePlan | None,
        round_number: int,
        stage: str,
    ) -> FixtureBuildResult:
        clubs = [participant.club_id for participant in sorted(participants, key=lambda item: item.seed or 9999)]
        if len(clubs) <= 1:
            return FixtureBuildResult(rounds=[], matches=[], playoffs=[])
        configured_bracket_size = rule_set.knockout_bracket_size or self._next_power_of_two(len(clubs))
        bracket_size = configured_bracket_size if round_number <= 1 else self._next_power_of_two(len(clubs))
        pairings = self._knockout_pairings(clubs, bracket_size)

        round_slots = self._round_slots(competition.id, round_number, schedule_plan)
        match_date, window, slot_sequence = round_slots.get(round_number, (None, None, 1))
        round_entry = CompetitionRound(
            id=generate_uuid(),
            competition_id=competition.id,
            round_number=round_number,
            stage=stage,
            status="scheduled",
            starts_at=window.kickoff_at(match_date) if match_date and window else None,
            metadata_json={},
        )
        matches: list[CompetitionMatch] = []
        playoffs: list[CompetitionPlayoff] = []
        for slot_index, (home_id, away_id, home_seed, away_seed) in enumerate(pairings, start=1):
            if home_id is None or away_id is None:
                continue
            match = CompetitionMatch(
                id=generate_uuid(),
                competition_id=competition.id,
                round_id=round_entry.id,
                round_number=round_number,
                stage=stage,
                home_club_id=home_id,
                away_club_id=away_id,
                match_date=match_date,
                window=window.value if window else None,
                slot_sequence=slot_sequence,
                requires_winner=True,
                status="scheduled",
            )
            matches.append(match)
            playoffs.append(
                CompetitionPlayoff(
                    id=generate_uuid(),
                    competition_id=competition.id,
                    round_id=round_entry.id,
                    slot_index=slot_index,
                    home_seed=home_seed,
                    away_seed=away_seed,
                    match_id=match.id,
                    status="scheduled",
                    metadata_json={"stage": stage, "round_number": round_number},
                )
            )
        return FixtureBuildResult(rounds=[round_entry], matches=matches, playoffs=playoffs)

    def _round_robin_pairings(self, clubs: list[str]) -> list[list[tuple[str, str]]]:
        rotating = list(clubs)
        if len(rotating) % 2 == 1:
            rotating.append("bye")
        rounds: list[list[tuple[str, str]]] = []
        for round_index in range(len(rotating) - 1):
            left = rotating[: len(rotating) // 2]
            right = list(reversed(rotating[len(rotating) // 2 :]))
            matchups: list[tuple[str, str]] = []
            for pairing_index, (club_one, club_two) in enumerate(zip(left, right, strict=True)):
                if club_one == "bye" or club_two == "bye":
                    continue
                if (round_index + pairing_index) % 2 == 0:
                    home, away = club_one, club_two
                else:
                    home, away = club_two, club_one
                matchups.append((home, away))
            rounds.append(matchups)
            rotating = [rotating[0], rotating[-1], *rotating[1:-1]]
        return rounds

    def _knockout_pairings(
        self,
        clubs: list[str],
        bracket_size: int,
    ) -> list[tuple[str | None, str | None, int, int]]:
        seeded = list(clubs)
        while len(seeded) < bracket_size:
            seeded.append("bye")
        pairs: list[tuple[str | None, str | None, int, int]] = []
        for index in range(bracket_size // 2):
            home_seed = index + 1
            away_seed = bracket_size - index
            home_id = seeded[home_seed - 1]
            away_id = seeded[away_seed - 1]
            pairs.append((home_id if home_id != "bye" else None, away_id if away_id != "bye" else None, home_seed, away_seed))
        return pairs

    def _round_slots(
        self,
        competition_id: str,
        total_rounds: int,
        schedule_plan: CompetitionSchedulePlan | None,
    ) -> dict[int, tuple[date | None, FixtureWindow | None, int]]:
        if schedule_plan is None or not schedule_plan.assignments:
            return {round_number: (None, None, 1) for round_number in range(1, total_rounds + 1)}
        assignments_by_date = {assignment.match_date: assignment for assignment in schedule_plan.assignments}
        ordered_dates = sorted(assignments_by_date.keys())
        round_slots: dict[int, tuple[date | None, FixtureWindow | None, int]] = {}
        round_number = 1
        for match_date in ordered_dates:
            assignment = assignments_by_date[match_date]
            slots = assignment.slot_sequences or tuple(range(1, len(assignment.windows) + 1))
            for slot_index in range(len(slots)):
                if round_number > total_rounds:
                    break
                if assignment.slot_sequences:
                    window = assignment.windows[0]
                    slot_sequence = assignment.slot_sequences[slot_index]
                else:
                    window = assignment.windows[slot_index % len(assignment.windows)]
                    slot_sequence = slots[slot_index]
                round_slots[round_number] = (match_date, window, slot_sequence)
                round_number += 1
        return round_slots

    @staticmethod
    def _next_power_of_two(value: int) -> int:
        bracket = 1
        while bracket < value:
            bracket *= 2
        return bracket


__all__ = ["CompetitionFixtureService", "FixtureBuildResult"]
