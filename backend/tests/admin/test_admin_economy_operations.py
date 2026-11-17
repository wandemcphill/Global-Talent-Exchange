from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.models.risk_ops import AuditLog


def test_admin_godmode_wallet_credit_dual_units_idempotency_and_audit(
    client,
    auth_user_factory,
    bootstrap_admin_headers,
    competition_admin_headers,
    app_session_factory,
) -> None:
    recipient = auth_user_factory(suffix="godmode-credit-target")

    # Non-admin & scoped admin without manage_payment_rails must get 403
    for blocked_headers in (recipient["headers"], competition_admin_headers):
        blocked = client.post(
            "/api/admin/god-mode/wallets/credit",
            headers=blocked_headers,
            json={
                "user_id": recipient["user_id"],
                "unit": "coin",
                "amount": "25",
                "reason": "Unauthorized credit attempt",
            },
        )
        assert blocked.status_code == 403, blocked.text

    # Credit GTEX Coin (coin) with idempotency key
    credit_coin = client.post(
        "/api/admin/god-mode/wallets/credit",
        headers=bootstrap_admin_headers,
        json={
            "user_id": recipient["user_id"],
            "unit": "coin",
            "amount": "125.5",
            "reason": "Seed winner GTC allocation",
            "idempotency_key": "godmode-credit-coin-001",
        },
    )
    assert credit_coin.status_code == 201, credit_coin.text
    coin_body = credit_coin.json()
    assert coin_body["unit"] == "coin"
    assert Decimal(str(coin_body["balance_before"])) == Decimal("0.0000")
    assert Decimal(str(coin_body["balance_after"])) == Decimal("125.5000")
    assert coin_body["idempotent_replay"] is False

    # Replaying exact same idempotency_key does not double-credit
    replay_coin = client.post(
        "/api/admin/god-mode/wallets/credit",
        headers=bootstrap_admin_headers,
        json={
            "user_id": recipient["user_id"],
            "unit": "coin",
            "amount": "125.5",
            "reason": "Seed winner GTC allocation",
            "idempotency_key": "godmode-credit-coin-001",
        },
    )
    assert replay_coin.status_code == 201, replay_coin.text
    assert replay_coin.json()["transaction_id"] == coin_body["transaction_id"]
    assert replay_coin.json()["idempotent_replay"] is True

    # Reusing the same idempotency_key with a different amount raises 409 conflict
    conflict = client.post(
        "/api/admin/god-mode/wallets/credit",
        headers=bootstrap_admin_headers,
        json={
            "user_id": recipient["user_id"],
            "unit": "coin",
            "amount": "999",
            "reason": "Conflicting payload test",
            "idempotency_key": "godmode-credit-coin-001",
        },
    )
    assert conflict.status_code == 409, conflict.text

    # Credit Fan Coin (credit) independently (preserve any welcome credit baseline)
    credit_before_resp = client.get("/api/wallets/summary?currency=credit", headers=recipient["headers"])
    assert credit_before_resp.status_code == 200, credit_before_resp.text
    credit_before = Decimal(str(credit_before_resp.json()["available_balance"]))

    credit_fnc = client.post(
        "/api/admin/god-mode/wallets/credit",
        headers=bootstrap_admin_headers,
        json={
            "user_id": recipient["user_id"],
            "unit": "credit",
            "amount": "75",
            "reason": "Fan Coin promo allocation",
            "idempotency_key": "godmode-credit-fnc-001",
        },
    )
    assert credit_fnc.status_code == 201, credit_fnc.text
    assert credit_fnc.json()["unit"] == "credit"
    assert Decimal(str(credit_fnc.json()["balance_before"])) == credit_before
    assert Decimal(str(credit_fnc.json()["balance_after"])) == credit_before + Decimal("75.0000")

    # Verify both wallet summaries + AuditLog persisted
    coin_summary = client.get("/api/wallets/summary?currency=coin", headers=recipient["headers"])
    credit_summary = client.get("/api/wallets/summary?currency=credit", headers=recipient["headers"])
    assert Decimal(str(coin_summary.json()["available_balance"])) == Decimal("125.5000")
    assert Decimal(str(credit_summary.json()["available_balance"])) == credit_before + Decimal("75.0000")

    with app_session_factory() as session:
        audit_rows = list(session.scalars(select(AuditLog).where(AuditLog.action_key == "admin.wallet.credited")).all())
        assert len(audit_rows) >= 2


def test_admin_wallet_credit_by_email_lands_in_the_personal_wallet(
    client,
    auth_user_factory,
    bootstrap_admin_headers,
) -> None:
    recipient = auth_user_factory(suffix="email-credit-target")
    before = client.get("/api/wallets/summary?currency=coin", headers=recipient["headers"])
    assert before.status_code == 200, before.text
    starting_balance = Decimal(str(before.json()["available_balance"]))

    credit = client.post(
        "/api/admin/god-mode/wallets/credit",
        headers=bootstrap_admin_headers,
        json={
            "user_id": recipient["email"],
            "unit": "coin",
            "amount": "200000",
            "reason": "Personal wallet credit by email",
        },
    )
    assert credit.status_code == 201, credit.text
    body = credit.json()
    assert body["email"] == recipient["email"]
    assert body["user_id"] == recipient["user_id"]
    assert body["wallet_label"] == "personal"
    assert Decimal(str(body["balance_after"])) == starting_balance + Decimal("200000.0000")

    after = client.get("/api/wallets/summary?currency=coin", headers=recipient["headers"])
    assert after.status_code == 200, after.text
    assert Decimal(str(after.json()["available_balance"])) == starting_balance + Decimal("200000.0000")

    missing = client.post(
        "/api/admin/god-mode/wallets/credit",
        headers=bootstrap_admin_headers,
        json={
            "user_id": "nobody@gtex.test",
            "unit": "coin",
            "amount": "1",
            "reason": "Unknown email must not succeed",
        },
    )
    assert missing.status_code == 404, missing.text


def test_admin_godmode_wallet_transfer_double_entry_and_validation(
    client,
    auth_user_factory,
    bootstrap_admin_headers,
    app_session_factory,
) -> None:
    sender = auth_user_factory(suffix="transfer-sender", funded_coin="200", funded_credit="100")
    receiver = auth_user_factory(suffix="transfer-receiver", funded_coin="10", funded_credit="5")

    # Self-transfer rejected
    same_user = client.post(
        "/api/admin/god-mode/wallets/transfer",
        headers=bootstrap_admin_headers,
        json={
            "from_user_id": sender["user_id"],
            "to_user_id": sender["user_id"],
            "unit": "coin",
            "amount": "10",
            "reason": "Invalid self transfer",
        },
    )
    assert same_user.status_code == 400, same_user.text

    # Insufficient balance rejected atomically
    too_much = client.post(
        "/api/admin/god-mode/wallets/transfer",
        headers=bootstrap_admin_headers,
        json={
            "from_user_id": sender["user_id"],
            "to_user_id": receiver["user_id"],
            "unit": "coin",
            "amount": "5000",
            "reason": "Exceeds available balance",
        },
    )
    assert too_much.status_code == 400, too_much.text

    # Valid atomic transfer for GTEX Coin and Fan Coin
    xfer_coin = client.post(
        "/api/admin/god-mode/wallets/transfer",
        headers=bootstrap_admin_headers,
        json={
            "from_user_id": sender["user_id"],
            "to_user_id": receiver["user_id"],
            "unit": "coin",
            "amount": "40",
            "reason": "Desk settlement adjustment GTC",
            "idempotency_key": "godmode-xfer-coin-001",
        },
    )
    assert xfer_coin.status_code == 201, xfer_coin.text
    assert Decimal(str(xfer_coin.json()["from_balance_before"])) == Decimal("200.0000")
    assert Decimal(str(xfer_coin.json()["from_balance_after"])) == Decimal("160.0000")
    assert Decimal(str(xfer_coin.json()["to_balance_before"])) == Decimal("10.0000")
    assert Decimal(str(xfer_coin.json()["to_balance_after"])) == Decimal("50.0000")

    xfer_credit = client.post(
        "/api/admin/god-mode/wallets/transfer",
        headers=bootstrap_admin_headers,
        json={
            "from_user_id": sender["user_id"],
            "to_user_id": receiver["user_id"],
            "unit": "credit",
            "amount": "25",
            "reason": "Desk settlement adjustment FNC",
            "idempotency_key": "godmode-xfer-credit-001",
        },
    )
    assert xfer_credit.status_code == 201, xfer_credit.text
    assert Decimal(str(xfer_credit.json()["from_balance_after"])) == (
        Decimal(str(xfer_credit.json()["from_balance_before"])) - Decimal("25.0000")
    )
    assert Decimal(str(xfer_credit.json()["to_balance_after"])) == (
        Decimal(str(xfer_credit.json()["to_balance_before"])) + Decimal("25.0000")
    )

    # Idempotent replay on transfer
    replay = client.post(
        "/api/admin/god-mode/wallets/transfer",
        headers=bootstrap_admin_headers,
        json={
            "from_user_id": sender["user_id"],
            "to_user_id": receiver["user_id"],
            "unit": "credit",
            "amount": "25",
            "reason": "Desk settlement adjustment FNC",
            "idempotency_key": "godmode-xfer-credit-001",
        },
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["idempotent_replay"] is True

    with app_session_factory() as session:
        audit_rows = list(
            session.scalars(select(AuditLog).where(AuditLog.action_key == "admin.wallet.transferred")).all()
        )
        assert len(audit_rows) >= 2


def test_admin_personal_user_points_grant_read_and_isolation(
    client,
    auth_user_factory,
    bootstrap_admin_headers,
    competition_admin_headers,
    app_session_factory,
) -> None:
    target = auth_user_factory(suffix="personal-points-user")
    coin_before = Decimal(
        str(client.get("/api/wallets/summary?currency=coin", headers=target["headers"]).json()["available_balance"])
    )
    credit_before = Decimal(
        str(client.get("/api/wallets/summary?currency=credit", headers=target["headers"]).json()["available_balance"])
    )

    # Non-admin & unprivileged scoped admin blocked from granting personal points
    for blocked_headers in (target["headers"], competition_admin_headers):
        res = client.post(
            "/api/admin/god-mode/points/grant",
            headers=blocked_headers,
            json={
                "user_id": target["user_id"],
                "amount": "100",
                "reason": "Blocked point grant",
            },
        )
        assert res.status_code == 403, res.text

    granted = client.post(
        "/api/admin/god-mode/points/grant",
        headers=bootstrap_admin_headers,
        json={
            "user_id": target["user_id"],
            "amount": "150",
            "reason": "Community ambassador milestone",
            "idempotency_key": "points-grant-001",
        },
    )
    assert granted.status_code == 201, granted.text
    grant_body = granted.json()
    assert Decimal(str(grant_body["balance_before"])) == Decimal("0.0000")
    assert Decimal(str(grant_body["balance_after"])) == Decimal("150.0000")
    assert grant_body["source_scope"] == "admin_grant"
    assert grant_body["idempotent_replay"] is False

    # Idempotent replay does not double grant
    replay = client.post(
        "/api/admin/god-mode/points/grant",
        headers=bootstrap_admin_headers,
        json={
            "user_id": target["user_id"],
            "amount": "150",
            "reason": "Community ambassador milestone",
            "idempotency_key": "points-grant-001",
        },
    )
    assert replay.status_code == 201, replay.text
    assert replay.json()["entry_id"] == grant_body["entry_id"]
    assert replay.json()["idempotent_replay"] is True

    # Mismatched idempotency key payload fails closed with 409
    mismatch = client.post(
        "/api/admin/god-mode/points/grant",
        headers=bootstrap_admin_headers,
        json={
            "user_id": target["user_id"],
            "amount": "999",
            "reason": "Conflicting key payload",
            "idempotency_key": "points-grant-001",
        },
    )
    assert mismatch.status_code == 409, mismatch.text

    # Admin read endpoint returns balance & ledger entries
    admin_read = client.get(
        f"/api/admin/god-mode/users/{target['user_id']}/points",
        headers=bootstrap_admin_headers,
    )
    assert admin_read.status_code == 200, admin_read.text
    assert Decimal(str(admin_read.json()["balance"])) == Decimal("150.0000")
    assert admin_read.json()["source_scope"] == "personal_reward_points"
    assert len(admin_read.json()["recent_entries"]) == 1

    # Self-service user read endpoint returns isolated personal reward balance without touching coin/credit wallets
    user_read = client.get("/users/me/points", headers=target["headers"])
    assert user_read.status_code == 200, user_read.text
    assert Decimal(str(user_read.json()["balance"])) == Decimal("150.0000")
    assert Decimal(str(user_read.json()["lifetime_earned"])) == Decimal("150.0000")

    coin_wallet = client.get("/api/wallets/summary?currency=coin", headers=target["headers"])
    credit_wallet = client.get("/api/wallets/summary?currency=credit", headers=target["headers"])
    assert Decimal(str(coin_wallet.json()["available_balance"])) == coin_before
    assert Decimal(str(credit_wallet.json()["available_balance"])) == credit_before

    with app_session_factory() as session:
        audit_rows = list(session.scalars(select(AuditLog).where(AuditLog.action_key == "admin.points.granted")).all())
        assert len(audit_rows) >= 1
