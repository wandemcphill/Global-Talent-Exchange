"""Exit gate for Club Legacy phase 6."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.admin_engine.service import AdminEngineService
from app.club_legacy.delegation import LegacyError
from app.club_legacy.full.phase6 import COMMERCIAL_ZONES, commercial_inventory, preview_kit, suggest_kit
from app.club_legacy.models import ClubLegacyAuditEvent, ClubLegacyKitVersion, ClubLegacySponsorZone
from app.club_legacy.operations import approve_sponsor, offer_sponsor, publish_kit, renew_sponsor, report_delivery
from app.models.admin_rules import AdminFeatureFlag
from app.models.user import User
from app.models.wallet import LedgerTransaction


def _enable(app) -> None:
    with app.state.session_factory() as session:
        AdminEngineService(session).seed_defaults()
        flag = session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == "club_legacy"))
        flag.enabled = True
        session.commit()


def _claim(client, headers) -> str:
    response = client.post(
        "/api/owner/clubs/claim", headers=headers, json={"city_name": "Lagos", "country_code": "NG"}
    )
    assert response.status_code == 200, response.text
    return response.json()["club_id"]


def _admin(session) -> User:
    return session.scalar(select(User).where(User.email == "admin@test.gtex.local"))


def _kits(session, club_id: str) -> int:
    return int(
        session.scalar(select(func.count()).select_from(ClubLegacyKitVersion).where(ClubLegacyKitVersion.club_id == club_id))
        or 0
    )


def test_contract_names_zones_preview_cannot_publish_and_publish_needs_a_human(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        inventory = [item["zone"] for item in commercial_inventory()]
        assert inventory == list(COMMERCIAL_ZONES)
        contract = offer_sponsor(
            session,
            club_id=club_id,
            user_id=admin.id,
            sponsor_name="Harbour Trust",
            placement="shirt_front",
            fee="2500",
            zones=["shirt_front", "sleeve", "board"],
        )
        zones = session.scalars(
            select(ClubLegacySponsorZone.zone).where(ClubLegacySponsorZone.contract_id == contract.id)
        ).all()
        assert set(zones) == {"shirt_front", "sleeve", "board"}
        assert contract.fee == Decimal("2500.00")
        preview = preview_kit(session, club_id=club_id, user_id=admin.id, contract_id=contract.id, template_name="Home")
        assert preview["published"] is False
        assert preview["zones"] == {"board": "board", "shirt_front": "shirt_front", "sleeve": "sleeve"}
        assert _kits(session, club_id) == 0
        suggestion = suggest_kit(session, club_id=club_id, user_id=admin.id, contract_id=contract.id)
        assert suggestion["can_publish"] is False
        assert suggestion["published"] is False
        assert set(suggestion["zones"]) == set(COMMERCIAL_ZONES)
        assert _kits(session, club_id) == 0
        with pytest.raises(LegacyError) as early:
            publish_kit(
                session,
                club_id=club_id,
                user_id=admin.id,
                contract_id=contract.id,
                template_name="Home",
                zones=preview["zones"],
            )
        assert early.value.code == "sponsor_not_approved"
        approve_sponsor(session, contract_id=contract.id, user_id=admin.id)
        suggestion = suggest_kit(session, club_id=club_id, user_id=admin.id, contract_id=contract.id)
        assert suggestion["can_publish"] is False
        assert _kits(session, club_id) == 0
        with pytest.raises(LegacyError) as mismatch:
            publish_kit(
                session,
                club_id=club_id,
                user_id=admin.id,
                contract_id=contract.id,
                template_name="Home",
                zones={"shirt_front": "shirt_front"},
            )
        assert mismatch.value.code == "placement_mismatch"
        kit = publish_kit(
            session,
            club_id=club_id,
            user_id=admin.id,
            contract_id=contract.id,
            template_name="Home",
            zones=preview["zones"],
        )
        assert kit.status == "published"
        assert kit.zones_json == preview["zones"]
        assert _kits(session, club_id) == 1
        session.commit()
    zones = client.get(f"/api/owner/legacy/{club_id}/sponsors/zones", headers=bootstrap_admin_headers)
    assert zones.status_code == 200, zones.text
    assert [item["zone"] for item in zones.json()["zones"]] == ["shirt_front", "sleeve", "board"]


def test_delivery_and_renewal_write_ledger_and_audit_rows(client, bootstrap_admin_headers, app):
    club_id = _claim(client, bootstrap_admin_headers)
    _enable(app)
    with app.state.session_factory() as session:
        admin = _admin(session)
        contract = offer_sponsor(
            session,
            club_id=club_id,
            user_id=admin.id,
            sponsor_name="Lagoon Board",
            placement="board",
            fee="800",
            zones=["board"],
        )
        approve_sponsor(session, contract_id=contract.id, user_id=admin.id)
        approve_sponsor(session, contract_id=contract.id, user_id=admin.id)
        assert (
            session.scalar(
                select(func.count()).select_from(LedgerTransaction).where(LedgerTransaction.idempotency_key == f"sponsor:{contract.id}")
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(ClubLegacyAuditEvent)
                .where(ClubLegacyAuditEvent.action == "sponsor_payment")
            )
            >= 1
        )
        report_delivery(
            session,
            contract_id=contract.id,
            user_id=admin.id,
            impressions=1200,
            note="Board ran for the full friendly.",
        )
        assert contract.impressions == 1200
        assert contract.delivery_report == "Board ran for the full friendly."
        assert contract.status == "completed"
        delivery = session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == f"delivery:{contract.id}")
        )
        assert delivery is not None
        audit = session.scalar(
            select(ClubLegacyAuditEvent).where(
                ClubLegacyAuditEvent.action == "sponsor_delivery",
                ClubLegacyAuditEvent.club_id == club_id,
            )
        )
        assert audit is not None
        assert audit.detail_json["impressions"] == 1200
        assert audit.detail_json["note"] == "Board ran for the full friendly."
        renewed = renew_sponsor(session, contract_id=contract.id, user_id=admin.id)
        assert renewed.id != contract.id
        assert renewed.renewed_from_id == contract.id
        assert renewed.status == "offered"
        renewed_zones = session.scalars(
            select(ClubLegacySponsorZone.zone).where(ClubLegacySponsorZone.contract_id == renewed.id)
        ).all()
        assert renewed_zones == ["board"]
        session.commit()
