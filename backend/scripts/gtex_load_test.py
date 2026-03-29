from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import os
from time import perf_counter
from uuid import uuid4

from app.auth.service import AuthService
from app.gtex.worker_runtime import AiBrainWorker, AiMatchmakerWorker, JackpotWorker, ValuationWorker, build_worker_context
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService


def create_user(context, *, label: str) -> User:
    with context.database.session_factory() as session:
        auth = AuthService()
        suffix = uuid4().hex[:10]
        user = auth.register_user(
            session,
            email=f"{label}-{suffix}@load.test",
            username=f"{label}_{suffix}",
            password="LoadTest123!",
            display_name=f"{label.title()} {suffix}",
        )
        session.commit()
        return user


def fund_user(context, *, user_id: str, amount: Decimal) -> None:
    with context.database.session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        wallet = WalletService()
        user_account = wallet.get_user_account(session, user, LedgerUnit.COIN)
        operations = wallet.ensure_operations_account(session, LedgerUnit.COIN)
        wallet.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=amount),
                LedgerPosting(account=operations, amount=-amount),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            transaction_type=LedgerTransactionType.ADJUSTMENT,
            reference=f"load-fund:{user_id}",
            description="GTEX load test funding",
        )
        session.commit()


def run_match_scenario(context, *, total_matches: int, concurrency: int) -> None:
    users = [create_user(context, label="match") for _ in range(max(2, total_matches))]
    for user in users:
        fund_user(context, user_id=user.id, amount=Decimal("10000.0000"))

    def submit(index: int) -> str:
        user = users[index % len(users)]
        with context.database.session_factory() as session:
            user_model = session.get(User, user.id)
            assert user_model is not None
            queue_entry = context.runtime.ai_leagues.queue_match_request(
                session,
                user=user_model,
                league_ref="ranked",
                entry_fee=Decimal("50.0000"),
                metadata={"load_index": index},
            )
            session.commit()
            return queue_entry.id

    started_at = perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(submit, index) for index in range(total_matches)]
        for _ in as_completed(futures):
            pass
    matchmaker = AiMatchmakerWorker(context=context)
    ai_brain = AiBrainWorker(context=context)
    pending = total_matches
    while pending > 0:
        pending -= matchmaker.run_once()
        pending -= ai_brain.run_once()
        if pending < 0:
            pending = 0
    duration = perf_counter() - started_at
    print(f"match scenario complete total_matches={total_matches} concurrency={concurrency} duration_seconds={duration:.2f}")


def run_jackpot_scenario(context, *, contributions: int) -> None:
    users = [create_user(context, label="jackpot") for _ in range(max(1, min(contributions, 20)))]
    for user in users:
        fund_user(context, user_id=user.id, amount=Decimal("10000.0000"))
    with context.database.session_factory() as session:
        round_record = context.runtime.jackpot.ensure_open_round(session)
        round_record.threshold_amount = Decimal("100.0000")
        session.commit()
    started_at = perf_counter()
    for index in range(contributions):
        user = users[index % len(users)]
        with context.database.session_factory() as session:
            user_model = session.get(User, user.id)
            assert user_model is not None
            context.runtime.jackpot.contribute_from_wallet(
                session,
                actor=user_model,
                source_type="platform_activity",
                source_id=f"load-jackpot-{index}",
                entry_fee=Decimal("100.0000"),
                eligibility_score=Decimal("1.0000"),
                metadata={"load_index": index},
            )
            session.commit()
    JackpotWorker(context=context).run_once()
    duration = perf_counter() - started_at
    print(f"jackpot scenario complete contributions={contributions} duration_seconds={duration:.2f}")


def run_market_scenario(context, *, trades: int, concurrency: int) -> None:
    creator = create_user(context, label="asset")
    traders = [create_user(context, label="trader") for _ in range(max(2, concurrency))]
    for trader in traders:
        fund_user(context, user_id=trader.id, amount=Decimal("25000.0000"))
    with context.database.session_factory() as session:
        creator_model = session.get(User, creator.id)
        assert creator_model is not None
        asset = context.runtime.creator_market.ensure_asset_for_user(session, creator_model)
        session.commit()
        player_id = asset.id

    def execute_trade(index: int) -> None:
        trader = traders[index % len(traders)]
        with context.database.session_factory() as session:
            trader_model = session.get(User, trader.id)
            assert trader_model is not None
            context.runtime.creator_market.buy_shares(
                session,
                buyer=trader_model,
                player_id=player_id,
                shares=1,
            )
            session.commit()

    started_at = perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(execute_trade, index) for index in range(trades)]
        for _ in as_completed(futures):
            pass
    valuation = ValuationWorker(context=context)
    while valuation.run_once():
        pass
    duration = perf_counter() - started_at
    print(f"market scenario complete trades={trades} concurrency={concurrency} duration_seconds={duration:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GTEX load simulations.")
    parser.add_argument("--scenario", choices=("matches", "jackpot", "market"), required=True)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=32)
    args = parser.parse_args()

    if args.scenario == "market":
        os.environ.setdefault("GTEX_CREATOR_TRADE_COOLDOWN_SECONDS", "0")
    context = build_worker_context()
    try:
        if args.scenario == "matches":
            run_match_scenario(context, total_matches=args.count, concurrency=args.concurrency)
        elif args.scenario == "jackpot":
            run_jackpot_scenario(context, contributions=args.count)
        else:
            run_market_scenario(context, trades=args.count, concurrency=args.concurrency)
    finally:
        context.shutdown()


if __name__ == "__main__":
    main()
