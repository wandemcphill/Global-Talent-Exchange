from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.global_memory.models import NationalTeamCountryRanking
from app.ingestion.models import Country
from app.leagues.models import LeagueClub
from app.leagues.repository import InMemoryLeagueEventRepository
from app.leagues.service import LeagueSeasonLifecycleService
from app.models import Base
import app.models  # noqa: F401
from app.models.national_team import NationalTeamCompetition, NationalTeamFlagBearer, NationalTeamResultMemory
from app.models.user import User, UserRole
from app.national_team_engine.competition_lifecycle_service import (
    NationalCompetitionLifecycleError,
    NationalCompetitionLifecycleService,
)
from app.national_team_engine.competition_profiles import default_reward_structure_for
from app.national_team_engine.schemas import NationalTeamCompetitionEntrySubmitRequest
from app.national_team_engine.tournament_service import NationalTeamTournamentService
from backend.tests.national_team_engine.rented_squads import submit_request
from app.owner_console.models import OwnerClubState
from app.owner_console.service import apply_division_result


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def _user(session, suffix: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=f"user_{suffix}",
        email=f"{suffix}@example.com",
        username=f"user_{suffix}",
        display_name=f"User {suffix}",
        password_hash="not-used",  # pragma: allowlist secret
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def _squad(session, actor, competition, country_code: str, country_name: str, ages: tuple[int, ...], ratings: tuple[int, ...]):
    return submit_request(
        session,
        actor=actor,
        competition=competition,
        country_code=country_code,
        country_name=country_name,
        ages=ages,
        ratings=ratings,
    )


def _named_squad(country_code: str, country_name: str, ages: tuple[int, ...], ratings: tuple[int, ...]):
    return NationalTeamCompetitionEntrySubmitRequest(
        country_code=country_code,
        country_name=country_name,
        squad=[
            {
                "player_name": f"{country_name} {index}",
                "age": age,
                "overall_rating": ratings[index],
                "position": "fw",
            }
            for index, age in enumerate(ages)
        ],
    )


def test_seeded_templates_chain_finals_and_split_prize_modes():
    with _session() as session:
        admin = _user(session, "admin", role=UserRole.ADMIN)
        seeded = NationalTeamTournamentService(session).seed_default_competitions(actor=admin)
        by_key = {item["key"]: item for item in seeded}
        assert "gtex-gold-cup" in by_key
        assert "gtex-olympics" in by_key
        assert "gtex-u21-euros" in by_key
        assert "gtex-world-cup-qualifier" in by_key
        world_cup = by_key["gtex-world-cup"]["metadata_json"]
        afcon = by_key["gtex-afcon"]["metadata_json"]
        assert world_cup["entry_fee_coin"] == "0.0000"
        assert world_cup["entry_policy"] == "flag_bearer_only"
        assert world_cup["resolution_mode"] == "scheduled"
        assert world_cup["reward_structure"]["reward_mode"] == "match_and_stage"
        assert afcon["reward_structure"]["reward_mode"] == "places"
        assert afcon["reward_structure"]["per_match_coin"]["win"] == "0.0000"
        assert world_cup["qualification_chain"]["accepts_from_keys"] == ["gtex-world-cup-qualifier"]
        assert (
            by_key["gtex-u17-afcon-qualifier"]["metadata_json"]["qualification_chain"]["feeds_into_key"]
            == "gtex-u17-afcon"
        )


def test_scheduled_country_playoff_remembers_the_user_and_feeds_the_finals():
    with _session() as session:
        admin = _user(session, "admin", role=UserRole.ADMIN)
        nigeria = [_user(session, f"ng_{index}") for index in range(2)]
        ghana = _user(session, "gh")
        outsider = _user(session, "outsider")
        session.add(
            Country(
                source_provider="test",
                provider_external_id="NG",
                name="Nigeria",
                alpha2_code="NG",
                fifa_code="NGA",
                confederation_code="CAF",
            )
        )
        session.add(
            Country(
                source_provider="test",
                provider_external_id="GH",
                name="Ghana",
                alpha2_code="GH",
                fifa_code="GHA",
                confederation_code="CAF",
            )
        )
        now = datetime.now(UTC)
        qualifier = NationalTeamCompetition(
            key="gtex-afcon-qualifier",
            title="AFCON Qualifiers",
            season_label="2030",
            region_type="afcon",
            age_band="senior",
            format_type="cup",
            status="published",
            entry_closes_at=now + timedelta(days=1),
            kickoff_at=now + timedelta(days=2),
            metadata_json={
                "competition_family": "afcon",
                "entry_policy": "open_representation",
                "resolution_mode": "scheduled",
                "minimum_squad_size": 2,
                "maximum_squad_size": 3,
                "qualification_chain": {"feeds_into_key": "gtex-afcon"},
                "competition_engine": {"tournament_slots": 2, "group_size": 2, "qualifier_group_size": 2},
            },
            created_by_user_id=admin.id,
        )
        finals = NationalTeamCompetition(
            key="gtex-afcon",
            title="GTEX AFCON",
            season_label="2030",
            region_type="afcon",
            age_band="senior",
            format_type="cup",
            status="published",
            metadata_json={
                "competition_family": "afcon",
                "entry_policy": "flag_bearer_only",
                "minimum_squad_size": 2,
                "maximum_squad_size": 3,
            },
            created_by_user_id=admin.id,
        )
        session.add(qualifier)
        session.add(finals)
        session.flush()
        lifecycle = NationalCompetitionLifecycleService(session)
        lifecycle.submit_entry(
            competition_id=qualifier.id,
            actor=nigeria[0],
            payload=_squad(session, nigeria[0], qualifier, "NG", "Nigeria", (28, 27), (90, 88)),
        )
        lifecycle.submit_entry(
            competition_id=qualifier.id,
            actor=nigeria[1],
            payload=_squad(session, nigeria[1], qualifier, "NG", "Nigeria", (26, 25), (70, 69)),
        )
        lifecycle.submit_entry(
            competition_id=qualifier.id,
            actor=ghana,
            payload=_squad(session, ghana, qualifier, "GH", "Ghana", (27, 26), (80, 79)),
        )
        qualifier.entry_closes_at = now - timedelta(hours=1)
        session.flush()
        locked = lifecycle.lock_entries(competition_id=qualifier.id)
        assert locked["current_stage"] == "pre_qualifier"
        opened = lifecycle.advance_lifecycle(competition_id=qualifier.id)
        assert opened["current_stage"] == "pre_qualifier"
        pending = opened["pending_round"]["matches"]
        assert pending
        assert all(
            match["kickoff_at"] < qualifier.kickoff_at.isoformat() for match in pending if match.get("kickoff_at")
        )
        for match in pending:
            if str(match.get("resolution") or "").endswith("_bye"):
                continue
            lifecycle.record_scheduled_match_result(
                competition_id=qualifier.id,
                match_id=match["match_id"],
                home_score=2,
                away_score=0,
            )
        bearers = list(session.scalars(select(NationalTeamFlagBearer)).all())
        assert any(bearer.country_code == "NG" and bearer.target_key == "gtex-afcon-qualifier" for bearer in bearers)
        memories = list(session.scalars(select(NationalTeamResultMemory)).all())
        assert memories
        assert all(memory.same_country_playoff for memory in memories)
        assert memories[0].home_user_id
        ranking = session.scalar(
            select(NationalTeamCountryRanking).where(NationalTeamCountryRanking.country_code == "NG")
        )
        assert ranking is None or int(ranking.matches_played) == 0
        try:
            lifecycle.submit_entry(
                competition_id=finals.id,
                actor=outsider,
                payload=_named_squad("NG", "Nigeria", (29, 28), (99, 98)),
            )
        except NationalCompetitionLifecycleError as exc:
            assert exc.reason == "flag_bearer_required"
        else:
            raise AssertionError("An outsider was allowed to carry Nigeria into the finals.")


def test_age_limits_cover_under_21_and_olympic_overage():
    with _session() as session:
        user = _user(session, "ages")
        session.add(
            Country(
                source_provider="test",
                provider_external_id="NG",
                name="Nigeria",
                alpha2_code="NG",
                fifa_code="NGA",
                confederation_code="CAF",
            )
        )
        under_21 = NationalTeamCompetition(
            key="u21-test",
            title="U21 Euros",
            season_label="2030",
            age_band="u21",
            status="published",
            metadata_json={
                "competition_family": "euros",
                "minimum_squad_size": 1,
                "maximum_squad_size": 4,
                "competition_engine": {"eligible_confederations": []},
            },
            created_by_user_id=user.id,
        )
        olympics = NationalTeamCompetition(
            key="olympics-test",
            title="Olympics",
            season_label="2030",
            age_band="olympics",
            status="published",
            metadata_json={
                "competition_family": "olympics",
                "minimum_squad_size": 4,
                "maximum_squad_size": 6,
                "competition_engine": {"eligible_confederations": []},
            },
            created_by_user_id=user.id,
        )
        session.add(under_21)
        session.add(olympics)
        session.flush()
        lifecycle = NationalCompetitionLifecycleService(session)
        try:
            lifecycle.submit_entry(
                competition_id=under_21.id,
                actor=user,
                payload=_squad(session, user, under_21, "NG", "Nigeria", (22,), (80,)),
            )
        except NationalCompetitionLifecycleError as exc:
            assert exc.reason == "invalid_squad_age"
        else:
            raise AssertionError("A 22-year-old entered an under-21 competition.")
        try:
            lifecycle.submit_entry(
                competition_id=olympics.id,
                actor=user,
                payload=_squad(session, user, olympics, "NG", "Nigeria", (24, 25, 26, 27), (80, 81, 82, 83)),
            )
        except NationalCompetitionLifecycleError as exc:
            assert exc.reason == "olympic_overage_limit"
        else:
            raise AssertionError("Four overage players entered the Olympics.")
        accepted = lifecycle.submit_entry(
            competition_id=olympics.id,
            actor=user,
            payload=_squad(session, user, olympics, "NG", "Nigeria", (21, 22, 24, 30), (80, 81, 82, 83)),
        )
        assert len(accepted["squad"]) == 4


def test_user_template_does_not_copy_world_cup_match_fees():
    with _session() as session:
        host = _user(session, "host")
        hosted = NationalTeamTournamentService(session).host_user_competition(
            actor=host,
            title="Friends youth cup",
            season_label="2030",
            template_key="youth_cup",
            place_prizes={"first": "25.0000", "second": "10.0000", "third": "5.0000"},
        )
        reward = hosted["metadata_json"]["reward_structure"]
        assert hosted["metadata_json"]["host_type"] == "user"
        assert hosted["age_band"] == "u20"
        assert reward["reward_mode"] == "places"
        assert reward["place_prizes"]["first"] == "25.0000"
        assert reward["per_match_coin"]["win"] == "0.0000"
        assert default_reward_structure_for("world_cup")["reward_mode"] == "match_and_stage"


def test_new_club_starts_in_foundation_and_cannot_buy_the_top_tier():
    with _session() as session:
        club = OwnerClubState(
            club_id="new-rich-club",
            owner_user_id="owner",
            club_name="New Rich",
            stage="active",
            manager_json={},
            facilities_json={},
            value_history_json=[],
        )
        session.add(club)
        session.flush()
        assert club.division_level == "foundation"
        service = LeagueSeasonLifecycleService(repository=InMemoryLeagueEventRepository())
        registered = service.register_season(
            buy_in_tier=1000,
            season_start=datetime.now(UTC).date(),
            clubs=(
                LeagueClub(club_id="new-rich-club", club_name="New Rich"),
                LeagueClub(club_id="other", club_name="Other"),
            ),
            club_divisions={"new-rich-club": "foundation", "other": "foundation"},
        )
        assert club.division_level == "foundation"
        assert registered.buy_in_tier == 0
        assert registered.division_level == "foundation"
        promoted = apply_division_result(session, "new-rich-club", final_position=1, field_size=20)
        assert promoted == "division_7"
        short_season = service.register_season(
            buy_in_tier=25,
            season_start=datetime.now(UTC).date(),
            clubs=(
                LeagueClub(club_id="new-rich-club", club_name="New Rich"),
                LeagueClub(club_id="other", club_name="Other"),
            ),
            club_divisions={"new-rich-club": "foundation", "other": "foundation"},
        )
        assert short_season.scheduled_matches_per_club == 1
        assert len(short_season.fixtures) == 1
        moved = apply_division_result(
            session,
            "new-rich-club",
            final_position=1,
            field_size=20,
            season_id="foundation-season",
        )
        repeated = apply_division_result(
            session,
            "new-rich-club",
            final_position=1,
            field_size=20,
            season_id="foundation-season",
        )
        assert moved == repeated == "division_6"


def _play_scheduled_until_complete(
    lifecycle: NationalCompetitionLifecycleService, competition_id: str, *, limit: int = 16
):
    payload = lifecycle.advance_lifecycle(competition_id=competition_id)
    for _ in range(limit):
        if payload["current_stage"] == "completed":
            return payload
        pending = payload.get("pending_round") or {}
        open_matches = [
            match
            for match in list(pending.get("matches") or [])
            if match.get("match_id")
            and str(match.get("status") or "") != "played"
            and not str(match.get("resolution") or "").endswith("_bye")
        ]
        if not open_matches:
            payload = lifecycle.advance_lifecycle(competition_id=competition_id)
            continue
        for match in open_matches:
            payload = lifecycle.record_scheduled_match_result(
                competition_id=competition_id,
                match_id=match["match_id"],
                home_score=2,
                away_score=0,
            )
    raise AssertionError(f"Scheduled competition stopped at {payload['current_stage']}.")


def test_scheduled_qualifier_plays_cross_country_matches_into_one_flag_bearer_per_country():
    with _session() as session:
        admin = _user(session, "sched_admin", role=UserRole.ADMIN)
        nigeria = _user(session, "sched_ng")
        ghana = _user(session, "sched_gh")
        outsider = _user(session, "sched_out")
        for code, name in (("NG", "Nigeria"), ("GH", "Ghana")):
            session.add(
                Country(
                    source_provider="test",
                    provider_external_id=f"sched-{code}",
                    name=name,
                    alpha2_code=code,
                    fifa_code=code,
                    confederation_code="CAF",
                )
            )
        now = datetime.now(UTC)
        qualifier = NationalTeamCompetition(
            key="gtex-played-afcon-qualifier",
            title="AFCON Qualifiers",
            season_label="2031",
            region_type="afcon",
            age_band="senior",
            format_type="cup",
            status="published",
            entry_closes_at=now + timedelta(days=1),
            kickoff_at=now + timedelta(days=4),
            metadata_json={
                "competition_family": "afcon",
                "entry_policy": "open_representation",
                "resolution_mode": "scheduled",
                "entry_fee_coin": "0.0000",
                "minimum_squad_size": 2,
                "maximum_squad_size": 3,
                "qualification_chain": {"feeds_into_key": "gtex-played-afcon"},
                "competition_engine": {
                    "tournament_slots": 2,
                    "group_size": 2,
                    "qualifier_group_size": 2,
                    "advance_per_group": 1,
                    "best_third_slots": 0,
                    "eligible_confederations": [],
                },
            },
            created_by_user_id=admin.id,
        )
        finals = NationalTeamCompetition(
            key="gtex-played-afcon",
            title="GTEX AFCON",
            season_label="2031",
            region_type="afcon",
            age_band="senior",
            format_type="cup",
            status="published",
            metadata_json={
                "competition_family": "afcon",
                "entry_policy": "flag_bearer_only",
                "entry_fee_coin": "0.0000",
                "minimum_squad_size": 2,
                "maximum_squad_size": 3,
                "competition_engine": {"eligible_confederations": []},
            },
            created_by_user_id=admin.id,
        )
        session.add(qualifier)
        session.add(finals)
        session.flush()
        lifecycle = NationalCompetitionLifecycleService(session)
        lifecycle.submit_entry(
            competition_id=qualifier.id,
            actor=nigeria,
            payload=_squad(session, nigeria, qualifier, "NG", "Nigeria", (28, 27), (90, 88)),
        )
        lifecycle.submit_entry(
            competition_id=qualifier.id,
            actor=ghana,
            payload=_squad(session, ghana, qualifier, "GH", "Ghana", (27, 26), (80, 79)),
        )
        qualifier.entry_closes_at = now - timedelta(hours=1)
        session.flush()
        locked = lifecycle.lock_entries(competition_id=qualifier.id)
        assert locked["current_stage"] == "tournament"
        opened = lifecycle.advance_lifecycle(competition_id=qualifier.id)
        pending = list((opened.get("pending_round") or {}).get("matches") or [])
        playable = [
            match
            for match in pending
            if match.get("match_id") and not str(match.get("resolution") or "").endswith("_bye")
        ]
        assert playable
        assert all(match["home_country_code"] != match["away_country_code"] for match in playable)
        assert all(match["kickoff_at"] < qualifier.kickoff_at.isoformat() for match in playable)
        assert qualifier.kickoff_at > now
        for match in playable:
            completed = lifecycle.record_scheduled_match_result(
                competition_id=qualifier.id,
                match_id=match["match_id"],
                home_score=2,
                away_score=0,
            )
        if completed["current_stage"] != "completed":
            completed = _play_scheduled_until_complete(lifecycle, qualifier.id)
        assert completed["current_stage"] == "completed"
        assert qualifier.metadata_json["entry_fee_coin"] == "0.0000"
        bearers = list(session.scalars(select(NationalTeamFlagBearer)).all())
        final_bearers = [bearer for bearer in bearers if bearer.target_key == finals.key]
        assert sorted((bearer.country_code, bearer.user_id) for bearer in final_bearers) == sorted(
            [("NG", nigeria.id), ("GH", ghana.id)]
        )
        memories = list(session.scalars(select(NationalTeamResultMemory)).all())
        assert any(
            not memory.same_country_playoff and memory.home_country_code != memory.away_country_code
            for memory in memories
        )
        accepted = lifecycle.submit_entry(
            competition_id=finals.id,
            actor=nigeria,
            payload=_squad(session, nigeria, finals, "NG", "Nigeria", (28, 27), (90, 88)),
        )
        assert accepted["country_code"] == "NG"
        with pytest.raises(NationalCompetitionLifecycleError) as rejected:
            lifecycle.submit_entry(
                competition_id=finals.id,
                actor=outsider,
                payload=_named_squad("NG", "Nigeria", (29, 28), (99, 98)),
            )
        assert rejected.value.reason == "flag_bearer_required"


def test_scheduled_four_country_group_and_knockout_finishes():
    with _session() as session:
        admin = _user(session, "four_admin", role=UserRole.ADMIN)
        countries = (("NG", "Nigeria", 90), ("GH", "Ghana", 80), ("SN", "Senegal", 85), ("CM", "Cameroon", 75))
        users = []
        for code, name, _rating in countries:
            users.append(_user(session, f"four_{code}"))
            session.add(
                Country(
                    source_provider="test",
                    provider_external_id=f"four-{code}",
                    name=name,
                    alpha2_code=code,
                    fifa_code=code,
                    confederation_code="CAF",
                )
            )
        now = datetime.now(UTC)
        competition = NationalTeamCompetition(
            key="gtex-played-four",
            title="Four Nation Cup",
            season_label="2031",
            region_type="afcon",
            age_band="senior",
            format_type="cup",
            status="published",
            entry_closes_at=now + timedelta(days=1),
            kickoff_at=now + timedelta(days=6),
            metadata_json={
                "competition_family": "afcon",
                "resolution_mode": "scheduled",
                "entry_fee_coin": "0.0000",
                "minimum_squad_size": 2,
                "maximum_squad_size": 3,
                "competition_engine": {
                    "tournament_slots": 2,
                    "group_size": 2,
                    "qualifier_group_size": 2,
                    "advance_per_group": 1,
                    "best_third_slots": 0,
                    "eligible_confederations": [],
                },
            },
            created_by_user_id=admin.id,
        )
        session.add(competition)
        session.flush()
        lifecycle = NationalCompetitionLifecycleService(session)
        for user, (code, name, rating) in zip(users, countries, strict=True):
            lifecycle.submit_entry(
                competition_id=competition.id,
                actor=user,
                payload=_squad(session, user, competition, code, name, (28, 27), (rating, rating - 1)),
            )
        competition.entry_closes_at = now - timedelta(hours=2)
        session.flush()
        locked = lifecycle.lock_entries(competition_id=competition.id)
        assert locked["current_stage"] == "qualifier"
        completed = _play_scheduled_until_complete(lifecycle, competition.id)
        assert completed["current_stage"] == "completed"
        assert completed["champion_entry_id"]
        tournament = completed["stage_results"]["tournament"]
        assert tournament["knockout_rounds"]
        assert completed["stage_results"]["qualifier"]["qualified_entry_ids"]
