from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select

from app.core.module import DomainModule
from app.models.club_profile import ClubProfile
from app.models.competition_escrow import CompetitionEscrow
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_reward import CompetitionReward
from app.models.competition_wallet_ledger import CompetitionWalletLedger
from app.models.manager_market import ManagerTradeRecord
from app.models.user import KycStatus, User, UserRole


@pytest.fixture(scope="module")
def test_settings(tmp_path_factory: pytest.TempPathFactory):
    from app.core.config import load_settings, reset_settings_cache

    database_path = tmp_path_factory.mktemp("gte-financial-summary-app") / "gte_app.db"
    media_root = tmp_path_factory.mktemp("gte-financial-summary-media")
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    managed_env = {
        "DATABASE_URL": database_url,
        "GTE_DATABASE_URL": database_url,
        "GTE_MEDIA_STORAGE_ROOT": str(media_root),
        "GTE_INGESTION_PROVIDER": "mock",
        "GTE_REAL_PLAYER_IMPORT_PROVIDER": "mock",
        "GTE_RUN_STARTUP_SEEDING": "0",
        "GTE_TASK_QUEUE_ENABLED": "0",
    }
    previous_env = {key: os.environ.get(key) for key in managed_env}

    try:
        for key, value in managed_env.items():
            os.environ[key] = value
        reset_settings_cache()
        yield load_settings()
    finally:
        reset_settings_cache()
        for key, previous_value in previous_env.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
        reset_settings_cache()


@pytest.fixture(scope="module")
def app(test_settings):
    from app.main import create_app

    modules = (
        DomainModule("auth", router_path="app.auth.router:router"),
        DomainModule("competitions", router_path="app.routes.competitions:router"),
    )
    engine = create_engine(test_settings.database_url, connect_args={"check_same_thread": False})
    application = create_app(
        settings=test_settings,
        engine=engine,
        modules=modules,
        run_migration_check=True,
    )
    yield application
    startup_thread = getattr(application.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)
    engine.dispose()


@pytest.fixture
def auth_user_factory(app_session_factory):
    from app.auth.security import create_access_token
    from app.models.wallet import LedgerUnit
    from app.wallets.service import WalletService

    def create_user(
        *,
        suffix: str | None = None,
        funded_credit: Decimal | str | None = None,
        funded_coin: Decimal | str | None = None,
    ) -> dict[str, str]:
        unique_suffix = suffix or uuid4().hex[:8]
        user_id = str(uuid4())
        email = f"{unique_suffix}@example.com"
        username = unique_suffix.replace("-", "_")
        with app_session_factory() as session:
            user = User(
                id=user_id,
                email=email,
                username=username,
                display_name=f"User {unique_suffix}",
                full_name=f"User {unique_suffix}",
                phone_number="1234567890",
                password_hash="not-used",
                role=UserRole.USER,
                kyc_status=KycStatus.FULLY_VERIFIED,
                last_login_at=datetime.now(timezone.utc),
            )
            session.add(user)
            session.flush()
            wallet_service = WalletService()
            if funded_credit is not None:
                wallet_service.credit_trade_proceeds(
                    session,
                    user=user,
                    amount=Decimal(str(funded_credit)),
                    reference=f"seed:credit:{user_id}",
                    description="Competition financial summary test credit funding",
                    external_reference=f"seed:credit:{user_id}",
                    unit=LedgerUnit.CREDIT,
                )
            if funded_coin is not None:
                wallet_service.credit_trade_proceeds(
                    session,
                    user=user,
                    amount=Decimal(str(funded_coin)),
                    reference=f"seed:coin:{user_id}",
                    description="Competition financial summary test coin funding",
                    external_reference=f"seed:coin:{user_id}",
                    unit=LedgerUnit.COIN,
                )
            session.commit()
        access_token = create_access_token(user_id)
        return {
            "email": email,
            "password": "not-used",
            "headers": {"Authorization": f"Bearer {access_token}"},
            "user_id": user_id,
            "username": username,
            "display_name": f"User {unique_suffix}",
        }

    return create_user


def _error_message(response) -> str:
    payload = response.json()
    return payload.get("detail") or payload.get("message")


def _create_club(app_session_factory, *, owner_user_id: str, slug: str, name: str) -> str:
    with app_session_factory() as session:
        club = ClubProfile(
            owner_user_id=owner_user_id,
            club_name=name,
            short_name=name[:20],
            slug=slug,
            primary_color="#A6FF1A",
            secondary_color="#0B1210",
            accent_color="#58D5FF",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
        )
        session.add(club)
        session.commit()
        return club.id


def _ledger_count(app_session_factory, *, competition_id: str, entry_type: str) -> int:
    with app_session_factory() as session:
        return int(
            session.scalar(
                select(func.count())
                .select_from(CompetitionWalletLedger)
                .where(
                    CompetitionWalletLedger.competition_id == competition_id,
                    CompetitionWalletLedger.entry_type == entry_type,
                )
            )
            or 0
        )


def _escrow_rows(app_session_factory, *, competition_id: str) -> list[CompetitionEscrow]:
    with app_session_factory() as session:
        return list(
            session.scalars(
                select(CompetitionEscrow)
                .where(CompetitionEscrow.competition_id == competition_id)
                .order_by(CompetitionEscrow.joined_at.asc(), CompetitionEscrow.created_at.asc())
            ).all()
        )


def _create_paid_competition(
    client,
    host: dict[str, str],
    *,
    name: str,
    format: str = "league",
    capacity: int = 12,
    entry_fee: str = "5.00",
    payout_structure: list[dict[str, str]] | None = None,
) -> str:
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": name,
            "format": format,
            "visibility": "public",
            "entry_fee": entry_fee,
            "currency": "credit",
            "capacity": capacity,
            "platform_fee_pct": "0.10",
            "payout_structure": payout_structure or [{"place": 1, "percent": "1.00"}],
            "rules_summary": "Financial summary validation competition.",
        },
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["platform_fee_pct"] == "0.30"

    publish_response = client.post(
        f"/api/competitions/{created['id']}/publish",
        headers=host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 200, publish_response.text
    return created["id"]


def _join_competition(
    client,
    app_session_factory,
    *,
    competition_id: str,
    user: dict[str, str],
    club_slug: str,
    club_name: str,
) -> dict[str, object]:
    club_id = _create_club(
        app_session_factory,
        owner_user_id=user["user_id"],
        slug=club_slug,
        name=club_name,
    )
    response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=user["headers"],
        json={"club_id": club_id},
    )
    assert response.status_code == 200, response.text
    return {"club_id": club_id, "summary": response.json()}


def test_gtex_financial_summary_exposes_dynamic_jackpot_pool(
    client,
    app_session_factory,
    competition_admin_headers,
    auth_user_factory,
) -> None:
    with app_session_factory() as session:
        for participant in session.query(CompetitionParticipant).all():
            participant.joined_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        session.commit()

    created = client.post(
        "/api/admin/competitions",
        headers=competition_admin_headers,
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
    jackpot_users = [auth_user_factory(suffix=f"jackpot-{index}") for index in range(1, 3)]
    client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=competition_admin_headers,
        json={"open_for_join": True},
    )
    for index, user in enumerate(jackpot_users, start=1):
        _join_competition(
            client,
            app_session_factory,
            competition_id=competition_id,
            user=user,
            club_slug=f"jackpot-club-{index}",
            club_name=f"Jackpot Club {index}",
        )

    rollover = client.post(
        "/api/admin/competitions",
        headers=competition_admin_headers,
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
    assert financials["prize_pool"] == "34.0000"
    assert financials["dynamic_prize_pool"] == {
        "enabled": True,
        "base_funding": "25.0000",
        "activity_boost": "0.5000",
        "jackpot_rollover": "8.5000",
        "total_pool": "34.0000",
        "active_users_5min": 4,
        "trade_volume_5min": "200.0000",
    }

    detail_response = client.get(f"/api/competitions/{competition_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["dynamic_prize_pool"]["total_pool"] == "34.0000"


def test_financial_summary_exposes_transparent_pool_breakdown(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="financial-summary-host")
    competition_id = _create_paid_competition(
        client,
        host,
        name="Transparent League",
        format="league",
        capacity=10,
        entry_fee="20.00",
        payout_structure=[
            {"place": 1, "percent": "0.50"},
            {"place": 2, "percent": "0.30"},
            {"place": 3, "percent": "0.20"},
        ],
    )
    entrants = [
        auth_user_factory(suffix=f"financial-summary-{index}", funded_credit="100.0000") for index in range(1, 3)
    ]
    joined_entries = []
    for index, user in enumerate(entrants, start=1):
        joined_entries.append(
            _join_competition(
                client,
                app_session_factory,
                competition_id=competition_id,
                user=user,
                club_slug=f"financial-summary-club-{index}",
                club_name=f"Financial Summary Club {index}",
            )
        )

    financials_response = client.get(f"/api/competitions/{competition_id}/financials")
    assert financials_response.status_code == 200
    financials = financials_response.json()
    assert {
        "competition_id": competition_id,
        "participant_count": 2,
        "entry_fee": "20.00",
        "gross_pool": "40.0000",
        "platform_fee_pct": "0.30",
        "platform_fee_amount": "12.0000",
        "host_fee_pct": "0.00",
        "host_fee_amount": "0.0000",
        "prize_pool": "28.0000",
        "currency": "credit",
    }.items() <= financials.items()
    assert financials["payout_structure"] == [
        {"place": 1, "percent": "0.50", "amount": "14.0000"},
        {"place": 2, "percent": "0.30", "amount": "8.4000"},
        {"place": 3, "percent": "0.20", "amount": "5.6000"},
    ]

    escrow_rows = _escrow_rows(app_session_factory, competition_id=competition_id)
    assert len(escrow_rows) == 2
    assert {row.amount_minor for row in escrow_rows} == {200_000}
    assert {row.currency for row in escrow_rows} == {"credit"}
    assert {row.escrow_status for row in escrow_rows} == {"escrowed"}
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="entry_fee_collection",
        )
        == 2
    )

    duplicate_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrants[0]["headers"],
        json={"club_id": joined_entries[0]["club_id"]},
    )
    assert duplicate_response.status_code == 200, duplicate_response.text
    unchanged = client.get(f"/api/competitions/{competition_id}/financials").json()
    assert unchanged["participant_count"] == 2
    assert unchanged["gross_pool"] == "40.0000"
    assert len(_escrow_rows(app_session_factory, competition_id=competition_id)) == 2
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="entry_fee_collection",
        )
        == 2
    )


def test_user_hosted_paid_twelve_team_cup_financials_and_duplicate_join(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="financial-twelve-host")
    competition_id = _create_paid_competition(
        client,
        host,
        name="Twelve Team Fan Coin Cup",
        format="cup",
        capacity=12,
        entry_fee="5.00",
        payout_structure=[{"place": 1, "percent": "1.00"}],
    )
    entrants = [
        auth_user_factory(suffix=f"financial-twelve-{index}", funded_credit="50.0000") for index in range(1, 13)
    ]
    joined_entries = []
    for index, user in enumerate(entrants, start=1):
        joined_entries.append(
            _join_competition(
                client,
                app_session_factory,
                competition_id=competition_id,
                user=user,
                club_slug=f"financial-twelve-club-{index}",
                club_name=f"Financial Twelve Club {index}",
            )
        )

    financials_response = client.get(f"/api/competitions/{competition_id}/financials")
    assert financials_response.status_code == 200, financials_response.text
    financials = financials_response.json()
    assert financials["participant_count"] == 12
    assert financials["entry_fee"] == "5.00"
    assert financials["gross_pool"] == "60.0000"
    assert financials["platform_fee_pct"] == "0.30"
    assert financials["platform_fee_amount"] == "18.0000"
    assert financials["prize_pool"] == "42.0000"
    assert financials["payout_structure"] == [{"place": 1, "percent": "1.00", "amount": "42.0000"}]

    assert len(_escrow_rows(app_session_factory, competition_id=competition_id)) == 12
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="entry_fee_collection",
        )
        == 12
    )

    duplicate_response = client.post(
        f"/api/competitions/{competition_id}/join",
        headers=entrants[0]["headers"],
        json={"club_id": joined_entries[0]["club_id"]},
    )
    assert duplicate_response.status_code == 200, duplicate_response.text
    assert client.get(f"/api/competitions/{competition_id}/financials").json()["gross_pool"] == "60.0000"
    assert len(_escrow_rows(app_session_factory, competition_id=competition_id)) == 12
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="entry_fee_collection",
        )
        == 12
    )


def test_top_three_split_never_exceeds_net_escrow(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="financial-top-three-host")
    competition_id = _create_paid_competition(
        client,
        host,
        name="Top Three Fan Coin Cup",
        format="cup",
        capacity=12,
        entry_fee="5.00",
        payout_structure=[
            {"place": 1, "percent": "0.60"},
            {"place": 2, "percent": "0.25"},
            {"place": 3, "percent": "0.15"},
        ],
    )
    entrants = [
        auth_user_factory(suffix=f"financial-top-three-{index}", funded_credit="50.0000") for index in range(1, 13)
    ]
    for index, user in enumerate(entrants, start=1):
        _join_competition(
            client,
            app_session_factory,
            competition_id=competition_id,
            user=user,
            club_slug=f"financial-top-three-club-{index}",
            club_name=f"Financial Top Three Club {index}",
        )

    financials = client.get(f"/api/competitions/{competition_id}/financials").json()
    assert financials["gross_pool"] == "60.0000"
    assert financials["platform_fee_amount"] == "12.0000"
    assert financials["prize_pool"] == "48.0000"
    assert financials["payout_structure"] == [
        {"place": 1, "percent": "0.60", "amount": "28.8000"},
        {"place": 2, "percent": "0.25", "amount": "12.0000"},
        {"place": 3, "percent": "0.15", "amount": "7.2000"},
    ]
    payout_sum = sum(Decimal(item["amount"]) for item in financials["payout_structure"])
    assert payout_sum <= Decimal(financials["prize_pool"])


def test_host_funded_fixed_prizes_surface_gross_up_and_require_escrow(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    unfunded_host = auth_user_factory(suffix="financial-unfunded-fixed-host")
    unfunded_create = client.post(
        "/api/competitions",
        headers=unfunded_host["headers"],
        json={
            "name": "Unfunded Fixed Prize Cup",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "capacity": 4,
            "currency": "coin",
            "prize_mode": "host_funded_fixed",
            "fixed_prizes": {"1": "60.00", "2": "25.00", "3": "15.00"},
            "payout_structure": [
                {"place": 1, "percent": "0.60"},
                {"place": 2, "percent": "0.25"},
                {"place": 3, "percent": "0.15"},
            ],
        },
    )
    assert unfunded_create.status_code == 201, unfunded_create.text
    publish_response = client.post(
        f"/api/competitions/{unfunded_create.json()['id']}/publish",
        headers=unfunded_host["headers"],
        json={"open_for_join": True},
    )
    assert publish_response.status_code == 400
    assert _error_message(publish_response) == "host_prize_insufficient_balance"

    funded_host = auth_user_factory(suffix="financial-funded-fixed-host", funded_coin=Decimal("200.0000"))
    funded_create = client.post(
        "/api/competitions",
        headers=funded_host["headers"],
        json={
            "name": "Funded Fixed Prize Cup",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "capacity": 4,
            "currency": "coin",
            "prize_mode": "host_funded_fixed",
            "fixed_prizes": {"1": "60.00", "2": "25.00", "3": "15.00"},
            "payout_structure": [
                {"place": 1, "percent": "0.60"},
                {"place": 2, "percent": "0.25"},
                {"place": 3, "percent": "0.15"},
            ],
        },
    )
    assert funded_create.status_code == 201, funded_create.text
    created = funded_create.json()
    assert created["host_funded_prize_total"] == "100.00"
    assert created["host_funding_required"] == "125.00"
    assert created["host_platform_fee"] == "25.00"

    competition_id = created["id"]
    funded_publish = client.post(
        f"/api/competitions/{competition_id}/publish",
        headers=funded_host["headers"],
        json={"open_for_join": True},
    )
    assert funded_publish.status_code == 200, funded_publish.text
    assert funded_publish.json()["host_funding_escrowed"] == "125.00"

    financials = client.get(f"/api/competitions/{competition_id}/financials").json()
    assert Decimal(financials["host_funded_prize_total"]) == Decimal("100.00")
    assert Decimal(financials["host_funding_required"]) == Decimal("125.00")
    assert Decimal(financials["host_funding_escrowed"]) == Decimal("125.00")
    assert financials["prize_pool"] == "100.0000"
    assert financials["payout_structure"] == [
        {"place": 1, "percent": "0.60", "amount": "60.0000"},
        {"place": 2, "percent": "0.25", "amount": "25.0000"},
        {"place": 3, "percent": "0.15", "amount": "15.0000"},
    ]
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="host_funded_prize_escrow",
        )
        == 1
    )


def test_free_no_prize_competition_has_zero_pot_and_no_escrow(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="financial-free-host")
    entrant = auth_user_factory(suffix="financial-free-entrant")
    competition_id = _create_paid_competition(
        client,
        host,
        name="Free No Prize League",
        format="league",
        capacity=4,
        entry_fee="0.00",
        payout_structure=[{"place": 1, "percent": "1.00"}],
    )
    _join_competition(
        client,
        app_session_factory,
        competition_id=competition_id,
        user=entrant,
        club_slug="financial-free-club",
        club_name="Financial Free Club",
    )

    financials = client.get(f"/api/competitions/{competition_id}/financials").json()
    assert financials["entry_fee"] == "0.00"
    assert financials["gross_pool"] == "0.0000"
    assert financials["platform_fee_amount"] == "0.0000"
    assert financials["prize_pool"] == "0.0000"
    assert financials["is_ranked"] is True
    assert financials["remaining_slots"] == 3
    escrow_rows = _escrow_rows(app_session_factory, competition_id=competition_id)
    assert len(escrow_rows) == 1
    assert escrow_rows[0].amount_minor == 0
    assert escrow_rows[0].escrow_status == "none"
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="entry_fee_collection",
        )
        == 0
    )


# The economic constitution prohibits mixing participant entry fees with a
# host-funded prize: validate_competition_funding_contract rejects both
# "FanCoin entry-pool competitions cannot also carry a host-funded prize" and
# "Participant-funded GTEX Coin prize pools are prohibited", and the model
# boundary enforces the same invariant. The original single test built exactly
# that now-impossible competition, so its subject -- refunding each escrow
# exactly once across a repeated cancel -- is covered here once per legal mode.


def test_cancellation_refunds_participant_escrow_once(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="financial-cancel-host")
    entrant = auth_user_factory(suffix="financial-cancel-entrant", funded_credit=Decimal("50.0000"))
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Refundable Entry Pool Cup",
            "format": "league",
            "visibility": "public",
            "entry_fee": "5.00",
            "currency": "credit",
            "capacity": 4,
            "payout_structure": [{"place": 1, "percent": "1.00"}],
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
    _join_competition(
        client,
        app_session_factory,
        competition_id=competition_id,
        user=entrant,
        club_slug="financial-cancel-club",
        club_name="Financial Cancel Club",
    )

    first_cancel = client.post(f"/api/competitions/{competition_id}/cancel", headers=host["headers"])
    assert first_cancel.status_code == 200, first_cancel.text
    assert first_cancel.json()["status"] == "cancelled"
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="entry_fee_refund",
        )
        == 1
    )
    refunded_rows = _escrow_rows(app_session_factory, competition_id=competition_id)
    assert len(refunded_rows) == 1
    assert refunded_rows[0].escrow_status == "refunded"

    second_cancel = client.post(f"/api/competitions/{competition_id}/cancel", headers=host["headers"])
    assert second_cancel.status_code == 200, second_cancel.text
    assert second_cancel.json()["status"] == "cancelled"
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="entry_fee_refund",
        )
        == 1
    )
    assert len(_escrow_rows(app_session_factory, competition_id=competition_id)) == 1


def test_cancellation_refunds_host_escrow_once(
    client,
    app_session_factory,
    auth_user_factory,
) -> None:
    host = auth_user_factory(suffix="financial-cancel-coin-host", funded_coin=Decimal("200.0000"))
    create_response = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Refundable Fixed Prize Cup",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "capacity": 4,
            "currency": "coin",
            "prize_mode": "host_funded_fixed",
            "fixed_prizes": {"1": "60.00", "2": "25.00", "3": "15.00"},
            "payout_structure": [
                {"place": 1, "percent": "0.60"},
                {"place": 2, "percent": "0.25"},
                {"place": 3, "percent": "0.15"},
            ],
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

    first_cancel = client.post(f"/api/competitions/{competition_id}/cancel", headers=host["headers"])
    assert first_cancel.status_code == 200, first_cancel.text
    assert first_cancel.json()["status"] == "cancelled"
    assert first_cancel.json()["host_funding_escrowed"] == "0.00"
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="host_funded_prize_refund",
        )
        == 1
    )

    second_cancel = client.post(f"/api/competitions/{competition_id}/cancel", headers=host["headers"])
    assert second_cancel.status_code == 200, second_cancel.text
    assert second_cancel.json()["status"] == "cancelled"
    assert second_cancel.json()["host_funding_escrowed"] == "0.00"
    assert (
        _ledger_count(
            app_session_factory,
            competition_id=competition_id,
            entry_type="host_funded_prize_refund",
        )
        == 1
    )


def test_summary_and_detail_keep_financial_fields_visible(client, auth_user_factory) -> None:
    host = auth_user_factory(suffix="financial-visible-host")
    created = client.post(
        "/api/competitions",
        headers=host["headers"],
        json={
            "name": "Free Discovery Cup",
            "format": "cup",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "credit",
            "capacity": 8,
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
