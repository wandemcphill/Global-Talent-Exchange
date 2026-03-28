from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import ensure_database_schema_current
from app.federations.service import FederationService
from app.ingestion.models import Country, Player
from app.models.club_profile import ClubProfile
from app.models.federation import FederationCompetitionType, FederationSanctionType, FederationVoteType
from app.models.player_contract import PlayerContract
from app.models.real_world_hub import RealityMode
from app.models.user import User, UserRole


def test_federation_service_governance_and_rules_work_with_sqlite_datetimes(tmp_path) -> None:
    database_path = Path(tmp_path) / "federation-service.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    ensure_database_schema_current(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        owner = User(
            email="owner@example.com",
            username="owner",
            password_hash="x",
            role=UserRole.USER,
        )
        session.add(owner)
        session.flush()

        nigeria = Country(
            source_provider="test",
            provider_external_id="ng-federation",
            name="Nigeria",
            alpha2_code="NG",
            alpha3_code="NGA",
            fifa_code="NGA",
        )
        spain = Country(
            source_provider="test",
            provider_external_id="es-federation",
            name="Spain",
            alpha2_code="ES",
            alpha3_code="ESP",
            fifa_code="ESP",
        )
        session.add_all([nigeria, spain])
        session.flush()

        club = ClubProfile(
            owner_user_id=owner.id,
            club_name="Lagos Comets",
            short_name="COM",
            slug="lagos-comets-fed",
            primary_color="#0044aa",
            secondary_color="#ffffff",
            accent_color="#ffcc00",
            country_code="NG",
            visibility="public",
            founded_at=date(1999, 1, 1),
        )
        session.add(club)
        session.flush()

        regen_player = Player(
            source_provider="seed",
            provider_external_id="regen-fed-1",
            full_name="Ayo Regen",
            position="CM",
            normalized_position="cm",
            country_id=nigeria.id,
            current_club_profile_id=club.id,
            is_real_player=False,
        )
        real_player = Player(
            source_provider="seed",
            provider_external_id="real-fed-1",
            full_name="Real Ace",
            position="ST",
            normalized_position="st",
            country_id=spain.id,
            current_club_profile_id=club.id,
            is_real_player=True,
        )
        session.add_all([regen_player, real_player])
        session.flush()

        session.add(
            PlayerContract(
                player_id=regen_player.id,
                club_id=club.id,
                status="active",
                wage_amount=Decimal("1000.00"),
                signed_on=date.today(),
                starts_on=date.today(),
                ends_on=date.today() + timedelta(days=365),
            )
        )
        session.commit()

        service = FederationService(session=session)
        federation = service.create_federation(
            actor=owner,
            name="Atlantic Federation",
            structure_json={"divisions": 1},
            rules_json={
                "competition_player_mode": "pure_regen",
                "squad_limits": {"max_active_contracts": 1},
                "salary_cap": {"max_total_wage": "1200.00"},
                "transfer_restrictions": {"max_fee": "100.00"},
                "nationality_rules": {"max_foreign_players": 0, "home_country_codes": ["NG"]},
                "ownership": {"require_governance_vote_for_sale": True},
                "economy": {"federation_share_bps": 2000},
            },
            is_public=True,
            default_reality_mode=RealityMode.PURE_REGEN,
            metadata_json={"region_code": "west_africa", "region_label": "West Africa"},
        )
        session.commit()

        league = service.create_league(
            actor=owner,
            federation_id=federation.id,
            name="Atlantic Premier",
            competition_type=FederationCompetitionType.LEAGUE,
            format="round-robin",
            divisions_json=[{"name": "Division 1"}],
            promotion_relegation_rules_json={"spots": 1},
            entry_requirements_json={},
            governance_rules_override_json={},
            season_label="2026",
            metadata_json={},
        )
        membership = service.create_membership(
            actor=owner,
            federation_id=federation.id,
            club_id=club.id,
            user_id=owner.id,
            role="commissioner",
            auto_activate=True,
            entry_requirements_json={},
            metadata_json={},
        )
        proposal = service.create_proposal(
            actor=owner,
            federation_id=federation.id,
            league_id=league.id,
            proposal_type="rule_change",
            title="Allow ownership transfer by vote",
            summary="Governance proposal to document ownership transfer approval flow.",
            payload_json={"rules_patch": {"ownership": {"require_governance_vote_for_sale": True}}},
            voting_ends_at=datetime.now(UTC) + timedelta(days=1),
            metadata_json={},
        )
        session.commit()
        session.expire_all()

        owner = session.get(User, owner.id)
        assert owner is not None
        proposal, vote = service.cast_vote(
            actor=owner,
            proposal_id=proposal.id,
            vote_type=FederationVoteType.YES,
            comment="approved",
        )
        sanction = service.apply_sanction(
            actor=owner,
            federation_id=federation.id,
            league_id=league.id,
            club_id=club.id,
            player_id=real_player.id,
            sanction_type=FederationSanctionType.FINE,
            reason="Rule breach for test coverage",
            fine_amount=Decimal("50.00"),
            points_deduction=0,
            suspension_matches=0,
            ends_at=None,
            metadata_json={},
        )
        validation = service.validate_action(
            federation_id=federation.id,
            league_id=league.id,
            action_type="transfer_bid",
            club_id=club.id,
            player_id=real_player.id,
            proposed_fee=Decimal("250.00"),
            proposed_wage=Decimal("500.00"),
            source_reference="smoke-transfer",
            metadata_json={},
        )
        revenue = service.distribute_revenue(
            federation_id=federation.id,
            source_type="broadcast_rights",
            source_reference=league.linked_competition_id,
            gross_amount=Decimal("1000.00"),
            federation_share_bps=None,
            metadata_json={},
        )
        narratives = service.generate_narratives(federation.id)
        dashboard = service.build_dashboard(federation.id)
        governance = service.build_governance_view(federation.id)
        regional_tournaments = service.list_regional_tournaments()

        assert membership.status == "active"
        assert vote.weight == 2
        assert proposal.yes_votes == 2
        assert sanction.club_id == club.id
        assert validation["allowed"] is False
        assert {item["code"] for item in validation["violations"]} == {
            "real_player_blocked",
            "squad_limit_exceeded",
            "salary_cap_exceeded",
            "transfer_fee_exceeded",
            "nationality_rule_violation",
        }
        assert revenue.federation_share == Decimal("200.0000")
        assert len(narratives) == 3
        assert any(member["club_id"] == club.id for member in dashboard["members"])
        assert len(governance["proposals"]) == 1
        assert len(governance["votes"]) == 1
        assert len(governance["sanctions"]) == 1
        assert regional_tournaments[0]["region_code"] == "west_africa"
        assert regional_tournaments[0]["region_label"] == "West Africa"
        assert regional_tournaments[0]["active_league_count"] == 1
    finally:
        session.close()
        engine.dispose()
