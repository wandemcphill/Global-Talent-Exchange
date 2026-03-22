from __future__ import annotations


def test_creator_profile_endpoints_create_patch_and_read_by_handle(referral_api) -> None:
    app, client, users, _session = referral_api
    app.state.current_user = users["creator"]

    create_response = client.post(
        "/api/creators/profile",
        json={
            "handle": "creator.one",
            "display_name": "Creator One",
            "tier": "featured",
            "status": "active",
            "default_competition_id": "comp-creator-1",
            "revenue_share_percent": "12.5",
        },
    )
    assert create_response.status_code == 201
    create_payload = create_response.json()
    assert create_payload["handle"] == "creator.one"
    assert create_payload["default_share_code"] == "creatorone"

    me_response = client.get("/api/creators/profile/me")
    assert me_response.status_code == 200
    assert me_response.json()["default_competition_id"] == "comp-creator-1"

    patch_response = client.patch(
        "/api/creators/profile",
        json={
            "display_name": "Creator One Updated",
            "default_competition_id": "comp-creator-2",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["display_name"] == "Creator One Updated"

    public_response = client.get("/api/creators/creator.one")
    assert public_response.status_code == 200
    assert public_response.json()["user_id"] == users["creator"].id

    competitions_response = client.get("/api/creators/me/competitions")
    assert competitions_response.status_code == 200
    competitions_payload = competitions_response.json()
    assert competitions_payload[0]["competition_id"] == "comp-creator-2"

    summary_response = client.get("/api/creators/me/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["profile"]["default_share_code"] == "creatorone"
    assert summary_payload["featured_competitions"][0]["competition_id"] == "comp-creator-2"


def test_creator_finance_endpoint_summarizes_rewards_and_withdrawals(referral_api) -> None:
    app, client, users, session = referral_api
    app.state.current_user = users["creator"]

    client.post(
        "/api/creators/profile",
        json={
            "handle": "creator.cash",
            "display_name": "Creator Cash",
            "tier": "featured",
            "status": "active",
            "default_competition_id": "comp-cash-1",
            "revenue_share_percent": "10.0",
        },
    )

    from app.models.reward_settlement import RewardSettlement, RewardSettlementStatus
    from app.models.gift_transaction import GiftTransaction, GiftTransactionStatus
    from app.models.wallet import LedgerUnit, PayoutRequest, PayoutStatus
    from app.models.treasury import TreasuryWithdrawalRequest, TreasuryWithdrawalStatus, RateDirection

    payout = PayoutRequest(
        user_id=users["creator"].id,
        account_id="acct-1",
        amount=20,
        unit=LedgerUnit.CREDIT,
        status=PayoutStatus.COMPLETED,
        destination_reference="bank:test",
        notes='{"requested_net_amount":"20.0000","fee_amount":"5.0000","total_debit":"25.0000"}',
    )
    session.add(payout)
    session.flush()
    session.add(
        GiftTransaction(
            sender_user_id=users["owner"].id,
            recipient_user_id=users["creator"].id,
            gift_catalog_item_id="gift-1",
            quantity=1,
            unit_price=10,
            gross_amount=10,
            platform_rake_amount=2,
            recipient_net_amount=8,
            ledger_unit=LedgerUnit.CREDIT,
            status=GiftTransactionStatus.SETTLED,
        )
    )
    session.add(
        RewardSettlement(
            user_id=users["creator"].id,
            competition_key="comp-cash-1",
            title="Weekly creator reward",
            gross_amount=15,
            platform_fee_amount=1,
            net_amount=14,
            ledger_unit=LedgerUnit.CREDIT,
            status=RewardSettlementStatus.SETTLED,
        )
    )
    session.add(
        TreasuryWithdrawalRequest(
            payout_request_id=payout.id,
            user_id=users["creator"].id,
            reference="WDL-TEST-1",
            status=TreasuryWithdrawalStatus.PAID,
            unit=LedgerUnit.CREDIT,
            amount_coin=20,
            amount_fiat=20000,
            currency_code="NGN",
            rate_value=1000,
            rate_direction=RateDirection.FIAT_PER_COIN,
            bank_name="GT Bank",
            bank_account_number="0123456789",
            bank_account_name="Creator Cash",
            kyc_status_snapshot="fully_verified",
            kyc_tier_snapshot="fully_verified",
        )
    )
    session.commit()

    response = client.get("/api/creators/me/finance")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["active_competitions"] >= 1
    assert payload["total_gift_income"] == "8.0000"
    assert payload["total_reward_income"] == "14.0000"
    assert payload["total_withdrawn_gross"] == "20.0000"
    assert payload["total_withdrawal_fees"] == "5.0000"
