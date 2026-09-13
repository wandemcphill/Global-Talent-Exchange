from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.ingestion.models import Player
from app.models.base import utcnow
from app.models.club_growth import AcademyRegenContractOffer
from app.models.player_contract import PlayerContract


class AcademyContractBridgeError(ValueError):
    """Raised when an academy promotion cannot be represented canonically."""


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def ensure_academy_player_contract(*, service, club_id: str, prospect_id: str) -> PlayerContract:
    """Idempotently materialize the accepted academy offer as the canonical PlayerContract.

    ``wage_minor`` is copied exactly into the existing PlayerContract decimal field.
    No new exchange-rate or salary-conversion rule is introduced here. The academy
    offer already owns the salary value; this bridge only carries it across lifecycle
    boundaries.
    """
    session = service.session
    offer = session.scalar(
        select(AcademyRegenContractOffer)
        .where(
            AcademyRegenContractOffer.club_id == club_id,
            AcademyRegenContractOffer.prospect_id == prospect_id,
            AcademyRegenContractOffer.status == "accepted",
        )
        .order_by(AcademyRegenContractOffer.created_at.desc())
    )
    if offer is None:
        raise AcademyContractBridgeError("accepted academy contract offer not found")

    player = session.scalar(
        select(Player).where(Player.provider_external_id == f"academy:{prospect_id}")
    )
    if player is None:
        raise AcademyContractBridgeError("canonical academy player not found")

    existing = session.scalar(
        select(PlayerContract)
        .where(
            PlayerContract.player_id == player.id,
            PlayerContract.club_id == club_id,
            PlayerContract.status.in_(("active", "expiring")),
        )
        .order_by(PlayerContract.starts_on.desc(), PlayerContract.created_at.desc())
    )
    if existing is not None:
        if player.current_club_profile_id != club_id:
            player.current_club_profile_id = club_id
        session.flush()
        return existing

    other_active = session.scalar(
        select(PlayerContract).where(
            PlayerContract.player_id == player.id,
            PlayerContract.status.in_(("active", "expiring")),
        )
    )
    if other_active is not None:
        raise AcademyContractBridgeError(
            "canonical academy player already has an active contract with another club"
        )

    starts_on = utcnow().date()
    ends_on = _add_months(starts_on, max(1, int(offer.duration_months))) - timedelta(days=1)
    contract = PlayerContract(
        player_id=player.id,
        club_id=club_id,
        status="active",
        wage_amount=Decimal(str(offer.wage_minor)),
        bonus_terms=None,
        release_clause_amount=None,
        signed_on=starts_on,
        starts_on=starts_on,
        ends_on=ends_on,
    )
    session.add(contract)
    player.current_club_profile_id = club_id
    session.flush()
    return contract
