from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ingestion.models import Country, Player
from app.models import Base
import app.models  # noqa: F401
from app.models.national_team import NationalTeamCompetition, NationalTeamCompetitionEntry, NationalTeamEntry
from app.models.national_team_tournament import NationalTeamRentalSquadMember
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.national_team_engine.schemas import NationalTeamSquadMemberUpsert
from app.national_team_engine.service import NationalTeamEngineService
from app.national_team_engine.tournament_service import NationalTeamTournamentService
from app.wallets.service import LedgerPosting, WalletService


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def _user(session, suffix: str) -> User:
    user = User(
        id=f"align_{suffix}",
        email=f"{suffix}@example.com",
        username=f"align_{suffix}",
        display_name=f"User {suffix}",
        password_hash="not-used",
        role=UserRole.USER,
    )
    session.add(user)
    session.flush()
    return user


def _competition(session, owner: User, key: str) -> NationalTeamCompetition:
    now = datetime.now(UTC)
    competition = NationalTeamCompetition(
        key=key,
        title="Alignment Cup",
        season_label="2031",
        region_type="global",
        age_band="senior",
        format_type="cup",
        status="published",
        entry_closes_at=now + timedelta(days=2),
        kickoff_at=now + timedelta(days=5),
        metadata_json={
            "entry_mode": "rental_only",
            "entry_fee_coin": "0.0000",
            "minimum_squad_size": 1,
            "maximum_squad_size": 23,
        },
        created_by_user_id=owner.id,
    )
    session.add(competition)
    session.flush()
    return competition


def _assert_same_identity(session, host: NationalTeamEntry) -> None:
    competition_entry = session.scalar(
        select(NationalTeamCompetitionEntry).where(
            NationalTeamCompetitionEntry.competition_id == host.competition_id,
            NationalTeamCompetitionEntry.user_id == host.entry_owner_user_id,
        )
    )
    assert competition_entry is not None
    rental_ids = list(
        session.scalars(
            select(NationalTeamRentalSquadMember.player_id)
            .where(NationalTeamRentalSquadMember.entry_id == host.id)
            .order_by(NationalTeamRentalSquadMember.created_at.asc())
        ).all()
    )
    squad_ids = [member.user_id for member in host.squad_members]
    expected_player_ids = list(dict.fromkeys([*rental_ids, *squad_ids]))
    actual_player_ids = [str(item.get("player_id")) for item in list(competition_entry.squad_json or [])]
    assert competition_entry.user_id == host.entry_owner_user_id
    assert competition_entry.country_code == host.country_code
    assert actual_player_ids == expected_player_ids


def test_submitting_a_squad_copies_user_country_and_player_ids_onto_the_competition_entry():
    with _session() as session:
        owner = _user(session, "owner")
        called_up = _user(session, "called")
        competition = _competition(session, owner, "align-squad")
        host = NationalTeamEntry(
            competition_id=competition.id,
            country_code="NG",
            country_name="Nigeria",
            entry_owner_user_id=owner.id,
            manager_user_id=owner.id,
        )
        session.add(host)
        session.flush()
        NationalTeamEngineService(session).upsert_squad(
            entry_id=host.id,
            actor=owner,
            members=[
                NationalTeamSquadMemberUpsert(
                    user_id=called_up.id,
                    player_name="Called Up",
                    shirt_number=9,
                    role_label="fw",
                )
            ],
        )
        session.refresh(host)
        _assert_same_identity(session, host)


def test_renting_a_player_copies_user_country_and_player_ids_onto_the_competition_entry():
    with _session() as session:
        owner = _user(session, "renter")
        wallet = WalletService()
        account = wallet.get_user_account(session, owner, LedgerUnit.COIN)
        platform = wallet.ensure_platform_account(session, LedgerUnit.COIN)
        wallet.append_transaction(
            session,
            postings=[
                LedgerPosting(account=platform, amount=Decimal("-500.0000"), source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
                LedgerPosting(account=account, amount=Decimal("500.0000"), source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference=f"align-fund:{owner.id}",
            description="Alignment funding",
            actor=owner,
        )
        country = Country(
            source_provider="test",
            provider_external_id="align-ng",
            name="Nigeria",
            alpha2_code="NG",
            alpha3_code="NGA",
            fifa_code="NGA",
            confederation_code="CAF",
        )
        session.add(country)
        session.flush()
        player = Player(
            source_provider="test",
            provider_external_id="align-player",
            country_id=country.id,
            full_name="Jay Jay",
            canonical_display_name="Jay Jay",
            position="ST",
            normalized_position="ST",
            is_real_player=True,
            is_tradable=True,
            market_value_eur=5_000_000.0,
            current_market_reference_value=5_000_000.0,
            dna_profile={"gsi": 76},
        )
        session.add(player)
        session.flush()
        competition = _competition(session, owner, "align-rent")
        host = NationalTeamEntry(
            competition_id=competition.id,
            country_code="NG",
            country_name="Nigeria",
            entry_owner_user_id=owner.id,
            manager_user_id=owner.id,
        )
        session.add(host)
        session.flush()
        NationalTeamTournamentService(session, wallet_service=wallet).rent_player(
            entry_id=host.id,
            actor=owner,
            player_id=player.id,
        )
        session.refresh(host)
        _assert_same_identity(session, host)
        competition_entry = session.scalar(
            select(NationalTeamCompetitionEntry).where(
                NationalTeamCompetitionEntry.competition_id == competition.id,
                NationalTeamCompetitionEntry.user_id == owner.id,
            )
        )
        assert [item["player_id"] for item in competition_entry.squad_json] == [player.id]
