from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.owner_console import engine, ledger
from app.owner_console.institutional_models import (
    OwnerClubAcademyGraduate,
    OwnerClubHistoryEntry,
    OwnerClubManagerialTenure,
    OwnerClubRivalry,
    OwnerClubSeasonArchive,
    OwnerClubTransferRecord,
    OwnerMediaOutlet,
    OwnerMediaStory,
    OwnerSupporterEvent,
    OwnerSupporterProfile,
    OwnerSupporterSegment,
)
from app.owner_console.models import (
    OwnerBroadcastEvent,
    OwnerClubState,
    OwnerCompetition,
    OwnerCompetitionEntry,
    OwnerInboxItem,
    OwnerMatch,
    OwnerNewsroomArticle,
    OwnerScoutingWatchlist,
    OwnerSquadPlayer,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: float | int, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, round(value))))


def _division_level_int(raw: Any) -> int:
    if raw is None:
        return 4
    if isinstance(raw, int):
        return max(1, min(4, raw))
    s = str(raw).strip().lower()
    if s in ("1", "division_1", "div_1", "premier", "first"):
        return 1
    if s in ("2", "division_2", "div_2", "second"):
        return 2
    if s in ("3", "division_3", "div_3", "third"):
        return 3
    if s in ("4", "division_4", "div_4", "foundation", "fourth"):
        return 4
    for ch in s:
        if ch.isdigit():
            return max(1, min(4, int(ch)))
    return 4


def _division_level_str(level_int: int) -> str:
    lvl = max(1, min(4, int(level_int)))
    return "foundation" if lvl >= 4 else f"division_{lvl}"


def _season_number_for_state(state: OwnerClubState | None) -> int:
    if state is None:
        return 1
    world_day = int(getattr(state, "world_day", 1) or 1)
    return max(1, ((world_day - 1) // 30) + 1)


def _status_label_for_sentiment(sentiment: int, scar_tissue: int = 0, protest_stage: str = "none") -> str:
    if protest_stage in ("banner_protest", "organised_boycott") and sentiment < 42:
        return "protesting"
    if sentiment >= 82:
        return "ecstatic"
    if sentiment >= 68:
        return "optimistic"
    if sentiment >= 52:
        return "content" if scar_tissue < 35 else "cautious"
    if sentiment >= 38:
        return "restless"
    if sentiment >= 24:
        return "frustrated"
    return "disengaged"


# ---------------------------------------------------------------------------
# Default Supporter Segment Definitions & Media Outlets Catalog
# ---------------------------------------------------------------------------

DEFAULT_SUPPORTER_SEGMENTS: tuple[dict[str, Any], ...] = (
    {
        "segment_key": "loyal_lifelong",
        "segment_name": "Loyal Lifelong Supporters",
        "population_share_pct": 22,
        "loyalty": 88,
        "sentiment": 68,
        "enthusiasm": 70,
        "priorities": {
            "club_identity": 0.95,
            "rivalry_record": 0.90,
            "results": 0.80,
            "youth_academy": 0.85,
            "owner_conduct": 0.85,
            "ticket_pricing": 0.65,
            "star_signings": 0.45,
        },
        "expectations": {
            "core_demand": "Preserve club heritage, honour rivalries, and field players who fight for the crest.",
            "tolerance_for_rebuild": "high_if_honest",
        },
    },
    {
        "segment_key": "regular_matchgoing",
        "segment_name": "Regular Match-Going Supporters",
        "population_share_pct": 24,
        "loyalty": 76,
        "sentiment": 65,
        "enthusiasm": 68,
        "priorities": {
            "ticket_pricing": 0.95,
            "matchday_experience": 0.90,
            "results": 0.85,
            "rivalry_record": 0.80,
            "owner_conduct": 0.70,
            "youth_academy": 0.60,
            "star_signings": 0.55,
        },
        "expectations": {
            "core_demand": "Fair ticket pricing, strong home form, and an electric stadium matchday experience.",
            "tolerance_for_rebuild": "medium",
        },
    },
    {
        "segment_key": "younger_supporters",
        "segment_name": "Younger Generation Supporters",
        "population_share_pct": 16,
        "loyalty": 64,
        "sentiment": 67,
        "enthusiasm": 74,
        "priorities": {
            "star_signings": 0.90,
            "youth_academy": 0.85,
            "results": 0.80,
            "ticket_pricing": 0.75,
            "matchday_experience": 0.75,
            "rivalry_record": 0.65,
            "owner_conduct": 0.55,
        },
        "expectations": {
            "core_demand": "Exciting attacking football, breakout wonderkids, and ambitious marquee signings.",
            "tolerance_for_rebuild": "high_for_youth",
        },
    },
    {
        "segment_key": "local_community",
        "segment_name": "Local Community Supporters",
        "population_share_pct": 15,
        "loyalty": 80,
        "sentiment": 66,
        "enthusiasm": 64,
        "priorities": {
            "youth_academy": 0.95,
            "owner_conduct": 0.90,
            "ticket_pricing": 0.88,
            "club_identity": 0.85,
            "results": 0.65,
            "rivalry_record": 0.75,
            "star_signings": 0.35,
        },
        "expectations": {
            "core_demand": "Accessible community engagement, local academy pathways, and responsible ownership.",
            "tolerance_for_rebuild": "high",
        },
    },
    {
        "segment_key": "international_followers",
        "segment_name": "International Followers",
        "population_share_pct": 13,
        "loyalty": 54,
        "sentiment": 66,
        "enthusiasm": 65,
        "priorities": {
            "star_signings": 0.95,
            "results": 0.90,
            "rivalry_record": 0.60,
            "owner_conduct": 0.45,
            "youth_academy": 0.45,
            "ticket_pricing": 0.05,
            "matchday_experience": 0.30,
        },
        "expectations": {
            "core_demand": "Trophies, high-profile players, and rising continental prestige.",
            "tolerance_for_rebuild": "low",
        },
    },
    {
        "segment_key": "organised_groups",
        "segment_name": "Organised Supporter Groups",
        "population_share_pct": 10,
        "loyalty": 90,
        "sentiment": 62,
        "enthusiasm": 78,
        "priorities": {
            "owner_conduct": 0.98,
            "ticket_pricing": 0.95,
            "club_identity": 0.95,
            "rivalry_record": 0.92,
            "results": 0.82,
            "youth_academy": 0.75,
            "star_signings": 0.40,
        },
        "expectations": {
            "core_demand": "Transparent governance, respect for supporters, fierce derby pride, and zero exploitation.",
            "tolerance_for_rebuild": "conditional_on_transparency",
        },
    },
)

DEFAULT_MEDIA_OUTLETS: tuple[dict[str, Any], ...] = (
    {
        "outlet_key": "local_club_chronicle",
        "outlet_name": "The Metropolitan Football Chronicle",
        "journalist_name": "Tunde Adebayo",
        "journalist_role": "Chief Club Beat Correspondent",
        "editorial_focus": "local_club_reporting",
        "credibility_tier": "tier_1_authoritative",
        "credibility_score": 91,
        "tone_style": "grounded_local",
    },
    {
        "outlet_key": "gtex_national_wire",
        "outlet_name": "GTEX National Football Wire",
        "journalist_name": "Clara Vance",
        "journalist_role": "National Football Editor",
        "editorial_focus": "national_football",
        "credibility_tier": "tier_1_authoritative",
        "credibility_score": 94,
        "tone_style": "authoritative_wire",
    },
    {
        "outlet_key": "transfer_insider_desk",
        "outlet_name": "The Transfer Ledger",
        "journalist_name": "Fabrizio Moretti",
        "journalist_role": "Recruitment & Market Specialist",
        "editorial_focus": "transfer_reporting",
        "credibility_tier": "tier_2_reliable",
        "credibility_score": 84,
        "tone_style": "market_tracker",
    },
    {
        "outlet_key": "boardroom_investigative",
        "outlet_name": "Boardroom & Balance Sheet Review",
        "journalist_name": "Ngozi Okafor",
        "journalist_role": "Investigative Governance & Finance Editor",
        "editorial_focus": "investigative_financial",
        "credibility_tier": "tier_1_authoritative",
        "credibility_score": 92,
        "tone_style": "investigative_scrutiny",
    },
    {
        "outlet_key": "tactical_youth_observer",
        "outlet_name": "NextGen & Competition Analyst",
        "journalist_name": "Marcus Sterling",
        "journalist_role": "Academy & Competition Columnist",
        "editorial_focus": "competition_analysis",
        "credibility_tier": "tier_2_reliable",
        "credibility_score": 87,
        "tone_style": "tactical_developmental",
    },
)


def ensure_media_outlets(session: Session) -> dict[str, OwnerMediaOutlet]:
    """Ensure the canonical set of media outlets and journalists exist."""
    existing = {
        row.outlet_key: row
        for row in session.scalars(select(OwnerMediaOutlet)).all()
    }
    for spec in DEFAULT_MEDIA_OUTLETS:
        if spec["outlet_key"] not in existing:
            outlet = OwnerMediaOutlet(
                outlet_key=spec["outlet_key"],
                outlet_name=spec["outlet_name"],
                journalist_name=spec["journalist_name"],
                journalist_role=spec["journalist_role"],
                editorial_focus=spec["editorial_focus"],
                credibility_tier=spec["credibility_tier"],
                credibility_score=spec["credibility_score"],
                tone_style=spec["tone_style"],
            )
            session.add(outlet)
            existing[spec["outlet_key"]] = outlet
    session.flush()
    return existing


# ---------------------------------------------------------------------------
# Initialization & Reconciliation of Institutional State
# ---------------------------------------------------------------------------


def ensure_club_institutional_ecosystem(
    session: Session,
    state: OwnerClubState,
) -> tuple[OwnerSupporterProfile, list[OwnerSupporterSegment]]:
    """Idempotently initialize or reconcile supporter profile, segments, media outlets, and founding history."""
    ensure_media_outlets(session)

    profile = session.scalar(
        select(OwnerSupporterProfile).where(OwnerSupporterProfile.club_id == state.club_id)
    )
    total_fans = max(200, int(state.fans or 1200))
    world_day = int(state.world_day or 1)

    if profile is None:
        div_int = _division_level_int(state.division_level)
        culture_label = "Community & Youth Traditionalists"
        if int(state.prestige or 10) >= 65:
            culture_label = "Continental Title Expectants"
        elif div_int <= 2:
            culture_label = "Passionate Top-Flight Contenders"

        profile = OwnerSupporterProfile(
            club_id=state.club_id,
            owner_user_id=state.owner_user_id,
            supporter_culture_label=culture_label,
            overall_sentiment=65,
            confidence_in_owner=66,
            confidence_in_manager=68,
            loyalty_index=74,
            matchday_enthusiasm=67,
            accumulated_frustration=0,
            consecutive_disappointments=0,
            consecutive_victories=0,
            ticket_price_tier=str((state.facilities_json or {}).get("_ticket_price_tier", "standard")),
            matchday_experience_rating=_clamp(55 + int((state.facilities_json or {}).get("stadium", 1)) * 6),
            active_protest_stage="none",
            active_campaign_headline=None,
            attendance_modifier_pct=0,
            owner_credibility_score=74,
            expectations_json={
                "season_target": "promotion_challenge" if div_int > 1 else "title_contender",
                "minimum_acceptable_finish": "top_half",
                "youth_pathway_expected": True,
                "affordable_tickets_expected": True,
                "rivalry_pride_expected": True,
            },
            atmosphere_profile_json={},
            last_reconciled_world_day=world_day,
        )
        session.add(profile)
        session.flush()

    segments = list(
        session.scalars(
            select(OwnerSupporterSegment)
            .where(OwnerSupporterSegment.club_id == state.club_id)
            .order_by(OwnerSupporterSegment.population_share_pct.desc())
        ).all()
    )
    by_key = {seg.segment_key: seg for seg in segments}

    for spec in DEFAULT_SUPPORTER_SEGMENTS:
        seg_key = spec["segment_key"]
        share = int(spec["population_share_pct"])
        member_count = max(15, int(round(total_fans * (share / 100.0))))
        if seg_key not in by_key:
            seg = OwnerSupporterSegment(
                club_id=state.club_id,
                segment_key=seg_key,
                segment_name=spec["segment_name"],
                population_share_pct=share,
                member_count=member_count,
                sentiment=int(spec["sentiment"]),
                loyalty=int(spec["loyalty"]),
                enthusiasm=int(spec["enthusiasm"]),
                owner_approval=int(profile.confidence_in_owner),
                scar_tissue=int(profile.accumulated_frustration),
                status_label=_status_label_for_sentiment(int(spec["sentiment"])),
                priorities_json=dict(spec["priorities"]),
                expectations_json=dict(spec["expectations"]),
                recent_memory_json=[],
            )
            session.add(seg)
            segments.append(seg)
            by_key[seg_key] = seg
        else:
            by_key[seg_key].member_count = member_count

    session.flush()

    # Ensure founding history entry exists (grounded in actual club creation state, never fabricating fake trophies)
    div_int = _division_level_int(state.division_level)
    record_history_entry(
        session,
        club_id=state.club_id,
        season_number=1,
        world_day=1,
        category="club_creation",
        event_type="institution_established",
        title=f"{state.club_name} Established under Current Ownership",
        narrative_summary=(
            f"{state.club_name} entered the GTEX football pyramid in Division {div_int} "
            f"with a supporter base of {total_fans:,} and institutional prestige {state.prestige}."
        ),
        entity_type="club",
        entity_id=state.club_id,
        entity_name=state.club_name,
        established_facts={
            "club_id": state.club_id,
            "club_name": state.club_name,
            "division_level": div_int,
            "initial_fans": total_fans,
            "initial_prestige": int(state.prestige or 10),
        },
        is_major_milestone=True,
        idempotency_key=f"history:club_creation:{state.club_id}",
    )

    # Ensure current active manager has an active tenure record
    manager = dict(state.manager_json or {})
    if manager and manager.get("name"):
        ensure_active_manager_tenure(session, state, manager)

    # Recompute atmosphere profile if empty
    if not profile.atmosphere_profile_json:
        profile.atmosphere_profile_json = compute_matchday_atmosphere(
            session,
            state,
            profile=profile,
            segments=segments,
        )
        flag_modified(profile, "atmosphere_profile_json")

    session.flush()
    return profile, segments


# ---------------------------------------------------------------------------
# Permanent Institutional History Ledger Helpers
# ---------------------------------------------------------------------------


def record_history_entry(
    session: Session,
    *,
    club_id: str,
    season_number: int,
    world_day: int,
    category: str,
    event_type: str,
    title: str,
    narrative_summary: str,
    idempotency_key: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    entity_name: str | None = None,
    established_facts: dict[str, Any] | None = None,
    is_major_milestone: bool = False,
) -> OwnerClubHistoryEntry:
    """Idempotently append an entry to the permanent club history ledger."""
    existing = session.scalar(
        select(OwnerClubHistoryEntry).where(OwnerClubHistoryEntry.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing

    entry = OwnerClubHistoryEntry(
        club_id=club_id,
        season_number=max(1, int(season_number or 1)),
        world_day=max(1, int(world_day or 1)),
        category=category,
        event_type=event_type,
        title=title[:240],
        narrative_summary=narrative_summary,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        entity_name=entity_name[:160] if entity_name else None,
        established_facts_json=dict(established_facts or {}),
        is_major_milestone=bool(is_major_milestone),
        idempotency_key=idempotency_key[:160],
    )
    session.add(entry)
    session.flush()
    return entry


def ensure_active_manager_tenure(
    session: Session,
    state: OwnerClubState,
    manager: dict[str, Any],
) -> OwnerClubManagerialTenure:
    """Ensure the current manager has an active tenure row, closing any stale active row."""
    mgr_id = str(manager.get("id") or manager.get("name") or "default_manager")
    mgr_name = str(manager.get("name") or "First-Team Manager")
    style = str(manager.get("style") or manager.get("mentality") or "balanced")
    world_day = int(state.world_day or 1)

    active_rows = list(
        session.scalars(
            select(OwnerClubManagerialTenure).where(
                OwnerClubManagerialTenure.club_id == state.club_id,
                OwnerClubManagerialTenure.status == "active",
            )
        ).all()
    )
    for row in active_rows:
        if row.manager_id == mgr_id or row.manager_name == mgr_name:
            return row
        row.status = "departed"
        row.departed_world_day = world_day
        if not row.departure_reason:
            row.departure_reason = "succeeded_by_new_appointment"
        row.tenure_summary = (
            f"Managed {row.matches_managed} matches ({row.wins}W-{row.draws}D-{row.losses}L) "
            f"before departing on World Day {world_day}."
        )

    tenure = OwnerClubManagerialTenure(
        club_id=state.club_id,
        manager_id=mgr_id,
        manager_name=mgr_name,
        role="first_team_manager",
        tactical_style=style,
        appointed_world_day=world_day,
        status="active",
        matches_managed=0,
        wins=0,
        draws=0,
        losses=0,
        goals_for=0,
        goals_against=0,
        trophies_won=0,
        honors_json=[],
        tenure_summary=f"Appointed First-Team Manager of {state.club_name} on World Day {world_day} ({style} style).",
    )
    session.add(tenure)
    session.flush()
    return tenure


# ---------------------------------------------------------------------------
# Supporter Sentiment Engine & Differentiated Segment Reactions
# ---------------------------------------------------------------------------


def _recompute_profile_aggregates(
    profile: OwnerSupporterProfile,
    segments: list[OwnerSupporterSegment],
) -> None:
    """Update club-wide supporter sentiment and protest stage from weighted segment values."""
    if not segments:
        return
    total_share = sum(max(1, int(s.population_share_pct)) for s in segments)
    weighted_sentiment = sum(int(s.sentiment) * max(1, int(s.population_share_pct)) for s in segments) / total_share
    weighted_loyalty = sum(int(s.loyalty) * max(1, int(s.population_share_pct)) for s in segments) / total_share
    weighted_enthusiasm = sum(int(s.enthusiasm) * max(1, int(s.population_share_pct)) for s in segments) / total_share
    weighted_owner = sum(int(s.owner_approval) * max(1, int(s.population_share_pct)) for s in segments) / total_share

    profile.overall_sentiment = _clamp(weighted_sentiment)
    profile.loyalty_index = _clamp(weighted_loyalty)
    profile.matchday_enthusiasm = _clamp(weighted_enthusiasm)
    profile.confidence_in_owner = _clamp(weighted_owner)

    by_key = {s.segment_key: s for s in segments}
    organised = by_key.get("organised_groups")
    matchgoing = by_key.get("regular_matchgoing")
    org_sent = int(organised.sentiment) if organised else profile.overall_sentiment
    mg_sent = int(matchgoing.sentiment) if matchgoing else profile.overall_sentiment

    # Grounded protest escalation / de-escalation rules
    if (
        org_sent <= 22
        or profile.overall_sentiment <= 24
        or (profile.consecutive_disappointments >= 5 and profile.overall_sentiment <= 35)
    ):
        profile.active_protest_stage = "organised_boycott"
        profile.active_campaign_headline = (
            "Supporter Coalition Calls for Matchday Walkout & Boardroom Accountability"
        )
    elif (
        org_sent <= 32
        or profile.overall_sentiment <= 34
        or (profile.ticket_price_tier == "exploitative" and mg_sent <= 40)
        or profile.consecutive_disappointments >= 4
    ):
        profile.active_protest_stage = "banner_protest"
        profile.active_campaign_headline = (
            "Organised Supporter Groups Unfurl Protest Banners Demanding Institutional Direction"
        )
    elif (
        org_sent <= 42
        or profile.overall_sentiment <= 43
        or (profile.ticket_price_tier in ("premium", "exploitative") and mg_sent <= 48)
        or profile.consecutive_disappointments >= 3
    ):
        profile.active_protest_stage = "petition"
        profile.active_campaign_headline = (
            "Supporters' Trust Circulates Formal Petition Over Club Direction & Standards"
        )
    elif profile.overall_sentiment <= 50 or profile.accumulated_frustration >= 35:
        profile.active_protest_stage = "grumbling"
        profile.active_campaign_headline = "Growing Terrace Murmurs Over Recent Club Decisions"
    else:
        profile.active_protest_stage = "none"
        profile.active_campaign_headline = None

    for seg in segments:
        seg.status_label = _status_label_for_sentiment(
            int(seg.sentiment),
            int(seg.scar_tissue),
            profile.active_protest_stage,
        )

    # Attendance modifier (-35% to +25%) driven by match-going enthusiasm, sentiment, and ticket pricing
    ticket_mod = {
        "affordable": 8,
        "standard": 0,
        "premium": -7,
        "exploitative": -18,
    }.get(profile.ticket_price_tier, 0)
    protest_mod = {
        "none": 0,
        "grumbling": -3,
        "petition": -6,
        "banner_protest": -12,
        "organised_boycott": -24,
    }.get(profile.active_protest_stage, 0)
    sentiment_mod = int(round((profile.overall_sentiment - 60) * 0.35))
    profile.attendance_modifier_pct = _clamp(ticket_mod + protest_mod + sentiment_mod, -40, 30)


def apply_supporter_reaction(
    session: Session,
    state: OwnerClubState,
    *,
    event_type: str,
    trigger_source_type: str,
    trigger_source_id: str,
    headline: str,
    summary: str,
    driver_Impacts: dict[str, float],
    idempotency_key: str,
    is_disappointment: bool = False,
    is_victory_relief: bool = False,
    credibility_delta: int = 0,
    contradiction_detected: bool = False,
    contradiction_reason: str | None = None,
) -> OwnerSupporterEvent:
    """Apply a differentiated reaction across all 6 supporter segments with scar-tissue memory."""
    existing = session.scalar(
        select(OwnerSupporterEvent).where(OwnerSupporterEvent.idempotency_key == idempotency_key)
    )
    if existing is not None:
        return existing

    profile, segments = ensure_club_institutional_ecosystem(session, state)
    old_sentiment = int(profile.overall_sentiment)

    if is_disappointment:
        profile.consecutive_disappointments = int(profile.consecutive_disappointments or 0) + 1
        profile.consecutive_victories = 0
        scar_gain = 8 + min(14, profile.consecutive_disappointments * 3)
        profile.accumulated_frustration = _clamp(int(profile.accumulated_frustration or 0) + scar_gain, 0, 100)
    elif is_victory_relief:
        profile.consecutive_victories = int(profile.consecutive_victories or 0) + 1
        profile.consecutive_disappointments = 0
        # Repeated disappointment memory decays gradually; one win cannot erase accumulated scar tissue
        decay = 8 if int(profile.accumulated_frustration or 0) >= 25 else 12
        profile.accumulated_frustration = _clamp(int(profile.accumulated_frustration or 0) - decay, 0, 100)

    if credibility_delta != 0:
        profile.owner_credibility_score = _clamp(int(profile.owner_credibility_score or 70) + credibility_delta, 0, 100)

    segment_deltas: dict[str, dict[str, Any]] = {}
    for seg in segments:
        priorities = dict(seg.priorities_json or {})
        raw_delta = 0.0
        for driver_key, base_impact in driver_Impacts.items():
            weight = float(priorities.get(driver_key, 0.5))
            raw_delta += float(base_impact) * weight

        # Apply scar-tissue dampening when recovering from repeated disappointments
        if raw_delta > 0 and int(seg.scar_tissue or 0) >= 18:
            dampener = max(0.32, 1.0 - (int(seg.scar_tissue) / 125.0))
            raw_delta = raw_delta * dampener
            # Prevent immediate jump to maximum confidence (>82) while scar tissue remains high
            max_cap = 76 if int(seg.scar_tissue) >= 35 else 86
        else:
            max_cap = 100

        int_delta = int(round(raw_delta))
        if raw_delta > 0 and int_delta == 0:
            int_delta = 1
        elif raw_delta < 0 and int_delta == 0:
            int_delta = -1

        old_seg_sentiment = int(seg.sentiment)
        new_seg_sentiment = _clamp(old_seg_sentiment + int_delta, 5, max_cap)
        actual_delta = new_seg_sentiment - old_seg_sentiment
        seg.sentiment = new_seg_sentiment
        seg.enthusiasm = _clamp(int(seg.enthusiasm) + int(round(int_delta * 0.85)), 5, 100)

        if "owner_conduct" in driver_Impacts or "ticket_pricing" in driver_Impacts or contradiction_detected:
            seg.owner_approval = _clamp(int(seg.owner_approval) + int_delta + (credibility_delta // 2), 5, 100)
        else:
            seg.owner_approval = _clamp(int(seg.owner_approval) + int(round(int_delta * 0.45)), 5, 100)

        if is_disappointment or actual_delta < -3:
            seg.scar_tissue = _clamp(int(seg.scar_tissue or 0) + abs(min(0, actual_delta)) + 4, 0, 100)
        elif is_victory_relief and actual_delta > 0:
            seg.scar_tissue = _clamp(int(seg.scar_tissue or 0) - 6, 0, 100)

        memory = list(seg.recent_memory_json or [])
        memory.insert(
            0,
            {
                "world_day": int(state.world_day or 1),
                "event_type": event_type,
                "headline": headline[:140],
                "delta": actual_delta,
                "sentiment_after": seg.sentiment,
            },
        )
        seg.recent_memory_json = memory[:10]
        flag_modified(seg, "recent_memory_json")

        segment_deltas[seg.segment_key] = {
            "segment_name": seg.segment_name,
            "delta": actual_delta,
            "sentiment_before": old_seg_sentiment,
            "sentiment_after": seg.sentiment,
            "scar_tissue": seg.scar_tissue,
            "status_label": seg.status_label,
        }

    _recompute_profile_aggregates(profile, segments)
    overall_delta = int(profile.overall_sentiment) - old_sentiment

    profile.atmosphere_profile_json = compute_matchday_atmosphere(
        session,
        state,
        profile=profile,
        segments=segments,
    )
    flag_modified(profile, "atmosphere_profile_json")

    sup_event = OwnerSupporterEvent(
        club_id=state.club_id,
        world_day=int(state.world_day or 1),
        event_type=event_type,
        trigger_source_type=trigger_source_type,
        trigger_source_id=str(trigger_source_id),
        headline=headline[:240],
        summary=summary,
        overall_sentiment_delta=overall_delta,
        credibility_delta=credibility_delta,
        attendance_impact_pct=int(profile.attendance_modifier_pct),
        segment_deltas_json=segment_deltas,
        contradiction_detected=contradiction_detected,
        contradiction_reason=contradiction_reason,
        idempotency_key=idempotency_key[:160],
    )
    session.add(sup_event)
    session.flush()
    return sup_event


def compute_matchday_atmosphere(
    session: Session,
    state: OwnerClubState,
    *,
    profile: OwnerSupporterProfile | None = None,
    segments: list[OwnerSupporterSegment] | None = None,
    opponent_club_id: str | None = None,
    opponent_name: str | None = None,
    is_knockout_or_decider: bool = False,
) -> dict[str, Any]:
    """Compute presentation-layer matchday atmosphere from real supporter, rivalry, and match data."""
    if profile is None or segments is None:
        profile, segments = ensure_club_institutional_ecosystem(session, state)

    rivalry = None
    if opponent_club_id:
        rivalry = session.scalar(
            select(OwnerClubRivalry).where(
                OwnerClubRivalry.club_id == state.club_id,
                OwnerClubRivalry.rival_club_id == str(opponent_club_id),
            )
        )
    rivalry_intensity = int(rivalry.intensity_score) if rivalry else 15
    rivalry_tier = str(rivalry.rivalry_tier) if rivalry else "standard"

    by_key = {s.segment_key: s for s in segments}
    organised = by_key.get("organised_groups")
    matchgoing = by_key.get("regular_matchgoing")
    lifelong = by_key.get("loyal_lifelong")

    enthusiasm = int(profile.matchday_enthusiasm or 65)
    sentiment = int(profile.overall_sentiment or 65)
    protest_stage = str(profile.active_protest_stage or "none")

    stakes_bonus = 14 if is_knockout_or_decider else 0
    rivalry_bonus = int(round(rivalry_intensity * 0.22)) if rivalry_intensity >= 35 else 0
    crowd_intensity = _clamp(int(round(enthusiasm * 0.6 + sentiment * 0.25)) + stakes_bonus + rivalry_bonus, 15, 100)

    banners: list[str] = []
    chants: list[str] = []
    visible_reactions: list[str] = []

    if protest_stage in ("banner_protest", "organised_boycott"):
        dominant_mood = "hostile_protest"
        stadium_ambience = "Tense & Mutinous — Whistles and Protest Banners in the Ultras Stand"
        banners.append(f"RESPECT THE SUPPORTERS — {state.club_name.upper()} BELONGS TO THE COMMUNITY")
        if profile.ticket_price_tier in ("premium", "exploitative"):
            banners.append("FOOTBALL WITHOUT FANS IS NOTHING — STOP PRICING OUT LOCALS")
        if profile.consecutive_disappointments >= 3:
            banners.append("DEMANDING STANDARDS & ACCOUNTABILITY FROM THE BOARDROOM")
        chants.append("We want our club back — accountability now!")
        visible_reactions.append("Organised supporter groups hold up protest banners in the 18th minute.")
    elif rivalry_intensity >= 55:
        dominant_mood = "ferocious_derby_cauldron"
        stadium_ambience = f"Electric Derby Cauldron vs {opponent_name or (rivalry.rival_club_name if rivalry else 'Rivals')}"
        banners.append(f"PRIDE OF {state.club_name.upper()} — NEVER YIELD THIS DERBY")
        chants.append(f"Stand up for {state.club_name} — Derby Day Roar!")
        visible_reactions.append("Full-stand tifo display and flares welcome the players onto the pitch.")
    elif sentiment >= 75:
        dominant_mood = "electric_belief"
        stadium_ambience = "Roaring Fortress — Scarves Held High Across Every Tier"
        banners.append(f"IN {state.club_name.upper()} WE TRUST — MARCHING TOWARD GLORY")
        chants.append("Ole, Ole — The Fortress Is Ours!")
        visible_reactions.append("Continuous rhythmic drumming and standing ovations from the lifelong stand.")
    elif sentiment <= 42:
        dominant_mood = "anxious_scrutiny"
        stadium_ambience = "Restless & Expectant — Every Misplaced Pass Draws Groans"
        banners.append("EARN THE SHIRT — SHOW FIGHT ON THE PITCH")
        chants.append("Play for the badge on the front!")
        visible_reactions.append("Supporters voice frustration quickly when possession is lost.")
    else:
        dominant_mood = "committed_support"
        stadium_ambience = "Vibrant Home Support — Steady Chants from the Match-Going Core"
        banners.append(f"FOREVER {state.club_name.upper()} · TRADITION & AMBITION")
        chants.append(f"Come on {state.club_name}!")
        visible_reactions.append("Vocal backing from the home end throughout the 90 minutes.")

    return {
        "club_id": state.club_id,
        "dominant_mood": dominant_mood,
        "crowd_intensity": crowd_intensity,
        "chant_volume_db": _clamp(72 + int(round(crowd_intensity * 0.35)), 70, 112),
        "stadium_ambience": stadium_ambience,
        "attendance_modifier_pct": int(profile.attendance_modifier_pct or 0),
        "ticket_price_tier": profile.ticket_price_tier,
        "protest_stage": protest_stage,
        "rivalry_tier": rivalry_tier,
        "rivalry_intensity": rivalry_intensity,
        "banners": banners,
        "chants": chants,
        "visible_reactions": visible_reactions,
        "organised_group_enthusiasm": int(organised.enthusiasm) if organised else enthusiasm,
        "matchgoing_sentiment": int(matchgoing.sentiment) if matchgoing else sentiment,
        "lifelong_loyalty": int(lifelong.loyalty) if lifelong else int(profile.loyalty_index),
    }


# ---------------------------------------------------------------------------
# Media Story Generation & Fact-Grounding Engine
# ---------------------------------------------------------------------------


def publish_media_story(
    session: Session,
    state: OwnerClubState,
    *,
    outlet_key: str,
    story_type: str,
    classification: str,
    headline: str,
    subheadline: str = "",
    body: str = "",
    source_type: str = "club_event",
    source_id: str = "",
    established_facts: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    reputation_delta: int = 0,
    supporter_sentiment_delta: int = 0,
    commercial_attractiveness_delta: int = 0,
    sponsorship_interest_delta: int = 0,
    leadership_pressure_delta: int = 0,
    also_mirror_to_newsroom: bool = True,
    enforce_grounding: bool = False,
) -> OwnerMediaStory:
    """Publish a persistent, grounded media story with verified/rumour/opinion classification and consequences."""
    idem = idempotency_key or f"media:{state.club_id}:{story_type}:{uuid4().hex[:10]}"
    existing = session.scalar(
        select(OwnerMediaStory).where(OwnerMediaStory.idempotency_key == idem)
    )
    if existing is not None:
        return existing

    outlets = ensure_media_outlets(session)
    outlet = outlets.get(outlet_key) or next(iter(outlets.values()))

    # Enforce strict classification rule: rumours and opinions are NEVER marked as confirmed fact
    valid_classifications = {"verified_event", "reported_information", "rumour", "opinion"}
    clean_classification = classification if classification in valid_classifications else "reported_information"
    is_confirmed_fact = clean_classification in {"verified_event", "reported_information"}

    facts = dict(established_facts or {})
    facts.setdefault("club_id", state.club_id)
    facts.setdefault("club_name", state.club_name)
    facts.setdefault("world_day", int(state.world_day or 1))
    facts["classification"] = clean_classification
    facts["is_confirmed_fact"] = is_confirmed_fact

    from app.owner_console import storytelling

    grounding_report = storytelling.validate_article_grounding(facts, f"{headline} {subheadline} {body}")
    if enforce_grounding and not grounding_report.get("valid", True):
        raise ValueError(f"unverified_media_grounding: {grounding_report}")

    story = OwnerMediaStory(
        club_id=state.club_id,
        world_day=int(state.world_day or 1),
        outlet_key=outlet.outlet_key,
        outlet_name=outlet.outlet_name,
        journalist_name=outlet.journalist_name,
        editorial_focus=outlet.editorial_focus,
        credibility_score=int(outlet.credibility_score),
        story_type=story_type,
        classification=clean_classification,
        is_confirmed_fact=is_confirmed_fact,
        headline=headline[:240],
        subheadline=subheadline[:320],
        body=body,
        source_type=source_type,
        source_id=str(source_id),
        established_facts_json=facts,
        grounding_report_json=grounding_report,
        reputation_delta=int(reputation_delta),
        supporter_sentiment_delta=int(supporter_sentiment_delta),
        commercial_attractiveness_delta=int(commercial_attractiveness_delta),
        sponsorship_interest_delta=int(sponsorship_interest_delta),
        leadership_pressure_delta=int(leadership_pressure_delta),
        idempotency_key=idem[:160],
    )
    session.add(story)
    session.flush()

    # Apply proportionate reputation delta to canonical ClubReputationService & OwnerClubState.prestige
    if reputation_delta != 0:
        state.prestige = _clamp(int(state.prestige or 10) + reputation_delta, 0, 100)
        try:
            from app.services.club_reputation_service import ClubReputationService

            ClubReputationService(session).apply_delta(
                club_id=state.club_id,
                delta=int(reputation_delta) * 2,
                event_type=f"media_{story_type}",
                source=outlet.outlet_name,
                summary=headline[:200],
                season=_season_number_for_state(state),
                metadata={"story_id": story.id, "classification": clean_classification},
                milestone=abs(reputation_delta) >= 4 and is_confirmed_fact,
            )
        except Exception as exc:
            logger.debug("ClubReputationService delta skipped: %s", exc)

    # Mirror verified/reported club stories to OwnerNewsroomArticle so existing newsroom feeds stay unified
    if also_mirror_to_newsroom and clean_classification != "rumour":
        existing_art = session.scalar(
            select(OwnerNewsroomArticle).where(OwnerNewsroomArticle.source_event_id == story.id)
        )
        if existing_art is None:
            session.add(
                OwnerNewsroomArticle(
                    save_context_id=f"save:{state.club_id}",
                    club_id=state.club_id,
                    source_event_id=story.id,
                    category=story_type,
                    headline=headline[:200],
                    subheadline=f"{outlet.outlet_name} · {outlet.journalist_name} ({clean_classification.replace('_', ' ').title()})"[:240],
                    editorial_narration=body,
                    established_facts_json=facts,
                    grounding_report_json=grounding_report,
                    hero_image_url="",
                    status="published",
                )
            )
            session.flush()

    return story


# ---------------------------------------------------------------------------
# Event Hooks: Match Completion, Rivalry Progression, Academy Debuts, Seasons
# ---------------------------------------------------------------------------


def record_match_institutional_impact(
    session: Session,
    match: OwnerMatch,
    comp: OwnerCompetition,
    side: dict[str, Any],
    opp_side: dict[str, Any],
    is_home: bool,
    gf: int,
    ga: int,
) -> dict[str, Any]:
    """Process supporter reaction, atmosphere, rivalry progression, managerial W/D/L, academy debuts, and media after a match."""
    state: OwnerClubState | None = side.get("state")
    if state is None:
        return {}

    idem_prefix = f"match:{match.id}:club:{state.club_id}"
    existing_hist = session.scalar(
        select(OwnerClubHistoryEntry).where(
            OwnerClubHistoryEntry.idempotency_key == f"{idem_prefix}:result"
        )
    )
    if existing_hist is not None:
        return {"already_recorded": True}

    profile, segments = ensure_club_institutional_ecosystem(session, state)
    world_day = int(state.world_day or 1)
    season_num = _season_number_for_state(state)
    opp_id = str(match.away_club_id if is_home else match.home_club_id)
    opp_name = str(match.away_name if is_home else match.home_name)
    margin = gf - ga
    result_str = "win" if gf > ga else "draw" if gf == ga else "loss"

    # 1. Update Historic Rivalry
    rivalry = session.scalar(
        select(OwnerClubRivalry).where(
            OwnerClubRivalry.club_id == state.club_id,
            OwnerClubRivalry.rival_club_id == opp_id,
        )
    )
    if rivalry is None:
        rivalry = OwnerClubRivalry(
            club_id=state.club_id,
            rival_club_id=opp_id,
            rival_club_name=opp_name,
            rivalry_name=f"{state.club_name} vs {opp_name}",
            origin_reason="knockout_clash" if comp.format == "knockout" else "repeated_encounters",
            intensity_score=24 if comp.format == "knockout" else 18,
            rivalry_tier="emerging",
            matches_played=0,
            wins=0,
            draws=0,
            losses=0,
            goals_for=0,
            goals_against=0,
            last_meeting_world_day=world_day,
            notable_encounters_json=[],
        )
        session.add(rivalry)
        session.flush()

    rivalry.matches_played = int(rivalry.matches_played or 0) + 1
    rivalry.goals_for = int(rivalry.goals_for or 0) + gf
    rivalry.goals_against = int(rivalry.goals_against or 0) + ga
    if gf > ga:
        rivalry.wins = int(rivalry.wins or 0) + 1
    elif gf == ga:
        rivalry.draws = int(rivalry.draws or 0) + 1
    else:
        rivalry.losses = int(rivalry.losses or 0) + 1

    intensity_gain = 8
    if comp.format == "knockout":
        intensity_gain += 12
    if abs(margin) >= 3 or (gf + ga) >= 5:
        intensity_gain += 7
    if abs(margin) <= 1 and rivalry.matches_played >= 2:
        intensity_gain += 6
    rivalry.intensity_score = _clamp(int(rivalry.intensity_score or 18) + intensity_gain, 15, 100)
    rivalry.last_meeting_world_day = world_day

    if rivalry.intensity_score >= 80 or rivalry.matches_played >= 6:
        rivalry.rivalry_tier = "historic_derby"
    elif rivalry.intensity_score >= 58 or rivalry.matches_played >= 4:
        rivalry.rivalry_tier = "fierce"
    elif rivalry.intensity_score >= 38 or rivalry.matches_played >= 2:
        rivalry.rivalry_tier = "competitive"
    else:
        rivalry.rivalry_tier = "emerging"

    encounters = list(rivalry.notable_encounters_json or [])
    encounters.insert(
        0,
        {
            "match_id": match.id,
            "world_day": world_day,
            "competition_name": comp.name,
            "round": match.round_number,
            "score": f"{gf}-{ga}",
            "result": result_str,
        },
    )
    rivalry.notable_encounters_json = encounters[:10]
    flag_modified(rivalry, "notable_encounters_json")

    if rivalry.matches_played == 3 or rivalry.rivalry_tier in ("fierce", "historic_derby"):
        record_history_entry(
            session,
            club_id=state.club_id,
            season_number=season_num,
            world_day=world_day,
            category="historic_rivalry",
            event_type="rivalry_intensified",
            title=f"Rivalry Intensifies: {state.club_name} vs {opp_name} ({rivalry.rivalry_tier.replace('_', ' ').title()})",
            narrative_summary=(
                f"After {rivalry.matches_played} competitive meetings ({rivalry.wins}W-{rivalry.draws}D-{rivalry.losses}L), "
                f"fixtures against {opp_name} have escalated into a {rivalry.rivalry_tier.replace('_', ' ')} rivalry "
                f"(intensity {rivalry.intensity_score}/100)."
            ),
            entity_type="rival_club",
            entity_id=opp_id,
            entity_name=opp_name,
            established_facts={
                "rival_club_name": opp_name,
                "matches_played": rivalry.matches_played,
                "wins": rivalry.wins,
                "draws": rivalry.draws,
                "losses": rivalry.losses,
                "intensity_score": rivalry.intensity_score,
            },
            is_major_milestone=rivalry.rivalry_tier == "historic_derby",
            idempotency_key=f"history:rivalry:{state.club_id}:{opp_id}:m{rivalry.matches_played}",
        )

    # 2. Update Active Manager Tenure W/D/L
    manager = dict(state.manager_json or {})
    tenure = ensure_active_manager_tenure(session, state, manager)
    tenure.matches_managed = int(tenure.matches_managed or 0) + 1
    tenure.goals_for = int(tenure.goals_for or 0) + gf
    tenure.goals_against = int(tenure.goals_against or 0) + ga
    if gf > ga:
        tenure.wins = int(tenure.wins or 0) + 1
    elif gf == ga:
        tenure.draws = int(tenure.draws or 0) + 1
    else:
        tenure.losses = int(tenure.losses or 0) + 1
    win_pct = int(round((tenure.wins / max(1, tenure.matches_managed)) * 100))
    tenure.tenure_summary = (
        f"{tenure.manager_name} ({tenure.tactical_style}): {tenure.matches_managed} matches managed "
        f"({tenure.wins}W-{tenure.draws}D-{tenure.losses}L, {win_pct}% win rate, {tenure.trophies_won} trophies)."
    )

    # 3. Detect Academy Graduate First-Team Debuts & Appearances/Goals
    xi_ids = set(side.get("xi") or [])
    debutants: list[OwnerClubAcademyGraduate] = []
    match_events = list(match.events_json or [])
    team_tag = "home" if is_home else "away"
    goal_texts = [
        str(ev.get("text") or "")
        for ev in match_events
        if ev.get("type") == "goal" and ev.get("team") == team_tag
    ]

    for sq_player in session.scalars(
        select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)
    ).all():
        if sq_player.id not in xi_ids:
            continue
        pers = dict(sq_player.personality_json or {})
        appearances = int(pers.get("club_appearances", 0)) + 1
        scored_in_match = sum(1 for txt in goal_texts if sq_player.name in txt)
        goals_total = int(pers.get("club_goals", 0)) + scored_in_match
        pers["club_appearances"] = appearances
        pers["club_goals"] = goals_total
        sq_player.personality_json = pers
        flag_modified(sq_player, "personality_json")

        if sq_player.is_regen or pers.get("academy_graduate"):
            grad = session.scalar(
                select(OwnerClubAcademyGraduate).where(
                    OwnerClubAcademyGraduate.club_id == state.club_id,
                    OwnerClubAcademyGraduate.player_id == str(sq_player.id),
                )
            )
            if grad is None:
                grad = OwnerClubAcademyGraduate(
                    club_id=state.club_id,
                    player_id=str(sq_player.id),
                    player_name=sq_player.name,
                    position=sq_player.position,
                    intake_world_day=max(1, world_day - 5),
                    promoted_world_day=world_day,
                    initial_rating=int(sq_player.rating),
                    current_rating=int(sq_player.rating),
                    potential_rating=int(sq_player.potential),
                    first_team_appearances=0,
                    first_team_goals=0,
                    status="promoted",
                    idempotency_key=f"academy_grad:{state.club_id}:{sq_player.id}",
                )
                session.add(grad)
                session.flush()

            grad.first_team_appearances = int(grad.first_team_appearances or 0) + 1
            grad.first_team_goals = int(grad.first_team_goals or 0) + scored_in_match
            grad.current_rating = int(sq_player.rating)
            if grad.debut_match_id is None:
                grad.debut_match_id = match.id
                grad.debut_world_day = world_day
                grad.debut_opponent_name = opp_name
                grad.status = "first_team_debutant"
                grad.narrative_note = (
                    f"Made senior first-team debut vs {opp_name} on World Day {world_day} ({gf}-{ga})."
                )
                debutants.append(grad)
                record_history_entry(
                    session,
                    club_id=state.club_id,
                    season_number=season_num,
                    world_day=world_day,
                    category="academy_debut",
                    event_type="first_team_debut",
                    title=f"Academy Debut: {sq_player.name} Makes First-Team Bow vs {opp_name}",
                    narrative_summary=(
                        f"Homegrown academy graduate {sq_player.name} ({sq_player.position}, {sq_player.rating} OVR) "
                        f"made their senior debut for {state.club_name} against {opp_name} in {comp.name}."
                    ),
                    entity_type="player",
                    entity_id=sq_player.id,
                    entity_name=sq_player.name,
                    established_facts={
                        "player_name": sq_player.name,
                        "position": sq_player.position,
                        "rating": int(sq_player.rating),
                        "opponent_name": opp_name,
                        "match_id": match.id,
                    },
                    is_major_milestone=True,
                    idempotency_key=f"history:academy_debut:{state.club_id}:{sq_player.id}",
                )
            elif grad.first_team_appearances >= 5:
                grad.status = "club_regular"

    # 4. Record Match History Milestone (Landmark Victory / Heavy Defeat / Standard Result)
    is_rivalry_match = rivalry.intensity_score >= 45
    if margin >= 3 or (gf > ga and is_rivalry_match):
        cat = "landmark_victory"
        ev_type = "derby_triumph" if is_rivalry_match else "statement_victory"
        title = f"Landmark Victory: {state.club_name} {gf}-{ga} {opp_name} in {comp.name}"
        is_mile = True
    elif margin <= -3:
        cat = "heavy_defeat"
        ev_type = "heavy_defeat"
        title = f"Heavy Defeat: {state.club_name} {gf}-{ga} {opp_name} in {comp.name}"
        is_mile = True
    else:
        cat = "competition_participation"
        ev_type = f"match_{result_str}"
        title = f"{comp.name} Round {match.round_number}: {state.club_name} {gf}-{ga} {opp_name}"
        is_mile = False

    record_history_entry(
        session,
        club_id=state.club_id,
        season_number=season_num,
        world_day=world_day,
        category=cat,
        event_type=ev_type,
        title=title,
        narrative_summary=(
            f"{state.club_name} recorded a {gf}-{ga} {result_str} against {opp_name} "
            f"in Round {match.round_number} of {comp.name} under {tenure.manager_name}."
        ),
        entity_type="match",
        entity_id=match.id,
        entity_name=f"{state.club_name} vs {opp_name}",
        established_facts={
            "match_id": match.id,
            "club_goals": gf,
            "opponent_goals": ga,
            "opponent_name": opp_name,
            "competition_name": comp.name,
            "round_number": int(match.round_number),
        },
        is_major_milestone=is_mile,
        idempotency_key=f"{idem_prefix}:result",
    )

    # 5. Apply Supporter Sentiment Reaction to the Match
    rivalry_factor = 1.4 if is_rivalry_match else 1.0
    if gf > ga:
        base_res = (6.0 + min(6.0, margin * 2.0)) * rivalry_factor
        drivers: dict[str, float] = {
            "results": base_res,
            "rivalry_record": base_res * (1.2 if is_rivalry_match else 0.5),
            "matchday_experience": 4.0 if is_home else 2.0,
        }
        if debutants:
            drivers["youth_academy"] = 7.0
        sup_headline = f"Supporters Celebrate {gf}-{ga} Victory Over {opp_name}"
        sup_summary = (
            f"Match-going and lifelong supporters hailed the {gf}-{ga} triumph against {opp_name} in {comp.name}."
        )
    elif gf == ga:
        drivers = {
            "results": -1.0 if is_home else 1.5,
            "rivalry_record": 1.0 if not is_home and is_rivalry_match else -1.0,
        }
        if debutants:
            drivers["youth_academy"] = 5.0
        sup_headline = f"Mixed Terrace Verdict After {gf}-{ga} Draw With {opp_name}"
        sup_summary = f"Supporters debated a hard-fought {gf}-{ga} draw against {opp_name} in Round {match.round_number}."
    else:
        loss_sev = (-7.0 - min(8.0, abs(margin) * 2.5)) * rivalry_factor
        drivers = {
            "results": loss_sev,
            "rivalry_record": loss_sev * (1.25 if is_rivalry_match else 0.6),
            "owner_conduct": -3.5 if profile.consecutive_disappointments >= 2 else -1.5,
        }
        if debutants:
            drivers["youth_academy"] = 4.0
        sup_headline = f"Supporter Frustration Mounts After {gf}-{ga} Defeat to {opp_name}"
        sup_summary = (
            f"Supporters voiced disappointment following the {gf}-{ga} defeat against {opp_name} in {comp.name}."
        )

    sup_event = apply_supporter_reaction(
        session,
        state,
        event_type="match_reaction",
        trigger_source_type="match",
        trigger_source_id=match.id,
        headline=sup_headline,
        summary=sup_summary,
        driver_Impacts=drivers,
        idempotency_key=f"{idem_prefix}:supporter_reaction",
        is_disappointment=(gf < ga),
        is_victory_relief=(gf > ga),
    )

    # Update manager confidence on profile
    profile.confidence_in_manager = _clamp(
        int(profile.confidence_in_manager or 68) + (5 if gf > ga else 0 if gf == ga else -6),
        5,
        100,
    )

    # 6. Inject Matchday Atmosphere into OwnerMatch.narrative_json
    atmosphere = compute_matchday_atmosphere(
        session,
        state,
        profile=profile,
        segments=segments,
        opponent_club_id=opp_id,
        opponent_name=opp_name,
        is_knockout_or_decider=(comp.format == "knockout"),
    )
    narrative = dict(match.narrative_json or {})
    side_key = "home" if is_home else "away"
    narrative[f"{side_key}_atmosphere"] = atmosphere
    if is_home or "atmosphere" not in narrative:
        narrative["atmosphere"] = atmosphere
        narrative["matchday_atmosphere"] = atmosphere
    match.narrative_json = narrative
    flag_modified(match, "narrative_json")

    # 7. Publish Grounded Media Coverage (Match Report + Conditional Streak/Protest/Debut Stories)
    rep_delta = 2 if (gf > ga and margin >= 2) else 1 if gf > ga else -2 if (gf < ga and abs(margin) >= 2) else -1 if gf < ga else 0
    publish_media_story(
        session,
        state,
        outlet_key="local_club_chronicle" if not is_rivalry_match else "gtex_national_wire",
        story_type="match_report" if not is_rivalry_match else "rivalry_coverage",
        classification="verified_event",
        headline=f"{state.club_name} {gf}-{ga} {opp_name}: {'Rivalry Statement' if is_rivalry_match and gf > ga else 'Full-Time Report'} in {comp.name}",
        subheadline=f"Round {match.round_number} verified match dispatch · Supporter sentiment now {profile.overall_sentiment}/100",
        body=(
            f"In Round {match.round_number} of {comp.name}, {state.club_name} finished {gf}-{ga} against {opp_name}. "
            f"Manager {tenure.manager_name} has now overseen {tenure.matches_managed} matches ({tenure.wins} wins, "
            f"{tenure.draws} draws, {tenure.losses} losses). Overall supporter sentiment stands at {profile.overall_sentiment} "
            f"following a {sup_event.overall_sentiment_delta:+d} shift."
        ),
        source_type="match",
        source_id=match.id,
        established_facts={
            "match_id": match.id,
            "club_goals": gf,
            "opponent_goals": ga,
            "opponent_name": opp_name,
            "round_number": int(match.round_number),
            "matches_managed": int(tenure.matches_managed),
            "manager_wins": int(tenure.wins),
            "manager_draws": int(tenure.draws),
            "manager_losses": int(tenure.losses),
            "supporter_sentiment": int(profile.overall_sentiment),
            "sentiment_delta": abs(int(sup_event.overall_sentiment_delta)),
        },
        idempotency_key=f"{idem_prefix}:media_match_report",
        reputation_delta=rep_delta,
        supporter_sentiment_delta=int(sup_event.overall_sentiment_delta),
        commercial_attractiveness_delta=2 if gf > ga else -1 if gf < ga else 0,
        leadership_pressure_delta=4 if gf < ga else -2 if gf > ga else 0,
    )

    # Conditional Editorial Scrutiny on Repeated Poor Results
    if profile.consecutive_disappointments >= 3:
        publish_media_story(
            session,
            state,
            outlet_key="boardroom_investigative",
            story_type="supporter_reaction",
            classification="opinion",
            headline=f"Scrutiny Deepens at {state.club_name} After {profile.consecutive_disappointments} Consecutive Setbacks",
            subheadline=f"Editorial column: Supporter frustration reaches {profile.accumulated_frustration}/100 as terrace pressure mounts",
            body=(
                f"After {profile.consecutive_disappointments} straight disappointments culminating in the {gf}-{ga} result "
                f"against {opp_name}, questions are intensifying around the leadership of {state.club_name}. "
                f"Supporter sentiment has fallen to {profile.overall_sentiment} with accumulated frustration at "
                f"{profile.accumulated_frustration}."
            ),
            source_type="match_streak",
            source_id=match.id,
            established_facts={
                "consecutive_disappointments": int(profile.consecutive_disappointments),
                "club_goals": gf,
                "opponent_goals": ga,
                "supporter_sentiment": int(profile.overall_sentiment),
                "accumulated_frustration": int(profile.accumulated_frustration),
            },
            idempotency_key=f"{idem_prefix}:media_scrutiny_column",
            reputation_delta=-1,
            leadership_pressure_delta=6,
            also_mirror_to_newsroom=True,
        )

    # Conditional Academy Debut Spotlight
    for deb in debutants:
        publish_media_story(
            session,
            state,
            outlet_key="tactical_youth_observer",
            story_type="academy_development",
            classification="verified_event",
            headline=f"Academy Breakthrough: {deb.player_name} Makes Senior Debut for {state.club_name}",
            subheadline=f"Rated {deb.current_rating} OVR (potential {deb.potential_rating}) · Community supporters hail youth pathway",
            body=(
                f"Academy graduate {deb.player_name} stepped onto the pitch for {state.club_name} against {opp_name} "
                f"in Round {match.round_number} of {comp.name}, recording a senior rating of {deb.current_rating} "
                f"and ceiling of {deb.potential_rating}."
            ),
            source_type="academy_debut",
            source_id=f"{match.id}:{deb.player_id}",
            established_facts={
                "player_name": deb.player_name,
                "round_number": int(match.round_number),
                "current_rating": int(deb.current_rating),
                "potential_rating": int(deb.potential_rating),
            },
            idempotency_key=f"{idem_prefix}:media_debut:{deb.player_id}",
            reputation_delta=1,
            supporter_sentiment_delta=3,
        )

    session.flush()
    return {
        "supporter_sentiment": profile.overall_sentiment,
        "atmosphere": atmosphere,
        "rivalry_tier": rivalry.rivalry_tier,
        "debutants": [d.player_name for d in debutants],
    }


def record_season_completion_archive(
    session: Session,
    comp: OwnerCompetition,
    entries_list: list[OwnerCompetitionEntry],
) -> list[OwnerClubSeasonArchive]:
    """Record permanent season archive, trophies, promotions/relegations, and media milestones when a competition finishes."""
    archives: list[OwnerClubSeasonArchive] = []
    total_clubs = len(entries_list)

    for entry in entries_list:
        if entry.is_ai:
            continue
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == entry.club_id))
        if state is None:
            continue

        idem_key = f"season_archive:{comp.id}:{state.club_id}"
        existing = session.scalar(
            select(OwnerClubSeasonArchive).where(OwnerClubSeasonArchive.idempotency_key == idem_key)
        )
        if existing is not None:
            archives.append(existing)
            continue

        profile, _ = ensure_club_institutional_ecosystem(session, state)
        world_day = int(state.world_day or 1)
        season_num = _season_number_for_state(state)
        pos = int(entry.final_position or 1)
        trophy_won = pos == 1
        div_level = _division_level_int(state.division_level)

        if pos == 1:
            promo_status = "title_winner"
            if div_level > 1 and comp.format == "league":
                state.division_level = _division_level_str(div_level - 1)
                promo_status = "promoted"
        elif pos == 2 and comp.format == "league" and div_level > 1 and total_clubs >= 4:
            state.division_level = _division_level_str(div_level - 1)
            promo_status = "promoted"
        elif pos == total_clubs and comp.format == "league" and div_level < 4 and total_clubs >= 4:
            state.division_level = _division_level_str(div_level + 1)
            promo_status = "relegated"
        else:
            promo_status = "retained"

        # Find top scorer from squad
        squad_rows = list(
            session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()
        )
        top_scorer_name = None
        top_scorer_goals = 0
        for sp in squad_rows:
            g = int((sp.personality_json or {}).get("club_goals", 0))
            if g > top_scorer_goals or top_scorer_name is None:
                top_scorer_goals = g
                top_scorer_name = sp.name

        manager = dict(state.manager_json or {})
        mgr_name = str(manager.get("name") or "First-Team Manager")
        tenure = ensure_active_manager_tenure(session, state, manager)
        if trophy_won:
            tenure.trophies_won = int(tenure.trophies_won or 0) + 1
            honors = list(tenure.honors_json or [])
            honors.append({"competition": comp.name, "season_number": season_num, "world_day": world_day})
            tenure.honors_json = honors
            flag_modified(tenure, "honors_json")

        summary_text = (
            f"{state.club_name} finished #{pos} in {comp.name} ({entry.won}W-{entry.drawn}D-{entry.lost}L, "
            f"{entry.points} pts, GF {entry.goals_for} / GA {entry.goals_against}) under {mgr_name}."
        )

        archive = OwnerClubSeasonArchive(
            club_id=state.club_id,
            season_number=season_num,
            season_label=f"Season {season_num}",
            competition_id=comp.id,
            competition_name=comp.name,
            competition_format=comp.format,
            division_level=div_level,
            final_position=pos,
            played=int(entry.played),
            won=int(entry.won),
            drawn=int(entry.drawn),
            lost=int(entry.lost),
            goals_for=int(entry.goals_for),
            goals_against=int(entry.goals_against),
            points=int(entry.points),
            trophy_won=trophy_won,
            promotion_status=promo_status,
            manager_name=mgr_name,
            top_scorer_name=top_scorer_name,
            top_scorer_goals=top_scorer_goals,
            prize_money_gtex=Decimal("0.00"),
            average_attendance=int(state.fans or 1200),
            narrative_summary=summary_text,
            records_snapshot_json={
                "final_position": pos,
                "points": int(entry.points),
                "goals_for": int(entry.goals_for),
                "goals_against": int(entry.goals_against),
                "trophy_won": trophy_won,
                "promotion_status": promo_status,
            },
            idempotency_key=idem_key,
        )
        session.add(archive)
        archives.append(archive)

        # Record in permanent club history ledger
        hist_cat = "trophy_award" if trophy_won else "promotion_relegation" if promo_status in ("promoted", "relegated") else "competition_participation"
        record_history_entry(
            session,
            club_id=state.club_id,
            season_number=season_num,
            world_day=world_day,
            category=hist_cat,
            event_type=f"season_finish_{promo_status}",
            title=(
                f"Champions of {comp.name}!"
                if trophy_won
                else f"Season Campaign Completed: #{pos} in {comp.name} ({promo_status.title()})"
            ),
            narrative_summary=summary_text,
            entity_type="competition",
            entity_id=comp.id,
            entity_name=comp.name,
            established_facts={
                "competition_name": comp.name,
                "final_position": pos,
                "points": int(entry.points),
                "won": int(entry.won),
                "drawn": int(entry.drawn),
                "lost": int(entry.lost),
                "goals_for": int(entry.goals_for),
                "goals_against": int(entry.goals_against),
            },
            is_major_milestone=trophy_won or promo_status in ("promoted", "relegated"),
            idempotency_key=f"history:{idem_key}",
        )

        # Supporter & Media reaction to season finish
        if trophy_won or promo_status == "promoted":
            apply_supporter_reaction(
                session,
                state,
                event_type="supporter_celebration",
                trigger_source_type="competition",
                trigger_source_id=comp.id,
                headline=f"Supporters Celebrate {comp.name} {'Title Triumph' if trophy_won else 'Promotion'}!",
                summary=summary_text,
                driver_Impacts={
                    "results": 16.0,
                    "club_identity": 12.0,
                    "owner_conduct": 10.0,
                    "star_signings": 8.0,
                },
                idempotency_key=f"supporter:{idem_key}",
                is_victory_relief=True,
            )
            publish_media_story(
                session,
                state,
                outlet_key="gtex_national_wire",
                story_type="season_milestone",
                classification="verified_event",
                headline=f"{state.club_name} Crowned #{pos} in {comp.name} With {entry.points} Points",
                subheadline=f"Season {season_num} milestone under {mgr_name} ({entry.won} wins, {entry.goals_for} goals)",
                body=(
                    f"{state.club_name} completed their {comp.name} campaign in position {pos}, accumulating "
                    f"{entry.points} points from {entry.played} matches ({entry.won} wins, {entry.drawn} draws, "
                    f"{entry.lost} losses) and scoring {entry.goals_for} goals."
                ),
                source_type="competition",
                source_id=comp.id,
                established_facts={
                    "final_position": pos,
                    "points": int(entry.points),
                    "played": int(entry.played),
                    "won": int(entry.won),
                    "drawn": int(entry.drawn),
                    "lost": int(entry.lost),
                    "goals_for": int(entry.goals_for),
                },
                idempotency_key=f"media:{idem_key}",
                reputation_delta=5 if trophy_won else 3,
                supporter_sentiment_delta=10,
                commercial_attractiveness_delta=6,
                sponsorship_interest_delta=6,
            )
        elif promo_status == "relegated":
            apply_supporter_reaction(
                session,
                state,
                event_type="protest_escalation",
                trigger_source_type="competition",
                trigger_source_id=comp.id,
                headline=f"Supporter Anger After Relegation Finish (#{pos}) in {comp.name}",
                summary=summary_text,
                driver_Impacts={
                    "results": -16.0,
                    "club_identity": -12.0,
                    "owner_conduct": -14.0,
                },
                idempotency_key=f"supporter:{idem_key}",
                is_disappointment=True,
            )

    session.flush()
    return archives


# ---------------------------------------------------------------------------
# Event Hooks: Managerial Changes, Transfers, Academy & Infrastructure
# ---------------------------------------------------------------------------


def record_managerial_change(
    session: Session,
    state: OwnerClubState,
    *,
    action: str,
    new_manager: dict[str, Any] | None = None,
    previous_manager: dict[str, Any] | None = None,
    reason: str = "boardroom_decision",
    severance_fan_coin: int = 0,
    severance_gtex: int = 0,
    idempotency_key: str | None = None,
) -> None:
    """Record managerial appointment or dismissal across tenures, history ledger, supporters, and media."""
    ensure_club_institutional_ecosystem(session, state)
    world_day = int(state.world_day or 1)
    season_num = _season_number_for_state(state)
    prev_name = str((previous_manager or {}).get("name") or "Previous Manager")
    new_name = str((new_manager or {}).get("name") or "Caretaker Manager")
    idem = idempotency_key or f"mgr_change:{state.club_id}:{action}:{prev_name}:{new_name}:d{world_day}"

    # Close any active tenure for previous manager
    active_tenures = list(
        session.scalars(
            select(OwnerClubManagerialTenure).where(
                OwnerClubManagerialTenure.club_id == state.club_id,
                OwnerClubManagerialTenure.status == "active",
            )
        ).all()
    )
    for row in active_tenures:
        if action == "dismissed" or (new_manager and row.manager_name != new_name):
            row.status = "departed"
            row.departed_world_day = world_day
            row.departure_reason = reason
            row.severance_paid_gtex = Decimal(str(severance_gtex))
            row.severance_paid_fan_coin = Decimal(str(severance_fan_coin))
            severance_label = (
                f"{severance_fan_coin:,} Fan Coin severance"
                if severance_fan_coin
                else (f"{severance_gtex:,} GTEX severance" if severance_gtex else "no severance")
            )
            row.tenure_summary = (
                f"{row.manager_name} departed on World Day {world_day} ({reason}) with {severance_label} after {row.matches_managed} matches "
                f"({row.wins}W-{row.draws}D-{row.losses}L, {row.trophies_won} trophies)."
            )

    if new_manager and new_manager.get("name"):
        ensure_active_manager_tenure(session, state, new_manager)

    title = (
        f"Managerial Appointment: {new_name} Named Head Coach of {state.club_name}"
        if action == "appointed"
        else (
            f"Managerial Departure: {prev_name} Relieved of Duties " f"({severance_fan_coin:,} Fan Coin Severance)"
            if severance_fan_coin
            else (f"Managerial Departure: {prev_name} Relieved of Duties " f"({severance_gtex:,} GTX Severance)")
        )
    )
    summary = (
        f"Owner appointed {new_name} ({(new_manager or {}).get('style', 'balanced')} philosophy) on World Day {world_day}."
        if action == "appointed"
        else f"{prev_name} departed {state.club_name} on World Day {world_day} ({reason}); {new_name} installed."
    )

    record_history_entry(
        session,
        club_id=state.club_id,
        season_number=season_num,
        world_day=world_day,
        category="managerial_change",
        event_type=f"manager_{action}",
        title=title,
        narrative_summary=summary,
        entity_type="manager",
        entity_id=str((new_manager or previous_manager or {}).get("id") or new_name),
        entity_name=new_name if action == "appointed" else prev_name,
        established_facts={
            "previous_manager": prev_name,
            "new_manager": new_name,
            "world_day": world_day,
            "severance_fan_coin": int(severance_fan_coin),
            "severance_gtex": int(severance_gtex),
            "severance_currency": "FAN_COIN" if severance_fan_coin else ("GTEX_COIN" if severance_gtex else None),
        },
        is_major_milestone=True,
        idempotency_key=f"history:{idem}",
    )

    apply_supporter_reaction(
        session,
        state,
        event_type="manager_change_reaction",
        trigger_source_type="manager",
        trigger_source_id=new_name,
        headline=title,
        summary=summary,
        driver_Impacts=(
            {"results": 4.0, "club_identity": 5.0, "owner_conduct": 4.0}
            if action == "appointed"
            else {"results": -2.0, "club_identity": -4.0, "owner_conduct": -3.0}
        ),
        idempotency_key=f"supporter:{idem}",
    )

    publish_media_story(
        session,
        state,
        outlet_key="gtex_national_wire",
        story_type="managerial_development",
        classification="verified_event",
        headline=title,
        subheadline=f"Official dugout transition at {state.club_name} on World Day {world_day}",
        body=(
            f"On World Day {world_day}, {state.club_name} confirmed a dugout transition: {summary}"
        ),
        source_type="manager_change",
        source_id=idem,
        established_facts={
            "world_day": world_day,
            "severance_fan_coin": int(severance_fan_coin),
            "severance_gtex": int(severance_gtex),
            "severance_currency": "FAN_COIN" if severance_fan_coin else ("GTEX_COIN" if severance_gtex else None),
        },
        idempotency_key=f"media:{idem}",
        reputation_delta=1 if action == "appointed" else -1,
        leadership_pressure_delta=-2 if action == "appointed" else 3,
    )


def record_transfer_movement(
    session: Session,
    state: OwnerClubState,
    *,
    direction: str,
    transfer_type: str,
    player_id: str,
    player_name: str,
    position: str,
    age: int,
    overall_rating: int,
    fee_gtex: int | float | Decimal,
    wage_gtex: int | float | Decimal = 0,
    counterparty_club_name: str = "GTEX Transfer Market",
    idempotency_key: str | None = None,
) -> OwnerClubTransferRecord:
    """Record a player signing or departure in the permanent transfer ledger, update records, and trigger supporter/media reaction."""
    ensure_club_institutional_ecosystem(session, state)
    world_day = int(state.world_day or 1)
    season_num = _season_number_for_state(state)
    fee_dec = Decimal(str(fee_gtex or 0))
    wage_dec = Decimal(str(wage_gtex or 0))
    idem = idempotency_key or f"transfer:{state.club_id}:{direction}:{player_id}:d{world_day}"

    existing = session.scalar(
        select(OwnerClubTransferRecord).where(OwnerClubTransferRecord.idempotency_key == idem)
    )
    if existing is not None:
        return existing

    # Check if this is a club record signing or record sale
    prev_records = list(
        session.scalars(
            select(OwnerClubTransferRecord).where(
                OwnerClubTransferRecord.club_id == state.club_id,
                OwnerClubTransferRecord.direction == direction,
            )
        ).all()
    )
    max_prev_fee = max((Decimal(str(r.fee_gtex or 0)) for r in prev_records), default=Decimal("0"))
    is_rec_signing = direction == "arrival" and fee_dec > 0 and fee_dec >= max_prev_fee
    is_rec_sale = direction == "departure" and fee_dec > 0 and fee_dec >= max_prev_fee

    if is_rec_signing:
        for r in prev_records:
            r.is_record_signing = False
    if is_rec_sale:
        for r in prev_records:
            r.is_record_sale = False

    note = (
        f"{'Club-record signing' if is_rec_signing else 'Signed'} from {counterparty_club_name} for {int(fee_dec):,} GTX."
        if direction == "arrival"
        else f"{'Club-record sale' if is_rec_sale else 'Departed'} to {counterparty_club_name} for {int(fee_dec):,} GTX."
    )

    rec = OwnerClubTransferRecord(
        club_id=state.club_id,
        direction=direction,
        transfer_type=transfer_type,
        player_id=str(player_id),
        player_name=player_name,
        position=position,
        age=int(age),
        overall_rating=int(overall_rating),
        fee_gtex=fee_dec,
        wage_gtex=wage_dec,
        counterparty_club_name=counterparty_club_name,
        season_number=season_num,
        world_day=world_day,
        is_record_signing=is_rec_signing,
        is_record_sale=is_rec_sale,
        narrative_note=note[:240],
        idempotency_key=idem[:160],
    )
    session.add(rec)
    session.flush()

    record_history_entry(
        session,
        club_id=state.club_id,
        season_number=season_num,
        world_day=world_day,
        category="player_signing" if direction == "arrival" else "player_departure",
        event_type="record_signing" if is_rec_signing else "record_sale" if is_rec_sale else f"transfer_{direction}",
        title=(
            f"{'Record Signing' if is_rec_signing else 'New Signing'}: {player_name} ({overall_rating} OVR) Joins {state.club_name}"
            if direction == "arrival"
            else f"{'Record Sale' if is_rec_sale else 'Player Departure'}: {player_name} Moves to {counterparty_club_name}"
        ),
        narrative_summary=(
            f"{player_name} ({position}, age {age}, {overall_rating} OVR) "
            + (
                f"joined {state.club_name} from {counterparty_club_name} for {int(fee_dec):,} GTX."
                if direction == "arrival"
                else f"departed {state.club_name} for {counterparty_club_name} for {int(fee_dec):,} GTX."
            )
        ),
        entity_type="player",
        entity_id=str(player_id),
        entity_name=player_name,
        established_facts={
            "player_name": player_name,
            "position": position,
            "age": int(age),
            "overall_rating": int(overall_rating),
            "fee_gtex": int(fee_dec),
            "counterparty_club_name": counterparty_club_name,
        },
        is_major_milestone=is_rec_signing or is_rec_sale or int(overall_rating) >= 78,
        idempotency_key=f"history:{idem}",
    )

    # Differentiated supporter reaction: international & younger fans love marquee arrivals; local/lifelong care if key stars are sold
    if direction == "arrival":
        star_boost = 9.0 if overall_rating >= 75 else 5.0
        drivers = {
            "star_signings": star_boost,
            "results": 4.0,
            "owner_conduct": 4.0,
            "youth_academy": 5.0 if age <= 20 else 1.0,
        }
        sup_head = f"Supporters Welcome Signing of {player_name} ({overall_rating} OVR)"
    else:
        drivers = {
            "star_signings": -6.0 if overall_rating >= 75 else -2.0,
            "results": -3.0 if overall_rating >= 75 else 0.0,
            "owner_conduct": 2.0 if is_rec_sale else -2.0,
        }
        sup_head = f"Supporters React to Departure of {player_name} to {counterparty_club_name}"

    apply_supporter_reaction(
        session,
        state,
        event_type="transfer_reaction",
        trigger_source_type="transfer",
        trigger_source_id=rec.id,
        headline=sup_head,
        summary=note,
        driver_Impacts=drivers,
        idempotency_key=f"supporter:{idem}",
    )

    publish_media_story(
        session,
        state,
        outlet_key="transfer_insider_desk",
        story_type="transfer_coverage",
        classification="verified_event",
        headline=(
            f"CONFIRMED: {state.club_name} Complete {int(fee_dec)} GTX Signing of {player_name}"
            if direction == "arrival"
            else f"CONFIRMED: {player_name} Departs {state.club_name} in {int(fee_dec)} GTX Deal"
        ),
        subheadline=f"Verified transfer ledger transaction · {position} rated {overall_rating} OVR (age {age})",
        body=(
            f"{state.club_name} have officially completed the {direction} of {player_name} "
            f"(age {age}, rating {overall_rating}) for a verified fee of {int(fee_dec)} GTX."
        ),
        source_type="transfer",
        source_id=rec.id,
        established_facts={
            "player_name": player_name,
            "age": int(age),
            "overall_rating": int(overall_rating),
            "fee_gtex": int(fee_dec),
        },
        idempotency_key=f"media:{idem}",
        reputation_delta=2 if (direction == "arrival" and overall_rating >= 75) else 1 if direction == "arrival" else 0,
        commercial_attractiveness_delta=3 if direction == "arrival" else -1,
    )

    return rec


def record_academy_promotion_milestone(
    session: Session,
    state: OwnerClubState,
    *,
    academy_player: Any,
    squad_player: OwnerSquadPlayer,
) -> OwnerClubAcademyGraduate:
    """Record an academy prospect's promotion to the first-team squad."""
    ensure_club_institutional_ecosystem(session, state)
    world_day = int(state.world_day or 1)
    season_num = _season_number_for_state(state)
    idem = f"academy_grad:{state.club_id}:{squad_player.id}"

    grad = session.scalar(
        select(OwnerClubAcademyGraduate).where(OwnerClubAcademyGraduate.idempotency_key == idem)
    )
    if grad is None:
        grad = OwnerClubAcademyGraduate(
            club_id=state.club_id,
            player_id=str(squad_player.id),
            player_name=squad_player.name,
            position=squad_player.position,
            intake_world_day=max(1, world_day - 3),
            promoted_world_day=world_day,
            initial_rating=int(academy_player.rating),
            current_rating=int(squad_player.rating),
            potential_rating=int(squad_player.potential),
            first_team_appearances=0,
            first_team_goals=0,
            status="promoted",
            narrative_note=(
                f"Promoted from {state.club_name} Youth Academy to the senior squad on World Day {world_day} "
                f"({squad_player.rating} OVR / {squad_player.potential} POT)."
            ),
            idempotency_key=idem,
        )
        session.add(grad)
        session.flush()

    record_history_entry(
        session,
        club_id=state.club_id,
        season_number=season_num,
        world_day=world_day,
        category="academy_graduate",
        event_type="academy_promotion",
        title=f"Academy Graduate Promoted: {squad_player.name} Elevates to Senior Squad",
        narrative_summary=(
            f"Homegrown prospect {squad_player.name} ({squad_player.position}, age {squad_player.age}, "
            f"{squad_player.rating} OVR / {squad_player.potential} POT) graduated from the academy into the first team."
        ),
        entity_type="player",
        entity_id=str(squad_player.id),
        entity_name=squad_player.name,
        established_facts={
            "player_name": squad_player.name,
            "position": squad_player.position,
            "age": int(squad_player.age),
            "rating": int(squad_player.rating),
            "potential": int(squad_player.potential),
        },
        is_major_milestone=True,
        idempotency_key=f"history:{idem}",
    )

    apply_supporter_reaction(
        session,
        state,
        event_type="academy_pride",
        trigger_source_type="academy_graduate",
        trigger_source_id=str(squad_player.id),
        headline=f"Community & Lifelong Supporters Celebrate Promotion of Academy Talent {squad_player.name}",
        summary=f"The promotion of {squad_player.name} ({squad_player.rating} OVR, {squad_player.potential} POT) energized local and youth-focused supporter segments.",
        driver_Impacts={
            "youth_academy": 10.0,
            "club_identity": 7.0,
            "owner_conduct": 4.0,
        },
        idempotency_key=f"supporter:{idem}",
    )

    publish_media_story(
        session,
        state,
        outlet_key="tactical_youth_observer",
        story_type="academy_development",
        classification="verified_event",
        headline=f"{state.club_name} Promote Homegrown Prospect {squad_player.name} to First Team",
        subheadline=f"Academy pipeline delivers {squad_player.position} aged {squad_player.age} with {squad_player.potential} potential",
        body=(
            f"{state.club_name} have promoted {squad_player.name} (age {squad_player.age}, rating {squad_player.rating}, "
            f"potential {squad_player.potential}) from the youth academy into the senior squad on World Day {world_day}."
        ),
        source_type="academy_promotion",
        source_id=str(squad_player.id),
        established_facts={
            "player_name": squad_player.name,
            "age": int(squad_player.age),
            "rating": int(squad_player.rating),
            "potential": int(squad_player.potential),
            "world_day": world_day,
        },
        idempotency_key=f"media:{idem}",
        reputation_delta=1,
        supporter_sentiment_delta=4,
    )

    return grad


def generate_grounded_transfer_rumour(
    session: Session,
    state: OwnerClubState,
    *,
    target_name: str,
    position: str,
    age: int,
    current_rating: int,
    estimated_value_gtex: int,
    source_id: str,
) -> OwnerMediaStory:
    """Publish a clearly labeled, unconfirmed transfer rumour (`classification='rumour'`, `is_confirmed_fact=False`)."""
    world_day = int(state.world_day or 1)
    idem = f"media:rumour:{state.club_id}:{source_id}:d{world_day}"
    return publish_media_story(
        session,
        state,
        outlet_key="transfer_insider_desk",
        story_type="transfer_coverage",
        classification="rumour",
        headline=f"RUMOUR: {state.club_name} Linked With Recruitment Interest in {target_name}",
        subheadline=f"Unconfirmed market speculation · {position} (age {age}, {current_rating} OVR) valued around {estimated_value_gtex} GTX",
        body=(
            f"Unconfirmed recruitment murmurs suggest {state.club_name} scouts have monitored {target_name} "
            f"(age {age}, rating {current_rating}, estimated value {estimated_value_gtex} GTX). "
            f"No formal transfer agreement has been confirmed by the club."
        ),
        source_type="transfer_rumour",
        source_id=str(source_id),
        established_facts={
            "target_name": target_name,
            "position": position,
            "age": int(age),
            "current_rating": int(current_rating),
            "estimated_value_gtex": int(estimated_value_gtex),
            "is_confirmed_transfer": False,
        },
        idempotency_key=idem,
        reputation_delta=0,
        supporter_sentiment_delta=1,
        also_mirror_to_newsroom=False,
    )


# ---------------------------------------------------------------------------
# Owner Supporter Engagement & Media Response Actions
# ---------------------------------------------------------------------------


def engage_supporters(
    session: Session,
    state: OwnerClubState,
    *,
    action_type: str,
    stance: str = "collaborative",
    message: str = "",
    ticket_price_tier: str | None = None,
    community_investment_gtex: int = 0,
) -> dict[str, Any]:
    """Execute an owner supporter engagement action with contradiction detection and persistent consequences."""
    profile, segments = ensure_club_institutional_ecosystem(session, state)
    world_day = int(state.world_day or 1)
    season_num = _season_number_for_state(state)
    clean_msg = (message or "").strip() or f"Owner {action_type.replace('_', ' ')} ({stance})"

    contradiction_detected = False
    contradiction_reason: str | None = None
    credibility_delta = 0
    drivers: dict[str, float] = {}

    if action_type == "ticketing_decision":
        new_tier = (ticket_price_tier or "standard").lower()
        if new_tier not in ("affordable", "standard", "premium", "exploitative"):
            new_tier = "standard"
        old_tier = profile.ticket_price_tier
        profile.ticket_price_tier = new_tier
        facs = dict(state.facilities_json or {})
        facs["_ticket_price_tier"] = new_tier
        state.facilities_json = facs
        flag_modified(state, "facilities_json")

        if new_tier == "affordable":
            drivers = {"ticket_pricing": 12.0, "owner_conduct": 8.0, "matchday_experience": 5.0}
            credibility_delta = 4
            headline = f"Owner Introduces Affordable Ticket Pricing Policy at {state.club_name}"
        elif new_tier == "standard":
            drivers = {"ticket_pricing": 2.0, "owner_conduct": 1.0}
            headline = f"{state.club_name} Standardizes Matchday Ticket Structure"
        elif new_tier == "premium":
            drivers = {"ticket_pricing": -12.0, "owner_conduct": -8.0, "star_signings": 2.0}
            credibility_delta = -3
            headline = f"Supporter Backlash Over Premium Ticket Price Hike at {state.club_name}"
        else:
            drivers = {"ticket_pricing": -22.0, "owner_conduct": -16.0, "club_identity": -12.0}
            credibility_delta = -10
            headline = f"Fury on the Terraces as {state.club_name} Imposes Exploitative Ticket Pricing"
        summary = f"Ticket pricing tier changed from {old_tier} to {new_tier}. {clean_msg}"

    elif action_type == "public_statement":
        msg_lower = clean_msg.lower()
        # Check for contradictions between statement claims and actual club behavior
        if (
            any(w in msg_lower for w in ("affordable", "accessible", "working-class", "fair ticket", "community access"))
            and profile.ticket_price_tier in ("premium", "exploitative")
        ):
            contradiction_detected = True
            contradiction_reason = (
                f"Statement promised affordable supporter access while club ticket pricing is set to '{profile.ticket_price_tier}'."
            )
        elif (
            any(w in msg_lower for w in ("dominant", "unbeaten", "crisis is over", "flawless form"))
            and profile.consecutive_disappointments >= 2
        ):
            contradiction_detected = True
            contradiction_reason = (
                f"Statement claimed strong on-pitch momentum despite {profile.consecutive_disappointments} consecutive disappointments."
            )
        elif stance == "dismissive" or any(w in msg_lower for w in ("ignore", "stop complaining", "quiet")):
            contradiction_detected = True
            contradiction_reason = "Dismissive posture toward supporter concerns alienated organised groups."

        if contradiction_detected:
            drivers = {"owner_conduct": -12.0, "club_identity": -8.0, "ticket_pricing": -6.0}
            credibility_delta = -12
            headline = f"Supporters Reject Contradictory Owner Statement at {state.club_name}"
            summary = f"Supporter groups pointed out a contradiction: {contradiction_reason}"
        else:
            drivers = {"owner_conduct": 6.0, "club_identity": 5.0, "results": 2.0}
            credibility_delta = 3
            headline = f"Owner Issues Public Institutional Statement to {state.club_name} Supporters"
            summary = clean_msg

    elif action_type == "supporter_meeting":
        if profile.ticket_price_tier == "exploitative" and stance != "concessional":
            contradiction_detected = True
            contradiction_reason = "Owner convened a supporter meeting but refused to address exploitative ticket pricing."
            drivers = {"owner_conduct": -8.0, "ticket_pricing": -10.0}
            credibility_delta = -8
            headline = f"Tense Supporter Town Hall Ends in Stalemate Over Pricing"
            summary = contradiction_reason
        else:
            drivers = {"owner_conduct": 9.0, "club_identity": 8.0, "ticket_pricing": 4.0}
            credibility_delta = 5
            headline = f"Owner Holds Constructive Forum With {state.club_name} Supporter Groups"
            summary = f"Direct dialogue with lifelong fans and organised supporter groups eased tensions. {clean_msg}"

    elif action_type == "community_initiative":
        invest = max(0, int(community_investment_gtex or 250))
        if invest > 0:
            try:
                bal = ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX)
                if bal >= Decimal(str(invest)):
                    ledger.record(
                        session,
                        event_type="community_initiative",
                        source=ledger.club_account(state.club_id),
                        destination=ledger.WORLD_CLUBS,
                        currency=ledger.GTEX,
                        gross=Decimal(str(invest)),
                        club_id=state.club_id,
                        user_id=state.owner_user_id,
                        related_type="supporter_engagement",
                        related_id=state.club_id,
                        memo=f"Community & Grassroots Initiative ({invest} GTX)",
                    )
            except Exception as exc:
                logger.debug("Community initiative ledger note: %s", exc)
        profile.matchday_experience_rating = _clamp(int(profile.matchday_experience_rating or 60) + 6, 0, 100)
        drivers = {
            "youth_academy": 9.0,
            "owner_conduct": 10.0,
            "club_identity": 9.0,
            "matchday_experience": 6.0,
        }
        credibility_delta = 6
        headline = f"{state.club_name} Launches Local Community & Grassroots Football Initiative"
        summary = f"Committed {invest} GTX to local community and matchday access programmes. {clean_msg}"

    else:  # respond_to_concern
        if profile.ticket_price_tier == "exploitative":
            profile.ticket_price_tier = "standard"
            facs = dict(state.facilities_json or {})
            facs["_ticket_price_tier"] = "standard"
            state.facilities_json = facs
            flag_modified(state, "facilities_json")
        drivers = {"owner_conduct": 8.0, "ticket_pricing": 7.0, "club_identity": 6.0}
        credibility_delta = 5
        headline = f"Ownership Responds Directly to Supporter Trust Petition at {state.club_name}"
        summary = f"Ownership addressed key terrace concerns and committed to concrete reforms. {clean_msg}"

    event_token = str(uuid4())[:8]
    sup_event = apply_supporter_reaction(
        session,
        state,
        event_type=f"owner_{action_type}",
        trigger_source_type="owner_engagement",
        trigger_source_id=event_token,
        headline=headline,
        summary=summary,
        driver_Impacts=drivers,
        idempotency_key=f"supporter:engage:{state.club_id}:{action_type}:{event_token}",
        is_disappointment=contradiction_detected or (action_type == "ticketing_decision" and profile.ticket_price_tier in ("premium", "exploitative")),
        credibility_delta=credibility_delta,
        contradiction_detected=contradiction_detected,
        contradiction_reason=contradiction_reason,
    )

    record_history_entry(
        session,
        club_id=state.club_id,
        season_number=season_num,
        world_day=world_day,
        category="owner_decision" if not contradiction_detected else "supporter_movement",
        event_type=f"supporter_{action_type}",
        title=headline,
        narrative_summary=summary,
        entity_type="supporter_profile",
        entity_id=profile.id,
        entity_name=state.club_name,
        established_facts={
            "action_type": action_type,
            "ticket_price_tier": profile.ticket_price_tier,
            "overall_sentiment": int(profile.overall_sentiment),
            "owner_credibility_score": int(profile.owner_credibility_score),
            "contradiction_detected": contradiction_detected,
        },
        is_major_milestone=action_type in ("community_initiative", "ticketing_decision") or contradiction_detected,
        idempotency_key=f"history:engage:{state.club_id}:{event_token}",
    )

    publish_media_story(
        session,
        state,
        outlet_key="boardroom_investigative" if contradiction_detected else "local_club_chronicle",
        story_type="supporter_reaction" if contradiction_detected else "financial_ownership",
        classification="opinion" if contradiction_detected else "reported_information",
        headline=headline,
        subheadline=(
            f"Credibility falls to {profile.owner_credibility_score}/100 after contradictory messaging"
            if contradiction_detected
            else f"Supporter sentiment moves to {profile.overall_sentiment}/100 · Credibility {profile.owner_credibility_score}/100"
        ),
        body=(
            f"{summary} Overall supporter sentiment at {state.club_name} now stands at {profile.overall_sentiment} "
            f"with owner credibility rated {profile.owner_credibility_score}."
        ),
        source_type="owner_engagement",
        source_id=sup_event.id,
        established_facts={
            "overall_sentiment": int(profile.overall_sentiment),
            "owner_credibility_score": int(profile.owner_credibility_score),
            "community_investment_gtex": int(community_investment_gtex or 250) if action_type == "community_initiative" else 0,
        },
        idempotency_key=f"media:engage:{state.club_id}:{event_token}",
        reputation_delta=-2 if contradiction_detected else 1,
        supporter_sentiment_delta=int(sup_event.overall_sentiment_delta),
    )

    overview = get_supporters_overview(session, state)
    overview["contradiction_detected"] = contradiction_detected
    overview["contradiction_reason"] = contradiction_reason
    overview["reaction"] = {
        "id": sup_event.id,
        "event_type": "owner_contradictory_statement" if contradiction_detected else sup_event.event_type,
        "overall_delta": int(sup_event.overall_sentiment_delta),
        "credibility_delta": int(sup_event.credibility_delta),
        "segment_deltas": {
            k: (int(v.get("delta", 0)) if isinstance(v, dict) else int(v))
            for k, v in (sup_event.segment_deltas_json or {}).items()
        },
    }
    return overview


def respond_to_media_story(
    session: Session,
    state: OwnerClubState,
    *,
    story_id: str,
    speaker_role: str = "owner",
    response_stance: str = "measured",
    statement_text: str = "",
) -> dict[str, Any]:
    """Record an official owner or sporting-staff response to a media story and persist its consequences."""
    profile, _ = ensure_club_institutional_ecosystem(session, state)
    story = session.get(OwnerMediaStory, story_id)
    if story is None or story.club_id != state.club_id:
        raise ValueError("media_story_not_found")

    world_day = int(state.world_day or 1)
    season_num = _season_number_for_state(state)
    clean_text = (statement_text or "").strip() or f"Official {speaker_role} response ({response_stance})"

    # Domain governance: Owner handles ownership/business/institutional stories; sporting press belongs to football staff
    sporting_story_types = {"match_report", "player_story", "academy_development"}
    role_mismatch_penalty = False
    if speaker_role == "owner" and story.story_type in sporting_story_types and response_stance == "tactical_interference":
        role_mismatch_penalty = True

    contradiction = False
    contradiction_note = None
    if (
        story.classification == "verified_event"
        and response_stance == "deny_facts"
    ):
        contradiction = True
        contradiction_note = "Attempted to deny a verified ledger/match event."

    if contradiction or role_mismatch_penalty:
        rep_delta = -2
        cred_delta = -8
        sent_delta = -5
        effect_summary = (
            contradiction_note
            or "Owner overstepped into live tactical commentary instead of delegating sporting press to the manager."
        )
    else:
        rep_delta = 1 if response_stance in ("transparent", "measured", "ambitious", "reassuring") else 0
        cred_delta = 3
        sent_delta = 3
        effect_summary = "Coordinated club response reinforced institutional credibility."

    response_payload = {
        "responded_at": _now().isoformat(),
        "world_day": world_day,
        "speaker_role": speaker_role,
        "responder_role": speaker_role,
        "speaker_name": (
            str((state.manager_json or {}).get("name") or "First-Team Manager")
            if speaker_role == "first_team_manager"
            else "Club Owner"
        ),
        "stance": response_stance,
        "response_tone": response_stance,
        "statement_text": clean_text,
        "response_text": clean_text,
        "contradiction_detected": contradiction,
        "role_mismatch_penalty": role_mismatch_penalty,
        "reputation_effect": rep_delta,
        "credibility_effect": cred_delta,
        "supporter_sentiment_effect": sent_delta,
        "effect_summary": effect_summary,
    }
    story.owner_response_json = response_payload
    flag_modified(story, "owner_response_json")

    state.prestige = _clamp(int(state.prestige or 10) + rep_delta, 0, 100)

    apply_supporter_reaction(
        session,
        state,
        event_type="media_response_reaction",
        trigger_source_type="media_story",
        trigger_source_id=story.id,
        headline=f"{response_payload['speaker_name']} Responds to '{story.headline[:80]}'",
        summary=f"{clean_text} ({effect_summary})",
        driver_Impacts={
            "owner_conduct": float(sent_delta * 1.5),
            "club_identity": float(sent_delta),
        },
        idempotency_key=f"supporter:media_resp:{story.id}:{world_day}",
        is_disappointment=contradiction or role_mismatch_penalty,
        credibility_delta=cred_delta,
        contradiction_detected=contradiction,
        contradiction_reason=contradiction_note,
    )

    record_history_entry(
        session,
        club_id=state.club_id,
        season_number=season_num,
        world_day=world_day,
        category="owner_decision",
        event_type="media_response_issued",
        title=f"Public Communiqué Issued on {story.outlet_name} Report",
        narrative_summary=f"{response_payload['speaker_name']} ({response_stance}): \"{clean_text}\"",
        entity_type="media_story",
        entity_id=story.id,
        entity_name=story.outlet_name,
        established_facts={
            "story_id": story.id,
            "outlet_name": story.outlet_name,
            "speaker_role": speaker_role,
            "stance": response_stance,
        },
        is_major_milestone=False,
        idempotency_key=f"history:media_resp:{story.id}:{world_day}",
    )

    session.flush()
    return {
        "story": _serialize_media_story(story),
        "response": response_payload,
        "supporter_sentiment": profile.overall_sentiment,
        "owner_credibility_score": profile.owner_credibility_score,
        "prestige": state.prestige,
    }


# ---------------------------------------------------------------------------
# Autonomous World Tick Integration (Offline Progression)
# ---------------------------------------------------------------------------


def process_world_day_institutional_tick(
    session: Session,
    state: OwnerClubState,
) -> dict[str, Any]:
    """Reconcile supporter sentiment, media coverage, and scouting rumours during autonomous world-day progression."""
    profile, segments = ensure_club_institutional_ecosystem(session, state)
    world_day = int(state.world_day or 1)
    if int(profile.last_reconciled_world_day or 0) >= world_day:
        return {"world_day": world_day, "already_reconciled": True}

    profile.last_reconciled_world_day = world_day

    # 1. If the club has high-priority watchlist targets, occasionally generate a clearly labeled transfer rumour
    watchlist_items = list(
        session.scalars(
            select(OwnerScoutingWatchlist).where(OwnerScoutingWatchlist.club_id == state.club_id)
        ).all()
    )
    rumours_generated = 0
    if watchlist_items and (world_day % 3 == 0):
        target = watchlist_items[world_day % len(watchlist_items)]
        generate_grounded_transfer_rumour(
            session,
            state,
            target_name=target.player_name,
            position=target.position,
            age=int(target.age),
            current_rating=int(target.current_rating),
            estimated_value_gtex=int(target.estimated_value_gtex),
            source_id=target.id,
        )
        rumours_generated += 1

    # 2. Periodic Financial & Governance Media Dispatch
    if world_day % 7 == 0:
        bal = int(ledger.balance(session, ledger.club_account(state.club_id), ledger.GTEX))
        publish_media_story(
            session,
            state,
            outlet_key="boardroom_investigative",
            story_type="financial_ownership",
            classification="reported_information",
            headline=f"Weekly Governance Audit: {state.club_name} Treasury at {bal} GTX on World Day {world_day}",
            subheadline=f"Supporter confidence {profile.confidence_in_owner}/100 · Prestige {state.prestige}/100",
            body=(
                f"On World Day {world_day}, {state.club_name} holds a verified club treasury balance of {bal} GTX "
                f"with institutional prestige at {state.prestige} and overall supporter sentiment at "
                f"{profile.overall_sentiment}."
            ),
            source_type="world_tick",
            source_id=f"{state.club_id}:d{world_day}",
            established_facts={
                "world_day": world_day,
                "treasury_balance_gtex": bal,
                "prestige": int(state.prestige or 10),
                "supporter_sentiment": int(profile.overall_sentiment),
            },
            idempotency_key=f"media:weekly_audit:{state.club_id}:d{world_day}",
            reputation_delta=1 if bal >= 5000 else 0,
        )

    profile.atmosphere_profile_json = compute_matchday_atmosphere(
        session,
        state,
        profile=profile,
        segments=segments,
    )
    flag_modified(profile, "atmosphere_profile_json")
    session.flush()
    return {
        "world_day": world_day,
        "supporter_sentiment": profile.overall_sentiment,
        "active_protest_stage": profile.active_protest_stage,
        "rumours_generated": rumours_generated,
    }


# ---------------------------------------------------------------------------
# Query & Serialization Views (Supporters, Media, Full Institutional Archive)
# ---------------------------------------------------------------------------


def _serialize_media_story(story: OwnerMediaStory) -> dict[str, Any]:
    return {
        "id": story.id,
        "club_id": story.club_id,
        "world_day": story.world_day,
        "outlet_key": story.outlet_key,
        "outlet_name": story.outlet_name,
        "journalist_name": story.journalist_name,
        "editorial_focus": story.editorial_focus,
        "credibility_score": story.credibility_score,
        "story_type": story.story_type,
        "classification": story.classification,
        "is_confirmed_fact": bool(story.is_confirmed_fact),
        "headline": story.headline,
        "subheadline": story.subheadline,
        "body": story.body,
        "source_type": story.source_type,
        "source_id": story.source_id,
        "established_facts": dict(story.established_facts_json or {}),
        "grounding_report": dict(story.grounding_report_json or {}),
        "reputation_delta": story.reputation_delta,
        "supporter_delta": story.supporter_sentiment_delta,
        "supporter_sentiment_delta": story.supporter_sentiment_delta,
        "commercial_delta": story.commercial_attractiveness_delta,
        "pressure_delta": story.leadership_pressure_delta,
        "consequences": {
            "reputation_delta": story.reputation_delta,
            "supporter_sentiment_delta": story.supporter_sentiment_delta,
            "commercial_attractiveness_delta": story.commercial_attractiveness_delta,
            "sponsorship_interest_delta": story.sponsorship_interest_delta,
            "leadership_pressure_delta": story.leadership_pressure_delta,
        },
        "owner_response": story.owner_response_json,
        "created_at": story.created_at.isoformat() if story.created_at else None,
    }


def get_supporters_overview(session: Session, state: OwnerClubState) -> dict[str, Any]:
    """Return full supporter ecosystem state, segments, expectations, recent reactions, and matchday atmosphere."""
    profile, segments = ensure_club_institutional_ecosystem(session, state)
    events = list(
        session.scalars(
            select(OwnerSupporterEvent)
            .where(OwnerSupporterEvent.club_id == state.club_id)
            .order_by(desc(OwnerSupporterEvent.created_at))
            .limit(30)
        ).all()
    )
    atmosphere = compute_matchday_atmosphere(session, state, profile=profile, segments=segments)
    exp_dict = dict(profile.expectations_json or {})
    recent_list = [
        {
            "id": ev.id,
            "world_day": ev.world_day,
            "event_type": ev.event_type,
            "title": ev.headline,
            "headline": ev.headline,
            "summary": ev.summary,
            "overall_delta": ev.overall_sentiment_delta,
            "overall_sentiment_delta": ev.overall_sentiment_delta,
            "credibility_delta": ev.credibility_delta,
            "attendance_impact_pct": ev.attendance_impact_pct,
            "protest_stage_after": profile.active_protest_stage,
            "contradiction_detected": bool(ev.contradiction_detected),
            "contradiction_reason": ev.contradiction_reason,
            "segment_deltas": dict(ev.segment_deltas_json or {}),
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev in events
    ]

    return {
        "club_id": state.club_id,
        "club_name": state.club_name,
        "world_day": int(state.world_day or 1),
        "total_supporters": int(state.fans or 1200),
        "profile": {
            "identity_archetype": profile.supporter_culture_label,
            "supporter_culture_label": profile.supporter_culture_label,
            "identity_summary": exp_dict.get(
                "identity_summary",
                f"{profile.supporter_culture_label} supporter base with expectation target: {exp_dict.get('season_target', 'competitive_progress')}.",
            ),
            "overall_sentiment": int(profile.overall_sentiment),
            "confidence_in_owner": int(profile.confidence_in_owner),
            "confidence_in_manager": int(profile.confidence_in_manager),
            "loyalty_index": int(profile.loyalty_index),
            "matchday_enthusiasm": int(profile.matchday_enthusiasm),
            "scar_tissue_score": int(profile.accumulated_frustration),
            "accumulated_frustration": int(profile.accumulated_frustration),
            "consecutive_disappointments": int(profile.consecutive_disappointments),
            "consecutive_victories": int(profile.consecutive_victories),
            "ticket_price_tier": profile.ticket_price_tier,
            "ticket_price_gtex": {"affordable": 10, "standard": 18, "premium": 32, "exploitative": 50}.get(
                profile.ticket_price_tier, 18
            ),
            "matchday_experience_rating": int(profile.matchday_experience_rating),
            "expectation_level": exp_dict.get("season_target", "top_half"),
            "protest_stage": profile.active_protest_stage,
            "active_protest_stage": profile.active_protest_stage,
            "active_campaign_title": profile.active_campaign_headline,
            "active_campaign_headline": profile.active_campaign_headline,
            "active_campaign_summary": profile.active_campaign_headline,
            "attendance_modifier_pct": int(profile.attendance_modifier_pct),
            "owner_credibility_score": int(profile.owner_credibility_score),
            "expectations": exp_dict,
        },
        "segments": [
            {
                "id": seg.id,
                "segment_key": seg.segment_key,
                "display_name": seg.segment_name,
                "segment_name": seg.segment_name,
                "share_pct": int(seg.population_share_pct),
                "population_share_pct": int(seg.population_share_pct),
                "population_estimate": int(seg.member_count),
                "member_count": int(seg.member_count),
                "sentiment": int(seg.sentiment),
                "loyalty": int(seg.loyalty),
                "engagement": int(seg.enthusiasm),
                "enthusiasm": int(seg.enthusiasm),
                "owner_approval": int(seg.owner_approval),
                "scar_tissue": int(seg.scar_tissue),
                "status_label": seg.status_label,
                "primary_expectation": (seg.expectations_json or {}).get("core_demand", "Competitive progress"),
                "recent_reaction": (
                    (seg.recent_memory_json or [{}])[0].get("headline")
                    if seg.recent_memory_json
                    else seg.status_label
                ),
                "priorities": dict(seg.priorities_json or {}),
                "expectations": dict(seg.expectations_json or {}),
                "recent_memory": list(seg.recent_memory_json or []),
            }
            for seg in segments
        ],
        "matchday_atmosphere": atmosphere,
        "recent_events": recent_list,
        "recent_reactions": recent_list,
    }


def get_media_ecosystem_overview(
    session: Session,
    state: OwnerClubState,
    *,
    classification: str | None = None,
    story_type: str | None = None,
    outlet_key: str | None = None,
    limit: int = 40,
) -> dict[str, Any]:
    """Return the club's persistent media stories, journalist outlets, public standing, and rumour vs fact breakdown."""
    profile, _ = ensure_club_institutional_ecosystem(session, state)
    outlets = ensure_media_outlets(session)

    stmt = select(OwnerMediaStory).where(OwnerMediaStory.club_id == state.club_id)
    if classification and classification != "all":
        stmt = stmt.where(OwnerMediaStory.classification == classification)
    if story_type and story_type != "all":
        stmt = stmt.where(OwnerMediaStory.story_type == story_type)
    if outlet_key and outlet_key != "all":
        stmt = stmt.where(OwnerMediaStory.outlet_key == outlet_key)

    stories = list(
        session.scalars(stmt.order_by(desc(OwnerMediaStory.created_at)).limit(max(1, min(100, limit)))).all()
    )

    # Calculate aggregate media consequences from recent coverage
    all_club_stories = list(
        session.scalars(
            select(OwnerMediaStory)
            .where(OwnerMediaStory.club_id == state.club_id)
            .order_by(desc(OwnerMediaStory.created_at))
            .limit(30)
        ).all()
    )
    comm_bonus = sum(int(s.commercial_attractiveness_delta or 0) for s in all_club_stories)
    spon_bonus = sum(int(s.sponsorship_interest_delta or 0) for s in all_club_stories)
    pressure = _clamp(25 + sum(int(s.leadership_pressure_delta or 0) for s in all_club_stories), 0, 100)
    rep_score = int(state.prestige or 10)
    rep_tier = (
        "Global Powerhouse"
        if rep_score >= 80
        else "Continental Contender"
        if rep_score >= 60
        else "Established Institution"
        if rep_score >= 35
        else "Emerging Challenger"
    )
    standing_obj = {
        "public_reputation": rep_score,
        "public_reputation_score": rep_score,
        "reputation_tier": rep_tier,
        "supporter_sentiment": int(profile.overall_sentiment),
        "owner_credibility_score": int(profile.owner_credibility_score),
        "commercial_attractiveness_index": _clamp(50 + rep_score // 2 + comm_bonus, 10, 100),
        "sponsorship_interest_index": _clamp(50 + rep_score // 2 + spon_bonus, 10, 100),
        "leadership_pressure_index": pressure,
        "verified_count": sum(1 for s in all_club_stories if s.classification == "verified_event"),
        "reported_count": sum(1 for s in all_club_stories if s.classification == "reported_information"),
        "rumour_count": sum(1 for s in all_club_stories if s.classification == "rumour"),
        "opinion_count": sum(1 for s in all_club_stories if s.classification == "opinion"),
    }

    return {
        "club_id": state.club_id,
        "club_name": state.club_name,
        "world_day": int(state.world_day or 1),
        "standing": standing_obj,
        "media_standing": standing_obj,
        "outlets": [
            {
                "outlet_key": o.outlet_key,
                "name": o.outlet_name,
                "outlet_name": o.outlet_name,
                "journalist_name": o.journalist_name,
                "journalist_role": o.journalist_role,
                "editorial_focus": o.editorial_focus,
                "credibility_tier": o.credibility_tier,
                "credibility_score": int(o.credibility_score),
                "tone_bias": o.tone_style,
                "tone_style": o.tone_style,
            }
            for o in outlets.values()
        ],
        "stories": [_serialize_media_story(s) for s in stories],
    }


def compute_club_records_and_chapters(
    session: Session,
    state: OwnerClubState,
    *,
    season_archives: list[OwnerClubSeasonArchive],
    manager_tenures: list[OwnerClubManagerialTenure],
    transfers: list[OwnerClubTransferRecord],
    academy_graduates: list[OwnerClubAcademyGraduate],
    rivalries: list[OwnerClubRivalry],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Compute grounded club records and historical storytelling chapters strictly from persisted facts."""
    squad_players = list(
        session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == state.club_id)).all()
    )

    # 1. Player appearance & goal records
    most_apps_player = None
    most_apps = 0
    top_goal_player = None
    top_goals = 0
    for sp in squad_players:
        pers = dict(sp.personality_json or {})
        apps = int(pers.get("club_appearances", max(0, int(sp.minutes or 0) // 90)))
        goals = int(pers.get("club_goals", 0))
        if apps > most_apps:
            most_apps = apps
            most_apps_player = {"player_id": sp.id, "player_name": sp.name, "position": sp.position, "appearances": apps}
        if goals > top_goals:
            top_goals = goals
            top_goal_player = {"player_id": sp.id, "player_name": sp.name, "position": sp.position, "goals": goals}

    # 2. Match records (biggest win, heaviest defeat, highest attendance)
    matches = list(
        session.scalars(
            select(OwnerMatch).where(
                (OwnerMatch.home_club_id == state.club_id) | (OwnerMatch.away_club_id == state.club_id),
                OwnerMatch.status == "played",
            )
        ).all()
    )
    biggest_win: dict[str, Any] | None = None
    biggest_win_margin = 0
    heaviest_defeat: dict[str, Any] | None = None
    heaviest_defeat_margin = 0
    highest_attendance: dict[str, Any] | None = None
    max_att = 0

    for m in matches:
        is_home = m.home_club_id == state.club_id
        gf = int(m.home_goals if is_home else m.away_goals)
        ga = int(m.away_goals if is_home else m.home_goals)
        opp_name = m.away_name if is_home else m.home_name
        margin = gf - ga
        if margin > biggest_win_margin or (margin > 0 and biggest_win is None):
            biggest_win_margin = margin
            biggest_win = {
                "match_id": m.id,
                "opponent": opp_name,
                "score": f"{gf}-{ga}",
                "margin": margin,
                "round": m.round_number,
            }
        if margin < heaviest_defeat_margin or (margin < 0 and heaviest_defeat is None):
            heaviest_defeat_margin = margin
            heaviest_defeat = {
                "match_id": m.id,
                "opponent": opp_name,
                "score": f"{gf}-{ga}",
                "margin": abs(margin),
                "round": m.round_number,
            }
        if is_home:
            att = int((m.narrative_json or {}).get("attendance") or 0)
            if att > max_att:
                max_att = att
                highest_attendance = {
                    "match_id": m.id,
                    "opponent": opp_name,
                    "attendance": att,
                    "score": f"{gf}-{ga}",
                }

    # 3. Transfer records
    arrivals = [t for t in transfers if t.direction in ("arrival", "in")]
    departures = [t for t in transfers if t.direction in ("departure", "out")]
    rec_signing = max(arrivals, key=lambda t: Decimal(str(t.fee_gtex or 0)), default=None)
    rec_sale = max(departures, key=lambda t: Decimal(str(t.fee_gtex or 0)), default=None)
    best_season = min(season_archives, key=lambda s: (int(s.division_level or 4), int(s.final_position or 99)), default=None)

    club_records = {
        "most_appearances": most_apps_player,
        "all_time_top_scorer": top_goal_player,
        "top_historic_scorer": top_goal_player,
        "biggest_victory": biggest_win,
        "heaviest_defeat": heaviest_defeat,
        "highest_home_attendance": highest_attendance,
        "highest_league_finish": (
            {
                "position": best_season.final_position,
                "competition_name": best_season.competition_name,
                "season_number": best_season.season_number,
                "division_level": best_season.division_level,
            }
            if best_season
            else None
        ),
        "record_signing": (
            {
                "player_name": rec_signing.player_name,
                "fee_gtex": float(rec_signing.fee_gtex),
                "overall_rating": rec_signing.overall_rating,
                "world_day": rec_signing.world_day,
            }
            if rec_signing
            else None
        ),
        "record_sale": (
            {
                "player_name": rec_sale.player_name,
                "fee_gtex": float(rec_sale.fee_gtex),
                "counterparty": rec_sale.counterparty_club_name,
                "world_day": rec_sale.world_day,
            }
            if rec_sale
            else None
        ),
        "total_matches_played": len(matches),
        "total_trophies_won": sum(1 for s in season_archives if s.trophy_won),
    }

    # 4. Fact-grounded Historical Storytelling Chapters
    div_int = _division_level_int(state.division_level)
    chapters: list[dict[str, Any]] = [
        {
            "chapter_key": "founding_charter",
            "title": f"The Founding Charter of {state.club_name}",
            "era_label": "Day 1 · Institutional Genesis",
            "narrative": (
                f"{state.club_name} began its recorded journey in Division {div_int}, "
                f"building an institutional culture around its {int(state.fans or 1200):,} supporters."
            ),
            "grounded_facts": {"division_level": div_int, "supporters": int(state.fans or 1200)},
        }
    ]

    first_promo_or_title = next((s for s in reversed(season_archives) if s.trophy_won or s.promotion_status == "promoted"), None)
    if first_promo_or_title:
        chapters.append(
            {
                "chapter_key": "breakthrough_campaign",
                "title": (
                    f"The Season {first_promo_or_title.season_number} Triumph in {first_promo_or_title.competition_name}"
                    if first_promo_or_title.trophy_won
                    else f"The Season {state.club_name} Secured Promotion in {first_promo_or_title.competition_name}"
                ),
                "era_label": first_promo_or_title.season_label,
                "narrative": first_promo_or_title.narrative_summary,
                "grounded_facts": {
                    "competition": first_promo_or_title.competition_name,
                    "final_position": first_promo_or_title.final_position,
                    "points": first_promo_or_title.points,
                },
            }
        )

    best_mgr = max(manager_tenures, key=lambda t: (t.trophies_won, t.wins), default=None)
    if best_mgr and best_mgr.matches_managed > 0:
        chapters.append(
            {
                "chapter_key": "defining_managerial_era",
                "title": (
                    f"The Manager Who Delivered Silverware: {best_mgr.manager_name}"
                    if best_mgr.trophies_won > 0
                    else f"The Dugout Tenure of {best_mgr.manager_name}"
                ),
                "era_label": f"World Day {best_mgr.appointed_world_day}" + (f"–{best_mgr.departed_world_day}" if best_mgr.departed_world_day else "–Present"),
                "narrative": best_mgr.tenure_summary,
                "grounded_facts": {
                    "manager_name": best_mgr.manager_name,
                    "matches_managed": best_mgr.matches_managed,
                    "wins": best_mgr.wins,
                    "trophies_won": best_mgr.trophies_won,
                },
            }
        )

    star_grad = max(academy_graduates, key=lambda g: (g.first_team_goals, g.first_team_appearances, g.current_rating), default=None)
    if star_grad:
        chapters.append(
            {
                "chapter_key": "academy_legacy_chapter",
                "title": f"Academy Pathway: The Rise of {star_grad.player_name}",
                "era_label": f"Promoted World Day {star_grad.promoted_world_day or star_grad.intake_world_day}",
                "narrative": (
                    f"Homegrown talent {star_grad.player_name} ({star_grad.position}, {star_grad.current_rating} OVR) "
                    f"embodied the club's youth philosophy, recording {star_grad.first_team_appearances} senior appearances "
                    f"and {star_grad.first_team_goals} goals."
                ),
                "grounded_facts": {
                    "player_name": star_grad.player_name,
                    "appearances": star_grad.first_team_appearances,
                    "goals": star_grad.first_team_goals,
                },
            }
        )

    top_rivalry = max(rivalries, key=lambda r: r.intensity_score, default=None)
    if top_rivalry and top_rivalry.matches_played >= 1:
        chapters.append(
            {
                "chapter_key": "defining_rivalry",
                "title": f"The {top_rivalry.rival_club_name} Rivalry ({top_rivalry.rivalry_tier.replace('_', ' ').title()})",
                "era_label": f"{top_rivalry.matches_played} Competitive Encounters",
                "narrative": (
                    f"Across {top_rivalry.matches_played} meetings ({top_rivalry.wins}W-{top_rivalry.draws}D-{top_rivalry.losses}L, "
                    f"GF {top_rivalry.goals_for} / GA {top_rivalry.goals_against}), clashes with {top_rivalry.rival_club_name} "
                    f"forged a {top_rivalry.rivalry_tier.replace('_', ' ')} rivalry."
                ),
                "grounded_facts": {
                    "rival_club_name": top_rivalry.rival_club_name,
                    "matches_played": top_rivalry.matches_played,
                    "intensity_score": top_rivalry.intensity_score,
                },
            }
        )

    return club_records, chapters


def get_institutional_history_archive(
    session: Session,
    state: OwnerClubState,
    *,
    category: str | None = None,
    limit: int = 80,
) -> dict[str, Any]:
    """Return the complete permanent club history ledger and structured institutional archives."""
    ensure_club_institutional_ecosystem(session, state)

    stmt = select(OwnerClubHistoryEntry).where(OwnerClubHistoryEntry.club_id == state.club_id)
    if category and category != "all":
        stmt = stmt.where(OwnerClubHistoryEntry.category == category)
    timeline_entries = list(
        session.scalars(
            stmt.order_by(desc(OwnerClubHistoryEntry.world_day), desc(OwnerClubHistoryEntry.created_at)).limit(
                max(1, min(200, limit))
            )
        ).all()
    )

    season_archives = list(
        session.scalars(
            select(OwnerClubSeasonArchive)
            .where(OwnerClubSeasonArchive.club_id == state.club_id)
            .order_by(desc(OwnerClubSeasonArchive.season_number), desc(OwnerClubSeasonArchive.created_at))
        ).all()
    )
    manager_tenures = list(
        session.scalars(
            select(OwnerClubManagerialTenure)
            .where(OwnerClubManagerialTenure.club_id == state.club_id)
            .order_by(desc(OwnerClubManagerialTenure.appointed_world_day))
        ).all()
    )
    transfers = list(
        session.scalars(
            select(OwnerClubTransferRecord)
            .where(OwnerClubTransferRecord.club_id == state.club_id)
            .order_by(desc(OwnerClubTransferRecord.world_day), desc(OwnerClubTransferRecord.created_at))
        ).all()
    )
    academy_graduates = list(
        session.scalars(
            select(OwnerClubAcademyGraduate)
            .where(OwnerClubAcademyGraduate.club_id == state.club_id)
            .order_by(desc(OwnerClubAcademyGraduate.first_team_appearances), desc(OwnerClubAcademyGraduate.current_rating))
        ).all()
    )
    rivalries = list(
        session.scalars(
            select(OwnerClubRivalry)
            .where(OwnerClubRivalry.club_id == state.club_id)
            .order_by(desc(OwnerClubRivalry.intensity_score), desc(OwnerClubRivalry.matches_played))
        ).all()
    )

    club_records, narrative_chapters = compute_club_records_and_chapters(
        session,
        state,
        season_archives=season_archives,
        manager_tenures=manager_tenures,
        transfers=transfers,
        academy_graduates=academy_graduates,
        rivalries=rivalries,
    )

    milestones = [e for e in timeline_entries if e.is_major_milestone]

    grad_list = [
        {
            "id": g.id,
            "player_id": g.player_id,
            "player_name": g.player_name,
            "position": g.position,
            "intake_world_day": g.intake_world_day,
            "promoted_world_day": g.promoted_world_day,
            "debut_world_day": g.debut_world_day,
            "debut_match_id": g.debut_match_id,
            "debut_opponent": g.debut_opponent_name,
            "debut_opponent_name": g.debut_opponent_name,
            "promoted_age": 17,
            "promoted_rating": g.initial_rating,
            "initial_rating": g.initial_rating,
            "current_rating": g.current_rating,
            "potential_rating": g.potential_rating,
            "first_team_appearances": g.first_team_appearances,
            "first_team_goals": g.first_team_goals,
            "status": g.status,
            "status_note": g.narrative_note,
            "narrative_note": g.narrative_note,
        }
        for g in academy_graduates
    ]
    rivalry_list = [
        {
            "id": r.id,
            "rival_club_id": r.rival_club_id,
            "opponent_club_name": r.rival_club_name,
            "rival_club_name": r.rival_club_name,
            "rivalry_title": r.rivalry_name,
            "rivalry_name": r.rivalry_name,
            "origin_reason": r.origin_reason,
            "intensity": r.intensity_score,
            "intensity_score": r.intensity_score,
            "rivalry_tier": r.rivalry_tier,
            "matches_played": r.matches_played,
            "wins": r.wins,
            "draws": r.draws,
            "losses": r.losses,
            "goals_for": r.goals_for,
            "goals_against": r.goals_against,
            "last_meeting_world_day": r.last_meeting_world_day,
            "notable_moments": [
                m.get("headline") or f"{m.get('score', '')} vs {r.rival_club_name}"
                for m in (r.notable_encounters_json or [])
                if isinstance(m, dict)
            ],
            "notable_encounters": list(r.notable_encounters_json or []),
        }
        for r in rivalries
    ]

    return {
        "club_id": state.club_id,
        "club_name": state.club_name,
        "world_day": int(state.world_day or 1),
        "season_number": _season_number_for_state(state),
        "timeline": [
            {
                "id": e.id,
                "season_number": e.season_number,
                "world_day": e.world_day,
                "category": e.category,
                "event_type": e.event_type,
                "title": e.title,
                "summary": e.narrative_summary,
                "narrative_summary": e.narrative_summary,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "entity_name": e.entity_name,
                "established_facts": dict(e.established_facts_json or {}),
                "is_milestone": bool(e.is_major_milestone),
                "is_major_milestone": bool(e.is_major_milestone),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in timeline_entries
        ],
        "milestones": [
            {
                "id": e.id,
                "season_number": e.season_number,
                "world_day": e.world_day,
                "category": e.category,
                "title": e.title,
                "narrative_summary": e.narrative_summary,
            }
            for e in milestones
        ],
        "season_archive": [
            {
                "id": s.id,
                "season_number": s.season_number,
                "season_label": s.season_label,
                "competition_id": s.competition_id,
                "competition_name": s.competition_name,
                "competition_format": s.competition_format,
                "division_level": s.division_level,
                "division_name": _division_level_str(int(s.division_level or 4)),
                "final_position": s.final_position,
                "played": s.played,
                "won": s.won,
                "drawn": s.drawn,
                "lost": s.lost,
                "goals_for": s.goals_for,
                "goals_against": s.goals_against,
                "points": s.points,
                "trophy_won": bool(s.trophy_won),
                "promoted": s.promotion_status == "promoted",
                "relegated": s.promotion_status == "relegated",
                "promotion_status": s.promotion_status,
                "manager_name": s.manager_name,
                "top_scorer_name": s.top_scorer_name,
                "top_scorer_goals": s.top_scorer_goals,
                "narrative_summary": s.narrative_summary,
            }
            for s in season_archives
        ],
        "managerial_history": [
            {
                "id": t.id,
                "manager_id": t.manager_id,
                "manager_name": t.manager_name,
                "role": t.role,
                "style": t.tactical_style,
                "tactical_style": t.tactical_style,
                "appointed_world_day": t.appointed_world_day,
                "departed_world_day": t.departed_world_day,
                "is_active": t.status == "active",
                "status": t.status,
                "matches_managed": t.matches_managed,
                "wins": t.wins,
                "draws": t.draws,
                "losses": t.losses,
                "goals_for": t.goals_for,
                "goals_against": t.goals_against,
                "win_rate_pct": int(round((t.wins / max(1, t.matches_managed)) * 100)) if t.matches_managed else 0,
                "trophies_won": t.trophies_won,
                "departure_reason": t.departure_reason,
                "severance_paid_gtex": float(t.severance_paid_gtex or 0),
                "tenure_summary": t.tenure_summary,
            }
            for t in manager_tenures
        ],
        "transfer_history": [
            {
                "id": tr.id,
                "direction": tr.direction,
                "transfer_type": tr.transfer_type,
                "player_id": tr.player_id,
                "player_name": tr.player_name,
                "position": tr.position,
                "age": tr.age,
                "overall_rating": tr.overall_rating,
                "fee_gtex": float(tr.fee_gtex or 0),
                "wage_gtex": float(tr.wage_gtex or 0),
                "counterparty_club_name": tr.counterparty_club_name,
                "season_number": tr.season_number,
                "world_day": tr.world_day,
                "is_record_signing": bool(tr.is_record_signing),
                "is_record_sale": bool(tr.is_record_sale),
                "narrative_note": tr.narrative_note,
            }
            for tr in transfers
        ],
        "academy_graduates": grad_list,
        "academy_legacy": grad_list,
        "rivalries": rivalry_list,
        "historic_rivalries": rivalry_list,
        "club_records": club_records,
        "historical_chapters": narrative_chapters,
        "narrative_chapters": narrative_chapters,
    }
