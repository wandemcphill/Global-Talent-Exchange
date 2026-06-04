from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.parse import quote

from sqlalchemy import func, select

from app.club_identity.models.reputation import ClubReputationProfile
from app.ingestion.models import Club as IngestionClub
from app.ingestion.models import Competition as IngestionCompetition
from app.ingestion.models import Country, InternalLeague, Player, PlayerSeasonStat, Season as IngestionSeason
from app.models.club_infra import ClubFacility
from app.models.club_profile import ClubProfile
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.regen import RegenPersonalityProfile, RegenProfile
from app.models.user import User
from app.models.wallet import LedgerUnit
from app.regen_universe.service import RegenUniverseService
from app.services.player_agency_service import PlayerAgencyService
from app.wallets.service import WalletService
from backend.tests.support.secrets import TEST_PASSWORD
from backend.tests.support.signup_payloads import player_signup_payload


def _register_user(client, *, suffix: str) -> dict[str, object]:
    response = client.post(
        "/auth/signup/player",
        json=player_signup_payload(
            email=f"{suffix}@example.com",
            username=suffix.replace("-", "_"),
            password=TEST_PASSWORD,
            full_name=f"Regen E2E {suffix}",
        ),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return {
        "user_id": payload["user"]["id"],
        "headers": {"Authorization": f"Bearer {payload['access_token']}"},
        "email": payload["user"]["email"],
    }


def _fund_coin(app_session_factory, *, user_id: str, amount: Decimal) -> None:
    wallet_service = WalletService()
    with app_session_factory() as session:
        user = session.get(User, user_id)
        assert user is not None
        wallet_service.credit_trade_proceeds(
            session,
            user=user,
            amount=amount,
            reference=f"regen-e2e:coin:{user_id}",
            description="Regen universe end-to-end wallet funding.",
            external_reference=f"regen-e2e:coin:{user_id}",
            unit=LedgerUnit.COIN,
        )
        session.commit()


def _seed_country(session, *, suffix: str) -> Country:
    country = Country(
        source_provider="test",
        provider_external_id=f"country-ng-{suffix}",
        name="Nigeria",
        alpha2_code="NG",
        alpha3_code="NGA",
        fifa_code="NGA",
        confederation_code="CAF",
        market_region="africa",
        is_enabled_for_universe=True,
    )
    session.add(country)
    session.flush()
    return country


def _create_club_profile(session, *, suffix: str, owner_user_id: str) -> ClubProfile:
    club = ClubProfile(
        owner_user_id=owner_user_id,
        club_name=f"Lagos Meteors {suffix}",
        short_name="LMT",
        slug=f"lagos-meteors-{suffix}",
        primary_color="#083d77",
        secondary_color="#f4d35e",
        accent_color="#ee964b",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        visibility="public",
    )
    session.add(club)
    session.flush()
    return club


def _create_player(
    session,
    *,
    suffix: str,
    provider_external_id: str,
    country_id: str,
    full_name: str,
    position: str,
    birth_date: date,
    market_value: int,
    gsi: int,
    current_club_profile_id: str | None = None,
    is_real_player: bool = True,
) -> Player:
    player = Player(
        source_provider="test",
        provider_external_id=f"{provider_external_id}-{suffix}",
        country_id=country_id,
        current_club_profile_id=current_club_profile_id,
        full_name=full_name,
        canonical_display_name=full_name,
        position=position,
        normalized_position=position,
        date_of_birth=birth_date,
        current_market_reference_value=market_value,
        market_value_eur=market_value,
        is_tradable=True,
        is_real_player=is_real_player,
        dna_profile={
            "gsi": gsi,
            "generation": 1,
            "regen_type": "real" if is_real_player else "club",
            "traits": ["line breaker", "press resistant", "late runner"],
        },
    )
    session.add(player)
    session.flush()
    return player


def _create_linked_user_competition(session, *, suffix: str, host_user_id: str) -> UserCompetition:
    competition = UserCompetition(
        host_user_id=host_user_id,
        name=f"GTEX U17 World Cup Host {suffix}",
        format="cup",
        currency="COIN",
        status="published",
        stage="live",
        source_type="national_team",
        source_id=f"national-e2e-{suffix}",
    )
    session.add(competition)
    session.flush()
    return competition


def _seed_national_award_match(
    session,
    *,
    suffix: str,
    linked_competition_id: str,
    seed_id: str,
    match_date: date,
) -> None:
    round_ = CompetitionRound(
        competition_id=linked_competition_id,
        round_number=1,
        stage="final",
        name="Final",
        status="completed",
    )
    session.add(round_)
    session.flush()
    session.add(
        CompetitionMatch(
            competition_id=linked_competition_id,
            round_id=round_.id,
            round_number=1,
            stage="final",
            home_club_id=f"ng-home-{suffix}",
            away_club_id=f"ng-away-{suffix}",
            status="completed",
            match_date=match_date,
            winner_club_id=f"ng-home-{suffix}",
            completed_at=datetime(match_date.year, match_date.month, match_date.day, 18, 0, tzinfo=timezone.utc),
            metadata_json={
                "player_performances": [
                    {
                        "subject_key": f"seed:{seed_id}",
                        "national_seed_id": seed_id,
                        "appearances": 3,
                        "starts": 3,
                        "minutes": 270,
                        "goals": 4,
                        "assists": 2,
                        "rating": 8.9,
                        "won_match": True,
                        "won_tournament": True,
                    }
                ]
            },
        )
    )
    session.flush()


def _active_regen_season(client) -> dict[str, object]:
    response = client.get("/regen-universe/seasons", params={"active_only": True})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items
    return items[0]


def _prepare_generated_son_for_agency(
    app_session_factory,
    *,
    generated_player_id: str,
    club_profile_id: str,
    country_id: str,
    suffix: str,
) -> None:
    with app_session_factory() as session:
        player = session.get(Player, generated_player_id)
        assert player is not None
        regen = session.scalar(select(RegenProfile).where(RegenProfile.player_id == generated_player_id))
        assert regen is not None
        regen_personality = session.scalar(
            select(RegenPersonalityProfile).where(RegenPersonalityProfile.regen_profile_id == regen.id)
        )
        assert regen_personality is not None

        next_league_rank = (session.scalar(select(func.max(InternalLeague.rank))) or 0) + 1

        league = InternalLeague(
            code=f"RGE{suffix[:5].upper()}",
            name=f"Regen League {suffix}",
            rank=next_league_rank,
            competition_multiplier=1.0,
            visibility_weight=1.0,
        )
        session.add(league)
        session.flush()

        competition = IngestionCompetition(
            source_provider="test",
            provider_external_id=f"regen-agency-competition-{suffix}",
            country_id=country_id,
            internal_league_id=league.id,
            name=f"GTEX Regen League {suffix}",
            slug=f"gtex-regen-league-{suffix}",
            code=f"RGE{suffix[:3].upper()}",
            competition_strength=38.0,
        )
        session.add(competition)
        session.flush()

        season = IngestionSeason(
            source_provider="test",
            provider_external_id=f"regen-agency-season-{suffix}",
            competition_id=competition.id,
            label="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_current=True,
        )
        session.add(season)
        session.flush()

        club = IngestionClub(
            source_provider="test",
            provider_external_id=f"regen-agency-club-{suffix}",
            country_id=country_id,
            current_competition_id=competition.id,
            internal_league_id=league.id,
            name=f"Lagos Meteors Academy {suffix}",
            slug=f"lagos-meteors-academy-{suffix}",
            short_name="LMA",
            code=f"LMA{suffix[:2].upper()}",
        )
        session.add(club)
        session.flush()

        player.country_id = country_id
        player.current_club_id = club.id
        player.current_competition_id = competition.id
        player.internal_league_id = league.id

        regen.metadata_json = {
            **dict(regen.metadata_json or {}),
            "decision_traits": {
                "ambition": 95,
                "loyalty": 18,
                "professionalism": 73,
                "greed": 44,
                "patience": 28,
                "ego": 86,
                "resilience": 30,
                "trophy_hunger": 82,
                "development_focus": 74,
                "temperament": 67,
                "adaptability": 58,
                "competitiveness": 79,
            },
        }
        regen_personality.ambition = 95
        regen_personality.loyalty = 18
        regen_personality.temperament = 67
        regen_personality.resilience = 30
        regen_personality.work_rate = 73
        regen_personality.leadership = 42

        session.add(
            ClubReputationProfile(
                id=f"rep-{club_profile_id}-{suffix}",
                club_id=club_profile_id,
                current_score=30,
                highest_score=30,
                prestige_tier="Established",
                total_league_titles=0,
                total_continental_titles=0,
                total_world_super_cup_titles=0,
                total_continental_qualifications=0,
            )
        )
        session.add(
            ClubFacility(
                id=f"facility-{club_profile_id}-{suffix}",
                club_id=club_profile_id,
                training_level=1,
                academy_level=1,
                medical_level=2,
                branding_level=1,
            )
        )
        session.flush()

        session.add(
            PlayerSeasonStat(
                id=f"agency-season-{generated_player_id}",
                source_provider="test",
                provider_external_id=f"agency-season-{generated_player_id}",
                player_id=generated_player_id,
                club_id=club.id,
                competition_id=competition.id,
                season_id=season.id,
                appearances=20,
                starts=2,
                minutes=180,
                goals=0,
                assists=0,
                clean_sheets=0,
                saves=0,
                average_rating=6.8,
            )
        )

        agency_service = PlayerAgencyService(session)
        decision = agency_service.maybe_submit_transfer_request(
            generated_player_id,
            reference_on=date(2026, 6, 20),
        )
        session.commit()
        assert decision.decision_code in {"transfer_request", "public_unhappy_state"}


def test_regen_universe_end_to_end(client, app_session_factory, bootstrap_admin_headers) -> None:
    suffix = "regen-e2e"
    user = _register_user(client, suffix=suffix)
    _fund_coin(app_session_factory, user_id=str(user["user_id"]), amount=Decimal("500.0000"))

    with app_session_factory() as session:
        RegenUniverseService(session).seed_defaults()
        country = _seed_country(session, suffix=suffix)
        club_profile = _create_club_profile(session, suffix=suffix, owner_user_id=str(user["user_id"]))
        parent_player = _create_player(
            session,
            suffix=suffix,
            provider_external_id="parent-player",
            country_id=country.id,
            full_name="Tunde Balogun",
            position="ST",
            birth_date=date(1998, 3, 14),
            market_value=18_000_000,
            gsi=82,
            current_club_profile_id=club_profile.id,
        )
        _create_player(
            session,
            suffix=suffix,
            provider_external_id="real-gk",
            country_id=country.id,
            full_name="Daniel Okonkwo",
            position="GK",
            birth_date=date(2009, 1, 5),
            market_value=12_000_000,
            gsi=78,
        )
        _create_player(
            session,
            suffix=suffix,
            provider_external_id="real-cb",
            country_id=country.id,
            full_name="Chisom Adebayo",
            position="CB",
            birth_date=date(2009, 4, 17),
            market_value=13_500_000,
            gsi=79,
        )
        _create_player(
            session,
            suffix=suffix,
            provider_external_id="real-st",
            country_id=country.id,
            full_name="Femi Adewale",
            position="ST",
            birth_date=date(2009, 7, 9),
            market_value=14_000_000,
            gsi=81,
        )
        linked_competition = _create_linked_user_competition(session, suffix=suffix, host_user_id=str(user["user_id"]))
        session.commit()

        club_profile_id = club_profile.id
        parent_player_id = parent_player.id
        linked_competition_id = linked_competition.id
        country_id = country.id

    season = _active_regen_season(client)
    assert season["is_active"] is True

    options_response = client.get("/api/regens/request-son/options", headers=user["headers"])
    assert options_response.status_code == 200, options_response.text
    options_payload = options_response.json()
    assert options_payload["club_id"] == club_profile_id
    assert any(item["player_id"] == parent_player_id for item in options_payload["eligible_parents"])

    preseed_response = client.post(
        "/admin/regen-universe/national-regens/preseed",
        headers=bootstrap_admin_headers,
        json={
            "country_codes": ["NG"],
            "age_band": "u17",
            "preseed_batch": f"regen-e2e-{suffix}",
        },
    )
    assert preseed_response.status_code == 201, preseed_response.text
    assert preseed_response.json()["summary"]["created"] >= 30

    competition_response = client.post(
        "/api/admin/national-team-engine/competitions",
        headers=bootstrap_admin_headers,
        json={
            "key": f"gtex-u17-world-cup-{suffix}",
            "title": "GTEX U17 World Cup",
            "season_label": "2026",
            "region_type": "global",
            "age_band": "u17",
            "format_type": "cup",
            "status": "published",
            "linked_competition_id": linked_competition_id,
            "entry_opens_at": "2026-01-01T00:00:00Z",
            "entry_closes_at": "2026-12-31T00:00:00Z",
            "kickoff_at": "2026-06-15T12:00:00Z",
            "metadata_json": {
                "entry_mode": "rental_only",
                "minimum_squad_size": 11,
                "maximum_squad_size": 23,
            },
        },
    )
    assert competition_response.status_code == 200, competition_response.text
    competition_id = competition_response.json()["id"]

    rental_pool_response = client.get(
        f"/api/national-team-engine/competitions/{competition_id}/rental-pool",
        params={"country_code": "NG", "limit": 40},
    )
    assert rental_pool_response.status_code == 200, rental_pool_response.text
    rental_pool = rental_pool_response.json()["items"]
    preseeded_pool_items = [item for item in rental_pool if item["source_bucket"] == "preseeded"]
    assert preseeded_pool_items
    for item in preseeded_pool_items[:5]:
        assert item["is_preseeded_national_regen"] is True
        assert item["buyable"] is False
        assert item["tradable"] is False
        assert item["transferable"] is False
        assert item["share_market_eligible"] is False
        assert item["card_mint_eligible"] is False
        assert item["buy_cta_allowed"] is False
        assert item["national_pool_only"] is True

    squad_response = client.post(
        f"/api/national-team-engine/competitions/{competition_id}/auto-build-squad",
        json={
            "country_code": "NG",
            "budget_coin": "10000.0000",
            "tactic": "balanced",
        },
    )
    assert squad_response.status_code == 200, squad_response.text
    squad_payload = squad_response.json()
    assert squad_payload["complete"] is True
    assert squad_payload["selected_count"] == 11
    assert squad_payload["source_mix"]["real"] > 0
    assert squad_payload["source_mix"]["preseeded"] > 0

    selected_preseeded = [item for item in squad_payload["players"] if item["source_bucket"] == "preseeded"]
    assert selected_preseeded
    selected_seed_id = selected_preseeded[0]["player_id"]
    for item in selected_preseeded:
        assert item["buyable"] is False
        assert item["tradable"] is False
        assert item["transferable"] is False
        assert item["buy_cta_allowed"] is False

    entry_response = client.post(
        f"/api/national-team-engine/competitions/{competition_id}/entries",
        headers=user["headers"],
        json={
            "country_code": "NG",
            "country_name": "Nigeria",
            "squad": [
                {
                    "player_id": item["player_id"],
                    "player_name": item["player_name"],
                    "age": item["age"],
                    "overall_rating": item["overall_rating"],
                    "position": item["primary_position"],
                    "metadata_json": {
                        "source_bucket": item["source_bucket"],
                        "is_preseeded_national_regen": item["is_preseeded_national_regen"],
                        "buyable": item["buyable"],
                        "tradable": item["tradable"],
                    },
                }
                for item in squad_payload["players"]
            ],
        },
    )
    assert entry_response.status_code == 200, entry_response.text
    assert len(entry_response.json()["squad"]) == 11

    with app_session_factory() as session:
        _seed_national_award_match(
            session,
            suffix=suffix,
            linked_competition_id=linked_competition_id,
            seed_id=selected_seed_id,
            match_date=date(2026, 6, 18),
        )
        session.commit()

    request_son_response = client.post(
        "/api/regens/request-son",
        headers=user["headers"],
        json={
            "parent_player_id": parent_player_id,
            "selected_traits": ["line breaker", "press resistant", "late runner"],
            "requested_name": "Afolabi Adeyemi",
            "requested_country_code": "NG",
            "requested_position": "ST",
            "payment_method": "wallet",
        },
    )
    assert request_son_response.status_code == 201, request_son_response.text
    order_payload = request_son_response.json()
    assert order_payload["status"] == "pending_payment"
    assert order_payload["generated_player"] is None

    pay_response = client.post(
        f"/api/regens/creation-orders/{order_payload['id']}/pay-with-wallet",
        headers=user["headers"],
    )
    assert pay_response.status_code == 200, pay_response.text
    generated_payload = pay_response.json()
    assert generated_payload["status"] == "generated"
    assert generated_payload["generated_player"]["full_name"] == "Afolabi Adeyemi"
    generated_player_id = generated_payload["generated_player"]["player_id"]

    with app_session_factory() as session:
        generated_regen = session.scalar(select(RegenProfile).where(RegenProfile.player_id == generated_player_id))
        assert generated_regen is not None
        assert generated_regen.generation_source == "requested_son"
        assert generated_regen.generated_for_club_id == club_profile_id

    _prepare_generated_son_for_agency(
        app_session_factory,
        generated_player_id=generated_player_id,
        club_profile_id=club_profile_id,
        country_id=country_id,
        suffix=suffix,
    )

    close_response = client.post(
        f"/admin/regen-universe/seasons/{season['id']}/close",
        headers=bootstrap_admin_headers,
        json={"close_date": "2026-06-30", "start_next_season": False},
    )
    assert close_response.status_code == 200, close_response.text

    awards_response = client.get("/regen-universe/awards", params={"season_id": season["id"]})
    rankings_response = client.get(
        "/regen-universe/rankings",
        params={"season_id": season["id"], "category": "overall"},
    )
    son_timeline_response = client.get(f"/regen-universe/players/{generated_player_id}/timeline")
    son_achievements_response = client.get(
        "/regen-universe/achievements",
        params={"player_id": generated_player_id},
    )
    seed_subject = quote(f"seed:{selected_seed_id}", safe="")
    seed_timeline_response = client.get(f"/regen-universe/players/{seed_subject}/timeline")

    assert awards_response.status_code == 200, awards_response.text
    assert rankings_response.status_code == 200, rankings_response.text
    assert son_timeline_response.status_code == 200, son_timeline_response.text
    assert son_achievements_response.status_code == 200, son_achievements_response.text
    assert seed_timeline_response.status_code == 200, seed_timeline_response.text

    awards_payload = awards_response.json()["items"]
    rankings_payload = rankings_response.json()["entries"]
    son_timeline = son_timeline_response.json()["items"]
    son_achievements = son_achievements_response.json()["items"]
    seed_timeline = seed_timeline_response.json()["items"]

    assert any(item["award"]["name"] == "GTEX World Player of the Year" for item in awards_payload)
    u17_award = next(item for item in awards_payload if item["award"]["code"] == "U17_WORLD_CUP_GOLDEN_BALL")
    assert u17_award["winners"][0]["player_id"] == f"seed:{selected_seed_id}"
    assert rankings_payload
    assert rankings_payload[0]["player_id"] == f"seed:{selected_seed_id}"
    assert any(item["event_type"] == "requested_son_created" for item in son_timeline)
    assert any(item["event_type"] == "transfer_request_submitted" for item in son_timeline)
    assert any(item["achievement_type"] == "requested_son_created" for item in son_achievements)
    assert any(item["event_type"] == "award_won" for item in seed_timeline)
    assert any(item["event_type"] == "tournament_winner" for item in seed_timeline)
