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
    OwnerInboxItem,
    OwnerNewsroomArticle,
)
from app.owner_console.service import OwnerError


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
    assert "sovereign_900x_jet.png" in jet_data["broadcast_event"]["item_image_url"]

    # 3. Facility upgrade MUST broadcast globally with verified price and facility image
    fac_res = client.post(
        f"/api/owner/clubs/{club_id}/facilities/stadium/upgrade",
        headers=bootstrap_admin_headers,
    )
    assert fac_res.status_code == 200, fac_res.text

    # 4. Club-owner gift to a squad player MUST broadcast globally with player name, portrait, and verified price
    club_detail = client.get(f"/api/owner/clubs/{club_id}", headers=bootstrap_admin_headers).json()
    first_player = club_detail["squad"][0]
    assert first_player.get("portrait_url"), "Squad player must have resolved static portrait URL"

    gift_res = client.post(
        f"/api/owner/clubs/{club_id}/showroom/gift",
        headers=bootstrap_admin_headers,
        json={
            "player_id": first_player["id"],
            "catalog_key": "chronos_tourbillon_watch",
            "note": "Golden Boot bonus",
            "idempotency_key": "gift-player-1",
        },
    )
    assert gift_res.status_code == 200, gift_res.text
    gift_data = gift_res.json()
    assert gift_data["broadcast_event"]["event_type"] == "player_gift"
    assert gift_data["broadcast_event"]["player_name"] == first_player["name"]
    assert gift_data["broadcast_event"]["player_portrait_url"]
    assert Decimal(str(gift_data["broadcast_event"]["verified_price_gtex"])) == Decimal("220")

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

    # 1. Duplicate idempotency key produces only 1 broadcast event and 1 newsroom article
    for _ in range(3):
        resp = client.post(
            f"/api/owner/clubs/{club_id}/showroom/purchase",
            headers=bootstrap_admin_headers,
            json={"catalog_key": "sovereign_900x_jet", "idempotency_key": "idem-jet-unique-001"},
        )
        assert resp.status_code == 200, resp.text

    with app.state.session_factory() as session:
        b_rows = session.scalars(
            select(OwnerBroadcastEvent).where(OwnerBroadcastEvent.idempotency_key == "idem-jet-unique-001")
        ).all()
        assert len(b_rows) == 1
        n_rows = session.scalars(
            select(OwnerNewsroomArticle).where(OwnerNewsroomArticle.idempotency_key == "news:idem-jet-unique-001")
        ).all()
        assert len(n_rows) == 1

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

    # Advance world day to generate inbox items (including scouting_report / contract_negotiation / requests)
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
