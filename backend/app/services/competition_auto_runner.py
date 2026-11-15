from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_start_mode import CompetitionStartMode
from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.common.enums.match_status import MatchStatus
from app.competition_engine.queue_contracts import MatchSimulationJob
from app.core.database import create_session_factory
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_entry import CompetitionEntry
from app.models.competition_match import CompetitionMatch
from app.models.competition_match_event import CompetitionMatchEvent
from app.models.competition_participant import CompetitionParticipant
from app.models.competition_rule_set import CompetitionRuleSet
from app.models.user import User
from app.match_engine.schemas import TeamTacticalPlanInput
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import TacticalStyle
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.players.performance_recorder import PlayerMatchPerformanceRecorder
from app.services.competition_lifecycle_service import CompetitionLifecycleService
from app.services.match_timeline_service import MatchTimelineService
from app.services.world_clock_service import WorldClockService

logger = logging.getLogger(__name__)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass(slots=True)
class CompetitionAutoRunner:
    session: Session
    lifecycle_service: CompetitionLifecycleService = field(init=False)
    world_clock: WorldClockService = field(init=False)
    match_service: MatchSimulationService = field(default_factory=MatchSimulationService)
    timeline_service: MatchTimelineService = field(default_factory=MatchTimelineService)
    team_factory: SyntheticSquadFactory = field(init=False)

    def __post_init__(self) -> None:
        self.lifecycle_service = CompetitionLifecycleService(self.session)
        self.world_clock = WorldClockService(self.session)
        bind = self.session.get_bind()
        session_factory = create_session_factory(bind) if bind is not None else None
        self.team_factory = SyntheticSquadFactory(
            session_factory=session_factory,
            allow_synthetic_fallback=False,
        )

    def effective_kickoff_at(self, competition: Competition, match: CompetitionMatch) -> datetime | None:
        """Determine authoritative kickoff datetime. Returns None if kickoff is unresolved."""
        if match.scheduled_at is not None:
            return _as_utc(match.scheduled_at)
        match_date = match.match_date
        if match_date is None and competition.scheduled_start_at is not None:
            match_date = _as_utc(competition.scheduled_start_at).date()
        if match_date is None:
            return None
        format_enum = CompetitionFormat(competition.format)
        window = (
            FixtureWindow(match.window)
            if match.window is not None
            else (FixtureWindow.SENIOR_1 if format_enum is CompetitionFormat.LEAGUE else FixtureWindow.FAST_CUP_OPEN)
        )
        return _as_utc(window.kickoff_at(match_date))

    def is_match_due(self, competition: Competition, match: CompetitionMatch, evaluation_time: datetime) -> bool:
        """A match is due only if its authoritative kickoff has arrived."""
        kickoff = self.effective_kickoff_at(competition, match)
        if kickoff is None:
            return False
        return kickoff <= _as_utc(evaluation_time)

    def run_until_idle(
        self,
        competition: Competition,
        *,
        simulate_scheduled_matches: bool = False,
        evaluation_time: datetime | None = None,
    ) -> Competition:
        eval_time = _as_utc(evaluation_time) or self.world_clock.now_virtual()
        for _ in range(32):
            self.session.refresh(competition)
            status = CompetitionStatus(competition.status)
            if status in {
                CompetitionStatus.COMPLETED,
                CompetitionStatus.SETTLED,
                CompetitionStatus.CANCELLED,
                CompetitionStatus.REFUNDED,
                CompetitionStatus.DISPUTED,
            }:
                break

            changed = False
            if self._should_launch(competition, now_virtual=eval_time):
                self.lifecycle_service.launch_competition(competition)
                changed = True

            matches = self._matches(competition.id)
            scheduled = [match for match in matches if match.status == MatchStatus.SCHEDULED.value]
            due = [match for match in scheduled if self.is_match_due(competition, match, eval_time)]
            if due and simulate_scheduled_matches:
                for match in due:
                    self._simulate_match(competition, match)
                changed = True
                matches = self._matches(competition.id)
                # Another worker may have completed and settled this competition
                # while this worker waited on a fixture row lock.
                self.session.refresh(competition)

            if simulate_scheduled_matches and matches and self._all_matches_complete(matches):
                if CompetitionFormat(competition.format) is CompetitionFormat.LEAGUE:
                    if CompetitionStatus(competition.status) is not CompetitionStatus.SETTLED:
                        self.lifecycle_service.finalize_competition(
                            competition,
                            settle=True,
                        )
                        changed = True
                else:
                    previous_status = competition.status
                    previous_match_count = len(matches)
                    self.lifecycle_service.advance_competition(
                        competition,
                        force=False,
                    )
                    matches = self._matches(competition.id)
                    if competition.status != previous_status or len(matches) != previous_match_count:
                        changed = True
                    if matches and self._all_matches_complete(matches):
                        status = CompetitionStatus(competition.status)
                        if status is not CompetitionStatus.SETTLED:
                            self.lifecycle_service.finalize_competition(
                                competition,
                                settle=True,
                            )
                            changed = True

            if not changed:
                break

        return competition

    def _should_launch(self, competition: Competition, now_virtual: datetime | None = None) -> bool:
        status = CompetitionStatus(competition.status)
        if status is CompetitionStatus.SEEDED:
            return True
        if status not in {
            CompetitionStatus.OPEN,
            CompetitionStatus.OPEN_FOR_JOIN,
            CompetitionStatus.PUBLISHED,
        }:
            return False

        scheduled_start = _as_utc(competition.scheduled_start_at)
        now = _as_utc(now_virtual) or self.world_clock.now_virtual()
        if scheduled_start is not None and scheduled_start > now:
            return False

        rule_set = self._rule_set(competition.id)
        participant_count = self._participant_count(competition.id)
        if participant_count < rule_set.min_participants:
            return False

        capacity = max(rule_set.max_participants, rule_set.min_participants)
        start_mode = CompetitionStartMode(competition.start_mode)
        if start_mode is CompetitionStartMode.WHEN_FULL:
            return participant_count >= capacity
        if start_mode is CompetitionStartMode.SCHEDULED:
            return True

        # Manual-after-min competitions still need a non-admin path to start.
        # Auto-running once the lobby is full keeps the user-hosted flow usable.
        return participant_count >= capacity

    def _simulate_match(
        self,
        competition: Competition,
        match: CompetitionMatch,
    ) -> CompetitionMatch:
        if match.status == MatchStatus.COMPLETED.value:
            return match

        # Serialize duplicate workers on the canonical fixture row. On PostgreSQL
        # the lock is held through result/event/standing writes and the caller's
        # transaction commit, so a competing worker re-reads the terminal status.
        locked_match = self.session.scalar(
            select(CompetitionMatch)
            .where(CompetitionMatch.id == match.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if locked_match is None:
            raise ValueError(f"Canonical fixture {match.id} disappeared before execution.")
        if locked_match.status == MatchStatus.COMPLETED.value:
            return locked_match
        if locked_match.status not in {
            MatchStatus.SCHEDULED.value,
            MatchStatus.IN_PROGRESS.value,
        }:
            raise ValueError(f"Canonical fixture {match.id} is {locked_match.status} and cannot be simulated.")
        match = locked_match

        job = self._simulation_job(competition, match)
        request = self.team_factory.build_request(job, session=self.session)
        request = self._apply_owner_pre_match_tactics(request, match)
        self._capture_institutional_match_context(match, competition, request)
        replay_payload = self.match_service.build_replay_payload(request)
        self._store_match_viewer_payload(match, replay_payload)
        self._store_match_events(match, replay_payload)
        completed = self.lifecycle_service.complete_match(
            match=match,
            home_score=replay_payload.summary.home_score,
            away_score=replay_payload.summary.away_score,
            decided_by_penalties=replay_payload.summary.decided_by_penalties,
            winner_club_id=replay_payload.summary.winner_team_id,
        )
        # Recorded *after* settlement so the performances carry the match's real
        # completion timestamp, which is what form windows are ordered by.
        self._store_match_performances(completed, replay_payload)
        try:
            from app.owner_console.canonical_match_projection import project_completed_canonical_match

            # The adapter owns per-club savepoints; this outer savepoint also
            # contains failures during canonical source-event creation/flush.
            with self.session.begin_nested():
                project_completed_canonical_match(self.session, completed.id)
        except Exception:
            logger.exception(
                "canonical_match.institutional_projection_deferred match_id=%s",
                completed.id,
            )
        return completed

    @staticmethod
    def _apply_owner_pre_match_tactics(request, match):
        """Apply validated owner choices saved against this canonical fixture ID."""
        metadata = dict(match.metadata_json or {})
        saved = dict(metadata.get("owner_pre_match_tactics") or {})
        if not saved:
            return request

        def apply(team):
            config = saved.get(team.team_id)
            if not isinstance(config, dict):
                return team
            mentality = str(config.get("mentality") or "").strip().lower()
            if mentality not in {"defensive", "balanced", "attacking"}:
                return team
            style = TacticalStyle(mentality)
            tuning = {
                "defensive": {
                    "pressing": 38,
                    "tempo": 42,
                    "aggression": 35,
                    "defensive_line": 32,
                    "width": 42,
                },
                "balanced": {
                    "pressing": 55,
                    "tempo": 55,
                    "aggression": 50,
                    "defensive_line": 50,
                    "width": 50,
                },
                "attacking": {
                    "pressing": 72,
                    "tempo": 76,
                    "aggression": 68,
                    "defensive_line": 68,
                    "width": 66,
                },
            }[mentality]
            plan_data = team.tactics.model_dump()
            plan_data.update(tuning)
            plan_data["style"] = style
            plan_data["mentality"] = style
            updated_team = team.model_copy(update={"tactics": TeamTacticalPlanInput.model_validate(plan_data)})
            return updated_team

        return request.model_copy(
            update={
                "home_team": apply(request.home_team),
                "away_team": apply(request.away_team),
            }
        )

    def _capture_institutional_match_context(self, match: CompetitionMatch, competition: Competition, request) -> None:
        """Capture stable manager identity and home/away atmosphere before kickoff.

        This context is presentation and institutional metadata only. It is not
        supplied to the simulator and cannot change player ability or the result.
        """
        from datetime import datetime, timezone

        from app.owner_console import living_institution
        from app.owner_console.models import OwnerClubState
        from app.models.manager_market import ManagerCatalogEntry, ManagerHolding, ManagerTeamAssignment
        from app.models.manager_marketplace import ManagerContract, ManagerContractStatus, ManagerProfile

        club_ids = {str(match.home_club_id), str(match.away_club_id)}
        states = {
            str(row.club_id): row
            for row in self.session.scalars(select(OwnerClubState).where(OwnerClubState.club_id.in_(club_ids))).all()
        }
        teams = {"home": request.home_team, "away": request.away_team}
        context: dict[str, object] = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "competition_id": str(competition.id),
            "competition_name": str(competition.name),
            "round_number": int(match.round_number),
            "stage": str(match.stage or ""),
            "requires_winner": bool(match.requires_winner),
        }
        is_decider = bool(
            match.requires_winner
            or str(match.stage or "").lower() in {"knockout", "final", "semi_final", "quarter_final"}
            or str(getattr(competition, "format", "")).lower() in {"cup", "knockout"}
        )

        for side_key, club_id, opponent_id in (
            ("home", str(match.home_club_id), str(match.away_club_id)),
            ("away", str(match.away_club_id), str(match.home_club_id)),
        ):
            state = states.get(club_id)
            team = teams[side_key]
            manager: dict[str, object] = dict(getattr(team, "manager_profile", None) or {})
            manager_name = str(manager.get("display_name") or manager.get("name") or manager.get("manager_name") or "")
            manager_id = str(manager.get("manager_id") or manager.get("id") or "")
            club = self.session.get(ClubProfile, club_id)
            owner_user_id = str(club.owner_user_id) if club is not None else ""

            manager_source = ""
            if owner_user_id:
                contract = self.session.scalar(
                    select(ManagerContract).where(
                        ManagerContract.club_user_id == owner_user_id,
                        ManagerContract.status == ManagerContractStatus.ACTIVE,
                    )
                )
                if contract is not None:
                    manager_profile = self.session.scalar(
                        select(ManagerProfile).where(ManagerProfile.manager_id == contract.manager_id)
                    )
                    if manager_profile is not None:
                        manager_id = str(manager_profile.manager_id or manager_id)
                        manager_name = str(manager_profile.name or manager_name or "First-Team Manager")
                        manager["preferred_style"] = manager_profile.preferred_style
                        manager_source = "manager_marketplace"

                if not manager_id:
                    assignment = self.session.scalar(
                        select(ManagerTeamAssignment).where(ManagerTeamAssignment.user_id == owner_user_id)
                    )
                    if assignment is not None and assignment.main_manager_asset_id:
                        holding = self.session.scalar(
                            select(ManagerHolding).where(ManagerHolding.asset_id == assignment.main_manager_asset_id)
                        )
                        if holding is not None:
                            catalog = self.session.scalar(
                                select(ManagerCatalogEntry).where(ManagerCatalogEntry.manager_id == holding.manager_id)
                            )
                            if catalog is not None:
                                manager_id = str(catalog.manager_id)
                                manager_name = str(catalog.display_name)
                                manager["mentality"] = catalog.mentality
                                manager_source = "manager_market"

            if manager_id:
                manager["_manager_source"] = manager_source
                manager["id"] = manager_id
                manager["manager_id"] = manager_id
            if manager_name:
                manager["name"] = manager_name
            supplied = bool(manager_id or manager_name)

            if state is not None:
                supporter_profile, segments = living_institution.ensure_club_institutional_ecosystem(
                    self.session, state
                )
                opponent_team = teams["away" if side_key == "home" else "home"]
                atmosphere = living_institution.compute_matchday_atmosphere(
                    self.session,
                    state,
                    profile=supporter_profile,
                    segments=segments,
                    opponent_club_id=opponent_id,
                    opponent_name=str(getattr(opponent_team, "team_name", opponent_id)),
                    is_knockout_or_decider=is_decider,
                )
                context[side_key] = {
                    "club_id": club_id,
                    "world_day": max(1, int(state.world_day or 1)),
                    "manager": manager if supplied else {},
                    "manager_snapshot_supplied": supplied,
                    "atmosphere": atmosphere,
                }
            else:
                context[side_key] = {
                    "club_id": club_id,
                    "manager": manager if supplied else {},
                    "manager_snapshot_supplied": supplied,
                }

        metadata = dict(match.metadata_json or {})
        if not isinstance(metadata.get("institutional_match_context"), dict):
            metadata["institutional_match_context"] = context
            match.metadata_json = metadata

    def _store_match_performances(self, match: CompetitionMatch, replay_payload) -> None:
        """Persist per-player ratings so this match can reach form and valuation.

        This is the link that did not previously exist: the match engine rated every
        player and then discarded the result. Only competition matches reach this
        path, which is exactly the eligibility boundary the economy requires.

        A failure to record performance must never fail an otherwise valid match
        settlement, so this is contained: the fixture result is authoritative, the
        derived economic signal is best-effort.
        """
        summary = getattr(replay_payload, "summary", None)
        player_stats = getattr(summary, "player_stats", None) if summary is not None else None
        if not player_stats:
            return
        try:
            PlayerMatchPerformanceRecorder(self.session).record_match(
                match=match,
                player_stats=player_stats,
            )
        except SQLAlchemyError:
            logger.exception(
                "Failed to record player performances for match %s in competition %s",
                match.id,
                match.competition_id,
            )

    def _simulation_job(
        self,
        competition: Competition,
        match: CompetitionMatch,
    ) -> MatchSimulationJob:
        format_enum = CompetitionFormat(competition.format)
        window = (
            FixtureWindow(match.window)
            if match.window is not None
            else (FixtureWindow.SENIOR_1 if format_enum is CompetitionFormat.LEAGUE else FixtureWindow.FAST_CUP_OPEN)
        )
        match_date = (
            match.match_date
            or (match.scheduled_at.astimezone(timezone.utc).date() if match.scheduled_at is not None else None)
            or (
                competition.scheduled_start_at.astimezone(timezone.utc).date()
                if competition.scheduled_start_at is not None
                else None
            )
            or self.world_clock.now_virtual_date()
        )
        scheduled_kickoff_at = (
            match.scheduled_at or self.effective_kickoff_at(competition, match) or window.kickoff_at(match_date)
        )
        owner_tactics = dict((match.metadata_json or {}).get("owner_pre_match_tactics") or {})
        home_owner_tactics = owner_tactics.get(match.home_club_id, {})
        away_owner_tactics = owner_tactics.get(match.away_club_id, {})
        return MatchSimulationJob(
            fixture_id=match.id,
            competition_id=competition.id,
            competition_type=(
                CompetitionType.LEAGUE if format_enum is CompetitionFormat.LEAGUE else CompetitionType.FAST_CUP
            ),
            match_date=match_date,
            window=window,
            slot_sequence=max(match.slot_sequence or 1, 1),
            competition_name=competition.name,
            stage_name=f"{match.stage.title()} Round {match.round_number}",
            round_number=max(match.round_number or 1, 1),
            scheduled_kickoff_at=scheduled_kickoff_at,
            simulation_seed=self._simulation_seed(match.id),
            home_club_id=match.home_club_id,
            home_club_name=self._club_name(competition.id, match.home_club_id),
            home_lineup_mode=(
                home_owner_tactics.get("lineup_mode", "strongest")
                if isinstance(home_owner_tactics, dict)
                else "strongest"
            ),
            away_club_id=match.away_club_id,
            away_club_name=self._club_name(competition.id, match.away_club_id),
            away_lineup_mode=(
                away_owner_tactics.get("lineup_mode", "strongest")
                if isinstance(away_owner_tactics, dict)
                else "strongest"
            ),
            is_cup_match=format_enum is CompetitionFormat.CUP,
            is_final=match.requires_winner and self._is_last_match(competition.id, match),
            allow_penalties=match.requires_winner,
        )

    def _store_match_viewer_payload(self, match: CompetitionMatch, replay_payload) -> None:
        viewer_payload = self.timeline_service.build_from_replay_payload(replay_payload)
        match.metadata_json = {
            **dict(match.metadata_json or {}),
            "match_viewer": viewer_payload.model_dump(mode="json"),
            "replay_payload": replay_payload.model_dump(mode="json"),
            "simulation_summary": replay_payload.summary.model_dump(mode="json"),
            "simulation_seed": replay_payload.seed,
        }

    def _store_match_events(self, match: CompetitionMatch, replay_payload) -> None:
        existing = self.session.scalar(
            select(CompetitionMatchEvent.id).where(CompetitionMatchEvent.match_id == match.id)
        )
        if existing is not None:
            return

        for event in replay_payload.timeline.events:
            event_type = getattr(event.event_type, "value", str(event.event_type))
            card_type = None
            if event_type == "yellow_card":
                card_type = "yellow"
            elif event_type == "red_card":
                card_type = "red"
            self.lifecycle_service.record_match_event(
                match=match,
                event_type=event_type,
                minute=event.minute,
                added_time=event.added_time,
                club_id=event.team_id,
                player_id=event.primary_player.player_id if event.primary_player else None,
                secondary_player_id=(event.secondary_player.player_id if event.secondary_player else None),
                card_type=card_type,
                highlight=event_type
                in {
                    "goal",
                    "penalty_goal",
                    "penalty_scored",
                    "red_card",
                    "injury",
                    "fulltime",
                },
                metadata_json={
                    "commentary": event.commentary,
                    "analyst_commentary": event.analyst_commentary,
                    "clock_label": event.clock_label,
                    "home_score": event.home_score,
                    "away_score": event.away_score,
                    "presentation_second": event.presentation_second,
                    **dict(event.metadata or {}),
                },
            )

    def _club_name(self, competition_id: str, club_id: str) -> str:
        club_profile = self.session.get(ClubProfile, club_id)
        if club_profile is not None:
            return club_profile.club_name

        club_profile = self.session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == club_id))
        if club_profile is not None:
            return club_profile.club_name

        participant = self.session.scalar(
            select(CompetitionParticipant).where(
                CompetitionParticipant.competition_id == competition_id,
                CompetitionParticipant.club_id == club_id,
            )
        )
        if participant is not None and participant.entry_id is not None:
            entry = self.session.get(CompetitionEntry, participant.entry_id)
            user_name = (entry.metadata_json or {}).get("user_name") if entry else None
            if isinstance(user_name, str) and user_name.strip():
                return user_name.strip()

        user = self.session.get(User, club_id)
        if user is not None:
            if user.display_name and user.display_name.strip():
                return user.display_name.strip()
            if user.username and user.username.strip():
                return user.username.strip()

        return club_id

    def _matches(self, competition_id: str) -> list[CompetitionMatch]:
        return list(
            self.session.scalars(
                select(CompetitionMatch)
                .where(CompetitionMatch.competition_id == competition_id)
                .order_by(
                    CompetitionMatch.round_number.asc(),
                    CompetitionMatch.slot_sequence.asc(),
                    CompetitionMatch.created_at.asc(),
                )
            ).all()
        )

    def _participant_count(self, competition_id: str) -> int:
        return len(
            self.session.scalars(
                select(CompetitionParticipant).where(CompetitionParticipant.competition_id == competition_id)
            ).all()
        )

    def _rule_set(self, competition_id: str) -> CompetitionRuleSet:
        rule_set = self.session.scalar(
            select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id == competition_id)
        )
        if rule_set is None:
            raise ValueError(f"Competition rules were not found for competition {competition_id}.")
        return rule_set

    def _is_last_match(self, competition_id: str, match: CompetitionMatch) -> bool:
        matches = self._matches(competition_id)
        if not matches:
            return False
        latest_round = max(item.round_number for item in matches)
        latest_round_matches = [item for item in matches if item.round_number == latest_round]
        return match.round_number == latest_round and len(latest_round_matches) == 1 and match.requires_winner

    @staticmethod
    def _all_matches_complete(matches: list[CompetitionMatch]) -> bool:
        return all(match.status == MatchStatus.COMPLETED.value for match in matches)

    @staticmethod
    def _simulation_seed(value: str) -> int:
        return sum(ord(character) for character in value) % 1_000_000


__all__ = ["CompetitionAutoRunner"]
