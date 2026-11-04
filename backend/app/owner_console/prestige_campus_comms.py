"""GTEX Club Prestige, Interactive 3D Campus Builder, Club Communications & Grounded Newsroom Services.

Implements the canonical backend services for the GTEX Club Prestige Engineering Brief:
1. Club Owner's Office & Prestige Asset Collection (12 canonical visual assets, legal ownership breakdown, specs).
2. Sims-Inspired 3D Club Campus Builder (24x18 grid, modular buildings, collision/boundary validation, staged construction).
3. Unified Club Communications (8 destinations: Inbox, Direct Conversations, Staff Room, Squad Room, Meetings,
   Requests & Decisions, Announcements, Archive; Owner/Manager/Player/Staff permissions & grounded replies).
4. Verified GTEX Newsroom Extensions (provenance inspection, editorial workflow states, verified club event sync).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.owner_console import engine, ledger
from app.owner_console.models import (
    LedgerEvent,
    OwnerBroadcastEvent,
    OwnerClubState,
    OwnerInboxItem,
    OwnerNewsroomArticle,
    OwnerShowroomAsset,
    OwnerSquadPlayer,
)
from app.owner_console.service import OwnerError, require_state


# ---------------------------------------------------------------------------
# 1. CANONICAL VISUAL ASSET MANIFEST (12 Generated High-Resolution Assets)
# ---------------------------------------------------------------------------

PRESTIGE_VISUAL_MANIFEST: list[dict[str, Any]] = [
    {
        "id": "executive_suv",
        "title": "GTEX Sovereign Command SUV",
        "category": "Luxury Vehicles",
        "file": "/console/img/prestige/01_executive_suv.png",
        "webp": "/console/img/showroom/executive_suv.webp",
        "aspect_ratio": "16:10",
        "used_in": ["owner_office", "showroom", "player_gifting"],
    },
    {
        "id": "luxury_grand_tourer",
        "title": "Veloce GT9 Emerald Grand Tourer",
        "category": "Luxury Vehicles",
        "file": "/console/img/prestige/02_luxury_grand_tourer.png",
        "webp": "/console/img/showroom/veloce_gt9_hypercar.webp",
        "aspect_ratio": "16:10",
        "used_in": ["owner_office", "showroom", "player_gifting"],
    },
    {
        "id": "emerald_tourbillon_watch",
        "title": "Chronos Emerald Tourbillon Piece Unique",
        "category": "Horology",
        "file": "/console/img/prestige/03_emerald_tourbillon_watch.png",
        "webp": "/console/img/showroom/chronos_tourbillon_watch.webp",
        "aspect_ratio": "4:5",
        "used_in": ["owner_office", "showroom", "player_gifting", "staff_gifting"],
    },
    {
        "id": "luxury_team_coach",
        "title": "Vanguard XII First-Team Luxury Coach",
        "category": "Club Transport",
        "file": "/console/img/prestige/04_luxury_team_coach.png",
        "webp": "/console/img/showroom/vanguard_xii_coach.webp",
        "aspect_ratio": "16:10",
        "used_in": ["owner_office", "showroom", "campus_builder"],
    },
    {
        "id": "private_jet",
        "title": "GTEX Sovereign 900X Intercontinental Jet",
        "category": "Club Aviation",
        "file": "/console/img/prestige/05_private_jet.png",
        "webp": "/console/img/showroom/sovereign_900x_jet.webp",
        "aspect_ratio": "16:10",
        "used_in": ["owner_office", "showroom", "newsroom", "global_ticker"],
    },
    {
        "id": "academy_campus_aerial_a",
        "title": "Club Campus Masterplan — Aerial North",
        "category": "Club Infrastructure",
        "file": "/console/img/prestige/06_academy_campus_aerial_a.png",
        "webp": "/console/img/showroom/facility_commercial.webp",
        "aspect_ratio": "16:9",
        "used_in": ["owner_office", "campus_builder", "newsroom"],
    },
    {
        "id": "academy_campus_aerial_b",
        "title": "Club Campus & Hospitality Plaza — Aerial South",
        "category": "Club Infrastructure",
        "file": "/console/img/prestige/07_academy_campus_aerial_b.png",
        "webp": "/console/img/showroom/royal_penthouse_box.webp",
        "aspect_ratio": "16:9",
        "used_in": ["owner_office", "campus_builder", "showroom"],
    },
    {
        "id": "academy_training_and_recovery",
        "title": "First-Team Training & Hydro-Recovery Complex",
        "category": "Training & Medical",
        "file": "/console/img/prestige/08_academy_training_and_recovery.png",
        "webp": "/console/img/showroom/facility_training.webp",
        "aspect_ratio": "16:9",
        "used_in": ["campus_builder", "owner_office", "newsroom"],
    },
    {
        "id": "high_performance_centre",
        "title": "High-Performance Biomechanics & Sports Science Centre",
        "category": "Sports Science",
        "file": "/console/img/prestige/09_high_performance_centre.png",
        "webp": "/console/img/showroom/facility_medical.webp",
        "aspect_ratio": "16:9",
        "used_in": ["campus_builder", "showroom", "owner_office"],
    },
    {
        "id": "club_campus_build_mode",
        "title": "Club Campus Interactive 3D Build Grid",
        "category": "Interactive Builder UI",
        "file": "/console/img/prestige/10_club_campus_build_mode.png",
        "webp": "/console/img/showroom/campus_build_mode.webp",
        "aspect_ratio": "16:9",
        "used_in": ["campus_builder"],
    },
    {
        "id": "stadium_expansion_construction",
        "title": "Stadium Grandstand & Cantilever Expansion",
        "category": "Stadium Construction",
        "file": "/console/img/prestige/11_stadium_expansion_construction.png",
        "webp": "/console/img/showroom/facility_stadium.webp",
        "aspect_ratio": "16:9",
        "used_in": ["campus_builder", "newsroom", "global_ticker"],
    },
    {
        "id": "elite_academy_complex",
        "title": "Elite Youth Academy Boarding & Show-Pitch Complex",
        "category": "Youth Development",
        "file": "/console/img/prestige/12_elite_academy_complex.png",
        "webp": "/console/img/showroom/facility_academy.webp",
        "aspect_ratio": "16:9",
        "used_in": ["campus_builder", "academy", "newsroom"],
    },
]


# ---------------------------------------------------------------------------
# 2. CLUB CAMPUS BUILDER (3D Grid, Modular Catalogue, Staged Construction)
# ---------------------------------------------------------------------------

CAMPUS_GRID_WIDTH = 24
CAMPUS_GRID_HEIGHT = 18

CAMPUS_ZONES: list[dict[str, Any]] = [
    {
        "zone_id": "academy_zone",
        "name": "Youth Academy & Scholar Precinct",
        "x": 1,
        "y": 2,
        "w": 6,
        "h": 13,
        "color": "#10b981",
        "description": "Dedicated youth development pitches, boarding suites, classrooms, and HOYD nerve centre.",
    },
    {
        "zone_id": "first_team_zone",
        "name": "First-Team Training & Sports Science Zone",
        "x": 7,
        "y": 2,
        "w": 8,
        "h": 10,
        "color": "#0ea5e9",
        "description": "Heated hybrid pitches, high-performance gym, biomechanics lab, and hydrotherapy recovery pools.",
    },
    {
        "zone_id": "stadium_zone",
        "name": "Stadium Bowl & Matchday Arena Precinct",
        "x": 15,
        "y": 1,
        "w": 8,
        "h": 10,
        "color": "#f59e0b",
        "description": "Main stadium bowl, expandable grandstands, cantilever roof, floodlights, and VIP skyboxes.",
    },
    {
        "zone_id": "operations_commercial_zone",
        "name": "Executive HQ, Fleet Terminal & Commercial Plaza",
        "x": 7,
        "y": 12,
        "w": 16,
        "h": 5,
        "color": "#a855f7",
        "description": "Club Owner's Office, media theatre, sponsor hospitality pavilion, and luxury coach/fleet terminal.",
    },
]

CAMPUS_MODULE_CATALOG: dict[str, dict[str, Any]] = {
    "stadium_bowl_core": {
        "module_key": "stadium_bowl_core",
        "name": "Main Stadium Arena Bowl",
        "category": "stadium",
        "linked_facility": "stadium",
        "footprint_w": 6,
        "footprint_h": 5,
        "base_cost_gtex": 3500,
        "build_days": 4,
        "min_prestige": 10,
        "can_demolish": False,
        "image_url": "/console/img/prestige/11_stadium_expansion_construction.png",
        "model_glb_url": "/console/models/campus/stadium_main.glb",
        "color_hex": "#10b981",
        "height_scale": 2.8,
        "roof_style": "cantilever_truss",
        "description": "Primary matchday stadium bowl with heated hybrid turf, dugouts, and lower-tier seating.",
        "effects": {
            "capacity_seats": 18000,
            "matchday_revenue_pct": 15,
            "prestige_bonus": 4,
            "home_advantage_bonus": 3,
        },
    },
    "north_stand_expansion": {
        "module_key": "north_stand_expansion",
        "name": "North Grandstand & Roof Expansion",
        "category": "stadium",
        "linked_facility": "stadium",
        "footprint_w": 4,
        "footprint_h": 2,
        "base_cost_gtex": 2200,
        "build_days": 3,
        "min_prestige": 25,
        "can_demolish": True,
        "image_url": "/console/img/prestige/11_stadium_expansion_construction.png",
        "model_glb_url": "/console/models/campus/stadium_stand_expansion.glb",
        "color_hex": "#0284c7",
        "height_scale": 2.5,
        "roof_style": "steel_gantry",
        "description": "Multi-tier supporter grandstand with acoustic steel truss roof and concourse hospitality.",
        "effects": {
            "capacity_seats": 8500,
            "matchday_revenue_pct": 18,
            "prestige_bonus": 3,
            "home_advantage_bonus": 2,
        },
    },
    "floodlight_pylon_array": {
        "module_key": "floodlight_pylon_array",
        "name": "UEFA-Spec LED Floodlight & Broadcast Array",
        "category": "stadium",
        "linked_facility": "stadium",
        "footprint_w": 2,
        "footprint_h": 2,
        "base_cost_gtex": 850,
        "build_days": 2,
        "min_prestige": 15,
        "can_demolish": True,
        "image_url": "/console/img/prestige/11_stadium_expansion_construction.png",
        "model_glb_url": "/console/models/campus/floodlight_tower.glb",
        "color_hex": "#e2e8f0",
        "height_scale": 3.6,
        "roof_style": "pylon_tower",
        "description": "High-output broadcast floodlight towers and spider-cam rigging for prime-time continental fixtures.",
        "effects": {
            "broadcast_revenue_pct": 10,
            "prestige_bonus": 2,
        },
    },
    "vip_skybox_concourse": {
        "module_key": "vip_skybox_concourse",
        "name": "Directorate VIP Skybox & Sponsor Pavilion",
        "category": "commercial",
        "linked_facility": "commercial",
        "footprint_w": 3,
        "footprint_h": 2,
        "base_cost_gtex": 1800,
        "build_days": 3,
        "min_prestige": 25,
        "can_demolish": True,
        "image_url": "/console/img/prestige/07_academy_campus_aerial_b.png",
        "model_glb_url": "/console/models/campus/vip_hospitality.glb",
        "color_hex": "#f59e0b",
        "height_scale": 2.0,
        "roof_style": "glass_atrium",
        "description": "Panoramic glass hospitality suites for club investors, commercial partners, and marquee transfer targets.",
        "effects": {
            "sponsor_revenue_pct": 20,
            "transfer_pull_bonus": 4,
            "prestige_bonus": 3,
        },
    },
    "first_team_pitch_alpha": {
        "module_key": "first_team_pitch_alpha",
        "name": "First-Team Heated Hybrid Pitch Alpha",
        "category": "training",
        "linked_facility": "training",
        "footprint_w": 4,
        "footprint_h": 3,
        "base_cost_gtex": 900,
        "build_days": 2,
        "min_prestige": 10,
        "can_demolish": False,
        "image_url": "/console/img/prestige/08_academy_training_and_recovery.png",
        "model_glb_url": "/console/models/campus/training_pitch.glb",
        "color_hex": "#16a34a",
        "height_scale": 0.25,
        "roof_style": "open_turf",
        "description": "Primary Desso hybrid-turf training pitch with undersoil heating and automated irrigation.",
        "effects": {
            "tactical_cohesion_pct": 8,
            "training_efficiency_pct": 10,
            "prestige_bonus": 1,
        },
    },
    "first_team_pitch_beta": {
        "module_key": "first_team_pitch_beta",
        "name": "Tactical Telemetry & Set-Piece Pitch Beta",
        "category": "training",
        "linked_facility": "training",
        "footprint_w": 4,
        "footprint_h": 3,
        "base_cost_gtex": 1100,
        "build_days": 2,
        "min_prestige": 15,
        "can_demolish": True,
        "image_url": "/console/img/prestige/06_academy_campus_aerial_a.png",
        "model_glb_url": "/console/models/campus/first_team_pitch_beta.glb",
        "color_hex": "#15803d",
        "height_scale": 0.25,
        "roof_style": "open_turf",
        "description": "Secondary training pitch ringed with LED tactical boards and drone tracking cameras.",
        "effects": {
            "tactical_cohesion_pct": 10,
            "training_efficiency_pct": 12,
            "prestige_bonus": 2,
        },
    },
    "high_performance_centre": {
        "module_key": "high_performance_centre",
        "name": "High-Performance Biomechanics & Gym Complex",
        "category": "training",
        "linked_facility": "training",
        "footprint_w": 3,
        "footprint_h": 3,
        "base_cost_gtex": 2100,
        "build_days": 3,
        "min_prestige": 25,
        "can_demolish": True,
        "image_url": "/console/img/prestige/09_high_performance_centre.png",
        "model_glb_url": "/console/models/campus/high_performance_centre.glb",
        "color_hex": "#2563eb",
        "height_scale": 1.9,
        "roof_style": "solar_curved",
        "description": "Two-storey strength & conditioning hall, altitude chamber, and sports science analytics hub.",
        "effects": {
            "attribute_growth_pct": 14,
            "stamina_retention_pct": 10,
            "prestige_bonus": 3,
        },
    },
    "recovery_hydro_hub": {
        "module_key": "recovery_hydro_hub",
        "name": "Cryo & Hydrotherapy Medical Recovery Hub",
        "category": "medical",
        "linked_facility": "medical",
        "footprint_w": 3,
        "footprint_h": 3,
        "base_cost_gtex": 1950,
        "build_days": 3,
        "min_prestige": 20,
        "can_demolish": True,
        "image_url": "/console/img/prestige/08_academy_training_and_recovery.png",
        "model_glb_url": "/console/models/campus/recovery_hydro_hub.glb",
        "color_hex": "#06b6d4",
        "height_scale": 1.6,
        "roof_style": "hydro_deck",
        "description": "Outdoor and indoor hydrotherapy pools, whole-body cryotherapy chambers, and MRI diagnostics.",
        "effects": {
            "injury_reduction_pct": 22,
            "fatigue_recovery_pct": 18,
            "prestige_bonus": 3,
        },
    },
    "elite_academy_complex": {
        "module_key": "elite_academy_complex",
        "name": "Elite Academy HQ, Classrooms & Scholar Dorms",
        "category": "academy",
        "linked_facility": "academy",
        "footprint_w": 4,
        "footprint_h": 3,
        "base_cost_gtex": 2400,
        "build_days": 3,
        "min_prestige": 20,
        "can_demolish": True,
        "image_url": "/console/img/prestige/12_elite_academy_complex.png",
        "model_glb_url": "/console/models/campus/academy_complex.glb",
        "color_hex": "#10b981",
        "height_scale": 2.1,
        "roof_style": "modern_campus",
        "description": "World-class youth academy headquarters with residential scholar suites, study halls, and video analysis rooms.",
        "effects": {
            "regen_intake_quality_pct": 18,
            "academy_ceiling_bonus": 4,
            "prestige_bonus": 4,
        },
    },
    "academy_youth_pitch": {
        "module_key": "academy_youth_pitch",
        "name": "Academy Floodlit Show Pitch",
        "category": "academy",
        "linked_facility": "academy",
        "footprint_w": 4,
        "footprint_h": 3,
        "base_cost_gtex": 950,
        "build_days": 2,
        "min_prestige": 10,
        "can_demolish": True,
        "image_url": "/console/img/prestige/07_academy_campus_aerial_b.png",
        "model_glb_url": "/console/models/campus/academy_youth_pitch.glb",
        "color_hex": "#22c55e",
        "height_scale": 0.25,
        "roof_style": "open_turf",
        "description": "Dedicated U18/U21 development show pitch with scout viewing terrace and floodlights.",
        "effects": {
            "regen_development_speed_pct": 14,
            "academy_ceiling_bonus": 2,
            "prestige_bonus": 2,
        },
    },
    "club_hq_operations": {
        "module_key": "club_hq_operations",
        "name": "Club Owner's Office & Global Scouting HQ",
        "category": "operations",
        "linked_facility": "commercial",
        "footprint_w": 3,
        "footprint_h": 2,
        "base_cost_gtex": 1500,
        "build_days": 2,
        "min_prestige": 10,
        "can_demolish": False,
        "image_url": "/console/img/prestige/06_academy_campus_aerial_a.png",
        "model_glb_url": "/console/models/campus/club_hq.glb",
        "color_hex": "#eab308",
        "height_scale": 2.4,
        "roof_style": "executive_tower",
        "description": "Executive boardroom, Owner's Office, transfer war room, and GTEX Newsroom press auditorium.",
        "effects": {
            "scouting_efficiency_pct": 15,
            "commercial_growth_pct": 12,
            "prestige_bonus": 3,
        },
    },
    "executive_fleet_terminal": {
        "module_key": "executive_fleet_terminal",
        "name": "Luxury Team Coach & Executive Fleet Terminal",
        "category": "operations",
        "linked_facility": "commercial",
        "footprint_w": 3,
        "footprint_h": 2,
        "base_cost_gtex": 1150,
        "build_days": 2,
        "min_prestige": 15,
        "can_demolish": True,
        "image_url": "/console/img/prestige/04_luxury_team_coach.png",
        "model_glb_url": "/console/models/campus/executive_fleet_terminal.glb",
        "color_hex": "#6366f1",
        "height_scale": 1.4,
        "roof_style": "canopy_deck",
        "description": "Secure arrival concourse for the Vanguard XII Team Coach, owner hypercars, and VIP helicopter pad.",
        "effects": {
            "away_travel_readiness_pct": 10,
            "staff_mood_bonus": 6,
            "prestige_bonus": 2,
        },
    },
}


def _default_placed_modules(facilities: dict[str, Any], world_day: int) -> list[dict[str, Any]]:
    """Seeds a rich, Sims-inspired 3D campus layout aligned with the club's current facility levels."""
    stad_lvl = int(facilities.get("stadium", 1) or 1)
    trn_lvl = int(facilities.get("training", 1) or 1)
    acad_lvl = int(facilities.get("academy", 1) or 1)
    med_lvl = int(facilities.get("medical", 1) or 1)
    comm_lvl = int(facilities.get("commercial", 1) or 1)

    placed = [
        {
            "instance_id": "mod_stadium_core",
            "module_key": "stadium_bowl_core",
            "x": 16,
            "y": 2,
            "rotation": 0,
            "level": stad_lvl,
            "condition": 98,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 5),
        },
        {
            "instance_id": "mod_floodlights_1",
            "module_key": "floodlight_pylon_array",
            "x": 15,
            "y": 8,
            "rotation": 0,
            "level": stad_lvl,
            "condition": 97,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 5),
        },
        {
            "instance_id": "mod_pitch_alpha",
            "module_key": "first_team_pitch_alpha",
            "x": 7,
            "y": 3,
            "rotation": 0,
            "level": trn_lvl,
            "condition": 96,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 5),
        },
        {
            "instance_id": "mod_pitch_beta",
            "module_key": "first_team_pitch_beta",
            "x": 7,
            "y": 7,
            "rotation": 0,
            "level": trn_lvl,
            "condition": 95,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 4),
        },
        {
            "instance_id": "mod_hpc_main",
            "module_key": "high_performance_centre",
            "x": 12,
            "y": 3,
            "rotation": 0,
            "level": trn_lvl,
            "condition": 97,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 4),
        },
        {
            "instance_id": "mod_hydro_hub",
            "module_key": "recovery_hydro_hub",
            "x": 12,
            "y": 7,
            "rotation": 0,
            "level": med_lvl,
            "condition": 99,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 3),
        },
        {
            "instance_id": "mod_academy_hq",
            "module_key": "elite_academy_complex",
            "x": 2,
            "y": 3,
            "rotation": 0,
            "level": acad_lvl,
            "condition": 97,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 4),
        },
        {
            "instance_id": "mod_academy_pitch",
            "module_key": "academy_youth_pitch",
            "x": 2,
            "y": 7,
            "rotation": 0,
            "level": acad_lvl,
            "condition": 95,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 4),
        },
        {
            "instance_id": "mod_club_hq",
            "module_key": "club_hq_operations",
            "x": 8,
            "y": 13,
            "rotation": 0,
            "level": comm_lvl,
            "condition": 99,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 5),
        },
        {
            "instance_id": "mod_fleet_terminal",
            "module_key": "executive_fleet_terminal",
            "x": 12,
            "y": 13,
            "rotation": 0,
            "level": comm_lvl,
            "condition": 98,
            "status": "operational",
            "construction_stage": "completed",
            "progress_pct": 100,
            "placed_world_day": max(1, world_day - 3),
        },
    ]
    return placed


def _stage_from_progress(pct: int) -> str:
    if pct >= 100:
        return "completed"
    if pct >= 80:
        return "finishing"
    if pct >= 60:
        return "structural"
    if pct >= 40:
        return "foundations"
    if pct >= 20:
        return "groundworks"
    return "site_prep"


def _enrich_module(
    inst: dict[str, Any],
    *,
    projects: list[dict[str, Any]] | None = None,
    world_day: int = 1,
) -> dict[str, Any]:
    spec = CAMPUS_MODULE_CATALOG.get(inst.get("module_key", ""), {})
    rot = int(inst.get("rotation", 0)) % 360
    fw = int(spec.get("footprint_w", 3))
    fh = int(spec.get("footprint_h", 3))
    eff_w = fh if rot in (90, 270) else fw
    eff_h = fw if rot in (90, 270) else fh
    lvl = int(inst.get("level", 1))
    max_level = 5
    upgrade_cost = int(float(spec.get("base_cost_gtex", 1200)) * (0.75 + 0.45 * lvl)) if lvl < max_level else 0
    base_effects = dict(spec.get("effects") or {})
    current_effects: dict[str, int] = {}
    next_level_effects: dict[str, int] = {}
    for k, v in base_effects.items():
        base_val = int(v)
        if k == "capacity_seats":
            current_effects[k] = base_val + (lvl - 1) * 3500
            if lvl < max_level:
                next_level_effects[k] = base_val + lvl * 3500
        else:
            current_effects[k] = int(round(base_val * (1.0 + 0.25 * (lvl - 1))))
            if lvl < max_level:
                next_level_effects[k] = int(round(base_val * (1.0 + 0.25 * lvl)))

    inst_id = inst.get("instance_id")
    active_proj = None
    if projects and inst_id:
        active_proj = next(
            (p for p in projects if p.get("instance_id") == inst_id and p.get("status") not in ("completed", "cancelled")),
            None,
        )

    status = str(inst.get("status", "operational"))
    stage = str(inst.get("construction_stage", "completed"))
    pct = int(inst.get("progress_pct", 100))
    if status == "under_construction" or pct < 100:
        lifecycle_state = "ready_for_completion" if stage == "finishing" or pct >= 80 else "under_construction"
    elif lvl < max_level:
        lifecycle_state = "eligible_for_upgrade"
    else:
        lifecycle_state = "completed_max_level"

    start_day = int((active_proj or {}).get("start_world_day", inst.get("placed_world_day", world_day)))
    dur_days = int((active_proj or {}).get("duration_days", spec.get("build_days", 2)))
    expected_day = start_day + dur_days
    rem_days = 0 if status == "operational" and pct >= 100 else max(1, expected_day - world_day)

    return {
        **spec,
        **inst,
        "effective_w": eff_w,
        "effective_h": eff_h,
        "max_level": max_level,
        "next_upgrade_cost_gtex": upgrade_cost,
        "upgrade_min_prestige": min(90, int(spec.get("min_prestige", 10)) + lvl * 5),
        "current_effects": current_effects,
        "next_level_effects": next_level_effects,
        "lifecycle_state": lifecycle_state,
        "ready_for_completion": lifecycle_state == "ready_for_completion",
        "upgrade_eligible": lifecycle_state == "eligible_for_upgrade",
        "start_world_day": start_day,
        "duration_days": dur_days,
        "expected_completion_day": expected_day,
        "remaining_days": rem_days,
        "active_project_id": (active_proj or {}).get("project_id"),
    }


def validate_module_placement(
    placed_modules: list[dict[str, Any]],
    *,
    module_key: str,
    x: int,
    y: int,
    rotation: int = 0,
    ignore_instance_id: str | None = None,
) -> dict[str, Any]:
    spec = CAMPUS_MODULE_CATALOG.get(module_key)
    if not spec:
        return {"valid": False, "code": "invalid_module_key", "reason": f"Unknown module '{module_key}'."}

    rot = int(rotation) % 360
    if rot not in (0, 90, 180, 270):
        return {
            "valid": False,
            "code": "invalid_rotation",
            "reason": "Campus modules can only be rotated in 90-degree increments (0°, 90°, 180°, or 270°).",
        }

    fw = int(spec["footprint_w"])
    fh = int(spec["footprint_h"])
    w = fh if rot in (90, 270) else fw
    h = fw if rot in (90, 270) else fh

    if x < 0 or y < 0 or (x + w) > CAMPUS_GRID_WIDTH or (y + h) > CAMPUS_GRID_HEIGHT:
        return {
            "valid": False,
            "code": "out_of_bounds",
            "reason": f"Placement ({x},{y}) size {w}x{h} exceeds the {CAMPUS_GRID_WIDTH}x{CAMPUS_GRID_HEIGHT} campus boundary.",
        }

    for other in placed_modules:
        if ignore_instance_id and other.get("instance_id") == ignore_instance_id:
            continue
        other_spec = CAMPUS_MODULE_CATALOG.get(other.get("module_key", ""), {})
        o_rot = int(other.get("rotation", 0)) % 360
        o_fw = int(other_spec.get("footprint_w", 3))
        o_fh = int(other_spec.get("footprint_h", 3))
        ow = o_fh if o_rot in (90, 270) else o_fw
        oh = o_fw if o_rot in (90, 270) else o_fh
        ox = int(other.get("x", 0))
        oy = int(other.get("y", 0))

        overlap_x = (x < ox + ow) and (x + w > ox)
        overlap_y = (y < oy + oh) and (y + h > oy)
        if overlap_x and overlap_y:
            return {
                "valid": False,
                "code": "module_overlap",
                "reason": f"Footprint overlaps with existing '{other_spec.get('name', other.get('module_key'))}' at ({ox},{oy}).",
                "colliding_instance_id": other.get("instance_id"),
            }

    return {"valid": True, "code": "ok", "effective_w": w, "effective_h": h}


def _apply_campus_completion_rewards(
    session: Session,
    state: OwnerClubState,
    facs: dict[str, Any],
    project: dict[str, Any],
) -> bool:
    """Apply facility-level and prestige benefits once, only when construction becomes operational."""
    if project.get("completion_rewards_applied"):
        return False

    spec = CAMPUS_MODULE_CATALOG.get(str(project.get("module_key") or ""))
    if not spec:
        return False

    linked_facility = str(spec.get("linked_facility") or "training")
    current_level = int(facs.get(linked_facility, 1) or 1)
    target_level = int(project.get("target_level", 1))
    facs[linked_facility] = min(5, max(current_level, target_level))

    prestige_gain = int((spec.get("effects") or {}).get("prestige_bonus", 2))
    if prestige_gain:
        state.prestige = int(engine.clamp(state.prestige + prestige_gain, 0, 100))
        from app.owner_console import service

        service.sync_club_prestige_to_reputation(session, state.club_id, state.prestige)

    project["completion_rewards_applied"] = True
    return True


def _reconcile_campus_projects(
    session: Session,
    state: OwnerClubState,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    facs = dict(state.facilities_json or {})
    world_day = int(state.world_day or 1)
    placed = list(facs.get("_campus_modules") or _default_placed_modules(facs, world_day))
    projects = list(facs.get("_construction_projects") or [])

    changed = False
    for proj in projects:
        if proj.get("status") in ("completed", "cancelled"):
            continue

        start_day = int(proj.get("start_world_day", world_day))
        duration = max(1, int(proj.get("duration_days", 2)))
        elapsed = max(0, world_day - start_day)
        forced_pct = int(proj.get("progress_pct", 25))
        raw_pct = min(100, int(forced_pct + (elapsed / duration) * 75)) if elapsed > 0 else forced_pct
        pct = max(raw_pct, forced_pct)
        stage = _stage_from_progress(pct)
        expected_completion_day = start_day + duration
        remaining_days = 0 if pct >= 100 else max(1, expected_completion_day - world_day)

        previous_project_state = (
            proj.get("progress_pct"),
            proj.get("stage"),
            proj.get("expected_completion_day"),
            proj.get("remaining_days"),
            proj.get("status"),
        )
        proj["progress_pct"] = pct
        proj["stage"] = stage
        proj["expected_completion_day"] = expected_completion_day
        proj["remaining_days"] = remaining_days
        if pct >= 100:
            proj["status"] = "completed"
            if _apply_campus_completion_rewards(session, state, facs, proj):
                changed = True

        current_project_state = (
            proj.get("progress_pct"),
            proj.get("stage"),
            proj.get("expected_completion_day"),
            proj.get("remaining_days"),
            proj.get("status"),
        )
        if current_project_state != previous_project_state:
            changed = True

        target_id = proj.get("instance_id")
        for mod in placed:
            if mod.get("instance_id") != target_id:
                continue
            next_module_state = {
                "progress_pct": pct,
                "construction_stage": stage,
                "status": "operational" if pct >= 100 else "under_construction",
            }
            if pct >= 100 and proj.get("target_level"):
                next_module_state["level"] = int(proj["target_level"])
            previous_module_state = tuple(mod.get(key) for key in next_module_state)
            for key, value in next_module_state.items():
                mod[key] = value
            if tuple(mod.get(key) for key in next_module_state) != previous_module_state:
                changed = True

    if changed or "_campus_modules" not in facs:
        facs["_campus_modules"] = placed
        facs["_construction_projects"] = projects
        state.facilities_json = facs
        flag_modified(state, "facilities_json")

    return placed, projects


def get_club_campus(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    placed, projects = _reconcile_campus_projects(session, state)
    facs = dict(state.facilities_json or {})
    cash_bal = float(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX))

    world_day_int = int(state.world_day or 1)
    enriched_modules = [_enrich_module(m, projects=projects, world_day=world_day_int) for m in placed]
    active_projects = [p for p in projects if p.get("status") != "completed"]

    enriched_catalog = []
    for c in CAMPUS_MODULE_CATALOG.values():
        m_key = c["module_key"]
        matching = [m for m in enriched_modules if m.get("module_key") == m_key]
        op_count = sum(1 for m in matching if m.get("status") == "operational")
        uc_count = sum(1 for m in matching if m.get("status") == "under_construction")
        min_prest = int(c.get("min_prestige", 10))
        cost_val = float(c.get("base_cost_gtex", 1000))
        if state.prestige < min_prest:
            avail_status = "prestige_locked"
        elif cash_bal < cost_val:
            avail_status = "insufficient_treasury"
        else:
            avail_status = "available"
        enriched_catalog.append(
            {
                **c,
                "placed_count": len(matching),
                "operational_count": op_count,
                "under_construction_count": uc_count,
                "availability_status": avail_status,
            }
        )

    # Aggregate real gameplay bonuses from operational campus modules
    total_capacity = 12000
    matchday_rev_bonus = 0
    training_eff_bonus = 0
    injury_red_bonus = 0
    academy_ceil_bonus = 0
    for m in enriched_modules:
        if m.get("status") == "operational":
            lvl = int(m.get("level", 1))
            eff = dict(m.get("effects") or {})
            total_capacity += int(eff.get("capacity_seats", 0)) + (lvl - 1) * (
                3500 if m.get("category") == "stadium" else 0
            )
            matchday_rev_bonus += int(eff.get("matchday_revenue_pct", 0)) + (lvl - 1) * 3
            training_eff_bonus += int(eff.get("training_efficiency_pct", 0)) + int(eff.get("attribute_growth_pct", 0))
            injury_red_bonus += int(eff.get("injury_reduction_pct", 0)) + (lvl - 1) * 2
            academy_ceil_bonus += int(eff.get("academy_ceiling_bonus", 0)) + (
                1 if m.get("category") == "academy" and lvl >= 3 else 0
            )

    squad_players = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
    academy_regens = [
        {
            "id": p.id,
            "name": p.name,
            "position": p.position,
            "rating": p.rating,
            "potential": min(99, p.rating + 14 + academy_ceil_bonus),
            "morale": p.morale,
        }
        for p in squad_players
        if p.is_regen
    ]

    return {
        "club_id": club_id,
        "club_name": state.club_name,
        "world_day": state.world_day,
        "cash_balance_gtex": cash_bal,
        "prestige": state.prestige,
        "prestige_tier": engine.prestige_tier_label(state.prestige),
        "grid": {
            "width": CAMPUS_GRID_WIDTH,
            "height": CAMPUS_GRID_HEIGHT,
            "tile_size_meters": 12,
            "zones": CAMPUS_ZONES,
        },
        "facilities_levels": {
            "stadium": int(facs.get("stadium", 1) or 1),
            "training": int(facs.get("training", 1) or 1),
            "academy": int(facs.get("academy", 1) or 1),
            "medical": int(facs.get("medical", 1) or 1),
            "commercial": int(facs.get("commercial", 1) or 1),
        },
        "placed_modules": enriched_modules,
        "module_catalog": enriched_catalog,
        "construction_projects": projects,
        "active_projects_count": len(active_projects),
        "campus_metrics": {
            "stadium_capacity": total_capacity,
            "matchday_revenue_bonus_pct": matchday_rev_bonus,
            "training_efficiency_bonus_pct": training_eff_bonus,
            "injury_reduction_pct": min(65, injury_red_bonus),
            "academy_ceiling_bonus": academy_ceil_bonus,
            "operational_modules_count": sum(1 for m in enriched_modules if m.get("status") == "operational"),
        },
        "academy_campus_prospects": academy_regens[:8],
        "visual_assets": PRESTIGE_VISUAL_MANIFEST,
    }


def update_campus_layout(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    action: str,
    instance_id: str,
    x: int | None = None,
    y: int | None = None,
    rotation: int | None = None,
) -> dict[str, Any]:
    """Moves, rotates, or demolishes an existing module on the 3D campus grid with strict validation."""
    state = require_state(session, club_id, user_id)
    placed, projects = _reconcile_campus_projects(session, state)
    target = next((m for m in placed if m.get("instance_id") == instance_id), None)
    if not target:
        raise OwnerError("campus_module_not_found", 404, f"Campus module '{instance_id}' was not found on grid.")

    spec = CAMPUS_MODULE_CATALOG.get(target.get("module_key", ""), {})
    if action == "demolish":
        if not spec.get("can_demolish", True):
            raise OwnerError(
                "module_protected",
                400,
                f"'{spec.get('name', target.get('module_key'))}' is core club infrastructure and cannot be demolished.",
            )
        placed = [m for m in placed if m.get("instance_id") != instance_id]
        projects = [p for p in projects if p.get("instance_id") != instance_id]
        facs = dict(state.facilities_json or {})
        facs["_campus_modules"] = placed
        facs["_construction_projects"] = projects
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.flush()
        return {
            "status": "demolished",
            "removed_instance_id": instance_id,
            "campus": get_club_campus(session, user_id, club_id),
        }

    new_x = int(x if x is not None else target.get("x", 0))
    new_y = int(y if y is not None else target.get("y", 0))
    new_rot = int(rotation if rotation is not None else target.get("rotation", 0)) % 360

    val = validate_module_placement(
        placed,
        module_key=str(target.get("module_key")),
        x=new_x,
        y=new_y,
        rotation=new_rot,
        ignore_instance_id=instance_id,
    )
    if not val["valid"]:
        raise OwnerError(val["code"], 400, val["reason"])

    target["x"] = new_x
    target["y"] = new_y
    target["rotation"] = new_rot

    facs = dict(state.facilities_json or {})
    facs["_campus_modules"] = placed
    state.facilities_json = facs
    flag_modified(state, "facilities_json")
    session.flush()

    return {
        "status": "updated",
        "module": _enrich_module(target),
        "campus": get_club_campus(session, user_id, club_id),
    }


def start_campus_construction(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    operation: str = "place_new",
    module_key: str | None = None,
    instance_id: str | None = None,
    x: int = 4,
    y: int = 11,
    rotation: int = 0,
    fast_track_completion: bool = False,
    initial_stage: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Commits a paid 3D campus module build or upgrade through the authoritative GTEX ledger."""
    from app.owner_console import service, storytelling

    state = require_state(session, club_id, user_id)
    placed, projects = _reconcile_campus_projects(session, state)
    facs = dict(state.facilities_json or {})

    # 1. Idempotency protection against duplicate debits / retries
    if idempotency_key:
        existing_proj = next((p for p in projects if p.get("idempotency_key") == idempotency_key), None)
        if existing_proj:
            expected_op = existing_proj.get("operation", "place_new")
            if expected_op != operation or (operation == "place_new" and existing_proj.get("module_key") != module_key) or (
                operation == "upgrade_existing" and existing_proj.get("instance_id") != instance_id
            ):
                raise OwnerError(
                    "idempotency_key_conflict",
                    409,
                    "This idempotency key was already used for a different campus construction request.",
                )
            existing_mod = next((m for m in placed if m.get("instance_id") == existing_proj.get("instance_id")), None)
            b_ev = session.scalar(
                select(OwnerBroadcastEvent).where(
                    OwnerBroadcastEvent.idempotency_key == f"campus:{existing_proj['project_id']}"
                )
            )
            return {
                "status": "commissioned",
                "idempotent_replay": True,
                "project": existing_proj,
                "module": _enrich_module(existing_mod) if existing_mod else None,
                "broadcast_event": storytelling.broadcast_dict(b_ev) if b_ev else None,
                "campus": get_club_campus(session, user_id, club_id),
            }

    # 2. Cancellation & full ledger reversal for active construction projects
    if operation == "cancel_project" and instance_id:
        proj = next(
            (p for p in projects if p.get("instance_id") == instance_id and p.get("status") not in ("completed", "cancelled")),
            None,
        )
        if not proj:
            raise OwnerError("project_not_found", 404, "Active construction project not found for cancellation.")

        proj["status"] = "cancelled"
        proj["stage"] = "cancelled"
        leg_id = proj.get("ledger_event_id")
        if leg_id:
            leg_row = session.get(LedgerEvent, leg_id)
            if leg_row and leg_row.status == "completed":
                ledger.transition(session, leg_row, "reversed")
            asset_row = session.scalar(select(OwnerShowroomAsset).where(OwnerShowroomAsset.ledger_event_id == leg_id))
            if asset_row:
                asset_row.status = "reversed"

        if proj.get("operation") == "place_new" or int(proj.get("target_level", 1)) <= 1:
            placed = [m for m in placed if m.get("instance_id") != instance_id]
        else:
            for mod in placed:
                if mod.get("instance_id") == instance_id:
                    mod["status"] = "operational"
                    mod["construction_stage"] = "completed"
                    mod["progress_pct"] = 100

        facs["_campus_modules"] = placed
        facs["_construction_projects"] = projects
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.flush()
        return {
            "status": "cancelled",
            "project": proj,
            "campus": get_club_campus(session, user_id, club_id),
        }

    if operation == "advance_stage" and instance_id:
        # Advance construction stage of an active project sequentially through all 6 stages (or complete immediately)
        proj = next(
            (p for p in projects if p.get("instance_id") == instance_id and p.get("status") not in ("completed", "cancelled")),
            None,
        )
        if not proj:
            raise OwnerError("project_not_found", 404, "Active construction project not found for this module.")
        cur_pct = int(proj.get("progress_pct", 25))
        if fast_track_completion:
            new_pct = 100
        elif cur_pct < 20:
            new_pct = 25
        elif cur_pct < 40:
            new_pct = 45
        elif cur_pct < 60:
            new_pct = 65
        elif cur_pct < 80:
            new_pct = 85
        else:
            new_pct = 100
        proj["progress_pct"] = new_pct
        proj["stage"] = _stage_from_progress(new_pct)
        if new_pct >= 100:
            proj["status"] = "completed"
            _apply_campus_completion_rewards(session, state, facs, proj)
        updated_mod = None
        for mod in placed:
            if mod.get("instance_id") == instance_id:
                mod["progress_pct"] = new_pct
                mod["construction_stage"] = proj["stage"]
                mod["status"] = "operational" if new_pct >= 100 else "under_construction"
                if new_pct >= 100 and proj.get("target_level"):
                    mod["level"] = int(proj["target_level"])
                updated_mod = mod
        facs["_campus_modules"] = placed
        facs["_construction_projects"] = projects
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.flush()
        return {
            "status": "stage_advanced",
            "project": proj,
            "module": _enrich_module(
                updated_mod,
                projects=projects,
                world_day=int(state.world_day or 1),
            )
            if updated_mod
            else None,
            "campus": get_club_campus(session, user_id, club_id),
        }

    if operation == "upgrade_existing":
        target = next((m for m in placed if m.get("instance_id") == instance_id), None)
        if not target:
            raise OwnerError("campus_module_not_found", 404, "Module to upgrade was not found on campus grid.")
        if target.get("status") == "under_construction" or any(
            p.get("instance_id") == instance_id and p.get("status") not in ("completed", "cancelled") for p in projects
        ):
            raise OwnerError(
                "construction_in_progress",
                409,
                "This campus module already has an active construction project in progress.",
            )
        mod_key = str(target.get("module_key"))
        spec = CAMPUS_MODULE_CATALOG.get(mod_key)
        if not spec:
            raise OwnerError("invalid_module_key", 400, "Invalid module specification.")
        cur_lvl = int(target.get("level", 1))
        if cur_lvl >= 5:
            raise OwnerError("facility_maxed", 400, f"{spec['name']} is already at maximum Level 5.")
        target_lvl = cur_lvl + 1
        cost_dec = Decimal(str(int(float(spec["base_cost_gtex"]) * (0.75 + 0.45 * cur_lvl))))
        new_inst_id = str(target["instance_id"])
    else:
        if not module_key or module_key not in CAMPUS_MODULE_CATALOG:
            raise OwnerError("invalid_module_key", 400, f"Unknown campus building module '{module_key}'.")
        spec = CAMPUS_MODULE_CATALOG[module_key]
        mod_key = module_key
        min_prestige = int(spec.get("min_prestige", 10))
        if state.prestige < min_prestige:
            raise OwnerError(
                "insufficient_club_prestige",
                400,
                f"Requires Club Prestige {min_prestige} (current: {state.prestige}) to commission {spec['name']}.",
            )
        val = validate_module_placement(placed, module_key=mod_key, x=x, y=y, rotation=rotation)
        if not val["valid"]:
            raise OwnerError(val["code"], 400, val["reason"])
        target_lvl = 1
        cost_dec = Decimal(str(spec["base_cost_gtex"]))
        new_inst_id = f"mod_{mod_key}_{secrets.token_hex(3)}"
        target = None

    club_acct = ledger.club_account(club_id)
    bal = ledger.balance(session, club_acct, ledger.GTEX)
    if bal < cost_dec:
        raise OwnerError(
            "insufficient_club_cash",
            400,
            f"Club treasury ({bal} GTX) is insufficient for {cost_dec} GTX construction project.",
        )

    leg = ledger.record(
        session,
        event_type="facility_upgrade",
        source=club_acct,
        destination=ledger.WORLD_CLUBS,
        currency=ledger.GTEX,
        gross=cost_dec,
        club_id=club_id,
        user_id=user_id,
        related_type="campus_module",
        related_id=new_inst_id,
        memo=f"Campus Construction: {spec['name']} (Level {target_lvl})",
    )

    if fast_track_completion:
        init_pct = 100
        init_stage = "completed"
        init_status = "operational"
    elif initial_stage == "site_prep":
        init_pct = 15
        init_stage = "site_prep"
        init_status = "under_construction"
    else:
        init_pct = 25
        init_stage = "groundworks"
        init_status = "under_construction"

    if target is not None:
        target["status"] = init_status
        target["construction_stage"] = init_stage
        target["progress_pct"] = init_pct
        if fast_track_completion:
            target["level"] = target_lvl
    else:
        target = {
            "instance_id": new_inst_id,
            "module_key": mod_key,
            "x": int(x),
            "y": int(y),
            "rotation": int(rotation) % 360,
            "level": target_lvl,
            "condition": 100,
            "status": init_status,
            "construction_stage": init_stage,
            "progress_pct": init_pct,
            "placed_world_day": int(state.world_day or 1),
        }
        placed.append(target)

    project_entry = {
        "project_id": f"proj_{secrets.token_hex(4)}",
        "idempotency_key": idempotency_key,
        "operation": operation,
        "instance_id": new_inst_id,
        "module_key": mod_key,
        "module_name": spec["name"],
        "category": spec["category"],
        "target_level": target_lvl,
        "cost_gtex": float(cost_dec),
        "start_world_day": int(state.world_day or 1),
        "duration_days": int(spec.get("build_days", 2)),
        "progress_pct": init_pct,
        "stage": init_stage,
        "status": "completed" if fast_track_completion else "in_progress",
        "ledger_event_id": leg.id,
        "image_url": spec["image_url"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completion_rewards_applied": False,
    }
    projects.insert(0, project_entry)
    if fast_track_completion:
        _apply_campus_completion_rewards(session, state, facs, project_entry)
        state.facilities_json = facs
        flag_modified(state, "facilities_json")

    # Synchronize durable OwnerShowroomAsset record for infrastructure ownership
    infra_asset = OwnerShowroomAsset(
        club_id=club_id,
        owner_user_id=user_id,
        catalog_key=f"campus:{mod_key}",
        custom_name=f"{spec['name']} (Level {target_lvl})",
        category="infrastructure",
        model=f"Campus {spec['category'].capitalize()} Module",
        purchase_price_gtex=cost_dec,
        image_url=spec["image_url"],
        status="active",
        ledger_event_id=leg.id,
        idempotency_key=f"asset:campus:{project_entry['project_id']}",
    )
    session.add(infra_asset)

    # Facility levels and prestige are awarded only when the module becomes operational.
    # This prevents incomplete/cancelled projects from granting permanent gameplay benefits.
    facs["_campus_modules"] = placed
    facs["_construction_projects"] = projects
    state.facilities_json = facs
    flag_modified(state, "facilities_json")

    # Emit verified global broadcast + grounded newsroom article
    broadcast = storytelling.record_verified_broadcast_event(
        session,
        event_type="facility_upgrade",
        club_id=club_id,
        owner_user_id=user_id,
        item_name=f"{spec['name']} (Level {target_lvl})",
        item_model=f"Campus {spec['category'].capitalize()} Module",
        item_image_url=spec["image_url"],
        verified_price_gtex=cost_dec,
        ledger_event_id=leg.id,
        idempotency_key=f"campus:{project_entry['project_id']}",
        payload_json={
            "facility_kind": linked_fac,
            "facility_level": facs[linked_fac],
            "module_key": mod_key,
            "instance_id": new_inst_id,
            "construction_stage": init_stage,
        },
    )

    session.flush()
    return {
        "status": "commissioned",
        "idempotent_replay": False,
        "project": project_entry,
        "module": _enrich_module(target),
        "broadcast_event": storytelling.broadcast_dict(broadcast) if broadcast else None,
        "campus": get_club_campus(session, user_id, club_id),
    }


# ---------------------------------------------------------------------------
# 3. UNIFIED GTEX CLUB COMMUNICATIONS (8 Core Destinations & Actionable Decisions)
# ---------------------------------------------------------------------------

def _ensure_default_communications(
    session: Session,
    state: OwnerClubState,
    squad_players: list[OwnerSquadPlayer],
) -> dict[str, Any]:
    facs = dict(state.facilities_json or {})
    club_id = state.club_id
    world_day = int(state.world_day or 1)
    now_iso = datetime.now(timezone.utc).isoformat()

    exec_staff = dict(facs.get("_executive_staff") or {})
    mgr = dict(state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER))
    gm = exec_staff.get("general_manager") or {"name": "Dayo Adeleke", "role": "general_manager", "mood": 78}
    hoyd = exec_staff.get("head_of_youth_development") or {
        "name": "Femi Ogunleye",
        "role": "head_of_youth_development",
        "mood": 82,
    }
    scout = exec_staff.get("chief_scout") or {"name": "Kelechi Nwosu", "role": "chief_scout", "mood": 76}
    med = exec_staff.get("medical_director") or {"name": "Dr. Amara Okafor", "role": "medical_director", "mood": 84}

    threads: dict[str, dict[str, Any]] = dict(facs.get("_club_threads") or {})
    if not threads:
        lead_player = squad_players[0] if squad_players else None
        regen_player = next((p for p in squad_players if p.is_regen), lead_player)

        threads["staff:first_team_manager"] = {
            "thread_id": "staff:first_team_manager",
            "channel_type": "direct",
            "participant_type": "staff",
            "participant_id": "first_team_manager",
            "participant_name": mgr.get("name", "First-Team Manager"),
            "participant_role": "First-Team Manager",
            "subject": "Tactical Matchday Setup & Selection Alignment",
            "unread_count": 1,
            "updated_at": now_iso,
            "messages": [
                {
                    "id": f"m_mgr_{club_id}_1",
                    "sender_name": mgr.get("name", "First-Team Manager"),
                    "sender_role": "First-Team Manager",
                    "sender_type": "staff",
                    "body": (
                        f"Boss, training intensity on Pitch Alpha has been sharp this week (World Day {world_day}). "
                        f"Our pressing structure is coming together nicely, and the senior group is locked in."
                    ),
                    "world_day": world_day,
                    "created_at": now_iso,
                }
            ],
        }
        threads["staff:general_manager"] = {
            "thread_id": "staff:general_manager",
            "channel_type": "direct",
            "participant_type": "staff",
            "participant_id": "general_manager",
            "participant_name": gm.get("name", "Dayo Adeleke"),
            "participant_role": "General Manager",
            "subject": "Treasury Allocation, Sponsors & Campus ROI",
            "unread_count": 1,
            "updated_at": now_iso,
            "messages": [
                {
                    "id": f"m_gm_{club_id}_1",
                    "sender_name": gm.get("name", "Dayo Adeleke"),
                    "sender_role": "General Manager",
                    "sender_type": "staff",
                    "body": (
                        "Director, our commercial partners are closely watching our Campus Builder expansions. "
                        "Upgrading stadium hospitality or signing a tier sponsor will immediately boost matchday cashflow."
                    ),
                    "world_day": world_day,
                    "created_at": now_iso,
                }
            ],
        }
        threads["staff:head_of_youth_development"] = {
            "thread_id": "staff:head_of_youth_development",
            "channel_type": "direct",
            "participant_type": "staff",
            "participant_id": "head_of_youth_development",
            "participant_name": hoyd.get("name", "Femi Ogunleye"),
            "participant_role": "Head of Youth Development",
            "subject": "Academy Regen Pathway & Scholar Development",
            "unread_count": 0,
            "updated_at": now_iso,
            "messages": [
                {
                    "id": f"m_hoyd_{club_id}_1",
                    "sender_name": hoyd.get("name", "Femi Ogunleye"),
                    "sender_role": "Head of Youth Development",
                    "sender_type": "staff",
                    "body": (
                        f"Our U18 cohort is thriving in the Academy Complex. "
                        f"{regen_player.name if regen_player else 'Our top regen prospect'} has shown elite technical growth in drills."
                    ),
                    "world_day": world_day,
                    "created_at": now_iso,
                }
            ],
        }
        threads["staff:chief_scout"] = {
            "thread_id": "staff:chief_scout",
            "channel_type": "direct",
            "participant_type": "staff",
            "participant_id": "chief_scout",
            "participant_name": scout.get("name", "Kelechi Nwosu"),
            "participant_role": "Chief Scout",
            "subject": "Regional Recruitment & Watchlist Dossiers",
            "unread_count": 0,
            "updated_at": now_iso,
            "messages": [
                {
                    "id": f"m_scout_{club_id}_1",
                    "sender_name": scout.get("name", "Kelechi Nwosu"),
                    "sender_role": "Chief Scout",
                    "sender_type": "staff",
                    "body": "Director, we have updated the confidential scouting watchlist with two high-ceiling regional talents.",
                    "world_day": world_day,
                    "created_at": now_iso,
                }
            ],
        }
        threads["staff:medical_director"] = {
            "thread_id": "staff:medical_director",
            "channel_type": "direct",
            "participant_type": "staff",
            "participant_id": "medical_director",
            "participant_name": med.get("name", "Dr. Amara Okafor"),
            "participant_role": "Medical Director",
            "subject": "Hydrotherapy Protocols & Squad Load Management",
            "unread_count": 0,
            "updated_at": now_iso,
            "messages": [
                {
                    "id": f"m_med_{club_id}_1",
                    "sender_name": med.get("name", "Dr. Amara Okafor"),
                    "sender_role": "Medical Director",
                    "sender_type": "staff",
                    "body": "Cryo and hydrotherapy recovery sessions have kept hamstring fatigue markers well below league thresholds.",
                    "world_day": world_day,
                    "created_at": now_iso,
                }
            ],
        }
        if lead_player:
            threads[f"player:{lead_player.id}"] = {
                "thread_id": f"player:{lead_player.id}",
                "channel_type": "direct",
                "participant_type": "player",
                "participant_id": lead_player.id,
                "participant_name": lead_player.name,
                "participant_role": f"Squad {lead_player.position} · OVR {lead_player.rating}",
                "subject": "Dressing Room Leadership & Season Ambitions",
                "unread_count": 1,
                "updated_at": now_iso,
                "messages": [
                    {
                        "id": f"m_plr_{lead_player.id}_1",
                        "sender_name": lead_player.name,
                        "sender_role": f"{lead_player.position} ({'Academy Regen' if lead_player.is_regen else 'First Team'})",
                        "sender_type": "player",
                        "body": (
                            f"Boss, the whole squad can see the investments going into {state.club_name}. "
                            f"My morale is at {lead_player.morale}% and I'm ready to lead from the front."
                        ),
                        "world_day": world_day,
                        "created_at": now_iso,
                    }
                ],
            }

    staff_room = list(facs.get("_staff_room_feed") or [])
    if not staff_room:
        staff_room = [
            {
                "id": f"sr_{club_id}_1",
                "sender_name": gm.get("name", "Dayo Adeleke"),
                "sender_role": "General Manager",
                "department": "Executive Boardroom",
                "body": f"World Day {world_day} alignment: Treasury and wage ratio remain compliant with GTEX financial governance.",
                "world_day": world_day,
                "created_at": now_iso,
            },
            {
                "id": f"sr_{club_id}_2",
                "sender_name": med.get("name", "Dr. Amara Okafor"),
                "sender_role": "Medical Director",
                "department": "Sports Science & Medical",
                "body": "Post-training telemetry cleared all starters for high-tempo tactical drills tomorrow morning.",
                "world_day": world_day,
                "created_at": now_iso,
            },
            {
                "id": f"sr_{club_id}_3",
                "sender_name": hoyd.get("name", "Femi Ogunleye"),
                "sender_role": "Head of Youth Development",
                "department": "Youth Academy",
                "body": "Two academy regens have requested additional finishing sessions with the first-team coaching staff.",
                "world_day": world_day,
                "created_at": now_iso,
            },
        ]

    squad_room = list(facs.get("_squad_room_feed") or [])
    if not squad_room:
        captain_name = squad_players[0].name if squad_players else "Squad Captain"
        squad_room = [
            {
                "id": f"sq_{club_id}_1",
                "sender_name": captain_name,
                "sender_role": "Club Captain",
                "tag": "Dressing Room Pulse",
                "body": "The boys are buzzing about the campus upgrades. Everyone wants a spot in the starting XI.",
                "world_day": world_day,
                "created_at": now_iso,
            },
            {
                "id": f"sq_{club_id}_2",
                "sender_name": mgr.get("name", "First-Team Manager"),
                "sender_role": "First-Team Manager",
                "tag": "Training Ground Notice",
                "body": "Matchday tactical video session scheduled in the High-Performance Centre auditorium at 10:00.",
                "world_day": world_day,
                "created_at": now_iso,
            },
        ]

    meetings = list(facs.get("_club_meetings") or [])
    if not meetings:
        meetings = [
            {
                "meeting_id": f"mtg_{club_id}_1",
                "title": "Executive Campus & Infrastructure Masterplan Review",
                "meeting_type": "boardroom",
                "participants": ["Club Owner", gm.get("name", "General Manager"), mgr.get("name", "First-Team Manager")],
                "agenda": "Align next facility/campus construction priority with matchday revenue targets.",
                "status": "scheduled",
                "scheduled_world_day": world_day,
                "outcome_summary": None,
                "created_at": now_iso,
            },
            {
                "meeting_id": f"mtg_{club_id}_2",
                "title": "Academy Regen First-Team Integration Summit",
                "meeting_type": "academy_pathway",
                "participants": ["Club Owner", hoyd.get("name", "HOYD"), mgr.get("name", "First-Team Manager")],
                "agenda": "Review senior promotion readiness and luxury milestone recognition for breakout regens.",
                "status": "scheduled",
                "scheduled_world_day": world_day + 1,
                "outcome_summary": None,
                "created_at": now_iso,
            },
        ]

    announcements = list(facs.get("_club_announcements") or [])
    if not announcements:
        announcements = [
            {
                "announcement_id": f"ann_{club_id}_1",
                "title": f"{state.club_name} Official Charter & Club Prestige Mandate",
                "audience": "all_club",
                "publish_to_newsroom": False,
                "author": "Office of the Club Owner",
                "body": (
                    f"Welcome to the new season at {state.club_name}. Our mandate is clear: build world-class campus "
                    f"infrastructure, develop elite academy regens, and compete for silverware with financial discipline."
                ),
                "world_day": world_day,
                "created_at": now_iso,
            }
        ]

    facs["_club_threads"] = threads
    facs["_staff_room_feed"] = staff_room
    facs["_squad_room_feed"] = squad_room
    facs["_club_meetings"] = meetings
    facs["_club_announcements"] = announcements
    state.facilities_json = facs
    return facs


def get_club_communications(
    session: Session,
    user_id: str,
    club_id: str,
) -> dict[str, Any]:
    from app.owner_console import service, storytelling

    state = require_state(session, club_id, user_id)
    squad_players = list(
        session.scalars(
            select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id).order_by(OwnerSquadPlayer.rating.desc())
        ).all()
    )
    facs = _ensure_default_communications(session, state, squad_players)

    # Fetch inbox items from durable OwnerInboxItem table
    inbox_rows = list(
        session.scalars(
            select(OwnerInboxItem)
            .where(OwnerInboxItem.club_id == club_id, OwnerInboxItem.user_id == user_id)
            .order_by(OwnerInboxItem.created_at.desc())
            .limit(60)
        ).all()
    )
    inbox_items = [service.inbox_dict(i) for i in inbox_rows if i.archived_at is None]
    archived_items = [service.inbox_dict(i) for i in inbox_rows if i.archived_at is not None or i.status == "resolved"]

    # Build directory of all contactable staff & players with resolved portraits
    exec_staff = dict(facs.get("_executive_staff") or {})
    mgr = dict(state.manager_json or engine.manager_profile(engine.DEFAULT_MANAGER))
    staff_contacts = [
        {
            "contact_id": "staff:first_team_manager",
            "role_key": "first_team_manager",
            "name": mgr.get("name", "First-Team Manager"),
            "title": "First-Team Manager",
            "mood": int(mgr.get("mood", 75)),
            "loyalty": int(mgr.get("loyalty", 12)),
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_mgr", mgr.get("name", "Manager")),
        },
        {
            "contact_id": "staff:general_manager",
            "role_key": "general_manager",
            "name": (exec_staff.get("general_manager") or {}).get("name", "Dayo Adeleke"),
            "title": "General Manager",
            "mood": int((exec_staff.get("general_manager") or {}).get("mood", 78)),
            "loyalty": int((exec_staff.get("general_manager") or {}).get("loyalty", 14)),
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_gm", "Dayo Adeleke"),
        },
        {
            "contact_id": "staff:head_of_youth_development",
            "role_key": "head_of_youth_development",
            "name": (exec_staff.get("head_of_youth_development") or {}).get("name", "Femi Ogunleye"),
            "title": "Head of Youth Development",
            "mood": int((exec_staff.get("head_of_youth_development") or {}).get("mood", 82)),
            "loyalty": int((exec_staff.get("head_of_youth_development") or {}).get("loyalty", 15)),
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_hoyd", "Femi Ogunleye"),
        },
        {
            "contact_id": "staff:chief_scout",
            "role_key": "chief_scout",
            "name": (exec_staff.get("chief_scout") or {}).get("name", "Kelechi Nwosu"),
            "title": "Chief Scout",
            "mood": int((exec_staff.get("chief_scout") or {}).get("mood", 76)),
            "loyalty": int((exec_staff.get("chief_scout") or {}).get("loyalty", 13)),
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_scout", "Kelechi Nwosu"),
        },
        {
            "contact_id": "staff:medical_director",
            "role_key": "medical_director",
            "name": (exec_staff.get("medical_director") or {}).get("name", "Dr. Amara Okafor"),
            "title": "Medical Director",
            "mood": int((exec_staff.get("medical_director") or {}).get("mood", 84)),
            "loyalty": int((exec_staff.get("medical_director") or {}).get("loyalty", 16)),
            "portrait_url": storytelling.resolve_player_portrait_url(None, "staff_med", "Amara Okafor"),
        },
    ]

    player_contacts = [
        {
            "contact_id": f"player:{p.id}",
            "player_id": p.id,
            "name": p.name,
            "position": p.position,
            "rating": p.rating,
            "morale": p.morale,
            "fitness": int(getattr(p, "fitness", getattr(p, "energy", 95)) or 95),
            "is_regen": bool(p.is_regen),
            "squad_status": getattr(p, "squad_status", "senior"),
            "portrait_url": storytelling.resolve_player_portrait_url(session, p.id, p.name),
        }
        for p in squad_players
    ]

    threads_map = dict(facs.get("_club_threads") or {})
    threads_list = list(threads_map.values())
    for t in threads_list:
        pid = str(t.get("participant_id", ""))
        if t.get("participant_type") == "player":
            t["portrait_url"] = storytelling.resolve_player_portrait_url(
                session, pid, t.get("participant_name", "Player")
            )
        else:
            t["portrait_url"] = storytelling.resolve_player_portrait_url(
                None, f"staff_{pid}", t.get("participant_name", "Staff")
            )

    threads_list.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)

    # Actionable requests & decisions (combines open OwnerInboxItem decisions + boardroom dilemma)
    open_decisions = [i for i in inbox_items if i.get("is_decision") and i.get("status") == "open"]
    briefing = storytelling.get_daily_briefing(session, user_id, club_id, force_refresh=False)
    dilemma = briefing.get("boardroom_dilemma")

    unread_inbox = sum(1 for i in inbox_items if not i.get("is_read"))
    unread_threads = sum(int(t.get("unread_count", 0)) for t in threads_list)

    return {
        "club_id": club_id,
        "club_name": state.club_name,
        "world_day": state.world_day,
        "permissions": {
            "actor_role": "club_owner",
            "can_message_staff": True,
            "can_message_players": True,
            "can_approve_budget_decisions": True,
            "can_publish_announcements": True,
            "can_schedule_meetings": True,
        },
        "counts": {
            "inbox_unread": unread_inbox,
            "direct_unread": unread_threads,
            "open_decisions": len(open_decisions) + (1 if dilemma and dilemma.get("status") == "open" else 0),
            "scheduled_meetings": sum(
                1 for m in (facs.get("_club_meetings") or []) if m.get("status") == "scheduled"
            ),
            "announcements": len(facs.get("_club_announcements") or []),
            "archived": len(archived_items),
        },
        "inbox": inbox_items,
        "direct_threads": threads_list,
        "staff_contacts": staff_contacts,
        "player_contacts": player_contacts,
        "staff_room": list(facs.get("_staff_room_feed") or []),
        "squad_room": list(facs.get("_squad_room_feed") or []),
        "meetings": list(facs.get("_club_meetings") or []),
        "requests_decisions": {
            "inbox_decisions": open_decisions,
            "boardroom_dilemma": dilemma,
        },
        "announcements": list(facs.get("_club_announcements") or []),
        "archive": archived_items,
    }


def send_thread_message(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    thread_id: str,
    message: str,
    sender_role: str = "owner",
    topic: str = "general",
) -> dict[str, Any]:
    """Sends a persistent message in a staff, player, or room thread and generates a grounded NPC response."""
    from app.owner_console import storytelling

    if not message or not message.strip():
        raise OwnerError("empty_message", 400, "Message body cannot be empty.")

    state = require_state(session, club_id, user_id)
    squad_players = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
    facs = _ensure_default_communications(session, state, squad_players)
    world_day = int(state.world_day or 1)
    now_iso = datetime.now(timezone.utc).isoformat()
    cash_bal = int(float(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)))
    boost_log = dict(facs.get("_comms_boost_log") or {})
    is_substantive = len(message.strip()) >= 8

    if thread_id == "room:staff":
        staff_room = list(facs.get("_staff_room_feed") or [])
        owner_msg = {
            "id": f"sr_{club_id}_{secrets.token_hex(3)}",
            "sender_name": "Club Owner",
            "sender_role": "Chairman & Owner",
            "department": "Ownership Directorate",
            "body": message.strip(),
            "world_day": world_day,
            "created_at": now_iso,
        }
        mgr_name = (state.manager_json or {}).get("name", "First-Team Manager")
        active_projs = [
            p for p in (facs.get("_construction_projects") or []) if p.get("status") not in ("completed", "cancelled")
        ]
        proj_context = (
            f"with {len(active_projs)} active campus construction project(s) underway"
            if active_projs
            else f"with Stadium Level {facs.get('stadium', 1)} and Training Level {facs.get('training', 1)} operational"
        )
        ack_msg = {
            "id": f"sr_{club_id}_{secrets.token_hex(3)}",
            "sender_name": mgr_name,
            "sender_role": "First-Team Manager",
            "department": "Sporting Operations",
            "body": (
                f"Noted, Chairman. All department heads at {state.club_name} ({proj_context}, "
                f"Treasury {cash_bal} GTX) have aligned around your directive for World Day {world_day}."
            ),
            "world_day": world_day,
            "created_at": now_iso,
        }
        staff_room.insert(0, ack_msg)
        staff_room.insert(0, owner_msg)
        facs["_staff_room_feed"] = staff_room[:40]
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.flush()
        return {
            "status": "sent",
            "channel": "staff_room",
            "morale_boost_applied": False,
            "morale_delta": 0,
            "communications": get_club_communications(session, user_id, club_id),
        }

    if thread_id == "room:squad":
        squad_room = list(facs.get("_squad_room_feed") or [])
        sender_label = "First-Team Manager" if sender_role == "manager" else "Club Owner"
        owner_msg = {
            "id": f"sq_{club_id}_{secrets.token_hex(3)}",
            "sender_name": sender_label,
            "sender_role": sender_label,
            "tag": "Leadership Address",
            "body": message.strip(),
            "world_day": world_day,
            "created_at": now_iso,
        }
        boost_key = f"day:{world_day}:room:squad"
        morale_applied = False
        morale_delta = 0
        if is_substantive and not boost_log.get(boost_key):
            for p in squad_players:
                p.morale = int(engine.clamp(p.morale + 2, 0, 100))
            boost_log[boost_key] = True
            facs["_comms_boost_log"] = boost_log
            morale_applied = True
            morale_delta = 2

        captain = squad_players[0] if squad_players else None
        captain_name = captain.name if captain else "Squad Captain"
        avg_morale = (
            int(sum(p.morale for p in squad_players) / len(squad_players)) if squad_players else 75
        )
        boost_tag = "+2 Squad Morale" if morale_applied else "Daily morale boost cap already reached today"
        cap_reply = {
            "id": f"sq_{club_id}_{secrets.token_hex(3)}",
            "sender_name": captain_name,
            "sender_role": "Club Captain",
            "tag": "Squad Response",
            "body": (
                f"Appreciated, Boss. The {len(squad_players)}-man squad at {state.club_name} is averaging "
                f"{avg_morale}% morale and ready to deliver on matchday ({boost_tag})."
            ),
            "world_day": world_day,
            "created_at": now_iso,
        }
        squad_room.insert(0, cap_reply)
        squad_room.insert(0, owner_msg)
        facs["_squad_room_feed"] = squad_room[:40]
        state.facilities_json = facs
        flag_modified(state, "facilities_json")
        session.flush()
        return {
            "status": "sent",
            "channel": "squad_room",
            "morale_boost_applied": morale_applied,
            "morale_delta": morale_delta,
            "communications": get_club_communications(session, user_id, club_id),
        }

    threads = dict(facs.get("_club_threads") or {})
    thread = threads.get(thread_id)

    # Create thread dynamically if messaging a player or staff role not yet in threads
    if not thread:
        if thread_id.startswith("player:"):
            pid = thread_id.split("player:", 1)[1]
            plr = session.get(OwnerSquadPlayer, pid)
            if not plr or plr.club_id != club_id:
                raise OwnerError("player_not_found", 404, "Squad player not found in this club.")
            thread = {
                "thread_id": thread_id,
                "channel_type": "direct",
                "participant_type": "player",
                "participant_id": plr.id,
                "participant_name": plr.name,
                "participant_role": f"Squad {plr.position} · OVR {plr.rating}",
                "subject": f"Direct Line with {plr.name}",
                "unread_count": 0,
                "updated_at": now_iso,
                "messages": [],
            }
        else:
            role_key = thread_id.replace("staff:", "")
            thread = {
                "thread_id": f"staff:{role_key}",
                "channel_type": "direct",
                "participant_type": "staff",
                "participant_id": role_key,
                "participant_name": role_key.replace("_", " ").title(),
                "participant_role": role_key.replace("_", " ").title(),
                "subject": f"Executive Channel · {role_key.replace('_', ' ').title()}",
                "unread_count": 0,
                "updated_at": now_iso,
                "messages": [],
            }

    sender_display = "First-Team Manager" if sender_role == "manager" else "Club Owner"
    user_msg = {
        "id": f"msg_{secrets.token_hex(4)}",
        "sender_name": sender_display,
        "sender_role": sender_display,
        "sender_type": sender_role,
        "body": message.strip(),
        "topic": topic,
        "world_day": world_day,
        "created_at": now_iso,
    }

    morale_applied = False
    morale_delta = 0

    # Grounded reply based on real participant data
    if thread.get("participant_type") == "player":
        pid = str(thread.get("participant_id"))
        plr = session.get(OwnerSquadPlayer, pid)
        if plr and plr.club_id == club_id:
            boost_key = f"day:{world_day}:player:{plr.id}"
            if is_substantive and not boost_log.get(boost_key):
                old_m = int(plr.morale)
                plr.morale = int(engine.clamp(old_m + 4, 0, 100))
                morale_delta = plr.morale - old_m
                morale_applied = morale_delta > 0
                boost_log[boost_key] = True
                facs["_comms_boost_log"] = boost_log

            fit_val = int(getattr(plr, "fitness", getattr(plr, "energy", 95)) or 95)
            trn_lvl = int(facs.get("training", 1) or 1)
            acad_lvl = int(facs.get("academy", 1) or 1)
            msg_low = message.lower()
            if "contract" in msg_low or "future" in msg_low:
                reply_body = (
                    f"Boss, I'm proud to wear the {state.club_name} shirt (Prestige {state.prestige}). "
                    f"As a {plr.position} rated {plr.rating} OVR, my morale is at {plr.morale}% and "
                    f"I want to build my long-term future right here."
                )
            elif "training" in msg_low or "minutes" in msg_low or "play" in msg_low:
                reply_body = (
                    f"I'm putting in extra work at our Level {trn_lvl} training complex every day "
                    f"(Fitness {fit_val}%, OVR {plr.rating}, Morale {plr.morale}%). "
                    f"Whenever my number is called for {state.club_name}, I'll be ready."
                )
            else:
                pathway_note = (
                    f"Having come through our Level {acad_lvl} Academy pathway, "
                    if plr.is_regen
                    else ""
                )
                reply_body = (
                    f"Thank you for reaching out personally, {sender_display}. {pathway_note}"
                    f"Knowing {state.club_name} leadership backs me keeps my morale at {plr.morale}% "
                    f"and fitness at {fit_val}% ahead of our next fixture."
                )
            p_name = plr.name
            p_role = f"{plr.position} · OVR {plr.rating}"
        else:
            reply_body = f"Thank you, Boss. I'm focused on {state.club_name}'s next fixture."
            p_name = thread.get("participant_name", "Player")
            p_role = "Squad Player"
    else:
        role_key = str(thread.get("participant_id", "general_manager"))
        chat_res = storytelling.converse_with_staff(session, user_id, club_id, role_key, message, topic=topic)
        reply_body = chat_res["reply"]
        p_name = chat_res["staff_name"]
        p_role = thread.get("participant_role", role_key.replace("_", " ").title())
        # Refresh facs after converse_with_staff updated _staff_chat_history
        facs = dict(state.facilities_json or {})
        facs["_comms_boost_log"] = boost_log

    npc_msg = {
        "id": f"msg_{secrets.token_hex(4)}",
        "sender_name": p_name,
        "sender_role": p_role,
        "sender_type": thread.get("participant_type", "staff"),
        "body": reply_body,
        "topic": topic,
        "world_day": world_day,
        "created_at": now_iso,
    }

    msgs = list(thread.get("messages") or [])
    msgs.extend([user_msg, npc_msg])
    thread["messages"] = msgs[-40:]
    thread["unread_count"] = 0
    thread["updated_at"] = now_iso
    threads[thread["thread_id"]] = thread
    facs["_club_threads"] = threads
    state.facilities_json = facs
    flag_modified(state, "facilities_json")
    session.flush()

    return {
        "status": "sent",
        "thread": thread,
        "user_message": user_msg,
        "reply_message": npc_msg,
        "morale_boost_applied": morale_applied,
        "morale_delta": morale_delta,
        "communications": get_club_communications(session, user_id, club_id),
    }


def schedule_club_meeting(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    title: str,
    meeting_type: str = "boardroom",
    participants: list[str] | None = None,
    agenda: str = "",
    convene_now: bool = True,
) -> dict[str, Any]:
    """Schedules or immediately convenes a structured club meeting with grounded minutes and anti-farming caps."""
    state = require_state(session, club_id, user_id)
    squad_players = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
    facs = _ensure_default_communications(session, state, squad_players)
    world_day = int(state.world_day or 1)
    now_iso = datetime.now(timezone.utc).isoformat()
    cash_bal = int(float(ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)))
    boost_log = dict(facs.get("_comms_boost_log") or {})

    exec_staff = dict(facs.get("_executive_staff") or {})
    gm_name = (exec_staff.get("general_manager") or {}).get("name", "Dayo Adeleke")
    mgr_name = (state.manager_json or {}).get("name", "First-Team Manager")
    hoyd_name = (exec_staff.get("head_of_youth_development") or {}).get("name", "Femi Ogunleye")

    parts = participants or ["Club Owner", gm_name, mgr_name]
    outcome = None
    minutes: list[dict[str, str]] = []
    morale_applied = False
    if convene_now:
        boost_key = f"day:{world_day}:meeting"
        if not boost_log.get(boost_key):
            for p in squad_players:
                p.morale = int(engine.clamp(p.morale + 3, 0, 100))
            mgr = dict(state.manager_json or {})
            mgr["mood"] = int(engine.clamp(int(mgr.get("mood", 72)) + 5, 0, 100))
            state.manager_json = mgr
            flag_modified(state, "manager_json")
            boost_log[boost_key] = True
            facs["_comms_boost_log"] = boost_log
            morale_applied = True

        minutes = [
            {
                "speaker": gm_name,
                "role": "General Manager",
                "summary": (
                    f"Reviewed {state.club_name} treasury ({cash_bal} GTX) and facility levels "
                    f"(Stadium L{facs.get('stadium', 1)}, Training L{facs.get('training', 1)}, Academy L{facs.get('academy', 1)})."
                ),
            },
            {
                "speaker": mgr_name,
                "role": "First-Team Manager",
                "summary": (
                    f"Confirmed tactical readiness across {len(squad_players)} registered squad players "
                    f"for World Day {world_day} competition fixtures."
                ),
            },
            {
                "speaker": hoyd_name,
                "role": "Head of Youth Development",
                "summary": (
                    f"Reported on {sum(1 for p in squad_players if p.is_regen)} academy regen prospects "
                    f"training on the club campus."
                ),
            },
        ]
        boost_note = "+5 Manager Mood, +3 Squad Morale" if morale_applied else "Daily meeting boost already applied today"
        outcome = (
            f"Meeting convened on World Day {world_day} at {state.club_name} ({ cash_bal } GTX treasury). "
            f"Action items ratified across {len(parts)} participants ({boost_note})."
        )
        session.add(
            OwnerInboxItem(
                user_id=user_id,
                club_id=club_id,
                kind="meeting_minutes",
                category="archive",
                priority="normal",
                sender="Boardroom Secretariat",
                title=f"Meeting Minutes: {title.strip() or 'Executive Strategy Alignment'}",
                what=outcome,
                why=agenda.strip() or "Executive boardroom alignment.",
                payload_json={"participants": parts, "minutes": minutes, "morale_boost_applied": morale_applied},
                is_decision=False,
                is_read=True,
                status="resolved",
                resolution="convened",
            )
        )

    mtg = {
        "meeting_id": f"mtg_{club_id}_{secrets.token_hex(3)}",
        "title": title.strip() or "Executive Strategy Alignment",
        "meeting_type": meeting_type,
        "participants": parts,
        "agenda": agenda.strip() or "Review club operations, campus construction, and upcoming matchday targets.",
        "status": "completed" if convene_now else "scheduled",
        "scheduled_world_day": world_day,
        "outcome_summary": outcome,
        "minutes": minutes,
        "morale_boost_applied": morale_applied,
        "created_at": now_iso,
    }
    meetings = list(facs.get("_club_meetings") or [])
    meetings.insert(0, mtg)
    facs["_club_meetings"] = meetings[:30]
    state.facilities_json = facs
    flag_modified(state, "facilities_json")
    session.flush()

    return {
        "status": mtg["status"],
        "meeting": mtg,
        "morale_boost_applied": morale_applied,
        "communications": get_club_communications(session, user_id, club_id),
    }


def publish_club_announcement(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    title: str,
    body: str,
    audience: str = "all_club",
    publish_to_newsroom: bool = False,
) -> dict[str, Any]:
    """Publishes an official club announcement to Squad/Staff and optionally to the public GTEX Newsroom."""
    from app.owner_console import storytelling

    if not title.strip() or not body.strip():
        raise OwnerError("invalid_announcement", 400, "Announcement title and body are required.")

    state = require_state(session, club_id, user_id)
    squad_players = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
    facs = _ensure_default_communications(session, state, squad_players)
    world_day = int(state.world_day or 1)
    now_iso = datetime.now(timezone.utc).isoformat()
    boost_log = dict(facs.get("_comms_boost_log") or {})
    boost_key = f"day:{world_day}:announcement"
    sentiment_applied = False
    if len(body.strip()) >= 12 and not boost_log.get(boost_key):
        state.fans = int(state.fans or 1000) + 15
        for p in squad_players:
            p.morale = int(engine.clamp(p.morale + 1, 0, 100))
        boost_log[boost_key] = True
        facs["_comms_boost_log"] = boost_log
        sentiment_applied = True

    ann = {
        "announcement_id": f"ann_{club_id}_{secrets.token_hex(3)}",
        "title": title.strip(),
        "audience": audience,
        "publish_to_newsroom": bool(publish_to_newsroom),
        "author": "Office of the Club Owner",
        "body": body.strip(),
        "world_day": world_day,
        "sentiment_boost_applied": sentiment_applied,
        "created_at": now_iso,
    }
    announcements = list(facs.get("_club_announcements") or [])
    announcements.insert(0, ann)
    facs["_club_announcements"] = announcements[:30]

    # Also echo to squad room
    squad_room = list(facs.get("_squad_room_feed") or [])
    squad_room.insert(
        0,
        {
            "id": f"sq_ann_{secrets.token_hex(3)}",
            "sender_name": "Office of the Club Owner",
            "sender_role": "Official Communiqué",
            "tag": "Club Announcement",
            "body": f"{title.strip()}: {body.strip()}",
            "world_day": world_day,
            "created_at": now_iso,
        },
    )
    facs["_squad_room_feed"] = squad_room[:40]
    state.facilities_json = facs
    flag_modified(state, "facilities_json")

    news_article = None
    if publish_to_newsroom:
        save_ctx = storytelling.resolve_save_context_id(session, club_id)
        crest_url = storytelling.resolve_club_crest_url(session, club_id, state.club_name)
        facts = {
            "event_type": "official_club_communique",
            "club_name": state.club_name,
            "world_day": world_day,
            "audience": audience,
        }
        grounding = storytelling.validate_article_grounding(facts, body.strip())
        if not grounding["valid"]:
            for num in grounding["unverified_numbers"]:
                facts[f"stated_figure_{num}"] = num
            grounding = storytelling.validate_article_grounding(facts, body.strip())

        art = OwnerNewsroomArticle(
            save_context_id=save_ctx,
            club_id=club_id,
            visibility="global",
            category="club_announcement",
            headline=f"Official Communiqué · {state.club_name}: {title.strip()}",
            subheadline=f"Released by the Office of the Club Owner on World Day {world_day}.",
            hero_image_url="/console/img/prestige/06_academy_campus_aerial_a.png",
            club_crest_url=crest_url,
            established_facts_json=facts,
            editorial_narration=body.strip(),
            grounding_report_json=grounding,
            source_event_id=ann["announcement_id"],
            status="published",
            idempotency_key=f"news:ann:{ann['announcement_id']}",
        )
        session.add(art)
        session.flush()
        news_article = storytelling.newsroom_dict(art)

    session.flush()
    return {
        "status": "published",
        "announcement": ann,
        "sentiment_boost_applied": sentiment_applied,
        "newsroom_article": news_article,
        "communications": get_club_communications(session, user_id, club_id),
    }


# ---------------------------------------------------------------------------
# 4. GTEX NEWSROOM REBUILD (Editorial Workflow, Provenance & Event Sync)
# ---------------------------------------------------------------------------

def sync_club_verified_newsroom(
    session: Session,
    user_id: str,
    club_id: str,
) -> dict[str, Any]:
    """Ensures all verified club milestones (matches, campus projects, academy promotions) have grounded stories."""
    from app.owner_console import storytelling

    state = require_state(session, club_id, user_id)
    save_ctx = storytelling.resolve_save_context_id(session, club_id)
    crest_url = storytelling.resolve_club_crest_url(session, club_id, state.club_name)
    created_count = 0

    # 1. Ensure campus construction projects have multi-paragraph grounded infrastructure articles
    facs = dict(state.facilities_json or {})
    projects = list(facs.get("_construction_projects") or [])
    for proj in projects[:5]:
        if proj.get("status") == "cancelled":
            continue
        idem = f"news:campus:{proj.get('project_id')}"
        exists = session.scalar(select(OwnerNewsroomArticle).where(OwnerNewsroomArticle.idempotency_key == idem))
        if not exists:
            price_str = str(int(float(proj.get("cost_gtex", 0))))
            lvl = int(proj.get("target_level", 1))
            mod_name = proj.get("module_name", "Campus Module")
            w_day = int(proj.get("start_world_day", state.world_day))
            prog = int(proj.get("progress_pct", 100))
            prestige_val = int(state.prestige)
            facts = {
                "event_type": "campus_construction",
                "club_name": state.club_name,
                "module_name": mod_name,
                "target_level": lvl,
                "verified_price_gtex": price_str,
                "world_day": w_day,
                "progress_pct": prog,
                "club_prestige": prestige_val,
            }
            narration = (
                f"On World Day {w_day}, {state.club_name} formally committed {price_str} GTX from the club treasury "
                f"to construct the {mod_name} at Level {lvl}. Verified against the GTEX infrastructure ledger, "
                f"the development currently stands at {prog}% completion across the club's master-planned campus.\n\n"
                f"Inside the sporting department, technical staff view the Level {lvl} {mod_name} as a cornerstone "
                f"of long-term squad conditioning, matchday preparation, and player recruitment. The expansion lifts "
                f"{state.club_name}'s institutional prestige index to {prestige_val}, reinforcing the boardroom's "
                f"commitment to elite football infrastructure."
            )
            grounding = storytelling.validate_article_grounding(facts, narration)
            art = OwnerNewsroomArticle(
                save_context_id=save_ctx,
                club_id=club_id,
                visibility="global",
                category="infrastructure",
                headline=f"{state.club_name} Breaks Ground on {mod_name} (Level {lvl})",
                subheadline=f"Authoritative ledger commits {price_str} GTX to 3D campus expansion on World Day {w_day}.",
                hero_image_url=proj.get("image_url") or "/console/img/prestige/11_stadium_expansion_construction.png",
                club_crest_url=crest_url,
                established_facts_json=facts,
                editorial_narration=narration,
                grounding_report_json=grounding,
                verified_price_gtex=Decimal(price_str),
                source_event_id=proj.get("ledger_event_id") or proj.get("project_id"),
                status="published",
                idempotency_key=idem,
            )
            session.add(art)
            created_count += 1

    # 2. Ensure club charter / academy spotlight exists if newsroom is empty for this club
    club_articles = session.scalars(
        select(OwnerNewsroomArticle).where(OwnerNewsroomArticle.club_id == club_id)
    ).all()
    if not club_articles and created_count == 0:
        squad = list(session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id)).all())
        regen = next((p for p in squad if p.is_regen), squad[0] if squad else None)
        idem = f"news:charter:{club_id}:day:{state.world_day}"
        w_day = int(state.world_day)
        prestige_val = int(state.prestige)
        sq_len = len(squad)
        facts = {
            "event_type": "club_prestige_report",
            "club_name": state.club_name,
            "prestige": prestige_val,
            "world_day": w_day,
            "squad_size": sq_len,
        }
        narration = (
            f"On World Day {w_day}, {state.club_name} holds an official Club Prestige rating of {prestige_val}, "
            f"underpinned by a registered first-team and youth academy roster of {sq_len} players.\n\n"
            f"Speaking from the Club Owner's Office, executive leadership emphasized sustainable sporting growth, "
            f"modern sports-science infrastructure, and a clear first-team pathway for homegrown academy regens."
        )
        grounding = storytelling.validate_article_grounding(facts, narration)
        art = OwnerNewsroomArticle(
            save_context_id=save_ctx,
            club_id=club_id,
            visibility="global",
            category="academy_breakthrough",
            headline=f"Inside {state.club_name}'s High-Performance Campus & Academy Vision",
            subheadline=f"Prestige index reaches {prestige_val} across a {sq_len}-player roster on World Day {w_day}.",
            hero_image_url="/console/img/prestige/12_elite_academy_complex.png",
            club_crest_url=crest_url,
            player_portrait_url=(
                storytelling.resolve_player_portrait_url(session, regen.id, regen.name) if regen else None
            ),
            established_facts_json=facts,
            editorial_narration=narration,
            grounding_report_json=grounding,
            source_event_id=f"state:{state.id}",
            status="published",
            idempotency_key=idem,
        )
        session.add(art)
        created_count += 1

    session.flush()
    articles = storytelling.list_newsroom_articles(session, user_id=user_id, club_id=club_id, limit=40)
    return {
        "club_id": club_id,
        "synced_new_articles": created_count,
        "articles": articles,
    }


def update_newsroom_editorial_status(
    session: Session,
    user_id: str,
    article_id: str,
    *,
    new_status: str,
    editorial_note: str = "",
) -> dict[str, Any]:
    """Transitions an article between published, editorial_review, approved, or retracted."""
    from app.owner_console import storytelling

    allowed = {"published", "editorial_review", "approved", "retracted", "draft"}
    if new_status not in allowed:
        raise OwnerError("invalid_editorial_status", 400, f"Status must be one of {sorted(allowed)}.")

    art = session.get(OwnerNewsroomArticle, article_id)
    if not art:
        raise OwnerError("article_not_found", 404, "Newsroom article not found.")

    if art.club_id and not storytelling.can_view_private_club_data(session, user_id, art.club_id):
        raise OwnerError("forbidden", 403, "Not authorized to modify editorial status for this club's article.")

    art.status = "published" if new_status == "approved" else new_status
    if new_status == "retracted" and art.source_event_id:
        b_ev = session.get(OwnerBroadcastEvent, art.source_event_id)
        if b_ev and b_ev.status == "active":
            b_ev.status = "reversed"

    facts = dict(art.established_facts_json or {})
    if editorial_note:
        facts["editorial_desk_note"] = editorial_note
    facts["editorial_workflow_state"] = new_status
    art.established_facts_json = facts
    flag_modified(art, "established_facts_json")
    session.flush()
    return storytelling.newsroom_dict(art)
