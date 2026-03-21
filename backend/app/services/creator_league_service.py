from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
import re

from sqlalchemy import case, select
from sqlalchemy.orm import Session, aliased

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.match_status import MatchStatus
from app.common.schemas.competition import CompetitionSchedulePlan, CompetitionWindowAssignment
from app.models.base import generate_uuid, utcnow
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_round import CompetitionRound
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.competition_schedule_job import CompetitionScheduleJob
from app.models.creator_league import (
    CreatorLeagueConfig,
    CreatorLeagueSeason,
    CreatorLeagueSeasonTier,
    CreatorLeagueTier,
)
from app.schemas.creator_league import (
    CreatorLeagueConfigUpdateRequest,
    CreatorLeagueConfigView,
    CreatorLeagueLiveMatchView,
    CreatorLeagueLivePriorityView,
    CreatorLeagueMovementRuleView,
    CreatorLeagueSeasonCreateRequest,
    CreatorLeagueSeasonTierView,
    CreatorLeagueSeasonView,
    CreatorLeagueStandingView,
    CreatorLeagueTierCreateRequest,
    CreatorLeagueTierUpdateRequest,
    CreatorLeagueTierView,
)
from app.risk_ops_engine.service import RiskOpsService
from app.services.competition_fixture_service import CompetitionFixtureService


class CreatorLeagueError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(slots=True)
class CreatorLeagueService:
    session: Session
    fixture_service: CompetitionFixtureService = field(default_factory=CompetitionFixtureService)

    LEAGUE_KEY = "creator_league"
    DEFAULT_DIVISION_COUNT = 3
    DEFAULT_CLUB_COUNT = 20
    DEFAULT_MOVEMENT_SPOTS = 3
    DEFAULT_FORMAT = "double_round_robin"
    DEFAULT_MATCH_FREQUENCY_DAYS = 7
    DEFAULT_SEASON_DURATION_DAYS = 266

    def get_overview(self) -> CreatorLeagueConfigView:
        config = self._ensure_config()
        return self._to_config_view(config)

    def update_config(
        self,
        payload: CreatorLeagueConfigUpdateRequest,
        *,
        actor_user_id: str | None = None,
    ) -> CreatorLeagueConfigView:
        config = self._ensure_config()
        previously_paused = config.seasons_paused
        financial_changes: dict[str, object] = {}

        if payload.enabled is not None:
            config.enabled = payload.enabled
        if payload.seasons_paused is not None:
            config.seasons_paused = payload.seasons_paused
        if payload.league_format is not None:
            config.league_format = payload.league_format
        if payload.default_club_count is not None:
            config.default_club_count = payload.default_club_count
        if payload.match_frequency_days is not None:
            config.match_frequency_days = payload.match_frequency_days
        if payload.season_duration_days is not None:
            config.season_duration_days = payload.season_duration_days
        if payload.broadcast_purchases_enabled is not None:
            config.broadcast_purchases_enabled = payload.broadcast_purchases_enabled
            financial_changes["broadcast_purchases_enabled"] = payload.broadcast_purchases_enabled
        if payload.season_pass_sales_enabled is not None:
            config.season_pass_sales_enabled = payload.season_pass_sales_enabled
            financial_changes["season_pass_sales_enabled"] = payload.season_pass_sales_enabled
        if payload.match_gifting_enabled is not None:
            config.match_gifting_enabled = payload.match_gifting_enabled
            financial_changes["match_gifting_enabled"] = payload.match_gifting_enabled
        if payload.settlement_review_enabled is not None:
            config.settlement_review_enabled = payload.settlement_review_enabled
            financial_changes["settlement_review_enabled"] = payload.settlement_review_enabled
        if payload.settlement_review_total_revenue_coin is not None:
            config.settlement_review_total_revenue_coin = payload.settlement_review_total_revenue_coin
            financial_changes["settlement_review_total_revenue_coin"] = str(payload.settlement_review_total_revenue_coin)
        if payload.settlement_review_creator_share_coin is not None:
            config.settlement_review_creator_share_coin = payload.settlement_review_creator_share_coin
            financial_changes["settlement_review_creator_share_coin"] = str(payload.settlement_review_creator_share_coin)
        if payload.settlement_review_platform_share_coin is not None:
            config.settlement_review_platform_share_coin = payload.settlement_review_platform_share_coin
            financial_changes["settlement_review_platform_share_coin"] = str(payload.settlement_review_platform_share_coin)
        if payload.settlement_review_shareholder_distribution_coin is not None:
            config.settlement_review_shareholder_distribution_coin = payload.settlement_review_shareholder_distribution_coin
            financial_changes["settlement_review_shareholder_distribution_coin"] = str(
                payload.settlement_review_shareholder_distribution_coin
            )
        if payload.division_count is not None:
            self._reconcile_division_count(config, payload.division_count)

        current_season = self._current_season(config.id)
        if not config.enabled or config.seasons_paused:
            if current_season is not None and current_season.status not in {"completed", "reset"}:
                self._pause_season_models(current_season)
        elif previously_paused and current_season is not None and current_season.status == "paused":
            current_season.status = "live"
            current_season.paused_at = None
            self._set_season_tier_status(current_season.id, "live")

        if actor_user_id is not None and financial_changes:
            RiskOpsService(self.session).log_audit(
                actor_user_id=actor_user_id,
                action_key="creator_league.financial.config.updated",
                resource_type="creator_league_finance",
                resource_id=config.id,
                detail="Creator League financial policy updated.",
                metadata_json=financial_changes,
            )
        self.session.commit()
        return self._to_config_view(config)

    def add_tier(self, payload: CreatorLeagueTierCreateRequest) -> CreatorLeagueConfigView:
        config = self._ensure_config()
        active_tiers = self._active_tiers(config.id)
        previous_last = active_tiers[-1] if active_tiers else None
        if previous_last is not None and previous_last.relegation_spots == 0:
            previous_last.relegation_spots = min(self.DEFAULT_MOVEMENT_SPOTS, max(0, previous_last.club_count - 1))

        next_order = len(active_tiers) + 1
        tier_name = payload.name or f"Division {next_order}"
        self.session.add(
            CreatorLeagueTier(
                config_id=config.id,
                name=tier_name,
                slug=self._slugify(tier_name),
                display_order=next_order,
                club_count=payload.club_count,
                promotion_spots=payload.promotion_spots,
                relegation_spots=payload.relegation_spots,
                active=True,
                metadata_json={},
            )
        )
        self.session.flush()
        self._normalize_tiers(self._active_tiers(config.id))
        self.session.commit()
        return self._to_config_view(config)

    def update_tier(self, tier_id: str, payload: CreatorLeagueTierUpdateRequest) -> CreatorLeagueConfigView:
        if payload.active is False:
            return self.delete_tier(tier_id)

        tier = self._require_tier(tier_id)
        if payload.name is not None:
            tier.name = payload.name
        if payload.club_count is not None:
            tier.club_count = payload.club_count
        if payload.promotion_spots is not None:
            tier.promotion_spots = payload.promotion_spots
        if payload.relegation_spots is not None:
            tier.relegation_spots = payload.relegation_spots

        self._normalize_tiers(self._active_tiers(tier.config_id))
        self.session.commit()
        config = self.session.get(CreatorLeagueConfig, tier.config_id)
        return self._to_config_view(config)

    def delete_tier(self, tier_id: str) -> CreatorLeagueConfigView:
        tier = self._require_tier(tier_id)
        active_tiers = self._active_tiers(tier.config_id)
        if len(active_tiers) <= 1:
            raise CreatorLeagueError("Creator League must keep at least one active division.", reason="minimum_divisions")

        self.session.delete(tier)
        self.session.flush()
        self._normalize_tiers(self._active_tiers(tier.config_id))
        self.session.commit()
        config = self.session.get(CreatorLeagueConfig, tier.config_id)
        return self._to_config_view(config)

    def reset_structure(self) -> CreatorLeagueConfigView:
        config = self._ensure_config()
        reset_at = utcnow()

        active_seasons = self.session.scalars(
            select(CreatorLeagueSeason)
            .where(CreatorLeagueSeason.config_id == config.id, CreatorLeagueSeason.status.in_(("scheduled", "live", "paused")))
        ).all()
        for season in active_seasons:
            season.status = "reset"
            season.completed_at = reset_at
            season.metadata_json = {**(season.metadata_json or {}), "reset_at": reset_at.isoformat()}
            self._set_season_tier_status(season.id, "reset")
            for season_tier in self._season_tiers(season.id):
                competition = self.session.get(Competition, season_tier.competition_id)
                if competition is not None:
                    competition.status = CompetitionStatus.CANCELLED.value
                    competition.stage = "reset"
                    competition.metadata_json = {**(competition.metadata_json or {}), "creator_league_reset": True}

        for tier in self._active_tiers(config.id):
            self.session.delete(tier)
        self.session.flush()

        config.enabled = True
        config.seasons_paused = False
        config.league_format = self.DEFAULT_FORMAT
        config.default_club_count = self.DEFAULT_CLUB_COUNT
        config.match_frequency_days = self.DEFAULT_MATCH_FREQUENCY_DAYS
        config.season_duration_days = self.DEFAULT_SEASON_DURATION_DAYS
        self._create_default_tiers(config.id)
        self.session.commit()
        return self._to_config_view(config)

    def create_season(self, payload: CreatorLeagueSeasonCreateRequest) -> CreatorLeagueSeasonView:
        config = self._ensure_config()
        if not config.enabled:
            raise CreatorLeagueError("Creator League is disabled.", reason="creator_league_disabled")
        if config.seasons_paused:
            raise CreatorLeagueError("Creator League seasons are paused.", reason="creator_league_paused")

        tiers = self._active_tiers(config.id)
        assignments = {assignment.tier_id: list(assignment.club_ids) for assignment in payload.assignments}
        if set(assignments) != {tier.id for tier in tiers}:
            raise CreatorLeagueError("Assignments must be provided for every active division.", reason="assignment_mismatch")

        all_club_ids = [club_id for club_ids in assignments.values() for club_id in club_ids]
        if len(all_club_ids) != len(set(all_club_ids)):
            raise CreatorLeagueError("A club cannot be assigned to multiple divisions in one season.", reason="duplicate_club_assignment")
        self._validate_club_ids(all_club_ids)

        season_number = (self.session.scalar(select(CreatorLeagueSeason.season_number).order_by(CreatorLeagueSeason.season_number.desc()).limit(1)) or 0) + 1
        season_name = payload.name or f"Creator League Season {season_number}"
        max_rounds = max(self._round_count(tier.club_count, config.league_format) for tier in tiers)
        required_duration_days = config.match_frequency_days * max(0, max_rounds - 1)
        season_duration_days = max(config.season_duration_days, required_duration_days)
        season_status = "live" if payload.activate else "scheduled"

        season = CreatorLeagueSeason(
            config_id=config.id,
            season_number=season_number,
            name=season_name,
            status=season_status,
            start_date=payload.start_date,
            end_date=payload.start_date + timedelta(days=season_duration_days),
            match_frequency_days=config.match_frequency_days,
            season_duration_days=season_duration_days,
            launched_at=utcnow() if payload.activate else None,
            metadata_json={},
        )
        self.session.add(season)
        self.session.flush()

        competitions: list[Competition] = []
        rule_sets: list[CompetitionRuleSet] = []
        participants: list[CompetitionParticipant] = []
        rounds: list[CompetitionRound] = []
        matches: list[CompetitionMatch] = []
        schedule_jobs: list[CompetitionScheduleJob] = []
        season_tiers: list[CreatorLeagueSeasonTier] = []

        for tier in tiers:
            club_ids = assignments[tier.id]
            if len(club_ids) != tier.club_count:
                raise CreatorLeagueError(f"{tier.name} requires exactly {tier.club_count} clubs.", reason="invalid_club_count")

            season_tier_id = generate_uuid()
            competition = self._build_competition(
                config=config,
                season=season,
                tier=tier,
                season_tier_id=season_tier_id,
                created_by_user_id=payload.created_by_user_id,
                activate=payload.activate,
            )
            rule_set = self._build_rule_set(competition.id, tier.club_count)
            tier_participants = [
                CompetitionParticipant(
                    competition_id=competition.id,
                    club_id=club_id,
                    seed=index,
                    seed_locked=True,
                    status="joined",
                    paid_entry_fee_minor=0,
                )
                for index, club_id in enumerate(club_ids, start=1)
            ]
            round_count = self._round_count(tier.club_count, config.league_format)
            schedule_plan = self._build_schedule_plan(
                competition_id=competition.id,
                start_date=payload.start_date,
                round_count=round_count,
                match_frequency_days=config.match_frequency_days,
            )
            schedule_jobs.append(
                CompetitionScheduleJob(
                    competition_id=competition.id,
                    status="scheduled",
                    requested_start_on=payload.start_date,
                    requested_dates_json=[assignment.match_date.isoformat() for assignment in schedule_plan.assignments],
                    assigned_dates_json=[assignment.match_date.isoformat() for assignment in schedule_plan.assignments],
                    schedule_plan_json=schedule_plan.model_dump(mode="json"),
                    preview_only=False,
                    alignment_group=f"{self.LEAGUE_KEY}:{season.id}",
                    alignment_week=payload.start_date.isocalendar().week,
                    alignment_year=payload.start_date.isocalendar().year,
                    requires_exclusive_windows=False,
                    priority=5,
                    created_by_user_id=payload.created_by_user_id,
                    metadata_json={"source": self.LEAGUE_KEY},
                )
            )
            fixture_build = self.fixture_service.build_initial_fixtures(
                competition=competition,
                rule_set=rule_set,
                participants=tier_participants,
                schedule_plan=schedule_plan,
            )
            for match in fixture_build.matches:
                if match.match_date is not None and match.window is not None:
                    match.scheduled_at = FixtureWindow(match.window).kickoff_at(match.match_date)

            competitions.append(competition)
            rule_sets.append(rule_set)
            participants.extend(tier_participants)
            rounds.extend(fixture_build.rounds)
            matches.extend(fixture_build.matches)
            season_tiers.append(
                CreatorLeagueSeasonTier(
                    id=season_tier_id,
                    season_id=season.id,
                    tier_id=tier.id,
                    competition_id=competition.id,
                    competition_name=competition.name,
                    tier_name=tier.name,
                    tier_order=tier.display_order,
                    club_ids_json=club_ids,
                    round_count=len(fixture_build.rounds),
                    fixture_count=len(fixture_build.matches),
                    status=season_status,
                    banner_title="LIVE NOW - Creator League",
                    banner_subtitle=None,
                    metadata_json={
                        "tier_slug": tier.slug,
                        "promotion_spots": tier.promotion_spots,
                        "relegation_spots": tier.relegation_spots,
                    },
                )
            )

        self.session.add_all(competitions)
        self.session.add_all(rule_sets)
        self.session.add_all(participants)
        self.session.add_all(rounds)
        self.session.add_all(matches)
        self.session.add_all(schedule_jobs)
        self.session.add_all(season_tiers)
        self.session.commit()
        return self.get_season(season.id)

    def get_season(self, season_id: str) -> CreatorLeagueSeasonView:
        season = self._require_season(season_id)
        return self._to_season_view(season)

    def pause_season(self, season_id: str) -> CreatorLeagueSeasonView:
        season = self._require_season(season_id)
        self._pause_season_models(season)
        config = self.session.get(CreatorLeagueConfig, season.config_id)
        if config is not None:
            config.seasons_paused = True
        self.session.commit()
        return self._to_season_view(season)

    def get_standings(self, season_tier_id: str) -> tuple[CreatorLeagueStandingView, ...]:
        season_tier = self._require_season_tier(season_tier_id)
        current_tier = self.session.get(CreatorLeagueTier, season_tier.tier_id)
        promotion_spots = int((season_tier.metadata_json or {}).get("promotion_spots", current_tier.promotion_spots if current_tier else 0))
        relegation_spots = int((season_tier.metadata_json or {}).get("relegation_spots", current_tier.relegation_spots if current_tier else 0))

        rows = self.session.execute(
            select(CompetitionParticipant, ClubProfile)
            .outerjoin(ClubProfile, ClubProfile.id == CompetitionParticipant.club_id)
            .where(CompetitionParticipant.competition_id == season_tier.competition_id)
            .order_by(
                CompetitionParticipant.points.desc(),
                CompetitionParticipant.goal_diff.desc(),
                CompetitionParticipant.goals_for.desc(),
                CompetitionParticipant.wins.desc(),
                CompetitionParticipant.seed.asc(),
                CompetitionParticipant.club_id.asc(),
            )
        ).all()
        standings: list[CreatorLeagueStandingView] = []
        total_rows = len(rows)
        for rank, (participant, club) in enumerate(rows, start=1):
            movement_zone = "safe"
            if promotion_spots > 0 and rank <= promotion_spots:
                movement_zone = "promotion"
            elif relegation_spots > 0 and rank > total_rows - relegation_spots:
                movement_zone = "relegation"
            standings.append(
                CreatorLeagueStandingView(
                    rank=rank,
                    club_id=participant.club_id,
                    club_name=club.club_name if club is not None else None,
                    played=participant.played,
                    wins=participant.wins,
                    draws=participant.draws,
                    losses=participant.losses,
                    goals_for=participant.goals_for,
                    goals_against=participant.goals_against,
                    goal_diff=participant.goal_diff,
                    points=participant.points,
                    movement_zone=movement_zone,
                )
            )
        return tuple(standings)

    def live_priority(self, *, limit: int = 10) -> CreatorLeagueLivePriorityView:
        home_club = aliased(ClubProfile)
        away_club = aliased(ClubProfile)
        rows = self.session.execute(
            select(CompetitionMatch, Competition, CreatorLeagueSeasonTier, CreatorLeagueSeason, home_club, away_club)
            .join(Competition, Competition.id == CompetitionMatch.competition_id)
            .outerjoin(CreatorLeagueSeasonTier, CreatorLeagueSeasonTier.competition_id == Competition.id)
            .outerjoin(CreatorLeagueSeason, CreatorLeagueSeason.id == CreatorLeagueSeasonTier.season_id)
            .outerjoin(home_club, home_club.id == CompetitionMatch.home_club_id)
            .outerjoin(away_club, away_club.id == CompetitionMatch.away_club_id)
            .where(CompetitionMatch.status == MatchStatus.IN_PROGRESS.value)
            .order_by(
                case((Competition.source_type == self.LEAGUE_KEY, 0), else_=1),
                case((CompetitionMatch.scheduled_at.is_(None), 1), else_=0),
                CompetitionMatch.scheduled_at.asc(),
                CompetitionMatch.created_at.asc(),
            )
            .limit(limit)
        ).all()

        matches: list[CreatorLeagueLiveMatchView] = []
        for index, (match, competition, season_tier, season, home, away) in enumerate(rows, start=1):
            is_creator_league = competition.source_type == self.LEAGUE_KEY
            home_name = home.club_name if home is not None else None
            away_name = away.club_name if away is not None else None
            matches.append(
                CreatorLeagueLiveMatchView(
                    match_id=match.id,
                    competition_id=competition.id,
                    competition_name=competition.name,
                    season_id=season.id if season is not None else None,
                    season_tier_id=season_tier.id if season_tier is not None else None,
                    home_club_id=match.home_club_id,
                    home_club_name=home_name,
                    away_club_id=match.away_club_id,
                    away_club_name=away_name,
                    scheduled_at=match.scheduled_at,
                    status=MatchStatus(match.status),
                    is_creator_league=is_creator_league,
                    priority_rank=index,
                    banner_title="LIVE NOW - Creator League" if is_creator_league else None,
                    banner_subtitle=f"{home_name or match.home_club_id} vs {away_name or match.away_club_id}" if is_creator_league else None,
                )
            )

        banner_title = None
        banner_subtitle = None
        creator_match = next((item for item in matches if item.is_creator_league), None)
        if creator_match is not None:
            banner_title = creator_match.banner_title
            banner_subtitle = creator_match.banner_subtitle
        elif matches:
            first_match = matches[0]
            banner_title = "LIVE NOW - Featured Match"
            banner_subtitle = f"{first_match.home_club_name or first_match.home_club_id} vs {first_match.away_club_name or first_match.away_club_id}"

        return CreatorLeagueLivePriorityView(
            banner_title=banner_title,
            banner_subtitle=banner_subtitle,
            matches=tuple(matches),
        )

    def _ensure_config(self) -> CreatorLeagueConfig:
        config = self.session.scalar(select(CreatorLeagueConfig).where(CreatorLeagueConfig.league_key == self.LEAGUE_KEY))
        if config is not None:
            return config

        config = CreatorLeagueConfig(
            league_key=self.LEAGUE_KEY,
            enabled=True,
            seasons_paused=False,
            league_format=self.DEFAULT_FORMAT,
            default_club_count=self.DEFAULT_CLUB_COUNT,
            match_frequency_days=self.DEFAULT_MATCH_FREQUENCY_DAYS,
            season_duration_days=self.DEFAULT_SEASON_DURATION_DAYS,
            metadata_json={},
        )
        self.session.add(config)
        self.session.flush()
        self._create_default_tiers(config.id)
        self.session.commit()
        return config

    def _create_default_tiers(self, config_id: str) -> None:
        for name, display_order, club_count, promotion_spots, relegation_spots in (
            ("Division 1", 1, self.DEFAULT_CLUB_COUNT, 0, self.DEFAULT_MOVEMENT_SPOTS),
            ("Division 2", 2, self.DEFAULT_CLUB_COUNT, self.DEFAULT_MOVEMENT_SPOTS, self.DEFAULT_MOVEMENT_SPOTS),
            ("Division 3", 3, self.DEFAULT_CLUB_COUNT, self.DEFAULT_MOVEMENT_SPOTS, 0),
        ):
            self.session.add(
                CreatorLeagueTier(
                    config_id=config_id,
                    name=name,
                    slug=self._slugify(name),
                    display_order=display_order,
                    club_count=club_count,
                    promotion_spots=promotion_spots,
                    relegation_spots=relegation_spots,
                    active=True,
                    metadata_json={},
                )
            )
        self.session.flush()

    def _reconcile_division_count(self, config: CreatorLeagueConfig, division_count: int) -> None:
        tiers = self._active_tiers(config.id)
        current_count = len(tiers)
        if division_count == current_count:
            return
        if division_count > current_count:
            previous_last = tiers[-1] if tiers else None
            if previous_last is not None and previous_last.relegation_spots == 0:
                previous_last.relegation_spots = min(self.DEFAULT_MOVEMENT_SPOTS, max(0, previous_last.club_count - 1))
            for order in range(current_count + 1, division_count + 1):
                tier_name = f"Division {order}"
                self.session.add(
                    CreatorLeagueTier(
                        config_id=config.id,
                        name=tier_name,
                        slug=self._slugify(tier_name),
                        display_order=order,
                        club_count=config.default_club_count,
                        promotion_spots=min(self.DEFAULT_MOVEMENT_SPOTS, max(0, config.default_club_count - 1)),
                        relegation_spots=0,
                        active=True,
                        metadata_json={},
                    )
                )
        else:
            for tier in tiers[division_count:]:
                self.session.delete(tier)
        self.session.flush()
        self._normalize_tiers(self._active_tiers(config.id))

    def _pause_season_models(self, season: CreatorLeagueSeason) -> None:
        season.status = "paused"
        season.paused_at = utcnow()
        self._set_season_tier_status(season.id, "paused")
        competition_ids = [season_tier.competition_id for season_tier in self._season_tiers(season.id)]
        if not competition_ids:
            return

        live_matches = self.session.scalars(
            select(CompetitionMatch).where(
                CompetitionMatch.competition_id.in_(competition_ids),
                CompetitionMatch.status == MatchStatus.IN_PROGRESS.value,
            )
        ).all()
        for match in live_matches:
            match.status = MatchStatus.PAUSED.value

        competitions = self.session.scalars(select(Competition).where(Competition.id.in_(competition_ids))).all()
        for competition in competitions:
            competition.stage = "paused"
            competition.metadata_json = {**(competition.metadata_json or {}), "season_paused": True}

    def _set_season_tier_status(self, season_id: str, status_value: str) -> None:
        for season_tier in self._season_tiers(season_id):
            season_tier.status = status_value

    def _active_tiers(self, config_id: str) -> list[CreatorLeagueTier]:
        return self.session.scalars(
            select(CreatorLeagueTier)
            .where(CreatorLeagueTier.config_id == config_id, CreatorLeagueTier.active.is_(True))
            .order_by(CreatorLeagueTier.display_order.asc(), CreatorLeagueTier.created_at.asc())
        ).all()

    def _season_tiers(self, season_id: str) -> list[CreatorLeagueSeasonTier]:
        return self.session.scalars(
            select(CreatorLeagueSeasonTier)
            .where(CreatorLeagueSeasonTier.season_id == season_id)
            .order_by(CreatorLeagueSeasonTier.tier_order.asc(), CreatorLeagueSeasonTier.created_at.asc())
        ).all()

    def _current_season(self, config_id: str) -> CreatorLeagueSeason | None:
        return self.session.scalar(
            select(CreatorLeagueSeason)
            .where(CreatorLeagueSeason.config_id == config_id)
            .order_by(
                case((CreatorLeagueSeason.status.in_(("live", "scheduled", "paused")), 0), else_=1),
                CreatorLeagueSeason.season_number.desc(),
            )
            .limit(1)
        )

    def _normalize_tiers(self, tiers: list[CreatorLeagueTier]) -> None:
        ordered = sorted(tiers, key=lambda item: (item.display_order, item.created_at))
        seen_slugs: set[str] = set()
        for index, tier in enumerate(ordered, start=1):
            tier.display_order = index
            tier.name = tier.name.strip() or f"Division {index}"
            slug_base = self._slugify(tier.name)
            slug = slug_base
            suffix = 2
            while slug in seen_slugs:
                slug = f"{slug_base}-{suffix}"
                suffix += 1
            tier.slug = slug
            seen_slugs.add(slug)

            max_spots = max(0, tier.club_count - 1)
            tier.promotion_spots = min(max(0, tier.promotion_spots), max_spots)
            tier.relegation_spots = min(max(0, tier.relegation_spots), max_spots)
            if tier.promotion_spots + tier.relegation_spots >= tier.club_count:
                overflow = tier.promotion_spots + tier.relegation_spots - tier.club_count + 1
                if tier.relegation_spots >= overflow:
                    tier.relegation_spots -= overflow
                else:
                    tier.promotion_spots = max(0, tier.promotion_spots - (overflow - tier.relegation_spots))
                    tier.relegation_spots = 0

        if ordered:
            ordered[0].promotion_spots = 0
            ordered[-1].relegation_spots = 0

    def _build_competition(
        self,
        *,
        config: CreatorLeagueConfig,
        season: CreatorLeagueSeason,
        tier: CreatorLeagueTier,
        season_tier_id: str,
        created_by_user_id: str | None,
        activate: bool,
    ) -> Competition:
        now = utcnow()
        return Competition(
            id=generate_uuid(),
            host_user_id=created_by_user_id or config.id,
            name=f"Creator League {tier.name} - Season {season.season_number}",
            description=f"{tier.name} schedule for {season.name}",
            competition_type=self.LEAGUE_KEY,
            source_type=self.LEAGUE_KEY,
            source_id=season_tier_id,
            format=CompetitionFormat.LEAGUE.value,
            visibility=CompetitionVisibility.PUBLIC.value,
            status=CompetitionStatus.LIVE.value if activate else CompetitionStatus.PUBLISHED.value,
            start_mode=CompetitionStartMode.SCHEDULED.value,
            scheduled_start_at=FixtureWindow.senior_windows()[0].kickoff_at(season.start_date),
            opened_at=now,
            launched_at=now if activate else None,
            stage="league",
            currency="coin",
            entry_fee_minor=0,
            platform_fee_bps=0,
            host_fee_bps=0,
            host_creation_fee_minor=0,
            gross_pool_minor=0,
            net_prize_pool_minor=0,
            metadata_json={
                "creator_league": True,
                "creator_league_config_id": config.id,
                "creator_league_season_id": season.id,
                "creator_league_tier_id": tier.id,
                "creator_league_tier_name": tier.name,
                "creator_league_season_tier_id": season_tier_id,
            },
        )

    def _build_rule_set(self, competition_id: str, club_count: int) -> CompetitionRuleSet:
        return CompetitionRuleSet(
            competition_id=competition_id,
            format=CompetitionFormat.LEAGUE.value,
            min_participants=club_count,
            max_participants=club_count,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
            league_tie_break_order=["points", "goal_diff", "goals_for", "wins"],
            league_home_away=True,
            cup_single_elimination=False,
            cup_two_leg_tie=False,
            cup_extra_time=False,
            cup_penalties=False,
            cup_allowed_participant_sizes=[],
            group_stage_enabled=False,
            group_count=None,
            group_size=None,
            group_advance_count=None,
            knockout_bracket_size=None,
        )

    def _build_schedule_plan(
        self,
        *,
        competition_id: str,
        start_date: date,
        round_count: int,
        match_frequency_days: int,
    ) -> CompetitionSchedulePlan:
        windows = FixtureWindow.senior_windows()
        assignments = tuple(
            CompetitionWindowAssignment(
                competition_id=competition_id,
                competition_type=self._competition_type(),
                match_date=start_date + timedelta(days=match_frequency_days * index),
                windows=(windows[index % len(windows)],),
                label=f"Round {index + 1}",
            )
            for index in range(round_count)
        )
        return CompetitionSchedulePlan(assignments=assignments)

    @staticmethod
    def _competition_type():
        from app.common.enums.competition_type import CompetitionType

        return CompetitionType.LEAGUE

    @staticmethod
    def _round_count(club_count: int, league_format: str) -> int:
        if club_count <= 1:
            return 0
        base_rounds = club_count - 1
        if league_format == "single_round_robin":
            return base_rounds
        return base_rounds * 2

    def _validate_club_ids(self, club_ids: list[str]) -> None:
        if not club_ids:
            raise CreatorLeagueError("Creator League season assignments require clubs.", reason="missing_clubs")
        existing_ids = set(self.session.scalars(select(ClubProfile.id).where(ClubProfile.id.in_(club_ids))).all())
        missing_ids = sorted(set(club_ids) - existing_ids)
        if missing_ids:
            raise CreatorLeagueError(
                f"Unknown club ids: {', '.join(missing_ids[:5])}",
                reason="club_not_found",
            )

    def _require_tier(self, tier_id: str) -> CreatorLeagueTier:
        tier = self.session.get(CreatorLeagueTier, tier_id)
        if tier is None:
            raise CreatorLeagueError(f"Creator League tier {tier_id} was not found.", reason="tier_not_found")
        return tier

    def _require_season(self, season_id: str) -> CreatorLeagueSeason:
        season = self.session.get(CreatorLeagueSeason, season_id)
        if season is None:
            raise CreatorLeagueError(f"Creator League season {season_id} was not found.", reason="season_not_found")
        return season

    def _require_season_tier(self, season_tier_id: str) -> CreatorLeagueSeasonTier:
        season_tier = self.session.get(CreatorLeagueSeasonTier, season_tier_id)
        if season_tier is None:
            raise CreatorLeagueError(
                f"Creator League season tier {season_tier_id} was not found.",
                reason="season_tier_not_found",
            )
        return season_tier

    def _to_config_view(self, config: CreatorLeagueConfig) -> CreatorLeagueConfigView:
        tiers = tuple(self._to_tier_view(tier) for tier in self._active_tiers(config.id))
        current_season = self._current_season(config.id)
        return CreatorLeagueConfigView(
            id=config.id,
            league_key=config.league_key,
            enabled=config.enabled,
            seasons_paused=config.seasons_paused,
            league_format=config.league_format,
            default_club_count=config.default_club_count,
            division_count=len(tiers),
            match_frequency_days=config.match_frequency_days,
            season_duration_days=config.season_duration_days,
            broadcast_purchases_enabled=config.broadcast_purchases_enabled,
            season_pass_sales_enabled=config.season_pass_sales_enabled,
            match_gifting_enabled=config.match_gifting_enabled,
            settlement_review_enabled=config.settlement_review_enabled,
            settlement_review_total_revenue_coin=config.settlement_review_total_revenue_coin,
            settlement_review_creator_share_coin=config.settlement_review_creator_share_coin,
            settlement_review_platform_share_coin=config.settlement_review_platform_share_coin,
            settlement_review_shareholder_distribution_coin=config.settlement_review_shareholder_distribution_coin,
            tiers=tiers,
            movement_rules=self._movement_rules(tuple(self._active_tiers(config.id))),
            current_season=self._to_season_view(current_season) if current_season is not None else None,
        )

    @staticmethod
    def _to_tier_view(tier: CreatorLeagueTier) -> CreatorLeagueTierView:
        return CreatorLeagueTierView(
            id=tier.id,
            name=tier.name,
            slug=tier.slug,
            display_order=tier.display_order,
            club_count=tier.club_count,
            promotion_spots=tier.promotion_spots,
            relegation_spots=tier.relegation_spots,
            active=tier.active,
        )

    def _to_season_view(self, season: CreatorLeagueSeason) -> CreatorLeagueSeasonView:
        tier_views = tuple(
            CreatorLeagueSeasonTierView(
                id=season_tier.id,
                tier_id=season_tier.tier_id,
                competition_id=season_tier.competition_id,
                competition_name=season_tier.competition_name,
                tier_name=season_tier.tier_name,
                tier_order=season_tier.tier_order,
                club_ids=tuple(season_tier.club_ids_json or ()),
                round_count=season_tier.round_count,
                fixture_count=season_tier.fixture_count,
                status=season_tier.status,
                banner_title=season_tier.banner_title,
                banner_subtitle=season_tier.banner_subtitle,
            )
            for season_tier in self._season_tiers(season.id)
        )
        return CreatorLeagueSeasonView(
            id=season.id,
            season_number=season.season_number,
            name=season.name,
            status=season.status,
            start_date=season.start_date,
            end_date=season.end_date,
            match_frequency_days=season.match_frequency_days,
            season_duration_days=season.season_duration_days,
            launched_at=season.launched_at,
            paused_at=season.paused_at,
            completed_at=season.completed_at,
            tiers=tier_views,
        )

    def _movement_rules(self, tiers: tuple[CreatorLeagueTier, ...]) -> tuple[CreatorLeagueMovementRuleView, ...]:
        rules: list[CreatorLeagueMovementRuleView] = []
        for index, tier in enumerate(tiers):
            if tier.promotion_spots > 0 and index > 0:
                target = tiers[index - 1]
                rules.append(
                    CreatorLeagueMovementRuleView(
                        tier_id=tier.id,
                        tier_name=tier.name,
                        direction="promotion",
                        target_tier_id=target.id,
                        target_tier_name=target.name,
                        spots=tier.promotion_spots,
                    )
                )
            if tier.relegation_spots > 0 and index < len(tiers) - 1:
                target = tiers[index + 1]
                rules.append(
                    CreatorLeagueMovementRuleView(
                        tier_id=tier.id,
                        tier_name=tier.name,
                        direction="relegation",
                        target_tier_id=target.id,
                        target_tier_name=target.name,
                        spots=tier.relegation_spots,
                    )
                )
        return tuple(rules)

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "division"


__all__ = ["CreatorLeagueError", "CreatorLeagueService"]
