from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.ingestion.models import Player
from app.models.club_growth import AcademyRegenContractOffer
from app.models.player_contract import PlayerContract
from app.schemas.player_lifecycle import ContractCreateRequest
from app.services.player_lifecycle_service import PlayerLifecycleService


ACADEMY_CONTRACT_WAGE_UNIT = "FanCoin"


class AcademyContractBridgeError(ValueError):
    """Raised when an academy promotion cannot be represented canonically."""


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def ensure_academy_player_contract(*, service, club_id: str, prospect_id: str) -> PlayerContract:
    """Idempotently bridge an accepted academy offer into PlayerLifecycleService."""
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

    starts_on = date.today()
    ends_on = _add_months(starts_on, max(1, int(offer.duration_months))) - timedelta(days=1)

    contract = PlayerLifecycleService(session).create_contract(
        player.id,
        ContractCreateRequest(
            club_id=club_id,
            # AcademyRegenContractOffer.wage_minor is already expressed in the
            # canonical FanCoin salary unit used by PlayerContract.
            wage_amount=Decimal(str(offer.wage_minor)),
            bonus_terms="Academy graduation contract.",
            release_clause_amount=None,
            starts_on=starts_on,
            ends_on=ends_on,
            signed_on=starts_on,
        ),
        reference_on=starts_on,
    )
    return contract
