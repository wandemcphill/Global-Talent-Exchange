from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import count
from random import Random

from backend.app.common.enums.match_status import MatchStatus
from backend.app.match_engine.schemas import MatchSimulationRequest
from backend.app.match_engine.simulation.models import (
    InternalPlayer,
    MatchCompetitionType,
    MatchEvent,
    MatchEventType,
    MatchTeamProfile,
    PlayerMatchStats,
    PlayerRole,
    SimulationResult,
    TacticalPlan,
    TeamMatchStats,
    TeamRuntimeState,
)
from backend.app.match_engine.simulation.penalties import PenaltyShootoutGenerator
from backend.app.match_engine.simulation.strength import DefaultTeamStrengthCalculator, TeamStrengthCalculator


@dataclass(frozen=True, slots=True)
class ScheduledItem:
    minute: int
    priority: int
    kind: str
    team_side: str | None
    index: int


class MatchEventGenerator:
    def __init__(
        self,
        *,
        strength_calculator: TeamStrengthCalculator | None = None,
        penalty_generator: PenaltyShootoutGenerator | None = None,
    ) -> None:
        self.strength_calculator = strength_calculator or DefaultTeamStrengthCalculator()
        self.penalty_generator = penalty_generator or PenaltyShootoutGenerator()

    def simulate(self, request: MatchSimulationRequest) -> SimulationResult:
        resolved_seed = self._resolve_seed(request)
        rng = Random(resolved_seed)
        requires_winner = self._resolve_requires_winner(request)

        home_profile = self._build_team_profile(request.home_team)
        away_profile = self._build_team_profile(request.away_team)
        home_strength = self.strength_calculator.calculate(home_profile, is_home=True)
        away_strength = self.strength_calculator.calculate(away_profile, is_home=False)
        home_state = self._build_runtime_state(home_profile, home_strength, is_home=True)
        away_state = self._build_runtime_state(away_profile, away_strength, is_home=False)
        player_stats = self._initialize_player_stats(home_state, away_state)

        events: list[MatchEvent] = []
        event_counter = count(1)
        events.append(
            self._make_event(
                match_id=request.match_id,
                event_counter=event_counter,
                event_type=MatchEventType.KICKOFF,
                minute=0,
                home_state=home_state,
                away_state=away_state,
                metadata={"stage": request.competition.stage},
            )
        )

        schedule = self._build_schedule(home_state, away_state, rng, is_final=request.competition.is_final)
        halftime_added = False
        for item in schedule:
            if not halftime_added and item.minute >= 45:
                events.append(
                    self._make_event(
                        match_id=request.match_id,
                        event_counter=event_counter,
                        event_type=MatchEventType.HALFTIME,
                        minute=45,
                        home_state=home_state,
                        away_state=away_state,
                    )
                )
                halftime_added = True

            state = self._state_for_side(item.team_side, home_state, away_state)
            opponent = self._opponent_for_side(item.team_side, home_state, away_state)
            if item.kind == "yellow":
                maybe_event = self._process_yellow_card(
                    match_id=request.match_id,
                    event_counter=event_counter,
                    state=state,
                    opponent=opponent,
                    minute=item.minute,
                    player_stats=player_stats,
                    rng=rng,
                )
                if maybe_event is not None:
                    events.append(maybe_event)
                continue

            if item.kind == "red":
                maybe_event = self._process_red_card(
                    match_id=request.match_id,
                    event_counter=event_counter,
                    state=state,
                    opponent=opponent,
                    minute=item.minute,
                    player_stats=player_stats,
                    rng=rng,
                    source="straight_red",
                )
                if maybe_event is not None:
                    events.append(maybe_event)
                continue

            if item.kind == "injury":
                events.extend(
                    self._process_injury(
                        match_id=request.match_id,
                        event_counter=event_counter,
                        state=state,
                        opponent=opponent,
                        minute=item.minute,
                        player_stats=player_stats,
                        rng=rng,
                    )
                )
                continue

            if item.kind == "chance":
                maybe_event = self._process_chance(
                    match_id=request.match_id,
                    event_counter=event_counter,
                    attacking=state,
                    defending=opponent,
                    minute=item.minute,
                    player_stats=player_stats,
                    rng=rng,
                )
                if maybe_event is not None:
                    events.append(maybe_event)
                continue

            if item.kind == "window":
                events.extend(
                    self._process_substitution_window(
                        match_id=request.match_id,
                        event_counter=event_counter,
                        minute=item.minute,
                        state=home_state,
                        opponent=away_state,
                        player_stats=player_stats,
                    )
                )
                events.extend(
                    self._process_substitution_window(
                        match_id=request.match_id,
                        event_counter=event_counter,
                        minute=item.minute,
                        state=away_state,
                        opponent=home_state,
                        player_stats=player_stats,
                    )
                )

        if not halftime_added:
            events.append(
                self._make_event(
                    match_id=request.match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.HALFTIME,
                    minute=45,
                    home_state=home_state,
                    away_state=away_state,
                )
            )

        events.append(
            self._make_event(
                match_id=request.match_id,
                event_counter=event_counter,
                event_type=MatchEventType.FULLTIME,
                minute=90,
                home_state=home_state,
                away_state=away_state,
                metadata={"goes_to_penalties": bool(requires_winner and home_state.stats.goals == away_state.stats.goals)},
            )
        )

        shootout = None
        if requires_winner and home_state.stats.goals == away_state.stats.goals:
            shootout = self.penalty_generator.generate(home_state, away_state, rng)
            for offset, attempt in enumerate(shootout.attempts, start=1):
                events.append(
                    self._make_event(
                        match_id=request.match_id,
                        event_counter=event_counter,
                        event_type=MatchEventType.PENALTY_GOAL if attempt.scored else MatchEventType.PENALTY_MISS,
                        minute=90 + offset,
                        home_state=home_state,
                        away_state=away_state,
                        team_id=attempt.team_id,
                        team_name=attempt.team_name,
                        primary_player_id=attempt.taker_id,
                        primary_player_name=attempt.taker_name,
                        secondary_player_id=attempt.goalkeeper_id,
                        secondary_player_name=attempt.goalkeeper_name,
                        metadata={
                            "shootout_round": attempt.order,
                            "home_penalties": attempt.home_penalties,
                            "away_penalties": attempt.away_penalties,
                        },
                    )
                )

        self._resolve_possession(home_state, away_state)
        self._finalize_player_minutes(player_stats)
        winner_team_id, winner_team_name = self._resolve_winner(home_state, away_state, shootout)
        upset = self._resolve_upset(home_state, away_state, winner_team_id)
        ordered_player_stats = tuple(
            sorted(
                player_stats.values(),
                key=lambda line: (
                    line.team_id,
                    -line.goals,
                    -line.assists,
                    -line.saves,
                    -line.missed_chances,
                    line.player_name,
                ),
            )
        )

        return SimulationResult(
            match_id=request.match_id,
            seed=resolved_seed,
            status=MatchStatus.COMPLETED,
            competition_type=request.competition.competition_type,
            stage=request.competition.stage,
            is_final=request.competition.is_final,
            requires_winner=requires_winner,
            home_team_id=home_state.team_id,
            home_team_name=home_state.team_name,
            away_team_id=away_state.team_id,
            away_team_name=away_state.team_name,
            winner_team_id=winner_team_id,
            winner_team_name=winner_team_name,
            home_score=home_state.stats.goals,
            away_score=away_state.stats.goals,
            decided_by_penalties=shootout is not None,
            home_penalty_score=shootout.home_penalties if shootout is not None else None,
            away_penalty_score=shootout.away_penalties if shootout is not None else None,
            upset=upset,
            summary_line=self._build_summary_line(home_state, away_state, shootout),
            home_strength=home_state.strength,
            away_strength=away_state.strength,
            home_stats=home_state.stats,
            away_stats=away_state.stats,
            player_stats=ordered_player_stats,
            events=tuple(events),
            shootout=shootout,
        )

    def _build_team_profile(self, team) -> MatchTeamProfile:
        return MatchTeamProfile(
            team_id=team.team_id,
            team_name=team.team_name,
            formation=team.formation,
            tactics=TacticalPlan(
                style=team.tactics.style,
                pressing=team.tactics.pressing,
                tempo=team.tactics.tempo,
                aggression=team.tactics.aggression,
                substitution_windows=team.tactics.substitution_windows,
                red_card_fallback_formation=team.tactics.red_card_fallback_formation,
                injury_auto_substitution=team.tactics.injury_auto_substitution,
                yellow_card_substitution_minute=team.tactics.yellow_card_substitution_minute,
                yellow_card_replacement_roles=team.tactics.yellow_card_replacement_roles,
                max_substitutions=team.tactics.max_substitutions,
            ),
            manager_profile=team.manager_profile,
            starters=tuple(self._build_player(player) for player in team.starters),
            bench=tuple(self._build_player(player) for player in team.bench),
        )

    def _build_player(self, player) -> InternalPlayer:
        return InternalPlayer(
            player_id=player.player_id,
            player_name=player.player_name,
            role=player.role,
            overall=player.overall,
            finishing=player.finishing,
            creativity=player.creativity,
            defending=player.defending,
            goalkeeping=player.goalkeeping,
            discipline=player.discipline,
            fitness=player.fitness,
        )

    def _build_runtime_state(self, team: MatchTeamProfile, strength, *, is_home: bool) -> TeamRuntimeState:
        player_map = {player.player_id: player for player in [*team.starters, *team.bench]}
        shape = self._parse_formation(team.formation)
        return TeamRuntimeState(
            team_id=team.team_id,
            team_name=team.team_name,
            is_home=is_home,
            starting_formation=team.formation,
            current_formation=team.formation,
            starting_shape=shape,
            current_shape=shape,
            tactics=team.tactics,
            strength=strength,
            players_by_id=player_map,
            active_player_ids=[player.player_id for player in team.starters],
            bench_player_ids=[player.player_id for player in team.bench],
            stats=TeamMatchStats(
                team_id=team.team_id,
                team_name=team.team_name,
                started_formation=team.formation,
                current_formation=team.formation,
            ),
        )

    def _initialize_player_stats(self, home: TeamRuntimeState, away: TeamRuntimeState) -> dict[str, PlayerMatchStats]:
        ledgers: dict[str, PlayerMatchStats] = {}
        for state in (home, away):
            for player_id, player in state.players_by_id.items():
                ledgers[player_id] = PlayerMatchStats(
                    player_id=player.player_id,
                    player_name=player.player_name,
                    team_id=state.team_id,
                    team_name=state.team_name,
                    role=player.role,
                    started=player_id in state.active_player_ids,
                )
        return ledgers

    def _build_schedule(self, home: TeamRuntimeState, away: TeamRuntimeState, rng: Random, *, is_final: bool) -> list[ScheduledItem]:
        items: list[ScheduledItem] = []
        item_index = 0
        for state, side in ((home, "home"), (away, "away")):
            for _ in range(self._yellow_card_count(state, rng)):
                item_index += 1
                items.append(ScheduledItem(minute=self._incident_minute(rng, 12, 88), priority=10, kind="yellow", team_side=side, index=item_index))
            for _ in range(self._red_card_count(state, rng)):
                item_index += 1
                items.append(ScheduledItem(minute=self._incident_minute(rng, 28, 84), priority=11, kind="red", team_side=side, index=item_index))
            for _ in range(self._injury_count(state, rng)):
                item_index += 1
                items.append(ScheduledItem(minute=self._incident_minute(rng, 18, 82), priority=12, kind="injury", team_side=side, index=item_index))

        total_chances = self._chance_count(home, away, rng, is_final=is_final)
        home_share = self._chance_share(home, away)
        for _ in range(total_chances):
            item_index += 1
            side = "home" if rng.random() < home_share else "away"
            items.append(ScheduledItem(minute=self._chance_minute(rng), priority=20, kind="chance", team_side=side, index=item_index))

        all_windows = sorted(set(home.tactics.substitution_windows) | set(away.tactics.substitution_windows))
        for window in all_windows:
            item_index += 1
            items.append(ScheduledItem(minute=window, priority=30, kind="window", team_side=None, index=item_index))

        return sorted(items, key=lambda item: (item.minute, item.priority, item.index))

    def _yellow_card_count(self, state: TeamRuntimeState, rng: Random) -> int:
        base = ((100.0 - state.strength.discipline) / 22.0) + (state.tactics.aggression / 55.0) - 1.1
        count = max(0, int(base) + int(rng.random() < (base % 1 if base > 0 else 0.0)))
        if state.tactics.aggression >= 82 and state.strength.discipline <= 60:
            count = max(count, 1)
        return min(count, 4)

    def _red_card_count(self, state: TeamRuntimeState, rng: Random) -> int:
        risk = max(0.0, ((state.tactics.aggression - 72.0) / 28.0) + ((45.0 - state.strength.discipline) / 28.0))
        if state.tactics.aggression >= 95 and state.strength.discipline <= 35:
            return int(rng.random() < 0.92)
        if risk <= 0.0:
            return 0
        return int(rng.random() < min(0.78, 0.18 + (risk * 0.28)))

    def _injury_count(self, state: TeamRuntimeState, rng: Random) -> int:
        risk = max(
            0.0,
            ((62.0 - state.strength.fitness) / 28.0)
            + ((state.tactics.tempo - 55.0) / 60.0)
            + ((state.tactics.pressing - 55.0) / 80.0),
        )
        count = int(rng.random() < min(0.76, 0.12 + (risk * 0.25))) if risk > 0 else 0
        if state.strength.fitness <= 42 and state.tactics.tempo >= 70:
            count = max(count, 1)
        return min(count, 2)

    def _chance_count(self, home: TeamRuntimeState, away: TeamRuntimeState, rng: Random, *, is_final: bool) -> int:
        tempo_average = (home.tactics.tempo + away.tactics.tempo) / 2.0
        quality_average = (home.strength.attack + away.strength.attack + home.strength.midfield + away.strength.midfield) / 4.0
        base = 9 + round((tempo_average - 50.0) / 12.0) + round((quality_average - 68.0) / 10.0) + rng.randint(0, 3)
        if is_final:
            base += 1
        return int(self._clamp(base, 8, 20 if is_final else 16))

    def _chance_share(self, home: TeamRuntimeState, away: TeamRuntimeState) -> float:
        home_pressure = (home.strength.attack * 0.50) + (home.strength.midfield * 0.35) - (away.strength.defense * 0.18) + 4.5
        away_pressure = (away.strength.attack * 0.50) + (away.strength.midfield * 0.35) - (home.strength.defense * 0.18)
        total = max(1.0, home_pressure + away_pressure)
        return self._clamp(home_pressure / total, 0.30, 0.70)

    def _incident_minute(self, rng: Random, minimum: int, maximum: int) -> int:
        minute = int(round(rng.triangular(minimum, maximum, (minimum + maximum) / 2)))
        return self._clamp_minute(minute)

    def _chance_minute(self, rng: Random) -> int:
        minute = int(round(rng.triangular(2, 89, 52)))
        return self._clamp_minute(minute)

    def _process_yellow_card(
        self,
        *,
        match_id: str,
        event_counter,
        state: TeamRuntimeState,
        opponent: TeamRuntimeState,
        minute: int,
        player_stats: dict[str, PlayerMatchStats],
        rng: Random,
    ) -> MatchEvent | None:
        player = self._choose_card_candidate(state, rng)
        if player is None:
            return None
        if player.player_id in state.yellow_carded_ids and rng.random() < 0.45:
            state.stats.yellow_cards += 1
            player_stats[player.player_id].yellow_cards += 1
            return self._process_red_card(
                match_id=match_id,
                event_counter=event_counter,
                state=state,
                opponent=opponent,
                minute=minute,
                player_stats=player_stats,
                rng=rng,
                source="second_yellow",
                forced_player=player,
            )
        state.yellow_carded_ids.add(player.player_id)
        state.stats.yellow_cards += 1
        player_stats[player.player_id].yellow_cards += 1
        home_state, away_state = self._ordered_states(state, opponent)
        return self._make_event(
            match_id=match_id,
            event_counter=event_counter,
            event_type=MatchEventType.YELLOW_CARD,
            minute=minute,
            home_state=home_state,
            away_state=away_state,
            team_id=state.team_id,
            team_name=state.team_name,
            primary_player_id=player.player_id,
            primary_player_name=player.player_name,
        )

    def _process_red_card(
        self,
        *,
        match_id: str,
        event_counter,
        state: TeamRuntimeState,
        opponent: TeamRuntimeState,
        minute: int,
        player_stats: dict[str, PlayerMatchStats],
        rng: Random,
        source: str,
        forced_player: InternalPlayer | None = None,
    ) -> MatchEvent | None:
        player = forced_player or self._choose_red_card_candidate(state, rng)
        if player is None or player.player_id in state.red_carded_ids:
            return None
        state.red_carded_ids.add(player.player_id)
        state.remove_active_player(player.player_id)
        state.current_formation = state.tactics.red_card_fallback_formation
        state.current_shape = self._parse_formation(state.current_formation)
        state.stats.current_formation = state.current_formation
        state.shape_attack_adjustment, state.shape_defense_adjustment = self._shape_adjustment(state.starting_shape, state.current_shape)
        state.stats.red_cards += 1
        ledger = player_stats[player.player_id]
        ledger.red_card = True
        if ledger.substituted_out_minute is None:
            ledger.substituted_out_minute = minute
        home_state, away_state = self._ordered_states(state, opponent)
        return self._make_event(
            match_id=match_id,
            event_counter=event_counter,
            event_type=MatchEventType.RED_CARD,
            minute=minute,
            home_state=home_state,
            away_state=away_state,
            team_id=state.team_id,
            team_name=state.team_name,
            primary_player_id=player.player_id,
            primary_player_name=player.player_name,
            metadata={"source": source, "fallback_formation": state.current_formation},
        )

    def _process_injury(
        self,
        *,
        match_id: str,
        event_counter,
        state: TeamRuntimeState,
        opponent: TeamRuntimeState,
        minute: int,
        player_stats: dict[str, PlayerMatchStats],
        rng: Random,
    ) -> list[MatchEvent]:
        player = self._choose_injury_candidate(state, rng)
        if player is None:
            return []
        state.injured_ids.add(player.player_id)
        state.stats.injuries += 1
        state.remove_active_player(player.player_id)
        ledger = player_stats[player.player_id]
        ledger.injured = True
        if ledger.substituted_out_minute is None:
            ledger.substituted_out_minute = minute
        home_state, away_state = self._ordered_states(state, opponent)
        events = [
            self._make_event(
                match_id=match_id,
                event_counter=event_counter,
                event_type=MatchEventType.INJURY,
                minute=minute,
                home_state=home_state,
                away_state=away_state,
                team_id=state.team_id,
                team_name=state.team_name,
                primary_player_id=player.player_id,
                primary_player_name=player.player_name,
            )
        ]
        if state.tactics.injury_auto_substitution and state.substitutions_remaining() > 0 and state.bench_player_ids:
            replacement = self._select_replacement(state, preferred_roles=(player.role, PlayerRole.MIDFIELDER, PlayerRole.DEFENDER, PlayerRole.FORWARD))
            if replacement is not None:
                substitution = self._apply_substitution(
                    match_id=match_id,
                    event_counter=event_counter,
                    state=state,
                    opponent=opponent,
                    minute=minute,
                    outgoing_player=player,
                    incoming_player=replacement,
                    player_stats=player_stats,
                    reason="injury",
                )
                if substitution is not None:
                    events.append(substitution)
        return events

    def _process_substitution_window(
        self,
        *,
        match_id: str,
        event_counter,
        minute: int,
        state: TeamRuntimeState,
        opponent: TeamRuntimeState,
        player_stats: dict[str, PlayerMatchStats],
    ) -> list[MatchEvent]:
        if state.substitutions_remaining() <= 0 or not state.bench_player_ids:
            return []
        active_outfielders = state.active_outfielders()
        if not active_outfielders:
            return []

        outgoing: InternalPlayer | None = None
        incoming: InternalPlayer | None = None
        reason: str | None = None

        protected_players = [
            player
            for player in active_outfielders
            if player.player_id in state.yellow_carded_ids and player.role in state.tactics.yellow_card_replacement_roles
        ]
        if minute >= state.tactics.yellow_card_substitution_minute and protected_players:
            outgoing = min(protected_players, key=lambda player: (player.discipline, player.fitness, player.overall))
            incoming = self._select_replacement(state, preferred_roles=(outgoing.role, PlayerRole.DEFENDER, PlayerRole.MIDFIELDER, PlayerRole.FORWARD))
            reason = "yellow_card_protection"

        if outgoing is None or incoming is None:
            score_delta = state.stats.goals - opponent.stats.goals
            if score_delta < 0:
                outgoing = min(active_outfielders, key=lambda player: (player.attacking_value(), player.fitness))
                incoming = self._select_replacement(state, preferred_roles=(PlayerRole.FORWARD, PlayerRole.MIDFIELDER, outgoing.role))
                reason = "chasing_goal"
            elif score_delta > 0 and minute >= 70:
                defensive_candidates = [player for player in active_outfielders if player.role in {PlayerRole.FORWARD, PlayerRole.MIDFIELDER}]
                if defensive_candidates:
                    outgoing = min(defensive_candidates, key=lambda player: (player.defensive_value(), player.fitness))
                    incoming = self._select_replacement(state, preferred_roles=(PlayerRole.DEFENDER, PlayerRole.MIDFIELDER, outgoing.role))
                    reason = "protect_lead"
            elif minute >= 72:
                outgoing = min(active_outfielders, key=lambda player: (player.fitness, player.overall))
                incoming = self._select_replacement(
                    state,
                    preferred_roles=(outgoing.role, PlayerRole.MIDFIELDER, PlayerRole.FORWARD, PlayerRole.DEFENDER),
                )
                reason = "fresh_legs"

        if outgoing is None or incoming is None:
            return []
        substitution = self._apply_substitution(
            match_id=match_id,
            event_counter=event_counter,
            state=state,
            opponent=opponent,
            minute=minute,
            outgoing_player=outgoing,
            incoming_player=incoming,
            player_stats=player_stats,
            reason=reason or "tactical",
        )
        return [substitution] if substitution is not None else []

    def _process_chance(
        self,
        *,
        match_id: str,
        event_counter,
        attacking: TeamRuntimeState,
        defending: TeamRuntimeState,
        minute: int,
        player_stats: dict[str, PlayerMatchStats],
        rng: Random,
    ) -> MatchEvent | None:
        shooter = self._choose_shooter(attacking, rng)
        if shooter is None:
            return None
        keeper = defending.goalkeeper()
        attack_rating = self._live_attack_rating(attacking, defending, minute)
        defense_rating = self._live_defense_rating(defending, attacking, minute)
        chance_quality = self._clamp(
            0.34
            + ((attack_rating - defense_rating) / 220.0)
            + (0.05 if attacking.stats.goals < defending.stats.goals and minute >= 60 else 0.0)
            + rng.uniform(-0.05, 0.05),
            0.10,
            0.78,
        )
        attacking.stats.shots += 1
        on_target_probability = self._clamp(0.26 + (chance_quality * 0.35) + ((shooter.finishing - 60.0) / 250.0), 0.16, 0.82)
        goal_probability = self._clamp(
            0.10
            + (chance_quality * 0.40)
            + ((shooter.finishing - (keeper.goalkeeping_value() if keeper is not None else defending.strength.goalkeeping)) / 260.0),
            0.05,
            0.68,
        )
        home_state, away_state = self._ordered_states(attacking, defending)

        if rng.random() < on_target_probability:
            attacking.stats.shots_on_target += 1
            if rng.random() < goal_probability:
                attacking.stats.goals += 1
                player_stats[shooter.player_id].goals += 1
                assister = self._choose_assister(attacking, shooter, rng)
                if assister is not None:
                    player_stats[assister.player_id].assists += 1
                return self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.GOAL,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=attacking.team_id,
                    team_name=attacking.team_name,
                    primary_player_id=shooter.player_id,
                    primary_player_name=shooter.player_name,
                    secondary_player_id=assister.player_id if assister is not None else None,
                    secondary_player_name=assister.player_name if assister is not None else None,
                    metadata={"assisted": assister is not None},
                )
            defending.stats.saves += 1
            if keeper is not None:
                player_stats[keeper.player_id].saves += 1
            return self._make_event(
                match_id=match_id,
                event_counter=event_counter,
                event_type=MatchEventType.SAVE,
                minute=minute,
                home_state=home_state,
                away_state=away_state,
                team_id=defending.team_id,
                team_name=defending.team_name,
                primary_player_id=keeper.player_id if keeper is not None else None,
                primary_player_name=keeper.player_name if keeper is not None else None,
                secondary_player_id=shooter.player_id,
                secondary_player_name=shooter.player_name,
                metadata={"chance_quality": round(chance_quality, 2)},
            )

        attacking.stats.missed_chances += 1
        player_stats[shooter.player_id].missed_chances += 1
        return self._make_event(
            match_id=match_id,
            event_counter=event_counter,
            event_type=MatchEventType.MISSED_CHANCE,
            minute=minute,
            home_state=home_state,
            away_state=away_state,
            team_id=attacking.team_id,
            team_name=attacking.team_name,
            primary_player_id=shooter.player_id,
            primary_player_name=shooter.player_name,
            metadata={"chance_quality": round(chance_quality, 2)},
        )

    def _apply_substitution(
        self,
        *,
        match_id: str,
        event_counter,
        state: TeamRuntimeState,
        opponent: TeamRuntimeState,
        minute: int,
        outgoing_player: InternalPlayer,
        incoming_player: InternalPlayer,
        player_stats: dict[str, PlayerMatchStats],
        reason: str,
    ) -> MatchEvent | None:
        if incoming_player.player_id not in state.bench_player_ids:
            return None
        if outgoing_player.player_id not in state.active_player_ids and reason != "injury":
            return None
        state.remove_active_player(outgoing_player.player_id)
        state.bench_player_ids.remove(incoming_player.player_id)
        state.add_active_player(incoming_player.player_id)
        state.substitutions_used += 1
        state.stats.substitutions += 1
        player_stats[outgoing_player.player_id].substituted_out_minute = minute
        player_stats[incoming_player.player_id].substituted_in_minute = minute
        home_state, away_state = self._ordered_states(state, opponent)
        return self._make_event(
            match_id=match_id,
            event_counter=event_counter,
            event_type=MatchEventType.SUBSTITUTION,
            minute=minute,
            home_state=home_state,
            away_state=away_state,
            team_id=state.team_id,
            team_name=state.team_name,
            primary_player_id=incoming_player.player_id,
            primary_player_name=incoming_player.player_name,
            secondary_player_id=outgoing_player.player_id,
            secondary_player_name=outgoing_player.player_name,
            metadata={
                "reason": reason,
                "outgoing_role": outgoing_player.role.value,
                "incoming_role": incoming_player.role.value,
            },
        )

    def _live_attack_rating(self, team: TeamRuntimeState, opponent: TeamRuntimeState, minute: int) -> float:
        score_delta = team.stats.goals - opponent.stats.goals
        style_modifier = {
            "attacking": 1.05,
            "balanced": 1.00,
            "defensive": 0.95,
        }[team.tactics.style.value]
        urgency = 1.0 + (0.05 * abs(score_delta)) if score_delta < 0 and minute >= 60 else 1.0
        game_management = 0.96 if score_delta > 0 and minute >= 75 else 1.0
        red_penalty = 1.0 - (0.15 * len(team.red_carded_ids))
        return team.strength.attack * style_modifier * urgency * game_management * red_penalty * (1.0 + team.shape_attack_adjustment)

    def _live_defense_rating(self, team: TeamRuntimeState, opponent: TeamRuntimeState, minute: int) -> float:
        score_delta = team.stats.goals - opponent.stats.goals
        style_modifier = {
            "attacking": 0.95,
            "balanced": 1.00,
            "defensive": 1.06,
        }[team.tactics.style.value]
        protect_lead = 1.04 if score_delta > 0 and minute >= 75 else 1.0
        red_penalty = 1.0 - (0.10 * len(team.red_carded_ids))
        return team.strength.defense * style_modifier * protect_lead * red_penalty * (1.0 + team.shape_defense_adjustment)

    def _choose_card_candidate(self, state: TeamRuntimeState, rng: Random) -> InternalPlayer | None:
        candidates = [player for player in state.active_outfielders() if player.player_id not in state.red_carded_ids]
        return self._weighted_choice(
            candidates,
            [max(1.0, (110.0 - player.discipline) + (state.tactics.aggression * 0.3) + (10.0 if player.role in {PlayerRole.DEFENDER, PlayerRole.MIDFIELDER} else 0.0)) for player in candidates],
            rng,
        )

    def _choose_red_card_candidate(self, state: TeamRuntimeState, rng: Random) -> InternalPlayer | None:
        candidates = [player for player in state.active_outfielders() if player.player_id not in state.red_carded_ids]
        return self._weighted_choice(
            candidates,
            [
                max(
                    1.0,
                    (120.0 - player.discipline)
                    + (state.tactics.aggression * 0.4)
                    + (18.0 if player.player_id in state.yellow_carded_ids else 0.0),
                )
                for player in candidates
            ],
            rng,
        )

    def _choose_injury_candidate(self, state: TeamRuntimeState, rng: Random) -> InternalPlayer | None:
        candidates = [player for player in state.active_outfielders() if player.player_id not in state.injured_ids]
        return self._weighted_choice(
            candidates,
            [max(1.0, (120.0 - player.fitness) + (state.tactics.tempo * 0.2) + (8.0 if player.role in {PlayerRole.FORWARD, PlayerRole.MIDFIELDER} else 0.0)) for player in candidates],
            rng,
        )

    def _choose_shooter(self, state: TeamRuntimeState, rng: Random) -> InternalPlayer | None:
        candidates = state.active_outfielders()
        return self._weighted_choice(
            candidates,
            [
                max(
                    1.0,
                    player.attacking_value()
                    + (12.0 if player.role is PlayerRole.FORWARD else 0.0)
                    + (6.0 if state.tactics.style.value == "attacking" and player.role is PlayerRole.FORWARD else 0.0),
                )
                for player in candidates
            ],
            rng,
        )

    def _choose_assister(self, state: TeamRuntimeState, shooter: InternalPlayer, rng: Random) -> InternalPlayer | None:
        if rng.random() > (0.78 if state.tactics.style.value != "defensive" else 0.62):
            return None
        candidates = [player for player in state.active_outfielders() if player.player_id != shooter.player_id]
        return self._weighted_choice(
            candidates,
            [max(1.0, player.control_value() + (8.0 if player.role is PlayerRole.MIDFIELDER else 0.0)) for player in candidates],
            rng,
        )

    def _select_replacement(self, state: TeamRuntimeState, *, preferred_roles: tuple[PlayerRole, ...]) -> InternalPlayer | None:
        candidates = state.available_bench(preferred_roles) or state.available_bench()
        if not candidates:
            return None
        return max(candidates, key=lambda player: (player.overall, player.fitness, player.attacking_value() + player.defensive_value()))

    def _resolve_possession(self, home: TeamRuntimeState, away: TeamRuntimeState) -> None:
        possession = 50.0
        possession += (home.strength.midfield - away.strength.midfield) * 0.28
        possession += (home.tactics.tempo - away.tactics.tempo) * 0.06
        possession += (home.tactics.pressing - away.tactics.pressing) * 0.04
        possession += (len(away.red_carded_ids) - len(home.red_carded_ids)) * 6.0
        possession += 2.0
        home.stats.possession = int(round(self._clamp(possession, 32.0, 68.0)))
        away.stats.possession = 100 - home.stats.possession

    def _finalize_player_minutes(self, player_stats: dict[str, PlayerMatchStats]) -> None:
        for ledger in player_stats.values():
            if not ledger.started and ledger.substituted_in_minute is None:
                ledger.minutes_played = 0
                continue
            start_minute = 0 if ledger.started else ledger.substituted_in_minute or 0
            end_minute = ledger.substituted_out_minute if ledger.substituted_out_minute is not None else 90
            ledger.minutes_played = max(0, min(90, end_minute) - min(90, start_minute))

    def _resolve_winner(self, home: TeamRuntimeState, away: TeamRuntimeState, shootout) -> tuple[str | None, str | None]:
        if shootout is not None:
            return shootout.winner_team_id, shootout.winner_team_name
        if home.stats.goals > away.stats.goals:
            return home.team_id, home.team_name
        if away.stats.goals > home.stats.goals:
            return away.team_id, away.team_name
        return None, None

    def _resolve_upset(self, home: TeamRuntimeState, away: TeamRuntimeState, winner_team_id: str | None) -> bool:
        if winner_team_id is None:
            return False
        favorite = home if home.strength.overall >= away.strength.overall else away
        underdog = away if favorite is home else home
        return winner_team_id == underdog.team_id and abs(home.strength.overall - away.strength.overall) >= 6.0

    def _build_summary_line(self, home: TeamRuntimeState, away: TeamRuntimeState, shootout) -> str:
        if shootout is None:
            return f"{home.team_name} {home.stats.goals}-{away.stats.goals} {away.team_name}"
        return f"{home.team_name} {home.stats.goals}-{away.stats.goals} {away.team_name} ({shootout.home_penalties}-{shootout.away_penalties} pens)"

    def _make_event(
        self,
        *,
        match_id: str,
        event_counter,
        event_type: MatchEventType,
        minute: int,
        home_state: TeamRuntimeState,
        away_state: TeamRuntimeState,
        team_id: str | None = None,
        team_name: str | None = None,
        primary_player_id: str | None = None,
        primary_player_name: str | None = None,
        secondary_player_id: str | None = None,
        secondary_player_name: str | None = None,
        added_time: int = 0,
        metadata: dict[str, str | int | float | bool | None] | None = None,
    ) -> MatchEvent:
        sequence = next(event_counter)
        return MatchEvent(
            event_id=f"{match_id}:{sequence:03d}",
            sequence=sequence,
            event_type=event_type,
            minute=minute,
            added_time=added_time,
            team_id=team_id,
            team_name=team_name,
            primary_player_id=primary_player_id,
            primary_player_name=primary_player_name,
            secondary_player_id=secondary_player_id,
            secondary_player_name=secondary_player_name,
            home_score=home_state.stats.goals,
            away_score=away_state.stats.goals,
            metadata=metadata or {},
        )

    def _resolve_seed(self, request: MatchSimulationRequest) -> int:
        if request.seed is not None:
            return request.seed
        seed_material = f"{request.match_id}:{request.home_team.team_id}:{request.away_team.team_id}:{request.competition.stage}"
        return int(sha256(seed_material.encode("utf-8")).hexdigest()[:12], 16)

    def _resolve_requires_winner(self, request: MatchSimulationRequest) -> bool:
        if request.competition.requires_winner is not None:
            return request.competition.requires_winner
        return request.competition.competition_type is MatchCompetitionType.CUP or request.competition.is_final

    def _state_for_side(self, side: str | None, home: TeamRuntimeState, away: TeamRuntimeState) -> TeamRuntimeState:
        return home if side == "home" else away

    def _opponent_for_side(self, side: str | None, home: TeamRuntimeState, away: TeamRuntimeState) -> TeamRuntimeState:
        return away if side == "home" else home

    def _ordered_states(self, state: TeamRuntimeState, opponent: TeamRuntimeState) -> tuple[TeamRuntimeState, TeamRuntimeState]:
        return (state, opponent) if state.is_home else (opponent, state)

    def _shape_adjustment(self, starting_shape: tuple[int, ...], current_shape: tuple[int, ...]) -> tuple[float, float]:
        start_defenders, start_midfielders, start_forwards = self._formation_profile(starting_shape)
        current_defenders, current_midfielders, current_forwards = self._formation_profile(current_shape)
        attack_adjustment = ((current_forwards - start_forwards) * 0.05) + ((current_midfielders - start_midfielders) * 0.02)
        defense_adjustment = ((current_defenders - start_defenders) * 0.05) + ((current_midfielders - start_midfielders) * 0.01)
        return attack_adjustment, defense_adjustment

    def _formation_profile(self, shape: tuple[int, ...]) -> tuple[int, int, int]:
        return shape[0], sum(shape[1:-1]), shape[-1]

    def _parse_formation(self, formation: str) -> tuple[int, ...]:
        return tuple(int(part) for part in formation.split("-"))

    def _weighted_choice(self, items: list[InternalPlayer], weights: list[float], rng: Random) -> InternalPlayer | None:
        if not items:
            return None
        total_weight = sum(max(0.0, weight) for weight in weights)
        if total_weight <= 0.0:
            return items[0]
        threshold = rng.random() * total_weight
        running_total = 0.0
        for item, weight in zip(items, weights, strict=True):
            running_total += max(0.0, weight)
            if running_total >= threshold:
                return item
        return items[-1]

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _clamp_minute(self, minute: int) -> int:
        if minute == 45:
            return 44
        return max(1, min(89, minute))
