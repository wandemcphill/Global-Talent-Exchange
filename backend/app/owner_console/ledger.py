from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.owner_console.models import LedgerEvent, OwnerWithdrawal
from app.wallets.service import LedgerError as WalletLedgerError
from app.wallets.service import LedgerPosting, WalletService

GTEX = "GTEX_COIN"
FAN = "FAN_COIN"
PLATFORM_FEES = "platform:fees"
PLATFORM_GRANTS = "platform:grants"
PLATFORM_SPONSORS = "platform:sponsor_pool"
WORLD_MARKET = "world:market"
WORLD_CLUBS = "world:clubs"
PAYSTACK = "external:paystack"
BANK_OUT = "external:bank_payout"
HELD = "owner_console:held"
TRANSFER_PLATFORM_FEE_BPS = 2_000
LIVE_STATUSES = ("completed", "pending_review", "held")
UNITS = {"GTEX_COIN": LedgerUnit.COIN, "FAN_COIN": LedgerUnit.CREDIT}
REASONS = {
    "deposit": LedgerEntryReason.DEPOSIT,
    "withdrawal": LedgerEntryReason.WITHDRAWAL_HOLD,
    "competition_entry_fee": LedgerEntryReason.COMPETITION_ENTRY,
    "competition_prize": LedgerEntryReason.COMPETITION_REWARD,
    "transfer_purchase": LedgerEntryReason.TRADE_SETTLEMENT,
    "transfer_sale": LedgerEntryReason.TRADE_SETTLEMENT,
    "related_party_transfer": LedgerEntryReason.TRADE_SETTLEMENT,
}
_wallet = WalletService()


class LedgerError(ValueError):
    pass


def D(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def user_account(user_id: str) -> str:
    return f"user:{user_id}"


def club_account(club_id: str) -> str:
    return f"club:{club_id}"


def wallet_account(session: Session, account: str, currency: str):
    """Map an owner-console account name onto the repo's wallet ledger (one wallet)."""
    unit = UNITS[currency]
    kind, _, ident = account.partition(":")
    if kind == "user":
        user = session.get(User, ident)
        if user is None:
            raise LedgerError("user_not_found")
        _wallet.ensure_default_accounts(session, user)
        return _wallet.get_user_account(session, user, unit)
    if kind == "club":
        return _wallet.ensure_club_treasury_account(session, ident, unit)
    if kind == "competition":
        return _wallet.ensure_named_system_account(
            session,
            code=f"competition:{ident}:{unit.value}:pot",
            label=f"Competition {ident} pot",
            unit=unit,
            allow_negative=False,
        )
    if account == PAYSTACK:
        return _wallet.ensure_deposit_clearing_account(session, unit)
    if account == BANK_OUT:
        return _wallet.ensure_withdrawal_clearing_account(session, unit)
    if account == HELD:
        return _wallet.ensure_named_system_account(
            session,
            code=f"owner_console:held:{unit.value}",
            label="Owner console held funds",
            unit=unit,
            allow_negative=False,
        )
    if account == PLATFORM_FEES:
        return _wallet.ensure_named_system_account(
            session,
            code=f"platform:{unit.value}:owner_console_fees",
            label="Owner console platform fees",
            unit=unit,
            allow_negative=True,
        )
    return _wallet.ensure_named_system_account(
        session,
        code=f"owner_console:{account.replace(':', '_')}:{unit.value}",
        label=f"Owner console {account}",
        unit=unit,
        allow_negative=True,
    )


def _post(
    session: Session, event: LedgerEvent, source: str, destination: str, net: Decimal, fee: Decimal, phase: str
) -> None:
    cur = event.currency
    postings = [
        LedgerPosting(account=wallet_account(session, source, cur), amount=-(net + fee)),
        LedgerPosting(account=wallet_account(session, destination, cur), amount=net),
    ]
    if fee > 0:
        postings.append(LedgerPosting(account=wallet_account(session, PLATFORM_FEES, cur), amount=fee))
    try:
        _wallet.append_transaction(
            session,
            postings=postings,
            reason=REASONS.get(event.event_type, LedgerEntryReason.ADJUSTMENT),
            reference=f"owner-console:{event.id}:{phase}",
            description=(event.memo or event.event_type)[:255],
            idempotency_key=f"oc:{event.id}:{phase}",
            metadata={"owner_ledger_event_id": event.id, "event_type": event.event_type, "phase": phase},
        )
    except WalletLedgerError as exc:
        raise LedgerError("insufficient_funds" if "nsufficient" in str(exc) else str(exc)) from exc


def post_event(session: Session, event: LedgerEvent) -> None:
    if event.status == "completed":
        _post(
            session,
            event,
            event.source_account,
            event.destination_account,
            D(event.net_amount),
            D(event.platform_fee),
            "settle",
        )
    else:
        _post(session, event, event.source_account, HELD, D(event.gross_amount), D(0), "hold")
        if event.status == "reversed":
            _post(session, event, HELD, event.source_account, D(event.gross_amount), D(0), "reverse")


def transition(session: Session, event: LedgerEvent, new_status: str) -> LedgerEvent:
    if event.status == new_status:
        return event
    if event.status not in ("pending_review", "held", "completed"):
        raise LedgerError("event_not_pending")
    if new_status == "completed":
        _post(session, event, HELD, event.destination_account, D(event.net_amount), D(event.platform_fee), "release")
    elif new_status == "reversed":
        source = event.destination_account if event.status == "completed" else HELD
        _post(session, event, source, event.source_account, D(event.gross_amount), D(0), "reverse")
        from app.owner_console import storytelling
        storytelling.reverse_broadcast_events_for_ledger(session, event.id)
    elif new_status not in ("pending_review", "held"):
        raise LedgerError("invalid_transition")
    event.status = new_status
    session.flush()
    return event


def backfill_wallet_postings(session: Session) -> int:
    events = session.scalars(select(LedgerEvent).order_by(LedgerEvent.created_at.asc())).all()
    for event in events:
        post_event(session, event)
    return len(events)


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
    post_event(session, event)
    return event


def assert_club_can_fund(session: Session, club_id: str, amount) -> None:
    gross_amount = D(amount)
    if gross_amount <= 0:
        return
    if balance(session, club_account(club_id), GTEX) < gross_amount:
        raise LedgerError("insufficient_club_treasury")


def settle_club_transfer(
    session: Session,
    *,
    buying_club_id: str,
    selling_club_id: str,
    amount,
    transfer_bid_id: str,
    memo: str,
) -> LedgerEvent | None:
    """Pay a player transfer from the buying club treasury; the seller nets the fee less the platform cut."""
    if D(amount) <= 0:
        return None
    existing = session.scalar(
        select(LedgerEvent).where(
            LedgerEvent.event_type == "transfer_purchase",
            LedgerEvent.related_object_type == "transfer_bid",
            LedgerEvent.related_object_id == transfer_bid_id,
        )
    )
    if existing is not None:
        return existing
    return record(
        session,
        event_type="transfer_purchase",
        source=club_account(buying_club_id),
        destination=club_account(selling_club_id),
        currency=GTEX,
        gross=amount,
        fee_bps=TRANSFER_PLATFORM_FEE_BPS,
        club_id=buying_club_id,
        related_type="transfer_bid",
        related_id=transfer_bid_id,
        memo=memo[:255],
    )


def balance(session: Session, account: str, currency: str) -> Decimal:
    return D(_wallet.get_balance(session, wallet_account(session, account, currency)))


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
    gtex_total = balance(session, acct, GTEX)
    promo_left = min(max(Decimal("0"), credits["promotional"] - spend), max(gtex_total, Decimal("0")))
    withdrawable = max(Decimal("0"), gtex_total - promo_left)
    console_net = sum(credits.values(), Decimal("0")) - spend - withdrawals
    pending = _sum(
        session,
        LedgerEvent.source_account == acct,
        LedgerEvent.event_type == "withdrawal",
        LedgerEvent.status.in_(("pending_review", "held")),
        column=LedgerEvent.gross_amount,
    )
    fan_total = balance(session, acct, FAN)
    return {
        "gtex_total": str(gtex_total),
        "exchange_activity": str(gtex_total - console_net),
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
    for event_type in (
        "gate_receipts",
        "competition_prize",
        "sponsor_revenue",
        "endorsement_revenue",
        "transfer_sale",
        "support_units",
        "gift",
    ):
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
            select(OwnerWithdrawal)
            .where(OwnerWithdrawal.user_id == user_id)
            .order_by(OwnerWithdrawal.created_at.desc())
        ).all()
    )
