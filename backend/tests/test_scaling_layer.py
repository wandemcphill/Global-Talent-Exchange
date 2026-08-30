from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.core.api_contract import install_api_contracts
from app.core.pagination import MAX_PER_PAGE
from app.core.rate_limit import MemoryRateLimitStore, RateLimitMiddleware
from app.core.response_cache import NamespacedResponseCache
from app.ingestion.models import Player
from app.models.player_token_market import PlayerShareMarket
from app.models.treasury import PaymentMode
from app.players.token_service import PlayerTokenMarketService
from app.treasury.service import TreasuryService


class FakeCacheBackend:
    enabled = True

    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[dict[str, object]] = []

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.values[key] = value
        self.set_calls.append({"key": key, "ttl_seconds": ttl_seconds})

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.values.pop(key, None)

    def increment(self, key: str, amount: int = 1) -> int:
        current = int(self.values.get(key, "0")) + amount
        self.values[key] = str(current)
        return current

    def ping(self) -> bool:
        return True


class _FakeGatewayResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


def _stub_korapay_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GTE_KORAPAY_SECRET_KEY", "sk_test_korapay")
    monkeypatch.setenv("GTE_KORAPAY_ENCRYPTION_KEY", "test-korapay-encryption-key")
    amounts_by_reference: dict[str, object] = {}

    def fake_post(url, *, json, headers, timeout):  # noqa: ANN001
        del url, headers, timeout
        reference = str(json["reference"])
        amounts_by_reference[reference] = json["amount"]
        return _FakeGatewayResponse(
            {
                "data": {
                    "checkout_url": f"https://checkout.korapay.test/pay/{reference}",
                    "payment_reference": reference,
                    "reference": reference,
                }
            }
        )

    def fake_get(url, *, headers, timeout):  # noqa: ANN001
        del headers, timeout
        reference = str(url).rstrip("/").rsplit("/", maxsplit=1)[-1]
        return _FakeGatewayResponse(
            {
                "data": {
                    "id": f"evt-{reference}",
                    "status": "success",
                    "amount": str(amounts_by_reference.get(reference, "250.0000")),
                    "payment_reference": reference,
                    "reference": reference,
                }
            }
        )

    monkeypatch.setattr("app.wallets.funding_service.httpx.post", fake_post)
    monkeypatch.setattr("app.wallets.funding_service.httpx.get", fake_get)


def test_player_markets_cache_hit_and_invalidation(
    client,
    demo_seed,
    app_session_factory,
    bootstrap_admin_headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del demo_seed
    fake_cache = FakeCacheBackend()
    original_cache_backend = getattr(client.app.state, "cache_backend", None)
    original_response_cache = getattr(client.app.state, "response_cache", None)
    client.app.state.cache_backend = fake_cache
    client.app.state.response_cache = NamespacedResponseCache(fake_cache)

    try:
        with app_session_factory() as session:
            player_id = session.scalar(
                select(Player.id)
                .outerjoin(PlayerShareMarket, PlayerShareMarket.player_id == Player.id)
                .where(Player.is_tradable.is_(True), PlayerShareMarket.id.is_(None))
                .limit(1)
            )
        assert player_id is not None

        create_market = client.post(
            f"/players/{player_id}/shares/market",
            headers=bootstrap_admin_headers,
            json={
                "total_shares": 1000,
                "share_price_coin": "5.0000",
                "liquidity_coin": "2500.0000",
                "status": "active",
            },
        )
        assert create_market.status_code == 200, create_market.text

        call_count = 0
        original_list_markets = PlayerTokenMarketService.list_markets

        def wrapped_list_markets(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_list_markets(self, *args, **kwargs)

        monkeypatch.setattr(PlayerTokenMarketService, "list_markets", wrapped_list_markets)

        first = client.get("/players/markets")
        assert first.status_code == 200, first.text
        assert first.json()["pagination"]["page"] == 1
        # N73 raised the default player-markets cache TTL from 5s to 300s to
        # cut DB load after the market-list OOM incident; this asserts the
        # cache is wired up at all, not a specific duration.
        assert fake_cache.set_calls[-1]["ttl_seconds"] == 300

        second = client.get("/players/markets")
        assert second.status_code == 200, second.text
        assert call_count == 1

        reprice = client.post(
            f"/players/{player_id}/shares/performance",
            headers=bootstrap_admin_headers,
            json={"multiplier": "1.0100", "reason": "cache_invalidation_test"},
        )
        assert reprice.status_code == 200, reprice.text

        third = client.get("/players/markets")
        assert third.status_code == 200, third.text
        assert call_count == 2
    finally:
        client.app.state.cache_backend = original_cache_backend
        client.app.state.response_cache = original_response_cache


def test_competitions_pagination_defaults_and_clamps(client, demo_seed) -> None:
    del demo_seed
    default_page = client.get("/competitions")
    assert default_page.status_code == 200, default_page.text
    default_payload = default_page.json()
    assert "items" in default_payload
    assert default_payload["pagination"]["page"] == 1
    assert default_payload["pagination"]["per_page"] == 20

    clamped_page = client.get("/competitions", params={"per_page": 999})
    assert clamped_page.status_code == 200, clamped_page.text
    clamped_payload = clamped_page.json()
    assert clamped_payload["pagination"]["per_page"] == MAX_PER_PAGE
    assert "total" in clamped_payload["pagination"]


def test_wallet_top_up_verify_settles_synchronously_and_credits_wallet(
    auth_user_factory, app_session_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # /wallet/top-up/verify calls out to the payment gateway and credits the
    # wallet within the same request/response cycle - it never touches a task
    # queue. This is deliberate: the funding flow screen shows the new balance
    # immediately from this response (no polling), and buying player shares
    # right after verifying a deposit (the critical E2E path) depends on the
    # balance already being posted by the time verify returns. See PR #82's
    # merge commit for the prior audit that identified and deferred this.
    #
    # Called through the router functions directly (request=None), matching
    # tests/wallets/test_wallet_router.py's established pattern for this
    # flow: going through the real HTTP Request pulls in the module-scoped
    # app's persisted AdminGodMode payment-rail state, which is a separate
    # admin on/off toggle unrelated to what this test verifies.
    from app.models.user import User
    from app.wallets.router import initiate_wallet_top_up, verify_wallet_top_up
    from app.wallets.schemas import WalletTopUpInitiateRequest, WalletTopUpVerifyRequest

    _stub_korapay_gateway(monkeypatch)
    with app_session_factory() as session:
        settings = TreasuryService().ensure_settings(session)
        original_deposit_mode = settings.deposit_mode
        settings.deposit_mode = PaymentMode.AUTOMATIC
        session.commit()
    try:
        user = auth_user_factory(suffix="wallet-sync-verify")

        with app_session_factory() as session:
            current_user = session.get(User, user["user_id"])
            initiated = initiate_wallet_top_up(
                WalletTopUpInitiateRequest(amount=Decimal("250")),
                session=session,
                current_user=current_user,
            )
            assert initiated.status == "pending"
            reference = initiated.reference

            verified = verify_wallet_top_up(
                WalletTopUpVerifyRequest(reference=reference),
                session=session,
                current_user=current_user,
            )
            assert verified.transaction.status == "verified"
            assert verified.transaction.reference == reference
            assert verified.wallet.balance == Decimal("246.2500")
    finally:
        with app_session_factory() as session:
            settings = TreasuryService().ensure_settings(session)
            settings.deposit_mode = original_deposit_mode
            session.commit()


def test_wallet_top_up_verify_rejects_unknown_reference(client, auth_user_factory) -> None:
    user = auth_user_factory(suffix="wallet-unknown-reference")

    response = client.post(
        "/wallet/top-up/verify",
        headers=user["headers"],
        json={"reference": "REF-DOES-NOT-EXIST"},
    )

    assert response.status_code == 400, response.text
    assert response.json() == {
        "error": True,
        "message": "Wallet transaction was not found.",
        "code": "bad_request",
    }


def test_auth_and_validation_errors_use_standard_envelope(client) -> None:
    auth_response = client.get("/wallet")
    assert auth_response.status_code == 401, auth_response.text
    assert auth_response.json()["error"] is True
    assert auth_response.json()["code"] == "unauthorized"

    validation_response = client.get("/regen-universe/rankings", params={"page": 0})
    assert validation_response.status_code == 422, validation_response.text
    assert validation_response.json()["error"] is True
    assert validation_response.json()["code"] == "validation_error"


def test_sensitive_rate_limit_override_returns_standard_429(monkeypatch: pytest.MonkeyPatch, test_settings) -> None:
    import app.core.rate_limit as rate_limit_module

    settings = replace(
        test_settings,
        distributed_rate_limit_enabled=True,
        redis_url=None,
        api_rate_limit_per_minute=100,
        auth_rate_limit_per_minute=100,
        market_rate_limit_per_minute=100,
        wallet_rate_limit_per_minute=100,
        wallet_read_rate_limit_per_minute=100,
        sensitive_rate_limit_per_minute=1,
    )
    monkeypatch.setattr(rate_limit_module, "extract_access_token_subject", lambda _request: "user-1")

    app = FastAPI()
    app.state.settings = settings
    install_api_contracts(app)
    app.add_middleware(RateLimitMiddleware)

    @app.post("/market/buy")
    def buy() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/regular")
    def regular(limit: int = Query(default=1, ge=1)) -> dict[str, bool]:
        return {"ok": limit > 0}

    with TestClient(app) as isolated_client:
        first = isolated_client.post("/market/buy")
        second = isolated_client.post("/market/buy")
        regular = isolated_client.get("/regular")

    assert first.status_code == 200, first.text
    assert second.status_code == 429, second.text
    assert second.json()["error"] is True
    assert second.json()["code"] == "rate_limit_exceeded"
    assert regular.status_code == 200, regular.text


def test_wallet_read_rate_limit_is_separate_from_wallet_writes(
    monkeypatch: pytest.MonkeyPatch,
    test_settings,
) -> None:
    import app.core.rate_limit as rate_limit_module

    settings = replace(
        test_settings,
        distributed_rate_limit_enabled=True,
        redis_url=None,
        api_rate_limit_per_minute=100,
        auth_rate_limit_per_minute=100,
        market_rate_limit_per_minute=100,
        wallet_rate_limit_per_minute=1,
        wallet_read_rate_limit_per_minute=2,
        sensitive_rate_limit_per_minute=100,
    )
    monkeypatch.setattr(rate_limit_module, "extract_access_token_subject", lambda _request: "user-1")

    app = FastAPI()
    app.state.settings = settings
    install_api_contracts(app)
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/wallets/overview")
    def wallet_overview() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/wallets/convert")
    def wallet_convert() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as isolated_client:
        first_read = isolated_client.get("/api/wallets/overview")
        second_read = isolated_client.get("/api/wallets/overview")
        third_read = isolated_client.get("/api/wallets/overview")
        first_write = isolated_client.post("/api/wallets/convert")
        second_write = isolated_client.post("/api/wallets/convert")

    assert first_read.status_code == 200, first_read.text
    assert second_read.status_code == 200, second_read.text
    assert third_read.status_code == 429, third_read.text
    assert third_read.headers["X-RateLimit-Scope"] == "wallet_read"
    assert first_write.status_code == 200, first_write.text
    assert second_write.status_code == 429, second_write.text
    assert second_write.headers["X-RateLimit-Scope"] == "wallet"


def test_memory_rate_limit_store_resets_after_window(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.core.rate_limit as rate_limit_module

    store = MemoryRateLimitStore()
    baseline = datetime(2026, 4, 2, tzinfo=timezone.utc)
    monkeypatch.setattr(rate_limit_module, "_utcnow", lambda: baseline)
    first_count, _ = store.increment(key="gte:test", window_seconds=60)
    second_count, _ = store.increment(key="gte:test", window_seconds=60)
    monkeypatch.setattr(rate_limit_module, "_utcnow", lambda: baseline + timedelta(seconds=61))
    reset_count, _ = store.increment(key="gte:test", window_seconds=60)

    assert first_count == 1
    assert second_count == 2
    assert reset_count == 1
