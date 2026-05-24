from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
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
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.services.competition_lifecycle_service import CompetitionLifecycleService
from app.services.match_timeline_service import MatchTimelineService


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
    match_service: MatchSimulationService = field(default_factory=MatchSimulationService)
    timeline_service: MatchTimelineService = field(default_factory=MatchTimelineService)
    team_factory: SyntheticSquadFactory = field(init=False)

    def __post_init__(self) -> None:
        self.lifecycle_service = CompetitionLifecycleService(self.session)
        bind = self.session.get_bind()
        session_factory = create_session_factory(bind) if bind is not None else None
        self.team_factory = SyntheticSquadFactory(
            session_factory=session_factory,
            allow_synthetic_fallback=False,
        )

    def run_until_idle(
        self,
        competition: Competition,
        *,
        simulate_scheduled_matches: bool = False,
    ) -> Competition:
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
            if self._should_launch(competition):
                self.lifecycle_service.launch_competition(competition)
                changed = True

            matches = self._matches(competition.id)
            scheduled = [match for match in matches if match.status == MatchStatus.SCHEDULED.value]
            if scheduled and simulate_scheduled_matches:
                for match in scheduled:
                    self._simulate_match(competition, match)
                changed = True
                matches = self._matches(competition.id)

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

    def _should_launch(self, competition: Competition) -> bool:
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
        now = datetime.now(timezone.utc)
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

        job = self._simulation_job(competition, match)
        replay_payload = self.match_service.build_replay_payload(
            self.team_factory.build_request(job, session=self.session)
        )
        self._store_match_viewer_payload(match, replay_payload)
        self._store_match_events(match, replay_payload)
        return self.lifecycle_service.complete_match(
            match=match,
            home_score=replay_payload.summary.home_score,
            away_score=replay_payload.summary.away_score,
            decided_by_penalties=replay_payload.summary.decided_by_penalties,
            winner_club_id=replay_payload.summary.winner_team_id,
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
            or datetime.now(timezone.utc).date()
        )
        scheduled_kickoff_at = match.scheduled_at or window.kickoff_at(match_date)
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
            away_club_id=match.away_club_id,
            away_club_name=self._club_name(competition.id, match.away_club_id),
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
