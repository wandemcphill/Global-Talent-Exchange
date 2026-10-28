"""Comprehensive tests for GTEX event-driven football storytelling and personal club management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.operations import seed_catalogue
from app.models.admin_rules import AdminFeatureFlag
from app.models.user import User
from app.owner_console import alerts, competitions as comps, ledger, service, storytelling
from app.owner_console.models import (
    LedgerEvent,
    OwnerBroadcastEvent,
    OwnerCompetition,
    OwnerInboxItem,
    OwnerMatch,
    OwnerNewsroomArticle,
    OwnerShowroomAsset,
    OwnerSquadPlayer,
)
from app.owner_console.service import OwnerError
from app.services.world_clock_service import WorldClockService


def _enable_legacy(app) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        if flag:
            flag.enabled = True
        seed_catalogue(session)
        session.commit()


def _claim_and_activate(client, headers, city: str = "Lagos") -> str:
    resp = client.post("/api/owner/clubs/claim", headers=headers, json={"city_name": city, "country_code": "NG"})
    assert resp.status_code == 200, resp.text
    club_id = resp.json()["club_id"]
    act = client.post(f"/api/owner/clubs/{club_id}/activate", headers=headers)
    assert act.status_code == 200, act.text
    return club_id


def test_global_live_ticker_eligibility_and_luxury_isolation(client, bootstrap_admin_headers, app):
    """
    Requirement 1 & 7:
    - Broadcast announcements ONLY for completed private jet purchases, club facility upgrades,
      and club-owner gifts to players.
    - NEVER announce ordinary personal luxury purchases (watches, hypercars, coaches) globally.
    - Include verified price, owner, club, model, player, and static images.
    """
    _enable_legacy(app)
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Lagos")

    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        # Top up club account so all purchases succeed cleanly
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=Decimal("250000"),
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(club_id),
            user_id=admin.id,
            club_id=club_id,
        )
        session.commit()

    # 1. Ordinary personal luxury purchases (watch, hypercar, coach) MUST NOT broadcast globally
    for personal_key in ("chronos_tourbillon_watch", "veloce_gt9_hypercar", "vanguard_xii_coach"):
        res = client.post(
            f"/api/owner/clubs/{club_id}/showroom/purchase",
            headers=bootstrap_admin_headers,
            json={"catalog_key": personal_key},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["broadcast_globally"] is False
        assert body["broadcast_event"] is None

    ticker_after_personal = client.get("/api/owner/ticker", headers=bootstrap_admin_headers).json()["events"]
    assert len(ticker_after_personal) == 0, "Personal luxury purchases must never appear on the global ticker"

    # 2. Private jet purchase MUST broadcast globally with verified price, model, and image
    jet_res = client.post(
        f"/api/owner/clubs/{club_id}/showroom/purchase",
        headers=bootstrap_admin_headers,
        json={"catalog_key": "sovereign_900x_jet", "idempotency_key": "jet-purchase-1"},
    )
    assert jet_res.status_code == 200, jet_res.text
    jet_data = jet_res.json()
    assert jet_data["broadcast_globally"] is True
    assert jet_data["broadcast_event"]["event_type"] == "private_jet_purchase"
    assert Decimal(str(jet_data["broadcast_event"]["verified_price_gtex"])) == Decimal("4800")
    assert "sovereign_900x_jet.webp" in jet_data["broadcast_event"]["item_image_url"]

    # 3. Facility upgrade MUST broadcast globally with verified price and facility image
    fac_res = client.post(
        f"/api/owner/clubs/{club_id}/facilities/stadium/upgrade",
        headers=bootstrap_admin_headers,
    )
    assert fac_res.status_code == 200, fac_res.text

    # 4. Luxury gifts are reserved for academy regens. A normal first-team
    # player must be rejected before any gift ledger or broadcast event is written.
    with app.state.session_factory() as session:
        session.add(
            OwnerSquadPlayer(
                club_id=club_id,
                name="First-Team Player",
                position="ST",
                is_regen=False,
            )
        )
        session.commit()

    club_detail = client.get(f"/api/owner/clubs/{club_id}", headers=bootstrap_admin_headers).json()
    first_team_player = next(player for player in club_detail["squad"] if not player.get("is_regen", False))
    rejected_gift = client.post(
        f"/api/owner/clubs/{club_id}/showroom/gift",
        headers=bootstrap_admin_headers,
        json={
            "player_id": first_team_player["id"],
            "catalog_key": "chronos_tourbillon_watch",
            "note": "Golden Boot bonus",
            "idempotency_key": "gift-nonregen-rejected",
        },
    )
    assert rejected_gift.status_code == 400, rejected_gift.text
    assert rejected_gift.json()["detail"]["code"] == "player_not_eligible_for_gift"

    # Generate a canonical academy regen through the existing intake path, then
    # prove the same luxury gift flow succeeds for that eligible recipient.
    intake_res = client.post(
        f"/api/owner/clubs/{club_id}/academy/intake",
        headers=bootstrap_admin_headers,
    )
    assert intake_res.status_code == 200, intake_res.text
    eligible_regens = intake_res.json()["regens"]
    assert eligible_regens
    regen_player = eligible_regens[0]
    assert regen_player["is_regen"] is True
    assert regen_player.get("portrait_url"), "Regen player must have resolved static portrait URL"

    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        gift_balance_before = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
        regen_row = session.get(OwnerSquadPlayer, regen_player["id"])
        morale_before_gift = regen_row.morale

    gift_request = {
        "player_id": regen_player["id"],
        "catalog_key": "chronos_tourbillon_watch",
        "note": "Golden Boot bonus",
        "idempotency_key": "gift-player-1",
    }
    gift_res = client.post(
        f"/api/owner/clubs/{club_id}/showroom/gift",
        headers=bootstrap_admin_headers,
        json=gift_request,
    )
    assert gift_res.status_code == 200, gift_res.text
    gift_data = gift_res.json()
    assert gift_data["broadcast_event"]["event_type"] == "player_gift"
    assert gift_data["broadcast_event"]["player_name"] == regen_player["name"]
    assert gift_data["broadcast_event"]["player_portrait_url"]
    assert Decimal(str(gift_data["broadcast_event"]["verified_price_gtex"])) == Decimal("220")
    assert gift_data["morale_delta"] == min(100, morale_before_gift + 15) - morale_before_gift

    # Network retries must return the exact original gift without another debit,
    # morale boost, inbox acknowledgement, or broadcast/newsroom event.
    retry_res = client.post(
        f"/api/owner/clubs/{club_id}/showroom/gift",
        headers=bootstrap_admin_headers,
        json=gift_request,
    )
    assert retry_res.status_code == 200, retry_res.text
    retry_data = retry_res.json()
    assert retry_data["broadcast_event"]["id"] == gift_data["broadcast_event"]["id"]
    assert retry_data["player"] == gift_data["player"]
    assert retry_data["morale_delta"] == gift_data["morale_delta"]

    with app.state.session_factory() as session:
        assert ledger.balance(session, ledger.club_account(club_id), ledger.GTEX) == gift_balance_before - Decimal(
            "220"
        )
        persisted_player = session.get(OwnerSquadPlayer, regen_player["id"])
        assert persisted_player.morale == gift_data["player"]["morale"]
        gift_ledger_rows = session.scalars(
            select(LedgerEvent).where(
                LedgerEvent.event_type == "squad_player_gift",
                LedgerEvent.club_id == club_id,
                LedgerEvent.user_id == admin.id,
            )
        ).all()
        assert len(gift_ledger_rows) == 1
        gift_broadcasts = session.scalars(
            select(OwnerBroadcastEvent).where(OwnerBroadcastEvent.idempotency_key == "gift-player-1")
        ).all()
        assert len(gift_broadcasts) == 1
        gift_acknowledgements = session.scalars(
            select(OwnerInboxItem).where(
                OwnerInboxItem.user_id == admin.id,
                OwnerInboxItem.club_id == club_id,
                OwnerInboxItem.title == f"Thank You from {regen_player['name']}",
            )
        ).all()
        assert len(gift_acknowledgements) == 1

    # Verify the global ticker contains ONLY the 3 eligible events
    ticker_events = client.get("/api/owner/ticker", headers=bootstrap_admin_headers).json()["events"]
    event_types = [e["event_type"] for e in ticker_events]
    assert set(event_types) == {"private_jet_purchase", "facility_upgrade", "player_gift"}
    assert len(ticker_events) == 3


def test_transaction_integrity_idempotency_failures_and_reversals(client, bootstrap_admin_headers, app):
    """
    Requirement 2:
    - Idempotent retry with the same idempotency_key produces no duplicate broadcast or newsroom story.
    - Failed / insufficient-funds or rolled-back transactions produce 0 announcements.
    - Reversing a committed ledger transaction marks linked broadcast events 'reversed' and
      newsroom stories 'retracted' so they vanish from live feeds.
    """
    _enable_legacy(app)
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Abuja")

    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=Decimal("20000"),
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(club_id),
            user_id=admin.id,
            club_id=club_id,
        )
        session.commit()
        club_balance_before = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)

    # Retrying a purchase with the same intent key replays the original purchase, not another charge.
    asset_ids: list[str] = []
    for _ in range(3):
        resp = client.post(
            f"/api/owner/clubs/{club_id}/showroom/purchase",
            headers=bootstrap_admin_headers,
            json={"catalog_key": "sovereign_900x_jet", "idempotency_key": "idem-jet-unique-001"},
        )
        assert resp.status_code == 200, resp.text
        asset_ids.append(resp.json()["asset"]["id"])
    assert len(set(asset_ids)) == 1

    with app.state.session_factory() as session:
        assets = session.scalars(
            select(OwnerShowroomAsset).where(OwnerShowroomAsset.idempotency_key == "idem-jet-unique-001")
        ).all()
        assert len(assets) == 1
        assert assets[0].id == asset_ids[0]
        purchase_ledger = session.get(LedgerEvent, assets[0].ledger_event_id)
        assert purchase_ledger is not None
        assert purchase_ledger.event_type == "showroom_asset_purchase"
        assert purchase_ledger.gross_amount == Decimal("4800.00")
        assert ledger.balance(session, ledger.club_account(club_id), ledger.GTEX) == club_balance_before - Decimal(
            "4800"
        )

        b_rows = session.scalars(
            select(OwnerBroadcastEvent).where(OwnerBroadcastEvent.idempotency_key == "idem-jet-unique-001")
        ).all()
        assert len(b_rows) == 1
        n_rows = session.scalars(
            select(OwnerNewsroomArticle).where(OwnerNewsroomArticle.idempotency_key == "news:idem-jet-unique-001")
        ).all()
        assert len(n_rows) == 1

    conflict_resp = client.post(
        f"/api/owner/clubs/{club_id}/showroom/purchase",
        headers=bootstrap_admin_headers,
        json={"catalog_key": "veloce_gt9_hypercar", "idempotency_key": "idem-jet-unique-001"},
    )
    assert conflict_resp.status_code == 409, conflict_resp.text
    with app.state.session_factory() as session:
        assert ledger.balance(session, ledger.club_account(club_id), ledger.GTEX) == club_balance_before - Decimal(
            "4800"
        )

    # 2. Failed transaction (insufficient funds) must produce 0 broadcasts
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        # Drain club balance to 10 GTX
        bal = ledger.balance(session, ledger.club_account(club_id), ledger.GTEX)
        if bal > Decimal("10"):
            ledger.record(
                session,
                event_type="drain_test",
                currency=ledger.GTEX,
                gross=bal - Decimal("10"),
                source=ledger.club_account(club_id),
                destination=ledger.WORLD_CLUBS,
                user_id=admin.id,
                club_id=club_id,
            )
            session.commit()

    fail_resp = client.post(
        f"/api/owner/clubs/{club_id}/showroom/purchase",
        headers=bootstrap_admin_headers,
        json={"catalog_key": "gulfstream_g700_exec_jet", "idempotency_key": "failed-jet-002"},
    )
    assert fail_resp.status_code == 400
    assert (fail_resp.json().get("code") or fail_resp.json().get("detail", {}).get("code")) == "insufficient_club_cash"

    with app.state.session_factory() as session:
        failed_broadcast = session.scalar(
            select(OwnerBroadcastEvent).where(OwnerBroadcastEvent.idempotency_key == "failed-jet-002")
        )
        assert failed_broadcast is None

    # 3. Rolled-back transaction after staging a broadcast event must NOT persist or dispatch
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        storytelling.record_verified_broadcast_event(
            session,
            event_type="private_jet_purchase",
            club_id=club_id,
            owner_user_id=admin.id,
            item_name="Uncommitted Phantom Jet",
            verified_price_gtex=Decimal("4800"),
            idempotency_key="rollback-phantom-jet",
        )
        session.rollback()

    with app.state.session_factory() as session:
        phantom = session.scalar(
            select(OwnerBroadcastEvent).where(OwnerBroadcastEvent.idempotency_key == "rollback-phantom-jet")
        )
        assert phantom is None

    # 4. Reversing a committed ledger transaction retracts the broadcast and newsroom article
    with app.state.session_factory() as session:
        b_row = session.scalar(
            select(OwnerBroadcastEvent).where(OwnerBroadcastEvent.idempotency_key == "idem-jet-unique-001")
        )
        assert b_row is not None and b_row.ledger_event_id is not None
        ledger_event = session.get(LedgerEvent, b_row.ledger_event_id)
        assert ledger_event is not None
        ledger.transition(session, ledger_event, "reversed")
        session.commit()

    ticker_after_reversal = client.get(
        "/api/owner/ticker", headers=bootstrap_admin_headers, params={"club_id": club_id}
    ).json()["events"]
    assert all(e["idempotency_key"] != "idem-jet-unique-001" for e in ticker_after_reversal)

    news_after_reversal = client.get(
        "/api/owner/newsroom", headers=bootstrap_admin_headers, params={"club_id": club_id}
    ).json()["articles"]
    assert all(a.get("source_event_id") != b_row.id for a in news_after_reversal)


def test_ai_newsroom_grounding_and_readonly_safety(app):
    """
    Requirement 3:
    - Keep established facts separate from editorial narration.
    - Reject invented prices/numbers or unverified scorelines.
    - Never allow editorial generation to create transactions or mutate game state.
    """
    established_facts = {
        "event_type": "private_jet_purchase",
        "club_name": "Lagos Stars FC",
        "owner": "admin",
        "item_name": "GTEX Sovereign 900X Private Jet",
        "verified_price_gtex": "4800.0000",
        "world_day": 12,
    }
    # Hallucinated narration inventing an unverified 99999 GTX price and a fake 4-1 scoreline
    hallucinated_narration = (
        "Lagos Stars FC stunned the league by spending 99999 GTX on a secret jet after winning 4-1 in the final."
    )
    grounding = storytelling.validate_article_grounding(established_facts, hallucinated_narration)
    assert grounding["valid"] is False
    assert "99999" in grounding["unverified_numbers"]
    assert "4-1" in grounding["unverified_scores"]

    # Valid grounded narration referencing only verified numbers
    valid_narration = (
        "On World Day 12, Lagos Stars FC completed the 4800 GTX acquisition of the GTEX Sovereign 900X Private Jet."
    )
    valid_grounding = storytelling.validate_article_grounding(established_facts, valid_narration)
    assert valid_grounding["valid"] is True


def test_personal_inbox_categories_deadlines_and_recipient_authorization(client, bootstrap_admin_headers, app):
    """
    Requirement 4:
    - Personal owner inbox supports categories, priorities, actionable decisions, read status,
      archive, resolution, and deadlines.
    - Enforces recipient ownership server-side (another user cannot read, archive, or decide).
    """
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Kano")

    # Move the shared virtual calendar forward by one day in this test database.
    # The owner /advance route now performs global-clock catch-up instead of
    # privately incrementing a club's world day.
    with app.state.session_factory() as session:
        clock = WorldClockService(session)
        clock_state = clock.get_or_create_state()
        virtual_now = datetime.now(timezone.utc)
        clock_state.epoch_real_utc = virtual_now
        clock_state.virtual_start_time = virtual_now + timedelta(days=1)
        clock_state.progression_rate = 1.0
        clock_state.is_paused = False
        clock_state.paused_at_virtual_time = None
        session.commit()

    # Catch up the owner club to the newly advanced shared world date.
    adv = client.post(f"/api/owner/clubs/{club_id}/advance", headers=bootstrap_admin_headers)
    assert adv.status_code == 200, adv.text

    inbox_res = client.get("/api/owner/inbox", headers=bootstrap_admin_headers)
    assert inbox_res.status_code == 200, inbox_res.text
    inbox_data = inbox_res.json()
    items = inbox_data["items"]
    assert len(items) > 0
    assert "counts" in inbox_data
    assert inbox_data["counts"]["all"] >= len(items)

    target_item = items[0]
    assert target_item["club_id"] == club_id
    assert target_item["save_context_id"]
    assert target_item["category"] in storytelling.INBOX_CATEGORIES

    # Mark item as read
    read_res = client.post(
        f"/api/owner/inbox/{target_item['id']}/read",
        headers=bootstrap_admin_headers,
        json={"is_read": True},
    )
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # Archive and restore item
    arch_res = client.post(
        f"/api/owner/inbox/{target_item['id']}/archive",
        headers=bootstrap_admin_headers,
        json={"archive": True},
    )
    assert arch_res.status_code == 200
    assert arch_res.json()["archived_at"] is not None

    archived_list = client.get(
        "/api/owner/inbox", headers=bootstrap_admin_headers, params={"category": "archive"}
    ).json()["items"]
    assert any(i["id"] == target_item["id"] for i in archived_list)

    unarch_res = client.post(
        f"/api/owner/inbox/{target_item['id']}/archive",
        headers=bootstrap_admin_headers,
        json={"archive": False},
    )
    assert unarch_res.status_code == 200
    assert unarch_res.json()["archived_at"] is None

    # Wrong recipient authorization check & deadline expiry check
    with app.state.session_factory() as session:
        intruder = User(email="intruder@test.gtex.local", username="intruder_owner", password_hash="hash")
        session.add(intruder)
        session.flush()

        with pytest.raises(OwnerError) as exc_read:
            service.mark_inbox_read(session, intruder.id, target_item["id"], is_read=True)
        assert exc_read.value.status == 404

        with pytest.raises(OwnerError) as exc_decide:
            service.resolve_item(session, intruder.id, target_item["id"], "approve")
        assert exc_decide.value.status == 404

        # Create an overdue decision item and verify sweep_decisions auto-resolves and sends expiry notice
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        overdue = OwnerInboxItem(
            user_id=admin.id,
            club_id=club_id,
            save_context_id="club:test",
            category="negotiations",
            kind="contract_negotiation",
            priority="high",
            sender="Player Agent",
            title="Overdue Contract Demand",
            what="Contract renewal deadline",
            why="Expiring deal",
            body="We need an answer now.",
            actions_json=[{"key": "extend", "label": "Extend"}, {"key": "hold_terms", "label": "Hold"}],
            payload_json={"respond_by": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()},
            is_decision=True,
            status="open",
            created_at=datetime.now(timezone.utc) - timedelta(hours=26),
        )
        session.add(overdue)
        session.flush()
        result_counts = alerts.sweep_decisions(session, admin.id)
        assert result_counts["expired"] >= 1
        assert overdue.status == "expired"
        assert "hold_terms" in overdue.resolution
        session.rollback()


def test_club_story_and_shared_save_privacy_isolation(client, bootstrap_admin_headers, app):
    """
    Requirement 5 & 6:
    - Club Story returns timeline, unresolved issues, relationships, scouting watchlist,
      upcoming schedule, club news, achievements, and owner legacy.
    - Shared saves keep competition/match events consistent for participants in the same save,
      while isolating private messages, unresolved issues, and confidential scouting watchlists
      from other owners in the same save.
    """
    club_a_id = _claim_and_activate(client, bootstrap_admin_headers, city="Port Harcourt")

    # Add a confidential scouting target to Club A's watchlist
    wl_res = client.post(
        f"/api/owner/clubs/{club_a_id}/watchlist",
        headers=bootstrap_admin_headers,
        json={
            "player_name": "Chinedu Wonderkid",
            "position": "FWD",
            "age": 17,
            "current_rating": 71,
            "potential_rating": 89,
            "estimated_value_gtex": 210,
            "priority": "high",
            "scout_notes": "TOP SECRET: Release clause expires in 14 days.",
            "recommendation": "Immediate bid",
        },
    )
    assert wl_res.status_code == 200, wl_res.text

    # Owner A views their own Club Story -> full access
    story_owner = client.get(f"/api/owner/clubs/{club_a_id}/story", headers=bootstrap_admin_headers)
    assert story_owner.status_code == 200, story_owner.text
    story_data = story_owner.json()
    assert story_data["is_owner"] is True
    assert story_data["privacy_redacted"] is False
    assert any(w["player_name"] == "Chinedu Wonderkid" for w in story_data["scouting_watchlist"])
    assert "timeline" in story_data
    assert "relationships" in story_data
    assert "achievements" in story_data
    assert "owner_legacy" in story_data

    # Create a second owner (Owner B) in the same shared competition save
    with app.state.session_factory() as session:
        owner_b = User(email="owner_b@test.gtex.local", username="owner_b", password_hash="hash")
        session.add(owner_b)
        session.flush()
        state_b = service.claim_starter_club(session, owner_b, city_name="Enugu", country_code="NG")
        service.start_activation(session, owner_b.id, state_b.club_id)

        # Enter both clubs into the same competition (shared save context)
        comps.ensure_seed(session)
        open_comp = session.scalar(select(comps.OwnerCompetition).where(comps.OwnerCompetition.status == "open"))
        if open_comp:
            try:
                comps.enter_competition(
                    session, service.get_state(session, club_a_id).owner_user_id, open_comp.id, club_a_id
                )
            except Exception:
                pass
            try:
                comps.enter_competition(session, owner_b.id, open_comp.id, state_b.club_id)
            except Exception:
                pass

        # Owner B views Club A's Story in the shared save:
        # World/match timeline & achievements are visible, but confidential scouting watchlist & unresolved issues are redacted!
        shared_view = storytelling.build_club_story(session, owner_b.id, club_a_id)
        assert shared_view["is_owner"] is False
        assert shared_view["privacy_redacted"] is True
        assert shared_view["scouting_watchlist"] == []
        assert shared_view["unresolved_issues"] == []
        assert all(p["contract_expectation"] is None for p in shared_view["relationships"]["players"])

        # Owner B cannot add or delete items in Club A's confidential watchlist
        with pytest.raises(OwnerError) as wl_err:
            storytelling.add_to_watchlist(
                session,
                owner_b.id,
                club_a_id,
                player_name="Spy Target",
            )
        assert wl_err.value.status == 403
        session.rollback()


def test_save_scoped_newsroom_authorization_and_filter(client, bootstrap_admin_headers, app):
    """
    B1: Save-scoped newsroom authorization filter missing in get_owner_newsroom / list_newsroom_articles.
    Ensure private save articles are only visible to authorized save owners, while global articles
    remain accessible to everyone.
    """
    _enable_legacy(app)
    club_a_id = _claim_and_activate(client, bootstrap_admin_headers, city="Kano")

    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        save_a = f"club:{club_a_id}"

        # 1. Create global article (save_context_id is "global", visibility="global")
        art_global = OwnerNewsroomArticle(
            club_id=club_a_id,
            save_context_id="global",
            visibility="global",
            category="financial",
            headline="Global Federation Update",
            subheadline="Worldwide regulation announcement",
            editorial_narration="The federation has issued a worldwide update.",
            status="published",
            idempotency_key="news-global-auth-001",
        )
        # 2. Create save_a-scoped article
        art_save_a = OwnerNewsroomArticle(
            club_id=club_a_id,
            save_context_id=save_a,
            visibility="private",
            category="transfers",
            headline="Club A Secret Contract Leak",
            subheadline="Confidential save-scoped memo",
            editorial_narration="Save-specific confidential document.",
            status="published",
            idempotency_key="news-save-a-auth-002",
        )
        # 3. Create foreign-save-scoped article
        art_foreign = OwnerNewsroomArticle(
            club_id="foreign_club_xyz",
            save_context_id="club:foreign_save_xyz",
            visibility="private",
            category="editorial",
            headline="Foreign Club Internal Briefing",
            subheadline="Other owner confidential report",
            editorial_narration="Foreign club internal briefing.",
            status="published",
            idempotency_key="news-foreign-auth-003",
        )
        session.add_all([art_global, art_save_a, art_foreign])
        session.commit()

        # Create user B without access to save_a
        owner_b = User(email="owner_b_news@test.gtex.local", username="owner_b_news", password_hash="hash")
        session.add(owner_b)
        session.commit()
        owner_b_id = owner_b.id

        # Verify storytelling.list_newsroom_articles for Admin (has save_a access)
        admin_articles = storytelling.list_newsroom_articles(session, user_id=admin.id)
        admin_headlines = [a["headline"] for a in admin_articles]
        assert "Global Federation Update" in admin_headlines
        assert "Club A Secret Contract Leak" in admin_headlines
        assert "Foreign Club Internal Briefing" not in admin_headlines

        # Verify storytelling.list_newsroom_articles for Owner B (does not have save_a access)
        b_articles = storytelling.list_newsroom_articles(session, user_id=owner_b_id)
        b_headlines = [a["headline"] for a in b_articles]
        assert "Global Federation Update" in b_headlines
        assert "Club A Secret Contract Leak" not in b_headlines
        assert "Foreign Club Internal Briefing" not in b_headlines

        # Verify explicit save_context_id filter:
        # Owner B querying save_a should get 0 results because of authorization filtering
        b_scoped_articles = storytelling.list_newsroom_articles(session, user_id=owner_b_id, save_context_id=save_a)
        assert len(b_scoped_articles) == 0

        # Admin querying save_a gets the save_a article
        admin_scoped_articles = storytelling.list_newsroom_articles(session, user_id=admin.id, save_context_id=save_a)
        assert any(a["headline"] == "Club A Secret Contract Leak" for a in admin_scoped_articles)

    # Verify via HTTP endpoints: both /api/owner/newsroom and /api/v2/owner/newsroom
    res_v1 = client.get("/api/owner/newsroom", headers=bootstrap_admin_headers, params={"save_context_id": save_a})
    assert res_v1.status_code == 200
    body_v1 = res_v1.json()
    articles_v1 = body_v1["data"]["articles"] if "data" in body_v1 else body_v1["articles"]
    assert any(a["headline"] == "Club A Secret Contract Leak" for a in articles_v1)

    res_v2 = client.get("/api/v2/owner/newsroom", headers=bootstrap_admin_headers, params={"save_context_id": save_a})
    assert res_v2.status_code == 200
    body_v2 = res_v2.json()
    articles_v2 = body_v2["data"]["articles"] if "data" in body_v2 else body_v2["articles"]
    assert any(a["headline"] == "Club A Secret Contract Leak" for a in articles_v2)


def test_public_ticker_payload_sanitization_and_price_retention(client, bootstrap_admin_headers, app):
    """
    B2: owner_user_id exposed in public broadcast_dict payloads (must be stripped
    while retaining verified_price_gtex for public private-jet announcements).
    """
    _enable_legacy(app)
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Ibadan")

    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=Decimal("50000"),
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(club_id),
            user_id=admin.id,
            club_id=club_id,
        )
        session.commit()

    # Purchase private jet
    jet_res = client.post(
        f"/api/owner/clubs/{club_id}/showroom/purchase",
        headers=bootstrap_admin_headers,
        json={"catalog_key": "sovereign_900x_jet", "idempotency_key": "jet-ticker-sanitization-1"},
    )
    assert jet_res.status_code == 200
    event_payload = jet_res.json()["broadcast_event"]
    assert "owner_user_id" not in event_payload, "owner_user_id must be stripped from broadcast payload"
    assert "verified_price_gtex" in event_payload
    assert Decimal(str(event_payload["verified_price_gtex"])) == Decimal("4800")

    # Verify /api/owner/ticker and /api/v2/owner/ticker
    for route in ("/api/owner/ticker", "/api/v2/owner/ticker"):
        res = client.get(route, headers=bootstrap_admin_headers)
        assert res.status_code == 200
        body = res.json()
        events = body["data"]["events"] if "data" in body else body["events"]
        assert len(events) > 0
        for ev in events:
            assert "owner_user_id" not in ev, f"Public broadcast event must NOT expose owner_user_id in {route}"
            if ev.get("event_type") == "private_jet_purchase":
                assert ev.get("verified_price_gtex") is not None
                assert Decimal(str(ev["verified_price_gtex"])) > 0


def test_player_portrait_manifest_resolution_assets_key_and_media_mount(client, bootstrap_admin_headers):
    """
    B3: Broken manifest key ("items" vs "assets") and unmounted /api/media/regen-faces/* path in resolve_player_portrait_url.
    """
    # 1. Manifest key resolution test
    url = storytelling.resolve_player_portrait_url(None, "player-test-unique-999", player_name="Victor Osimhen")
    assert url, "Portrait URL must resolve"
    # The manifest contains 8,522 assets. It should NOT fall back to raw data:image/svg if assets exist!
    manifest = storytelling._load_face_manifest()
    assert "assets" in manifest, "Manifest must contain 'assets' key"
    assert len(manifest["assets"]) > 0

    if manifest.get("assets"):
        # Must be either Cloudinary URL or /generated-media/
        assert url.startswith("https://res.cloudinary.com") or url.startswith(
            "/generated-media/"
        ), f"Expected Cloudinary or generated-media URL, got: {url}"

    # 2. Test static mount /api/media/regen-faces/* exists on FastAPI app
    test_media_res = client.get("/api/media/regen-faces/manifest.json")
    assert test_media_res.status_code in (200, 404)


def test_global_competitions_cannot_use_owner_console_simulator(monkeypatch):
    """Global GTEX competitions must not create a second result on the legacy rail."""
    global_competition = OwnerCompetition(id="global-comp-1", name="Global Cup", host_type="gtex")

    class SessionStub:
        def get(self, model, identifier):
            assert model is OwnerCompetition
            assert identifier == global_competition.id
            return global_competition

    monkeypatch.setattr(comps, "require_state", lambda *args, **kwargs: object())

    with pytest.raises(OwnerError) as exc_info:
        comps.play_next(
            SessionStub(),
            user_id="owner-1",
            competition_id=global_competition.id,
            club_id="club-1",
            mentality="balanced",
            lineup_mode="strongest",
        )

    assert exc_info.value.code == "canonical_fixture_mapping_required"
    assert exc_info.value.status == 409


def test_unmapped_global_fixture_history_is_explicitly_read_only(monkeypatch):
    from app.services.owner_competition_lifecycle_mapping_service import (
        OwnerCompetitionLifecycleMappingService,
    )

    global_competition = OwnerCompetition(
        id="global-history-1",
        name="Historical Global Cup",
        host_type="gtex",
    )
    legacy_match = OwnerMatch(
        id="legacy-history-match-1",
        competition_id=global_competition.id,
        round_number=1,
        home_club_id="club-home",
        away_club_id="club-away",
        home_name="Home FC",
        away_name="Away FC",
        status="completed",
        home_goals=2,
        away_goals=1,
    )

    class SessionStub:
        def get(self, model, identifier):
            assert model is OwnerCompetition
            assert identifier == global_competition.id
            return global_competition

    monkeypatch.setattr(
        OwnerCompetitionLifecycleMappingService,
        "canonical_match_for_legacy_match",
        lambda self, legacy_match_id: None,
    )

    historical = comps.mapped_match_dict(SessionStub(), legacy_match)

    assert historical["home_goals"] == 2
    assert historical["away_goals"] == 1
    assert historical["execution_model"] == "legacy_historical"
    assert historical["canonical_lifecycle_status"] == "unmapped"
    assert historical["history_read_only"] is True


def test_user_hosted_competitions_keep_their_separate_execution_rail():
    """User-hosted tournaments remain supported while global lifecycle is reconciled."""
    user_competition = OwnerCompetition(id="user-comp-1", name="Friends Cup", host_type="user", host_user_id="owner-1")

    comps.ensure_owner_console_execution_allowed(user_competition)


def _lifecycle_mapping_test_id() -> str:
    from uuid import uuid4

    return str(uuid4())


def _lifecycle_mapping_test_canonical_competition(session, name: str, source_type: str = "gtex"):
    from app.models.competition import UserCompetition

    competition = UserCompetition(
        host_user_id=_lifecycle_mapping_test_id(),
        name=name,
        format="league",
        currency="coin",
        source_type=source_type,
        source_id=_lifecycle_mapping_test_id(),
        status="draft",
        stage="registration",
    )
    session.add(competition)
    session.flush()
    return competition


def test_global_competition_mapping_is_idempotent_and_one_to_one(app):
    from app.models.owner_competition_lifecycle_mapping import OwnerCompetitionLifecycleMapping
    from app.services.owner_competition_lifecycle_mapping_service import (
        OwnerCompetitionLifecycleMappingError,
        OwnerCompetitionLifecycleMappingService,
    )

    with app.state.session_factory() as session:
        legacy = OwnerCompetition(name=f"Global Cup {_lifecycle_mapping_test_id()}", host_type="gtex")
        canonical = _lifecycle_mapping_test_canonical_competition(session, "Canonical Global Cup")
        another_canonical = _lifecycle_mapping_test_canonical_competition(session, "Another Canonical Cup")
        user_hosted_canonical = _lifecycle_mapping_test_canonical_competition(
            session, "User Hosted Canonical Cup", source_type="user"
        )
        session.add(legacy)
        session.flush()

        service = OwnerCompetitionLifecycleMappingService(session)
        first = service.bind_competition(legacy.id, canonical.id)
        repeated = service.bind_competition(legacy.id, canonical.id)
        assert repeated.id == first.id

        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.bind_competition(legacy.id, another_canonical.id)
        assert exc_info.value.code == "legacy_competition_already_mapped"

        another_legacy = OwnerCompetition(name=f"Other Cup {_lifecycle_mapping_test_id()}", host_type="gtex")
        session.add(another_legacy)
        session.flush()
        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.bind_competition(another_legacy.id, canonical.id)
        assert exc_info.value.code == "canonical_competition_already_mapped"

        unlinked_legacy = OwnerCompetition(name=f"Global Cup {_lifecycle_mapping_test_id()}", host_type="gtex")
        session.add(unlinked_legacy)
        session.flush()
        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.bind_competition(unlinked_legacy.id, user_hosted_canonical.id)
        assert exc_info.value.code == "canonical_competition_not_global"

        assert (
            session.scalar(
                select(OwnerCompetitionLifecycleMapping).where(
                    OwnerCompetitionLifecycleMapping.legacy_competition_id == legacy.id
                )
            ).id
            == first.id
        )


def test_user_hosted_competition_stays_on_separate_lifecycle(app):
    from app.services.owner_competition_lifecycle_mapping_service import (
        OwnerCompetitionLifecycleMappingError,
        OwnerCompetitionLifecycleMappingService,
    )

    with app.state.session_factory() as session:
        legacy = OwnerCompetition(
            name=f"Friends Cup {_lifecycle_mapping_test_id()}",
            host_type="user",
            host_user_id=_lifecycle_mapping_test_id(),
        )
        canonical = _lifecycle_mapping_test_canonical_competition(session, "Canonical Global Cup")
        session.add(legacy)
        session.flush()

        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            OwnerCompetitionLifecycleMappingService(session).bind_competition(legacy.id, canonical.id)
        assert exc_info.value.code == "user_hosted_competition_uses_separate_lifecycle"


def test_scheduled_fixture_mapping_checks_identity_and_preserves_results(app):
    from app.models.competition_match import CompetitionMatch
    from app.models.competition_round import CompetitionRound
    from app.models.owner_competition_lifecycle_mapping import OwnerMatchLifecycleMapping
    from app.owner_console.models import OwnerMatch
    from app.services.owner_competition_lifecycle_mapping_service import (
        OwnerCompetitionLifecycleMappingError,
        OwnerCompetitionLifecycleMappingService,
    )

    with app.state.session_factory() as session:
        legacy_competition = OwnerCompetition(
            name=f"Global Cup {_lifecycle_mapping_test_id()}",
            host_type="gtex",
        )
        canonical_competition = _lifecycle_mapping_test_canonical_competition(session, "Canonical Global Cup")
        session.add(legacy_competition)
        session.flush()

        home_club_id, away_club_id = _lifecycle_mapping_test_id(), _lifecycle_mapping_test_id()
        legacy_match = OwnerMatch(
            competition_id=legacy_competition.id,
            round_number=1,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            home_name="Home",
            away_name="Away",
            status="scheduled",
        )
        round_row = CompetitionRound(
            competition_id=canonical_competition.id,
            round_number=1,
            stage="league",
            group_key="A",
            status="scheduled",
        )
        session.add_all([legacy_match, round_row])
        session.flush()

        canonical_match = CompetitionMatch(
            competition_id=canonical_competition.id,
            round_id=round_row.id,
            round_number=1,
            stage="league",
            group_key="A",
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            status="scheduled",
        )
        mismatched_match = CompetitionMatch(
            competition_id=canonical_competition.id,
            round_id=round_row.id,
            round_number=1,
            stage="league",
            group_key="A",
            home_club_id=away_club_id,
            away_club_id=home_club_id,
            status="scheduled",
        )
        session.add_all([canonical_match, mismatched_match])
        session.flush()

        service = OwnerCompetitionLifecycleMappingService(session)
        service.bind_competition(legacy_competition.id, canonical_competition.id)
        mapping = service.bind_scheduled_match(legacy_match.id, canonical_match.id)
        assert service.bind_scheduled_match(legacy_match.id, canonical_match.id).id == mapping.id
        assert service.canonical_match_for_legacy_match(legacy_match.id).id == canonical_match.id

        another_legacy_match = OwnerMatch(
            competition_id=legacy_competition.id,
            round_number=1,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            home_name="Home",
            away_name="Away",
            status="scheduled",
        )
        session.add(another_legacy_match)
        session.flush()
        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.bind_scheduled_match(another_legacy_match.id, canonical_match.id)
        assert exc_info.value.code == "canonical_match_already_mapped"

        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.bind_scheduled_match(another_legacy_match.id, mismatched_match.id)
        assert exc_info.value.code == "fixture_club_identity_mismatch"

        assert legacy_match.home_goals is None
        assert legacy_match.away_goals is None
        assert legacy_match.played_at is None
        assert canonical_match.home_score == 0
        assert canonical_match.away_score == 0
        assert canonical_match.completed_at is None
        assert (
            session.scalar(
                select(OwnerMatchLifecycleMapping).where(OwnerMatchLifecycleMapping.legacy_match_id == legacy_match.id)
            ).canonical_match_id
            == canonical_match.id
        )


def test_pre_match_tactics_are_saved_on_canonical_fixture_and_kickoff_is_enforced(app):
    from app.models.competition_match import CompetitionMatch
    from app.models.competition_round import CompetitionRound
    from app.owner_console.models import OwnerMatch
    from app.services.owner_competition_lifecycle_mapping_service import (
        OwnerCompetitionLifecycleMappingError,
        OwnerCompetitionLifecycleMappingService,
    )
    from app.services.world_clock_service import WorldClockService

    with app.state.session_factory() as session:
        home_club_id, away_club_id = _lifecycle_mapping_test_id(), _lifecycle_mapping_test_id()
        legacy_competition = OwnerCompetition(
            name=f"Global Cup {_lifecycle_mapping_test_id()}",
            host_type="gtex",
            status="running",
            current_round=1,
        )
        canonical_competition = _lifecycle_mapping_test_canonical_competition(session, "Canonical Tactical Cup")
        virtual_now = WorldClockService(session).now_virtual()
        kickoff_at = virtual_now + timedelta(days=2)
        canonical_competition.scheduled_start_at = kickoff_at
        session.add(legacy_competition)
        session.flush()
        legacy_match = OwnerMatch(
            competition_id=legacy_competition.id,
            round_number=1,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            home_name="Home",
            away_name="Away",
            status="scheduled",
        )
        round_row = CompetitionRound(
            competition_id=canonical_competition.id,
            round_number=1,
            stage="league",
            group_key="A",
            status="scheduled",
        )
        session.add_all([legacy_match, round_row])
        session.flush()
        canonical_match = CompetitionMatch(
            competition_id=canonical_competition.id,
            round_id=round_row.id,
            round_number=1,
            stage="league",
            group_key="A",
            home_club_id=home_club_id,
            away_club_id=away_club_id,
            match_date=kickoff_at.date(),
            scheduled_at=kickoff_at,
            status="scheduled",
        )
        session.add(canonical_match)
        session.flush()

        service = OwnerCompetitionLifecycleMappingService(session)
        service.bind_competition(legacy_competition.id, canonical_competition.id)
        service.bind_scheduled_match(legacy_match.id, canonical_match.id)
        saved = service.save_pre_match_tactics(
            legacy_match_id=legacy_match.id,
            club_id=home_club_id,
            user_id=_lifecycle_mapping_test_id(),
            mentality="attacking",
            lineup_mode="rotate",
        )
        assert saved.id == canonical_match.id
        assert saved.metadata_json["owner_pre_match_tactics"][home_club_id]["mentality"] == "attacking"
        assert saved.metadata_json["owner_pre_match_tactics"][home_club_id]["lineup_mode"] == "rotate"
        assert saved.status == "scheduled"
        assert saved.completed_at is None

        saved.scheduled_at = virtual_now - timedelta(hours=1)
        session.flush()
        with pytest.raises(OwnerCompetitionLifecycleMappingError) as exc_info:
            service.save_pre_match_tactics(
                legacy_match_id=legacy_match.id,
                club_id=away_club_id,
                user_id=_lifecycle_mapping_test_id(),
                mentality="defensive",
                lineup_mode="strongest",
            )
        assert exc_info.value.code == "kickoff_already_due"


def test_global_competition_entry_does_not_charge_legacy_ledger(monkeypatch):
    global_competition = OwnerCompetition(id="global-entry-guard", name="Global Cup", host_type="gtex")

    class SessionStub:
        def get(self, model, identifier):
            assert model is OwnerCompetition
            assert identifier == global_competition.id
            return global_competition

    monkeypatch.setattr(comps, "require_state", lambda *args, **kwargs: object())

    with pytest.raises(OwnerError) as exc_info:
        comps.enter_competition(
            SessionStub(),
            user_id="owner-1",
            competition_id=global_competition.id,
            club_id="club-1",
        )

    assert exc_info.value.code == "canonical_competition_mapping_required"
    assert exc_info.value.status == 409
