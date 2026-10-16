from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ingestion.models import Country, InjuryStatus, Player
from app.models import Base
from app.models.federation import FederationSanction, FederationSanctionType
from app.models.national_team import NationalTeamCompetition, NationalTeamEntry
from app.models.player_contract import PlayerContract
from app.models.user import User
from app.models.wallet import (
    LedgerEntryReason,
    LedgerSourceTag,
    LedgerUnit,
)
from app.national_team_engine.competition_lifecycle_service import (
    NationalCompetitionLifecycleError,
    NationalCompetitionLifecycleService,
)
from app.national_team_engine.tournament_service import (
    NationalTeamTournamentError,
    NationalTeamTournamentService,
)
from app.wallets.service import LedgerPosting, WalletService


def _build_session_factory(database_path: Path) -> sessionmaker:
    engine = create_engine(f"sqlite:///{database_path}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    return SessionLocal


def _create_user(session, email_prefix: str) -> User:
    uid = uuid.uuid4().hex[:6]
    user = User(
        email=f"{email_prefix}_{uid}@gtex.test",
        username=f"{email_prefix}_{uid}",
        full_name=f"User {email_prefix}",
        role="user",
        password_hash="mock_hash_1234567890",  # pragma: allowlist secret
    )
    session.add(user)
    session.flush()
    return user


def _fund_user(session, wallet_service: WalletService, user: User, amount: Decimal = Decimal("1000.00")):
    user_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
    platform_account = wallet_service.ensure_platform_account(session, LedgerUnit.COIN)
    wallet_service.append_transaction(
        session,
        postings=[
            LedgerPosting(account=platform_account, amount=-amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
            LedgerPosting(account=user_account, amount=amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
        ],
        reason=LedgerEntryReason.ADJUSTMENT,
        reference=f"test-funding:{user.id}",
        description="Test funding",
        actor=user,
    )


def _create_country(session, name: str, alpha2: str, alpha3: str, fifa: str, confederation: str = "UEFA") -> Country:
    country = Country(
        source_provider="canonical",
        provider_external_id=f"c-{alpha2.lower()}",
        name=name,
        alpha2_code=alpha2.upper(),
        alpha3_code=alpha3.upper(),
        fifa_code=fifa.upper(),
        confederation_code=confederation,
    )
    session.add(country)
    session.flush()
    return country


def _create_legendary_player(
    session,
    full_name: str,
    country: Country,
    birth_date: date | None = date(1985, 2, 5),
    position: str = "ST",
    market_value_eur: float = 50_000_000.0,
    source_provider: str = "gtex_legend",
) -> Player:
    player = Player(
        source_provider=source_provider,
        provider_external_id=f"legend-{uuid.uuid4().hex[:8]}",
        country_id=country.id,
        full_name=full_name,
        canonical_display_name=full_name,
        date_of_birth=birth_date,
        position=position,
        normalized_position=position,
        is_real_player=True,
        is_tradable=True,
        market_value_eur=market_value_eur,
        current_market_reference_value=market_value_eur,
        dna_profile={"legendary": True, "rarity": "legendary"},
    )
    session.add(player)
    session.flush()
    return player


def _create_competition(
    session,
    key: str = "legend_nations_cup",
    title: str = "Legend Nations Cup",
    age_band: str = "senior",
) -> NationalTeamCompetition:
    competition = NationalTeamCompetition(
        key=f"{key}_{uuid.uuid4().hex[:6]}",
        title=title,
        season_label="2026",
        region_type="global",
        age_band=age_band,
        format_type="cup",
        status="draft",
        active=True,
        metadata_json={
            "entry_mode": "rental_only",
            "minimum_squad_size": 1,
            "maximum_squad_size": 23,
            "free_player_quota": 5,
        },
    )
    session.add(competition)
    session.flush()
    return competition


def test_legendary_player_rental_and_national_eligibility_flow(tmp_path: Path):
    """Test full flow: exist -> appear in eligible rental pool -> be rented -> enter squad -> satisfy nationality -> reject ineligible nationality."""
    session_factory = _build_session_factory(tmp_path / "legend-rental.db")
    wallet_service = WalletService()

    with session_factory() as session:
        tournament_service = NationalTeamTournamentService(session=session, wallet_service=wallet_service)

        argentina = _create_country(session, "Argentina", "AR", "ARG", "ARG", "CONMEBOL")
        _create_country(session, "Brazil", "BR", "BRA", "BRA", "CONMEBOL")

        legend = _create_legendary_player(session, "Diego Maradona", argentina, birth_date=date(1960, 10, 30))

        user = _create_user(session, "manager")
        _fund_user(session, wallet_service, user, Decimal("1000.00"))

        competition = _create_competition(session)

        arg_entry = NationalTeamEntry(
            competition_id=competition.id,
            country_code="AR",
            country_name="Argentina",
            entry_owner_user_id=user.id,
            manager_user_id=user.id,
        )
        session.add(arg_entry)
        session.flush()

        # 1. Appear in eligible rental pool for Argentina
        arg_pool = tournament_service.list_rental_players(
            competition_id=competition.id,
            country_code="AR",
            entry_id=arg_entry.id,
            actor=user,
        )
        legend_item = next((item for item in arg_pool["items"] if item["player_id"] == legend.id), None)
        assert legend_item is not None
        assert legend_item["player_name"] == "Diego Maradona"
        assert legend_item["nationality"] == "Argentina"
        assert legend_item["eligibility"]["eligible"] is True

        # 2. Be rented using standard rental mechanics
        rented_detail = tournament_service.rent_player(
            entry_id=arg_entry.id,
            actor=user,
            player_id=legend.id,
        )
        assert len(rented_detail["rental_squad_members"]) == 1
        squad_member = rented_detail["rental_squad_members"][0]
        assert squad_member["player_id"] == legend.id
        assert squad_member["player_name"] == "Diego Maradona"

        # 3. Prove ineligible nationality continues to fail
        bra_entry = NationalTeamEntry(
            competition_id=competition.id,
            country_code="BR",
            country_name="Brazil",
            entry_owner_user_id=user.id,
            manager_user_id=user.id,
        )
        session.add(bra_entry)
        session.flush()

        bra_pool = tournament_service.list_rental_players(
            competition_id=competition.id,
            country_code="BR",
            entry_id=bra_entry.id,
            actor=user,
        )
        legend_bra_item = next((item for item in bra_pool["items"] if item["player_id"] == legend.id), None)
        # The player is filtered out of BR pool because nationality is AR
        assert legend_bra_item is None

        with pytest.raises(NationalTeamTournamentError) as exc_info:
            tournament_service.rent_player(
                entry_id=bra_entry.id,
                actor=user,
                player_id=legend.id,
                expose_specific_outside_pool_reason=True,
            )
        assert exc_info.value.reason == "nationality_mismatch"


def test_legendary_player_obeys_existing_restrictions(tmp_path: Path):
    """Prove legendary players obey injury, suspension, contract lock, age rules, and duplicate rules."""
    session_factory = _build_session_factory(tmp_path / "legend-restrictions.db")
    wallet_service = WalletService()

    with session_factory() as session:
        tournament_service = NationalTeamTournamentService(session=session, wallet_service=wallet_service)

        italy = _create_country(session, "Italy", "IT", "ITA", "ITA", "UEFA")
        user = _create_user(session, "coach")
        _fund_user(session, wallet_service, user, Decimal("1000.00"))

        competition = _create_competition(session, age_band="u20")

        legend_senior = _create_legendary_player(session, "Roberto Baggio", italy, birth_date=date(1967, 2, 18))
        legend_young = _create_legendary_player(session, "Young Paolo Maldini", italy, birth_date=date(2008, 6, 26))

        it_entry = NationalTeamEntry(
            competition_id=competition.id,
            country_code="IT",
            country_name="Italy",
            entry_owner_user_id=user.id,
            manager_user_id=user.id,
        )
        session.add(it_entry)
        session.flush()

        # Age rule check (U20 competition)
        u20_pool = tournament_service.list_rental_players(
            competition_id=competition.id,
            country_code="IT",
            entry_id=it_entry.id,
            actor=user,
        )
        pool_ids = {item["player_id"] for item in u20_pool["items"]}
        assert legend_senior.id not in pool_ids
        assert legend_young.id in pool_ids

        # Injury restriction check
        injury = InjuryStatus(
            source_provider="canonical",
            provider_external_id="inj-1",
            player_id=legend_young.id,
            status="injured",
            detail="Hamstring strain",
            expected_return_at=(datetime.now().date() + timedelta(days=10)),
        )
        session.add(injury)
        session.flush()

        eligibility = tournament_service.rental_eligibility_for_pool_item(
            competition=competition,
            item={"player_id": legend_young.id, "country_tokens": {"IT"}},
            country_code="IT",
            entry=it_entry,
            actor=user,
        )
        assert eligibility["eligible"] is False
        assert "injury_unavailable" in eligibility["reasons"]

        session.delete(injury)
        session.flush()

        # Suspension restriction check
        sanction = FederationSanction(
            federation_id="fed-1",
            applied_by_user_id=user.id,
            player_id=legend_young.id,
            sanction_type=FederationSanctionType.PLAYER_BAN.value,
            reason="Disciplinary ban",
            status="active",
            starts_at=datetime.now() - timedelta(days=1),
            ends_at=datetime.now() + timedelta(days=5),
        )
        session.add(sanction)
        session.flush()

        eligibility_susp = tournament_service.rental_eligibility_for_pool_item(
            competition=competition,
            item={"player_id": legend_young.id, "country_tokens": {"IT"}},
            country_code="IT",
            entry=it_entry,
            actor=user,
        )
        assert eligibility_susp["eligible"] is False
        assert "suspension_active" in eligibility_susp["reasons"]

        session.delete(sanction)
        session.flush()

        # Contract lock check
        contract_lock = PlayerContract(
            player_id=legend_young.id,
            club_id="club-1",
            status="contract_locked",
            signed_on=(datetime.now() - timedelta(days=1)).date(),
            starts_on=(datetime.now() - timedelta(days=1)).date(),
            ends_on=(datetime.now() + timedelta(days=30)).date(),
        )
        session.add(contract_lock)
        session.flush()

        eligibility_contract = tournament_service.rental_eligibility_for_pool_item(
            competition=competition,
            item={"player_id": legend_young.id, "country_tokens": {"IT"}},
            country_code="IT",
            entry=it_entry,
            actor=user,
        )
        assert eligibility_contract["eligible"] is False
        assert "contract_locked" in eligibility_contract["reasons"]

        session.delete(contract_lock)
        session.flush()

        # Duplicate check
        rented = tournament_service.rent_player(
            entry_id=it_entry.id,
            actor=user,
            player_id=legend_young.id,
        )
        assert len(rented["rental_squad_members"]) == 1

        eligibility_dup = tournament_service.rental_eligibility_for_pool_item(
            competition=competition,
            item={"player_id": legend_young.id, "country_tokens": {"IT"}},
            country_code="IT",
            entry=it_entry,
            actor=user,
        )
        assert eligibility_dup["eligible"] is False
        assert "duplicate_player" in eligibility_dup["reasons"]


def test_legendary_player_in_competition_lifecycle(tmp_path: Path):
    """Test legendary players participating in the full competition submission & lifecycle."""
    session_factory = _build_session_factory(tmp_path / "legend-lifecycle.db")

    with session_factory() as session:
        lifecycle_service = NationalCompetitionLifecycleService(session=session)

        france = _create_country(session, "France", "FR", "FRA", "FRA", "UEFA")
        spain = _create_country(session, "Spain", "ES", "ESP", "ESP", "UEFA")

        zidane = _create_legendary_player(session, "Zinedine Zidane", france, birth_date=date(1972, 6, 23))
        iniesta = _create_legendary_player(session, "Andres Iniesta", spain, birth_date=date(1984, 5, 11))

        user_fr = _create_user(session, "fr_manager")
        user_es = _create_user(session, "es_manager")

        competition = _create_competition(session, key="euro_legend_cup", title="Euro Legend Cup", age_band="senior")

        # 1. Submit France squad with Zidane
        fr_entry = lifecycle_service.submit_entry(
            competition_id=competition.id,
            actor=user_fr,
            payload=type(
                "Payload",
                (),
                {
                    "country_code": "FR",
                    "country_name": "France",
                    "squad": [
                        {
                            "player_id": zidane.id,
                            "player_name": "Zinedine Zidane",
                            "date_of_birth": "1972-06-23",
                            "overall_rating": 94,
                            "position": "AM",
                        }
                    ],
                },
            )(),
        )
        assert fr_entry["country_code"] == "FR"
        assert fr_entry["squad"][0]["player_id"] == zidane.id

        # 2. Ineligible nationality submission test (e.g. trying to submit Iniesta for France)
        with pytest.raises(NationalCompetitionLifecycleError) as exc_info:
            lifecycle_service.submit_entry(
                competition_id=competition.id,
                actor=user_fr,
                payload=type(
                    "Payload",
                    (),
                    {
                        "country_code": "FR",
                        "country_name": "France",
                        "squad": [
                            {
                                "player_id": iniesta.id,
                                "player_name": "Andres Iniesta",
                                "date_of_birth": "1984-05-11",
                                "overall_rating": 92,
                                "position": "CM",
                            }
                        ],
                    },
                )(),
            )
        assert exc_info.value.reason == "player_not_eligible"

        # 3. Submit Spain squad with Iniesta
        es_entry = lifecycle_service.submit_entry(
            competition_id=competition.id,
            actor=user_es,
            payload=type(
                "Payload",
                (),
                {
                    "country_code": "ES",
                    "country_name": "Spain",
                    "squad": [
                        {
                            "player_id": iniesta.id,
                            "player_name": "Andres Iniesta",
                            "date_of_birth": "1984-05-11",
                            "overall_rating": 92,
                            "position": "CM",
                        }
                    ],
                },
            )(),
        )
        assert es_entry["country_code"] == "ES"
        assert es_entry["squad"][0]["player_id"] == iniesta.id

        # 4. Lock entries & advance competition lifecycle
        locked_payload = lifecycle_service.lock_entries(competition_id=competition.id)
        assert locked_payload["competition"].status == "locked"

        advanced_payload = lifecycle_service.advance_lifecycle(competition_id=competition.id)
        assert advanced_payload["current_stage"] == "completed"
        assert advanced_payload["champion_entry_id"] in {fr_entry["id"], es_entry["id"]}
