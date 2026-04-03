from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.tests.support.secrets import TEST_PASSWORD
from app.auth.security import create_access_token
from app.ingestion.models import Player
from app.models.auth_session import AuthSession
from app.models.competition_entry import CompetitionEntry
from app.models.competition_match import CompetitionMatch
from app.models.player_token_market import PlayerShareHolding
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.models.user import User
from app.models.wallet import LedgerUnit, PaymentEvent
from app.models.treasury import PaymentMode
from app.policies.service import PolicyService
from app.treasury.service import TreasuryService
from app.wallets.service import LedgerError, WalletService


def _suffix(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _register_user(client, *, prefix: str) -> dict[str, object]:
    email = f"{_suffix(prefix)}@example.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": f"{prefix.title()} User",
            "phone_number": "08000000000",
            "password": TEST_PASSWORD,
            "is_over_18": True,
            "region_code": "NG",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    payload["email"] = email
    payload["password"] = TEST_PASSWORD
    payload["headers"] = _auth_headers(payload["access_token"])
    return payload


def _login_user(client, *, email: str, password: str) -> dict[str, object]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    payload = response.json()
    payload["email"] = email
    payload["password"] = password
    payload["headers"] = _auth_headers(payload["access_token"])
    return payload


def _enable_automatic_deposits(app_session_factory, *, user_id: str) -> None:
    with app_session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        policy_service = PolicyService(session)
        policy_service.seed_defaults()
        region_code = policy_service.resolve_country_code_for_user(user=user)
        profile = policy_service.ensure_user_region_profile(user=user, region_code=region_code)
        profile.region_code = region_code
        settings = TreasuryService().ensure_settings(session)
        settings.deposit_mode = PaymentMode.AUTOMATIC
        session.commit()


def _enable_gateway_deposit_controls(client, *, admin_headers: dict[str, str]) -> None:
    response = client.put(
        "/api/admin/god-mode/withdrawal-controls",
        headers=admin_headers,
        json={
            "egame_withdrawals_enabled": False,
            "trade_withdrawals_enabled": True,
            "processor_mode": "automatic_gateway",
            "deposits_via_bank_transfer": False,
            "payouts_via_bank_transfer": True,
            "reason": "Enable gateway deposit path for reliability tests.",
        },
    )
    assert response.status_code == 200, response.text


def _seed_wallet_balance(
    app_session_factory,
    *,
    user_id: str,
    amount: Decimal,
    unit: LedgerUnit,
) -> None:
    with app_session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        wallet_service = WalletService()
        wallet_service.credit_trade_proceeds(
            session,
            user=user,
            amount=amount,
            reference=f"seed:{unit.value}:{user_id}:{uuid4().hex[:6]}",
            description=f"Seeded {unit.value} balance for reliability testing",
            external_reference=f"seed:{unit.value}:{user_id}:{uuid4().hex[:6]}",
            unit=unit,
        )
        session.commit()


def _seed_real_player(app_session_factory, *, prefix: str) -> str:
    player_id = _suffix(prefix)
    with app_session_factory() as session:
        player = Player(
            id=player_id,
            source_provider="transfermarkt_2nd_zip",
            provider_external_id=f"transfermarkt:{player_id}",
            full_name="Victor Osimhen",
            canonical_display_name="Victor Osimhen",
            position="Striker",
            normalized_position="striker",
            date_of_birth=date(1998, 12, 29),
            preferred_foot="right",
            is_tradable=True,
            is_real_player=True,
            real_player_tier="featured",
            identity_confidence_score=0.99,
            source_last_refreshed_at=datetime(2026, 3, 29, 12, 0, tzinfo=timezone.utc),
            real_world_club_name="Galactic FC",
            real_world_league_name="Global Elite League",
            current_market_reference_value=120_000_000.0,
            market_reference_currency="EUR",
            normalization_profile_version="real_player_v1",
        )
        session.add(player)
        session.flush()

        source_link = RealPlayerSourceLink(
            id=f"source-link-{player_id}",
            gtex_player_id=player.id,
            source_name="transfermarkt_2nd_zip",
            source_player_key=f"transfermarkt:{player_id}",
            canonical_name=player.full_name,
            known_aliases_json=["Osimhen"],
            nationality="Nigeria",
            date_of_birth=player.date_of_birth,
            birth_year=1998,
            primary_position="Striker",
            current_real_world_club=player.real_world_club_name,
            identity_confidence_score=0.99,
            is_verified_real_player=True,
            verification_state="verified",
        )
        session.add(source_link)
        session.flush()

        session.add(
            RealPlayerProfile(
                id=f"profile-{player_id}",
                gtex_player_id=player.id,
                source_link_id=source_link.id,
                source_name="transfermarkt_2nd_zip",
                source_player_key=source_link.source_player_key,
                canonical_name=player.full_name,
                known_aliases_json=["Osimhen"],
                nationality="Nigeria",
                birth_year=1998,
                date_of_birth=player.date_of_birth,
                dominant_foot="right",
                primary_position="Striker",
                secondary_positions_json=["Forward"],
                current_club_name=player.real_world_club_name,
                current_league_name=player.real_world_league_name,
                competition_level="elite",
                appearances=31,
                minutes_played=2460,
                goals=24,
                assists=5,
                clean_sheets=0,
                injury_status="fit",
                current_market_reference_value=120_000_000.0,
                market_reference_currency="EUR",
                source_last_refreshed_at=player.source_last_refreshed_at,
                normalization_profile_version="real_player_v1",
                normalized_signals_json={"competition_level": "elite"},
                ingestion_batch_id="critical-system-reliability",
                ingestion_source_version="2026-03-29",
                pricing_snapshot_id=f"snapshot-{player_id}",
                metadata_json={"test": "critical_system_reliability"},
            )
        )
        session.commit()
    return player_id


def _issue_expired_access_token(
    app_session_factory,
    *,
    user_id: str,
    session_id: str,
) -> str:
    with app_session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        return create_access_token(
            user.id,
            expires_delta=timedelta(seconds=-5),
            claims={
                "email": user.email,
                "role": user.role.value,
                "sid": session_id,
            },
        )


def _issue_invalid_session_token(
    app_session_factory,
    *,
    user_id: str,
) -> str:
    with app_session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        return create_access_token(
            user.id,
            claims={
                "email": user.email,
                "role": user.role.value,
                "sid": _suffix("missing-session"),
            },
        )


def _create_coin_payment_event(
    client,
    app_session_factory,
    *,
    user_id: str,
    headers: dict[str, str],
    admin_headers: dict[str, str],
    amount: Decimal,
    provider_reference: str,
) -> PaymentEvent:
    _enable_automatic_deposits(app_session_factory, user_id=user_id)
    _enable_gateway_deposit_controls(client, admin_headers=admin_headers)
    response = client.post(
        "/api/wallets/payment-events",
        headers=headers,
        json={
            "provider": "monnify",
            "provider_reference": provider_reference,
            "amount": str(amount),
            "pack_code": "starter-50",
        },
    )
    assert response.status_code == 201, response.text

    with app_session_factory() as session:
        event = session.scalar(select(PaymentEvent).where(PaymentEvent.provider_reference == provider_reference))
        assert event is not None
        session.expunge(event)
        return event


def test_wallet_deposit_verification_increases_balance_and_rejects_double_verification(
    client,
    app_session_factory,
    bootstrap_admin_headers,
) -> None:
    registered = _register_user(client, prefix="wallet-verify")
    login = _login_user(client, email=registered["email"], password=registered["password"])
    provider_reference = _suffix("wallet-payment")

    _create_coin_payment_event(
        client,
        app_session_factory,
        user_id=login["user"]["id"],
        headers=login["headers"],
        admin_headers=bootstrap_admin_headers,
        amount=Decimal("50.0000"),
        provider_reference=provider_reference,
    )

    with app_session_factory() as session:
        user = session.get(User, login["user"]["id"])
        payment_event = session.scalar(
            select(PaymentEvent).where(PaymentEvent.provider_reference == provider_reference)
        )
        assert user is not None
        assert payment_event is not None

        WalletService().verify_payment_event(session, payment_event, actor=user)
        session.commit()
        session.refresh(payment_event)
        assert payment_event.status.value == "verified"

        with pytest.raises(LedgerError, match="Only pending payment events can be verified"):
            WalletService().verify_payment_event(session, payment_event, actor=user)
        session.rollback()

    summary_response = client.get(
        "/api/wallets/summary",
        headers=login["headers"],
        params={"currency": "coin"},
    )
    assert summary_response.status_code == 200, summary_response.text
    summary = summary_response.json()
    assert Decimal(summary["available_balance"]) == Decimal("50.0000")
    assert Decimal(summary["total_balance"]) == Decimal("50.0000")


def test_wallet_conversion_cannot_create_negative_balance(client, app_session_factory) -> None:
    registered = _register_user(client, prefix="wallet-negative")
    login = _login_user(client, email=registered["email"], password=registered["password"])

    convert_response = client.post(
        "/api/wallets/conversions",
        headers=login["headers"],
        json={
            "amount": "1.0000",
            "source_unit": "coin",
            "idempotency_key": _suffix("wallet-negative"),
        },
    )
    assert convert_response.status_code == 409
    assert "does not have enough balance" in convert_response.json()["detail"]

    summary_response = client.get(
        "/api/wallets/summary",
        headers=login["headers"],
        params={"currency": "coin"},
    )
    assert summary_response.status_code == 200, summary_response.text
    summary = summary_response.json()
    assert Decimal(summary["available_balance"]) == Decimal("0.0000")
    assert Decimal(summary["total_balance"]) == Decimal("0.0000")

    with app_session_factory() as session:
        user = session.get(User, login["user"]["id"])
        assert user is not None
        balance = WalletService().get_balance(
            session,
            WalletService().get_user_account(session, user, LedgerUnit.COIN),
        )
        assert balance == Decimal("0.0000")


def test_auth_expired_token_refresh_works_and_invalid_token_is_rejected(
    client,
    app_session_factory,
) -> None:
    registered = _register_user(client, prefix="auth-critical")
    login = _login_user(client, email=registered["email"], password=registered["password"])
    expired_access_token = _issue_expired_access_token(
        app_session_factory,
        user_id=login["user"]["id"],
        session_id=login["session_id"],
    )

    expired_response = client.get(
        "/api/auth/me",
        headers=_auth_headers(expired_access_token),
    )
    assert expired_response.status_code == 401
    assert "expired" in expired_response.json()["detail"].lower()

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
        headers={"X-Device-Id": "critical-system-device"},
    )
    assert refresh_response.status_code == 200, refresh_response.text
    refreshed = refresh_response.json()
    assert refreshed["access_token"] != login["access_token"]
    assert refreshed["refresh_token"] != login["refresh_token"]

    me_response = client.get(
        "/api/auth/me",
        headers=_auth_headers(refreshed["access_token"]),
    )
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["id"] == login["user"]["id"]

    invalid_session_token = _issue_invalid_session_token(
        app_session_factory,
        user_id=login["user"]["id"],
    )
    invalid_response = client.get(
        "/api/auth/me",
        headers=_auth_headers(invalid_session_token),
    )
    assert invalid_response.status_code == 401
    assert (
        "invalid" in invalid_response.json()["detail"].lower() or "session" in invalid_response.json()["detail"].lower()
    )


def test_market_buy_sell_flow_updates_holdings_wallet_and_price(
    client,
    app_session_factory,
    bootstrap_admin_headers,
) -> None:
    registered = _register_user(client, prefix="market-critical")
    login = _login_user(client, email=registered["email"], password=registered["password"])
    user_id = login["user"]["id"]
    player_id = _seed_real_player(app_session_factory, prefix="market-player")
    _seed_wallet_balance(
        app_session_factory,
        user_id=user_id,
        amount=Decimal("10.0000"),
        unit=LedgerUnit.COIN,
    )

    issue_response = client.post(
        f"/players/{player_id}/shares/market",
        headers=bootstrap_admin_headers,
        json={
            "total_shares": 1000,
            "share_price_coin": "0.5000",
            "liquidity_coin": "20.0000",
            "status": "active",
        },
    )
    assert issue_response.status_code == 200, issue_response.text

    before_summary = client.get(
        "/api/wallets/summary",
        headers=login["headers"],
        params={"currency": "coin"},
    ).json()

    buy_response = client.post(
        f"/players/{player_id}/shares/buy",
        headers=login["headers"],
        json={"share_count": 10},
    )
    assert buy_response.status_code == 201, buy_response.text
    buy_payload = buy_response.json()

    after_buy_summary = client.get(
        "/api/wallets/summary",
        headers=login["headers"],
        params={"currency": "coin"},
    ).json()

    sell_response = client.post(
        f"/players/{player_id}/shares/sell",
        headers=login["headers"],
        json={"share_count": 4},
    )
    assert sell_response.status_code == 201, sell_response.text
    sell_payload = sell_response.json()

    after_sell_summary = client.get(
        "/api/wallets/summary",
        headers=login["headers"],
        params={"currency": "coin"},
    ).json()

    assert buy_payload["holding"]["share_count"] == 10
    assert sell_payload["holding"]["share_count"] == 6
    assert Decimal(after_buy_summary["available_balance"]) < Decimal(before_summary["available_balance"])
    assert Decimal(after_sell_summary["available_balance"]) > Decimal(after_buy_summary["available_balance"])
    assert Decimal(buy_payload["market"]["share_price_coin"]) != Decimal("0.5000")
    assert Decimal(sell_payload["market"]["share_price_coin"]) != Decimal(buy_payload["market"]["share_price_coin"])

    with app_session_factory() as session:
        holding = session.scalar(
            select(PlayerShareHolding).where(
                PlayerShareHolding.user_id == user_id,
                PlayerShareHolding.player_id == player_id,
            )
        )
        assert holding is not None
        assert holding.share_count == 6


def test_competition_join_records_entry_and_match_simulation_saves_result(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="competition-host")
    challenger = auth_user_factory(suffix="competition-challenger")

    create_response = client.post(
        "/api/competitions/create",
        json={
            "name": "Critical Reliability League",
            "format": "league",
            "type": "user_hosted",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "coin",
            "capacity": 2,
            "max_players": 2,
            "creator_id": host["user_id"],
            "creator_name": "Host Club",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "rules": "Auto-run a two-club reliability fixture.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    competition_id = create_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200, publish_response.text

    host_join = client.post(
        "/api/competitions/join",
        headers=host["headers"],
        json={
            "competition_id": competition_id,
            "user_id": host["user_id"],
            "user_name": "Host Club",
        },
    )
    assert host_join.status_code == 200, host_join.text

    challenger_join = client.post(
        "/api/competitions/join",
        headers=challenger["headers"],
        json={
            "competition_id": competition_id,
            "user_id": challenger["user_id"],
            "user_name": "Challenger Club",
        },
    )
    assert challenger_join.status_code == 200, challenger_join.text
    assert challenger_join.json()["status"] == "settled"

    fixtures_response = client.get(f"/api/competitions/{competition_id}/fixtures")
    assert fixtures_response.status_code == 200, fixtures_response.text
    fixtures = fixtures_response.json()
    assert len(fixtures) == 1

    events_response = client.get(f"/api/competitions/{competition_id}/matches/{fixtures[0]['id']}/events")
    assert events_response.status_code == 200, events_response.text
    assert len(events_response.json()) > 0

    with app_session_factory() as session:
        entries = session.scalars(
            select(CompetitionEntry).where(CompetitionEntry.competition_id == competition_id)
        ).all()
        match = session.scalar(
            select(CompetitionMatch).where(
                CompetitionMatch.competition_id == competition_id,
                CompetitionMatch.id == fixtures[0]["id"],
            )
        )
        assert len(entries) == 2
        assert any(entry.user_id == challenger["user_id"] for entry in entries)
        assert match is not None
        assert match.status == "completed"
        assert match.home_score is not None
        assert match.away_score is not None
        if match.home_score != match.away_score:
            assert match.winner_club_id is not None


def test_end_to_end_register_login_fund_wallet_buy_player_and_join_competition(
    client,
    app_session_factory,
    bootstrap_admin_headers,
    competition_admin_headers,
) -> None:
    player_id = _seed_real_player(app_session_factory, prefix="e2e-player")

    issue_response = client.post(
        f"/players/{player_id}/shares/market",
        headers=bootstrap_admin_headers,
        json={
            "total_shares": 1000,
            "share_price_coin": "0.5000",
            "liquidity_coin": "20.0000",
            "status": "active",
        },
    )
    assert issue_response.status_code == 200, issue_response.text

    create_competition_response = client.post(
        "/api/competitions",
        json={
            "name": "Critical E2E Cup",
            "format": "league",
            "visibility": "public",
            "entry_fee": "1.00",
            "currency": "coin",
            "capacity": 2,
            "creator_id": "system-host",
            "creator_name": "System Host",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
        },
    )
    assert create_competition_response.status_code == 201, create_competition_response.text
    competition_id = create_competition_response.json()["id"]

    publish_response = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200, publish_response.text

    registered = _register_user(client, prefix="critical-e2e")
    login = _login_user(client, email=registered["email"], password=registered["password"])

    initiate_top_up = client.post(
        "/wallet/top-up/initiate",
        headers=login["headers"],
        json={"amount": "500000.0000"},
    )
    assert initiate_top_up.status_code == 201, initiate_top_up.text
    top_up_reference = initiate_top_up.json()["reference"]

    verify_top_up = client.post(
        "/wallet/top-up/verify",
        headers=login["headers"],
        json={"reference": top_up_reference},
    )
    assert verify_top_up.status_code == 200, verify_top_up.text
    verified_credit_balance = Decimal(verify_top_up.json()["wallet"]["balance"])
    assert verified_credit_balance > Decimal("300.0000")

    credit_summary = client.get(
        "/api/wallets/summary",
        headers=login["headers"],
        params={"currency": "credit"},
    )
    assert credit_summary.status_code == 200, credit_summary.text
    assert Decimal(credit_summary.json()["available_balance"]) == verified_credit_balance

    convert_response = client.post(
        "/api/wallets/conversions",
        headers=login["headers"],
        json={
            "amount": "300.0000",
            "source_unit": "credit",
            "idempotency_key": _suffix("credit-to-coin"),
        },
    )
    assert convert_response.status_code == 201, convert_response.text
    assert Decimal(convert_response.json()["target_amount"]) == Decimal("3.0000")

    buy_response = client.post(
        f"/players/{player_id}/shares/buy",
        headers=login["headers"],
        json={"share_count": 2},
    )
    assert buy_response.status_code == 201, buy_response.text
    assert buy_response.json()["holding"]["share_count"] == 2

    join_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=login["headers"],
        json={
            "user_id": login["user"]["id"],
            "user_name": login["user"]["display_name"],
        },
    )
    assert join_response.status_code == 200, join_response.text
    joined = join_response.json()
    assert joined["participant_count"] == 1

    coin_summary = client.get(
        "/api/wallets/summary",
        headers=login["headers"],
        params={"currency": "coin"},
    )
    assert coin_summary.status_code == 200, coin_summary.text
    assert Decimal(coin_summary.json()["available_balance"]) == Decimal("1.0000")

    holdings_response = client.get("/players/me/shares/holdings", headers=login["headers"])
    assert holdings_response.status_code == 200, holdings_response.text
    holdings = holdings_response.json()
    assert any(item["player_id"] == player_id and item["share_count"] == 2 for item in holdings)

    with app_session_factory() as session:
        auth_session = session.get(AuthSession, login["session_id"])
        entry = session.scalar(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == competition_id,
                CompetitionEntry.user_id == login["user"]["id"],
            )
        )
        assert auth_session is not None
        assert entry is not None
