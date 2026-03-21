from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.ingestion.models import Player
from app.models.player_cards import PlayerCardListing
from app.models.player_contract import PlayerContract
from app.models.regen import RegenOnboardingFlag, RegenProfile
from app.schemas.club_requests import ClubCreateRequest
from app.services.club_branding_service import ClubBrandingService
from app.services.regen_market_service import (
    RegenAwardEvent,
    RegenDemandEvent,
    RegenMarketService,
    RegenPerformanceEvent,
    RegenRecommendationRequest,
    RegenSearchFilters,
    RegenTradeRestrictedError,
)


def _create_club(session, *, slug: str) -> object:
    return ClubBrandingService(session).create_club_profile(
        owner_user_id="user-owner",
        payload=ClubCreateRequest.model_validate(
            {
                "club_name": "Harbor FC",
                "short_name": "HFC",
                "slug": slug,
                "primary_color": "#114477",
                "secondary_color": "#ffffff",
                "accent_color": "#ff9900",
                "country_code": "NG",
                "region_name": "Lagos",
                "city_name": "Lagos",
                "visibility": "public",
            }
        ),
    )


def _starter_regens(session, club_id: str) -> list[RegenProfile]:
    return session.scalars(
        select(RegenProfile).where(RegenProfile.generated_for_club_id == club_id).order_by(RegenProfile.regen_id)
    ).all()


def _onboarding_flag(session, regen: RegenProfile) -> RegenOnboardingFlag:
    flag = session.scalar(select(RegenOnboardingFlag).where(RegenOnboardingFlag.regen_id == regen.id))
    assert flag is not None
    return flag


def _make_tradable(session, regen: RegenProfile) -> None:
    flag = _onboarding_flag(session, regen)
    flag.is_non_tradable = False
    session.flush()


def _make_wonderkid(session, regen: RegenProfile, *, current_min: int = 68, current_max: int = 72, potential_min: int = 88, potential_max: int = 93) -> None:
    player = _player_for_regen(session, regen)
    assert player is not None
    player.date_of_birth = date.today() - timedelta(days=18 * 365)
    regen.current_ability_range_json = {"minimum": current_min, "maximum": current_max}
    regen.potential_range_json = {"minimum": potential_min, "maximum": potential_max}
    regen.current_gsi = current_max
    session.flush()


def _player_for_regen(session, regen: RegenProfile):
    player = session.get(Player, regen.player_id)
    assert player is not None
    return player


def _contract_for_regen(session, regen: RegenProfile) -> PlayerContract:
    contract = session.scalar(
        select(PlayerContract).where(
            PlayerContract.player_id == regen.player_id,
            PlayerContract.status == "active",
        )
    )
    assert contract is not None
    return contract


def _open_listing(session, regen: RegenProfile, *, listing_id: str) -> None:
    session.add(
        PlayerCardListing(
            listing_id=listing_id,
            player_card_id=regen.linked_unique_card_id,
            seller_user_id="user-owner",
            quantity=1,
            price_per_card_credits=1_500,
            status="open",
            expires_at=None,
            metadata_json={"origin": "test"},
        )
    )
    session.flush()


def test_regen_value_increases_from_performance(session) -> None:
    club = _create_club(session, slug="regen-value-performance")
    regen = _starter_regens(session, club.id)[0]
    service = RegenMarketService(session)

    baseline = service.refresh_value(regen.id)
    updated = service.record_match_performance(
        regen.id,
        RegenPerformanceEvent(
            match_rating=9.2,
            goals=2,
            assists=1,
            mvp_award=True,
            club_success_score=2.0,
            fan_demand_score=3.0,
            narrative_significance=2.5,
        ),
        club_id=club.id,
    )

    assert updated.current_value_coin > baseline.current_value_coin
    assert updated.ability_component > baseline.ability_component
    assert updated.demand_component > baseline.demand_component


def test_regen_value_increases_from_awards(session) -> None:
    club = _create_club(session, slug="regen-value-award")
    regen = _starter_regens(session, club.id)[0]
    service = RegenMarketService(session)

    baseline = service.refresh_value(regen.id)
    updated = service.record_award(
        regen.id,
        RegenAwardEvent(
            award_code="golden_boy_shortlist",
            fan_demand_score=2.0,
            narrative_significance=1.5,
        ),
        club_id=club.id,
    )

    assert updated.current_value_coin > baseline.current_value_coin
    assert updated.reputation_component > baseline.reputation_component
    assert updated.narrative_component >= baseline.narrative_component


def test_scouting_estimate_accuracy_varies_with_quality(session) -> None:
    club = _create_club(session, slug="regen-scouting-variance")
    regen = _starter_regens(session, club.id)[0]
    _make_wonderkid(session, regen)
    service = RegenMarketService(session)

    actual_current = round((regen.current_ability_range_json["minimum"] + regen.current_ability_range_json["maximum"]) / 2)
    actual_potential = round((regen.potential_range_json["minimum"] + regen.potential_range_json["maximum"]) / 2)
    low_reports = [
        service.create_scout_report(
            regen.id,
            club_id=club.id,
            scout_identity=f"low-{index}",
            scout_rating=35,
            manager_style="balanced",
        )
        for index in range(4)
    ]
    high_reports = [
        service.create_scout_report(
            regen.id,
            club_id=club.id,
            scout_identity=f"high-{index}",
            scout_rating=92,
            manager_style="youth_developer",
            premium_service=True,
        )
        for index in range(4)
    ]

    low_error = sum(abs(report.current_ability_estimate - actual_current) + abs(report.future_potential_estimate - actual_potential) for report in low_reports) / len(low_reports)
    high_error = sum(abs(report.current_ability_estimate - actual_current) + abs(report.future_potential_estimate - actual_potential) for report in high_reports) / len(high_reports)

    assert min(report.scout_confidence_bps for report in high_reports) > max(report.scout_confidence_bps for report in low_reports)
    assert high_error < low_error
    assert all(report.wonderkid_signal for report in high_reports)


def test_manager_recommendation_styles_prioritize_different_profiles(session) -> None:
    club = _create_club(session, slug="regen-style-recommendations")
    regens = _starter_regens(session, club.id)
    youth_target, star_target = regens[0], regens[1]
    _make_wonderkid(session, youth_target, current_min=67, current_max=71, potential_min=89, potential_max=94)
    star_target.is_special_lineage = True
    star_target.metadata_json = {
        **star_target.metadata_json,
        "hall_of_fame_bound": True,
        "son_of_legend": True,
    }
    star_target.current_ability_range_json = {"minimum": 80, "maximum": 84}
    star_target.potential_range_json = {"minimum": 86, "maximum": 90}
    star_target.current_gsi = 84
    session.flush()

    service = RegenMarketService(session)
    service.record_award(star_target.id, RegenAwardEvent(award_code="gtex_best_player_shortlist", fan_demand_score=1.5), club_id=club.id)
    service.refresh_value(youth_target.id)

    youth_recommendation = service.recommend_regens(
        RegenRecommendationRequest(
            club_id=club.id,
            manager_style="youth_developer",
            premium_service=True,
            limit=1,
        )
    )[0]
    star_recommendation = service.recommend_regens(
        RegenRecommendationRequest(
            club_id=club.id,
            manager_style="star_recruiter",
            limit=1,
        )
    )[0]

    assert youth_recommendation.regen_id == youth_target.regen_id
    assert star_recommendation.regen_id == star_target.regen_id


def test_high_regen_trade_fee_applies_by_default(session) -> None:
    club = _create_club(session, slug="regen-fee-default")
    regen = _starter_regens(session, club.id)[0]
    _make_tradable(session, regen)
    service = RegenMarketService(session)

    settlement = service.quote_transfer_settlement(regen.id, 10_000)

    assert settlement.applied_fee_bps == 4_500
    assert settlement.fee_amount_coin == 4_500
    assert settlement.seller_net_coin == 5_500
    assert settlement.guardrail_triggered is False


def test_onboarding_starter_regens_are_non_tradable(session) -> None:
    club = _create_club(session, slug="regen-onboarding")
    regens = _starter_regens(session, club.id)
    flags = session.scalars(
        select(RegenOnboardingFlag).where(RegenOnboardingFlag.club_id == club.id).order_by(RegenOnboardingFlag.squad_slot)
    ).all()
    service = RegenMarketService(session)

    assert len(flags) == 2
    assert all(flag.is_non_tradable for flag in flags)
    assert flags[0].metadata_json["starter_first_team_target"] == 18
    assert flags[0].metadata_json["starter_academy_target"] == 18
    with pytest.raises(RegenTradeRestrictedError, match="starter_regen_non_tradable"):
        service.quote_transfer_settlement(regens[0].id, 8_000)


def test_real_player_balance_protections_cool_regen_demand(session) -> None:
    club = _create_club(session, slug="regen-balance-protection")
    regen = _starter_regens(session, club.id)[0]
    _make_tradable(session, regen)
    service = RegenMarketService(session)

    baseline = service.record_demand_signal(
        regen.id,
        RegenDemandEvent(signal_type="fan_demand", signal_strength=3.0, supporting_count=2),
    )
    _open_listing(session, regen, listing_id="listing-regen-pressure")
    cooled = service.record_demand_signal(
        regen.id,
        RegenDemandEvent(signal_type="fan_demand", signal_strength=3.0, supporting_count=2),
    )
    pressured_settlement = service.quote_transfer_settlement(regen.id, 10_000)

    assert cooled.guardrail_multiplier < baseline.guardrail_multiplier
    assert cooled.metadata["market_balance"]["regen_market_share"] > 0.20
    assert pressured_settlement.guardrail_triggered is True
    assert pressured_settlement.applied_fee_bps > 4_500


def test_wonderkid_discovery_flow_and_search_hooks(session) -> None:
    club = _create_club(session, slug="regen-wonderkid-flow")
    regen = _starter_regens(session, club.id)[0]
    _make_tradable(session, regen)
    _make_wonderkid(session, regen, current_min=69, current_max=72, potential_min=89, potential_max=94)
    contract = _contract_for_regen(session, regen)
    contract.ends_on = date.today() + timedelta(days=10)
    session.flush()
    _open_listing(session, regen, listing_id="listing-wonderkid")

    service = RegenMarketService(session)
    service.record_award(
        regen.id,
        RegenAwardEvent(
            award_code="golden_boy_shortlist",
            fan_demand_score=2.5,
            narrative_significance=2.0,
        ),
        club_id=club.id,
    )
    report = service.create_scout_report(
        regen.id,
        club_id=club.id,
        scout_identity="chief-scout",
        scout_rating=91,
        manager_style="youth_developer",
        premium_service=True,
    )
    results = service.search_regens(
        RegenSearchFilters(
            position_needs=(regen.primary_position,),
            age_max=20,
            potential_min=85,
            transfer_listed_only=True,
            contract_expires_within_days=30,
            hometown_affinity=club.club_name,
            award_codes=("golden_boy_shortlist",),
            wonderkid_only=True,
        )
    )

    assert report.wonderkid_signal is True
    assert "premium_intel" in report.tags
    assert len(results) == 1
    assert results[0].profile.regen_id == regen.regen_id
