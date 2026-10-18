"""Phase 6 sponsors: zones, contracts, preview, publish, delivery, and renewal.

Commercial inventory is the sponsor zones shirt front, sleeve, and board.
A contract names the zones it bought and the fee. Preview and compose
suggestions never publish a kit. Publish creates a kit version only after a
human approves the contract, and the published zones must equal the contract
zones. Payment and delivery each write a ledger line and an audit row.
Renewal opens a new contract linked to the previous one.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError, require_owner
from app.club_legacy.full.support import money
from app.club_legacy.ledger import post_club_legacy_transfer
from app.club_legacy.models import (
    ClubLegacyAuditEvent,
    ClubLegacyKitVersion,
    ClubLegacySponsorContract,
    ClubLegacySponsorZone,
)
from app.owner_console import ledger

COMMERCIAL_ZONES = ("shirt_front", "sleeve", "board")
LEGACY_ZONE_ALIASES = {"front": "front", "shirt": "shirt_front", "shirt_front": "shirt_front"}


def commercial_inventory() -> list[dict]:
    return [
        {"zone": "shirt_front", "label": "Shirt front"},
        {"zone": "sleeve", "label": "Sleeve"},
        {"zone": "board", "label": "Board"},
    ]


def offer_sponsor(
    session: Session,
    *,
    club_id: str,
    user_id: str,
    sponsor_name: str,
    placement: str,
    fee,
    zones: list[str] | None = None,
) -> ClubLegacySponsorContract:
    require_owner(session, club_id, user_id)
    named = _normalize_zones(zones if zones is not None else [placement])
    if placement not in named:
        placement = named[0]
    contract = ClubLegacySponsorContract(
        club_id=club_id,
        sponsor_name=sponsor_name,
        placement=placement,
        fee=money(fee),
        status="offered",
    )
    session.add(contract)
    session.flush()
    for zone in named:
        session.add(ClubLegacySponsorZone(contract_id=contract.id, zone=zone))
    session.flush()
    return contract


def _normalize_zones(zones: list[str]) -> list[str]:
    if not zones:
        raise LegacyError("zones_required", 409, "A sponsor contract names at least one zone.")
    named: list[str] = []
    allowed = set(COMMERCIAL_ZONES) | set(LEGACY_ZONE_ALIASES)
    for zone in zones:
        if zone not in allowed:
            raise LegacyError("unknown_zone", 409, f"{zone} is not a commercial sponsor zone.")
        canonical = LEGACY_ZONE_ALIASES.get(zone, zone)
        if canonical not in named:
            named.append(canonical)
    return named


def contract_zones(session: Session, contract: ClubLegacySponsorContract) -> dict[str, str]:
    rows = session.scalars(
        select(ClubLegacySponsorZone).where(ClubLegacySponsorZone.contract_id == contract.id).order_by(ClubLegacySponsorZone.zone)
    ).all()
    if not rows:
        return {contract.placement: contract.placement}
    return {row.zone: row.zone for row in rows}


def _audit(session: Session, *, club_id: str, actor_user_id: str | None, action: str, detail: dict) -> None:
    session.add(
        ClubLegacyAuditEvent(club_id=club_id, actor_user_id=actor_user_id, action=action, detail_json=detail)
    )


def approve_sponsor(session: Session, *, contract_id: str, user_id: str) -> ClubLegacySponsorContract:
    contract = session.get(ClubLegacySponsorContract, contract_id)
    if contract is None:
        raise LegacyError("contract_not_found", 404)
    require_owner(session, contract.club_id, user_id)
    if contract.status == "approved":
        return contract
    if contract.status != "offered":
        raise LegacyError("sponsor_not_offered", 409)
    contract.status = "approved"
    source = ledger.wallet_account(session, ledger.PLATFORM_SPONSORS, ledger.GTEX)
    destination = ledger.wallet_account(session, ledger.club_account(contract.club_id), ledger.GTEX)
    post_club_legacy_transfer(
        session,
        idempotency_key=f"sponsor:{contract.id}",
        source=source,
        destination=destination,
        amount=contract.fee,
        description=f"Sponsor {contract.sponsor_name}",
    )
    _audit(
        session,
        club_id=contract.club_id,
        actor_user_id=user_id,
        action="sponsor_payment",
        detail={"contract_id": contract.id, "fee": str(contract.fee), "human_approved": True},
    )
    _audit(
        session,
        club_id=contract.club_id,
        actor_user_id=user_id,
        action="sponsor_approved",
        detail={"contract_id": contract.id, "approved_by": user_id},
    )
    session.flush()
    return contract


def _human_approved(session: Session, contract: ClubLegacySponsorContract) -> bool:
    if contract.status != "approved":
        return False
    events = session.scalars(
        select(ClubLegacyAuditEvent).where(
            ClubLegacyAuditEvent.club_id == contract.club_id,
            ClubLegacyAuditEvent.action == "sponsor_approved",
        )
    ).all()
    return any((event.detail_json or {}).get("contract_id") == contract.id for event in events)


def preview_kit(session: Session, *, club_id: str, user_id: str, contract_id: str, template_name: str) -> dict:
    """Show the kit a human could publish. This does not create a kit version."""
    require_owner(session, club_id, user_id)
    contract = session.get(ClubLegacySponsorContract, contract_id)
    if contract is None or contract.club_id != club_id:
        raise LegacyError("contract_not_found", 404)
    return {
        "status": "preview",
        "published": False,
        "template_name": template_name,
        "zones": contract_zones(session, contract),
        "contract_id": contract.id,
    }


def suggest_kit(
    session: Session, *, club_id: str, user_id: str, contract_id: str
) -> dict:
    """A compose suggestion may propose zones. It cannot approve or publish."""
    require_owner(session, club_id, user_id)
    contract = session.get(ClubLegacySponsorContract, contract_id)
    if contract is None or contract.club_id != club_id:
        raise LegacyError("contract_not_found", 404)
    proposed = {zone: zone for zone in COMMERCIAL_ZONES}
    _audit(
        session,
        club_id=club_id,
        actor_user_id=user_id,
        action="sponsor_suggestion",
        detail={"contract_id": contract.id, "zones": proposed, "can_publish": False},
    )
    session.flush()
    return {"status": "suggestion", "published": False, "can_publish": False, "zones": proposed, "contract_id": contract.id}


def publish_kit(
    session: Session, *, club_id: str, user_id: str, contract_id: str, template_name: str, zones: dict
) -> ClubLegacyKitVersion:
    require_owner(session, club_id, user_id)
    contract = session.get(ClubLegacySponsorContract, contract_id)
    if contract is None or contract.club_id != club_id:
        raise LegacyError("contract_not_found", 404)
    if not _human_approved(session, contract):
        raise LegacyError("sponsor_not_approved", 409, "Publish only after the sponsor contract is approved.")
    expected = contract_zones(session, contract)
    placement_matches = zones.get("front") == contract.placement or contract.placement in zones.values()
    if not placement_matches or zones != expected:
        raise LegacyError("placement_mismatch", 409, "Published zones must match the contract zones.")
    existing = session.scalar(
        select(ClubLegacyKitVersion).where(
            ClubLegacyKitVersion.contract_id == contract.id,
            ClubLegacyKitVersion.status == "published",
        )
    )
    if existing is not None:
        return existing
    version = (
        session.scalar(select(func.count()).select_from(ClubLegacyKitVersion).where(ClubLegacyKitVersion.club_id == club_id))
        or 0
    ) + 1
    kit = ClubLegacyKitVersion(
        club_id=club_id,
        version=int(version),
        template_name=template_name,
        zones_json=dict(zones),
        status="published",
        contract_id=contract.id,
    )
    session.add(kit)
    _audit(
        session,
        club_id=club_id,
        actor_user_id=user_id,
        action="kit_published",
        detail={"contract_id": contract.id, "zones": expected, "version": int(version)},
    )
    session.flush()
    return kit


def report_delivery(
    session: Session, *, contract_id: str, user_id: str, impressions: int, note: str
) -> ClubLegacySponsorContract:
    contract = session.get(ClubLegacySponsorContract, contract_id)
    if contract is None or contract.status != "approved":
        raise LegacyError("delivery_unavailable", 409)
    require_owner(session, contract.club_id, user_id)
    if impressions < 0:
        raise LegacyError("invalid_impressions")
    contract.impressions = impressions
    contract.delivery_report = note
    contract.status = "completed"
    source = ledger.wallet_account(session, "legacy:delivery_recognized", ledger.GTEX)
    destination = ledger.wallet_account(session, "legacy:delivery_reported", ledger.GTEX)
    post_club_legacy_transfer(
        session,
        idempotency_key=f"delivery:{contract.id}",
        source=source,
        destination=destination,
        amount=money("1.00"),
        description=f"Delivery {impressions} impressions: {note}"[:255],
    )
    _audit(
        session,
        club_id=contract.club_id,
        actor_user_id=user_id,
        action="sponsor_delivery",
        detail={"contract_id": contract.id, "impressions": impressions, "note": note},
    )
    session.flush()
    return contract


def renew_sponsor(session: Session, *, contract_id: str, user_id: str) -> ClubLegacySponsorContract:
    previous = session.get(ClubLegacySponsorContract, contract_id)
    if previous is None or previous.status != "completed":
        raise LegacyError("renewal_unavailable", 409)
    require_owner(session, previous.club_id, user_id)
    zones = list(contract_zones(session, previous))
    renewed = ClubLegacySponsorContract(
        club_id=previous.club_id,
        sponsor_name=previous.sponsor_name,
        placement=previous.placement,
        fee=previous.fee,
        status="offered",
        renewed_from_id=previous.id,
    )
    session.add(renewed)
    session.flush()
    for zone in zones:
        session.add(ClubLegacySponsorZone(contract_id=renewed.id, zone=zone))
    _audit(
        session,
        club_id=previous.club_id,
        actor_user_id=user_id,
        action="sponsor_renewed",
        detail={"contract_id": renewed.id, "renewed_from_id": previous.id, "zones": zones},
    )
    session.flush()
    return renewed


def contract_dict(session: Session, contract: ClubLegacySponsorContract) -> dict:
    return {
        "id": contract.id,
        "club_id": contract.club_id,
        "sponsor_name": contract.sponsor_name,
        "placement": contract.placement,
        "zones": list(contract_zones(session, contract)),
        "fee": str(contract.fee),
        "status": contract.status,
        "impressions": contract.impressions,
        "delivery_report": contract.delivery_report,
        "renewed_from_id": contract.renewed_from_id,
    }
