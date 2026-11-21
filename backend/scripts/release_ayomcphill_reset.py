"""Return ayomcphill's acquired players to the market and recover a stranded club treasury.

The VIDA FC wipe kept the same user id, so player units stayed owned and any coin
already in that club treasury stayed on the deleted club. This script prints the
holding count, circulation deltas, and refund total, then applies the repair when
--activate is passed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import dotenv_values
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import normalize_database_url
from app.core.database import load_model_modules
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerEntry, LedgerUnit
from app.owner_console import ledger
from app.owner_console.models import LedgerEvent, OwnerClubState, OwnerSquadPlayer
from app.players.token_service import PlayerTokenMarketService
from app.wallets.service import WalletService

USER_ID = "abb89108-a0c9-4d05-9910-262b7a40cf71"
VIDA_CLUB_ID = "fa6f8f63-9db5-4555-b9ac-e71f11013c57"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Release ayomcphill acquisitions and recover the stranded treasury.")
    parser.add_argument("--activate", action="store_true", help="Persist the repair. Default is a dry run.")
    return parser.parse_args()


def _database_url() -> str:
    env = dotenv_values(BACKEND_ROOT / ".env")
    database_url = os.getenv("DATABASE_URL") or env.get("DATABASE_URL") or env.get("GTE_DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")
    return normalize_database_url(database_url)


def _money(value) -> str:
    return str(Decimal(str(value or "0")).quantize(Decimal("0.0001")))


def _account(session, code: str) -> LedgerAccount | None:
    return session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))


def _entry_sum(session, account_id: str) -> Decimal:
    total = session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(LedgerEntry.account_id == account_id)
    )
    return Decimal(str(total or "0")).quantize(Decimal("0.0001"))


def _reconcile_projection(session, account: LedgerAccount | None) -> dict[str, str]:
    if account is None:
        return {"action": "missing_account"}
    entries = _entry_sum(session, account.id)
    projection = session.scalar(select(LedgerBalanceProjection).where(LedgerBalanceProjection.account_id == account.id))
    if projection is None:
        return {"code": account.code, "action": "missing_projection", "entries": _money(entries)}
    current = Decimal(str(projection.balance or "0")).quantize(Decimal("0.0001"))
    if current == entries:
        return {"code": account.code, "action": "ok", "balance": _money(current)}
    projection.balance = entries
    return {
        "code": account.code,
        "action": "rebuilt",
        "before": _money(current),
        "after": _money(entries),
    }


def _club_snapshot(session, club_id: str) -> dict[str, str]:
    economy = ledger.club_economy(session, club_id)
    return {
        "club_id": club_id,
        "cash_gtex": str(economy["cash_gtex"]),
        "deposited": str(economy["deposited"]),
        "squad_grant": str(economy["squad_grant"]),
        "earned": str(economy["earned"]),
    }


def _holding_preview(session) -> list[dict[str, object]]:
    rows = session.execute(
        select(
            PlayerShareHolding.player_id,
            PlayerShareHolding.share_count,
            PlayerShareMarket.circulating_shares,
            PlayerShareMarket.released_shares,
            PlayerShareMarket.total_shares,
        )
        .join(PlayerShareMarket, PlayerShareMarket.player_id == PlayerShareHolding.player_id)
        .where(
            PlayerShareHolding.user_id == USER_ID,
            PlayerShareHolding.share_count > 0,
        )
    ).all()
    preview = []
    for player_id, share_count, circulating, released, total in rows:
        shares = int(share_count or 0)
        circulating_before = int(circulating or 0)
        preview.append(
            {
                "player_id": player_id,
                "shares": shares,
                "circulating_before": circulating_before,
                "circulating_after": circulating_before - shares,
                "released_shares": released,
                "total_shares": total,
            }
        )
    return preview


def main() -> int:
    args = parse_args()
    database_url = _database_url()
    load_model_modules()
    connect_args = {} if database_url.startswith("sqlite") else {"prepare_threshold": None, "connect_timeout": 15}
    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    wallet = WalletService()
    print("connecting", flush=True)
    with session_factory() as session:
        session.execute(text("SET statement_timeout = '25s'"))
        session.execute(text("SET lock_timeout = '8s'"))
        print("connected", flush=True)
        user = session.get(User, USER_ID)
        if user is None:
            raise SystemExit("ayomcphill user was not found")
        print("user loaded", flush=True)

        user_account = wallet.get_user_account(session, user, LedgerUnit.COIN)
        vida_account = _account(session, f"club:{VIDA_CLUB_ID}:coin:treasury")
        clubs = list(
            session.scalars(
                select(OwnerClubState)
                .where(OwnerClubState.owner_user_id == USER_ID)
                .order_by(OwnerClubState.created_at.asc())
            ).all()
        )
        current_clubs = [club for club in clubs if club.club_id != VIDA_CLUB_ID]
        current = current_clubs[-1] if current_clubs else None
        squad_rows = session.scalars(select(OwnerSquadPlayer).where(OwnerSquadPlayer.club_id == VIDA_CLUB_ID)).all()

        report: dict[str, object] = {
            "dry_run": not args.activate,
            "user_id": USER_ID,
            "wallet_before": _reconcile_projection(session, user_account),
            "vida_treasury_before": _reconcile_projection(session, vida_account),
            "clubs_before": [_club_snapshot(session, club.club_id) for club in clubs],
            "holdings": _holding_preview(session),
            "vida_squad_rows": len(squad_rows),
        }
        report["holding_count"] = len(report["holdings"])
        print(f"preview holdings={report['holding_count']} squad_rows={report['vida_squad_rows']}", flush=True)

        release = PlayerTokenMarketService(session=session, wallet_service=wallet).release_account_acquisitions(
            user_id=USER_ID
        )
        report["release"] = release

        for row in squad_rows:
            session.delete(row)

        retagged = None
        if current is not None:
            earned_topups = list(
                session.scalars(
                    select(LedgerEvent).where(
                        LedgerEvent.club_id == current.club_id,
                        LedgerEvent.event_type == "owner_capital_injection",
                        LedgerEvent.balance_class == "earned",
                        LedgerEvent.status == "completed",
                        LedgerEvent.destination_account == ledger.club_account(current.club_id),
                        LedgerEvent.currency == ledger.GTEX,
                    )
                ).all()
            )
            topup_total = sum((ledger.D(event.gross_amount) for event in earned_topups), Decimal("0.00"))
            if topup_total > 0:
                ledger.record(
                    session,
                    event_type="owner_capital_injection",
                    source=ledger.club_account(current.club_id),
                    destination=ledger.PLATFORM_GRANTS,
                    currency=ledger.GTEX,
                    gross=topup_total,
                    balance_class="earned",
                    club_id=current.club_id,
                    user_id=USER_ID,
                    related_type="club",
                    related_id=current.club_id,
                    memo="Reclassify owner wallet top-up out of earned club funds",
                )
                ledger.record(
                    session,
                    event_type="owner_capital_injection",
                    source=ledger.PLATFORM_GRANTS,
                    destination=ledger.club_account(current.club_id),
                    currency=ledger.GTEX,
                    gross=topup_total,
                    balance_class="deposited",
                    club_id=current.club_id,
                    user_id=USER_ID,
                    related_type="club",
                    related_id=current.club_id,
                    memo="Owner wallet top-up counted as deposited club treasury",
                )
                retagged = {"club_id": current.club_id, "amount": _money(topup_total)}
        report["topup_retagged_as_deposited"] = retagged

        moved = None
        if current is not None and vida_account is not None:
            stranded = ledger.balance(session, ledger.club_account(VIDA_CLUB_ID), ledger.GTEX)
            protected = ledger._net_squad_grant(session, ledger.club_account(VIDA_CLUB_ID))
            movable = max(Decimal("0.00"), stranded - protected)
            if movable > 0:
                ledger.record(
                    session,
                    event_type="owner_capital_injection",
                    source=ledger.club_account(VIDA_CLUB_ID),
                    destination=ledger.club_account(current.club_id),
                    currency=ledger.GTEX,
                    gross=movable,
                    balance_class="deposited",
                    club_id=current.club_id,
                    user_id=USER_ID,
                    related_type="club",
                    related_id=current.club_id,
                    memo="Moved stranded VIDA FC treasury onto the replacement club",
                )
                moved = {
                    "from_club_id": VIDA_CLUB_ID,
                    "to_club_id": current.club_id,
                    "amount": _money(movable),
                    "protected_grant_left_behind": _money(protected),
                }
        report["treasury_move"] = moved
        report["wallet_after"] = _money(ledger.balance(session, ledger.user_account(USER_ID), ledger.GTEX))
        report["vida_after"] = _money(ledger.balance(session, ledger.club_account(VIDA_CLUB_ID), ledger.GTEX))
        report["clubs_after"] = [_club_snapshot(session, club.club_id) for club in clubs]

        if args.activate:
            session.commit()
        else:
            session.rollback()

    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
