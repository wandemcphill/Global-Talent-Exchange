from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.ultimate_league.league_service import (
    GTexPrizePayout,
    LeagueCompetitor,
    LeagueStandingEntry,
    LeagueTierDefinition,
    LeagueTournamentPlan,
    TacticalPresetListing,
    UltimateLeagueError,
)
from app.ultimate_league.runtime import UltimateLeagueNotFoundError, UltimateLeagueRuntime
from app.ultimate_league.schemas import (
    TacticalPresetListingRequest,
    TacticalPresetPurchaseRequest,
    TacticalPresetView,
    UltimateLeagueCompetitorInput,
    UltimateLeagueCompetitorView,
    UltimateLeagueMatchmakingRequest,
    UltimateLeagueMatchmakingResponse,
    UltimateLeagueMatchProposalView,
    UltimateLeagueMatchResultRequest,
    UltimateLeagueMatchResultResponse,
    UltimateLeaguePayoutPreviewRequest,
    UltimateLeaguePayoutPreviewResponse,
    UltimateLeaguePayoutView,
    UltimateLeagueRatingUpdateView,
    UltimateLeagueStandingEntryView,
    UltimateLeagueStandingsView,
    UltimateLeagueTierView,
    UltimateLeagueTournamentMatchView,
    UltimateLeagueTournamentRequest,
    UltimateLeagueTournamentRoundView,
    UltimateLeagueTournamentSlotView,
    UltimateLeagueTournamentView,
)

router = APIRouter(tags=["ultimate-league"])
legacy_router = APIRouter(prefix="/ultimate-league")
api_router = APIRouter(prefix="/api/ultimate-league")


def get_ultimate_league_runtime(request: Request) -> UltimateLeagueRuntime:
    runtime = getattr(request.app.state, "ultimate_league_runtime", None)
    if runtime is None:
        runtime = UltimateLeagueRuntime()
        request.app.state.ultimate_league_runtime = runtime
    return runtime


@legacy_router.get("/tiers", response_model=list[UltimateLeagueTierView])
@api_router.get("/tiers", response_model=list[UltimateLeagueTierView])
def list_tiers(
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
) -> list[UltimateLeagueTierView]:
    counts = {definition.tier: len(runtime.standings(definition.tier)) for definition in runtime.list_tiers()}
    return [
        _serialize_tier(definition, competitor_count=counts.get(definition.tier, 0))
        for definition in runtime.list_tiers()
    ]


@legacy_router.put("/competitors/{competitor_id}", response_model=UltimateLeagueCompetitorView)
@api_router.put("/competitors/{competitor_id}", response_model=UltimateLeagueCompetitorView)
def upsert_competitor(
    competitor_id: str,
    payload: UltimateLeagueCompetitorInput,
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
    current_user: User = Depends(get_current_user),
) -> UltimateLeagueCompetitorView:
    if payload.competitor_id != competitor_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Path competitor_id must match payload competitor_id."
        )
    if payload.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Competitor ownership must match the authenticated user.",
        )
    competitor = runtime.upsert_competitor(
        LeagueCompetitor(
            competitor_id=payload.competitor_id,
            display_name=payload.display_name,
            elo_rating=payload.elo_rating,
            user_id=payload.user_id,
            wins=payload.wins,
            draws=payload.draws,
            losses=payload.losses,
            region=payload.region,
            queue_entered_at=payload.queue_entered_at,
            fatigue=payload.fatigue,
            injury_status=payload.injury_status,
            tactical_preset_id=payload.tactical_preset_id,
        )
    )
    return _serialize_competitor(runtime, competitor)


@legacy_router.get("/competitors/{competitor_id}", response_model=UltimateLeagueCompetitorView)
@api_router.get("/competitors/{competitor_id}", response_model=UltimateLeagueCompetitorView)
def get_competitor(
    competitor_id: str,
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
) -> UltimateLeagueCompetitorView:
    try:
        return _serialize_competitor(runtime, runtime.get_competitor(competitor_id))
    except UltimateLeagueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@legacy_router.get("/standings/{tier}", response_model=UltimateLeagueStandingsView)
@api_router.get("/standings/{tier}", response_model=UltimateLeagueStandingsView)
def get_standings(
    tier: str,
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
) -> UltimateLeagueStandingsView:
    try:
        entries = runtime.standings(tier)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return UltimateLeagueStandingsView(
        tier=tier,
        entries=[_serialize_standing_entry(runtime, entry) for entry in entries],
    )


@legacy_router.post("/matchmaking/batch", response_model=UltimateLeagueMatchmakingResponse)
@api_router.post("/matchmaking/batch", response_model=UltimateLeagueMatchmakingResponse)
def create_matchmaking_batch(
    payload: UltimateLeagueMatchmakingRequest,
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
    _: User = Depends(get_current_user),
) -> UltimateLeagueMatchmakingResponse:
    try:
        batch = runtime.matchmaking(
            competitor_ids=payload.competitor_ids,
            prefer_same_tier=payload.prefer_same_tier,
        )
    except (UltimateLeagueError, UltimateLeagueNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return UltimateLeagueMatchmakingResponse(
        proposals=[
            UltimateLeagueMatchProposalView(
                match_id=proposal.match_id,
                home=_serialize_competitor(runtime, runtime.get_competitor(proposal.home.competitor_id)),
                away=_serialize_competitor(runtime, runtime.get_competitor(proposal.away.competitor_id)),
                rating_gap=proposal.rating_gap,
                search_window_used=proposal.search_window_used,
                same_tier=proposal.same_tier,
                same_region=proposal.same_region,
            )
            for proposal in batch.proposals
        ],
        unmatched=[
            _serialize_competitor(runtime, runtime.get_competitor(item.competitor_id)) for item in batch.unmatched
        ],
    )


@legacy_router.post("/matches/result", response_model=UltimateLeagueMatchResultResponse)
@api_router.post("/matches/result", response_model=UltimateLeagueMatchResultResponse)
def submit_match_result(
    payload: UltimateLeagueMatchResultRequest,
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
    current_user: User = Depends(get_current_user),
) -> UltimateLeagueMatchResultResponse:
    try:
        home_candidate = runtime.get_competitor(payload.home_competitor_id)
        away_candidate = runtime.get_competitor(payload.away_competitor_id)
        if current_user.id not in {home_candidate.user_id, away_candidate.user_id}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a participant may submit an Ultimate League match result.",
            )
        home, away, rating_update = runtime.record_match_result(
            home_competitor_id=payload.home_competitor_id,
            away_competitor_id=payload.away_competitor_id,
            home_score=payload.home_score,
            away_score=payload.away_score,
            importance=payload.importance,
        )
    except UltimateLeagueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UltimateLeagueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return UltimateLeagueMatchResultResponse(
        home=_serialize_competitor(runtime, home),
        away=_serialize_competitor(runtime, away),
        rating_update=UltimateLeagueRatingUpdateView(
            home_competitor_id=rating_update.home_competitor_id,
            away_competitor_id=rating_update.away_competitor_id,
            expected_home_score=rating_update.expected_home_score,
            expected_away_score=rating_update.expected_away_score,
            actual_home_score=rating_update.actual_home_score,
            actual_away_score=rating_update.actual_away_score,
            home_delta=rating_update.home_delta,
            away_delta=rating_update.away_delta,
            home_new_rating=rating_update.home_new_rating,
            away_new_rating=rating_update.away_new_rating,
            effective_k_factor=rating_update.effective_k_factor,
        ),
    )


@legacy_router.post("/tournaments", response_model=UltimateLeagueTournamentView)
@api_router.post("/tournaments", response_model=UltimateLeagueTournamentView)
def create_tournament(
    payload: UltimateLeagueTournamentRequest,
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
    _: User = Depends(get_current_user),
) -> UltimateLeagueTournamentView:
    try:
        tournament = runtime.create_tournament(
            tournament_id=payload.tournament_id,
            tier=payload.tier,
            starts_at=payload.starts_at,
            competitor_ids=payload.competitor_ids,
            field_size=payload.field_size,
            round_spacing_minutes=payload.round_spacing_minutes,
            match_spacing_minutes=payload.match_spacing_minutes,
            parallel_matches=payload.parallel_matches,
        )
    except UltimateLeagueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UltimateLeagueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _serialize_tournament(runtime, tournament)


@legacy_router.get("/tournaments/{tournament_id}", response_model=UltimateLeagueTournamentView)
@api_router.get("/tournaments/{tournament_id}", response_model=UltimateLeagueTournamentView)
def get_tournament(
    tournament_id: str,
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
) -> UltimateLeagueTournamentView:
    try:
        return _serialize_tournament(runtime, runtime.get_tournament(tournament_id))
    except UltimateLeagueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@legacy_router.post("/tournaments/{tournament_id}/payouts/preview", response_model=UltimateLeaguePayoutPreviewResponse)
@api_router.post("/tournaments/{tournament_id}/payouts/preview", response_model=UltimateLeaguePayoutPreviewResponse)
def preview_payouts(
    tournament_id: str,
    payload: UltimateLeaguePayoutPreviewRequest,
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
) -> UltimateLeaguePayoutPreviewResponse:
    try:
        payouts = runtime.preview_payouts(
            tournament_id=tournament_id,
            placements=payload.placements,
            gross_pool_gtex=payload.gross_pool_gtex,
            entrant_count=payload.entrant_count,
            payout_percentages=payload.payout_percentages,
        )
    except UltimateLeagueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UltimateLeagueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return UltimateLeaguePayoutPreviewResponse(
        tournament_id=tournament_id,
        payouts=[_serialize_payout(item) for item in payouts],
        total_gtex=sum((item.amount for item in payouts), start=Decimal("0.0000")),
    )


@legacy_router.get("/tactical-presets", response_model=list[TacticalPresetView])
@api_router.get("/tactical-presets", response_model=list[TacticalPresetView])
def list_tactical_presets(
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
) -> list[TacticalPresetView]:
    return [_serialize_tactical_preset(item) for item in runtime.list_tactical_presets()]


@legacy_router.post("/tactical-presets", response_model=TacticalPresetView)
@api_router.post("/tactical-presets", response_model=TacticalPresetView)
def upsert_tactical_preset(
    payload: TacticalPresetListingRequest,
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
    _: User = Depends(get_current_user),
) -> TacticalPresetView:
    try:
        preset = runtime.upsert_tactical_preset(
            preset_id=payload.preset_id,
            seller_competitor_id=payload.seller_competitor_id,
            title=payload.title,
            formation=payload.formation,
            style=payload.style,
            price_gtex=payload.price_gtex,
            tags=payload.tags,
            fatigue_ceiling=payload.fatigue_ceiling,
            injury_cover_enabled=payload.injury_cover_enabled,
        )
    except UltimateLeagueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_tactical_preset(preset)


@legacy_router.post("/tactical-presets/{preset_id}/purchase", response_model=TacticalPresetView)
@api_router.post("/tactical-presets/{preset_id}/purchase", response_model=TacticalPresetView)
def purchase_tactical_preset(
    preset_id: str,
    payload: TacticalPresetPurchaseRequest,
    _: User = Depends(get_current_user),
    runtime: UltimateLeagueRuntime = Depends(get_ultimate_league_runtime),
) -> TacticalPresetView:
    # Purchases spend a competitor's balance; they must never be anonymous.
    try:
        preset = runtime.purchase_tactical_preset(
            preset_id=preset_id,
            buyer_competitor_id=payload.buyer_competitor_id,
        )
    except UltimateLeagueNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except UltimateLeagueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _serialize_tactical_preset(preset)


def _serialize_competitor(runtime: UltimateLeagueRuntime, competitor: LeagueCompetitor) -> UltimateLeagueCompetitorView:
    return UltimateLeagueCompetitorView(
        competitor_id=competitor.competitor_id,
        display_name=competitor.display_name,
        elo_rating=competitor.elo_rating,
        user_id=competitor.user_id,
        wins=competitor.wins,
        draws=competitor.draws,
        losses=competitor.losses,
        matches_played=competitor.matches_played,
        league_points=competitor.league_points,
        win_rate=competitor.win_rate,
        tier=runtime.service.tier_for_rating(competitor.elo_rating).tier,
        region=competitor.region,
        queue_entered_at=competitor.queue_entered_at,
        fatigue=competitor.fatigue,
        injury_status=competitor.injury_status,
        availability_status=competitor.availability_status,
        tactical_preset_id=competitor.tactical_preset_id,
    )


def _serialize_tier(definition: LeagueTierDefinition, *, competitor_count: int) -> UltimateLeagueTierView:
    return UltimateLeagueTierView(
        tier=definition.tier,
        label=definition.label,
        min_elo=definition.min_elo,
        max_elo=definition.max_elo,
        promotion_slots=definition.promotion_slots,
        relegation_slots=definition.relegation_slots,
        default_tournament_size=definition.default_tournament_size,
        competitor_count=competitor_count,
    )


def _serialize_standing_entry(
    runtime: UltimateLeagueRuntime, entry: LeagueStandingEntry
) -> UltimateLeagueStandingEntryView:
    return UltimateLeagueStandingEntryView(
        rank=entry.rank,
        tier=entry.tier,
        zone=entry.zone,
        competitor=_serialize_competitor(runtime, entry.competitor),
        league_points=entry.league_points,
        matches_played=entry.matches_played,
        win_rate=entry.win_rate,
    )


def _serialize_tournament(
    runtime: UltimateLeagueRuntime, tournament: LeagueTournamentPlan
) -> UltimateLeagueTournamentView:
    entrants = [
        _serialize_competitor(runtime, runtime.get_competitor(entrant.competitor_id))
        for entrant in tournament.entrants
        if entrant.competitor_id in runtime.competitors
    ]
    return UltimateLeagueTournamentView(
        tournament_id=tournament.tournament_id,
        tier=tournament.tier,
        entrants=entrants,
        recommended_payout_percentages=list(tournament.recommended_payout_percentages),
        bracket_size=tournament.bracket.bracket_size,
        rounds=[
            UltimateLeagueTournamentRoundView(
                round_number=round_view.round_number,
                round_name=round_view.round_name,
                matches=[
                    UltimateLeagueTournamentMatchView(
                        match_id=match.match_id,
                        round_number=match.round_number,
                        round_name=match.round_name,
                        slot_number=match.slot_number,
                        starts_at=match.starts_at,
                        home=_serialize_slot(match.home),
                        away=_serialize_slot(match.away),
                        winner_to_match_id=match.winner_to_match_id,
                        bye_match=match.bye_match,
                    )
                    for match in round_view.matches
                ],
            )
            for round_view in tournament.bracket.rounds
        ],
    )


def _serialize_slot(slot) -> UltimateLeagueTournamentSlotView | None:
    if slot is None:
        return None
    return UltimateLeagueTournamentSlotView(
        competitor_id=slot.competitor_id,
        display_name=slot.display_name,
        seed=slot.seed,
        source_match_id=slot.source_match_id,
        auto_advanced=slot.auto_advanced,
    )


def _serialize_tactical_preset(item: TacticalPresetListing) -> TacticalPresetView:
    return TacticalPresetView(
        preset_id=item.preset_id,
        seller_competitor_id=item.seller_competitor_id,
        seller_display_name=item.seller_display_name,
        title=item.title,
        formation=item.formation,
        style=item.style,
        price_gtex=item.price_gtex,
        tags=list(item.tags),
        fatigue_ceiling=item.fatigue_ceiling,
        injury_cover_enabled=item.injury_cover_enabled,
        created_at=item.created_at,
    )


def _serialize_payout(payout: GTexPrizePayout) -> UltimateLeaguePayoutView:
    return UltimateLeaguePayoutView(
        tournament_id=payout.tournament_id,
        tier=payout.tier,
        placement=payout.placement,
        competitor_id=payout.competitor_id,
        display_name=payout.display_name,
        amount=payout.amount,
        share_percentage=payout.share_percentage,
        unit=payout.unit,
    )


router.include_router(legacy_router)
router.include_router(api_router)


__all__ = ["get_ultimate_league_runtime", "router"]
