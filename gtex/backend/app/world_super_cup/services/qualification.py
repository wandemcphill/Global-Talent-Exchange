from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.config.competition_constants import (
    WORLD_SUPER_CUP_DIRECT_SLOTS,
    WORLD_SUPER_CUP_PLAYOFF_TEAMS,
)
from app.world_super_cup.models import (
    ClubSeasonPerformance,
    CoefficientEntry,
    PlayoffMatch,
    QualificationPlan,
    QualifiedClub,
)
from app.world_super_cup.services.match_resolution import resolve_seeded_score


@dataclass(frozen=True, slots=True)
class _ClubQualificationProfile:
    club_id: str
    club_name: str
    region: str
    total_points: int
    recent_points: int
    previous_points: int
    winner_seasons: tuple[int, ...]
    runner_up_seasons: tuple[int, ...]


@dataclass(slots=True)
class QualificationCoefficientService:
    def seasons_considered(self, results: tuple[ClubSeasonPerformance, ...]) -> tuple[int, int]:
        seasons = sorted({result.season_year for result in results}, reverse=True)
        if len(seasons) < 2:
            raise ValueError("World Super Cup qualification requires two completed seasons")
        return seasons[0], seasons[1]

    def build_table(self, results: tuple[ClubSeasonPerformance, ...]) -> tuple[CoefficientEntry, ...]:
        recent_season, previous_season = self.seasons_considered(results)
        profiles = self._build_profiles(results, recent_season, previous_season)
        entries = [
            CoefficientEntry(
                club_id=profile.club_id,
                club_name=profile.club_name,
                region=profile.region,
                total_points=profile.total_points,
                recent_season_points=profile.recent_points,
                previous_season_points=profile.previous_points,
                winner_seasons=profile.winner_seasons,
                runner_up_seasons=profile.runner_up_seasons,
            )
            for profile in profiles.values()
        ]
        return tuple(
            sorted(
                entries,
                key=lambda entry: (
                    -entry.total_points,
                    -entry.recent_season_points,
                    -entry.previous_season_points,
                    entry.club_name,
                ),
            )
        )

    def _build_profiles(
        self,
        results: tuple[ClubSeasonPerformance, ...],
        recent_season: int,
        previous_season: int,
    ) -> dict[str, _ClubQualificationProfile]:
        season_filter = {recent_season, previous_season}
        bucket: dict[str, dict[str, object]] = {}
        for result in results:
            if result.season_year not in season_filter:
                continue
            if result.club_id not in bucket:
                bucket[result.club_id] = {
                    "club_name": result.club_name,
                    "region": result.region,
                    "total_points": 0,
                    "recent_points": 0,
                    "previous_points": 0,
                    "winner_seasons": [],
                    "runner_up_seasons": [],
                }
            current = bucket[result.club_id]
            current["total_points"] = int(current["total_points"]) + result.coefficient_points
            if result.season_year == recent_season:
                current["recent_points"] = int(current["recent_points"]) + result.coefficient_points
            elif result.season_year == previous_season:
                current["previous_points"] = int(current["previous_points"]) + result.coefficient_points
            if result.continental_finish == "winner":
                current["winner_seasons"].append(result.season_year)
            elif result.continental_finish == "runner_up":
                current["runner_up_seasons"].append(result.season_year)

        profiles: dict[str, _ClubQualificationProfile] = {}
        for club_id, current in bucket.items():
            profiles[club_id] = _ClubQualificationProfile(
                club_id=club_id,
                club_name=str(current["club_name"]),
                region=str(current["region"]),
                total_points=int(current["total_points"]),
                recent_points=int(current["recent_points"]),
                previous_points=int(current["previous_points"]),
                winner_seasons=tuple(sorted(current["winner_seasons"], reverse=True)),
                runner_up_seasons=tuple(sorted(current["runner_up_seasons"], reverse=True)),
            )
        return profiles


@dataclass(slots=True)
class DirectQualifierSelector:
    total_slots: int = WORLD_SUPER_CUP_DIRECT_SLOTS
    support_equal_region_representation: bool = True

    def select(
        self,
        coefficient_table: tuple[CoefficientEntry, ...],
    ) -> tuple[QualifiedClub, ...]:
        regions = tuple(sorted({entry.region for entry in coefficient_table}))
        quotas = self._allocate_region_slots(coefficient_table, regions)
        profiles = self._profiles_by_region(coefficient_table)
        selected_ids: set[str] = set()
        qualifiers: list[QualifiedClub] = []
        overall_seed = 1

        for region in regions:
            candidates = self._ordered_region_candidates(profiles[region])
            regional_seed = 1
            for entry, qualification_path in candidates:
                if regional_seed > quotas[region]:
                    break
                qualifiers.append(
                    QualifiedClub(
                        club_id=entry.club_id,
                        club_name=entry.club_name,
                        region=entry.region,
                        qualification_path=qualification_path,
                        coefficient_points=entry.total_points,
                        regional_seed=regional_seed,
                        overall_seed=overall_seed,
                    )
                )
                selected_ids.add(entry.club_id)
                regional_seed += 1
                overall_seed += 1

        if len(qualifiers) < self.total_slots:
            for entry in coefficient_table:
                if entry.club_id in selected_ids:
                    continue
                qualifiers.append(
                    QualifiedClub(
                        club_id=entry.club_id,
                        club_name=entry.club_name,
                        region=entry.region,
                        qualification_path=self._qualification_path(entry),
                        coefficient_points=entry.total_points,
                        regional_seed=quotas.get(entry.region, 0) + 1,
                        overall_seed=overall_seed,
                    )
                )
                selected_ids.add(entry.club_id)
                overall_seed += 1
                if len(qualifiers) == self.total_slots:
                    break

        return tuple(qualifiers)

    def _allocate_region_slots(
        self,
        coefficient_table: tuple[CoefficientEntry, ...],
        regions: tuple[str, ...],
    ) -> dict[str, int]:
        if not regions:
            return {}
        base_slots = self.total_slots // len(regions)
        remainder = self.total_slots % len(regions)
        quotas = {region: base_slots for region in regions}
        if self.support_equal_region_representation and remainder == 0:
            return quotas

        region_strength = {
            region: max(entry.total_points for entry in coefficient_table if entry.region == region) for region in regions
        }
        ordered_regions = sorted(regions, key=lambda region: (-region_strength[region], region))
        for region in ordered_regions[:remainder]:
            quotas[region] += 1
        return quotas

    def _profiles_by_region(
        self,
        coefficient_table: tuple[CoefficientEntry, ...],
    ) -> dict[str, tuple[CoefficientEntry, ...]]:
        grouped: dict[str, list[CoefficientEntry]] = {}
        for entry in coefficient_table:
            grouped.setdefault(entry.region, []).append(entry)
        return {
            region: tuple(
                sorted(
                    entries,
                    key=lambda entry: (
                        -entry.total_points,
                        -entry.recent_season_points,
                        -entry.previous_season_points,
                        entry.club_name,
                    ),
                )
            )
            for region, entries in grouped.items()
        }

    def _ordered_region_candidates(
        self,
        entries: tuple[CoefficientEntry, ...],
    ) -> tuple[tuple[CoefficientEntry, str], ...]:
        ordered: list[tuple[CoefficientEntry, str]] = []
        seen: set[str] = set()

        winners = sorted(
            [entry for entry in entries if entry.winner_seasons],
            key=lambda entry: (-max(entry.winner_seasons), -entry.total_points, entry.club_name),
        )
        runners_up = sorted(
            [entry for entry in entries if entry.runner_up_seasons],
            key=lambda entry: (-max(entry.runner_up_seasons), -entry.total_points, entry.club_name),
        )

        for entry in winners:
            if entry.club_id not in seen:
                ordered.append((entry, "continental_winner"))
                seen.add(entry.club_id)
        for entry in runners_up:
            if entry.club_id not in seen:
                ordered.append((entry, "runner_up"))
                seen.add(entry.club_id)
        for entry in entries:
            if entry.club_id not in seen:
                ordered.append((entry, "coefficient"))
                seen.add(entry.club_id)

        return tuple(ordered)

    def _qualification_path(self, entry: CoefficientEntry) -> str:
        if entry.winner_seasons:
            return "continental_winner"
        if entry.runner_up_seasons:
            return "runner_up"
        return "coefficient"


@dataclass(slots=True)
class PlayoffQualifierSelector:
    total_slots: int = WORLD_SUPER_CUP_PLAYOFF_TEAMS

    def select(
        self,
        coefficient_table: tuple[CoefficientEntry, ...],
        direct_qualifiers: tuple[QualifiedClub, ...],
    ) -> tuple[QualifiedClub, ...]:
        selected_direct = {club.club_id for club in direct_qualifiers}
        remaining_entries = tuple(entry for entry in coefficient_table if entry.club_id not in selected_direct)
        regions = tuple(sorted({entry.region for entry in remaining_entries}))
        quotas = self._allocate_region_slots(remaining_entries, regions)
        grouped = self._profiles_by_region(remaining_entries)
        qualifiers: list[QualifiedClub] = []
        selected_ids: set[str] = set()
        overall_seed = 1

        for region in regions:
            regional_seed = 1
            for entry in grouped[region]:
                if regional_seed > quotas[region]:
                    break
                qualifiers.append(
                    QualifiedClub(
                        club_id=entry.club_id,
                        club_name=entry.club_name,
                        region=entry.region,
                        qualification_path="playoff_seed",
                        coefficient_points=entry.total_points,
                        regional_seed=regional_seed,
                        overall_seed=overall_seed,
                    )
                )
                selected_ids.add(entry.club_id)
                regional_seed += 1
                overall_seed += 1

        if len(qualifiers) < self.total_slots:
            for entry in remaining_entries:
                if entry.club_id in selected_ids:
                    continue
                qualifiers.append(
                    QualifiedClub(
                        club_id=entry.club_id,
                        club_name=entry.club_name,
                        region=entry.region,
                        qualification_path="playoff_seed",
                        coefficient_points=entry.total_points,
                        regional_seed=quotas.get(entry.region, 0) + 1,
                        overall_seed=overall_seed,
                    )
                )
                selected_ids.add(entry.club_id)
                overall_seed += 1
                if len(qualifiers) == self.total_slots:
                    break

        return tuple(
            sorted(
                qualifiers,
                key=lambda club: (-club.coefficient_points, club.club_name),
            )
        )

    def _allocate_region_slots(
        self,
        coefficient_table: tuple[CoefficientEntry, ...],
        regions: tuple[str, ...],
    ) -> dict[str, int]:
        if not regions:
            return {}
        base_slots = self.total_slots // len(regions)
        remainder = self.total_slots % len(regions)
        quotas = {region: base_slots for region in regions}
        region_strength = {
            region: max(entry.total_points for entry in coefficient_table if entry.region == region) for region in regions
        }
        ordered_regions = sorted(regions, key=lambda region: (-region_strength[region], region))
        for region in ordered_regions[:remainder]:
            quotas[region] += 1
        return quotas

    def _profiles_by_region(
        self,
        coefficient_table: tuple[CoefficientEntry, ...],
    ) -> dict[str, tuple[CoefficientEntry, ...]]:
        grouped: dict[str, list[CoefficientEntry]] = {}
        for entry in coefficient_table:
            grouped.setdefault(entry.region, []).append(entry)
        return {
            region: tuple(
                sorted(
                    entries,
                    key=lambda entry: (
                        -entry.total_points,
                        -entry.recent_season_points,
                        -entry.previous_season_points,
                        entry.club_name,
                    ),
                )
            )
            for region, entries in grouped.items()
        }


@dataclass(slots=True)
class WorldSuperCupQualificationService:
    coefficient_service: QualificationCoefficientService = field(default_factory=QualificationCoefficientService)
    direct_selector: DirectQualifierSelector = field(default_factory=DirectQualifierSelector)
    playoff_selector: PlayoffQualifierSelector = field(default_factory=PlayoffQualifierSelector)

    def build_plan(
        self,
        results: tuple[ClubSeasonPerformance, ...],
        tournament_start: datetime,
    ) -> QualificationPlan:
        seasons_considered = self.coefficient_service.seasons_considered(results)
        coefficient_table = self.coefficient_service.build_table(results)
        direct_qualifiers = self.direct_selector.select(coefficient_table)
        playoff_qualifiers = self.playoff_selector.select(coefficient_table, direct_qualifiers)
        playoff_matches = self._generate_playoff_matches(playoff_qualifiers, tournament_start)
        playoff_winners = tuple(
            QualifiedClub(
                club_id=match.winner.club_id,
                club_name=match.winner.club_name,
                region=match.winner.region,
                qualification_path="playoff_winner",
                coefficient_points=match.winner.coefficient_points,
                regional_seed=match.winner.regional_seed,
                overall_seed=index,
            )
            for index, match in enumerate(playoff_matches, start=1)
            if match.winner is not None
        )
        main_event_clubs = tuple(
            sorted(
                (*direct_qualifiers, *playoff_winners),
                key=lambda club: (-club.coefficient_points, club.club_name),
            )
        )
        return QualificationPlan(
            seasons_considered=seasons_considered,
            coefficient_table=coefficient_table,
            direct_qualifiers=direct_qualifiers,
            playoff_qualifiers=playoff_qualifiers,
            playoff_matches=playoff_matches,
            playoff_winners=playoff_winners,
            main_event_clubs=main_event_clubs,
        )

    def _generate_playoff_matches(
        self,
        playoff_qualifiers: tuple[QualifiedClub, ...],
        tournament_start: datetime,
    ) -> tuple[PlayoffMatch, ...]:
        ordered = tuple(
            sorted(playoff_qualifiers, key=lambda club: (-club.coefficient_points, club.club_name))
        )
        matches: list[PlayoffMatch] = []
        pair_count = len(ordered) // 2
        for index in range(pair_count):
            home_club = ordered[index]
            away_club = ordered[-(index + 1)]
            kickoff_at = tournament_start.replace(hour=8, minute=0) + timedelta(minutes=index * 15)
            home_score, away_score, decided_by = resolve_seeded_score(
                home_club.coefficient_points,
                away_club.coefficient_points,
                allow_draw=False,
            )
            winner = home_club if home_score > away_score else away_club
            if home_score == away_score:
                winner = home_club if home_club.coefficient_points >= away_club.coefficient_points else away_club
            matches.append(
                PlayoffMatch(
                    match_id=f"playoff-{index + 1}",
                    stage="playoff",
                    home_club=home_club,
                    away_club=away_club,
                    kickoff_at=kickoff_at,
                    venue=f"Qualifier Hub {index + 1}",
                    winner=winner,
                    decided_by=decided_by,
                    home_score=home_score,
                    away_score=away_score,
                )
            )
        return tuple(matches)
