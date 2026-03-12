from __future__ import annotations

from backend.app.club_identity.models.dynasty_models import (
    DynastyAssessment,
    DynastySnapshot,
    DynastyStatus,
    DynastyWindowMetrics,
    EraLabel,
)


class FallenGiantService:
    def maybe_mark_fallen_giant(
        self,
        current: DynastyAssessment,
        metrics: DynastyWindowMetrics,
        history: list[DynastySnapshot],
    ) -> DynastyAssessment:
        if current.active_dynasty or metrics.season_count < 4:
            return current

        major_history = [
            snapshot
            for snapshot in history
            if snapshot.era_label in {
                EraLabel.DOMINANT_ERA,
                EraLabel.CONTINENTAL_DYNASTY,
                EraLabel.GLOBAL_DYNASTY,
            }
        ]
        if not major_history:
            return current

        if not self._has_long_decline(metrics):
            return current

        peak_score = max(snapshot.dynasty_score for snapshot in major_history)
        reasons = (
            "Previously sustained a major dynasty-level peak",
            "Failed to win league, continental, or global titles across the latest four seasons",
            "Collapsed below the elite-finish bar that defined the earlier peak",
        )
        return DynastyAssessment(
            dynasty_status=DynastyStatus.FALLEN,
            era_label=EraLabel.FALLEN_GIANT,
            active_dynasty=False,
            dynasty_score=max(current.dynasty_score, max(25, peak_score - 30)),
            reasons=reasons,
        )

    def _has_long_decline(self, metrics: DynastyWindowMetrics) -> bool:
        return (
            metrics.league_titles == 0
            and metrics.champions_league_titles == 0
            and metrics.world_super_cup_titles == 0
            and metrics.top_four_finishes <= 1
            and metrics.trophy_density <= 1
            and metrics.reputation_gain_total <= 4
        )
