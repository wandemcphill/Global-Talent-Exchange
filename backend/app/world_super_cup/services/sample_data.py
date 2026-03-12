from __future__ import annotations

from backend.app.world_super_cup.models import ClubSeasonPerformance

ACTIVE_REGIONS: tuple[str, ...] = (
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "Oceania",
    "South America",
)

REGION_STRENGTH: dict[str, int] = {
    "Africa": 2,
    "Asia": 4,
    "Europe": 8,
    "North America": 5,
    "Oceania": 1,
    "South America": 7,
}


def build_demo_season_results() -> tuple[ClubSeasonPerformance, ...]:
    results: list[ClubSeasonPerformance] = []
    recent_season = 2025
    previous_season = 2024

    for region in ACTIVE_REGIONS:
        regional_bonus = REGION_STRENGTH[region]
        slug = region.lower().replace(" ", "-")
        for club_number in range(1, 9):
            club_id = f"{slug}-club-{club_number}"
            club_name = f"{region} Club {club_number}"
            recent_points = 86 - (club_number * 5) + regional_bonus
            previous_points = 72 - (club_number * 4) + regional_bonus
            recent_finish = None
            previous_finish = None
            if club_number == 1:
                recent_finish = "winner"
            elif club_number == 2:
                recent_finish = "runner_up"
            elif club_number == 3:
                previous_finish = "winner"
            elif club_number == 4:
                previous_finish = "runner_up"

            results.append(
                ClubSeasonPerformance(
                    club_id=club_id,
                    club_name=club_name,
                    region=region,
                    season_year=recent_season,
                    coefficient_points=recent_points,
                    continental_finish=recent_finish,
                )
            )
            results.append(
                ClubSeasonPerformance(
                    club_id=club_id,
                    club_name=club_name,
                    region=region,
                    season_year=previous_season,
                    coefficient_points=previous_points,
                    continental_finish=previous_finish,
                )
            )

    return tuple(results)
