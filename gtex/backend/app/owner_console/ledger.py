from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.owner_console.models import LedgerEvent, OwnerWithdrawal

GTEX = "GTEX_COIN"
FAN = "FAN_COIN"
PLATFORM_FEES = "platform:fees"
PLATFORM_GRANTS = "platform:grants"
PLATFORM_SPONSORS = "platform:sponsor_pool"
WORLD_MARKET = "world:market"
WORLD_CLUBS = "world:clubs"
PAYSTACK = "external:paystack"
BANK_OUT = "external:bank_payout"
LIVE_STATUSES = ("completed", "pending_review", "held")


class LedgerError(ValueError):
    pass


def D(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def user_account(user_id: str) -> str:
    return f"user:{user_id}"


def club_account(club_id: str) -> str:
    return f"club:{club_id}"


def record(
    session: Session,
    *,
    event_type: str,
    source: str,
    destination: str,
    currency: str,
    gross,
    fee_bps: int = 0,
    balance_class: str = "earned",
    status: str = "completed",
    club_id: str | None = None,
    user_id: str | None = None,
    related_type: str | None = None,
    related_id: str | None = None,
    memo: str | None = None,
    check_funds: bool = True,
) -> LedgerEvent:
    gross_amount = D(gross)
    if gross_amount <= 0:
        raise LedgerError("amount_must_be_positive")
    if check_funds and not source.startswith(("platform:", "world:", "external:")):
        if balance(session, source, currency) < gross_amount:
            raise LedgerError("insufficient_funds")
    fee = D(gross_amount * Decimal(fee_bps) / Decimal(10000))
    event = LedgerEvent(
        event_type=event_type,
        source_account=source,
        destination_account=destination,
        currency=currency,
        gross_amount=gross_amount,
        platform_fee=fee,
        net_amount=gross_amount - fee,
        balance_class=balance_class,
        status=status,
        club_id=club_id,
        user_id=user_id,
        related_object_type=related_type,
        related_object_id=related_id,
        memo=memo,
    )
    session.add(event)
    session.flush()
    return event


def balance(session: Session, account: str, currency: str) -> Decimal:
    inflow = session.scalar(
        select(func.coalesce(func.sum(LedgerEvent.net_amount), 0)).where(
            LedgerEvent.destination_account == account,
            LedgerEvent.currency == currency,
            LedgerEvent.status == "completed",
        )
    )
    outflow = session.scalar(
        select(func.coalesce(func.sum(LedgerEvent.gross_amount), 0)).where(
            LedgerEvent.source_account == account,
            LedgerEvent.currency == currency,
            LedgerEvent.status.in_(LIVE_STATUSES),
        )
    )
    return D(inflow or 0) - D(outflow or 0)


def _sum(session: Session, *conditions, column=LedgerEvent.net_amount) -> Decimal:
    return D(session.scalar(select(func.coalesce(func.sum(column), 0)).where(*conditions)) or 0)


def wallet_classes(session: Session, user_id: str) -> dict[str, str]:
    acct = user_account(user_id)
    credits = {
        cls: _sum(
            session,
            LedgerEvent.destination_account == acct,
            LedgerEvent.currency == GTEX,
            LedgerEvent.status == "completed",
            LedgerEvent.balance_class == cls,
        )
        for cls in ("deposited", "earned", "promotional")
    }
    withdrawals = _sum(
        session,
        LedgerEvent.source_account == acct,
        LedgerEvent.currency == GTEX,
        LedgerEvent.event_type == "withdrawal",
        LedgerEvent.status.in_(LIVE_STATUSES),
        column=LedgerEvent.gross_amount,
    )
    spend = _sum(
        session,
        LedgerEvent.source_account == acct,
        LedgerEvent.currency == GTEX,
        LedgerEvent.event_type != "withdrawal",
        LedgerEvent.status.in_(LIVE_STATUSES),
        column=LedgerEvent.gross_amount,
    )
    promo_left = max(Decimal("0"), credits["promotional"] - spend)
    spend_beyond_promo = max(Decimal("0"), spend - credits["promotional"])
    withdrawable = max(Decimal("0"), credits["earned"] + credits["deposited"] - spend_beyond_promo - withdrawals)
    pending = _sum(
        session,
        LedgerEvent.source_account == acct,
        LedgerEvent.event_type == "withdrawal",
        LedgerEvent.status.in_(("pending_review", "held")),
        column=LedgerEvent.gross_amount,
    )
    fan_total = balance(session, acct, FAN)
    return {
        "gtex_total": str(balance(session, acct, GTEX)),
        "fan_total": str(fan_total),
        "deposited": str(credits["deposited"]),
        "earned": str(credits["earned"]),
        "promotional": str(promo_left),
        "withdrawable": str(withdrawable),
        "non_withdrawable": str(promo_left + fan_total),
        "pending_review": str(pending),
    }


def club_economy(session: Session, club_id: str) -> dict[str, object]:
    acct = club_account(club_id)
    sources = {}
    for event_type in ("gate_receipts", "competition_prize", "sponsor_revenue", "endorsement_revenue", "transfer_sale", "support_units", "gift"):
        sources[event_type] = str(
            _sum(
                session,
                LedgerEvent.destination_account == acct,
                LedgerEvent.event_type == event_type,
                LedgerEvent.status == "completed",
            )
        )
    held = _sum(
        session,
        LedgerEvent.destination_account == acct,
        LedgerEvent.status == "held",
    )
    spend = _sum(
        session,
        LedgerEvent.source_account == acct,
        LedgerEvent.currency == GTEX,
        LedgerEvent.status == "completed",
        column=LedgerEvent.gross_amount,
    )
    return {
        "cash_gtex": str(balance(session, acct, GTEX)),
        "gifts_fan_coin": str(balance(session, acct, FAN)),
        "earnings_sources": sources,
        "pending_payouts": str(held),
        "total_spend": str(spend),
    }


def events_for(session: Session, *, user_id: str, club_ids: list[str], limit: int = 100) -> list[LedgerEvent]:
    accounts = [user_account(user_id)] + [club_account(cid) for cid in club_ids]
    stmt = (
        select(LedgerEvent)
        .where((LedgerEvent.source_account.in_(accounts)) | (LedgerEvent.destination_account.in_(accounts)))
        .order_by(LedgerEvent.created_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def serialize(event: LedgerEvent) -> dict[str, object]:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "source_account": event.source_account,
        "destination_account": event.destination_account,
        "club_id": event.club_id,
        "user_id": event.user_id,
        "currency": event.currency,
        "gross_amount": str(event.gross_amount),
        "platform_fee": str(event.platform_fee),
        "net_amount": str(event.net_amount),
        "balance_class": event.balance_class,
        "status": event.status,
        "related_object_type": event.related_object_type,
        "related_object_id": event.related_object_id,
        "memo": event.memo,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def pending_withdrawals(session: Session, user_id: str) -> list[OwnerWithdrawal]:
    return list(
        session.scalars(
            select(OwnerWithdrawal).where(OwnerWithdrawal.user_id == user_id).order_by(OwnerWithdrawal.created_at.desc())
        ).all()
    )
