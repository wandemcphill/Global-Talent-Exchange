from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.market.player_eligibility_policy import is_preseeded_national_regen
from app.models.club_profile import ClubProfile
from app.models.player_agency_state import PlayerAgencyState
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.player_personality import PlayerPersonality
from app.models.regen import RegenOriginMetadata, RegenPersonalityProfile, RegenProfile
from app.models.regen_ecosystem import Agent
from app.models.story_feed import StoryFeedItem
from app.models.transfer_market import PlayerCoachRelationship, PlayerDecisionProfile
from app.regen_universe.models import RegenSeason, RegenStoryEvent
from app.schemas.player_agency import (
    AgencyDecisionView,
    AgencyReasonView,
    ContractDecisionRequest,
    ContractDecisionView,
    PlayerAgencySnapshotView,
    PreferredClubDestinationView,
    PlayerAgencyStateView,
    PlayerPersonalityView,
    TransferDecisionRequest,
    TransferDecisionView,
)
from app.services.contract_decision_service import ContractDecisionService
from app.services.player_agency_context_service import (
    AgencyDecisionOutcome,
    AgencyReason,
    ContractEvaluationInput,
    PlayerAgencyContextService,
    TransferEvaluationInput,
    clamp,
    quantize_amount,
)
from app.services.transfer_decision_service import TransferDecisionService

_AUTO_AGENT_NAMES = (
    "Mercury Sports",
    "Northbridge Agency",
    "Atlas Representation",
    "Crescent Football",
    "Harbor Elite",
)
_POSITIVE_REASON_CODES = {
    "wage_upside",
    "role_pathway",
    "development_fit",
    "club_stature",
    "minutes_path",
    "prestige_step",
    "league_step",
    "wage_uplift",
    "stability_pull",
    "leadership_voice",
    "agent_backing",
}
_TRANSFER_REQUEST_THRESHOLD_STATUSES = {"transfer_request", "public_unhappy_state"}


@dataclass(slots=True)
class PlayerAgencyService:
    session: Session
    context_service: PlayerAgencyContextService = field(init=False)
    contract_decision_service: ContractDecisionService = field(init=False)
    transfer_decision_service: TransferDecisionService = field(init=False)

    def __post_init__(self) -> None:
        self.context_service = PlayerAgencyContextService(self.session)
        self.contract_decision_service = ContractDecisionService()
        self.transfer_decision_service = TransferDecisionService()

    def get_agency_profile(self, player_id: str, *, reference_on: date | None = None) -> PlayerAgencySnapshotView:
        return self.get_snapshot(player_id, reference_on=reference_on)

    def get_snapshot(self, player_id: str, *, reference_on: date | None = None) -> PlayerAgencySnapshotView:
        player, regen, personality, state, transfer_request = self.sync(player_id, reference_on=reference_on)
        return PlayerAgencySnapshotView(
            player_id=player.id,
            regen_id=regen.regen_id,
            personality=self._to_personality_view(personality),
            state=self._to_state_view(state),
            transfer_request_decision=self._to_decision_view(transfer_request),
        )

    def evaluate_contract_decision(
        self,
        player_id: str,
        offer: ContractDecisionRequest | dict[str, object],
        *,
        reference_on: date | None = None,
    ) -> ContractDecisionView:
        payload = offer if isinstance(offer, ContractDecisionRequest) else ContractDecisionRequest.model_validate(offer)
        return self.evaluate_contract_offer(player_id, payload, reference_on=reference_on)

    def evaluate_contract_offer(
        self,
        player_id: str,
        payload: ContractDecisionRequest,
        *,
        reference_on: date | None = None,
    ) -> ContractDecisionView:
        player, regen, personality, state, _transfer_request = self.sync(
            player_id, reference_on=reference_on or payload.requested_on
        )
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

        agent = self._ensure_agent_for_player(player_id)
        relationship_score = self._current_club_relationship_score(player_context)
        outcome = self.contract_decision_service.evaluate(
            player_context=player_context,
            club_context=club_context,
            offer=offer,
        )
        outcome = self._apply_contract_personality(
            outcome,
            player_context=player_context,
            club_context=club_context,
            offer=offer,
            agent=agent,
            relationship_score=relationship_score,
        )
        hydrated = self._with_timings(outcome, effective_date)
        state.contract_stance = self._contract_stance_from_decision(hydrated.decision_code)
        state.last_contract_decision_at = datetime.combine(effective_date, datetime.min.time())
        state.recent_offer_cooldown_until = hydrated.cooldown_until
        state.next_review_at = self._later_datetime(state.next_review_at, hydrated.next_review_at)
        state.metadata_json = self._store_decision_cache(state.metadata_json, "contract", digest, hydrated)
        self._sync_player_decision_profile(
            player=player,
            regen=regen,
            personality=personality,
            state=state,
            player_context=player_context,
            agent=agent,
            reference_on=effective_date,
        )
        self.session.flush()
        return ContractDecisionView(**self._decision_payload(hydrated), contract_stance=state.contract_stance)

    def evaluate_transfer_decision(
        self,
        player_id: str,
        offer: TransferDecisionRequest | dict[str, object],
        *,
        reference_on: date | None = None,
    ) -> TransferDecisionView:
        payload = offer if isinstance(offer, TransferDecisionRequest) else TransferDecisionRequest.model_validate(offer)
        return self.evaluate_transfer_opportunity(player_id, payload, reference_on=reference_on)

    def evaluate_transfer_opportunity(
        self,
        player_id: str,
        payload: TransferDecisionRequest,
        *,
        reference_on: date | None = None,
    ) -> TransferDecisionView:
        player, regen, personality, state, _transfer_request = self.sync(
            player_id, reference_on=reference_on or payload.requested_on
        )
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

        agent = self._ensure_agent_for_player(player_id)
        relationship_score = self._current_club_relationship_score(player_context)
        outcome = self.transfer_decision_service.evaluate_move(
            player_context=player_context,
            club_context=club_context,
            move=move,
        )
        outcome = self._apply_transfer_personality(
            outcome,
            player_context=player_context,
            club_context=club_context,
            move=move,
            agent=agent,
            relationship_score=relationship_score,
        )
        hydrated = self._with_timings(outcome, effective_date)
        state.last_transfer_decision_at = datetime.combine(effective_date, datetime.min.time())
        state.recent_offer_cooldown_until = hydrated.cooldown_until
        state.next_review_at = self._later_datetime(state.next_review_at, hydrated.next_review_at)
        state.metadata_json = self._store_decision_cache(state.metadata_json, "transfer", digest, hydrated)
        if hydrated.decision_code == "requests_transfer_if_blocked":
            state.transfer_appetite = clamp(max(state.transfer_appetite, hydrated.decision_score))
        self._sync_player_decision_profile(
            player=player,
            regen=regen,
            personality=personality,
            state=state,
            player_context=player_context,
            agent=agent,
            reference_on=effective_date,
        )
        self.session.flush()
        return TransferDecisionView(
            **self._decision_payload(hydrated),
            transfer_request_status=(
                "transfer_request"
                if hydrated.decision_code == "requests_transfer_if_blocked"
                else state.transfer_request_status
            ),
        )

    def get_preferred_club_shortlist(
        self,
        player_id: str,
        offers: list[TransferDecisionRequest | dict[str, object]],
        *,
        reference_on: date | None = None,
    ) -> tuple[PreferredClubDestinationView, ...]:
        shortlist: list[PreferredClubDestinationView] = []
        for raw_offer in offers:
            payload = (
                raw_offer
                if isinstance(raw_offer, TransferDecisionRequest)
                else TransferDecisionRequest.model_validate(raw_offer)
            )
            decision = self.evaluate_transfer_decision(player_id, payload, reference_on=reference_on)
            club = self.session.get(ClubProfile, payload.destination_club_id)
            shortlist.append(
                PreferredClubDestinationView(
                    rank=1,
                    destination_club_id=payload.destination_club_id,
                    destination_club_name=club.club_name if club is not None else None,
                    decision=decision,
                )
            )
        shortlist.sort(
            key=lambda item: (
                self._decision_priority(item.decision.decision_code),
                item.decision.decision_score,
            ),
            reverse=True,
        )
        ranked: list[PreferredClubDestinationView] = []
        for index, item in enumerate(shortlist, start=1):
            ranked.append(
                PreferredClubDestinationView(
                    rank=index,
                    destination_club_id=item.destination_club_id,
                    destination_club_name=item.destination_club_name,
                    decision=item.decision.model_copy(update={"preferred_destination_rank": index}),
                )
            )
        return tuple(ranked)

    def maybe_submit_transfer_request(
        self,
        player_id: str,
        context: dict[str, object] | None = None,
        *,
        reference_on: date | None = None,
    ) -> AgencyDecisionView:
        context_payload = dict(context or {})
        effective_date = reference_on or context_payload.get("reference_on") or date.today()
        if not isinstance(effective_date, date):
            effective_date = date.today()
        previous_state = self.session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == player_id))
        previous_status = previous_state.transfer_request_status if previous_state is not None else "no_action"
        player, regen, personality, state, transfer_request = self.sync(player_id, reference_on=effective_date)
        agent = self._ensure_agent_for_player(player_id)
        player_context = self.context_service.build_player_context(
            player=player,
            regen=regen,
            personality=personality,
            state=state,
            reference_on=effective_date,
        )
        transfer_request = self._escalate_transfer_request_if_needed(
            transfer_request,
            personality=personality,
            state=state,
            player_context=player_context,
        )
        state.transfer_request_status = transfer_request.decision_code
        if transfer_request.decision_code in _TRANSFER_REQUEST_THRESHOLD_STATUSES:
            state.last_transfer_request_at = datetime.combine(effective_date, datetime.min.time())
        self._sync_player_decision_profile(
            player=player,
            regen=regen,
            personality=personality,
            state=state,
            player_context=player_context,
            agent=agent,
            reference_on=effective_date,
        )
        if not self._eligible_for_club_transfer_requests(regen):
            self.session.flush()
            return self._to_decision_view(transfer_request)
        if self._status_rank(transfer_request.decision_code) < self._status_rank("transfer_request"):
            self.session.flush()
            return self._to_decision_view(transfer_request)
        latest_transfer_event = self._latest_transfer_request_event(player.id)
        transfer_request_on = (
            state.last_transfer_request_at.date() if state.last_transfer_request_at is not None else effective_date
        )
        should_create_event = (
            self._status_rank(previous_status) < self._status_rank("transfer_request")
            or latest_transfer_event is None
            or latest_transfer_event.occurred_on < transfer_request_on
        )
        if should_create_event:
            lifecycle_event = self._create_transfer_request_event(
                player=player,
                regen=regen,
                state=state,
                transfer_request=transfer_request,
                agent=agent,
                occurred_on=effective_date,
            )
            self._create_transfer_request_story(
                player=player,
                regen=regen,
                lifecycle_event=lifecycle_event,
                transfer_request=transfer_request,
                occurred_on=effective_date,
            )
        self.session.flush()
        return self._to_decision_view(transfer_request)

    def run_regen_agency_tick(
        self,
        season_id: str | None = None,
        *,
        reference_on: date | None = None,
    ) -> dict[str, object]:
        if reference_on is None and season_id is not None:
            season = self.session.get(RegenSeason, season_id)
            if season is None:
                raise KeyError(f"Season {season_id} was not found.")
            reference_on = season.closed_at.date() if season.closed_at is not None else season.end_date
        effective_date = reference_on or date.today()
        player_ids = list(
            self.session.scalars(
                select(Player.id)
                .join(RegenProfile, RegenProfile.player_id == Player.id)
                .where(RegenProfile.status == "active")
                .order_by(Player.id.asc())
            )
        )
        transfer_requests_created = 0
        decision_profiles_synced = 0
        skipped_national_pool_only = 0
        touched_players: list[str] = []
        for player_id in player_ids:
            regen = self._require_regen_profile(player_id)
            if not self._eligible_for_club_transfer_requests(regen):
                skipped_national_pool_only += 1
                continue
            transfer_events_before = (
                self.session.query(PlayerLifecycleEvent)
                .filter(
                    PlayerLifecycleEvent.player_id == player_id,
                    PlayerLifecycleEvent.event_type == "transfer_request_submitted",
                )
                .count()
            )
            decision = self.maybe_submit_transfer_request(player_id, reference_on=effective_date)
            decision_profiles_synced += 1
            touched_players.append(player_id)
            transfer_events_after = (
                self.session.query(PlayerLifecycleEvent)
                .filter(
                    PlayerLifecycleEvent.player_id == player_id,
                    PlayerLifecycleEvent.event_type == "transfer_request_submitted",
                )
                .count()
            )
            if (
                self._status_rank(decision.decision_code) >= self._status_rank("transfer_request")
                and transfer_events_after > transfer_events_before
            ):
                transfer_requests_created += 1
        self.session.flush()
        return {
            "season_id": season_id,
            "reference_on": effective_date.isoformat(),
            "scanned": len(player_ids),
            "decision_profiles_synced": decision_profiles_synced,
            "transfer_requests_created": transfer_requests_created,
            "skipped_national_pool_only": skipped_national_pool_only,
            "touched_player_ids": touched_players,
        }

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
        state.happiness = clamp(
            (state.morale * 0.64) + (state.club_project_belief * 0.16) + (100.0 - state.transfer_appetite) * 0.20
        )
        state.contract_stance = self._contract_stance(
            state=state, personality=personality, player_context=player_context
        )
        transfer_request = self.transfer_decision_service.evaluate_transfer_request(player_context=player_context)
        transfer_request = self._with_timings(transfer_request, effective_date)
        transfer_request = self._escalate_transfer_request_if_needed(
            transfer_request,
            personality=personality,
            state=state,
            player_context=player_context,
        )
        state.transfer_request_status = transfer_request.decision_code
        state.next_review_at = self._later_datetime(state.next_review_at, transfer_request.next_review_at)
        if transfer_request.decision_code in {"transfer_request", "public_unhappy_state"}:
            state.last_transfer_request_at = datetime.combine(effective_date, datetime.min.time())
        state.metadata_json = {
            **dict(state.metadata_json or {}),
            "current_club_relationship_score": round(self._current_club_relationship_score(player_context), 2),
        }
        self._sync_player_decision_profile(
            player=player,
            regen=regen,
            personality=personality,
            state=state,
            player_context=player_context,
            agent=self._ensure_agent_for_player(player_id),
            reference_on=effective_date,
        )
        self.session.flush()
        return player, regen, personality, state, transfer_request

    def record_blocked_move(
        self, player_id: str, *, reference_on: date | None = None, reason: str | None = None
    ) -> None:
        effective_date = reference_on or date.today()
        _player, _regen, _personality, state, _transfer_request = self.sync(player_id, reference_on=effective_date)
        state.last_transfer_denial_at = datetime.combine(effective_date, datetime.min.time())
        promise_memory = dict(state.promise_memory_json or {})
        promise_memory["denied_move_count"] = int(promise_memory.get("denied_move_count", 0)) + 1
        if reason:
            promise_memory["last_denied_move_reason"] = reason
        state.promise_memory_json = promise_memory
        unmet = [item for item in list(state.unmet_expectations_json or []) if item.get("code") != "denied_move"]
        unmet.append(
            {"code": "denied_move", "detail": reason or "Move blocked", "opened_on": effective_date.isoformat()}
        )
        state.unmet_expectations_json = unmet
        state.grievance_count = len(unmet)
        state.transfer_appetite = clamp(state.transfer_appetite + 14.0)
        state.morale = clamp(state.morale - 10.0)
        self.session.flush()

    def _ensure_personality(self, *, player: Player, regen: RegenProfile) -> PlayerPersonality:
        resolved = self._deterministic_personality(player=player, regen=regen)
        personality = self.session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == player.id))
        if personality is not None:
            if personality.regen_profile_id is None:
                personality.regen_profile_id = regen.id
            metadata = dict(personality.metadata_json or {})
            metadata.update(
                {
                    "seed_version": 2,
                    "source": "deterministic_regen_profile",
                    "leadership": int(resolved["leadership"]),
                    "resilience": int(resolved["resilience"]),
                }
            )
            personality.metadata_json = metadata
            return personality
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
            metadata_json={
                "seed_version": 2,
                "source": "deterministic_regen_profile",
                "leadership": int(resolved["leadership"]),
                "resilience": int(resolved["resilience"]),
            },
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
            preferred_role_band=self.context_service.infer_preferred_role_band(
                personality=personality, career_stage=career_stage
            ),
            career_stage=career_stage,
            career_target_band=personality.default_career_target_band,
            salary_expectation_amount=quantize_amount(
                max(150, round((regen.current_gsi * 6.0) + (personality.ambition * 3.1) + (personality.greed * 2.6)))
            ),
            metadata_json={},
        )
        self.session.add(state)
        self.session.flush()
        return state

    def _deterministic_personality(self, *, player: Player, regen: RegenProfile) -> dict[str, int | str]:
        seed = f"{regen.regen_id}:{player.id}:{regen.birth_country_code}:{regen.generated_at.isoformat()}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        metadata_traits = dict((regen.metadata_json or {}).get("decision_traits") or {})
        regen_personality = self.session.scalar(
            select(RegenPersonalityProfile).where(RegenPersonalityProfile.regen_profile_id == regen.id)
        )
        origin = self.session.scalar(
            select(RegenOriginMetadata).where(RegenOriginMetadata.regen_profile_id == regen.id)
        )

        def hashed_value(index: int, minimum: int = 25, maximum: int = 90) -> int:
            raw = int(digest[index : index + 4], 16)
            return minimum + (raw % (maximum - minimum + 1))

        resolved = {
            "ambition": int(
                metadata_traits.get(
                    "ambition",
                    (
                        getattr(regen_personality, "ambition", hashed_value(0))
                        if regen_personality is not None
                        else hashed_value(0)
                    ),
                )
            ),
            "loyalty": int(
                metadata_traits.get(
                    "loyalty",
                    (
                        getattr(regen_personality, "loyalty", hashed_value(4))
                        if regen_personality is not None
                        else hashed_value(4)
                    ),
                )
            ),
            "professionalism": int(
                metadata_traits.get(
                    "professionalism",
                    (
                        getattr(regen_personality, "work_rate", hashed_value(8))
                        if regen_personality is not None
                        else hashed_value(8)
                    ),
                )
            ),
            "greed": int(metadata_traits.get("greed", hashed_value(12))),
            "temperament": int(
                metadata_traits.get(
                    "temperament",
                    (
                        getattr(regen_personality, "temperament", hashed_value(16))
                        if regen_personality is not None
                        else hashed_value(16)
                    ),
                )
            ),
            "patience": int(
                metadata_traits.get(
                    "patience",
                    (
                        getattr(regen_personality, "resilience", hashed_value(20))
                        if regen_personality is not None
                        else hashed_value(20)
                    ),
                )
            ),
            "adaptability": int(metadata_traits.get("adaptability", hashed_value(24))),
            "competitiveness": int(metadata_traits.get("competitiveness", hashed_value(28))),
            "ego": int(metadata_traits.get("ego", hashed_value(32))),
            "development_focus": int(metadata_traits.get("development_focus", hashed_value(36))),
            "hometown_affinity": int(
                metadata_traits.get(
                    "hometown_affinity", 82 if origin is not None and origin.city_name else hashed_value(40)
                )
            ),
            "trophy_hunger": int(metadata_traits.get("trophy_hunger", hashed_value(44))),
            "media_appetite": int(metadata_traits.get("media_appetite", hashed_value(48))),
            "leadership": int(
                metadata_traits.get(
                    "leadership",
                    (
                        getattr(regen_personality, "leadership", hashed_value(52))
                        if regen_personality is not None
                        else hashed_value(52)
                    ),
                )
            ),
            "resilience": int(
                metadata_traits.get(
                    "resilience",
                    (
                        getattr(regen_personality, "resilience", hashed_value(56))
                        if regen_personality is not None
                        else hashed_value(56)
                    ),
                )
            ),
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
        return {
            key: (int(clamp(value, 0, 100)) if isinstance(value, int) else value) for key, value in resolved.items()
        }

    def _wage_satisfaction(self, player_context) -> float:
        expectation = max(float(player_context.salary_expectation_amount), 1.0)
        current_wage = float(player_context.current_wage_amount)
        ratio = current_wage / expectation
        return clamp((ratio * 78.0) + (player_context.personality.loyalty * 0.08))

    def _playing_time_satisfaction(self, player_context) -> float:
        return clamp(
            (player_context.current_minutes_score * 0.82)
            + (player_context.personality.patience * 0.10)
            - (player_context.personality.ego * 0.06)
        )

    def _development_satisfaction(self, player_context) -> float:
        potential_gap = max(
            0,
            int((player_context.regen.potential_range_json or {}).get("maximum", player_context.regen.current_gsi))
            - player_context.regen.current_gsi,
        )
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
        resilience = self._trait_score(player_context.personality, "resilience")
        return clamp(
            (100.0 - player_context.state.playing_time_satisfaction) * 0.25
            + (100.0 - player_context.state.wage_satisfaction) * 0.18
            + (100.0 - player_context.state.development_satisfaction) * 0.12
            + (100.0 - player_context.state.club_project_belief) * 0.15
            + ambition_gap * 0.18
            + denied_move_pressure
            + max(0.0, 50.0 - resilience) * 0.08
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
        if (
            player_context.days_remaining is not None
            and player_context.days_remaining <= 180
            and state.wage_satisfaction < 55.0
        ):
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
        if cooldown_until is None or datetime.fromisoformat(str(cooldown_until)) < datetime.combine(
            reference_on, datetime.min.time()
        ):
            return None
        return {
            "decision_code": cache["decision_code"],
            "decision_score": cache["decision_score"],
            "confidence_score": cache.get("confidence_score", cache["decision_score"]),
            "confidence_band": cache["confidence_band"],
            "accepted": bool(cache.get("accepted", self._is_positive_decision(cache["decision_code"]))),
            "rejected": bool(cache.get("rejected", self._is_negative_decision(cache["decision_code"]))),
            "concerns": tuple(cache.get("concerns", [])),
            "explanation": str(cache.get("explanation") or ""),
            "primary_reasons": tuple(AgencyReasonView(**item) for item in cache.get("primary_reasons", [])),
            "secondary_reasons": tuple(AgencyReasonView(**item) for item in cache.get("secondary_reasons", [])),
            "persuading_factors": tuple(cache.get("persuading_factors", [])),
            "component_scores": dict(cache.get("component_scores", {})),
            "decision_weight_breakdown": dict(cache.get("decision_weight_breakdown", {})),
            "next_review_at": (
                datetime.fromisoformat(str(cache["next_review_at"])) if cache.get("next_review_at") else None
            ),
            "cooldown_until": (
                datetime.fromisoformat(str(cache["cooldown_until"])) if cache.get("cooldown_until") else None
            ),
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
            "confidence_score": round(outcome.decision_score, 2),
            "confidence_band": outcome.confidence_band,
            "accepted": self._is_positive_decision(outcome.decision_code),
            "rejected": self._is_negative_decision(outcome.decision_code),
            "concerns": list(self._concerns_from_outcome(outcome)),
            "explanation": self._explanation_from_outcome(outcome),
            "primary_reasons": [self._reason_payload(item) for item in outcome.primary_reasons],
            "secondary_reasons": [self._reason_payload(item) for item in outcome.secondary_reasons],
            "persuading_factors": list(outcome.persuading_factors),
            "component_scores": dict(outcome.component_scores),
            "decision_weight_breakdown": dict(outcome.decision_weight_breakdown),
            "next_review_at": outcome.next_review_at.isoformat() if outcome.next_review_at is not None else None,
            "cooldown_until": outcome.cooldown_until.isoformat() if outcome.cooldown_until is not None else None,
        }
        return metadata

    def _decision_digest(self, scope: str, player_id: str, payload: dict[str, object]) -> str:
        return hashlib.sha256(
            f"{scope}:{player_id}:{json.dumps(payload, sort_keys=True, default=str)}".encode("utf-8")
        ).hexdigest()

    def _with_timings(self, outcome: AgencyDecisionOutcome, reference_on: date) -> AgencyDecisionOutcome:
        return AgencyDecisionOutcome(
            decision_code=outcome.decision_code,
            decision_score=outcome.decision_score,
            confidence_band=outcome.confidence_band,
            primary_reasons=outcome.primary_reasons,
            secondary_reasons=outcome.secondary_reasons,
            persuading_factors=outcome.persuading_factors,
            component_scores=outcome.component_scores,
            decision_weight_breakdown=outcome.decision_weight_breakdown,
            next_review_at=self.context_service.review_time(outcome.decision_code, reference_on=reference_on),
            cooldown_until=self.context_service.decision_cooldown(outcome.decision_code, reference_on=reference_on),
        )

    def _decision_payload(self, outcome: AgencyDecisionOutcome) -> dict[str, object]:
        return {
            "decision_code": outcome.decision_code,
            "decision_score": outcome.decision_score,
            "confidence_score": round(outcome.decision_score, 2),
            "confidence_band": outcome.confidence_band,
            "accepted": self._is_positive_decision(outcome.decision_code),
            "rejected": self._is_negative_decision(outcome.decision_code),
            "concerns": self._concerns_from_outcome(outcome),
            "explanation": self._explanation_from_outcome(outcome),
            "primary_reasons": tuple(self._to_reason_view(item) for item in outcome.primary_reasons),
            "secondary_reasons": tuple(self._to_reason_view(item) for item in outcome.secondary_reasons),
            "persuading_factors": outcome.persuading_factors,
            "component_scores": outcome.component_scores,
            "decision_weight_breakdown": outcome.decision_weight_breakdown,
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

    def _is_positive_decision(self, decision_code: str) -> bool:
        return decision_code in {
            "accept",
            "accept_if_improved_terms",
            "eager_to_join",
            "open_to_join",
            "requests_transfer_if_blocked",
        }

    def _is_negative_decision(self, decision_code: str) -> bool:
        return decision_code in {
            "reject",
            "rejects_move",
            "prefers_current_club",
            "prefers_to_stay_on_current_terms",
        }

    def _decision_priority(self, decision_code: str) -> int:
        return {
            "requests_transfer_if_blocked": 5,
            "eager_to_join": 4,
            "open_to_join": 3,
            "accept": 3,
            "accept_if_improved_terms": 2,
            "requests_renegotiation": 2,
            "hesitant_needs_better_terms": 1,
            "delay_undecided": 1,
            "prefers_to_stay_on_current_terms": 0,
            "prefers_current_club": 0,
            "reject": -1,
            "rejects_move": -1,
        }.get(decision_code, 0)

    def _status_rank(self, status: str) -> int:
        return {
            "no_action": 0,
            "private_unrest": 1,
            "agent_warning": 2,
            "transfer_request": 3,
            "public_unhappy_state": 4,
        }.get(status, 0)

    def _trait_score(self, personality: PlayerPersonality, key: str, default: float = 50.0) -> float:
        value = dict(personality.metadata_json or {}).get(key)
        if isinstance(value, (int, float)):
            return float(clamp(float(value)))
        return float(default)

    def _current_club_relationship_score(self, player_context) -> float:
        relationship = self.session.scalar(
            select(PlayerCoachRelationship).where(
                PlayerCoachRelationship.player_id == player_context.player.id,
                PlayerCoachRelationship.club_id == player_context.current_club.club_id,
            )
        )
        base_score = (
            (player_context.personality.loyalty * 0.28)
            + (player_context.state.happiness * 0.24)
            + (player_context.state.club_project_belief * 0.20)
            + (player_context.state.playing_time_satisfaction * 0.12)
            + (player_context.state.wage_satisfaction * 0.08)
            + (self._trait_score(player_context.personality, "leadership") * 0.08)
        )
        if relationship is None:
            return clamp(base_score)
        return clamp(
            (base_score * 0.74)
            + (relationship.relationship_score * 0.22)
            - (relationship.conflict_level * 0.10)
            + (relationship.integration_success_modifier * 0.08)
        )

    def _ensure_agent_for_player(self, player_id: str) -> Agent:
        agents = self.session.scalars(select(Agent).order_by(Agent.created_at.asc(), Agent.id.asc())).all()
        for agent in agents:
            if player_id in set(agent.player_ids_json or []):
                metadata = dict(agent.metadata_json or {})
                if "persona" not in metadata:
                    metadata["persona"] = self._default_agent_persona(player_id)
                    agent.metadata_json = metadata
                return agent
        digest = hashlib.sha256(f"agent:{player_id}".encode("utf-8")).hexdigest()
        agent = Agent(
            name=_AUTO_AGENT_NAMES[int(digest[:2], 16) % len(_AUTO_AGENT_NAMES)],
            negotiation_skill=48 + (int(digest[2:6], 16) % 45),
            player_ids_json=[player_id],
            metadata_json={
                "auto_created": True,
                "persona": self._default_agent_persona(player_id),
            },
        )
        self.session.add(agent)
        self.session.flush()
        return agent

    def _default_agent_persona(self, player_id: str) -> str:
        personas = ("power_broker", "player_champion", "steady_operator", "club_loyalist")
        digest = hashlib.sha256(f"agent-persona:{player_id}".encode("utf-8")).hexdigest()
        return personas[int(digest[:2], 16) % len(personas)]

    def _agent_persona(self, agent: Agent) -> str:
        metadata = dict(agent.metadata_json or {})
        persona = metadata.get("persona")
        if isinstance(persona, str) and persona.strip():
            return persona.strip()
        return self._default_agent_persona((agent.player_ids_json or ["agent"])[0])

    def _apply_contract_personality(
        self,
        outcome: AgencyDecisionOutcome,
        *,
        player_context,
        club_context,
        offer: ContractEvaluationInput,
        agent: Agent,
        relationship_score: float,
    ) -> AgencyDecisionOutcome:
        score = float(outcome.decision_score)
        component_scores = dict(outcome.component_scores)
        component_scores["current_club_relationship"] = round(relationship_score, 2)
        component_scores["agent_negotiation"] = round(float(agent.negotiation_skill), 2)
        decision_weight_breakdown = dict(outcome.decision_weight_breakdown)
        reasons = list(outcome.primary_reasons) + list(outcome.secondary_reasons)
        agent_persona = self._agent_persona(agent)
        resilience = self._trait_score(player_context.personality, "resilience")
        leadership = self._trait_score(player_context.personality, "leadership")
        same_club_offer = club_context.club_id == player_context.current_club.club_id

        if same_club_offer and relationship_score >= 70.0 and player_context.personality.loyalty >= 68:
            score = clamp(score + 6.0)
            decision_weight_breakdown["club_relationship_weight"] = 6.0
            reasons.append(
                AgencyReason(
                    code="stability_pull",
                    text="The relationship with the current club still feels strong.",
                    weight=16.0,
                )
            )
        elif not same_club_offer and relationship_score >= 76.0 and player_context.personality.loyalty >= 72:
            score = clamp(score - 8.0)
            decision_weight_breakdown["club_relationship_weight"] = -8.0
            reasons.append(
                AgencyReason(
                    code="current_club_pull",
                    text="A strong bond with the current club makes leaving harder.",
                    weight=18.0,
                )
            )

        if agent_persona == "power_broker" and component_scores.get("wage", 0.0) < 64.0:
            score = clamp(score - 6.0)
            decision_weight_breakdown["agent_persona_weight"] = (
                decision_weight_breakdown.get("agent_persona_weight", 0.0) - 6.0
            )
            reasons.append(
                AgencyReason(
                    code="agent_pressure", text="The agent wants stronger terms before committing.", weight=14.0
                )
            )
        elif agent_persona == "club_loyalist" and same_club_offer and relationship_score >= 64.0:
            score = clamp(score + 4.0)
            decision_weight_breakdown["agent_persona_weight"] = (
                decision_weight_breakdown.get("agent_persona_weight", 0.0) + 4.0
            )
            reasons.append(
                AgencyReason(
                    code="agent_backing", text="The agent sees value in continuity at the current club.", weight=10.0
                )
            )

        if leadership >= 74.0 and same_club_offer and player_context.current_club.expected_minutes_score >= 58.0:
            score = clamp(score + 4.0)
            decision_weight_breakdown["leadership_weight"] = 4.0
            reasons.append(
                AgencyReason(
                    code="leadership_voice", text="Leadership responsibility at the club still matters.", weight=10.0
                )
            )

        if resilience <= 42.0 and player_context.state.happiness <= 50.0 and not same_club_offer:
            score = clamp(score + 4.0)
            decision_weight_breakdown["resilience_weight"] = 4.0
            reasons.append(
                AgencyReason(
                    code="fresh_start_pull",
                    text="A fresh environment looks appealing after recent frustration.",
                    weight=11.0,
                )
            )

        primary_reasons, secondary_reasons = self._sorted_reasons(reasons)
        decision_code = self.contract_decision_service._decision_code(
            score=score,
            player_context=player_context,
            club_context=club_context,
            offer=offer,
            wage_score=component_scores.get("wage", 0.0),
            role_score=component_scores.get("role", 0.0),
            development_score=component_scores.get("development", 0.0),
        )
        return AgencyDecisionOutcome(
            decision_code=decision_code,
            decision_score=round(score, 2),
            confidence_band=self.contract_decision_service._confidence_band(score),
            primary_reasons=primary_reasons,
            secondary_reasons=secondary_reasons,
            persuading_factors=outcome.persuading_factors,
            component_scores=component_scores,
            decision_weight_breakdown=decision_weight_breakdown,
        )

    def _apply_transfer_personality(
        self,
        outcome: AgencyDecisionOutcome,
        *,
        player_context,
        club_context,
        move: TransferEvaluationInput,
        agent: Agent,
        relationship_score: float,
    ) -> AgencyDecisionOutcome:
        score = float(outcome.decision_score)
        component_scores = dict(outcome.component_scores)
        component_scores["current_club_relationship"] = round(relationship_score, 2)
        component_scores["agent_negotiation"] = round(float(agent.negotiation_skill), 2)
        decision_weight_breakdown = dict(outcome.decision_weight_breakdown)
        reasons = list(outcome.primary_reasons) + list(outcome.secondary_reasons)
        agent_persona = self._agent_persona(agent)
        resilience = self._trait_score(player_context.personality, "resilience")
        leadership = self._trait_score(player_context.personality, "leadership")

        if agent_persona in {"power_broker", "player_champion"} and component_scores.get("prestige_gain", 0.0) >= 58.0:
            score = clamp(score + 5.0)
            decision_weight_breakdown["agent_persona_weight"] = (
                decision_weight_breakdown.get("agent_persona_weight", 0.0) + 5.0
            )
            reasons.append(
                AgencyReason(
                    code="agent_backing", text="The agent is pushing the player toward a bigger project.", weight=13.0
                )
            )
        if agent_persona == "club_loyalist" and relationship_score >= 68.0:
            score = clamp(score - 6.0)
            decision_weight_breakdown["agent_persona_weight"] = (
                decision_weight_breakdown.get("agent_persona_weight", 0.0) - 6.0
            )
            reasons.append(
                AgencyReason(
                    code="stability_pull",
                    text="The agent believes the current club still deserves patience.",
                    weight=12.0,
                )
            )

        if (
            player_context.personality.ambition >= 84
            and component_scores.get("prestige_gain", 0.0) >= 62.0
            and component_scores.get("minutes", 0.0) >= 60.0
        ):
            score = clamp(score + 6.0)
            decision_weight_breakdown["ambition_weight"] = 6.0
            reasons.append(
                AgencyReason(
                    code="prestige_step", text="The move aligns with a high-ambition career path.", weight=15.0
                )
            )

        if relationship_score >= 78.0 and player_context.personality.loyalty >= 76:
            score = clamp(score - 9.0)
            decision_weight_breakdown["club_relationship_weight"] = -9.0
            reasons.append(
                AgencyReason(
                    code="current_club_pull",
                    text="The current club relationship remains a serious anchor.",
                    weight=18.0,
                )
            )

        if resilience <= 44.0 and player_context.state.happiness <= 48.0:
            score = clamp(score + 5.0)
            decision_weight_breakdown["resilience_weight"] = 5.0
            reasons.append(
                AgencyReason(
                    code="fresh_start_pull",
                    text="Low resilience and low happiness make a move easier to justify.",
                    weight=12.0,
                )
            )

        if leadership >= 76.0 and relationship_score >= 70.0 and player_context.state.playing_time_satisfaction >= 52.0:
            score = clamp(score - 5.0)
            decision_weight_breakdown["leadership_weight"] = -5.0
            reasons.append(
                AgencyReason(
                    code="leadership_voice",
                    text="Leadership responsibility at the current club slows the move down.",
                    weight=11.0,
                )
            )

        primary_reasons, secondary_reasons = self._sorted_reasons(reasons)
        decision_code = self.transfer_decision_service._decision_code(
            score=score,
            player_context=player_context,
            club_context=club_context,
            move=move,
            prestige_gain=component_scores.get("prestige_gain", 0.0),
            league_gain=component_scores.get("league_gain", 0.0),
            wage_score=component_scores.get("wage", 0.0),
            relative_wage_uplift=max(
                float(move.offered_wage_amount) / max(float(player_context.current_wage_amount), 1.0), 0.0
            ),
        )
        return AgencyDecisionOutcome(
            decision_code=decision_code,
            decision_score=round(score, 2),
            confidence_band=self.transfer_decision_service._confidence_band(score),
            primary_reasons=primary_reasons,
            secondary_reasons=secondary_reasons,
            persuading_factors=outcome.persuading_factors,
            component_scores=component_scores,
            decision_weight_breakdown=decision_weight_breakdown,
        )

    def _sorted_reasons(self, reasons: list[AgencyReason]) -> tuple[tuple[AgencyReason, ...], tuple[AgencyReason, ...]]:
        deduped: dict[str, AgencyReason] = {}
        for reason in reasons:
            existing = deduped.get(reason.code)
            if existing is None or reason.weight > existing.weight:
                deduped[reason.code] = reason
        ordered = tuple(sorted(deduped.values(), key=lambda item: item.weight, reverse=True))
        return ordered[:3], ordered[3:6]

    def _concerns_from_outcome(self, outcome: AgencyDecisionOutcome) -> tuple[str, ...]:
        concerns: list[str] = []
        for reason in (*outcome.primary_reasons, *outcome.secondary_reasons):
            if reason.code not in _POSITIVE_REASON_CODES:
                concerns.append(reason.text)
        return tuple(dict.fromkeys(concerns))[:3]

    def _explanation_from_outcome(self, outcome: AgencyDecisionOutcome) -> str:
        reasons = [reason.text for reason in outcome.primary_reasons[:2]]
        if not reasons:
            return "The player needs more time before committing."
        lead = {
            "requests_transfer_if_blocked": "Ready to push for the move because",
            "eager_to_join": "Eager to join because",
            "open_to_join": "Open to the move because",
            "accept": "Accepted because",
            "accept_if_improved_terms": "Would accept with better terms because",
            "hesitant_needs_better_terms": "Hesitant because",
            "delay_undecided": "Still undecided because",
            "requests_renegotiation": "Pushing for better terms because",
            "prefers_current_club": "Rejected because",
            "prefers_to_stay_on_current_terms": "Rejected because",
            "reject": "Rejected because",
            "rejects_move": "Rejected because",
        }.get(outcome.decision_code, "Undecided because")
        return f"{lead} {' and '.join(reason.rstrip('.') for reason in reasons)}."

    def _escalate_transfer_request_if_needed(
        self,
        outcome: AgencyDecisionOutcome,
        *,
        personality: PlayerPersonality,
        state: PlayerAgencyState,
        player_context,
    ) -> AgencyDecisionOutcome:
        escalated = outcome
        if (
            escalated.decision_code == "private_unrest"
            and personality.ego >= 78
            and (
                player_context.current_minutes_score <= 35.0
                or state.playing_time_satisfaction <= 20.0
                or state.grievance_count >= 2
            )
        ):
            escalated = AgencyDecisionOutcome(
                decision_code="agent_warning",
                decision_score=max(round(escalated.decision_score, 2), 54.0),
                confidence_band=self.transfer_decision_service._confidence_band(max(escalated.decision_score, 54.0)),
                primary_reasons=escalated.primary_reasons,
                secondary_reasons=escalated.secondary_reasons,
                persuading_factors=escalated.persuading_factors,
                component_scores=dict(escalated.component_scores),
                decision_weight_breakdown={
                    **dict(escalated.decision_weight_breakdown),
                    "ego_visibility_weight": 4.0,
                },
                next_review_at=escalated.next_review_at,
                cooldown_until=escalated.cooldown_until,
            )
        if escalated.decision_code != "agent_warning":
            return escalated
        if (
            personality.ambition >= 84
            and (state.playing_time_satisfaction <= 38.0 or player_context.current_minutes_score <= 35.0)
            and (state.happiness <= 60.0 or state.transfer_appetite >= 60.0 or state.grievance_count >= 2)
        ):
            return AgencyDecisionOutcome(
                decision_code="transfer_request",
                decision_score=max(round(escalated.decision_score, 2), 68.0),
                confidence_band=self.transfer_decision_service._confidence_band(max(escalated.decision_score, 68.0)),
                primary_reasons=escalated.primary_reasons,
                secondary_reasons=escalated.secondary_reasons,
                persuading_factors=escalated.persuading_factors,
                component_scores=dict(escalated.component_scores),
                decision_weight_breakdown={
                    **dict(escalated.decision_weight_breakdown),
                    "tick_escalation_weight": 6.0,
                },
                next_review_at=escalated.next_review_at,
                cooldown_until=escalated.cooldown_until,
            )
        return escalated

    def _preferred_leagues(self, regen: RegenProfile, profile: PlayerDecisionProfile | None) -> list[str]:
        if profile is not None and profile.preferred_leagues_json:
            return list(dict.fromkeys(str(item) for item in profile.preferred_leagues_json if str(item).strip()))
        decision_traits = dict((regen.metadata_json or {}).get("decision_traits") or {})
        raw_preferred = decision_traits.get("preferred_leagues") or []
        if isinstance(raw_preferred, list):
            return list(dict.fromkeys(str(item) for item in raw_preferred if str(item).strip()))
        return []

    def _sync_player_decision_profile(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        personality: PlayerPersonality,
        state: PlayerAgencyState,
        player_context,
        agent: Agent,
        reference_on: date,
    ) -> PlayerDecisionProfile:
        profile = self.session.scalar(select(PlayerDecisionProfile).where(PlayerDecisionProfile.player_id == player.id))
        if profile is None:
            profile = PlayerDecisionProfile(player_id=player.id)
            self.session.add(profile)
        profile.preferred_leagues_json = self._preferred_leagues(regen, profile)
        profile.preferred_play_style = str(
            (regen.metadata_json or {}).get("preferred_play_style") or profile.preferred_play_style or "balanced"
        )
        profile.wage_expectation_amount = state.salary_expectation_amount
        profile.ambition_level = personality.ambition
        profile.happiness = round(state.happiness, 2)
        profile.loyalty = round(float(personality.loyalty), 2)
        profile.ambition = round(float(personality.ambition), 2)
        profile.frustration = round(
            clamp(
                ((100.0 - state.happiness) * 0.56) + (state.transfer_appetite * 0.44) + (state.grievance_count * 4.0)
            ),
            2,
        )
        profile.metadata_json = {
            **dict(profile.metadata_json or {}),
            "career_stage": state.career_stage,
            "career_target_band": state.career_target_band,
            "preferred_role_band": state.preferred_role_band,
            "current_club_relationship_score": round(self._current_club_relationship_score(player_context), 2),
            "agent_persona": self._agent_persona(agent),
            "agent_negotiation_skill": int(agent.negotiation_skill),
            "leadership": round(self._trait_score(personality, "leadership"), 2),
            "resilience": round(self._trait_score(personality, "resilience"), 2),
            "last_synced_on": reference_on.isoformat(),
        }
        return profile

    def _eligible_for_club_transfer_requests(self, regen: RegenProfile) -> bool:
        if is_preseeded_national_regen(regen):
            return False
        metadata = dict(regen.metadata_json or {})
        if metadata.get("national_pool_only") is True:
            return False
        return regen.generation_source not in {"preseeded_national_pool", "national_seed"}

    def _create_transfer_request_event(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        state: PlayerAgencyState,
        transfer_request: AgencyDecisionOutcome,
        agent: Agent,
        occurred_on: date,
    ) -> PlayerLifecycleEvent:
        existing = self.session.scalar(
            select(PlayerLifecycleEvent).where(
                PlayerLifecycleEvent.player_id == player.id,
                PlayerLifecycleEvent.event_type == "transfer_request_submitted",
                PlayerLifecycleEvent.occurred_on == occurred_on,
            )
        )
        if existing is not None:
            return existing
        summary = f"{player.full_name} submitted a transfer request after " f"{self._reason_phrase(transfer_request)}."
        event = PlayerLifecycleEvent(
            player_id=player.id,
            club_id=player.current_club_profile_id,
            event_type="transfer_request_submitted",
            event_status="recorded",
            occurred_on=occurred_on,
            summary=summary,
            details_json={
                "transfer_request_status": state.transfer_request_status,
                "decision_score": transfer_request.decision_score,
                "confidence_band": transfer_request.confidence_band,
                "agent_persona": self._agent_persona(agent),
                "primary_reasons": [reason.code for reason in transfer_request.primary_reasons],
                "explanation": self._explanation_from_outcome(transfer_request),
            },
        )
        self.session.add(event)
        self.session.flush()
        return event

    def _create_transfer_request_story(
        self,
        *,
        player: Player,
        regen: RegenProfile,
        lifecycle_event: PlayerLifecycleEvent,
        transfer_request: AgencyDecisionOutcome,
        occurred_on: date,
    ) -> None:
        occurred_at = datetime.combine(occurred_on, datetime.min.time(), tzinfo=timezone.utc)
        story_key = f"lifecycle:{lifecycle_event.id}"
        story = self.session.scalar(select(RegenStoryEvent).where(RegenStoryEvent.event_key == story_key))
        summary = lifecycle_event.summary
        metadata = {
            "lifecycle_event_id": lifecycle_event.id,
            "transfer_request_status": lifecycle_event.details_json.get("transfer_request_status"),
            "primary_reasons": list(lifecycle_event.details_json.get("primary_reasons") or []),
            "explanation": self._explanation_from_outcome(transfer_request),
        }
        if story is None:
            story = RegenStoryEvent(
                event_key=story_key,
                subject_key=player.id,
                player_id=player.id,
                regen_profile_id=regen.id,
                national_seed_id=None,
                event_type="transfer_request_submitted",
                title="Transfer request submitted",
                summary=summary,
                occurred_at=occurred_at,
                metadata_json=metadata,
            )
            self.session.add(story)
        else:
            story.title = "Transfer request submitted"
            story.summary = summary
            story.occurred_at = occurred_at
            story.metadata_json = metadata
        self._publish_story_feed_item(
            story_type="transfer_request_submitted",
            subject_id=player.id,
            country_code=regen.birth_country_code,
            title=f"{player.full_name} wants a move",
            body=summary,
            metadata_json={
                "event_key": story_key,
                "player_id": player.id,
                "regen_profile_id": regen.id,
                "transfer_request_status": lifecycle_event.details_json.get("transfer_request_status"),
            },
        )

    def _publish_story_feed_item(
        self,
        *,
        story_type: str,
        subject_id: str,
        country_code: str | None,
        title: str,
        body: str,
        metadata_json: dict[str, object],
    ) -> None:
        event_key = str(metadata_json.get("event_key") or "")
        existing_items = self.session.scalars(
            select(StoryFeedItem).where(
                StoryFeedItem.story_type == story_type,
                StoryFeedItem.subject_id == subject_id,
            )
        ).all()
        for item in existing_items:
            if str((item.metadata_json or {}).get("event_key") or "") == event_key:
                item.title = title
                item.body = body
                item.country_code = country_code
                item.metadata_json = metadata_json
                return
        self.session.add(
            StoryFeedItem(
                story_type=story_type,
                audience="public",
                title=title,
                body=body,
                subject_type="player",
                subject_id=subject_id,
                country_code=country_code,
                metadata_json=metadata_json,
            )
        )

    def _reason_phrase(self, outcome: AgencyDecisionOutcome) -> str:
        if not outcome.primary_reasons:
            return "growing unrest at the club"
        reason_texts = [reason.text.rstrip(".") for reason in outcome.primary_reasons[:2]]
        return " and ".join(reason_texts)

    def _latest_transfer_request_event(self, player_id: str) -> PlayerLifecycleEvent | None:
        return self.session.scalar(
            select(PlayerLifecycleEvent)
            .where(
                PlayerLifecycleEvent.player_id == player_id,
                PlayerLifecycleEvent.event_type == "transfer_request_submitted",
            )
            .order_by(PlayerLifecycleEvent.occurred_on.desc(), PlayerLifecycleEvent.created_at.desc())
        )

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
