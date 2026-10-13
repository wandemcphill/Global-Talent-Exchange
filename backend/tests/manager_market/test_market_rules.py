from __future__ import annotations

from sqlalchemy import func, select

from backend.app.models.manager_market import ManagerCatalogEntry


def _catalog_by_id(client) -> dict[str, dict[str, object]]:
    response = client.get("/api/managers/catalog", params={"limit": 1000})
    assert response.status_code == 200
    payload = response.json()
    return {item["manager_id"]: item for item in payload["items"]}


def test_manager_catalog_is_seeded_during_app_startup(app, client) -> None:
    startup_thread = getattr(app.state, "deferred_startup_thread", None)
    if startup_thread is not None:
        startup_thread.join(timeout=30)
    _catalog_by_id(client)

    with app.state.session_factory() as session:
        total = session.scalar(select(func.count()).select_from(ManagerCatalogEntry))
        ferguson = session.scalar(
            select(ManagerCatalogEntry).where(ManagerCatalogEntry.manager_id == "sir-alex-ferguson")
        )
        pep = session.scalar(select(ManagerCatalogEntry).where(ManagerCatalogEntry.manager_id == "pep-guardiola"))

    assert total is not None and total > 0
    assert ferguson is not None
    assert ferguson.supply_total == 1
    assert ferguson.supply_available == 1
    assert pep is not None
    assert pep.supply_total == 1
    assert pep.supply_available == 1


def test_catalog_exposes_paid_recruit_pricing_and_manager_impact(client) -> None:
    catalog = _catalog_by_id(client)
    ferguson = catalog["sir-alex-ferguson"]
    pep = catalog["pep-guardiola"]
    assert float(ferguson["recruit_price_fancoin"]) > 0
    assert float(ferguson["annual_wage_fancoin"]) > 0
    assert int(ferguson["manager_impact"]) >= 80
    assert float(pep["recruit_price_fancoin"]) > 0
    assert int(pep["manager_impact"]) >= 70
