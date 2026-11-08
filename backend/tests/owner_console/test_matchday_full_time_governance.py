"""End-whistle -> Owner Authority bridge: gift income becomes a governed, idempotent decision."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.auth.dependencies import get_current_user
from app.models.competition_match import CompetitionMatch
from app.models.user import User, UserRole
from app.owner_console import ledger
from app.owner_console.models import ClubDelegatedDecision, ClubDelegatedDecisionAuditLog, OwnerInboxItem
from backend.tests.owner_console.test_react_gifting_live_broadcast import _build_test_app


def _add_match(
    app,
    *,
    completed: bool,
    home_club_id: str = "home",
    away_club_id: str = "away",
    metadata_json: dict | None = None,
) -> str:
    match_id = f"match-{uuid.uuid4().hex[:8]}"
    with app.state.session_factory() as session:
        session.add(
            CompetitionMatch(
                id=match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id=home_club_id,
                away_club_id=away_club_id,
                status="completed" if completed else "in_progress",
                completed_at=datetime.now(UTC) if completed else None,
                metadata_json=metadata_json or {},
            )
        )
        session.commit()
    return match_id


def _gift(client: TestClient, club_id: str, match_id: str, code: str = "stadium_roar") -> None:
    res = client.post("/owner/gifts/send", json={"club_id": club_id, "gift_code": code, "match_id": match_id})
    assert res.status_code == 200, res.text


def _club_balance(app, club_id: str):
    with app.state.session_factory() as session:
        return ledger.balance(session, ledger.club_account(club_id), ledger.FAN)


def test_unknown_match_is_404_and_incomplete_match_is_409(tmp_path):
    app, _user_id, _club_id, _hub = _build_test_app(tmp_path)
    client = TestClient(app)
    assert client.post("/owner/matches/nope/full-time-governance").status_code == 404

    live = _add_match(app, completed=False)
    res = client.post(f"/owner/matches/{live}/full-time-governance")
    assert res.status_code == 409
    assert res.json()["detail"]["code"] == "match_not_complete"


def test_full_time_escalates_gift_income_to_owner_and_is_idempotent(tmp_path):
    app, user_id, club_id, _hub = _build_test_app(tmp_path)
    client = TestClient(app)
    match_id = _add_match(app, completed=True)
    _gift(client, club_id, match_id, "stadium_roar")
    _gift(client, club_id, match_id, "captains_armband")
    balance_before = _club_balance(app, club_id)

    first = client.post(f"/owner/matches/{match_id}/full-time-governance")
    assert first.status_code == 200, first.text
    results = first.json()["results"]
    assert len(results) == 1
    proposed = results[0]
    assert proposed["outcome"] == "proposed"
    assert proposed["club_id"] == club_id
    # Reserved owner decision: must not be auto-approved by the system actor.
    assert proposed["decision_status"] == "pending_approval"
    assert proposed["requires_owner_approval"] is True
    assert proposed["gift_count"] == 2

    second = client.post(f"/owner/matches/{match_id}/full-time-governance")
    assert second.status_code == 200
    again = second.json()["results"][0]
    assert again["outcome"] == "already_recorded"
    assert again["decision_id"] == proposed["decision_id"]

    with app.state.session_factory() as session:
        decisions = session.scalars(select(ClubDelegatedDecision).where(ClubDelegatedDecision.club_id == club_id)).all()
        assert len(decisions) == 1
        decision = decisions[0]
        assert decision.activity_key == "financial_planning"
        assert decision.financial_amount_gtex is None
        assert decision.payload_json["match_id"] == match_id
        assert decision.payload_json["currency"] == ledger.FAN
        inbox = session.scalars(select(OwnerInboxItem).where(OwnerInboxItem.club_id == club_id)).all()
        assert [i.kind for i in inbox].count("delegated_decision_request") == 1
        audit_count = session.scalar(
            select(func.count())
            .select_from(ClubDelegatedDecisionAuditLog)
            .where(ClubDelegatedDecisionAuditLog.decision_id == decision.id)
        )
        assert audit_count == 1

    # Governance records a decision only; it must never move money.
    assert _club_balance(app, club_id) == balance_before


def test_match_without_gifts_creates_no_decision(tmp_path):
    app, _user_id, club_id, _hub = _build_test_app(tmp_path)
    client = TestClient(app)
    match_id = _add_match(app, completed=True)

    res = client.post(f"/owner/matches/{match_id}/full-time-governance")
    assert res.status_code == 200
    assert res.json()["results"] == []
    with app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ClubDelegatedDecision)) == 0


def test_non_owner_gets_empty_result_and_no_decision(tmp_path):
    app, _owner_id, club_id, _hub = _build_test_app(tmp_path)
    client = TestClient(app)
    match_id = _add_match(app, completed=True)
    _gift(client, club_id, match_id)

    with app.state.session_factory() as session:
        stranger = User(
            id=str(uuid.uuid4()),
            email="stranger@gtex.test",
            username="stranger",
            display_name="Stranger",
            full_name="Stranger",
            role=UserRole.USER,
            is_active=True,
            password_hash="pw_mock",  # pragma: allowlist secret
        )
        session.add(stranger)
        session.commit()
        stranger_id = stranger.id

    def as_stranger():
        with app.state.session_factory() as session:
            return session.get(User, stranger_id)

    app.dependency_overrides[get_current_user] = as_stranger
    res = client.post(f"/owner/matches/{match_id}/full-time-governance")
    assert res.status_code == 200
    assert res.json()["results"] == []
    with app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(ClubDelegatedDecision)) == 0


def test_post_match_bonus_auto_approved_within_threshold(tmp_path):
    app, user_id, club_id, _hub = _build_test_app(tmp_path)
    client = TestClient(app)
    match_id = _add_match(app, completed=True, home_club_id=club_id)

    # 5,000 GTX is <= 10,000 GTX balanced limit for operational_expenditure -> auto_approved
    res = client.post(
        f"/owner/matches/{match_id}/full-time-governance",
        json={"bonus_amount_gtex": 5000, "bonus_note": "Clean sheet win bonus"},
    )
    assert res.status_code == 200, res.text
    results = res.json()["results"]
    assert len(results) == 1
    item = results[0]
    assert item["club_id"] == club_id
    assert item["outcome"] == "proposed"
    assert item["decision_type"] == "post_match_bonus"
    assert item["decision_status"] == "auto_approved"
    assert item["requires_owner_approval"] is False

    # Second call returns already_recorded
    again = client.post(
        f"/owner/matches/{match_id}/full-time-governance",
        json={"bonus_amount_gtex": 5000},
    )
    assert again.status_code == 200
    assert again.json()["results"][0]["outcome"] == "already_recorded"
    assert again.json()["results"][0]["decision_id"] == item["decision_id"]


def test_post_match_bonus_escalated_above_threshold(tmp_path):
    app, user_id, club_id, _hub = _build_test_app(tmp_path)
    client = TestClient(app)
    match_id = _add_match(app, completed=True, home_club_id=club_id)

    # 25,000 GTX exceeds 10,000 GTX balanced limit -> pending_approval + owner inbox request
    res = client.post(
        f"/owner/matches/{match_id}/full-time-governance",
        json={"bonus_amount_gtex": 25000, "bonus_note": "Title win bonus"},
    )
    assert res.status_code == 200, res.text
    results = res.json()["results"]
    assert len(results) == 1
    item = results[0]
    assert item["outcome"] == "proposed"
    assert item["decision_type"] == "post_match_bonus"
    assert item["decision_status"] == "pending_approval"
    assert item["requires_owner_approval"] is True

    with app.state.session_factory() as session:
        inbox = session.scalars(select(OwnerInboxItem).where(OwnerInboxItem.club_id == club_id)).all()
        assert len(inbox) == 1
        assert inbox[0].category == "requests"


def test_metadata_bonus_and_gift_combination(tmp_path):
    app, user_id, club_id, _hub = _build_test_app(tmp_path)
    client = TestClient(app)
    match_id = _add_match(
        app,
        completed=True,
        home_club_id=club_id,
        metadata_json={"post_match_bonus_gtex": 7500},
    )
    _gift(client, club_id, match_id, "stadium_roar")

    res = client.post(f"/owner/matches/{match_id}/full-time-governance")
    assert res.status_code == 200, res.text
    results = res.json()["results"]
    assert len(results) == 2

    gift_res = next(r for r in results if r.get("gift_count") is not None)
    bonus_res = next(r for r in results if r.get("decision_type") == "post_match_bonus")

    assert gift_res["requires_owner_approval"] is True
    assert gift_res["decision_status"] == "pending_approval"
    assert bonus_res["requires_owner_approval"] is False
    assert bonus_res["decision_status"] == "auto_approved"
