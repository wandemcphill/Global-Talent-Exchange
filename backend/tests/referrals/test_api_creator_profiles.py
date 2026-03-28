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


def test_creator_insights_endpoint_returns_profile_patterns_and_recommendations(referral_api) -> None:
    app, client, users, session = referral_api
    app.state.current_user = users["creator"]

    create_response = client.post(
        "/api/creators/profile",
        json={
            "handle": "creator.insights",
            "display_name": "Creator Insights",
            "tier": "featured",
            "status": "active",
            "default_competition_id": "comp-insights-1",
            "revenue_share_percent": "15.0",
        },
    )
    assert create_response.status_code == 201
    creator_id = create_response.json()["creator_id"]

    from app.media_engine.schemas import CreatorClipRevenueAttributionRequest
    from app.models.highlight_share import HighlightShareExport
    from app.models.user import User, UserRole
    from app.services.creator_clip_monetization_service import CreatorClipMonetizationService

    session.add(
        User(
            id=users["creator"].id,
            email=users["creator"].email,
            username=users["creator"].username,
            password_hash="hashed",
            role=UserRole.USER,
            display_name=users["creator"].display_name,
        )
    )
    session.flush()

    exports = [
        HighlightShareExport(
            id="insights-export-1",
            user_id=users["creator"].id,
            match_key="creator-insights-match-1",
            source_storage_key="media/highlights/temp/creator-insights-match-1.mp4",
            export_storage_key="media/exports/creator-insights-match-1.zip",
            status="generated",
            aspect_ratio="9:16",
            watermark_label="GTEX",
            share_title="Debate insights 1",
            metadata_json={},
        ),
        HighlightShareExport(
            id="insights-export-2",
            user_id=users["creator"].id,
            match_key="creator-insights-match-2",
            source_storage_key="media/highlights/temp/creator-insights-match-2.mp4",
            export_storage_key="media/exports/creator-insights-match-2.zip",
            status="generated",
            aspect_ratio="9:16",
            watermark_label="GTEX",
            share_title="Debate insights 2",
            metadata_json={},
        ),
        HighlightShareExport(
            id="insights-export-3",
            user_id=users["creator"].id,
            match_key="creator-insights-match-3",
            source_storage_key="media/highlights/temp/creator-insights-match-3.mp4",
            export_storage_key="media/exports/creator-insights-match-3.zip",
            status="generated",
            aspect_ratio="9:16",
            watermark_label="GTEX",
            share_title="Meme insights 1",
            metadata_json={},
        ),
    ]
    session.add_all(exports)
    session.flush()

    monetization = CreatorClipMonetizationService(session)
    monetization.attribute_revenue(
        export_id="insights-export-1",
        payload=CreatorClipRevenueAttributionRequest(
            views=165000,
            source_reference="creator-insights-source-1",
            force_viral_bonus=True,
            metadata_json={
                "format": "debate",
                "duration_seconds": 18,
                "completion_rate": 0.9,
                "share_rate": 0.065,
                "loop_rate": 0.24,
                "hook_style": "fast-start",
                "audience_cluster": "debate-core",
            },
        ),
    )
    monetization.attribute_revenue(
        export_id="insights-export-2",
        payload=CreatorClipRevenueAttributionRequest(
            views=132000,
            source_reference="creator-insights-source-2",
            force_viral_bonus=True,
            metadata_json={
                "format": "debate",
                "duration_seconds": 19,
                "completion_rate": 0.85,
                "share_rate": 0.05,
                "loop_rate": 0.19,
                "hook_style": "fast-start",
                "audience_cluster": "debate-core",
            },
        ),
    )
    monetization.attribute_revenue(
        export_id="insights-export-3",
        payload=CreatorClipRevenueAttributionRequest(
            views=41000,
            source_reference="creator-insights-source-3",
            force_viral_bonus=False,
            metadata_json={
                "format": "meme",
                "duration_seconds": 31,
                "completion_rate": 0.56,
                "share_rate": 0.012,
                "loop_rate": 0.07,
                "hook_style": "slow-build",
                "audience_cluster": "casual-fans",
            },
        ),
    )
    session.commit()

    response = client.get("/api/creators/me/insights")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["profile_key"] == f"creator:{creator_id}:profile"
    assert payload["creator_metrics"]["best_format"] == "debate"
    assert payload["creator_metrics"]["optimal_duration"] == "15-20s"
    assert payload["analyzer"]["strongest_format"] == "debate"
    assert any("Videos 15-20s perform best" == item for item in payload["analyzer"]["patterns"])
    assert payload["recommendations"]["best_format"] == "debate"
    assert payload["recommendations"]["optimal_length"] == "18s"
    assert payload["recommendations"]["hook_style"] == "fast-start"
    assert payload["recommendations"]["posting_strategy"] == "high frequency"
    assert payload["viral_feedback_loop"]["clips_analyzed"] == 3

    alias_response = client.get("/creators/me/insights")
    assert alias_response.status_code == 200, alias_response.text
    assert alias_response.json()["profile_key"] == f"creator:{creator_id}:profile"


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

    from app.media_engine.schemas import CreatorClipRevenueAttributionRequest
    from app.models.highlight_share import HighlightShareExport
    from app.models.reward_settlement import RewardSettlement, RewardSettlementStatus
    from app.models.gift_transaction import GiftTransaction, GiftTransactionStatus
    from app.models.user import User, UserRole
    from app.models.wallet import LedgerUnit, PayoutRequest, PayoutStatus
    from app.models.treasury import TreasuryWithdrawalRequest, TreasuryWithdrawalStatus, RateDirection
    from app.services.creator_clip_monetization_service import CreatorClipMonetizationService

    session.add(
        User(
            id=users["creator"].id,
            email=users["creator"].email,
            username=users["creator"].username,
            password_hash="hashed",
            role=UserRole.USER,
            display_name=users["creator"].display_name,
        )
    )
    session.flush()

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
    export = HighlightShareExport(
        user_id=users["creator"].id,
        match_key="creator-finance-match-1",
        source_storage_key="media/highlights/temp/creator-finance-match-1.mp4",
        export_storage_key="media/exports/creator-finance-match-1.zip",
        status="generated",
        aspect_ratio="9:16",
        watermark_label="GTEX",
        share_title="Creator finance highlight",
        metadata_json={},
    )
    session.add(export)
    session.flush()
    CreatorClipMonetizationService(session).attribute_revenue(
        export_id=export.id,
        payload=CreatorClipRevenueAttributionRequest(
            views=150000,
            source_reference="finance-test-clip-1",
        ),
    )
    session.commit()

    response = client.get("/api/creators/me/finance")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["active_competitions"] >= 1
    assert payload["total_gift_income"] == "8.0000"
    assert payload["total_reward_income"] == "14.0000"
    assert payload["total_clip_income"] == "165.0000"
    assert payload["total_clip_views"] == 150000
    assert payload["viral_clip_count"] == 1
    assert payload["total_viral_bonus"] == "15.0000"
    assert payload["wallet_balance"] == "165.0000"
    assert payload["total_withdrawn_gross"] == "20.0000"
    assert payload["total_withdrawal_fees"] == "5.0000"
