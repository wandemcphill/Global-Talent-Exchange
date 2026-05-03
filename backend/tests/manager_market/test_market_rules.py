from __future__ import annotations

from sqlalchemy import func, select

from backend.app.models.manager_market import ManagerCatalogEntry, ManagerHolding


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
    return {
        item["manager_id"]: item
        for item in payload["items"]
    }


def _response_text(response) -> str:
    return str(response.json())


def test_manager_catalog_is_seeded_during_app_startup(app, client) -> None:
    startup_thread = getattr(app.state, "deferred_startup_thread", None)
    if startup_thread is not None:
        startup_thread.join(timeout=30)
    _catalog_by_id(client)

    with app.state.session_factory() as session:
        total = session.scalar(select(func.count()).select_from(ManagerCatalogEntry))
        ferguson = session.scalar(
            select(ManagerCatalogEntry).where(
                ManagerCatalogEntry.manager_id == "sir-alex-ferguson"
            )
        )
        pep = session.scalar(
            select(ManagerCatalogEntry).where(
                ManagerCatalogEntry.manager_id == "pep-guardiola"
            )
        )

    assert total is not None and total > 0
    assert ferguson is not None
    assert ferguson.supply_total == 1
    assert ferguson.supply_available == 1
    assert pep is not None
    assert pep.supply_total == 1
    assert pep.supply_available == 1


def test_free_recruitment_preserves_wallet_balance_and_enforces_scarcity(
    app,
    client,
    demo_seed,
) -> None:
    first_user_headers = _auth_headers_for(client, demo_seed.demo_users[0])
    second_user_headers = _auth_headers_for(client, demo_seed.demo_users[1])
    third_user_headers = _auth_headers_for(client, demo_seed.demo_users[2])

    wallet_before = client.get(
        "/api/wallets/summary",
        headers=first_user_headers,
    )
    assert wallet_before.status_code == 200
    before_payload = wallet_before.json()

    recruit_ferguson = client.post(
        "/api/managers/recruit",
        headers=first_user_headers,
        json={"manager_id": "sir-alex-ferguson", "slot": "bench"},
    )
    assert recruit_ferguson.status_code == 200

    wallet_after = client.get(
        "/api/wallets/summary",
        headers=first_user_headers,
    )
    assert wallet_after.status_code == 200
    after_payload = wallet_after.json()
    assert after_payload["available_balance"] == before_payload["available_balance"]
    assert after_payload["total_balance"] == before_payload["total_balance"]

    sold_out_ferguson = client.post(
        "/api/managers/recruit",
        headers=second_user_headers,
        json={"manager_id": "sir-alex-ferguson", "slot": "bench"},
    )
    assert sold_out_ferguson.status_code == 400
    assert "active digital copy" in _response_text(sold_out_ferguson)

    recruit_pep_first = client.post(
        "/api/managers/recruit",
        headers=first_user_headers,
        json={"manager_id": "pep-guardiola", "slot": "bench"},
    )
    assert recruit_pep_first.status_code == 200

    recruit_pep_second = client.post(
        "/api/managers/recruit",
        headers=second_user_headers,
        json={"manager_id": "pep-guardiola", "slot": "bench"},
    )
    assert recruit_pep_second.status_code == 400
    assert "active digital copy" in _response_text(recruit_pep_second)

    sold_out_pep = client.post(
        "/api/managers/recruit",
        headers=third_user_headers,
        json={"manager_id": "pep-guardiola", "slot": "bench"},
    )
    assert sold_out_pep.status_code == 400
    assert "active digital copy" in _response_text(sold_out_pep)

    catalog = _catalog_by_id(client)
    assert catalog["sir-alex-ferguson"]["supply_total"] == 1
    assert catalog["sir-alex-ferguson"]["supply_available"] == 0
    assert catalog["pep-guardiola"]["supply_total"] == 1
    assert catalog["pep-guardiola"]["supply_available"] == 0

    with app.state.session_factory() as session:
        ferguson_owned = session.scalar(
            select(func.count())
            .select_from(ManagerHolding)
            .where(
                ManagerHolding.manager_id == "sir-alex-ferguson",
                ManagerHolding.status.in_(["owned", "listed"]),
            )
        )
        pep_owned = session.scalar(
            select(func.count())
            .select_from(ManagerHolding)
            .where(
                ManagerHolding.manager_id == "pep-guardiola",
                ManagerHolding.status.in_(["owned", "listed"]),
            )
        )

    assert ferguson_owned == 1
    assert pep_owned == 1
