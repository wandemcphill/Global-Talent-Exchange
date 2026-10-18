from __future__ import annotations

from datetime import timedelta


def test_fast_cup_api_surfaces_upcoming_join_bracket_countdown_and_summary(api_client, base_now) -> None:
    upcoming_response = api_client.get(
        "/fast-cups/upcoming",
        params={"now": base_now.isoformat(), "horizon_intervals": 1},
    )
    assert upcoming_response.status_code == 200

    cups = upcoming_response.json()["cups"]
    assert len(cups) == 8

    senior_32 = next(cup for cup in cups if cup["division"] == "senior" and cup["size"] == 32)

    for index in range(1, 33):
        response = api_client.post(
            f"/fast-cups/{senior_32['cup_id']}/join",
            json={"club_id": f"senior-club-{index:03d}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["escrow_status"] == "escrowed"
        assert body["entry_fee_currency"] == "credit"

    bracket_response = api_client.get(f"/fast-cups/{senior_32['cup_id']}/bracket")
    assert bracket_response.status_code == 200
    bracket_payload = bracket_response.json()
    assert bracket_payload["total_rounds"] == 5
    first_home = bracket_payload["rounds"][0]["matches"][0]["home"]["club_id"]
    first_away = bracket_payload["rounds"][0]["matches"][0]["away"]["club_id"]
    assert first_home.startswith("senior-club-")
    assert first_away.startswith("senior-club-")

    countdown_response = api_client.get(
        f"/fast-cups/{senior_32['cup_id']}/countdown",
        params={"now": base_now.isoformat()},
    )
    assert countdown_response.status_code == 200
    countdown_payload = countdown_response.json()
    assert countdown_payload["status"] == "ready"
    assert countdown_payload["slots_remaining"] == 0

    early_summary_response = api_client.get(
        f"/fast-cups/{senior_32['cup_id']}/result-summary",
        params={"now": base_now.isoformat()},
    )
    assert early_summary_response.status_code == 409

    kickoff_plus_duration = base_now + timedelta(minutes=30)
    summary_response = api_client.get(
        f"/fast-cups/{senior_32['cup_id']}/result-summary",
        params={"now": kickoff_plus_duration.isoformat()},
    )
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["champion"]["club_id"].startswith("senior-club-")
    assert summary_payload["expected_duration_minutes"] == 30
    assert len(summary_payload["events"]) == 6
    assert summary_payload["penalty_shootouts"] >= 1

    from sqlalchemy import func, select
    from app.auth.dependencies import get_current_user
    from app.core.database import get_session
    from app.models.fast_cup_finance import FastCupPayout
    from app.models.user import User, UserRole
    from app.models.wallet import LedgerTransaction
    from fastapi import HTTPException, status

    # Read-only result-summary GET must never create payout rows or payout ledger entries.
    session = list(api_client.app.dependency_overrides[get_session]())[0]
    payout_count_before = session.scalar(
        select(func.count()).select_from(FastCupPayout).where(FastCupPayout.cup_id == senior_32["cup_id"])
    )
    ledger_count_before = session.scalar(
        select(func.count()).select_from(LedgerTransaction).where(
            LedgerTransaction.idempotency_key.like(f"fast-cup-payout:{senior_32['cup_id']}:%")
        )
    )
    assert payout_count_before == 0
    assert ledger_count_before == 0

    # Unauthenticated POST /settle (overriding user dependency to raise 401 or no auth)

    def unauth_user():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    api_client.app.dependency_overrides[get_current_user] = unauth_user
    unauth_settle = api_client.post(
        f"/fast-cups/{senior_32['cup_id']}/settle",
        params={"now": kickoff_plus_duration.isoformat()},
    )
    assert unauth_settle.status_code == 401

    # Non-admin user POST /settle (returning regular user)
    # Restore original override where current_user has UserRole.USER
    actor = session.get(User, "fast-cup-owner")

    api_client.app.dependency_overrides[get_current_user] = lambda: actor
    forbidden_settle = api_client.post(
        f"/fast-cups/{senior_32['cup_id']}/settle",
        params={"now": kickoff_plus_duration.isoformat()},
    )
    assert forbidden_settle.status_code == 403

    # Admin user POST /settle
    actor.role = UserRole.ADMIN
    session.commit()

    admin_settle = api_client.post(
        f"/fast-cups/{senior_32['cup_id']}/settle",
        params={"now": kickoff_plus_duration.isoformat()},
    )
    assert admin_settle.status_code == 200
    settle_payload = admin_settle.json()
    assert settle_payload["champion"]["club_id"] == summary_payload["champion"]["club_id"]

    session.expire_all()
    payout_count_after_settle = session.scalar(
        select(func.count()).select_from(FastCupPayout).where(FastCupPayout.cup_id == senior_32["cup_id"])
    )
    ledger_count_after_settle = session.scalar(
        select(func.count()).select_from(LedgerTransaction).where(
            LedgerTransaction.idempotency_key.like(f"fast-cup-payout:{senior_32['cup_id']}:%")
        )
    )
    assert payout_count_after_settle > 0
    assert ledger_count_after_settle > 0

    # A follow-up GET remains read-only after payout settlement.
    after_settlement_read = api_client.get(
        f"/fast-cups/{senior_32['cup_id']}/result-summary",
        params={"now": kickoff_plus_duration.isoformat()},
    )
    assert after_settlement_read.status_code == 200
    session.expire_all()
    assert (
        session.scalar(
            select(func.count()).select_from(FastCupPayout).where(FastCupPayout.cup_id == senior_32["cup_id"])
        )
        == payout_count_after_settle
    )
    assert (
        session.scalar(
            select(func.count()).select_from(LedgerTransaction).where(
                LedgerTransaction.idempotency_key.like(f"fast-cup-payout:{senior_32['cup_id']}:%")
            )
        )
        == ledger_count_after_settle
    )

    # Repeating the authorized mutation is idempotent: no duplicate payout or ledger credit.
    repeated_settle = api_client.post(
        f"/fast-cups/{senior_32['cup_id']}/settle",
        params={"now": kickoff_plus_duration.isoformat()},
    )
    assert repeated_settle.status_code == 200
    session.expire_all()
    assert (
        session.scalar(
            select(func.count()).select_from(FastCupPayout).where(FastCupPayout.cup_id == senior_32["cup_id"])
        )
        == payout_count_after_settle
    )
    assert (
        session.scalar(
            select(func.count()).select_from(LedgerTransaction).where(
                LedgerTransaction.idempotency_key.like(f"fast-cup-payout:{senior_32['cup_id']}:%")
            )
        )
        == ledger_count_after_settle
    )
