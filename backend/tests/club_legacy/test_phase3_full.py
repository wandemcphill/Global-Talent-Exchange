"""Full phase 3 exit gate: club page, net worth, ledger history, and showroom."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.full.phase3 import club_page, financial_history, owner_net_worth
from app.club_legacy.models import ClubLegacyAsset, ClubLegacyCatalogueItem
from app.club_legacy.operations import club_valuation, offer_sponsor, purchase_asset, set_stake, showroom
from app.models.admin_rules import AdminFeatureFlag
from app.models.club_dynasty_progress import ClubDynastyProgress
from app.models.club_trophy import ClubTrophy
from app.models.user import User
from app.models.wallet import LedgerEntry


def _enable(app) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        flag.enabled = True
        session.commit()


def _claim(client, headers) -> str:
    response = client.post("/api/owner/clubs/claim", headers=headers, json={"city_name": "Lagos", "country_code": "NG"})
    assert response.status_code == 200, response.text
    return response.json()["club_id"]


def test_club_page_uses_real_records_and_survives_a_model_failure(client, bootstrap_admin_headers, app, monkeypatch):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        page = club_page(session, club_id)
        assert page["location"]["city"] == "Lagos"
        assert page["location"]["country_code"] == "NG"
        assert page["location"]["continent_code"] == "AF"
        assert page["honours"] == []
        assert page["history"] == []
        assert page["commercial"] == []
        assert page["roster"]
        assert page["sections"]["facilities"]
        assert page["staff"] == []
        assert "personal_assets" not in page
        assert page["showroom_fallback"] == "static-card"
        assert "Champions League" not in str(page["honours"])
        session.add(
            ClubTrophy(
                club_id=club_id,
                trophy_type="cup",
                trophy_name="Lagos Cup",
                competition_source="Lagos Cup",
                season_label="2026",
            )
        )
        progress = session.scalar(select(ClubDynastyProgress).where(ClubDynastyProgress.club_id == club_id))
        progress.seasons_completed = 1
        progress.last_season_label = "2026"
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        offer_sponsor(
            session, club_id=club_id, user_id=admin.id, sponsor_name="Harbour Trust", placement="front", fee="100"
        )
        session.flush()
        filled = club_page(session, club_id)
        assert filled["honours"][0]["name"] == "Lagos Cup"
        assert filled["history"][0]["label"] == "2026"
        assert filled["commercial"][0]["name"] == "Harbour Trust"
        assert filled["roster"][0]["name"]

        def boom(*args, **kwargs):
            raise RuntimeError("glb failed")

        monkeypatch.setattr("app.club_legacy.operations.showroom", boom)
        survived = club_page(session, club_id)
        assert survived["honours"][0]["name"] == "Lagos Cup"
        assert survived["showroom_fallback"] == "static-card"
        assert survived["showroom"]["fallback"] == "static-card"
        assert survived["showroom"]["model_error"] == "RuntimeError"
        session.commit()

    opened = client.get(f"/api/owner/legacy/{club_id}/page", headers=bootstrap_admin_headers)
    assert opened.status_code == 200, opened.text
    assert opened.json()["honours"]
    assert "personal_assets" not in opened.json()


def test_net_worth_is_stake_plus_personal_assets_and_history_is_the_ledger(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = session.scalar(select(User).where(User.email == "admin@test.gtex.local"))
        set_stake(session, club_id=club_id, holder_user_id=admin.id, percentage="40")
        purchase_asset(
            session,
            club_id=club_id,
            user_id=admin.id,
            sku="gtex-watch-icon",
            owner_class="owner",
            idempotency_key="phase3-watch",
        )
        valuation = club_valuation(session, club_id)
        worth = owner_net_worth(session, admin.id)
        equity = (valuation * Decimal("0.40")).quantize(Decimal("0.01"))
        assert Decimal(worth["equity"]) == equity
        assert Decimal(worth["equity"]) != valuation
        assert Decimal(worth["personal_assets"]) > 0
        expected = (
            Decimal(worth["personal_cash"]) + Decimal(worth["personal_assets"]) + Decimal(worth["equity"])
        ).quantize(Decimal("0.01"))
        assert Decimal(worth["net_worth"]) == expected
        history = financial_history(session, club_id)
        assert history
        entry_ids = {row["entry_id"] for row in history}
        stored = session.scalars(select(LedgerEntry.id).where(LedgerEntry.id.in_(entry_ids))).all()
        assert set(stored) == entry_ids
        lifetime = sum((abs(Decimal(row["amount"])) for row in history), Decimal("0"))
        assert Decimal(worth["net_worth"]) != lifetime
        room = showroom(session, club_id)
        labels = {item["ownership_label"] for item in room["exhibits"]}
        assert "Club" in labels or "Not owned" in labels
        assert "Not owned" in labels
        watch = session.scalar(select(ClubLegacyCatalogueItem).where(ClubLegacyCatalogueItem.sku == "gtex-watch-icon"))
        session.add(
            ClubLegacyAsset(
                catalogue_id=watch.id,
                edition_number=7,
                owner_class="player",
                owner_ref="player-7",
                club_id=club_id,
                status="owned",
            )
        )
        session.add(
            ClubLegacyAsset(
                catalogue_id=watch.id,
                edition_number=8,
                owner_class="manager",
                owner_ref="manager-8",
                club_id=club_id,
                status="owned",
            )
        )
        session.flush()
        again = showroom(session, club_id)
        owned = {item["ownership_label"] for item in again["exhibits"]}
        assert {"Owner", "Player", "Manager", "Not owned"} <= owned
        assert again["fallback"] == "static-card"
        session.commit()

    finance = client.get(f"/api/owner/legacy/full/phase3/{club_id}/finance", headers=bootstrap_admin_headers)
    assert finance.status_code == 200, finance.text
    assert finance.json()["entries"]
    worth_response = client.get(f"/api/owner/legacy/full/phase3/{club_id}/net-worth", headers=bootstrap_admin_headers)
    assert worth_response.status_code == 200, worth_response.text
    assert Decimal(worth_response.json()["net_worth"]) != Decimal(worth_response.json()["club_valuation"])
