from __future__ import annotations

from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import event, select
from sqlalchemy.engine import Connection

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
    connection: Connection,
    target: ClubSquadTierMembership,
) -> None:
    """Promotion creates exactly one active canonical PlayerContract.

    Academy promotion already uses SquadTierService as its canonical bridge.
    This listener closes the remaining persistence gap without creating a
    second player or second promotion path. It only fires for the explicit
    academy promotion source and uses the caller's transaction connection.
    """
    if target.source != "academy_promotion" or target.status != "active":
        return

    player_row = connection.execute(
        select(Player.__table__.c.id, Player.__table__.c.provider_external_id).where(
            Player.__table__.c.id == target.player_id
        )
    ).first()
    if player_row is None:
        raise ValueError("academy_player_missing_for_contract")

    external_id = str(player_row.provider_external_id or "")
    if not external_id.startswith("academy:"):
        raise ValueError("academy_promotion_player_identity_missing")
    prospect_id = external_id.split(":", 1)[1]

    active_contract = connection.execute(
        select(PlayerContract.__table__.c.id, PlayerContract.__table__.c.club_id).where(
            PlayerContract.__table__.c.player_id == target.player_id,
            PlayerContract.__table__.c.status == "active",
        )
    ).first()
    if active_contract is not None:
        if active_contract.club_id != target.club_id:
            raise ValueError("academy_player_contract_club_mismatch")
        return

    offer_row = connection.execute(
        select(
            AcademyRegenContractOffer.__table__.c.wage_minor,
            AcademyRegenContractOffer.__table__.c.duration_months,
        )
        .where(
            AcademyRegenContractOffer.__table__.c.prospect_id == prospect_id,
            AcademyRegenContractOffer.__table__.c.club_id == target.club_id,
            AcademyRegenContractOffer.__table__.c.status == "accepted",
        )
        .order_by(AcademyRegenContractOffer.__table__.c.updated_at.desc())
    ).first()
    if offer_row is None:
        raise ValueError("academy_accepted_contract_offer_missing")
    if int(offer_row.duration_months) <= 0:
        raise ValueError("academy_contract_duration_invalid")

    signed_on = date.today()
    ends_on = _add_months(signed_on, int(offer_row.duration_months))
    connection.execute(
        PlayerContract.__table__.insert().values(
            id=str(uuid4()),
            player_id=target.player_id,
            club_id=target.club_id,
            status="active",
            wage_amount=Decimal(str(offer_row.wage_minor)),
            signed_on=signed_on,
            starts_on=signed_on,
            ends_on=ends_on,
        )
    )
