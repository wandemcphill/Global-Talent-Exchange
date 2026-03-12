from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.club_identity.models.reputation import ClubReputationProfile, ReputationEventType
from backend.app.club_identity.reputation.schemas import ContinentalStage, SeasonReputationOutcome, WorldSuperCupStage


@dataclass(frozen=True, slots=True)
class CalculatedReputationEntry:
    event_type: ReputationEventType
    source: str
    delta: int
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)
    milestone: str | None = None
    badge_code: str | None = None


@dataclass(frozen=True, slots=True)
class CalculatedSeasonDelta:
    entries: tuple[CalculatedReputationEntry, ...]
    total_delta: int
    badges: tuple[str, ...]
    milestones: tuple[str, ...]


class ReputationCalculator:
    _league_finish_points = {1: 100, 2: 60, 3: 40, 4: 25}
    _continental_stage_points = {
        ContinentalStage.LEAGUE_PHASE: 10,
        ContinentalStage.ROUND_OF_16: 25,
        ContinentalStage.QUARTER_FINAL: 40,
        ContinentalStage.SEMI_FINAL: 60,
        ContinentalStage.RUNNER_UP: 90,
        ContinentalStage.WINNER: 180,
    }
    _world_super_cup_points = {
        WorldSuperCupStage.QUARTER_FINAL: 50,
        WorldSuperCupStage.SEMI_FINAL: 80,
        WorldSuperCupStage.RUNNER_UP: 130,
        WorldSuperCupStage.WINNER: 250,
    }

    def calculate(
        self,
        outcome: SeasonReputationOutcome,
        profile: ClubReputationProfile | None = None,
    ) -> CalculatedSeasonDelta:
        profile_state = profile or ClubReputationProfile(
            club_id=outcome.club_id,
            total_league_titles=0,
            total_continental_qualifications=0,
            prestige_tier="Local",
        )
        entries: list[CalculatedReputationEntry] = []
        unlocked_badges: list[str] = []
        milestones: list[str] = []

        def add_score(source: str, delta: int, summary: str, **payload: object) -> None:
            if delta <= 0:
                return
            entries.append(
                CalculatedReputationEntry(
                    event_type=ReputationEventType.SCORE_DELTA,
                    source=source,
                    delta=delta,
                    summary=summary,
                    payload=payload,
                )
            )

        def add_badge(title: str, badge_code: str, **payload: object) -> None:
            unlocked_badges.append(badge_code)
            milestones.append(title)
            entries.append(
                CalculatedReputationEntry(
                    event_type=ReputationEventType.MILESTONE_UNLOCKED,
                    source="milestone",
                    delta=0,
                    summary=title,
                    milestone=title,
                    badge_code=badge_code,
                    payload=payload,
                )
            )

        league_points = self._league_finish_points.get(outcome.league_finish or 0, 0)
        add_score(
            "league_finish",
            league_points,
            f"League finish bonus for place {outcome.league_finish}",
            league_finish=outcome.league_finish,
        )

        if outcome.qualified_for_continental:
            add_score("continental_qualification", 30, "Continental qualification secured")
        continental_points = self._continental_stage_points.get(outcome.continental_stage, 0)
        add_score(
            "continental_performance",
            continental_points,
            f"Continental performance reached {outcome.continental_stage.value}",
            continental_stage=outcome.continental_stage.value,
        )

        if outcome.qualified_for_world_super_cup:
            add_score("world_super_cup_qualification", 50, "World Super Cup qualification secured")
        world_super_cup_points = self._world_super_cup_points.get(outcome.world_super_cup_stage, 0)
        add_score(
            "world_super_cup_performance",
            world_super_cup_points,
            f"World Super Cup run reached {outcome.world_super_cup_stage.value}",
            world_super_cup_stage=outcome.world_super_cup_stage.value,
        )

        add_score(
            "other_trophies",
            outcome.other_trophy_wins * 20,
            "Additional trophy haul strengthened club prestige",
            other_trophy_wins=outcome.other_trophy_wins,
        )
        if outcome.consecutive_top_competition_seasons > 1:
            top_competition_bonus = min((outcome.consecutive_top_competition_seasons - 1) * 8, 40)
            add_score(
                "top_competition_consistency",
                top_competition_bonus,
                "Consistency in top competitions strengthened reputation",
                consecutive_top_competition_seasons=outcome.consecutive_top_competition_seasons,
            )

        add_score(
            "top_scorer_awards",
            outcome.top_scorer_awards * 20,
            "Top scorer awards boosted club attacking reputation",
            top_scorer_awards=outcome.top_scorer_awards,
        )
        add_score(
            "top_assist_awards",
            outcome.top_assist_awards * 10,
            "Top assist awards boosted creative reputation",
            top_assist_awards=outcome.top_assist_awards,
        )

        if outcome.undefeated_league_season:
            add_score("undefeated_season", 40, "Undefeated league season achieved")
        if outcome.league_title_streak >= 2:
            add_score(
                "back_to_back_league_titles",
                30,
                "Back-to-back league title bonus awarded",
                league_title_streak=outcome.league_title_streak,
            )
        if outcome.continental_title_streak >= 2:
            add_score(
                "back_to_back_continental_titles",
                50,
                "Consecutive continental title bonus awarded",
                continental_title_streak=outcome.continental_title_streak,
            )

        age_bonus = min(outcome.club_age_years // 25, 4) * 2
        add_score("club_age", age_bonus, "Club age added a small legacy bonus", club_age_years=outcome.club_age_years)

        if outcome.activity_consistency_ratio >= 0.85:
            add_score(
                "activity_consistency",
                10,
                "Strong season-to-season activity consistency maintained",
                activity_consistency_ratio=outcome.activity_consistency_ratio,
            )
        elif outcome.activity_consistency_ratio >= 0.60:
            add_score(
                "activity_consistency",
                5,
                "Club remained consistently active through the season",
                activity_consistency_ratio=outcome.activity_consistency_ratio,
            )

        if outcome.fair_play_bonus:
            add_score("fair_play", 5, "Fair play bonus awarded")

        if outcome.league_finish == 1 and (profile_state.total_league_titles or 0) == 0:
            add_badge("First League Title", "first_league_title", season=outcome.season)
        if outcome.qualified_for_continental and (profile_state.total_continental_qualifications or 0) == 0:
            add_badge("First Continental Qualification", "first_continental_qualification", season=outcome.season)
        if outcome.continental_stage == ContinentalStage.WINNER:
            add_badge("Continental Champion", "continental_champion", season=outcome.season)
        if outcome.world_super_cup_stage == WorldSuperCupStage.WINNER:
            add_badge("World Super Cup Champion", "world_super_cup_champion", season=outcome.season)
        if outcome.league_title_streak >= 2:
            add_badge("Back-to-Back Champion", "back_to_back_champion", season=outcome.season)
        if outcome.undefeated_league_season and outcome.league_finish == 1:
            add_badge("Invincibles", "invincibles", season=outcome.season)
        if outcome.giant_killer:
            add_score("giant_killer", 15, "Giant killer bonus awarded")
            add_badge("Giant Killer", "giant_killer", season=outcome.season)
        if outcome.top_scorer_awards > 0 and outcome.top_assist_awards > 0:
            add_score("golden_attack", 15, "Golden attack bonus awarded")
            add_badge("Golden Attack", "golden_attack", season=outcome.season)

        return CalculatedSeasonDelta(
            entries=tuple(entries),
            total_delta=sum(entry.delta for entry in entries),
            badges=tuple(dict.fromkeys(unlocked_badges)),
            milestones=tuple(dict.fromkeys(milestones)),
        )
