from __future__ import annotations

from dataclasses import dataclass

from app.services.player_agency_context_service import (
    AgencyClubContext,
    AgencyDecisionOutcome,
    AgencyPlayerContext,
    AgencyReason,
    ContractEvaluationInput,
    clamp,
)


@dataclass(slots=True)
class ContractDecisionService:
    def evaluate(
        self,
        *,
        player_context: AgencyPlayerContext,
        club_context: AgencyClubContext,
        offer: ContractEvaluationInput,
    ) -> AgencyDecisionOutcome:
        target_weights = self._target_weights(player_context.career_target_band)
        same_club_offer = club_context.club_id == player_context.current_club.club_id
        wage_ratio = float(offer.offered_wage_amount / max(player_context.salary_expectation_amount, player_context.current_wage_amount or 1))
        wage_score = clamp((wage_ratio * 72.0) + (15.0 if offer.offered_wage_amount > player_context.current_wage_amount else 0.0))
        length_score = self._length_score(player_context.career_stage, offer.contract_years)
        role_score = self._role_score(player_context.preferred_role_band, offer.role_promised, club_context.expected_minutes_score)
        release_clause_score = self._release_clause_score(player_context, offer)
        bonus_score = clamp(float(offer.bonus_amount or 0) / max(float(offer.offered_wage_amount or 1), 1.0) * 100.0)
        development_score = clamp((club_context.development_score * 0.75) + (club_context.expected_minutes_score * 0.25))
        project_score = club_context.project_attractiveness
        congestion_score = clamp(100.0 - club_context.squad_congestion)
        current_club_penalty = 0.0
        if not same_club_offer:
            current_club_penalty = clamp(
                (player_context.personality.loyalty * 0.22)
                + (player_context.state.happiness * 0.10)
                + (player_context.current_club.project_attractiveness * 0.12)
            )
            if (
                player_context.career_target_band == "development-first"
                and development_score >= 78.0
                and club_context.club_stature >= player_context.current_club.club_stature + 10.0
            ):
                current_club_penalty *= 0.45
            elif (
                player_context.career_target_band in {"prestige-first", "trophy-first"}
                and club_context.club_stature >= player_context.current_club.club_stature + 12.0
            ):
                current_club_penalty *= 0.60
        morale_score = clamp((player_context.state.morale * 0.65) + (player_context.state.happiness * 0.35))

        component_scores = {
            "wage": round(wage_score, 2),
            "length": round(length_score, 2),
            "role": round(role_score, 2),
            "release_clause": round(release_clause_score, 2),
            "bonus": round(bonus_score, 2),
            "stature": round(club_context.club_stature, 2),
            "league_quality": round(club_context.league_quality, 2),
            "development": round(development_score, 2),
            "project": round(project_score, 2),
            "congestion": round(congestion_score, 2),
            "morale": round(morale_score, 2),
            "current_club_pull": round(current_club_penalty, 2),
        }
        decision_weight_breakdown = {
            "wage_weight": round(wage_score * target_weights["wage"], 2),
            "contract_length_weight": round(length_score * 0.08, 2),
            "role_weight": round(role_score * target_weights["role"], 2),
            "release_clause_weight": round(release_clause_score * 0.05, 2),
            "bonus_weight": round(bonus_score * 0.03, 2),
            "club_prestige_weight": round(club_context.club_stature * target_weights["prestige"], 2),
            "league_quality_weight": round(club_context.league_quality * 0.07, 2),
            "development_weight": round(development_score * target_weights["development"], 2),
            "club_project_weight": round(project_score * 0.10, 2),
            "squad_congestion_weight": round(congestion_score * 0.06, 2),
            "morale_weight": round(morale_score * 0.06, 2),
            "current_club_pull_weight": round(-current_club_penalty, 2),
            "grievance_weight": round(-(player_context.state.grievance_count * 3.5), 2),
        }
        weighted_score = clamp(
            (wage_score * target_weights["wage"])
            + (length_score * 0.08)
            + (role_score * target_weights["role"])
            + (release_clause_score * 0.05)
            + (bonus_score * 0.03)
            + (club_context.club_stature * target_weights["prestige"])
            + (club_context.league_quality * 0.07)
            + (development_score * target_weights["development"])
            + (project_score * 0.10)
            + (congestion_score * 0.06)
            + (morale_score * 0.06)
            - current_club_penalty
            - (player_context.state.grievance_count * 3.5)
        )
        if offer.offered_wage_amount < player_context.current_wage_amount and player_context.personality.greed >= 55:
            weighted_score = clamp(weighted_score - 12.0)
            decision_weight_breakdown["greed_penalty_weight"] = -12.0
        if role_score < 45.0 and player_context.personality.ego >= 68:
            weighted_score = clamp(weighted_score - 10.0)
            decision_weight_breakdown["ego_role_penalty_weight"] = -10.0
        if offer.is_renewal and player_context.state.transfer_request_status in {"transfer_request", "public_unhappy_state"}:
            weighted_score = clamp(weighted_score - 9.0)
            decision_weight_breakdown["renewal_unrest_penalty_weight"] = -9.0

        decision_code = self._decision_code(
            score=weighted_score,
            player_context=player_context,
            club_context=club_context,
            offer=offer,
            wage_score=wage_score,
            role_score=role_score,
            development_score=development_score,
        )
        reasons = self._reasons(
            player_context=player_context,
            club_context=club_context,
            component_scores=component_scores,
            offer=offer,
        )
        persuading_factors = self._persuading_factors(
            wage_score=wage_score,
            role_score=role_score,
            development_score=development_score,
            project_score=project_score,
            length_score=length_score,
            release_clause_score=release_clause_score,
        )
        return AgencyDecisionOutcome(
            decision_code=decision_code,
            decision_score=round(weighted_score, 2),
            confidence_band=self._confidence_band(weighted_score),
            primary_reasons=reasons[:3],
            secondary_reasons=reasons[3:6],
            persuading_factors=persuading_factors,
            component_scores=component_scores,
            decision_weight_breakdown=decision_weight_breakdown,
        )

    def _target_weights(self, career_target_band: str) -> dict[str, float]:
        if career_target_band == "money-first":
            return {"wage": 0.24, "role": 0.10, "prestige": 0.11, "development": 0.08}
        if career_target_band == "minutes-first":
            return {"wage": 0.12, "role": 0.22, "prestige": 0.08, "development": 0.12}
        if career_target_band == "prestige-first":
            return {"wage": 0.14, "role": 0.12, "prestige": 0.18, "development": 0.10}
        if career_target_band == "trophy-first":
            return {"wage": 0.12, "role": 0.12, "prestige": 0.17, "development": 0.09}
        if career_target_band == "stability-first":
            return {"wage": 0.14, "role": 0.13, "prestige": 0.10, "development": 0.09}
        return {"wage": 0.15, "role": 0.15, "prestige": 0.11, "development": 0.14}

    def _length_score(self, career_stage: str, contract_years: int) -> float:
        if career_stage in {"wonderkid", "prospect"}:
            return {1: 48.0, 2: 72.0, 3: 90.0, 4: 72.0, 5: 58.0}.get(contract_years, 58.0)
        if career_stage in {"prime", "established", "breakout"}:
            return {1: 55.0, 2: 82.0, 3: 88.0, 4: 72.0, 5: 52.0}.get(contract_years, 52.0)
        return {1: 92.0, 2: 86.0, 3: 64.0, 4: 42.0, 5: 24.0}.get(contract_years, 24.0)

    def _role_score(self, preferred_role_band: str, role_promised: str | None, expected_minutes_score: float) -> float:
        role_map = {
            "rotation": 56.0,
            "breakthrough": 66.0,
            "starter": 84.0,
            "star": 95.0,
            "leading": 95.0,
            "first_team": 82.0,
        }
        promised_score = role_map.get((role_promised or "").strip().lower())
        if promised_score is None:
            promised_score = expected_minutes_score
        preference_bonus = 8.0 if preferred_role_band in {(role_promised or "").strip().lower(), "rotation"} else 0.0
        return clamp((promised_score * 0.72) + (expected_minutes_score * 0.28) + preference_bonus)

    def _release_clause_score(self, player_context: AgencyPlayerContext, offer: ContractEvaluationInput) -> float:
        if offer.release_clause_amount is None:
            return 58.0 if player_context.personality.ambition >= 68 else 64.0
        if player_context.personality.ambition >= 70 or player_context.personality.development_focus >= 70:
            return 86.0
        return 72.0

    def _decision_code(
        self,
        *,
        score: float,
        player_context: AgencyPlayerContext,
        club_context: AgencyClubContext,
        offer: ContractEvaluationInput,
        wage_score: float,
        role_score: float,
        development_score: float,
    ) -> str:
        same_club_renewal = offer.is_renewal and club_context.club_id == player_context.current_club.club_id
        if same_club_renewal and player_context.personality.loyalty >= 70 and role_score >= 70.0:
            if player_context.career_stage == "veteran" and wage_score >= 44.0:
                return "accept"
            if wage_score < 44.0 or player_context.state.wage_satisfaction < 44.0:
                return "requests_renegotiation"
            return "accept"
        if (
            not same_club_renewal
            and player_context.career_target_band == "development-first"
            and development_score >= 80.0
            and role_score >= 72.0
            and club_context.club_stature >= player_context.current_club.club_stature + 10.0
            and wage_score >= 40.0
        ):
            return "accept"
        if offer.is_renewal and player_context.state.transfer_request_status in {"transfer_request", "public_unhappy_state"} and score < 68.0:
            return "reject"
        if offer.is_renewal and club_context.club_id == player_context.current_club.club_id and score < 56.0 and player_context.personality.loyalty >= 68:
            return "prefers_to_stay_on_current_terms"
        if score >= 78.0:
            return "accept"
        if score >= 66.0:
            if wage_score < 62.0 or role_score < 60.0:
                return "accept_if_improved_terms"
            return "accept"
        if score >= 55.0:
            if wage_score < 62.0 or role_score < 58.0:
                return "requests_renegotiation"
            return "delay_undecided"
        if offer.is_renewal and player_context.personality.loyalty >= 70 and score >= 45.0:
            return "prefers_to_stay_on_current_terms"
        if score >= 46.0:
            return "delay_undecided"
        return "reject"

    def _reasons(
        self,
        *,
        player_context: AgencyPlayerContext,
        club_context: AgencyClubContext,
        component_scores: dict[str, float],
        offer: ContractEvaluationInput,
    ) -> tuple[AgencyReason, ...]:
        reasons: list[AgencyReason] = []
        if component_scores["wage"] >= 68.0:
            reasons.append(AgencyReason("wage_upside", "The wage package beats the current expectation.", component_scores["wage"] - 50.0))
        elif component_scores["wage"] <= 50.0:
            reasons.append(AgencyReason("wage_shortfall", "The wage offer does not meet the current expectation.", 50.0 - component_scores["wage"]))
        if component_scores["role"] >= 68.0:
            reasons.append(AgencyReason("role_pathway", "The promised role gives a credible route to minutes.", component_scores["role"] - 50.0))
        elif component_scores["role"] <= 50.0:
            reasons.append(AgencyReason("role_risk", "The squad role looks too small for the player’s expectations.", 50.0 - component_scores["role"]))
        if component_scores["development"] >= 65.0:
            reasons.append(AgencyReason("development_fit", "The club setup supports the next stage of development.", component_scores["development"] - 50.0))
        if component_scores["stature"] >= 68.0:
            reasons.append(AgencyReason("club_stature", "The club stature aligns with the player’s ambition.", component_scores["stature"] - 50.0))
        if component_scores["project"] <= 52.0:
            reasons.append(AgencyReason("project_doubt", "The wider club project is not convincing enough.", 52.0 - component_scores["project"]))
        if component_scores["current_club_pull"] >= 16.0:
            reasons.append(AgencyReason("current_club_pull", "Loyalty and comfort at the current club still matter.", component_scores["current_club_pull"]))
        if player_context.state.grievance_count >= 2 and not offer.is_renewal:
            reasons.append(AgencyReason("wants_change", "Existing grievances make a fresh project more attractive.", player_context.state.grievance_count * 5.0))
        if component_scores["length"] <= 48.0:
            reasons.append(AgencyReason("length_mismatch", "The contract length does not fit the current career stage.", 50.0 - component_scores["length"]))
        return tuple(sorted(reasons, key=lambda item: item.weight, reverse=True))

    def _persuading_factors(
        self,
        *,
        wage_score: float,
        role_score: float,
        development_score: float,
        project_score: float,
        length_score: float,
        release_clause_score: float,
    ) -> tuple[str, ...]:
        factors: list[str] = []
        if wage_score < 65.0:
            factors.append("Improve the wage package.")
        if role_score < 62.0:
            factors.append("Offer a bigger squad role and clearer minutes.")
        if development_score < 60.0:
            factors.append("Present a stronger development plan.")
        if project_score < 60.0:
            factors.append("Sell the long-term club project more clearly.")
        if length_score < 55.0:
            factors.append("Adjust the contract length to fit the career stage.")
        if release_clause_score < 62.0:
            factors.append("Add a more realistic release clause.")
        return tuple(factors[:3])

    def _confidence_band(self, score: float) -> str:
        if score >= 82.0 or score <= 38.0:
            return "high"
        if score >= 70.0 or score <= 48.0:
            return "medium"
        return "low"
