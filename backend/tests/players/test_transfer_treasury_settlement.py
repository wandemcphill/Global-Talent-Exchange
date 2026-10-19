from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_finance import models as _club_finance_models  # noqa: F401
from app.common.enums.contract_status import ContractStatus
from app.models.player_contract import PlayerContract
from app.models.transfer_bid import TransferBid
from app.owner_console import ledger
from app.owner_console.models import LedgerEvent
from app.schemas.player_lifecycle import ContractCreateRequest, TransferBidAcceptRequest, TransferBidCreateRequest
from app.services.player_lifecycle_service import PlayerLifecycleService, PlayerLifecycleValidationError
from tests.players.test_player_lifecycle import add_window, seed_base_context

BID_AMOUNT = Decimal("4500000.00")
TRANSFER_DAY = date(2026, 3, 12)


def _treasury(session: Session, club_id: str) -> Decimal:
    return ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)


def _platform_fees(session: Session) -> Decimal:
    return ledger.balance(session, ledger.PLATFORM_FEES, ledger.GTEX)


def _set_treasury(session: Session, club_id: str, target: Decimal) -> None:
    excess = _treasury(session, club_id) - target
    ledger.record(
        session,
        event_type="owner_distribution",
        source=ledger.club_account(club_id),
        destination=ledger.WORLD_CLUBS,
        currency=ledger.GTEX,
        gross=excess,
        club_id=club_id,
    )
    session.commit()


def _seed(session: Session) -> tuple[PlayerLifecycleService, dict[str, str], str, PlayerContract]:
    service = PlayerLifecycleService(session)
    context = seed_base_context(session)
    window = add_window(session, window_id="window-treasury", opens_on=date(2026, 3, 1), closes_on=date(2026, 3, 31))
    contract = service.create_contract(
        context["player_id"],
        ContractCreateRequest(
            club_id=context["club_profile_id"],
            wage_amount=Decimal("80000.00"),
            signed_on=date(2025, 7, 1),
            starts_on=date(2025, 7, 1),
            ends_on=date(2026, 12, 31),
        ),
    )
    return service, context, window.id, contract


def _create_bid(service: PlayerLifecycleService, window_id: str, context: dict[str, str]) -> TransferBid:
    return service.create_bid(
        window_id,
        TransferBidCreateRequest(
            player_id=context["player_id"],
            buying_club_id=context["buyer_profile_id"],
            bid_amount=BID_AMOUNT,
            wage_offer_amount=Decimal("95000.00"),
        ),
        submitted_on=TRANSFER_DAY,
    )


def _accept(service: PlayerLifecycleService, window_id: str, bid_id: str) -> TransferBid:
    return service.accept_bid(
        window_id,
        bid_id,
        TransferBidAcceptRequest(
            contract_ends_on=date(2028, 6, 30),
            contract_starts_on=TRANSFER_DAY,
            wage_amount=Decimal("95000.00"),
            signed_on=TRANSFER_DAY,
        ),
        reference_on=TRANSFER_DAY,
    )


def test_bid_is_rejected_when_buying_club_treasury_cannot_cover_it(lifecycle_session: Session) -> None:
    service, context, window_id, _ = _seed(lifecycle_session)
    _set_treasury(lifecycle_session, context["buyer_profile_id"], BID_AMOUNT - Decimal("0.01"))

    with pytest.raises(PlayerLifecycleValidationError, match="treasury"):
        _create_bid(service, window_id, context)

    assert lifecycle_session.scalars(select(TransferBid)).all() == []


def test_accepted_transfer_moves_fee_between_club_treasuries_with_platform_cut(lifecycle_session: Session) -> None:
    service, context, window_id, _ = _seed(lifecycle_session)
    buyer_before = _treasury(lifecycle_session, context["buyer_profile_id"])
    seller_before = _treasury(lifecycle_session, context["club_profile_id"])
    fees_before = _platform_fees(lifecycle_session)

    bid = _create_bid(service, window_id, context)
    assert _treasury(lifecycle_session, context["buyer_profile_id"]) == buyer_before

    _accept(service, window_id, bid.id)
    _accept(service, window_id, bid.id)

    assert _treasury(lifecycle_session, context["buyer_profile_id"]) == buyer_before - BID_AMOUNT
    assert _treasury(lifecycle_session, context["club_profile_id"]) == seller_before + Decimal("3600000.00")
    assert _platform_fees(lifecycle_session) == fees_before + Decimal("900000.00")
    events = lifecycle_session.scalars(select(LedgerEvent).where(LedgerEvent.event_type == "transfer_purchase")).all()
    assert len(events) == 1
    assert events[0].related_object_id == bid.id
    assert events[0].platform_fee == Decimal("900000.00")


def test_acceptance_fails_without_side_effects_when_treasury_was_spent_after_bidding(
    lifecycle_session: Session,
) -> None:
    service, context, window_id, old_contract = _seed(lifecycle_session)
    bid = _create_bid(service, window_id, context)
    _set_treasury(lifecycle_session, context["buyer_profile_id"], Decimal("1000.00"))
    seller_before = _treasury(lifecycle_session, context["club_profile_id"])

    with pytest.raises(PlayerLifecycleValidationError, match="treasury"):
        _accept(service, window_id, bid.id)
    lifecycle_session.rollback()

    lifecycle_session.refresh(old_contract)
    assert old_contract.status == ContractStatus.ACTIVE.value
    assert old_contract.ends_on == date(2026, 12, 31)
    assert _treasury(lifecycle_session, context["buyer_profile_id"]) == Decimal("1000.00")
    assert _treasury(lifecycle_session, context["club_profile_id"]) == seller_before
