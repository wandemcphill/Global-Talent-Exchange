from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from itertools import count
from random import Random

from app.common.enums.match_status import MatchStatus
from app.match_engine.schemas import MatchKitIdentityInput, MatchSimulationRequest, MatchTeamIdentityInput
from app.match_engine.simulation.models import (
    BadgeVisualIdentity,
    InternalPlayer,
    KitVisualIdentity,
    MatchCompetitionType,
    MatchEvent,
    MatchEventType,
    MatchTeamProfile,
    MatchVisualIdentityPayload,
    PlayerMatchStats,
    PlayerRole,
    PlayerVisualIdentity,
    SimulationResult,
    TacticalPlan,
    TeamMatchStats,
    TeamRuntimeState,
    TeamVisualIdentity,
)
from app.match_engine.simulation.penalties import PenaltyShootoutGenerator
from app.match_engine.simulation.strength import DefaultTeamStrengthCalculator, TeamStrengthCalculator


@dataclass(frozen=True, slots=True)
class ScheduledItem:
    minute: int
    priority: int
    kind: str
    team_side: str | None
    index: int
    payload: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class MatchNarrativeContext:
    favorite_side: str
    upset_probability: float
    stage_pressure: float
    rivalry_intensity: float
    home_advantage_note: str
    clash_resolved: bool


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
        seed = self._resolve_seed(request)
        rng = Random(seed)
        requires_winner = self._resolve_requires_winner(request)
        home_profile = self._build_team_profile(request.home_team)
        away_profile = self._build_team_profile(request.away_team)
        home_strength = self.strength_calculator.calculate(home_profile, is_home=True)
        away_strength = self.strength_calculator.calculate(away_profile, is_home=False)
        home_visual, away_visual, clash_resolved = self._resolve_visual_identities(home_profile.visual_identity, away_profile.visual_identity)
        home_state = self._build_runtime_state(home_profile, home_strength, is_home=True, visual_identity=home_visual)
        away_state = self._build_runtime_state(away_profile, away_strength, is_home=False, visual_identity=away_visual)
        narrative = self._prepare_match_context(request, home_state, away_state, clash_resolved=clash_resolved)
        player_stats = self._initialize_player_stats(home_state, away_state)
        events: list[MatchEvent] = []
        event_counter = count(1)
        events.append(self._make_event(match_id=request.match_id, event_counter=event_counter, event_type=MatchEventType.KICKOFF, minute=0, home_state=home_state, away_state=away_state, metadata={"stage": request.competition.stage, "upset_probability": round(narrative.upset_probability, 3)}))
        schedule = self._build_schedule(home_state, away_state, rng, is_final=request.competition.is_final, narrative=narrative)
        schedule = self._merge_tactical_changes(schedule, request, home_state, away_state)
        halftime_added = False
        for item in schedule:
            if not halftime_added and item.minute >= 45:
                halftime_added = True
                self._apply_halftime_reset(home_state, away_state)
                events.append(self._make_event(match_id=request.match_id, event_counter=event_counter, event_type=MatchEventType.HALFTIME, minute=45, home_state=home_state, away_state=away_state))
            state = home_state if item.team_side == "home" else away_state
            opponent = away_state if item.team_side == "home" else home_state
            if item.kind == "yellow":
                event = self._process_yellow_card(match_id=request.match_id, event_counter=event_counter, state=state, opponent=opponent, minute=item.minute, player_stats=player_stats, rng=rng)
                if event is not None:
                    events.append(event)
            elif item.kind == "red":
                event = self._process_red_card(match_id=request.match_id, event_counter=event_counter, state=state, opponent=opponent, minute=item.minute, player_stats=player_stats, rng=rng, source="straight_red")
                if event is not None:
                    events.append(event)
            elif item.kind == "tactical_change":
                event = self._apply_tactical_change(
                    match_id=request.match_id,
                    event_counter=event_counter,
                    state=state,
                    opponent=opponent,
                    minute=item.minute,
                    payload=item.payload or {},
                )
                if event is not None:
                    events.append(event)
            elif item.kind == "tactical_substitution":
                events.extend(
                    self._apply_tactical_substitution(
                        match_id=request.match_id,
                        event_counter=event_counter,
                        state=state,
                        opponent=opponent,
                        minute=item.minute,
                        payload=item.payload or {},
                        player_stats=player_stats,
                    )
                )
            elif item.kind == "injury":
                events.extend(self._process_injury(match_id=request.match_id, event_counter=event_counter, state=state, opponent=opponent, minute=item.minute, player_stats=player_stats, rng=rng))
            elif item.kind == "tactical":
                event = self._process_tactical_swing(match_id=request.match_id, event_counter=event_counter, state=state, opponent=opponent, minute=item.minute, rng=rng)
                if event is not None:
                    events.append(event)
            elif item.kind == "foul":
                event = self._process_tactical_foul(match_id=request.match_id, event_counter=event_counter, state=state, opponent=opponent, minute=item.minute, rng=rng)
                if event is not None:
                    events.append(event)
            elif item.kind == "fatigue":
                event = self._process_fatigue_event(match_id=request.match_id, event_counter=event_counter, state=state, opponent=opponent, minute=item.minute)
                if event is not None:
                    events.append(event)
            elif item.kind == "chance":
                events.extend(
                    self._process_chance(
                        match_id=request.match_id,
                        event_counter=event_counter,
                        attacking=state,
                        defending=opponent,
                        minute=item.minute,
                        player_stats=player_stats,
                        rng=rng,
                        narrative=narrative,
                    )
                )
            elif item.kind == "window":
                events.extend(self._process_substitution_window(match_id=request.match_id, event_counter=event_counter, minute=item.minute, state=home_state, opponent=away_state, player_stats=player_stats))
                events.extend(self._process_substitution_window(match_id=request.match_id, event_counter=event_counter, minute=item.minute, state=away_state, opponent=home_state, player_stats=player_stats))
        if not halftime_added:
            self._apply_halftime_reset(home_state, away_state)
            events.append(self._make_event(match_id=request.match_id, event_counter=event_counter, event_type=MatchEventType.HALFTIME, minute=45, home_state=home_state, away_state=away_state))
        events.append(self._make_event(match_id=request.match_id, event_counter=event_counter, event_type=MatchEventType.FULLTIME, minute=90, home_state=home_state, away_state=away_state, metadata={"goes_to_penalties": bool(requires_winner and home_state.stats.goals == away_state.stats.goals)}))
        shootout = None
        if requires_winner and home_state.stats.goals == away_state.stats.goals:
            shootout = self.penalty_generator.generate(home_state, away_state, rng)
            for offset, attempt in enumerate(shootout.attempts, start=1):
                events.append(self._make_event(match_id=request.match_id, event_counter=event_counter, event_type=MatchEventType.PENALTY_GOAL if attempt.scored else MatchEventType.PENALTY_MISS, minute=90 + offset, home_state=home_state, away_state=away_state, team_id=attempt.team_id, team_name=attempt.team_name, primary_player_id=attempt.taker_id, primary_player_name=attempt.taker_name, secondary_player_id=attempt.goalkeeper_id, secondary_player_name=attempt.goalkeeper_name, metadata={"shootout_round": attempt.order, "home_penalties": attempt.home_penalties, "away_penalties": attempt.away_penalties, "importance": 5, "pressure_level": "shootout"}))
        self._resolve_possession(home_state, away_state)
        self._finalize_player_minutes(player_stats)
        winner_team_id, winner_team_name = self._resolve_winner(home_state, away_state, shootout)
        upset = self._resolve_upset(home_state, away_state, winner_team_id)
        ordered_player_stats = tuple(sorted(player_stats.values(), key=lambda line: (line.team_id, -line.goals, -line.assists, -line.saves, -line.missed_chances, line.player_name)))
        return SimulationResult(
            match_id=request.match_id,
            seed=seed,
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
            upset_probability=narrative.upset_probability,
            upset_reason_codes=self._upset_reason_codes(upset=upset, winner_team_id=winner_team_id, home_state=home_state, away_state=away_state, events=events),
            home_advantage_note=narrative.home_advantage_note,
            summary_line=self._build_summary_line(home_state, away_state, shootout, upset=upset),
            home_strength=home_state.strength,
            away_strength=away_state.strength,
            home_stats=home_state.stats,
            away_stats=away_state.stats,
            player_stats=ordered_player_stats,
            events=tuple(events),
            manager_influence_notes=self._manager_influence_notes(home_state, away_state, events),
            tactical_battle_summary=self._tactical_battle_summary(home_state, away_state),
            form_motivation_summary=self._form_motivation_summary(home_state, away_state),
            momentum_swings=self._momentum_swings(events),
            turning_points=self._turning_points(events),
            key_matchups=self._key_matchups(ordered_player_stats),
            tactical_impact_notes=self._tactical_impact_notes(events),
            visual_identity=MatchVisualIdentityPayload(home_team=home_state.visual_identity, away_team=away_state.visual_identity, clash_resolved=narrative.clash_resolved),
            shootout=shootout,
        )

    def _build_team_profile(self, team) -> MatchTeamProfile:
        starters = tuple(self._build_player(player) for player in team.starters)
        bench = tuple(self._build_player(player) for player in team.bench)
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
                defensive_line=team.tactics.defensive_line,
                width=team.tactics.width,
                mentality=team.tactics.mentality,
                set_piece_emphasis=team.tactics.set_piece_emphasis,
                player_instructions=team.tactics.player_instructions,
                game_state_adjustments=team.tactics.game_state_adjustments,
                tactical_quality=team.tactics.tactical_quality,
                adaptability=team.tactics.adaptability,
                game_management=team.tactics.game_management,
            ),
            manager_profile=team.manager_profile,
            club_context=team.club_context.model_dump(mode="python") if team.club_context is not None else None,
            visual_identity=self._team_visual_identity(team, starters, bench),
            starters=starters,
            bench=bench,
        )

    def _build_player(self, player) -> InternalPlayer:
        role_bias = {PlayerRole.GOALKEEPER: (-18, 3, 4, 7, -24, 6, 0), PlayerRole.DEFENDER: (-2, 1, 2, 6, -7, 5, 0), PlayerRole.MIDFIELDER: (0, 4, 6, 3, 4, -6, 7), PlayerRole.FORWARD: (6, 5, 1, 4, 8, -2, 3)}[player.role]
        pace, composure, decision, positioning, off_ball, aerial, technique = role_bias
        return InternalPlayer(player_id=player.player_id, player_name=player.player_name, role=player.role, overall=player.overall, finishing=player.finishing, creativity=player.creativity, defending=player.defending, goalkeeping=player.goalkeeping, discipline=player.discipline, fitness=player.fitness, shirt_number=player.shirt_number, display_name=player.display_name, position_archetype=player.position_archetype, pace=self._resolve_rating(player.pace, player.overall + pace), composure=self._resolve_rating(player.composure, player.overall + composure), decision_making=self._resolve_rating(player.decision_making, player.overall + decision), positioning=self._resolve_rating(player.positioning, player.overall + positioning), off_ball_movement=self._resolve_rating(player.off_ball_movement, player.overall + off_ball), aerial_ability=self._resolve_rating(player.aerial_ability, player.overall + aerial), technique=self._resolve_rating(player.technique, player.creativity + technique), stamina_curve=self._resolve_rating(player.stamina_curve, player.fitness - 2), consistency=self._resolve_rating(player.consistency, player.overall + 1), clutch_factor=self._resolve_rating(player.clutch_factor, player.finishing if player.role is PlayerRole.FORWARD else player.overall), big_match_temperament=self._resolve_rating(player.big_match_temperament, player.overall), recent_form=self._resolve_rating(player.recent_form, player.overall), morale=self._resolve_rating(player.morale, 60), motivation=self._resolve_rating(player.motivation, 60), fatigue_load=max(0, min(100, player.fatigue_load if player.fatigue_load is not None else 36)), injury_risk=max(0, min(100, player.injury_risk if player.injury_risk is not None else 20)), leadership=self._resolve_rating(player.leadership, player.overall))

    def _team_visual_identity(self, team, starters: tuple[InternalPlayer, ...], bench: tuple[InternalPlayer, ...]) -> TeamVisualIdentity:
        identity = team.identity or MatchTeamIdentityInput(club_name=team.team_name, short_club_code=team.team_name[:3].upper())
        short_code = (identity.national_team_code or identity.short_club_code or team.team_name[:3]).upper()
        home_kit = identity.home_kit or MatchKitIdentityInput(front_text=short_code)
        away_kit = identity.away_kit or MatchKitIdentityInput(
            kit_type="away",
            primary_color="#F5F7FA",
            secondary_color="#123C73",
            accent_color="#E2A400",
            shorts_color="#F5F7FA",
            socks_color="#123C73",
            pattern_type="sash",
            collar_style="v_neck",
            sleeve_style="raglan",
            badge_placement="left_chest",
            front_text=short_code,
        )
        third_kit = identity.third_kit or MatchKitIdentityInput(
            kit_type="third",
            primary_color=identity.badge_accent_color,
            secondary_color=identity.badge_secondary_color,
            accent_color=identity.badge_primary_color,
            shorts_color=identity.badge_accent_color,
            socks_color=identity.badge_secondary_color,
            pattern_type="stripe",
            collar_style="crew",
            sleeve_style="short",
            badge_placement="left_chest",
            front_text=short_code,
        )
        goalkeeper_kit = identity.goalkeeper_kit or MatchKitIdentityInput(
            kit_type="goalkeeper",
            primary_color="#1F2937",
            secondary_color="#A7F3D0",
            accent_color="#F9FAFB",
            shorts_color="#111827",
            socks_color="#A7F3D0",
            pattern_type="chevron",
            collar_style="crew",
            sleeve_style="long",
            badge_placement="left_chest",
            front_text=f"{short_code or 'GK'}",
        )
        players = tuple(
            PlayerVisualIdentity(
                player_id=player.player_id,
                display_name=player.display_name or player.player_name,
                shirt_name=player.shirt_name(),
                shirt_number=player.shirt_number,
                role=player.role,
            )
            for player in (*starters, *bench)
        )
        return TeamVisualIdentity(
            team_id=team.team_id,
            team_name=identity.club_name or team.team_name,
            short_club_code=short_code,
            badge=BadgeVisualIdentity(
                badge_url=identity.badge_url,
                shape=identity.badge_shape,
                initials=identity.badge_initials,
                primary_color=identity.badge_primary_color,
                secondary_color=identity.badge_secondary_color,
                accent_color=identity.badge_accent_color,
            ),
            selected_kit=self._kit_visual(home_kit),
            alternate_kit=self._kit_visual(away_kit),
            third_kit=self._kit_visual(third_kit),
            goalkeeper_kit=self._kit_visual(goalkeeper_kit),
            player_visuals=players,
        )

    def _kit_visual(self, kit: MatchKitIdentityInput) -> KitVisualIdentity:
        return KitVisualIdentity(kit_type=kit.kit_type, primary_color=kit.primary_color, secondary_color=kit.secondary_color, accent_color=kit.accent_color, shorts_color=kit.shorts_color, socks_color=kit.socks_color, pattern_type=kit.pattern_type, collar_style=kit.collar_style, sleeve_style=kit.sleeve_style, badge_placement=kit.badge_placement, front_text=kit.front_text)

    def _resolve_visual_identities(self, home: TeamVisualIdentity | None, away: TeamVisualIdentity | None) -> tuple[TeamVisualIdentity, TeamVisualIdentity, bool]:
        if home is None or away is None:
            raise ValueError("Match visual identity must be available for both teams.")
        clash = self._kits_clash(home.selected_kit, away.selected_kit)
        if not clash:
            return home, away, False
        adjusted = replace(away, selected_kit=away.alternate_kit, clash_adjusted=True)
        if self._kits_clash(home.selected_kit, adjusted.selected_kit) and away.third_kit is not None:
            adjusted = replace(adjusted, selected_kit=away.third_kit)
        if self._kits_clash(home.selected_kit, adjusted.selected_kit):
            adjusted = replace(
                adjusted,
                selected_kit=replace(adjusted.selected_kit, primary_color="#F7FAFC", secondary_color="#111827"),
            )
        return home, adjusted, True

    def _build_runtime_state(self, team: MatchTeamProfile, strength, *, is_home: bool, visual_identity: TeamVisualIdentity) -> TeamRuntimeState:
        players = {player.player_id: player for player in [*team.starters, *team.bench]}
        shape = tuple(int(part) for part in team.formation.split("-"))
        return TeamRuntimeState(team_id=team.team_id, team_name=team.team_name, is_home=is_home, starting_formation=team.formation, current_formation=team.formation, starting_shape=shape, current_shape=shape, tactics=team.tactics, strength=strength, players_by_id=players, active_player_ids=[player.player_id for player in team.starters], bench_player_ids=[player.player_id for player in team.bench], stats=TeamMatchStats(team_id=team.team_id, team_name=team.team_name, started_formation=team.formation, current_formation=team.formation), visual_identity=visual_identity, dynamic_morale=strength.morale, dynamic_motivation=strength.motivation, fatigue_level=strength.fatigue_load)

    def _prepare_match_context(self, request: MatchSimulationRequest, home: TeamRuntimeState, away: TeamRuntimeState, *, clash_resolved: bool) -> MatchNarrativeContext:
        favorite_side = "home" if home.strength.overall >= away.strength.overall else "away"
        stage_pressure = 0.34 if request.competition.competition_type is MatchCompetitionType.LEAGUE else 0.46
        if request.competition.is_final:
            stage_pressure += 0.18
        rivalry = self._infer_rivalry(home.team_name, away.team_name)
        home.home_advantage_score = self._clamp(2.2 + (home.strength.chemistry - 60.0) * 0.04 + (home.strength.morale - away.strength.morale) * 0.04 + stage_pressure * 3.2 + rivalry * 1.8 + max(0.0, (away.strength.fatigue_load - home.strength.fatigue_load) * 0.03), 1.0, 7.4)
        home.tactical_mismatch_edge = self._tactical_mismatch(home, away)
        away.tactical_mismatch_edge = self._tactical_mismatch(away, home)
        underdog = away if favorite_side == "home" else home
        favorite = home if favorite_side == "home" else away
        upset_probability = self._clamp(0.06 + (abs(home.strength.overall - away.strength.overall) * 0.006) + ((underdog.strength.upset_punch - favorite.strength.upset_resistance) * 0.006) + (underdog.tactical_mismatch_edge * 0.012) + (0.012 if underdog.is_home else 0.0), 0.04, 0.28)
        underdog.upset_potential = self._clamp(underdog.strength.upset_punch * 0.10, 0.0, 12.0)
        favorite.upset_potential = self._clamp(abs(home.strength.overall - away.strength.overall) * 0.20, 0.0, 8.0)
        note = "Home support, venue familiarity, and the late push slightly favored the hosts." if home.home_advantage_score >= 4.6 else "Home advantage was present but kept within a realistic range."
        return MatchNarrativeContext(favorite_side=favorite_side, upset_probability=round(upset_probability, 3), stage_pressure=stage_pressure, rivalry_intensity=rivalry, home_advantage_note=note, clash_resolved=clash_resolved)

    def _build_schedule(self, home: TeamRuntimeState, away: TeamRuntimeState, rng: Random, *, is_final: bool, narrative: MatchNarrativeContext) -> list[ScheduledItem]:
        items: list[ScheduledItem] = []
        index = 0
        for state, side in ((home, "home"), (away, "away")):
            for _ in range(self._yellow_card_count(state, rng, narrative=narrative)):
                index += 1
                items.append(ScheduledItem(minute=self._incident_minute(rng, 12, 88), priority=10, kind="yellow", team_side=side, index=index))
            for _ in range(self._red_card_count(state, rng, narrative=narrative)):
                index += 1
                items.append(ScheduledItem(minute=self._incident_minute(rng, 24, 84), priority=11, kind="red", team_side=side, index=index))
            for _ in range(self._injury_count(state, rng)):
                index += 1
                items.append(ScheduledItem(minute=self._incident_minute(rng, 18, 84), priority=12, kind="injury", team_side=side, index=index))
            for _ in range(self._tactical_foul_count(state, rng, narrative=narrative)):
                index += 1
                items.append(ScheduledItem(minute=self._incident_minute(rng, 14, 88), priority=13, kind="foul", team_side=side, index=index))
            for _ in range(self._fatigue_event_count(state, rng)):
                index += 1
                items.append(ScheduledItem(minute=self._incident_minute(rng, 52, 86), priority=14, kind="fatigue", team_side=side, index=index))
            if state.strength.tactical_quality >= 62 or state.strength.adaptability >= 64:
                index += 1
                items.append(ScheduledItem(minute=self._incident_minute(rng, 54, 80), priority=18, kind="tactical", team_side=side, index=index))
        total_chances = self._chance_count(home, away, rng, is_final=is_final, narrative=narrative)
        home_share = self._chance_share(home, away)
        for _ in range(total_chances):
            index += 1
            items.append(ScheduledItem(minute=self._chance_minute(rng), priority=20, kind="chance", team_side="home" if rng.random() < home_share else "away", index=index))
        for window in sorted(set(home.tactics.substitution_windows) | set(away.tactics.substitution_windows)):
            index += 1
            items.append(ScheduledItem(minute=window, priority=30, kind="window", team_side=None, index=index))
        return sorted(items, key=lambda item: (item.minute, item.priority, item.index))

    def _merge_tactical_changes(
        self,
        schedule: list[ScheduledItem],
        request: MatchSimulationRequest,
        home: TeamRuntimeState,
        away: TeamRuntimeState,
    ) -> list[ScheduledItem]:
        if not request.tactical_changes:
            return schedule
        items = list(schedule)
        index = max((item.index for item in schedule), default=0)
        for change in sorted(request.tactical_changes, key=lambda entry: (entry.requested_minute, entry.requested_second)):
            if change.team_id == home.team_id:
                team_side = "home"
            elif change.team_id == away.team_id:
                team_side = "away"
            else:
                continue
            change_id = change.change_id or f"{request.match_id}:{change.team_id}:{change.requested_minute}:{change.requested_second}:{index + 1}"
            urgency = (change.urgency or "normal").lower()
            if change.adjustment is not None:
                index += 1
                apply_minute = self._safe_checkpoint_minute(change.requested_minute)
                items.append(
                    ScheduledItem(
                        minute=apply_minute,
                        priority=16,
                        kind="tactical_change",
                        team_side=team_side,
                        index=index,
                        payload={
                            "change_id": change_id,
                            "urgency": urgency,
                            "requested_minute": change.requested_minute,
                            "requested_second": change.requested_second,
                            "adjustment": change.adjustment,
                            "notes": change.notes,
                        },
                    )
                )
            if change.substitution is not None:
                delay = 0 if urgency in {"urgent", "injury", "red_card"} else 1
                index += 1
                apply_minute = self._safe_checkpoint_minute(change.requested_minute + delay)
                items.append(
                    ScheduledItem(
                        minute=apply_minute,
                        priority=17,
                        kind="tactical_substitution",
                        team_side=team_side,
                        index=index,
                        payload={
                            "change_id": change_id,
                            "urgency": urgency,
                            "requested_minute": change.requested_minute,
                            "requested_second": change.requested_second,
                            "substitution": change.substitution,
                        },
                    )
                )
        return sorted(items, key=lambda item: (item.minute, item.priority, item.index))

    def _yellow_card_count(self, state: TeamRuntimeState, rng: Random, *, narrative: MatchNarrativeContext) -> int:
        base = ((100.0 - state.strength.discipline) / 24.0) + (state.tactics.aggression / 62.0) + ((state.dynamic_motivation - 60.0) / 48.0) + (narrative.rivalry_intensity * 0.8) - 0.8
        return min(max(0, int(base) + int(rng.random() < (base % 1 if base > 0 else 0.0))), 5)

    def _red_card_count(self, state: TeamRuntimeState, rng: Random, *, narrative: MatchNarrativeContext) -> int:
        risk = max(0.0, ((state.tactics.aggression - 72.0) / 30.0) + ((44.0 - state.strength.discipline) / 28.0) + ((state.fatigue_level - 46.0) / 65.0) + (narrative.rivalry_intensity * 0.18))
        return 0 if risk <= 0 else int(rng.random() < min(0.72, 0.12 + (risk * 0.22)))

    def _injury_count(self, state: TeamRuntimeState, rng: Random) -> int:
        risk = max(0.0, ((state.fatigue_level - 36.0) / 25.0) + ((state.tactics.tempo - 55.0) / 70.0) + ((state.tactics.pressing - 55.0) / 85.0))
        return min(int(rng.random() < min(0.78, 0.10 + (risk * 0.24))) if risk > 0 else 0, 2)

    def _tactical_foul_count(self, state: TeamRuntimeState, rng: Random, *, narrative: MatchNarrativeContext) -> int:
        risk = max(
            0.0,
            ((state.tactics.aggression - 55.0) / 38.0)
            + ((60.0 - state.strength.discipline) / 60.0)
            + (narrative.rivalry_intensity * 0.6),
        )
        return 1 if rng.random() < min(0.65, 0.18 + (risk * 0.28)) else 0

    def _fatigue_event_count(self, state: TeamRuntimeState, rng: Random) -> int:
        risk = max(0.0, (state.fatigue_level - 50.0) / 20.0)
        return 1 if rng.random() < min(0.55, 0.12 + (risk * 0.30)) else 0

    def _chance_count(self, home: TeamRuntimeState, away: TeamRuntimeState, rng: Random, *, is_final: bool, narrative: MatchNarrativeContext) -> int:
        quality = (home.strength.attack + away.strength.attack + home.strength.midfield + away.strength.midfield + home.strength.tactical_quality + away.strength.tactical_quality) / 6.0
        base = 8 + round((((home.tactics.tempo + away.tactics.tempo) / 2.0) - 50.0) / 14.0) + round((quality - 66.0) / 10.0) + round(narrative.stage_pressure * 4.0) + rng.randint(0, 3)
        if is_final:
            base += 1
        return int(self._clamp(base, 8, 21 if is_final else 18))

    def _chance_share(self, home: TeamRuntimeState, away: TeamRuntimeState) -> float:
        home_pressure = (home.strength.attack * 0.42) + (home.strength.midfield * 0.26) + (home.strength.tactical_quality * 0.12) + home.home_advantage_score + (home.tactical_mismatch_edge * 1.8) - (away.strength.defense * 0.16)
        away_pressure = (away.strength.attack * 0.42) + (away.strength.midfield * 0.26) + (away.strength.tactical_quality * 0.12) + (away.tactical_mismatch_edge * 1.8) - (home.strength.defense * 0.16)
        return self._clamp(home_pressure / max(1.0, home_pressure + away_pressure), 0.28, 0.72)

    def _incident_minute(self, rng: Random, minimum: int, maximum: int) -> int:
        minute = int(round(rng.triangular(minimum, maximum, (minimum + maximum) / 2)))
        return self._clamp_minute(minute)

    def _chance_minute(self, rng: Random) -> int:
        return self._clamp_minute(int(round(rng.triangular(2, 89, 53))))

    def _initialize_player_stats(self, home: TeamRuntimeState, away: TeamRuntimeState) -> dict[str, PlayerMatchStats]:
        ledgers: dict[str, PlayerMatchStats] = {}
        for state in (home, away):
            for player_id, player in state.players_by_id.items():
                ledgers[player_id] = PlayerMatchStats(player_id=player.player_id, player_name=player.player_name, team_id=state.team_id, team_name=state.team_name, role=player.role, started=player_id in state.active_player_ids)
        return ledgers

    def _process_tactical_swing(self, *, match_id: str, event_counter, state: TeamRuntimeState, opponent: TeamRuntimeState, minute: int, rng: Random) -> MatchEvent | None:
        swing = ((state.strength.tactical_quality - opponent.strength.tactical_quality) * 0.18) + ((state.strength.adaptability - opponent.strength.adaptability) * 0.12) + rng.uniform(-1.5, 2.4)
        if swing < 1.25:
            return None
        state.manager_influence_score += swing
        state.momentum = self._clamp(state.momentum + (swing * 0.55), -12.0, 14.0)
        state.dynamic_morale = self._clamp(state.dynamic_morale + (swing * 0.35), 30.0, 99.0)
        state.stats.tactical_swings += 1
        home_state, away_state = self._ordered_states(state, opponent)
        return self._make_event(match_id=match_id, event_counter=event_counter, event_type=MatchEventType.TACTICAL_SWING, minute=minute, home_state=home_state, away_state=away_state, team_id=state.team_id, team_name=state.team_name, metadata={"tactical_source": "manager_adjustment", "momentum_swing": round(swing, 2), "importance": 3 if swing < 2.6 else 4, "pressure_level": "phase_change"})

    def _apply_tactical_change(
        self,
        *,
        match_id: str,
        event_counter,
        state: TeamRuntimeState,
        opponent: TeamRuntimeState,
        minute: int,
        payload: dict[str, object],
    ) -> MatchEvent | None:
        adjustment = payload.get("adjustment")
        if adjustment is None:
            return None
        old_tactics = state.tactics
        updates: dict[str, object] = {}
        if getattr(adjustment, "tempo", None) is not None:
            updates["tempo"] = int(adjustment.tempo)
        if getattr(adjustment, "pressing", None) is not None:
            updates["pressing"] = int(adjustment.pressing)
        if getattr(adjustment, "aggression", None) is not None:
            updates["aggression"] = int(adjustment.aggression)
        if getattr(adjustment, "defensive_line", None) is not None:
            updates["defensive_line"] = int(adjustment.defensive_line)
        if getattr(adjustment, "width", None) is not None:
            updates["width"] = int(adjustment.width)
        if getattr(adjustment, "mentality", None) is not None:
            updates["mentality"] = adjustment.mentality
        if getattr(adjustment, "set_piece_emphasis", None) is not None:
            updates["set_piece_emphasis"] = int(adjustment.set_piece_emphasis)
        if getattr(adjustment, "player_instructions", None) is not None:
            updates["player_instructions"] = adjustment.player_instructions
        if getattr(adjustment, "game_state_adjustments", None) is not None:
            updates["game_state_adjustments"] = adjustment.game_state_adjustments

        formation_change = None
        if getattr(adjustment, "formation", None):
            formation_change = str(adjustment.formation)
            state.current_formation = formation_change
            state.current_shape = tuple(int(part) for part in formation_change.split("-"))
            state.stats.current_formation = formation_change
            state.shape_attack_adjustment, state.shape_defense_adjustment = self._shape_adjustment(state.starting_shape, state.current_shape)

        if updates:
            state.tactics = replace(state.tactics, **updates)

        tempo_delta = (updates.get("tempo", old_tactics.tempo) - old_tactics.tempo) if updates else 0
        pressing_delta = (updates.get("pressing", old_tactics.pressing) - old_tactics.pressing) if updates else 0
        impact = 0.0
        impact += abs(tempo_delta) / 18.0 if tempo_delta else 0.0
        impact += abs(pressing_delta) / 18.0 if pressing_delta else 0.0
        if formation_change is not None:
            impact += 1.1
        if updates.get("mentality") is not None:
            impact += 0.8

        state.manager_influence_score += impact * 0.4
        state.momentum = self._clamp(state.momentum + (impact * 0.4), -12.0, 14.0)
        state.dynamic_morale = self._clamp(state.dynamic_morale + (impact * 0.3), 25.0, 99.0)
        state.dynamic_motivation = self._clamp(state.dynamic_motivation + (impact * 0.25), 25.0, 99.0)
        if tempo_delta > 0 or pressing_delta > 0:
            state.fatigue_level = self._clamp(state.fatigue_level + (max(tempo_delta, pressing_delta) / 18.0), 5.0, 99.0)

        state.tactical_mismatch_edge = self._tactical_mismatch(state, opponent)
        opponent.tactical_mismatch_edge = self._tactical_mismatch(opponent, state)
        home_state, away_state = self._ordered_states(state, opponent)
        return self._make_event(
            match_id=match_id,
            event_counter=event_counter,
            event_type=MatchEventType.TACTICAL_CHANGE,
            minute=minute,
            home_state=home_state,
            away_state=away_state,
            team_id=state.team_id,
            team_name=state.team_name,
            metadata={
                "change_id": payload.get("change_id"),
                "requested_minute": payload.get("requested_minute"),
                "requested_second": payload.get("requested_second"),
                "urgency": payload.get("urgency", "normal"),
                "adjustments": {**updates, **({"formation": formation_change} if formation_change else {})},
                "importance": 3 if impact >= 1.5 else 2,
            },
        )

    def _apply_tactical_substitution(
        self,
        *,
        match_id: str,
        event_counter,
        state: TeamRuntimeState,
        opponent: TeamRuntimeState,
        minute: int,
        payload: dict[str, object],
        player_stats: dict[str, PlayerMatchStats],
    ) -> list[MatchEvent]:
        substitution = payload.get("substitution")
        if substitution is None:
            return []
        if state.substitutions_remaining() <= 0:
            return []
        outgoing = state.players_by_id.get(substitution.outgoing_player_id)
        incoming = state.players_by_id.get(substitution.incoming_player_id)
        if outgoing is None or incoming is None:
            return []
        reason = substitution.reason or "user_requested"
        metadata = {
            "change_id": payload.get("change_id"),
            "requested_minute": payload.get("requested_minute"),
            "requested_second": payload.get("requested_second"),
            "urgency": payload.get("urgency"),
        }
        event = self._apply_substitution(
            match_id=match_id,
            event_counter=event_counter,
            state=state,
            opponent=opponent,
            minute=minute,
            outgoing_player=outgoing,
            incoming_player=incoming,
            player_stats=player_stats,
            reason=reason,
            extra_metadata=metadata,
        )
        if event is None:
            return []
        events = [event]
        swing = float(event.metadata.get("swing_rating", 0.0))
        if swing >= 4.5:
            home_state, away_state = self._ordered_states(state, opponent)
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.SUBSTITUTION_IMPACT,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=state.team_id,
                    team_name=state.team_name,
                    primary_player_id=event.primary_player_id,
                    primary_player_name=event.primary_player_name,
                    secondary_player_id=event.secondary_player_id,
                    secondary_player_name=event.secondary_player_name,
                    metadata={"swing_rating": round(swing, 2), "reason": reason, "importance": 3},
                )
            )
        return events

    def _process_tactical_foul(
        self,
        *,
        match_id: str,
        event_counter,
        state: TeamRuntimeState,
        opponent: TeamRuntimeState,
        minute: int,
        rng: Random,
    ) -> MatchEvent | None:
        player = self._choose_card_candidate(state, rng)
        if player is None:
            return None
        state.dynamic_morale = self._clamp(state.dynamic_morale - 0.4, 25.0, 99.0)
        home_state, away_state = self._ordered_states(state, opponent)
        return self._make_event(
            match_id=match_id,
            event_counter=event_counter,
            event_type=MatchEventType.TACTICAL_FOUL,
            minute=minute,
            home_state=home_state,
            away_state=away_state,
            team_id=state.team_id,
            team_name=state.team_name,
            primary_player_id=player.player_id,
            primary_player_name=player.player_name,
            metadata={"importance": 2, "pressure_level": self._pressure_level(state, opponent, minute)},
        )

    def _process_fatigue_event(
        self,
        *,
        match_id: str,
        event_counter,
        state: TeamRuntimeState,
        opponent: TeamRuntimeState,
        minute: int,
    ) -> MatchEvent | None:
        candidates = state.active_outfielders()
        if not candidates:
            return None
        player = max(candidates, key=lambda entry: (entry.fatigue_load, 100 - entry.stamina_curve))
        state.fatigue_level = self._clamp(state.fatigue_level + 1.2, 5.0, 99.0)
        home_state, away_state = self._ordered_states(state, opponent)
        return self._make_event(
            match_id=match_id,
            event_counter=event_counter,
            event_type=MatchEventType.FATIGUE_EVENT,
            minute=minute,
            home_state=home_state,
            away_state=away_state,
            team_id=state.team_id,
            team_name=state.team_name,
            primary_player_id=player.player_id,
            primary_player_name=player.player_name,
            metadata={"importance": 2, "fatigue_level": round(state.fatigue_level, 2)},
        )

    def _process_yellow_card(self, *, match_id: str, event_counter, state: TeamRuntimeState, opponent: TeamRuntimeState, minute: int, player_stats: dict[str, PlayerMatchStats], rng: Random) -> MatchEvent | None:
        player = self._choose_card_candidate(state, rng)
        if player is None:
            return None
        if player.player_id in state.yellow_carded_ids and rng.random() < 0.42:
            state.stats.yellow_cards += 1
            player_stats[player.player_id].yellow_cards += 1
            return self._process_red_card(match_id=match_id, event_counter=event_counter, state=state, opponent=opponent, minute=minute, player_stats=player_stats, rng=rng, source="second_yellow", forced_player=player)
        state.yellow_carded_ids.add(player.player_id)
        state.stats.yellow_cards += 1
        player_stats[player.player_id].yellow_cards += 1
        state.dynamic_morale = self._clamp(state.dynamic_morale - 0.8, 30.0, 99.0)
        home_state, away_state = self._ordered_states(state, opponent)
        return self._make_event(match_id=match_id, event_counter=event_counter, event_type=MatchEventType.YELLOW_CARD, minute=minute, home_state=home_state, away_state=away_state, team_id=state.team_id, team_name=state.team_name, primary_player_id=player.player_id, primary_player_name=player.player_name, metadata={"importance": 2, "pressure_level": self._pressure_level(state, opponent, minute)})

    def _process_red_card(self, *, match_id: str, event_counter, state: TeamRuntimeState, opponent: TeamRuntimeState, minute: int, player_stats: dict[str, PlayerMatchStats], rng: Random, source: str, forced_player: InternalPlayer | None = None) -> MatchEvent | None:
        player = forced_player or self._choose_red_card_candidate(state, rng)
        if player is None or player.player_id in state.red_carded_ids:
            return None
        state.red_carded_ids.add(player.player_id)
        state.remove_active_player(player.player_id)
        state.current_formation = state.tactics.red_card_fallback_formation
        state.current_shape = tuple(int(part) for part in state.current_formation.split("-"))
        state.stats.current_formation = state.current_formation
        state.shape_attack_adjustment, state.shape_defense_adjustment = self._shape_adjustment(state.starting_shape, state.current_shape)
        state.stats.red_cards += 1
        ledger = player_stats[player.player_id]
        ledger.red_card = True
        if ledger.substituted_out_minute is None:
            ledger.substituted_out_minute = minute
        state.dynamic_morale = self._clamp(state.dynamic_morale - 6.0, 25.0, 99.0)
        opponent.dynamic_morale = self._clamp(opponent.dynamic_morale + 3.0, 25.0, 99.0)
        opponent.momentum = self._clamp(opponent.momentum + 2.2, -12.0, 14.0)
        home_state, away_state = self._ordered_states(state, opponent)
        return self._make_event(match_id=match_id, event_counter=event_counter, event_type=MatchEventType.RED_CARD, minute=minute, home_state=home_state, away_state=away_state, team_id=state.team_id, team_name=state.team_name, primary_player_id=player.player_id, primary_player_name=player.player_name, metadata={"source": source, "fallback_formation": state.current_formation, "importance": 5})

    def _process_injury(self, *, match_id: str, event_counter, state: TeamRuntimeState, opponent: TeamRuntimeState, minute: int, player_stats: dict[str, PlayerMatchStats], rng: Random) -> list[MatchEvent]:
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
        state.dynamic_morale = self._clamp(state.dynamic_morale - 2.5, 25.0, 99.0)
        home_state, away_state = self._ordered_states(state, opponent)
        events = [self._make_event(match_id=match_id, event_counter=event_counter, event_type=MatchEventType.INJURY, minute=minute, home_state=home_state, away_state=away_state, team_id=state.team_id, team_name=state.team_name, primary_player_id=player.player_id, primary_player_name=player.player_name, metadata={"importance": 4 if minute < 70 else 3, "pressure_level": self._pressure_level(state, opponent, minute), "injury_risk": player.injury_risk})]
        if state.tactics.injury_auto_substitution and state.substitutions_remaining() > 0 and state.bench_player_ids:
            replacement = self._select_replacement(state, preferred_roles=(player.role, PlayerRole.MIDFIELDER, PlayerRole.DEFENDER, PlayerRole.FORWARD))
            if replacement is not None:
                substitution = self._apply_substitution(match_id=match_id, event_counter=event_counter, state=state, opponent=opponent, minute=minute, outgoing_player=player, incoming_player=replacement, player_stats=player_stats, reason="injury")
                if substitution is not None:
                    events.append(substitution)
        return events

    def _process_substitution_window(self, *, match_id: str, event_counter, minute: int, state: TeamRuntimeState, opponent: TeamRuntimeState, player_stats: dict[str, PlayerMatchStats]) -> list[MatchEvent]:
        if state.substitutions_remaining() <= 0 or not state.bench_player_ids:
            return []
        active = state.active_outfielders()
        if not active:
            return []
        outgoing = incoming = None
        reason = None
        protected = [player for player in active if player.player_id in state.yellow_carded_ids and player.role in state.tactics.yellow_card_replacement_roles]
        if minute >= state.tactics.yellow_card_substitution_minute and protected:
            outgoing = min(protected, key=lambda player: (player.discipline, player.fitness, player.overall))
            incoming = self._select_replacement(state, preferred_roles=(outgoing.role, PlayerRole.DEFENDER, PlayerRole.MIDFIELDER, PlayerRole.FORWARD))
            reason = "yellow_card_protection"
        if outgoing is None or incoming is None:
            score_delta = state.stats.goals - opponent.stats.goals
            if score_delta < 0:
                outgoing = min(active, key=lambda player: (player.attacking_value(), player.fitness))
                incoming = self._select_replacement(state, preferred_roles=(PlayerRole.FORWARD, PlayerRole.MIDFIELDER, outgoing.role))
                reason = "chasing_goal"
            elif score_delta > 0 and minute >= 68:
                defensive = [player for player in active if player.role in {PlayerRole.FORWARD, PlayerRole.MIDFIELDER}]
                if defensive:
                    outgoing = min(defensive, key=lambda player: (player.defensive_value(), player.fitness))
                    incoming = self._select_replacement(state, preferred_roles=(PlayerRole.DEFENDER, PlayerRole.MIDFIELDER, outgoing.role))
                    reason = "protect_lead"
            elif minute >= 70:
                outgoing = min(active, key=lambda player: (player.fitness, player.stamina_curve, player.overall))
                incoming = self._select_replacement(state, preferred_roles=(outgoing.role, PlayerRole.MIDFIELDER, PlayerRole.FORWARD, PlayerRole.DEFENDER))
                reason = "fresh_legs"
        if outgoing is None or incoming is None:
            return []
        substitution = self._apply_substitution(match_id=match_id, event_counter=event_counter, state=state, opponent=opponent, minute=minute, outgoing_player=outgoing, incoming_player=incoming, player_stats=player_stats, reason=reason or "tactical")
        if substitution is None:
            return []
        events = [substitution]
        swing = float(substitution.metadata.get("swing_rating", 0.0))
        if swing >= 4.5:
            home_state, away_state = self._ordered_states(state, opponent)
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.SUBSTITUTION_IMPACT,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=state.team_id,
                    team_name=state.team_name,
                    primary_player_id=substitution.primary_player_id,
                    primary_player_name=substitution.primary_player_name,
                    secondary_player_id=substitution.secondary_player_id,
                    secondary_player_name=substitution.secondary_player_name,
                    metadata={
                        "swing_rating": round(swing, 2),
                        "reason": substitution.metadata.get("reason"),
                        "importance": 3 if swing < 6 else 4,
                    },
                )
            )
        if swing >= 6.0:
            state.stats.tactical_swings += 1
            home_state, away_state = self._ordered_states(state, opponent)
            events.append(self._make_event(match_id=match_id, event_counter=event_counter, event_type=MatchEventType.TACTICAL_SWING, minute=minute, home_state=home_state, away_state=away_state, team_id=state.team_id, team_name=state.team_name, metadata={"tactical_source": reason or "tactical", "momentum_swing": round(swing / 3.0, 2), "importance": 4, "pressure_level": self._pressure_level(state, opponent, minute)}))
        return events

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
        narrative: MatchNarrativeContext,
    ) -> list[MatchEvent]:
        events: list[MatchEvent] = []
        family = self._chance_family(attacking, defending, minute, rng)
        shooter = self._choose_shooter(attacking, rng, chance_family=family)
        if shooter is None:
            return events
        keeper = defending.goalkeeper()
        attack_rating = self._live_attack_rating(attacking, defending, minute, narrative=narrative)
        defense_rating = self._live_defense_rating(defending, attacking, minute, narrative=narrative)
        pressure = self._pressure_level(attacking, defending, minute)
        importance = self._chance_importance(attacking, defending, minute, chance_family=family)
        base = {
            "counterattack": 0.44,
            "through_ball_one_on_one": 0.58,
            "cutback": 0.48,
            "set_piece_header": 0.42,
            "back_post_header": 0.46,
            "penalty_box_scramble": 0.38,
            "long_range_effort": 0.24,
            "near_post_finish": 0.41,
            "late_siege": 0.44,
            "defensive_error": 0.50,
        }.get(family, 0.36)
        quality = self._clamp(
            base
            + ((attack_rating - defense_rating) / 230.0)
            + ((shooter.composure - 60.0) / 350.0)
            + ((shooter.recent_form - 58.0) / 400.0)
            + (0.03 if attacking.stats.goals < defending.stats.goals and minute >= 60 else 0.0)
            + rng.uniform(-0.05, 0.05),
            0.08,
            0.84,
        )
        attacking.stats.shots += 1
        if quality >= 0.48:
            attacking.stats.big_chances += 1
        on_target = self._clamp(
            0.22 + (quality * 0.36) + ((shooter.finishing - 60.0) / 280.0) + ((shooter.technique - 60.0) / 420.0),
            0.14,
            0.86,
        )
        goal = self._clamp(
            0.08
            + (quality * 0.38)
            + (
                (shooter.finishing - (keeper.goalkeeping_value() if keeper is not None else defending.strength.goalkeeping))
                / 260.0
            )
            + ((shooter.clutch_factor - 58.0) / 500.0)
            + ((shooter.big_match_temperament - 58.0) / 600.0)
            - (0.03 if narrative.favorite_side == ("home" if attacking.is_home else "away") and narrative.upset_probability >= 0.18 else 0.0),
            0.04,
            0.72,
        )
        home_state, away_state = self._ordered_states(attacking, defending)
        metadata = {
            "chance_family": family,
            "build_up_pattern": "through_middle" if attacking.tactics.mentality.value != "defensive" else "direct_transition",
            "tactical_source": self._tactical_source(attacking, minute, family),
            "pressure_level": pressure,
            "importance": importance,
            "chance_quality": round(quality, 2),
            "momentum_swing": round((importance * 0.6) + (quality * 1.4), 2),
        }

        if metadata["momentum_swing"] >= 2.4 or rng.random() < 0.08:
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.POSSESSION_SWING,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=attacking.team_id,
                    team_name=attacking.team_name,
                    metadata=metadata,
                )
            )
        if family == "counterattack":
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.COUNTER_ATTACK,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=attacking.team_id,
                    team_name=attacking.team_name,
                    primary_player_id=shooter.player_id,
                    primary_player_name=shooter.player_name,
                    metadata=metadata,
                )
            )
        if family in {"set_piece_header", "back_post_header"}:
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.SET_PIECE_CHANCE,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=attacking.team_id,
                    team_name=attacking.team_name,
                    primary_player_id=shooter.player_id,
                    primary_player_name=shooter.player_name,
                    metadata=metadata,
                )
            )
        if family == "defensive_error":
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.DEFENSIVE_ERROR,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=defending.team_id,
                    team_name=defending.team_name,
                    primary_player_id=shooter.player_id,
                    primary_player_name=shooter.player_name,
                    metadata=metadata,
                )
            )
        events.append(
            self._make_event(
                match_id=match_id,
                event_counter=event_counter,
                event_type=MatchEventType.DANGEROUS_ATTACK,
                minute=minute,
                home_state=home_state,
                away_state=away_state,
                team_id=attacking.team_id,
                team_name=attacking.team_name,
                primary_player_id=shooter.player_id,
                primary_player_name=shooter.player_name,
                metadata=metadata,
            )
        )

        penalty_award_chance = 0.06 if family in {"penalty_box_scramble", "defensive_error"} else 0.03
        if rng.random() < penalty_award_chance:
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.PENALTY_AWARDED,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=attacking.team_id,
                    team_name=attacking.team_name,
                    primary_player_id=shooter.player_id,
                    primary_player_name=shooter.player_name,
                    metadata=metadata,
                )
            )
            penalty_quality = self._clamp(
                0.72
                + ((shooter.penalty_value() - (keeper.goalkeeping_value() if keeper is not None else defending.strength.goalkeeping)) / 420.0)
                + rng.uniform(-0.06, 0.06),
                0.55,
                0.92,
            )
            attacking.stats.shots_on_target += 1
            if rng.random() < penalty_quality:
                attacking.stats.goals += 1
                player_stats[shooter.player_id].goals += 1
                self._apply_momentum(attacking, defending, delta=(2.1 + importance * 0.25))
                events.append(
                    self._make_event(
                        match_id=match_id,
                        event_counter=event_counter,
                        event_type=MatchEventType.PENALTY_SCORED,
                        minute=minute,
                        home_state=home_state,
                        away_state=away_state,
                        team_id=attacking.team_id,
                        team_name=attacking.team_name,
                        primary_player_id=shooter.player_id,
                        primary_player_name=shooter.player_name,
                        metadata={**metadata, "assisted": False, "penalty": True},
                    )
                )
            else:
                defending.stats.saves += 1
                if keeper is not None:
                    player_stats[keeper.player_id].saves += 1
                attacking.stats.missed_chances += 1
                player_stats[shooter.player_id].missed_chances += 1
                self._apply_momentum(defending, attacking, delta=(1.4 + importance * 0.20))
                events.append(
                    self._make_event(
                        match_id=match_id,
                        event_counter=event_counter,
                        event_type=MatchEventType.PENALTY_MISSED,
                        minute=minute,
                        home_state=home_state,
                        away_state=away_state,
                        team_id=attacking.team_id,
                        team_name=attacking.team_name,
                        primary_player_id=shooter.player_id,
                        primary_player_name=shooter.player_name,
                        secondary_player_id=keeper.player_id if keeper is not None else None,
                        secondary_player_name=keeper.player_name if keeper is not None else None,
                        metadata={**metadata, "penalty": True},
                    )
                )
            return events

        events.append(
            self._make_event(
                match_id=match_id,
                event_counter=event_counter,
                event_type=MatchEventType.SHOT,
                minute=minute,
                home_state=home_state,
                away_state=away_state,
                team_id=attacking.team_id,
                team_name=attacking.team_name,
                primary_player_id=shooter.player_id,
                primary_player_name=shooter.player_name,
                metadata=metadata,
            )
        )
        if rng.random() < on_target:
            attacking.stats.shots_on_target += 1
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.SHOT_ON_TARGET,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=attacking.team_id,
                    team_name=attacking.team_name,
                    primary_player_id=shooter.player_id,
                    primary_player_name=shooter.player_name,
                    metadata=metadata,
                )
            )
            if rng.random() < goal:
                attacking.stats.goals += 1
                player_stats[shooter.player_id].goals += 1
                assister = self._choose_assister(attacking, shooter, rng, chance_family=family)
                if assister is not None:
                    player_stats[assister.player_id].assists += 1
                self._apply_momentum(attacking, defending, delta=(2.2 + importance * 0.25))
                events.append(
                    self._make_event(
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
                        metadata={**metadata, "assisted": assister is not None},
                    )
                )
                return events
            defending.stats.saves += 1
            if keeper is not None:
                player_stats[keeper.player_id].saves += 1
            self._apply_momentum(defending, attacking, delta=(1.4 + importance * 0.20))
            save_type = MatchEventType.DOUBLE_SAVE if quality >= 0.56 and importance >= 4 and rng.random() < 0.32 else MatchEventType.GOALKEEPER_SAVE
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=save_type,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=defending.team_id,
                    team_name=defending.team_name,
                    primary_player_id=keeper.player_id if keeper is not None else None,
                    primary_player_name=keeper.player_name if keeper is not None else None,
                    secondary_player_id=shooter.player_id,
                    secondary_player_name=shooter.player_name,
                    metadata=metadata,
                )
            )
            return events

        attacking.stats.missed_chances += 1
        player_stats[shooter.player_id].missed_chances += 1
        attacking.dynamic_morale = self._clamp(attacking.dynamic_morale - (1.0 + quality * 2.4), 25.0, 99.0)
        if quality >= 0.54 and rng.random() < 0.36:
            attacking.stats.woodwork += 1
            events.append(
                self._make_event(
                    match_id=match_id,
                    event_counter=event_counter,
                    event_type=MatchEventType.WOODWORK,
                    minute=minute,
                    home_state=home_state,
                    away_state=away_state,
                    team_id=attacking.team_id,
                    team_name=attacking.team_name,
                    primary_player_id=shooter.player_id,
                    primary_player_name=shooter.player_name,
                    metadata=metadata,
                )
            )
            return events
        missed_type = MatchEventType.MISSED_BIG_CHANCE if quality >= 0.55 else MatchEventType.MISSED_CHANCE
        events.append(
            self._make_event(
                match_id=match_id,
                event_counter=event_counter,
                event_type=missed_type,
                minute=minute,
                home_state=home_state,
                away_state=away_state,
                team_id=attacking.team_id,
                team_name=attacking.team_name,
                primary_player_id=shooter.player_id,
                primary_player_name=shooter.player_name,
                metadata=metadata,
            )
        )
        return events

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
        extra_metadata: dict[str, object] | None = None,
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
        swing = max(0.0, ((incoming_player.attacking_value() - outgoing_player.attacking_value()) * 0.55) + ((incoming_player.defensive_value() - outgoing_player.defensive_value()) * 0.45) + ((incoming_player.fitness - outgoing_player.fitness) * 0.25))
        state.manager_influence_score += swing * 0.22
        state.dynamic_morale = self._clamp(state.dynamic_morale + (swing * 0.12), 25.0, 99.0)
        state.fatigue_level = self._clamp(state.fatigue_level - 4.0, 5.0, 99.0)
        home_state, away_state = self._ordered_states(state, opponent)
        metadata = {
            "reason": reason,
            "outgoing_role": outgoing_player.role.value,
            "incoming_role": incoming_player.role.value,
            "swing_rating": round(swing, 2),
            "importance": 3 if swing < 6 else 4,
        }
        if extra_metadata:
            metadata.update(extra_metadata)
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
            metadata=metadata,
        )

    def _live_attack_rating(self, team: TeamRuntimeState, opponent: TeamRuntimeState, minute: int, *, narrative: MatchNarrativeContext) -> float:
        score_delta = team.stats.goals - opponent.stats.goals
        mentality = team.tactics.mentality.value
        style = {"attacking": 1.08, "balanced": 1.00, "defensive": 0.92}[mentality]
        urgency = 1.0 + (0.05 * abs(score_delta)) if score_delta < 0 and minute >= 58 else 1.0
        management = 0.96 if score_delta > 0 and minute >= 74 else 1.0
        morale = 0.92 + (team.dynamic_morale / 620.0)
        motivation = 0.92 + (team.dynamic_motivation / 650.0)
        fatigue = 1.0 - max(0.0, (team.fatigue_level - 42.0) / 180.0) - max(0.0, minute - 65) / 1200.0
        home_push = 1.0 + ((team.home_advantage_score * 0.018) if team.is_home and minute >= 70 else 0.0)
        late_push = 1.0 + (0.05 if team.is_home and score_delta <= 0 and minute >= 78 else 0.0)
        nervous = 0.98 if team.is_home and narrative.favorite_side == "home" and score_delta < 0 and minute >= 72 else 1.0
        tactical = 1.0 + (team.tactical_mismatch_edge * 0.012) + ((team.strength.tactical_quality - opponent.strength.tactical_quality) / 500.0)
        momentum = 1.0 + max(-0.08, min(0.10, team.momentum / 45.0))
        red = 1.0 - (0.15 * len(team.red_carded_ids))
        tempo = 1.0 + ((team.tactics.tempo - 50.0) / 520.0)
        width = 1.0 + ((team.tactics.width - 50.0) / 600.0)
        line_push = 1.0 + ((team.tactics.defensive_line - 50.0) / 650.0)
        press = 1.0 + ((team.tactics.pressing - 50.0) / 640.0)
        return (
            team.strength.attack
            * style
            * urgency
            * management
            * morale
            * motivation
            * fatigue
            * home_push
            * late_push
            * nervous
            * tactical
            * momentum
            * red
            * tempo
            * width
            * line_push
            * press
            * (1.0 + team.shape_attack_adjustment)
        )

    def _live_defense_rating(self, team: TeamRuntimeState, opponent: TeamRuntimeState, minute: int, *, narrative: MatchNarrativeContext) -> float:
        score_delta = team.stats.goals - opponent.stats.goals
        mentality = team.tactics.mentality.value
        style = {"attacking": 0.92, "balanced": 1.00, "defensive": 1.08}[mentality]
        protect = 1.05 if score_delta > 0 and minute >= 72 else 1.0
        fatigue = 1.0 - max(0.0, (team.fatigue_level - 44.0) / 220.0) - max(0.0, minute - 70) / 1500.0
        morale = 0.94 + (team.dynamic_morale / 700.0)
        tactical = 1.0 + ((team.strength.tactical_quality - opponent.strength.tactical_quality) / 550.0) + (team.tactical_mismatch_edge * 0.008)
        low_block = 1.03 if mentality == "defensive" and score_delta > 0 else 1.0
        home_recovery = 1.02 if team.is_home and score_delta <= 0 and narrative.stage_pressure >= 0.40 else 1.0
        red = 1.0 - (0.10 * len(team.red_carded_ids))
        line_hold = 1.0 + ((team.tactics.defensive_line - 50.0) / 700.0)
        width = 1.0 + ((team.tactics.width - 50.0) / 750.0)
        return (
            team.strength.defense
            * style
            * protect
            * fatigue
            * morale
            * tactical
            * low_block
            * home_recovery
            * red
            * line_hold
            * width
            * (1.0 + team.shape_defense_adjustment)
        )

    def _choose_card_candidate(self, state: TeamRuntimeState, rng: Random) -> InternalPlayer | None:
        candidates = [player for player in state.active_outfielders() if player.player_id not in state.red_carded_ids]
        weights = [max(1.0, (110.0 - player.discipline) + (state.tactics.aggression * 0.28) + (state.fatigue_level * 0.12) + ((player.motivation - 55.0) * 0.18) + (10.0 if player.role in {PlayerRole.DEFENDER, PlayerRole.MIDFIELDER} else 0.0)) for player in candidates]
        return self._weighted_choice(candidates, weights, rng)

    def _choose_red_card_candidate(self, state: TeamRuntimeState, rng: Random) -> InternalPlayer | None:
        candidates = [player for player in state.active_outfielders() if player.player_id not in state.red_carded_ids]
        weights = [max(1.0, (118.0 - player.discipline) + (state.tactics.aggression * 0.34) + (state.fatigue_level * 0.16) + (18.0 if player.player_id in state.yellow_carded_ids else 0.0)) for player in candidates]
        return self._weighted_choice(candidates, weights, rng)

    def _choose_injury_candidate(self, state: TeamRuntimeState, rng: Random) -> InternalPlayer | None:
        candidates = [player for player in state.active_outfielders() if player.player_id not in state.injured_ids]
        weights = [max(1.0, player.injury_risk + (state.fatigue_level * 0.42) + ((100.0 - player.stamina_curve) * 0.36) + (8.0 if player.role in {PlayerRole.FORWARD, PlayerRole.MIDFIELDER} else 0.0)) for player in candidates]
        return self._weighted_choice(candidates, weights, rng)

    def _choose_shooter(self, state: TeamRuntimeState, rng: Random, *, chance_family: str) -> InternalPlayer | None:
        candidates = state.active_outfielders()
        if chance_family in {"set_piece_header", "back_post_header"}:
            candidates = [player for player in candidates if player.role in {PlayerRole.DEFENDER, PlayerRole.FORWARD}] or candidates
        if chance_family == "long_range_effort":
            candidates = [player for player in candidates if player.role in {PlayerRole.MIDFIELDER, PlayerRole.FORWARD}] or candidates
        weights = [max(1.0, player.attacking_value() + (player.aerial_ability * 0.30 if chance_family in {"set_piece_header", "back_post_header"} else 0.0) + (player.creativity * 0.18 if chance_family == "long_range_effort" else 0.0) + (12.0 if player.role is PlayerRole.FORWARD else 0.0)) for player in candidates]
        return self._weighted_choice(candidates, weights, rng)

    def _choose_assister(self, state: TeamRuntimeState, shooter: InternalPlayer, rng: Random, *, chance_family: str) -> InternalPlayer | None:
        if chance_family in {"penalty_box_scramble", "long_range_effort"} and rng.random() < 0.55:
            return None
        if rng.random() > (0.82 if state.tactics.style.value != "defensive" else 0.66):
            return None
        candidates = [player for player in state.active_outfielders() if player.player_id != shooter.player_id]
        weights = [max(1.0, player.control_value() + (player.creativity * 0.22) + (player.technique * 0.18) + (10.0 if player.role is PlayerRole.MIDFIELDER else 0.0)) for player in candidates]
        return self._weighted_choice(candidates, weights, rng)

    def _chance_family(self, attacking: TeamRuntimeState, defending: TeamRuntimeState, minute: int, rng: Random) -> str:
        score_delta = attacking.stats.goals - defending.stats.goals
        mentality = attacking.tactics.mentality.value
        options = [
            ("counterattack", 1.0 + (0.35 if mentality == "defensive" else 0.0) + (0.25 if score_delta < 0 else 0.0)),
            ("through_ball_one_on_one", 1.15 + (attacking.strength.attack / 140.0)),
            ("cutback", 1.05 + (attacking.strength.midfield / 180.0)),
            ("set_piece_header", 0.82 + (attacking.tactics.aggression / 180.0)),
            ("penalty_box_scramble", 0.78 + (0.20 if minute >= 75 else 0.0)),
            ("long_range_effort", 0.65 + (attacking.strength.midfield / 260.0)),
            ("near_post_finish", 0.72 + (attacking.tactics.tempo / 220.0)),
            ("back_post_header", 0.66 + (attacking.strength.attack / 220.0)),
        ]
        if minute >= 78 and score_delta <= 0 and attacking.is_home:
            options.append(("late_siege", 0.98 + (attacking.home_advantage_score / 8.0)))
        if defending.fatigue_level >= 48 or defending.stats.red_cards > 0:
            options.append(("defensive_error", 0.74 + (defending.fatigue_level / 180.0)))
        return self._weighted_choice_str(options, rng)

    def _tactical_source(self, attacking: TeamRuntimeState, minute: int, chance_family: str) -> str:
        if chance_family in {"counterattack", "through_ball_one_on_one"}:
            return "transition"
        if chance_family in {"set_piece_header", "back_post_header"}:
            return "set_piece"
        if minute >= 78 and attacking.is_home and attacking.stats.goals <= 0:
            return "late_home_push"
        if attacking.tactics.mentality.value == "defensive":
            return "low_block_counter"
        if attacking.tactics.pressing >= 68:
            return "high_press"
        return "structured_build_up"

    def _pressure_level(self, attacking: TeamRuntimeState, defending: TeamRuntimeState, minute: int) -> str:
        if minute >= 85:
            return "stoppage_drama" if abs(attacking.stats.goals - defending.stats.goals) <= 1 else "closing_phase"
        if minute >= 72:
            return "late_pressure"
        if minute >= 46:
            return "second_half"
        return "opening_phase"

    def _chance_importance(self, attacking: TeamRuntimeState, defending: TeamRuntimeState, minute: int, *, chance_family: str) -> int:
        importance = 2 + int(chance_family in {"through_ball_one_on_one", "late_siege", "defensive_error"}) + int(minute >= 75) + int(abs(attacking.stats.goals - defending.stats.goals) <= 1)
        return max(1, min(5, importance))

    def _select_replacement(self, state: TeamRuntimeState, *, preferred_roles: tuple[PlayerRole, ...]) -> InternalPlayer | None:
        candidates = state.available_bench(preferred_roles) or state.available_bench()
        return max(candidates, key=lambda player: (player.overall, player.fitness, player.consistency, player.attacking_value() + player.defensive_value())) if candidates else None

    def _resolve_possession(self, home: TeamRuntimeState, away: TeamRuntimeState) -> None:
        possession = 50.0 + (home.strength.midfield - away.strength.midfield) * 0.22 + (home.strength.tactical_quality - away.strength.tactical_quality) * 0.10 + (home.strength.chemistry - away.strength.chemistry) * 0.06 + (home.tactics.tempo - away.tactics.tempo) * 0.05 + (home.tactics.pressing - away.tactics.pressing) * 0.03 + (len(away.red_carded_ids) - len(home.red_carded_ids)) * 5.5 + home.home_advantage_score * 0.8
        home.stats.possession = int(round(self._clamp(possession, 31.0, 69.0)))
        away.stats.possession = 100 - home.stats.possession

    def _apply_halftime_reset(self, home: TeamRuntimeState, away: TeamRuntimeState) -> None:
        for state, opponent in ((home, away), (away, home)):
            delta = state.stats.goals - opponent.stats.goals
            state.dynamic_morale = self._clamp(state.dynamic_morale + (1.2 if delta >= 0 else -0.6), 25.0, 99.0)
            state.fatigue_level = self._clamp(state.fatigue_level + 1.6, 5.0, 99.0)
            if delta < 0:
                state.dynamic_motivation = self._clamp(state.dynamic_motivation + 1.8, 25.0, 99.0)

    def _apply_momentum(self, beneficiary: TeamRuntimeState, affected: TeamRuntimeState, *, delta: float) -> None:
        beneficiary.momentum = self._clamp(beneficiary.momentum + delta, -12.0, 14.0)
        affected.momentum = self._clamp(affected.momentum - (delta * 0.65), -12.0, 14.0)
        beneficiary.dynamic_morale = self._clamp(beneficiary.dynamic_morale + (delta * 0.55), 25.0, 99.0)
        affected.dynamic_morale = self._clamp(affected.dynamic_morale - (delta * 0.42), 25.0, 99.0)

    def _finalize_player_minutes(self, player_stats: dict[str, PlayerMatchStats]) -> None:
        for ledger in player_stats.values():
            if not ledger.started and ledger.substituted_in_minute is None:
                ledger.minutes_played = 0
                continue
            start = 0 if ledger.started else ledger.substituted_in_minute or 0
            end = ledger.substituted_out_minute if ledger.substituted_out_minute is not None else 90
            ledger.minutes_played = max(0, min(90, end) - min(90, start))

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
        return winner_team_id == underdog.team_id and abs(home.strength.overall - away.strength.overall) >= 5.0

    def _build_summary_line(self, home: TeamRuntimeState, away: TeamRuntimeState, shootout, *, upset: bool) -> str:
        line = f"{home.team_name} {home.stats.goals}-{away.stats.goals} {away.team_name}"
        if shootout is not None:
            line = f"{line} ({shootout.home_penalties}-{shootout.away_penalties} pens)"
        return f"{line} - upset result" if upset else line

    def _upset_reason_codes(self, *, upset: bool, winner_team_id: str | None, home_state: TeamRuntimeState, away_state: TeamRuntimeState, events: list[MatchEvent]) -> tuple[str, ...]:
        if not upset or winner_team_id is None:
            return ()
        winner = home_state if winner_team_id == home_state.team_id else away_state
        loser = away_state if winner is home_state else home_state
        reasons: list[str] = []
        if winner.tactical_mismatch_edge > 1.4:
            reasons.append("tactical_mismatch")
        if any(
            event.event_type in {MatchEventType.DOUBLE_SAVE, MatchEventType.GOALKEEPER_SAVE}
            and event.team_id == winner.team_id
            for event in events
        ):
            reasons.append("elite_goalkeeping")
        if any(event.event_type is MatchEventType.RED_CARD and event.team_id == loser.team_id for event in events):
            reasons.append("red_card")
        if any(event.event_type is MatchEventType.INJURY and event.team_id == loser.team_id for event in events):
            reasons.append("key_injury")
        if any(
            event.minute <= 18
            and event.event_type in {MatchEventType.GOAL, MatchEventType.PENALTY_SCORED}
            and event.team_id == winner.team_id
            for event in events
        ):
            reasons.append("early_goal_distortion")
        if any(
            event.event_type in {MatchEventType.WOODWORK, MatchEventType.MISSED_CHANCE, MatchEventType.MISSED_BIG_CHANCE}
            and event.team_id == loser.team_id
            and float(event.metadata.get("chance_quality", 0.0)) >= 0.55
            for event in events
        ):
            reasons.append("favorite_wastefulness")
        if winner.manager_influence_score - loser.manager_influence_score >= 1.6:
            reasons.append("manager_outcoaching")
        if winner.strength.motivation - loser.strength.motivation >= 4:
            reasons.append("underdog_motivation")
        return tuple(dict.fromkeys(reasons))

    def _manager_influence_notes(self, home_state: TeamRuntimeState, away_state: TeamRuntimeState, events: list[MatchEvent]) -> tuple[str, ...]:
        notes: list[str] = []
        if home_state.manager_influence_score - away_state.manager_influence_score >= 1.6:
            notes.append(f"{home_state.team_name} found the cleaner in-game adjustments.")
        elif away_state.manager_influence_score - home_state.manager_influence_score >= 1.6:
            notes.append(f"{away_state.team_name} found the cleaner in-game adjustments.")
        if any(
            event.event_type in {MatchEventType.TACTICAL_SWING, MatchEventType.TACTICAL_CHANGE}
            and event.team_id == home_state.team_id
            for event in events
        ):
            notes.append(f"{home_state.team_name} generated at least one visible tactical swing.")
        if any(
            event.event_type in {MatchEventType.TACTICAL_SWING, MatchEventType.TACTICAL_CHANGE}
            and event.team_id == away_state.team_id
            for event in events
        ):
            notes.append(f"{away_state.team_name} generated at least one visible tactical swing.")
        return tuple(notes[:5])

    def _tactical_battle_summary(self, home_state: TeamRuntimeState, away_state: TeamRuntimeState) -> str:
        if home_state.tactical_mismatch_edge - away_state.tactical_mismatch_edge >= 1.0:
            return f"{home_state.team_name} won the tactical battle through cleaner structure and better game-state control."
        if away_state.tactical_mismatch_edge - home_state.tactical_mismatch_edge >= 1.0:
            return f"{away_state.team_name} won the tactical battle through cleaner structure and better game-state control."
        return "The tactical battle stayed live throughout, with neither side fully controlling the chessboard."

    def _form_motivation_summary(self, home_state: TeamRuntimeState, away_state: TeamRuntimeState) -> str:
        home_signal = home_state.strength.recent_form + home_state.strength.motivation
        away_signal = away_state.strength.recent_form + away_state.strength.motivation
        if home_signal - away_signal >= 6:
            return f"{home_state.team_name} carried the sharper form and emotional edge into the fixture."
        if away_signal - home_signal >= 6:
            return f"{away_state.team_name} carried the sharper form and emotional edge into the fixture."
        return "Form and motivation were close enough that the match state, not just pre-match mood, decided the story."

    def _momentum_swings(self, events: list[MatchEvent]) -> tuple[str, ...]:
        swings = [f"{event.minute}' {(event.team_name or event.primary_player_name or 'Match')} swung the momentum through {event.event_type.value.replace('_', ' ')}." for event in events if float(event.metadata.get("momentum_swing", 0.0)) >= 1.6]
        return tuple(swings[:4])

    def _turning_points(self, events: list[MatchEvent]) -> tuple[str, ...]:
        points = [
            f"{event.minute}' {(event.primary_player_name or event.team_name or 'Match')} - {event.event_type.value.replace('_', ' ')}"
            for event in events
            if event.event_type
            in {
                MatchEventType.GOAL,
                MatchEventType.PENALTY_SCORED,
                MatchEventType.PENALTY_MISSED,
                MatchEventType.RED_CARD,
                MatchEventType.DOUBLE_SAVE,
                MatchEventType.GOALKEEPER_SAVE,
                MatchEventType.TACTICAL_SWING,
                MatchEventType.TACTICAL_CHANGE,
                MatchEventType.WOODWORK,
            }
        ]
        return tuple(points[:5])

    def _key_matchups(self, player_stats: tuple[PlayerMatchStats, ...]) -> tuple[str, ...]:
        notable = [player for player in player_stats if player.started][:4]
        pairs: list[str] = []
        for index in range(0, len(notable) - 1, 2):
            pairs.append(f"{notable[index].player_name} vs {notable[index + 1].player_name}")
        return tuple(pairs[:3])

    def _tactical_impact_notes(self, events: list[MatchEvent]) -> tuple[str, ...]:
        notes: list[str] = []
        if any(event.event_type is MatchEventType.RED_CARD for event in events):
            notes.append("A red card forced a shape compromise and changed the balance of territory.")
        if any(event.event_type is MatchEventType.INJURY for event in events):
            notes.append("An injury disrupted rhythm and forced at least one reactive substitution.")
        if any(event.event_type in {MatchEventType.TACTICAL_SWING, MatchEventType.TACTICAL_CHANGE} for event in events):
            notes.append("Manager interventions materially changed the tactical picture.")
        if any(event.event_type is MatchEventType.WOODWORK for event in events):
            notes.append("Fine margins mattered, with the woodwork stopping at least one high-leverage moment.")
        return tuple(notes[:4])

    def _make_event(self, *, match_id: str, event_counter, event_type: MatchEventType, minute: int, home_state: TeamRuntimeState, away_state: TeamRuntimeState, team_id: str | None = None, team_name: str | None = None, primary_player_id: str | None = None, primary_player_name: str | None = None, secondary_player_id: str | None = None, secondary_player_name: str | None = None, added_time: int = 0, metadata: dict[str, object] | None = None) -> MatchEvent:
        sequence = next(event_counter)
        base_metadata = dict(metadata or {})
        base_metadata.setdefault("home_formation", home_state.current_formation)
        base_metadata.setdefault("away_formation", away_state.current_formation)
        base_metadata.setdefault("home_momentum", round(home_state.momentum, 2))
        base_metadata.setdefault("away_momentum", round(away_state.momentum, 2))
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
            metadata=base_metadata,
        )

    def _resolve_seed(self, request: MatchSimulationRequest) -> int:
        if request.seed is not None:
            return request.seed
        seed_material = f"{request.match_id}:{request.home_team.team_id}:{request.away_team.team_id}:{request.competition.stage}"
        seed = int(sha256(seed_material.encode("utf-8")).hexdigest()[:12], 16)
        if request.tactical_changes:
            change_material = "|".join(
                f"{change.team_id}:{change.requested_minute}:{change.requested_second}:{change.change_id or ''}"
                for change in request.tactical_changes
            )
            seed ^= int(sha256(change_material.encode("utf-8")).hexdigest()[:12], 16)
        return seed

    def _resolve_requires_winner(self, request: MatchSimulationRequest) -> bool:
        if request.competition.requires_winner is not None:
            return request.competition.requires_winner
        return request.competition.competition_type is MatchCompetitionType.CUP or request.competition.is_final

    def _infer_rivalry(self, home_team_name: str, away_team_name: str) -> float:
        return 0.18 if ({token.lower() for token in home_team_name.split() if token} & {token.lower() for token in away_team_name.split() if token}) else 0.0

    def _tactical_mismatch(self, team: TeamRuntimeState, opponent: TeamRuntimeState) -> float:
        style_bonus = 1.0 if team.tactics.style.value == "defensive" and opponent.tactics.style.value == "attacking" else -0.4 if team.tactics.style.value == "attacking" and opponent.tactics.style.value == "defensive" else 0.0
        if team.tactics.pressing >= 68 and opponent.tactics.tempo <= 52:
            style_bonus += 0.5
        return round(((team.strength.tactical_quality - opponent.strength.tactical_quality) * 0.08) + style_bonus, 2)

    def _kits_clash(self, home_kit: KitVisualIdentity, away_kit: KitVisualIdentity) -> bool:
        return home_kit.primary_color.upper() in {away_kit.primary_color.upper(), away_kit.secondary_color.upper()} or home_kit.secondary_color.upper() == away_kit.primary_color.upper()

    def _ordered_states(self, state: TeamRuntimeState, opponent: TeamRuntimeState) -> tuple[TeamRuntimeState, TeamRuntimeState]:
        return (state, opponent) if state.is_home else (opponent, state)

    def _shape_adjustment(self, starting_shape: tuple[int, ...], current_shape: tuple[int, ...]) -> tuple[float, float]:
        attack = ((current_shape[-1] - starting_shape[-1]) * 0.05) + ((sum(current_shape[1:-1]) - sum(starting_shape[1:-1])) * 0.02)
        defense = ((current_shape[0] - starting_shape[0]) * 0.05) + ((sum(current_shape[1:-1]) - sum(starting_shape[1:-1])) * 0.01)
        return attack, defense

    def _weighted_choice(self, items: list[InternalPlayer], weights: list[float], rng: Random) -> InternalPlayer | None:
        if not items:
            return None
        total = sum(max(0.0, weight) for weight in weights)
        if total <= 0.0:
            return items[0]
        threshold = rng.random() * total
        running = 0.0
        for item, weight in zip(items, weights, strict=True):
            running += max(0.0, weight)
            if running >= threshold:
                return item
        return items[-1]

    def _weighted_choice_str(self, entries: list[tuple[str, float]], rng: Random) -> str:
        total = sum(max(0.0, weight) for _, weight in entries)
        if total <= 0.0:
            return entries[0][0]
        threshold = rng.random() * total
        running = 0.0
        for item, weight in entries:
            running += max(0.0, weight)
            if running >= threshold:
                return item
        return entries[-1][0]

    def _resolve_rating(self, value: int | None, fallback: int) -> int:
        return max(1, min(99, value if value is not None else fallback))

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _safe_checkpoint_minute(self, minute: int) -> int:
        return self._clamp_minute(max(1, minute))

    def _clamp_minute(self, minute: int) -> int:
        if minute == 45:
            return 44
        return max(1, min(89, minute))
