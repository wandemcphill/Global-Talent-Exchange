from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TournamentSchedulerError(ValueError):
    pass


class TournamentFormat(StrEnum):
    SINGLE_ELIMINATION = "single_elimination"


@dataclass(frozen=True, slots=True)
class TournamentEntrant:
    competitor_id: str
    display_name: str
    elo_rating: int
    seed: int | None = None
    tier_key: str | None = None


@dataclass(frozen=True, slots=True)
class TournamentParticipantSlot:
    competitor_id: str | None
    display_name: str | None
    seed: int | None
    source_match_id: str | None = None
    auto_advanced: bool = False


@dataclass(frozen=True, slots=True)
class TournamentMatch:
    match_id: str
    round_number: int
    round_name: str
    slot_number: int
    starts_at: datetime
    home: TournamentParticipantSlot | None
    away: TournamentParticipantSlot | None
    winner_to_match_id: str | None = None
    bye_match: bool = False


@dataclass(frozen=True, slots=True)
class TournamentRound:
    round_number: int
    round_name: str
    matches: tuple[TournamentMatch, ...]


@dataclass(frozen=True, slots=True)
class TournamentBracket:
    tournament_id: str
    format: TournamentFormat
    created_at: datetime
    bracket_size: int
    entrants: tuple[TournamentEntrant, ...]
    rounds: tuple[TournamentRound, ...]


@dataclass(slots=True)
class _GeneratedMatchState:
    match_id: str
    round_number: int
    round_name: str
    slot_number: int
    starts_at: datetime
    home: TournamentParticipantSlot | None
    away: TournamentParticipantSlot | None
    winner_to_match_id: str | None = None
    bye_match: bool = False
    resolved_slot: TournamentParticipantSlot | None = None


@dataclass(slots=True)
class TournamentScheduler:
    default_round_spacing: timedelta = timedelta(hours=2)
    default_match_spacing: timedelta = timedelta(minutes=45)
    default_parallel_matches: int = 2

    def build_single_elimination(
        self,
        *,
        tournament_id: str,
        entrants: list[TournamentEntrant] | tuple[TournamentEntrant, ...],
        starts_at: datetime,
        round_spacing: timedelta | None = None,
        match_spacing: timedelta | None = None,
        parallel_matches: int | None = None,
    ) -> TournamentBracket:
        if len(entrants) < 2:
            raise TournamentSchedulerError("At least two entrants are required to build a bracket.")

        normalized_entrants = self._normalize_entrants(entrants)
        bracket_size = self._next_power_of_two(len(normalized_entrants))
        seed_order = self._seed_order(bracket_size)
        seeded_slots = self._seeded_slots(seed_order, normalized_entrants)

        effective_round_spacing = round_spacing or self.default_round_spacing
        effective_match_spacing = match_spacing or self.default_match_spacing
        effective_parallel_matches = max(1, parallel_matches or self.default_parallel_matches)

        all_rounds: list[list[_GeneratedMatchState]] = []
        current_round = self._first_round(
            seeded_slots=seeded_slots,
            starts_at=starts_at,
            match_spacing=effective_match_spacing,
            parallel_matches=effective_parallel_matches,
        )
        all_rounds.append(current_round)

        round_number = 2
        while len(current_round) > 1:
            current_round = self._next_round(
                previous_round=current_round,
                round_number=round_number,
                starts_at=starts_at + (effective_round_spacing * (round_number - 1)),
                match_spacing=effective_match_spacing,
                parallel_matches=effective_parallel_matches,
            )
            all_rounds.append(current_round)
            round_number += 1

        rounds = tuple(
            TournamentRound(
                round_number=round_states[0].round_number,
                round_name=round_states[0].round_name,
                matches=tuple(
                    TournamentMatch(
                        match_id=state.match_id,
                        round_number=state.round_number,
                        round_name=state.round_name,
                        slot_number=state.slot_number,
                        starts_at=state.starts_at,
                        home=state.home,
                        away=state.away,
                        winner_to_match_id=state.winner_to_match_id,
                        bye_match=state.bye_match,
                    )
                    for state in round_states
                ),
            )
            for round_states in all_rounds
        )

        return TournamentBracket(
            tournament_id=tournament_id,
            format=TournamentFormat.SINGLE_ELIMINATION,
            created_at=_utcnow(),
            bracket_size=bracket_size,
            entrants=tuple(normalized_entrants),
            rounds=rounds,
        )

    def _first_round(
        self,
        *,
        seeded_slots: tuple[TournamentParticipantSlot | None, ...],
        starts_at: datetime,
        match_spacing: timedelta,
        parallel_matches: int,
    ) -> list[_GeneratedMatchState]:
        match_count = len(seeded_slots) // 2
        round_name = self._round_name(match_count)
        matches: list[_GeneratedMatchState] = []
        for slot_number in range(match_count):
            home = seeded_slots[slot_number * 2]
            away = seeded_slots[(slot_number * 2) + 1]
            bye_match = (home is None) != (away is None)
            resolved_slot = self._resolve_bye(home, away)
            matches.append(
                _GeneratedMatchState(
                    match_id=f"ul-bracket-{uuid4().hex[:12]}",
                    round_number=1,
                    round_name=round_name,
                    slot_number=slot_number + 1,
                    starts_at=starts_at + (match_spacing * (slot_number // parallel_matches)),
                    home=home,
                    away=away,
                    bye_match=bye_match,
                    resolved_slot=resolved_slot,
                )
            )
        return matches

    def _next_round(
        self,
        *,
        previous_round: list[_GeneratedMatchState],
        round_number: int,
        starts_at: datetime,
        match_spacing: timedelta,
        parallel_matches: int,
    ) -> list[_GeneratedMatchState]:
        match_count = len(previous_round) // 2
        round_name = self._round_name(match_count)
        matches: list[_GeneratedMatchState] = []

        for slot_number in range(match_count):
            left = previous_round[slot_number * 2]
            right = previous_round[(slot_number * 2) + 1]
            match_id = f"ul-bracket-{uuid4().hex[:12]}"
            left.winner_to_match_id = match_id
            right.winner_to_match_id = match_id

            home = self._advance_slot(left)
            away = self._advance_slot(right)
            bye_match = (home is None) != (away is None)
            resolved_slot = self._resolve_bye(home, away)
            matches.append(
                _GeneratedMatchState(
                    match_id=match_id,
                    round_number=round_number,
                    round_name=round_name,
                    slot_number=slot_number + 1,
                    starts_at=starts_at + (match_spacing * (slot_number // parallel_matches)),
                    home=home,
                    away=away,
                    bye_match=bye_match,
                    resolved_slot=resolved_slot,
                )
            )
        return matches

    def _normalize_entrants(
        self,
        entrants: list[TournamentEntrant] | tuple[TournamentEntrant, ...],
    ) -> list[TournamentEntrant]:
        provided_seeds = [entrant.seed for entrant in entrants if entrant.seed is not None]
        use_provided_seed = len(provided_seeds) == len(entrants) and len(set(provided_seeds)) == len(provided_seeds)
        if use_provided_seed:
            ordered = sorted(entrants, key=lambda entrant: (entrant.seed or 0, -entrant.elo_rating, entrant.display_name.lower()))
        else:
            ordered = sorted(entrants, key=lambda entrant: (-entrant.elo_rating, entrant.display_name.lower(), entrant.competitor_id))
        return [
            TournamentEntrant(
                competitor_id=entrant.competitor_id,
                display_name=entrant.display_name,
                elo_rating=entrant.elo_rating,
                seed=index,
                tier_key=entrant.tier_key,
            )
            for index, entrant in enumerate(ordered, start=1)
        ]

    def _seeded_slots(
        self,
        seed_order: tuple[int, ...],
        entrants: list[TournamentEntrant],
    ) -> tuple[TournamentParticipantSlot | None, ...]:
        entrant_by_seed = {entrant.seed: entrant for entrant in entrants}
        slots: list[TournamentParticipantSlot | None] = []
        for seed in seed_order:
            entrant = entrant_by_seed.get(seed)
            if entrant is None:
                slots.append(None)
                continue
            slots.append(
                TournamentParticipantSlot(
                    competitor_id=entrant.competitor_id,
                    display_name=entrant.display_name,
                    seed=entrant.seed,
                )
            )
        return tuple(slots)

    def _advance_slot(self, match_state: _GeneratedMatchState) -> TournamentParticipantSlot:
        if match_state.resolved_slot is not None:
            return TournamentParticipantSlot(
                competitor_id=match_state.resolved_slot.competitor_id,
                display_name=match_state.resolved_slot.display_name,
                seed=match_state.resolved_slot.seed,
                source_match_id=match_state.match_id,
                auto_advanced=True,
            )
        return TournamentParticipantSlot(
            competitor_id=None,
            display_name=None,
            seed=None,
            source_match_id=match_state.match_id,
            auto_advanced=False,
        )

    def _resolve_bye(
        self,
        home: TournamentParticipantSlot | None,
        away: TournamentParticipantSlot | None,
    ) -> TournamentParticipantSlot | None:
        if home is not None and away is None:
            return TournamentParticipantSlot(
                competitor_id=home.competitor_id,
                display_name=home.display_name,
                seed=home.seed,
                source_match_id=home.source_match_id,
                auto_advanced=True,
            )
        if away is not None and home is None:
            return TournamentParticipantSlot(
                competitor_id=away.competitor_id,
                display_name=away.display_name,
                seed=away.seed,
                source_match_id=away.source_match_id,
                auto_advanced=True,
            )
        return None

    def _next_power_of_two(self, entrant_count: int) -> int:
        bracket_size = 1
        while bracket_size < entrant_count:
            bracket_size *= 2
        return bracket_size

    def _seed_order(self, bracket_size: int) -> tuple[int, ...]:
        if bracket_size < 2:
            raise TournamentSchedulerError("Bracket size must be at least two.")
        order = [1, 2]
        while len(order) < bracket_size:
            complement = (len(order) * 2) + 1
            expanded: list[int] = []
            for seed in order:
                expanded.extend((seed, complement - seed))
            order = expanded
        return tuple(order)

    def _round_name(self, match_count: int) -> str:
        if match_count == 1:
            return "Final"
        if match_count == 2:
            return "Semifinal"
        if match_count == 4:
            return "Quarterfinal"
        if match_count == 8:
            return "Round of 16"
        return f"Round of {match_count * 2}"


__all__ = [
    "TournamentBracket",
    "TournamentEntrant",
    "TournamentFormat",
    "TournamentMatch",
    "TournamentParticipantSlot",
    "TournamentRound",
    "TournamentScheduler",
    "TournamentSchedulerError",
]
