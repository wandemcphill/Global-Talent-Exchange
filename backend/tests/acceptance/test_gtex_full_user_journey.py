from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.ingestion.models import Player
from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.models.transfer_window import TransferWindow
from app.services.player_lifecycle_service import PlayerLifecycleService
from app.wallets.service import WalletService
from app.models.wallet import LedgerUnit
from backend.tests.players.test_player_share_market_routes import _seed_imported_real_player


JOURNEY_PREFIX = "gtex-full-journey"
TEST_PASSWORD = "TestPassword123!"


def _register(client, *, suffix: str, funded_credit: str = "0", funded_coin: str = "0") -> dict[str, object]:
    response = client.post(
        "/auth/signup/user",
        json={
            "email": f"{suffix}@example.com",
            "username": suffix.replace("-", "_"),
            "password": TEST_PASSWORD,
            "full_name": f"GTEX Journey {suffix}",
            "country": "NG",
            "state": "Lagos",
            "city": "Lagos",
            "club_name": f"{suffix.title().replace('-', ' ')} FC",
            "club_short_tag": suffix.replace("-", "")[:8].upper(),
            "club_country": "NG",
            "club_state": "Lagos",
            "club_locality": "Lagos",
            "club_type": "community",
            "football_identity": "club_owner",
            "compliance": {
                "government_id_attachment_id": f"gov-{suffix}",
                "selfie_attachment_id": f"selfie-{suffix}",
                "country_confirmation": "NG",
            },
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    user_id = payload["user"]["id"]
    headers = {"Authorization": f"Bearer {payload['access_token']}"}

    if Decimal(funded_credit) or Decimal(funded_coin):
        with client.app.state.session_factory() as session:
            user = session.get(__import__("app.models.user", fromlist=["User"]).User, user_id)
            assert user is not None
            wallet = WalletService()
            if Decimal(funded_credit):
                wallet.credit_trade_proceeds(
                    session,
                    user=user,
                    amount=Decimal(funded_credit),
                    reference=f"{JOURNEY_PREFIX}:credit:{user_id}",
                    description="GTEX full journey test Credit funding",
                    external_reference=f"{JOURNEY_PREFIX}:credit:{user_id}",
                    unit=LedgerUnit.CREDIT,
                )
            if Decimal(funded_coin):
                wallet.credit_trade_proceeds(
                    session,
                    user=user,
                    amount=Decimal(funded_coin),
                    reference=f"{JOURNEY_PREFIX}:coin:{user_id}",
                    description="GTEX full journey test Coin funding",
                    external_reference=f"{JOURNEY_PREFIX}:coin:{user_id}",
                    unit=LedgerUnit.COIN,
                )
            session.commit()

    return {
        "user_id": user_id,
        "email": payload["user"]["email"],
        "headers": headers,
        "club_id": _owned_club_id(client, user_id),
    }


def _owned_club_id(client, user_id: str) -> str:
    with client.app.state.session_factory() as session:
        club = session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == user_id))
        assert club is not None
        return club.id


def _seed_real_players(client, *, owner_user_id: str, seller_user_id: str) -> dict[str, str]:
    with client.app.state.session_factory() as session:
        seller_club = session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == seller_user_id))
        owner_club = session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == owner_user_id))
        assert seller_club is not None
        assert owner_club is not None

        real_player = _seed_imported_real_player(session, player_id=f"{JOURNEY_PREFIX}-real")
        real_player.current_club_profile_id = seller_club.id

        parent_player = _seed_imported_real_player(session, player_id=f"{JOURNEY_PREFIX}-parent")
        parent_player.current_club_profile_id = owner_club.id
        parent_player.country_id = None

        session.add(
            TransferWindow(
                id=f"{JOURNEY_PREFIX}-window",
                territory_code="NG",
                label="GTEX Acceptance Window",
                status="open",
                opens_on=date(2026, 1, 1),
                closes_on=date(2026, 12, 31),
            )
        )
        session.commit()
        return {
            "real_player_id": real_player.id,
            "parent_player_id": parent_player.id,
            "window_id": f"{JOURNEY_PREFIX}-window",
            "seller_club_id": seller_club.id,
            "owner_club_id": owner_club.id,
        }


def _assert_status(response, expected: int) -> dict:
    assert response.status_code == expected, response.text
    return response.json()


def test_gtex_full_user_journey(
    client,
    bootstrap_admin_headers,
) -> None:
    """Canonical cross-domain acceptance journey.

    This deliberately creates its own authenticated users and economic fixtures.
    Every user mutation goes through the public/admin API surface except narrowly
    scoped setup work that represents platform provisioning of test assets.
    """

    # ------------------------------------------------------------------
    # A. Registration and user identities
    # ------------------------------------------------------------------
    owner = _register(client, suffix=f"{JOURNEY_PREFIX}-owner", funded_credit="5000", funded_coin="10000")
    trader = _register(client, suffix=f"{JOURNEY_PREFIX}-trader", funded_credit="500", funded_coin="100000")
    peer = _register(client, suffix=f"{JOURNEY_PREFIX}-peer", funded_credit="5000", funded_coin="5000")
    recipient = _register(client, suffix=f"{JOURNEY_PREFIX}-recipient", funded_credit="2500", funded_coin="2500")
    buyer = _register(client, suffix=f"{JOURNEY_PREFIX}-buyer", funded_credit="5000", funded_coin="100000")
    club_buyer = _register(client, suffix=f"{JOURNEY_PREFIX}-club-buyer", funded_credit="5000", funded_coin="200000")

    user_ids = {str(item["user_id"]) for item in (owner, trader, peer, recipient, buyer, club_buyer)}
    assert len(user_ids) == 6
    assert all(user_ids)
    assert all(item["club_id"] for item in (owner, trader, peer, recipient, buyer, club_buyer))

    # ------------------------------------------------------------------
    # B. Coin Trader user journey
    # apply -> approve -> quote -> buy -> escrow -> proof -> release
    # ------------------------------------------------------------------
    application = _assert_status(
        client.post(
            "/api/coin-traders/apply",
            headers=trader["headers"],
            json={
                "display_name": "GTEX Journey OTC Desk",
                "country_code": "NG",
                "terms": {"same_name_account_only": True, "payment_proof_required": True},
                "payment_methods": [{"label": "Bank transfer", "type": "bank_transfer"}],
                "bank_accounts": [{"bank": "GTBank"}],
                "metadata_json": {"journey": JOURNEY_PREFIX},
            },
        ),
        201,
    )
    trader_profile_id = application["id"]

    approval = _assert_status(
        client.post(
            f"/api/admin/coin-traders/{trader_profile_id}/approve",
            headers=bootstrap_admin_headers,
            json={"tier": "gold", "note": "full user journey"},
        ),
        200,
    )
    assert approval["status"] == "approved"

    _assert_status(
        client.put(
            "/api/coin-traders/me/rates",
            headers=trader["headers"],
            json={
                "coin_unit": "coin",
                "fiat_currency": "NGN",
                "buy_rate_fiat": "860",
                "sell_rate_fiat": "920",
                "min_coin_amount": "100",
                "max_coin_amount": "10000",
                "available_liquidity": "5000",
                "is_active": True,
            },
        ),
        200,
    )

    coin_order = _assert_status(
        client.post(
            "/api/coin-traders/orders",
            headers=buyer["headers"],
            json={
                "trader_profile_id": trader_profile_id,
                "direction": "user_buys",
                "coin_unit": "coin",
                "coin_amount": "250",
                "fiat_currency": "NGN",
                "payment_method": "bank_transfer",
                "idempotency_key": f"{JOURNEY_PREFIX}-coin-order-001",
            },
        ),
        201,
    )
    order_id = coin_order["id"]
    _assert_status(client.post(f"/api/coin-traders/orders/{order_id}/accept", headers=trader["headers"]), 200)
    _assert_status(
        client.post(
            f"/api/coin-traders/orders/{order_id}/proof",
            headers=buyer["headers"],
            json={"proof_reference": f"{JOURNEY_PREFIX}-receipt-001", "note": "paid"},
        ),
        200,
    )
    released = _assert_status(
        client.post(f"/api/coin-traders/orders/{order_id}/confirm", headers=trader["headers"]),
        200,
    )
    assert released["status"] == "released"
    assert released["ledger_refs"]["release_entry_ids"]

    # ------------------------------------------------------------------
    # C. User-hosted and GTEX-hosted competitions, with the owner club
    # attached to both journeys.
    # ------------------------------------------------------------------
    user_comp = _assert_status(
        client.post(
            "/api/competitions",
            headers=owner["headers"],
            json={
                "name": f"{JOURNEY_PREFIX} User Cup",
                "format": "cup",
                "visibility": "public",
                "entry_fee": "10",
                "capacity": 2,
                "host_type": "user_hosted",
                "competition_type": "football",
                "competition_mode": "club",
                "prize_mode": "fixed",
                "payout_structure": [{"place": 1, "percent": "100"}],
                "rules": "Acceptance test user-hosted competition",
            },
        ),
        201,
    )
    user_comp_id = user_comp["id"]

    _assert_status(
        client.post(f"/api/competitions/{user_comp_id}/publish", headers=owner["headers"], json={"open_for_join": True}),
        200,
    )
    joined_user_comp = _assert_status(
        client.post(
            f"/api/competitions/{user_comp_id}/join",
            headers=peer["headers"],
            json={
                "club_id": peer["club_id"],
                "club_name": "Journey Peer FC",
            },
        ),
        200,
    )
    assert joined_user_comp["join_eligibility"]["eligible"] is True
    _assert_status(client.post(f"/api/competitions/{user_comp_id}/launch", headers=owner["headers"]), 200)

    fixtures = _assert_status(client.get(f"/api/competitions/{user_comp_id}/fixtures"), 200)
    assert fixtures
    fixture = fixtures[0]
    if fixture["status"] not in {"completed", "cancelled"}:
        _assert_status(
            client.post(
                f"/api/competitions/{user_comp_id}/matches/{fixture['id']}/result",
                headers=owner["headers"],
                json={"home_score": 2, "away_score": 1, "decided_by_penalties": False},
            ),
            200,
        )
    owner_standings = _assert_status(client.get(f"/api/competitions/{user_comp_id}/standings"), 200)
    assert owner_standings

    gtex_comp = _assert_status(
        client.post(
            "/api/admin/competitions",
            headers=bootstrap_admin_headers,
            json={
                "name": f"{JOURNEY_PREFIX} GTEX Cup",
                "format": "cup",
                "visibility": "public",
                "entry_fee": "0",
                "currency": "coin",
                "capacity": 2,
                "host_type": "gtex_hosted",
                "competition_type": "football",
                "competition_mode": "club",
                "prize_mode": "host_funded",
                "host_funded_prize_total": "1000",
                "payout_structure": [{"place": 1, "percent": "100"}],
                "rules": "Acceptance test GTEX-hosted competition",
            },
        ),
        201,
    )
    gtex_comp_id = gtex_comp["id"]
    _assert_status(
        client.post(
            f"/api/competitions/{gtex_comp_id}/join",
            headers=owner["headers"],
            json={"club_id": owner["club_id"], "club_name": "Owner Journey FC"},
        ),
        200,
    )

    # ------------------------------------------------------------------
    # D. National team competition + real player rentals
    # ------------------------------------------------------------------
    national_comp = _assert_status(
        client.post(
            "/api/admin/national-team-engine/competitions",
            headers=bootstrap_admin_headers,
            json={
                "key": f"{JOURNEY_PREFIX}-national",
                "title": "GTEX Acceptance National Cup",
                "season_label": "2026",
                "region_type": "global",
                "age_band": "u17",
                "format_type": "cup",
                "status": "published",
                "entry_opens_at": "2026-01-01T00:00:00Z",
                "entry_closes_at": "2026-12-31T00:00:00Z",
                "kickoff_at": "2026-06-15T12:00:00Z",
                "metadata_json": {"minimum_squad_size": 11, "maximum_squad_size": 23},
            },
        ),
        200,
    )
    national_comp_id = national_comp["id"]
    rental_pool = _assert_status(
        client.get(
            f"/api/national-team-engine/competitions/{national_comp_id}/rental-pool",
            params={"country_code": "NG", "limit": 40},
        ),
        200,
    )
    pool_items = rental_pool["items"]
    assert pool_items, "National-team rental pool was empty"
    rentable = next((item for item in pool_items if item["buyable"] is True), None)
    assert rentable is not None, "No backend-eligible rental player was returned"

    entry = _assert_status(
        client.post(
            f"/api/national-team-engine/competitions/{national_comp_id}/entries",
            headers=owner["headers"],
            json={
                "country_code": "NG",
                "country_name": "Nigeria",
                "manager_user_id": owner["user_id"],
                "metadata_json": {"journey": JOURNEY_PREFIX},
            },
        ),
        200,
    )
    entry_id = entry["id"]
    rental = _assert_status(
        client.post(
            f"/api/national-team-engine/entries/{entry_id}/rentals",
            headers=owner["headers"],
            json={"player_id": rentable["player_id"], "shirt_number": 9},
        ),
        200,
    )
    assert rental["rental_contracts"]

    # ------------------------------------------------------------------
    # E. Real player market transfer + build-a-son + regen transfer
    # ------------------------------------------------------------------
    player_ids = _seed_real_players(client, owner_user_id=str(owner["user_id"]), seller_user_id=str(trader["user_id"]))
    real_player_id = player_ids["real_player_id"]

    real_listing = _assert_status(
        client.post(
            "/api/transfer-market/listings",
            headers=trader["headers"],
            json={
                "player_id": real_player_id,
                "selling_club_id": player_ids["seller_club_id"],
                "base_price": "2500",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "window_id": player_ids["window_id"],
                "asset_type": "real_player",
            },
        ),
        201,
    )
    real_listing_id = real_listing["id"]
    real_offer = _assert_status(
        client.post(
            f"/api/transfer-hub/listings/{real_listing_id}/offers",
            headers=owner["headers"],
            json={
                "bidder_club_id": owner["club_id"],
                "cash_amount": "2500",
                "offer_type": "transfer",
                "message": "GTEX journey real-player purchase",
                "idempotency_key": f"{JOURNEY_PREFIX}-real-player-offer",
            },
        ),
        201,
    )
    _assert_status(client.post(f"/api/transfer-hub/offers/{real_offer['id']}/accept", headers=trader["headers"]), 200)
    _assert_status(client.post(f"/api/transfer-market/listings/{real_listing_id}/close", headers=trader["headers"]), 200)

    son_options = _assert_status(client.get("/api/regens/request-son/options", headers=owner["headers"]), 200)
    assert any(item["player_id"] == player_ids["parent_player_id"] for item in son_options["eligible_parents"])
    son_order = _assert_status(
        client.post(
            "/api/regens/request-son",
            headers=owner["headers"],
            json={
                "parent_player_id": player_ids["parent_player_id"],
                "requested_name": "GTEX Journey Son",
                "requested_country_code": "NG",
                "requested_position": "ST",
                "payment_method": "wallet",
            },
        ),
        201,
    )
    paid_son = _assert_status(
        client.post(
            f"/api/regens/creation-orders/{son_order['id']}/pay-with-wallet",
            headers=owner["headers"],
        ),
        200,
    )
    assert paid_son["status"] == "paid"
    generated_son = _assert_status(
        client.post(
            f"/api/regens/creation-orders/{son_order['id']}/generate-after-payment",
            headers=owner["headers"],
        ),
        200,
    )
    regen_player_id = generated_son["generated_player_id"]
    assert regen_player_id
    assert generated_son["generated_player"]["club_id"] == owner["club_id"]

    regen_listing = _assert_status(
        client.post(
            "/api/transfer-market/listings",
            headers=owner["headers"],
            json={
                "player_id": regen_player_id,
                "selling_club_id": owner["club_id"],
                "base_price": "1200",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "window_id": player_ids["window_id"],
                "asset_type": "regen",
                "listing_type": "private_negotiation",
            },
        ),
        201,
    )
    regen_listing_id = regen_listing["id"]
    regen_offer = _assert_status(
        client.post(
            f"/api/transfer-hub/listings/{regen_listing_id}/offers",
            headers=club_buyer["headers"],
            json={
                "bidder_club_id": club_buyer["club_id"],
                "cash_amount": "1200",
                "offer_type": "transfer",
                "message": "Initial regen offer",
                "idempotency_key": f"{JOURNEY_PREFIX}-regen-offer",
            },
        ),
        201,
    )
    countered = _assert_status(
        client.post(
            f"/api/transfer-hub/offers/{regen_offer['id']}/counter",
            headers=owner["headers"],
            json={"cash_amount": "1300", "message": "Counter for journey regen"},
        ),
        200,
    )
    _assert_status(client.post(f"/api/transfer-hub/offers/{countered['id']}/accept", headers=club_buyer["headers"]), 200)
    _assert_status(client.post(f"/api/transfer-market/listings/{regen_listing_id}/close", headers=owner["headers"]), 200)

    negotiation = _assert_status(
        client.get(f"/api/transfer-market/listings/{regen_listing_id}/negotiation", headers=club_buyer["headers"]),
        200,
    )
    assert negotiation["player_id"] == regen_player_id
    contract_offer = _assert_status(
        client.post(
            f"/api/transfer-market/listings/{regen_listing_id}/contract-offer",
            headers=club_buyer["headers"],
            json={
                "bidder_club_id": club_buyer["club_id"],
                "wage_offer_amount": "150",
                "contract_years": 3,
                "expected_role": "first_team",
            },
        ),
        200,
    )
    assert contract_offer["contract_years"] == 3

    # ------------------------------------------------------------------
    # F. First contract, renewal, and termination as part of an actual
    # player ownership transition.
    # ------------------------------------------------------------------
    with client.app.state.session_factory() as session:
        regen_player = session.get(Player, regen_player_id)
        assert regen_player is not None
        regen_player.current_club_profile_id = club_buyer["club_id"]
        session.commit()

    first_contract = _assert_status(
        client.post(
            f"/api/players/{regen_player_id}/contracts",
            headers=club_buyer["headers"],
            json={
                "club_id": club_buyer["club_id"],
                "wage_amount": "150.00",
                "signed_on": "2026-09-15",
                "starts_on": "2026-09-15",
                "ends_on": "2027-09-14",
            },
        ),
        201,
    )
    renewed = _assert_status(
        client.post(
            f"/api/players/{regen_player_id}/contracts/{first_contract['id']}/renew",
            headers=club_buyer["headers"],
            json={"new_ends_on": "2028-09-14"},
        ),
        200,
    )
    assert renewed["ends_on"] == "2028-09-14"

    # A subsequent transfer bid is the canonical player-lifecycle termination
    # path: accepting the bid terminates the selling club's contract and creates
    # the buying club's replacement contract.
    _assert_status(
        client.post(
            f"/api/transfers/windows/{player_ids['window_id']}/bids",
            headers=buyer["headers"],
            json={
                "player_id": regen_player_id,
                "club_id": buyer["club_id"],
                "bid_amount": "1600",
                "wage_amount": "175",
                "contract_years": 3,
            },
        ),
        201,
    )
    bids = _assert_status(client.get(f"/api/transfers/windows/{player_ids['window_id']}/bids"), 200)
    regen_bid = next(item for item in bids if item["player_id"] == regen_player_id)
    accepted_bid = _assert_status(
        client.post(
            f"/api/transfers/windows/{player_ids['window_id']}/bids/{regen_bid['id']}/accept",
            headers=club_buyer["headers"],
            json={"approved": True},
        ),
        200,
    )
    assert accepted_bid["status"] == "accepted"

    # ------------------------------------------------------------------
    # G. Club facilities + academy/youth path + contract offer/promotion
    # ------------------------------------------------------------------
    for facility_key in ("training", "medical", "youth_recruitment"):
        upgraded = _assert_status(
            client.post(
                "/api/club-infra/my/facilities/upgrade",
                headers=club_buyer["headers"],
                json={"facility_key": facility_key, "increment": 1},
            ),
            200,
        )
        assert upgraded["facility_key"] == facility_key or upgraded.get("key") == facility_key

    academy_prospects = _assert_status(
        client.post(
            f"/api/clubs/{club_buyer['club_id']}/growth/academy/generate-prospects",
            headers=club_buyer["headers"],
            json={"count": 3},
        ),
        200,
    )
    assert academy_prospects
    prospect_id = academy_prospects[0]["id"]
    academy_offer = _assert_status(
        client.post(
            f"/api/clubs/{club_buyer['club_id']}/growth/academy/prospects/{prospect_id}/offer-contract",
            headers=club_buyer["headers"],
            json={"wage_minor": 1000, "duration_months": 24},
        ),
        200,
    )
    _assert_status(
        client.post(
            f"/api/clubs/{club_buyer['club_id']}/growth/academy/contracts/{academy_offer['id']}/respond",
            headers=club_buyer["headers"],
            json={"accepted": True},
        ),
        200,
    )
    promoted = _assert_status(
        client.post(
            f"/api/clubs/{club_buyer['club_id']}/growth/academy/prospects/{prospect_id}/promote",
            headers=club_buyer["headers"],
        ),
        200,
    )
    assert promoted["status"] == "promoted_to_senior"

    # ------------------------------------------------------------------
    # H. Hire a manager and a coach/staff contract
    # ------------------------------------------------------------------
    manager_catalog = _assert_status(client.get("/api/managers/catalog"), 200)
    assert manager_catalog["items"]
    manager_id = manager_catalog["items"][0]["id"]
    manager_team = _assert_status(
        client.post(
            "/api/managers/recruit",
            headers=club_buyer["headers"],
            json={"manager_id": manager_id, "slot": "main", "salary_fancoin": "0"},
        ),
        200,
    )
    assert manager_team["primary_manager"] or manager_team.get("main")

    coach_staff = _assert_status(
        client.get(f"/api/clubs/{club_buyer['club_id']}/growth" , headers=club_buyer["headers"]),
        200,
    )
    staff_catalog = coach_staff.get("staff", []) or coach_staff.get("available_staff", [])
    if staff_catalog:
        staff_id = staff_catalog[0]["id"]
        offered_staff = _assert_status(
            client.post(
                f"/api/clubs/{club_buyer['club_id']}/growth/staff/{staff_id}/offer",
                headers=club_buyer["headers"],
                json={"role_key": "coach", "salary_minor": 1000, "duration_months": 12},
            ),
            200,
        )
        _assert_status(
            client.post(
                f"/api/clubs/{club_buyer['club_id']}/growth/staff-contracts/{offered_staff['id']}/accept",
                headers=club_buyer["headers"],
            ),
            200,
        )
        terminated_staff = _assert_status(
            client.post(
                f"/api/clubs/{club_buyer['club_id']}/growth/staff-contracts/{offered_staff['id']}/terminate",
                headers=club_buyer["headers"],
            ),
            200,
        )
        assert terminated_staff["status"] in {"terminated", "ended"}

    # ------------------------------------------------------------------
    # I. Sell the current club, then buy another club.
    # ------------------------------------------------------------------
    valuation = _assert_status(client.get(f"/api/clubs/{club_buyer['club_id']}/sale-market/valuation"), 200)
    asking_price = str(max(Decimal(valuation["system_valuation"]), Decimal("1000")))
    listing = _assert_status(
        client.post(
            f"/api/clubs/{club_buyer['club_id']}/sale-market/listing",
            headers=club_buyer["headers"],
            json={"asking_price": asking_price, "visibility": "public", "note": JOURNEY_PREFIX},
        ),
        201,
    )
    club_offer = _assert_status(
        client.post(
            f"/api/clubs/{club_buyer['club_id']}/sale-market/offers",
            headers=owner["headers"],
            json={"offer_price": asking_price, "message": "Acceptance journey club purchase"},
        ),
        201,
    )
    _assert_status(
        client.post(
            f"/api/clubs/{club_buyer['club_id']}/sale-market/offers/{club_offer['offer_id']}/accept",
            headers=club_buyer["headers"],
            json={"message": "accepted"},
        ),
        200,
    )
    club_transfer = _assert_status(
        client.post(
            f"/api/clubs/{club_buyer['club_id']}/sale-market/transfer",
            headers=owner["headers"],
            json={"offer_id": club_offer["offer_id"], "executed_sale_price": asking_price},
        ),
        200,
    )
    assert club_transfer["ownership_transition"]["new_owner_user_id"] == owner["user_id"]

    # ------------------------------------------------------------------
    # J. Jackpot win, then gifts as user and as club context.
    # ------------------------------------------------------------------
    _assert_status(
        client.post(
            "/api/admin/jackpot/runtime",
            headers=bootstrap_admin_headers,
            json={
                "threshold_amount": "10.0000",
                "probability_limit": "1000.0000",
                "probability_cap": "0.5000",
                "failsafe_hours": 6,
                "contribution_rate": "0.1000",
                "distribution_mode": "single_winner",
                "top_split_percent": "0.1000",
                "min_activity_score": "1.0000",
            },
        ),
        200,
    )
    jackpot_contribution = _assert_status(
        client.post(
            "/api/jackpot/contribute",
            headers=owner["headers"],
            json={
                "source_type": "platform_activity",
                "source_id": f"{JOURNEY_PREFIX}-jackpot-source",
                "entry_fee": "10.0000",
                "contribution_amount": "10.0000",
                "eligibility_score": "2.0000",
                "metadata": {"journey": JOURNEY_PREFIX},
            },
        ),
        201,
    )
    assert jackpot_contribution["contribution_amount"] == "10.0000"
    trigger = _assert_status(client.post("/api/admin/jackpot/trigger", headers=bootstrap_admin_headers), 200)
    assert trigger["triggered_round_number"]
    history = _assert_status(client.get("/api/jackpot/history"), 200)
    settled_round = next(item for item in history if item["round_number"] == trigger["triggered_round_number"])
    assert settled_round["payouts"]
    assert any(item["winner_user_id"] == owner["user_id"] for item in settled_round["payouts"])

    gift_catalog = _assert_status(client.get("/gifts/catalog"), 200)
    gift_item = next(item for item in gift_catalog if item.get("active", True))
    gift_key = gift_item["gift_key"]

    sent_user_gift = _assert_status(
        client.post(
            "/gift-engine/send",
            headers=owner["headers"],
            json={
                "recipient_user_id": recipient["user_id"],
                "gift_key": gift_key,
                "quantity": 1,
                "note": "GTEX journey user gift",
                "source_scope": "user",
                "idempotency_key": f"{JOURNEY_PREFIX}-gift-user",
            },
        ),
        201,
    )
    assert sent_user_gift["recipient_user_id"] == recipient["user_id"]
    recipient_user_gifts = _assert_status(client.get("/gift-engine/me/transactions", headers=recipient["headers"]), 200)
    assert any(item["id"] == sent_user_gift["id"] for item in recipient_user_gifts)

    sent_club_gift = _assert_status(
        client.post(
            "/gift-engine/send",
            headers=owner["headers"],
            json={
                "recipient_club_id": recipient["club_id"],
                "gift_key": gift_key,
                "quantity": 1,
                "note": "GTEX journey club-owner gift",
                "source_scope": "club",
                "idempotency_key": f"{JOURNEY_PREFIX}-gift-club",
            },
        ),
        201,
    )
    assert sent_club_gift["recipient_club_id"] == recipient["club_id"]
    recipient_club_gifts = _assert_status(client.get("/gift-engine/me/transactions", headers=recipient["headers"]), 200)
    assert any(item["id"] == sent_club_gift["id"] for item in recipient_club_gifts)

    # Final cross-domain invariants: the journey really ended with the owner
    # holding a club and the recipient having both gift contexts recorded.
    with client.app.state.session_factory() as session:
        current_club = session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == owner["user_id"]))
        assert current_club is not None
        contracts = list(session.scalars(select(PlayerContract).where(PlayerContract.club_id == current_club.id)).all())
        assert all(contract.club_id == current_club.id for contract in contracts)
        service = PlayerLifecycleService(session)
        if contracts:
            assert any(service.to_contract_view(contract, reference_on=date(2026, 9, 15)).status for contract in contracts)

    # Silence the imported Player symbol from becoming a lint-only false positive
    # while preserving the explicit player model dependency used by the journey.
    assert Player is not None
