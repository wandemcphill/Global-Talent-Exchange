from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, or_, select

from app.auth.service import AuthService
from app.gtex import redis_keys
from app.gtex.runtime import build_gtex_runtime, ensure_gtex_runtime
from app.gtex.worker_runtime import AiBrainWorker, AiMatchmakerWorker, JackpotWorker, WorkerContext
from app.global_memory.constants import MATCH_COMPLETED
from app.global_memory.models import GlobalProjectionCheckpoint, UserDynasty
from app.models.base import utcnow
from app.models.gtex_economy import GtexCreatorTrade
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.models.wallet import LedgerTransaction
from app.wallets.service import LedgerPosting, WalletService


def _register_user(app_session_factory, *, label: str) -> tuple[User, dict[str, str]]:
    with app_session_factory() as session:
        auth = AuthService()
        suffix = uuid4().hex[:8]
        user = auth.register_user(
            session,
            email=f"{label}-{suffix}@example.com",
            username=f"{label}_{suffix}",
            password="TestPass123!",
            display_name=f"{label.title()} {suffix}",
        )
        session.commit()
        token, _ = auth.issue_access_token(user, session=session)
        session.commit()
        return user, {"Authorization": f"Bearer {token}"}


def _fund_user(app_session_factory, *, user_id: str, amount: Decimal) -> None:
    with app_session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        wallet_service = WalletService()
        user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
        operations = wallet_service.ensure_operations_account(session, LedgerUnit.COIN)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=user_account, amount=amount),
                LedgerPosting(account=operations, amount=-amount),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            transaction_type=LedgerTransactionType.ADJUSTMENT,
            reference=f"test-fund:{user_id}",
            description="Seed user wallet for GTEX tests",
        )
        session.commit()


def _age_latest_trade(app_session_factory, *, user_id: str, age: timedelta) -> None:
    with app_session_factory() as session:
        latest_trade = session.scalar(
            select(GtexCreatorTrade)
            .where(or_(GtexCreatorTrade.buyer_id == user_id, GtexCreatorTrade.seller_id == user_id))
            .order_by(GtexCreatorTrade.created_at.desc())
        )
        assert latest_trade is not None
        latest_trade.created_at = utcnow() - age
        session.commit()


def _worker_context(app) -> WorkerContext:
    return WorkerContext(
        database=app.state.container.database,
        runtime=ensure_gtex_runtime(app),
        event_publisher=app.state.event_publisher,
    )


def test_jackpot_trigger_under_worker_load(client, app, app_session_factory):
    runtime = ensure_gtex_runtime(app)
    user, headers = _register_user(app_session_factory, label="jackpot")
    _fund_user(app_session_factory, user_id=user.id, amount=Decimal("2000.0000"))
    with app_session_factory() as session:
        current_round = runtime.jackpot.ensure_open_round(session)
        current_round.threshold_amount = Decimal("50.0000")
        session.commit()
    response = client.post(
        "/jackpot/contribute",
        headers=headers,
        json={
            "source_type": "platform_activity",
            "source_id": "test-jackpot-load",
            "entry_fee": "600.0000",
            "eligibility_score": "1.0000",
            "metadata": {"scenario": "jackpot_trigger_under_worker_load"},
        },
    )
    assert response.status_code == 201, response.text
    worker = JackpotWorker(context=_worker_context(app))
    assert worker.run_once() is True
    history = client.get("/jackpot/history").json()
    closed_round = next(item for item in history if item["status"] in {"settled", "cancelled"})
    assert closed_round["trigger_mode"] == "threshold"
    if closed_round["payouts"]:
        assert closed_round["payouts"][0]["payout_amount"] == "60.0000"


def test_admin_jackpot_runtime_update_and_manual_trigger(
    client,
    app,
    app_session_factory,
    bootstrap_admin_headers,
):
    runtime = ensure_gtex_runtime(app)
    with app_session_factory() as session:
        current_round_number = runtime.jackpot.ensure_open_round(session).round_number
    user, headers = _register_user(app_session_factory, label="jackpot-admin")
    _fund_user(app_session_factory, user_id=user.id, amount=Decimal("500.0000"))

    update_response = client.post(
        "/admin/jackpot/runtime",
        headers=bootstrap_admin_headers,
        json={
            "threshold_amount": "125.0000",
            "probability_limit": "900.0000",
            "probability_cap": "0.3500",
            "failsafe_hours": 3,
            "contribution_rate": "0.1500",
            "distribution_mode": "top_split",
            "top_split_percent": "0.5000",
            "min_activity_score": "1.2500",
        },
    )

    assert update_response.status_code == 200, update_response.text
    runtime_payload = update_response.json()
    assert runtime_payload["threshold_amount"] == "125.0000"
    assert runtime_payload["probability_limit"] == "900.0000"
    assert runtime_payload["probability_cap"] == "0.3500"
    assert runtime_payload["contribution_rate"] == "0.1500"
    assert runtime_payload["distribution_mode"] == "top_split"
    assert runtime_payload["top_split_percent"] == "0.5000"
    assert runtime_payload["min_activity_score"] == "1.2500"
    assert runtime_payload["failsafe_hours"] == 3
    assert runtime.settings.jackpot_threshold_amount == Decimal("125.0000")
    assert runtime.settings.jackpot_contribution_rate == Decimal("0.1500")

    balance_response = client.patch(
        "/admin/jackpot/balance",
        headers=bootstrap_admin_headers,
        json={"balance": "25.0000", "reason": "seed launch jackpot display"},
    )
    assert balance_response.status_code == 200, balance_response.text
    assert balance_response.json()["balance"] == "25.0000"
    reset_balance_response = client.patch(
        "/admin/jackpot/balance",
        headers=bootstrap_admin_headers,
        json={"balance": "0.0000", "reason": "reset for manual trigger assertion"},
    )
    assert reset_balance_response.status_code == 200, reset_balance_response.text
    assert reset_balance_response.json()["balance"] == "0.0000"

    contribution_response = client.post(
        "/jackpot/contribute",
        headers=headers,
        json={
            "source_type": "platform_activity",
            "source_id": "jackpot-manual-ui",
            "entry_fee": "50.0000",
            "contribution_amount": "50.0000",
            "eligibility_score": "2.0000",
            "metadata": {"scenario": "admin_jackpot_runtime_update"},
        },
    )

    assert contribution_response.status_code == 201, contribution_response.text
    contribution_payload = contribution_response.json()
    assert contribution_payload["contribution_amount"] == "50.0000"

    trigger_response = client.post(
        "/admin/jackpot/trigger",
        headers=bootstrap_admin_headers,
    )

    assert trigger_response.status_code == 200, trigger_response.text
    trigger_payload = trigger_response.json()
    assert trigger_payload["triggered_round_number"] == current_round_number
    assert trigger_payload["next_round_number"] == current_round_number + 1

    state_payload = client.get("/jackpot/state").json()
    assert state_payload["round_number"] == current_round_number + 1
    history_payload = client.get("/jackpot/history").json()
    settled_round = next(item for item in history_payload if item["round_number"] == current_round_number)
    assert settled_round["trigger_mode"] == "manual"
    assert settled_round["payouts"][0]["payout_amount"] == "50.0000"

    reset_runtime_response = client.post(
        "/admin/jackpot/runtime",
        headers=bootstrap_admin_headers,
        json={
            "threshold_amount": "500.0000",
            "probability_limit": "1000.0000",
            "probability_cap": "0.5000",
            "failsafe_hours": 6,
            "contribution_rate": "0.1000",
            "distribution_mode": "single_winner",
            "top_split_percent": "0.1000",
            "min_activity_score": "1.0000",
        },
    )
    assert reset_runtime_response.status_code == 200, reset_runtime_response.text


def test_gtex_runtime_uses_shared_wallet_cache_backend() -> None:
    class FakeCacheBackend:
        enabled = True

        def get(self, key: str) -> str | None:
            return None

        def set(self, key: str, value: str, ttl_seconds: int) -> None:
            return None

        def delete_many(self, keys: list[str]) -> None:
            return None

        def ping(self) -> bool:
            return True

    cache_backend = FakeCacheBackend()
    runtime = build_gtex_runtime(
        app_settings=None,
        session_factory=None,
        event_publisher=None,
        cache_backend=cache_backend,
        redis_url=None,
        realtime_channel="gtex.test.realtime",
    )

    try:
        assert runtime.wallet_service.cache_backend is cache_backend
        assert runtime.jackpot.wallet_service.cache_backend is cache_backend
        assert runtime.creator_market.wallet_service.cache_backend is cache_backend
        assert runtime.economy.wallet_service.cache_backend is cache_backend
    finally:
        runtime.shutdown()


def test_creator_market_buy_sell_and_trending(client, app_session_factory, app):
    runtime = ensure_gtex_runtime(app)
    creator_user, _ = _register_user(app_session_factory, label="creator")
    trader_user, trader_headers = _register_user(app_session_factory, label="trader")
    _fund_user(app_session_factory, user_id=trader_user.id, amount=Decimal("5000.0000"))
    with app_session_factory() as session:
        creator_model = session.get(User, creator_user.id)
        assert creator_model is not None
        asset = runtime.creator_market.ensure_asset_for_user(session, creator_model)
        session.commit()
        player_id = asset.id
    buy_response = client.post(
        "/market/buy",
        headers=trader_headers,
        json={"player_id": player_id, "shares": 10},
    )
    assert buy_response.status_code == 201, buy_response.text
    runtime.state_store.delete(redis_keys.creator_cooldown(trader_user.id, player_id))
    with app_session_factory() as session:
        latest_trade = session.query(GtexCreatorTrade).order_by(GtexCreatorTrade.created_at.desc()).first()
        assert latest_trade is not None
        latest_trade.created_at = utcnow() - timedelta(seconds=10)
        session.commit()
    sell_response = client.post(
        "/market/sell",
        headers=trader_headers,
        json={"player_id": player_id, "shares": 5},
    )
    assert sell_response.status_code == 201, sell_response.text
    player_response = client.get(f"/players/{player_id}", headers=trader_headers)
    assert player_response.status_code == 200
    payload = player_response.json()
    assert payload["holding"]["shares_owned"] == "5.0000"
    trending_response = client.get("/market/trending")
    assert trending_response.status_code == 200
    assert any(item["id"] == player_id for item in trending_response.json()["items"])


def test_creator_market_flags_and_admin_ban_flow(client, app, app_session_factory, bootstrap_admin_headers):
    runtime = ensure_gtex_runtime(app)
    creator_user, _ = _register_user(app_session_factory, label="risk-creator")
    looping_user, looping_headers = _register_user(app_session_factory, label="risk-loop")
    shared_ip_user, shared_ip_headers = _register_user(app_session_factory, label="risk-shared")
    _fund_user(app_session_factory, user_id=looping_user.id, amount=Decimal("8000.0000"))
    _fund_user(app_session_factory, user_id=shared_ip_user.id, amount=Decimal("4000.0000"))

    with app_session_factory() as session:
        creator_model = session.get(User, creator_user.id)
        assert creator_model is not None
        asset = runtime.creator_market.ensure_asset_for_user(session, creator_model)
        session.commit()
        player_id = asset.id

    shared_ip = "198.51.100.24"
    looping_trade_headers = {**looping_headers, "X-Forwarded-For": shared_ip}
    shared_ip_trade_headers = {**shared_ip_headers, "X-Forwarded-For": shared_ip}

    first_buy = client.post(
        "/market/buy",
        headers=looping_trade_headers,
        json={"player_id": player_id, "shares": 10},
    )
    assert first_buy.status_code == 201, first_buy.text
    _age_latest_trade(app_session_factory, user_id=looping_user.id, age=timedelta(minutes=12))
    runtime.state_store.delete(redis_keys.creator_cooldown(looping_user.id, player_id))

    second_buy = client.post(
        "/market/buy",
        headers=shared_ip_trade_headers,
        json={"player_id": player_id, "shares": 3},
    )
    assert second_buy.status_code == 201, second_buy.text

    sell_one = client.post(
        "/market/sell",
        headers=looping_trade_headers,
        json={"player_id": player_id, "shares": 4},
    )
    assert sell_one.status_code == 201, sell_one.text
    _age_latest_trade(app_session_factory, user_id=looping_user.id, age=timedelta(minutes=9))
    runtime.state_store.delete(redis_keys.creator_cooldown(looping_user.id, player_id))

    buy_back = client.post(
        "/market/buy",
        headers=looping_trade_headers,
        json={"player_id": player_id, "shares": 4},
    )
    assert buy_back.status_code == 201, buy_back.text
    _age_latest_trade(app_session_factory, user_id=looping_user.id, age=timedelta(minutes=6))
    runtime.state_store.delete(redis_keys.creator_cooldown(looping_user.id, player_id))

    sell_back = client.post(
        "/market/sell",
        headers=looping_trade_headers,
        json={"player_id": player_id, "shares": 4},
    )
    assert sell_back.status_code == 201, sell_back.text

    shared_ip_flags = client.get(f"/admin/flags?user_id={shared_ip_user.id}", headers=bootstrap_admin_headers)
    assert shared_ip_flags.status_code == 200, shared_ip_flags.text
    assert "shared_ip_accounts" in {item["category"] for item in shared_ip_flags.json()}

    rapid_loop_flags = client.get(f"/admin/flags?user_id={looping_user.id}", headers=bootstrap_admin_headers)
    assert rapid_loop_flags.status_code == 200, rapid_loop_flags.text
    assert "rapid_trade_loop" in {item["category"] for item in rapid_loop_flags.json()}

    ban_response = client.post(
        "/admin/ban-user",
        headers=bootstrap_admin_headers,
        json={"user_id": looping_user.id, "reason": "Automated fraud test ban"},
    )
    assert ban_response.status_code == 200, ban_response.text
    banned_payload = ban_response.json()
    assert banned_payload["banned"] is True
    assert "block_trading" in banned_payload["actions_applied"]

    blocked_trade = client.post(
        "/market/buy",
        headers=looping_trade_headers,
        json={"player_id": player_id, "shares": 1},
    )
    assert blocked_trade.status_code == 401, blocked_trade.text


def test_ai_match_completion_updates_economy(client, app, app_session_factory):
    runtime = ensure_gtex_runtime(app)
    player_user, headers = _register_user(app_session_factory, label="league")
    _fund_user(app_session_factory, user_id=player_user.id, amount=Decimal("1000.0000"))
    match_request = client.post(
        "/match/find",
        headers=headers,
        json={"league_id": "ranked", "entry_fee": "50.0000", "metadata": {"scenario": "ai_match_completion"}},
    )
    assert match_request.status_code == 202, match_request.text
    queue_entry_id = match_request.json()["queue_entry_id"]
    matchmaker = AiMatchmakerWorker(context=_worker_context(app))
    ai_brain = AiBrainWorker(context=_worker_context(app))
    assert matchmaker.run_once() >= 1
    assert ai_brain.run_once() >= 1
    with app_session_factory() as session:
        from app.models.gtex_economy import GtexMatchQueueEntry

        queue_entry = session.get(GtexMatchQueueEntry, queue_entry_id)
        assert queue_entry is not None
        assert queue_entry.match_id is not None
        match_id = queue_entry.match_id
    match_response = client.get(f"/ai/match/{match_id}")
    assert match_response.status_code == 200, match_response.text
    match_payload = match_response.json()
    assert match_payload["status"] == "completed"
    assert match_payload["jackpot_contribution"] == "5.0000"
    assert match_payload["match_storyline"]
    assert match_payload["key_moments"]
    assert match_payload["player_highlights"]
    assert isinstance(match_payload["rivalry"], dict)
    assert isinstance(match_payload["match_context"], dict)
    leagues_response = client.get("/ai/leagues")
    assert leagues_response.status_code == 200
    assert leagues_response.json()["leagues"]
    jackpot_state = client.get("/jackpot/state").json()
    assert Decimal(jackpot_state["balance"]) >= Decimal("5.0000")
    with app_session_factory() as session:
        user_model = session.get(User, player_user.id)
        assert user_model is not None
        asset = runtime.creator_market.ensure_asset_for_user(session, user_model)
        assert asset.total_matches >= 1


def test_match_completion_projection_is_idempotent(client, app, app_session_factory):
    runtime = ensure_gtex_runtime(app)
    home_user, home_headers = _register_user(app_session_factory, label="league-home")
    away_user, away_headers = _register_user(app_session_factory, label="league-away")
    _fund_user(app_session_factory, user_id=home_user.id, amount=Decimal("1000.0000"))
    _fund_user(app_session_factory, user_id=away_user.id, amount=Decimal("1000.0000"))

    home_request = client.post(
        "/match/find",
        headers=home_headers,
        json={"league_id": "ranked", "entry_fee": "50.0000", "metadata": {"scenario": "idempotent_home"}},
    )
    assert home_request.status_code == 202, home_request.text
    away_request = client.post(
        "/match/find",
        headers=away_headers,
        json={"league_id": "ranked", "entry_fee": "50.0000", "metadata": {"scenario": "idempotent_away"}},
    )
    assert away_request.status_code == 202, away_request.text

    matchmaker = AiMatchmakerWorker(context=_worker_context(app))
    assert matchmaker.run_once() >= 1

    with app_session_factory() as session:
        from app.models.gtex_economy import GtexMatch, GtexMatchQueueEntry, GtexMatchStatus

        queue_entry = session.get(GtexMatchQueueEntry, home_request.json()["queue_entry_id"])
        assert queue_entry is not None
        assert queue_entry.match_id is not None
        match_id = queue_entry.match_id
        match = session.get(GtexMatch, match_id)
        assert match is not None
        match.status = GtexMatchStatus.COMPLETED
        match.started_at = match.started_at or utcnow()
        match.completed_at = utcnow()
        match.home_score = 2
        match.away_score = 1
        match.winner_participant_type = match.home_participant_type
        match.winner_user_id = home_user.id
        match.winner_ai_id = None
        match.metadata_json = {"scenario": "idempotent_manual_settlement"}
        transaction_count_before = session.scalar(select(func.count()).select_from(LedgerTransaction)) or 0
        runtime.economy.settle_match_completion(session, match=match)
        session.commit()

    with app_session_factory() as session:
        from app.models.gtex_economy import GtexMatch

        stored_match = session.get(GtexMatch, match_id)
        assert stored_match is not None
        assert stored_match.metadata_json["economy_settled_at"]
        checkpoint_count = session.scalar(
            select(func.count())
            .select_from(GlobalProjectionCheckpoint)
            .where(
                GlobalProjectionCheckpoint.event_name == MATCH_COMPLETED,
                GlobalProjectionCheckpoint.aggregate_id == stored_match.id,
            )
        )
        transaction_count_after_first = session.scalar(select(func.count()).select_from(LedgerTransaction)) or 0
        dynasty = session.scalar(select(UserDynasty).where(UserDynasty.user_id == home_user.id))
        assert dynasty is not None
        assert dynasty.earnings_minor > 0
        assert checkpoint_count == 1

        runtime.economy.settle_match_completion(session, match=stored_match)
        session.commit()

    with app_session_factory() as session:
        final_checkpoint_count = session.scalar(
            select(func.count())
            .select_from(GlobalProjectionCheckpoint)
            .where(
                GlobalProjectionCheckpoint.event_name == MATCH_COMPLETED,
                GlobalProjectionCheckpoint.aggregate_id == match_id,
            )
        )
        final_transaction_count = session.scalar(select(func.count()).select_from(LedgerTransaction)) or 0
        dynasty = session.scalar(select(UserDynasty).where(UserDynasty.user_id == home_user.id))
        assert dynasty is not None
        assert dynasty.earnings_minor > 0
        assert final_checkpoint_count == 1
        assert final_transaction_count == transaction_count_after_first
        assert final_transaction_count > transaction_count_before
