from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from random import Random

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import (
    Competition,
    Country,
    InternalLeague,
    Match,
    Player,
    PlayerMatchStat,
    PlayerSeasonStat,
    Season as IngestionSeason,
    TeamStanding,
)
from app.market.player_eligibility_policy import market_access_payload
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.national_team import NationalTeamCompetition
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.regen_ecosystem import CareerEvent, NationalRegenSeed, RegenBloodlineLink
from app.models.regen import RegenLegacyRecord, RegenLineageProfile, RegenProfile, RegenScoutReport
from app.regen_universe.awards_engine import AwardDefinition, AwardsEngine, DEFAULT_AWARD_DEFINITIONS
from app.regen_universe.models import (
    RegenAward,
    RegenAchievement,
    RegenAwardWinner,
    RegenHallOfFame,
    RegenPerformanceRecord,
    RegenRankingSnapshot,
    RegenSeason,
    RegenStoryEvent,
)
from app.regen_universe.ranking_engine import PerformanceInput, RankingEngine
from app.schemas.regen_core import (
    AbilityRangeView,
    RegenOriginView,
    RegenPersonalityView,
    RegenProfileView,
    RegenStorySeedView,
)
from app.services.regen_market_service import RegenAwardEvent, RegenMarketService


class RegenUniverseError(ValueError):
    pass


_LEGACY_AWARD_CODE_MAP = {
    "WORLD_PLAYER": "BALLON_DOR",
    "TOP_SCORER": "GOLDEN_BOOT",
    "PLAYMAKER": "BEST_MIDFIELDER",
    "DEFENDER": "BEST_DEFENDER",
    "GOALKEEPER": "BEST_GOALKEEPER",
}

_FALLBACK_COUNTRY_PROFILES = (
    {
        "code": "BR",
        "name": "Brazil",
        "weight": 1.6,
        "first_names": ("Joao", "Pedro", "Lucas", "Gabriel", "Vitor"),
        "last_names": ("Silva", "Santos", "Costa", "Oliveira", "Souza"),
    },
    {
        "code": "NG",
        "name": "Nigeria",
        "weight": 1.5,
        "first_names": ("Tunde", "Kelechi", "Musa", "David", "Samuel"),
        "last_names": ("Okafor", "Adebayo", "Iheanacho", "Onyeka", "Nwosu"),
    },
    {
        "code": "AR",
        "name": "Argentina",
        "weight": 1.2,
        "first_names": ("Mateo", "Tomas", "Thiago", "Julian", "Santiago"),
        "last_names": ("Romero", "Fernandez", "Gomez", "Alvarez", "Lopez"),
    },
    {
        "code": "FR",
        "name": "France",
        "weight": 1.1,
        "first_names": ("Theo", "Hugo", "Kylian", "Amine", "Youssouf"),
        "last_names": ("Diallo", "Camara", "Benzema", "Konate", "Dembele"),
    },
    {
        "code": "ES",
        "name": "Spain",
        "weight": 1.0,
        "first_names": ("Pablo", "Mario", "Diego", "Alvaro", "Martin"),
        "last_names": ("Garcia", "Ruiz", "Martin", "Lopez", "Torres"),
    },
    {
        "code": "SN",
        "name": "Senegal",
        "weight": 0.9,
        "first_names": ("Sadio", "Pape", "Moussa", "Idrissa", "Cheikh"),
        "last_names": ("Ndiaye", "Sarr", "Diop", "Faye", "Niane"),
    },
)

_POSITION_ROLLS = (
    ("ST", 1.0),
    ("RW", 0.8),
    ("LW", 0.8),
    ("AM", 0.9),
    ("CM", 1.0),
    ("DM", 0.75),
    ("CB", 0.95),
    ("RB", 0.6),
    ("LB", 0.6),
    ("GK", 0.45),
)


@dataclass(frozen=True, slots=True)
class _UniverseProspect:
    lookup_id: str
    player_id: str | None
    regen_id: str
    name: str
    age: int
    nationality: str
    nationality_code: str | None
    position: str
    potential: int
    current_rating: int
    growth_curve: float
    club_id: str | None
    generated_at: datetime
    source_type: str
    regen_type: str
    uniqueness_score: float
    story_snippet: str | None = None
    discovery_badges: tuple[str, ...] = ()
    market_value_coin: int | None = None
    profile: RegenProfileView | None = None
    card: dict[str, object] | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _UniverseSubject:
    subject_key: str
    player_id: str | None
    national_seed_id: str | None
    regen_profile_id: str | None
    player_name: str
    age: int | None
    position_group: str
    source_type: str
    nationality_code: str | None = None


@dataclass(slots=True)
class _AggregateBucket:
    player_id: str
    player_name: str
    age: int | None
    position_group: str
    player_row_id: str | None = None
    national_seed_id: str | None = None
    regen_profile_id: str | None = None
    source_type: str = "regen"
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
    trophy_points: float = 0.0
    big_match_impact: float = 0.0
    source_ingestion_season_ids: set[str] = field(default_factory=set)
    competition_families: set[str] = field(default_factory=set)
    national_age_bands: set[str] = field(default_factory=set)
    competition_titles: set[str] = field(default_factory=set)
    competition_ids: set[str] = field(default_factory=set)
    won_tournament: bool = False


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _calculate_age(date_of_birth: date | None, as_of: date) -> int | None:
    if date_of_birth is None:
        return None
    age = as_of.year - date_of_birth.year
    if (as_of.month, as_of.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


def _position_group_from_position(position: str | None, normalized_position: str | None = None) -> str:
    tokens = {
        token.strip().lower()
        for token in (
            normalized_position,
            position,
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
    normalized = (normalized_position or "").strip().lower()
    if normalized in {"goalkeeper", "defender", "midfielder", "forward"}:
        return normalized
    return "forward"


def _position_group(player: Player) -> str:
    return _position_group_from_position(player.position, player.normalized_position)


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


def _normalize_position_label(position: str | None) -> str:
    token = (position or "").strip().upper()
    if not token:
        return "CM"
    aliases = {
        "CF": "ST",
        "CAM": "AM",
        "CDM": "DM",
        "RCB": "CB",
        "LCB": "CB",
        "RWB": "RB",
        "LWB": "LB",
    }
    return aliases.get(token, token)


def _position_story_label(position: str | None) -> str:
    mapping = {
        "GK": "goalkeeper",
        "CB": "centre-back",
        "RB": "full-back",
        "LB": "full-back",
        "DM": "holding midfielder",
        "CM": "midfielder",
        "AM": "midfielder",
        "RW": "winger",
        "LW": "winger",
        "ST": "striker",
    }
    return mapping.get(_normalize_position_label(position), "prospect")


def _growth_curve_label(growth_curve: float) -> str:
    if growth_curve >= 0.82:
        return "rocket"
    if growth_curve >= 0.68:
        return "surging"
    if growth_curve >= 0.54:
        return "steady"
    return "raw"


@dataclass(slots=True)
class RegenUniverseService:
    session: Session
    ranking_engine: RankingEngine = field(default_factory=RankingEngine)
    awards_engine: AwardsEngine = field(default_factory=AwardsEngine)

    def seed_defaults(self) -> None:
        existing_awards = {award.code: award for award in self.session.scalars(select(RegenAward))}
        for legacy_code, next_code in _LEGACY_AWARD_CODE_MAP.items():
            legacy = existing_awards.get(legacy_code)
            replacement = existing_awards.get(next_code)
            if legacy is None or replacement is not None:
                continue
            legacy.code = next_code
            existing_awards[next_code] = legacy
            existing_awards.pop(legacy_code, None)
        for definition in DEFAULT_AWARD_DEFINITIONS:
            existing = existing_awards.get(definition.code)
            if existing is not None:
                existing.name = definition.name
                existing.description = definition.description
                existing.category = definition.category
                existing.ranking_category = definition.ranking_category
                existing.eligibility_rules_json = dict(definition.eligibility_rules)
                existing.is_regen_only = True
                existing.sort_order = definition.sort_order
                existing.metadata_json = dict(definition.metadata)
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
                    subject_key=performance.player_id,
                    player_id=self._performance_player_id(performance),
                    national_seed_id=self._performance_national_seed_id(performance),
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
                        subject_key=item.player_id,
                        player_id=self._ranking_player_id(item.player_id),
                        national_seed_id=self._ranking_national_seed_id(item.player_id),
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
        award_real_player_ids = [
            item.player_id for item in award_selections if not self._is_seed_subject(item.player_id)
        ]
        regen_by_player = (
            {
                profile.player_id: profile
                for profile in self.session.scalars(
                    select(RegenProfile).where(RegenProfile.player_id.in_(award_real_player_ids))
                ).all()
            }
            if award_real_player_ids
            else {}
        )
        market_service = RegenMarketService(self.session)
        story_candidate_ids: set[str] = set()
        for selection in award_selections:
            award = award_lookup[selection.award_code]
            if (selection.rank is None or selection.rank <= 1) and not self._is_seed_subject(selection.player_id):
                story_candidate_ids.add(selection.player_id)
            self.session.add(
                RegenAwardWinner(
                    award_id=award.id,
                    season_id=season.id,
                    subject_key=selection.player_id,
                    player_id=self._ranking_player_id(selection.player_id),
                    national_seed_id=self._ranking_national_seed_id(selection.player_id),
                    player_name=selection.player_name,
                    ranking_score=selection.ranking_score,
                    rank=selection.rank,
                    awarded_at=_utcnow(),
                    metadata_json=dict(selection.metadata),
                )
            )
            regen = regen_by_player.get(selection.player_id)
            if regen is not None:
                market_service.record_award(
                    regen.id,
                    RegenAwardEvent(
                        award_code=self._market_award_code(award),
                        award_name=self._market_award_name(award),
                        award_category=award.category,
                        season_label=str(season.season_number),
                        rank=selection.rank,
                        fan_demand_score=(
                            2.0
                            if selection.rank == 1
                            else 1.0 if selection.rank is not None and selection.rank <= 3 else 0.4
                        ),
                        narrative_significance=3.0 if selection.rank == 1 else 1.5,
                    ),
                    club_id=regen.generated_for_club_id,
                )

        season.is_active = False
        season.closed_at = _utcnow()
        if close_date is not None:
            season.end_date = close_date
        self.session.flush()
        from app.regen_universe.expansion_service import RegenUniverseExpansionService

        story_service = RegenUniverseExpansionService(self.session)
        if story_candidate_ids:
            for player_id in story_candidate_ids:
                story_service.refresh_story(
                    player_id,
                    trigger="major_trophy_win",
                    notify=False,
                    publish=True,
                )
        story_service.apply_evolution_cycle(season_id=season.id)

        next_season_id: str | None = None
        if start_next_season:
            next_season = self._ensure_next_active_season(season)
            next_season_id = next_season.id

        hall_of_fame_count = self._refresh_hall_of_fame()
        self._sync_season_story_surfaces(season.id)
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
                .order_by(
                    RegenAwardWinner.rank.is_(None),
                    RegenAwardWinner.rank.asc(),
                    RegenAwardWinner.ranking_score.desc(),
                    RegenAwardWinner.player_name.asc(),
                )
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

    def list_rankings(
        self,
        *,
        season_id: str | None = None,
        category: str = "overall",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
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
                .offset(offset)
                .limit(limit)
            )
        )
        return {
            "season": self._season_payload(season),
            "category": category,
            "entries": [self._ranking_payload(item) for item in entries],
        }

    def list_hall_of_fame(self, *, limit: int = 50, offset: int = 0) -> dict[str, object]:
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
                .offset(offset)
                .limit(limit)
            )
        )
        return {"entries": [self._hall_of_fame_payload(item) for item in entries]}

    def get_player_prestige_summary(self, player_id: str) -> dict[str, object] | None:
        hall_of_fame = None
        if not self._is_seed_subject(player_id):
            hall_of_fame = self.session.scalar(select(RegenHallOfFame).where(RegenHallOfFame.player_id == player_id))
        latest_ranking = self.session.execute(
            select(RegenRankingSnapshot, RegenSeason)
            .join(RegenSeason, RegenSeason.id == RegenRankingSnapshot.season_id)
            .where(
                RegenRankingSnapshot.subject_key == player_id,
                RegenRankingSnapshot.category == "overall",
            )
            .order_by(RegenSeason.season_number.desc(), RegenRankingSnapshot.rank.asc())
        ).first()
        active_ranking = self.session.execute(
            select(RegenRankingSnapshot, RegenSeason)
            .join(RegenSeason, RegenSeason.id == RegenRankingSnapshot.season_id)
            .where(
                RegenRankingSnapshot.subject_key == player_id,
                RegenRankingSnapshot.category == "overall",
                RegenSeason.is_active.is_(True),
            )
            .order_by(RegenSeason.season_number.desc(), RegenRankingSnapshot.rank.asc())
        ).first()
        recent_awards = self.session.execute(
            select(RegenAwardWinner, RegenAward, RegenSeason)
            .join(RegenAward, RegenAward.id == RegenAwardWinner.award_id)
            .join(RegenSeason, RegenSeason.id == RegenAwardWinner.season_id)
            .where(RegenAwardWinner.subject_key == player_id)
            .order_by(
                RegenSeason.season_number.desc(),
                RegenAward.sort_order.asc(),
                RegenAwardWinner.rank.is_(None),
                RegenAwardWinner.rank.asc(),
            )
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
            "peak_rank": (
                hall_of_fame.peak_rank
                if hall_of_fame is not None
                else (latest_ranking[0].rank if latest_ranking else None)
            ),
            "seasons_active": hall_of_fame.seasons_active if hall_of_fame is not None else 0,
            "legacy_score": hall_of_fame.legacy_score if hall_of_fame is not None else 0.0,
            "current_overall_ranking": active_ranking_payload,
            "latest_overall_ranking": latest_ranking_payload,
            "recent_awards": awards_payload,
        }

    def _resolve_country_name(self, country_code: str | None, *, fallback_name: str | None = None) -> str:
        if fallback_name:
            return fallback_name
        normalized = (country_code or "").strip().upper()
        if not normalized:
            return "Unknown"
        country = self.session.scalar(
            select(Country).where(
                or_(
                    Country.alpha2_code == normalized,
                    Country.alpha3_code == normalized,
                    Country.fifa_code == normalized,
                )
            )
        )
        return country.name if country is not None else normalized

    @staticmethod
    def _seed_age(seed: NationalRegenSeed) -> int:
        if getattr(seed, "age", None) is not None:
            return int(seed.age)
        metadata = dict(seed.metadata_json or {})
        explicit = metadata.get("age")
        if isinstance(explicit, int):
            return explicit
        return 18

    @staticmethod
    def _seed_uniqueness_score(seed: NationalRegenSeed) -> float:
        return {
            "legendary": 0.92,
            "elite": 0.84,
            "rare": 0.74,
            "common": 0.62,
        }.get(str(seed.rarity_tier or "").strip().lower(), 0.58)

    @staticmethod
    def _seed_market_value(seed: NationalRegenSeed) -> int:
        return max(75_000, (seed.current_rating * 1_800) + (seed.potential_rating * 2_400))

    @staticmethod
    def _weighted_potential_roll(rng: Random) -> int:
        roll = rng.random()
        if roll < 0.48:
            return rng.randint(68, 78)
        if roll < 0.78:
            return rng.randint(79, 86)
        if roll < 0.95:
            return rng.randint(87, 92)
        return rng.randint(93, 97)

    def _synthetic_profile_from_prospect(self, prospect: _UniverseProspect) -> RegenProfileView:
        minimum_current = max(40, prospect.current_rating - 4)
        maximum_current = min(99, prospect.current_rating + 2)
        minimum_potential = max(prospect.current_rating, prospect.potential - 6)
        story_seed = None
        if prospect.story_snippet:
            story_seed = RegenStorySeedView(
                background="academy_hype",
                temperament=_growth_curve_label(prospect.growth_curve),
                ambition="world_stage",
                pressure_response="composed",
                snippet=prospect.story_snippet,
            )
        personality_tags = tuple(dict.fromkeys(prospect.discovery_badges))
        return RegenProfileView(
            id=prospect.regen_id,
            regen_id=prospect.regen_id,
            club_id=prospect.club_id or "independent-pool",
            player_id=prospect.lookup_id,
            linked_unique_card_id=f"synthetic-card:{prospect.regen_id}",
            display_name=prospect.name,
            age=prospect.age,
            birth_country_code=prospect.nationality_code or "UNK",
            primary_position=prospect.position,
            secondary_positions=tuple(),
            current_gsi=prospect.current_rating,
            current_ability_range=AbilityRangeView(minimum=minimum_current, maximum=maximum_current),
            potential_range=AbilityRangeView(minimum=minimum_potential, maximum=prospect.potential),
            current_rating=prospect.current_rating,
            potential=prospect.potential,
            scout_confidence="medium",
            generation_source=prospect.source_type,
            regen_type=prospect.regen_type,
            status="scout_pool",
            is_special_lineage=prospect.regen_type == "legend_regen",
            uniqueness_score=prospect.uniqueness_score,
            growth_curve=prospect.growth_curve,
            morale=0.62,
            chemistry_affinity={},
            story_seed=story_seed,
            generated_at=prospect.generated_at,
            club_quality_score=60.0,
            personality=RegenPersonalityView(
                temperament=58,
                leadership=50,
                ambition=74,
                loyalty=52,
                work_rate=68,
                flair=72,
                resilience=66,
                personality_tags=personality_tags,
            ),
            origin=RegenOriginView(
                country_code=prospect.nationality_code or "UNK",
                region_name=None,
                city_name=None,
            ),
            metadata=dict(prospect.metadata),
        )

    def _synthetic_card_payload(self, prospect: _UniverseProspect) -> dict[str, object]:
        badges: list[dict[str, str]] = []
        if prospect.potential >= 90:
            badges.append({"code": "elite_potential", "label": "Elite Potential", "emphasis": "highlight"})
        if prospect.source_type == "national_seed":
            badges.append({"code": "national_pool", "label": "National Pool", "emphasis": "standard"})
        if prospect.source_type == "generated":
            badges.append({"code": "generated", "label": "Generated", "emphasis": "standard"})
        for badge in prospect.discovery_badges:
            badges.append({"code": badge.lower().replace(" ", "_"), "label": badge, "emphasis": "standard"})
        return {
            "name": prospect.name,
            "position": prospect.position,
            "rating": prospect.current_rating,
            "potential": prospect.potential,
            "regen_type_badge": "Legend Echo" if prospect.regen_type == "legend_regen" else "New Wave",
            "uniqueness_badge": "Elite DNA" if prospect.uniqueness_score >= 0.82 else "Scouting Pulse",
            "legacy_score": 0.0,
            "traits_icons": tuple(
                dict.fromkeys([_growth_curve_label(prospect.growth_curve), prospect.position.lower()])
            ),
            "personality_tag": prospect.discovery_badges[0] if prospect.discovery_badges else None,
            "story_snippet": prospect.story_snippet,
            "badges": tuple(badges),
        }

    def _player_summary_payload(self, prospect: _UniverseProspect) -> dict[str, object]:
        return {
            "id": prospect.lookup_id,
            "name": prospect.name,
            "age": prospect.age,
            "nationality": prospect.nationality,
            "nationality_code": prospect.nationality_code,
            "position": prospect.position,
            "potential": prospect.potential,
            "current_rating": prospect.current_rating,
            "growth_curve": round(prospect.growth_curve, 4),
            "club_id": prospect.club_id,
            "source_type": prospect.source_type,
            "market_access": self._prospect_market_access_payload(prospect),
        }

    def _prospect_market_access_payload(self, prospect: _UniverseProspect) -> dict[str, bool]:
        if prospect.source_type == "national_seed":
            return market_access_payload(
                {
                    "source_type": "national_seed",
                    "is_preseeded_national_regen": True,
                    "national_pool_only": True,
                }
            )
        if prospect.player_id is not None:
            player = self.session.get(Player, prospect.player_id)
            if player is not None:
                return market_access_payload(player)
        return market_access_payload(
            {
                "share_market_eligible": False,
                "tradable": False,
                "buyable": False,
                "transferable": False,
                "card_mint_eligible": False,
                "buy_cta_allowed": False,
            }
        )

    def _scouting_note_for_prospect(self, prospect: _UniverseProspect) -> str:
        position_label = _position_story_label(prospect.position)
        growth_label = _growth_curve_label(prospect.growth_curve)
        return (
            f"{prospect.age}-year-old {position_label} from {prospect.nationality} with "
            f"{prospect.current_rating}/{prospect.potential} upside and a {growth_label} growth curve."
        )

    def _prospect_from_regen(
        self,
        *,
        regen: RegenProfile,
        market_service: RegenMarketService,
    ) -> _UniverseProspect | None:
        profile = market_service.get_profile_view(regen.id)
        if profile.status == "retired":
            return None
        latest_value = market_service.get_latest_value_view(regen.id)
        discovery_badges = tuple(badge.badge_name for badge in market_service.list_discovery_badges(regen.id))
        return _UniverseProspect(
            lookup_id=profile.player_id or f"regen:{profile.regen_id}",
            player_id=profile.player_id,
            regen_id=profile.regen_id,
            name=profile.display_name,
            age=profile.age,
            nationality=self._resolve_country_name(profile.birth_country_code),
            nationality_code=profile.birth_country_code,
            position=_normalize_position_label(profile.primary_position),
            potential=profile.potential or profile.current_rating or profile.current_gsi,
            current_rating=profile.current_rating or profile.current_gsi,
            growth_curve=profile.growth_curve,
            club_id=profile.club_id,
            generated_at=profile.generated_at,
            source_type="regen",
            regen_type=profile.regen_type,
            uniqueness_score=profile.uniqueness_score,
            story_snippet=profile.story_seed.snippet if profile.story_seed is not None else None,
            discovery_badges=discovery_badges,
            market_value_coin=latest_value.current_value_coin,
            profile=profile,
            card=self._card_payload(profile, legacy_score=0.0, discovery_badges=list(discovery_badges)),
            metadata=dict(profile.metadata),
        )

    def _prospect_from_seed(self, seed: NationalRegenSeed) -> _UniverseProspect:
        story_seed = dict((seed.personality_seed_json or {}).get("story_seed") or {})
        lookup_id = f"seed:{seed.id}"
        prospect = _UniverseProspect(
            lookup_id=lookup_id,
            player_id=None,
            regen_id=lookup_id,
            name=seed.display_name,
            age=self._seed_age(seed),
            nationality=self._resolve_country_name(seed.country_code, fallback_name=seed.country_name),
            nationality_code=seed.country_code,
            position=_normalize_position_label(seed.primary_position),
            potential=seed.potential_rating,
            current_rating=seed.current_rating,
            growth_curve=round(float(seed.growth_curve), 4),
            club_id=f"national-pool-{str(seed.country_code or 'global').lower()}",
            generated_at=seed.created_at,
            source_type="national_seed",
            regen_type=(
                "legend_regen"
                if seed.seed_type == "legendary_regen" or seed.rarity_tier == "legendary"
                else "organic_newgen"
            ),
            uniqueness_score=self._seed_uniqueness_score(seed),
            story_snippet=str(story_seed.get("snippet")).strip() or None,
            discovery_badges=tuple(
                dict.fromkeys(
                    [
                        str(seed.rarity_tier).title(),
                        "National Pool",
                    ]
                )
            ),
            market_value_coin=self._seed_market_value(seed),
            metadata=dict(seed.metadata_json or {}),
        )
        profile = self._synthetic_profile_from_prospect(prospect)
        return replace(prospect, profile=profile, card=self._synthetic_card_payload(prospect))

    def _fallback_country_catalog(self) -> tuple[dict[str, object], ...]:
        countries = list(
            self.session.scalars(
                select(Country)
                .where(Country.is_enabled_for_universe.is_(True))
                .order_by(Country.name.asc(), Country.id.asc())
            ).all()
        )
        if not countries:
            return _FALLBACK_COUNTRY_PROFILES
        catalog: list[dict[str, object]] = []
        for country in countries[:12]:
            code = country.alpha2_code or country.fifa_code or country.alpha3_code or country.id[:2].upper()
            weight = 1.0
            if (country.market_region or "").strip().lower() in {"europe", "south_america", "africa"}:
                weight += 0.2
            catalog.append(
                {
                    "code": code,
                    "name": country.name,
                    "weight": weight,
                    "first_names": ("Ayo", "Leo", "Milan", "Rayan", "Noah"),
                    "last_names": ("Cole", "Diallo", "Costa", "Nwosu", "Torres"),
                }
            )
        return tuple(catalog) if catalog else _FALLBACK_COUNTRY_PROFILES

    def _generate_fallback_prospects(self, *, limit: int, age_min: int, age_max: int) -> list[_UniverseProspect]:
        rng = Random(f"regen-universe:{date.today().isoformat()}:{limit}:{age_min}:{age_max}")
        countries = self._fallback_country_catalog()
        prospects: list[_UniverseProspect] = []
        position_choices = [item[0] for item in _POSITION_ROLLS]
        position_weights = [item[1] for item in _POSITION_ROLLS]
        for index in range(limit):
            country = rng.choices(countries, weights=[float(item["weight"]) for item in countries], k=1)[0]
            potential = self._weighted_potential_roll(rng)
            age = rng.choices(
                list(range(age_min, age_max + 1)),
                weights=[1, 3, 4, 4, 3, 2, 1][: (age_max - age_min + 1)],
                k=1,
            )[0]
            current_rating = max(58, min(potential - 1, potential - rng.randint(7, 20)))
            growth_curve = round(min(0.98, 0.38 + ((potential - current_rating) / 40.0) + (rng.random() * 0.18)), 4)
            position = rng.choices(position_choices, weights=position_weights, k=1)[0]
            name = f"{rng.choice(country['first_names'])} {rng.choice(country['last_names'])}"
            lookup_id = f"generated:{country['code']}:{index + 1}"
            prospect = _UniverseProspect(
                lookup_id=lookup_id,
                player_id=None,
                regen_id=lookup_id,
                name=name,
                age=age,
                nationality=str(country["name"]),
                nationality_code=str(country["code"]),
                position=position,
                potential=potential,
                current_rating=current_rating,
                growth_curve=growth_curve,
                club_id="independent-scout-pool",
                generated_at=_utcnow() - timedelta(hours=index * 2),
                source_type="generated",
                regen_type="organic_newgen",
                uniqueness_score=round(0.58 + (rng.random() * 0.28), 4),
                story_snippet=f"{_position_story_label(position).title()} prospect climbing out of the {country['name']} youth stream.",
                discovery_badges=("Generated", "Scout Watch"),
                market_value_coin=max(50_000, (current_rating * 1_550) + (potential * 2_100)),
                metadata={"generated": True},
            )
            profile = self._synthetic_profile_from_prospect(prospect)
            prospects.append(replace(prospect, profile=profile, card=self._synthetic_card_payload(prospect)))
        return prospects

    def _discovery_pool(self, *, limit: int, age_min: int = 15, age_max: int = 21) -> list[_UniverseProspect]:
        market_service = RegenMarketService(self.session)
        prospects: list[_UniverseProspect] = []
        for regen in self.session.scalars(select(RegenProfile).order_by(RegenProfile.generated_at.desc())):
            prospect = self._prospect_from_regen(regen=regen, market_service=market_service)
            if prospect is None or prospect.age < age_min or prospect.age > age_max:
                continue
            prospects.append(prospect)
        seeds = list(
            self.session.scalars(
                select(NationalRegenSeed)
                .where(NationalRegenSeed.status.in_(("active", "available")))
                .order_by(
                    NationalRegenSeed.potential_rating.desc(),
                    NationalRegenSeed.current_rating.desc(),
                    NationalRegenSeed.created_at.desc(),
                )
            ).all()
        )
        for seed in seeds:
            age = self._seed_age(seed)
            if age < age_min or age > age_max:
                continue
            prospects.append(self._prospect_from_seed(seed))
        if not prospects:
            prospects.extend(self._generate_fallback_prospects(limit=max(limit, 12), age_min=age_min, age_max=age_max))
        unique: dict[str, _UniverseProspect] = {}
        for prospect in prospects:
            unique.setdefault(prospect.lookup_id, prospect)
        return list(unique.values())

    def _prospect_lookup(self, player_id: str) -> _UniverseProspect | None:
        normalized = (player_id or "").strip()
        if not normalized:
            return None
        for prospect in self._discovery_pool(limit=64, age_min=15, age_max=21):
            if normalized in {prospect.lookup_id, prospect.player_id or ""}:
                return prospect
        return None

    @staticmethod
    def _is_seed_subject(subject_key: str | None) -> bool:
        return str(subject_key or "").strip().startswith("seed:")

    def _subject_prospect(self, subject_key: str) -> _UniverseProspect | None:
        normalized = (subject_key or "").strip()
        if not normalized:
            return None
        if self._is_seed_subject(normalized):
            seed_id = normalized.split(":", 1)[1]
            seed = self.session.get(NationalRegenSeed, seed_id)
            return self._prospect_from_seed(seed) if seed is not None else None
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == normalized))
        if regen is None:
            return None
        return self._prospect_from_regen(regen=regen, market_service=RegenMarketService(self.session))

    def _resolve_subject(self, subject_key: str, *, as_of: date | None = None) -> _UniverseSubject | None:
        normalized = (subject_key or "").strip()
        if not normalized:
            return None
        if self._is_seed_subject(normalized):
            seed_id = normalized.split(":", 1)[1]
            seed = self.session.get(NationalRegenSeed, seed_id)
            if seed is None:
                return None
            return _UniverseSubject(
                subject_key=normalized,
                player_id=None,
                national_seed_id=seed.id,
                regen_profile_id=None,
                player_name=seed.display_name,
                age=self._seed_age(seed),
                position_group=_position_group_from_position(seed.primary_position, seed.primary_position),
                source_type="national_seed",
                nationality_code=seed.country_code,
            )
        player = self.session.get(Player, normalized)
        if player is None:
            return None
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
        reference_date = as_of or date.today()
        return _UniverseSubject(
            subject_key=player.id,
            player_id=player.id,
            national_seed_id=None,
            regen_profile_id=regen.id if regen is not None else None,
            player_name=player.full_name,
            age=_calculate_age(player.date_of_birth, reference_date),
            position_group=_position_group(player),
            source_type="regen",
            nationality_code=regen.birth_country_code if regen is not None else None,
        )

    def _subject_player_payload(self, subject_key: str) -> dict[str, object] | None:
        prospect = self._subject_prospect(subject_key)
        if prospect is None:
            return None
        return self._player_summary_payload(prospect)

    def _performance_player_id(self, performance) -> str | None:
        value = performance.metadata.get("player_id") if isinstance(performance.metadata, dict) else None
        return str(value) if value else None

    def _performance_national_seed_id(self, performance) -> str | None:
        value = performance.metadata.get("national_seed_id") if isinstance(performance.metadata, dict) else None
        return str(value) if value else None

    def _ranking_player_id(self, subject_key: str) -> str | None:
        return None if self._is_seed_subject(subject_key) else subject_key

    def _ranking_national_seed_id(self, subject_key: str) -> str | None:
        if not self._is_seed_subject(subject_key):
            return None
        _, _, seed_id = subject_key.partition(":")
        return seed_id or None

    def get_player_lookup(self, player_id: str) -> dict[str, object] | None:
        prospect = self._subject_prospect(player_id)
        if prospect is None:
            prospect = self._prospect_lookup(player_id)
        if prospect is None or prospect.profile is None or prospect.card is None:
            return None
        return {
            "player": self._player_summary_payload(prospect),
            "profile": prospect.profile,
            "card": prospect.card,
            "scouting_note": self._scouting_note_for_prospect(prospect),
            "discovery_badges": list(prospect.discovery_badges),
            "market_value_coin": prospect.market_value_coin,
            "prestige": self.get_player_prestige_summary(prospect.lookup_id),
            "timeline": self.list_player_timeline(player_id=prospect.lookup_id, limit=8)["items"],
            "achievements": self.list_achievements(subject_key=prospect.lookup_id, limit=8)["items"],
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
        discovery_badges = [badge.badge_name for badge in market_service.list_discovery_badges(regen.id)]
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
            "timeline": self.list_player_timeline(player_id=player_id, limit=12)["items"],
            "achievements": self.list_achievements(subject_key=player_id, limit=12)["items"],
        }

    def list_player_timeline(
        self,
        *,
        player_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, object]:
        self._ensure_subject_story_surfaces(player_id)
        items = list(
            self.session.scalars(
                select(RegenStoryEvent)
                .where(RegenStoryEvent.subject_key == player_id)
                .order_by(RegenStoryEvent.occurred_at.desc(), RegenStoryEvent.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        total = int(
            self.session.scalar(
                select(func.count()).select_from(RegenStoryEvent).where(RegenStoryEvent.subject_key == player_id)
            )
            or 0
        )
        return {
            "player_id": player_id,
            "items": [self._story_event_payload(item) for item in items],
            "total": total,
        }

    def list_achievements(
        self,
        *,
        subject_key: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, object]:
        if subject_key:
            self._ensure_subject_story_surfaces(subject_key)
        stmt = select(RegenAchievement).order_by(RegenAchievement.earned_at.desc(), RegenAchievement.created_at.desc())
        count_stmt = select(func.count()).select_from(RegenAchievement)
        if subject_key:
            stmt = stmt.where(RegenAchievement.subject_key == subject_key)
            count_stmt = count_stmt.where(RegenAchievement.subject_key == subject_key)
        items = list(self.session.scalars(stmt.offset(offset).limit(limit)))
        total = int(self.session.scalar(count_stmt) or 0)
        return {"items": [self._achievement_payload(item) for item in items], "total": total}

    def _story_event_payload(self, event: RegenStoryEvent) -> dict[str, object]:
        metadata = dict(event.metadata_json or {})
        return {
            "id": event.id,
            "event_key": event.event_key,
            "subject_key": event.subject_key,
            "player_id": event.subject_key,
            "player_name": metadata.get("player_name"),
            "event_type": event.event_type,
            "title": event.title,
            "summary": event.summary,
            "occurred_at": event.occurred_at,
            "metadata_json": metadata,
        }

    def _achievement_payload(self, achievement: RegenAchievement) -> dict[str, object]:
        metadata = dict(achievement.metadata_json or {})
        return {
            "id": achievement.id,
            "achievement_key": achievement.achievement_key,
            "subject_key": achievement.subject_key,
            "player_id": achievement.subject_key,
            "player_name": metadata.get("player_name"),
            "achievement_type": achievement.achievement_type,
            "title": achievement.title,
            "description": achievement.description,
            "earned_at": achievement.earned_at,
            "metadata_json": metadata,
        }

    def _upsert_story_event(
        self,
        *,
        event_key: str,
        subject: _UniverseSubject,
        event_type: str,
        title: str,
        summary: str,
        occurred_at: datetime,
        season_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> RegenStoryEvent:
        payload = dict(metadata or {})
        payload.setdefault("player_name", subject.player_name)
        payload.setdefault("source_type", subject.source_type)
        event = self.session.scalar(select(RegenStoryEvent).where(RegenStoryEvent.event_key == event_key))
        if event is None:
            event = RegenStoryEvent(
                event_key=event_key,
                subject_key=subject.subject_key,
                player_id=subject.player_id,
                regen_profile_id=subject.regen_profile_id,
                national_seed_id=subject.national_seed_id,
                season_id=season_id,
                event_type=event_type,
                title=title,
                summary=summary,
                occurred_at=occurred_at,
                metadata_json=payload,
            )
            self.session.add(event)
            return event
        event.subject_key = subject.subject_key
        event.player_id = subject.player_id
        event.regen_profile_id = subject.regen_profile_id
        event.national_seed_id = subject.national_seed_id
        event.season_id = season_id
        event.event_type = event_type
        event.title = title
        event.summary = summary
        event.occurred_at = occurred_at
        event.metadata_json = payload
        return event

    def _upsert_achievement(
        self,
        *,
        achievement_key: str,
        subject: _UniverseSubject,
        achievement_type: str,
        title: str,
        description: str,
        earned_at: datetime,
        season_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> RegenAchievement:
        payload = dict(metadata or {})
        payload.setdefault("player_name", subject.player_name)
        payload.setdefault("source_type", subject.source_type)
        achievement = self.session.scalar(
            select(RegenAchievement).where(RegenAchievement.achievement_key == achievement_key)
        )
        if achievement is None:
            achievement = RegenAchievement(
                achievement_key=achievement_key,
                subject_key=subject.subject_key,
                player_id=subject.player_id,
                regen_profile_id=subject.regen_profile_id,
                national_seed_id=subject.national_seed_id,
                season_id=season_id,
                achievement_type=achievement_type,
                title=title,
                description=description,
                earned_at=earned_at,
                metadata_json=payload,
            )
            self.session.add(achievement)
            return achievement
        achievement.subject_key = subject.subject_key
        achievement.player_id = subject.player_id
        achievement.regen_profile_id = subject.regen_profile_id
        achievement.national_seed_id = subject.national_seed_id
        achievement.season_id = season_id
        achievement.achievement_type = achievement_type
        achievement.title = title
        achievement.description = description
        achievement.earned_at = earned_at
        achievement.metadata_json = payload
        return achievement

    def _sync_season_story_surfaces(self, season_id: str) -> None:
        season = self.session.get(RegenSeason, season_id)
        if season is None:
            return
        award_rows = self.session.execute(
            select(RegenAwardWinner, RegenAward)
            .join(RegenAward, RegenAward.id == RegenAwardWinner.award_id)
            .where(RegenAwardWinner.season_id == season_id)
        ).all()
        for winner, award in award_rows:
            subject = self._resolve_subject(winner.subject_key, as_of=season.end_date)
            if subject is None:
                continue
            summary = f"{winner.player_name} won {award.name} in GTEX season {season.season_number}."
            metadata = {
                **dict(winner.metadata_json or {}),
                "award_code": award.code,
                "award_name": award.name,
                "season_number": season.season_number,
                "rank": winner.rank,
            }
            self._upsert_story_event(
                event_key=f"award:{winner.id}",
                subject=subject,
                event_type="award_won",
                title=award.name,
                summary=summary,
                occurred_at=winner.awarded_at,
                season_id=season.id,
                metadata=metadata,
            )
            self._upsert_achievement(
                achievement_key=f"award:{winner.id}",
                subject=subject,
                achievement_type="award_won",
                title=award.name,
                description=summary,
                earned_at=winner.awarded_at,
                season_id=season.id,
                metadata=metadata,
            )

        national_records = [
            record
            for record in self.session.scalars(
                select(RegenPerformanceRecord)
                .where(RegenPerformanceRecord.season_id == season_id)
                .order_by(RegenPerformanceRecord.overall_score.desc())
            )
            if str((record.metadata_json or {}).get("competition_scope") or "").strip().lower() == "national"
        ]
        for record in national_records:
            subject = self._resolve_subject(record.subject_key, as_of=season.end_date)
            if subject is None:
                continue
            metadata = dict(record.metadata_json or {})
            title = f"National-team call-up for {metadata.get('competition_title') or 'GTEX selection'}"
            self._upsert_story_event(
                event_key=f"callup:{season_id}:{record.subject_key}",
                subject=subject,
                event_type="national_team_callup",
                title=title,
                summary=f"{record.player_name} featured for the national side in {metadata.get('competition_title') or 'national-team competition'}.",
                occurred_at=season.closed_at or _utcnow(),
                season_id=season_id,
                metadata=metadata,
            )
            if bool(metadata.get("won_tournament")):
                tournament_title = str(metadata.get("competition_title") or "National competition")
                self._upsert_story_event(
                    event_key=f"tournament:{season_id}:{record.subject_key}",
                    subject=subject,
                    event_type="tournament_winner",
                    title=f"{tournament_title} winner",
                    summary=f"{record.player_name} finished the campaign as a tournament winner in {tournament_title}.",
                    occurred_at=season.closed_at or _utcnow(),
                    season_id=season_id,
                    metadata=metadata,
                )
                self._upsert_achievement(
                    achievement_key=f"tournament:{season_id}:{record.subject_key}",
                    subject=subject,
                    achievement_type="tournament_winner",
                    title=f"{tournament_title} winner",
                    description=f"Won {tournament_title} during GTEX season {season.season_number}.",
                    earned_at=season.closed_at or _utcnow(),
                    season_id=season_id,
                    metadata=metadata,
                )

    def _ensure_subject_story_surfaces(self, subject_key: str) -> None:
        subject = self._resolve_subject(subject_key)
        if subject is None:
            return
        if subject.player_id:
            career_entries = list(
                self.session.scalars(
                    select(PlayerCareerEntry)
                    .where(PlayerCareerEntry.player_id == subject.player_id)
                    .order_by(PlayerCareerEntry.start_on.asc(), PlayerCareerEntry.created_at.asc())
                )
            )
            debut_entry = next((item for item in career_entries if (item.appearances or 0) > 0), None)
            if debut_entry is not None and debut_entry.start_on is not None:
                self._upsert_story_event(
                    event_key=f"debut:{debut_entry.id}",
                    subject=subject,
                    event_type="debut",
                    title="Senior debut",
                    summary=f"{subject.player_name} made a debut for {debut_entry.club_name}.",
                    occurred_at=datetime.combine(debut_entry.start_on, datetime.min.time(), tzinfo=timezone.utc),
                    metadata={"club_name": debut_entry.club_name, "season_label": debut_entry.season_label},
                )
            first_goal_entry = next((item for item in career_entries if (item.goals or 0) > 0), None)
            if first_goal_entry is not None and first_goal_entry.start_on is not None:
                self._upsert_story_event(
                    event_key=f"first-goal:{first_goal_entry.id}",
                    subject=subject,
                    event_type="first_goal",
                    title="First goal",
                    summary=f"{subject.player_name} hit a first goal for {first_goal_entry.club_name}.",
                    occurred_at=datetime.combine(first_goal_entry.start_on, datetime.min.time(), tzinfo=timezone.utc),
                    metadata={"club_name": first_goal_entry.club_name, "season_label": first_goal_entry.season_label},
                )

            lifecycle_events = list(
                self.session.scalars(
                    select(PlayerLifecycleEvent)
                    .where(PlayerLifecycleEvent.player_id == subject.player_id)
                    .order_by(PlayerLifecycleEvent.occurred_on.asc(), PlayerLifecycleEvent.created_at.asc())
                )
            )
            for lifecycle in lifecycle_events:
                if lifecycle.event_type not in {"transfer_request_submitted", "contract_renewed"}:
                    continue
                self._upsert_story_event(
                    event_key=f"lifecycle:{lifecycle.id}",
                    subject=subject,
                    event_type=lifecycle.event_type,
                    title=lifecycle.event_type.replace("_", " ").title(),
                    summary=lifecycle.summary,
                    occurred_at=datetime.combine(lifecycle.occurred_on, datetime.min.time(), tzinfo=timezone.utc),
                    metadata=dict(lifecycle.details_json or {}),
                )

            career_events = list(
                self.session.scalars(
                    select(CareerEvent)
                    .where(CareerEvent.player_id == subject.player_id)
                    .order_by(CareerEvent.occurred_on.asc(), CareerEvent.created_at.asc())
                )
            )
            for career_event in career_events:
                if career_event.type != "requested_son_created":
                    continue
                occurred_at = datetime.combine(career_event.occurred_on, datetime.min.time(), tzinfo=timezone.utc)
                event_metadata = dict(career_event.metadata_json or {})
                event_token = str(event_metadata.get("order_id") or career_event.id)
                self._upsert_story_event(
                    event_key=f"career:{event_token}",
                    subject=subject,
                    event_type="requested_son_created",
                    title="Requested son created",
                    summary=career_event.summary or f"{subject.player_name} arrived through the request-son pathway.",
                    occurred_at=occurred_at,
                    metadata=event_metadata,
                )
                self._upsert_achievement(
                    achievement_key=f"career:{event_token}",
                    subject=subject,
                    achievement_type="requested_son_created",
                    title="Requested son created",
                    description=career_event.summary
                    or f"{subject.player_name} was generated through a paid request-son flow.",
                    earned_at=occurred_at,
                    metadata=event_metadata,
                )

            if subject.regen_profile_id:
                bloodline = self.session.scalar(
                    select(RegenBloodlineLink).where(RegenBloodlineLink.regen_profile_id == subject.regen_profile_id)
                )
                if bloodline is not None:
                    metadata = dict(bloodline.metadata_json or {})
                    self._upsert_story_event(
                        event_key=f"bloodline:{bloodline.id}",
                        subject=subject,
                        event_type="bloodline_milestone",
                        title="Bloodline milestone",
                        summary=f"{subject.player_name} carries a traceable bloodline arc into the regen universe.",
                        occurred_at=bloodline.created_at,
                        metadata=metadata,
                    )
                    self._upsert_achievement(
                        achievement_key=f"bloodline:{bloodline.id}",
                        subject=subject,
                        achievement_type="bloodline_milestone",
                        title="Bloodline milestone",
                        description=f"{subject.player_name} added a new milestone to an active regen bloodline.",
                        earned_at=bloodline.created_at,
                        metadata=metadata,
                    )

            hall_of_fame = self.session.scalar(
                select(RegenHallOfFame).where(RegenHallOfFame.player_id == subject.player_id)
            )
            if hall_of_fame is not None:
                metadata = dict(hall_of_fame.metadata_json or {})
                self._upsert_story_event(
                    event_key=f"hall-of-fame:{hall_of_fame.id}",
                    subject=subject,
                    event_type="hall_of_fame_inducted",
                    title="Hall of Fame",
                    summary=f"{subject.player_name} entered the GTEX Hall of Fame.",
                    occurred_at=hall_of_fame.updated_at,
                    metadata=metadata,
                )
                self._upsert_achievement(
                    achievement_key=f"hall-of-fame:{hall_of_fame.id}",
                    subject=subject,
                    achievement_type="hall_of_fame_inducted",
                    title="Hall of Fame",
                    description=f"{subject.player_name} is now a GTEX Hall of Fame player.",
                    earned_at=hall_of_fame.updated_at,
                    metadata=metadata,
                )

    def list_rising_stars(self, *, limit: int = 20, offset: int = 0, age_max: int = 21) -> dict[str, object]:
        candidates: list[tuple[float, dict[str, object]]] = []
        for prospect in self._discovery_pool(limit=max((offset + limit) * 3, 24), age_min=15, age_max=age_max):
            if prospect.profile is None or prospect.card is None:
                continue
            prestige = (
                self.get_player_prestige_summary(prospect.player_id)
                if prospect.player_id is not None and not prospect.lookup_id.startswith("seed:")
                else None
            )
            legacy_score = float(prestige["legacy_score"]) if prestige is not None else 0.0
            entry = {
                "player_id": prospect.lookup_id,
                "player": self._player_summary_payload(prospect),
                "profile": prospect.profile,
                "card": prospect.card,
                "legacy_score": legacy_score,
                "market_value_coin": prospect.market_value_coin,
                "momentum_label": self._rising_star_momentum_label(prospect.profile),
            }
            score = (
                (prospect.potential * 1.7)
                + (prospect.current_rating * 0.6)
                + (prospect.uniqueness_score * 100.0)
                + (legacy_score * 0.2)
                + (6.0 if prospect.source_type == "regen" else 1.5 if prospect.source_type == "national_seed" else 0.0)
            )
            candidates.append((score, entry))

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1]["player"]["potential"],
                item[1]["player"]["current_rating"],
                item[1]["profile"].generated_at,
            ),
            reverse=True,
        )
        entries = [entry for _, entry in candidates]
        return {
            "entries": entries[offset : offset + limit],
            "total": len(entries),
        }

    def list_bloodlines(self, *, limit: int = 20, offset: int = 0) -> dict[str, object]:
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
                        (
                            self.session.get(RegenProfile, item.regen_id).generated_at
                            if self.session.get(RegenProfile, item.regen_id) is not None
                            else _utcnow()
                        ),
                        item.created_at,
                    ),
                ),
                start=1,
            ):
                regen = self.session.get(RegenProfile, lineage.regen_id)
                if regen is None:
                    continue
                profile = market_service.get_profile_view(regen.id)
                prestige = (
                    self.get_player_prestige_summary(profile.player_id) if profile.player_id is not None else None
                )
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
                (
                    0.0
                    if len(entries) == 1
                    else sum(abs(entry["uniqueness_score"] - baseline) for entry in entries[1:]) / (len(entries) - 1)
                ),
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
        return {
            "entries": chains[offset : offset + limit],
            "total": len(chains),
        }

    def list_scouting_feed(self, *, limit: int = 20, offset: int = 0) -> dict[str, object]:
        items: list[dict[str, object]] = []
        for prospect in self._discovery_pool(limit=max((offset + limit) * 2, 20), age_min=15, age_max=21):
            items.append(
                {
                    "feed_id": f"discover:{prospect.lookup_id}",
                    "feed_type": "new_regen_discovered",
                    "player_id": prospect.lookup_id,
                    "regen_id": prospect.regen_id,
                    "player": self._player_summary_payload(prospect),
                    "title": f"{prospect.age}-year-old {_position_story_label(prospect.position)} from {prospect.nationality} discovered",
                    "summary": prospect.story_snippet or self._scouting_note_for_prospect(prospect),
                    "occurred_at": prospect.generated_at,
                    "importance": round(0.48 + (prospect.uniqueness_score * 0.45), 4),
                    "badges": list(dict.fromkeys([prospect.source_type, *prospect.discovery_badges])),
                }
            )
            if (prospect.potential - prospect.current_rating) >= 14:
                items.append(
                    {
                        "feed_id": f"spike:{prospect.lookup_id}",
                        "feed_type": "potential_spike",
                        "player_id": prospect.lookup_id,
                        "regen_id": prospect.regen_id,
                        "player": self._player_summary_payload(prospect),
                        "title": f"{_position_story_label(prospect.position).title()} potential spike tracked",
                        "summary": f"{prospect.name} is carrying a {prospect.current_rating} to {prospect.potential} development window.",
                        "occurred_at": prospect.generated_at,
                        "importance": round(0.54 + ((prospect.potential - prospect.current_rating) / 100.0), 4),
                        "badges": ["potential_spike", _growth_curve_label(prospect.growth_curve)],
                    }
                )
            if prospect.potential >= 90 or prospect.uniqueness_score >= 0.82:
                items.append(
                    {
                        "feed_id": f"hidden:{prospect.lookup_id}",
                        "feed_type": "hidden_gem",
                        "player_id": prospect.lookup_id,
                        "regen_id": prospect.regen_id,
                        "player": self._player_summary_payload(prospect),
                        "title": f"{prospect.name} is rising as a hidden gem",
                        "summary": "Scouts are flagging rare upside, quick development potential, and immediate national-team intrigue.",
                        "occurred_at": prospect.generated_at,
                        "importance": round(0.58 + (prospect.uniqueness_score * 0.4), 4),
                        "badges": ["hidden_gem", prospect.source_type],
                    }
                )

        market_service = RegenMarketService(self.session)
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
                    "player": {
                        "id": profile.player_id,
                        "name": profile.display_name,
                        "age": profile.age,
                        "nationality": self._resolve_country_name(profile.birth_country_code),
                        "nationality_code": profile.birth_country_code,
                        "position": _normalize_position_label(profile.primary_position),
                        "potential": profile.potential or profile.current_rating or profile.current_gsi,
                        "current_rating": profile.current_rating or profile.current_gsi,
                        "growth_curve": round(profile.growth_curve, 4),
                        "club_id": profile.club_id,
                        "source_type": "regen",
                    },
                    "title": f"Scouting alert on {profile.display_name}",
                    "summary": report.summary_text,
                    "occurred_at": report.created_at,
                    "importance": round(max(report.hidden_gem_score / 100.0, 0.6), 4),
                    "badges": list(report.tags_json),
                }
            )

        recent_awards = self.session.execute(
            select(RegenAwardWinner, RegenAward)
            .join(RegenAward, RegenAward.id == RegenAwardWinner.award_id)
            .order_by(RegenAwardWinner.awarded_at.desc(), RegenAward.sort_order.asc())
            .limit(max(limit, 10))
        ).all()
        for winner, award in recent_awards:
            items.append(
                {
                    "feed_id": f"award:{winner.id}",
                    "feed_type": "award_won",
                    "player_id": winner.subject_key,
                    "regen_id": winner.subject_key,
                    "player": self._subject_player_payload(winner.subject_key),
                    "title": f"{winner.player_name} won {award.name}",
                    "summary": str((winner.metadata_json or {}).get("selection_reason") or award.description),
                    "occurred_at": winner.awarded_at,
                    "importance": round(0.72 + (0.03 if winner.rank == 1 else 0.0), 4),
                    "badges": ["award_won", award.code.lower()],
                }
            )

        recent_story_events = list(
            self.session.scalars(
                select(RegenStoryEvent)
                .where(RegenStoryEvent.event_type.in_(("transfer_request_submitted", "contract_renewed")))
                .order_by(RegenStoryEvent.occurred_at.desc(), RegenStoryEvent.id.asc())
                .limit(max(limit, 10))
            )
        )
        for event in recent_story_events:
            items.append(
                {
                    "feed_id": f"story:{event.id}",
                    "feed_type": event.event_type,
                    "player_id": event.subject_key,
                    "regen_id": event.subject_key,
                    "player": self._subject_player_payload(event.subject_key),
                    "title": event.title,
                    "summary": event.summary,
                    "occurred_at": event.occurred_at,
                    "importance": 0.74 if event.event_type == "transfer_request_submitted" else 0.64,
                    "badges": [event.event_type],
                }
            )

        items.sort(
            key=lambda item: (
                RegenUniverseService._aware_datetime(item["occurred_at"]),
                item["importance"],
            ),
            reverse=True,
        )
        return {
            "items": items[offset : offset + limit],
            "total": len(items),
        }

    def _build_club_performance_buckets(self, season: RegenSeason) -> dict[str, _AggregateBucket]:
        player_rows = list(
            self.session.execute(
                select(Player, RegenProfile)
                .join(RegenProfile, RegenProfile.player_id == Player.id)
                .where(Player.is_real_player.is_(False))
                .order_by(Player.full_name.asc(), Player.id.asc())
            ).all()
        )
        source_season_ids = self._source_ingestion_season_ids(season)
        title_lookup: set[tuple[str, str]] = set()
        standings_stmt = select(TeamStanding).where(
            TeamStanding.position == 1,
            TeamStanding.standing_type == "total",
        )
        if source_season_ids:
            standings_stmt = standings_stmt.where(TeamStanding.season_id.in_(source_season_ids))
        for standing in self.session.scalars(standings_stmt):
            if standing.club_id and standing.season_id:
                title_lookup.add((standing.club_id, standing.season_id))

        buckets = {
            player.id: _AggregateBucket(
                player_id=player.id,
                player_name=player.full_name,
                age=_calculate_age(player.date_of_birth, season.end_date),
                position_group=_position_group(player),
                player_row_id=player.id,
                regen_profile_id=regen.id,
                source_type="regen",
            )
            for player, regen in player_rows
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
            if stat.club_id and stat.season_id and (stat.club_id, stat.season_id) in title_lookup:
                bucket.trophy_points += 1.35 if competition is not None and competition.is_major else 1.0
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
            importance = _competition_importance(competition, internal_league)
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
                stage = (match.stage or "").strip().lower()
                stage_multiplier = 1.0
                if "final" in stage:
                    stage_multiplier = 1.8
                    bucket.trophy_points += 1.5 if competition is not None and competition.is_major else 1.0
                elif "semi" in stage:
                    stage_multiplier = 1.45
                elif "quarter" in stage or "knockout" in stage:
                    stage_multiplier = 1.25
                rating_bonus = max((stat.rating or 6.8) - 6.0, 0.35)
                bucket.big_match_impact += stage_multiplier * importance * rating_bonus
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
                weight = max(stat.minutes or 0, stat.appearances or 0, 1)
                bucket.competition_total += importance * weight
                bucket.competition_weight += weight
            if stat.season_id:
                bucket.source_ingestion_season_ids.add(stat.season_id)
        return buckets

    def _build_national_performance_buckets(self, season: RegenSeason) -> dict[str, _AggregateBucket]:
        competitions = [
            item
            for item in self.session.scalars(
                select(NationalTeamCompetition)
                .where(NationalTeamCompetition.linked_competition_id.is_not(None))
                .order_by(NationalTeamCompetition.created_at.asc(), NationalTeamCompetition.id.asc())
            )
            if self._national_competition_overlaps_season(item, season)
        ]
        if not competitions:
            return {}
        linked_lookup = {str(item.linked_competition_id): item for item in competitions if item.linked_competition_id}
        match_rows = list(
            self.session.scalars(
                select(CompetitionMatch)
                .where(CompetitionMatch.competition_id.in_(tuple(linked_lookup)))
                .order_by(CompetitionMatch.match_date.asc(), CompetitionMatch.created_at.asc())
            )
        )
        if not match_rows:
            return {}
        match_ids = [item.id for item in match_rows]
        events_by_match: dict[str, list[CompetitionMatchEvent]] = defaultdict(list)
        for event in self.session.scalars(
            select(CompetitionMatchEvent)
            .where(CompetitionMatchEvent.match_id.in_(match_ids))
            .order_by(CompetitionMatchEvent.created_at.asc(), CompetitionMatchEvent.id.asc())
        ):
            events_by_match[event.match_id].append(event)

        buckets: dict[str, _AggregateBucket] = {}
        for match in match_rows:
            national_competition = linked_lookup.get(match.competition_id)
            if national_competition is None:
                continue
            family = self._national_competition_family(national_competition)
            importance = self._national_competition_importance(national_competition, match.stage)
            performance_rows = dict(match.metadata_json or {}).get("player_performances")
            if isinstance(performance_rows, list) and performance_rows:
                for raw in performance_rows:
                    if not isinstance(raw, dict):
                        continue
                    self._apply_national_performance_row(
                        buckets=buckets,
                        raw=raw,
                        season=season,
                        national_competition=national_competition,
                        competition_family=family,
                        importance=importance,
                    )
                continue
            self._apply_national_event_fallback(
                buckets=buckets,
                season=season,
                national_competition=national_competition,
                competition_family=family,
                importance=importance,
                events=events_by_match.get(match.id, []),
            )
        return buckets

    @staticmethod
    def _national_competition_overlaps_season(competition: NationalTeamCompetition, season: RegenSeason) -> bool:
        candidates = (
            competition.kickoff_at,
            competition.completed_at,
            competition.entry_opens_at,
            competition.entry_closes_at,
            competition.created_at,
        )
        if not any(candidates):
            return True
        window_start = datetime.combine(season.start_date, datetime.min.time(), tzinfo=timezone.utc)
        window_end = datetime.combine(season.end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
        return any(
            candidate is not None and window_start <= RegenUniverseService._aware_datetime(candidate) < window_end
            for candidate in candidates
        )

    @staticmethod
    def _aware_datetime(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _national_competition_family(competition: NationalTeamCompetition) -> str:
        descriptor = f"{competition.key} {competition.title}".strip().lower()
        age_band = str(competition.age_band or "").strip().lower()
        if "afcon" in descriptor:
            return "afcon"
        if "world cup" in descriptor and age_band == "u17":
            return "u17_world_cup"
        if "world cup" in descriptor and age_band == "u20":
            return "u20_world_cup"
        if "world cup" in descriptor:
            return "world_cup"
        return descriptor.replace(" ", "_") or "national_competition"

    @staticmethod
    def _national_competition_importance(competition: NationalTeamCompetition, stage: str | None) -> float:
        family = RegenUniverseService._national_competition_family(competition)
        importance = 1.08
        if family in {"u17_world_cup", "u20_world_cup", "world_cup"}:
            importance = 1.34
        elif family == "afcon":
            importance = 1.24
        elif str(competition.region_type or "").strip().lower() == "global":
            importance = 1.2
        stage_label = str(stage or "").strip().lower()
        if "final" in stage_label:
            importance += 0.18
        elif "semi" in stage_label:
            importance += 0.12
        elif "quarter" in stage_label or "knockout" in stage_label:
            importance += 0.08
        return round(importance, 4)

    def _apply_national_performance_row(
        self,
        *,
        buckets: dict[str, _AggregateBucket],
        raw: dict[str, object],
        season: RegenSeason,
        national_competition: NationalTeamCompetition,
        competition_family: str,
        importance: float,
    ) -> None:
        subject_key = str(raw.get("subject_key") or raw.get("player_id") or "").strip()
        national_seed_id = str(raw.get("national_seed_id") or "").strip()
        if not subject_key and national_seed_id:
            subject_key = f"seed:{national_seed_id}"
        subject = self._resolve_subject(subject_key, as_of=season.end_date)
        if subject is None:
            return
        bucket = buckets.get(subject.subject_key)
        if bucket is None:
            bucket = _AggregateBucket(
                player_id=subject.subject_key,
                player_name=subject.player_name,
                age=subject.age,
                position_group=subject.position_group,
                player_row_id=subject.player_id,
                national_seed_id=subject.national_seed_id,
                regen_profile_id=subject.regen_profile_id,
                source_type=subject.source_type,
            )
            buckets[subject.subject_key] = bucket

        appearances = max(int(raw.get("appearances") or 1), 0)
        starts = max(int(raw.get("starts") or (appearances if bool(raw.get("started", True)) else 0)), 0)
        minutes = max(int(raw.get("minutes") or (90 if appearances > 0 else 0)), 0)
        goals = max(int(raw.get("goals") or 0), 0)
        assists = max(int(raw.get("assists") or 0), 0)
        saves = max(int(raw.get("saves") or 0), 0)
        clean_sheets = max(int(raw.get("clean_sheets") or (1 if raw.get("clean_sheet") else 0)), 0)
        rating_raw = raw.get("rating")
        rating_value = float(rating_raw) if rating_raw is not None else None
        match_count = max(int(raw.get("match_count") or appearances or 1), 1)

        bucket.appearances += appearances
        bucket.starts += starts
        bucket.minutes_played += minutes
        bucket.goals += goals
        bucket.assists += assists
        bucket.clean_sheets += clean_sheets
        bucket.saves += saves
        bucket.match_count += match_count
        bucket.start_matches += min(starts, match_count)
        bucket.full_minutes_matches += min(match_count, 1 if minutes >= 75 else 0)
        weight = max(minutes, appearances, 1)
        if rating_value is not None:
            bucket.season_rating_total += rating_value * weight
            bucket.season_rating_weight += weight
            bucket.match_rating_total += rating_value * match_count
            bucket.match_rating_weight += match_count
            bucket.rated_match_count += match_count
            bucket.high_rating_matches += match_count if rating_value >= 7.0 else 0
            bucket.big_match_impact += max(rating_value - 6.0, 0.35) * importance
        bucket.competition_total += importance * weight
        bucket.competition_weight += weight
        if bool(raw.get("won_match")):
            bucket.matches_won += min(match_count, appearances or 1)
        if bool(raw.get("won_tournament")):
            bucket.won_tournament = True
            bucket.trophy_points += 1.8
        bucket.competition_families.add(competition_family)
        bucket.national_age_bands.add(str(national_competition.age_band or "senior").strip().lower())
        bucket.competition_titles.add(national_competition.title)
        bucket.competition_ids.add(national_competition.id)

    def _apply_national_event_fallback(
        self,
        *,
        buckets: dict[str, _AggregateBucket],
        season: RegenSeason,
        national_competition: NationalTeamCompetition,
        competition_family: str,
        importance: float,
        events: list[CompetitionMatchEvent],
    ) -> None:
        by_subject: dict[str, dict[str, object]] = {}
        for event in events:
            subject_key = str(event.player_id or "").strip()
            if not subject_key:
                continue
            row = by_subject.setdefault(
                subject_key,
                {
                    "subject_key": subject_key,
                    "appearances": 1,
                    "starts": 1,
                    "minutes": int((event.metadata_json or {}).get("minutes") or 90),
                    "goals": 0,
                    "assists": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "rating": (event.metadata_json or {}).get("rating"),
                    "won_match": bool((event.metadata_json or {}).get("won_match")),
                    "won_tournament": bool((event.metadata_json or {}).get("won_tournament")),
                },
            )
            event_type = str(event.event_type or "").strip().lower()
            if event_type in {"goal", "penalty_goal"}:
                row["goals"] = int(row["goals"]) + 1
            elif event_type == "assist":
                row["assists"] = int(row["assists"]) + 1
            elif event_type in {"save", "goalkeeper_save"}:
                row["saves"] = int(row["saves"]) + 1
            elif event_type == "clean_sheet":
                row["clean_sheets"] = int(row["clean_sheets"]) + 1
        for row in by_subject.values():
            self._apply_national_performance_row(
                buckets=buckets,
                raw=row,
                season=season,
                national_competition=national_competition,
                competition_family=competition_family,
                importance=importance,
            )

    @staticmethod
    def _merge_bucket(target: _AggregateBucket, incoming: _AggregateBucket) -> None:
        target.player_name = incoming.player_name or target.player_name
        target.age = incoming.age if incoming.age is not None else target.age
        target.position_group = incoming.position_group or target.position_group
        target.player_row_id = incoming.player_row_id or target.player_row_id
        target.national_seed_id = incoming.national_seed_id or target.national_seed_id
        target.regen_profile_id = incoming.regen_profile_id or target.regen_profile_id
        target.source_type = incoming.source_type or target.source_type
        target.appearances += incoming.appearances
        target.starts += incoming.starts
        target.minutes_played += incoming.minutes_played
        target.goals += incoming.goals
        target.assists += incoming.assists
        target.clean_sheets += incoming.clean_sheets
        target.saves += incoming.saves
        target.season_rating_total += incoming.season_rating_total
        target.season_rating_weight += incoming.season_rating_weight
        target.match_rating_total += incoming.match_rating_total
        target.match_rating_weight += incoming.match_rating_weight
        target.competition_total += incoming.competition_total
        target.competition_weight += incoming.competition_weight
        target.matches_won += incoming.matches_won
        target.match_count += incoming.match_count
        target.rated_match_count += incoming.rated_match_count
        target.high_rating_matches += incoming.high_rating_matches
        target.full_minutes_matches += incoming.full_minutes_matches
        target.start_matches += incoming.start_matches
        target.has_season_stats = target.has_season_stats or incoming.has_season_stats
        target.trophy_points += incoming.trophy_points
        target.big_match_impact += incoming.big_match_impact
        target.source_ingestion_season_ids.update(incoming.source_ingestion_season_ids)
        target.competition_families.update(incoming.competition_families)
        target.national_age_bands.update(incoming.national_age_bands)
        target.competition_titles.update(incoming.competition_titles)
        target.competition_ids.update(incoming.competition_ids)
        target.won_tournament = target.won_tournament or incoming.won_tournament

    def _performance_input_from_bucket(
        self,
        *,
        bucket: _AggregateBucket,
        previous_scores: dict[str, float],
    ) -> PerformanceInput | None:
        if bucket.appearances <= 0 and bucket.minutes_played <= 0 and bucket.goals <= 0 and bucket.assists <= 0:
            return None
        if bucket.season_rating_weight > 0:
            average_rating = round(bucket.season_rating_total / bucket.season_rating_weight, 4)
        elif bucket.match_rating_weight > 0:
            average_rating = round(bucket.match_rating_total / bucket.match_rating_weight, 4)
        else:
            average_rating = None
        competition_importance = (
            round(bucket.competition_total / bucket.competition_weight, 4) if bucket.competition_weight > 0 else 1.0
        )
        metadata: dict[str, object] = {
            "player_id": bucket.player_row_id,
            "national_seed_id": bucket.national_seed_id,
            "regen_profile_id": bucket.regen_profile_id,
            "source_type": bucket.source_type,
            "source_ingestion_season_ids": sorted(bucket.source_ingestion_season_ids),
            "match_count": bucket.match_count,
            "trophy_points": round(bucket.trophy_points, 4),
            "big_match_impact": round(bucket.big_match_impact, 4),
        }
        if bucket.competition_families:
            metadata.update(
                {
                    "competition_scope": "national",
                    "competition_family": sorted(bucket.competition_families)[0],
                    "competition_families": sorted(bucket.competition_families),
                    "competition_title": sorted(bucket.competition_titles)[0] if bucket.competition_titles else None,
                    "competition_ids": sorted(bucket.competition_ids),
                    "national_age_band": (sorted(bucket.national_age_bands)[0] if bucket.national_age_bands else None),
                    "won_tournament": bucket.won_tournament,
                }
            )
        else:
            metadata["competition_scope"] = "club"
        consistency_score = self._consistency_score(bucket=bucket, average_rating=average_rating)
        return PerformanceInput(
            player_id=bucket.player_id,
            player_name=bucket.player_name,
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
            previous_overall_score=previous_scores.get(bucket.player_id),
            metadata=metadata,
        )

    def _build_performance_inputs(self, season: RegenSeason) -> list[PerformanceInput]:
        buckets = self._build_club_performance_buckets(season)
        for subject_key, incoming in self._build_national_performance_buckets(season).items():
            existing = buckets.get(subject_key)
            if existing is None:
                buckets[subject_key] = incoming
                continue
            self._merge_bucket(existing, incoming)
        previous_season = self.session.scalar(
            select(RegenSeason)
            .where(RegenSeason.season_number < season.season_number)
            .order_by(RegenSeason.season_number.desc())
        )
        previous_scores = {}
        if previous_season is not None:
            previous_scores = {
                record.subject_key: record.overall_score
                for record in self.session.scalars(
                    select(RegenPerformanceRecord).where(RegenPerformanceRecord.season_id == previous_season.id)
                )
            }
        inputs: list[PerformanceInput] = []
        for bucket in buckets.values():
            performance_input = self._performance_input_from_bucket(bucket=bucket, previous_scores=previous_scores)
            if performance_input is not None:
                inputs.append(performance_input)
        return inputs

    def _consistency_score(self, *, bucket: _AggregateBucket, average_rating: float | None) -> float:
        if bucket.match_count > 0:
            high_rating_ratio = (
                bucket.high_rating_matches / max(bucket.rated_match_count, 1) if bucket.rated_match_count > 0 else 0.0
            )
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
                select(Player)
                .join(RegenProfile, RegenProfile.player_id == Player.id)
                .where(Player.is_real_player.is_(False))
            )
        )
        overall_rankings = defaultdict(list)
        for ranking in self.session.scalars(
            select(RegenRankingSnapshot).where(RegenRankingSnapshot.category == "overall")
        ):
            overall_rankings[ranking.subject_key].append(ranking)
        performance_records = defaultdict(list)
        for record in self.session.scalars(select(RegenPerformanceRecord)):
            performance_records[record.subject_key].append(record)
        award_winners = defaultdict(list)
        for winner in self.session.scalars(select(RegenAwardWinner)):
            award_winners[winner.subject_key].append(winner)

        for player in profiles:
            peak_rank = min((item.rank for item in overall_rankings.get(player.id, [])), default=None)
            seasons_active = len({record.season_id for record in performance_records.get(player.id, [])})
            total_awards = len(award_winners.get(player.id, []))
            cumulative_score = sum(record.overall_score for record in performance_records.get(player.id, []))
            top_five_bonus = sum(4.0 for item in overall_rankings.get(player.id, []) if item.rank <= 5)
            rank_bonus = max(0.0, 25.0 - float(peak_rank or 25))
            legacy_score = round(
                (cumulative_score * 0.35)
                + (total_awards * 12.0)
                + (seasons_active * 3.0)
                + top_five_bonus
                + rank_bonus,
                4,
            )
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
        active = self.session.scalar(
            select(RegenSeason).where(RegenSeason.is_active.is_(True)).order_by(RegenSeason.season_number.desc())
        )
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
        return list(
            self.session.scalars(select(RegenAward).order_by(RegenAward.sort_order.asc(), RegenAward.code.asc()))
        )

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
            current_ids = list(
                self.session.scalars(select(IngestionSeason.id).where(IngestionSeason.is_current.is_(True)))
            )
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

    def _market_award_code(self, award: RegenAward) -> str:
        metadata = dict(award.metadata_json or {})
        market_award_code = metadata.get("market_award_code")
        if isinstance(market_award_code, str) and market_award_code.strip():
            return market_award_code.strip()
        return award.code.lower()

    def _market_award_name(self, award: RegenAward) -> str:
        metadata = dict(award.metadata_json or {})
        equivalent_name = metadata.get("equivalent_name")
        if isinstance(equivalent_name, str) and equivalent_name.strip():
            return equivalent_name.replace("Regen", "Star").strip()
        return award.name.replace("Regen", "Star").strip()

    def _award_winner_payload(self, winner: RegenAwardWinner) -> dict[str, object]:
        return {
            "id": winner.id,
            "player_id": winner.subject_key,
            "player_name": winner.player_name,
            "ranking_score": winner.ranking_score,
            "rank": winner.rank,
            "awarded_at": winner.awarded_at,
            "metadata_json": dict(winner.metadata_json),
        }

    def _ranking_payload(self, ranking: RegenRankingSnapshot) -> dict[str, object]:
        return {
            "id": ranking.id,
            "player_id": ranking.subject_key,
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
        traits_icons = tuple(tag.lower().replace(" ", "_") for tag in trait_source if tag)
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
            "personality_tag": (
                personality_tags[0]
                if personality_tags
                else (profile.story_seed.temperament if profile.story_seed is not None else None)
            ),
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
