from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401
from backend.app.governance_engine.service import GovernanceEngineService
from backend.app.models.base import Base
from backend.app.models.club_profile import ClubProfile
from backend.app.models.creator_share_market import CreatorClubShareHolding, CreatorClubShareMarket
from backend.app.models.governance_engine import GovernanceProposalScope, GovernanceVoteChoice
from backend.app.models.user import User


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        yield db_session


def _create_user(session, *, user_id: str, email: str, username: str) -> User:
    user = User(id=user_id, email=email, username=username, password_hash="hashed")
    session.add(user)
    session.flush()
    return user


def test_governance_uses_canonical_creator_shares_for_votes_and_panel(session) -> None:
    owner = _create_user(session, user_id="owner-gov", email="owner-gov@example.com", username="owner-gov")
    fan = _create_user(session, user_id="fan-gov", email="fan-gov@example.com", username="fan-gov")
    session.add(
        ClubProfile(
            id="club-gov",
            owner_user_id=owner.id,
            club_name="Governance Club FC",
            short_name="GCF",
            slug="governance-club-fc",
            crest_asset_ref=None,
            primary_color="#112233",
            secondary_color="#ddeeff",
            accent_color="#44aa66",
            home_venue_name="Governance Arena",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            description="Club governance test club",
            visibility="public",
            founded_at=None,
        )
    )
    session.add(
        CreatorClubShareMarket(
            id="market-gov",
            club_id="club-gov",
            creator_user_id=owner.id,
            issued_by_user_id=owner.id,
            status="active",
            share_price_coin=Decimal("5.0000"),
            max_shares_issued=100,
            shares_sold=10,
            max_shares_per_fan=100,
            creator_controlled_shares=101,
            shareholder_revenue_share_bps=2000,
            total_purchase_volume_coin=Decimal("50.0000"),
            total_revenue_distributed_coin=Decimal("0.0000"),
            metadata_json={"governance_policy": {"proposal_share_threshold": 5, "quorum_share_bps": 1000, "max_holder_bps": 1000}},
        )
    )
    session.add(
        CreatorClubShareHolding(
            id="holding-gov",
            market_id="market-gov",
            club_id="club-gov",
            user_id=fan.id,
            share_count=10,
            total_spent_coin=Decimal("50.0000"),
            revenue_earned_coin=Decimal("0.0000"),
            metadata_json={},
        )
    )
    session.flush()

    service = GovernanceEngineService(session)
    proposal = service.create_proposal(
        proposer=fan,
        club_id="club-gov",
        scope=GovernanceProposalScope.CLUB,
        title="Upgrade governance rules",
        summary="Increase the transparency requirements for club governance actions.",
        category="governance",
        minimum_tokens_required=1,
        quorum_token_weight=0,
        voting_ends_at_iso=None,
        metadata_json={},
    )
    owner_vote_proposal, owner_vote = service.cast_vote(
        proposal_id=proposal.id,
        voter=owner,
        choice=GovernanceVoteChoice.YES,
    )
    final_proposal, fan_vote = service.cast_vote(
        proposal_id=proposal.id,
        voter=fan,
        choice=GovernanceVoteChoice.NO,
    )
    panel = service.build_club_panel(club_id="club-gov", user=fan)

    assert proposal.minimum_tokens_required == 5
    assert proposal.quorum_token_weight == 20
    assert proposal.metadata_json["governance_unit"] == "creator_club_shares"
    assert owner_vote.token_weight == 101
    assert owner_vote.influence_weight == 101
    assert owner_vote.metadata_json["is_owner_vote"] is True
    assert fan_vote.influence_weight == 10
    assert owner_vote_proposal.yes_weight == 101
    assert final_proposal.no_weight == 10
    assert panel["viewer_can_vote"] is True
    assert panel["viewer_share_count"] == 10
    assert panel["policy"]["proposal_share_threshold"] == 5
    assert panel["anti_takeover_cap_share_count"] == 20
    assert panel["open_proposal_count"] == 1
