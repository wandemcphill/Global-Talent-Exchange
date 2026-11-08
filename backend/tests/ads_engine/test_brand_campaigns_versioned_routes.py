from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_current_user, get_optional_current_user, get_session
from app.main import create_app
from app.models.base import Base
from app.models.brand_ad_campaign import BrandAdCampaign
from app.models.brand_advertising import BrandAdEvent, BrandAdReviewEvent, BrandAdvertiserProfile
from app.models.user import User, UserRole
from app.modules import ensure_modules_loaded


@pytest.fixture(scope="module")
def app_and_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            BrandAdCampaign.__table__,
            BrandAdvertiserProfile.__table__,
            BrandAdEvent.__table__,
            BrandAdReviewEvent.__table__,
        ],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    advertiser_user = User(
        id="00000000-0000-4000-8000-000000000010",
        email="advertiser_v2@example.com",
        username="adv_v2",
        password_hash="pw",  # pragma: allowlist secret
        role=UserRole.USER,
    )
    admin_user = User(
        id="00000000-0000-4000-8000-000000000020",
        email="admin_v2@example.com",
        username="admin_v2",
        password_hash="pw",  # pragma: allowlist secret
        role=UserRole.ADMIN,
    )
    with factory() as session:
        session.add_all([advertiser_user, admin_user])
        session.commit()

    app = create_app(engine=engine, run_migration_check=False)
    ensure_modules_loaded(app)

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    yield app, factory, advertiser_user, admin_user


def test_versioned_brand_advertising_route_table_registration(app_and_db):
    app, _, _, _ = app_and_db
    route_paths = {route.path for route in app.routes}

    expected_v2_endpoints = {
        "/api/v2/ads/brand/profile",
        "/api/v2/ads/brand/campaigns",
        "/api/v2/ads/brand/campaigns/{campaign_id}",
        "/api/v2/ads/brand/campaigns/{campaign_id}/submit",
        "/api/v2/ads/brand/campaigns/{campaign_id}/history",
        "/api/v2/ads/brand/reports",
        "/api/v2/ads/brand/admin/campaigns",
        "/api/v2/ads/brand/admin/reports",
        "/api/v2/ads/brand/admin/campaigns/{campaign_id}/review",
        "/api/v2/ads/brand/admin/campaigns/{campaign_id}/music-rights",
        "/api/v2/ads/brand/admin/campaigns/{campaign_id}/conversions",
    }

    for expected_path in expected_v2_endpoints:
        assert expected_path in route_paths, f"Expected versioned route missing: {expected_path}"

    # Confirm that unversioned /api/ads/brand/... was NEVER mounted (explaining the 404 bug)
    assert "/api/ads/brand/admin/campaigns" not in route_paths
    assert "/api/ads/brand/admin/reports" not in route_paths
    assert "/api/ads/brand/campaigns" not in route_paths
    assert "/api/ads/brand/profile" not in route_paths


def test_unversioned_brand_requests_return_404(app_and_db):
    app, _, advertiser_user, admin_user = app_and_db
    client = TestClient(app)

    # Even with valid admin dependency overrides, the unversioned route produces 404
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    try:
        res1 = client.get("/api/ads/brand/admin/campaigns")
        assert res1.status_code == 404, f"Expected 404, got {res1.status_code}: {res1.text}"

        res2 = client.get("/api/ads/brand/admin/reports")
        assert res2.status_code == 404, f"Expected 404, got {res2.status_code}: {res2.text}"

        res3 = client.get("/api/ads/brand/campaigns")
        assert res3.status_code == 404, f"Expected 404, got {res3.status_code}: {res3.text}"

        res4 = client.get("/api/ads/brand/profile")
        assert res4.status_code == 404, f"Expected 404, got {res4.status_code}: {res4.text}"
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
        app.dependency_overrides.pop(get_current_user, None)


def test_versioned_admin_endpoints_require_admin_role(app_and_db):
    app, _, advertiser_user, admin_user = app_and_db
    client = TestClient(app)

    # 1. Unauthenticated -> 401
    app.dependency_overrides.pop(get_current_admin, None)
    app.dependency_overrides.pop(get_current_user, None)

    res_unauth = client.get("/api/v2/ads/brand/admin/campaigns")
    assert res_unauth.status_code == 401

    # 2. Authenticated as non-admin user -> 403
    def mock_non_admin_attempt():
        from fastapi import HTTPException, status

        if advertiser_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
        return advertiser_user

    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    app.dependency_overrides[get_current_admin] = mock_non_admin_attempt

    res_forbidden = client.get("/api/v2/ads/brand/admin/campaigns")
    assert res_forbidden.status_code == 403

    # 3. Authenticated as admin user -> 200 OK
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    res_admin = client.get("/api/v2/ads/brand/admin/campaigns")
    assert res_admin.status_code == 200
    admin_body = res_admin.json()
    campaigns = admin_body.get("data") if isinstance(admin_body, dict) and "data" in admin_body else admin_body
    assert isinstance(campaigns, list)

    res_reports = client.get("/api/v2/ads/brand/admin/reports")
    assert res_reports.status_code == 200
    reports_body = res_reports.json()
    data = reports_body.get("data") if isinstance(reports_body, dict) and "data" in reports_body else reports_body
    assert "reports" in data


def test_versioned_advertiser_endpoints_require_authenticated_user(app_and_db):
    app, _, advertiser_user, _ = app_and_db
    client = TestClient(app)

    # 1. Unauthenticated -> 401
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)

    res_unauth = client.get("/api/v2/ads/brand/campaigns")
    assert res_unauth.status_code == 401

    # 2. Authenticated -> 200 OK
    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    res_auth = client.get("/api/v2/ads/brand/campaigns")
    assert res_auth.status_code == 200
    body = res_auth.json()
    campaigns = body.get("data") if isinstance(body, dict) and "data" in body else body
    assert isinstance(campaigns, list)

    res_profile = client.get("/api/v2/ads/brand/profile")
    assert res_profile.status_code == 200


def test_public_advertising_endpoints_remain_accessible(app_and_db):
    app, _, _, _ = app_and_db
    client = TestClient(app)

    # Public delivery should be reachable without auth
    res_campaigns = client.get("/public/ads/campaigns?placement=homepage_rail")
    assert res_campaigns.status_code in {200, 204}

    res_music = client.get("/public/ads/music/promotions")
    assert res_music.status_code == 200
