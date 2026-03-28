from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.competition_participant import CompetitionParticipant
from app.models.competition_reward import CompetitionReward
from app.models.manager_market import ManagerTradeRecord


def test_gtex_financial_summary_exposes_dynamic_jackpot_pool(client, app_session_factory) -> None:
    with app_session_factory() as session:
        for participant in session.query(CompetitionParticipant).all():
            participant.joined_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        session.commit()

    created = client.post(
        "/api/competitions",
        json={
            "name": "GTEX Jackpot Cup",
            "format": "cup",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 8,
            "creator_id": "gtex-host-1",
            "creator_name": "GTEX",
            "source_type": "gtex_hosted",
            "payout_structure": [
                {"place": 1, "percent": "1.00"},
            ],
        },
    ).json()
    competition_id = created["id"]
    client.post(f"/api/competitions/{competition_id}/publish", json={"open_for_join": True})
    client.post(f"/api/competitions/{competition_id}/join", json={"user_id": "club-jackpot-1"})
    client.post(f"/api/competitions/{competition_id}/join", json={"user_id": "club-jackpot-2"})

    rollover = client.post(
        "/api/competitions",
        json={
            "name": "GTEX Rollover Cup",
            "format": "cup",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 8,
            "creator_id": "gtex-host-2",
            "creator_name": "GTEX",
            "source_type": "gtex_hosted",
            "payout_structure": [
                {"place": 1, "percent": "1.00"},
            ],
        },
    ).json()

    with app_session_factory() as session:
        session.add(
            ManagerTradeRecord(
                trade_id="jackpot-trade-1",
                mode="spot",
                listing_id=None,
                proposer_asset_id=None,
                requested_asset_id=None,
                gross_credits="200.0000",
                fee_credits="10.0000",
                seller_net_credits="190.0000",
                settlement_reference="jackpot-trade-ref-1",
                settlement_status="settled",
                immediate_withdrawal_eligible=True,
            )
        )
        session.add(
            CompetitionReward(
                competition_id=rollover["id"],
                reward_pool_id=None,
                participant_id=None,
                club_id=None,
                placement=None,
                reward_type="prize",
                currency="coin",
                amount_minor=85_000,
                status="pending",
                ledger_transaction_id=None,
                settled_at=None,
                metadata_json={"reason": "unclaimed_rollover"},
            )
        )
        session.commit()

    financials_response = client.get(f"/api/competitions/{competition_id}/financials")
    assert financials_response.status_code == 200
    financials = financials_response.json()
    assert financials["prize_pool"] == "33.8000"
    assert financials["dynamic_prize_pool"] == {
        "enabled": True,
        "base_funding": "25.0000",
        "activity_boost": "0.3000",
        "jackpot_rollover": "8.5000",
        "total_pool": "33.8000",
        "active_users_5min": 2,
        "trade_volume_5min": "200.0000",
    }

    detail_response = client.get(f"/api/competitions/{competition_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["dynamic_prize_pool"]["total_pool"] == "33.8000"


def test_financial_summary_exposes_transparent_pool_breakdown(client) -> None:
    created = client.post(
        "/api/competitions",
        json={
            "name": "Transparent League",
            "format": "league",
            "visibility": "public",
            "entry_fee": "20.00",
            "currency": "credit",
            "capacity": 10,
            "creator_id": "host-5",
            "platform_fee_pct": "0.10",
            "host_fee_pct": "0.05",
            "payout_structure": [
                {"place": 1, "percent": "0.50"},
                {"place": 2, "percent": "0.30"},
                {"place": 3, "percent": "0.20"},
            ],
        },
    ).json()
    competition_id = created["id"]
    client.post(f"/api/competitions/{competition_id}/publish", json={"open_for_join": True})
    client.post(f"/api/competitions/{competition_id}/join", json={"user_id": "club-1"})
    client.post(f"/api/competitions/{competition_id}/join", json={"user_id": "club-2"})

    financials_response = client.get(f"/api/competitions/{competition_id}/financials")
    assert financials_response.status_code == 200
    financials = financials_response.json()
    assert financials == {
        "competition_id": competition_id,
        "participant_count": 2,
        "entry_fee": "20.00",
        "gross_pool": "40.0000",
        "platform_fee_pct": "0.10",
        "platform_fee_amount": "4.0000",
        "host_fee_pct": "0.05",
        "host_fee_amount": "2.0000",
        "prize_pool": "34.0000",
        "payout_structure": [
            {"place": 1, "percent": "0.50", "amount": "17.0000"},
            {"place": 2, "percent": "0.30", "amount": "10.2000"},
            {"place": 3, "percent": "0.20", "amount": "6.8000"},
        ],
        "currency": "credit",
    }


def test_summary_and_detail_keep_financial_fields_visible(client) -> None:
    created = client.post(
        "/api/competitions",
        json={
            "name": "Free Discovery Cup",
            "format": "cup",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "credit",
            "capacity": 8,
            "creator_id": "host-7",
        },
    ).json()
    competition_id = created["id"]
    detail_response = client.get(f"/api/competitions/{competition_id}")
    summary_response = client.get(f"/api/competitions/{competition_id}/summary")

    assert detail_response.status_code == 200
    assert summary_response.status_code == 200
    required_fields = {
        "name",
        "creator_id",
        "format",
        "visibility",
        "participant_count",
        "entry_fee",
        "platform_fee_pct",
        "host_fee_pct",
        "prize_pool",
        "payout_structure",
        "status",
        "join_eligibility",
        "rules_summary",
    }
    for payload in (detail_response.json(), summary_response.json()):
        assert required_fields.issubset(payload.keys())
