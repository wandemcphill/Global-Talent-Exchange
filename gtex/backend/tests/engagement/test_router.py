from __future__ import annotations

from sqlalchemy.orm import Session

from app.live_ops.service import LiveOpsService
from app.models.user import User


def test_engagement_routes_cover_predictions_finance_and_live_ops(
    engagement_client,
    engagement_app,
    session: Session,
) -> None:
    response = engagement_client.post(
        "/predictions",
        json={
            "match_id": "match-1",
            "predicted_outcome": "home_win",
            "confidence_level": 0.7,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["predicted_outcome"] == "home_win"

    leaderboard_response = engagement_client.get("/predictions/leaderboard")
    assert leaderboard_response.status_code == 200, leaderboard_response.text
    assert leaderboard_response.json()["entries"][0]["user_id"] == "fan-user"
    assert leaderboard_response.json()["entries"][0]["total_correct_predictions"] == 0

    finance_response = engagement_client.get("/finance")
    assert finance_response.status_code == 200, finance_response.text
    assert finance_response.json()["balance"] == "0.0000"

    sponsors_response = engagement_client.get("/sponsors")
    assert sponsors_response.status_code == 200, sponsors_response.text
    assert len(sponsors_response.json()) == 3

    season_pass_response = engagement_client.get("/season-pass")
    assert season_pass_response.status_code == 200, season_pass_response.text
    assert season_pass_response.json()["level"] == 1

    engagement_app.state.user_state["current_user"] = session.get(User, "fan-user")
    LiveOpsService(session).award_xp(
        user_id="fan-user",
        source_type="router_test",
        amount=200,
        reference_key="router-test-xp",
    )
    session.commit()

    claim_response = engagement_client.post("/season-pass/claim", json={"level": 1})
    assert claim_response.status_code == 200, claim_response.text
    assert claim_response.json()["level"] == 1

    live_events_response = engagement_client.get("/live-events")
    assert live_events_response.status_code == 200, live_events_response.text
    assert len(live_events_response.json()) >= 1
