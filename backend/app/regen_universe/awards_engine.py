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
        code="BALLON_DOR",
        name="GTEX World Player of the Year",
        description="Best regen performer across the full GTEX season based on deterministic prestige ranking.",
        category="individual",
        ranking_category="overall",
        eligibility_rules={"ranking_category": "overall"},
        sort_order=10,
        metadata={
            "equivalent_name": "World Player of the Year",
            "market_award_code": "gtex_best_player",
            "shortlist_sizes": [30, 10, 3],
        },
    ),
    AwardDefinition(
        code="GOLDEN_BOY",
        name="GTEX Young Player of the Year",
        description="Best U21 regen performer with elite seasonal impact and minutes.",
        category="individual",
        ranking_category="overall",
        eligibility_rules={"max_age": 21, "min_appearances": 8},
        sort_order=20,
        metadata={
            "equivalent_name": "Young Player of the Year",
            "market_award_code": "gtex_golden_boy",
            "shortlist_sizes": [30, 10, 3],
        },
    ),
    AwardDefinition(
        code="U17_WORLD_CUP_GOLDEN_BALL",
        name="GTEX U17 World Cup Golden Ball",
        description="Best performer in GTEX U17 World Cup competition play, including preseeded national regens.",
        category="national_competition",
        ranking_category="overall",
        eligibility_rules={
            "competition_scope": "national",
            "competition_families": ["u17_world_cup"],
            "age_bands": ["u17"],
            "min_appearances": 1,
        },
        sort_order=25,
        metadata={
            "equivalent_name": "U17 World Cup Golden Ball",
            "market_award_code": "gtex_u17_world_cup_golden_ball",
        },
    ),
    AwardDefinition(
        code="U20_WORLD_CUP_GOLDEN_BALL",
        name="GTEX U20 World Cup Golden Ball",
        description="Best performer in GTEX U20 World Cup competition play, including preseeded national regens.",
        category="national_competition",
        ranking_category="overall",
        eligibility_rules={
            "competition_scope": "national",
            "competition_families": ["u20_world_cup"],
            "age_bands": ["u20"],
            "min_appearances": 1,
        },
        sort_order=26,
        metadata={
            "equivalent_name": "U20 World Cup Golden Ball",
            "market_award_code": "gtex_u20_world_cup_golden_ball",
        },
    ),
    AwardDefinition(
        code="AFCON_PLAYER_OF_THE_TOURNAMENT",
        name="GTEX AFCON Player of the Tournament",
        description="Best performer across GTEX AFCON tournament matches, including preseeded national regens.",
        category="national_competition",
        ranking_category="overall",
        eligibility_rules={
            "competition_scope": "national",
            "competition_families": ["afcon"],
            "min_appearances": 1,
        },
        sort_order=27,
        metadata={
            "equivalent_name": "AFCON Player of the Tournament",
            "market_award_code": "gtex_afcon_player_of_the_tournament",
        },
    ),
    AwardDefinition(
        code="GOLDEN_BOOT",
        name="GTEX Golden Boot",
        description="Top regen goalscorer after weighting output, minutes, and competition context.",
        category="individual",
        ranking_category="forward",
        eligibility_rules={"min_appearances": 5},
        sort_order=30,
        metadata={
            "equivalent_name": "Golden Boot",
            "market_award_code": "gtex_top_scorer",
            "shortlist_sizes": [30, 10, 3],
        },
    ),
    AwardDefinition(
        code="BEST_MIDFIELDER",
        name="GTEX Best Midfielder",
        description="Most influential regen midfielder judged by creation, control, ratings, and sustained impact.",
        category="individual",
        ranking_category="midfielder",
        eligibility_rules={"position_groups": ["midfielder"], "min_appearances": 5},
        sort_order=40,
        metadata={
            "equivalent_name": "Best Midfielder",
            "market_award_code": "gtex_best_midfielder",
            "shortlist_sizes": [30, 10, 3],
        },
    ),
    AwardDefinition(
        code="BEST_DEFENDER",
        name="GTEX Best Defender",
        description="Top defensive regen measured by clean sheets, reliability, ratings, and winning impact.",
        category="individual",
        ranking_category="defender",
        eligibility_rules={"position_groups": ["defender"], "min_appearances": 5},
        sort_order=50,
        metadata={
            "equivalent_name": "Best Defender",
            "market_award_code": "gtex_best_defender",
            "shortlist_sizes": [30, 10, 3],
        },
    ),
    AwardDefinition(
        code="BEST_GOALKEEPER",
        name="GTEX Golden Glove",
        description="Top regen goalkeeper based on shot-stopping, clean sheets, ratings, and consistency.",
        category="individual",
        ranking_category="goalkeeper",
        eligibility_rules={"position_groups": ["goalkeeper"], "min_appearances": 5},
        sort_order=60,
        metadata={
            "equivalent_name": "Golden Glove",
            "market_award_code": "gtex_best_goalkeeper",
            "shortlist_sizes": [30, 10, 3],
        },
    ),
    AwardDefinition(
        code="BREAKOUT_STAR",
        name="GTEX Breakout Regen",
        description="Most improved regen compared with the previous GTEX season or, for debut seasons, a controlled baseline.",
        category="individual",
        ranking_category="overall",
        eligibility_rules={"min_appearances": 8, "requires_improvement": True},
        sort_order=70,
        metadata={
            "equivalent_name": "Breakout Star",
            "market_award_code": "gtex_breakout_star",
            "shortlist_sizes": [30, 10, 3],
        },
    ),
    AwardDefinition(
        code="TEAM_OF_THE_YEAR",
        name="GTEX Team of the Year",
        description="Best regen XI selected by a deterministic 4-3-3 from position-based prestige rankings.",
        category="team_selection",
        ranking_category=None,
        eligibility_rules={"formation": {"goalkeeper": 1, "defender": 4, "midfielder": 3, "forward": 3}},
        sort_order=80,
        metadata={
            "equivalent_name": "Team of the Year",
            "market_award_code": "gtex_team_of_the_year",
            "shortlist_sizes": [30, 10, 3],
        },
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
            if definition.code == "BALLON_DOR":
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
            elif definition.code == "U17_WORLD_CUP_GOLDEN_BALL":
                winner = self._select_best(
                    definition,
                    candidates=self._eligible(performances, definition.eligibility_rules),
                    score_getter=lambda item: item.overall_score,
                )
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "U20_WORLD_CUP_GOLDEN_BALL":
                winner = self._select_best(
                    definition,
                    candidates=self._eligible(performances, definition.eligibility_rules),
                    score_getter=lambda item: item.overall_score,
                )
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "AFCON_PLAYER_OF_THE_TOURNAMENT":
                winner = self._select_best(
                    definition,
                    candidates=self._eligible(performances, definition.eligibility_rules),
                    score_getter=lambda item: item.overall_score,
                )
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "GOLDEN_BOOT":
                winner = self._select_best(
                    definition,
                    candidates=self._eligible(performances, definition.eligibility_rules),
                    score_getter=lambda item: item.scorer_score,
                )
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "BEST_MIDFIELDER":
                winner = self._select_best(
                    definition,
                    candidates=self._eligible(performances, definition.eligibility_rules),
                    score_getter=lambda item: item.midfielder_score,
                )
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "BEST_DEFENDER":
                winner = self._from_ranking(definition, rankings.get("defender", []), records_by_player)
                if winner is not None:
                    selections.append(winner)
            elif definition.code == "BEST_GOALKEEPER":
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
        source_types = {str(value) for value in rules.get("source_types", [])}
        competition_scope = str(rules.get("competition_scope") or "").strip().lower()
        competition_families = {str(value).strip().lower() for value in rules.get("competition_families", [])}
        age_bands = {str(value).strip().lower() for value in rules.get("age_bands", [])}
        return [
            item
            for item in performances
            if item.appearances >= min_appearances
            and (max_age is None or (item.age is not None and item.age <= max_age))
            and (not position_groups or item.position_group in position_groups)
            and (not source_types or str(item.metadata.get("source_type") or "").strip().lower() in source_types)
            and (
                not competition_scope
                or str(item.metadata.get("competition_scope") or "").strip().lower() == competition_scope
            )
            and (
                not competition_families
                or str(item.metadata.get("competition_family") or "").strip().lower() in competition_families
            )
            and (not age_bands or str(item.metadata.get("national_age_band") or "").strip().lower() in age_bands)
        ]


__all__ = ["AwardDefinition", "AwardSelection", "AwardsEngine", "DEFAULT_AWARD_DEFINITIONS"]
