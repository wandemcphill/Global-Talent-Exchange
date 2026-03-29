from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from app.auth.service import AuthService
from app.gtex import redis_keys
from app.gtex.runtime import ensure_gtex_runtime
from app.gtex.worker_runtime import AiBrainWorker, AiMatchmakerWorker, JackpotWorker, WorkerContext
from app.models.base import utcnow
from app.models.gtex_economy import GtexCreatorTrade
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
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
