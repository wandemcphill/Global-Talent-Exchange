from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from backend.app.models.manager_market import ManagerHolding
from backend.app.models.wallet import LedgerUnit


def _auth_headers_for(client, user) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": user.password},
    )
    assert response.status_code == 200
    payload = response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}


def _catalog_by_id(client) -> dict[str, dict[str, object]]:
    response = client.get("/api/managers/catalog", params={"limit": 1000})
    assert response.status_code == 200
    payload = response.json()
    return {item["manager_id"]: item for item in payload["items"]}


def test_paid_recruitment_debits_fancoin_and_enforces_scarcity(
    app,
    client,
    demo_seed,
) -> None:
    first_user_headers = _auth_headers_for(client, demo_seed.demo_users[0])
    second_user_headers = _auth_headers_for(client, demo_seed.demo_users[1])

    catalog = _catalog_by_id(client)
    ferguson = catalog["sir-alex-ferguson"]
    recruit_price = Decimal(str(ferguson["recruit_price_fancoin"]))
    assert recruit_price > 0
    assert int(ferguson["manager_impact"]) >= 1

    wallet_before = client.get(
        "/api/wallets/summary",
        headers=first_user_headers,
        params={"currency": LedgerUnit.CREDIT.value},
    )
    assert wallet_before.status_code == 200
    before_payload = wallet_before.json()
    before_balance = Decimal(str(before_payload["available_balance"]))

    recruit_ferguson = client.post(
        "/api/managers/recruit",
        headers=first_user_headers,
        json={"manager_id": "sir-alex-ferguson", "slot": "bench"},
    )
    assert recruit_ferguson.status_code == 200, recruit_ferguson.text

    wallet_after = client.get(
        "/api/wallets/summary",
        headers=first_user_headers,
        params={"currency": LedgerUnit.CREDIT.value},
    )
    assert wallet_after.status_code == 200
    after_balance = Decimal(str(wallet_after.json()["available_balance"]))
    assert after_balance == before_balance - recruit_price

    sold_out = client.post(
        "/api/managers/recruit",
        headers=second_user_headers,
        json={"manager_id": "sir-alex-ferguson", "slot": "bench"},
    )
    assert sold_out.status_code == 400
    assert "active digital copy" in str(sold_out.json())

    with app.state.session_factory() as session:
        owned = session.scalar(
            select(func.count())
            .select_from(ManagerHolding)
            .where(
                ManagerHolding.manager_id == "sir-alex-ferguson",
                ManagerHolding.status.in_(["owned", "listed"]),
            )
        )
    assert owned == 1
