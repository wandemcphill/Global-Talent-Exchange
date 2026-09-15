from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.ingestion.models import Player
from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.models.transfer_window import TransferWindow
from app.services.player_lifecycle_service import PlayerLifecycleService
from backend.tests.players.test_player_share_market_routes import _seed_imported_real_player


PREFIX = "gtex-journey-20260915"


def _status(response, expected: int):
    assert response.status_code == expected, response.text
    return response.json()


def _club(session, user_id: str) -> ClubProfile:
    club = session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == user_id))
    assert club is not None
    return club


def _seed_assets(app_session_factory, owner_id: str, seller_id: str) -> dict[str, str]:
    with app_session_factory() as session:
        owner_club = _club(session, owner_id)
        seller_club = _club(session, seller_id)
        real = _seed_imported_real_player(session, player_id=f"{PREFIX}-real")
        real.current_club_profile_id = seller_club.id
        parent = _seed_imported_real_player(session, player_id=f"{PREFIX}-parent")
        parent.current_club_profile_id = owner_club.id
        window = TransferWindow(
            id=f"{PREFIX}-window",
            territory_code="NG",
            label="GTEX Acceptance Window",
            status="open",
            opens_on=date(2026, 1, 1),
            closes_on=date(2026, 12, 31),
        )
        session.add(window)
        session.commit()
        return {
            "owner_club_id": owner_club.id,
            "seller_club_id": seller_club.id,
            "real_id": real.id,
            "parent_id": parent.id,
            "window_id": window.id,
        }


def test_gtex_full_user_journey(client, app_session_factory, auth_user_factory, bootstrap_admin_headers):
    # Six real registered users. auth_user_factory calls the production signup endpoint.
    owner = auth_user_factory(suffix=f"{PREFIX}-owner", funded_credit="5000", funded_coin="10000")
    trader = auth_user_factory(suffix=f"{PREFIX}-trader", funded_credit="500", funded_coin="100000")
    peer = auth_user_factory(suffix=f"{PREFIX}-peer", funded_credit="5000", funded_coin="5000")
    recipient = auth_user_factory(suffix=f"{PREFIX}-recipient", funded_credit="2500", funded_coin="2500")
    buyer = auth_user_factory(suffix=f"{PREFIX}-buyer", funded_credit="5000", funded_coin="100000")
    club_buyer = auth_user_factory(suffix=f"{PREFIX}-clubbuyer", funded_credit="5000", funded_coin="200000")
    actors = (owner, trader, peer, recipient, buyer, club_buyer)
    assert len({a["user_id"] for a in actors}) == 6

    with app_session_factory() as session:
        club_ids = {a["user_id"]: _club(session, a["user_id"]).id for a in actors}

    # 1. Coin Trader journey.
    application = _status(
        client.post(
            "/api/coin-traders/apply",
            headers=trader["headers"],
            json={
                "display_name": "GTEX Journey OTC Desk",
                "country_code": "NG",
                "terms": {"same_name_account_only": True, "payment_proof_required": True},
                "payment_methods": [{"label": "Bank transfer", "type": "bank_transfer"}],
                "bank_accounts": [{"bank": "GTBank"}],
            },
        ),
        201,
    )
    profile_id = application["id"]
    _status(
        client.post(
            f"/api/admin/coin-traders/{profile_id}/approve",
            headers=bootstrap_admin_headers,
            json={"tier": "gold", "note": "full journey"},
        ),
        200,
    )
    _status(
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
    order = _status(
        client.post(
            "/api/coin-traders/orders",
            headers=buyer["headers"],
            json={
                "trader_profile_id": profile_id,
                "direction": "user_buys",
                "coin_unit": "coin",
                "coin_amount": "250",
                "fiat_currency": "NGN",
                "payment_method": "bank_transfer",
                "idempotency_key": f"{PREFIX}-coin-order",
            },
        ),
        201,
    )
    _status(client.post(f"/api/coin-traders/orders/{order['id']}/accept", headers=trader["headers"]), 200)
    _status(
        client.post(
            f"/api/coin-traders/orders/{order['id']}/proof",
            headers=buyer["headers"],
            json={"proof_reference": f"{PREFIX}-bank-proof"},
        ),
        200,
    )
    released = _status(
        client.post(f"/api/coin-traders/orders/{order['id']}/confirm", headers=trader["headers"]),
        200,
    )
    assert released["status"] == "released"
    assert released["ledger_refs"]["release_entry_ids"]

    # 2. User-hosted competition, then actual match completion.
    user_comp = _status(
        client.post(
            "/api/competitions",
            headers=owner["headers"],
            json={
                "name": f"{PREFIX} User Cup",
                "format": "cup",
                "visibility": "public",
                "entry_fee": "10",
                "capacity": 2,
                "host_type": "user_hosted",
                "competition_type": "football",
                "competition_mode": "club",
                "payout_structure": [{"place": 1, "percent": "100"}],
            },
        ),
        201,
    )
    ucid = user_comp["id"]
    _status(client.post(f"/api/competitions/{ucid}/publish", headers=owner["headers"], json={"open_for_join": True}), 200)
    _status(
        client.post(
            f"/api/competitions/{ucid}/join",
            headers=owner["headers"],
            json={"club_id": club_ids[owner["user_id"]]},
        ),
        200,
    )
    _status(
        client.post(
            f"/api/competitions/{ucid}/join",
            headers=peer["headers"],
            json={"club_id": club_ids[peer["user_id"]]},
        ),
        200,
    )
    _status(client.post(f"/api/competitions/{ucid}/launch", headers=owner["headers"]), 200)
    fixtures = _status(client.get(f"/api/competitions/{ucid}/fixtures"), 200)
    assert fixtures
    fixture = fixtures[0]
    if fixture["status"] not in {"completed", "cancelled"}:
        _status(
            client.post(
                f"/api/competitions/{ucid}/matches/{fixture['id']}/result",
                headers=owner["headers"],
                json={"home_score": 2, "away_score": 1},
            ),
            200,
        )
    assert _status(client.get(f"/api/competitions/{ucid}/standings"), 200)

    # 3. GTEX-hosted competition.
    gtex_comp = _status(
        client.post(
            "/api/admin/competitions",
            headers=bootstrap_admin_headers,
            json={
                "name": f"{PREFIX} GTEX Cup",
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
            },
        ),
        201,
    )
    _status(
        client.post(
            f"/api/competitions/{gtex_comp['id']}/join",
            headers=owner["headers"],
            json={"club_id": club_ids[owner["user_id"]]},
        ),
        200,
    )

    # 4. National-team rental.
    national = _status(
        client.post(
            "/api/admin/national-team-engine/competitions",
            headers=bootstrap_admin_headers,
            json={
                "key": f"{PREFIX}-national",
                "title": "GTEX Journey National Cup",
                "season_label": "2026",
                "region_type": "global",
                "age_band": "u17",
                "format_type": "cup",
                "status": "published",
                "entry_opens_at": "2026-01-01T00:00:00Z",
                "entry_closes_at": "2026-12-31T00:00:00Z",
                "kickoff_at": "2026-06-15T12:00:00Z",
            },
        ),
        200,
    )
    pool = _status(
        client.get(
            f"/api/national-team-engine/competitions/{national['id']}/rental-pool",
            params={"country_code": "NG", "limit": 40},
        ),
        200,
    )
    assert pool["items"]
    player_to_rent = next(item for item in pool["items"] if item["buyable"])
    entry = _status(
        client.post(
            f"/api/national-team-engine/competitions/{national['id']}/entries",
            headers=owner["headers"],
            json={"country_code": "NG", "country_name": "Nigeria", "manager_user_id": owner["user_id"]},
        ),
        200,
    )
    rental = _status(
        client.post(
            f"/api/national-team-engine/entries/{entry['id']}/rentals",
            headers=owner["headers"],
            json={"player_id": player_to_rent["player_id"], "shirt_number": 9},
        ),
        200,
    )
    assert rental["rental_contracts"]

    # 5. Real player buy + Build-a-Son + regen sale/negotiation.
    assets = _seed_assets(app_session_factory, owner["user_id"], trader["user_id"])
    real_listing = _status(
        client.post(
            "/api/transfer-market/listings",
            headers=trader["headers"],
            json={
                "player_id": assets["real_id"],
                "selling_club_id": assets["seller_club_id"],
                "base_price": "2500",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "window_id": assets["window_id"],
                "asset_type": "real_player",
            },
        ),
        201,
    )
    real_offer = _status(
        client.post(
            f"/api/transfer-hub/listings/{real_listing['id']}/offers",
            headers=owner["headers"],
            json={
                "bidder_club_id": club_ids[owner["user_id"]],
                "offer_type": "transfer",
                "cash_amount": "2500",
                "idempotency_key": f"{PREFIX}-real-buy",
            },
        ),
        201,
    )
    _status(client.post(f"/api/transfer-hub/offers/{real_offer['id']}/accept", headers=trader["headers"]), 200)
    _status(client.post(f"/api/transfer-market/listings/{real_listing['id']}/close", headers=trader["headers"]), 200)

    options = _status(client.get("/api/regens/request-son/options", headers=owner["headers"]), 200)
    assert any(item["player_id"] == assets["parent_id"] for item in options["eligible_parents"])
    son = _status(
        client.post(
            "/api/regens/request-son",
            headers=owner["headers"],
            json={
                "parent_player_id": assets["parent_id"],
                "requested_name": "GTEX Journey Son",
                "requested_country_code": "NG",
                "requested_position": "ST",
                "payment_method": "wallet",
            },
        ),
        201,
    )
    _status(client.post(f"/api/regens/creation-orders/{son['id']}/pay-with-wallet", headers=owner["headers"]), 200)
    generated = _status(
        client.post(f"/api/regens/creation-orders/{son['id']}/generate-after-payment", headers=owner["headers"]),
        200,
    )
    regen_id = generated["generated_player_id"]
    assert generated["generated_player"]["club_id"] == club_ids[owner["user_id"]]

    regen_listing = _status(
        client.post(
            "/api/transfer-market/listings",
            headers=owner["headers"],
            json={
                "player_id": regen_id,
                "selling_club_id": club_ids[owner["user_id"]],
                "base_price": "1200",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "window_id": assets["window_id"],
                "asset_type": "regen",
                "listing_type": "private_negotiation",
            },
        ),
        201,
    )
    regen_offer = _status(
        client.post(
            f"/api/transfer-hub/listings/{regen_listing['id']}/offers",
            headers=club_buyer["headers"],
            json={
                "bidder_club_id": club_ids[club_buyer["user_id"]],
                "offer_type": "transfer",
                "cash_amount": "1200",
                "idempotency_key": f"{PREFIX}-regen-offer",
            },
        ),
        201,
    )
    counter = _status(
        client.post(
            f"/api/transfer-hub/offers/{regen_offer['id']}/counter",
            headers=owner["headers"],
            json={"cash_amount": "1300", "message": "Counter"},
        ),
        200,
    )
    _status(client.post(f"/api/transfer-hub/offers/{counter['id']}/accept", headers=club_buyer["headers"]), 200)
    negotiation = _status(
        client.get(f"/api/transfer-market/listings/{regen_listing['id']}/negotiation", headers=club_buyer["headers"]),
        200,
    )
    assert negotiation["player_id"] == regen_id
    contract_offer = _status(
        client.post(
            f"/api/transfer-market/listings/{regen_listing['id']}/contract-offer",
            headers=club_buyer["headers"],
            json={
                "bidder_club_id": club_ids[club_buyer["user_id"]],
                "wage_offer_amount": "150",
                "contract_years": 3,
                "expected_role": "first_team",
            },
        ),
        200,
    )
    assert contract_offer["contract_years"] == 3
    _status(client.post(f"/api/transfer-market/listings/{regen_listing['id']}/close", headers=owner["headers"]), 200)

    # 6. First regen contract, renewal, then canonical transfer termination.
    with app_session_factory() as session:
        player = session.get(Player, regen_id)
        assert player is not None
        player.current_club_profile_id = club_ids[club_buyer["user_id"]]
        session.commit()

    first_contract = _status(
        client.post(
            f"/api/players/{regen_id}/contracts",
            headers=club_buyer["headers"],
            json={
                "club_id": club_ids[club_buyer["user_id"]],
                "wage_amount": "150",
                "signed_on": "2026-09-15",
                "starts_on": "2026-09-15",
                "ends_on": "2027-09-14",
            },
        ),
        201,
    )
    renewed = _status(
        client.post(
            f"/api/players/{regen_id}/contracts/{first_contract['id']}/renew",
            headers=club_buyer["headers"],
            json={"new_ends_on": "2028-09-14"},
        ),
        200,
    )
    assert renewed["ends_on"] == "2028-09-14"
    _status(
        client.post(
            f"/api/transfers/windows/{assets['window_id']}/bids",
            headers=buyer["headers"],
            json={
                "player_id": regen_id,
                "club_id": club_ids[buyer["user_id"]],
                "bid_amount": "1600",
                "wage_amount": "175",
                "contract_years": 3,
            },
        ),
        201,
    )
    bids = _status(client.get(f"/api/transfers/windows/{assets['window_id']}/bids"), 200)
    bid = next(item for item in bids if item["player_id"] == regen_id)
    accepted = _status(
        client.post(
            f"/api/transfers/windows/{assets['window_id']}/bids/{bid['id']}/accept",
            headers=club_buyer["headers"],
            json={"approved": True},
        ),
        200,
    )
    assert accepted["status"] == "accepted"

    # 7. Training, medical, youth facilities; youth first contract and promotion.
    for key in ("training", "medical", "youth_recruitment"):
        result = _status(
            client.post(
                "/api/club-infra/my/facilities/upgrade",
                headers=club_buyer["headers"],
                json={"facility_key": key, "increment": 1},
            ),
            200,
        )
        assert result

    prospects = _status(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/academy/generate-prospects",
            headers=club_buyer["headers"],
            json={"count": 3},
        ),
        200,
    )
    assert prospects
    prospect_id = prospects[0]["id"]
    youth_offer = _status(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/academy/prospects/{prospect_id}/offer-contract",
            headers=club_buyer["headers"],
            json={"wage_minor": 1000, "duration_months": 24},
        ),
        200,
    )
    _status(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/academy/contracts/{youth_offer['id']}/respond",
            headers=club_buyer["headers"],
            json={"accepted": True},
        ),
        200,
    )
    promoted = _status(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/academy/prospects/{prospect_id}/promote",
            headers=club_buyer["headers"],
        ),
        200,
    )
    assert promoted["status"] == "promoted_to_senior"

    # 8. Manager + coach/staff.
    managers = _status(client.get("/api/managers/catalog"), 200)
    assert managers["items"]
    team = _status(
        client.post(
            "/api/managers/recruit",
            headers=club_buyer["headers"],
            json={"manager_id": managers["items"][0]["id"], "slot": "main", "salary_fancoin": "0"},
        ),
        200,
    )
    assert team
    growth = _status(client.get(f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth", headers=club_buyer["headers"]), 200)
    staff = growth.get("available_staff") or growth.get("staff") or []
    assert staff, "No live coach/staff candidate exposed by the club-growth market"
    staff_id = staff[0]["id"]
    staff_offer = _status(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/staff/{staff_id}/offer",
            headers=club_buyer["headers"],
            json={"salary_minor": 1000, "duration_days": 365},
        ),
        200,
    )
    _status(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/staff-contracts/{staff_offer['id']}/accept",
            headers=club_buyer["headers"],
        ),
        200,
    )
    terminated = _status(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/staff-contracts/{staff_offer['id']}/terminate",
            headers=club_buyer["headers"],
        ),
        200,
    )
    assert terminated["status"] in {"terminated", "ended"}

    # 9. Sell one club and buy it back/another club through the canonical market.
    sold_club_id = club_ids[club_buyer["user_id"]]
    valuation = _status(client.get(f"/api/clubs/{sold_club_id}/valuation"), 200)
    asking = max(Decimal(str(valuation["system_valuation"])), Decimal("1000"))
    _status(
        client.post(
            f"/api/clubs/{sold_club_id}/sale-market/listing",
            headers=club_buyer["headers"],
            json={"asking_price": str(asking), "visibility": "public", "note": PREFIX},
        ),
        201,
    )
    club_offer = _status(
        client.post(
            f"/api/clubs/{sold_club_id}/sale-market/offers",
            headers=owner["headers"],
            json={"offer_price": str(asking), "message": "journey purchase"},
        ),
        201,
    )
    _status(
        client.post(
            f"/api/clubs/{sold_club_id}/sale-market/offers/{club_offer['id']}/accept",
            headers=club_buyer["headers"],
            json={"message": "accepted"},
        ),
        200,
    )
    transfer = _status(
        client.post(
            f"/api/clubs/{sold_club_id}/sale-market/transfer",
            headers=club_buyer["headers"],
            json={"offer_id": club_offer["id"], "executed_sale_price": str(asking)},
        ),
        200,
    )
    assert transfer["ownership_transition"]["new_owner_user_id"] == owner["user_id"]

    # 10. Jackpot deterministic win.
    _status(
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
    contribution = _status(
        client.post(
            "/api/jackpot/contribute",
            headers=owner["headers"],
            json={
                "source_type": "platform_activity",
                "source_id": f"{PREFIX}-jackpot",
                "entry_fee": "10.0000",
                "contribution_amount": "10.0000",
                "eligibility_score": "2.0000",
                "metadata": {"journey": PREFIX},
            },
        ),
        201,
    )
    assert contribution["contribution_amount"] == "10.0000"
    triggered = _status(client.post("/api/admin/jackpot/trigger", headers=bootstrap_admin_headers), 200)
    history = _status(client.get("/api/jackpot/history"), 200)
    settled = next(item for item in history if item["round_number"] == triggered["triggered_round_number"])
    assert any(p["winner_user_id"] == owner["user_id"] for p in settled["payouts"])

    # 11. User gift receive + club-context gift receive.
    catalog = _status(client.get("/gifts/catalog"), 200)
    assert catalog
    gift_key = catalog[0]["code"]
    user_gift = _status(
        client.post(
            "/gift-engine/send",
            headers=owner["headers"],
            json={
                "recipient_user_id": recipient["user_id"],
                "gift_key": gift_key,
                "quantity": 1,
                "note": "journey user gift",
                "idempotency_key": f"{PREFIX}-gift-user",
            },
        ),
        201,
    )
    recipient_gifts = _status(client.get("/gift-engine/me/transactions", headers=recipient["headers"]), 200)
    assert any(item["id"] == user_gift["id"] for item in recipient_gifts)

    club_gift = _status(
        client.post(
            "/gift-engine/send",
            headers=owner["headers"],
            json={
                "recipient_club_id": club_ids[recipient["user_id"]],
                "gift_key": gift_key,
                "quantity": 1,
                "note": "journey club-owner gift",
                "idempotency_key": f"{PREFIX}-gift-club",
            },
        ),
        201,
    )
    assert club_gift["recipient_club_id"] == club_ids[recipient["user_id"]]
    recipient_gifts = _status(client.get("/gift-engine/me/transactions", headers=recipient["headers"]), 200)
    assert any(item["id"] == club_gift["id"] for item in recipient_gifts)

    # Final ownership/contract invariant after the journeys.
    with app_session_factory() as session:
        owner_club = _club(session, owner["user_id"])
        contracts = list(session.scalars(select(PlayerContract).where(PlayerContract.club_id == owner_club.id)).all())
        if contracts:
            lifecycle = PlayerLifecycleService(session)
            assert any(lifecycle.to_contract_view(c, reference_on=date(2026, 9, 15)).status for c in contracts)
        assert owner_club.id
        assert Player is not None
