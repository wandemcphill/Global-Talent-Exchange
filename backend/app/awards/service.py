from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Club, Match, TeamStanding
from app.models.manager_marketplace import ManagerProfile
from app.models.national_team import NationalTeamCompetition, NationalTeamEntry
from app.models.user import User
from app.regen_universe.models import RegenAward, RegenAwardWinner, RegenPerformanceRecord, RegenSeason


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class AwardCategoryDefinition:
    code: str
    name: str
    equivalent_name: str
    category_group: str
    entity_type: str
    shortlist_sizes: tuple[int, ...] = (30, 10, 3)
    source_award_code: str | None = None


@dataclass(frozen=True, slots=True)
class AwardCandidate:
    entity_id: str
    entity_type: str
    display_name: str
    nomination_score: float
    components: dict[str, float]
    metadata: dict[str, Any]


_CATEGORY_DEFINITIONS: tuple[AwardCategoryDefinition, ...] = (
    AwardCategoryDefinition("BALLON_DOR", "GTEX Ballon d'Or", "Ballon d'Or", "individual", "player", source_award_code="BALLON_DOR"),
    AwardCategoryDefinition("GOLDEN_BOY", "GTEX Golden Boy", "Golden Boy", "individual", "player", source_award_code="GOLDEN_BOY"),
    AwardCategoryDefinition("GOLDEN_BOOT", "GTEX Golden Boot", "Golden Boot", "individual", "player", source_award_code="GOLDEN_BOOT"),
    AwardCategoryDefinition("BEST_MIDFIELDER", "GTEX Best Midfielder", "Best Midfielder", "individual", "player", source_award_code="BEST_MIDFIELDER"),
    AwardCategoryDefinition("BEST_DEFENDER", "GTEX Best Defender", "Best Defender", "individual", "player", source_award_code="BEST_DEFENDER"),
    AwardCategoryDefinition("CLUB_OF_THE_YEAR", "GTEX Club of the Year", "Club of the Year", "team", "club"),
    AwardCategoryDefinition("NATIONAL_TEAM_OF_THE_YEAR", "GTEX National Team of the Year", "National Team of the Year", "team", "national_team"),
    AwardCategoryDefinition("BEST_MANAGER", "GTEX Best Manager", "Best Manager", "manager", "manager"),
    AwardCategoryDefinition("TEAM_OF_THE_YEAR", "GTEX Team of the Year", "Team of the Year", "team_selection", "player", source_award_code="TEAM_OF_THE_YEAR"),
)


class AwardsCultureService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_categories(self) -> list[dict[str, Any]]:
        return [
            {
                "award_code": item.code,
                "award_name": item.name,
                "equivalent_name": item.equivalent_name,
                "category_group": item.category_group,
                "entity_type": item.entity_type,
                "shortlist_sizes": list(item.shortlist_sizes),
                "metadata": {"broadcast_ready": True},
            }
            for item in _CATEGORY_DEFINITIONS
        ]

    def list_nominees(self, *, season_id: str | None = None, award_code: str | None = None) -> list[dict[str, Any]]:
        season = self._resolve_target_season(season_id)
        if season is None:
            return []
        results: list[dict[str, Any]] = []
        for category in self._categories(award_code):
            candidates = self._candidates_for_category(category, season)
            stages = self._shortlist_stages(candidates, category.shortlist_sizes)
            results.append(
                {
                    "award_code": category.code,
                    "award_name": category.name,
                    "equivalent_name": category.equivalent_name,
                    "category_group": category.category_group,
                    "entity_type": category.entity_type,
                    "stages": stages,
                    "validation": {
                        "has_finalists": bool(stages and stages[-1]["nominees"]),
                        "sorted_descending": self._is_descending(candidates),
                    },
                }
            )
        return results

    def list_winners(self, *, season_id: str | None = None, award_code: str | None = None) -> list[dict[str, Any]]:
        season = self._resolve_target_season(season_id)
        if season is None:
            return []
        payload: list[dict[str, Any]] = []
        winners_by_award = self._stored_winners_by_code(season)
        nominees = {item["award_code"]: item for item in self.list_nominees(season_id=season.id, award_code=award_code)}
        for category in self._categories(award_code):
            nominee_bucket = nominees.get(category.code, {})
            finalists = list((nominee_bucket.get("stages") or [{}])[-1].get("nominees") or [])
            winners = winners_by_award.get(category.code)
            if winners is None:
                winners = finalists[:1]
            payload.append(
                {
                    "award_code": category.code,
                    "award_name": category.name,
                    "equivalent_name": category.equivalent_name,
                    "entity_type": category.entity_type,
                    "winners": winners,
                    "finalists": finalists,
                    "metadata": {
                        "season_id": season.id,
                        "season_number": season.season_number,
                        "broadcast_mode": "tv",
                    },
                }
            )
        return payload

    def get_ceremony(self, *, season_id: str | None = None) -> dict[str, Any] | None:
        season = self._resolve_target_season(season_id)
        if season is None:
            return None
        winners = self.list_winners(season_id=season.id)
        segments: list[dict[str, Any]] = []
        presenters = ["Amina Cole", "Marcus Vale", "Jonah Kade"]
        debates: list[str] = []
        bulletins: list[str] = []
        market_reactions: list[str] = []
        consistency = True
        for order, winner_bucket in enumerate(winners, start=1):
            finalists = list(winner_bucket.get("finalists") or [])
            crowned = list(winner_bucket.get("winners") or [])
            if finalists and crowned:
                consistency = consistency and finalists[0]["entity_id"] == crowned[0]["entity_id"]
            winner_name = crowned[0]["display_name"] if crowned else "TBD"
            award_name = str(winner_bucket["award_name"])
            debates.append(f"Pundits split over {award_name}: the final three all had a case before {winner_name} pulled clear.")
            bulletins.append(f"{award_name} goes to {winner_name}, with the shortlist flow closing exactly in ranking order.")
            if crowned and winner_bucket["entity_type"] == "player":
                market_reactions.append(f"{winner_name} sees an immediate demand spike after the {award_name} reveal.")
            segments.append(
                {
                    "order": order,
                    "award_code": winner_bucket["award_code"],
                    "title": award_name,
                    "presenter": presenters[(order - 1) % len(presenters)],
                    "reveal_style": "golden-envelope" if order <= 3 else "studio-light-wall",
                    "narration": f"The room falls silent as {award_name} reaches its final reveal and {winner_name} is crowned.",
                    "highlight_reel": [
                        f"{winner_name} season-defining moments package",
                        f"{award_name} finalist montage",
                    ],
                    "finalists": finalists,
                    "winners": crowned,
                }
            )
        return {
            "season_id": season.id,
            "season_number": season.season_number,
            "title": f"GTEX Awards Night {season.season_number}",
            "broadcast_mode": "tv",
            "countdown_seconds": 120,
            "presenters": presenters,
            "debates": debates,
            "news_bulletins": bulletins,
            "market_reactions": market_reactions,
            "segments": segments,
            "validation": {
                "ranking_consistency": consistency,
                "segments_ready": len(segments),
                "winner_count": sum(len(item.get("winners") or []) for item in winners),
            },
            "generated_at": _utcnow(),
        }

    def _categories(self, award_code: str | None) -> list[AwardCategoryDefinition]:
        items = list(_CATEGORY_DEFINITIONS)
        if award_code is not None:
            items = [item for item in items if item.code == award_code]
        return items

    def _resolve_target_season(self, season_id: str | None) -> RegenSeason | None:
        if season_id is not None:
            return self.session.get(RegenSeason, season_id)
        return self.session.scalar(
            select(RegenSeason).order_by(RegenSeason.is_active.desc(), RegenSeason.season_number.desc())
        )

    def _stored_winners_by_code(self, season: RegenSeason) -> dict[str, list[dict[str, Any]]]:
        awards = {
            award.id: award
            for award in self.session.scalars(select(RegenAward))
        }
        grouped: dict[str, list[dict[str, Any]]] = {}
        for winner in self.session.scalars(
            select(RegenAwardWinner).where(RegenAwardWinner.season_id == season.id).order_by(
                RegenAwardWinner.rank.is_(None),
                RegenAwardWinner.rank.asc(),
                RegenAwardWinner.ranking_score.desc(),
            )
        ).all():
            award = awards.get(winner.award_id)
            if award is None:
                continue
            grouped.setdefault(award.code, []).append(
                {
                    "entity_id": winner.player_id,
                    "entity_type": "player",
                    "display_name": winner.player_name,
                    "rank": winner.rank or 1,
                    "nomination_score": round(winner.ranking_score, 4),
                    "components": {
                        "performance": round(winner.ranking_score, 4),
                        "trophies": 0.0,
                        "consistency": 0.0,
                        "big_match_impact": 0.0,
                        "total": round(winner.ranking_score, 4),
                    },
                    "metadata": dict(winner.metadata_json or {}),
                }
            )
        return grouped

    def _candidates_for_category(self, category: AwardCategoryDefinition, season: RegenSeason) -> list[AwardCandidate]:
        if category.code in {"BALLON_DOR", "GOLDEN_BOY", "GOLDEN_BOOT", "BEST_MIDFIELDER", "BEST_DEFENDER"}:
            return self._player_candidates(category, season)
        if category.code == "TEAM_OF_THE_YEAR":
            return self._team_of_the_year_candidates(season)
        if category.code == "CLUB_OF_THE_YEAR":
            return self._club_candidates(season)
        if category.code == "NATIONAL_TEAM_OF_THE_YEAR":
            return self._national_team_candidates()
        if category.code == "BEST_MANAGER":
            return self._manager_candidates()
        return []

    def _player_candidates(self, category: AwardCategoryDefinition, season: RegenSeason) -> list[AwardCandidate]:
        award = None
        if category.source_award_code is not None:
            award = self.session.scalar(select(RegenAward).where(RegenAward.code == category.source_award_code))
        rules = dict(award.eligibility_rules_json or {}) if award is not None else {}
        score_field = {
            "BALLON_DOR": "overall_score",
            "GOLDEN_BOY": "overall_score",
            "GOLDEN_BOOT": "scorer_score",
            "BEST_MIDFIELDER": "midfielder_score",
            "BEST_DEFENDER": "defender_score",
            "TEAM_OF_THE_YEAR": "overall_score",
        }.get(category.code, "overall_score")
        candidates: list[AwardCandidate] = []
        for record in self.session.scalars(select(RegenPerformanceRecord).where(RegenPerformanceRecord.season_id == season.id)).all():
            if record.appearances < int(rules.get("min_appearances", 0)):
                continue
            if "max_age" in rules and (record.age is None or record.age > int(rules["max_age"])):
                continue
            position_groups = {str(item) for item in rules.get("position_groups", [])}
            if position_groups and record.position_group not in position_groups:
                continue
            performance = float(getattr(record, score_field))
            trophies = float((record.metadata_json or {}).get("trophy_points", 0.0)) * 18.0
            consistency = float(record.consistency_score) * 20.0
            big_match = float((record.metadata_json or {}).get("big_match_impact", 0.0)) * 12.0
            total = round(performance + trophies + consistency + big_match, 4)
            candidates.append(
                AwardCandidate(
                    entity_id=record.player_id,
                    entity_type="player",
                    display_name=record.player_name,
                    nomination_score=total,
                    components={
                        "performance": round(performance, 4),
                        "trophies": round(trophies, 4),
                        "consistency": round(consistency, 4),
                        "big_match_impact": round(big_match, 4),
                        "total": total,
                    },
                    metadata={
                        "age": record.age,
                        "position_group": record.position_group,
                        "season_id": season.id,
                    },
                )
            )
        return self._sort_candidates(candidates)

    def _team_of_the_year_candidates(self, season: RegenSeason) -> list[AwardCandidate]:
        candidates: list[AwardCandidate] = []
        for record in self.session.scalars(select(RegenPerformanceRecord).where(RegenPerformanceRecord.season_id == season.id)).all():
            total = round(float(record.overall_score) + (float(record.consistency_score) * 20.0), 4)
            candidates.append(
                AwardCandidate(
                    entity_id=record.player_id,
                    entity_type="player",
                    display_name=record.player_name,
                    nomination_score=total,
                    components={
                        "performance": round(float(record.overall_score), 4),
                        "trophies": round(float((record.metadata_json or {}).get("trophy_points", 0.0)) * 10.0, 4),
                        "consistency": round(float(record.consistency_score) * 20.0, 4),
                        "big_match_impact": round(float((record.metadata_json or {}).get("big_match_impact", 0.0)) * 8.0, 4),
                        "total": total,
                    },
                    metadata={"position_group": record.position_group},
                )
            )
        return self._sort_candidates(candidates)

    def _club_candidates(self, season: RegenSeason) -> list[AwardCandidate]:
        source_season_ids = self._source_ingestion_season_ids(season)
        club_lookup = {
            club.id: club.name
            for club in self.session.scalars(select(Club)).all()
        }
        aggregates: dict[str, dict[str, float | str]] = {}
        match_stmt = select(Match)
        if source_season_ids:
            match_stmt = match_stmt.where(Match.season_id.in_(source_season_ids))
        for match in self.session.scalars(match_stmt).all():
            for club_id, goals_for, goals_against, won in (
                (match.home_club_id, match.home_score or 0, match.away_score or 0, match.winner_club_id == match.home_club_id),
                (match.away_club_id, match.away_score or 0, match.home_score or 0, match.winner_club_id == match.away_club_id),
            ):
                bucket = aggregates.setdefault(
                    club_id,
                    {
                        "name": club_lookup.get(club_id, club_id),
                        "wins": 0.0,
                        "matches": 0.0,
                        "goal_difference": 0.0,
                        "titles": 0.0,
                        "big_match": 0.0,
                    },
                )
                bucket["matches"] += 1.0
                bucket["goal_difference"] += float(goals_for - goals_against)
                if won:
                    bucket["wins"] += 1.0
                    stage = (match.stage or "").lower()
                    if "final" in stage:
                        bucket["big_match"] += 2.5
                    elif "semi" in stage:
                        bucket["big_match"] += 1.4
        standing_stmt = select(TeamStanding).where(TeamStanding.position == 1, TeamStanding.standing_type == "total")
        if source_season_ids:
            standing_stmt = standing_stmt.where(TeamStanding.season_id.in_(source_season_ids))
        for standing in self.session.scalars(standing_stmt).all():
            bucket = aggregates.setdefault(
                standing.club_id,
                {
                    "name": club_lookup.get(standing.club_id, standing.club_id),
                    "wins": 0.0,
                    "matches": 0.0,
                    "goal_difference": 0.0,
                    "titles": 0.0,
                    "big_match": 0.0,
                },
            )
            bucket["titles"] += 1.0
            bucket["wins"] += standing.won
            bucket["matches"] += max(standing.played, 1)
            bucket["goal_difference"] += standing.goal_difference
        candidates: list[AwardCandidate] = []
        for club_id, bucket in aggregates.items():
            matches = max(float(bucket["matches"]), 1.0)
            win_ratio = float(bucket["wins"]) / matches
            performance = float(bucket["wins"]) * 4.0 + float(bucket["goal_difference"]) * 0.25
            trophies = float(bucket["titles"]) * 40.0
            consistency = win_ratio * 25.0
            big_match = float(bucket["big_match"]) * 8.0
            total = round(performance + trophies + consistency + big_match, 4)
            candidates.append(
                AwardCandidate(
                    entity_id=club_id,
                    entity_type="club",
                    display_name=str(bucket["name"]),
                    nomination_score=total,
                    components={
                        "performance": round(performance, 4),
                        "trophies": round(trophies, 4),
                        "consistency": round(consistency, 4),
                        "big_match_impact": round(big_match, 4),
                        "total": total,
                    },
                    metadata={"matches": matches, "win_ratio": round(win_ratio, 4)},
                )
            )
        return self._sort_candidates(candidates)

    def _manager_candidates(self) -> list[AwardCandidate]:
        candidates: list[AwardCandidate] = []
        rows = self.session.execute(
            select(ManagerProfile, User).join(User, User.id == ManagerProfile.manager_id)
        ).all()
        for profile, user in rows:
            matches_managed = max(profile.matches_managed, 1)
            win_ratio = profile.wins / matches_managed
            performance = (profile.wins * 2.2) + (profile.reputation_score * 0.08)
            trophies = max(profile.reputation_score - 1000, 0) / 25.0
            consistency = win_ratio * 25.0
            big_match = max(profile.wins - profile.current_losing_streak, 0) * 0.7
            total = round(performance + trophies + consistency + big_match, 4)
            candidates.append(
                AwardCandidate(
                    entity_id=profile.id,
                    entity_type="manager",
                    display_name=user.full_name or user.username or profile.id,
                    nomination_score=total,
                    components={
                        "performance": round(performance, 4),
                        "trophies": round(trophies, 4),
                        "consistency": round(consistency, 4),
                        "big_match_impact": round(big_match, 4),
                        "total": total,
                    },
                    metadata={"wins": profile.wins, "matches_managed": profile.matches_managed},
                )
            )
        return self._sort_candidates(candidates)

    def _national_team_candidates(self) -> list[AwardCandidate]:
        candidates: list[AwardCandidate] = []
        rows = self.session.execute(
            select(NationalTeamEntry, NationalTeamCompetition).join(
                NationalTeamCompetition,
                NationalTeamCompetition.id == NationalTeamEntry.competition_id,
            )
        ).all()
        for entry, competition in rows:
            metadata = dict(entry.metadata_json or {})
            wins = float(metadata.get("wins", 0.0))
            trophies_count = float(metadata.get("trophies", 0.0))
            win_ratio = float(metadata.get("win_ratio", 0.0))
            big_matches = float(metadata.get("big_match_impact", metadata.get("knockout_wins", 0.0)))
            performance = float(metadata.get("performance_score", wins * 5.0 + entry.squad_size * 0.1))
            trophies = trophies_count * 40.0
            consistency = (win_ratio or min(wins / max(entry.squad_size, 1), 1.0)) * 25.0
            big_match = big_matches * 12.0
            total = round(performance + trophies + consistency + big_match, 4)
            candidates.append(
                AwardCandidate(
                    entity_id=entry.id,
                    entity_type="national_team",
                    display_name=entry.country_name,
                    nomination_score=total,
                    components={
                        "performance": round(performance, 4),
                        "trophies": round(trophies, 4),
                        "consistency": round(consistency, 4),
                        "big_match_impact": round(big_match, 4),
                        "total": total,
                    },
                    metadata={
                        "country_code": entry.country_code,
                        "competition_title": competition.title,
                    },
                )
            )
        return self._sort_candidates(candidates)

    def _shortlist_stages(self, candidates: list[AwardCandidate], shortlist_sizes: tuple[int, ...]) -> list[dict[str, Any]]:
        labels = {30: "Top 30", 10: "Top 10", 3: "Final 3"}
        stages: list[dict[str, Any]] = []
        for size in shortlist_sizes:
            nominees = [
                self._candidate_payload(candidate, rank=index)
                for index, candidate in enumerate(candidates[:size], start=1)
            ]
            stages.append(
                {
                    "stage": f"top_{size}",
                    "stage_label": labels.get(size, f"Top {size}"),
                    "size": size,
                    "nominees": nominees,
                }
            )
        return stages

    def _candidate_payload(self, candidate: AwardCandidate, *, rank: int) -> dict[str, Any]:
        return {
            "entity_id": candidate.entity_id,
            "entity_type": candidate.entity_type,
            "display_name": candidate.display_name,
            "rank": rank,
            "nomination_score": candidate.nomination_score,
            "components": candidate.components,
            "metadata": dict(candidate.metadata),
        }

    def _sort_candidates(self, candidates: list[AwardCandidate]) -> list[AwardCandidate]:
        return sorted(
            candidates,
            key=lambda item: (
                -item.nomination_score,
                -item.components.get("performance", 0.0),
                item.display_name.casefold(),
                item.entity_id,
            ),
        )

    def _is_descending(self, candidates: list[AwardCandidate]) -> bool:
        return all(
            candidates[index].nomination_score >= candidates[index + 1].nomination_score
            for index in range(len(candidates) - 1)
        )

    def _source_ingestion_season_ids(self, season: RegenSeason) -> tuple[str, ...]:
        metadata = dict(season.metadata_json or {})
        configured_ids = metadata.get("source_ingestion_season_ids")
        if isinstance(configured_ids, list):
            cleaned = [str(item) for item in configured_ids if item]
            if cleaned:
                return tuple(cleaned)
        return ()


__all__ = ["AwardsCultureService"]
