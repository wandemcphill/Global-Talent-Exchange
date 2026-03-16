from __future__ import annotations

from datetime import date
import random

import pytest

from backend.app.core.config import get_settings
from backend.app.services.regen_service import RegenClubContext, RegenGenerationEngine


def test_regen_service_generates_region_aware_academy_intake(club_ops_services) -> None:
    regen = club_ops_services["regen"]

    batch = regen.generate_academy_intake(
        club_id="club-lagos",
        club_context=RegenClubContext(
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            youth_coaching=4,
            training_level=4,
            academy_level=4,
            academy_investment=4,
            first_team_gsi=63,
            club_reputation=58,
        ),
        random_seed=7,
    )
    generated_regens = regen.list_regens("club-lagos")

    assert 2 <= batch.intake_size <= 4
    assert len(batch.candidates) == batch.intake_size
    assert len(generated_regens) == batch.intake_size
    assert all(candidate.birth_city == "Lagos" for candidate in batch.candidates)
    assert all(candidate.birth_region == "Lagos" for candidate in batch.candidates)
    assert all(profile.origin.ethnolinguistic_profile == "yoruba" for profile in generated_regens)
    assert all(profile.current_ability_range.minimum < profile.current_ability_range.maximum for profile in generated_regens)
    assert all(profile.potential_range.maximum >= profile.current_ability_range.maximum for profile in generated_regens)


def test_regen_service_bootstraps_two_unique_starter_regens(club_ops_services) -> None:
    regen = club_ops_services["regen"]

    bundle = regen.generate_starter_regens(
        club_id="club-starters",
        club_context=RegenClubContext(
            country_code="GH",
            region_name="Greater Accra",
            city_name="Accra",
            first_team_gsi=60,
        ),
        random_seed=11,
    )
    repeat_bundle = regen.generate_starter_regens(
        club_id="club-starters",
        club_context=RegenClubContext(country_code="GH", region_name="Greater Accra", city_name="Accra"),
        random_seed=11,
    )

    assert len(bundle.regens) == 2
    assert all(25 <= regen_profile.age <= 30 for regen_profile in bundle.regens)
    assert all(50 <= regen_profile.current_gsi <= 68 for regen_profile in bundle.regens)
    assert len({regen_profile.regen_id for regen_profile in bundle.regens}) == 2
    assert len({regen_profile.linked_unique_card_id for regen_profile in bundle.regens}) == 2
    assert {regen_profile.regen_id for regen_profile in repeat_bundle.regens} == {
        regen_profile.regen_id for regen_profile in bundle.regens
    }


def test_regen_service_enforces_season_supply_caps(club_ops_services) -> None:
    regen = club_ops_services["regen"]
    season_label = "2025/2026"

    regen.generate_starter_regens(
        club_id="club-cap-a",
        club_context=RegenClubContext(country_code="NG", region_name="Lagos", city_name="Lagos"),
        season_label=season_label,
        total_active_player_base=100,
        random_seed=3,
    )

    with pytest.raises(ValueError, match="season_regen_supply_cap_reached"):
        regen.generate_academy_intake(
            club_id="club-cap-b",
            club_context=RegenClubContext(country_code="NG", region_name="Enugu", city_name="Enugu"),
            season_label=season_label,
            total_active_player_base=100,
            intake_size=2,
            random_seed=4,
        )


def test_regen_naming_respects_nigerian_cultural_boundaries() -> None:
    engine = RegenGenerationEngine(get_settings())

    igbo_bundle = engine.generate_starter_regens(
        club_id="club-enugu",
        season_label="2025/2026",
        club_context=RegenClubContext(country_code="NG", region_name="Enugu", city_name="Enugu"),
        count=4,
        used_names=set(),
        rng=random.Random(21),
    )
    hausa_bundle = engine.generate_starter_regens(
        club_id="club-kano",
        season_label="2025/2026",
        club_context=RegenClubContext(country_code="NG", region_name="Kano", city_name="Kano"),
        count=4,
        used_names=set(),
        rng=random.Random(22),
    )

    assert all(profile.origin.ethnolinguistic_profile == "igbo" for profile in igbo_bundle.regens)
    assert all(profile.origin.religion_naming_pattern == "christian" for profile in igbo_bundle.regens)
    assert all(
        profile.display_name.split(" ", 1)[1] in {"Okeke", "Eze", "Okafor", "Nwosu", "Umeh", "Onyeka"}
        for profile in igbo_bundle.regens
    )
    assert all(profile.origin.ethnolinguistic_profile == "hausa" for profile in hausa_bundle.regens)
    assert all(profile.origin.religion_naming_pattern == "muslim" for profile in hausa_bundle.regens)
    assert all("Chibuzor Adekunle" != profile.display_name for profile in igbo_bundle.regens + hausa_bundle.regens)
    assert all("Ibrahim Jacob" != profile.display_name for profile in igbo_bundle.regens + hausa_bundle.regens)


def test_regen_quality_weighting_favors_strong_clubs() -> None:
    engine = RegenGenerationEngine(get_settings())
    strong_context = RegenClubContext(
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        youth_coaching=5,
        training_level=5,
        academy_level=5,
        academy_investment=5,
        first_team_gsi=75,
        club_reputation=72,
        competition_quality=70,
        manager_youth_development=70,
    )
    weak_context = RegenClubContext(
        country_code="NG",
        region_name="Kano",
        city_name="Kano",
        youth_coaching=1,
        training_level=1,
        academy_level=1,
        academy_investment=1,
        first_team_gsi=42,
        club_reputation=18,
        competition_quality=25,
        manager_youth_development=20,
    )

    strong_highs: list[int] = []
    weak_highs: list[int] = []
    for seed in range(40):
        strong_generated = engine.generate_academy_intake(
            club_id=f"club-strong-{seed}",
            season_label="2025/2026",
            club_context=strong_context,
            intake_size=1,
            used_names=set(),
            rng=random.Random(seed),
        )
        weak_generated = engine.generate_academy_intake(
            club_id=f"club-weak-{seed}",
            season_label="2025/2026",
            club_context=weak_context,
            intake_size=1,
            used_names=set(),
            rng=random.Random(seed),
        )
        strong_highs.append(strong_generated.regens[0].potential_range.maximum)
        weak_highs.append(weak_generated.regens[0].potential_range.maximum)

    assert sum(strong_highs) / len(strong_highs) > sum(weak_highs) / len(weak_highs)


def test_generated_academy_candidates_have_control_windows_and_can_expire_to_free_agency(club_ops_services) -> None:
    regen = club_ops_services["regen"]

    batch = regen.generate_academy_intake(
        club_id="club-window",
        club_context=RegenClubContext(country_code="NG", region_name="Lagos", city_name="Lagos"),
        season_label="2025/2026",
        intake_size=2,
        random_seed=12,
    )

    assert all(candidate.decision_deadline_on is not None for candidate in batch.candidates)
    assert all(candidate.free_agency_status == "club_control_window" for candidate in batch.candidates)
    assert all(candidate.platform_capture_share_pct == 70 for candidate in batch.candidates)
    assert all(candidate.previous_club_capture_share_pct == 30 for candidate in batch.candidates)

    released = regen.expire_candidate_control_windows(reference_on=date(2100, 1, 1))

    assert len(released) == len(batch.candidates)
    assert all(candidate.status == "free_agent" for candidate in released)
    assert all(candidate.free_agency_status == "open_market" for candidate in released)
    assert len(regen.list_free_agents()) == len(batch.candidates)
