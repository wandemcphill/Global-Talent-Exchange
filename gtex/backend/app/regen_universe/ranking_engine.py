from __future__ import annotations

from dataclasses import dataclass, field


RANKING_CATEGORIES = ("overall", "forward", "midfielder", "defender", "goalkeeper")


@dataclass(frozen=True, slots=True)
class PerformanceInput:
    player_id: str
    player_name: str
    age: int | None
    position_group: str
    appearances: int
    starts: int
    minutes_played: int
    goals: int
    assists: int
    clean_sheets: int
    saves: int
    average_rating: float | None
    matches_won: int
    competition_importance: float
    consistency_score: float
    previous_overall_score: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ComputedPerformance:
    player_id: str
    player_name: str
    age: int | None
    position_group: str
    appearances: int
    starts: int
    minutes_played: int
    goals: int
    assists: int
    clean_sheets: int
    saves: int
    average_rating: float | None
    matches_won: int
    win_ratio: float
    competition_importance: float
    consistency_score: float
    previous_overall_score: float | None
    improvement_score: float
    overall_score: float
    forward_score: float
    midfielder_score: float
    defender_score: float
    goalkeeper_score: float
    playmaker_score: float
    scorer_score: float
    metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class RankedPerformance:
    player_id: str
    player_name: str
    category: str
    score: float
    rank: int
    position_group: str
    metadata: dict[str, object]


class RankingEngine:
    def score_inputs(self, inputs: list[PerformanceInput]) -> list[ComputedPerformance]:
        return [self._score_item(item) for item in inputs]

    def build_rankings(self, records: list[ComputedPerformance]) -> dict[str, list[RankedPerformance]]:
        rankings: dict[str, list[RankedPerformance]] = {}
        score_map = {
            "overall": "overall_score",
            "forward": "forward_score",
            "midfielder": "midfielder_score",
            "defender": "defender_score",
            "goalkeeper": "goalkeeper_score",
        }
        for category in RANKING_CATEGORIES:
            candidates = [
                record
                for record in records
                if category == "overall" or record.position_group == category
            ]
            candidates.sort(key=lambda item: self._sort_key(item, getattr(item, score_map[category])))
            rankings[category] = [
                RankedPerformance(
                    player_id=item.player_id,
                    player_name=item.player_name,
                    category=category,
                    score=round(getattr(item, score_map[category]), 4),
                    rank=index,
                    position_group=item.position_group,
                    metadata={
                        "minutes_played": item.minutes_played,
                        "goals": item.goals,
                        "assists": item.assists,
                        "clean_sheets": item.clean_sheets,
                        "saves": item.saves,
                        "average_rating": item.average_rating,
                        "competition_importance": item.competition_importance,
                        "consistency_score": item.consistency_score,
                    },
                )
                for index, item in enumerate(candidates, start=1)
            ]
        return rankings

    def _score_item(self, item: PerformanceInput) -> ComputedPerformance:
        appearances = max(item.appearances, 0)
        starts = max(item.starts, 0)
        minutes = max(item.minutes_played, 0)
        goals = max(item.goals, 0)
        assists = max(item.assists, 0)
        clean_sheets = max(item.clean_sheets, 0)
        saves = max(item.saves, 0)
        rating = item.average_rating if item.average_rating is not None else 6.0
        rating_delta = max(rating - 6.0, 0.0)
        win_ratio = round(item.matches_won / appearances, 4) if appearances > 0 else 0.0
        competition_importance = max(item.competition_importance, 0.75)
        consistency = max(min(item.consistency_score, 1.0), 0.0)
        minutes_factor = min(minutes / 900.0, 4.0)
        start_factor = starts / appearances if appearances > 0 else 0.0

        forward_score = competition_importance * (
            (goals * 5.5)
            + (assists * 3.2)
            + (rating_delta * 18.0)
            + (minutes_factor * 6.0)
            + (win_ratio * 8.0)
            + (consistency * 10.0)
            + (start_factor * 4.0)
        )
        midfielder_score = competition_importance * (
            (goals * 2.2)
            + (assists * 4.4)
            + (clean_sheets * 0.6)
            + (rating_delta * 20.0)
            + (minutes_factor * 7.0)
            + (win_ratio * 9.0)
            + (consistency * 11.0)
            + (start_factor * 4.0)
        )
        defender_score = competition_importance * (
            (goals * 1.2)
            + (assists * 1.8)
            + (clean_sheets * 3.8)
            + (rating_delta * 21.0)
            + (minutes_factor * 8.0)
            + (win_ratio * 10.0)
            + (consistency * 11.0)
            + (start_factor * 4.5)
        )
        goalkeeper_score = competition_importance * (
            (clean_sheets * 4.5)
            + (saves * 0.35)
            + (rating_delta * 20.0)
            + (minutes_factor * 8.0)
            + (win_ratio * 10.0)
            + (consistency * 10.0)
            + (start_factor * 4.5)
        )
        overall_score = competition_importance * (
            (goals * 4.0)
            + (assists * 3.4)
            + (clean_sheets * 2.2)
            + (saves * 0.12)
            + (rating_delta * 18.0)
            + (minutes_factor * 7.0)
            + (win_ratio * 9.0)
            + (consistency * 10.0)
            + (start_factor * 4.0)
        )
        if item.position_group == "forward":
            overall_score += forward_score * 0.2
        elif item.position_group == "midfielder":
            overall_score += midfielder_score * 0.2
        elif item.position_group == "defender":
            overall_score += defender_score * 0.2
        elif item.position_group == "goalkeeper":
            overall_score += goalkeeper_score * 0.25

        playmaker_score = competition_importance * (
            (assists * 6.0)
            + (goals * 1.5)
            + (rating_delta * 16.0)
            + (minutes_factor * 6.0)
            + (win_ratio * 8.0)
            + (consistency * 9.0)
        )
        scorer_score = competition_importance * (
            (goals * 7.0)
            + (assists * 1.8)
            + (rating_delta * 14.0)
            + (minutes_factor * 5.0)
            + (win_ratio * 6.0)
            + (consistency * 6.0)
        )

        if item.previous_overall_score is None:
            improvement_score = round(overall_score * 0.35 if (item.age or 99) <= 23 and appearances >= 10 else 0.0, 4)
            improvement_basis = "debut_baseline" if improvement_score > 0 else "insufficient_baseline"
        else:
            improvement_score = round(overall_score - item.previous_overall_score, 4)
            improvement_basis = "previous_season"

        metadata = dict(item.metadata)
        metadata.update(
            {
                "score_breakdown": {
                    "competition_importance": round(competition_importance, 4),
                    "minutes_factor": round(minutes_factor, 4),
                    "start_factor": round(start_factor, 4),
                    "rating_delta": round(rating_delta, 4),
                    "win_ratio": round(win_ratio, 4),
                    "consistency_score": round(consistency, 4),
                },
                "improvement_basis": improvement_basis,
            }
        )
        return ComputedPerformance(
            player_id=item.player_id,
            player_name=item.player_name,
            age=item.age,
            position_group=item.position_group,
            appearances=appearances,
            starts=starts,
            minutes_played=minutes,
            goals=goals,
            assists=assists,
            clean_sheets=clean_sheets,
            saves=saves,
            average_rating=item.average_rating,
            matches_won=item.matches_won,
            win_ratio=round(win_ratio, 4),
            competition_importance=round(competition_importance, 4),
            consistency_score=round(consistency, 4),
            previous_overall_score=item.previous_overall_score,
            improvement_score=improvement_score,
            overall_score=round(overall_score, 4),
            forward_score=round(forward_score, 4),
            midfielder_score=round(midfielder_score, 4),
            defender_score=round(defender_score, 4),
            goalkeeper_score=round(goalkeeper_score, 4),
            playmaker_score=round(playmaker_score, 4),
            scorer_score=round(scorer_score, 4),
            metadata=metadata,
        )

    def _sort_key(self, item: ComputedPerformance, score: float) -> tuple[float, int, int, int, str, str]:
        return (
            -round(score, 4),
            -item.minutes_played,
            -item.goals,
            -item.assists,
            item.player_name.casefold(),
            item.player_id,
        )


__all__ = [
    "ComputedPerformance",
    "PerformanceInput",
    "RankedPerformance",
    "RANKING_CATEGORIES",
    "RankingEngine",
]
