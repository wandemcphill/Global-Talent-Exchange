from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ingestion.models import Competition, InternalLeague, Match, Player, PlayerMatchStat, PlayerSeasonStat, Season as IngestionSeason
from app.models.regen import RegenDiscoveryBadge, RegenLegacyRecord, RegenLineageProfile, RegenProfile, RegenScoutReport
from app.regen_universe.awards_engine import AwardDefinition, AwardsEngine, DEFAULT_AWARD_DEFINITIONS
from app.regen_universe.models import (
    RegenAward,
    RegenAwardWinner,
    RegenHallOfFame,
    RegenPerformanceRecord,
    RegenRankingSnapshot,
    RegenSeason,
)
from app.regen_universe.ranking_engine import PerformanceInput, RankingEngine
from app.services.regen_market_service import RegenMarketService


class RegenUniverseError(ValueError):
    pass


@dataclass(slots=True)
class _AggregateBucket:
    player_id: str
    player_name: str
    age: int | None
    position_group: str
    appearances: int = 0
    starts: int = 0
    minutes_played: int = 0
    goals: int = 0
    assists: int = 0
    clean_sheets: int = 0
    saves: int = 0
    season_rating_total: float = 0.0
    season_rating_weight: int = 0
    match_rating_total: float = 0.0
    match_rating_weight: int = 0
    competition_total: float = 0.0
    competition_weight: int = 0
    matches_won: int = 0
    match_count: int = 0
    rated_match_count: int = 0
    high_rating_matches: int = 0
    full_minutes_matches: int = 0
    start_matches: int = 0
    has_season_stats: bool = False
    source_ingestion_season_ids: set[str] = field(default_factory=set)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _calculate_age(date_of_birth: date | None, as_of: date) -> int | None:
    if date_of_birth is None:
        return None
    age = as_of.year - date_of_birth.year
    if (as_of.month, as_of.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


def _position_group(player: Player) -> str:
    tokens = {
        token.strip().lower()
        for token in (
            player.normalized_position,
            player.position,
        )
        if token
    }
    if any(token in {"gk", "goalkeeper"} for token in tokens):
        return "goalkeeper"
    if any(token in {"cb", "rb", "lb", "rwb", "lwb", "defender", "df", "back"} for token in tokens):
        return "defender"
    if any(token in {"cm", "cdm", "cam", "am", "dm", "midfielder", "mf", "rm", "lm"} for token in tokens):
        return "midfielder"
    if any(token in {"st", "cf", "ss", "fw", "forward", "attacker", "winger", "lw", "rw"} for token in tokens):
        return "forward"
    normalized = (player.normalized_position or "").strip().lower()
    if normalized in {"goalkeeper", "defender", "midfielder", "forward"}:
        return normalized
    return "forward"


def _competition_importance(competition: Competition | None, internal_league: InternalLeague | None) -> float:
    importance = 1.0
    if competition is not None:
        if competition.is_major:
            importance += 0.25
        if competition.competition_strength is not None:
            bounded_strength = max(min(competition.competition_strength, 100.0), 0.0)
            importance += bounded_strength / 200.0
    if internal_league is not None:
        importance += max(0, 6 - internal_league.rank) * 0.04
    return round(importance, 4)


@dataclass(slots=True)
class RegenUniverseService:
    session: Session
    ranking_engine: RankingEngine = field(default_factory=RankingEngine)
    awards_engine: AwardsEngine = field(default_factory=AwardsEngine)

    def seed_defaults(self) -> None:
        existing_codes = {
            code
            for code in self.session.scalars(select(RegenAward.code))
        }
        for definition in DEFAULT_AWARD_DEFINITIONS:
            if definition.code in existing_codes:
                continue
            self.session.add(
                RegenAward(
                    code=definition.code,
                    name=definition.name,
                    description=definition.description,
                    category=definition.category,
                    ranking_category=definition.ranking_category,
                    eligibility_rules_json=dict(definition.eligibility_rules),
                    is_regen_only=True,
                    sort_order=definition.sort_order,
                    metadata_json=dict(definition.metadata),
                )
            )
        active_season = self.session.scalar(
            select(RegenSeason).where(RegenSeason.is_active.is_(True)).order_by(RegenSeason.season_number.desc())
        )
        if active_season is None:
            last_season = self.session.scalar(select(RegenSeason).order_by(RegenSeason.season_number.desc()))
            today = date.today()
            season_number = (last_season.season_number + 1) if last_season is not None else 1
            self.session.add(
                RegenSeason(
                    season_number=season_number,
                    start_date=date(today.year, 1, 1),
                    end_date=date(today.year, 12, 31),
                    is_active=True,
                    metadata_json={"auto_seeded": True},
                )
            )
        self.session.flush()

    def list_seasons(self, *, active_only: bool = False) -> list[RegenSeason]:
        stmt = select(RegenSeason)
        if active_only:
            stmt = stmt.where(RegenSeason.is_active.is_(True))
        stmt = stmt.order_by(RegenSeason.season_number.asc())
        return list(self.session.scalars(stmt))

    def create_season(
        self,
        *,
        season_number: int,
        start_date: date,
        end_date: date,
        source_ingestion_season_ids: list[str] | None = None,
        is_active: bool = True,
    ) -> RegenSeason:
        if end_date < start_date:
            raise RegenUniverseError("regen_universe_invalid_season_window")
        existing = self.session.scalar(select(RegenSeason).where(RegenSeason.season_number == season_number))
        if existing is not None:
            raise RegenUniverseError("regen_universe_season_number_exists")
        if is_active:
            active = self.session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
            if active is not None:
                raise RegenUniverseError("regen_universe_active_season_exists")
        season = RegenSeason(
            season_number=season_number,
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
            metadata_json={"source_ingestion_season_ids": list(source_ingestion_season_ids or [])},
        )
        self.session.add(season)
        self.session.flush()
        return season

    def close_season(
        self,
        season_id: str | None = None,
        *,
        close_date: date | None = None,
        start_next_season: bool = True,
    ) -> dict[str, object]:
        season = self._resolve_season(season_id)
        if season is None:
            raise RegenUniverseError("regen_universe_season_not_found")
        if close_date is not None and close_date < season.start_date:
            raise RegenUniverseError("regen_universe_close_date_before_start")

        computed_performances = self.ranking_engine.score_inputs(self._build_performance_inputs(season))
        rankings = self.ranking_engine.build_rankings(computed_performances)

        self.session.execute(delete(RegenAwardWinner).where(RegenAwardWinner.season_id == season.id))
        self.session.execute(delete(RegenRankingSnapshot).where(RegenRankingSnapshot.season_id == season.id))
        self.session.execute(delete(RegenPerformanceRecord).where(RegenPerformanceRecord.season_id == season.id))

        for performance in computed_performances:
            self.session.add(
                RegenPerformanceRecord(
                    season_id=season.id,
                    player_id=performance.player_id,
                    player_name=performance.player_name,
                    age=performance.age,
                    position_group=performance.position_group,
                    appearances=performance.appearances,
                    starts=performance.starts,
                    minutes_played=performance.minutes_played,
                    goals=performance.goals,
                    assists=performance.assists,
                    clean_sheets=performance.clean_sheets,
                    saves=performance.saves,
                    average_rating=performance.average_rating,
                    matches_won=performance.matches_won,
                    win_ratio=performance.win_ratio,
                    competition_importance=performance.competition_importance,
                    consistency_score=performance.consistency_score,
                    previous_overall_score=performance.previous_overall_score,
                    improvement_score=performance.improvement_score,
                    overall_score=performance.overall_score,
                    forward_score=performance.forward_score,
                    midfielder_score=performance.midfielder_score,
                    defender_score=performance.defender_score,
                    goalkeeper_score=performance.goalkeeper_score,
                    playmaker_score=performance.playmaker_score,
                    scorer_score=performance.scorer_score,
                    metadata_json=dict(performance.metadata),
                )
            )

        ranking_snapshot_count = 0
        for category, ranking in rankings.items():
            for item in ranking:
                ranking_snapshot_count += 1
                self.session.add(
                    RegenRankingSnapshot(
                        season_id=season.id,
                        player_id=item.player_id,
                        player_name=item.player_name,
                        category=item.category,
                        score=item.score,
                        rank=item.rank,
                        metadata_json=dict(item.metadata),
                    )
                )

        award_definitions = self._award_definitions()
        award_lookup = {award.code: award for award in award_definitions}
        award_selections = self.awards_engine.select_winners(
            definitions=[self._definition_from_model(item) for item in award_definitions],
            performances=computed_performances,
            rankings=rankings,
        )
        story_candidate_ids: set[str] = set()
        for selection in award_selections:
            award = award_lookup[selection.award_code]
            if selection.rank is None or selection.rank <= 1:
                story_candidate_ids.add(selection.player_id)
            self.session.add(
                RegenAwardWinner(
                    award_id=award.id,
                    season_id=season.id,
                    player_id=selection.player_id,
                    player_name=selection.player_name,
                    ranking_score=selection.ranking_score,
                    rank=selection.rank,
                    awarded_at=_utcnow(),
                    metadata_json=dict(selection.metadata),
                )
            )

        season.is_active = False
        season.closed_at = _utcnow()
        if close_date is not None:
            season.end_date = close_date
        self.session.flush()
        if story_candidate_ids:
            from app.regen_universe.expansion_service import RegenUniverseExpansionService

            story_service = RegenUniverseExpansionService(self.session)
            for player_id in story_candidate_ids:
                story_service.refresh_story(
                    player_id,
                    trigger="major_trophy_win",
                    notify=False,
                    publish=True,
                )

        next_season_id: str | None = None
        if start_next_season:
            next_season = self._ensure_next_active_season(season)
            next_season_id = next_season.id

        hall_of_fame_count = self._refresh_hall_of_fame()
        self.session.flush()
        return {
            "season_id": season.id,
            "season_number": season.season_number,
            "performance_records_created": len(computed_performances),
            "ranking_snapshots_created": ranking_snapshot_count,
            "award_winners_created": len(award_selections),
            "hall_of_fame_entries_tracked": hall_of_fame_count,
            "next_season_id": next_season_id,
            "source_ingestion_season_ids": list(self._source_ingestion_season_ids(season)),
        }

    def list_awards(self, *, season_id: str | None = None, award_code: str | None = None) -> list[dict[str, object]]:
        season = self._resolve_target_season(season_id)
        if season is None:
            return []
        definitions = self._award_definitions()
        if award_code:
            definitions = [item for item in definitions if item.code == award_code]
        winners = list(
            self.session.scalars(
                select(RegenAwardWinner)
                .where(RegenAwardWinner.season_id == season.id)
                .order_by(RegenAwardWinner.rank.is_(None), RegenAwardWinner.rank.asc(), RegenAwardWinner.ranking_score.desc(), RegenAwardWinner.player_name.asc())
            )
        )
        grouped_winners: dict[str, list[RegenAwardWinner]] = defaultdict(list)
        for winner in winners:
            grouped_winners[winner.award_id].append(winner)
        return [
            {
                "award": self._award_payload(definition),
                "season": self._season_payload(season),
                "winners": [self._award_winner_payload(item) for item in grouped_winners.get(definition.id, [])],
            }
            for definition in definitions
        ]

    def list_rankings(self, *, season_id: str | None = None, category: str = "overall", limit: int = 50) -> dict[str, object]:
        season = self._resolve_target_season(season_id)
        if season is None:
            return {"season": None, "category": category, "entries": []}
        entries = list(
            self.session.scalars(
                select(RegenRankingSnapshot)
                .where(
                    RegenRankingSnapshot.season_id == season.id,
                    RegenRankingSnapshot.category == category,
                )
                .order_by(RegenRankingSnapshot.rank.asc(), RegenRankingSnapshot.player_name.asc())
                .limit(limit)
            )
        )
        return {
            "season": self._season_payload(season),
            "category": category,
            "entries": [self._ranking_payload(item) for item in entries],
        }

    def list_hall_of_fame(self, *, limit: int = 50) -> dict[str, object]:
        entries = list(
            self.session.scalars(
                select(RegenHallOfFame)
                .order_by(
                    RegenHallOfFame.legacy_score.desc(),
                    RegenHallOfFame.total_awards.desc(),
                    RegenHallOfFame.peak_rank.is_(None),
                    RegenHallOfFame.peak_rank.asc(),
                    RegenHallOfFame.player_name.asc(),
                )
                .limit(limit)
            )
        )
        return {"entries": [self._hall_of_fame_payload(item) for item in entries]}

    def get_player_prestige_summary(self, player_id: str) -> dict[str, object] | None:
        hall_of_fame = self.session.scalar(select(RegenHallOfFame).where(RegenHallOfFame.player_id == player_id))
        latest_ranking = self.session.execute(
            select(RegenRankingSnapshot, RegenSeason)
            .join(RegenSeason, RegenSeason.id == RegenRankingSnapshot.season_id)
            .where(
                RegenRankingSnapshot.player_id == player_id,
                RegenRankingSnapshot.category == "overall",
            )
            .order_by(RegenSeason.season_number.desc(), RegenRankingSnapshot.rank.asc())
        ).first()
        active_ranking = self.session.execute(
            select(RegenRankingSnapshot, RegenSeason)
            .join(RegenSeason, RegenSeason.id == RegenRankingSnapshot.season_id)
            .where(
                RegenRankingSnapshot.player_id == player_id,
                RegenRankingSnapshot.category == "overall",
                RegenSeason.is_active.is_(True),
            )
            .order_by(RegenSeason.season_number.desc(), RegenRankingSnapshot.rank.asc())
        ).first()
        recent_awards = self.session.execute(
            select(RegenAwardWinner, RegenAward, RegenSeason)
            .join(RegenAward, RegenAward.id == RegenAwardWinner.award_id)
            .join(RegenSeason, RegenSeason.id == RegenAwardWinner.season_id)
            .where(RegenAwardWinner.player_id == player_id)
            .order_by(RegenSeason.season_number.desc(), RegenAward.sort_order.asc(), RegenAwardWinner.rank.is_(None), RegenAwardWinner.rank.asc())
        ).all()
        if hall_of_fame is None and latest_ranking is None and not recent_awards:
            return None
        awards_payload = [
            {
                "award_code": award.code,
                "award_name": award.name,
                "season_number": season.season_number,
                "rank": winner.rank,
                "ranking_score": winner.ranking_score,
            }
            for winner, award, season in recent_awards[:5]
        ]
        latest_ranking_payload = None
        if latest_ranking is not None:
            ranking, ranking_season = latest_ranking
            latest_ranking_payload = {
                "season_number": ranking_season.season_number,
                "rank": ranking.rank,
                "score": ranking.score,
            }
        active_ranking_payload = None
        if active_ranking is not None:
            ranking, ranking_season = active_ranking
            active_ranking_payload = {
                "season_number": ranking_season.season_number,
                "rank": ranking.rank,
                "score": ranking.score,
            }
        return {
            "player_id": player_id,
            "total_awards": hall_of_fame.total_awards if hall_of_fame is not None else len(recent_awards),
            "peak_rank": hall_of_fame.peak_rank if hall_of_fame is not None else (latest_ranking[0].rank if latest_ranking else None),
            "seasons_active": hall_of_fame.seasons_active if hall_of_fame is not None else 0,
            "legacy_score": hall_of_fame.legacy_score if hall_of_fame is not None else 0.0,
            "current_overall_ranking": active_ranking_payload,
            "latest_overall_ranking": latest_ranking_payload,
            "recent_awards": awards_payload,
        }

    def get_player_showcase(self, player_id: str) -> dict[str, object] | None:
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player_id))
        if regen is None:
            return None

        market_service = RegenMarketService(self.session)
        profile = market_service.get_profile_view(regen.id)
        latest_value = market_service.get_latest_value_view(regen.id)
        prestige = self.get_player_prestige_summary(player_id)
        legacy = self.session.scalar(select(RegenLegacyRecord).where(RegenLegacyRecord.regen_id == regen.id))
        discovery_badges = [
            badge.badge_name
            for badge in market_service.list_discovery_badges(regen.id)
        ]
        legacy_score = (
            legacy.legacy_score
            if legacy is not None
            else float(prestige["legacy_score"]) if prestige is not None else 0.0
        )
        return {
            "player_id": player_id,
            "profile": profile,
            "card": self._card_payload(
                profile,
                legacy_score=legacy_score,
                discovery_badges=discovery_badges,
            ),
            "prestige": prestige,
            "legacy": self._legacy_payload(legacy, profile),
            "latest_value": latest_value,
            "discovery_badges": discovery_badges,
        }

    def list_rising_stars(self, *, limit: int = 20, age_max: int = 21) -> dict[str, object]:
        candidates: list[tuple[float, dict[str, object]]] = []
        market_service = RegenMarketService(self.session)
        for regen in self.session.scalars(select(RegenProfile).order_by(RegenProfile.generated_at.desc())):
            profile = market_service.get_profile_view(regen.id)
            if profile.age > age_max or profile.status == "retired":
                continue
            latest_value = market_service.get_latest_value_view(regen.id)
            prestige = self.get_player_prestige_summary(profile.player_id) if profile.player_id is not None else None
            legacy_score = float(prestige["legacy_score"]) if prestige is not None else 0.0
            entry = {
                "player_id": profile.player_id,
                "profile": profile,
                "card": self._card_payload(
                    profile,
                    legacy_score=legacy_score,
                    discovery_badges=[badge.badge_name for badge in market_service.list_discovery_badges(regen.id)],
                ),
                "legacy_score": legacy_score,
                "market_value_coin": latest_value.current_value_coin,
                "momentum_label": self._rising_star_momentum_label(profile),
            }
            score = (
                (profile.potential or profile.current_rating or 0) * 1.6
                + (profile.uniqueness_score * 100.0)
                + (legacy_score * 0.25)
                + ((profile.current_rating or 0) * 0.5)
            )
            candidates.append((score, entry))

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1]["profile"].potential or 0,
                item[1]["profile"].uniqueness_score,
                item[1]["profile"].generated_at,
            ),
            reverse=True,
        )
        return {"entries": [entry for _, entry in candidates[:limit]]}

    def list_bloodlines(self, *, limit: int = 20) -> dict[str, object]:
        market_service = RegenMarketService(self.session)
        lineage_rows = list(
            self.session.scalars(
                select(RegenLineageProfile).order_by(RegenLineageProfile.created_at.asc(), RegenLineageProfile.id.asc())
            )
        )
        grouped: dict[str, list[RegenLineageProfile]] = defaultdict(list)
        for lineage in lineage_rows:
            grouped[f"{lineage.related_legend_type}:{lineage.related_legend_ref_id}"].append(lineage)

        chains: list[dict[str, object]] = []
        for key, rows in grouped.items():
            entries: list[dict[str, object]] = []
            for index, lineage in enumerate(
                sorted(
                    rows,
                    key=lambda item: (
                        (self.session.get(RegenProfile, item.regen_id).generated_at if self.session.get(RegenProfile, item.regen_id) is not None else _utcnow()),
                        item.created_at,
                    ),
                ),
                start=1,
            ):
                regen = self.session.get(RegenProfile, lineage.regen_id)
                if regen is None:
                    continue
                profile = market_service.get_profile_view(regen.id)
                prestige = self.get_player_prestige_summary(profile.player_id) if profile.player_id is not None else None
                entries.append(
                    {
                        "player_id": profile.player_id,
                        "regen_id": profile.regen_id,
                        "display_name": profile.display_name,
                        "regen_type": profile.regen_type,
                        "generation_index": index,
                        "primary_position": profile.primary_position,
                        "current_rating": profile.current_rating or profile.current_gsi,
                        "potential": profile.potential or profile.current_gsi,
                        "uniqueness_score": profile.uniqueness_score,
                        "legacy_score": float(prestige["legacy_score"]) if prestige is not None else 0.0,
                        "story_snippet": profile.story_seed.snippet if profile.story_seed is not None else None,
                    }
                )
            if not entries:
                continue
            baseline = entries[0]["uniqueness_score"]
            drift_score = round(
                0.0
                if len(entries) == 1
                else sum(abs(entry["uniqueness_score"] - baseline) for entry in entries[1:]) / (len(entries) - 1),
                4,
            )
            first = rows[0]
            chains.append(
                {
                    "bloodline_key": key,
                    "origin_label": first.narrative_text or first.related_legend_ref_id,
                    "origin_ref_id": first.related_legend_ref_id,
                    "origin_type": first.related_legend_type,
                    "drift_score": drift_score,
                    "entries": entries,
                }
            )

        chains.sort(
            key=lambda item: (
                len(item["entries"]),
                max((entry["uniqueness_score"] for entry in item["entries"]), default=0.0),
                item["drift_score"],
            ),
            reverse=True,
        )
        return {"entries": chains[:limit]}

    def list_scouting_feed(self, *, limit: int = 20) -> dict[str, object]:
        market_service = RegenMarketService(self.session)
        items: list[dict[str, object]] = []
        regens = list(
            self.session.scalars(
                select(RegenProfile).order_by(RegenProfile.generated_at.desc())
            )
        )
        for regen in regens[: max(limit, 10)]:
            profile = market_service.get_profile_view(regen.id)
            items.append(
                {
                    "feed_id": f"new:{regen.id}",
                    "feed_type": "new_regen_discovered",
                    "player_id": profile.player_id,
                    "regen_id": profile.regen_id,
                    "title": f"{profile.display_name} enters the universe",
                    "summary": profile.story_seed.snippet if profile.story_seed is not None else "Freshly generated prospect added to the pool.",
                    "occurred_at": profile.generated_at,
                    "importance": round(0.45 + (profile.uniqueness_score * 0.55), 4),
                    "badges": [profile.regen_type],
                }
            )
            if profile.age <= 21 and (profile.potential or 0) >= 86 and (profile.current_rating or 0) >= 68:
                items.append(
                    {
                        "feed_id": f"breakout:{regen.id}",
                        "feed_type": "breakout_player",
                        "player_id": profile.player_id,
                        "regen_id": profile.regen_id,
                        "title": f"{profile.display_name} is trending as a breakout",
                        "summary": "High current level and elite ceiling are converging into a fast-rising profile.",
                        "occurred_at": profile.generated_at,
                        "importance": round(0.55 + (((profile.current_rating or 0) + (profile.potential or 0)) / 400.0), 4),
                        "badges": ["breakout", "rising_star"],
                    }
                )
            if profile.uniqueness_score >= 0.75:
                items.append(
                    {
                        "feed_id": f"hidden:{regen.id}",
                        "feed_type": "hidden_gem",
                        "player_id": profile.player_id,
                        "regen_id": profile.regen_id,
                        "title": f"{profile.display_name} grades as a hidden gem",
                        "summary": "Rare trait mix, high narrative value, and unusual upside create a premium scouting signal.",
                        "occurred_at": profile.generated_at,
                        "importance": round(0.5 + (profile.uniqueness_score * 0.5), 4),
                        "badges": ["hidden_gem"],
                    }
                )

        recent_reports = list(
            self.session.scalars(
                select(RegenScoutReport).order_by(RegenScoutReport.created_at.desc(), RegenScoutReport.id.asc())
            )
        )
        for report in recent_reports[: max(limit, 10)]:
            if not report.wonderkid_signal and report.hidden_gem_score < 70:
                continue
            regen = self.session.get(RegenProfile, report.regen_id)
            if regen is None:
                continue
            profile = market_service.get_profile_view(regen.id)
            items.append(
                {
                    "feed_id": f"scout:{report.id}",
                    "feed_type": "hidden_gem",
                    "player_id": profile.player_id,
                    "regen_id": profile.regen_id,
                    "title": f"Scouting alert on {profile.display_name}",
                    "summary": report.summary_text,
                    "occurred_at": report.created_at,
                    "importance": round(max(report.hidden_gem_score / 100.0, 0.6), 4),
                    "badges": list(report.tags_json),
                }
            )

        items.sort(
            key=lambda item: (
                item["occurred_at"],
                item["importance"],
            ),
            reverse=True,
        )
        return {"items": items[:limit]}

    def _build_performance_inputs(self, season: RegenSeason) -> list[PerformanceInput]:
        players = list(
            self.session.scalars(
                select(Player)
                .join(RegenProfile, RegenProfile.player_id == Player.id)
                .where(Player.is_real_player.is_(False))
                .order_by(Player.full_name.asc(), Player.id.asc())
            )
        )
        source_season_ids = self._source_ingestion_season_ids(season)
        previous_season = self.session.scalar(
            select(RegenSeason)
            .where(RegenSeason.season_number < season.season_number)
            .order_by(RegenSeason.season_number.desc())
        )
        previous_scores = {}
        if previous_season is not None:
            previous_scores = {
                record.player_id: record.overall_score
                for record in self.session.scalars(
                    select(RegenPerformanceRecord).where(RegenPerformanceRecord.season_id == previous_season.id)
                )
            }
        buckets = {
            player.id: _AggregateBucket(
                player_id=player.id,
                player_name=player.full_name,
                age=_calculate_age(player.date_of_birth, season.end_date),
                position_group=_position_group(player),
            )
            for player in players
        }

        season_stats_stmt = (
            select(PlayerSeasonStat, Competition, InternalLeague)
            .join(Player, Player.id == PlayerSeasonStat.player_id)
            .join(RegenProfile, RegenProfile.player_id == Player.id)
            .outerjoin(Competition, Competition.id == PlayerSeasonStat.competition_id)
            .outerjoin(InternalLeague, InternalLeague.id == Competition.internal_league_id)
            .where(Player.is_real_player.is_(False))
        )
        if source_season_ids:
            season_stats_stmt = season_stats_stmt.where(PlayerSeasonStat.season_id.in_(source_season_ids))
        for stat, competition, internal_league in self.session.execute(season_stats_stmt):
            bucket = buckets.get(stat.player_id)
            if bucket is None:
                continue
            bucket.has_season_stats = True
            bucket.appearances += max(stat.appearances or 0, 0)
            bucket.starts += max(stat.starts or 0, 0)
            bucket.minutes_played += max(stat.minutes or 0, 0)
            bucket.goals += max(stat.goals or 0, 0)
            bucket.assists += max(stat.assists or 0, 0)
            bucket.clean_sheets += max(stat.clean_sheets or 0, 0)
            bucket.saves += max(stat.saves or 0, 0)
            weight = max(stat.minutes or 0, stat.appearances or 0, 1)
            if stat.average_rating is not None:
                bucket.season_rating_total += stat.average_rating * weight
                bucket.season_rating_weight += weight
            importance = _competition_importance(competition, internal_league)
            bucket.competition_total += importance * weight
            bucket.competition_weight += weight
            if stat.season_id:
                bucket.source_ingestion_season_ids.add(stat.season_id)

        match_stats_stmt = (
            select(PlayerMatchStat, Match, Competition, InternalLeague)
            .join(Player, Player.id == PlayerMatchStat.player_id)
            .join(RegenProfile, RegenProfile.player_id == Player.id)
            .join(Match, Match.id == PlayerMatchStat.match_id)
            .outerjoin(Competition, Competition.id == Match.competition_id)
            .outerjoin(InternalLeague, InternalLeague.id == Competition.internal_league_id)
            .where(Player.is_real_player.is_(False))
        )
        if source_season_ids:
            match_stats_stmt = match_stats_stmt.where(
                (PlayerMatchStat.season_id.in_(source_season_ids)) | (Match.season_id.in_(source_season_ids))
            )
        else:
            window_end = datetime.combine(season.end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
            window_start = datetime.combine(season.start_date, datetime.min.time(), tzinfo=timezone.utc)
            match_stats_stmt = match_stats_stmt.where(
                Match.kickoff_at.is_not(None),
                Match.kickoff_at >= window_start,
                Match.kickoff_at < window_end,
            )
        for stat, match, competition, internal_league in self.session.execute(match_stats_stmt):
            bucket = buckets.get(stat.player_id)
            if bucket is None:
                continue
            bucket.match_count += 1
            bucket.start_matches += 1 if (stat.starts or 0) > 0 else 0
            bucket.full_minutes_matches += 1 if (stat.minutes or 0) >= 75 else 0
            if stat.rating is not None:
                bucket.match_rating_total += stat.rating
                bucket.match_rating_weight += 1
                bucket.rated_match_count += 1
                bucket.high_rating_matches += 1 if stat.rating >= 7.0 else 0
            if match.winner_club_id is not None and stat.club_id == match.winner_club_id:
                bucket.matches_won += 1
            if not bucket.has_season_stats:
                bucket.appearances += max(stat.appearances or 1, 0)
                bucket.starts += max(stat.starts or 0, 0)
                bucket.minutes_played += max(stat.minutes or 0, 0)
                bucket.goals += max(stat.goals or 0, 0)
                bucket.assists += max(stat.assists or 0, 0)
                bucket.clean_sheets += 1 if stat.clean_sheet else 0
                bucket.saves += max(stat.saves or 0, 0)
                if stat.rating is not None:
                    bucket.season_rating_total += stat.rating
                    bucket.season_rating_weight += 1
                importance = _competition_importance(competition, internal_league)
                weight = max(stat.minutes or 0, stat.appearances or 0, 1)
                bucket.competition_total += importance * weight
                bucket.competition_weight += weight
            if stat.season_id:
                bucket.source_ingestion_season_ids.add(stat.season_id)

        inputs: list[PerformanceInput] = []
        for player in players:
            bucket = buckets[player.id]
            if bucket.appearances <= 0 and bucket.minutes_played <= 0 and bucket.goals <= 0 and bucket.assists <= 0:
                continue
            if bucket.season_rating_weight > 0:
                average_rating = round(bucket.season_rating_total / bucket.season_rating_weight, 4)
            elif bucket.match_rating_weight > 0:
                average_rating = round(bucket.match_rating_total / bucket.match_rating_weight, 4)
            else:
                average_rating = None
            if bucket.competition_weight > 0:
                competition_importance = round(bucket.competition_total / bucket.competition_weight, 4)
            else:
                competition_importance = 1.0
            consistency_score = self._consistency_score(bucket=bucket, average_rating=average_rating)
            inputs.append(
                PerformanceInput(
                    player_id=player.id,
                    player_name=player.full_name,
                    age=bucket.age,
                    position_group=bucket.position_group,
                    appearances=bucket.appearances,
                    starts=bucket.starts,
                    minutes_played=bucket.minutes_played,
                    goals=bucket.goals,
                    assists=bucket.assists,
                    clean_sheets=bucket.clean_sheets,
                    saves=bucket.saves,
                    average_rating=average_rating,
                    matches_won=bucket.matches_won,
                    competition_importance=competition_importance,
                    consistency_score=consistency_score,
                    previous_overall_score=previous_scores.get(player.id),
                    metadata={
                        "source_ingestion_season_ids": sorted(bucket.source_ingestion_season_ids),
                        "match_count": bucket.match_count,
                    },
                )
            )
        return inputs

    def _consistency_score(self, *, bucket: _AggregateBucket, average_rating: float | None) -> float:
        if bucket.match_count > 0:
            high_rating_ratio = bucket.high_rating_matches / max(bucket.rated_match_count, 1) if bucket.rated_match_count > 0 else 0.0
            full_minutes_ratio = bucket.full_minutes_matches / bucket.match_count
            start_ratio = bucket.start_matches / bucket.match_count
            return round(min((high_rating_ratio * 0.5) + (full_minutes_ratio * 0.25) + (start_ratio * 0.25), 1.0), 4)
        normalized_rating = 0.0
        if average_rating is not None:
            normalized_rating = max(min((average_rating - 6.0) / 2.0, 1.0), 0.0)
        start_ratio = bucket.starts / max(bucket.appearances, 1) if bucket.appearances > 0 else 0.0
        return round(min((normalized_rating * 0.6) + (start_ratio * 0.4), 1.0), 4)

    def _refresh_hall_of_fame(self) -> int:
        profiles = list(
            self.session.scalars(
                select(Player).join(RegenProfile, RegenProfile.player_id == Player.id).where(Player.is_real_player.is_(False))
            )
        )
        overall_rankings = defaultdict(list)
        for ranking in self.session.scalars(select(RegenRankingSnapshot).where(RegenRankingSnapshot.category == "overall")):
            overall_rankings[ranking.player_id].append(ranking)
        performance_records = defaultdict(list)
        for record in self.session.scalars(select(RegenPerformanceRecord)):
            performance_records[record.player_id].append(record)
        award_winners = defaultdict(list)
        for winner in self.session.scalars(select(RegenAwardWinner)):
            award_winners[winner.player_id].append(winner)

        for player in profiles:
            peak_rank = min((item.rank for item in overall_rankings.get(player.id, [])), default=None)
            seasons_active = len({record.season_id for record in performance_records.get(player.id, [])})
            total_awards = len(award_winners.get(player.id, []))
            cumulative_score = sum(record.overall_score for record in performance_records.get(player.id, []))
            top_five_bonus = sum(4.0 for item in overall_rankings.get(player.id, []) if item.rank <= 5)
            rank_bonus = max(0.0, 25.0 - float(peak_rank or 25))
            legacy_score = round((cumulative_score * 0.35) + (total_awards * 12.0) + (seasons_active * 3.0) + top_five_bonus + rank_bonus, 4)
            entry = self.session.scalar(select(RegenHallOfFame).where(RegenHallOfFame.player_id == player.id))
            if entry is None:
                entry = RegenHallOfFame(player_id=player.id, player_name=player.full_name)
                self.session.add(entry)
            entry.player_name = player.full_name
            entry.total_awards = total_awards
            entry.peak_rank = peak_rank
            entry.seasons_active = seasons_active
            entry.legacy_score = legacy_score
            entry.metadata_json = {
                "cumulative_overall_score": round(cumulative_score, 4),
                "top_five_finishes": sum(1 for item in overall_rankings.get(player.id, []) if item.rank <= 5),
                "latest_award_count": total_awards,
            }
        return len(profiles)

    def _ensure_next_active_season(self, season: RegenSeason) -> RegenSeason:
        active = self.session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)).order_by(RegenSeason.season_number.desc()))
        if active is not None:
            return active
        duration = season.end_date - season.start_date
        next_start = season.end_date + timedelta(days=1)
        next_end = next_start + duration
        next_season = RegenSeason(
            season_number=season.season_number + 1,
            start_date=next_start,
            end_date=next_end,
            is_active=True,
            metadata_json={},
        )
        self.session.add(next_season)
        self.session.flush()
        return next_season

    def _award_definitions(self) -> list[RegenAward]:
        return list(self.session.scalars(select(RegenAward).order_by(RegenAward.sort_order.asc(), RegenAward.code.asc())))

    def _definition_from_model(self, award: RegenAward) -> AwardDefinition:
        return AwardDefinition(
            code=award.code,
            name=award.name,
            description=award.description,
            category=award.category,
            ranking_category=award.ranking_category,
            eligibility_rules=dict(award.eligibility_rules_json),
            sort_order=award.sort_order,
            metadata=dict(award.metadata_json),
        )

    def _source_ingestion_season_ids(self, season: RegenSeason) -> tuple[str, ...]:
        metadata = season.metadata_json if isinstance(season.metadata_json, dict) else {}
        configured_ids = metadata.get("source_ingestion_season_ids")
        if isinstance(configured_ids, list):
            cleaned = tuple(str(item) for item in configured_ids if item)
            if cleaned:
                return cleaned
        overlapping = list(
            self.session.scalars(
                select(IngestionSeason.id).where(
                    IngestionSeason.start_date.is_not(None),
                    IngestionSeason.end_date.is_not(None),
                    IngestionSeason.start_date <= season.end_date,
                    IngestionSeason.end_date >= season.start_date,
                )
            )
        )
        if overlapping:
            return tuple(overlapping)
        if season.is_active:
            current_ids = list(self.session.scalars(select(IngestionSeason.id).where(IngestionSeason.is_current.is_(True))))
            if current_ids:
                return tuple(current_ids)
        return ()

    def _resolve_target_season(self, season_id: str | None) -> RegenSeason | None:
        season = self._resolve_season(season_id)
        if season is not None:
            return season
        return self.session.scalar(
            select(RegenSeason).order_by(RegenSeason.is_active.desc(), RegenSeason.season_number.desc())
        )

    def _resolve_season(self, season_id: str | None) -> RegenSeason | None:
        if season_id is not None:
            return self.session.get(RegenSeason, season_id)
        return self.session.scalar(
            select(RegenSeason).where(RegenSeason.is_active.is_(True)).order_by(RegenSeason.season_number.desc())
        )

    def _season_payload(self, season: RegenSeason) -> dict[str, object]:
        metadata = season.metadata_json if isinstance(season.metadata_json, dict) else {}
        return {
            "id": season.id,
            "season_number": season.season_number,
            "start_date": season.start_date,
            "end_date": season.end_date,
            "is_active": season.is_active,
            "closed_at": season.closed_at,
            "source_ingestion_season_ids": list(metadata.get("source_ingestion_season_ids", [])),
        }

    def _award_payload(self, award: RegenAward) -> dict[str, object]:
        return {
            "id": award.id,
            "code": award.code,
            "name": award.name,
            "description": award.description,
            "category": award.category,
            "ranking_category": award.ranking_category,
            "eligibility_rules_json": dict(award.eligibility_rules_json),
            "is_regen_only": award.is_regen_only,
        }

    def _award_winner_payload(self, winner: RegenAwardWinner) -> dict[str, object]:
        return {
            "id": winner.id,
            "player_id": winner.player_id,
            "player_name": winner.player_name,
            "ranking_score": winner.ranking_score,
            "rank": winner.rank,
            "awarded_at": winner.awarded_at,
            "metadata_json": dict(winner.metadata_json),
        }

    def _ranking_payload(self, ranking: RegenRankingSnapshot) -> dict[str, object]:
        return {
            "id": ranking.id,
            "player_id": ranking.player_id,
            "player_name": ranking.player_name,
            "category": ranking.category,
            "score": ranking.score,
            "rank": ranking.rank,
            "metadata_json": dict(ranking.metadata_json),
        }

    def _hall_of_fame_payload(self, entry: RegenHallOfFame) -> dict[str, object]:
        return {
            "id": entry.id,
            "player_id": entry.player_id,
            "player_name": entry.player_name,
            "total_awards": entry.total_awards,
            "peak_rank": entry.peak_rank,
            "seasons_active": entry.seasons_active,
            "legacy_score": entry.legacy_score,
            "metadata_json": dict(entry.metadata_json),
        }

    def _legacy_payload(self, legacy: RegenLegacyRecord | None, profile) -> dict[str, object] | None:
        if legacy is None:
            return None
        metadata = dict(legacy.metadata_json or {})
        return {
            "regen_id": legacy.regen_id,
            "player_id": legacy.player_id,
            "total_matches": legacy.appearances_total,
            "goals": legacy.goals_total,
            "assists": legacy.assists_total,
            "trophies": int(metadata.get("trophies", 0)),
            "peak_rating": profile.current_rating or profile.current_gsi,
            "seasons_total": legacy.seasons_total,
            "awards_total": legacy.awards_total,
            "legacy_score": legacy.legacy_score,
            "legacy_tier": legacy.legacy_tier,
            "is_legend": legacy.is_legend,
            "narrative_summary": legacy.narrative_summary,
            "career_path": list(metadata.get("career_path", [])),
        }

    def _card_payload(
        self,
        profile,
        *,
        legacy_score: float,
        discovery_badges: list[str],
    ) -> dict[str, object]:
        metadata = dict(profile.metadata or {})
        visual_profile = metadata.get("visual_profile") if isinstance(metadata.get("visual_profile"), dict) else {}
        badges: list[dict[str, object]] = []
        if profile.regen_type == "legend_regen":
            badges.append({"code": "bloodline", "label": "Bloodline", "emphasis": "premium"})
        if profile.age <= 21 and (profile.current_rating or 0) >= 70:
            badges.append({"code": "breakout", "label": "Breakout", "emphasis": "hot"})
        if (profile.potential or 0) >= 90:
            badges.append({"code": "elite_potential", "label": "Elite Potential", "emphasis": "premium"})
        if profile.personality.professionalism >= 75 and profile.personality.adaptability >= 70:
            badges.append({"code": "tactical_genius", "label": "Tactical Genius", "emphasis": "sharp"})
        for badge_name in discovery_badges[:2]:
            badges.append({"code": badge_name.lower().replace(" ", "_"), "label": badge_name, "emphasis": "earned"})

        uniqueness_badge = "standard"
        if profile.uniqueness_score >= 0.85:
            uniqueness_badge = "mythic"
        elif profile.uniqueness_score >= 0.72:
            uniqueness_badge = "rare"
        elif profile.uniqueness_score >= 0.58:
            uniqueness_badge = "distinct"

        personality_tags = tuple(profile.personality.personality_tags)
        trait_source = personality_tags[:3]
        if not trait_source and profile.story_seed is not None:
            trait_source = (profile.story_seed.temperament,)
        traits_icons = tuple(
            tag.lower().replace(" ", "_")
            for tag in trait_source
            if tag
        )
        return {
            "name": profile.display_name,
            "face_seed": visual_profile.get("portrait_seed"),
            "position": profile.primary_position,
            "rating": profile.current_rating or profile.current_gsi,
            "potential": profile.potential or profile.current_gsi,
            "regen_type_badge": "Legend Echo" if profile.regen_type == "legend_regen" else "Organic NewGen",
            "uniqueness_badge": uniqueness_badge,
            "legacy_score": legacy_score,
            "traits_icons": traits_icons,
            "personality_tag": personality_tags[0] if personality_tags else (profile.story_seed.temperament if profile.story_seed is not None else None),
            "story_snippet": profile.story_seed.snippet if profile.story_seed is not None else None,
            "badges": badges,
        }

    def _rising_star_momentum_label(self, profile) -> str:
        if (profile.potential or 0) >= 92 and profile.uniqueness_score >= 0.75:
            return "Wonderkid surge"
        if (profile.current_rating or 0) >= 72:
            return "Breakout form"
        if profile.regen_type == "legend_regen":
            return "Legacy spotlight"
        return "High-upside prospect"


__all__ = ["RegenUniverseError", "RegenUniverseService"]
