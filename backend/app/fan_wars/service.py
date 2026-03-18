from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
import math
import re

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.common.enums.competition_start_mode import CompetitionStartMode
from backend.app.common.enums.competition_status import CompetitionStatus
from backend.app.common.enums.competition_visibility import CompetitionVisibility
from backend.app.common.enums.fixture_window import FixtureWindow
from backend.app.fan_wars.schemas import (
    CreatorCountryAssignmentRequest,
    CreatorCountryAssignmentView,
    FanWarDashboardView,
    FanWarLeaderboardEntryView,
    FanWarLeaderboardView,
    FanWarPeriodType,
    FanWarPointRecordRequest,
    FanWarPointView,
    FanWarProfileType,
    FanWarProfileUpsertRequest,
    FanWarProfileView,
    FanWarSourceBreakdownView,
    FanWarSummaryView,
    NationsCupCreateRequest,
    NationsCupEntryView,
    NationsCupGroupView,
    NationsCupOverviewView,
    NationsCupRecordView,
    PresentationBannerView,
    RivalryLeaderboardEntryView,
    RivalryLeaderboardView,
)
from backend.app.models.base import generate_uuid, utcnow
from backend.app.models.club_profile import ClubProfile
from backend.app.models.competition import Competition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_rule_set import CompetitionRuleSet
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.creator_provisioning import CreatorSquad
from backend.app.models.fan_war import (
    CountryCreatorAssignment,
    FanWarPoint,
    FanWarProfile,
    FanbaseRanking,
    NationsCupEntry,
    NationsCupFanMetric,
)
from backend.app.models.user import User
from backend.app.models.user_region import UserRegionProfile
from backend.app.services.competition_lifecycle_service import CompetitionLifecycleService


class FanWarError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(slots=True)
class FanWarService:
    session: Session
    lifecycle_service: CompetitionLifecycleService = field(init=False)
    NATIONS_CUP_SOURCE_TYPE = "gtex_nations_cup"
    PROFILE_TYPES: tuple[FanWarProfileType, ...] = ("club", "country", "creator")
    BOARD_FILTERS = {"global": None, "club": "club", "country": "country", "creator": "creator"}
    SOURCE_METRIC_FIELDS = {
        "watch_match": ("watch_actions", "watch_points"),
        "gift": ("gift_actions", "gift_points"),
        "prediction": ("prediction_actions", "prediction_points"),
        "tournament_participation": ("tournament_actions", "tournament_points"),
        "creator_support": ("creator_support_actions", "creator_support_points"),
        "club_support": ("club_support_actions", "club_support_points"),
    }
    DEFAULT_SCORING = {
        "watch_match": {"base_points": 4, "unit_points": 4, "max_units": 8, "spend_scale_minor": 0, "spend_exponent": 0.0, "spend_multiplier": 0.0, "max_spend_points": 0, "event_cap": 40},
        "gift": {"base_points": 6, "unit_points": 0, "max_units": 1, "spend_scale_minor": 100, "spend_exponent": 0.5, "spend_multiplier": 2.5, "max_spend_points": 30, "event_cap": 36},
        "prediction": {"base_points": 12, "unit_points": 6, "max_units": 3, "spend_scale_minor": 0, "spend_exponent": 0.0, "spend_multiplier": 0.0, "max_spend_points": 0, "event_cap": 30},
        "tournament_participation": {"base_points": 15, "unit_points": 8, "max_units": 3, "spend_scale_minor": 0, "spend_exponent": 0.0, "spend_multiplier": 0.0, "max_spend_points": 0, "event_cap": 39},
        "creator_support": {"base_points": 8, "unit_points": 4, "max_units": 4, "spend_scale_minor": 0, "spend_exponent": 0.0, "spend_multiplier": 0.0, "max_spend_points": 0, "event_cap": 24},
        "club_support": {"base_points": 8, "unit_points": 4, "max_units": 4, "spend_scale_minor": 0, "spend_exponent": 0.0, "spend_multiplier": 0.0, "max_spend_points": 0, "event_cap": 24},
    }
    CREATOR_TIER_ORDER = {"elite": 0, "established": 1, "community": 2, "emerging": 3}

    def __post_init__(self) -> None:
        self.lifecycle_service = CompetitionLifecycleService(self.session)

    def upsert_profile(self, payload: FanWarProfileUpsertRequest) -> FanWarProfileView:
        profile = self._ensure_profile(
            profile_type=payload.profile_type,
            display_name=payload.display_name,
            club_id=payload.club_id,
            creator_profile_id=payload.creator_profile_id,
            country_code=payload.country_code,
            country_name=payload.country_name,
            tagline=payload.tagline,
            scoring_config_json=payload.scoring_config_json,
            metadata_json=payload.metadata_json,
        )
        return self._to_profile_view(profile)

    def link_rivals(self, profile_id: str, rival_profile_id: str) -> tuple[FanWarProfileView, FanWarProfileView]:
        profile = self._require_profile(profile_id)
        rival = self._require_profile(rival_profile_id)
        if profile.profile_type != rival.profile_type:
            raise FanWarError("Rival fanbases must belong to the same fanbase type.", reason="rival_type_mismatch")
        profile.rivalry_profile_ids_json = self._merged_rivals(profile.rivalry_profile_ids_json, rival.id)
        rival.rivalry_profile_ids_json = self._merged_rivals(rival.rivalry_profile_ids_json, profile.id)
        return self._to_profile_view(profile), self._to_profile_view(rival)

    def assign_creator_country(self, payload: CreatorCountryAssignmentRequest, *, actor: User | None) -> CreatorCountryAssignmentView:
        creator = self._require_creator_profile(payload.creator_profile_id)
        club = self._creator_club_for_profile(creator.id)
        represented_country_code = payload.represented_country_code.strip().upper()
        represented_country_name = (payload.represented_country_name or represented_country_code).strip()
        eligible_codes = self._eligible_country_codes_for_creator(
            creator_profile_id=creator.id,
            explicit_codes=payload.eligible_country_codes,
            represented_country_code=represented_country_code,
            allow_admin_override=payload.allow_admin_override,
        )
        if represented_country_code not in eligible_codes and not payload.allow_admin_override:
            raise FanWarError("Creator cannot represent a country outside the eligible set without an override.", reason="country_not_eligible")

        assignment = self.session.scalar(select(CountryCreatorAssignment).where(CountryCreatorAssignment.creator_profile_id == creator.id))
        if assignment is None:
            assignment = CountryCreatorAssignment(
                creator_profile_id=creator.id,
                creator_user_id=creator.user_id,
                club_id=club.id if club is not None else None,
                represented_country_code=represented_country_code,
                represented_country_name=represented_country_name,
                eligible_country_codes_json=eligible_codes,
                assignment_rule=payload.assignment_rule,
                allow_admin_override=payload.allow_admin_override,
                assigned_by_user_id=actor.id if actor is not None else None,
                effective_from=payload.effective_from or date.today(),
                metadata_json=payload.metadata_json,
            )
            self.session.add(assignment)
        else:
            assignment.club_id = club.id if club is not None else assignment.club_id
            assignment.represented_country_code = represented_country_code
            assignment.represented_country_name = represented_country_name
            assignment.eligible_country_codes_json = eligible_codes
            assignment.assignment_rule = payload.assignment_rule
            assignment.allow_admin_override = payload.allow_admin_override
            assignment.assigned_by_user_id = actor.id if actor is not None else assignment.assigned_by_user_id
            assignment.effective_from = payload.effective_from or assignment.effective_from
            assignment.metadata_json = payload.metadata_json

        self._ensure_profile(profile_type="country", display_name=represented_country_name, country_code=represented_country_code, country_name=represented_country_name, metadata_json={"assignment_creator_profile_id": creator.id})
        self.session.flush()
        return self._to_assignment_view(assignment)

    def record_points(self, payload: FanWarPointRecordRequest) -> tuple[FanWarPointView, ...]:
        profiles = self._resolve_target_profiles(payload)
        if not profiles:
            raise FanWarError("Fan war point event requires at least one target fanbase.", reason="missing_target_fanbase")

        awarded_at = self._ensure_aware(payload.awarded_at or utcnow())
        entry = self._resolve_nations_cup_entry(payload)
        created_points: list[FanWarPoint] = []
        resolved_points: list[FanWarPoint] = []
        for profile in profiles:
            existing = None
            if payload.dedupe_key:
                existing = self.session.scalar(select(FanWarPoint).where(FanWarPoint.profile_id == profile.id, FanWarPoint.dedupe_key == payload.dedupe_key))
            if existing is not None:
                resolved_points.append(existing)
                continue

            base_points, weighted_points = self._score_event(
                profile=profile,
                source_type=payload.source_type,
                engagement_units=payload.engagement_units,
                spend_amount_minor=payload.spend_amount_minor,
                quality_multiplier_bps=payload.quality_multiplier_bps,
            )
            point = FanWarPoint(
                profile_id=profile.id,
                actor_user_id=payload.actor_user_id,
                competition_id=payload.competition_id,
                match_id=payload.match_id,
                nations_cup_entry_id=entry.id if entry is not None else payload.nations_cup_entry_id,
                source_type=payload.source_type,
                source_ref=payload.source_ref,
                base_points=base_points,
                bonus_points=weighted_points - base_points,
                weighted_points=weighted_points,
                engagement_units=payload.engagement_units,
                spend_amount_minor=payload.spend_amount_minor,
                quality_multiplier_bps=payload.quality_multiplier_bps,
                awarded_at=awarded_at,
                dedupe_key=payload.dedupe_key,
                metadata_json=payload.metadata_json,
            )
            self.session.add(point)
            profile.prestige_points = int(profile.prestige_points or 0) + weighted_points
            profile.last_activity_at = awarded_at
            created_points.append(point)
            resolved_points.append(point)

        if created_points:
            self.session.flush()

        if entry is not None and created_points:
            self._apply_nations_cup_metric(
                entry=entry,
                source_type=payload.source_type,
                actor_user_id=payload.actor_user_id,
                energy_points=max(point.weighted_points for point in created_points),
                awarded_at=awarded_at,
            )

        return tuple(self._to_point_view(point) for point in resolved_points)

    def get_leaderboard(self, *, board_type: str, period_type: FanWarPeriodType, limit: int = 20, reference_date: date | None = None) -> FanWarLeaderboardView:
        normalized_board = self._normalize_board_type(board_type)
        window_start, window_end = self._window_bounds(period_type, reference_date)
        if not self._has_rankings(normalized_board, period_type, window_start):
            self.refresh_rankings(period_type=period_type, reference_date=reference_date)
        entries = self._ranking_entries(normalized_board, period_type, window_start, limit)
        return FanWarLeaderboardView(
            board_type=normalized_board,
            period_type=period_type,
            window_start=window_start,
            window_end=window_end,
            banner=self._leaderboard_banner(entries=entries, board_type=normalized_board, period_type=period_type),
            entries=tuple(entries),
        )

    def get_rivalry_leaderboard(self, *, board_type: str = "global", period_type: FanWarPeriodType = "weekly", limit: int = 20, reference_date: date | None = None) -> RivalryLeaderboardView:
        leaderboard = self.get_leaderboard(board_type=board_type, period_type=period_type, limit=500, reference_date=reference_date)
        entries = self._build_rivalry_entries(leaderboard.entries, board_type=leaderboard.board_type)[:limit]
        banner = None
        if entries:
            top = entries[0]
            leader_name = top.left_display_name if top.leader_profile_id == top.left_profile_id else top.right_display_name
            trailer_name = top.right_display_name if top.leader_profile_id == top.left_profile_id else top.left_display_name
            banner = PresentationBannerView(
                title=f"{leader_name} lead the rivalry board",
                subtitle=f"{leader_name} hold a {top.points_gap}-point edge over {trailer_name}.",
                accent_label=period_type.title(),
                highlighted_profile_id=top.leader_profile_id,
                trailing_profile_id=top.right_profile_id if top.leader_profile_id == top.left_profile_id else top.left_profile_id,
                points_delta=top.points_gap,
            )
        return RivalryLeaderboardView(board_type=leaderboard.board_type, period_type=period_type, banner=banner, entries=tuple(entries))

    def get_dashboard(self, *, profile_id: str, period_type: FanWarPeriodType = "weekly", reference_date: date | None = None) -> FanWarDashboardView:
        profile = self._require_profile(profile_id)
        window_start, window_end = self._window_bounds(period_type, reference_date)
        global_board = self.get_leaderboard(board_type="global", period_type=period_type, limit=500, reference_date=reference_date)
        category_board = self.get_leaderboard(board_type=profile.profile_type, period_type=period_type, limit=500, reference_date=reference_date)
        global_rank = next((entry.rank for entry in global_board.entries if entry.profile_id == profile_id), None)
        category_rank = next((entry.rank for entry in category_board.entries if entry.profile_id == profile_id), None)
        rivalry_entries = tuple(item for item in self.get_rivalry_leaderboard(board_type=profile.profile_type, period_type=period_type, limit=20, reference_date=reference_date).entries if profile_id in {item.left_profile_id, item.right_profile_id})
        summary = self._fan_war_summary(profile_id=profile_id, window_start=window_start, window_end=window_end, reference_date=reference_date)
        return FanWarDashboardView(
            profile=self._to_profile_view(profile),
            period_type=period_type,
            window_start=window_start,
            window_end=window_end,
            global_rank=global_rank,
            category_rank=category_rank,
            banner=self._dashboard_banner(profile=profile, rivalry_entries=rivalry_entries, global_rank=global_rank, summary=summary),
            summary=summary,
            rivalry_entries=rivalry_entries,
        )

    def refresh_rankings(self, *, period_type: FanWarPeriodType, reference_date: date | None = None) -> None:
        window_start, window_end = self._window_bounds(period_type, reference_date)
        previous_start, _previous_end = self._previous_window_bounds(period_type, window_start)
        start_at = datetime.combine(window_start, datetime.min.time(), tzinfo=UTC)
        end_at = datetime.combine(window_end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        previous_ranks = {
            board_type: {
                row.profile_id: row.rank
                for row in self.session.scalars(select(FanbaseRanking).where(FanbaseRanking.board_type == board_type, FanbaseRanking.period_type == period_type, FanbaseRanking.window_start == previous_start)).all()
            }
            for board_type in self.BOARD_FILTERS
        }
        aggregates = self.session.execute(
            select(FanWarPoint.profile_id, func.coalesce(func.sum(FanWarPoint.weighted_points), 0), func.count(FanWarPoint.id), func.count(func.distinct(FanWarPoint.actor_user_id)))
            .where(FanWarPoint.awarded_at >= start_at, FanWarPoint.awarded_at < end_at)
            .group_by(FanWarPoint.profile_id)
        ).all()
        profile_map = {profile.id: profile for profile in self.session.scalars(select(FanWarProfile).where(FanWarProfile.id.in_([row[0] for row in aggregates]))).all()}
        for board_type, type_filter in self.BOARD_FILTERS.items():
            self.session.execute(delete(FanbaseRanking).where(FanbaseRanking.board_type == board_type, FanbaseRanking.period_type == period_type, FanbaseRanking.window_start == window_start))
            ranked_rows = []
            for profile_id, points_total, event_count, unique_supporters in aggregates:
                profile = profile_map.get(profile_id)
                if profile is None or (type_filter is not None and profile.profile_type != type_filter):
                    continue
                ranked_rows.append((profile, int(points_total or 0), int(event_count or 0), int(unique_supporters or 0)))
            ranked_rows.sort(key=lambda item: (-item[1], -item[3], -item[2], item[0].display_name.lower()))
            for rank, (profile, points_total, event_count, unique_supporters) in enumerate(ranked_rows, start=1):
                self.session.add(
                    FanbaseRanking(
                        board_type=board_type,
                        period_type=period_type,
                        window_start=window_start,
                        window_end=window_end,
                        profile_id=profile.id,
                        profile_type=profile.profile_type,
                        rank=rank,
                        points_total=points_total,
                        event_count=event_count,
                        unique_supporters=unique_supporters,
                        movement=previous_ranks[board_type].get(profile.id, rank) - rank,
                        summary_json={"display_name": profile.display_name},
                        metadata_json={},
                    )
                )
        self.session.flush()

    def create_nations_cup(self, payload: NationsCupCreateRequest) -> NationsCupOverviewView:
        assignments = self._select_nations_cup_assignments(payload)
        participant_count = len(assignments)
        expected_count = payload.group_count * payload.group_size
        if participant_count != expected_count:
            raise FanWarError(f"Nations Cup requires exactly {expected_count} creators for the selected format.", reason="invalid_nations_cup_size")
        knockout_size = payload.group_count * payload.group_advance_count
        if not self._is_power_of_two(knockout_size):
            raise FanWarError("Nations Cup knockout size must resolve to a power of two.", reason="invalid_knockout_size")

        created_by_user_id = payload.created_by_user_id or assignments[0].creator_user_id
        competition = Competition(
            id=generate_uuid(),
            host_user_id=created_by_user_id,
            name=payload.title or "GTEX Nations Cup",
            description="Creator national competition",
            competition_type="nations_cup",
            source_type=self.NATIONS_CUP_SOURCE_TYPE,
            source_id=generate_uuid(),
            format=CompetitionFormat.CUP.value,
            visibility=CompetitionVisibility.PUBLIC.value,
            status=CompetitionStatus.PUBLISHED.value if payload.activate else CompetitionStatus.DRAFT.value,
            start_mode=CompetitionStartMode.SCHEDULED.value,
            scheduled_start_at=FixtureWindow.senior_windows()[0].kickoff_at(payload.start_date),
            opened_at=utcnow(),
            launched_at=None,
            stage="registration",
            currency="coin",
            entry_fee_minor=0,
            platform_fee_bps=0,
            host_fee_bps=0,
            host_creation_fee_minor=0,
            gross_pool_minor=0,
            net_prize_pool_minor=0,
            metadata_json={
                "nations_cup": True,
                "season_label": payload.season_label or str(payload.start_date.year),
                "group_count": payload.group_count,
                "group_size": payload.group_size,
                "group_advance_count": payload.group_advance_count,
                **payload.metadata_json,
            },
        )
        rule_set = CompetitionRuleSet(
            competition_id=competition.id,
            format=CompetitionFormat.CUP.value,
            min_participants=participant_count,
            max_participants=participant_count,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
            league_tie_break_order=["points", "goal_diff", "goals_for", "wins"],
            league_home_away=False,
            cup_single_elimination=True,
            cup_two_leg_tie=False,
            cup_extra_time=True,
            cup_penalties=True,
            cup_allowed_participant_sizes=[knockout_size],
            group_stage_enabled=True,
            group_count=payload.group_count,
            group_size=payload.group_size,
            group_advance_count=payload.group_advance_count,
            knockout_bracket_size=knockout_size,
        )
        self.session.add(competition)
        self.session.add(rule_set)
        self.session.flush()

        participants: list[CompetitionParticipant] = []
        entries: list[NationsCupEntry] = []
        for seed, assignment in enumerate(assignments, start=1):
            club = self._creator_club_for_profile(assignment.creator_profile_id)
            creator = self._require_creator_profile(assignment.creator_profile_id)
            if club is None:
                raise FanWarError("Creator must have a provisioned club before entering Nations Cup.", reason="creator_club_missing")
            participants.append(CompetitionParticipant(competition_id=competition.id, club_id=club.id, seed=seed, seed_locked=True, status="joined", paid_entry_fee_minor=0))
            entries.append(
                NationsCupEntry(
                    competition_id=competition.id,
                    assignment_id=assignment.id,
                    creator_profile_id=creator.id,
                    creator_user_id=creator.user_id,
                    club_id=club.id,
                    country_code=assignment.represented_country_code,
                    country_name=assignment.represented_country_name,
                    seed=seed,
                    status="qualified",
                    metadata_json={"season_label": competition.metadata_json.get("season_label")},
                )
            )
        self.session.add_all(participants)
        self.session.add_all(entries)
        self.session.flush()

        if payload.activate:
            self.lifecycle_service.launch_competition(competition)
        self._sync_nations_cup_entries(competition.id)
        return self.get_nations_cup(competition.id)

    def advance_nations_cup(self, competition_id: str, *, force: bool = False) -> NationsCupOverviewView:
        competition = self._require_nations_cup_competition(competition_id)
        self.lifecycle_service.advance_competition(competition, force=force)
        self._sync_nations_cup_entries(competition.id)
        return self.get_nations_cup(competition.id)

    def get_nations_cup(self, competition_id: str) -> NationsCupOverviewView:
        competition = self._require_nations_cup_competition(competition_id)
        self._sync_nations_cup_entries(competition.id)
        entries = self.session.scalars(select(NationsCupEntry).where(NationsCupEntry.competition_id == competition.id).order_by(NationsCupEntry.group_key.asc().nullslast(), NationsCupEntry.seed.asc(), NationsCupEntry.created_at.asc())).all()
        participants = {participant.club_id: participant for participant in self.session.scalars(select(CompetitionParticipant).where(CompetitionParticipant.competition_id == competition.id)).all()}
        creators = {creator.id: creator for creator in self.session.scalars(select(CreatorProfile).where(CreatorProfile.id.in_([entry.creator_profile_id for entry in entries]))).all()}
        clubs = {club.id: club for club in self.session.scalars(select(ClubProfile).where(ClubProfile.id.in_([entry.club_id for entry in entries]))).all()}
        entry_views = [self._to_nations_cup_entry_view(entry=entry, participant=participants.get(entry.club_id), creator=creators.get(entry.creator_profile_id), club=clubs.get(entry.club_id)) for entry in entries]
        groups_map: dict[str, list[NationsCupEntryView]] = defaultdict(list)
        for entry_view in entry_views:
            if entry_view.group_key:
                groups_map[entry_view.group_key].append(entry_view)
        groups = tuple(NationsCupGroupView(group_key=group_key, standings=tuple(sorted(items, key=lambda item: (item.group_rank or 999, item.seed)))) for group_key, items in sorted(groups_map.items()))
        rule_set = self._rule_set(competition.id)
        format_description = f"{rule_set.group_count or 0} groups of {rule_set.group_size or 0}, top {rule_set.group_advance_count or 0} advance to a {rule_set.knockout_bracket_size or 0}-team knockout"
        return NationsCupOverviewView(
            competition_id=competition.id,
            title=competition.name,
            season_label=str(competition.metadata_json.get("season_label") or competition.name),
            status=competition.status,
            stage=competition.stage,
            start_date=(competition.scheduled_start_at or utcnow()).date(),
            format_description=format_description,
            banner=self._nations_cup_banner(entry_views),
            groups=groups,
            entries=tuple(entry_views),
            records=self._nations_cup_records(entry_views),
            total_fan_energy=sum(item.fan_energy_score for item in entry_views),
        )

    def _resolve_target_profiles(self, payload: FanWarPointRecordRequest) -> list[FanWarProfile]:
        if payload.profile_ids:
            return [self._require_profile(profile_id) for profile_id in payload.profile_ids]
        categories = payload.target_categories or self._inferred_target_categories(payload)
        profiles: list[FanWarProfile] = []
        if "club" in categories and payload.club_id:
            profiles.append(self._ensure_profile(profile_type="club", club_id=payload.club_id, metadata_json={"auto_created_from": payload.source_type}))
        if "country" in categories and payload.country_code:
            profiles.append(self._ensure_profile(profile_type="country", display_name=payload.country_name, country_code=payload.country_code, country_name=payload.country_name, metadata_json={"auto_created_from": payload.source_type}))
        if "creator" in categories and payload.creator_profile_id:
            profiles.append(self._ensure_profile(profile_type="creator", creator_profile_id=payload.creator_profile_id, metadata_json={"auto_created_from": payload.source_type}))
        return profiles

    def _ensure_profile(
        self,
        *,
        profile_type: FanWarProfileType,
        display_name: str | None = None,
        club_id: str | None = None,
        creator_profile_id: str | None = None,
        country_code: str | None = None,
        country_name: str | None = None,
        tagline: str | None = None,
        scoring_config_json: dict[str, object] | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> FanWarProfile:
        entity_key, resolved_display_name, resolved_slug, resolved_club_id, resolved_creator_profile_id, resolved_country_code, resolved_country_name = self._profile_identity(
            profile_type=profile_type,
            display_name=display_name,
            club_id=club_id,
            creator_profile_id=creator_profile_id,
            country_code=country_code,
            country_name=country_name,
        )
        profile = self.session.scalar(select(FanWarProfile).where(FanWarProfile.entity_key == entity_key))
        if profile is None:
            profile = FanWarProfile(
                profile_type=profile_type,
                entity_key=entity_key,
                display_name=resolved_display_name,
                slug=self._unique_profile_slug(resolved_slug),
                club_id=resolved_club_id,
                creator_profile_id=resolved_creator_profile_id,
                country_code=resolved_country_code,
                country_name=resolved_country_name,
                tagline=tagline,
                scoring_config_json=dict(scoring_config_json or {}),
                rivalry_profile_ids_json=[],
                prestige_points=0,
                metadata_json=dict(metadata_json or {}),
            )
            self.session.add(profile)
            self.session.flush()
            return profile

        profile.display_name = resolved_display_name
        profile.club_id = resolved_club_id
        profile.creator_profile_id = resolved_creator_profile_id
        profile.country_code = resolved_country_code
        profile.country_name = resolved_country_name
        if tagline is not None:
            profile.tagline = tagline
        if scoring_config_json:
            profile.scoring_config_json = dict(scoring_config_json)
        if metadata_json:
            profile.metadata_json = {**(profile.metadata_json or {}), **metadata_json}
        self.session.flush()
        return profile

    def _profile_identity(
        self,
        *,
        profile_type: FanWarProfileType,
        display_name: str | None,
        club_id: str | None,
        creator_profile_id: str | None,
        country_code: str | None,
        country_name: str | None,
    ) -> tuple[str, str, str, str | None, str | None, str | None, str | None]:
        if profile_type == "club":
            if not club_id:
                raise FanWarError("Club fanbase profile requires a club id.", reason="club_id_required")
            club = self._require_club(club_id)
            return (f"club:{club.id}", display_name or club.club_name, club.slug or self._slugify(club.club_name), club.id, None, club.country_code, None)
        if profile_type == "creator":
            if not creator_profile_id:
                raise FanWarError("Creator fanbase profile requires a creator profile id.", reason="creator_profile_id_required")
            creator = self._require_creator_profile(creator_profile_id)
            return (f"creator:{creator.id}", display_name or creator.display_name, creator.handle or self._slugify(creator.display_name), None, creator.id, None, None)
        if not country_code:
            raise FanWarError("Country fanbase profile requires a country code.", reason="country_code_required")
        normalized_code = country_code.strip().upper()
        resolved_name = (country_name or display_name or normalized_code).strip()
        return (f"country:{normalized_code}", resolved_name, self._slugify(resolved_name), None, None, normalized_code, resolved_name)

    def _score_event(
        self,
        *,
        profile: FanWarProfile,
        source_type: str,
        engagement_units: int,
        spend_amount_minor: int,
        quality_multiplier_bps: int,
    ) -> tuple[int, int]:
        rules = self._scoring_rules(profile, source_type)
        max_units = max(1, int(rules.get("max_units", engagement_units or 1)))
        capped_units = min(max(1, engagement_units), max_units)
        base_points = int(rules.get("base_points", 0)) + int(rules.get("unit_points", 0)) * capped_units
        spend_scale_minor = int(rules.get("spend_scale_minor", 0) or 0)
        spend_points = 0
        if spend_amount_minor > 0 and spend_scale_minor > 0:
            scaled_amount = spend_amount_minor / spend_scale_minor
            spend_points = int(round(math.pow(max(scaled_amount, 0.0), float(rules.get("spend_exponent", 0.0))) * float(rules.get("spend_multiplier", 0.0))))
            spend_points = min(int(rules.get("max_spend_points", spend_points)), spend_points)
        raw_points = max(0, base_points + spend_points)
        weighted_points = int(round(raw_points * (quality_multiplier_bps / 10000)))
        weighted_points = min(int(rules.get("event_cap", weighted_points)), weighted_points)
        return base_points, max(0, weighted_points)

    def _scoring_rules(self, profile: FanWarProfile, source_type: str) -> dict[str, object]:
        rules = dict(self.DEFAULT_SCORING[source_type])
        profile_overrides = (profile.scoring_config_json or {}).get(source_type)
        if isinstance(profile_overrides, dict):
            rules.update(profile_overrides)
        return rules

    def _resolve_nations_cup_entry(self, payload: FanWarPointRecordRequest) -> NationsCupEntry | None:
        if payload.nations_cup_entry_id:
            entry = self.session.get(NationsCupEntry, payload.nations_cup_entry_id)
            if entry is None:
                raise FanWarError("Nations Cup entry was not found.", reason="nations_cup_entry_not_found")
            return entry
        if not payload.competition_id:
            return None
        competition = self.session.get(Competition, payload.competition_id)
        if competition is None or competition.source_type != self.NATIONS_CUP_SOURCE_TYPE:
            return None
        stmt = select(NationsCupEntry).where(NationsCupEntry.competition_id == competition.id)
        if payload.creator_profile_id:
            stmt = stmt.where(NationsCupEntry.creator_profile_id == payload.creator_profile_id)
        elif payload.club_id:
            stmt = stmt.where(NationsCupEntry.club_id == payload.club_id)
        elif payload.country_code:
            stmt = stmt.where(NationsCupEntry.country_code == payload.country_code.strip().upper())
        else:
            return None
        return self.session.scalar(stmt)

    def _apply_nations_cup_metric(
        self,
        *,
        entry: NationsCupEntry,
        source_type: str,
        actor_user_id: str | None,
        energy_points: int,
        awarded_at: datetime,
    ) -> None:
        metric = self.session.scalar(select(NationsCupFanMetric).where(NationsCupFanMetric.competition_id == entry.competition_id, NationsCupFanMetric.entry_id == entry.id))
        if metric is None:
            metric = NationsCupFanMetric(competition_id=entry.competition_id, entry_id=entry.id, country_code=entry.country_code, creator_profile_id=entry.creator_profile_id, metadata_json={})
            self.session.add(metric)
            self.session.flush()
        action_field, point_field = self.SOURCE_METRIC_FIELDS[source_type]
        setattr(metric, action_field, int(getattr(metric, action_field) or 0) + 1)
        setattr(metric, point_field, int(getattr(metric, point_field) or 0) + energy_points)
        metric.total_energy = int(metric.total_energy or 0) + energy_points
        metric.contribution_count = int(metric.contribution_count or 0) + 1
        metric.last_event_at = awarded_at
        unique_supporters = self.session.scalar(select(func.count(func.distinct(FanWarPoint.actor_user_id))).where(FanWarPoint.nations_cup_entry_id == entry.id, FanWarPoint.actor_user_id.is_not(None)))
        metric.unique_supporter_count = int(unique_supporters or 0)
        entry.fan_energy_score = metric.total_energy
        self._apply_entry_prestige(entry)

    def _fan_war_summary(self, *, profile_id: str, window_start: date, window_end: date, reference_date: date | None) -> FanWarSummaryView:
        start_at = datetime.combine(window_start, datetime.min.time(), tzinfo=UTC)
        end_at = datetime.combine(window_end + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        totals = self.session.execute(select(func.coalesce(func.sum(FanWarPoint.weighted_points), 0), func.count(FanWarPoint.id), func.count(func.distinct(FanWarPoint.actor_user_id))).where(FanWarPoint.profile_id == profile_id, FanWarPoint.awarded_at >= start_at, FanWarPoint.awarded_at < end_at)).one()
        source_rows = self.session.execute(
            select(FanWarPoint.source_type, func.coalesce(func.sum(FanWarPoint.weighted_points), 0), func.count(FanWarPoint.id))
            .where(FanWarPoint.profile_id == profile_id, FanWarPoint.awarded_at >= start_at, FanWarPoint.awarded_at < end_at)
            .group_by(FanWarPoint.source_type)
            .order_by(func.coalesce(func.sum(FanWarPoint.weighted_points), 0).desc())
        ).all()
        recent_points = self.session.scalars(select(FanWarPoint).where(FanWarPoint.profile_id == profile_id, FanWarPoint.awarded_at >= start_at, FanWarPoint.awarded_at < end_at).order_by(FanWarPoint.awarded_at.desc(), FanWarPoint.created_at.desc()).limit(5)).all()

        ref_day = reference_date or date.today()
        current_span_end = datetime.combine(ref_day + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        current_span_start = current_span_end - timedelta(days=7)
        previous_span_start = current_span_start - timedelta(days=7)
        current_momentum = self.session.scalar(select(func.coalesce(func.sum(FanWarPoint.weighted_points), 0)).where(FanWarPoint.profile_id == profile_id, FanWarPoint.awarded_at >= current_span_start, FanWarPoint.awarded_at < current_span_end))
        previous_momentum = self.session.scalar(select(func.coalesce(func.sum(FanWarPoint.weighted_points), 0)).where(FanWarPoint.profile_id == profile_id, FanWarPoint.awarded_at >= previous_span_start, FanWarPoint.awarded_at < current_span_start))

        return FanWarSummaryView(
            total_points=int(totals[0] or 0),
            event_count=int(totals[1] or 0),
            unique_supporters=int(totals[2] or 0),
            momentum_points=int((current_momentum or 0) - (previous_momentum or 0)),
            source_breakdown=tuple(FanWarSourceBreakdownView(source_type=row[0], points=int(row[1] or 0), event_count=int(row[2] or 0)) for row in source_rows),
            recent_points=tuple(self._to_point_view(item) for item in recent_points),
        )

    def _select_nations_cup_assignments(self, payload: NationsCupCreateRequest) -> list[CountryCreatorAssignment]:
        if payload.creator_profile_ids:
            assignments = []
            seen_countries: set[str] = set()
            for creator_profile_id in payload.creator_profile_ids:
                assignment = self.session.scalar(select(CountryCreatorAssignment).where(CountryCreatorAssignment.creator_profile_id == creator_profile_id))
                if assignment is None:
                    raise FanWarError("Creator is missing a country assignment.", reason="creator_country_assignment_missing")
                if assignment.represented_country_code in seen_countries:
                    raise FanWarError("Nations Cup cannot include duplicate represented countries.", reason="duplicate_country_assignment")
                seen_countries.add(assignment.represented_country_code)
                assignments.append(assignment)
            return assignments

        candidates = list(self.session.scalars(select(CountryCreatorAssignment)).all())
        candidates.sort(key=lambda item: (self.CREATOR_TIER_ORDER.get(self._require_creator_profile(item.creator_profile_id).tier, 99), self._require_creator_profile(item.creator_profile_id).display_name.lower(), item.created_at))
        selected: list[CountryCreatorAssignment] = []
        seen_countries: set[str] = set()
        for assignment in candidates:
            if assignment.represented_country_code in seen_countries:
                continue
            selected.append(assignment)
            seen_countries.add(assignment.represented_country_code)
            if len(selected) >= payload.group_count * payload.group_size:
                break
        return selected

    def _sync_nations_cup_entries(self, competition_id: str) -> None:
        competition = self._require_nations_cup_competition(competition_id)
        entries = self.session.scalars(select(NationsCupEntry).where(NationsCupEntry.competition_id == competition.id)).all()
        if not entries:
            return
        participants = {participant.club_id: participant for participant in self.session.scalars(select(CompetitionParticipant).where(CompetitionParticipant.competition_id == competition.id)).all()}
        group_ranks = self._group_ranks(list(participants.values()))
        metric_map = {metric.entry_id: metric for metric in self.session.scalars(select(NationsCupFanMetric).where(NationsCupFanMetric.competition_id == competition.id)).all()}
        knockout_matches = self.session.scalars(select(CompetitionMatch).where(CompetitionMatch.competition_id == competition.id, CompetitionMatch.stage == "knockout")).all()
        knockout_club_ids = {club_id for match in knockout_matches for club_id in (match.home_club_id, match.away_club_id) if club_id is not None}
        champion_club_id = self._champion_club_id(knockout_matches)

        for entry in entries:
            participant = participants.get(entry.club_id)
            metric = metric_map.get(entry.id)
            entry.group_key = participant.group_key if participant is not None else entry.group_key
            entry.advanced_to_knockout = bool(participant.advanced) if participant is not None else entry.advanced_to_knockout
            entry.fan_energy_score = int(metric.total_energy) if metric is not None else int(entry.fan_energy_score or 0)
            if champion_club_id and entry.club_id == champion_club_id:
                entry.status = "champion"
            elif competition.stage == "group":
                entry.status = "group_stage"
            elif entry.club_id in knockout_club_ids or entry.advanced_to_knockout:
                entry.status = "knockout"
            else:
                entry.status = "eliminated"
            entry.record_summary_json = {"group_rank": group_ranks.get((entry.group_key or "", entry.club_id)), "competition_stage": competition.stage, "competition_status": competition.status}
            self._apply_entry_prestige(entry, participant=participant)

    def _apply_entry_prestige(self, entry: NationsCupEntry, *, participant: CompetitionParticipant | None = None) -> None:
        participant = participant or self.session.scalar(select(CompetitionParticipant).where(CompetitionParticipant.competition_id == entry.competition_id, CompetitionParticipant.club_id == entry.club_id))
        competition_points = int(participant.points or 0) if participant is not None else 0
        wins = int(participant.wins or 0) if participant is not None else 0
        goal_diff = int(participant.goal_diff or 0) if participant is not None else 0
        status_bonus = {"qualified": 0, "group_stage": 12, "knockout": 60, "eliminated": 20, "champion": 220}.get(entry.status, 0)
        performance_bonus = competition_points * 4 + wins * 10 + max(goal_diff, 0) * 2 + status_bonus
        fan_energy = int(entry.fan_energy_score or 0)
        entry.country_prestige_points = fan_energy + performance_bonus
        entry.creator_prestige_points = performance_bonus + max(0, fan_energy // 3)
        entry.fanbase_prestige_points = fan_energy + competition_points * 2

    def _group_ranks(self, participants: list[CompetitionParticipant]) -> dict[tuple[str, str], int]:
        grouped: dict[str, list[CompetitionParticipant]] = defaultdict(list)
        for participant in participants:
            grouped[participant.group_key or ""].append(participant)
        rankings: dict[tuple[str, str], int] = {}
        for group_key, items in grouped.items():
            ordered = sorted(items, key=lambda item: (-int(item.points or 0), -int(item.goal_diff or 0), -int(item.goals_for or 0), -int(item.wins or 0), int(item.seed or 9999)))
            for rank, participant in enumerate(ordered, start=1):
                rankings[(group_key, participant.club_id)] = rank
        return rankings

    def _champion_club_id(self, knockout_matches: list[CompetitionMatch]) -> str | None:
        completed = [match for match in knockout_matches if match.status == "completed" and match.winner_club_id]
        if not completed:
            return None
        latest = max(completed, key=lambda item: (item.round_number, self._ensure_aware(item.completed_at or item.updated_at or item.created_at)))
        return latest.winner_club_id

    def _rule_set(self, competition_id: str) -> CompetitionRuleSet:
        rule_set = self.session.scalar(select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id == competition_id))
        if rule_set is None:
            raise FanWarError("Competition rules were not found.", reason="competition_rules_not_found")
        return rule_set

    def _ranking_entries(self, board_type: str, period_type: FanWarPeriodType, window_start: date, limit: int) -> list[FanWarLeaderboardEntryView]:
        rankings = self.session.scalars(select(FanbaseRanking).where(FanbaseRanking.board_type == board_type, FanbaseRanking.period_type == period_type, FanbaseRanking.window_start == window_start).order_by(FanbaseRanking.rank.asc()).limit(limit)).all()
        profiles = {profile.id: profile for profile in self.session.scalars(select(FanWarProfile).where(FanWarProfile.id.in_([row.profile_id for row in rankings]))).all()}
        return [
            FanWarLeaderboardEntryView(
                rank=row.rank,
                profile_id=row.profile_id,
                profile_type=profiles[row.profile_id].profile_type,
                display_name=profiles[row.profile_id].display_name,
                club_id=profiles[row.profile_id].club_id,
                creator_profile_id=profiles[row.profile_id].creator_profile_id,
                country_code=profiles[row.profile_id].country_code,
                country_name=profiles[row.profile_id].country_name,
                points_total=row.points_total,
                event_count=row.event_count,
                unique_supporters=row.unique_supporters,
                movement=row.movement,
            )
            for row in rankings
            if row.profile_id in profiles
        ]

    def _build_rivalry_entries(self, entries: tuple[FanWarLeaderboardEntryView, ...], *, board_type: str) -> list[RivalryLeaderboardEntryView]:
        entry_map = {entry.profile_id: entry for entry in entries}
        profiles = {profile.id: profile for profile in self.session.scalars(select(FanWarProfile).where(FanWarProfile.id.in_(list(entry_map)))).all()}
        seen_pairs: set[tuple[str, str]] = set()
        rivalry_entries: list[RivalryLeaderboardEntryView] = []
        for profile_id, entry in entry_map.items():
            profile = profiles.get(profile_id)
            if profile is None:
                continue
            for rival_id in profile.rivalry_profile_ids_json or []:
                rival_entry = entry_map.get(rival_id)
                rival_profile = profiles.get(rival_id)
                if rival_entry is None or rival_profile is None:
                    continue
                if board_type != "global" and rival_profile.profile_type != board_type:
                    continue
                pair = tuple(sorted((profile_id, rival_id)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                leader_profile_id = None
                if entry.points_total > rival_entry.points_total:
                    leader_profile_id = entry.profile_id
                elif rival_entry.points_total > entry.points_total:
                    leader_profile_id = rival_entry.profile_id
                rivalry_entries.append(RivalryLeaderboardEntryView(profile_type=profile.profile_type, left_profile_id=entry.profile_id, left_display_name=entry.display_name, left_points=entry.points_total, right_profile_id=rival_entry.profile_id, right_display_name=rival_entry.display_name, right_points=rival_entry.points_total, leader_profile_id=leader_profile_id, points_gap=abs(entry.points_total - rival_entry.points_total)))
        rivalry_entries.sort(key=lambda item: (-(item.left_points + item.right_points), item.points_gap, item.left_display_name.lower(), item.right_display_name.lower()))
        return rivalry_entries

    def _leaderboard_banner(self, *, entries: list[FanWarLeaderboardEntryView], board_type: str, period_type: FanWarPeriodType) -> PresentationBannerView | None:
        if not entries:
            return None
        leader = entries[0]
        trailer = entries[1] if len(entries) > 1 else None
        gap = leader.points_total - trailer.points_total if trailer is not None else leader.points_total
        board_label = "Global" if board_type == "global" else board_type.title()
        return PresentationBannerView(title=f"{leader.display_name} top the {board_label} fan wars", subtitle=f"Current gap: {gap} points.", accent_label=period_type.title(), highlighted_profile_id=leader.profile_id, trailing_profile_id=trailer.profile_id if trailer is not None else None, points_delta=gap)

    def _dashboard_banner(self, *, profile: FanWarProfile, rivalry_entries: tuple[RivalryLeaderboardEntryView, ...], global_rank: int | None, summary: FanWarSummaryView) -> PresentationBannerView | None:
        if rivalry_entries:
            rivalry = rivalry_entries[0]
            leader_name = rivalry.left_display_name if rivalry.leader_profile_id == rivalry.left_profile_id else rivalry.right_display_name
            trailer_name = rivalry.right_display_name if rivalry.leader_profile_id == rivalry.left_profile_id else rivalry.left_display_name
            return PresentationBannerView(title=f"{leader_name} lead the rivalry", subtitle=f"{leader_name} are {rivalry.points_gap} points ahead of {trailer_name}.", accent_label=profile.profile_type.title(), highlighted_profile_id=rivalry.leader_profile_id, trailing_profile_id=rivalry.right_profile_id if rivalry.leader_profile_id == rivalry.left_profile_id else rivalry.left_profile_id, points_delta=rivalry.points_gap)
        if global_rank == 1:
            return PresentationBannerView(title=f"{profile.display_name} lead the global fan wars", subtitle=f"{summary.total_points} points banked in the active window.", accent_label="World No. 1", highlighted_profile_id=profile.id, points_delta=summary.total_points)
        return PresentationBannerView(title=f"{profile.display_name} are building momentum", subtitle=f"Momentum delta: {summary.momentum_points} points over the last seven days.", accent_label=profile.profile_type.title(), highlighted_profile_id=profile.id, points_delta=summary.momentum_points)

    def _nations_cup_banner(self, entry_views: list[NationsCupEntryView]) -> PresentationBannerView | None:
        if not entry_views:
            return None
        leader = max(entry_views, key=lambda item: (item.country_prestige_points, item.fan_energy_score, item.competition_points))
        return PresentationBannerView(title=f"{leader.country_name} set the Nations Cup pace", subtitle=f"{leader.country_name} have {leader.country_prestige_points} prestige points and {leader.fan_energy_score} fan energy.", accent_label=leader.status.replace("_", " ").title(), highlighted_profile_id=leader.id, points_delta=leader.country_prestige_points)

    def _nations_cup_records(self, entry_views: list[NationsCupEntryView]) -> tuple[NationsCupRecordView, ...]:
        if not entry_views:
            return ()
        champion = next((item for item in entry_views if item.status == "champion"), None)
        most_energy = max(entry_views, key=lambda item: item.fan_energy_score)
        most_prestige = max(entry_views, key=lambda item: item.country_prestige_points)
        return (
            NationsCupRecordView(label="Champion", value=champion.country_name if champion is not None else "TBD", entry_id=champion.id if champion is not None else None),
            NationsCupRecordView(label="Highest Fan Energy", value=f"{most_energy.country_name} ({most_energy.fan_energy_score})", entry_id=most_energy.id),
            NationsCupRecordView(label="Highest Country Prestige", value=f"{most_prestige.country_name} ({most_prestige.country_prestige_points})", entry_id=most_prestige.id),
        )

    def _to_profile_view(self, profile: FanWarProfile) -> FanWarProfileView:
        return FanWarProfileView(id=profile.id, profile_type=profile.profile_type, display_name=profile.display_name, slug=profile.slug, club_id=profile.club_id, creator_profile_id=profile.creator_profile_id, country_code=profile.country_code, country_name=profile.country_name, tagline=profile.tagline, prestige_points=int(profile.prestige_points or 0), rival_profile_ids=tuple(profile.rivalry_profile_ids_json or ()), scoring_config_json=profile.scoring_config_json or {}, metadata_json=profile.metadata_json or {})

    def _to_point_view(self, point: FanWarPoint) -> FanWarPointView:
        return FanWarPointView(id=point.id, profile_id=point.profile_id, source_type=point.source_type, source_ref=point.source_ref, competition_id=point.competition_id, match_id=point.match_id, nations_cup_entry_id=point.nations_cup_entry_id, base_points=int(point.base_points or 0), bonus_points=int(point.bonus_points or 0), weighted_points=int(point.weighted_points or 0), engagement_units=int(point.engagement_units or 0), spend_amount_minor=int(point.spend_amount_minor or 0), quality_multiplier_bps=int(point.quality_multiplier_bps or 0), awarded_at=self._ensure_aware(point.awarded_at), metadata_json=point.metadata_json or {})

    def _to_assignment_view(self, assignment: CountryCreatorAssignment) -> CreatorCountryAssignmentView:
        return CreatorCountryAssignmentView(id=assignment.id, creator_profile_id=assignment.creator_profile_id, creator_user_id=assignment.creator_user_id, club_id=assignment.club_id, represented_country_code=assignment.represented_country_code, represented_country_name=assignment.represented_country_name, eligible_country_codes=tuple(assignment.eligible_country_codes_json or ()), assignment_rule=assignment.assignment_rule, allow_admin_override=assignment.allow_admin_override, assigned_by_user_id=assignment.assigned_by_user_id, effective_from=assignment.effective_from, effective_to=assignment.effective_to, metadata_json=assignment.metadata_json or {})

    def _to_nations_cup_entry_view(self, *, entry: NationsCupEntry, participant: CompetitionParticipant | None, creator: CreatorProfile | None, club: ClubProfile | None) -> NationsCupEntryView:
        group_rank = (entry.record_summary_json or {}).get("group_rank")
        return NationsCupEntryView(
            id=entry.id,
            competition_id=entry.competition_id,
            creator_profile_id=entry.creator_profile_id,
            creator_user_id=entry.creator_user_id,
            club_id=entry.club_id,
            club_name=club.club_name if club is not None else None,
            creator_display_name=creator.display_name if creator is not None else None,
            country_code=entry.country_code,
            country_name=entry.country_name,
            seed=entry.seed,
            group_key=entry.group_key,
            status=entry.status,
            advanced_to_knockout=entry.advanced_to_knockout,
            fan_energy_score=int(entry.fan_energy_score or 0),
            country_prestige_points=int(entry.country_prestige_points or 0),
            creator_prestige_points=int(entry.creator_prestige_points or 0),
            fanbase_prestige_points=int(entry.fanbase_prestige_points or 0),
            played=int(participant.played or 0) if participant is not None else 0,
            wins=int(participant.wins or 0) if participant is not None else 0,
            draws=int(participant.draws or 0) if participant is not None else 0,
            losses=int(participant.losses or 0) if participant is not None else 0,
            goal_diff=int(participant.goal_diff or 0) if participant is not None else 0,
            competition_points=int(participant.points or 0) if participant is not None else 0,
            group_rank=int(group_rank) if isinstance(group_rank, int) else None,
            record_summary_json=entry.record_summary_json or {},
            metadata_json=entry.metadata_json or {},
        )

    def _normalize_board_type(self, board_type: str) -> str:
        normalized = board_type.strip().lower()
        if normalized not in self.BOARD_FILTERS:
            raise FanWarError("Unsupported fanbase leaderboard board type.", reason="invalid_board_type")
        return normalized

    def _window_bounds(self, period_type: FanWarPeriodType, reference_date: date | None) -> tuple[date, date]:
        ref = reference_date or date.today()
        if period_type == "weekly":
            start = ref - timedelta(days=ref.weekday())
            return start, start + timedelta(days=6)
        if period_type == "monthly":
            start = ref.replace(day=1)
            next_month = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
            return start, next_month - timedelta(days=1)
        return date(ref.year, 1, 1), date(ref.year, 12, 31)

    def _previous_window_bounds(self, period_type: FanWarPeriodType, current_start: date) -> tuple[date, date]:
        if period_type == "weekly":
            return current_start - timedelta(days=7), current_start - timedelta(days=1)
        if period_type == "monthly":
            previous_end = current_start - timedelta(days=1)
            return previous_end.replace(day=1), previous_end
        previous_year = current_start.year - 1
        return date(previous_year, 1, 1), date(previous_year, 12, 31)

    def _has_rankings(self, board_type: str, period_type: FanWarPeriodType, window_start: date) -> bool:
        count = self.session.scalar(select(func.count(FanbaseRanking.id)).where(FanbaseRanking.board_type == board_type, FanbaseRanking.period_type == period_type, FanbaseRanking.window_start == window_start))
        return bool(count)

    def _eligible_country_codes_for_creator(self, *, creator_profile_id: str, explicit_codes: tuple[str, ...], represented_country_code: str, allow_admin_override: bool) -> list[str]:
        eligible = {code.strip().upper() for code in explicit_codes if code}
        creator = self._require_creator_profile(creator_profile_id)
        squad = self.session.scalar(select(CreatorSquad).where(CreatorSquad.creator_profile_id == creator.id))
        if squad is not None:
            club = self.session.get(ClubProfile, squad.club_id)
            if club is not None and club.country_code:
                eligible.add(club.country_code.strip().upper())
        region = self.session.scalar(select(UserRegionProfile).where(UserRegionProfile.user_id == creator.user_id))
        if region is not None and region.region_code:
            eligible.add(region.region_code.strip().upper())
        if allow_admin_override:
            eligible.add(represented_country_code)
        if not eligible:
            eligible.add(represented_country_code)
        return sorted(eligible)

    def _merged_rivals(self, current_rivals: list[str] | None, rival_id: str) -> list[str]:
        merged = {item for item in current_rivals or [] if item}
        merged.add(rival_id)
        return sorted(merged)

    def _unique_profile_slug(self, base_slug: str) -> str:
        candidate = self._slugify(base_slug)
        resolved = candidate
        suffix = 2
        while self.session.scalar(select(FanWarProfile).where(FanWarProfile.slug == resolved)) is not None:
            resolved = f"{candidate}-{suffix}"
            suffix += 1
        return resolved

    def _inferred_target_categories(self, payload: FanWarPointRecordRequest) -> tuple[FanWarProfileType, ...]:
        categories: list[FanWarProfileType] = []
        if payload.club_id:
            categories.append("club")
        if payload.country_code:
            categories.append("country")
        if payload.creator_profile_id:
            categories.append("creator")
        return tuple(categories)

    def _require_profile(self, profile_id: str) -> FanWarProfile:
        profile = self.session.get(FanWarProfile, profile_id)
        if profile is None:
            raise FanWarError("Fan war profile was not found.", reason="fan_war_profile_not_found")
        return profile

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise FanWarError("Club was not found.", reason="club_not_found")
        return club

    def _require_creator_profile(self, creator_profile_id: str) -> CreatorProfile:
        creator = self.session.get(CreatorProfile, creator_profile_id)
        if creator is None:
            raise FanWarError("Creator profile was not found.", reason="creator_profile_not_found")
        return creator

    def _creator_club_for_profile(self, creator_profile_id: str) -> ClubProfile | None:
        squad = self.session.scalar(select(CreatorSquad).where(CreatorSquad.creator_profile_id == creator_profile_id))
        if squad is None:
            return None
        return self.session.get(ClubProfile, squad.club_id)

    def _require_nations_cup_competition(self, competition_id: str) -> Competition:
        competition = self.session.get(Competition, competition_id)
        if competition is None or competition.source_type != self.NATIONS_CUP_SOURCE_TYPE:
            raise FanWarError("Nations Cup competition was not found.", reason="nations_cup_not_found")
        return competition

    @staticmethod
    def _slugify(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "fanbase"

    @staticmethod
    def _ensure_aware(value: datetime | None) -> datetime:
        if value is None:
            return utcnow()
        if value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)

    @staticmethod
    def _is_power_of_two(value: int) -> bool:
        return value > 0 and value & (value - 1) == 0


__all__ = ["FanWarError", "FanWarService"]
