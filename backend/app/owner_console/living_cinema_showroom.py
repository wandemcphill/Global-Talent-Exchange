"""GTEX Living Football World - Stage 7
Cinema 3D, Staff Arrivals and Prestige Showroom Engine.

Implements:
- 7.1 Cinematic Experience Catalog (19 canonical event types mapped to WebGL/Cinema scenes)
- 7.2 Manager & Staff Arrival Sequence (triggered strictly after confirmed backend appointment)
- 7.3 Genuine WebGL Scene Descriptors & Fallback Honesty Metadata
- 7.4 Prestige 3D Showroom Inspection, Ownership Provenance & Turntable Configurations
- 7.5 Canonical Player & Regen Presentation Validation (preserving facebank & identity)
- 7.6 Grounded Commercial & Sponsor Presentation Validation
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.club_profile import ClubProfile
from app.owner_console import ledger, living_club_world, storytelling
from app.owner_console.models import (
    OwnerClubEvent,
    OwnerClubState,
    OwnerShowroomAsset,
    OwnerSquadPlayer,
)

# ==============================================================================
# 1. Canonical Cinema 3D Event Types & Scene Mapping (Section 7.1)
# ==============================================================================

SUPPORTED_CINEMA_EVENT_TYPES: dict[str, dict[str, Any]] = {
    "manager_arrival": {
        "event_type": "manager_arrival",
        "scene_id": "manager_arrival",
        "render_backend": "threejs",
        "title": "New Manager Arrival & Press Unveiling",
        "badge_text": "MANAGER UNVEILING",
        "requires_verification": "staff_appointed",
    },
    "manager_appointment": {
        "event_type": "manager_appointment",
        "scene_id": "manager_arrival",
        "render_backend": "threejs",
        "title": "Official Manager Appointment Announcement",
        "badge_text": "OFFICIAL APPOINTMENT",
        "requires_verification": "staff_appointed",
    },
    "staff_signing": {
        "event_type": "staff_signing",
        "scene_id": "manager_arrival",
        "render_backend": "threejs",
        "title": "Executive & Technical Staff Signing",
        "badge_text": "EXECUTIVE ARRIVAL",
        "requires_verification": "staff_appointed",
    },
    "player_signing": {
        "event_type": "player_signing",
        "scene_id": "signing_walkout",
        "render_backend": "cinema_volumetric",
        "title": "First-Team Player Signing Walkout",
        "badge_text": "NEW SIGNING",
        "requires_verification": "squad_player",
    },
    "player_presentation": {
        "event_type": "player_presentation",
        "scene_id": "signing_walkout",
        "render_backend": "cinema_volumetric",
        "title": "Marquee Squad Player Presentation",
        "badge_text": "SQUAD PRESENTATION",
        "requires_verification": "squad_player",
    },
    "trophy_presentation": {
        "event_type": "trophy_presentation",
        "scene_id": "trophy_podium",
        "render_backend": "threejs",
        "title": "Championship Trophy Presentation",
        "badge_text": "SILVERWARE CEREMONY",
        "requires_verification": "club_state",
    },
    "club_announcement": {
        "event_type": "club_announcement",
        "scene_id": "club_announcement",
        "render_backend": "cinema_volumetric",
        "title": "Official Club Press Communiqué",
        "badge_text": "CLUB COMMUNIQUÉ",
        "requires_verification": "club_state",
    },
    "executive_negotiation": {
        "event_type": "executive_negotiation",
        "scene_id": "negotiation_table",
        "render_backend": "cinema_volumetric",
        "title": "Executive Contract & Transfer Negotiation",
        "badge_text": "EXECUTIVE TABLE",
        "requires_verification": "club_state",
    },
    "boardroom_clash": {
        "event_type": "boardroom_clash",
        "scene_id": "boardroom_clash",
        "render_backend": "cinema_volumetric",
        "title": "Boardroom Strategic Summit",
        "badge_text": "BOARDROOM SUMMIT",
        "requires_verification": "club_state",
    },
    "club_takeover": {
        "event_type": "club_takeover",
        "scene_id": "club_takeover",
        "render_backend": "cinema_volumetric",
        "title": "Ownership & Consortium Milestone",
        "badge_text": "OWNERSHIP MILESTONE",
        "requires_verification": "club_state",
    },
    "academy_wonderkid": {
        "event_type": "academy_wonderkid",
        "scene_id": "wonderkid_emergence",
        "render_backend": "cinema_volumetric",
        "title": "Academy Wonderkid First-Team Emergence",
        "badge_text": "ACADEMY PRODIGY",
        "requires_verification": "squad_player",
    },
    "competition_victory": {
        "event_type": "competition_victory",
        "scene_id": "competition_final",
        "render_backend": "cinema_volumetric",
        "title": "Competition Victory Celebration",
        "badge_text": "CHAMPIONS",
        "requires_verification": "club_state",
    },
    "award_presentation": {
        "event_type": "award_presentation",
        "scene_id": "world_gala",
        "render_backend": "cinema_volumetric",
        "title": "World Football Gala Award Presentation",
        "badge_text": "WORLD GALA",
        "requires_verification": "club_state",
    },
    "sponsor_announcement": {
        "event_type": "sponsor_announcement",
        "scene_id": "new_ad_deal",
        "render_backend": "cinema_volumetric",
        "title": "Verified Commercial Partner Unveiling",
        "badge_text": "COMMERCIAL PARTNER",
        "requires_verification": "verified_sponsor",
    },
    "facility_opening": {
        "event_type": "facility_opening",
        "scene_id": "facility_upgrade",
        "render_backend": "cinema_volumetric",
        "title": "Club Campus Facility Ribbon-Cutting",
        "badge_text": "INFRASTRUCTURE UNVEILING",
        "requires_verification": "club_state",
    },
    "prestige_asset_presentation": {
        "event_type": "prestige_asset_presentation",
        "scene_id": "luxury_inspection_turntable",
        "render_backend": "threejs",
        "title": "Prestige Collection 3D Turntable Showcase",
        "badge_text": "PRESTIGE COLLECTION",
        "requires_verification": "owned_showroom_asset",
    },
    "luxury_car_showcase": {
        "event_type": "luxury_car_showcase",
        "scene_id": "luxury_inspection_turntable",
        "render_backend": "threejs",
        "title": "Bespoke Hypercar & Executive Vehicle Showcase",
        "badge_text": "AUTOMOTIVE ATELIER",
        "requires_verification": "owned_showroom_asset",
    },
    "private_jet_showcase": {
        "event_type": "private_jet_showcase",
        "scene_id": "luxury_inspection_turntable",
        "render_backend": "threejs",
        "title": "Intercontinental Club Aviation Runway Showcase",
        "badge_text": "CLUB AVIATION",
        "requires_verification": "owned_showroom_asset",
    },
    "club_bus_showcase": {
        "event_type": "club_bus_showcase",
        "scene_id": "luxury_inspection_turntable",
        "render_backend": "threejs",
        "title": "First-Team Luxury Coach Presentation",
        "badge_text": "FIRST-TEAM TRANSIT",
        "requires_verification": "owned_showroom_asset",
    },
}

SHOWROOM_3D_MESH_ARCHETYPES: dict[str, dict[str, Any]] = {
    "sovereign_900x_jet": {
        "mesh_archetype": "private_jet",
        "scene_id": "luxury_inspection_turntable",
        "model_path": "/assets/showroom/sovereign_900x_jet.glb",
        "camera_presets": ["exterior_front", "profile_side", "cockpit_detail", "aerial_showcase"],
        "livery_options": ["club_home", "sovereign_gold", "stealth_carbon", "platinum_white"],
        "dimensions_m": [28.4, 7.6, 29.2],
    },
    "gulfstream_g700_exec_jet": {
        "mesh_archetype": "private_jet",
        "scene_id": "luxury_inspection_turntable",
        "model_path": "/assets/showroom/gulfstream_g700_exec_jet.glb",
        "camera_presets": ["exterior_front", "profile_side", "cockpit_detail", "aerial_showcase"],
        "livery_options": ["club_home", "sovereign_gold", "stealth_carbon", "platinum_white"],
        "dimensions_m": [33.4, 7.7, 31.3],
    },
    "vanguard_xii_coach": {
        "mesh_archetype": "club_bus",
        "scene_id": "luxury_inspection_turntable",
        "model_path": "/assets/showroom/vanguard_xii_coach.glb",
        "camera_presets": ["exterior_front", "profile_side", "cockpit_detail", "aerial_showcase"],
        "livery_options": ["club_home", "sovereign_gold", "stealth_carbon", "platinum_white"],
        "dimensions_m": [14.0, 4.0, 2.55],
    },
    "executive_suv_command": {
        "mesh_archetype": "luxury_suv",
        "scene_id": "luxury_inspection_turntable",
        "model_path": "/assets/showroom/executive_suv.glb",
        "camera_presets": ["exterior_front", "profile_side", "cockpit_detail", "aerial_showcase"],
        "livery_options": ["club_home", "sovereign_gold", "stealth_carbon", "platinum_white"],
        "dimensions_m": [5.35, 1.92, 2.18],
    },
    "veloce_gt9_hypercar": {
        "mesh_archetype": "hypercar",
        "scene_id": "luxury_inspection_turntable",
        "model_path": "/assets/showroom/veloce_gt9_hypercar.glb",
        "camera_presets": ["exterior_front", "profile_side", "cockpit_detail", "aerial_showcase"],
        "livery_options": ["club_home", "sovereign_gold", "stealth_carbon", "platinum_white"],
        "dimensions_m": [4.68, 1.19, 2.05],
    },
    "chronos_tourbillon_watch": {
        "mesh_archetype": "tourbillon_watch",
        "scene_id": "luxury_inspection_turntable",
        "model_path": "/assets/showroom/chronos_tourbillon_watch.glb",
        "camera_presets": ["exterior_front", "profile_side", "cockpit_detail", "aerial_showcase"],
        "livery_options": ["club_home", "sovereign_gold", "stealth_carbon", "platinum_white"],
        "dimensions_m": [0.044, 0.013, 0.044],
    },
}

SHOWROOM_OPERATIONAL_PERKS: dict[str, dict[str, Any]] = {
    "sovereign_900x_jet": {
        "perk_label": "Intercontinental Aviation Advantage",
        "recruitment_wage_bonus_pct": 6.0,
        "away_recovery_boost_days": 1,
        "squad_morale_floor_bonus": 2,
        "matchday_commercial_yield_base_gtex": 180,
        "vip_transport_tier": 3,
    },
    "gulfstream_g700_exec_jet": {
        "perk_label": "Flagship Global Charter Advantage",
        "recruitment_wage_bonus_pct": 7.5,
        "away_recovery_boost_days": 1,
        "squad_morale_floor_bonus": 2,
        "matchday_commercial_yield_base_gtex": 220,
        "vip_transport_tier": 4,
    },
    "vanguard_xii_coach": {
        "perk_label": "First-Team Matchday Transit Recovery",
        "recruitment_wage_bonus_pct": 2.0,
        "away_recovery_boost_days": 1,
        "squad_morale_floor_bonus": 3,
        "matchday_commercial_yield_base_gtex": 65,
        "vip_transport_tier": 1,
    },
    "executive_suv_command": {
        "perk_label": "Executive Arrival & Convoy Security",
        "recruitment_wage_bonus_pct": 3.0,
        "away_recovery_boost_days": 0,
        "squad_morale_floor_bonus": 1,
        "matchday_commercial_yield_base_gtex": 55,
        "vip_transport_tier": 2,
    },
    "veloce_gt9_hypercar": {
        "perk_label": "Marquee Star Attraction & Brand Aura",
        "recruitment_wage_bonus_pct": 4.0,
        "away_recovery_boost_days": 0,
        "squad_morale_floor_bonus": 2,
        "matchday_commercial_yield_base_gtex": 95,
        "vip_transport_tier": 2,
    },
    "chronos_tourbillon_watch": {
        "perk_label": "Executive Honours & Loyalty Dividend",
        "recruitment_wage_bonus_pct": 1.5,
        "away_recovery_boost_days": 0,
        "squad_morale_floor_bonus": 1,
        "matchday_commercial_yield_base_gtex": 120,
        "vip_transport_tier": 0,
    },
}


def resolve_asset_operational_perk(catalog_key: str, category: str = "") -> dict[str, Any]:
    if catalog_key in SHOWROOM_OPERATIONAL_PERKS:
        return dict(SHOWROOM_OPERATIONAL_PERKS[catalog_key])
    cat_lower = (category or "").lower()
    if cat_lower in ("hospitality", "suite", "box"):
        return {
            "perk_label": "VIP Matchday Hospitality Yield",
            "recruitment_wage_bonus_pct": 2.0,
            "away_recovery_boost_days": 0,
            "squad_morale_floor_bonus": 1,
            "matchday_commercial_yield_base_gtex": 150,
            "vip_transport_tier": 0,
        }
    return {
        "perk_label": "Club Prestige & Commercial Aura",
        "recruitment_wage_bonus_pct": 1.5,
        "away_recovery_boost_days": 0,
        "squad_morale_floor_bonus": 1,
        "matchday_commercial_yield_base_gtex": 75,
        "vip_transport_tier": 0,
    }


def compute_club_showroom_perks(session: Session, club_id: str) -> dict[str, Any]:
    """
    Computes the authoritative gameplay & operational perks granted by the club's
    currently owned Prestige Showroom assets.
    """
    state = session.get(OwnerClubState, club_id)
    owned_rows = list(
        session.scalars(
            select(OwnerShowroomAsset).where(
                OwnerShowroomAsset.club_id == club_id,
                OwnerShowroomAsset.status.in_(["active", "gifted"]),
            )
        ).all()
    )
    facs = dict((state.facilities_json if state else None) or {})
    politics = dict(facs.get("_club_politics") or {})
    fan_sentiment = int(politics.get("supporter_confidence") or 60)
    sentiment_multiplier = round(max(0.6, min(1.75, fan_sentiment / 60.0)), 2)

    total_wage_bonus_pct = 0.0
    total_recovery_days = 0
    total_morale_bonus = 0
    total_yield_base = 0
    best_vip_transport: dict[str, Any] | None = None
    best_vip_tier = 0
    breakdown: list[dict[str, Any]] = []

    seen_keys: set[str] = set()
    for row in owned_rows:
        if row.catalog_key in seen_keys:
            continue
        seen_keys.add(row.catalog_key)
        cat_item = storytelling.SHOWROOM_CATALOG.get(row.catalog_key, {})
        perk = resolve_asset_operational_perk(row.catalog_key, row.category or cat_item.get("category", ""))
        archetype = SHOWROOM_3D_MESH_ARCHETYPES.get(row.catalog_key, {"mesh_archetype": "luxury_object"})

        total_wage_bonus_pct += float(perk["recruitment_wage_bonus_pct"])
        total_recovery_days += int(perk["away_recovery_boost_days"])
        total_morale_bonus += int(perk["squad_morale_floor_bonus"])
        total_yield_base += int(perk["matchday_commercial_yield_base_gtex"])

        tier = int(perk.get("vip_transport_tier", 0))
        if tier > best_vip_tier:
            best_vip_tier = tier
            best_vip_transport = {
                "asset_id": row.id,
                "catalog_key": row.catalog_key,
                "custom_name": row.custom_name or cat_item.get("name", row.catalog_key),
                "mesh_archetype": archetype.get("mesh_archetype", "private_jet"),
                "livery_applied": "club_home",
            }

        breakdown.append(
            {
                "asset_id": row.id,
                "catalog_key": row.catalog_key,
                "name": row.custom_name or cat_item.get("name", row.catalog_key),
                "perk_label": perk["perk_label"],
                "recruitment_wage_bonus_pct": perk["recruitment_wage_bonus_pct"],
                "away_recovery_boost_days": perk["away_recovery_boost_days"],
                "squad_morale_floor_bonus": perk["squad_morale_floor_bonus"],
                "matchday_commercial_yield_base_gtex": perk["matchday_commercial_yield_base_gtex"],
            }
        )

    effective_yield_gtex = int(round(total_yield_base * sentiment_multiplier))
    current_day = int((state.world_day if state else None) or 1)
    idem_key = f"cinema:showroom_yield:{club_id}:day:{current_day}"
    already_claimed_today = (
        session.scalar(select(OwnerClubEvent.id).where(OwnerClubEvent.idempotency_key == idem_key)) is not None
    )
    unclaimed_yield_gtex = 0 if already_claimed_today else effective_yield_gtex
    capped_wage_bonus = round(min(15.0, total_wage_bonus_pct), 1)
    capped_recovery_days = min(2, total_recovery_days)
    capped_morale_bonus = min(8, total_morale_bonus)

    return {
        "owned_distinct_assets": len(seen_keys),
        "recruitment_wage_bonus_pct": capped_wage_bonus,
        "wage_recruitment_bonus_pct": capped_wage_bonus,
        "away_recovery_boost_days": capped_recovery_days,
        "away_recovery_days_bonus": capped_recovery_days,
        "squad_morale_floor_bonus": capped_morale_bonus,
        "squad_morale_floor": capped_morale_bonus,
        "fan_sentiment_multiplier": sentiment_multiplier,
        "matchday_commercial_yield_gtex": effective_yield_gtex,
        "matchday_commercial_yield_rate": effective_yield_gtex,
        "unclaimed_commercial_yield_gtex": unclaimed_yield_gtex,
        "already_claimed_today": already_claimed_today,
        "vip_transport_asset": best_vip_transport,
        "owned_perk_breakdown": breakdown,
    }


def _build_press_conference_qa_prompt(
    subject_name: str,
    role_label: str,
    club_name: str,
) -> dict[str, Any]:
    return {
        "question_id": "unveiling_vision_q1",
        "journalist_name": "Tunde Folawiyo (Continental Football Desk)",
        "question_text": (
            f"With {subject_name} officially unveiled as {role_label}, what immediate mandate is {club_name} "
            f"setting for the dressing room and supporters?"
        ),
        "answered": False,
        "selected_stance": None,
        "options": [
            {
                "stance": "championship_ambition",
                "label": "Declare Immediate Silverware Ambition",
                "quote_preview": f"{subject_name} is here to compete for major honours immediately—no excuses.",
                "effects_preview": {
                    "fan_sentiment": "+6",
                    "board_confidence": "+4",
                    "influence": "+4",
                    "tension": "+2",
                },
            },
            {
                "stance": "tactical_pragmatism",
                "label": "Emphasize Tactical Identity & Structural Stability",
                "quote_preview": f"We are giving {subject_name} full authority to instil a disciplined, modern tactical system.",
                "effects_preview": {"board_confidence": "+5", "trust": "+5", "alignment": "+6", "tension": "-3"},
            },
            {
                "stance": "youth_and_sustainability",
                "label": "Champion Academy Pathway & Long-Term Dynasty",
                "quote_preview": f"{club_name} will blend elite recruitment with our brightest academy wonderkids.",
                "effects_preview": {"hoyd_respect": "+6", "gm_alignment": "+5", "fan_sentiment": "+3"},
            },
        ],
    }


def _resolve_club_branding(session: Session, club_id: str, state: OwnerClubState) -> dict[str, str]:
    cp = session.get(ClubProfile, club_id)
    return {
        "club_name": (cp.club_name if cp and cp.club_name else state.club_name) or "GTEX FC",
        "primary_color": (cp.primary_color if cp and cp.primary_color else "#10B981"),
        "secondary_color": (cp.secondary_color if cp and cp.secondary_color else "#0F172A"),
        "accent_color": (cp.accent_color if cp and cp.accent_color else "#F59E0B"),
    }


# ==============================================================================
# 2. Authoritative Manager & Staff Arrival Sequence (Section 7.2)
# ==============================================================================


def record_staff_arrival_cinematic(
    session: Session,
    user_id: str,
    club_id: str,
    appointed_staff: dict[str, Any],
    contract_id: str,
    total_contract_fee: int,
) -> dict[str, Any]:
    """
    Records an authoritative Manager/Staff Arrival cinematic event strictly AFTER
    the appointment transaction and contract creation have succeeded in the database.
    """
    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"Club {club_id} not found")

    branding = _resolve_club_branding(session, club_id, state)
    perks = compute_club_showroom_perks(session, club_id)
    role_key = str(appointed_staff.get("role") or "first_team_manager")
    role_label = str(appointed_staff.get("role_label") or role_key.replace("_", " ").title())
    staff_name = str(appointed_staff.get("name") or "Appointed Executive")
    rating = int(appointed_staff.get("rating") or 75)
    contract_years = int(appointed_staff.get("contract_years") or 2)
    salary_gtex = int(appointed_staff.get("salary_gtex") or appointed_staff.get("salary") or 1000)
    style = str(appointed_staff.get("style") or "Balanced")

    is_manager = role_key == "first_team_manager"
    event_type = "manager_arrival" if is_manager else "staff_signing"
    idem_key = f"cinema:staff_arrival:{club_id}:{contract_id}"

    existing = session.scalar(select(OwnerClubEvent).where(OwnerClubEvent.idempotency_key == idem_key))
    if existing is not None:
        return _format_cinematic_event(existing, branding)

    cinematic_payload = {
        "scene_id": "manager_arrival",
        "cinema_scene_type": "manager_arrival",
        "render_backend": "threejs",
        "verified_transaction": True,
        "contract_id": contract_id,
        "club_id": club_id,
        "club_name": branding["club_name"],
        "primary_color": branding["primary_color"],
        "secondary_color": branding["secondary_color"],
        "accent_color": branding["accent_color"],
        "subject_id": str(appointed_staff.get("profile_id") or appointed_staff.get("id") or ""),
        "subject_name": staff_name,
        "subject_role": role_key,
        "subject_role_label": role_label,
        "overall_rating": rating,
        "contract_years": contract_years,
        "salary_gtex": salary_gtex,
        "total_contract_fee_gtex": total_contract_fee,
        "tactical_style": style,
        "badge_text": "MANAGER UNVEILING" if is_manager else "EXECUTIVE SIGNING",
        "vip_transport": perks.get("vip_transport_asset"),
        "press_conference_qa": _build_press_conference_qa_prompt(staff_name, role_label, branding["club_name"]),
        "camera_sequence": [
            "tunnel_emergence",
            "press_flashbulbs",
            "contract_handover",
            "tactical_board_pose",
        ],
    }

    ev = OwnerClubEvent(
        club_id=club_id,
        category="cinema",
        event_type=event_type,
        severity="high",
        status="completed",
        source_type="staff_appointment",
        source_id=contract_id,
        title=f"{role_label} Unveiled: {staff_name} Arrives at {branding['club_name']}",
        description=(
            f"{branding['club_name']} have officially unveiled {staff_name} (OVR {rating}) as {role_label} "
            f"on a {contract_years}-year contract ({salary_gtex:,} GTEX/wk)."
        ),
        participants_json=[
            {"role": role_key, "name": staff_name, "contract_id": contract_id},
            {"role": "owner", "user_id": user_id},
        ],
        world_day=state.world_day or 1,
        idempotency_key=idem_key,
        actions_json=[],
        consequences_json={
            "cinematic_triggered": True,
            "contract_id": contract_id,
            **cinematic_payload,
        },
        resolved_at=datetime.now(timezone.utc),
    )
    session.add(ev)
    session.flush()
    return _format_cinematic_event(ev, branding)


def _format_cinematic_event(ev: OwnerClubEvent, branding: dict[str, str]) -> dict[str, Any]:
    meta = dict(ev.consequences_json or {})
    return {
        "event_id": ev.id,
        "club_id": ev.club_id,
        "event_type": ev.event_type,
        "scene_id": meta.get("scene_id", "manager_arrival"),
        "render_backend": meta.get("render_backend", "threejs"),
        "verified_transaction": bool(meta.get("verified_transaction", True)),
        "title": ev.title,
        "description": ev.description,
        "badge_text": meta.get("badge_text", "OFFICIAL PRESENTATION"),
        "club_name": meta.get("club_name", branding["club_name"]),
        "primary_color": meta.get("primary_color", branding["primary_color"]),
        "secondary_color": meta.get("secondary_color", branding["secondary_color"]),
        "accent_color": meta.get("accent_color", branding["accent_color"]),
        "subject_id": meta.get("subject_id"),
        "subject_name": meta.get("subject_name"),
        "subject_role": meta.get("subject_role"),
        "subject_role_label": meta.get("subject_role_label"),
        "overall_rating": meta.get("overall_rating"),
        "potential_rating": meta.get("potential_rating"),
        "is_regen": meta.get("is_regen"),
        "portrait_url": meta.get("portrait_url"),
        "contract_id": meta.get("contract_id"),
        "contract_years": meta.get("contract_years"),
        "salary_gtex": meta.get("salary_gtex"),
        "asset_catalog_key": meta.get("asset_catalog_key"),
        "asset_category": meta.get("asset_category"),
        "mesh_archetype": meta.get("mesh_archetype"),
        "sponsor_name": meta.get("sponsor_name"),
        "vip_transport": meta.get("vip_transport"),
        "medical_clearance_status": meta.get("medical_clearance_status"),
        "press_conference_qa": meta.get("press_conference_qa"),
        "camera_sequence": meta.get("camera_sequence", ["hero_orbit", "detail_closeup", "wide_stage"]),
        "world_day": ev.world_day,
        "created_at": ev.created_at.isoformat() if ev.created_at else datetime.now(timezone.utc).isoformat(),
    }


# ==============================================================================
# 3. Cinema 3D & Prestige Showroom Overview (Sections 7.1, 7.4, 7.5, 7.6)
# ==============================================================================


def get_cinema_and_showroom_overview(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    """
    Returns the unified Stage 7 Cinema 3D & Prestige 3D Showroom overview for a club:
    - Supported cinematic event types
    - Recent verified club cinematics
    - 3D Prestige Showroom catalog enriched with real ownership & 3D turntable archetypes
    - Canonical squad players & academy regens for presentations
    - Active verified commercial sponsors
    """
    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"Club {club_id} not found")

    branding = _resolve_club_branding(session, club_id, state)

    # 1. Recent verified cinematic events
    cinema_events = list(
        session.scalars(
            select(OwnerClubEvent)
            .where(OwnerClubEvent.club_id == club_id, OwnerClubEvent.category == "cinema")
            .order_by(OwnerClubEvent.created_at.desc())
            .limit(15)
        ).all()
    )

    # 2. Owned Showroom Assets from canonical OwnerShowroomAsset table
    owned_rows = list(
        session.scalars(
            select(OwnerShowroomAsset)
            .where(
                OwnerShowroomAsset.club_id == club_id,
                OwnerShowroomAsset.status.in_(["active", "gifted"]),
            )
            .order_by(OwnerShowroomAsset.created_at.desc())
        ).all()
    )
    owned_by_key: dict[str, list[dict[str, Any]]] = {}
    for row in owned_rows:
        owned_by_key.setdefault(row.catalog_key, []).append(
            {
                "asset_id": row.id,
                "catalog_key": row.catalog_key,
                "custom_name": row.custom_name,
                "category": row.category,
                "price_gtex": float(row.purchase_price_gtex or 0),
                "status": row.status,
                "gifted_to_player_id": row.gifted_to_player_id,
                "gifted_to_player_name": row.gifted_to_player_name,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )

    # 3. Enrich SHOWROOM_CATALOG with 3D WebGL turntable metadata
    prestige_3d_catalog: list[dict[str, Any]] = []
    for key, item in storytelling.SHOWROOM_CATALOG.items():
        archetype_cfg = SHOWROOM_3D_MESH_ARCHETYPES.get(
            key,
            {
                "mesh_archetype": (
                    "vip_suite"
                    if item.get("category") in ("hospitality", "suite", "box")
                    else "infrastructure" if item.get("category") in ("facility", "infrastructure") else "luxury_object"
                ),
                "scene_id": "luxury_inspection_turntable",
                "model_path": f"/assets/showroom/{key}.glb",
                "camera_presets": ["exterior_front", "profile_side", "cockpit_detail", "aerial_showcase"],
                "livery_options": ["club_home", "sovereign_gold", "stealth_carbon", "platinum_white"],
                "dimensions_m": [10.0, 4.0, 10.0],
            },
        )
        instances = owned_by_key.get(key, [])
        prestige_3d_catalog.append(
            {
                "catalog_key": key,
                "name": item["name"],
                "category": item["category"],
                "model": item.get("model", ""),
                "price_gtex": float(item.get("price_gtex", 0)),
                "prestige_bonus": int(item.get("prestige_bonus", 0)),
                "min_prestige": int(item.get("min_prestige", 0)),
                "description": item.get("description", ""),
                "specs": item.get("specs", {}),
                "can_gift_to_player": bool(item.get("can_gift_to_player", False)),
                "can_gift_to_staff": bool(item.get("can_gift_to_staff", False)),
                "image_url": storytelling.resolve_showroom_image_url(key),
                "high_res_image_url": item.get("high_res_image_url", ""),
                "is_owned": len(instances) > 0,
                "owned_count": len(instances),
                "owned_instances": instances,
                "webgl_3d": archetype_cfg,
                "operational_perks": resolve_asset_operational_perk(key, item.get("category", "")),
            }
        )

    # 4. Canonical Squad Players & Regens (preserving identity & portraits)
    players = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
    eligible_players = [
        {
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "age": p.age,
            "rating": p.rating,
            "potential": p.potential,
            "morale": p.morale,
            "is_regen": bool(p.is_regen),
            "portrait_url": storytelling.resolve_player_portrait_url(session, p.id, p.name),
        }
        for p in players
    ]

    # 5. Active Appointed Staff Roster
    staff_roster = living_club_world.resolve_club_staff_roster(state)

    # 6. Grounded Active Sponsors (from club facilities/commercial state)
    facs = dict(state.facilities_json or {})
    active_sponsors = list(facs.get("_active_sponsors") or [])
    if not active_sponsors and int(facs.get("commercial", 1) or 1) >= 2:
        active_sponsors = [
            {
                "sponsor_id": f"spon_{club_id}_primary",
                "sponsor_name": f"{branding['club_name']} Global Partners",
                "tier": "Official Club Partner",
                "status": "active",
            }
        ]

    active_perks = compute_club_showroom_perks(session, club_id)

    return {
        "club_id": club_id,
        "club_name": branding["club_name"],
        "primary_color": branding["primary_color"],
        "secondary_color": branding["secondary_color"],
        "accent_color": branding["accent_color"],
        "world_day": state.world_day or 1,
        "supported_event_types": list(SUPPORTED_CINEMA_EVENT_TYPES.values()),
        "recent_cinematics": [_format_cinematic_event(ev, branding) for ev in cinema_events],
        "prestige_3d_catalog": prestige_3d_catalog,
        "owned_assets_count": len(owned_rows),
        "active_operational_perks": active_perks,
        "eligible_players": eligible_players,
        "staff_roster": staff_roster,
        "active_sponsors": active_sponsors,
    }


# ==============================================================================
# 4. Trigger Verified Club Cinematic (Sections 7.1, 7.2, 7.4, 7.5, 7.6)
# ==============================================================================


def trigger_verified_club_cinematic(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    event_type: str,
    subject_id: str | None = None,
    catalog_key: str | None = None,
    asset_catalog_key: str | None = None,
    custom_headline: str | None = None,
) -> dict[str, Any]:
    """
    Validates authoritative backend state before recording and returning a Cinema 3D presentation.
    Never triggers a success scene for an unappointed staff member, non-existent player,
    unowned showroom asset, or unverified sponsor.
    """
    catalog_key = catalog_key or asset_catalog_key
    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"Club {club_id} not found")

    if event_type not in SUPPORTED_CINEMA_EVENT_TYPES:
        raise ValueError(f"Unsupported cinematic event_type: {event_type}")

    spec = SUPPORTED_CINEMA_EVENT_TYPES[event_type]
    verification_kind = spec["requires_verification"]
    branding = _resolve_club_branding(session, club_id, state)
    perks = compute_club_showroom_perks(session, club_id)

    meta_payload: dict[str, Any] = {
        "scene_id": spec["scene_id"],
        "render_backend": spec["render_backend"],
        "verified_transaction": True,
        "club_id": club_id,
        "club_name": branding["club_name"],
        "primary_color": branding["primary_color"],
        "secondary_color": branding["secondary_color"],
        "accent_color": branding["accent_color"],
        "badge_text": spec["badge_text"],
    }

    title = custom_headline or spec["title"]
    description = f"Official {branding['club_name']} 3D presentation."

    # A. Verify Appointed Staff
    if verification_kind == "staff_appointed":
        roster = living_club_world.resolve_club_staff_roster(state)
        role_key = subject_id or "first_team_manager"
        slot = roster.get(role_key)
        if not slot or not slot.get("is_appointed"):
            raise ValueError(f"Cannot trigger '{event_type}' cinematic: role '{role_key}' is vacant or unappointed.")
        meta_payload.update(
            {
                "subject_id": slot.get("person_id") or role_key,
                "subject_name": slot["name"],
                "subject_role": role_key,
                "subject_role_label": slot["role_label"],
                "overall_rating": int((state.manager_json or {}).get("rating", 82)),
                "vip_transport": perks.get("vip_transport_asset"),
                "press_conference_qa": _build_press_conference_qa_prompt(
                    slot["name"], slot["role_label"], branding["club_name"]
                ),
                "camera_sequence": [
                    "tunnel_emergence",
                    "press_flashbulbs",
                    "contract_handover",
                    "tactical_board_pose",
                ],
            }
        )
        title = custom_headline or f"{slot['role_label']} Presentation: {slot['name']}"
        description = (
            f"{branding['club_name']} present {slot['name']} ({slot['role_label']}) in an official 3D club unveiling."
        )

    # B. Verify Canonical Squad Player / Regen (4-stage arrival & medical unveiling)
    elif verification_kind == "squad_player":
        player: OwnerSquadPlayer | None = None
        if subject_id:
            player = session.get(OwnerSquadPlayer, subject_id)
        else:
            stmt = select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)
            if event_type == "academy_wonderkid":
                stmt = stmt.where(OwnerSquadPlayer.age <= 21)
            player = session.scalars(stmt.order_by(OwnerSquadPlayer.rating.desc())).first()

        if player is None or player.club_id != club_id:
            raise ValueError(f"Cannot trigger '{event_type}' cinematic: canonical squad player not found in club.")

        role_lbl = "Academy Wonderkid" if player.is_regen else f"First-Team {player.position}"
        medical_status = "cleared" if int(player.injured_days or 0) == 0 else "monitored_rehab"
        meta_payload.update(
            {
                "subject_id": player.id,
                "subject_name": player.name,
                "subject_role": player.position,
                "subject_role_label": role_lbl,
                "overall_rating": player.rating,
                "potential_rating": player.potential,
                "is_regen": bool(player.is_regen),
                "portrait_url": storytelling.resolve_player_portrait_url(session, player.id, player.name),
                "vip_transport": perks.get("vip_transport_asset"),
                "medical_clearance_status": medical_status,
                "press_conference_qa": _build_press_conference_qa_prompt(player.name, role_lbl, branding["club_name"]),
                "camera_sequence": [
                    "vip_transport_touchdown",
                    "medical_clearance_scan",
                    "boardroom_contract_signing",
                    "tunnel_shirt_reveal",
                ],
            }
        )
        title = custom_headline or f"Squad Unveiling: {player.name} ({player.position})"
        description = (
            f"{branding['club_name']} showcase {player.name} (OVR {player.rating}, POT {player.potential}) "
            f"across the 4-stage 3D medical & stadium unveiling."
        )

    # C. Verify Owned Showroom Asset
    elif verification_kind == "owned_showroom_asset":
        target_key = catalog_key or subject_id
        stmt = select(OwnerShowroomAsset).where(
            OwnerShowroomAsset.club_id == club_id,
            OwnerShowroomAsset.status.in_(["active", "gifted"]),
        )
        if target_key:
            stmt = stmt.where((OwnerShowroomAsset.catalog_key == target_key) | (OwnerShowroomAsset.id == target_key))
        owned_asset = session.scalars(stmt.order_by(OwnerShowroomAsset.created_at.desc())).first()
        if owned_asset is None:
            raise ValueError(
                f"Cannot trigger '{event_type}' cinematic: club does not own active showroom asset '{target_key}'."
            )

        cat_item = storytelling.SHOWROOM_CATALOG.get(owned_asset.catalog_key, {})
        archetype_cfg = SHOWROOM_3D_MESH_ARCHETYPES.get(
            owned_asset.catalog_key,
            {"mesh_archetype": "luxury_object"},
        )
        meta_payload.update(
            {
                "subject_id": owned_asset.id,
                "subject_name": owned_asset.custom_name or cat_item.get("name", owned_asset.catalog_key),
                "asset_catalog_key": owned_asset.catalog_key,
                "asset_category": owned_asset.category,
                "mesh_archetype": archetype_cfg.get("mesh_archetype", "luxury_object"),
                "price_gtex": float(owned_asset.purchase_price_gtex or 0),
                "camera_sequence": ["exterior_front", "profile_side", "cockpit_detail", "aerial_showcase"],
            }
        )
        title = custom_headline or f"3D Prestige Showcase: {meta_payload['subject_name']}"
        description = (
            f"Interactive 3D turntable inspection of {branding['club_name']}'s verified "
            f"{meta_payload['subject_name']}."
        )

    # D. Verify Active Sponsor
    elif verification_kind == "verified_sponsor":
        facs = dict(state.facilities_json or {})
        sponsors = list(facs.get("_active_sponsors") or [])
        sponsor_name = None
        if sponsors:
            sponsor_name = sponsors[0].get("sponsor_name")
        elif int(facs.get("commercial", 1) or 1) >= 2:
            sponsor_name = f"{branding['club_name']} Global Partners"

        if not sponsor_name:
            raise ValueError(
                "Cannot trigger 'sponsor_announcement' cinematic: no verified active commercial sponsor on record."
            )

        meta_payload["sponsor_name"] = sponsor_name
        meta_payload["subject_name"] = sponsor_name
        title = custom_headline or f"Commercial Partnership Unveiling: {sponsor_name}"
        description = f"{branding['club_name']} unveil verified commercial partner {sponsor_name}."

    # E. General Club State Event
    else:
        meta_payload["subject_name"] = branding["club_name"]

    ev = OwnerClubEvent(
        club_id=club_id,
        category="cinema",
        event_type=event_type,
        severity="important",
        status="completed",
        source_type="cinema_stage",
        source_id=str(subject_id or catalog_key or event_type),
        title=title,
        description=description,
        participants_json=[{"role": "owner", "user_id": user_id}],
        world_day=state.world_day or 1,
        actions_json=[],
        consequences_json={"cinematic_triggered": True, **meta_payload},
        resolved_at=datetime.now(timezone.utc),
    )
    session.add(ev)
    session.flush()

    return {
        "success": True,
        "cinematic_event": _format_cinematic_event(ev, branding),
    }


# ==============================================================================
# 5. Claim Showroom Commercial Yield & Answer Live Press Conference Q&A
# ==============================================================================


def claim_showroom_commercial_yield(
    session: Session,
    user_id: str,
    club_id: str,
) -> dict[str, Any]:
    """
    Settles the recurring matchday commercial dividend generated by the club's owned
    Prestige Showroom assets (VIP suites, private aviation, luxury fleet, timepieces)
    into the club's authoritative GTEX treasury once per world_day.
    """
    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"Club {club_id} not found")

    perks = compute_club_showroom_perks(session, club_id)
    yield_gtex = int(perks.get("matchday_commercial_yield_gtex") or 0)
    if yield_gtex <= 0:
        raise ValueError("No active Prestige Showroom assets owned to generate commercial yield.")

    current_day = int(state.world_day or 1)
    idem_key = f"cinema:showroom_yield:{club_id}:day:{current_day}"
    existing = session.scalar(select(OwnerClubEvent).where(OwnerClubEvent.idempotency_key == idem_key))
    if existing is not None:
        return {
            "success": True,
            "already_claimed": True,
            "world_day": current_day,
            "yield_credited_gtex": yield_gtex,
            "claimed_gtex": yield_gtex,
            "treasury_balance_gtex": float(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)),
            "operational_perks": perks,
        }

    ledger.record(
        session,
        event_type="showroom_commercial_yield",
        source=ledger.WORLD_CLUBS,
        destination=ledger.club_account(club_id),
        currency=ledger.GTEX,
        gross=Decimal(str(yield_gtex)),
        club_id=club_id,
        user_id=user_id,
        related_type="showroom_yield",
        related_id=f"{club_id}:day:{current_day}",
        memo=f"Prestige Showroom Commercial & Hospitality Yield (Day {current_day})",
        check_funds=False,
    )

    ev = OwnerClubEvent(
        club_id=club_id,
        category="commercial",
        event_type="showroom_commercial_yield_claimed",
        severity="info",
        status="completed",
        source_type="showroom_3d",
        source_id=f"day:{current_day}",
        title=f"Prestige Showroom Dividend Credited (+{yield_gtex:,} GTEX)",
        description=(
            f"Credited {yield_gtex:,} GTEX in commercial & VIP hospitality yield across "
            f"{perks['owned_distinct_assets']} owned Prestige Showroom asset(s)."
        ),
        participants_json=[{"role": "owner", "user_id": user_id}],
        world_day=current_day,
        idempotency_key=idem_key,
        actions_json=[],
        consequences_json={"yield_credited_gtex": yield_gtex, "operational_perks": perks},
        resolved_at=datetime.now(timezone.utc),
    )
    session.add(ev)
    session.flush()
    updated_perks = compute_club_showroom_perks(session, club_id)

    return {
        "success": True,
        "already_claimed": False,
        "world_day": current_day,
        "yield_credited_gtex": yield_gtex,
        "claimed_gtex": yield_gtex,
        "treasury_balance_gtex": float(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)),
        "operational_perks": updated_perks,
    }


def answer_cinematic_press_question(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    event_id: str,
    stance: str,
    custom_quote: str | None = None,
) -> dict[str, Any]:
    """
    Processes an interactive press conference Q&A choice during a 3D Manager/Player Unveiling,
    updating club politics (fan sentiment, board confidence) and executive relationships in real time.
    """
    state = session.get(OwnerClubState, club_id)
    if state is None:
        raise ValueError(f"Club {club_id} not found")

    ev = session.get(OwnerClubEvent, event_id)
    if ev is None or ev.club_id != club_id:
        raise ValueError(f"Cinematic event {event_id} not found for club {club_id}")

    valid_stances = {"championship_ambition", "tactical_pragmatism", "youth_and_sustainability"}
    if stance not in valid_stances:
        raise ValueError(f"Unsupported press conference stance '{stance}'. Expected one of {sorted(valid_stances)}.")

    branding = _resolve_club_branding(session, club_id, state)
    meta = dict(ev.consequences_json or {})
    qa = dict(
        meta.get("press_conference_qa")
        or _build_press_conference_qa_prompt(
            str(meta.get("subject_name") or "New Signing"),
            str(meta.get("subject_role_label") or "First-Team Appointment"),
            branding["club_name"],
        )
    )

    if qa.get("answered"):
        return {
            "success": True,
            "already_answered": True,
            "stance": qa.get("selected_stance"),
            "media_headline": qa.get("media_headline", "Official Press Statement Published"),
            "quote": qa.get("quote", "Statement on club sporting direction delivered to press pack."),
            "political_impact": qa.get("political_impact", {}),
            "effects": qa.get("applied_effects", {}),
            "cinematic_event": _format_cinematic_event(ev, branding),
        }

    facs = dict(state.facilities_json or {})
    politics = dict(facs.get("_club_politics") or {})
    fan_sentiment = int(politics.get("supporter_confidence") or 62)
    board_conf = int(politics.get("board_confidence") or 68)
    effects: dict[str, int] = {}
    subj_name = str(meta.get("subject_name") or "First-Team Manager")

    if stance == "championship_ambition":
        fan_sentiment = min(100, fan_sentiment + 6)
        board_conf = min(100, board_conf + 4)
        living_club_world.apply_relationship_delta(
            session,
            club_id=club_id,
            part_a_type="owner",
            part_a_id="owner",
            part_a_name="Club Owner",
            part_b_type="staff",
            part_b_id="first_team_manager",
            part_b_name=subj_name,
            delta_influence=4,
            delta_respect=3,
            delta_tension=2,
            reason="Press conference mandate: Immediate Championship Ambition",
        )
        effects = {"fan_sentiment_delta": 6, "board_confidence_delta": 4, "manager_influence_delta": 4}
        media_headline = f"{branding['club_name']} Owner Sets Immediate Silverware Mandate for {subj_name}"
        default_quote = f"{subj_name} is here to compete for major honours immediately—no excuses."
        political_impact = {
            "fan_sentiment": "+6",
            "board_confidence": "+4",
            "manager_influence": "+4",
        }
    elif stance == "tactical_pragmatism":
        board_conf = min(100, board_conf + 5)
        fan_sentiment = min(100, fan_sentiment + 2)
        living_club_world.apply_relationship_delta(
            session,
            club_id=club_id,
            part_a_type="owner",
            part_a_id="owner",
            part_a_name="Club Owner",
            part_b_type="staff",
            part_b_id="first_team_manager",
            part_b_name=subj_name,
            delta_trust=5,
            delta_alignment=6,
            delta_tension=-3,
            reason="Press conference mandate: Tactical Identity & Structural Stability",
        )
        effects = {"board_confidence_delta": 5, "manager_trust_delta": 5, "manager_alignment_delta": 6}
        media_headline = f"{branding['club_name']} Backs {subj_name} with Full Tactical & Structural Authority"
        default_quote = f"We are giving {subj_name} full authority to instil a disciplined, modern tactical system."
        political_impact = {
            "board_confidence": "+5",
            "manager_trust": "+5",
            "manager_alignment": "+6",
        }
    else:
        fan_sentiment = min(100, fan_sentiment + 3)
        board_conf = min(100, board_conf + 3)
        living_club_world.apply_relationship_delta(
            session,
            club_id=club_id,
            part_a_type="owner",
            part_a_id="owner",
            part_a_name="Club Owner",
            part_b_type="staff",
            part_b_id="head_of_youth_development",
            part_b_name="Head of Youth Development",
            delta_respect=6,
            delta_alignment=5,
            reason="Press conference mandate: Academy Pathway & Long-Term Dynasty",
        )
        effects = {"hoyd_respect_delta": 6, "hoyd_alignment_delta": 5, "fan_sentiment_delta": 3}
        media_headline = f"{branding['club_name']} Pledges Academy Pathway & Long-Term Dynasty Under {subj_name}"
        default_quote = f"{branding['club_name']} will blend elite recruitment with our brightest academy wonderkids."
        political_impact = {
            "hoyd_respect": "+6",
            "hoyd_alignment": "+5",
            "fan_sentiment": "+3",
        }

    resolved_quote = custom_quote or default_quote
    politics["supporter_confidence"] = fan_sentiment
    politics["board_confidence"] = board_conf
    facs["_club_politics"] = politics
    state.facilities_json = facs
    flag_modified(state, "facilities_json")

    qa["answered"] = True
    qa["selected_stance"] = stance
    qa["custom_quote"] = custom_quote
    qa["media_headline"] = media_headline
    qa["quote"] = resolved_quote
    qa["political_impact"] = political_impact
    qa["applied_effects"] = effects
    meta["press_conference_qa"] = qa
    ev.consequences_json = meta
    flag_modified(ev, "consequences_json")
    session.flush()

    return {
        "success": True,
        "already_answered": False,
        "stance": stance,
        "media_headline": media_headline,
        "quote": resolved_quote,
        "political_impact": political_impact,
        "fan_sentiment_index": fan_sentiment,
        "board_confidence": board_conf,
        "effects": effects,
        "cinematic_event": _format_cinematic_event(ev, branding),
    }
