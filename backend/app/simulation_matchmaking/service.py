from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
from math import log2
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.economy.economy_service import EconomyService
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.schemas import (
    MatchClubContextInput,
    MatchCompetitionContextInput,
    MatchPlayerInput,
    MatchSimulationRequest,
    MatchTeamInput,
    TeamTacticalPlanInput,
)
from app.match_engine.simulation.models import MatchCompetitionType, PlayerRole, TacticalStyle
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.fast_match import (
    FastMatchEntitlement,
    FastMatchResult,
    FastMatchSession,
    FastMatchSessionStatus,
    FastMatchSettlement,
    FastMatchSettlementStatus,
)
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.services.match_timeline_service import MatchTimelineService
from app.live_match.service import (
    LiveMatchError,
    get_live_match_engine,
    session_public_state,
)
from app.simulation_matchmaking.schemas import (
    AvailabilityStatus,
    BotClubProfile,
    ConnectionQuality,
    FastMatchEntitlementResponse,
    HostedCompetitionPreviewRequest,
    HostedCompetitionPreviewResponse,
    HostedCompetitionType,
    LiveMatchSettlementView,
    LiveSessionBridgeView,
    MatchContextView,
    MatchSimulationBridgeView,
    MarketplaceFeedbackHooksView,
    PressingProfile,
    QuickGameRequest,
    QuickGameResponse,
    QuickGameStyle,
    QuickTournamentRequest,
    QuickTournamentResponse,
    SimulationExecutionMode,
    SimulationGameProfileInput,
    SimulationGameProfileView,
    SimulationMatchType,
    TacticalProfileInput,
    TacticalStyleProfile,
    TempoProfile,
    TournamentMatchView,
    TournamentRoundView,
)


class SimulationMatchmakingError(ValueError):
    pass


class ProfileNotFoundError(SimulationMatchmakingError):
    pass


class MatchmakingUnavailableError(SimulationMatchmakingError):
    pass


FAST_MATCH_ENTRY_SERVICE_KEY = "fast-match-entry"
FAST_MATCH_CURRENCY = LedgerUnit.CREDIT
FAST_MATCH_CURRENCY_LABEL = "Fan Coin"


@dataclass(frozen=True, slots=True)
class CandidateScore:
    profile: SimulationGameProfileView
    tactical_contrast: int
    tactical_fit: float
    latency_score: float
    rating_delta: int
    strength_delta: int
    total_score: float


@dataclass(slots=True)
class SimulationMatchmakingService:
    profiles: dict[str, SimulationGameProfileView] = field(default_factory=dict)
    bot_profiles: tuple[SimulationGameProfileView, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.bot_profiles:
            self.bot_profiles = self._default_bots()

    def upsert_profile(self, payload: SimulationGameProfileInput) -> SimulationGameProfileView:
        profile = SimulationGameProfileView(
            user_id=payload.user_id,
            club_id=payload.club_id,
            club_name=payload.club_name or self._derive_club_name(payload.club_id),
            manager_rating=payload.manager_rating,
            tactical_profile=payload.tactical_profile,
            squad_strength=payload.squad_strength,
            squad_depth=payload.squad_depth,
            preferred_match_type=list(payload.preferred_match_type),
            connection_quality=payload.connection_quality,
            region=payload.region.upper(),
            availability=payload.availability,
        )
        self.profiles[profile.user_id] = profile
        return profile

    def get_profile(self, user_id: str) -> SimulationGameProfileView:
        profile = self.profiles.get(user_id)
        if profile is None:
            raise ProfileNotFoundError(f"Simulation profile '{user_id}' was not found.")
        return profile

    def get_fast_match_entitlement(
        self,
        *,
        actor: User,
        session: Session,
    ) -> FastMatchEntitlementResponse:
        entitlement = self._get_or_create_fast_match_entitlement(actor=actor, session=session)
        quote = EconomyService(session).quote_match_entry(
            payment_unit=FAST_MATCH_CURRENCY,
            service_key=FAST_MATCH_ENTRY_SERVICE_KEY,
        )
        return self._entitlement_response(entitlement, fee=quote.gross_amount)

    def create_quick_game(
        self,
        payload: QuickGameRequest,
        *,
        actor: User | None = None,
        session: Session | None = None,
    ) -> QuickGameResponse:
        if actor is not None:
            payload = payload.model_copy(update={"user_id": actor.id})
        requester = self._profile_for_quick_game(payload, actor=actor, session=session)
        human_candidates = self._eligible_quick_game_candidates(requester, include_bots=False)
        exact_matches = [
            candidate
            for candidate in human_candidates
            if abs(candidate.manager_rating - requester.manager_rating) <= payload.preferences.max_rating_delta
            and abs(candidate.squad_strength - requester.squad_strength) <= payload.preferences.max_squad_strength_delta
        ]
        if not exact_matches and payload.include_bots:
            exact_matches = self._bot_fallback_candidates(requester, payload)
        if not exact_matches:
            raise MatchmakingUnavailableError(
                "No suitable Quick Match opponent was available in the current search window."
            )

        ranked = sorted(
            (
                self._score_candidate(requester, candidate, match_style=payload.preferences.match_style)
                for candidate in exact_matches
            ),
            key=lambda item: (-item.total_score, item.rating_delta, item.strength_delta, item.profile.user_id),
        )
        best = ranked[0]
        match_id = f"match_{uuid4().hex[:10]}"
        live_match_key = f"fast-match:{match_id}"
        queue_source = "bot" if best.profile.is_bot else "player"
        context_type = self._match_context_type(best.tactical_contrast, queue_source=queue_source)
        recommended_mode = payload.preferences.preferred_execution_mode or self._recommended_mode(
            requester,
            best.profile,
            latency_score=best.latency_score,
        )
        match_engine_request = self._build_match_engine_request(
            match_id=match_id,
            home=requester,
            away=best.profile,
            competition_type=MatchCompetitionType.LEAGUE,
            stage="quick_game",
            requires_winner=False,
        )
        free_matches_remaining = 10
        free_matches_used = 0
        charge_required_now = False
        fan_coin_entry_fee = Decimal("0.0000")
        entitlement_status = "free_run_active"
        settlement_status: str | None = None
        result_label: str | None = None

        # Head-to-head against another human in LIVE mode → spin up the real-time
        # tick engine and let the match actually play out, instead of pre-computing
        # and settling the result up front. Bot / async pairings keep the one-shot
        # settle path unchanged. (Settlement-on-finish for live H2H is a follow-up.)
        live_session_view: LiveSessionBridgeView | None = None
        is_live_head_to_head = (
            queue_source == "player" and recommended_mode is SimulationExecutionMode.LIVE
        )
        if is_live_head_to_head:
            live_session_view = self._create_live_session(
                match_id=match_id,
                home=requester,
                away=best.profile,
            )

        if actor is not None and session is not None and not is_live_head_to_head:
            entitlement = self._get_or_create_fast_match_entitlement(actor=actor, session=session)
            quote = EconomyService(session).quote_match_entry(
                payment_unit=FAST_MATCH_CURRENCY,
                service_key=FAST_MATCH_ENTRY_SERVICE_KEY,
            )
            fan_coin_entry_fee = quote.gross_amount
            charge_required_now = self._charge_required(entitlement)
            wallet_ledger_id: str | None = None
            if charge_required_now and fan_coin_entry_fee > Decimal("0.0000"):
                payment = EconomyService(session).collect_match_entry(
                    user=actor,
                    payment_unit=FAST_MATCH_CURRENCY,
                    service_key=FAST_MATCH_ENTRY_SERVICE_KEY,
                    reference=f"fast-match-entry:{match_id}",
                    external_reference=live_match_key,
                    description="Fast Match Fan Coin entry fee",
                    actor=actor,
                    idempotency_key=f"fast-match-entry:{actor.id}:{match_id}",
                    metadata={
                        "fast_match": {
                            "match_id": match_id,
                            "live_match_key": live_match_key,
                            "entry_currency_label": FAST_MATCH_CURRENCY_LABEL,
                        }
                    },
                )
                wallet_ledger_id = payment.transaction_id

            replay_payload = MatchSimulationService().build_replay_payload(match_engine_request)
            viewer_payload = MatchTimelineService().build_from_replay_payload(replay_payload).model_dump(mode="json")
            result = self._result_for_requester(replay_payload.summary.winner_team_id, requester=requester)
            result_label = result.value
            settlement = self._settle_fast_match(
                session=session,
                actor=actor,
                entitlement=entitlement,
                match_id=match_id,
                live_match_key=live_match_key,
                result=result,
                was_free=not charge_required_now,
                fan_coin_charged=fan_coin_entry_fee if charge_required_now else Decimal("0.0000"),
                wallet_ledger_id=wallet_ledger_id,
            )
            settlement_status = (
                settlement.settlement_status.value
                if hasattr(settlement.settlement_status, "value")
                else str(settlement.settlement_status)
            )
            session.add(
                FastMatchSession(
                    user_id=actor.id,
                    match_id=match_id,
                    live_match_key=live_match_key,
                    opponent_user_id=best.profile.user_id,
                    home_club_id=requester.club_id,
                    away_club_id=best.profile.club_id,
                    entitlement_id=entitlement.id,
                    settlement_id=settlement.id,
                    status=FastMatchSessionStatus.SETTLED,
                    charge_required_now=charge_required_now,
                    entry_currency=FAST_MATCH_CURRENCY.value,
                    fan_coin_entry_fee=fan_coin_entry_fee,
                    wallet_ledger_id=wallet_ledger_id,
                    result=result.value,
                    viewer_payload_json=viewer_payload,
                    simulation_request_json=match_engine_request.model_dump(mode="json"),
                    metadata_json={
                        "entry_currency_label": FAST_MATCH_CURRENCY_LABEL,
                        "queue_source": queue_source,
                        "viewer_mode_hint": "twoD",
                    },
                )
            )
            session.flush()
            free_matches_remaining = entitlement.free_matches_remaining
            free_matches_used = entitlement.free_matches_used
            entitlement_status = self._entitlement_status(entitlement)

        return QuickGameResponse(
            match_id=match_id,
            live_match_key=live_match_key,
            viewer_route=f"/api/match-viewer/{live_match_key}",
            live_session=live_session_view,
            opponent=best.profile,
            match_context=MatchContextView(
                type=context_type,
                expected_difficulty=self._expected_difficulty(
                    requester, best.profile, tactical_contrast=best.tactical_contrast
                ),
                tactical_story=self._describe_tactical_story(requester, best.profile, context_type=context_type),
                tactical_compatibility_score=best.tactical_contrast,
                rating_delta=best.profile.manager_rating - requester.manager_rating,
                squad_strength_delta=best.profile.squad_strength - requester.squad_strength,
                latency_tier=self._latency_tier(best.latency_score),
                queue_source=queue_source,
            ),
            simulation_bridge=MatchSimulationBridgeView(
                seed_hint=self._seed_hint(match_id),
                recommended_mode=recommended_mode,
                live_supported=True,
                async_supported=True,
                marketplace_feedback_enabled=True,
                match_engine_request=match_engine_request,
            ),
            free_matches_remaining=free_matches_remaining,
            free_matches_used=free_matches_used,
            charge_on_loss=True,
            charge_required_now=charge_required_now,
            entry_currency=FAST_MATCH_CURRENCY.value,
            entry_currency_label=FAST_MATCH_CURRENCY_LABEL,
            fan_coin_entry_fee=fan_coin_entry_fee,
            entitlement_status=entitlement_status,
            settlement_status=settlement_status,
            result=result_label,
            rules_copy="Play free until you lose or reach 10 matches.",
        )

    def settle_live_match(
        self,
        *,
        match_id: str,
        actor: User,
        session: Session,
    ) -> LiveMatchSettlementView:
        """Settle a finished head-to-head live match for its initiator (home side).

        Applies the same entitlement / Fan Coin economy effects the one-shot quick
        game settles up front — but driven by the *live* final score, once the
        match reaches full time. Idempotent per match (the FastMatchSession /
        settlement unique constraints on match_id make repeat calls a no-op).
        Only the initiator (home user) settles, matching the one-shot model where
        the requester is the entry-fee owner; the opponent is unaffected here.
        """
        engine = get_live_match_engine()
        try:
            live = engine.get(match_id)
        except LiveMatchError as exc:
            raise MatchmakingUnavailableError("Live match session was not found.") from exc
        if live.phase != "full_time":
            raise MatchmakingUnavailableError("Live match is still in progress.")
        if live.home_user_id is not None and actor.id != live.home_user_id:
            raise MatchmakingUnavailableError("Only the match initiator can settle this result.")

        entitlement = self._get_or_create_fast_match_entitlement(actor=actor, session=session)

        existing = session.scalar(
            select(FastMatchSession).where(FastMatchSession.match_id == match_id)
        )
        if existing is not None:
            return self._live_settlement_view(
                live=live,
                result=existing.result or FastMatchResult.DRAW.value,
                entitlement=entitlement,
                charge_required_now=existing.charge_required_now,
                fan_coin_charged=existing.fan_coin_entry_fee,
                already_settled=True,
            )

        if live.home_score > live.away_score:
            result = FastMatchResult.WIN
        elif live.away_score > live.home_score:
            result = FastMatchResult.LOSS
        else:
            result = FastMatchResult.DRAW

        live_match_key = f"fast-match:{match_id}"
        quote = EconomyService(session).quote_match_entry(
            payment_unit=FAST_MATCH_CURRENCY,
            service_key=FAST_MATCH_ENTRY_SERVICE_KEY,
        )
        fan_coin_entry_fee = quote.gross_amount
        charge_required_now = self._charge_required(entitlement)
        wallet_ledger_id: str | None = None
        if charge_required_now and fan_coin_entry_fee > Decimal("0.0000"):
            payment = EconomyService(session).collect_match_entry(
                user=actor,
                payment_unit=FAST_MATCH_CURRENCY,
                service_key=FAST_MATCH_ENTRY_SERVICE_KEY,
                reference=f"fast-match-entry:{match_id}",
                external_reference=live_match_key,
                description="Live head-to-head Fan Coin entry fee",
                actor=actor,
                idempotency_key=f"fast-match-entry:{actor.id}:{match_id}",
                metadata={
                    "fast_match": {
                        "match_id": match_id,
                        "live_match_key": live_match_key,
                        "entry_currency_label": FAST_MATCH_CURRENCY_LABEL,
                        "mode": "live_head_to_head",
                    }
                },
            )
            wallet_ledger_id = payment.transaction_id

        settlement = self._settle_fast_match(
            session=session,
            actor=actor,
            entitlement=entitlement,
            match_id=match_id,
            live_match_key=live_match_key,
            result=result,
            was_free=not charge_required_now,
            fan_coin_charged=fan_coin_entry_fee if charge_required_now else Decimal("0.0000"),
            wallet_ledger_id=wallet_ledger_id,
        )
        session.add(
            FastMatchSession(
                user_id=actor.id,
                match_id=match_id,
                live_match_key=live_match_key,
                opponent_user_id=live.away_user_id,
                home_club_id=live.home_id,
                away_club_id=live.away_id,
                entitlement_id=entitlement.id,
                settlement_id=settlement.id,
                status=FastMatchSessionStatus.SETTLED,
                charge_required_now=charge_required_now,
                entry_currency=FAST_MATCH_CURRENCY.value,
                fan_coin_entry_fee=fan_coin_entry_fee,
                wallet_ledger_id=wallet_ledger_id,
                result=result.value,
                viewer_payload_json=session_public_state(live),
                simulation_request_json={},
                metadata_json={
                    "entry_currency_label": FAST_MATCH_CURRENCY_LABEL,
                    "queue_source": "player",
                    "viewer_mode_hint": "live",
                    "final_score": f"{live.home_score}-{live.away_score}",
                },
            )
        )
        session.flush()
        return self._live_settlement_view(
            live=live,
            result=result.value,
            entitlement=entitlement,
            charge_required_now=charge_required_now,
            fan_coin_charged=fan_coin_entry_fee if charge_required_now else Decimal("0.0000"),
            already_settled=False,
        )

    def _live_settlement_view(
        self,
        *,
        live,
        result: str,
        entitlement: FastMatchEntitlement,
        charge_required_now: bool,
        fan_coin_charged: Decimal,
        already_settled: bool,
    ) -> LiveMatchSettlementView:
        return LiveMatchSettlementView(
            match_id=live.match_id,
            result=result,
            settlement_status=FastMatchSettlementStatus.SETTLED.value,
            home_score=live.home_score,
            away_score=live.away_score,
            free_matches_remaining=entitlement.free_matches_remaining,
            free_matches_used=entitlement.free_matches_used,
            charge_required_now=charge_required_now,
            fan_coin_charged=fan_coin_charged,
            entry_currency=FAST_MATCH_CURRENCY.value,
            entry_currency_label=FAST_MATCH_CURRENCY_LABEL,
            entitlement_status=self._entitlement_status(entitlement),
            already_settled=already_settled,
        )

    def create_quick_tournament(self, payload: QuickTournamentRequest) -> QuickTournamentResponse:
        organizer = self.get_profile(payload.user_id)
        entrants = self._select_tournament_entrants(
            organizer=organizer,
            requested_ids=payload.entrant_user_ids,
            size=payload.size,
            allow_bots=payload.preferences.allow_bots,
        )
        if len(entrants) < payload.size:
            raise MatchmakingUnavailableError("Not enough entrants were available to build a quick tournament bracket.")

        seeded = sorted(entrants, key=self._tournament_seed_score, reverse=True)
        pairs = self._pair_first_round(seeded, avoid_same_style_early=payload.preferences.avoid_same_style_early)
        round_one_matches = [
            TournamentMatchView(
                match_id=f"tour-match_{uuid4().hex[:10]}",
                home=home,
                away=away,
                context=f"{self._tactical_label(home)} vs {self._tactical_label(away)}",
                storybeat=self._describe_tactical_story(
                    home,
                    away,
                    context_type=self._match_context_type(
                        self._tactical_contrast_score(home, away), queue_source="player"
                    ),
                ),
                simulation_mode=payload.preferences.preferred_execution_mode,
                match_engine_request=self._build_match_engine_request(
                    match_id=f"tour-sim_{uuid4().hex[:10]}",
                    home=home,
                    away=away,
                    competition_type=MatchCompetitionType.CUP,
                    stage="round_1",
                    requires_winner=True,
                ),
            )
            for home, away in pairs
        ]
        rounds = [TournamentRoundView(round=1, label="Round 1", matches=round_one_matches)]
        remaining_matches = len(round_one_matches) // 2
        for round_number in range(2, int(log2(payload.size)) + 1):
            rounds.append(
                TournamentRoundView(
                    round=round_number,
                    label="Final" if remaining_matches == 1 else f"Round {round_number}",
                    matches=[
                        TournamentMatchView(
                            match_id=f"tour-placeholder_{round_number}_{index + 1}",
                            home=None,
                            away=None,
                            context="TBD",
                            storybeat="Advancing clubs will inherit the bracket path created by the style-aware seeding.",
                            simulation_mode=payload.preferences.preferred_execution_mode,
                            match_engine_request=None,
                        )
                        for index in range(max(1, remaining_matches))
                    ],
                )
            )
            remaining_matches = max(1, remaining_matches // 2)
        return QuickTournamentResponse(
            tournament_id=f"tour_{uuid4().hex[:10]}",
            bracket=rounds,
            narrative=self._tournament_narrative(entrants),
            entrants=entrants,
            marketplace_feedback_enabled=True,
        )

    def preview_hosted_competition(self, payload: HostedCompetitionPreviewRequest) -> HostedCompetitionPreviewResponse:
        host = self.get_profile(payload.host_user_id)
        target_count = payload.target_club_count or self._default_hosted_size(payload.competition_type)
        eligible_styles = list(payload.eligibility.tactical_styles)
        if payload.competition_type is HostedCompetitionType.TACTICAL_CUP and not eligible_styles:
            eligible_styles = [host.tactical_profile.style]

        entrants = self._select_hosted_competition_clubs(
            host=host,
            requested_ids=payload.participant_user_ids,
            target_count=target_count,
            allow_bots=payload.allow_bots,
            competition_type=payload.competition_type,
            styles=eligible_styles,
            min_strength=payload.eligibility.min_squad_strength,
            max_strength=payload.eligibility.max_squad_strength,
            regions=payload.eligibility.regions,
        )
        if len(entrants) < target_count:
            raise MatchmakingUnavailableError(
                "Not enough qualified clubs were available for the hosted competition preview."
            )

        title = payload.title or self._default_competition_title(host, payload.competition_type, styles=eligible_styles)
        return HostedCompetitionPreviewResponse(
            competition_id=f"competition_{uuid4().hex[:10]}",
            competition_type=payload.competition_type,
            title=title,
            format=self._hosted_competition_format(payload.competition_type),
            simulation_mode=payload.simulation_mode,
            qualified_clubs=entrants,
            narrative=self._hosted_competition_narrative(payload.competition_type, entrants, styles=eligible_styles),
            match_flow=self._hosted_match_flow(payload.competition_type, payload.simulation_mode),
            marketplace_hooks=MarketplaceFeedbackHooksView(),
        )

    def _eligible_quick_game_candidates(
        self,
        requester: SimulationGameProfileView,
        *,
        include_bots: bool,
    ) -> list[SimulationGameProfileView]:
        humans = [
            profile
            for profile in self.profiles.values()
            if profile.user_id != requester.user_id
            and profile.availability is AvailabilityStatus.ONLINE
            and SimulationMatchType.QUICK in profile.preferred_match_type
        ]
        if not include_bots:
            return humans
        return humans + [
            profile
            for profile in self.bot_profiles
            if profile.availability is AvailabilityStatus.ONLINE
            and SimulationMatchType.QUICK in profile.preferred_match_type
        ]

    def _bot_fallback_candidates(
        self,
        requester: SimulationGameProfileView,
        payload: QuickGameRequest,
    ) -> list[SimulationGameProfileView]:
        wider_rating = payload.preferences.max_rating_delta + 100
        wider_strength = payload.preferences.max_squad_strength_delta + 8
        return [
            profile
            for profile in self.bot_profiles
            if abs(profile.manager_rating - requester.manager_rating) <= wider_rating
            and abs(profile.squad_strength - requester.squad_strength) <= wider_strength
        ]

    def _score_candidate(
        self,
        requester: SimulationGameProfileView,
        candidate: SimulationGameProfileView,
        *,
        match_style: QuickGameStyle,
    ) -> CandidateScore:
        rating_delta = abs(candidate.manager_rating - requester.manager_rating)
        strength_delta = abs(candidate.squad_strength - requester.squad_strength)
        tactical_contrast = self._tactical_contrast_score(requester, candidate)
        tactical_fit = self._tactical_fit_score(tactical_contrast, match_style=match_style)
        latency_score = self._latency_score(requester, candidate)
        rating_fit = max(0.0, 100.0 - (rating_delta * 1.6))
        strength_fit = max(0.0, 100.0 - (strength_delta * 8.5))
        total = (tactical_fit * 0.58) + (rating_fit * 0.20) + (strength_fit * 0.12) + (latency_score * 0.10)
        return CandidateScore(
            profile=candidate,
            tactical_contrast=tactical_contrast,
            tactical_fit=tactical_fit,
            latency_score=latency_score,
            rating_delta=rating_delta,
            strength_delta=strength_delta,
            total_score=round(total, 2),
        )

    def _select_tournament_entrants(
        self,
        *,
        organizer: SimulationGameProfileView,
        requested_ids: list[str],
        size: int,
        allow_bots: bool,
    ) -> list[SimulationGameProfileView]:
        selected: list[SimulationGameProfileView] = [organizer]
        seen = {organizer.user_id}

        def _append(profile: SimulationGameProfileView) -> None:
            if profile.user_id in seen:
                return
            seen.add(profile.user_id)
            selected.append(profile)

        for user_id in requested_ids:
            if user_id != organizer.user_id:
                _append(self.get_profile(user_id))

        ranked_humans = sorted(
            (
                profile
                for profile in self.profiles.values()
                if profile.user_id != organizer.user_id
                and profile.availability is AvailabilityStatus.ONLINE
                and SimulationMatchType.TOURNAMENT in profile.preferred_match_type
            ),
            key=lambda profile: (
                self._region_bucket(profile.region) != self._region_bucket(organizer.region),
                abs(profile.manager_rating - organizer.manager_rating),
                -self._tactical_contrast_score(organizer, profile),
            ),
        )
        for profile in ranked_humans:
            if len(selected) >= size:
                break
            _append(profile)

        if allow_bots:
            ranked_bots = sorted(
                (
                    profile
                    for profile in self.bot_profiles
                    if SimulationMatchType.TOURNAMENT in profile.preferred_match_type
                ),
                key=lambda profile: (
                    self._region_bucket(profile.region) != self._region_bucket(organizer.region),
                    abs(profile.manager_rating - organizer.manager_rating),
                    abs(profile.squad_strength - organizer.squad_strength),
                ),
            )
            for profile in ranked_bots:
                if len(selected) >= size:
                    break
                _append(profile)
        return selected[:size]

    def _pair_first_round(
        self,
        seeded: list[SimulationGameProfileView],
        *,
        avoid_same_style_early: bool,
    ) -> list[tuple[SimulationGameProfileView, SimulationGameProfileView]]:
        top_half = seeded[: len(seeded) // 2]
        remaining = list(reversed(seeded[len(seeded) // 2 :]))
        pairs: list[tuple[SimulationGameProfileView, SimulationGameProfileView]] = []
        for favorite in top_half:
            opponent = max(
                remaining,
                key=lambda candidate: self._tournament_pair_score(
                    favorite,
                    candidate,
                    avoid_same_style_early=avoid_same_style_early,
                ),
            )
            remaining.remove(opponent)
            pairs.append((favorite, opponent))
        return pairs

    def _tournament_pair_score(
        self,
        favorite: SimulationGameProfileView,
        candidate: SimulationGameProfileView,
        *,
        avoid_same_style_early: bool,
    ) -> float:
        tactical = self._tactical_contrast_score(favorite, candidate)
        diversity_bonus = (
            24.0
            if avoid_same_style_early and favorite.tactical_profile.style != candidate.tactical_profile.style
            else 0.0
        )
        seed_gap = min(40.0, abs(self._tournament_seed_score(favorite) - self._tournament_seed_score(candidate)) / 8.0)
        region_bonus = 12.0 if self._region_bucket(favorite.region) == self._region_bucket(candidate.region) else 0.0
        return tactical + diversity_bonus + seed_gap + region_bonus

    def _select_hosted_competition_clubs(
        self,
        *,
        host: SimulationGameProfileView,
        requested_ids: list[str],
        target_count: int,
        allow_bots: bool,
        competition_type: HostedCompetitionType,
        styles: list[TacticalStyleProfile],
        min_strength: int | None,
        max_strength: int | None,
        regions: list[str],
    ) -> list[SimulationGameProfileView]:
        allowed_regions = {region.upper() for region in regions}
        allowed_styles = set(styles)
        selected: list[SimulationGameProfileView] = []
        seen: set[str] = set()

        def _eligible(profile: SimulationGameProfileView) -> bool:
            if profile.availability is not AvailabilityStatus.ONLINE:
                return False
            required_type = (
                SimulationMatchType.HOSTED
                if competition_type is HostedCompetitionType.LEAGUE_MODE
                else SimulationMatchType.TOURNAMENT
            )
            if (
                required_type not in profile.preferred_match_type
                and SimulationMatchType.HOSTED not in profile.preferred_match_type
            ):
                return False
            if allowed_styles and profile.tactical_profile.style not in allowed_styles:
                return False
            if min_strength is not None and profile.squad_strength < min_strength:
                return False
            if max_strength is not None and profile.squad_strength > max_strength:
                return False
            if allowed_regions and profile.region.upper() not in allowed_regions:
                return False
            return True

        def _append(profile: SimulationGameProfileView) -> None:
            if profile.user_id in seen or not _eligible(profile):
                return
            seen.add(profile.user_id)
            selected.append(profile)

        _append(host)
        for user_id in requested_ids:
            _append(self.get_profile(user_id))

        ranked_humans = sorted(
            (profile for profile in self.profiles.values() if profile.user_id != host.user_id and _eligible(profile)),
            key=lambda profile: (
                abs(profile.manager_rating - host.manager_rating),
                abs(profile.squad_strength - host.squad_strength),
                -self._tactical_contrast_score(host, profile),
            ),
        )
        for profile in ranked_humans:
            if len(selected) >= target_count:
                break
            _append(profile)

        if allow_bots:
            ranked_bots = sorted(
                (profile for profile in self.bot_profiles if _eligible(profile)),
                key=lambda profile: (
                    abs(profile.manager_rating - host.manager_rating),
                    abs(profile.squad_strength - host.squad_strength),
                ),
            )
            for profile in ranked_bots:
                if len(selected) >= target_count:
                    break
                _append(profile)
        return selected[:target_count]

    def _profile_for_quick_game(
        self,
        payload: QuickGameRequest,
        *,
        actor: User | None,
        session: Session | None,
    ) -> SimulationGameProfileView:
        try:
            return self.get_profile(payload.user_id)
        except ProfileNotFoundError:
            if actor is None:
                raise
            profile = self._default_profile_for_actor(actor=actor, session=session)
            self.profiles[profile.user_id] = profile
            return profile

    def _default_profile_for_actor(self, *, actor: User, session: Session | None) -> SimulationGameProfileView:
        club = None
        if session is not None:
            club = session.scalar(
                select(ClubProfile)
                .where(ClubProfile.owner_user_id == actor.id)
                .order_by(ClubProfile.created_at.asc())
            )
        club_id = club.id if club is not None else f"user-club:{actor.id}"
        club_name = club.club_name if club is not None else (getattr(actor, "display_name", None) or "GTEX Fast Match FC")
        return SimulationGameProfileView(
            user_id=actor.id,
            club_id=club_id,
            club_name=club_name,
            manager_rating=1400,
            tactical_profile=TacticalProfileInput(
                style=TacticalStyleProfile.BALANCED,
                pressing=PressingProfile.MEDIUM,
                tempo=TempoProfile.NORMAL,
            ),
            squad_strength=64,
            squad_depth=62,
            preferred_match_type=[SimulationMatchType.QUICK],
            connection_quality=ConnectionQuality.GOOD,
            region="GLOBAL",
            availability=AvailabilityStatus.ONLINE,
        )

    def _get_or_create_fast_match_entitlement(self, *, actor: User, session: Session) -> FastMatchEntitlement:
        entitlement = session.scalar(
            select(FastMatchEntitlement).where(
                FastMatchEntitlement.user_id == actor.id,
                FastMatchEntitlement.season_id.is_(None),
            )
        )
        if entitlement is not None:
            return entitlement
        entitlement = FastMatchEntitlement(user_id=actor.id, season_id=None)
        session.add(entitlement)
        session.flush()
        return entitlement

    def _charge_required(self, entitlement: FastMatchEntitlement) -> bool:
        return bool(
            entitlement.charge_required
            or entitlement.free_eligibility_exhausted
            or entitlement.has_lost_free_run
            or entitlement.free_matches_remaining <= 0
            or entitlement.free_matches_used >= entitlement.free_match_limit
        )

    def _result_for_requester(
        self,
        winner_team_id: str | None,
        *,
        requester: SimulationGameProfileView,
    ) -> FastMatchResult:
        if winner_team_id is None:
            return FastMatchResult.DRAW
        return FastMatchResult.WIN if winner_team_id == f"{requester.club_id}-home" else FastMatchResult.LOSS

    def _settle_fast_match(
        self,
        *,
        session: Session,
        actor: User,
        entitlement: FastMatchEntitlement,
        match_id: str,
        live_match_key: str,
        result: FastMatchResult,
        was_free: bool,
        fan_coin_charged: Decimal,
        wallet_ledger_id: str | None,
    ) -> FastMatchSettlement:
        idempotency_key = f"fast-match-settlement:{actor.id}:{match_id}"
        existing = session.scalar(
            select(FastMatchSettlement).where(
                (FastMatchSettlement.match_id == match_id)
                | (FastMatchSettlement.idempotency_key == idempotency_key)
            )
        )
        if existing is not None:
            return existing

        self._apply_fast_match_result(entitlement=entitlement, match_id=match_id, result=result, was_free=was_free)
        settlement = FastMatchSettlement(
            user_id=actor.id,
            match_id=match_id,
            entitlement_id=entitlement.id,
            result=result,
            was_free=was_free,
            fan_coin_charged=fan_coin_charged,
            settlement_status=FastMatchSettlementStatus.SETTLED,
            idempotency_key=idempotency_key,
            wallet_ledger_id=wallet_ledger_id,
            metadata_json={
                "live_match_key": live_match_key,
                "entry_currency": FAST_MATCH_CURRENCY.value,
                "entry_currency_label": FAST_MATCH_CURRENCY_LABEL,
            },
            settled_at=utcnow(),
        )
        session.add(settlement)
        session.flush()
        return settlement

    def _apply_fast_match_result(
        self,
        *,
        entitlement: FastMatchEntitlement,
        match_id: str,
        result: FastMatchResult,
        was_free: bool,
    ) -> None:
        if was_free:
            entitlement.free_matches_used = min(entitlement.free_match_limit, entitlement.free_matches_used + 1)
            entitlement.free_matches_remaining = max(0, entitlement.free_match_limit - entitlement.free_matches_used)

        if result == FastMatchResult.WIN:
            entitlement.wins_count += 1
            entitlement.current_streak += 1
        elif result == FastMatchResult.DRAW:
            entitlement.draws_count += 1
        else:
            entitlement.losses_count += 1
            entitlement.current_streak = 0
            if was_free:
                entitlement.has_lost_free_run = True
                entitlement.free_eligibility_exhausted = True
                entitlement.charge_required = True

        if entitlement.free_matches_used >= entitlement.free_match_limit:
            entitlement.free_eligibility_exhausted = True
            entitlement.charge_required = True
            entitlement.free_matches_remaining = 0
        entitlement.last_match_id = match_id

    def _entitlement_response(self, entitlement: FastMatchEntitlement, *, fee: Decimal) -> FastMatchEntitlementResponse:
        return FastMatchEntitlementResponse(
            free_match_limit=entitlement.free_match_limit,
            free_matches_used=entitlement.free_matches_used,
            free_matches_remaining=entitlement.free_matches_remaining,
            wins_count=entitlement.wins_count,
            losses_count=entitlement.losses_count,
            draws_count=entitlement.draws_count,
            current_streak=entitlement.current_streak,
            has_lost_free_run=entitlement.has_lost_free_run,
            free_eligibility_exhausted=entitlement.free_eligibility_exhausted,
            charge_required_now=self._charge_required(entitlement),
            entry_currency=FAST_MATCH_CURRENCY.value,
            entry_currency_label=FAST_MATCH_CURRENCY_LABEL,
            fan_coin_entry_fee=fee,
            entitlement_status=self._entitlement_status(entitlement),
        )

    def _entitlement_status(self, entitlement: FastMatchEntitlement) -> str:
        if entitlement.has_lost_free_run:
            return "free_run_lost"
        if entitlement.free_eligibility_exhausted:
            return "free_run_exhausted"
        return "free_run_active"

    def _create_live_session(
        self,
        *,
        match_id: str,
        home: SimulationGameProfileView,
        away: SimulationGameProfileView,
    ) -> LiveSessionBridgeView:
        """Create the real-time live-match session and bind each user to a side."""
        engine = get_live_match_engine()
        engine.create(
            match_id=match_id,
            home_id=home.club_id,
            away_id=away.club_id,
            home_name=home.club_name,
            away_name=away.club_name,
            home_overall=self._clamp_rating(home.squad_strength),
            away_overall=self._clamp_rating(away.squad_strength),
            home_formation=self._formation_for_style(home.tactical_profile.style),
            away_formation=self._formation_for_style(away.tactical_profile.style),
            home_user_id=home.user_id,
            away_user_id=away.user_id,
        )
        # The requester is always the home side in this pairing.
        return LiveSessionBridgeView(
            match_id=match_id,
            session_route=f"/api/live-match/sessions/{match_id}",
            your_side="home",
            home_user_id=home.user_id,
            away_user_id=away.user_id,
            home_name=home.club_name,
            away_name=away.club_name,
        )

    def _build_match_engine_request(
        self,
        *,
        match_id: str,
        home: SimulationGameProfileView,
        away: SimulationGameProfileView,
        competition_type: MatchCompetitionType,
        stage: str,
        requires_winner: bool,
    ) -> MatchSimulationRequest:
        return MatchSimulationRequest(
            match_id=match_id,
            seed=self._seed_hint(match_id),
            competition=MatchCompetitionContextInput(
                competition_type=competition_type,
                stage=stage,
                is_final=stage == "final",
                requires_winner=requires_winner,
            ),
            home_team=self._build_team_input(home, team_id=f"{home.club_id}-home"),
            away_team=self._build_team_input(away, team_id=f"{away.club_id}-away"),
        )

    def _build_team_input(self, profile: SimulationGameProfileView, *, team_id: str) -> MatchTeamInput:
        formation = self._formation_for_style(profile.tactical_profile.style)
        starter_roles = self._starter_roles(formation)
        bench_roles = (
            PlayerRole.GOALKEEPER,
            PlayerRole.DEFENDER,
            PlayerRole.DEFENDER,
            PlayerRole.MIDFIELDER,
            PlayerRole.MIDFIELDER,
            PlayerRole.FORWARD,
            PlayerRole.FORWARD,
        )
        base_overall = max(48, min(95, profile.squad_strength))
        discipline = self._clamp_rating(55 + ((profile.manager_rating - 1300) // 20))
        fitness = self._clamp_rating(58 + ((profile.squad_depth - 50) // 2))
        style = self._match_engine_style(profile.tactical_profile.style, profile.tactical_profile.pressing)
        starters = [
            self._build_player_input(
                team_id=team_id,
                shirt_number=index + 1,
                role=role,
                base_overall=base_overall,
                discipline=discipline,
                fitness=fitness,
                depth_modifier=0,
            )
            for index, role in enumerate(starter_roles)
        ]
        bench = [
            self._build_player_input(
                team_id=team_id,
                shirt_number=index + 101,
                role=role,
                base_overall=max(42, base_overall - max(2, (100 - profile.squad_depth) // 12)),
                discipline=min(99, discipline + 2),
                fitness=min(99, fitness + 3),
                depth_modifier=max(1, (profile.squad_depth - 50) // 12),
            )
            for index, role in enumerate(bench_roles)
        ]
        return MatchTeamInput(
            team_id=team_id,
            team_name=profile.club_name,
            formation=formation,
            tactics=TeamTacticalPlanInput(
                style=style,
                pressing=self._pressing_value(profile.tactical_profile.pressing),
                tempo=self._tempo_value(profile.tactical_profile.tempo),
                aggression=self._aggression_value(profile.tactical_profile),
                defensive_line=self._defensive_line(profile.tactical_profile),
                width=self._width_value(profile.tactical_profile.style),
                mentality=style,
                set_piece_emphasis=self._set_piece_value(profile.tactical_profile.style),
                tactical_quality=self._clamp_rating(56 + ((profile.manager_rating - 1200) // 10)),
                adaptability=self._clamp_rating(54 + ((profile.squad_depth - 50) // 2)),
                game_management=self._clamp_rating(54 + ((profile.manager_rating - 1250) // 12)),
                substitution_windows=(58, 70, 82),
                red_card_fallback_formation="4-4-1",
                injury_auto_substitution=True,
                yellow_card_substitution_minute=72,
                yellow_card_replacement_roles=(PlayerRole.DEFENDER, PlayerRole.MIDFIELDER),
                max_substitutions=5,
            ),
            manager_profile={
                "manager_rating": profile.manager_rating,
                "simulation_tactical_profile": profile.tactical_profile.model_dump(mode="python"),
                "bot_profile": profile.bot_profile.value if profile.bot_profile is not None else None,
            },
            club_context=MatchClubContextInput(
                club_tier=profile.squad_strength,
                competition_tier=72 if SimulationMatchType.TOURNAMENT in profile.preferred_match_type else 68,
                team_chemistry=self._clamp_rating(52 + ((profile.squad_depth - 45) // 2)),
                recent_form=self._clamp_rating(52 + ((profile.manager_rating - 1300) // 18)),
                morale=self._clamp_rating(56 + ((profile.squad_strength - 60) // 2)),
                motivation=self._clamp_rating(58 + ((profile.manager_rating - 1250) // 18)),
                fatigue_load=max(16, 42 - ((profile.squad_depth - 45) // 3)),
                travel_load=22 if profile.region.startswith("AF-") else 28,
                rivalry_intensity=12,
                schedule_pressure=34,
            ),
            starters=starters,
            bench=bench,
        )

    def _build_player_input(
        self,
        *,
        team_id: str,
        shirt_number: int,
        role: PlayerRole,
        base_overall: int,
        discipline: int,
        fitness: int,
        depth_modifier: int,
    ) -> MatchPlayerInput:
        variation = (shirt_number % 3) - 1 + depth_modifier
        overall = self._clamp_rating(base_overall + variation)
        resolved_shirt_number = shirt_number if shirt_number <= 99 else None
        display_name = f"{team_id[:2].upper()}{shirt_number}" if resolved_shirt_number is not None else None
        if role is PlayerRole.GOALKEEPER:
            return MatchPlayerInput(
                player_id=f"{team_id}-p{shirt_number}",
                player_name=f"{team_id.title()} Keeper {shirt_number}",
                role=role,
                overall=self._clamp_rating(overall - 2),
                finishing=10,
                creativity=34,
                defending=56,
                goalkeeping=self._clamp_rating(base_overall + 10 + variation),
                discipline=discipline,
                fitness=fitness,
                shirt_number=resolved_shirt_number,
                display_name=display_name,
            )
        if role is PlayerRole.DEFENDER:
            return MatchPlayerInput(
                player_id=f"{team_id}-p{shirt_number}",
                player_name=f"{team_id.title()} Defender {shirt_number}",
                role=role,
                overall=overall,
                finishing=self._clamp_rating(base_overall - 16 + variation),
                creativity=self._clamp_rating(base_overall - 4 + variation),
                defending=self._clamp_rating(base_overall + 8 + variation),
                goalkeeping=5,
                discipline=discipline,
                fitness=fitness,
                shirt_number=resolved_shirt_number,
                display_name=display_name,
            )
        if role is PlayerRole.MIDFIELDER:
            return MatchPlayerInput(
                player_id=f"{team_id}-p{shirt_number}",
                player_name=f"{team_id.title()} Midfielder {shirt_number}",
                role=role,
                overall=self._clamp_rating(overall + 1),
                finishing=self._clamp_rating(base_overall - 2 + variation),
                creativity=self._clamp_rating(base_overall + 8 + variation),
                defending=self._clamp_rating(base_overall - 5 + variation),
                goalkeeping=5,
                discipline=discipline,
                fitness=fitness,
                shirt_number=resolved_shirt_number,
                display_name=display_name,
            )
        return MatchPlayerInput(
            player_id=f"{team_id}-p{shirt_number}",
            player_name=f"{team_id.title()} Forward {shirt_number}",
            role=role,
            overall=self._clamp_rating(overall + 2),
            finishing=self._clamp_rating(base_overall + 10 + variation),
            creativity=self._clamp_rating(base_overall + 2 + variation),
            defending=self._clamp_rating(base_overall - 18 + variation),
            goalkeeping=5,
            discipline=discipline,
            fitness=fitness,
            shirt_number=resolved_shirt_number,
            display_name=display_name,
        )

    def _tactical_contrast_score(self, left: SimulationGameProfileView, right: SimulationGameProfileView) -> int:
        left_style = left.tactical_profile.style
        right_style = right.tactical_profile.style
        pair = frozenset({left_style, right_style})
        base = 68
        if left_style == right_style:
            base = 62
        elif pair == {TacticalStyleProfile.POSSESSION, TacticalStyleProfile.COUNTER}:
            base = 96
        elif pair == {TacticalStyleProfile.POSSESSION, TacticalStyleProfile.LONG_BALL}:
            base = 86
        elif pair == {TacticalStyleProfile.DIRECT, TacticalStyleProfile.POSSESSION}:
            base = 82
        elif pair == {TacticalStyleProfile.BALANCED, TacticalStyleProfile.COUNTER}:
            base = 79
        elif pair == {TacticalStyleProfile.BALANCED, TacticalStyleProfile.POSSESSION}:
            base = 72
        elif pair == {TacticalStyleProfile.LONG_BALL, TacticalStyleProfile.COUNTER}:
            base = 74
        pressing_pair = {left.tactical_profile.pressing, right.tactical_profile.pressing}
        tempo_pair = {left.tactical_profile.tempo, right.tactical_profile.tempo}
        if left.tactical_profile.pressing == right.tactical_profile.pressing:
            base -= 6
        if pressing_pair == {PressingProfile.HIGH, PressingProfile.LOW}:
            base += 8
        if PressingProfile.HIGH in pressing_pair and TacticalStyleProfile.LONG_BALL in pair:
            base += 12
        if tempo_pair == {TempoProfile.FAST, TempoProfile.SLOW}:
            base += 8
        elif len(tempo_pair) == 2:
            base += 4
        if (
            left.tactical_profile.style == right.tactical_profile.style
            and left.tactical_profile.pressing == right.tactical_profile.pressing
            and left.tactical_profile.tempo == right.tactical_profile.tempo
        ):
            base = 70
        return int(max(0, min(100, base)))

    def _tactical_fit_score(self, contrast: int, *, match_style: QuickGameStyle) -> float:
        target = 68 if match_style is QuickGameStyle.BALANCED else 94
        return max(0.0, 100.0 - (abs(contrast - target) * 2.2))

    def _latency_score(self, left: SimulationGameProfileView, right: SimulationGameProfileView) -> float:
        base = 56.0
        if left.region == right.region:
            base = 96.0
        elif self._region_bucket(left.region) == self._region_bucket(right.region):
            base = 82.0
        connection_map = {
            ConnectionQuality.POOR: -14.0,
            ConnectionQuality.FAIR: -5.0,
            ConnectionQuality.GOOD: 6.0,
            ConnectionQuality.EXCELLENT: 10.0,
        }
        base += connection_map[left.connection_quality]
        base += connection_map[right.connection_quality]
        return max(0.0, min(100.0, base))

    def _recommended_mode(
        self,
        requester: SimulationGameProfileView,
        candidate: SimulationGameProfileView,
        *,
        latency_score: float,
    ) -> SimulationExecutionMode:
        if (
            latency_score >= 82
            and requester.connection_quality in {ConnectionQuality.GOOD, ConnectionQuality.EXCELLENT}
            and candidate.connection_quality in {ConnectionQuality.GOOD, ConnectionQuality.EXCELLENT}
        ):
            return SimulationExecutionMode.LIVE
        return SimulationExecutionMode.ASYNC

    def _latency_tier(self, latency_score: float) -> str:
        if latency_score >= 90:
            return "excellent"
        if latency_score >= 74:
            return "good"
        return "playable"

    def _match_context_type(self, tactical_contrast: int, *, queue_source: str) -> str:
        if queue_source == "bot":
            return "fallback_bot"
        return "tactical_clash" if tactical_contrast >= 86 else "balanced"

    def _expected_difficulty(
        self,
        requester: SimulationGameProfileView,
        opponent: SimulationGameProfileView,
        *,
        tactical_contrast: int,
    ) -> str:
        edge = (opponent.manager_rating - requester.manager_rating) + (
            (opponent.squad_strength - requester.squad_strength) * 8
        )
        if edge >= 45 or tactical_contrast >= 92 or opponent.bot_profile is BotClubProfile.ELITE_TACTICAL:
            return "high"
        if edge <= -45 or opponent.bot_profile is BotClubProfile.BEGINNER:
            return "low"
        return "medium"

    def _describe_tactical_story(
        self,
        left: SimulationGameProfileView,
        right: SimulationGameProfileView,
        *,
        context_type: str,
    ) -> str:
        if context_type == "fallback_bot":
            return (
                f"{left.club_name} receives an instant bot fallback against {right.club_name} to keep the queue moving."
            )
        if context_type == "tactical_clash":
            return (
                f"{left.club_name} want {self._tactical_phrase(left.tactical_profile)}, while "
                f"{right.club_name} answer with {self._tactical_phrase(right.tactical_profile)}."
            )
        return (
            f"Both managers arrive with comparable profiles, creating a measured duel between "
            f"{self._tactical_label(left)} and {self._tactical_label(right)}."
        )

    def _tournament_seed_score(self, profile: SimulationGameProfileView) -> float:
        return (profile.manager_rating * 0.65) + (profile.squad_strength * 7.0) + (profile.squad_depth * 2.5)

    def _tournament_narrative(self, entrants: list[SimulationGameProfileView]) -> str:
        distinct_styles = {profile.tactical_profile.style for profile in entrants}
        rating_spread = max(profile.manager_rating for profile in entrants) - min(
            profile.manager_rating for profile in entrants
        )
        if len(distinct_styles) >= max(3, len(entrants) // 3):
            return "Clash of styles tournament"
        if rating_spread >= 180:
            return "Underdog path tournament"
        return "Balanced contenders bracket"

    def _default_hosted_size(self, competition_type: HostedCompetitionType) -> int:
        return 10 if competition_type is HostedCompetitionType.LEAGUE_MODE else 8

    def _default_competition_title(
        self,
        host: SimulationGameProfileView,
        competition_type: HostedCompetitionType,
        *,
        styles: list[TacticalStyleProfile],
    ) -> str:
        if competition_type is HostedCompetitionType.LEAGUE_MODE:
            return f"{host.club_name} League Mode"
        if competition_type is HostedCompetitionType.TACTICAL_CUP:
            return f"{self._style_text(styles[0])} Tactical Cup" if styles else "Tactical Cup"
        return "Transfer Showcase Cup"

    def _hosted_competition_format(self, competition_type: HostedCompetitionType) -> str:
        return "round_robin" if competition_type is HostedCompetitionType.LEAGUE_MODE else "knockout"

    def _hosted_competition_narrative(
        self,
        competition_type: HostedCompetitionType,
        entrants: list[SimulationGameProfileView],
        *,
        styles: list[TacticalStyleProfile],
    ) -> str:
        if competition_type is HostedCompetitionType.LEAGUE_MODE:
            return (
                f"{len(entrants)} clubs enter a round-robin ladder built for stable scouting signal and table pressure."
            )
        if competition_type is HostedCompetitionType.TACTICAL_CUP:
            if styles:
                return f"A style-locked cup where {self._style_text(styles[0]).lower()} teams collide without mirror-match bloat."
            return "A style-driven knockout cup that prioritizes tactical identity over random entry."
        return "A showcase cup where match performance feeds scouting visibility, market heat, and transfer demand."

    def _hosted_match_flow(
        self,
        competition_type: HostedCompetitionType,
        simulation_mode: SimulationExecutionMode,
    ) -> list[str]:
        if competition_type is HostedCompetitionType.LEAGUE_MODE:
            return [
                "Round-robin schedule with standings updates after every simulated fixture.",
                f"{simulation_mode.value.capitalize()} fixtures can coexist with async catch-up runs.",
                "Player form and club momentum feed season-long scouting visibility.",
            ]
        if competition_type is HostedCompetitionType.TACTICAL_CUP:
            return [
                "Bracket seeded to avoid same-style meetings in the opening round whenever possible.",
                f"{simulation_mode.value.capitalize()} knockout ties can run instantly or on a deferred schedule.",
                "Tactical identity stays central to both entry rules and story framing.",
            ]
        return [
            "Knockout ties are tuned to surface player performance spikes for scouting.",
            f"{simulation_mode.value.capitalize()} execution supports both instant showcase nights and async tournament blocks.",
            "Strong tournament runs raise player form, transfer demand, and marketplace placement.",
        ]

    def _derive_club_name(self, club_id: str) -> str:
        cleaned = club_id.replace("-", " ").replace("_", " ").strip()
        return " ".join(part.capitalize() for part in cleaned.split()) or club_id

    def _seed_hint(self, key: str) -> int:
        return int(sha256(key.encode("utf-8")).hexdigest()[:8], 16) % 1_000_000

    def _formation_for_style(self, style: TacticalStyleProfile) -> str:
        return {
            TacticalStyleProfile.POSSESSION: "4-3-3",
            TacticalStyleProfile.COUNTER: "4-2-3-1",
            TacticalStyleProfile.LONG_BALL: "4-4-2",
            TacticalStyleProfile.BALANCED: "4-3-3",
            TacticalStyleProfile.DIRECT: "3-4-3",
        }[style]

    def _match_engine_style(self, style: TacticalStyleProfile, pressing: PressingProfile) -> TacticalStyle:
        if style in {TacticalStyleProfile.COUNTER, TacticalStyleProfile.LONG_BALL}:
            return TacticalStyle.DEFENSIVE
        if style is TacticalStyleProfile.DIRECT or pressing is PressingProfile.HIGH:
            return TacticalStyle.ATTACKING
        return TacticalStyle.BALANCED

    def _pressing_value(self, pressing: PressingProfile) -> int:
        return {PressingProfile.LOW: 35, PressingProfile.MEDIUM: 58, PressingProfile.HIGH: 82}[pressing]

    def _tempo_value(self, tempo: TempoProfile) -> int:
        return {TempoProfile.SLOW: 38, TempoProfile.NORMAL: 58, TempoProfile.FAST: 80}[tempo]

    def _aggression_value(self, profile: TacticalProfileInput) -> int:
        base = 48
        if profile.pressing is PressingProfile.HIGH:
            base += 14
        if profile.style is TacticalStyleProfile.DIRECT:
            base += 8
        if profile.style is TacticalStyleProfile.COUNTER:
            base -= 4
        return self._clamp_rating(base)

    def _defensive_line(self, profile: TacticalProfileInput) -> int:
        base = 52
        if profile.pressing is PressingProfile.HIGH:
            base += 16
        if profile.style in {TacticalStyleProfile.COUNTER, TacticalStyleProfile.LONG_BALL}:
            base -= 10
        return self._clamp_rating(base)

    def _width_value(self, style: TacticalStyleProfile) -> int:
        return {
            TacticalStyleProfile.POSSESSION: 58,
            TacticalStyleProfile.COUNTER: 46,
            TacticalStyleProfile.LONG_BALL: 62,
            TacticalStyleProfile.BALANCED: 54,
            TacticalStyleProfile.DIRECT: 66,
        }[style]

    def _set_piece_value(self, style: TacticalStyleProfile) -> int:
        return {
            TacticalStyleProfile.POSSESSION: 48,
            TacticalStyleProfile.COUNTER: 58,
            TacticalStyleProfile.LONG_BALL: 72,
            TacticalStyleProfile.BALANCED: 54,
            TacticalStyleProfile.DIRECT: 64,
        }[style]

    def _starter_roles(self, formation: str) -> list[PlayerRole]:
        lines = [int(part) for part in formation.split("-")]
        return (
            [PlayerRole.GOALKEEPER]
            + ([PlayerRole.DEFENDER] * lines[0])
            + ([PlayerRole.MIDFIELDER] * sum(lines[1:-1]))
            + ([PlayerRole.FORWARD] * lines[-1])
        )

    def _tactical_phrase(self, profile: TacticalProfileInput) -> str:
        return f"{self._style_text(profile.style).lower()} with {profile.pressing.value} pressing and a {profile.tempo.value} tempo"

    def _tactical_label(self, profile: SimulationGameProfileView) -> str:
        return self._style_text(profile.tactical_profile.style)

    def _style_text(self, style: TacticalStyleProfile) -> str:
        return style.value.replace("_", " ").title()

    def _region_bucket(self, region: str) -> str:
        return region.split("-", 1)[0].upper()

    def _clamp_rating(self, value: int) -> int:
        return max(1, min(99, value))

    def _default_bots(self) -> tuple[SimulationGameProfileView, ...]:
        return (
            SimulationGameProfileView(
                user_id="bot_beginner_af_west",
                club_id="bot_club_beginner_af_west",
                club_name="Accra Sparks",
                manager_rating=1320,
                tactical_profile=TacticalProfileInput(
                    style=TacticalStyleProfile.BALANCED,
                    pressing=PressingProfile.MEDIUM,
                    tempo=TempoProfile.NORMAL,
                ),
                squad_strength=73,
                squad_depth=61,
                preferred_match_type=[
                    SimulationMatchType.QUICK,
                    SimulationMatchType.TOURNAMENT,
                    SimulationMatchType.HOSTED,
                ],
                connection_quality=ConnectionQuality.GOOD,
                region="AF-WEST",
                availability=AvailabilityStatus.ONLINE,
                is_bot=True,
                bot_profile=BotClubProfile.BEGINNER,
            ),
            SimulationGameProfileView(
                user_id="bot_balanced_af_west",
                club_id="bot_club_balanced_af_west",
                club_name="Lagos Titans AI",
                manager_rating=1440,
                tactical_profile=TacticalProfileInput(
                    style=TacticalStyleProfile.COUNTER,
                    pressing=PressingProfile.MEDIUM,
                    tempo=TempoProfile.FAST,
                ),
                squad_strength=79,
                squad_depth=68,
                preferred_match_type=[
                    SimulationMatchType.QUICK,
                    SimulationMatchType.TOURNAMENT,
                    SimulationMatchType.HOSTED,
                ],
                connection_quality=ConnectionQuality.GOOD,
                region="AF-WEST",
                availability=AvailabilityStatus.ONLINE,
                is_bot=True,
                bot_profile=BotClubProfile.BALANCED,
            ),
            SimulationGameProfileView(
                user_id="bot_elite_tactical_af_west",
                club_id="bot_club_elite_tactical_af_west",
                club_name="Abidjan Press Lab",
                manager_rating=1560,
                tactical_profile=TacticalProfileInput(
                    style=TacticalStyleProfile.DIRECT,
                    pressing=PressingProfile.HIGH,
                    tempo=TempoProfile.FAST,
                ),
                squad_strength=84,
                squad_depth=76,
                preferred_match_type=[
                    SimulationMatchType.QUICK,
                    SimulationMatchType.TOURNAMENT,
                    SimulationMatchType.HOSTED,
                ],
                connection_quality=ConnectionQuality.EXCELLENT,
                region="AF-WEST",
                availability=AvailabilityStatus.ONLINE,
                is_bot=True,
                bot_profile=BotClubProfile.ELITE_TACTICAL,
            ),
        )
