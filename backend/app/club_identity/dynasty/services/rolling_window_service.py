from __future__ import annotations

from app.club_identity.models.dynasty_models import (
    ClubDynastySeasonSummary,
    DynastyWindowMetrics,
)

DYNASTY_WINDOW_SEASONS = 4


class RollingWindowService:
    def build_windows(
        self,
        seasons: list[ClubDynastySeasonSummary],
    ) -> list[DynastyWindowMetrics]:
        if not seasons:
            return []

        ordered = sorted(seasons, key=lambda season: season.season_index)
        windows: list[DynastyWindowMetrics] = []
        for end_index in range(len(ordered)):
            start_index = max(0, end_index - (DYNASTY_WINDOW_SEASONS - 1))
            window = ordered[start_index : end_index + 1]
            recent_two = window[-2:]
            windows.append(
                DynastyWindowMetrics(
                    club_id=window[-1].club_id,
                    club_name=window[-1].club_name,
                    season_count=len(window),
                    window_start_season_id=window[0].season_id,
                    window_start_season_label=window[0].season_label,
                    window_end_season_id=window[-1].season_id,
                    window_end_season_label=window[-1].season_label,
                    seasons=tuple(window),
                    league_titles=sum(1 for season in window if season.league_title),
                    champions_league_titles=sum(1 for season in window if season.champions_league_title),
                    world_super_cup_titles=sum(1 for season in window if season.world_super_cup_winner),
                    top_four_finishes=sum(1 for season in window if season.top_four_finish),
                    elite_finishes=sum(1 for season in window if season.elite_finish),
                    world_super_cup_qualifications=sum(
                        1 for season in window if season.world_super_cup_qualified
                    ),
                    trophy_density=sum(season.trophy_count for season in window),
                    reputation_gain_total=sum(season.reputation_gain for season in window),
                    recent_two_top_four_finishes=sum(1 for season in recent_two if season.top_four_finish),
                    recent_two_trophy_density=sum(season.trophy_count for season in recent_two),
                    recent_two_reputation_gain=sum(season.reputation_gain for season in recent_two),
                    recent_two_league_titles=sum(1 for season in recent_two if season.league_title),
                )
            )
        return windows
