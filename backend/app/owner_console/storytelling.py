"""GTEX Event-Driven Football Storytelling & Personal Club Management Engine.

Provides:
1. Transaction-safe Global Live Ticker (verified private jets, facility upgrades, player gifts ONLY).
2. AI Grounded Newsroom (strict separation of established facts from editorial narration, read-only).
3. Rich static imagery resolvers (face-bank player portraits, club crests, stadium and showroom PNGs).
4. Shared-save context resolution & confidential owner data isolation.
5. Luxury Showroom & Squad Player Gifting.
6. Club Story & Legacy Chronicle builder.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubProfile
from app.models.user import User
from app.owner_console import ledger
from app.owner_console.models import (
    OwnerBroadcastEvent,
    OwnerCompetition,
    OwnerCompetitionEntry,
    OwnerInboxItem,
    OwnerMatch,
    OwnerNewsroomArticle,
    OwnerScoutingWatchlist,
    OwnerSquadPlayer,
)
from app.owner_console.service import OwnerClubState, OwnerError, require_state

logger = logging.getLogger(__name__)

INBOX_CATEGORIES = (
    "requests",
    "deadlines",
    "staff_recommendations",
    "player_issues",
    "scouting_reports",
    "negotiations",
    "scheduling",
    "archive",
)

SHOWROOM_CATALOG: dict[str, dict[str, Any]] = {
    "sovereign_900x_jet": {
        "catalog_key": "sovereign_900x_jet",
        "name": "GTEX Sovereign 900X Private Jet",
        "category": "jet",
        "model": "Sovereign 900X Long-Range VIP",
        "price_gtex": 4800.0,
        "prestige_bonus": 8,
        "broadcast_on_purchase": True,
        "image_file": "sovereign_900x_jet.png",
        "description": "Executive intercontinental aircraft for continental away fixtures and owner mobility.",
        "can_gift_to_player": True,
    },
    "gulfstream_g700_exec_jet": {
        "catalog_key": "gulfstream_g700_exec_jet",
        "name": "Gulfstream G700 Executive Jet",
        "category": "jet",
        "model": "G700 Flagship Club Aviation",
        "price_gtex": 6200.0,
        "prestige_bonus": 10,
        "broadcast_on_purchase": True,
        "image_file": "sovereign_900x_jet.png",
        "description": "Ultra-long-range boardroom in the sky featuring bespoke club livery and recovery suites.",
        "can_gift_to_player": True,
    },
    "vanguard_xii_coach": {
        "catalog_key": "vanguard_xii_coach",
        "name": "Vanguard XII Luxury Team Coach",
        "category": "coach",
        "model": "Vanguard XII Armored First-Team Bus",
        "price_gtex": 320.0,
        "prestige_bonus": 2,
        "broadcast_on_purchase": False,
        "image_file": "vanguard_xii_coach.png",
        "description": "Armored luxury transit for matchday squad arrivals with custom tactical review screens.",
        "can_gift_to_player": False,
    },
    "veloce_gt9_hypercar": {
        "catalog_key": "veloce_gt9_hypercar",
        "name": "Veloce GT9 Hypercar",
        "category": "vehicle",
        "model": "GT9 Twin-Turbo V12",
        "price_gtex": 850.0,
        "prestige_bonus": 4,
        "broadcast_on_purchase": False,
        "image_file": "veloce_gt9_hypercar.png",
        "description": "Hand-built performance vehicle. Kept in private owner collection unless gifted to a star player.",
        "can_gift_to_player": True,
    },
    "chronos_tourbillon_watch": {
        "catalog_key": "chronos_tourbillon_watch",
        "name": "Chronos Tourbillon Piece Unique",
        "category": "watch",
        "model": "Piece Unique Sapphire-Carbon",
        "price_gtex": 220.0,
        "prestige_bonus": 2,
        "broadcast_on_purchase": False,
        "image_file": "chronos_tourbillon_watch.png",
        "description": "Haute horlogerie timepiece. Perfect personal milestone gift for squad leaders and regens.",
        "can_gift_to_player": True,
    },
    "penthouse_box_suite": {
        "catalog_key": "penthouse_box_suite",
        "name": "Royal Penthouse Hospitality Box",
        "category": "suite",
        "model": "Directorate VIP Skybox",
        "price_gtex": 500.0,
        "prestige_bonus": 3,
        "broadcast_on_purchase": False,
        "image_file": "arena_imperiale_stadium.png",
        "description": "VIP private salon inside the stadium for high-stakes investor hosting and sponsor meetings.",
        "can_gift_to_player": False,
    },
}

FACILITY_IMAGES = {
    "stadium": "/console/img/showroom/arena_imperiale_stadium.png",
    "training": "/console/img/showroom/apex_performance_campus.png",
    "academy": "/console/img/showroom/apex_performance_campus.png",
    "commercial": "/console/img/showroom/arena_imperiale_stadium.png",
    "medical": "/console/img/showroom/apex_performance_campus.png",
}

# Manifest face-bank path for fallback static portraits
_MANIFEST_CACHE: dict[str, Any] | None = None


def _load_face_manifest() -> dict[str, Any]:
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    manifest_path = os.path.join(backend_root, "generated_media", "regen_newgen_faces", "manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                _MANIFEST_CACHE = json.load(f)
                return _MANIFEST_CACHE
        except Exception as e:
            logger.warning("failed to load regen face manifest: %s", e)
    _MANIFEST_CACHE = {}
    return _MANIFEST_CACHE


def resolve_showroom_image_url(catalog_key: str) -> str:
    item = SHOWROOM_CATALOG.get(catalog_key)
    if item and item.get("image_file"):
        return f"/console/img/showroom/{item['image_file']}"
    if catalog_key in FACILITY_IMAGES:
        return FACILITY_IMAGES[catalog_key]
    return "/console/img/showroom/sovereign_900x_jet.png"


def resolve_stadium_image_url(stadium_style: str = "stadium") -> str:
    return "/console/img/showroom/arena_imperiale_stadium.png"


def resolve_club_crest_url(session: Session, club_id: str, club_name: str | None = None) -> str:
    profile = session.get(ClubProfile, club_id)
    if profile and profile.crest_asset_ref:
        return f"/api/media/{profile.crest_asset_ref}"
    name = (profile.club_name if profile else club_name) or "GTEX"
    initials = "".join([part[0] for part in name.split()[:2]]).upper() or "FC"
    primary = (profile.primary_color if profile else None) or "#0F766E"
    secondary = (profile.secondary_color if profile else None) or "#F8FAFC"
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
        f"<polygon points='50,4 92,20 84,78 50,96 16,78 8,20' fill='{primary}' stroke='{secondary}' stroke-width='4'/>"
        f"<text x='50' y='58' font-family='sans-serif' font-weight='900' font-size='26' fill='{secondary}' text-anchor='middle'>{initials}</text>"
        f"</svg>"
    )
    import urllib.parse

    return f"data:image/svg+xml;utf8,{urllib.parse.quote(svg)}"


def resolve_player_portrait_url(session: Session | None, player_id: str, player_name: str | None = None) -> str:
    player = session.get(OwnerSquadPlayer, player_id) if session else None
    name = (player.name if player else player_name) or "Player"
    # 1. Check if face-bank manifest has a mapped static portrait
    manifest = _load_face_manifest()
    items = manifest.get("assets") or manifest.get("items") or []
    if items:
        h = int(hashlib.md5(player_id.encode("utf-8")).hexdigest()[:8], 16)
        chosen = items[h % len(items)]
        if chosen.get("cloudinary_secure_url"):
            return str(chosen["cloudinary_secure_url"])
        rel = chosen.get("storage_key") or chosen.get("source_path") or chosen.get("relative_path")
        if rel:
            import urllib.parse

            rel_clean = urllib.parse.quote(str(rel).replace("\\", "/").lstrip("/"), safe="/")
            return f"/generated-media/{rel_clean}"
    # 2. Deterministic high-quality vector portrait fallback
    initials = "".join([part[0] for part in name.split()[:2]]).upper() or "P"
    palette = ["#0F766E", "#1E3A8A", "#831843", "#14532D", "#7C2D12", "#4C1D95"]
    h_idx = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:4], 16) % len(palette)
    color = palette[h_idx]
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'>"
        f"<circle cx='60' cy='60' r='58' fill='{color}' stroke='#FFFFFF' stroke-width='3' stroke-opacity='0.3'/>"
        f"<circle cx='60' cy='46' r='24' fill='#FFFFFF' fill-opacity='0.85'/>"
        f"<path d='M24 104 C24 76, 96 76, 96 104 Z' fill='#FFFFFF' fill-opacity='0.85'/>"
        f"<text x='60' y='52' font-family='sans-serif' font-weight='900' font-size='16' fill='{color}' text-anchor='middle'>{initials}</text>"
        f"</svg>"
    )
    import urllib.parse

    return f"data:image/svg+xml;utf8,{urllib.parse.quote(svg)}"


def resolve_save_context_id(session: Session, club_id: str) -> str:
    entry = session.scalar(
        select(OwnerCompetitionEntry)
        .join(OwnerCompetition, OwnerCompetition.id == OwnerCompetitionEntry.competition_id)
        .where(
            OwnerCompetitionEntry.club_id == club_id,
            OwnerCompetition.status.in_(("open", "running", "completed")),
        )
        .order_by(OwnerCompetitionEntry.created_at.desc())
    )
    if entry:
        return f"competition:{entry.competition_id}"
    return f"club:{club_id}"


def user_save_context_ids(session: Session, user_id: str) -> list[str]:
    states = session.scalars(select(OwnerClubState).where(OwnerClubState.owner_user_id == user_id)).all()
    out = set()
    for s in states:
        out.add(resolve_save_context_id(session, s.club_id))
        out.add(f"club:{s.club_id}")
    return sorted(out)


def _get_club_state(session: Session, club_id: str) -> OwnerClubState | None:
    return session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))


def can_view_private_club_data(session: Session, user_id: str, club_id: str) -> bool:
    state = _get_club_state(session, club_id)
    if not state:
        return False
    if state.owner_user_id == user_id:
        return True
    user = session.get(User, user_id)
    if user and getattr(user.role, "value", user.role) in ("admin", "super_admin"):
        return True
    return False


def validate_article_grounding(established_facts: dict[str, Any], editorial_narration: str) -> dict[str, Any]:
    """Validates that editorial text does not invent unverified prices, scorelines or game numbers."""
    editorial_clean = re.sub(r"\b202\d\b", "", editorial_narration)
    found_numbers = re.findall(r"\b\d+(?:[\.,]\d+)?\b", editorial_clean)
    verified_numbers: set[str] = set()

    for k, v in established_facts.items():
        if isinstance(v, (int, float, Decimal)):
            verified_numbers.add(str(int(float(v))))
            verified_numbers.add(str(v))
        elif isinstance(v, str):
            for num in re.findall(r"\b\d+(?:[\.,]\d+)?\b", v):
                verified_numbers.add(num)
                verified_numbers.add(str(int(float(num.replace(",", "")))))

    unverified_numbers = []
    for num in found_numbers:
        clean = num.replace(",", "")
        if clean in verified_numbers or str(int(float(clean))) in verified_numbers:
            continue
        unverified_numbers.append(num)

    found_scores = re.findall(r"\b(\d+)\s*[-–]\s*(\d+)\b", editorial_narration)
    verified_scores: set[str] = set()
    if "home_goals" in established_facts and "away_goals" in established_facts:
        hg = str(established_facts["home_goals"])
        ag = str(established_facts["away_goals"])
        verified_scores.add(f"{hg}-{ag}")
        verified_scores.add(f"{hg}–{ag}")

    unverified_scores = []
    for h, a in found_scores:
        pair1 = f"{h}-{a}"
        pair2 = f"{h}–{a}"
        if pair1 not in verified_scores and pair2 not in verified_scores:
            unverified_scores.append(pair1)

    is_valid = len(unverified_numbers) == 0 and len(unverified_scores) == 0
    return {
        "valid": is_valid,
        "unverified_numbers": unverified_numbers,
        "unverified_scores": unverified_scores,
    }


def build_grounded_editorial(
    category: str,
    established_facts: dict[str, Any],
) -> tuple[str, str, str]:
    club = established_facts.get("club_name") or established_facts.get("home_club") or "GTEX Club"
    owner = established_facts.get("owner_display_name") or established_facts.get("owner") or "The Board"
    item = established_facts.get("item_name") or "Prestige Asset"
    price = established_facts.get("verified_price_gtex")
    player = established_facts.get("player_name")

    if category == "fleet_aviation":
        headline = f"{club} Commissions Executive Long-Range Aviation"
        subheadline = f"Official private jet acquisition approved and funded at {price} GTX."
        narration = (
            f"In a major operational investment, {owner} has formally added the {item} to {club}'s fleet. "
            f"The verified transaction commits {price} GTX from the club treasury, providing dedicated intercontinental transit "
            f"and player recovery suites for high-stakes competition fixtures."
        )
    elif category == "infrastructure":
        facility = established_facts.get("facility_kind") or "Campus"
        lvl = established_facts.get("facility_level") or 2
        headline = f"{club} Unveils Level {lvl} {facility.capitalize()} Modernisation"
        subheadline = f"Facility upgrade commits {price} GTX to world-class sporting infrastructure."
        narration = (
            f"Club leadership has greenlit the modernisation of {club}'s {facility} facilities to Level {lvl}. "
            f"The authoritative ledger reflects a {price} GTX infrastructure investment to boost performance and youth development."
        )
    elif category == "squad_culture":
        headline = f"{owner} Presents Personal Luxury Gift to {player}"
        subheadline = f"{item} presented as performance dedication bonus at {price} GTX."
        narration = (
            f"Dressing room morale surged at {club} as {owner} formally presented {player} with the {item}. "
            f"Valued at {price} GTX on the GTEX register, the gesture highlights boardroom trust in squad talent."
        )
    else:
        hg = established_facts.get("home_goals", 0)
        ag = established_facts.get("away_goals", 0)
        hc = established_facts.get("home_club", "Home")
        ac = established_facts.get("away_club", "Away")
        headline = f"Full Time: {hc} {hg} – {ag} {ac}"
        subheadline = "Fixture committed to official competition standings."
        narration = (
            f"The final whistle blew on a contested fixture between {hc} and {ac}, concluding at {hg}–{ag}. "
            f"Match points and official matchday performance logs have committed to the league table."
        )
    return headline, subheadline, narration


def record_verified_broadcast_event(
    session: Session,
    *,
    event_type: str,
    club_id: str,
    owner_user_id: str,
    item_name: str,
    item_model: str | None = None,
    item_image_url: str | None = None,
    player_id: str | None = None,
    player_name: str | None = None,
    player_portrait_url: str | None = None,
    verified_price_gtex: Decimal | float | None = None,
    headline: str | None = None,
    summary: str | None = None,
    save_context_id: str | None = None,
    ledger_event_id: str | None = None,
    idempotency_key: str | None = None,
    editorial_narration: str | None = None,
    newsroom_category: str | None = None,
    payload_json: dict[str, Any] | None = None,
) -> OwnerBroadcastEvent | None:
    """Records a durable broadcast announcement strictly for private jets, facility upgrades, or player gifts."""
    ELIGIBLE_EVENTS = {"private_jet_purchase", "facility_upgrade", "player_gift"}
    if event_type not in ELIGIBLE_EVENTS:
        logger.info("Skipping global broadcast for ineligible event_type=%s", event_type)
        return None

    if idempotency_key:
        existing = session.scalar(
            select(OwnerBroadcastEvent).where(OwnerBroadcastEvent.idempotency_key == idempotency_key)
        )
        if existing:
            return existing

    state = _get_club_state(session, club_id)
    club_name = state.club_name if state else "GTEX Club"
    owner_user = session.get(User, owner_user_id)
    owner_display = (owner_user.display_name or owner_user.username) if owner_user else "Club Ownership"
    save_ctx = save_context_id or resolve_save_context_id(session, club_id)

    price_dec = Decimal(str(verified_price_gtex)) if verified_price_gtex is not None else Decimal("0.0000")

    if not headline:
        if event_type == "private_jet_purchase":
            headline = f"{club_name} Commissions {item_name}"
            summary = f"{owner_display} has acquired {item_name} for {price_dec:f} GTX."
        elif event_type == "facility_upgrade":
            headline = f"{club_name} Completes Facility Upgrade"
            summary = f"{club_name} upgraded {item_name} for {price_dec:f} GTX."
        else:
            headline = f"{owner_display} Gifts {item_name} to {player_name or 'Player'}"
            summary = f"Dedication gift valued at {price_dec:f} GTX presented to squad."

    crest_url = resolve_club_crest_url(session, club_id, club_name)

    broadcast = OwnerBroadcastEvent(
        save_context_id=save_ctx,
        club_id=club_id,
        club_name=club_name,
        club_crest_url=crest_url,
        owner_user_id=owner_user_id,
        owner_display_name=owner_display,
        event_type=event_type,
        item_name=item_name,
        item_model=item_model,
        item_image_url=item_image_url,
        player_id=player_id,
        player_name=player_name,
        player_portrait_url=player_portrait_url,
        verified_price_gtex=price_dec,
        currency="GTEX",
        status="active",
        headline=headline,
        summary=summary or "",
        ledger_event_id=ledger_event_id,
        idempotency_key=idempotency_key,
        payload_json={
            "world_day": state.world_day if state else 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(payload_json or {}),
        },
    )
    session.add(broadcast)
    session.flush()

    # Create linked Newsroom article
    cat_map = {
        "private_jet_purchase": "fleet_aviation",
        "facility_upgrade": "infrastructure",
        "player_gift": "squad_culture",
    }
    n_category = newsroom_category or cat_map.get(event_type, "editorial")
    established_facts = {
        "event_type": event_type,
        "club_name": club_name,
        "owner_display_name": owner_display,
        "item_name": item_name,
        "item_model": item_model,
        "verified_price_gtex": str(price_dec),
        "player_name": player_name,
        "world_day": state.world_day if state else 1,
    }
    def_hl, def_sub, def_narr = build_grounded_editorial(n_category, established_facts)
    final_narration = editorial_narration or def_narr
    grounding_report = validate_article_grounding(established_facts, final_narration)
    if not grounding_report["valid"]:
        logger.warning("Editorial narration had unverified claims, falling back to grounded default")
        final_narration = def_narr
        grounding_report = validate_article_grounding(established_facts, final_narration)

    news_article = OwnerNewsroomArticle(
        save_context_id=save_ctx,
        club_id=club_id,
        visibility="global",
        category=n_category,
        headline=def_hl,
        subheadline=def_sub,
        hero_image_url=item_image_url or crest_url,
        club_crest_url=crest_url,
        player_portrait_url=player_portrait_url,
        established_facts_json=established_facts,
        editorial_narration=final_narration,
        grounding_report_json=grounding_report,
        verified_price_gtex=price_dec,
        source_event_id=broadcast.id,
        status="published",
        idempotency_key=f"news:{idempotency_key}" if idempotency_key else None,
    )
    session.add(news_article)

    # Attach after_commit real-time dispatch listener
    _stage_realtime_broadcast(session, broadcast)
    return broadcast


def _stage_realtime_broadcast(session: Session, broadcast: OwnerBroadcastEvent) -> None:
    from sqlalchemy import event
    from app.realtime.service import publish_realtime_domain_event

    b_data = broadcast_dict(broadcast)

    def _on_commit():
        try:
            publish_realtime_domain_event(
                "storytelling.ticker.broadcast",
                b_data,
                save_context_id=broadcast.save_context_id,
                club_id=broadcast.club_id,
            )
        except Exception as err:
            logger.warning("Failed to publish realtime ticker broadcast: %s", err)

    event.listen(session, "after_commit", lambda s: _on_commit(), once=True)


def broadcast_dict(ev: OwnerBroadcastEvent) -> dict[str, Any]:
    return {
        "id": ev.id,
        "save_context_id": ev.save_context_id,
        "club_id": ev.club_id,
        "club_name": ev.club_name,
        "club_crest_url": ev.club_crest_url,
        "owner_display_name": ev.owner_display_name,
        "event_type": ev.event_type,
        "item_name": ev.item_name,
        "item_model": ev.item_model,
        "item_image_url": ev.item_image_url,
        "player_id": ev.player_id,
        "player_name": ev.player_name,
        "player_portrait_url": ev.player_portrait_url,
        "verified_price_gtex": str(ev.verified_price_gtex) if ev.verified_price_gtex is not None else None,
        "currency": ev.currency,
        "status": ev.status,
        "headline": ev.headline,
        "summary": ev.summary,
        "idempotency_key": ev.idempotency_key,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


def reverse_broadcast_events_for_ledger(session: Session, ledger_event_id: str) -> int:
    """Marks any broadcast event linked to a reversed ledger transaction as 'reversed' and retracts stories."""
    events = session.scalars(
        select(OwnerBroadcastEvent).where(
            OwnerBroadcastEvent.ledger_event_id == ledger_event_id,
            OwnerBroadcastEvent.status == "active",
        )
    ).all()
    count = 0
    for ev in events:
        ev.status = "reversed"
        count += 1
        articles = session.scalars(
            select(OwnerNewsroomArticle).where(
                OwnerNewsroomArticle.source_event_id == ev.id,
                OwnerNewsroomArticle.status == "published",
            )
        ).all()
        for art in articles:
            art.status = "retracted"
    return count


def list_ticker_events(
    session: Session,
    *,
    user_id: str | None = None,
    club_id: str | None = None,
    save_context_id: str | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    stmt = (
        select(OwnerBroadcastEvent)
        .where(OwnerBroadcastEvent.status == "active")
        .order_by(OwnerBroadcastEvent.created_at.desc())
    )
    if club_id:
        stmt = stmt.where(OwnerBroadcastEvent.club_id == club_id)
    if save_context_id:
        stmt = stmt.where(OwnerBroadcastEvent.save_context_id == save_context_id)
    rows = session.scalars(stmt.limit(limit)).all()
    return [broadcast_dict(r) for r in rows]


def list_newsroom_articles(
    session: Session,
    *,
    user_id: str | None = None,
    club_id: str | None = None,
    save_context_id: str | None = None,
    category: str | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    stmt = (
        select(OwnerNewsroomArticle)
        .where(OwnerNewsroomArticle.status == "published")
        .order_by(OwnerNewsroomArticle.created_at.desc())
    )
    if club_id:
        stmt = stmt.where(OwnerNewsroomArticle.club_id == club_id)
        if user_id and not can_view_private_club_data(session, user_id, club_id):
            stmt = stmt.where(OwnerNewsroomArticle.visibility == "global")

    allowed_saves = set(user_save_context_ids(session, user_id)) if user_id else None

    if save_context_id:
        if allowed_saves is not None and save_context_id not in allowed_saves:
            stmt = stmt.where(
                OwnerNewsroomArticle.save_context_id == save_context_id,
                OwnerNewsroomArticle.visibility == "global",
            )
        else:
            stmt = stmt.where(
                or_(
                    OwnerNewsroomArticle.save_context_id == save_context_id,
                    OwnerNewsroomArticle.visibility == "global",
                )
            )
    elif allowed_saves is not None:
        if allowed_saves:
            stmt = stmt.where(
                or_(
                    OwnerNewsroomArticle.visibility == "global",
                    OwnerNewsroomArticle.save_context_id.in_(allowed_saves),
                )
            )
        else:
            stmt = stmt.where(OwnerNewsroomArticle.visibility == "global")

    if category and category != "all":
        stmt = stmt.where(OwnerNewsroomArticle.category == category)
    rows = session.scalars(stmt.limit(limit)).all()
    return [newsroom_dict(r) for r in rows]


get_owner_newsroom = list_newsroom_articles


def newsroom_dict(art: OwnerNewsroomArticle) -> dict[str, Any]:
    return {
        "id": art.id,
        "save_context_id": art.save_context_id,
        "club_id": art.club_id,
        "visibility": art.visibility,
        "category": art.category,
        "headline": art.headline,
        "subheadline": art.subheadline,
        "hero_image_url": art.hero_image_url,
        "club_crest_url": art.club_crest_url,
        "player_portrait_url": art.player_portrait_url,
        "established_facts": art.established_facts_json or {},
        "editorial_narration": art.editorial_narration,
        "grounding_report": art.grounding_report_json or {},
        "verified_price_gtex": str(art.verified_price_gtex) if art.verified_price_gtex is not None else None,
        "source_event_id": art.source_event_id,
        "status": art.status,
        "created_at": art.created_at.isoformat() if art.created_at else None,
    }


def record_match_news_article(
    session: Session,
    match: OwnerMatch,
    home_state: OwnerClubState,
    away_state: OwnerClubState,
) -> OwnerNewsroomArticle:
    save_ctx = f"competition:{match.competition_id}"
    home_name = home_state.club_name
    away_name = away_state.club_name
    home_crest = resolve_club_crest_url(session, match.home_club_id, home_name)
    facts = {
        "competition_id": match.competition_id,
        "round_number": match.round_number,
        "home_club": home_name,
        "away_club": away_name,
        "home_goals": match.home_score,
        "away_goals": match.away_score,
        "winner": (
            home_name
            if match.home_score > match.away_score
            else (away_name if match.away_score > match.home_score else "Draw")
        ),
    }
    hl, sub, narr = build_grounded_editorial("match_report", facts)
    grounding = validate_article_grounding(facts, narr)
    hero = resolve_stadium_image_url("stadium")
    art = OwnerNewsroomArticle(
        save_context_id=save_ctx,
        club_id=match.home_club_id,
        visibility="save",
        category="match_report",
        headline=hl,
        subheadline=sub,
        hero_image_url=hero,
        club_crest_url=home_crest,
        established_facts_json=facts,
        editorial_narration=narr,
        grounding_report_json=grounding,
        source_event_id=match.id,
        status="published",
        idempotency_key=f"match-news:{match.id}",
    )
    session.add(art)
    return art


def get_club_showroom(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    require_state(session, club_id, user_id)
    items = []
    for k, v in SHOWROOM_CATALOG.items():
        items.append(
            {
                **v,
                "image_url": resolve_showroom_image_url(k),
            }
        )
    owned = []
    # Fetch from OwnerBroadcastEvent or asset table
    b_rows = session.scalars(
        select(OwnerBroadcastEvent)
        .where(
            OwnerBroadcastEvent.club_id == club_id,
            OwnerBroadcastEvent.status == "active",
        )
        .order_by(OwnerBroadcastEvent.created_at.desc())
    ).all()
    for b in b_rows:
        owned.append(
            {
                "id": b.id,
                "catalog_key": b.event_type,
                "custom_name": b.item_name,
                "category": "jet" if b.event_type == "private_jet_purchase" else b.event_type,
                "purchase_price_gtex": float(b.verified_price_gtex or 0),
                "gifted_to_player_name": b.player_name,
                "image_url": b.item_image_url,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
        )
    return {
        "catalog": items,
        "owned_assets": owned,
    }


def purchase_showroom_asset(
    session: Session,
    user_id: str,
    club_id: str,
    catalog_key: str,
    custom_name: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    state = require_state(session, club_id, user_id)
    item = SHOWROOM_CATALOG.get(catalog_key)
    if not item:
        raise OwnerError("invalid_showroom_item", 400, f"Item {catalog_key} does not exist in catalog.")

    price = Decimal(str(item["price_gtex"]))
    club_acct = ledger.club_account(club_id)
    bal = ledger.balance(session, club_acct, ledger.GTEX)
    if bal < price:
        raise OwnerError("insufficient_club_cash", 400, f"Club cash {bal} GTX is insufficient for {price} GTX.")

    leg = ledger.record(
        session,
        event_type="showroom_asset_purchase",
        currency=ledger.GTEX,
        gross=price,
        source=club_acct,
        destination=ledger.WORLD_CLUBS,
        user_id=user_id,
        club_id=club_id,
        memo=f"Acquired {item['name']}",
    )

    image_url = resolve_showroom_image_url(catalog_key)
    c_name = custom_name or item["name"]

    # ONLY broadcast if category is jet!
    broadcast = None
    if item.get("broadcast_on_purchase") and item.get("category") == "jet":
        broadcast = record_verified_broadcast_event(
            session,
            event_type="private_jet_purchase",
            club_id=club_id,
            owner_user_id=user_id,
            item_name=c_name,
            item_model=item.get("model"),
            item_image_url=image_url,
            verified_price_gtex=price,
            ledger_event_id=leg.id,
            idempotency_key=idempotency_key,
        )

    # Apply prestige bonus
    state.prestige = min(100, state.prestige + item.get("prestige_bonus", 0))

    return {
        "asset": {
            "catalog_key": catalog_key,
            "custom_name": c_name,
            "price_gtex": str(price),
            "image_url": image_url,
        },
        "broadcast_globally": bool(broadcast),
        "broadcast_event": broadcast_dict(broadcast) if broadcast else None,
    }


def gift_asset_to_squad_player(
    session: Session,
    user_id: str,
    club_id: str,
    player_id: str,
    catalog_key: str | None = None,
    asset_id: str | None = None,
    note: str = "",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    require_state(session, club_id, user_id)
    player = session.get(OwnerSquadPlayer, player_id)
    if not player or player.club_id != club_id:
        raise OwnerError("player_not_found", 404, "Player not in club squad.")

    item_key = catalog_key or "chronos_tourbillon_watch"
    item = SHOWROOM_CATALOG.get(item_key)
    if not item or not item.get("can_gift_to_player"):
        raise OwnerError("invalid_gift_item", 400, "Item cannot be gifted to a player.")

    price = Decimal(str(item["price_gtex"]))
    club_acct = ledger.club_account(club_id)
    bal = ledger.balance(session, club_acct, ledger.GTEX)
    if bal < price:
        raise OwnerError("insufficient_club_cash", 400, f"Club cash {bal} GTX is insufficient for {price} GTX gift.")

    leg = ledger.record(
        session,
        event_type="squad_player_gift",
        currency=ledger.GTEX,
        gross=price,
        source=club_acct,
        destination=ledger.WORLD_CLUBS,
        user_id=user_id,
        club_id=club_id,
        memo=f"Owner gifted {item['name']} to {player.name}",
    )

    # Boost player morale
    old_morale = player.morale
    player.morale = min(100, player.morale + 15)

    player_portrait = resolve_player_portrait_url(session, player.id, player.name)
    item_image = resolve_showroom_image_url(item_key)

    broadcast = record_verified_broadcast_event(
        session,
        event_type="player_gift",
        club_id=club_id,
        owner_user_id=user_id,
        item_name=item["name"],
        item_model=item.get("model"),
        item_image_url=item_image,
        player_id=player.id,
        player_name=player.name,
        player_portrait_url=player_portrait,
        verified_price_gtex=price,
        ledger_event_id=leg.id,
        idempotency_key=idempotency_key,
    )

    # Generate acknowledgement inbox item
    ack = OwnerInboxItem(
        user_id=user_id,
        club_id=club_id,
        save_context_id=resolve_save_context_id(session, club_id),
        category="player_issues",
        kind="player_unrest",
        priority="low",
        sender=player.name,
        title=f"Thank You from {player.name}",
        what=f"{player.name} received your personal gift of the {item['name']}.",
        why=note or "Player morale boosted across the squad.",
        body=f"Boss, receiving the {item['name']} meant everything. I'm ready to leave everything on the pitch for the badge.",
        is_decision=False,
        status="resolved",
        resolution="acknowledged",
        outcome_text=f"Morale increased from {old_morale} to {player.morale}.",
        ai_generated=True,
    )
    session.add(ack)

    return {
        "player": {
            "id": player.id,
            "name": player.name,
            "morale": player.morale,
            "portrait_url": player_portrait,
        },
        "morale_delta": player.morale - old_morale,
        "asset": {
            "catalog_key": item_key,
            "custom_name": item["name"],
            "image_url": item_image,
        },
        "broadcast_event": broadcast_dict(broadcast) if broadcast else None,
    }


def ensure_default_watchlist(session: Session, state: OwnerClubState) -> list[OwnerScoutingWatchlist]:
    rows = session.scalars(
        select(OwnerScoutingWatchlist)
        .where(OwnerScoutingWatchlist.club_id == state.club_id)
        .order_by(OwnerScoutingWatchlist.created_at.desc())
    ).all()
    if rows:
        return list(rows)

    # Seed 2 realistic high-potential prospects
    save_ctx = resolve_save_context_id(session, state.club_id)
    defaults = [
        OwnerScoutingWatchlist(
            club_id=state.club_id,
            save_context_id=save_ctx,
            player_name="Tariq Danjuma",
            position="MID",
            age=18,
            current_rating=68,
            potential_rating=85,
            estimated_value_gtex=Decimal("120.0000"),
            priority="high",
            scout_notes="Rapid dynamic box-to-box midfielder with exceptional passing range.",
            recommendation="Direct approach before regional competition entry",
        ),
        OwnerScoutingWatchlist(
            club_id=state.club_id,
            save_context_id=save_ctx,
            player_name="Emeka Sterling",
            position="FWD",
            age=19,
            current_rating=70,
            potential_rating=87,
            estimated_value_gtex=Decimal("190.0000"),
            priority="medium",
            scout_notes="Explosive inverted winger with high conversion rate under pressure.",
            recommendation="Monitor matchday performances",
        ),
    ]
    for d in defaults:
        session.add(d)
    session.flush()
    return defaults


def watchlist_dict(r: OwnerScoutingWatchlist) -> dict[str, Any]:
    return {
        "id": r.id,
        "club_id": r.club_id,
        "save_context_id": r.save_context_id,
        "player_id": r.player_id,
        "player_name": r.player_name,
        "position": r.position,
        "age": r.age,
        "current_rating": r.current_rating,
        "potential_rating": r.potential_rating,
        "estimated_value_gtex": float(r.estimated_value_gtex or 0),
        "priority": r.priority,
        "scout_notes": r.scout_notes,
        "recommendation": r.recommendation,
        "portrait_url": resolve_player_portrait_url(None, r.id, r.player_name),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def add_to_watchlist(
    session: Session,
    user_id: str,
    club_id: str,
    *,
    player_id: str | None = None,
    player_name: str | None = None,
    position: str = "MID",
    age: int = 19,
    current_rating: int = 68,
    potential_rating: int = 83,
    estimated_value_gtex: float = 120.0,
    priority: str = "medium",
    scout_notes: str = "",
    recommendation: str = "Monitor closely",
) -> dict[str, Any]:
    require_state(session, club_id, user_id)
    save_ctx = resolve_save_context_id(session, club_id)
    name = player_name or "Target Prospect"
    item = OwnerScoutingWatchlist(
        club_id=club_id,
        save_context_id=save_ctx,
        player_id=player_id,
        player_name=name,
        position=position,
        age=age,
        current_rating=current_rating,
        potential_rating=potential_rating,
        estimated_value_gtex=Decimal(str(estimated_value_gtex)),
        priority=priority,
        scout_notes=scout_notes,
        recommendation=recommendation,
    )
    session.add(item)
    session.flush()
    return watchlist_dict(item)


def remove_from_watchlist(
    session: Session,
    user_id: str,
    club_id: str,
    item_id: str,
) -> dict[str, Any]:
    require_state(session, club_id, user_id)
    item = session.get(OwnerScoutingWatchlist, item_id)
    if not item or item.club_id != club_id:
        raise OwnerError("watchlist_item_not_found", 404, "Watchlist item not found.")
    session.delete(item)
    return {"status": "deleted", "id": item_id}


def build_club_story(session: Session, user_id: str, club_id: str) -> dict[str, Any]:
    state = _get_club_state(session, club_id)
    if not state:
        raise OwnerError("club_not_found", 404, "Club state not found.")

    profile = session.get(ClubProfile, club_id)
    is_owner = state.owner_user_id == user_id
    can_private = can_view_private_club_data(session, user_id, club_id)
    save_ctx = resolve_save_context_id(session, club_id)

    # 1. Timeline: Combine verified broadcasts and matches
    timeline: list[dict[str, Any]] = []
    b_rows = session.scalars(
        select(OwnerBroadcastEvent)
        .where(OwnerBroadcastEvent.club_id == club_id, OwnerBroadcastEvent.status == "active")
        .order_by(OwnerBroadcastEvent.created_at.desc())
        .limit(20)
    ).all()
    for b in b_rows:
        timeline.append(
            {
                "id": b.id,
                "type": "broadcast",
                "category": b.event_type,
                "title": b.headline,
                "summary": b.summary,
                "verified_price_gtex": str(b.verified_price_gtex) if b.verified_price_gtex is not None else None,
                "image_url": b.item_image_url,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
        )

    # Add matches
    match_rows = session.scalars(
        select(OwnerMatch)
        .where(or_(OwnerMatch.home_club_id == club_id, OwnerMatch.away_club_id == club_id))
        .order_by(OwnerMatch.played_at.desc(), OwnerMatch.round_number.desc())
        .limit(10)
    ).all()
    for m in match_rows:
        timeline.append(
            {
                "id": m.id,
                "type": "match",
                "category": "match_result" if m.status == "completed" else "fixture",
                "title": (
                    f"Match Round {m.round_number}: {m.home_goals} - {m.away_goals}"
                    if m.status == "completed"
                    else f"Scheduled vs Round {m.round_number}"
                ),
                "summary": f"{m.status.capitalize()} fixture in competition.",
                "image_url": resolve_stadium_image_url("stadium"),
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
        )
    timeline.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    # 2. Unresolved Issues (Redacted for non-owners)
    unresolved_issues: list[dict[str, Any]] = []
    if can_private:
        items = session.scalars(
            select(OwnerInboxItem)
            .where(
                OwnerInboxItem.club_id == club_id,
                OwnerInboxItem.status == "open",
                OwnerInboxItem.archived_at.is_(None),
            )
            .order_by(OwnerInboxItem.created_at.desc())
            .limit(10)
        ).all()
        from app.owner_console.service import inbox_dict

        unresolved_issues = [inbox_dict(i) for i in items]

    # 3. Staff & Player Relationships
    manager_data = state.manager_json or {}
    squad_players = session.scalars(
        select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == club_id).order_by(OwnerSquadPlayer.rating.desc())
    ).all()

    relationships = {
        "manager": {
            "name": manager_data.get("name") or "First Team Manager",
            "mood": manager_data.get("mood", 70),
            "loyalty": manager_data.get("loyalty", 12),
            "tactical_preference": manager_data.get("tactical_preference", "Balanced Possession"),
            "temperament": manager_data.get("temperament", "ambitious"),
            "relationship_status": "strong" if manager_data.get("mood", 70) >= 65 else "steady",
        },
        "players": [
            {
                "player_id": p.id,
                "name": p.name,
                "position": p.position,
                "rating": p.rating,
                "morale": p.morale,
                "trust_level": "devoted" if p.morale >= 80 else "committed" if p.morale >= 60 else "cautious",
                "contract_expectation": "Wants first-team guarantees" if can_private and p.morale < 60 else None,
                "portrait_url": resolve_player_portrait_url(session, p.id, p.name),
            }
            for p in squad_players[:12]
        ],
    }

    # 4. Scouting Watchlist (Redacted for non-owners)
    scouting_watchlist: list[dict[str, Any]] = []
    if can_private:
        w_rows = ensure_default_watchlist(session, state)
        scouting_watchlist = [watchlist_dict(w) for w in w_rows]

    # 5. Upcoming Schedule & Recent Results
    entries = session.scalars(select(OwnerCompetitionEntry).where(OwnerCompetitionEntry.club_id == club_id)).all()
    comp_ids = list({e.competition_id for e in entries})
    upcoming: list[dict[str, Any]] = []
    recent: list[dict[str, Any]] = []
    if comp_ids:
        for m in session.scalars(
            select(OwnerMatch).where(OwnerMatch.competition_id.in_(comp_ids)).order_by(OwnerMatch.round_number.asc())
        ).all():
            if m.home_club_id == club_id or m.away_club_id == club_id:
                m_card = {
                    "id": m.id,
                    "competition_id": m.competition_id,
                    "round": m.round_number,
                    "home_club_id": m.home_club_id,
                    "away_club_id": m.away_club_id,
                    "home_name": (
                        _get_club_state(session, m.home_club_id).club_name
                        if _get_club_state(session, m.home_club_id)
                        else "Home Club"
                    ),
                    "away_name": (
                        _get_club_state(session, m.away_club_id).club_name
                        if _get_club_state(session, m.away_club_id)
                        else "Away Club"
                    ),
                    "status": m.status,
                    "home_goals": m.home_score,
                    "away_goals": m.away_score,
                }
                (upcoming if m.status == "scheduled" else recent).append(m_card)

    # 6. Club News (Public & Save news)
    club_news = list_newsroom_articles(session, club_id=club_id, limit=8)

    # 7. Achievements & Owner Legacy
    achievements = [
        {
            "id": "starter-foundation",
            "title": "Foundation Formed",
            "detail": "Official club charter ratified on World Day 1.",
            "badge": "milestone",
        },
        {
            "id": "prestige-tier",
            "title": f"Prestige Level {state.prestige}",
            "detail": "Boardroom reputation benchmark achieved.",
            "badge": "reputation",
        },
    ]
    if len(squad_players) >= 16:
        achievements.append(
            {
                "id": "squad-ready",
                "title": "Squad Depth Certified",
                "detail": f"Roster of {len(squad_players)} players registered.",
                "badge": "squad",
            }
        )
    if any(b.event_type == "private_jet_purchase" for b in b_rows):
        achievements.append(
            {
                "id": "aviation-tier",
                "title": "Fleet Aviation Owner",
                "detail": "Executive private jet commissioned for squad transit.",
                "badge": "luxury",
            }
        )

    wins = sum(
        1
        for m in recent
        if (m["home_club_id"] == club_id and m["home_goals"] > m["away_goals"])
        or (m["away_club_id"] == club_id and m["away_goals"] > m["home_goals"])
    )
    total_played = len(recent)
    win_rate = int((wins / total_played) * 100) if total_played > 0 else 0

    owner_legacy = {
        "prestige": state.prestige,
        "fans": state.fans,
        "matches_played": total_played,
        "wins": wins,
        "win_rate_pct": win_rate,
        "trophies_count": len([a for a in achievements if a.get("badge") == "silverware"]),
        "prestige_assets_owned": len(b_rows),
        "tier": (
            "Continental Contender"
            if state.prestige >= 60
            else "Emerging Force" if state.prestige >= 40 else "Developing Club"
        ),
        "composite_score": int(state.prestige * 0.4 + win_rate * 0.3 + min(100, len(squad_players) * 4) * 0.3),
        "era_label": f"Day {state.world_day} Era",
        "on_pitch": win_rate,
        "talent_factory": min(100, int((state.facilities_json or {}).get("academy", 1) * 20)),
        "commercial": min(100, int((state.facilities_json or {}).get("commercial", 1) * 20)),
        "culture": min(100, int((state.facilities_json or {}).get("training", 1) * 20)),
        "ownership_group": {
            "label": (
                f"Multi-Club Group ({state.owner_user_id[:6]})"
                if len(
                    session.scalars(
                        select(OwnerClubState).where(OwnerClubState.owner_user_id == state.owner_user_id)
                    ).all()
                )
                > 1
                else "Independent Ownership"
            ),
        },
    }

    return {
        "club": {
            "club_id": state.club_id,
            "club_name": state.club_name,
            "short_name": profile.short_name if profile else None,
            "crest_url": resolve_club_crest_url(session, club_id, state.club_name),
            "stadium_image_url": resolve_stadium_image_url("stadium"),
            "city": profile.city_name if profile else None,
            "country_code": profile.country_code if profile else None,
            "world_day": state.world_day,
            "value": str(state.fans * 10 + state.prestige * 500),
            "primary_color": profile.primary_color if profile else "#0F766E",
            "secondary_color": profile.secondary_color if profile else "#0F172A",
        },
        "save_context_id": save_ctx,
        "is_owner": is_owner,
        "privacy_redacted": not can_private,
        "timeline": timeline,
        "unresolved_issues": unresolved_issues,
        "relationships": relationships,
        "scouting_watchlist": scouting_watchlist,
        "upcoming_schedule": upcoming,
        "recent_results": recent,
        "club_news": club_news,
        "achievements": achievements,
        "owner_legacy": owner_legacy,
    }
