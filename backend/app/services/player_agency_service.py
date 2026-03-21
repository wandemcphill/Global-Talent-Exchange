from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.player_agency_state import PlayerAgencyState
from app.models.player_personality import PlayerPersonality
from app.models.regen import RegenOriginMetadata, RegenPersonalityProfile, RegenProfile
from app.schemas.player_agency import (
    AgencyDecisionView,
    AgencyReasonView,
    ContractDecisionRequest,
    ContractDecisionView,
    PlayerAgencySnapshotView,
    PlayerAgencyStateView,
    PlayerPersonalityView,
    TransferDecisionRequest,
    TransferDecisionView,
)
from app.services.contract_decision_service import ContractDecisionService
from app.services.player_agency_context_service import (
    AgencyDecisionOutcome,
    ContractEvaluationInput,
    PlayerAgencyContextService,
    TransferEvaluationInput,
    clamp,
    quantize_amount,
)
from app.services.transfer_decision_service import TransferDecisionService


@dataclass(slots=True)
class PlayerAgencyService:
    session: Session

    def __post_init__(self) -> None:
        self.context_service = PlayerAgencyContextService(self.session)
        self.contract_decision_service = ContractDecisionService()
        self.transfer_decision_service = TransferDecisionService()

    def get_snapshot(self, player_id: str, *, reference_on: date | None = None) -> PlayerAgencySnapshotView:
        player, regen, personality, state, transfer_request = self.sync(player_id, reference_on=reference_on)
        return PlayerAgencySnapshotView(
            player_id=player.id,
            regen_id=regen.regen_id,
            personality=self._to_personality_view(personality),
            state=self._to_state_view(state),
            transfer_request_decision=self._to_decision_view(transfer_request),
        )

    def evaluate_contract_offer(
        self,
        player_id: str,
        payload: ContractDecisionRequest,
        *,
        reference_on: date | None = None,
    ) -> ContractDecisionView:
        player, regen, personality, state, _transfer_request = self.sync(player_id, reference_on=reference_on or payload.requested_on)
        effective_date = reference_on or payload.requested_on or date.today()
        player_context = self.context_service.build_player_context(
            player=player,
            regen=regen,
            personality=personality,
            state=state,
            reference_on=effective_date,
        )
        club_context = self.context_service.build_club_context(
            player=player,
            regen=regen,
            club_id=payload.offering_club_id or player_context.current_club.club_id,
            reference_on=effective_date,
            club_stature=payload.club_stature,
            league_quality=payload.league_quality,
            competition_level=payload.competition_level,
            expected_minutes=payload.pathway_to_minutes,
            development_fit=payload.development_opportunity,
            squad_congestion=payload.squad_congestion,
            project_attractiveness=payload.project_attractiveness,
            continental_football=payload.continental_football,
            role_label=payload.role_promised,
        )
        offer = ContractEvaluationInput(
            offering_club_id=payload.offering_club_id,
            offered_wage_amount=payload.offered_wage_amount,
            contract_years=payload.contract_years,
            role_promised=payload.role_promised,
            release_clause_amount=payload.release_clause_amount,
            bonus_amount=payload.bonus_amount,
            club_stature=payload.club_stature,
            league_quality=payload.league_quality,
            pathway_to_minutes=payload.pathway_to_minutes,
            development_opportunity=payload.development_opportunity,
            squad_congestion=payload.squad_congestion,
            project_attractiveness=payload.project_attractiveness,
            competition_level=payload.competition_level,
            continental_football=payload.continental_football,
            is_renewal=payload.is_renewal,
            requested_on=payload.requested_on,
        )
        digest = self._decision_digest("contract", player_id, payload.model_dump(mode="json"))
        cached = self._cached_decision(state, cache_key="contract", digest=digest, reference_on=effective_date)
        if cached is not None:
            return ContractDecisionView(**cached, contract_stance=state.contract_stance)

        outcome = self.contract_decision_service.evaluate(
            player_context=player_context,
            club_context=club_context,
            offer=offer,
        )
        hydrated = self._with_timings(outcome, effective_date)
        state.contract_stance = self._contract_stance_from_decision(hydrated.decision_code)
        state.last_contract_decision_at = datetime.combine(effective_date, datetime.min.time())
        state.recent_offer_cooldown_until = hydrated.cooldown_until
        state.next_review_at = self._later_datetime(state.next_review_at, hydrated.next_review_at)
        state.metadata_json = self._store_decision_cache(state.metadata_json, "contract", digest, hydrated)
        self.session.flush()
        return ContractDecisionView(**self._decision_payload(hydrated), contract_stance=state.contract_stance)

    def evaluate_transfer_opportunity(
        self,
        player_id: str,
        payload: TransferDecisionRequest,
        *,
        reference_on: date | None = None,
    ) -> TransferDecisionView:
        player, regen, personality, state, _transfer_request = self.sync(player_id, reference_on=reference_on or payload.requested_on)
        effective_date = reference_on or payload.requested_on or date.today()
        player_context = self.context_service.build_player_context(
            player=player,
            regen=regen,
            personality=personality,
            state=state,
            reference_on=effective_date,
        )
        club_context = self.context_service.build_club_context(
            player=player,
            regen=regen,
            club_id=payload.destination_club_id,
            reference_on=effective_date,
            club_stature=payload.club_stature,
            league_quality=payload.league_quality,
            competition_level=payload.competition_level,
            expected_minutes=payload.expected_minutes,
            development_fit=payload.development_fit,
            squad_congestion=payload.squad_congestion,
            geography_score=payload.geography_score,
            continental_football=payload.continental_football,
            role_label=payload.expected_role,
        )
        move = TransferEvaluationInput(
            destination_club_id=payload.destination_club_id,
            offered_wage_amount=payload.offered_wage_amount,
            contract_years=payload.contract_years,
            expected_role=payload.expected_role,
            expected_minutes=payload.expected_minutes,
            club_stature=payload.club_stature,
            league_quality=payload.league_quality,
            competition_level=payload.competition_level,
            squad_congestion=payload.squad_congestion,
            development_fit=payload.development_fit,
            geography_score=payload.geography_score,
            continental_football=payload.continental_football,
            transfer_denied_recently=payload.transfer_denied_recently,
            requested_on=payload.requested_on,
        )
        digest = self._decision_digest("transfer", player_id, payload.model_dump(mode="json"))
        cached = self._cached_decision(state, cache_key="transfer", digest=digest, reference_on=effective_date)
        if cached is not None:
            return TransferDecisionView(**cached, transfer_request_status=state.transfer_request_status)

        outcome = self.transfer_decision_service.evaluate_move(
            player_context=player_context,
            club_context=club_context,
            move=move,
        )
        hydrated = self._with_timings(outcome, effective_date)
        state.last_transfer_decision_at = datetime.combine(effective_date, datetime.min.time())
        state.recent_offer_cooldown_until = hydrated.cooldown_until
        state.next_review_at = self._later_datetime(state.next_review_at, hydrated.next_review_at)
        state.metadata_json = self._store_decision_cache(state.metadata_json, "transfer", digest, hydrated)
        if hydrated.decision_code == "requests_transfer_if_blocked":
            state.transfer_appetite = clamp(max(state.transfer_appetite, hydrated.decision_score))
        self.session.flush()
        return TransferDecisionView(
            **self._decision_payload(hydrated),
            transfer_request_status=("transfer_request" if hydrated.decision_code == "requests_transfer_if_blocked" else state.transfer_request_status),
        )

    def sync(
        self,
        player_id: str,
        *,
        reference_on: date | None = None,
    ) -> tuple[Player, RegenProfile, PlayerPersonality, PlayerAgencyState, AgencyDecisionOutcome]:
        effective_date = reference_on or date.today()
        player = self._require_player(player_id)
        regen = self._require_regen_profile(player_id)
        personality = self._ensure_personality(player=player, regen=regen)
        state = self._ensure_state(player=player, regen=regen, personality=personality, reference_on=effective_date)
        player_context = self.context_service.build_player_context(
            player=player,
            regen=regen,
            personality=personality,
            state=state,
            reference_on=effective_date,
        )
        state.career_stage = player_context.career_stage
        state.career_target_band = player_context.career_target_band
        state.preferred_role_band = player_context.preferred_role_band
        state.current_club_id = player_context.current_club.club_id
        state.salary_expectation_amount = player_context.salary_expectation_amount
        state.wage_satisfaction = self._wage_satisfaction(player_context)
        state.playing_time_satisfaction = self._playing_time_satisfaction(player_context)
        state.development_satisfaction = self._development_satisfaction(player_context)
        state.club_project_belief = clamp(player_context.current_club.project_attractiveness)
        state.grievance_count, state.unmet_expectations_json = self._current_grievances(state)
        state.transfer_appetite = self._transfer_appetite(player_context)
        state.morale = clamp(
            (state.wage_satisfaction * 0.24)
            + (state.playing_time_satisfaction * 0.28)
            + (state.development_satisfaction * 0.18)
            + (state.club_project_belief * 0.18)
            - (state.grievance_count * 5.0)
            + (personality.professionalism * 0.05)
        )
        state.happiness = clamp((state.morale * 0.64) + (state.club_project_belief * 0.16) + (100.0 - state.transfer_appetite) * 0.20)
        state.contract_stance = self._contract_stance(state=state, personality=personality, player_context=player_context)
        transfer_request = self.transfer_decision_service.evaluate_transfer_request(player_context=player_context)
        transfer_request = self._with_timings(transfer_request, effective_date)
        state.transfer_request_status = transfer_request.decision_code
        state.next_review_at = self._later_datetime(state.next_review_at, transfer_request.next_review_at)
        if transfer_request.decision_code in {"transfer_request", "public_unhappy_state"}:
            state.last_transfer_request_at = datetime.combine(effective_date, datetime.min.time())
        self.session.flush()
        return player, regen, personality, state, transfer_request

    def record_blocked_move(self, player_id: str, *, reference_on: date | None = None, reason: str | None = None) -> None:
        effective_date = reference_on or date.today()
        _player, _regen, _personality, state, _transfer_request = self.sync(player_id, reference_on=effective_date)
        state.last_transfer_denial_at = datetime.combine(effective_date, datetime.min.time())
        promise_memory = dict(state.promise_memory_json or {})
        promise_memory["denied_move_count"] = int(promise_memory.get("denied_move_count", 0)) + 1
        if reason:
            promise_memory["last_denied_move_reason"] = reason
        state.promise_memory_json = promise_memory
        unmet = [item for item in list(state.unmet_expectations_json or []) if item.get("code") != "denied_move"]
        unmet.append({"code": "denied_move", "detail": reason or "Move blocked", "opened_on": effective_date.isoformat()})
        state.unmet_expectations_json = unmet
        state.grievance_count = len(unmet)
        state.transfer_appetite = clamp(state.transfer_appetite + 14.0)
        state.morale = clamp(state.morale - 10.0)
        self.session.flush()

    def _ensure_personality(self, *, player: Player, regen: RegenProfile) -> PlayerPersonality:
        personality = self.session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == player.id))
        if personality is not None:
            if personality.regen_profile_id is None:
                personality.regen_profile_id = regen.id
            return personality
        resolved = self._deterministic_personality(player=player, regen=regen)
        personality = PlayerPersonality(
            player_id=player.id,
            regen_profile_id=regen.id,
            source_scope="regen",
            ambition=resolved["ambition"],
            loyalty=resolved["loyalty"],
            professionalism=resolved["professionalism"],
            greed=resolved["greed"],
            temperament=resolved["temperament"],
            patience=resolved["patience"],
            adaptability=resolved["adaptability"],
            competitiveness=resolved["competitiveness"],
            ego=resolved["ego"],
            development_focus=resolved["development_focus"],
            hometown_affinity=resolved["hometown_affinity"],
            trophy_hunger=resolved["trophy_hunger"],
            media_appetite=resolved["media_appetite"],
            default_career_target_band=resolved["default_career_target_band"],
            metadata_json={"seed_version": 1, "source": "deterministic_regen_profile"},
        )
        self.session.add(personality)
        self.session.flush()
        return personality

    def _ensure_state(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        personality: PlayerPersonality,
        reference_on: date,
    ) -> PlayerAgencyState:
        state = self.session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == player.id))
        if state is not None:
            if state.regen_profile_id is None:
                state.regen_profile_id = regen.id
            return state
        career_stage = self.context_service.infer_career_stage(
            player=player,
            regen=regen,
            personality=personality,
            reference_on=reference_on,
        )
        state = PlayerAgencyState(
            player_id=player.id,
            regen_profile_id=regen.id,
            current_club_id=player.current_club_profile_id,
            morale=58.0,
            happiness=60.0,
            transfer_appetite=12.0,
            contract_stance="balanced",
            wage_satisfaction=58.0,
            playing_time_satisfaction=60.0,
            development_satisfaction=64.0,
            club_project_belief=60.0,
            grievance_count=0,
            promise_memory_json={},
            unmet_expectations_json=[],
            transfer_request_status="no_action",
            preferred_role_band=self.context_service.infer_preferred_role_band(personality=personality, career_stage=career_stage),
            career_stage=career_stage,
            career_target_band=personality.default_career_target_band,
            salary_expectation_amount=quantize_amount(max(150, round((regen.current_gsi * 6.0) + (personality.ambition * 3.1) + (personality.greed * 2.6)))),
            metadata_json={},
        )
        self.session.add(state)
        self.session.flush()
        return state

    def _deterministic_personality(self, *, player: Player, regen: RegenProfile) -> dict[str, int | str]:
        seed = f"{regen.regen_id}:{player.id}:{regen.birth_country_code}:{regen.generated_at.isoformat()}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        metadata_traits = dict((regen.metadata_json or {}).get("decision_traits") or {})
        regen_personality = self.session.scalar(select(RegenPersonalityProfile).where(RegenPersonalityProfile.regen_profile_id == regen.id))
        origin = self.session.scalar(select(RegenOriginMetadata).where(RegenOriginMetadata.regen_profile_id == regen.id))

        def hashed_value(index: int, minimum: int = 25, maximum: int = 90) -> int:
            raw = int(digest[index:index + 4], 16)
            return minimum + (raw % (maximum - minimum + 1))

        resolved = {
            "ambition": int(metadata_traits.get("ambition", getattr(regen_personality, "ambition", hashed_value(0)) if regen_personality is not None else hashed_value(0))),
            "loyalty": int(metadata_traits.get("loyalty", getattr(regen_personality, "loyalty", hashed_value(4)) if regen_personality is not None else hashed_value(4))),
            "professionalism": int(metadata_traits.get("professionalism", getattr(regen_personality, "work_rate", hashed_value(8)) if regen_personality is not None else hashed_value(8))),
            "greed": int(metadata_traits.get("greed", hashed_value(12))),
            "temperament": int(metadata_traits.get("temperament", getattr(regen_personality, "temperament", hashed_value(16)) if regen_personality is not None else hashed_value(16))),
            "patience": int(metadata_traits.get("patience", getattr(regen_personality, "resilience", hashed_value(20)) if regen_personality is not None else hashed_value(20))),
            "adaptability": int(metadata_traits.get("adaptability", hashed_value(24))),
            "competitiveness": int(metadata_traits.get("competitiveness", hashed_value(28))),
            "ego": int(metadata_traits.get("ego", hashed_value(32))),
            "development_focus": int(metadata_traits.get("development_focus", hashed_value(36))),
            "hometown_affinity": int(metadata_traits.get("hometown_affinity", 82 if origin is not None and origin.city_name else hashed_value(40))),
            "trophy_hunger": int(metadata_traits.get("trophy_hunger", hashed_value(44))),
            "media_appetite": int(metadata_traits.get("media_appetite", hashed_value(48))),
        }
        ambition = resolved["ambition"]
        trophy_hunger = resolved["trophy_hunger"]
        greed = resolved["greed"]
        development_focus = resolved["development_focus"]
        loyalty = resolved["loyalty"]
        professionalism = resolved["professionalism"]
        if greed >= 78:
            target_band = "money-first"
        elif development_focus >= 68:
            target_band = "development-first"
        elif ambition >= 82 and trophy_hunger >= 72:
            target_band = "trophy-first"
        elif ambition >= 72:
            target_band = "prestige-first"
        elif loyalty + professionalism >= 132:
            target_band = "stability-first"
        else:
            target_band = "minutes-first"
        resolved["default_career_target_band"] = target_band
        return {key: (int(clamp(value, 0, 100)) if isinstance(value, int) else value) for key, value in resolved.items()}

    def _wage_satisfaction(self, player_context) -> float:
        expectation = max(float(player_context.salary_expectation_amount), 1.0)
        current_wage = float(player_context.current_wage_amount)
        ratio = current_wage / expectation
        return clamp((ratio * 78.0) + (player_context.personality.loyalty * 0.08))

    def _playing_time_satisfaction(self, player_context) -> float:
        return clamp((player_context.current_minutes_score * 0.82) + (player_context.personality.patience * 0.10) - (player_context.personality.ego * 0.06))

    def _development_satisfaction(self, player_context) -> float:
        potential_gap = max(0, int((player_context.regen.potential_range_json or {}).get("maximum", player_context.regen.current_gsi)) - player_context.regen.current_gsi)
        urgency_bonus = 8.0 if player_context.career_stage in {"wonderkid", "prospect", "breakout"} else 0.0
        return clamp(
            (player_context.current_club.development_score * 0.52)
            + (player_context.current_club.expected_minutes_score * 0.22)
            + (potential_gap * 0.9)
            + urgency_bonus
        )

    def _transfer_appetite(self, player_context) -> float:
        ambition_gap = max(0.0, player_context.personality.ambition - player_context.current_club.club_stature)
        denied_move_pressure = 14.0 if player_context.state.last_transfer_denial_at is not None else 0.0
        return clamp(
            (100.0 - player_context.state.playing_time_satisfaction) * 0.25
            + (100.0 - player_context.state.wage_satisfaction) * 0.18
            + (100.0 - player_context.state.development_satisfaction) * 0.12
            + (100.0 - player_context.state.club_project_belief) * 0.15
            + ambition_gap * 0.18
            + denied_move_pressure
            - (player_context.personality.loyalty * 0.10)
            - (player_context.personality.patience * 0.06)
        )

    def _current_grievances(self, state: PlayerAgencyState) -> tuple[int, list[dict[str, object]]]:
        unmet = [item for item in list(state.unmet_expectations_json or []) if item.get("code") == "denied_move"]
        if state.playing_time_satisfaction < 45.0:
            unmet.append({"code": "playing_time", "detail": "Minutes below expectation"})
        if state.wage_satisfaction < 45.0:
            unmet.append({"code": "wage", "detail": "Wage below expectation"})
        if state.development_satisfaction < 45.0:
            unmet.append({"code": "development", "detail": "Development pathway weak"})
        if state.club_project_belief < 45.0:
            unmet.append({"code": "project", "detail": "Club project credibility low"})
        deduped: dict[str, dict[str, object]] = {}
        for item in unmet:
            deduped[str(item.get("code") or "issue")] = item
        issues = list(deduped.values())
        return len(issues), issues

    def _contract_stance(self, *, state: PlayerAgencyState, personality: PlayerPersonality, player_context) -> str:
        if state.transfer_request_status in {"transfer_request", "public_unhappy_state"}:
            return "open_market"
        if player_context.days_remaining is not None and player_context.days_remaining <= 180 and state.wage_satisfaction < 55.0:
            return "requests_upgrade"
        if personality.loyalty >= 72 and state.happiness >= 62.0:
            return "stable"
        if state.wage_satisfaction < 52.0 or state.playing_time_satisfaction < 50.0:
            return "requests_renegotiation"
        return "balanced"

    def _contract_stance_from_decision(self, decision_code: str) -> str:
        if decision_code in {"accept", "accept_if_improved_terms"}:
            return "engaged"
        if decision_code in {"requests_renegotiation", "delay_undecided"}:
            return "requests_renegotiation"
        if decision_code in {"reject", "prefers_to_stay_on_current_terms"}:
            return "stable"
        return "balanced"

    def _cached_decision(
        self,
        state: PlayerAgencyState,
        *,
        cache_key: str,
        digest: str,
        reference_on: date,
    ) -> dict[str, object] | None:
        metadata = dict(state.metadata_json or {})
        cache = dict(metadata.get(f"{cache_key}_decision_cache") or {})
        if cache.get("digest") != digest:
            return None
        cooldown_until = cache.get("cooldown_until")
        if cooldown_until is None or datetime.fromisoformat(str(cooldown_until)) < datetime.combine(reference_on, datetime.min.time()):
            return None
        return {
            "decision_code": cache["decision_code"],
            "decision_score": cache["decision_score"],
            "confidence_band": cache["confidence_band"],
            "primary_reasons": tuple(AgencyReasonView(**item) for item in cache.get("primary_reasons", [])),
            "secondary_reasons": tuple(AgencyReasonView(**item) for item in cache.get("secondary_reasons", [])),
            "persuading_factors": tuple(cache.get("persuading_factors", [])),
            "component_scores": dict(cache.get("component_scores", {})),
            "next_review_at": datetime.fromisoformat(str(cache["next_review_at"])) if cache.get("next_review_at") else None,
            "cooldown_until": datetime.fromisoformat(str(cache["cooldown_until"])) if cache.get("cooldown_until") else None,
        }

    def _store_decision_cache(
        self,
        metadata_json: dict[str, object] | None,
        cache_key: str,
        digest: str,
        outcome: AgencyDecisionOutcome,
    ) -> dict[str, object]:
        metadata = dict(metadata_json or {})
        metadata[f"{cache_key}_decision_cache"] = {
            "digest": digest,
            "decision_code": outcome.decision_code,
            "decision_score": outcome.decision_score,
            "confidence_band": outcome.confidence_band,
            "primary_reasons": [self._reason_payload(item) for item in outcome.primary_reasons],
            "secondary_reasons": [self._reason_payload(item) for item in outcome.secondary_reasons],
            "persuading_factors": list(outcome.persuading_factors),
            "component_scores": dict(outcome.component_scores),
            "next_review_at": outcome.next_review_at.isoformat() if outcome.next_review_at is not None else None,
            "cooldown_until": outcome.cooldown_until.isoformat() if outcome.cooldown_until is not None else None,
        }
        return metadata

    def _decision_digest(self, scope: str, player_id: str, payload: dict[str, object]) -> str:
        return hashlib.sha256(f"{scope}:{player_id}:{json.dumps(payload, sort_keys=True, default=str)}".encode("utf-8")).hexdigest()

    def _with_timings(self, outcome: AgencyDecisionOutcome, reference_on: date) -> AgencyDecisionOutcome:
        return AgencyDecisionOutcome(
            decision_code=outcome.decision_code,
            decision_score=outcome.decision_score,
            confidence_band=outcome.confidence_band,
            primary_reasons=outcome.primary_reasons,
            secondary_reasons=outcome.secondary_reasons,
            persuading_factors=outcome.persuading_factors,
            component_scores=outcome.component_scores,
            next_review_at=self.context_service.review_time(outcome.decision_code, reference_on=reference_on),
            cooldown_until=self.context_service.decision_cooldown(outcome.decision_code, reference_on=reference_on),
        )

    def _decision_payload(self, outcome: AgencyDecisionOutcome) -> dict[str, object]:
        return {
            "decision_code": outcome.decision_code,
            "decision_score": outcome.decision_score,
            "confidence_band": outcome.confidence_band,
            "primary_reasons": tuple(self._to_reason_view(item) for item in outcome.primary_reasons),
            "secondary_reasons": tuple(self._to_reason_view(item) for item in outcome.secondary_reasons),
            "persuading_factors": outcome.persuading_factors,
            "component_scores": outcome.component_scores,
            "next_review_at": outcome.next_review_at,
            "cooldown_until": outcome.cooldown_until,
        }

    def _to_decision_view(self, outcome: AgencyDecisionOutcome) -> AgencyDecisionView:
        return AgencyDecisionView(**self._decision_payload(outcome))

    def _to_reason_view(self, reason) -> AgencyReasonView:
        return AgencyReasonView(code=reason.code, text=reason.text, weight=round(reason.weight, 2))

    def _reason_payload(self, reason) -> dict[str, object]:
        return {"code": reason.code, "text": reason.text, "weight": round(reason.weight, 2)}

    def _to_personality_view(self, personality: PlayerPersonality) -> PlayerPersonalityView:
        return PlayerPersonalityView(
            ambition=personality.ambition,
            loyalty=personality.loyalty,
            professionalism=personality.professionalism,
            greed=personality.greed,
            temperament=personality.temperament,
            patience=personality.patience,
            adaptability=personality.adaptability,
            competitiveness=personality.competitiveness,
            ego=personality.ego,
            development_focus=personality.development_focus,
            hometown_affinity=personality.hometown_affinity,
            trophy_hunger=personality.trophy_hunger,
            media_appetite=personality.media_appetite,
            default_career_target_band=personality.default_career_target_band,
        )

    def _to_state_view(self, state: PlayerAgencyState) -> PlayerAgencyStateView:
        return PlayerAgencyStateView(
            morale=state.morale,
            happiness=state.happiness,
            transfer_appetite=state.transfer_appetite,
            contract_stance=state.contract_stance,
            wage_satisfaction=state.wage_satisfaction,
            playing_time_satisfaction=state.playing_time_satisfaction,
            development_satisfaction=state.development_satisfaction,
            club_project_belief=state.club_project_belief,
            grievance_count=state.grievance_count,
            transfer_request_status=state.transfer_request_status,
            preferred_role_band=state.preferred_role_band,
            career_stage=state.career_stage,
            career_target_band=state.career_target_band,
            salary_expectation_amount=state.salary_expectation_amount,
            promise_memory_json=dict(state.promise_memory_json or {}),
            unmet_expectations_json=list(state.unmet_expectations_json or []),
            recent_offer_cooldown_until=state.recent_offer_cooldown_until,
            next_review_at=state.next_review_at,
        )

    def _later_datetime(self, current: datetime | None, candidate: datetime | None) -> datetime | None:
        if current is None:
            return candidate
        if candidate is None:
            return current
        return max(current, candidate)

    def _require_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise KeyError(f"Player {player_id} was not found.")
        return player

    def _require_regen_profile(self, player_id: str) -> RegenProfile:
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player_id))
        if regen is None:
            raise KeyError(f"Player {player_id} does not have a regen profile.")
        return regen
