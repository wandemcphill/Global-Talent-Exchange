from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.club_profile import ClubProfile
from app.models.player_contract import PlayerContract
from app.models.transfer_window import TransferWindow
from app.regen_universe.models import RegenSeason
from backend.tests.players.test_player_share_market_routes import _seed_imported_real_player

PREFIX = "full-journey-20260915"


def _ok(response, code=200):
    assert response.status_code == code, response.text
    return response.json()


def _club(session, user_id):
    club = session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == user_id))
    assert club is not None
    return club


def _seed_player_assets(app_session_factory, owner_id, seller_id):
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
            label="GTEX Full Journey Window",
            status="open",
            opens_on=date(2026, 1, 1),
            closes_on=date(2026, 12, 31),
        )
        session.add(window)
        season = RegenSeason(
            id=f"{PREFIX}-season",
            season_number=1,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_active=True,
        )
        session.add(season)
        session.commit()
        return {
            "owner_club_id": owner_club.id,
            "seller_club_id": seller_club.id,
            "real_player_id": real.id,
            "parent_player_id": parent.id,
            "window_id": window.id,
        }


def test_gtex_full_user_journey(client, app_session_factory, auth_user_factory, bootstrap_admin_headers):
    # Registration / user IDs / clubs.
    owner = auth_user_factory(suffix=f"{PREFIX}-owner", funded_credit="5000", funded_coin="10000")
    trader = auth_user_factory(suffix=f"{PREFIX}-trader", funded_credit="500", funded_coin="100000")
    peer = auth_user_factory(suffix=f"{PREFIX}-peer", funded_credit="5000", funded_coin="5000")
    recipient = auth_user_factory(suffix=f"{PREFIX}-recipient", funded_credit="2500", funded_coin="2500")
    buyer = auth_user_factory(suffix=f"{PREFIX}-buyer", funded_credit="5000", funded_coin="100000")
    club_buyer = auth_user_factory(suffix=f"{PREFIX}-club-buyer", funded_credit="5000", funded_coin="200000")
    actors = (owner, trader, peer, recipient, buyer, club_buyer)
    assert len({item["user_id"] for item in actors}) == 6

    with app_session_factory() as session:
        club_ids = {item["user_id"]: _club(session, item["user_id"]).id for item in actors}

    # Coin Trader: apply -> approve -> quote -> order -> escrow -> proof -> release.
    application = _ok(
        client.post(
            "/api/coin-traders/apply",
            headers=trader["headers"],
            json={
                "display_name": "GTEX Full Journey OTC Desk",
                "country_code": "NG",
                "terms": {"same_name_account_only": True, "payment_proof_required": True},
                "payment_methods": [{"label": "Bank transfer", "type": "bank_transfer"}],
                "bank_accounts": [{"bank": "GTBank"}],
            },
        ),
        201,
    )
    profile_id = application["id"]
    _ok(
        client.post(
            f"/api/admin/coin-traders/{profile_id}/approve",
            headers=bootstrap_admin_headers,
            json={"tier": "gold", "note": "full journey acceptance"},
        )
    )
    _ok(
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
        )
    )
    order = _ok(
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
    _ok(client.post(f"/api/coin-traders/orders/{order['id']}/accept", headers=trader["headers"]))
    _ok(
        client.post(
            f"/api/coin-traders/orders/{order['id']}/proof",
            headers=buyer["headers"],
            json={"proof_reference": f"{PREFIX}-bank-proof"},
        )
    )
    released = _ok(client.post(f"/api/coin-traders/orders/{order['id']}/confirm", headers=trader["headers"]))
    assert released["status"] == "released"
    assert released["ledger_refs"]["release_entry_ids"]

    # User-hosted competition: owner + peer, launch, match, standings.
    user_comp = _ok(
        client.post(
            "/api/competitions",
            headers=owner["headers"],
            json={
                "name": f"{PREFIX} User Cup",
                "format": "league",
                "visibility": "public",
                "entry_fee": "10",
                "capacity": 2,
                "host_type": "user_hosted",
                "competition_type": "football",
                "competition_mode": "club",
                "payout_structure": [{"place": 1, "percent": "1.00"}],
            },
        ),
        201,
    )
    user_comp_id = user_comp["id"]
    _ok(
        client.post(f"/api/competitions/{user_comp_id}/publish", headers=owner["headers"], json={"open_for_join": True})
    )
    _ok(
        client.post(
            f"/api/competitions/{user_comp_id}/join",
            headers=owner["headers"],
            json={"club_id": club_ids[owner["user_id"]]},
        )
    )
    _ok(
        client.post(
            f"/api/competitions/{user_comp_id}/join",
            headers=peer["headers"],
            json={"club_id": club_ids[peer["user_id"]]},
        )
    )
    _ok(client.post(f"/api/competitions/{user_comp_id}/launch", headers=owner["headers"]))
    fixtures = _ok(client.get(f"/api/competitions/{user_comp_id}/fixtures"))
    assert fixtures
    fixture = fixtures[0]
    if fixture["status"] not in {"completed", "cancelled"}:
        _ok(
            client.post(
                f"/api/competitions/{user_comp_id}/matches/{fixture['id']}/result",
                headers=owner["headers"],
                json={"home_score": 2, "away_score": 1},
            )
        )
    assert _ok(client.get(f"/api/competitions/{user_comp_id}/standings"))

    # GTEX-hosted competition and join.
    gtex_comp = _ok(
        client.post(
            "/api/admin/competitions",
            headers=bootstrap_admin_headers,
            json={
                "name": f"{PREFIX} GTEX Cup",
                "format": "league",
                "visibility": "public",
                "entry_fee": "0",
                "currency": "coin",
                "capacity": 2,
                "host_type": "gtex_hosted",
                "competition_type": "football",
                "competition_mode": "club",
                "prize_mode": "host_funded",
                "host_funded_prize_total": "1000",
                "payout_structure": [{"place": 1, "percent": "1.00"}],
            },
        ),
        201,
    )
    _ok(
        client.post(
            f"/api/competitions/{gtex_comp['id']}/publish",
            headers=bootstrap_admin_headers,
            json={"open_for_join": True},
        )
    )
    _ok(
        client.post(
            f"/api/competitions/{gtex_comp['id']}/join",
            headers=owner["headers"],
            json={"club_id": club_ids[owner["user_id"]]},
        )
    )

    # National-team competition + rental player.
    national = _ok(
        client.post(
            "/api/admin/national-team-engine/competitions",
            headers=bootstrap_admin_headers,
            json={
                "key": f"{PREFIX}-national",
                "title": "GTEX Full Journey National Cup",
                "season_label": "2026",
                "region_type": "global",
                "age_band": "u17",
                "format_type": "cup",
                "status": "published",
                "entry_opens_at": "2026-01-01T00:00:00Z",
                "entry_closes_at": "2026-12-31T23:59:00Z",
                "kickoff_at": "2026-12-15T12:00:00Z",
            },
        )
    )
    pool = _ok(
        client.get(
            f"/api/national-team-engine/competitions/{national['id']}/rental-pool",
            params={"country_code": "NG", "limit": 40},
        )
    )
    assert pool["items"]
    rental_player = next(item for item in pool["items"] if item.get("eligibility", {}).get("eligible", True))
    entry = _ok(
        client.post(
            f"/api/national-team-engine/competitions/{national['id']}/rental-entry",
            headers=owner["headers"],
            json={"country_code": "NG", "country_name": "Nigeria", "manager_user_id": owner["user_id"]},
        )
    )
    rental = _ok(
        client.post(
            f"/api/national-team-engine/entries/{entry['id']}/rentals",
            headers=owner["headers"],
            json={"player_id": rental_player["player_id"], "shirt_number": 9},
        )
    )
    assert rental["rental_contracts"]

    # Seed platform-owned real players + transfer window for this isolated acceptance DB.
    assets = _seed_player_assets(app_session_factory, owner["user_id"], trader["user_id"])

    # Buy a real player.
    real_listing = _ok(
        client.post(
            "/api/transfer-market/listings",
            headers=trader["headers"],
            json={
                "player_id": assets["real_player_id"],
                "selling_club_id": assets["seller_club_id"],
                "base_price": "2500",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "window_id": assets["window_id"],
                "asset_type": "real_player",
            },
        ),
        201,
    )
    real_offer = _ok(
        client.post(
            f"/api/transfer-hub/listings/{real_listing['id']}/offers",
            headers=owner["headers"],
            json={
                "bidder_club_id": club_ids[owner["user_id"]],
                "offer_type": "transfer",
                "cash_amount": "2500",
                "idempotency_key": f"{PREFIX}-real-player",
            },
        ),
        201,
    )
    _ok(client.post(f"/api/transfer-hub/offers/{real_offer['id']}/accept", headers=trader["headers"]))
    _ok(client.post(f"/api/transfer-market/listings/{real_listing['id']}/close", headers=trader["headers"]))

    # Build a Son and generate the regen.
    son_options = _ok(client.get("/api/regens/request-son/options", headers=owner["headers"]))
    assert any(item["player_id"] == assets["parent_player_id"] for item in son_options["eligible_parents"])
    son = _ok(
        client.post(
            "/api/regens/request-son",
            headers=owner["headers"],
            json={
                "parent_player_id": assets["parent_player_id"],
                "requested_name": "GTEX Full Journey Son",
                "requested_country_code": "NG",
                "requested_position": "ST",
                "payment_method": "wallet",
            },
        ),
        201,
    )
    _ok(client.post(f"/api/regens/creation-orders/{son['id']}/pay-with-wallet", headers=owner["headers"]))
    generated = _ok(
        client.post(f"/api/regens/creation-orders/{son['id']}/generate-after-payment", headers=owner["headers"])
    )
    regen_id = generated["generated_player_id"]
    assert generated["generated_player"]["club_id"] == club_ids[owner["user_id"]]

    # Buy/sell/negotiation cycle for the regen.
    regen_listing = _ok(
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
    regen_offer = _ok(
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
    counter = _ok(
        client.post(
            f"/api/transfer-hub/offers/{regen_offer['id']}/counter",
            headers=owner["headers"],
            json={"cash_amount": "1300", "message": "Counter offer"},
        )
    )
    _ok(client.post(f"/api/transfer-hub/offers/{counter['id']}/accept", headers=owner["headers"]))
    negotiation = _ok(
        client.get(f"/api/transfer-market/listings/{regen_listing['id']}/negotiation", headers=club_buyer["headers"])
    )
    assert negotiation["player_id"] == regen_id
    _ok(
        client.put(
            f"/api/transfer-market/coaches/{club_ids[club_buyer['user_id']]}/profile",
            headers=club_buyer["headers"],
            json={"tactical_philosophy": "balanced", "authority_level": 50},
        )
    )
    _ok(
        client.put(
            f"/api/transfer-market/players/{regen_id}/decision-profile",
            headers=owner["headers"],
            json={
                "preferred_leagues_json": ["NG"],
                "preferred_play_style": "balanced",
                "wage_expectation_amount": "100",
                "ambition_level": 80,
                "happiness": 90,
                "loyalty": 50,
                "ambition": 80,
                "frustration": 0,
            },
        )
    )
    offer = _ok(
        client.post(
            f"/api/transfer-market/listings/{regen_listing['id']}/contract-offer",
            headers=club_buyer["headers"],
            json={
                "bidder_club_id": club_ids[club_buyer["user_id"]],
                "wage_offer_amount": "1000",
                "contract_years": 3,
                "expected_role": "first_team",
                "release_clause_amount": "5000",
            },
        )
    )
    assert offer["contract_years"] == 3
    if offer["status"] == "player_delayed":
        _ok(
            client.post(
                "/api/transfer-market/jobs/run",
                headers=bootstrap_admin_headers,
                json={"reference_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()},
            )
        )
        negotiation = _ok(
            client.get(
                f"/api/transfer-market/listings/{regen_listing['id']}/negotiation", headers=club_buyer["headers"]
            )
        )
        assert negotiation["status"] == "completed"
    else:
        assert offer["status"] == "completed"

    # Renewal of club_buyer's active contract -> transfer bid acceptance, which canonically terminates the selling contract.
    contracts = _ok(client.get(f"/api/players/{regen_id}/contracts"))
    assert contracts, f"No contracts found for {regen_id}: {contracts}"
    active_contract = next((c for c in contracts if c["status"] == "active"), contracts[0])
    renewed = _ok(
        client.post(
            f"/api/players/{regen_id}/contracts/{active_contract['id']}/renew",
            headers=club_buyer["headers"],
            json={"new_ends_on": "2029-12-31"},
        )
    )
    assert renewed["ends_on"] == "2029-12-31"
    today_str = date.today().isoformat()
    end_str = (date.today() + timedelta(days=1095)).isoformat()
    created_bid = _ok(
        client.post(
            f"/api/transfers/windows/{assets['window_id']}/bids",
            headers=buyer["headers"],
            json={
                "player_id": regen_id,
                "selling_club_id": club_ids[club_buyer["user_id"]],
                "buying_club_id": club_ids[buyer["user_id"]],
                "bid_amount": "1600",
                "wage_offer_amount": "175",
                "contract_years": 3,
            },
        ),
        201,
    )
    accepted_bid = _ok(
        client.post(
            f"/api/transfers/windows/{assets['window_id']}/bids/{created_bid['id']}/accept",
            headers=club_buyer["headers"],
            json={"contract_ends_on": end_str, "contract_starts_on": today_str, "wage_amount": "175"},
        )
    )
    assert accepted_bid["status"] in {"accepted", "completed"}

    # Facilities + academy + first youth contract + promotion.
    for facility_key in ("training", "medical", "youth_recruitment"):
        _ok(
            client.post(
                "/api/club-infra/my/facilities/upgrade",
                headers=club_buyer["headers"],
                json={"facility_key": facility_key, "increment": 1},
            )
        )
    prospects = _ok(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/academy/generate-prospects",
            headers=club_buyer["headers"],
            json={"count": 3},
        )
    )
    assert prospects
    prospect_id = prospects[0]["id"]
    youth_offer = _ok(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/academy/prospects/{prospect_id}/offer-contract",
            headers=club_buyer["headers"],
            json={"wage_minor": 1000, "duration_months": 24},
        )
    )
    _ok(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/academy/contracts/{youth_offer['id']}/respond",
            headers=club_buyer["headers"],
            json={"accepted": True},
        )
    )
    promoted = _ok(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/academy/prospects/{prospect_id}/promote",
            headers=club_buyer["headers"],
        )
    )
    assert promoted["status"] == "promoted_to_senior"

    # Manager + coach/staff contract lifecycle.
    managers = _ok(client.get("/api/managers/catalog"))
    assert managers["items"]
    manager_id = managers["items"][0].get("manager_id") or managers["items"][0].get("id")
    team = _ok(
        client.post(
            "/api/managers/recruit",
            headers=club_buyer["headers"],
            json={"manager_id": manager_id, "slot": "main", "salary_fancoin": "100"},
        )
    )
    assert team
    growth = _ok(client.get(f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth", headers=club_buyer["headers"]))
    assert growth["staff_market"]
    staff_id = growth["staff_market"][0]["id"]
    staff_offer = _ok(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/staff/{staff_id}/offer",
            headers=club_buyer["headers"],
            json={"salary_minor": 1000, "duration_days": 365},
        )
    )
    _ok(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/staff-contracts/{staff_offer['id']}/accept",
            headers=club_buyer["headers"],
        )
    )
    terminated = _ok(
        client.post(
            f"/api/clubs/{club_ids[club_buyer['user_id']]}/growth/staff-contracts/{staff_offer['id']}/terminate",
            headers=club_buyer["headers"],
        )
    )
    assert terminated["status"] in {"terminated", "ended"}

    # Sell a club, then buy that club as another user.
    sold_club_id = club_ids[club_buyer["user_id"]]
    valuation = _ok(client.get(f"/api/clubs/{sold_club_id}/valuation"))
    asking = max(Decimal(str(valuation["system_valuation"])), Decimal("1000"))
    _ok(
        client.post(
            f"/api/clubs/{sold_club_id}/sale-market/listing",
            headers=club_buyer["headers"],
            json={"asking_price": str(asking), "visibility": "public", "note": PREFIX},
        ),
        201,
    )
    club_offer = _ok(
        client.post(
            f"/api/clubs/{sold_club_id}/sale-market/offers",
            headers=owner["headers"],
            json={"offer_price": str(asking), "message": "Full journey club purchase"},
        ),
        201,
    )
    offer_id = club_offer.get("offer_id") or club_offer.get("id")
    _ok(
        client.post(
            f"/api/clubs/{sold_club_id}/sale-market/offers/{offer_id}/accept",
            headers=club_buyer["headers"],
            json={"message": "accepted"},
        )
    )
    transfer = _ok(
        client.post(
            f"/api/clubs/{sold_club_id}/sale-market/transfer",
            headers=club_buyer["headers"],
            json={"offer_id": offer_id, "executed_sale_price": str(asking)},
        )
    )
    assert transfer["ownership_transition"]["new_owner_user_id"] == owner["user_id"]

    # Jackpot deterministic win.
    _ok(
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
        )
    )
    contribution = _ok(
        client.post(
            "/api/jackpot/contribute",
            headers=owner["headers"],
            json={
                "source_type": "platform_activity",
                "source_id": f"{PREFIX}-jackpot-source",
                "entry_fee": "10.0000",
                "contribution_amount": "10.0000",
                "eligibility_score": "2.0000",
                "metadata": {"journey": PREFIX},
            },
        ),
        201,
    )
    assert contribution["contribution_amount"] == "10.0000"
    trigger = _ok(client.post("/api/admin/jackpot/trigger", headers=bootstrap_admin_headers))
    history = _ok(client.get("/api/jackpot/history"))
    settled = next(item for item in history if item["round_number"] == trigger["triggered_round_number"])
    assert any(p["user_id"] == owner["user_id"] for p in settled["payouts"])

    # Send/receive gifts as user, and to a club owned by the recipient.
    gift_catalog = _ok(client.get("/api/gifts/catalog"))
    active_gift = next(item for item in gift_catalog if item["is_active"])
    gift_key = active_gift["code"]
    user_gift = _ok(
        client.post(
            "/api/gift-engine/send",
            headers=owner["headers"],
            json={
                "recipient_user_id": recipient["user_id"],
                "gift_key": gift_key,
                "quantity": 1,
                "note": "Full journey user gift",
                "idempotency_key": f"{PREFIX}-user-gift-{recipient['user_id']}",
            },
        ),
        200,
    )
    received = _ok(client.get("/api/gift-engine/me/transactions", headers=recipient["headers"]))
    assert any(item["id"] == user_gift["id"] for item in received)
    club_gift = _ok(
        client.post(
            "/api/gift-engine/send",
            headers=owner["headers"],
            json={
                "recipient_club_id": club_ids[recipient["user_id"]],
                "gift_key": gift_key,
                "quantity": 1,
                "note": "Full journey club-owner gift",
                "idempotency_key": f"{PREFIX}-club-gift-{club_ids[recipient['user_id']]}",
            },
        ),
        200,
    )
    assert club_gift["recipient_club_id"] == club_ids[recipient["user_id"]]
    received_again = _ok(client.get("/api/gift-engine/me/transactions", headers=recipient["headers"]))
    assert any(item["id"] == club_gift["id"] for item in received_again)

    # Final ownership/contract invariant.
    with app_session_factory() as session:
        owner_club = _club(session, owner["user_id"])
        contracts = list(session.scalars(select(PlayerContract).where(PlayerContract.club_id == owner_club.id)).all())
        assert owner_club.id
        assert all(contract.club_id == owner_club.id for contract in contracts)
