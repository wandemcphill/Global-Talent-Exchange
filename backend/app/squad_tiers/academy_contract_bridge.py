from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.club_growth import AcademyRegenContractOffer
from app.models.club_squad_tier import ClubSquadTierMembership
from app.models.player_contract import PlayerContract


def _add_months(value: date, months: int) -> date:
    total = value.year * 12 + (value.month - 1) + months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


@event.listens_for(ClubSquadTierMembership, "after_insert")
def _ensure_academy_player_contract(
    _mapper: object,
    connection: object,
    target: ClubSquadTierMembership,
) -> None:
    """Promotion creates exactly one active canonical PlayerContract.

    Academy promotion already uses SquadTierService as its canonical bridge.
    This listener closes the remaining persistence gap without creating a
    second player or second promotion path. It only fires for the explicit
    academy promotion source and is idempotent against an existing active
    contract.
    """
    if target.source != "academy_promotion" or target.status != "active":
        return

    session = Session(bind=connection, future=True)
    try:
        active_contract = session.scalar(
            select(PlayerContract).where(
                PlayerContract.player_id == target.player_id,
                PlayerContract.status == "active",
            )
        )
        if active_contract is not None:
            if active_contract.club_id != target.club_id:
                raise ValueError("academy_player_contract_club_mismatch")
            return

        player = session.get(Player, target.player_id)
        if player is None:
            raise ValueError("academy_player_missing_for_contract")

        external_id = str(player.provider_external_id or "")
        if not external_id.startswith("academy:"):
            raise ValueError("academy_promotion_player_identity_missing")
        prospect_id = external_id.split(":", 1)[1]

        offer = session.scalar(
            select(AcademyRegenContractOffer)
            .where(
                AcademyRegenContractOffer.prospect_id == prospect_id,
                AcademyRegenContractOffer.club_id == target.club_id,
                AcademyRegenContractOffer.status == "accepted",
            )
            .order_by(AcademyRegenContractOffer.updated_at.desc())
        )
        if offer is None:
            raise ValueError("academy_accepted_contract_offer_missing")
        if offer.duration_months <= 0:
            raise ValueError("academy_contract_duration_invalid")

        signed_on = date.today()
        ends_on = _add_months(signed_on, offer.duration_months)
        session.add(
            PlayerContract(
                id=str(uuid4()),
                player_id=player.id,
                club_id=target.club_id,
                status="active",
                wage_amount=Decimal(str(offer.wage_minor)),
                signed_on=signed_on,
                starts_on=signed_on,
                ends_on=ends_on,
            )
        )
        session.flush()
    finally:
        session.close()
