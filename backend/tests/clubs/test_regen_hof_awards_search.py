from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from backend.app.models.club_hall_of_fame import ClubHallOfFameEntry
from backend.app.models.regen import RegenLegacyRecord, RegenProfile
from backend.app.schemas.club_requests import ClubCreateRequest
from backend.app.services.club_branding_service import ClubBrandingService
from backend.app.services.club_hall_of_fame_service import ClubHallOfFameService
from backend.app.services.regen_legacy_service import RegenLegacyService
from backend.app.services.regen_lineage_service import RegenLineageService
from backend.app.services.regen_market_service import RegenAwardEvent, RegenMarketService, RegenSearchFilters
from backend.app.services.regen_service import LineageSelection


def _create_club(session, *, slug: str) -> object:
    return ClubBrandingService(session).create_club_profile(
        owner_user_id="user-owner",
        payload=ClubCreateRequest.model_validate(
            {
                "club_name": "Legacy FC",
                "short_name": "LFC",
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


def test_award_names_reject_regen_keyword(app_session_factory) -> None:
    with app_session_factory() as session:
        club = _create_club(session, slug="award-name-guard")
        regen = _starter_regens(session, club.id)[0]
        service = RegenMarketService(session)
        with pytest.raises(ValueError, match="award_name_contains_regen"):
            service.record_award(
                regen.id,
                RegenAwardEvent(award_code="mvp", award_name="Regen MVP"),
                club_id=club.id,
            )


def test_hall_of_fame_insertion(app_session_factory) -> None:
    with app_session_factory() as session:
        club = _create_club(session, slug="hof-insert")
        regen = _starter_regens(session, club.id)[0]
        service = ClubHallOfFameService(session)
        entry = service.add_entry(
            club_id=club.id,
            entry_category="Legends",
            regen_id=regen.id,
            narrative_summary="Club icon etched in history.",
        )
        stored = session.get(ClubHallOfFameEntry, entry.id)
        assert stored is not None
        assert stored.entry_category == "Legends"
        assert stored.regen_id == regen.id


def test_regen_search_filters_lineage_twins_awards(app_session_factory) -> None:
    with app_session_factory() as session:
        club = _create_club(session, slug="regen-search-filters")
        regen_a, regen_b = _starter_regens(session, club.id)[:2]

        lineage_service = RegenLineageService(session)
        lineage_service.attach_lineage(
            regen_id=regen_a.id,
            selection=LineageSelection(
                relationship_type="son_of_legend",
                related_legend_type="real_legend",
                related_legend_ref_id="legend-01",
                lineage_country_code=regen_a.birth_country_code,
                lineage_region_name=regen_a.birth_region,
                lineage_city_name=regen_a.birth_city,
                lineage_hometown_code=regen_a.birth_city,
                is_real_legend_lineage=True,
                tags=("son_of_legend", "lineage"),
            ),
        )
        regen_a.is_special_lineage = True
        lineage_service.attach_twins_group(
            regen_ids=(regen_a.id, regen_b.id),
            club_id=club.id,
            season_label="2026/2027",
            visual_seed="seed-legacy",
            similarity_score=0.9,
        )
        session.flush()

        market = RegenMarketService(session)
        market.record_award(
            regen_a.id,
            RegenAwardEvent(award_code="gtex_best_player", award_name="GTEX Best Player"),
            club_id=club.id,
        )
        legacy_service = RegenLegacyService(session)
        legacy = legacy_service.snapshot_legacy(regen_a.id, club_id=club.id, retired_on=date.today())
        legacy.is_legend = True
        legacy.legacy_score = max(legacy.legacy_score, 150.0)
        regen_a.status = "retired"
        session.flush()

        results = market.search_regens(RegenSearchFilters(sons_of_legends_only=True))
        assert regen_a.id in {item.profile.id for item in results}

        twin_results = market.search_regens(RegenSearchFilters(twins_only=True))
        twin_ids = {item.profile.id for item in twin_results}
        assert regen_a.id in twin_ids
        assert regen_b.id in twin_ids

        award_results = market.search_regens(RegenSearchFilters(award_winners_only=True))
        assert regen_a.id in {item.profile.id for item in award_results}

        legend_results = market.search_regens(RegenSearchFilters(retired_legends_only=True))
        assert regen_a.id in {item.profile.id for item in legend_results}

        legacy_record = session.scalar(select(RegenLegacyRecord).where(RegenLegacyRecord.regen_id == regen_a.id))
        assert legacy_record is not None
