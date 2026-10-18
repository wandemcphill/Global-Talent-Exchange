"""Public club card redaction and owner decision deadlines."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.admin_engine.service import DEFAULT_FEATURE_FLAGS
from app.club_legacy.flags import legacy_enabled
from app.club_legacy.models import ClubLegacyAsset, ClubLegacyCatalogueItem, ClubLegacyExecutive
from app.club_legacy.operations import showroom as owner_showroom
from app.ingestion.models import Player
from app.models.club_profile import ClubLifecycleStatus, ClubProfile, ClubType
from app.models.player_token_market import PlayerShareHolding, PlayerShareMarket, PlayerSharePriceSnapshot
from app.models.user import PublicAccountType, User
from app.owner_console import alerts
from app.owner_console.models import (
    LedgerEvent,
    OwnerClubState,
    OwnerCompetition,
    OwnerCompetitionEntry,
    OwnerInboxItem,
    OwnerSponsorDeal,
    OwnerSquadPlayer,
)
from app.owner_console.public_showroom import PUBLIC_SHOWROOM_KEYS


def test_response_windows_and_rollout_clock():
    assert alerts.response_hours("transfer_bid") == 48
    assert alerts.response_hours("regen_breakthrough") == 72
    assert alerts.response_hours("competition_invite") == 24
    assert alerts.response_hours("manager_meeting") == 96
    created = alerts.CLOCK_START + timedelta(days=2)
    assert alerts.respond_by(_item("transfer_bid", created)) == created + timedelta(hours=48)
    old = alerts.CLOCK_START - timedelta(days=30)
    assert alerts.respond_by(_item("competition_invite", old)) == alerts.CLOCK_START + timedelta(hours=24)
    assert alerts.respond_by(_item("decision_expired", alerts.CLOCK_START, is_decision=False)) is None
    actions = [{"key": "accept", "label": "Accept bid"}, {"key": "reject", "label": "Reject"}]
    assert alerts.expiry_action(_item("transfer_bid", alerts.CLOCK_START, actions))["key"] == "reject"
    unknown = [{"key": "go", "label": "Go"}, {"key": "skip", "label": "Skip"}]
    assert alerts.expiry_action(_item("brand_new_kind", alerts.CLOCK_START, unknown))["key"] == "skip"


def test_public_showroom_allowlist_for_logged_out_caller(client, app):
    seed = next(item for item in DEFAULT_FEATURE_FLAGS if item["feature_key"] == "club_legacy")
    assert seed["enabled"] is False
    with app.state.session_factory() as session:
        assert legacy_enabled(session) is False
        user = User(
            email="public-card@gte.local",
            username="public_card",
            password_hash="hash",
            display_name="Public Card",
            account_type=PublicAccountType.USER,
        )
        session.add(user)
        session.flush()
        club = ClubProfile(
            owner_user_id=user.id,
            club_name="Lagos Lions",
            short_name="LAL",
            club_type=ClubType.COMMUNITY,
            lifecycle_status=ClubLifecycleStatus.ACTIVE,
            slug="lagos-lions-public",
            primary_color="#0F766E",
            secondary_color="#0F172A",
            accent_color="#F4C24D",
            country_code="NG",
            city_name="Lagos",
            founded_at=date(1998, 4, 1),
            crest_asset_ref="https://cdn.example/lagos.png",
            visibility="public",
        )
        session.add(club)
        session.flush()
        session.add(
            OwnerClubState(
                club_id=club.id,
                owner_user_id=user.id,
                club_name=club.club_name,
                stage="active",
                facilities_json={"academy": 4},
                fans=424242,
                prestige=313131,
            )
        )
        session.add(
            OwnerSponsorDeal(
                club_id=club.id,
                sponsor_name="HiddenSponsorXYZ",
                slot="shirt",
                per_match_gross=Decimal("9000"),
            )
        )
        session.add(
            OwnerSquadPlayer(club_id=club.id, name="HiddenStrikerXYZ", position="ST", age=19, rating=88, is_regen=True)
        )
        session.add(ClubLegacyExecutive(club_id=club.id, role="gm", name="HiddenExecXYZ"))
        catalogue = ClubLegacyCatalogueItem(
            sku="hidden-jet-xyz",
            name="HiddenJetXYZ",
            category="jet",
            price=Decimal("250000"),
            fallback_label="Secret jet",
        )
        session.add(catalogue)
        session.flush()
        session.add(
            ClubLegacyAsset(
                catalogue_id=catalogue.id,
                edition_number=1,
                owner_class="club",
                owner_ref=club.id,
                club_id=club.id,
                status="owned",
            )
        )
        session.add(
            LedgerEvent(
                event_type="launch_grant",
                source_account="platform:grants",
                destination_account=f"club:{club.id}:gtex",
                club_id=club.id,
                user_id=user.id,
                currency="GTEX_COIN",
                gross_amount=Decimal("424242.00"),
                net_amount=Decimal("424242.00"),
                memo="HiddenCashXYZ",
            )
        )
        competition = OwnerCompetition(name="GTEX Cup", tier="Open", status="complete")
        session.add(competition)
        session.flush()
        session.add(
            OwnerCompetitionEntry(
                competition_id=competition.id,
                club_id=club.id,
                club_name=club.club_name,
                owner_user_id=user.id,
                final_position=1,
            )
        )
        session.commit()
        club_id = club.id
        owned = owner_showroom(session, club_id)
        assert any(exhibit["name"] == "HiddenJetXYZ" for exhibit in owned["exhibits"])

    public = client.get("/api/owner/public/showroom/lagos-lions-public")
    assert public.status_code == 200, public.text
    data = public.json()
    assert set(data) == set(PUBLIC_SHOWROOM_KEYS)
    assert data["club_name"] == "Lagos Lions"
    assert data["short_name"] == "LAL"
    assert data["city"] == "Lagos"
    assert data["country_code"] == "NG"
    assert data["primary_color"] == "#0F766E"
    assert data["secondary_color"] == "#0F172A"
    assert data["founded"] == 1998
    assert data["crest_url"] == "https://cdn.example/lagos.png"
    assert len(data["trophies"]) == 1
    assert data["trophies"][0]["competition"] == "GTEX Cup"
    assert data["trophies"][0]["tier"] == "Open"
    assert data["trophies"][0]["position"] == 1
    leaked = public.text
    for secret in (
        "HiddenSponsorXYZ",
        "HiddenStrikerXYZ",
        "HiddenExecXYZ",
        "HiddenJetXYZ",
        "HiddenCashXYZ",
        "424242",
        "313131",
    ):
        assert secret not in leaked
    assert client.get("/api/owner/public/showroom/does-not-exist").status_code == 404
    assert client.get(f"/api/owner/legacy/{club_id}/showroom").status_code == 401


def test_decision_expiry_applies_safe_default_and_warns_once(app):
    created = alerts.CLOCK_START + timedelta(hours=2)
    with app.state.session_factory() as session:
        user = User(
            email="deadline-owner@gte.local",
            username="deadline_owner",
            password_hash="hash",
            display_name="Deadline Owner",
            account_type=PublicAccountType.USER,
        )
        session.add(user)
        session.flush()
        item = OwnerInboxItem(
            user_id=user.id,
            club_id=None,
            kind="transfer_bid",
            sender="Scout",
            title="Bid for Ade",
            what="A bid arrived.",
            why="The player is in demand.",
            actions_json=[
                {"key": "accept", "label": "Accept bid"},
                {"key": "reject", "label": "Reject"},
            ],
            payload_json={},
            is_decision=True,
            status="open",
            created_at=created,
        )
        session.add(item)
        session.commit()
        due = alerts.respond_by(item)
        assert due == created + timedelta(hours=48)

        warned = alerts.sweep_decisions(session, user.id, at=due - timedelta(hours=5))
        session.commit()
        assert warned == {"expired": 0, "warned": 1}
        session.refresh(item)
        assert item.status == "open"
        assert item.payload_json["expiry_warned"] is True
        note = session.scalar(select(OwnerInboxItem).where(OwnerInboxItem.kind == "decision_expiring"))
        assert note is not None and note.is_decision is False and "Reject" in note.what

        again = alerts.sweep_decisions(session, user.id, at=due - timedelta(hours=1))
        session.commit()
        assert again == {"expired": 0, "warned": 0}

        expired = alerts.sweep_decisions(session, user.id, at=due + timedelta(minutes=1))
        session.commit()
        assert expired == {"expired": 1, "warned": 0}
        session.refresh(item)
        assert item.status == "expired"
        assert item.resolution == "expired:reject"
        assert item.outcome_text.startswith("Expired after 48h")
        closed = session.scalar(select(OwnerInboxItem).where(OwnerInboxItem.kind == "decision_expired"))
        assert closed is not None and "Reject" in closed.why
        payload = alerts.service.inbox_dict(item)
        assert payload["respond_by"] is None
        assert payload["status"] == "expired"


def test_wonderkid_price_jump_uses_share_history_and_skips_missing_readings(app):
    at = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    with app.state.session_factory() as session:
        user = User(
            email="wonderkid-alert@gte.local",
            username="wonderkid_alert",
            password_hash="hash",
            display_name="Wonderkid Alert",
            account_type=PublicAccountType.USER,
        )
        session.add(user)
        session.flush()
        kid = _player(session, "kid", "Wonder Kid", date(2008, 1, 15), "gtex_regen")
        quiet = _player(session, "quiet", "Quiet Kid", date(2008, 6, 1), "gtex_regen")
        veteran = _player(session, "vet", "Old Regen", date(1990, 1, 1), "gtex_regen")
        real = _player(session, "real", "Real Teen", date(2008, 3, 1), "manual")
        session.flush()
        markets = {}
        for player in (kid, quiet, veteran, real):
            market = PlayerShareMarket(player_id=player.id, share_price_coin=Decimal("12.0000"), status="active")
            session.add(market)
            markets[player.id] = market
            session.add(PlayerShareHolding(user_id=user.id, player_id=player.id, share_count=25))
        session.flush()
        for player in (kid, veteran, real):
            session.add(
                PlayerSharePriceSnapshot(
                    player_id=player.id,
                    market_id=markets[player.id].id,
                    snapshot_date=date(2026, 10, 8),
                    share_price_coin=Decimal("10.0000"),
                )
            )
        session.commit()

        assert alerts.PRICE_SERIES_READY is True
        created = alerts.sweep_price_jumps(session, at=at)
        session.commit()
        assert created == 1
        item = session.scalar(select(OwnerInboxItem).where(OwnerInboxItem.kind == "wonderkid_price_jump"))
        assert item is not None
        assert item.user_id == user.id
        assert item.is_decision is False
        assert "Wonder Kid" in item.title
        assert item.payload_json["direction"] == "up"
        assert "Quiet Kid" not in item.title
        assert alerts.sweep_price_jumps(session, at=at) == 0


def _player(session, external_id: str, name: str, dob: date, provider: str) -> Player:
    player = Player(
        source_provider=provider,
        provider_external_id=f"alert:{external_id}",
        full_name=name,
        position="ST",
        date_of_birth=dob,
    )
    session.add(player)
    return player


def _item(kind: str, created: datetime, actions=None, is_decision=True) -> OwnerInboxItem:
    return OwnerInboxItem(
        user_id="u1",
        club_id="c1",
        kind=kind,
        sender="s",
        title="t",
        what="w",
        why="y",
        actions_json=actions or [],
        payload_json={},
        is_decision=is_decision,
        created_at=created,
    )
