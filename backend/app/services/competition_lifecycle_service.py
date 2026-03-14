from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.common.enums.competition_status import CompetitionStatus
from backend.app.common.enums.match_status import MatchStatus
from backend.app.models.competition import Competition
from backend.app.models.competition_match import CompetitionMatch
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.competition_playoff import CompetitionPlayoff
from backend.app.models.competition_prize_rule import CompetitionPrizeRule
from backend.app.models.competition_reward_pool import CompetitionRewardPool
from backend.app.models.competition_round import CompetitionRound
from backend.app.models.competition_rule_set import CompetitionRuleSet
from backend.app.models.competition_schedule_job import CompetitionScheduleJob
from backend.app.models.competition_seed_rule import CompetitionSeedRule
from backend.app.services.competition_fixture_service import CompetitionFixtureService, FixtureBuildResult
from backend.app.services.competition_match_service import CompetitionMatchService
from backend.app.services.competition_reward_service import CompetitionRewardService
from backend.app.services.competition_schedule_service import CompetitionScheduleService
from backend.app.services.competition_seeding_service import CompetitionSeedingService
from backend.app.services.competition_visibility_service import CompetitionVisibilityService
from backend.app.story_feed_engine.service import StoryFeedService


@dataclass(slots=True)
class CompetitionLifecycleService:
    session: Session
    schedule_service: CompetitionScheduleService = field(init=False)
    fixture_service: CompetitionFixtureService = field(default_factory=CompetitionFixtureService)
    seeding_service: CompetitionSeedingService = field(default_factory=CompetitionSeedingService)
    match_service: CompetitionMatchService = field(init=False)
    reward_service: CompetitionRewardService = field(default_factory=CompetitionRewardService)
    visibility_service: CompetitionVisibilityService = field(default_factory=CompetitionVisibilityService)

    def __post_init__(self) -> None:
        self.schedule_service = CompetitionScheduleService(self.session)
        self.match_service = CompetitionMatchService(self.session)

    def seed_competition(
        self,
        competition: Competition,
        *,
        manual_seed_order: Iterable[str] | None = None,
    ) -> list[CompetitionParticipant]:
        participants = self._participants(competition.id)
        seed_rule = self._seed_rule(competition.id)
        ordered = self.seeding_service.seed_participants(
            participants=participants,
            seed_rule=seed_rule,
            manual_seed_order=manual_seed_order,
            seed_token=competition.id,
        )
        for participant in ordered:
            participant.status = "seeded"
        competition.status = CompetitionStatus.SEEDED.value
        competition.seeded_at = datetime.now(timezone.utc)
        competition.stage = "seeded"
        self.session.flush()
        return ordered

    def launch_competition(
        self,
        competition: Competition,
    ) -> FixtureBuildResult:
        rule_set = self._rule_set(competition.id)
        participants = self._participants(competition.id)
        if len(participants) < rule_set.min_participants:
            raise ValueError("Competition requires more participants before launch.")
        if not any(participant.seed for participant in participants):
            self.seed_competition(competition)
            participants = self._participants(competition.id)
        if rule_set.group_stage_enabled:
            self._assign_groups(rule_set, participants)

        schedule_plan = self._schedule_plan_for_launch(competition, rule_set, len(participants))
        fixtures = self.fixture_service.build_initial_fixtures(
            competition=competition,
            rule_set=rule_set,
            participants=participants,
            schedule_plan=schedule_plan,
        )
        self.session.add_all(fixtures.rounds)
        self.session.add_all(fixtures.matches)
        if fixtures.playoffs:
            self.session.add_all(fixtures.playoffs)

        competition.status = CompetitionStatus.LIVE.value
        competition.launched_at = datetime.now(timezone.utc)
        competition.stage = "group" if rule_set.group_stage_enabled else ("league" if competition.format == CompetitionFormat.LEAGUE.value else "knockout")
        StoryFeedService(self.session).publish(
            story_type="competition_launch",
            title=f"{competition.name} is live",
            body="Competition fixtures have been generated and kickoff is underway.",
            audience="public",
            subject_type="competition",
            subject_id=competition.id,
            metadata_json={"competition_id": competition.id, "format": competition.format},
            published_by_user_id=competition.host_user_id,
        )
        self.session.flush()
        return fixtures

    def advance_competition(self, competition: Competition, *, force: bool = False) -> FixtureBuildResult | None:
        rule_set = self._rule_set(competition.id)
        matches = list(
            self.session.scalars(
                select(CompetitionMatch).where(CompetitionMatch.competition_id == competition.id)
            ).all()
        )
        if not matches:
            return None

        if rule_set.group_stage_enabled and not self._has_knockout_matches(matches):
            if not self._all_stage_complete(matches, stage="group") and not force:
                return None
            standings_by_group = self._group_standings(competition.id, rule_set)
            advancing = self._advance_from_groups(rule_set, standings_by_group)
            for participant in advancing:
                participant.advanced = True
            schedule_plan = self._schedule_plan_for_launch(competition, rule_set, len(advancing))
            fixtures = self.fixture_service.build_next_knockout_round(
                competition=competition,
                rule_set=rule_set,
                winners=advancing,
                schedule_plan=schedule_plan,
                round_number=1,
                stage="knockout",
            )
            self.session.add_all(fixtures.rounds)
            self.session.add_all(fixtures.matches)
            if fixtures.playoffs:
                self.session.add_all(fixtures.playoffs)
            competition.stage = "knockout"
            self.session.flush()
            return fixtures

        latest_round = self._latest_knockout_round(matches)
        if latest_round is None:
            return None
        latest_matches = [match for match in matches if match.stage == latest_round.stage and match.round_number == latest_round.round_number]
        if not self._all_matches_complete(latest_matches) and not force:
            return None
        winners = self._winners_from_matches(latest_matches)
        if len(winners) <= 1:
            competition.status = CompetitionStatus.COMPLETED.value
            competition.completed_at = datetime.now(timezone.utc)
            competition.stage = "completed"
            self.session.flush()
            return None

        next_round_number = latest_round.round_number + 1
        schedule_plan = self._schedule_plan_for_launch(competition, rule_set, len(winners))
        fixtures = self.fixture_service.build_next_knockout_round(
            competition=competition,
            rule_set=rule_set,
            winners=winners,
            schedule_plan=schedule_plan,
            round_number=next_round_number,
            stage=latest_round.stage,
        )
        self.session.add_all(fixtures.rounds)
        self.session.add_all(fixtures.matches)
        if fixtures.playoffs:
            self.session.add_all(fixtures.playoffs)
        self.session.flush()
        return fixtures

    def finalize_competition(self, competition: Competition, *, settle: bool = True) -> list[CompetitionRewardPool]:
        matches = list(
            self.session.scalars(
                select(CompetitionMatch).where(CompetitionMatch.competition_id == competition.id)
            ).all()
        )
        if matches and not self._all_matches_complete(matches):
            raise ValueError("Competition cannot finalize until all matches are complete.")

        rule_set = self._rule_set(competition.id)
        prize_rule = self._prize_rule(competition.id)
        standings = self.match_service.standings(
            competition_id=competition.id,
            rule_set=rule_set,
        )
        reward_pools = list(
            self.session.scalars(
                select(CompetitionRewardPool).where(CompetitionRewardPool.competition_id == competition.id)
            ).all()
        )
        if not reward_pools:
            reward_pools.append(
                CompetitionRewardPool(
                    competition_id=competition.id,
                    pool_type="entry_fee",
                    currency=competition.currency,
                    amount_minor=competition.net_prize_pool_minor,
                    status="planned",
                    metadata_json={},
                )
            )
            self.session.add(reward_pools[-1])
        rewards: list = []
        for pool in reward_pools:
            rewards.extend(
                self.reward_service.build_rewards(
                    competition_id=competition.id,
                    pool=pool,
                    prize_rule=prize_rule,
                    standings=standings,
                    settle=settle,
                )
            )
            pool.status = "settled" if settle else "planned"
        self.session.add_all(rewards)
        competition.status = CompetitionStatus.SETTLED.value if settle else CompetitionStatus.COMPLETED.value
        competition.completed_at = competition.completed_at or datetime.now(timezone.utc)
        competition.settled_at = datetime.now(timezone.utc) if settle else None
        competition.stage = "settled" if settle else "completed"
        StoryFeedService(self.session).publish(
            story_type="competition_result",
            title=f"{competition.name} completed",
            body="Competition settlements have been prepared and final standings are available.",
            audience="public",
            subject_type="competition",
            subject_id=competition.id,
            metadata_json={"competition_id": competition.id, "settled": settle},
            published_by_user_id=competition.host_user_id,
        )
        self.session.flush()
        return reward_pools

    def record_match_event(
        self,
        *,
        match: CompetitionMatch,
        event_type: str,
        minute: int | None,
        added_time: int | None,
        club_id: str | None,
        player_id: str | None,
        secondary_player_id: str | None,
        card_type: str | None,
        highlight: bool,
        metadata_json: dict,
    ):
        return self.match_service.record_event(
            competition_id=match.competition_id,
            match_id=match.id,
            event_type=event_type,
            minute=minute,
            added_time=added_time,
            club_id=club_id,
            player_id=player_id,
            secondary_player_id=secondary_player_id,
            card_type=card_type,
            highlight=highlight,
            metadata_json=metadata_json,
        )

    def complete_match(
        self,
        *,
        match: CompetitionMatch,
        home_score: int,
        away_score: int,
        decided_by_penalties: bool = False,
        winner_club_id: str | None = None,
    ) -> CompetitionMatch:
        rule_set = self._rule_set(match.competition_id)
        return self.match_service.complete_match(
            match=match,
            rule_set=rule_set,
            home_score=home_score,
            away_score=away_score,
            decided_by_penalties=decided_by_penalties,
            winner_club_id=winner_club_id,
        )

    def _schedule_plan_for_launch(
        self,
        competition: Competition,
        rule_set: CompetitionRuleSet,
        participant_count: int,
    ) -> CompetitionSchedulePlan | None:
        schedule_job = self.session.scalar(
            select(CompetitionScheduleJob)
            .where(
                CompetitionScheduleJob.competition_id == competition.id,
                CompetitionScheduleJob.preview_only.is_(False),
            )
            .order_by(CompetitionScheduleJob.created_at.desc())
        )
        if schedule_job is not None and schedule_job.schedule_plan_json:
            return CompetitionSchedulePlan.model_validate(schedule_job.schedule_plan_json)
        start_date = (competition.scheduled_start_at or datetime.now(timezone.utc)).date()
        preview = self.schedule_service.preview(
            competition=competition,
            rule_set=rule_set,
            participant_count=participant_count,
            start_date=start_date,
            requested_dates=None,
            priority=100,
            requires_exclusive_windows=False,
            alignment_group=None,
        )
        return preview.plan

    def _participants(self, competition_id: str) -> list[CompetitionParticipant]:
        return list(
            self.session.scalars(
                select(CompetitionParticipant).where(CompetitionParticipant.competition_id == competition_id)
            ).all()
        )

    def _rule_set(self, competition_id: str) -> CompetitionRuleSet:
        rule_set = self.session.scalar(
            select(CompetitionRuleSet).where(CompetitionRuleSet.competition_id == competition_id)
        )
        if rule_set is None:
            raise ValueError("Competition rules are missing.")
        return rule_set

    def _prize_rule(self, competition_id: str) -> CompetitionPrizeRule:
        prize_rule = self.session.scalar(
            select(CompetitionPrizeRule).where(CompetitionPrizeRule.competition_id == competition_id)
        )
        if prize_rule is None:
            raise ValueError("Competition prize rules are missing.")
        return prize_rule

    def _seed_rule(self, competition_id: str) -> CompetitionSeedRule:
        seed_rule = self.session.scalar(
            select(CompetitionSeedRule).where(CompetitionSeedRule.competition_id == competition_id)
        )
        if seed_rule is None:
            seed_rule = CompetitionSeedRule(competition_id=competition_id)
            self.session.add(seed_rule)
            self.session.flush()
        return seed_rule

    def _assign_groups(self, rule_set: CompetitionRuleSet, participants: list[CompetitionParticipant]) -> None:
        if not rule_set.group_stage_enabled:
            return
        ordered = sorted(participants, key=lambda item: item.seed or 9999)
        group_size = rule_set.group_size or max(2, min(4, len(ordered)))
        group_count = rule_set.group_count or max(1, int((len(ordered) + group_size - 1) / group_size))
        for index, participant in enumerate(ordered):
            group_index = (index % group_count) + 1
            participant.group_key = f"g{group_index:02d}"

    def _group_standings(
        self,
        competition_id: str,
        rule_set: CompetitionRuleSet,
    ) -> dict[str, list[CompetitionParticipant]]:
        groups: dict[str, list[CompetitionParticipant]] = {}
        participants = self._participants(competition_id)
        for participant in participants:
            key = participant.group_key or "g00"
            groups.setdefault(key, []).append(participant)
        ranked: dict[str, list[CompetitionParticipant]] = {}
        for key, entries in groups.items():
            ranked[key] = self.match_service._rank_participants(
                competition_id=competition_id,
                participants=entries,
                rule_set=rule_set,
            )
        return ranked

    def _advance_from_groups(
        self,
        rule_set: CompetitionRuleSet,
        standings_by_group: dict[str, list[CompetitionParticipant]],
    ) -> list[CompetitionParticipant]:
        advance_count = rule_set.group_advance_count or 2
        advancing: list[CompetitionParticipant] = []
        for group_entries in standings_by_group.values():
            advancing.extend(group_entries[:advance_count])
        return advancing

    @staticmethod
    def _all_matches_complete(matches: Iterable[CompetitionMatch]) -> bool:
        return all(match.status == MatchStatus.COMPLETED.value for match in matches)

    @staticmethod
    def _all_stage_complete(matches: Iterable[CompetitionMatch], *, stage: str) -> bool:
        stage_matches = [match for match in matches if match.stage == stage]
        if not stage_matches:
            return False
        return all(match.status == MatchStatus.COMPLETED.value for match in stage_matches)

    @staticmethod
    def _has_knockout_matches(matches: Iterable[CompetitionMatch]) -> bool:
        return any(match.stage == "knockout" for match in matches)

    def _latest_knockout_round(self, matches: Iterable[CompetitionMatch]) -> CompetitionRound | None:
        rounds = list(
            self.session.scalars(
                select(CompetitionRound).where(
                    CompetitionRound.competition_id == matches[0].competition_id,
                    CompetitionRound.stage == "knockout",
                )
            ).all()
        )
        if not rounds:
            return None
        return max(rounds, key=lambda item: item.round_number)

    def _winners_from_matches(self, matches: Iterable[CompetitionMatch]) -> list[CompetitionParticipant]:
        winners: list[CompetitionParticipant] = []
        for match in matches:
            winner_id = match.winner_club_id
            if winner_id is None:
                continue
            participant = self.session.scalar(
                select(CompetitionParticipant).where(
                    CompetitionParticipant.competition_id == match.competition_id,
                    CompetitionParticipant.club_id == winner_id,
                )
            )
            if participant is not None:
                winners.append(participant)
        return winners


__all__ = ["CompetitionLifecycleService"]
