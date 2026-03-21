from __future__ import annotations

from random import Random

from app.match_engine.simulation.models import PenaltyAttempt, PenaltyShootout, TeamRuntimeState


class PenaltyShootoutGenerator:
    def generate(self, home: TeamRuntimeState, away: TeamRuntimeState, rng: Random) -> PenaltyShootout:
        home_order = self._penalty_order(home)
        away_order = self._penalty_order(away)
        home_score = 0
        away_score = 0
        home_taken = 0
        away_taken = 0
        attempts: list[PenaltyAttempt] = []

        for round_number in range(1, 6):
            home_attempt = self._take_attempt(round_number, home, away, home_order[(round_number - 1) % len(home_order)], home_score, away_score, rng)
            home_score = home_attempt.home_penalties
            away_score = home_attempt.away_penalties
            home_taken += 1
            attempts.append(home_attempt)
            if self._winner_is_locked(home_score, away_score, home_taken, away_taken):
                winner_team_id, winner_team_name = self._winner(home, away, home_score, away_score)
                return PenaltyShootout(
                    winner_team_id=winner_team_id,
                    winner_team_name=winner_team_name,
                    home_penalties=home_score,
                    away_penalties=away_score,
                    attempts=tuple(attempts),
                )

            away_attempt = self._take_attempt(round_number, away, home, away_order[(round_number - 1) % len(away_order)], home_score, away_score, rng)
            home_score = away_attempt.home_penalties
            away_score = away_attempt.away_penalties
            away_taken += 1
            attempts.append(away_attempt)
            if self._winner_is_locked(home_score, away_score, home_taken, away_taken):
                winner_team_id, winner_team_name = self._winner(home, away, home_score, away_score)
                return PenaltyShootout(
                    winner_team_id=winner_team_id,
                    winner_team_name=winner_team_name,
                    home_penalties=home_score,
                    away_penalties=away_score,
                    attempts=tuple(attempts),
                )

        sudden_death_round = 6
        while home_score == away_score:
            home_attempt = self._take_attempt(sudden_death_round, home, away, home_order[(sudden_death_round - 1) % len(home_order)], home_score, away_score, rng)
            home_score = home_attempt.home_penalties
            away_score = home_attempt.away_penalties
            attempts.append(home_attempt)

            away_attempt = self._take_attempt(sudden_death_round, away, home, away_order[(sudden_death_round - 1) % len(away_order)], home_score, away_score, rng)
            home_score = away_attempt.home_penalties
            away_score = away_attempt.away_penalties
            attempts.append(away_attempt)
            sudden_death_round += 1

        winner_team_id, winner_team_name = self._winner(home, away, home_score, away_score)
        return PenaltyShootout(
            winner_team_id=winner_team_id,
            winner_team_name=winner_team_name,
            home_penalties=home_score,
            away_penalties=away_score,
            attempts=tuple(attempts),
        )

    def _penalty_order(self, team: TeamRuntimeState):
        active_players = team.active_outfielders() or team.active_players()
        ordered = sorted(active_players, key=lambda player: (player.penalty_value(), player.overall), reverse=True)
        if ordered:
            return ordered
        goalkeeper = team.goalkeeper()
        if goalkeeper is not None:
            return [goalkeeper]
        return list(team.players_by_id.values())[:1]

    def _take_attempt(
        self,
        round_number: int,
        taking_team: TeamRuntimeState,
        defending_team: TeamRuntimeState,
        taker,
        home_score: int,
        away_score: int,
        rng: Random,
    ) -> PenaltyAttempt:
        goalkeeper = defending_team.goalkeeper()
        save_rating = goalkeeper.goalkeeping_value() if goalkeeper is not None else defending_team.strength.goalkeeping
        chance = self._clamp(
            0.58
            + ((taker.penalty_value() - save_rating) / 170.0)
            + ((taking_team.strength.overall - defending_team.strength.overall) / 400.0),
            0.38,
            0.90,
        )
        scored = rng.random() < chance
        if taking_team.is_home:
            home_score = home_score + int(scored)
        else:
            away_score = away_score + int(scored)
        return PenaltyAttempt(
            order=round_number,
            team_id=taking_team.team_id,
            team_name=taking_team.team_name,
            taker_id=taker.player_id,
            taker_name=taker.player_name,
            goalkeeper_id=goalkeeper.player_id if goalkeeper is not None else None,
            goalkeeper_name=goalkeeper.player_name if goalkeeper is not None else None,
            scored=scored,
            home_penalties=home_score,
            away_penalties=away_score,
        )

    def _winner_is_locked(self, home_score: int, away_score: int, home_taken: int, away_taken: int) -> bool:
        home_remaining = 5 - home_taken
        away_remaining = 5 - away_taken
        return home_score > away_score + away_remaining or away_score > home_score + home_remaining

    def _winner(self, home: TeamRuntimeState, away: TeamRuntimeState, home_score: int, away_score: int) -> tuple[str, str]:
        return (home.team_id, home.team_name) if home_score > away_score else (away.team_id, away.team_name)

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
