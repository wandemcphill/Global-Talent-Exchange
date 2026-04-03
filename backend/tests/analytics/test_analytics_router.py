from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.tests.support.secrets import TEST_PASSWORD
from app.auth.service import AuthService, DuplicateUserError
from app.main import INITIAL_ADMIN_DISPLAY_NAME, INITIAL_ADMIN_EMAIL, INITIAL_ADMIN_PASSWORD
from app.models.competitive_integrity import Match, CompetitiveMatchCompetitionType, CompetitiveMatchStatus
from app.models.player_cards import PlayerCardMomentum
from app.models.risk_ops import SystemEvent, SystemEventSeverity
from app.models.user import User


def _prepare_admin(client, app_session_factory) -> None:
    startup_thread = getattr(client.app.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)
    with app_session_factory() as session:
        try:
            AuthService().ensure_admin_user(
                session,
                email=INITIAL_ADMIN_EMAIL,
                password=INITIAL_ADMIN_PASSWORD,
                username="analytics-admin",
                display_name=INITIAL_ADMIN_DISPLAY_NAME,
            )
        except (DuplicateUserError, IntegrityError):
            session.rollback()
            assert session.scalar(select(User).where(User.email == INITIAL_ADMIN_EMAIL)) is not None
        session.commit()


def _login_admin(client) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": INITIAL_ADMIN_EMAIL, "password": INITIAL_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_user_headers(app_session_factory, *, email: str, username: str) -> dict[str, str]:
    with app_session_factory() as session:
        existing = session.scalar(select(User).where(User.email == email))
        if existing is None:
            user = AuthService().register_user(
                session,
                email=email,
                username=username,
                password=TEST_PASSWORD,
            )
        else:
            user = session.get(User, existing.id)
        token, _ = AuthService().issue_access_token(user, session=session)
        session.commit()
        return {"Authorization": f"Bearer {token}"}


def _seed_analytics_insight_state(app_session_factory) -> str:
    with app_session_factory() as session:
        home_user = session.scalar(select(User).where(User.email == "analytics-home@example.com"))
        if home_user is None:
            home_user = AuthService().register_user(
                session,
                email="analytics-home@example.com",
                username="analyticshome",
                password=TEST_PASSWORD,
            )
        else:
            home_user = session.get(User, home_user.id)

        away_user = session.scalar(select(User).where(User.email == "analytics-away@example.com"))
        if away_user is None:
            away_user = AuthService().register_user(
                session,
                email="analytics-away@example.com",
                username="analyticsaway",
                password=TEST_PASSWORD,
            )
        else:
            away_user = session.get(User, away_user.id)

        momentum = session.get(PlayerCardMomentum, "analytics-player-1")
        if momentum is None:
            session.add(
                PlayerCardMomentum(
                    player_id="analytics-player-1",
                    last_trade_price_credits=Decimal("75.0000"),
                    momentum_7d_pct=Decimal("12.5000"),
                    momentum_30d_pct=Decimal("18.0000"),
                    trend_direction="up",
                    metadata_json={},
                )
            )

        match = session.scalar(
            select(Match).where(
                Match.home_user_id == home_user.id,
                Match.away_user_id == away_user.id,
            )
        )
        if match is None:
            now = datetime.now(timezone.utc)
            match = Match(
                competition_type=CompetitiveMatchCompetitionType.CASUAL,
                home_user_id=home_user.id,
                away_user_id=away_user.id,
                is_user_online_home=False,
                is_user_online_away=False,
                locked_lineup_home={},
                locked_lineup_away={},
                kickoff_at=now - timedelta(hours=2),
                status=CompetitiveMatchStatus.COMPLETED,
                result_payload={"summary": {"home_score": 6, "away_score": 4, "upset": True}},
                started_at=now - timedelta(hours=2),
                completed_at=now - timedelta(hours=1, minutes=40),
            )
            session.add(match)
            session.flush()

        if session.scalar(select(SystemEvent).where(SystemEvent.event_key == "analytics-anomaly-1")) is None:
            session.add(
                SystemEvent(
                    event_key="analytics-anomaly-1",
                    event_type="integrity_anomaly",
                    severity=SystemEventSeverity.CRITICAL,
                    title="Integrity anomaly",
                    body="Suspicious match pattern detected.",
                    subject_type="competitive_match",
                    subject_id=match.id,
                    metadata_json={"match_id": match.id},
                )
            )

        session.commit()
        return match.id


def test_analytics_event_tracking_enriches_device_fingerprint(client, app_session_factory) -> None:
    headers = {
        **_create_user_headers(
            app_session_factory,
            email="analytics-user@example.com",
            username="analyticsuser",
        ),
        "X-Device-Id": "device-analytics-1",
        "User-Agent": "analytics-test-client",
        "Accept-Language": "en-NG",
    }

    response = client.post(
        "/api/analytics/events",
        headers=headers,
        json={"name": "signup_started", "metadata": {"source": "tests"}},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["metadata_json"]["source"] == "tests"
    assert payload["metadata_json"]["device_fingerprint"]
    assert "x-device-id" in payload["metadata_json"]["device_signal_sources"]
    assert "user-agent" in payload["metadata_json"]["device_signal_sources"]

    fingerprint_response = client.get("/api/analytics/device-fingerprint", headers=headers)
    assert fingerprint_response.status_code == 200, fingerprint_response.text
    fingerprint_payload = fingerprint_response.json()
    assert fingerprint_payload["fingerprint"] == payload["metadata_json"]["device_fingerprint"]
    assert "x-device-id" in fingerprint_payload["source_signals"]


def test_influencer_leaderboard_route_returns_contract(client) -> None:
    response = client.get("/api/analytics/influencer-leaderboard")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["metric"] == "fraud_adjusted_score"
    assert isinstance(payload["items"], list)


def test_admin_analytics_routes_return_insight_payloads(client, app_session_factory) -> None:
    _prepare_admin(client, app_session_factory)
    headers = _login_admin(client)
    match_id = _seed_analytics_insight_state(app_session_factory)

    predictions_response = client.get("/api/admin/analytics/price-predictions", headers=headers)
    assert predictions_response.status_code == 200, predictions_response.text
    predictions_payload = predictions_response.json()
    assert any(item["player_id"] == "analytics-player-1" for item in predictions_payload["items"])

    segments_response = client.get("/api/admin/analytics/user-segments", headers=headers)
    assert segments_response.status_code == 200, segments_response.text
    assert segments_response.json()["segments"]

    outcomes_response = client.get("/api/admin/analytics/match-outcomes", headers=headers)
    assert outcomes_response.status_code == 200, outcomes_response.text
    outcomes_payload = outcomes_response.json()
    assert outcomes_payload["matches"] >= 1
    assert outcomes_payload["upset_rate"] > 0

    anomalies_response = client.get("/api/admin/analytics/anomalies", headers=headers)
    assert anomalies_response.status_code == 200, anomalies_response.text
    anomalies_payload = anomalies_response.json()
    assert anomalies_payload["critical_count"] >= 1
    assert anomalies_payload["matches_scanned"] >= 1
    assert anomalies_payload["flagged_matches"] >= 1
    assert any(item["match_id"] == match_id for item in anomalies_payload["top_findings"])

    learning_response = client.get("/api/admin/analytics/agent-learning", headers=headers)
    assert learning_response.status_code == 200, learning_response.text
    learning_payload = learning_response.json()
    assert learning_payload["mode"] == "adaptive_heuristics"
    assert learning_payload["status"] == "active"
