from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_identity.models.reputation import (
    ClubReputationProfile,
    PrestigeTier,
    ReputationEventLog,
    ReputationEventType,
    ReputationSnapshot,
)
from app.club_identity.reputation.inactivity_decay_service import InactivityDecayService
from app.club_identity.reputation.prestige_tier_service import PrestigeTierService
from app.club_identity.reputation.reputation_calculator import ReputationCalculator
from app.club_identity.reputation.schemas import ContinentalStage, SeasonReputationOutcome, WorldSuperCupStage
from app.core.events import DomainEvent, EventPublisher, utcnow


@dataclass(frozen=True, slots=True)
class SeasonRollupResult:
    profile: ClubReputationProfile
    snapshot: ReputationSnapshot
    created: bool
    event_count: int


class SeasonReputationRollupService:
    def __init__(
        self,
        calculator: ReputationCalculator | None = None,
        prestige_tier_service: PrestigeTierService | None = None,
        inactivity_decay_service: InactivityDecayService | None = None,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._calculator = calculator or ReputationCalculator()
        self._prestige_tier_service = prestige_tier_service or PrestigeTierService()
        self._inactivity_decay_service = inactivity_decay_service or InactivityDecayService()
        self._event_publisher = event_publisher

    def apply_season_outcome(self, session: Session, outcome: SeasonReputationOutcome) -> SeasonRollupResult:
        existing_snapshot = session.scalar(
            select(ReputationSnapshot).where(
                ReputationSnapshot.club_id == outcome.club_id,
                ReputationSnapshot.season == outcome.season,
            )
        )
        if existing_snapshot is not None:
            profile = self._get_or_create_profile(session, outcome.club_id)
            return SeasonRollupResult(
                profile=profile,
                snapshot=existing_snapshot,
                created=False,
                event_count=existing_snapshot.event_count,
            )

        profile = self._get_or_create_profile(session, outcome.club_id)
        score_before = profile.current_score
        running_score = score_before
        badges: list[str] = []
        milestones: list[str] = []
        event_count = 0

        decay_decision = self._inactivity_decay_service.calculate_decay(profile, outcome.season)
        if decay_decision is not None:
            running_score = max(running_score + decay_decision.delta, 0)
            self._append_event(
                session=session,
                club_id=outcome.club_id,
                season=outcome.season,
                event_type=ReputationEventType.INACTIVITY_DECAY,
                source="inactivity_decay",
                delta=decay_decision.delta,
                score_after=running_score,
                summary=decay_decision.summary,
                payload={"seasons_inactive": decay_decision.seasons_inactive},
            )
            event_count += 1

        calculated = self._calculator.calculate(outcome=outcome, profile=profile)
        for entry in calculated.entries:
            running_score = max(running_score + entry.delta, 0)
            self._append_event(
                session=session,
                club_id=outcome.club_id,
                season=outcome.season,
                event_type=entry.event_type,
                source=entry.source,
                delta=entry.delta,
                score_after=running_score,
                summary=entry.summary,
                milestone=entry.milestone,
                badge_code=entry.badge_code,
                payload=entry.payload,
            )
            event_count += 1

        badges.extend(calculated.badges)
        milestones.extend(calculated.milestones)

        new_tier = self._prestige_tier_service.determine_tier(running_score)
        previous_tier = PrestigeTier(profile.prestige_tier)
        if previous_tier != PrestigeTier.DYNASTY and new_tier == PrestigeTier.DYNASTY:
            dynasty_milestone = "Dynasty Era Started"
            badges.append("dynasty_era_started")
            milestones.append(dynasty_milestone)
            self._append_event(
                session=session,
                club_id=outcome.club_id,
                season=outcome.season,
                event_type=ReputationEventType.MILESTONE_UNLOCKED,
                source="milestone",
                delta=0,
                score_after=running_score,
                summary=dynasty_milestone,
                milestone=dynasty_milestone,
                badge_code="dynasty_era_started",
                payload={"prestige_tier": new_tier.value},
            )
            event_count += 1

        unique_badges = list(dict.fromkeys(badges))
        unique_milestones = list(dict.fromkeys(milestones))

        snapshot = ReputationSnapshot(
            club_id=outcome.club_id,
            season=outcome.season,
            score_before=score_before,
            season_delta=running_score - score_before,
            score_after=running_score,
            prestige_tier=new_tier.value,
            badges=unique_badges,
            milestones=unique_milestones,
            event_count=event_count,
            rolled_up_at=utcnow(),
        )
        session.add(snapshot)

        self._update_profile(profile=profile, outcome=outcome, score_after=running_score, prestige_tier=new_tier)
        session.flush()

        if self._event_publisher is not None:
            self._event_publisher.publish(
                DomainEvent(
                    name="club.reputation.rolled_up",
                    payload={
                        "club_id": outcome.club_id,
                        "season": outcome.season,
                        "current_score": profile.current_score,
                        "prestige_tier": profile.prestige_tier,
                    },
                )
            )

        return SeasonRollupResult(profile=profile, snapshot=snapshot, created=True, event_count=event_count)

    def _get_or_create_profile(self, session: Session, club_id: str) -> ClubReputationProfile:
        profile = session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id))
        if profile is not None:
            return profile
        profile = ClubReputationProfile(
            club_id=club_id,
            current_score=0,
            highest_score=0,
            prestige_tier=PrestigeTier.LOCAL.value,
            total_seasons=0,
            consecutive_top_competition_seasons=0,
            consecutive_league_titles=0,
            consecutive_continental_titles=0,
            total_league_titles=0,
            total_continental_qualifications=0,
            total_continental_titles=0,
            total_world_super_cup_qualifications=0,
            total_world_super_cup_titles=0,
            total_top_scorer_awards=0,
            total_top_assist_awards=0,
        )
        session.add(profile)
        session.flush()
        return profile

    def _append_event(
        self,
        session: Session,
        club_id: str,
        season: int,
        event_type: ReputationEventType,
        source: str,
        delta: int,
        score_after: int,
        summary: str,
        payload: dict[str, object],
        milestone: str | None = None,
        badge_code: str | None = None,
    ) -> None:
        session.add(
            ReputationEventLog(
                club_id=club_id,
                season=season,
                event_type=event_type.value,
                source=source,
                delta=delta,
                score_after=score_after,
                summary=summary,
                milestone=milestone,
                badge_code=badge_code,
                payload=payload,
            )
        )

    def _update_profile(
        self,
        profile: ClubReputationProfile,
        outcome: SeasonReputationOutcome,
        score_after: int,
        prestige_tier: PrestigeTier,
    ) -> None:
        profile.current_score = score_after
        profile.highest_score = max(profile.highest_score, score_after)
        profile.prestige_tier = prestige_tier.value
        profile.total_seasons += 1
        profile.last_active_season = outcome.season
        profile.last_rollup_at = utcnow()
        profile.consecutive_top_competition_seasons = (
            outcome.consecutive_top_competition_seasons if outcome.qualified_for_continental else 0
        )
        profile.consecutive_league_titles = outcome.league_title_streak if outcome.league_finish == 1 else 0
        profile.consecutive_continental_titles = (
            outcome.continental_title_streak if outcome.continental_stage == ContinentalStage.WINNER else 0
        )
        if outcome.league_finish == 1:
            profile.total_league_titles += 1
        if outcome.qualified_for_continental:
            profile.total_continental_qualifications += 1
        if outcome.continental_stage == ContinentalStage.WINNER:
            profile.total_continental_titles += 1
        if outcome.qualified_for_world_super_cup:
            profile.total_world_super_cup_qualifications += 1
        if outcome.world_super_cup_stage == WorldSuperCupStage.WINNER:
            profile.total_world_super_cup_titles += 1
        profile.total_top_scorer_awards += outcome.top_scorer_awards
        profile.total_top_assist_awards += outcome.top_assist_awards
