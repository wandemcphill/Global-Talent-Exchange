from __future__ import annotations

import math
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.ingestion.models import Player
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.regen import RegenProfile, RegenScoutReport
from app.models.regen_ecosystem import Scout
from app.models.scouting_intelligence import ScoutMission, ScoutReport, ScoutingNetwork
from app.models.transfer_market import TransferListing
from app.models.user import User
from app.schemas.regen_ecosystem import ScoutReportView
from app.services.regen_ecosystem_service import (
    RegenEcosystemError,
    RegenEcosystemNotFoundError,
    RegenEcosystemService,
    RegenEcosystemValidationError,
)
from app.talent.models import TalentRankingSnapshot
from app.talent.service import TalentExchangeService
from app.transfer_market.schemas import WatchlistEntryCreateRequest
from app.transfer_market.service import TransferMarketService

router = APIRouter(tags=["player-lifecycle"])


def _service(session: Session = Depends(get_session)) -> RegenEcosystemService:
    return RegenEcosystemService(session)


def _raise(exc: RegenEcosystemError) -> None:
    if isinstance(exc, RegenEcosystemNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RegenEcosystemValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


def _resolve_owned_club_ids(session: Session, user_id: str) -> list[str]:
    return list(
        session.scalars(
            select(ClubProfile.id).where(ClubProfile.owner_user_id == user_id).order_by(ClubProfile.created_at.asc())
        ).all()
    )


def _resolve_active_scout(session: Session, *, owned_club_ids: list[str]) -> Scout | None:
    """Resolve an active scout strictly through clubs owned by the caller."""
    if not owned_club_ids:
        return None
    return session.scalar(
        select(Scout)
        .where(
            Scout.club_id.in_(owned_club_ids),
            Scout.active.is_(True),
        )
        .order_by(Scout.created_at.asc(), Scout.id.asc())
    )


@router.post("/scout/report/{player_id}", response_model=ScoutReportView)
def scout_player(
    player_id: str,
    current_user: User = Depends(get_current_user),
    service: RegenEcosystemService = Depends(_service),
) -> ScoutReportView:
    """Generate and persist a live scout report using the authenticated user's own active scout."""
    clean_player_id = player_id.strip()
    if not clean_player_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player id is required to scout.",
        )

    owned_club_ids = _resolve_owned_club_ids(service.session, current_user.id)
    scout = _resolve_active_scout(service.session, owned_club_ids=owned_club_ids)
    if scout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active scout is assigned to the authenticated club user",
        )

    # 1. Check if the player is a regen profile
    regen = service.session.scalar(
        select(RegenProfile).where(
            or_(
                RegenProfile.id == clean_player_id,
                RegenProfile.regen_id == clean_player_id,
                RegenProfile.player_id == clean_player_id,
            )
        )
    )

    if regen is not None:
        try:
            result = service.get_scout_report(regen.id, scout_id=scout.id)
            if not result.club_id:
                result.club_id = scout.club_id
        except RegenEcosystemError as exc:
            _raise(exc)
        service.session.commit()
        return result

    # 2. Check if the player is a canonical real player
    player = service.session.get(Player, clean_player_id)
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player '{clean_player_id}' was not found.",
        )

    # Real player scouting: reuse canonical TalentExchangeService and persistence
    talent_service = TalentExchangeService(service.session)
    try:
        talent_profile = talent_service.get_profile_row(player.id)
    except Exception:
        talent_profile = talent_service.sync_profile_from_player(player.id)

    accuracy = max(0, min(100, scout.skill_rating))
    dna_profile = player.dna_profile if isinstance(player.dna_profile, dict) else {}

    def authoritative_rating(value: Any) -> int | None:
        """Accept an explicitly supplied canonical rating; never invent one."""
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            return None
        rounded = int(round(value))
        return rounded if 1 <= rounded <= 99 else None

    # A talent ranking is a sporting-discovery score, not a player's overall
    # ability rating. Use the canonical imported rating field for this report.
    current_ability = authoritative_rating(dna_profile.get("overall_rating"))
    if current_ability is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A trusted overall_rating is unavailable; this player cannot receive an ability estimate yet.",
        )

    potential_source = player.potential
    if potential_source is None:
        potential_source = dna_profile.get("potential_rating")
    future_potential = authoritative_rating(potential_source)
    if future_potential is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A trusted potential rating is unavailable; this player cannot receive a potential estimate yet.",
        )

    latest_ranking = service.session.scalar(
        select(TalentRankingSnapshot)
        .where(TalentRankingSnapshot.player_id == player.id)
        .order_by(TalentRankingSnapshot.as_of.desc(), TalentRankingSnapshot.created_at.desc())
    )
    components = (
        {
            str(item.get("code")): item
            for item in latest_ranking.components_json
            if isinstance(item, dict) and item.get("code")
        }
        if latest_ranking is not None and isinstance(latest_ranking.components_json, list)
        else {}
    )

    visible_stats: dict[str, int] = {"rating": current_ability}
    form_component = components.get("recent_form")
    if isinstance(form_component, dict) and int(form_component.get("sample_size") or 0) > 0:
        form_score = authoritative_rating(form_component.get("score"))
        if form_score is not None:
            visible_stats["form"] = form_score
    if float(talent_profile.experience_years or 0.0) > 0:
        visible_stats["experience"] = min(30, int(round(talent_profile.experience_years)))
    for key, value in dna_profile.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            visible_stats[str(key)] = int(value)

    # Consistency is only meaningful when the ranking pipeline has sufficient
    # rated appearances. Never expose a neutral database default as observed form.
    consistency_component = components.get("consistency")
    consistency_score = None
    if isinstance(consistency_component, dict) and int(consistency_component.get("sample_size") or 0) >= 3:
        consistency_score = authoritative_rating(consistency_component.get("score"))
    hidden_stats: dict[str, int | None] = {
        "potential_ceiling": future_potential,
        "consistency": consistency_score,
    }

    error_span = max(1, round((100 - accuracy) / 10))
    potential_range = {
        "minimum": max(1, future_potential - error_span),
        "maximum": min(99, future_potential + error_span),
    }

    summary_text = (
        f"Scout {scout.id} report for {player.canonical_display_name or player.full_name}: "
        f"{player.normalized_position or player.position or 'Player'}, source ability rating {current_ability}, "
        f"source potential rating {future_potential}. No missing values were substituted."
    )

    # Persist report for real player
    club_id = scout.club_id
    if club_id:
        network = service.session.scalar(
            select(ScoutingNetwork).where(ScoutingNetwork.club_id == club_id).order_by(ScoutingNetwork.created_at.asc())
        )
        if network is None:
            network = ScoutingNetwork(
                club_id=club_id,
                network_name="Club Scouting Network",
                region_code=scout.region or "global",
                region_name=scout.region or "Global",
                specialty_code=scout.specialty or "youth",
                quality_tier="standard",
                weekly_cost_coin=0,
                scout_identity=scout.id,
            )
            service.session.add(network)
            service.session.flush()

        mission = service.session.scalar(
            select(ScoutMission).where(ScoutMission.club_id == club_id, ScoutMission.network_id == network.id)
        )
        if mission is None:
            mission = ScoutMission(
                club_id=club_id,
                network_id=network.id,
                mission_name="Direct Player Scout",
                mission_type="direct",
                target_position=player.normalized_position or "ANY",
                target_region=scout.region or "global",
                status="completed",
            )
            service.session.add(mission)
            service.session.flush()

        scout_report_row = ScoutReport(
            mission_id=mission.id,
            network_id=network.id,
            club_id=club_id,
            player_id=player.id,
            recommendation_rank=1,
            lifecycle_phase=(
                "senior"
                if (player.date_of_birth and (date.today().year - player.date_of_birth.year) >= 21)
                else "youth"
            ),
            confidence_bps=accuracy * 100,
            fit_score=float(current_ability),
            potential_signal_score=float(future_potential),
            value_signal_score=float(player.market_value_eur or 0.0),
            hidden_gem_signal=bool(future_potential - current_ability >= 10),
            current_ability_estimate=current_ability,
            future_potential_estimate=future_potential,
            value_hint_coin=(
                int(player.current_market_reference_value or 0) if player.current_market_reference_value else None
            ),
            summary_text=summary_text,
            tags_json=["real_player", "scouted"],
            metadata_json={"scout_id": scout.id, "accuracy": accuracy},
        )
        service.session.add(scout_report_row)

    service.session.commit()

    return ScoutReportView(
        scout_id=scout.id,
        player_id=player.id,
        regen_profile_id=None,
        club_id=club_id,
        accuracy=accuracy,
        visible_stats=visible_stats,
        hidden_stats=hidden_stats,
        potential_range=potential_range,
        personality_state={},
        rarity_tier="standard",
        badge_codes=tuple(talent_profile.active_signal_codes_json or []),
        summary_text=summary_text,
        generated_at=utcnow(),
    )


@router.get("/scout/reports/{player_id}", response_model=ScoutReportView)
def get_player_scout_report(
    player_id: str,
    current_user: User = Depends(get_current_user),
    service: RegenEcosystemService = Depends(_service),
) -> ScoutReportView:
    """Retrieve the latest persisted scout report for a player owned by the authenticated caller's club.

    Strict ownership isolation: Reports belonging to other clubs are never returned.
    """
    clean_player_id = player_id.strip()
    if not clean_player_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player id is required to retrieve a scout report.",
        )

    owned_club_ids = _resolve_owned_club_ids(service.session, current_user.id)
    scout_ids = (
        list(service.session.scalars(select(Scout.id).where(Scout.club_id.in_(owned_club_ids))).all())
        if owned_club_ids
        else []
    )

    # 1. Check regen scout report
    regen = service.session.scalar(
        select(RegenProfile).where(
            or_(
                RegenProfile.id == clean_player_id,
                RegenProfile.regen_id == clean_player_id,
                RegenProfile.player_id == clean_player_id,
            )
        )
    )

    if regen is not None:
        report_conditions = []
        if owned_club_ids:
            report_conditions.append(RegenScoutReport.club_id.in_(owned_club_ids))
        if scout_ids:
            report_conditions.append(RegenScoutReport.scout_identity.in_(scout_ids))

        if report_conditions:
            regen_report = service.session.scalar(
                select(RegenScoutReport)
                .where(
                    RegenScoutReport.regen_id == regen.id,
                    or_(*report_conditions),
                )
                .order_by(RegenScoutReport.created_at.desc())
            )
            if regen_report is not None:
                attr = service._ensure_attribute_profile(regen)
                accuracy = max(0, min(100, round(regen_report.scout_confidence_bps / 110)))
                hidden_stats = {
                    key: service._estimate_hidden_value(
                        actual=value,
                        accuracy=accuracy,
                        specialty="youth",
                        stat_key=key,
                        scout_id=regen_report.scout_identity or "scout",
                        regen_id=regen.id,
                    )
                    for key, value in (attr.hidden_stats_json or {}).items()
                }
                return ScoutReportView(
                    scout_id=regen_report.scout_identity or "scout",
                    player_id=clean_player_id,
                    regen_profile_id=regen.id,
                    club_id=regen_report.club_id,
                    accuracy=accuracy,
                    visible_stats=dict(attr.visible_stats_json or {}),
                    hidden_stats=hidden_stats,
                    potential_range=dict(regen.potential_range_json or {}),
                    personality_state=dict(attr.personality_state_json or {}),
                    rarity_tier=attr.rarity_tier,
                    badge_codes=tuple(attr.badge_codes_json or []),
                    summary_text=regen_report.summary_text,
                    generated_at=regen_report.created_at,
                )

    # 2. Check canonical scout report for real player
    if owned_club_ids:
        scout_report = service.session.scalar(
            select(ScoutReport)
            .where(
                ScoutReport.player_id == clean_player_id,
                ScoutReport.club_id.in_(owned_club_ids),
            )
            .order_by(ScoutReport.created_at.desc())
        )
        if scout_report is not None:
            accuracy = max(0, min(100, round(scout_report.confidence_bps / 100)))
            scout_id = str((scout_report.metadata_json or {}).get("scout_id") or "scout")
            return ScoutReportView(
                scout_id=scout_id,
                player_id=scout_report.player_id or clean_player_id,
                regen_profile_id=scout_report.regen_profile_id,
                club_id=scout_report.club_id,
                accuracy=accuracy,
                visible_stats={
                    "rating": scout_report.current_ability_estimate,
                    "potential": scout_report.future_potential_estimate,
                },
                hidden_stats={"fit_score": int(scout_report.fit_score)},
                potential_range={
                    "minimum": max(1, scout_report.future_potential_estimate - 3),
                    "maximum": min(99, scout_report.future_potential_estimate + 3),
                },
                personality_state={},
                rarity_tier="standard",
                badge_codes=tuple(scout_report.tags_json or []),
                summary_text=scout_report.summary_text,
                generated_at=scout_report.created_at,
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No scout report found for player '{clean_player_id}' for the authenticated club.",
    )


@router.get("/scout/reports", response_model=list[ScoutReportView])
def list_club_scout_reports(
    current_user: User = Depends(get_current_user),
    service: RegenEcosystemService = Depends(_service),
) -> list[ScoutReportView]:
    """List all persisted scout reports for the authenticated caller's club."""
    owned_club_ids = _resolve_owned_club_ids(service.session, current_user.id)
    scout_ids = (
        list(service.session.scalars(select(Scout.id).where(Scout.club_id.in_(owned_club_ids))).all())
        if owned_club_ids
        else []
    )

    reports: list[ScoutReportView] = []

    # 1. Regens
    report_conditions = []
    if owned_club_ids:
        report_conditions.append(RegenScoutReport.club_id.in_(owned_club_ids))
    if scout_ids:
        report_conditions.append(RegenScoutReport.scout_identity.in_(scout_ids))

    if report_conditions:
        regen_reports = service.session.scalars(
            select(RegenScoutReport).where(or_(*report_conditions)).order_by(RegenScoutReport.created_at.desc())
        ).all()
        for rr in regen_reports:
            regen = service.session.get(RegenProfile, rr.regen_id)
            if regen is None:
                continue
            accuracy = max(0, min(100, round(rr.scout_confidence_bps / 110)))
            attr = service._ensure_attribute_profile(regen)
            reports.append(
                ScoutReportView(
                    scout_id=rr.scout_identity or "scout",
                    player_id=regen.player_id,
                    regen_profile_id=regen.id,
                    accuracy=accuracy,
                    visible_stats=dict(attr.visible_stats_json or {}),
                    hidden_stats={},
                    potential_range=dict(regen.potential_range_json or {}),
                    personality_state=dict(attr.personality_state_json or {}),
                    rarity_tier=attr.rarity_tier,
                    badge_codes=tuple(attr.badge_codes_json or []),
                    summary_text=rr.summary_text,
                    generated_at=rr.created_at,
                )
            )

    # 2. Real players
    if owned_club_ids:
        intel_reports = service.session.scalars(
            select(ScoutReport).where(ScoutReport.club_id.in_(owned_club_ids)).order_by(ScoutReport.created_at.desc())
        ).all()
        for ir in intel_reports:
            accuracy = max(0, min(100, round(ir.confidence_bps / 100)))
            scout_id = str((ir.metadata_json or {}).get("scout_id") or "scout")
            reports.append(
                ScoutReportView(
                    scout_id=scout_id,
                    player_id=ir.player_id or "",
                    regen_profile_id=ir.regen_profile_id,
                    accuracy=accuracy,
                    visible_stats={
                        "rating": ir.current_ability_estimate,
                        "potential": ir.future_potential_estimate,
                    },
                    hidden_stats={"fit_score": int(ir.fit_score)},
                    potential_range={
                        "minimum": max(1, ir.future_potential_estimate - 3),
                        "maximum": min(99, ir.future_potential_estimate + 3),
                    },
                    personality_state={},
                    rarity_tier="standard",
                    badge_codes=tuple(ir.tags_json or []),
                    summary_text=ir.summary_text,
                    generated_at=ir.created_at,
                )
            )

    return reports


@router.post("/scout/reports/{player_id}/transfer-room")
def handoff_scout_report_to_transfer_room(
    player_id: str,
    current_user: User = Depends(get_current_user),
    service: RegenEcosystemService = Depends(_service),
) -> dict[str, Any]:
    """Connect a valid scouting discovery directly to the existing transfer market workflow."""
    clean_player_id = player_id.strip()
    if not clean_player_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player id is required for transfer room handoff.",
        )

    owned_club_ids = _resolve_owned_club_ids(service.session, current_user.id)
    if not owned_club_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Club ownership is required to hand off a discovery into the transfer market.",
        )
    club_id = owned_club_ids[0]

    # Verify target player exists
    player = service.session.get(Player, clean_player_id)
    regen = service.session.scalar(
        select(RegenProfile).where(
            or_(
                RegenProfile.id == clean_player_id,
                RegenProfile.regen_id == clean_player_id,
                RegenProfile.player_id == clean_player_id,
            )
        )
    )
    if player is None and regen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player '{clean_player_id}' was not found.",
        )
    resolved_player_id = player.id if player else regen.player_id

    # Verify discovery provenance: club must have a scout report for this player
    has_regen_report = False
    if regen is not None:
        has_regen_report = (
            service.session.scalar(
                select(RegenScoutReport.id).where(
                    RegenScoutReport.regen_id == regen.id,
                    RegenScoutReport.club_id.in_(owned_club_ids),
                )
            )
            is not None
        )
    has_intel_report = (
        service.session.scalar(
            select(ScoutReport.id).where(
                ScoutReport.player_id == resolved_player_id,
                ScoutReport.club_id.in_(owned_club_ids),
            )
        )
        is not None
    )

    if not has_regen_report and not has_intel_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A persisted scout report by the authenticated club is required before transfer room handoff.",
        )

    # Reuse canonical TransferMarketService
    tm_service = TransferMarketService(service.session)
    tm_service.add_watchlist_entry(
        WatchlistEntryCreateRequest(
            player_id=resolved_player_id,
            club_id=club_id,
            source="scouting_discovery",
            discovery_score=85.0,
        ),
        actor=current_user,
        club_id=club_id,
    )

    # Check for active transfer listing
    open_listing = service.session.scalar(
        select(TransferListing).where(
            TransferListing.player_id == resolved_player_id,
            TransferListing.status == "open",
        )
    )

    service.session.commit()

    return {
        "status": "handed_off",
        "player_id": resolved_player_id,
        "club_id": club_id,
        "in_transfer_room": True,
        "has_active_listing": open_listing is not None,
        "listing_id": open_listing.id if open_listing else None,
        "asking_price": float(open_listing.base_price) if open_listing else None,
        "market_status": "open_opportunity" if open_listing else "watchlist_active",
        "message": "Player discovery successfully handed off to transfer market watchlist.",
    }


__all__ = ["router"]
