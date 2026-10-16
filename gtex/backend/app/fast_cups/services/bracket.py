from __future__ import annotations

from datetime import timedelta

from app.competition_engine.queue_contracts import SUPPORTED_MATCH_MOMENTS
from app.config.competition_constants import (
    FINAL_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MAX_MINUTES,
    MATCH_PRESENTATION_MIN_MINUTES,
)
from app.fast_cups.models.domain import (
    FastCup,
    FastCupBracket,
    FastCupEntrant,
    FastCupMatch,
    FastCupRound,
    FastCupStage,
    FastCupValidationError,
)

DEFAULT_KEY_MOMENTS = tuple(moment for moment in SUPPORTED_MATCH_MOMENTS if moment != "penalties")

_SIZE_TO_STAGE = {
    256: FastCupStage.ROUND_OF_256,
    128: FastCupStage.ROUND_OF_128,
    64: FastCupStage.ROUND_OF_64,
    32: FastCupStage.ROUND_OF_32,
    16: FastCupStage.ROUND_OF_16,
    8: FastCupStage.QUARTERFINAL,
    4: FastCupStage.SEMIFINAL,
    2: FastCupStage.FINAL,
}


class FastCupBracketService:
    def build_seeded_bracket(self, cup: FastCup) -> FastCupBracket:
        entrants = _validated_entrants(cup)
        rounds: list[FastCupRound] = []
        current_size = len(entrants)
        next_round_sources: tuple[str, ...] = ()
        total_matches = 0
        round_number = 1

        while current_size >= 2:
            stage = _SIZE_TO_STAGE[current_size]
            scheduled_at = cup.slot.kickoff_at + timedelta(minutes=(round_number - 1) * MATCH_PRESENTATION_MAX_MINUTES)
            match_count = current_size // 2
            matches: list[FastCupMatch] = []
            if round_number == 1:
                seeded_pairs = _pair_round(current_participants=entrants)
                for slot_number, (home, away) in enumerate(seeded_pairs, start=1):
                    matches.append(
                        FastCupMatch(
                            tie_id=_tie_id(cup.cup_id, stage, slot_number),
                            stage=stage,
                            round_number=round_number,
                            slot_number=slot_number,
                            scheduled_at=scheduled_at,
                            presentation_min_minutes=MATCH_PRESENTATION_MIN_MINUTES,
                            presentation_max_minutes=_presentation_cap(stage),
                            home=home,
                            away=away,
                            key_moments=DEFAULT_KEY_MOMENTS,
                        )
                    )
            else:
                for slot_number in range(1, match_count + 1):
                    source_home = next_round_sources[(slot_number * 2) - 2]
                    source_away = next_round_sources[(slot_number * 2) - 1]
                    matches.append(
                        FastCupMatch(
                            tie_id=_tie_id(cup.cup_id, stage, slot_number),
                            stage=stage,
                            round_number=round_number,
                            slot_number=slot_number,
                            scheduled_at=scheduled_at,
                            presentation_min_minutes=MATCH_PRESENTATION_MIN_MINUTES,
                            presentation_max_minutes=_presentation_cap(stage),
                            key_moments=DEFAULT_KEY_MOMENTS,
                            home_source_tie_id=source_home,
                            away_source_tie_id=source_away,
                        )
                    )
            rounds.append(
                FastCupRound(
                    stage=stage,
                    round_number=round_number,
                    scheduled_at=scheduled_at,
                    presentation_max_minutes=_presentation_cap(stage),
                    matches=tuple(matches),
                )
            )
            total_matches += match_count
            next_round_sources = tuple(match.tie_id for match in matches)
            current_size //= 2
            round_number += 1

        return FastCupBracket(
            rounds=tuple(rounds),
            total_rounds=len(rounds),
            total_matches=total_matches,
            expected_duration_minutes=_expected_duration_minutes(cup),
            simulated=False,
        )

    def simulate_bracket(self, cup: FastCup, *, winner_overrides: dict[str, str] | None = None) -> FastCupBracket:
        entrants = _validated_entrants(cup)
        seed_lookup = {entrant.club_id: seed for seed, entrant in enumerate(entrants, start=1)}
        winner_overrides = winner_overrides or {}
        current_participants = entrants
        rounds: list[FastCupRound] = []
        semifinalists: list[FastCupEntrant] = []
        runner_up: FastCupEntrant | None = None
        champion: FastCupEntrant | None = None
        total_matches = 0
        round_number = 1

        while len(current_participants) >= 2:
            stage = _SIZE_TO_STAGE[len(current_participants)]
            scheduled_at = cup.slot.kickoff_at + timedelta(minutes=(round_number - 1) * MATCH_PRESENTATION_MAX_MINUTES)
            pairs = _pair_round(current_participants=current_participants)
            winners: list[FastCupEntrant] = []
            matches: list[FastCupMatch] = []
            for slot_number, (home, away) in enumerate(pairs, start=1):
                tie_id = _tie_id(cup.cup_id, stage, slot_number)
                winner = _select_winner(
                    home=home,
                    away=away,
                    tie_id=tie_id,
                    winner_overrides=winner_overrides,
                    seed_lookup=seed_lookup,
                )
                match = _simulate_match(
                    tie_id=tie_id,
                    stage=stage,
                    round_number=round_number,
                    slot_number=slot_number,
                    scheduled_at=scheduled_at,
                    home=home,
                    away=away,
                    winner=winner,
                    seed_lookup=seed_lookup,
                )
                matches.append(match)
                winners.append(winner)
                if stage is FastCupStage.SEMIFINAL:
                    loser = away if winner.club_id == home.club_id else home
                    semifinalists.append(loser)
                if stage is FastCupStage.FINAL:
                    champion = winner
                    runner_up = away if winner.club_id == home.club_id else home

            rounds.append(
                FastCupRound(
                    stage=stage,
                    round_number=round_number,
                    scheduled_at=scheduled_at,
                    presentation_max_minutes=_presentation_cap(stage),
                    matches=tuple(matches),
                )
            )
            total_matches += len(matches)
            current_participants = tuple(winners)
            round_number += 1

        if champion is None or runner_up is None:
            raise FastCupValidationError("Fast cup simulation could not determine a champion.")

        return FastCupBracket(
            rounds=tuple(rounds),
            total_rounds=len(rounds),
            total_matches=total_matches,
            expected_duration_minutes=_expected_duration_minutes(cup),
            simulated=True,
            champion=champion,
            runner_up=runner_up,
            semifinalists=tuple(semifinalists),
        )


def _validated_entrants(cup: FastCup) -> tuple[FastCupEntrant, ...]:
    if len(cup.entrants) != cup.size:
        raise FastCupValidationError("Bracket generation requires the fast cup registration list to be full.")
    unique_ids = {entrant.club_id for entrant in cup.entrants}
    if len(unique_ids) != len(cup.entrants):
        raise FastCupValidationError("Fast cup entrants must be unique.")
    return cup.entrants


def _pair_round(*, current_participants: tuple[FastCupEntrant, ...]) -> tuple[tuple[FastCupEntrant, FastCupEntrant], ...]:
    pairings: list[tuple[FastCupEntrant, FastCupEntrant]] = []
    for index in range(len(current_participants) // 2):
        pairings.append((current_participants[index], current_participants[-(index + 1)]))
    return tuple(pairings)


def _tie_id(cup_id: str, stage: FastCupStage, slot_number: int) -> str:
    return f"{cup_id}:{stage.value}:{slot_number}"


def _presentation_cap(stage: FastCupStage) -> int:
    if stage is FastCupStage.FINAL:
        return FINAL_PRESENTATION_MAX_MINUTES
    return MATCH_PRESENTATION_MAX_MINUTES


def _expected_duration_minutes(cup: FastCup) -> int:
    return int((cup.slot.expected_completion_at - cup.slot.kickoff_at).total_seconds() // 60)


def _select_winner(
    *,
    home: FastCupEntrant,
    away: FastCupEntrant,
    tie_id: str,
    winner_overrides: dict[str, str],
    seed_lookup: dict[str, int],
) -> FastCupEntrant:
    override = winner_overrides.get(tie_id)
    if override is not None:
        if override == home.club_id:
            return home
        if override == away.club_id:
            return away
        raise FastCupValidationError(f"Winner override '{override}' is not part of tie '{tie_id}'.")
    if seed_lookup[home.club_id] <= seed_lookup[away.club_id]:
        return home
    return away


def _simulate_match(
    *,
    tie_id: str,
    stage: FastCupStage,
    round_number: int,
    slot_number: int,
    scheduled_at,
    home: FastCupEntrant,
    away: FastCupEntrant,
    winner: FastCupEntrant,
    seed_lookup: dict[str, int],
) -> FastCupMatch:
    home_seed = seed_lookup[home.club_id]
    away_seed = seed_lookup[away.club_id]
    presentation_max_minutes = _presentation_cap(stage)
    seed_gap = abs(home_seed - away_seed)
    decided_by_penalties = (home_seed + away_seed + slot_number + round_number) % 5 == 0
    key_moments = DEFAULT_KEY_MOMENTS
    if decided_by_penalties:
        scoreline = 1 if (seed_gap + slot_number) % 2 else 0
        home_goals = scoreline
        away_goals = scoreline
        home_penalties = 5 if winner.club_id == home.club_id else 4
        away_penalties = 5 if winner.club_id == away.club_id else 4
        key_moments = (*DEFAULT_KEY_MOMENTS, "penalties")
    else:
        losing_goals = 1 if seed_gap <= 8 else 0
        winning_goals = max(losing_goals + 1, 2 if stage is not FastCupStage.FINAL else 1)
        if winner.club_id == home.club_id:
            home_goals = winning_goals
            away_goals = losing_goals
        else:
            home_goals = losing_goals
            away_goals = winning_goals
        home_penalties = None
        away_penalties = None
    return FastCupMatch(
        tie_id=tie_id,
        stage=stage,
        round_number=round_number,
        slot_number=slot_number,
        scheduled_at=scheduled_at,
        presentation_min_minutes=MATCH_PRESENTATION_MIN_MINUTES,
        presentation_max_minutes=presentation_max_minutes,
        home=home,
        away=away,
        winner=winner,
        home_goals=home_goals,
        away_goals=away_goals,
        home_penalties=home_penalties,
        away_penalties=away_penalties,
        decided_by_penalties=decided_by_penalties,
        key_moments=key_moments,
    )
