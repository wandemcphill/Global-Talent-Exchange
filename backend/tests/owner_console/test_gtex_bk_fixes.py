"""Targeted regression suite for Phase BK (B1, B2, B3, J-M4 / O-11, O-16 / GAP-J1)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

from sqlalchemy import select

from app.ingestion.models import Player
from app.models.notification_record import NotificationRecord
from app.models.regen import RegenProfile
from app.models.user import User
from app.owner_console import ledger, service, storytelling
from app.owner_console.models import (
    OwnerBroadcastEvent,
    OwnerNewsroomArticle,
    OwnerSquadPlayer,
)


def _claim_and_activate(client, headers, city: str = "Lagos") -> str:
    resp = client.post("/api/owner/clubs/claim", headers=headers, json={"city_name": city, "country_code": "NG"})
    assert resp.status_code == 200, resp.text
    club_id = resp.json()["club_id"]
    act = client.post(f"/api/owner/clubs/{club_id}/activate", headers=headers)
    assert act.status_code == 200, act.text
    return club_id


def test_b1_save_scoped_newsroom_authorization(client, bootstrap_admin_headers, app):
    """B1: GET /owner/newsroom accepts save_context_id and never leaks visibility='save' match reports across saves."""
    club_a_id = _claim_and_activate(client, bootstrap_admin_headers, city="Lagos")
    save_a = f"club:{club_a_id}"
    foreign_save = "competition:foreign-save-999"

    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        assert admin is not None

        other_user = User(
            email="bk_other_owner@test.gtex.local",
            username="bk_other_owner",
            password_hash="hash",
        )
        session.add(other_user)
        session.flush()
        other_user_id = other_user.id

        art_global = OwnerNewsroomArticle(
            club_id=club_a_id,
            save_context_id="global",
            visibility="global",
            category="editorial",
            headline="BK Global League Bulletin",
            subheadline="Public bulletin",
            editorial_narration="Official public bulletin.",
            status="published",
            idempotency_key="bk-b1-global-001",
        )
        art_save_match = OwnerNewsroomArticle(
            club_id=club_a_id,
            save_context_id=save_a,
            visibility="save",
            category="match_report",
            headline="BK Save A Match Report 2-0",
            subheadline="Fixture committed to save A",
            editorial_narration="Save A match report.",
            status="published",
            idempotency_key="bk-b1-save-a-002",
        )
        art_foreign_match = OwnerNewsroomArticle(
            club_id="foreign_club_999",
            save_context_id=foreign_save,
            visibility="save",
            category="match_report",
            headline="BK Foreign Save Match Report 3-1",
            subheadline="Fixture committed to foreign save",
            editorial_narration="Foreign save match report.",
            status="published",
            idempotency_key="bk-b1-foreign-save-003",
        )
        session.add_all([art_global, art_save_match, art_foreign_match])
        session.commit()

        # 1. When save_context_id is None and user_id is None, visibility=="save" articles are excluded
        anon_articles = storytelling.list_newsroom_articles(session, user_id=None, save_context_id=None, limit=50)
        anon_headlines = {a["headline"] for a in anon_articles}
        assert "BK Global League Bulletin" in anon_headlines
        assert "BK Save A Match Report 2-0" not in anon_headlines
        assert "BK Foreign Save Match Report 3-1" not in anon_headlines

        # 2. Other user without save_a access never receives save_a or foreign_save match reports when save_context_id is omitted
        other_articles = storytelling.list_newsroom_articles(
            session, user_id=other_user_id, save_context_id=None, limit=50
        )
        other_headlines = {a["headline"] for a in other_articles}
        assert "BK Global League Bulletin" in other_headlines
        assert "BK Save A Match Report 2-0" not in other_headlines
        assert "BK Foreign Save Match Report 3-1" not in other_headlines

        # 3. Other user explicitly querying save_a cannot read save-scoped match reports
        other_scoped = storytelling.list_newsroom_articles(
            session, user_id=other_user_id, save_context_id=save_a, limit=50
        )
        assert all(a["headline"] != "BK Save A Match Report 2-0" for a in other_scoped)

    # 4. Authorized owner calling GET /api/owner/newsroom with save_context_id=save_a receives save_a match report but not foreign_save
    res_scoped = client.get(
        "/api/owner/newsroom",
        headers=bootstrap_admin_headers,
        params={"save_context_id": save_a, "limit": 50},
    )
    assert res_scoped.status_code == 200, res_scoped.text
    scoped_headlines = {a["headline"] for a in res_scoped.json()["articles"]}
    assert "BK Save A Match Report 2-0" in scoped_headlines
    assert "BK Foreign Save Match Report 3-1" not in scoped_headlines

    # 5. Authorized owner calling GET /api/owner/newsroom without save_context_id still excludes foreign_save match report
    res_unscoped = client.get(
        "/api/owner/newsroom",
        headers=bootstrap_admin_headers,
        params={"limit": 50},
    )
    assert res_unscoped.status_code == 200, res_unscoped.text
    unscoped_headlines = {a["headline"] for a in res_unscoped.json()["articles"]}
    assert "BK Save A Match Report 2-0" in unscoped_headlines
    assert "BK Foreign Save Match Report 3-1" not in unscoped_headlines


def test_b2_broadcast_dict_strips_owner_user_id_and_retains_display_name_and_price(
    client, bootstrap_admin_headers, app
):
    """B2: broadcast_dict removes owner_user_id while retaining owner_display_name and verified_price_gtex (O-09)."""
    club_id = _claim_and_activate(client, bootstrap_admin_headers, city="Lagos")

    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        assert admin is not None
        ledger.record(
            session,
            event_type="owner_capital_injection",
            currency=ledger.GTEX,
            gross=Decimal("25000"),
            source=ledger.PLATFORM_GRANTS,
            destination=ledger.club_account(club_id),
            user_id=admin.id,
            club_id=club_id,
        )
        ev = storytelling.record_verified_broadcast_event(
            session,
            event_type="private_jet_purchase",
            club_id=club_id,
            owner_user_id=admin.id,
            item_name="GTEX Sovereign 900X Private Jet",
            item_model="Sovereign 900X Long-Range VIP",
            verified_price_gtex=Decimal("4800.0000"),
            idempotency_key="bk-b2-jet-001",
        )
        session.commit()
        assert ev is not None
        serialized = storytelling.broadcast_dict(ev)
        assert "owner_user_id" not in serialized
        assert serialized["owner_display_name"]
        assert Decimal(str(serialized["verified_price_gtex"])) == Decimal("4800.0000")

    ticker_res = client.get("/api/owner/ticker", headers=bootstrap_admin_headers)
    assert ticker_res.status_code == 200, ticker_res.text
    events = ticker_res.json()["events"]
    assert len(events) > 0
    for item in events:
        assert "owner_user_id" not in item
        assert "owner_display_name" in item
        assert "verified_price_gtex" in item


def test_b3_canonical_regen_portrait_resolution(app, monkeypatch):
    """B3: resolve_player_portrait_url supports 'assets' and 'items' manifest keys and delegates to RegenPortraitService."""
    # 1. Verify default manifest ('assets' key) resolves to Cloudinary or /generated-media/ (never /api/media/regen-faces/)
    url_assets = storytelling.resolve_player_portrait_url(None, "bk-player-assets-01", "Kelechi Iheanacho")
    assert not url_assets.startswith("/api/media/regen-faces/")
    assert url_assets.startswith("https://res.cloudinary.com/") or url_assets.startswith("/generated-media/")

    # 2. Verify 'items' fallback key and legacy /api/media/regen-faces/ path normalization
    monkeypatch.setattr(
        storytelling,
        "_load_face_manifest",
        lambda: {
            "items": [
                {
                    "relative_path": "/api/media/regen-faces/script_skin_hair/African/Black/africa-black-1.png",
                }
            ]
        },
    )
    url_items_fallback = storytelling.resolve_player_portrait_url(None, "bk-player-items-02", "Samuel Chukwueze")
    assert url_items_fallback == "/generated-media/regen_newgen_faces/script_skin_hair/African/Black/africa-black-1.png"
    assert "/api/media/regen-faces/" not in url_items_fallback

    # 3. Verify delegation to RegenPortraitService when OwnerSquadPlayer.player_ref points to a canonical Regen Player
    with app.state.session_factory() as session:
        canonical_player = Player(
            id="bk-canonical-regen-player-1",
            source_provider="gtex_regen",
            provider_external_id="bk-canonical-regen-player-1",
            full_name="Tunde Bakare",
            position="CM",
            normalized_position="CM",
            date_of_birth=date(2007, 5, 14),
            is_real_player=False,
        )
        regen_profile = RegenProfile(
            id="bk-regen-profile-1",
            regen_id="RGN-BK-001",
            player_id=canonical_player.id,
            linked_unique_card_id="card-bk-001",
            generated_for_club_id="club-bk-001",
            birth_country_code="NG",
            primary_position="CM",
            current_gsi=72,
            current_ability_range_json={"min": 68, "max": 75},
            potential_range_json={"min": 82, "max": 89},
            scout_confidence="high",
            generation_source="academy",
            status="academy_candidate",
            club_quality_score=70.0,
        )
        squad_player = OwnerSquadPlayer(
            id="bk-owner-squad-player-1",
            club_id="club-bk-001",
            player_ref=canonical_player.id,
            name="Tunde Bakare",
            position="MID",
            age=18,
            rating=72,
            potential=86,
            is_regen=True,
        )
        session.add_all([canonical_player, regen_profile, squad_player])
        session.flush()

        delegated_url = storytelling.resolve_player_portrait_url(session, squad_player.id, squad_player.name)
        assert delegated_url
        assert not delegated_url.startswith("/api/media/regen-faces/")
        assert (
            delegated_url.startswith("https://res.cloudinary.com/")
            or "/generated-media/" in delegated_url
        )
        session.rollback()


def test_jm4_o11_notification_deep_link_and_target_serialization(client, bootstrap_admin_headers, app):
    """J-M4 / O-11: Serialized notifications expose deep_link_route, target_type, and target_id with /matches/{resource_id} fallback."""
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        assert admin is not None

        explicit_record = NotificationRecord(
            user_id=admin.id,
            topic="story",
            template_key="owner.inbox.decision",
            resource_type="inbox_item",
            resource_id="inbox-item-77",
            message="Boardroom decision requires your approval.",
            metadata_json={
                "deep_link_route": "/owner/inbox",
                "target_type": "owner_inbox",
                "target_id": "inbox-item-77",
            },
        )
        match_fallback_record = NotificationRecord(
            user_id=admin.id,
            topic="competition",
            template_key="match_live_now",
            resource_type="match",
            resource_id="match-resource-888",
            fixture_id="fixture-888",
            competition_id="comp-1",
            message="Lagos FC vs Kano FC is live now.",
            metadata_json={"match_id": "fixture-888"},
        )
        session.add_all([explicit_record, match_fallback_record])
        session.commit()
        explicit_id = explicit_record.id
        match_id = match_fallback_record.id

    res = client.get("/api/notifications/me", headers=bootstrap_admin_headers, params={"limit": 50})
    assert res.status_code == 200, res.text
    items = {item["notification_id"]: item for item in res.json()}

    assert explicit_id in items
    exp_item = items[explicit_id]
    assert exp_item["deep_link_route"] == "/owner/inbox"
    assert exp_item["target_type"] == "owner_inbox"
    assert exp_item["target_id"] == "inbox-item-77"
    assert exp_item["metadata"]["deep_link_route"] == "/owner/inbox"
    assert exp_item["metadata"]["target_type"] == "owner_inbox"
    assert exp_item["metadata"]["target_id"] == "inbox-item-77"

    assert match_id in items
    m_item = items[match_id]
    assert m_item["deep_link_route"] == "/matches/match-resource-888"
    assert m_item["target_type"] == "match"
    assert m_item["target_id"] == "match-resource-888"
    assert m_item["metadata"]["deep_link_route"] == "/matches/match-resource-888"
    assert m_item["metadata"]["target_type"] == "match"
    assert m_item["metadata"]["target_id"] == "match-resource-888"


def test_o16_gap_j1_owner_routes_registered_in_contract_and_dart_bindings():
    """O-16 / GAP-J1: Verify owner storytelling & inbox routes are registered in shared/api_contract.json and gte_api_contract.g.dart."""
    repo_root = Path(__file__).resolve().parents[3]
    contract_path = repo_root / "shared" / "api_contract.json"
    dart_binding_path = repo_root / "frontend" / "lib" / "data" / "generated" / "gte_api_contract.g.dart"

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    dart_source = dart_binding_path.read_text(encoding="utf-8")

    required_owner_aliases = (
        "/api/owner/ticker",
        "/api/owner/newsroom",
        "/api/owner/inbox",
        "/api/owner/inbox/{item_id}/read",
        "/api/owner/inbox/{item_id}/archive",
        "/api/owner/inbox/{item_id}/decide",
        "/api/owner/clubs/{club_id}/story",
        "/api/owner/clubs/{club_id}/showroom",
        "/api/owner/clubs/{club_id}/showroom/purchase",
        "/api/owner/clubs/{club_id}/showroom/gift",
        "/api/owner/clubs/{club_id}/watchlist",
    )

    owner_routes = contract.get("routes", {}).get("owner", {})
    all_contract_aliases: set[str] = set()
    for entry in owner_routes.values():
        all_contract_aliases.update(entry.get("aliases", []))

    for route_alias in required_owner_aliases:
        canonical = f"/api/v2{route_alias[len('/api'):]}"
        assert route_alias in all_contract_aliases, f"Missing {route_alias} in shared/api_contract.json"
        assert canonical in contract.get("canonical_paths", {}), f"Missing {canonical} in shared/api_contract.json"
        assert f"'{route_alias}': '{canonical}'" in dart_source, f"Missing {route_alias} alias in gte_api_contract.g.dart"
        assert f"'{canonical}'," in dart_source, f"Missing {canonical} canonical path in gte_api_contract.g.dart"
