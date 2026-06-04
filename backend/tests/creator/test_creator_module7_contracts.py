from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.creator.contracts import CreateCampaignContractRequest, CampaignStatusUpdateRequest
from app.creator.module7_service import CreatorModule7ContractService
from app.creator.router import router as creator_router
from app.models.base import Base
from app.models.creator_attention_earnings import CreatorWallet
from app.models.creator_campaign import CreatorCampaign
from app.models.creator_marketplace import (
    CreatorMarketplaceCampaign,
    CreatorMarketplaceOffer,
    CreatorMarketplaceParticipation,
    CreatorMarketplaceReputationScore,
)
from app.models.creator_monetization import CreatorRevenueSettlement
from app.models.creator_profile import CreatorProfile
from app.models.club_profile import ClubProfile, ClubType
from app.models.event_backbone import EventOutbox
from app.models.moderation_report import ModerationReport
from app.models.risk_ops import AuditLog
from app.models.sponsored_clip import SponsoredClip
from app.models.user import User, UserRole
from app.models.wallet import (
    LedgerAccount,
    LedgerAccountKind,
    LedgerBalanceProjection,
    LedgerEntry,
    LedgerTransaction,
    LedgerUnit,
    PayoutRequest,
)


def _build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            CreatorProfile.__table__,
            CreatorCampaign.__table__,
            CreatorWallet.__table__,
            CreatorMarketplaceCampaign.__table__,
            CreatorMarketplaceOffer.__table__,
            CreatorMarketplaceParticipation.__table__,
            CreatorMarketplaceReputationScore.__table__,
            ClubProfile.__table__,
            CreatorRevenueSettlement.__table__,
            SponsoredClip.__table__,
            ModerationReport.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            PayoutRequest.__table__,
            EventOutbox.__table__,
            AuditLog.__table__,
        ],
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _user(user_id: str = "creator-user") -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        display_name="Creator One",
        password_hash="unused",
        role=UserRole.USER,
        is_active=True,
    )


def _profile(user: User, profile_id: str = "creator-profile") -> CreatorProfile:
    return CreatorProfile(
        id=profile_id,
        user_id=user.id,
        handle="creator-one",
        display_name=user.display_name or user.username,
    )


def _club(user: User, club_id: str = "creator-club") -> ClubProfile:
    return ClubProfile(
        id=club_id,
        owner_user_id=user.id,
        club_name="Creator FC",
        short_name="CFC",
        club_type=ClubType.COMMUNITY,
        slug=club_id,
        primary_color="#101820",
        secondary_color="#f2aa4c",
        accent_color="#ffffff",
    )


def _client(session_factory: sessionmaker[Session], current_user: User) -> TestClient:
    app = FastAPI()
    app.include_router(creator_router)

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: current_user
    return TestClient(app)


def _seed_ledger_balance(session: Session, user: User, amount: Decimal) -> LedgerAccount:
    account = LedgerAccount(
        owner_user_id=user.id,
        code=f"user:{user.id}:credit",
        label="Fan Coin",
        unit=LedgerUnit.CREDIT,
        kind=LedgerAccountKind.USER,
    )
    session.add(account)
    session.flush()
    session.add(
        LedgerBalanceProjection(
            account_id=account.id,
            owner_user_id=user.id,
            unit=LedgerUnit.CREDIT,
            balance=amount,
        )
    )
    return account


def test_creator_wallet_returns_blocked_when_no_financial_truth_exists() -> None:
    session_factory = _build_session_factory()
    creator = _user("creator-null-wallet")
    with session_factory() as session:
        session.add_all([creator, _profile(creator, "profile-null-wallet")])
        session.commit()

    with _client(session_factory, creator) as client:
        response = client.get("/api/creator/wallet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "blocked"
    assert payload["balance"] is None
    assert "creator_wallet_balance_unavailable" in payload["blocked_reason"]
    assert payload["withdrawal_available"] is False


def test_campaign_status_changes_and_clip_submission_expose_audit_refs() -> None:
    session_factory = _build_session_factory()
    creator = _user("creator-campaign-audit")
    with session_factory() as session:
        session.add_all([creator, _profile(creator, "profile-campaign-audit")])
        session.commit()

        service = CreatorModule7ContractService(session)
        created = service.create_campaign(
            actor=creator,
            payload=CreateCampaignContractRequest(
                title="Launch Week Push",
                sponsor="Peak Cola",
                brief="Short-form launch clips.",
                budget=Decimal("125.0000"),
            ),
        )
        campaign_id = created.campaign.id
        assert created.audit_reference
        assert session.get(AuditLog, created.audit_reference).action_key == "creator.campaign.created"

        updated = service.update_campaign_status(
            actor=creator,
            campaign_id=campaign_id,
            payload=CampaignStatusUpdateRequest(status="active", reason="brief approved"),
        )
        assert updated.audit_reference
        status_audit = session.get(AuditLog, updated.audit_reference)
        assert status_audit.action_key == "creator.campaign.status_changed"
        assert status_audit.metadata_json["before"]["status"] == "draft"
        assert status_audit.metadata_json["after"]["status"] == "active"
        session.commit()

    with _client(session_factory, creator) as client:
        submit_response = client.post(
            "/api/creator/clips",
            json={
                "campaign_id": campaign_id,
                "title": "Kickoff Clip",
                "url": "https://cdn.example.com/kickoff.mp4",
            },
        )

    assert submit_response.status_code == 201
    submit_payload = submit_response.json()
    assert submit_payload["audit_reference"]
    assert submit_payload["clip"]["status"] == "pending"

    with session_factory() as session:
        audit = session.get(AuditLog, submit_payload["audit_reference"])
        assert audit.action_key == "creator.clip.submitted"
        assert audit.resource_id == submit_payload["clip"]["id"]


def test_clip_contract_surfaces_all_moderation_states() -> None:
    session_factory = _build_session_factory()
    creator = _user("creator-moderation-states")
    with session_factory() as session:
        profile = _profile(creator, "profile-moderation-states")
        campaign = CreatorCampaign(
            id="campaign-moderation-states",
            creator_profile_id=profile.id,
            name="Moderation State Campaign",
            metadata_json={
                "status": "active",
                "submitted_clips": [
                    {
                        "id": f"clip-{state}",
                        "campaign_id": "campaign-moderation-states",
                        "title": f"{state.title()} clip",
                        "url": f"https://cdn.example.com/{state}.mp4",
                        "moderation_status": state,
                        "moderation_note": f"{state} note",
                    }
                    for state in ("pending", "approved", "flagged", "rejected")
                ],
            },
        )
        session.add_all([creator, profile, campaign])
        session.commit()

        payload = CreatorModule7ContractService(session).list_clips(actor=creator)

    assert payload.state == "confirmed"
    assert {clip.status for clip in payload.clips} == {"pending", "approved", "flagged", "rejected"}


def test_creator_withdrawal_blocks_display_only_wallet_and_persists_audit_ref() -> None:
    session_factory = _build_session_factory()
    creator = _user("creator-display-wallet")
    with session_factory() as session:
        session.add_all(
            [
                creator,
                _profile(creator, "profile-display-wallet"),
                CreatorWallet(
                    creator_user_id=creator.id,
                    total_earnings_credit=Decimal("20.0000"),
                    available_balance_credit=Decimal("20.0000"),
                ),
            ]
        )
        session.commit()

    with _client(session_factory, creator) as client:
        response = client.post(
            "/api/creator/wallet/withdraw",
            json={
                "amount": "5.0000",
                "method": "bank_transfer",
                "destination_reference": "bank:creator-display-wallet",
                "unit": "credit",
            },
        )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["state"] == "blocked"
    assert "creator_wallet_ledger_unavailable" in detail["blocked_reason"]
    assert detail["audit_reference"]

    with session_factory() as session:
        audit = session.get(AuditLog, detail["audit_reference"])
        assert audit is not None
        assert audit.action_key == "creator.withdrawal.requested"
        assert audit.outcome == "blocked"


def test_creator_withdrawal_uses_ledger_truth_and_returns_audit_ref() -> None:
    session_factory = _build_session_factory()
    creator = _user("creator-ledger-wallet")
    with session_factory() as session:
        session.add_all([creator, _profile(creator, "profile-ledger-wallet")])
        _seed_ledger_balance(session, creator, Decimal("100.0000"))
        session.commit()

    with _client(session_factory, creator) as client:
        wallet_response = client.get("/api/creator/wallet")
        withdraw_response = client.post(
            "/api/creator/wallet/withdraw",
            json={
                "amount": "20.0000",
                "method": "bank_transfer",
                "destination_reference": "bank:creator-ledger-wallet",
                "unit": "credit",
            },
        )

    assert wallet_response.status_code == 200
    assert wallet_response.json()["state"] == "confirmed"
    assert wallet_response.json()["balance"]["available"] == "100.0000"
    assert wallet_response.json()["withdrawal_available"] is True

    assert withdraw_response.status_code == 201
    payload = withdraw_response.json()
    assert payload["action_state"] == "completed"
    assert payload["amount"] == "20.0000"
    assert payload["fee_amount"] == "5.0000"
    assert payload["total_debit"] == "25.0000"
    assert payload["audit_reference"]

    with session_factory() as session:
        payout = session.get(PayoutRequest, payload["payout_request_id"])
        audit = session.get(AuditLog, payload["audit_reference"])
        assert payout is not None
        assert payout.amount == Decimal("20.0000")
        assert payout.unit == LedgerUnit.CREDIT
        assert audit is not None
        assert audit.action_key == "creator.withdrawal.requested"
        assert audit.resource_id == payout.id


def test_creator_settlements_surface_direct_creator_revenue_truth() -> None:
    session_factory = _build_session_factory()
    creator = _user("creator-direct-settlement")
    with session_factory() as session:
        profile = _profile(creator, "profile-direct-settlement")
        club = _club(creator, "club-direct-settlement")
        session.add_all(
            [
                creator,
                profile,
                club,
                CreatorRevenueSettlement(
                    id="settlement-direct-1",
                    season_id="season-direct-1",
                    competition_id="competition-direct-1",
                    match_id="match-direct-1",
                    home_club_id=club.id,
                    away_club_id="away-club-direct-1",
                    total_revenue_coin=Decimal("50.0000"),
                    total_creator_share_coin=Decimal("30.0000"),
                    home_creator_share_coin=Decimal("30.0000"),
                    away_creator_share_coin=Decimal("0.0000"),
                    review_status="approved",
                    metadata_json={"home_ledger_transaction_id": "ledger-direct-1"},
                ),
            ]
        )
        session.commit()

        payload = CreatorModule7ContractService(session).list_settlements(actor=creator)

    assert payload.state == "confirmed"
    assert payload.gap_reasons == ()
    assert len(payload.settlements) == 1
    settlement = payload.settlements[0]
    assert settlement.id == "settlement-direct-1:home"
    assert settlement.campaign_id == "competition-direct-1"
    assert settlement.amount == Decimal("30.0000")
    assert settlement.status == "approved"
    assert settlement.wallet_transaction_id == "ledger-direct-1"
    assert settlement.degraded_reason is None


def test_creator_settlements_degrade_only_when_direct_wallet_transaction_is_missing() -> None:
    session_factory = _build_session_factory()
    creator = _user("creator-missing-settlement-transaction")
    with session_factory() as session:
        profile = _profile(creator, "profile-missing-settlement-transaction")
        home_club = _club(creator, "club-missing-settlement-transaction")
        session.add_all(
            [
                creator,
                profile,
                home_club,
                CreatorRevenueSettlement(
                    id="settlement-missing-transaction",
                    season_id="season-missing-transaction",
                    competition_id="competition-missing-transaction",
                    match_id="match-missing-transaction",
                    home_club_id=home_club.id,
                    away_club_id="away-club-missing-transaction",
                    total_revenue_coin=Decimal("80.0000"),
                    total_creator_share_coin=Decimal("42.0000"),
                    home_creator_share_coin=Decimal("42.0000"),
                    away_creator_share_coin=Decimal("0.0000"),
                    review_status="approved",
                    metadata_json={},
                ),
                CreatorRevenueSettlement(
                    id="settlement-zero-without-transaction",
                    season_id="season-zero-without-transaction",
                    competition_id="competition-zero-without-transaction",
                    match_id="match-zero-without-transaction",
                    home_club_id=home_club.id,
                    away_club_id="away-club-zero-without-transaction",
                    total_revenue_coin=Decimal("10.0000"),
                    total_creator_share_coin=Decimal("0.0000"),
                    home_creator_share_coin=Decimal("0.0000"),
                    away_creator_share_coin=Decimal("0.0000"),
                    review_status="approved",
                    metadata_json={},
                ),
            ]
        )
        session.commit()

        payload = CreatorModule7ContractService(session).list_settlements(actor=creator)

    assert payload.state == "degraded"
    by_id = {item.id: item for item in payload.settlements}
    assert "creator_settlement_wallet_transaction_missing" in (
        by_id["settlement-missing-transaction:home"].degraded_reason or ""
    )
    assert by_id["settlement-zero-without-transaction:home"].degraded_reason is None
