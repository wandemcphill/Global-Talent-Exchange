from __future__ import annotations

from datetime import datetime, timedelta, timezone

from decimal import Decimal
from uuid import uuid4

import pytest

from backend.tests.support.secrets import DASHBOARD_TEST_ADMIN_PASSWORD
from app.ingestion.models import Country, Player
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService


def _login(client, *, email: str, password: str) -> dict[str, str]:
    cache = getattr(client, "_auth_header_cache", {})
    cache_key = (email, password)
    if cache_key in cache:
        return cache[cache_key]
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    cache[cache_key] = headers
    setattr(client, "_auth_header_cache", cache)
    return headers


def _error_message(response) -> str:
    body = response.json()
    return str(body.get("detail") or body.get("message") or body.get("code") or "")


@pytest.fixture(scope="module")
def national_admin_headers(client, app_session_factory) -> dict[str, str]:
    from app.auth.service import AuthService
    from app.models.user import UserRole

    email = "vidvimedialtd@gmail.com"
    with app_session_factory() as session:
        AuthService().ensure_admin_user(
            session,
            email=email,
            password=DASHBOARD_TEST_ADMIN_PASSWORD,
            username="vidvimedialtd",
            display_name="GTEX National Team Admin",
            role=UserRole.SUPER_ADMIN,
        )
        session.commit()
    return _login(client, email=email, password=DASHBOARD_TEST_ADMIN_PASSWORD)


def _create_competition(client, admin_headers: dict[str, str], *, key_prefix: str) -> dict:
    response = client.post(
        "/api/admin/national-team-engine/competitions",
        headers=admin_headers,
        json={
            "key": f"{key_prefix}-{uuid4().hex[:8]}",
            "title": "GTEX World Cup",
            "season_label": "2030",
            "region_type": "global",
            "age_band": "senior",
            "format_type": "cup",
            "status": "published",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _create_entry(
    client,
    admin_headers: dict[str, str],
    *,
    competition_id: str,
    manager_user_id: str,
    country_code: str,
    country_name: str,
) -> dict:
    response = client.post(
        f"/api/admin/national-team-engine/competitions/{competition_id}/entries",
        headers=admin_headers,
        json={
            "country_code": country_code,
            "country_name": country_name,
            "manager_user_id": manager_user_id,
            "metadata_json": {"seed": country_code},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _competition_squad(prefix: str) -> list[dict[str, object]]:
    positions = ("GK", "CB", "CM")
    return [
        {
            "player_name": f"{prefix} Player {index}",
            "age": 24 + index,
            "overall_rating": 68 + index,
            "position": position,
        }
        for index, position in enumerate(positions, start=1)
    ]


def _seed_national_pool(
    app_session_factory,
    *,
    prefix: str,
    funded_user_id: str,
    home_code: str,
    home_name: str,
    away_code: str,
    away_name: str,
) -> dict[str, str]:
    wallet_service = WalletService()
    player_ids: dict[str, str] = {}
    with app_session_factory() as session:
        home_country = Country(
            source_provider="test",
            provider_external_id=f"{prefix}-country-home",
            name=home_name,
            alpha2_code=home_code,
            alpha3_code=f"{home_code}A",
            fifa_code=home_code,
        )
        away_country = Country(
            source_provider="test",
            provider_external_id=f"{prefix}-country-away",
            name=away_name,
            alpha2_code=away_code,
            alpha3_code=f"{away_code}A",
            fifa_code=away_code,
        )
        session.add_all([home_country, away_country])
        session.flush()

        specs = [
            ("home-gk", f"{prefix} Keeper", "GK", 70, "preseeded", False, False, home_country.id),
            ("home-rb", f"{prefix} Right Back", "RB", 66, "club", True, False, home_country.id),
            ("home-cb1", f"{prefix} Centre Back One", "CB", 68, "club", True, False, home_country.id),
            ("home-cb2", f"{prefix} Centre Back Two", "CB", 72, "real", True, True, home_country.id),
            ("home-lb", f"{prefix} Left Back", "LB", 64, "preseeded", False, False, home_country.id),
            ("home-dm", f"{prefix} Anchor", "DM", 74, "club", True, False, home_country.id),
            ("home-cm", f"{prefix} Controller", "CM", 75, "club", True, False, home_country.id),
            ("home-rw", f"{prefix} Right Winger", "RW", 78, "real", True, True, home_country.id),
            ("home-am", f"{prefix} Creator", "AM", 76, "preseeded", False, False, home_country.id),
            ("home-lw", f"{prefix} Left Winger", "LW", 71, "preseeded", False, False, home_country.id),
            ("home-st", f"{prefix} Striker", "ST", 80, "real", True, True, home_country.id),
            ("away-st", f"{prefix} Away Striker", "ST", 82, "real", True, True, away_country.id),
        ]
        for slug, full_name, position, gsi, source_bucket, tradable, is_real, country_id in specs:
            player = Player(
                source_provider="test",
                provider_external_id=f"{prefix}-{slug}",
                country_id=country_id,
                full_name=full_name,
                position=position,
                normalized_position=position,
                is_tradable=tradable,
                is_real_player=is_real,
                dna_profile={"gsi": gsi, "regen_type": source_bucket},
            )
            session.add(player)
            session.flush()
            player_ids[slug] = player.id

        funded_user = session.get(User, funded_user_id)
        assert funded_user is not None
        user_account = wallet_service.get_user_account(session, funded_user, LedgerUnit.COIN)
        platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=platform_account, amount=Decimal("-1500.0000")),
                LedgerPosting(account=user_account, amount=Decimal("1500.0000")),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference=f"test-funding:{prefix}:{funded_user_id}",
            description="National team router test funding",
            actor=funded_user,
        )
        session.commit()
    return player_ids


def test_admin_can_create_national_team_competition_and_entry(client, demo_seed, national_admin_headers) -> None:
    admin_headers = national_admin_headers
    response = client.post(
        "/api/admin/national-team-engine/competitions",
        headers=admin_headers,
        json={
            "key": "gtex-world-cup-2030",
            "title": "GTEX World Cup",
            "season_label": "2030",
            "region_type": "global",
            "age_band": "senior",
            "format_type": "cup",
            "status": "published",
        },
    )
    assert response.status_code == 200, response.text
    competition = response.json()

    manager_user = demo_seed.demo_users[0]
    entry_response = client.post(
        f"/api/admin/national-team-engine/competitions/{competition['id']}/entries",
        headers=admin_headers,
        json={
            "country_code": "NG",
            "country_name": "Nigeria",
            "manager_user_id": manager_user.user_id,
            "metadata_json": {"seed": 1},
        },
    )
    assert entry_response.status_code == 200, entry_response.text
    entry = entry_response.json()
    assert entry["country_code"] == "NG"
    assert entry["manager_user_id"] == manager_user.user_id

    list_response = client.get("/api/national-team-engine/competitions")
    assert list_response.status_code == 200
    assert any(item["key"] == "gtex-world-cup-2030" for item in list_response.json())


def test_rental_pool_returns_preseeded_regen_portrait_and_restrictions(
    client,
    app_session_factory,
    national_admin_headers,
) -> None:
    competition = _create_competition(client, national_admin_headers, key_prefix="preseeded-portrait-pool")
    with app_session_factory() as session:
        session.add(
            Country(
                source_provider="test",
                provider_external_id=f"country-ng-{uuid4().hex[:8]}",
                name="Nigeria",
                alpha2_code="NG",
                alpha3_code="NGA",
                fifa_code="NGA",
            )
        )
        session.add(
            NationalRegenSeed(
                seed_key=f"ng-seed-{uuid4().hex}",
                display_name="Ayo Okafor",
                age=18,
                age_band="senior",
                country_code="NG",
                country_name="Nigeria",
                primary_position="ST",
                current_rating=82,
                potential_rating=91,
                rarity_tier="rare",
                status="available",
                metadata_json={
                    "portraitUrl": "https://media.test/generated-media/regen_newgen_faces/script_skin_hair/African/Black/African-Black-001.png",
                    "portraitStatus": "approved",
                    "portraitSourceProvider": "approved_newgen_bank",
                },
            )
        )
        session.commit()

    response = client.get(
        f"/api/national-team-engine/competitions/{competition['id']}/rental-pool",
        params={"country_code": "NG", "preseeded_only": True, "limit": 20},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["partial"] is False
    assert payload["failed_count"] == 0
    assert payload["source_counts"]["preseeded"] >= 1
    seed_item = next(item for item in payload["items"] if item["player_name"] == "Ayo Okafor")
    assert seed_item["image_url"].endswith("African-Black-001.png")
    assert seed_item["portrait_url"] == seed_item["image_url"]
    assert seed_item["portrait_status"] == "approved"
    assert seed_item["is_preseeded_national_regen"] is True
    assert seed_item["national_pool_only"] is True
    assert seed_item["buyable"] is False
    assert seed_item["tradable"] is False
    assert seed_item["transferable"] is False


def test_rental_pool_empty_country_is_valid_response(client, national_admin_headers) -> None:
    competition = _create_competition(client, national_admin_headers, key_prefix="empty-country-pool")

    response = client.get(
        f"/api/national-team-engine/competitions/{competition['id']}/rental-pool",
        params={"country_code": "ZZ", "preseeded_only": True, "limit": 20},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["partial"] is False


def test_multiple_users_can_rent_same_national_team(client, demo_seed, national_admin_headers) -> None:
    competition_response = client.post(
        "/api/admin/national-team-engine/competitions",
        headers=national_admin_headers,
        json={
            "key": f"same-country-rental-{uuid4().hex[:8]}",
            "title": "Same Country Rental Cup",
            "season_label": "2030",
            "region_type": "global",
            "age_band": "senior",
            "format_type": "cup",
            "status": "published",
            "metadata_json": {"minimum_squad_size": 3, "maximum_squad_size": 5},
        },
    )
    assert competition_response.status_code == 200, competition_response.text
    competition = competition_response.json()
    primary = demo_seed.demo_users[0]
    secondary = demo_seed.demo_users[1]
    primary_headers = _login(client, email=primary.email, password=primary.password)
    secondary_headers = _login(client, email=secondary.email, password=secondary.password)

    first_entry = client.post(
        f"/api/national-team-engine/competitions/{competition['id']}/rental-entry",
        headers=primary_headers,
        json={"country_code": "NG", "country_name": "Nigeria"},
    )
    assert first_entry.status_code == 200, first_entry.text

    second_entry = client.post(
        f"/api/national-team-engine/competitions/{competition['id']}/rental-entry",
        headers=secondary_headers,
        json={"country_code": "NG", "country_name": "Nigeria"},
    )
    assert second_entry.status_code == 200, second_entry.text

    first_payload = first_entry.json()
    second_payload = second_entry.json()
    assert first_payload["id"] != second_payload["id"]
    assert first_payload["country_code"] == second_payload["country_code"] == "NG"
    assert first_payload["entry_owner_user_id"] == primary.user_id
    assert second_payload["entry_owner_user_id"] == secondary.user_id


def test_admin_can_upsert_squad_and_user_can_view_history(client, demo_seed, national_admin_headers) -> None:
    admin_headers = national_admin_headers
    user_headers = _login(client, email=demo_seed.demo_users[0].email, password=demo_seed.demo_users[0].password)
    competition_id = client.get("/api/national-team-engine/competitions").json()[0]["id"]
    entry_response = client.post(
        f"/api/admin/national-team-engine/competitions/{competition_id}/entries",
        headers=admin_headers,
        json={
            "country_code": "GH",
            "country_name": "Ghana",
            "manager_user_id": demo_seed.demo_users[0].user_id,
            "metadata_json": {"seed": 2},
        },
    )
    assert entry_response.status_code == 200, entry_response.text
    entry = entry_response.json()

    squad_response = client.post(
        f"/api/admin/national-team-engine/entries/{entry['id']}/squad",
        headers=admin_headers,
        json={
            "members": [
                {
                    "user_id": demo_seed.demo_users[0].user_id,
                    "player_name": "Demo Captain",
                    "shirt_number": 8,
                    "role_label": "captain",
                    "status": "selected",
                },
                {
                    "user_id": demo_seed.demo_users[1].user_id,
                    "player_name": "Demo Striker",
                    "shirt_number": 9,
                    "role_label": "forward",
                    "status": "selected",
                },
            ]
        },
    )
    assert squad_response.status_code == 200, squad_response.text
    detail = squad_response.json()
    assert detail["squad_size"] == 2
    assert len(detail["squad_members"]) == 2

    history_response = client.get("/api/national-team-engine/me/history", headers=user_headers)
    assert history_response.status_code == 200, history_response.text
    history = history_response.json()
    assert len(history["managed_entries"]) >= 1
    assert len(history["squad_memberships"]) >= 1


def test_live_linked_competition_blocks_new_rentals(client, demo_seed, national_admin_headers) -> None:
    admin_headers = national_admin_headers
    manager = demo_seed.demo_users[0]
    manager_headers = _login(client, email=manager.email, password=manager.password)
    second_manager = demo_seed.demo_users[1]
    second_manager_headers = _login(client, email=second_manager.email, password=second_manager.password)

    competition_response = client.post(
        "/api/competitions",
        headers=admin_headers,
        json={
            "name": "Live Lock League",
            "format": "league",
            "visibility": "public",
            "entry_fee": "0.00",
            "currency": "credit",
            "capacity": 2,
            "creator_id": "lock-host",
            "payout_structure": [{"place": 1, "percent": "1.00"}],
            "scheduled_start_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )
    assert competition_response.status_code == 201, competition_response.text
    linked_competition_id = competition_response.json()["id"]

    publish = client.post(
        f"/api/competitions/{linked_competition_id}/publish",
        headers=admin_headers,
        json={"open_for_join": True},
    )
    assert publish.status_code == 200, publish.text
    joined = client.post(
        f"/api/competitions/{linked_competition_id}/join",
        headers=manager_headers,
        json={"user_id": manager.user_id},
    )
    assert joined.status_code == 200, joined.text
    joined = client.post(
        f"/api/competitions/{linked_competition_id}/join",
        headers=second_manager_headers,
        json={"user_id": second_manager.user_id},
    )
    assert joined.status_code == 200, joined.text
    seed = client.post(
        f"/api/competitions/{linked_competition_id}/seed",
        headers=admin_headers,
        json={"seed_method": "random"},
    )
    assert seed.status_code == 200, seed.text
    launch = client.post(
        f"/api/competitions/{linked_competition_id}/launch",
        headers=admin_headers,
    )
    assert launch.status_code == 200, launch.text
    assert launch.json()["status"] == "live"

    competition = client.post(
        "/api/admin/national-team-engine/competitions",
        headers=admin_headers,
        json={
            "key": "gtex-world-cup-live-lock",
            "title": "GTEX World Cup Live Lock",
            "season_label": "2030",
            "region_type": "global",
            "age_band": "senior",
            "format_type": "cup",
            "status": "published",
            "linked_competition_id": linked_competition_id,
        },
    )
    assert competition.status_code == 200, competition.text
    national_team_competition = competition.json()

    entry_response = client.post(
        f"/api/admin/national-team-engine/competitions/{national_team_competition['id']}/entries",
        headers=admin_headers,
        json={
            "country_code": "NG",
            "country_name": "Nigeria",
            "manager_user_id": manager.user_id,
            "metadata_json": {"seed": 1},
        },
    )
    assert entry_response.status_code == 200, entry_response.text
    entry = entry_response.json()

    rental_pool = client.get(
        f"/api/national-team-engine/competitions/{national_team_competition['id']}/rental-pool",
        headers=manager_headers,
    )
    assert rental_pool.status_code == 200, rental_pool.text
    player_id = rental_pool.json()["items"][0]["player_id"]

    rent_response = client.post(
        f"/api/national-team-engine/entries/{entry['id']}/rentals",
        headers=manager_headers,
        json={"player_id": player_id},
    )
    assert rent_response.status_code == 409, rent_response.text
    assert _error_message(rent_response) == "competition_already_live"


def test_rental_pool_filters_by_country_and_source_bucket_with_bucket_pricing(
    client, demo_seed, app_session_factory, national_admin_headers
) -> None:
    admin_headers = national_admin_headers
    competition = _create_competition(client, admin_headers, key_prefix="pool-filter")
    home_code = "NP1"
    home_name = "Nation Prime One"
    away_code = "AX1"
    away_name = "Away X One"
    player_ids = _seed_national_pool(
        app_session_factory,
        prefix="pool-filter",
        funded_user_id=demo_seed.demo_users[0].user_id,
        home_code=home_code,
        home_name=home_name,
        away_code=away_code,
        away_name=away_name,
    )

    filtered_response = client.get(
        f"/api/national-team-engine/competitions/{competition['id']}/rental-pool",
        params=[("country_code", home_code), ("source_bucket", "preseeded")],
    )
    assert filtered_response.status_code == 200, filtered_response.text
    filtered_payload = filtered_response.json()
    assert filtered_payload["total"] >= 1
    assert all(item["source_bucket"] == "preseeded" for item in filtered_payload["items"])
    assert all(item["country_code"] == home_code for item in filtered_payload["items"])
    assert all(item["supply_mode"] == "infinite" for item in filtered_payload["items"])

    all_response = client.get(
        f"/api/national-team-engine/competitions/{competition['id']}/rental-pool",
        params={"country_code": home_code},
    )
    assert all_response.status_code == 200, all_response.text
    players_by_id = {item["player_id"]: item for item in all_response.json()["items"]}

    real_player = players_by_id[player_ids["home-st"]]
    preseeded_player = players_by_id[player_ids["home-gk"]]
    club_player = players_by_id[player_ids["home-cm"]]
    assert Decimal(str(real_player["loan_price_coin"])) == Decimal("80.0000")
    assert Decimal(str(preseeded_player["loan_price_coin"])) == Decimal("42.0000")
    assert Decimal(str(club_player["loan_price_coin"])) == Decimal("67.5000")
    assert all(Decimal(str(item["demand_multiplier"])) == Decimal("1.0000") for item in players_by_id.values())


def test_rent_player_enforces_country_lock_and_auto_build_returns_budgeted_squad(
    client, demo_seed, app_session_factory, national_admin_headers
) -> None:
    admin_headers = national_admin_headers
    manager_headers = _login(client, email=demo_seed.demo_users[0].email, password=demo_seed.demo_users[0].password)
    competition = _create_competition(client, admin_headers, key_prefix="pool-rent")
    home_code = "NP2"
    home_name = "Nation Prime Two"
    away_code = "AX2"
    away_name = "Away X Two"
    player_ids = _seed_national_pool(
        app_session_factory,
        prefix="pool-rent",
        funded_user_id=demo_seed.demo_users[0].user_id,
        home_code=home_code,
        home_name=home_name,
        away_code=away_code,
        away_name=away_name,
    )
    entry = _create_entry(
        client,
        admin_headers,
        competition_id=competition["id"],
        manager_user_id=demo_seed.demo_users[0].user_id,
        country_code=home_code,
        country_name=home_name,
    )

    reject_response = client.post(
        f"/api/national-team-engine/entries/{entry['id']}/rentals",
        headers=manager_headers,
        json={"player_id": player_ids["away-st"]},
    )
    assert reject_response.status_code == 409, reject_response.text
    assert _error_message(reject_response) == "player_not_eligible"

    success_response = client.post(
        f"/api/national-team-engine/entries/{entry['id']}/rentals",
        headers=manager_headers,
        json={"player_id": player_ids["home-st"]},
    )
    assert success_response.status_code == 200, success_response.text
    rented_entry = success_response.json()
    rented_member = next(
        item for item in rented_entry["rental_squad_members"] if item["player_id"] == player_ids["home-st"]
    )
    assert rented_member["metadata_json"]["source_bucket"] == "real"
    assert rented_member["metadata_json"]["supply_mode"] == "infinite"

    repriced_pool = client.get(
        f"/api/national-team-engine/competitions/{competition['id']}/rental-pool",
        params={"country_code": home_code},
    )
    assert repriced_pool.status_code == 200, repriced_pool.text
    repriced_player = next(item for item in repriced_pool.json()["items"] if item["player_id"] == player_ids["home-st"])
    assert Decimal(str(repriced_player["demand_multiplier"])) >= Decimal("1.1500")
    assert Decimal(str(repriced_player["loan_price_coin"])) > Decimal("80.0000")

    auto_build_response = client.post(
        f"/api/national-team-engine/competitions/{competition['id']}/auto-build-squad",
        json={
            "country_code": home_code,
            "budget_coin": "700.0000",
            "tactic": "balanced",
        },
    )
    assert auto_build_response.status_code == 200, auto_build_response.text
    auto_build_payload = auto_build_response.json()
    assert auto_build_payload["formation"] == "4-2-3-1"
    assert auto_build_payload["complete"] is True
    assert auto_build_payload["selected_count"] == 11
    assert Decimal(str(auto_build_payload["total_cost_coin"])) <= Decimal("700.0000")
    assert all(item["country_code"] == home_code for item in auto_build_payload["players"])
    assert auto_build_payload["source_mix"]["real"] >= 1
    assert auto_build_payload["source_mix"]["regen"] >= 1


def test_claim_free_players_grants_starter_pack_shape_from_national_pool(
    client, demo_seed, app_session_factory, national_admin_headers
) -> None:
    admin_headers = national_admin_headers
    manager_headers = _login(client, email=demo_seed.demo_users[0].email, password=demo_seed.demo_users[0].password)
    competition = _create_competition(client, admin_headers, key_prefix="pool-free")
    home_code = "NP3"
    home_name = "Nation Prime Three"
    away_code = "AX3"
    away_name = "Away X Three"
    _seed_national_pool(
        app_session_factory,
        prefix="pool-free",
        funded_user_id=demo_seed.demo_users[0].user_id,
        home_code=home_code,
        home_name=home_name,
        away_code=away_code,
        away_name=away_name,
    )
    entry = _create_entry(
        client,
        admin_headers,
        competition_id=competition["id"],
        manager_user_id=demo_seed.demo_users[0].user_id,
        country_code=home_code,
        country_name=home_name,
    )

    claim_response = client.post(
        f"/api/national-team-engine/entries/{entry['id']}/free-players/claim",
        headers=manager_headers,
    )
    assert claim_response.status_code == 200, claim_response.text
    payload = claim_response.json()
    assert len(payload["rental_squad_members"]) == 5
    positions = [item["metadata_json"]["primary_position"] for item in payload["rental_squad_members"]]
    assigned_slots = [item["metadata_json"]["assigned_slot"] for item in payload["rental_squad_members"]]
    assert "GK" in positions
    assert "ST" in positions
    assert any(slot == "WINGER" for slot in assigned_slots)
    assert assigned_slots.count("MIDFIELDER") == 2


def test_qualifier_lock_blocks_new_entries_and_updates_country_rankings(
    client, demo_seed, national_admin_headers
) -> None:
    admin_headers = national_admin_headers
    primary_headers = _login(client, email=demo_seed.demo_users[0].email, password=demo_seed.demo_users[0].password)
    secondary_headers = _login(client, email=demo_seed.demo_users[1].email, password=demo_seed.demo_users[1].password)
    third_user = demo_seed.demo_users[2]
    third_headers = _login(client, email=third_user.email, password=third_user.password)

    competition_response = client.post(
        "/api/admin/national-team-engine/competitions",
        headers=admin_headers,
        json={
            "key": f"ranking-lock-{uuid4().hex[:8]}",
            "title": "GTEX World Cup Ranking Lock",
            "season_label": "2030",
            "region_type": "global",
            "age_band": "senior",
            "format_type": "cup",
            "status": "published",
            "metadata_json": {
                "minimum_squad_size": 3,
                "maximum_squad_size": 5,
                "tournament_slots": 2,
            },
        },
    )
    assert competition_response.status_code == 200, competition_response.text
    competition = competition_response.json()

    first_entry = client.post(
        f"/api/national-team-engine/competitions/{competition['id']}/entries",
        headers=primary_headers,
        json={
            "country_code": "NG",
            "country_name": "Nigeria",
            "squad": _competition_squad("Nigeria"),
        },
    )
    assert first_entry.status_code == 200, first_entry.text

    second_entry = client.post(
        f"/api/national-team-engine/competitions/{competition['id']}/entries",
        headers=secondary_headers,
        json={
            "country_code": "GH",
            "country_name": "Ghana",
            "squad": _competition_squad("Ghana"),
        },
    )
    assert second_entry.status_code == 200, second_entry.text

    lock_response = client.post(
        f"/api/admin/national-team-engine/competitions/{competition['id']}/entries/lock",
        headers=admin_headers,
    )
    assert lock_response.status_code == 200, lock_response.text
    assert lock_response.json()["current_stage"] == "tournament"

    locked_user_response = client.post(
        f"/api/national-team-engine/competitions/{competition['id']}/entries",
        headers=third_headers,
        json={
            "country_code": "SN",
            "country_name": "Senegal",
            "squad": _competition_squad("Senegal"),
        },
    )
    assert locked_user_response.status_code == 409, locked_user_response.text
    assert _error_message(locked_user_response) == "entry_locked"

    locked_admin_response = client.post(
        f"/api/admin/national-team-engine/competitions/{competition['id']}/entries",
        headers=admin_headers,
        json={
            "country_code": "CI",
            "country_name": "Cote d'Ivoire",
            "manager_user_id": third_user.user_id,
            "metadata_json": {"seed": 3},
        },
    )
    assert locked_admin_response.status_code == 409, locked_admin_response.text
    assert "locked" in _error_message(locked_admin_response).lower()

    advance_response = client.post(
        f"/api/admin/national-team-engine/competitions/{competition['id']}/lifecycle/advance",
        headers=admin_headers,
    )
    assert advance_response.status_code == 200, advance_response.text
    assert advance_response.json()["current_stage"] == "completed"

    rankings_response = client.get("/api/national-team-engine/rankings")
    assert rankings_response.status_code == 200, rankings_response.text
    rankings_by_country = {item["country_code"]: item for item in rankings_response.json()}
    assert {"NG", "GH"}.issubset(rankings_by_country)
    assert rankings_by_country["NG"]["matches_played"] >= 1
    assert rankings_by_country["GH"]["matches_played"] >= 1
    assert rankings_by_country["NG"]["elo_rating"] != 1500.0 or rankings_by_country["GH"]["elo_rating"] != 1500.0
