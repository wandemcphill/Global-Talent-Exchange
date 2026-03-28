from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from statistics import mean

from app.ai_manager.schemas import (
    AIManagerProfileInput,
    AIManagerProfileView,
    AutopilotActivationView,
    AutopilotRunRequest,
    AutopilotRunResponse,
    ClubFinanceContextInput,
    ClubPlayerInput,
    FinanceActionView,
    FinancialStrategy,
    LineHeight,
    LiveDecisionResponse,
    LiveMatchDecisionRequest,
    ManagerTacticalStyle,
    OpponentContextInput,
    PersonalityProfileInput,
    PlayerAvailability,
    PressingIntensity,
    RewardDivision,
    RewardPolicySummaryView,
    RewardPreviewRequest,
    RewardPreviewResponse,
    RoleAssignmentView,
    SelectedPlayerView,
    SquadPlanView,
    TempoSetting,
    TrainingAssignmentView,
    TransferMarketContextInput,
    TransferRecommendationView,
    TransferTargetInput,
)

FORMATION_TEMPLATES: dict[str, tuple[str, ...]] = {
    "4-3-3": ("GK", "RB", "CB", "CB", "LB", "CM", "CM", "CM", "RW", "ST", "LW"),
    "4-1-4-1": ("GK", "RB", "CB", "CB", "LB", "DM", "CM", "CM", "RW", "LW", "ST"),
    "4-4-2": ("GK", "RB", "CB", "CB", "LB", "RM", "CM", "CM", "LM", "ST", "ST"),
    "4-5-1": ("GK", "RB", "CB", "CB", "LB", "RM", "CM", "CM", "CM", "LM", "ST"),
    "4-2-3-1": ("GK", "RB", "CB", "CB", "LB", "DM", "CM", "RW", "AM", "LW", "ST"),
    "5-4-1": ("GK", "RWB", "CB", "CB", "CB", "LWB", "CM", "CM", "RW", "LW", "ST"),
}

STYLE_FORMATIONS: dict[ManagerTacticalStyle, dict[str, str]] = {
    ManagerTacticalStyle.POSSESSION: {"attacking": "4-3-3", "defensive": "4-1-4-1"},
    ManagerTacticalStyle.DIRECT: {"attacking": "4-4-2", "defensive": "4-5-1"},
    ManagerTacticalStyle.COUNTER: {"attacking": "4-2-3-1", "defensive": "5-4-1"},
    ManagerTacticalStyle.BALANCED: {"attacking": "4-2-3-1", "defensive": "4-4-2"},
}

DIVISION_MULTIPLIERS: dict[RewardDivision, float] = {
    RewardDivision.D1: 2.0,
    RewardDivision.D2: 1.5,
    RewardDivision.D3: 1.2,
    RewardDivision.OPEN: 1.0,
}

PREMIUM_EFFICIENCY_TOOLS = [
    "cosmetic upgrades",
    "training acceleration",
    "advanced scouting analytics",
]

BLOCKED_PAY_TO_WIN_PATHS = [
    "buying wins",
    "wallet-based stat boosts",
    "uncapped premium performance bonuses",
]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_position(position: str) -> str:
    normalized = position.strip().upper()
    aliases = {
        "RCB": "CB",
        "LCB": "CB",
        "SW": "CB",
        "RDM": "DM",
        "LDM": "DM",
        "CAM": "AM",
        "LAM": "AM",
        "RAM": "AM",
        "RCM": "CM",
        "LCM": "CM",
        "CDM": "DM",
        "CF": "ST",
        "SS": "ST",
        "RF": "RW",
        "LF": "LW",
        "RMF": "RM",
        "LMF": "LM",
    }
    return aliases.get(normalized, normalized)


def _position_group(position: str) -> str:
    normalized = _normalize_position(position)
    if normalized in {"RWB", "LWB", "RB", "LB"}:
        return "wide_defender"
    if normalized == "CB":
        return "center_back"
    if normalized == "GK":
        return "goalkeeper"
    if normalized in {"DM", "CM", "AM"}:
        return "midfield"
    if normalized in {"RW", "LW", "RM", "LM"}:
        return "wide_attack"
    if normalized == "ST":
        return "forward"
    return normalized


def _player_positions(player: ClubPlayerInput) -> set[str]:
    positions = {_normalize_position(player.primary_position)}
    positions.update(_normalize_position(position) for position in player.secondary_positions)
    return positions


@dataclass(frozen=True, slots=True)
class ActivationPolicy:
    threshold_hours: float = 6.0
    ai_reward_multiplier: float = 0.85
    ai_win_streak_bonus_cap: float = 0.15

    def evaluate(self, *, user_last_active_hours: float) -> AutopilotActivationView:
        ai_active = user_last_active_hours > self.threshold_hours
        if ai_active:
            summary = "AI manager is in autonomous mode because the user has been inactive past the offline threshold."
        else:
            summary = "AI manager is in advisory mode because the user is still recently active."
        return AutopilotActivationView(
            ai_active=ai_active,
            mode="autonomous" if ai_active else "advisory",
            inactivity_threshold_hours=self.threshold_hours,
            reward_penalty_multiplier=self.ai_reward_multiplier if ai_active else 1.0,
            applied_win_streak_bonus_cap=self.ai_win_streak_bonus_cap if ai_active else 0.0,
            summary=summary,
        )


@dataclass(frozen=True, slots=True)
class SquadPlanner:
    def plan(
        self,
        *,
        profile: AIManagerProfileView,
        payload: AutopilotRunRequest,
    ) -> SquadPlanView:
        available_players = [player for player in payload.squad if player.availability is PlayerAvailability.AVAILABLE]
        injuries = len(payload.squad) - len(available_players)
        average_fatigue = mean(player.fatigue for player in payload.squad)
        underdog = payload.opponent.strength > payload.club_strength + 4
        defensive_variant = underdog or average_fatigue >= 0.55 or injuries >= 3
        formation = STYLE_FORMATIONS[profile.tactical_style]["defensive" if defensive_variant else "attacking"]
        slots = FORMATION_TEMPLATES[formation]
        selection_pool = available_players if len(available_players) >= 11 else list(payload.squad)

        remaining = list(selection_pool)
        selected_rows: list[tuple[str, ClubPlayerInput, float, bool]] = []
        for slot in slots:
            best_player = max(
                remaining,
                key=lambda player: self._slot_score(
                    player=player,
                    slot=slot,
                    profile=profile,
                ),
            )
            score, natural_position = self._slot_score(
                player=best_player,
                slot=slot,
                profile=profile,
                return_natural_position=True,
            )
            selected_rows.append((slot, best_player, score, natural_position))
            remaining.remove(best_player)

        starting_eleven = [
            SelectedPlayerView(
                player_id=player.player_id,
                name=player.name,
                slot=slot,
                rating=player.rating,
                age=player.age,
                fatigue=player.fatigue,
                form=player.form,
                selection_score=round(score, 2),
                natural_position=natural_position,
            )
            for slot, player, score, natural_position in selected_rows
        ]

        bench_candidates = sorted(
            remaining,
            key=lambda player: self._overall_player_score(player=player, profile=profile),
            reverse=True,
        )[: payload.bench_size]
        bench = [
            SelectedPlayerView(
                player_id=player.player_id,
                name=player.name,
                slot=_normalize_position(player.primary_position),
                rating=player.rating,
                age=player.age,
                fatigue=player.fatigue,
                form=player.form,
                selection_score=round(self._overall_player_score(player=player, profile=profile), 2),
                natural_position=True,
            )
            for player in bench_candidates
        ]

        line_height = self._line_height(profile=profile, defensive_variant=defensive_variant)
        pressing = self._pressing(profile=profile, defensive_variant=defensive_variant)
        tempo = self._tempo(profile=profile, defensive_variant=defensive_variant)
        attack_bias = round(
            _clamp01(
                0.42
                + (profile.personality_profile.aggression * 0.25)
                + (profile.risk_tolerance * 0.18)
                + (0.06 if not defensive_variant else -0.08)
            ),
            2,
        )
        rationale = [
            "Defensive variant selected because the club is the underdog or the squad is carrying fatigue/injury pressure."
            if defensive_variant
            else "Attacking variant selected because the squad is stable enough to lean into the manager's style.",
            f"Opponent strength {payload.opponent.strength} vs club strength {payload.club_strength} shaped the initial formation choice.",
        ]
        if any(player.age <= 21 for _, player, _, _ in selected_rows) and profile.personality_profile.youth_bias >= 0.6:
            rationale.append("Youth-biased profile pushed high-upside younger players into the starting XI.")

        role_assignments = [
            RoleAssignmentView(
                slot=slot,
                player_id=player.player_id,
                role=self._role_for_slot(slot=slot, style=profile.tactical_style, aggression=profile.personality_profile.aggression),
            )
            for slot, player, _, _ in selected_rows
        ]
        return SquadPlanView(
            formation=formation,
            line_height=line_height,
            pressing=pressing,
            tempo=tempo,
            attack_bias=attack_bias,
            starting_eleven=starting_eleven,
            bench=bench,
            role_assignments=role_assignments,
            rationale=rationale,
        )

    def _slot_score(
        self,
        *,
        player: ClubPlayerInput,
        slot: str,
        profile: AIManagerProfileView,
        return_natural_position: bool = False,
    ) -> float | tuple[float, bool]:
        fit_score, natural_position = self._fit_score(player=player, slot=slot)
        score = (
            (player.rating * 0.55)
            + (player.potential * 0.10)
            + (player.form * 18.0)
            + (player.stamina * 12.0)
            + (player.morale * 7.0)
            - (player.fatigue * 14.0)
            + fit_score
        )
        if player.age <= 21:
            score += profile.personality_profile.youth_bias * 6.0
        if player.availability is not PlayerAvailability.AVAILABLE:
            score -= 35.0
        rounded = round(score, 2)
        if return_natural_position:
            return rounded, natural_position
        return rounded

    def _overall_player_score(self, *, player: ClubPlayerInput, profile: AIManagerProfileView) -> float:
        score = (
            (player.rating * 0.60)
            + (player.potential * 0.10)
            + (player.form * 20.0)
            + (player.stamina * 10.0)
            + (player.morale * 6.0)
            - (player.fatigue * 10.0)
        )
        if player.age <= 21:
            score += profile.personality_profile.youth_bias * 5.0
        if player.availability is not PlayerAvailability.AVAILABLE:
            score -= 25.0
        return round(score, 2)

    def _fit_score(self, *, player: ClubPlayerInput, slot: str) -> tuple[float, bool]:
        normalized_slot = _normalize_position(slot)
        positions = _player_positions(player)
        if normalized_slot in positions:
            return 28.0, True
        if any(_position_group(position) == _position_group(normalized_slot) for position in positions):
            return 18.0, False
        return 4.0, False

    def _line_height(self, *, profile: AIManagerProfileView, defensive_variant: bool) -> LineHeight:
        base = 0.35 + (profile.personality_profile.aggression * 0.40) + (profile.risk_tolerance * 0.15)
        if defensive_variant:
            base -= 0.24
        if base >= 0.72:
            return LineHeight.HIGH
        if base >= 0.48:
            return LineHeight.MEDIUM
        return LineHeight.LOW

    def _pressing(self, *, profile: AIManagerProfileView, defensive_variant: bool) -> PressingIntensity:
        base = (profile.personality_profile.aggression * 0.70) + (profile.personality_profile.discipline * 0.20)
        if defensive_variant:
            base -= 0.10
        if base >= 0.72:
            return PressingIntensity.HIGH
        if base >= 0.43:
            return PressingIntensity.MEDIUM
        return PressingIntensity.LOW

    def _tempo(self, *, profile: AIManagerProfileView, defensive_variant: bool) -> TempoSetting:
        if defensive_variant and profile.tactical_style in {ManagerTacticalStyle.POSSESSION, ManagerTacticalStyle.BALANCED}:
            return TempoSetting.SLOW
        if profile.tactical_style in {ManagerTacticalStyle.DIRECT, ManagerTacticalStyle.COUNTER} or profile.risk_tolerance >= 0.65:
            return TempoSetting.FAST
        return TempoSetting.NORMAL

    def _role_for_slot(self, *, slot: str, style: ManagerTacticalStyle, aggression: float) -> str:
        normalized_slot = _normalize_position(slot)
        if normalized_slot == "GK":
            return "sweeper_keeper" if style is ManagerTacticalStyle.POSSESSION or aggression >= 0.6 else "shot_stopper"
        if normalized_slot == "CB":
            return "stopper" if aggression >= 0.6 else "cover_defender"
        if normalized_slot in {"RB", "LB", "RWB", "LWB"}:
            return "overlapping_fullback" if aggression >= 0.55 else "stay_back_fullback"
        if normalized_slot == "DM":
            return "anchor_playmaker" if style is ManagerTacticalStyle.POSSESSION else "screening_midfielder"
        if normalized_slot == "CM":
            if style is ManagerTacticalStyle.POSSESSION:
                return "controller"
            if style is ManagerTacticalStyle.DIRECT:
                return "box_to_box"
            return "shuttler"
        if normalized_slot == "AM":
            return "creator" if style is ManagerTacticalStyle.POSSESSION else "shadow_runner"
        if normalized_slot in {"RW", "LW", "RM", "LM"}:
            return "wide_creator" if style is ManagerTacticalStyle.POSSESSION else "inside_forward"
        if normalized_slot == "ST":
            if style is ManagerTacticalStyle.DIRECT:
                return "target_forward"
            if style is ManagerTacticalStyle.COUNTER or aggression >= 0.65:
                return "pressing_forward"
            if style is ManagerTacticalStyle.POSSESSION:
                return "false_nine"
            return "advanced_forward"
        return "balanced_role"


@dataclass(frozen=True, slots=True)
class MatchDecisionEngine:
    def evaluate(self, *, profile: AIManagerProfileView, payload: LiveMatchDecisionRequest) -> LiveDecisionResponse:
        goal_difference = payload.score_for - payload.score_against
        xg_difference = payload.xg_for - payload.xg_against
        average_fatigue = payload.average_fatigue if payload.average_fatigue is not None else 1.0 - payload.average_stamina
        attack_bias = _clamp01(0.40 + (profile.personality_profile.aggression * 0.22) + (profile.risk_tolerance * 0.20))
        formation = STYLE_FORMATIONS[profile.tactical_style]["attacking"]
        tempo = TempoSetting.NORMAL
        line_height = LineHeight.MEDIUM
        pressing = PressingIntensity.MEDIUM
        waste_time_behavior = False
        trigger_substitution = False
        substitution_reason: str | None = None
        directive = "hold_shape"
        rationale: list[str] = []

        if payload.minute >= 70 and (goal_difference < 0 or xg_difference <= -0.5):
            attack_bias = _clamp01(attack_bias + 0.24)
            formation = "3-4-3"
            tempo = TempoSetting.FAST
            pressing = PressingIntensity.HIGH
            line_height = LineHeight.HIGH if payload.red_cards_for == 0 else LineHeight.MEDIUM
            directive = "go_all_out_attack"
            rationale.append("Late scoreboard or xG deficit triggers an all-out attacking switch with a higher line and faster tempo.")
            if payload.substitutions_used < payload.maximum_substitutions:
                trigger_substitution = True
                substitution_reason = "Fresh attacking legs are needed while chasing the match."
        elif goal_difference > 0 and payload.minute > 75:
            attack_bias = _clamp01(attack_bias - 0.18)
            formation = STYLE_FORMATIONS[profile.tactical_style]["defensive"]
            tempo = TempoSetting.SLOW
            line_height = LineHeight.LOW
            pressing = PressingIntensity.LOW
            waste_time_behavior = True
            directive = "protect_lead"
            rationale.append("Leading late in the match shifts the plan toward control, slower tempo, and game management.")

        if payload.possession_share < 0.40 and goal_difference <= 0:
            pressing = PressingIntensity.HIGH
            line_height = LineHeight.HIGH if payload.red_cards_for == 0 else line_height
            attack_bias = _clamp01(attack_bias + 0.08)
            directive = "increase_pressing" if directive == "hold_shape" else directive
            rationale.append("Low possession share without a lead calls for a more aggressive press to recover territory.")

        if payload.red_cards_for > payload.red_cards_against:
            attack_bias = _clamp01(attack_bias - 0.12)
            formation = STYLE_FORMATIONS[profile.tactical_style]["defensive"]
            line_height = LineHeight.LOW
            pressing = PressingIntensity.LOW
            directive = "stabilize_shape" if directive == "hold_shape" else directive
            rationale.append("The club is down a player, so the defensive line drops to limit transition exposure.")
        elif payload.red_cards_against > payload.red_cards_for and goal_difference <= 0:
            attack_bias = _clamp01(attack_bias + 0.10)
            line_height = LineHeight.HIGH
            pressing = PressingIntensity.HIGH
            rationale.append("The opponent is down a player, so the team can pin them deeper and sustain pressure.")

        if (payload.average_stamina <= 0.70 or average_fatigue >= 0.30) and payload.substitutions_used < payload.maximum_substitutions:
            trigger_substitution = True
            substitution_reason = substitution_reason or "Fatigue has moved beyond the safe workload threshold."
            rationale.append("Fatigue has crossed the substitution threshold and risks late-match drop-off.")

        if payload.opponent_switched_shape and profile.personality_profile.adaptability >= 0.6:
            directive = "counter_adjustment" if directive == "hold_shape" else directive
            rationale.append("High adaptability triggers an immediate response to the opponent's shape switch.")

        if not rationale:
            rationale.append("Current state does not justify a major tactical swing, so the base plan holds.")

        return LiveDecisionResponse(
            directive=directive,
            formation=formation,
            attack_bias=round(attack_bias, 2),
            tempo=tempo,
            line_height=line_height,
            pressing=pressing,
            waste_time_behavior=waste_time_behavior,
            trigger_substitution=trigger_substitution,
            substitution_reason=substitution_reason,
            rationale=rationale,
        )


@dataclass(frozen=True, slots=True)
class FinanceController:
    def review(
        self,
        *,
        profile: AIManagerProfileView,
        squad: list[ClubPlayerInput],
        finance: ClubFinanceContextInput,
    ) -> list[FinanceActionView]:
        actions: list[FinanceActionView] = []
        wage_ratio = finance.wage_bill / finance.revenue
        reserve_floor = int(finance.revenue * 0.15)
        expensive_player = self._high_cost_player(squad)

        if wage_ratio > 0.70 and expensive_player is not None:
            actions.append(
                FinanceActionView(
                    action="sell_high_cost_player",
                    rationale=(
                        f"Wage-to-revenue ratio is {wage_ratio:.2f}, so {expensive_player.name} becomes the cost-control sale candidate."
                    ),
                )
            )

        if finance.transfer_budget <= int(finance.revenue * 0.05) or finance.cash_balance < reserve_floor:
            actions.append(
                FinanceActionView(
                    action="prioritize_free_agents",
                    rationale="Liquidity is tight, so recruitment should lean toward free agents and low-commitment deals.",
                )
            )

        if profile.financial_strategy is FinancialStrategy.SUSTAINABLE and finance.cash_balance <= int(finance.revenue * 0.25):
            actions.append(
                FinanceActionView(
                    action="freeze_risky_spend",
                    rationale="Sustainable financial strategy keeps a cash buffer and blocks nonessential spend at the current reserve level.",
                )
            )
        elif profile.financial_strategy is FinancialStrategy.AGGRESSIVE and finance.cash_balance > int(finance.revenue * 0.40):
            actions.append(
                FinanceActionView(
                    action="reinvest_in_squad",
                    rationale="Aggressive financial strategy allows selective reinvestment because the club is still above its reserve floor.",
                )
            )

        if not actions:
            actions.append(
                FinanceActionView(
                    action="maintain_stability",
                    rationale="Finances are inside the safety rails, so the club can hold its current operating plan.",
                )
            )
        return actions

    def _high_cost_player(self, squad: list[ClubPlayerInput]) -> ClubPlayerInput | None:
        if not squad:
            return None
        return max(squad, key=lambda player: (player.wage_cost, player.age, -player.form))


@dataclass(frozen=True, slots=True)
class TransferAgent:
    cooldown_hours: float = 24.0

    def evaluate(
        self,
        *,
        profile: AIManagerProfileView,
        squad: list[ClubPlayerInput],
        finance: ClubFinanceContextInput,
        market: TransferMarketContextInput,
    ) -> list[TransferRecommendationView]:
        if market.hours_since_last_transfer < self.cooldown_hours:
            return [
                TransferRecommendationView(
                    action="hold",
                    rationale="Transfer cooldown is still active, so the club should avoid back-to-back market moves.",
                )
            ]

        actions: list[TransferRecommendationView] = []
        reserve_floor = int(finance.revenue * 0.15)
        average_wage = max(1.0, finance.wage_bill / max(len(squad), 1))
        constrained_budget = finance.transfer_budget <= int(finance.revenue * 0.05) or finance.cash_balance < reserve_floor

        affordable_targets: list[tuple[TransferTargetInput, float]] = []
        free_agents: list[tuple[TransferTargetInput, float]] = []
        for target in market.targets:
            if not target.is_free_agent:
                if target.asking_price > finance.transfer_budget:
                    continue
                if finance.cash_balance - target.asking_price < reserve_floor:
                    continue
            score = self._target_score(profile=profile, target=target, average_wage=average_wage)
            if target.is_free_agent:
                free_agents.append((target, score))
            affordable_targets.append((target, score))

        if constrained_budget and free_agents:
            target, score = max(free_agents, key=lambda item: item[1])
            actions.append(
                TransferRecommendationView(
                    action="sign_free_agent",
                    player_name=target.name,
                    score=round(score, 2),
                    rationale="Budget pressure is high, so the best-value free agent becomes the preferred move.",
                )
            )
        elif affordable_targets:
            target, score = max(affordable_targets, key=lambda item: item[1])
            actions.append(
                TransferRecommendationView(
                    action="sign_free_agent" if target.is_free_agent else "buy_player",
                    player_name=target.name,
                    score=round(score, 2),
                    rationale="Target score blends skill, potential, tactical fit, and wage efficiency inside the club guardrails.",
                )
            )

        youth_candidate = self._youth_candidate(squad)
        if youth_candidate is not None and profile.personality_profile.youth_bias >= 0.65:
            actions.append(
                TransferRecommendationView(
                    action="promote_youth",
                    player_name=youth_candidate.name,
                    score=round(float(youth_candidate.potential), 2),
                    rationale="Strong youth bias promotes an internal prospect instead of forcing another external buy.",
                )
            )

        if finance.wage_bill / finance.revenue > 0.70:
            sell_candidate = self._sell_candidate(squad)
            if sell_candidate is not None:
                actions.append(
                    TransferRecommendationView(
                        action="sell_underperformer",
                        player_name=sell_candidate.name,
                        score=None,
                        rationale="Wage pressure is above the safe threshold, so an expensive underperformer should be moved on.",
                    )
                )

        if not actions:
            actions.append(
                TransferRecommendationView(
                    action="hold",
                    rationale="No target clears the tactical and financial guardrails, so the club should hold its position.",
                )
            )
        return actions[:3]

    def _target_score(
        self,
        *,
        profile: AIManagerProfileView,
        target: TransferTargetInput,
        average_wage: float,
    ) -> float:
        wage_penalty = min(100.0, (target.wage_cost / average_wage) * 15.0)
        score = (
            (target.skill * 0.4)
            + (target.potential * 0.2)
            + ((target.fit_to_tactic * 100.0) * 0.3)
            - (wage_penalty * 0.1)
        )
        if target.age <= 21:
            score += profile.personality_profile.youth_bias * 5.0
        return round(score, 2)

    def _youth_candidate(self, squad: list[ClubPlayerInput]) -> ClubPlayerInput | None:
        candidates = [
            player
            for player in squad
            if player.age <= 20 and player.potential - player.rating >= 8 and player.availability is PlayerAvailability.AVAILABLE
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda player: (player.potential - player.rating, player.form, player.morale))

    def _sell_candidate(self, squad: list[ClubPlayerInput]) -> ClubPlayerInput | None:
        if not squad:
            return None
        return max(squad, key=lambda player: (player.wage_cost, player.age, 1.0 - player.form))


@dataclass(frozen=True, slots=True)
class TrainingOptimizer:
    def plan(self, *, profile: AIManagerProfileView, squad: list[ClubPlayerInput]) -> list[TrainingAssignmentView]:
        assignments: list[TrainingAssignmentView] = []
        ranked_players = sorted(
            squad,
            key=lambda player: (
                player.injury_risk >= 0.7,
                player.form < 0.45,
                player.potential - player.rating,
                -player.fatigue,
            ),
            reverse=True,
        )
        for player in ranked_players:
            focus, intensity, rationale = self._assignment(profile=profile, player=player)
            if focus is None:
                continue
            assignments.append(
                TrainingAssignmentView(
                    player_id=player.player_id,
                    player_name=player.name,
                    focus=focus,
                    intensity=intensity,
                    rationale=rationale,
                )
            )
            if len(assignments) == 5:
                break

        if assignments:
            return assignments

        stable_players = sorted(squad, key=lambda player: (player.form, player.stamina), reverse=True)[:3]
        return [
            TrainingAssignmentView(
                player_id=player.player_id,
                player_name=player.name,
                focus="maintenance",
                intensity="medium",
                rationale="Player is stable, so the weekly block can remain on general maintenance work.",
            )
            for player in stable_players
        ]

    def _assignment(
        self,
        *,
        profile: AIManagerProfileView,
        player: ClubPlayerInput,
    ) -> tuple[str | None, str | None, str | None]:
        if player.injury_risk >= 0.7 or player.fatigue >= 0.75:
            return (
                "recovery",
                "low",
                "Workload drops immediately because injury risk or fatigue is above the safe threshold.",
            )
        if player.form < 0.45:
            return (
                self._technical_focus(player.primary_position),
                "medium" if player.injury_risk < 0.5 else "low",
                "Poor form triggers a focused corrective block instead of generic training.",
            )
        if player.age <= 20 and player.potential - player.rating >= 8 and profile.personality_profile.youth_bias >= 0.55:
            return (
                "development",
                "high" if player.fatigue < 0.5 else "medium",
                "High-upside young player receives a development block because the manager leans toward youth progression.",
            )
        return None, None, None

    def _technical_focus(self, position: str) -> str:
        normalized = _normalize_position(position)
        if normalized == "GK":
            return "shot_stopping"
        if normalized in {"CB", "RB", "LB", "RWB", "LWB"}:
            return "defensive_shape"
        if normalized in {"DM", "CM", "AM"}:
            return "ball_retention"
        return "finishing"


@dataclass(frozen=True, slots=True)
class MonetizationPolicy:
    ai_reward_multiplier: float = 0.85
    ai_win_streak_cap: int = 3

    def summary(self, *, ai_active: bool) -> RewardPolicySummaryView:
        return RewardPolicySummaryView(
            ai_reward_multiplier=self.ai_reward_multiplier if ai_active else 1.0,
            ai_win_streak_bonus_cap=0.15 if ai_active else 0.0,
            premium_efficiency_tools=list(PREMIUM_EFFICIENCY_TOOLS),
            blocked_pay_to_win_paths=list(BLOCKED_PAY_TO_WIN_PATHS),
        )

    def preview(self, payload: RewardPreviewRequest) -> RewardPreviewResponse:
        division_multiplier = DIVISION_MULTIPLIERS[payload.division]
        raw_win_streak_bonus = payload.win_streak * 0.05
        applied_streak = min(payload.win_streak, self.ai_win_streak_cap) if payload.ai_active else payload.win_streak
        applied_win_streak_bonus = applied_streak * 0.05
        reward_multiplier = payload.difficulty_multiplier * division_multiplier * (1.0 + applied_win_streak_bonus)
        competitive_reward = round(payload.base_reward * reward_multiplier)
        tournament_bonus = round(payload.base_reward * payload.tournament_stage_weight)
        prize_pool_reward = round(payload.entry_fee_pool * payload.entry_fee_multiplier)
        subtotal = competitive_reward + tournament_bonus + prize_pool_reward
        ai_penalty_multiplier = self.ai_reward_multiplier if payload.ai_active else 1.0
        final_reward = round(subtotal * ai_penalty_multiplier)
        premium_tools = list(PREMIUM_EFFICIENCY_TOOLS) if payload.premium_features_enabled else []
        return RewardPreviewResponse(
            base_reward=payload.base_reward,
            final_reward=final_reward,
            division_multiplier=division_multiplier,
            raw_win_streak_bonus=round(raw_win_streak_bonus, 2),
            applied_win_streak_bonus=round(applied_win_streak_bonus, 2),
            reward_multiplier=round(reward_multiplier, 2),
            tournament_bonus=tournament_bonus,
            prize_pool_reward=prize_pool_reward,
            ai_penalty_multiplier=ai_penalty_multiplier,
            premium_efficiency_tools=premium_tools,
            blocked_pay_to_win_paths=list(BLOCKED_PAY_TO_WIN_PATHS),
            competitive_integrity_passed=True,
        )


@dataclass(slots=True)
class AIManagerService:
    profiles: dict[str, AIManagerProfileView] = field(default_factory=dict)
    activation_policy: ActivationPolicy = field(default_factory=ActivationPolicy)
    squad_planner: SquadPlanner = field(default_factory=SquadPlanner)
    match_decision_engine: MatchDecisionEngine = field(default_factory=MatchDecisionEngine)
    transfer_agent: TransferAgent = field(default_factory=TransferAgent)
    training_optimizer: TrainingOptimizer = field(default_factory=TrainingOptimizer)
    finance_controller: FinanceController = field(default_factory=FinanceController)
    monetization_policy: MonetizationPolicy = field(default_factory=MonetizationPolicy)

    def upsert_profile(self, payload: AIManagerProfileInput) -> AIManagerProfileView:
        profile = AIManagerProfileView(
            club_id=payload.club_id,
            personality_profile=payload.personality_profile,
            tactical_style=payload.tactical_style,
            financial_strategy=payload.financial_strategy,
            risk_tolerance=round(payload.risk_tolerance if payload.risk_tolerance is not None else payload.personality_profile.risk, 2),
        )
        self.profiles[payload.club_id] = profile
        return profile

    def get_profile(self, club_id: str) -> AIManagerProfileView:
        profile = self.profiles.get(club_id)
        if profile is None:
            profile = self._default_profile(club_id)
            self.profiles[club_id] = profile
        return profile

    def run_autopilot(self, payload: AutopilotRunRequest) -> AutopilotRunResponse:
        profile = self.upsert_profile(payload.manager_override) if payload.manager_override is not None else self.get_profile(payload.club_id)
        activation = self.activation_policy.evaluate(user_last_active_hours=payload.user_last_active_hours)
        squad_plan = self.squad_planner.plan(profile=profile, payload=payload)
        finance_actions = self.finance_controller.review(profile=profile, squad=payload.squad, finance=payload.finance)
        transfer_actions = self.transfer_agent.evaluate(
            profile=profile,
            squad=payload.squad,
            finance=payload.finance,
            market=payload.market,
        )
        training_plan = self.training_optimizer.plan(profile=profile, squad=payload.squad)
        reward_policy = self.monetization_policy.summary(ai_active=activation.ai_active)
        decision_log = self._decision_log(
            activation=activation,
            squad_plan=squad_plan,
            finance_actions=finance_actions,
            transfer_actions=transfer_actions,
            opponent=payload.opponent,
        )
        return AutopilotRunResponse(
            manager=profile,
            activation=activation,
            squad_plan=squad_plan,
            transfer_actions=transfer_actions,
            training_plan=training_plan,
            finance_actions=finance_actions,
            reward_policy=reward_policy,
            decision_log=decision_log,
        )

    def evaluate_live_decision(self, payload: LiveMatchDecisionRequest) -> LiveDecisionResponse:
        profile = self.upsert_profile(payload.manager_override) if payload.manager_override is not None else self.get_profile(payload.club_id)
        return self.match_decision_engine.evaluate(profile=profile, payload=payload)

    def preview_reward(self, payload: RewardPreviewRequest) -> RewardPreviewResponse:
        return self.monetization_policy.preview(payload)

    def _default_profile(self, club_id: str) -> AIManagerProfileView:
        digest = sha256(club_id.encode("utf-8")).hexdigest()
        tactical_styles = list(ManagerTacticalStyle)
        financial_strategies = list(FinancialStrategy)
        personality = PersonalityProfileInput(
            aggression=round(0.2 + (int(digest[0:2], 16) / 255) * 0.65, 2),
            risk=round(0.2 + (int(digest[2:4], 16) / 255) * 0.65, 2),
            youth_bias=round(0.2 + (int(digest[4:6], 16) / 255) * 0.65, 2),
            discipline=round(0.2 + (int(digest[6:8], 16) / 255) * 0.65, 2),
            adaptability=round(0.2 + (int(digest[8:10], 16) / 255) * 0.65, 2),
        )
        return AIManagerProfileView(
            club_id=club_id,
            personality_profile=personality,
            tactical_style=tactical_styles[int(digest[10:12], 16) % len(tactical_styles)],
            financial_strategy=financial_strategies[int(digest[12:14], 16) % len(financial_strategies)],
            risk_tolerance=personality.risk,
        )

    def _decision_log(
        self,
        *,
        activation: AutopilotActivationView,
        squad_plan: SquadPlanView,
        finance_actions: list[FinanceActionView],
        transfer_actions: list[TransferRecommendationView],
        opponent: OpponentContextInput,
    ) -> list[str]:
        return [
            activation.summary,
            f"Pre-match setup selected {squad_plan.formation} with {squad_plan.line_height.value} line height against {opponent.club_name}.",
            f"Top finance action: {finance_actions[0].action}.",
            f"Top transfer action: {transfer_actions[0].action}.",
        ]


__all__ = ["AIManagerService"]
