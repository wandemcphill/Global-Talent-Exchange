from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.services.player_agency_context_service import (
    AgencyClubContext,
    AgencyDecisionOutcome,
    AgencyPlayerContext,
    AgencyReason,
    TransferEvaluationInput,
    clamp,
)


@dataclass(slots=True)
class TransferDecisionService:
    def evaluate_move(
        self,
        *,
        player_context: AgencyPlayerContext,
        club_context: AgencyClubContext,
        move: TransferEvaluationInput,
    ) -> AgencyDecisionOutcome:
        target_weights = self._target_weights(player_context.career_target_band)
        wage_ratio = float(move.offered_wage_amount / max(player_context.salary_expectation_amount, player_context.current_wage_amount or 1))
        wage_score = clamp((wage_ratio * 70.0) + (18.0 if move.offered_wage_amount > player_context.current_wage_amount else 0.0))
        minutes_score = clamp((club_context.expected_minutes_score * 0.76) + self._role_bonus(move.expected_role))
        development_score = clamp((club_context.development_score * 0.72) + (minutes_score * 0.28))
        prestige_gain = clamp(50.0 + ((club_context.club_stature - player_context.current_club.club_stature) * 1.2))
        league_gain = clamp(50.0 + ((club_context.league_quality - player_context.current_club.league_quality) * 1.2))
        continental_score = 88.0 if club_context.continental_football else 42.0
        bench_security = clamp(100.0 - club_context.bench_risk)
        grievance_drive = clamp(
            (100.0 - player_context.state.morale) * 0.28
            + (100.0 - player_context.state.playing_time_satisfaction) * 0.24
            + (100.0 - player_context.state.club_project_belief) * 0.18
            + (player_context.state.grievance_count * 7.0)
            + (14.0 if self._denied_recently(player_context, move) else 0.0)
        )
        loyalty_anchor = clamp(
            (player_context.personality.loyalty * 0.34)
            + (player_context.state.happiness * 0.18)
            + (player_context.current_club.project_attractiveness * 0.16)
        )
        component_scores = {
            "wage": round(wage_score, 2),
            "minutes": round(minutes_score, 2),
            "development": round(development_score, 2),
            "prestige_gain": round(prestige_gain, 2),
            "league_gain": round(league_gain, 2),
            "continental": round(continental_score, 2),
            "bench_security": round(bench_security, 2),
            "geography": round(club_context.geography_score, 2),
            "grievance_drive": round(grievance_drive, 2),
            "loyalty_anchor": round(loyalty_anchor, 2),
        }
        weighted_score = clamp(
            (wage_score * target_weights["wage"])
            + (minutes_score * target_weights["minutes"])
            + (development_score * target_weights["development"])
            + (prestige_gain * target_weights["prestige"])
            + (league_gain * 0.08)
            + (continental_score * 0.06)
            + (bench_security * 0.09)
            + (club_context.geography_score * 0.05)
            + (grievance_drive * 0.11)
            - (loyalty_anchor * 0.10)
        )
        if club_context.bench_risk >= 62.0 and player_context.personality.ego >= 70:
            weighted_score = clamp(weighted_score - 9.0)
        if move.offered_wage_amount < player_context.current_wage_amount and player_context.personality.greed >= 60:
            weighted_score = clamp(weighted_score - 10.0)

        decision_code = self._decision_code(
            score=weighted_score,
            player_context=player_context,
            prestige_gain=prestige_gain,
            wage_score=wage_score,
        )
        reasons = self._reasons(
            player_context=player_context,
            component_scores=component_scores,
        )
        return AgencyDecisionOutcome(
            decision_code=decision_code,
            decision_score=round(weighted_score, 2),
            confidence_band=self._confidence_band(weighted_score),
            primary_reasons=reasons[:3],
            secondary_reasons=reasons[3:6],
            persuading_factors=self._persuading_factors(component_scores),
            component_scores=component_scores,
        )

    def evaluate_transfer_request(self, *, player_context: AgencyPlayerContext) -> AgencyDecisionOutcome:
        contract_urgency = 0.0
        if player_context.days_remaining is not None and player_context.days_remaining <= 180:
            contract_urgency = clamp(100.0 - (player_context.days_remaining / 2.0))
        denied_move_pressure = 18.0 if player_context.state.last_transfer_denial_at is not None else 0.0
        target_gap = max(0.0, player_context.personality.ambition - player_context.current_club.club_stature)
        decision_score = clamp(
            (100.0 - player_context.state.playing_time_satisfaction) * 0.25
            + (100.0 - player_context.state.wage_satisfaction) * 0.18
            + (100.0 - player_context.state.development_satisfaction) * 0.13
            + (100.0 - player_context.state.club_project_belief) * 0.16
            + (100.0 - player_context.state.morale) * 0.16
            + contract_urgency * 0.06
            + target_gap * 0.14
            + denied_move_pressure
            - (player_context.personality.loyalty * 0.10)
            - (player_context.personality.patience * 0.06)
        )
        decision_code = self._transfer_request_code(decision_score)
        if player_context.state.next_review_at is not None and datetime.combine(player_context.reference_on, datetime.min.time()) < player_context.state.next_review_at:
            existing_rank = self._status_rank(player_context.state.transfer_request_status)
            candidate_rank = self._status_rank(decision_code)
            if candidate_rank < existing_rank and decision_score >= max(0.0, self._status_floor(player_context.state.transfer_request_status) - 10.0):
                decision_code = player_context.state.transfer_request_status
                decision_score = max(decision_score, self._status_floor(decision_code) - 4.0)
        reasons = self._transfer_request_reasons(player_context=player_context, contract_urgency=contract_urgency, target_gap=target_gap)
        return AgencyDecisionOutcome(
            decision_code=decision_code,
            decision_score=round(decision_score, 2),
            confidence_band=self._confidence_band(decision_score),
            primary_reasons=reasons[:3],
            secondary_reasons=reasons[3:6],
            persuading_factors=self._transfer_request_persuaders(player_context),
            component_scores={
                "playing_time": round(100.0 - player_context.state.playing_time_satisfaction, 2),
                "wage": round(100.0 - player_context.state.wage_satisfaction, 2),
                "development": round(100.0 - player_context.state.development_satisfaction, 2),
                "project": round(100.0 - player_context.state.club_project_belief, 2),
                "morale": round(100.0 - player_context.state.morale, 2),
                "contract_urgency": round(contract_urgency, 2),
                "ambition_gap": round(target_gap, 2),
            },
        )

    def _target_weights(self, career_target_band: str) -> dict[str, float]:
        if career_target_band == "money-first":
            return {"wage": 0.24, "minutes": 0.10, "development": 0.08, "prestige": 0.10}
        if career_target_band == "minutes-first":
            return {"wage": 0.12, "minutes": 0.24, "development": 0.12, "prestige": 0.08}
        if career_target_band == "prestige-first":
            return {"wage": 0.13, "minutes": 0.12, "development": 0.10, "prestige": 0.18}
        if career_target_band == "trophy-first":
            return {"wage": 0.11, "minutes": 0.12, "development": 0.08, "prestige": 0.18}
        if career_target_band == "stability-first":
            return {"wage": 0.12, "minutes": 0.13, "development": 0.09, "prestige": 0.10}
        return {"wage": 0.14, "minutes": 0.18, "development": 0.15, "prestige": 0.12}

    def _role_bonus(self, expected_role: str | None) -> float:
        normalized = (expected_role or "").strip().lower()
        if normalized in {"star", "leading"}:
            return 16.0
        if normalized in {"starter", "first_team"}:
            return 10.0
        if normalized in {"breakthrough", "prospect"}:
            return 4.0
        if normalized in {"rotation", "squad"}:
            return -6.0
        return 0.0

    def _decision_code(
        self,
        *,
        score: float,
        player_context: AgencyPlayerContext,
        prestige_gain: float,
        wage_score: float,
    ) -> str:
        if score >= 82.0 and (player_context.state.transfer_appetite >= 68.0 or prestige_gain >= 62.0):
            return "requests_transfer_if_blocked"
        if score >= 74.0:
            return "eager_to_join"
        if score >= 62.0:
            return "open_to_join"
        if score >= 52.0:
            return "hesitant_needs_better_terms"
        if player_context.personality.loyalty >= 72 and player_context.state.morale >= 58 and wage_score < 82.0:
            return "prefers_current_club"
        return "rejects_move"

    def _reasons(
        self,
        *,
        player_context: AgencyPlayerContext,
        component_scores: dict[str, float],
    ) -> tuple[AgencyReason, ...]:
        reasons: list[AgencyReason] = []
        if component_scores["minutes"] >= 66.0:
            reasons.append(AgencyReason("minutes_path", "The move offers a stronger route to regular minutes.", component_scores["minutes"] - 50.0))
        elif component_scores["minutes"] <= 48.0:
            reasons.append(AgencyReason("bench_risk", "There is too much bench risk at the destination club.", 50.0 - component_scores["minutes"]))
        if component_scores["prestige_gain"] >= 62.0:
            reasons.append(AgencyReason("prestige_step", "The destination is a clear step up in stature.", component_scores["prestige_gain"] - 50.0))
        if component_scores["league_gain"] >= 58.0:
            reasons.append(AgencyReason("league_step", "The move improves league quality and exposure.", component_scores["league_gain"] - 50.0))
        if component_scores["wage"] >= 65.0:
            reasons.append(AgencyReason("wage_uplift", "The wage offer materially improves the current package.", component_scores["wage"] - 50.0))
        elif component_scores["wage"] <= 50.0:
            reasons.append(AgencyReason("wage_gap", "The wage offer is not persuasive enough for a move.", 50.0 - component_scores["wage"]))
        if component_scores["development"] >= 64.0:
            reasons.append(AgencyReason("development_fit", "The club looks like a strong development fit.", component_scores["development"] - 50.0))
        if component_scores["grievance_drive"] >= 20.0:
            reasons.append(AgencyReason("wants_change", "Current grievances make a move easier to justify.", component_scores["grievance_drive"]))
        if component_scores["loyalty_anchor"] >= 20.0:
            reasons.append(AgencyReason("current_club_pull", "Loyalty still pulls the player toward the current club.", component_scores["loyalty_anchor"]))
        if component_scores["geography"] <= 38.0 and player_context.personality.adaptability <= 48:
            reasons.append(AgencyReason("adaptation_risk", "The geography looks hard to adapt to right now.", 40.0 - component_scores["geography"]))
        return tuple(sorted(reasons, key=lambda item: item.weight, reverse=True))

    def _persuading_factors(self, component_scores: dict[str, float]) -> tuple[str, ...]:
        factors: list[str] = []
        if component_scores["wage"] < 65.0:
            factors.append("Increase the wage uplift.")
        if component_scores["minutes"] < 62.0:
            factors.append("Offer a clearer route to starts.")
        if component_scores["development"] < 60.0:
            factors.append("Show a better development pathway.")
        if component_scores["prestige_gain"] < 58.0:
            factors.append("Present a stronger competitive project.")
        return tuple(factors[:3])

    def _transfer_request_code(self, score: float) -> str:
        if score >= 82.0:
            return "public_unhappy_state"
        if score >= 68.0:
            return "transfer_request"
        if score >= 54.0:
            return "agent_warning"
        if score >= 38.0:
            return "private_unrest"
        return "no_action"

    def _transfer_request_reasons(
        self,
        *,
        player_context: AgencyPlayerContext,
        contract_urgency: float,
        target_gap: float,
    ) -> tuple[AgencyReason, ...]:
        reasons: list[AgencyReason] = []
        if player_context.state.playing_time_satisfaction <= 45.0:
            reasons.append(AgencyReason("playing_time", "Playing time has fallen below expectations.", 100.0 - player_context.state.playing_time_satisfaction))
        if player_context.state.wage_satisfaction <= 48.0:
            reasons.append(AgencyReason("wage_discontent", "Current wages are lagging behind expectations.", 100.0 - player_context.state.wage_satisfaction))
        if player_context.state.development_satisfaction <= 48.0:
            reasons.append(AgencyReason("development_stall", "Development feels stalled at the current club.", 100.0 - player_context.state.development_satisfaction))
        if player_context.state.club_project_belief <= 48.0:
            reasons.append(AgencyReason("project_doubt", "Belief in the club project has dropped.", 100.0 - player_context.state.club_project_belief))
        if player_context.state.morale <= 45.0:
            reasons.append(AgencyReason("low_morale", "Morale is now low enough to fuel unrest.", 100.0 - player_context.state.morale))
        if contract_urgency > 0:
            reasons.append(AgencyReason("contract_urgency", "The contract situation is becoming urgent.", contract_urgency))
        if target_gap > 8.0:
            reasons.append(AgencyReason("ambition_gap", "Ambition has outgrown the current project.", target_gap))
        if player_context.state.last_transfer_denial_at is not None:
            reasons.append(AgencyReason("denied_move", "A previously blocked move is still remembered.", 18.0))
        return tuple(sorted(reasons, key=lambda item: item.weight, reverse=True))

    def _transfer_request_persuaders(self, player_context: AgencyPlayerContext) -> tuple[str, ...]:
        factors: list[str] = []
        if player_context.state.playing_time_satisfaction < 55.0:
            factors.append("Deliver a clearer route to regular starts.")
        if player_context.state.wage_satisfaction < 55.0:
            factors.append("Improve wage terms.")
        if player_context.state.club_project_belief < 60.0:
            factors.append("Reinforce the club project with tangible ambition.")
        if player_context.state.development_satisfaction < 60.0:
            factors.append("Show a more credible development pathway.")
        return tuple(factors[:3])

    def _status_rank(self, status: str) -> int:
        return {
            "no_action": 0,
            "private_unrest": 1,
            "agent_warning": 2,
            "transfer_request": 3,
            "public_unhappy_state": 4,
        }.get(status, 0)

    def _status_floor(self, status: str) -> float:
        return {
            "no_action": 0.0,
            "private_unrest": 38.0,
            "agent_warning": 54.0,
            "transfer_request": 68.0,
            "public_unhappy_state": 82.0,
        }.get(status, 0.0)

    def _denied_recently(self, player_context: AgencyPlayerContext, move: TransferEvaluationInput) -> bool:
        if move.transfer_denied_recently is not None:
            return move.transfer_denied_recently
        return player_context.state.last_transfer_denial_at is not None

    def _confidence_band(self, score: float) -> str:
        if score >= 82.0 or score <= 36.0:
            return "high"
        if score >= 68.0 or score <= 50.0:
            return "medium"
        return "low"
