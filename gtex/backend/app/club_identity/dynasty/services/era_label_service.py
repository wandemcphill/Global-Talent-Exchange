from __future__ import annotations

from app.club_identity.models.dynasty_models import (
    DynastyAssessment,
    DynastyStatus,
    DynastyWindowMetrics,
    EraLabel,
)


class EraLabelService:
    def assess(self, metrics: DynastyWindowMetrics) -> DynastyAssessment:
        reasons: list[str] = []
        score = self._score(metrics)

        if self._is_global_dynasty(metrics):
            reasons.extend(
                [
                    "Won the World Super Cup inside the rolling four-season window",
                    "Sustained top-four league finishes while staying in the global qualification tier",
                    "Backed the global win with domestic or continental silverware",
                ]
            )
            return DynastyAssessment(
                dynasty_status=DynastyStatus.ACTIVE,
                era_label=EraLabel.GLOBAL_DYNASTY,
                active_dynasty=True,
                dynasty_score=score,
                reasons=tuple(reasons),
            )

        if self._is_continental_dynasty(metrics):
            reasons.extend(
                [
                    "Lifted a Champions League title in the rolling window",
                    "Paired continental success with repeated elite league finishes",
                    "Qualified repeatedly for the World Super Cup path",
                ]
            )
            return DynastyAssessment(
                dynasty_status=DynastyStatus.ACTIVE,
                era_label=EraLabel.CONTINENTAL_DYNASTY,
                active_dynasty=True,
                dynasty_score=score,
                reasons=tuple(reasons),
            )

        if self._is_dominant_era(metrics):
            reasons.extend(
                [
                    "Won at least two league titles inside four seasons",
                    "Stayed in the top four often enough to prove the run is sustained",
                ]
            )
            return DynastyAssessment(
                dynasty_status=DynastyStatus.ACTIVE,
                era_label=EraLabel.DOMINANT_ERA,
                active_dynasty=True,
                dynasty_score=score,
                reasons=tuple(reasons),
            )

        if self._is_emerging_power(metrics):
            reasons.extend(
                [
                    "Built a sharp two-season surge with trophies and top-four finishes",
                    "Added meaningful reputation growth to the on-pitch rise",
                ]
            )
            return DynastyAssessment(
                dynasty_status=DynastyStatus.ACTIVE,
                era_label=EraLabel.EMERGING_POWER,
                active_dynasty=True,
                dynasty_score=score,
                reasons=tuple(reasons),
            )

        return DynastyAssessment(
            dynasty_status=DynastyStatus.NONE,
            era_label=EraLabel.NONE,
            active_dynasty=False,
            dynasty_score=score,
            reasons=tuple(),
        )

    def _score(self, metrics: DynastyWindowMetrics) -> int:
        score = 0
        score += metrics.league_titles * 24
        score += metrics.champions_league_titles * 34
        score += metrics.world_super_cup_titles * 42
        score += metrics.top_four_finishes * 6
        score += metrics.world_super_cup_qualifications * 7
        score += metrics.elite_finishes * 4
        score += min(metrics.trophy_density, 8) * 4
        score += max(0, min(metrics.reputation_gain_total, 60)) // 3
        if metrics.league_titles >= 2:
            score += 8
        if metrics.champions_league_titles >= 1:
            score += 10
        if metrics.world_super_cup_titles >= 1:
            score += 12
        return score

    def _is_emerging_power(self, metrics: DynastyWindowMetrics) -> bool:
        if metrics.season_count < 2:
            return False
        has_hero_result = (
            metrics.recent_two_league_titles >= 1
            or metrics.champions_league_titles >= 1
            or metrics.world_super_cup_qualifications >= 1
        )
        return (
            metrics.recent_two_top_four_finishes >= 2
            and metrics.recent_two_trophy_density >= 2
            and metrics.recent_two_reputation_gain >= 12
            and has_hero_result
        )

    def _is_dominant_era(self, metrics: DynastyWindowMetrics) -> bool:
        return (
            metrics.season_count >= 4
            and metrics.league_titles >= 2
            and metrics.top_four_finishes >= 3
            and metrics.trophy_density >= 3
            and metrics.reputation_gain_total >= 18
        )

    def _is_continental_dynasty(self, metrics: DynastyWindowMetrics) -> bool:
        return (
            metrics.season_count >= 4
            and metrics.champions_league_titles >= 1
            and metrics.top_four_finishes >= 3
            and metrics.world_super_cup_qualifications >= 2
            and metrics.trophy_density >= 4
            and metrics.reputation_gain_total >= 24
            and (metrics.league_titles >= 1 or metrics.elite_finishes >= 2)
        )

    def _is_global_dynasty(self, metrics: DynastyWindowMetrics) -> bool:
        return (
            metrics.season_count >= 4
            and metrics.world_super_cup_titles >= 1
            and metrics.world_super_cup_qualifications >= 2
            and metrics.top_four_finishes >= 3
            and metrics.trophy_density >= 5
            and metrics.reputation_gain_total >= 30
            and (metrics.league_titles >= 2 or metrics.champions_league_titles >= 1)
        )
