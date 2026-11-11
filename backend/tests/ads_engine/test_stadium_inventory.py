"""Stadium perimeter inventory: only live, paid, approved, in-window stadium campaigns are delivered."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from itertools import count

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ads_engine.brand_campaigns import public_router
from app.auth.dependencies import get_session
from app.models.base import Base
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent
from app.models.commercial_network import AdvertiserWorkspace

_seq = count(1)


def _build() -> tuple[TestClient, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(public_router, prefix="/public/ads")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[BrandAdCampaign.__table__, BrandAdEvent.__table__, AdvertiserWorkspace.__table__],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    return TestClient(app), factory


def _add(factory: sessionmaker[Session], **overrides) -> str:
    now = datetime.now(UTC)
    values = {
        "brand_name": f"Brand {next(_seq)}",
        "headline": "Official partner",
        "placement": "stadium_perimeter",
        "placements_json": ["stadium_perimeter"],
        "destination_url": "https://brand.example.com",
        "campaign_type": "brand",
        "status": "active",
        "payment_status": "paid",
        "is_approved": True,
        "is_active": True,
        "start_at": now - timedelta(hours=1),
        "end_at": now + timedelta(days=3),
        "priority": 100,
    }
    values.update(overrides)
    with factory() as session:
        row = BrandAdCampaign(**values)
        session.add(row)
        session.commit()
        return row.id


def _ids(client: TestClient) -> list[str]:
    res = client.get("/public/ads/stadium/inventory")
    assert res.status_code == 200, res.text
    return [c["id"] for c in res.json()["campaigns"]]


def test_empty_inventory_returns_no_campaigns_so_house_ads_are_used() -> None:
    client, _ = _build()
    assert _ids(client) == []


def test_only_paid_approved_live_stadium_campaigns_are_returned() -> None:
    client, factory = _build()
    now = datetime.now(UTC)
    live = _add(factory)
    _add(factory, payment_status="unpaid")
    _add(factory, payment_status="pending")
    _add(factory, status="paused", is_active=False)
    _add(factory, is_approved=False)
    _add(factory, end_at=now - timedelta(minutes=1))
    _add(factory, start_at=now + timedelta(days=1), end_at=now + timedelta(days=5))
    _add(factory, placement="homepage_hero", placements_json=["homepage_hero"])
    _add(factory, campaign_type="music")
    _add(factory, destination_url="javascript:alert(1)")

    assert _ids(client) == [live]


def test_suspended_workspace_is_excluded() -> None:
    client, factory = _build()
    with factory() as session:
        ok = AdvertiserWorkspace(
            id="ws-ok", owner_user_id="u1", company_name="Ok", contact_email="ok@example.com", status="active"
        )
        bad = AdvertiserWorkspace(
            id="ws-bad", owner_user_id="u2", company_name="Bad", contact_email="bad@example.com", status="suspended"
        )
        session.add_all([ok, bad])
        session.commit()
    good_id = _add(factory, workspace_id="ws-ok")
    _add(factory, workspace_id="ws-bad")
    assert _ids(client) == [good_id]


def test_priority_order_and_budget_exhaustion() -> None:
    client, factory = _build()
    low = _add(factory, priority=10)
    high = _add(factory, priority=300)
    exhausted = _add(factory, pricing_model="CPM", budget_amount=1, unit_price=1)
    with factory() as session:
        for index in range(1000):
            session.add(
                BrandAdEvent(
                    campaign_id=exhausted,
                    event_type="impression",
                    idempotency_key=f"imp-{index}",
                    event_source="server",
                    metadata_json={},
                )
            )
        session.commit()
    assert _ids(client) == [high, low]


def test_asset_backed_creative_resolves_and_video_creative_is_not_drawn() -> None:
    client, factory = _build()
    image_id = _add(factory, creative_asset_id="asset-img", creative_media_type="image/png", priority=200)
    video_id = _add(factory, creative_asset_id="asset-vid", creative_media_type="video/mp4", priority=100)
    body = client.get("/public/ads/stadium/inventory").json()["campaigns"]
    by_id = {c["id"]: c for c in body}
    assert by_id[image_id]["creative_url"] == "/api/v2/public/ads/media/asset-img"
    assert by_id[video_id]["creative_url"] is None
    assert all(c["placement"] == "stadium_perimeter" for c in body)
