from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.regen_universe.ranking_engine import ComputedPerformance, RankedPerformance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class AwardDefinition:
    code: str
    name: str
    description: str
    category: str
    ranking_category: str | None
    eligibility_rules: dict[str, object]
    sort_order: int
    metadata: dict[str, object]


@dataclass(frozen=True, slots=True)
class AwardSelection:
    award_code: str
    player_id: str
    player_name: str
    ranking_score: float
    rank: int | None
    metadata: dict[str, object]


DEFAULT_AWARD_DEFINITIONS: tuple[AwardDefinition, ...] = (
    AwardDefinition(
        code="WORLD_PLAYER",
        name="GTEX World Player of the Year",
        description="Best regen performer across the full GTEX season based on deterministic prestige ranking.",
        category="seasonal",
        ranking_category="overall",
        eligibility_rules={"ranking_category": "overall"},
        sort_order=10,
        metadata={},
    ),
    AwardDefinition(
        code="GOLDEN_BOY",
        name="GTEX Golden Boy",
        description="Best U21 regen performer with elite seasonal impact and minutes.",
        category="seasonal",
        ranking_category="overall",
        eligibility_rules={"max_age": 21, "min_appearances": 8},
        sort_order=20,
        metadata={},
    ),
    AwardDefinition(
        code="TOP_SCORER",
        name="GTEX Top Scorer",
        description="Top regen goalscorer after weighting output, minutes, and competition context.",
        category="seasonal",
        ranking_category="forward",
        eligibility_rules={"min_appearances": 5},
        sort_order=30,
        metadata={},
    ),
    AwardDefinition(
        code="PLAYMAKER",
        name="GTEX Playmaker of the Year",
        description="Most influential regen creator judged by assists, ratings, and sustained impact.",
        category="seasonal",
        ranking_category="overall",
        eligibility_rules={"min_appearances": 5},
        sort_order=40,
        metadata={},
    ),
    AwardDefinition(
        code="DEFENDER",
        name="GTEX Defender of the Year",
        description="Top defensive regen measured by clean sheets, reliability, ratings, and winning impact.",
        category="seasonal",
        ranking_category="defender",
        eligibility_rules={"position_groups": ["defender"], "min_appearances": 5},
        sort_order=50,
        metadata={},
    ),
    AwardDefinition(
        code="GOALKEEPER",
        name="GTEX Goalkeeper of the Year",
        description="Top regen goalkeeper based on shot-stopping, clean sheets, ratings, and consistency.",
        category="seasonal",
        ranking_category="goalkeeper",
        eligibility_rules={"position_groups": ["goalkeeper"], "min_appearances": 5},
        sort_order=60,
        metadata={},
    ),
    AwardDefinition(
        code="BREAKOUT_STAR",
        name="GTEX Breakout Star",
        description="Most improved regen compared with the previous GTEX season or, for debut seasons, a controlled baseline.",
        category="seasonal",
        ranking_category="overall",
        eligibility_rules={"min_appearances": 8, "requires_improvement": True},
        sort_order=70,
        metadata={},
    ),
    AwardDefinition(
        code="TEAM_OF_THE_YEAR",
        name="GTEX Team of the Year",
        description="Best regen XI selected by a deterministic 4-3-3 from position-based prestige rankings.",
        category="team_selection",
        ranking_category=None,
        eligibility_rules={"formation": {"goalkeeper": 1, "defender": 4, "midfielder": 3, "forward": 3}},
        sort_order=80,
        metadata={},
    ),
)


class AwardsEngine:
    def select_winners(
        self,
        *,
        definitions: list[AwardDefinition],
        performances: list[ComputedPerformance],
        rankings: dict[str, list[RankedPerformance]],
    ) -> list[AwardSelection]:
        if not performances:
            return []
        records_by_player = {record.player_id: record for record in performances}
        selections: list[AwardSelection] = []
        for definition in sorted(definitions, key=lambda item: item.sort_order):
            if definition.code == "WORLD_PLAYER":
                winner = self._from_ranking(definition, rankings.get("overall", []), records_by_player)
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "GOLDEN_BOY":
                winner = self._select_best(
                    definition,
                    candidates=self._eligible(performances, definition.eligibility_rules),
                    score_getter=lambda item: item.overall_score,
                )
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "TOP_SCORER":
                winner = self._select_best(
                    definition,
                    candidates=self._eligible(performances, definition.eligibility_rules),
                    score_getter=lambda item: item.scorer_score,
                )
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "PLAYMAKER":
                winner = self._select_best(
                    definition,
                    candidates=self._eligible(performances, definition.eligibility_rules),
                    score_getter=lambda item: item.playmaker_score,
                )
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "DEFENDER":
                winner = self._from_ranking(definition, rankings.get("defender", []), records_by_player)
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "GOALKEEPER":
                winner = self._from_ranking(definition, rankings.get("goalkeeper", []), records_by_player)
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "BREAKOUT_STAR":
                winner = self._select_best(
                    definition,
                    candidates=[
                        item
                        for item in self._eligible(performances, definition.eligibility_rules)
                        if item.improvement_score > 0
                    ],
                    score_getter=lambda item: item.improvement_score,
                )
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "TEAM_OF_THE_YEAR":
                selections.extend(self._team_of_the_year(definition, rankings, records_by_player))
        return selections

    def _from_ranking(
        self,
        definition: AwardDefinition,
        ranking: list[RankedPerformance],
        records_by_player: dict[str, ComputedPerformance],
    ) -> AwardSelection | None:
        if not ranking:
            return None
        top = ranking[0]
        record = records_by_player[top.player_id]
        return AwardSelection(
            award_code=definition.code,
            player_id=top.player_id,
            player_name=top.player_name,
            ranking_score=top.score,
            rank=top.rank,
            metadata={
                "award_name": definition.name,
                "selection_reason": f"ranked #{top.rank} in {top.category}",
                "category": top.category,
                "score_breakdown": record.metadata.get("score_breakdown", {}),
                "awarded_at": _utcnow().isoformat(),
            },
        )

    def _select_best(
        self,
        definition: AwardDefinition,
        *,
        candidates: list[ComputedPerformance],
        score_getter,
    ) -> AwardSelection | None:
        if not candidates:
            return None
        ordered = sorted(
            candidates,
            key=lambda item: (
                -round(score_getter(item), 4),
                -item.minutes_played,
                -item.goals,
                -item.assists,
                item.player_name.casefold(),
                item.player_id,
            ),
        )
        winner = ordered[0]
        return AwardSelection(
            award_code=definition.code,
            player_id=winner.player_id,
            player_name=winner.player_name,
            ranking_score=round(score_getter(winner), 4),
            rank=1,
            metadata={
                "award_name": definition.name,
                "selection_reason": "best eligible player by deterministic award score",
                "position_group": winner.position_group,
                "score_breakdown": winner.metadata.get("score_breakdown", {}),
                "eligibility": definition.eligibility_rules,
                "awarded_at": _utcnow().isoformat(),
            },
        )

    def _team_of_the_year(
        self,
        definition: AwardDefinition,
        rankings: dict[str, list[RankedPerformance]],
        records_by_player: dict[str, ComputedPerformance],
    ) -> list[AwardSelection]:
        formation = definition.eligibility_rules.get("formation", {})
        selected_player_ids: set[str] = set()
        selections: list[AwardSelection] = []
        slot = 1
        for category, required_count in formation.items():
            category_rankings = rankings.get(category, [])
            chosen = 0
            for ranked in category_rankings:
                if ranked.player_id in selected_player_ids:
                    continue
                selected_player_ids.add(ranked.player_id)
                record = records_by_player[ranked.player_id]
                selections.append(
                    AwardSelection(
                        award_code=definition.code,
                        player_id=ranked.player_id,
                        player_name=ranked.player_name,
                        ranking_score=ranked.score,
                        rank=slot,
                        metadata={
                            "award_name": definition.name,
                            "selection_reason": f"selected for {category} slot in 4-3-3",
                            "position_group": record.position_group,
                            "team_slot": slot,
                            "formation": formation,
                            "score_breakdown": record.metadata.get("score_breakdown", {}),
                            "awarded_at": _utcnow().isoformat(),
                        },
                    )
                )
                chosen += 1
                slot += 1
                if chosen >= int(required_count):
                    break
        return selections

    def _eligible(
        self,
        performances: list[ComputedPerformance],
        rules: dict[str, object],
    ) -> list[ComputedPerformance]:
        max_age = int(rules["max_age"]) if "max_age" in rules else None
        min_appearances = int(rules.get("min_appearances", 0))
        position_groups = {str(value) for value in rules.get("position_groups", [])}
        return [
            item
            for item in performances
            if item.appearances >= min_appearances
            and (max_age is None or (item.age is not None and item.age <= max_age))
            and (not position_groups or item.position_group in position_groups)
        ]


__all__ = ["AwardDefinition", "AwardSelection", "AwardsEngine", "DEFAULT_AWARD_DEFINITIONS"]
