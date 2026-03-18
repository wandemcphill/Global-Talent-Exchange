from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.common.enums.competition_type import CompetitionType
from backend.app.common.schemas.competition import CompetitionScheduleRequest
from backend.app.competition_engine.scheduler import CompetitionScheduler
from backend.app.hosted_competition_engine.service import HostedCompetitionService
from backend.app.models.calendar_engine import CalendarEvent, CalendarSeason, CompetitionLifecycleRun
from backend.app.models.hosted_competition import UserHostedCompetition
from backend.app.models.national_team import NationalTeamCompetition
from backend.app.models.user import User
from backend.app.national_team_engine.service import NationalTeamEngineService
from backend.app.story_feed_engine.service import StoryFeedService


class CalendarEngineError(ValueError):
    pass


@dataclass(slots=True)
class CalendarEngineService:
    session: Session

    def seed_defaults(self) -> None:
        existing = self.session.scalar(select(CalendarSeason).where(CalendarSeason.season_key == "gtex-2026"))
        if existing is None:
            self.session.add(
                CalendarSeason(
                    season_key="gtex-2026",
                    title="GTEX 2026 Season",
                    starts_on=date(2026, 1, 1),
                    ends_on=date(2026, 12, 31),
                    status="live",
                    metadata_json={"default": True},
                    active=True,
                )
            )
        self.session.flush()

    def list_seasons(self, *, active_only: bool = False) -> list[CalendarSeason]:
        stmt = select(CalendarSeason)
        if active_only:
            stmt = stmt.where(CalendarSeason.active.is_(True))
        stmt = stmt.order_by(CalendarSeason.starts_on.asc())
        return list(self.session.scalars(stmt).all())

    def create_season(self, *, payload, actor: User) -> CalendarSeason:
        if payload.ends_on < payload.starts_on:
            raise CalendarEngineError("Season end date cannot be earlier than start date.")
        season = CalendarSeason(
            season_key=payload.season_key.strip().lower(),
            title=payload.title.strip(),
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            status=payload.status.strip().lower(),
            metadata_json=dict(payload.metadata_json),
            created_by_user_id=actor.id,
            active=True,
        )
        self.session.add(season)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise CalendarEngineError("Season key already exists.") from exc
        return season

    def create_event(self, *, payload, actor: User) -> CalendarEvent:
        if payload.ends_on < payload.starts_on:
            raise CalendarEngineError("Event end date cannot be earlier than start date.")
        event = CalendarEvent(
            season_id=payload.season_id,
            event_key=payload.event_key.strip().lower(),
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            source_type=payload.source_type.strip().lower(),
            source_id=payload.source_id,
            family=payload.family.strip().lower(),
            age_band=payload.age_band.strip().lower(),
            starts_on=payload.starts_on,
            ends_on=payload.ends_on,
            exclusive_windows=payload.exclusive_windows,
            pause_other_gtx_competitions=payload.pause_other_gtx_competitions,
            visibility=payload.visibility.strip().lower(),
            status=payload.status.strip().lower(),
            metadata_json=dict(payload.metadata_json),
            created_by_user_id=actor.id,
        )
        self.session.add(event)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise CalendarEngineError("Calendar event key already exists.") from exc
        return event

    def list_events(
        self,
        *,
        active_only: bool = False,
        as_of: date | None = None,
        source_type: str | None = None,
        source_id: str | None = None,
        family: str | None = None,
        visibility: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[CalendarEvent]:
        stmt = select(CalendarEvent)
        if active_only:
            stmt = stmt.where(CalendarEvent.status.in_(("scheduled", "live")))
        if as_of is not None:
            stmt = stmt.where(CalendarEvent.starts_on <= as_of, CalendarEvent.ends_on >= as_of)
        if source_type:
            stmt = stmt.where(CalendarEvent.source_type == source_type.strip().lower())
        if source_id:
            stmt = stmt.where(CalendarEvent.source_id == source_id)
        if family:
            stmt = stmt.where(CalendarEvent.family == family.strip().lower())
        if visibility:
            stmt = stmt.where(CalendarEvent.visibility == visibility.strip().lower())
        if status:
            stmt = stmt.where(CalendarEvent.status == status.strip().lower())
        stmt = stmt.order_by(CalendarEvent.starts_on.asc(), CalendarEvent.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def list_lifecycle_runs(self, *, limit: int = 50) -> list[CompetitionLifecycleRun]:
        stmt = select(CompetitionLifecycleRun).order_by(CompetitionLifecycleRun.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def current_pause_status(self, *, as_of: date | None = None):
        as_of = as_of or date.today()
        events = self.list_events(active_only=True, as_of=as_of)
        blockers = [event for event in events if event.pause_other_gtx_competitions]
        blocked_families: set[str] = set()
        for event in blockers:
            blocked_families.update(event.metadata_json.get("pause_families", ["league", "champions", "hosted"]))
        active_event_keys = [event.event_key for event in blockers]
        if not blockers:
            summary = "No GTEX-wide pause windows are active. The calendar is open for normal competition traffic."
        else:
            summary = f"{len(blockers)} pause window(s) active. Blocked families: {', '.join(sorted(blocked_families))}."
        return {
            "as_of": as_of,
            "blocked_competition_families": sorted(blocked_families),
            "active_event_keys": active_event_keys,
            "summary": summary,
        }

    def _season_for(self, day: date) -> CalendarSeason | None:
        return self.session.scalar(select(CalendarSeason).where(CalendarSeason.starts_on <= day, CalendarSeason.ends_on >= day, CalendarSeason.active.is_(True)).order_by(CalendarSeason.starts_on.asc()))

    def _upsert_source_event(
        self,
        *,
        event_key: str,
        title: str,
        description: str | None,
        source_type: str,
        source_id: str,
        starts_on: date,
        ends_on: date,
        family: str,
        age_band: str,
        exclusive_windows: bool,
        pause_other_gtx_competitions: bool,
        actor: User | None,
        metadata_json: dict,
    ) -> CalendarEvent:
        event = self.session.scalar(select(CalendarEvent).where(CalendarEvent.event_key == event_key))
        season = self._season_for(starts_on)
        if event is None:
            event = CalendarEvent(
                season_id=season.id if season else None,
                event_key=event_key,
                title=title,
                description=description,
                source_type=source_type,
                source_id=source_id,
                family=family,
                age_band=age_band,
                starts_on=starts_on,
                ends_on=ends_on,
                exclusive_windows=exclusive_windows,
                pause_other_gtx_competitions=pause_other_gtx_competitions,
                visibility="public",
                status="scheduled",
                metadata_json=metadata_json,
                created_by_user_id=actor.id if actor is not None else None,
            )
            self.session.add(event)
        else:
            event.season_id = season.id if season else None
            event.title = title
            event.description = description
            event.starts_on = starts_on
            event.ends_on = ends_on
            event.exclusive_windows = exclusive_windows
            event.pause_other_gtx_competitions = pause_other_gtx_competitions
            event.metadata_json = metadata_json
        self.session.flush()
        return event

    def upsert_sourced_event(
        self,
        *,
        event_key: str,
        title: str,
        description: str | None,
        source_type: str,
        source_id: str,
        starts_on: date,
        ends_on: date,
        family: str,
        age_band: str = "senior",
        visibility: str = "public",
        status: str = "live",
        exclusive_windows: bool = False,
        pause_other_gtx_competitions: bool = False,
        metadata_json: dict | None = None,
        actor: User | None = None,
    ) -> CalendarEvent:
        if ends_on < starts_on:
            raise CalendarEngineError("Event end date cannot be earlier than start date.")
        event = self._upsert_source_event(
            event_key=event_key.strip().lower(),
            title=title.strip(),
            description=description.strip() if description else None,
            source_type=source_type.strip().lower(),
            source_id=source_id,
            starts_on=starts_on,
            ends_on=ends_on,
            family=family.strip().lower(),
            age_band=age_band.strip().lower(),
            exclusive_windows=exclusive_windows,
            pause_other_gtx_competitions=pause_other_gtx_competitions,
            actor=actor,
            metadata_json=dict(metadata_json or {}),
        )
        event.visibility = visibility.strip().lower()
        event.status = status.strip().lower()
        if actor is not None and event.created_by_user_id is None:
            event.created_by_user_id = actor.id
        self.session.flush()
        return event

    def launch_hosted_competition(self, *, competition_id: str, actor: User, payload) -> tuple[CalendarEvent, CompetitionLifecycleRun]:
        hosted = HostedCompetitionService(self.session).get_competition(competition_id)
        if hosted is None:
            raise CalendarEngineError("Hosted competition was not found.")
        starts_on = payload.starts_on or (hosted.starts_at.date() if hosted.starts_at else date.today())
        current_participants = len(HostedCompetitionService(self.session).participants_for_competition(hosted.id))
        if current_participants < 2:
            raise CalendarEngineError("Hosted competition needs at least two participants before launch.")
        format_name = self._infer_hosted_format(hosted)
        total_rounds, total_matches, requested_dates, competition_type = self._build_schedule_shape(format_name, current_participants, starts_on)
        event = self._upsert_source_event(
            event_key=f"hosted:{hosted.slug}",
            title=payload.override_title or hosted.title,
            description=hosted.description,
            source_type="hosted_competition",
            source_id=hosted.id,
            starts_on=requested_dates[0],
            ends_on=requested_dates[-1],
            family=payload.preferred_family.strip().lower(),
            age_band="senior",
            exclusive_windows=False,
            pause_other_gtx_competitions=False,
            actor=actor,
            metadata_json={"participants": current_participants, "template_id": hosted.template_id, "slug": hosted.slug},
        )
        plan = CompetitionScheduler().build_schedule(
            (
                CompetitionScheduleRequest(
                    competition_id=hosted.id,
                    competition_type=competition_type,
                    requested_dates=tuple(requested_dates),
                    priority=100,
                    required_windows=1,
                    requires_exclusive_windows=False,
                ),
            )
        )
        run = CompetitionLifecycleRun(
            event_id=event.id,
            source_type="hosted_competition",
            source_id=hosted.id,
            source_title=hosted.title,
            competition_format=format_name,
            status="scheduled",
            stage="fixtures_generated",
            generated_rounds=total_rounds,
            generated_matches=total_matches,
            scheduled_dates_json=[item.isoformat() for item in requested_dates],
            summary_text=f"{hosted.title} scheduled over {len(requested_dates)} day(s) with {total_matches} match slot(s).",
            metadata_json={
                "participants": current_participants,
                "scheduler_assignments": len(plan.assignments),
                "paused_competitions": [item.competition_id for item in plan.paused_competitions],
            },
            launched_by_user_id=actor.id,
        )
        self.session.add(run)
        hosted.status = "live"
        event.status = "live"
        self.session.flush()
        StoryFeedService(self.session).publish(
            story_type="hosted_competition_launch",
            title=f"{hosted.title} is live",
            body=f"{hosted.title} launched with {current_participants} participant(s) across {total_rounds} round(s).",
            subject_type="hosted_competition",
            subject_id=hosted.id,
            metadata_json={"scheduled_dates": run.scheduled_dates_json, "matches": total_matches},
            published_by_user_id=actor.id,
            featured=current_participants >= 8,
        )
        return event, run

    def launch_national_competition(self, *, competition_id: str, actor: User, payload) -> tuple[CalendarEvent, CompetitionLifecycleRun]:
        competition = NationalTeamEngineService(self.session).get_competition(competition_id)
        if competition is None:
            raise CalendarEngineError("National team competition was not found.")
        starts_on = payload.starts_on or date.today()
        entries = competition.entries or []
        if len(entries) < 2:
            raise CalendarEngineError("National team competition needs at least two entries before launch.")
        event_key = f"national:{competition.key}"
        exclusive_windows = payload.exclusive_windows
        if exclusive_windows is None:
            exclusive_windows = competition.region_type == "global" and competition.age_band == "senior"
        pause_other = payload.pause_other_gtx_competitions
        if pause_other is None:
            pause_other = bool(exclusive_windows)
        total_rounds, total_matches, requested_dates, competition_type = self._build_schedule_shape(
            competition.format_type,
            len(entries),
            starts_on,
            national=True,
            exclusive=bool(exclusive_windows),
        )
        event = self._upsert_source_event(
            event_key=event_key,
            title=payload.override_title or competition.title,
            description=competition.notes,
            source_type="national_team_competition",
            source_id=competition.id,
            starts_on=requested_dates[0],
            ends_on=requested_dates[-1],
            family="national_team",
            age_band=competition.age_band,
            exclusive_windows=bool(exclusive_windows),
            pause_other_gtx_competitions=bool(pause_other),
            actor=actor,
            metadata_json={
                "competition_key": competition.key,
                "entries": len(entries),
                "pause_families": ["league", "champions", "hosted"] if pause_other else [],
            },
        )
        plan = CompetitionScheduler().build_schedule(
            (
                CompetitionScheduleRequest(
                    competition_id=competition.id,
                    competition_type=competition_type,
                    requested_dates=tuple(requested_dates),
                    priority=10 if exclusive_windows else 80,
                    required_windows=1,
                    requires_exclusive_windows=bool(exclusive_windows),
                ),
            )
        )
        run = CompetitionLifecycleRun(
            event_id=event.id,
            source_type="national_team_competition",
            source_id=competition.id,
            source_title=competition.title,
            competition_format=competition.format_type,
            status="scheduled",
            stage="fixtures_generated",
            generated_rounds=total_rounds,
            generated_matches=total_matches,
            scheduled_dates_json=[item.isoformat() for item in requested_dates],
            summary_text=f"{competition.title} scheduled for {len(entries)} country entries.",
            metadata_json={
                "entries": len(entries),
                "scheduler_assignments": len(plan.assignments),
                "exclusive_windows": bool(exclusive_windows),
            },
            launched_by_user_id=actor.id,
        )
        self.session.add(run)
        competition.status = "live"
        event.status = "live"
        self.session.flush()
        StoryFeedService(self.session).publish(
            story_type="national_team_schedule",
            title=f"{competition.title} fixtures set",
            body=f"{competition.title} now has its first lifecycle run and calendar window assignments.",
            subject_type="national_team_competition",
            subject_id=competition.id,
            metadata_json={"scheduled_dates": run.scheduled_dates_json, "exclusive": bool(exclusive_windows)},
            published_by_user_id=actor.id,
            featured=bool(exclusive_windows),
        )
        return event, run

    def dashboard(self):
        today = date.today()
        return {
            "seasons": self.list_seasons(active_only=True),
            "active_events": self.list_events(active_only=True, as_of=today),
            "active_pause_status": self.current_pause_status(as_of=today),
            "recent_lifecycle_runs": self.list_lifecycle_runs(limit=20),
        }

    @staticmethod
    def _infer_hosted_format(hosted: UserHostedCompetition) -> str:
        metadata = hosted.metadata_json or {}
        return str(metadata.get("cup_or_league") or metadata.get("format") or ("league" if "league" in hosted.slug else "cup")).strip().lower()

    @staticmethod
    def _build_schedule_shape(format_name: str, participant_count: int, starts_on: date, *, national: bool = False, exclusive: bool = False):
        format_name = format_name.strip().lower()
        if format_name == "league":
            rounds = max(1, (participant_count - 1) * 2)
            matches = max(1, participant_count * (participant_count - 1))
            requested_dates = [starts_on + timedelta(days=7 * index) for index in range(min(rounds, 12))]
            competition_type = CompetitionType.LEAGUE
        else:
            bracket_size = 1
            while bracket_size < participant_count:
                bracket_size *= 2
            rounds = int(math.log2(bracket_size))
            matches = max(1, bracket_size - 1)
            spacing_days = 3 if national else 2
            requested_dates = [starts_on + timedelta(days=spacing_days * index) for index in range(max(1, rounds))]
            if national and exclusive:
                competition_type = CompetitionType.WORLD_SUPER_CUP
            else:
                competition_type = CompetitionType.FAST_CUP
        return rounds, matches, requested_dates, competition_type
