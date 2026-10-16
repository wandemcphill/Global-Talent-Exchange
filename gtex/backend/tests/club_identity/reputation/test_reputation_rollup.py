from __future__ import annotations

from sqlalchemy import func, select

from app.club_identity.models.reputation import ClubReputationProfile, ReputationEventLog, ReputationSnapshot
from app.club_identity.reputation.schemas import ContinentalStage, SeasonReputationOutcome, WorldSuperCupStage
from app.club_identity.reputation.season_reputation_rollup import SeasonReputationRollupService


def test_multi_season_rollup_accumulates_and_stays_idempotent(session) -> None:
    service = SeasonReputationRollupService()
    first_outcome = SeasonReputationOutcome(
        club_id="club-1",
        season=1,
        league_finish=1,
        qualified_for_continental=True,
        continental_stage=ContinentalStage.ROUND_OF_16,
        top_scorer_awards=1,
        league_title_streak=1,
        club_age_years=40,
    )
    second_outcome = SeasonReputationOutcome(
        club_id="club-1",
        season=2,
        league_finish=2,
        qualified_for_continental=True,
        continental_stage=ContinentalStage.WINNER,
        qualified_for_world_super_cup=True,
        world_super_cup_stage=WorldSuperCupStage.RUNNER_UP,
        top_assist_awards=1,
        club_age_years=41,
    )

    first_result = service.apply_season_outcome(session, first_outcome)
    second_result = service.apply_season_outcome(session, second_outcome)
    session.commit()

    repeated_second = service.apply_season_outcome(session, second_outcome)
    session.commit()

    profile = session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == "club-1"))
    snapshots = session.scalars(
        select(ReputationSnapshot).where(ReputationSnapshot.club_id == "club-1").order_by(ReputationSnapshot.season.asc())
    ).all()
    event_count = session.scalar(select(func.count()).select_from(ReputationEventLog).where(ReputationEventLog.club_id == "club-1"))

    assert first_result.created is True
    assert second_result.created is True
    assert repeated_second.created is False
    assert profile is not None
    assert profile.current_score == snapshots[-1].score_after
    assert profile.total_seasons == 2
    assert len(snapshots) == 2
    assert event_count == first_result.event_count + second_result.event_count


def test_rollup_unlocks_milestones_and_dynasty_era(session) -> None:
    service = SeasonReputationRollupService()
    session.add(
        ClubReputationProfile(
            club_id="club-2",
            current_score=1495,
            highest_score=1495,
            prestige_tier="Legendary",
            total_seasons=6,
            last_active_season=6,
            total_league_titles=2,
            total_continental_qualifications=3,
        )
    )
    session.flush()

    result = service.apply_season_outcome(
        session,
        SeasonReputationOutcome(
            club_id="club-2",
            season=7,
            league_finish=1,
            qualified_for_continental=True,
            continental_stage=ContinentalStage.WINNER,
            league_title_streak=2,
            undefeated_league_season=True,
            top_scorer_awards=1,
            top_assist_awards=1,
            club_age_years=60,
            activity_consistency_ratio=0.9,
        ),
    )
    session.commit()

    milestone_titles = session.scalars(
        select(ReputationEventLog.summary)
        .where(ReputationEventLog.club_id == "club-2", ReputationEventLog.milestone.is_not(None))
        .order_by(ReputationEventLog.created_at.asc())
    ).all()

    assert result.profile.prestige_tier == "Dynasty"
    assert "Continental Champion" in milestone_titles
    assert "Back-to-Back Champion" in milestone_titles
    assert "Invincibles" in milestone_titles
    assert "Dynasty Era Started" in milestone_titles


def test_inactivity_decay_is_mild_and_only_after_long_gaps(session) -> None:
    service = SeasonReputationRollupService()
    session.add(
        ClubReputationProfile(
            club_id="club-3",
            current_score=720,
            highest_score=720,
            prestige_tier="Elite",
            total_seasons=3,
            last_active_season=3,
        )
    )
    session.flush()

    result = service.apply_season_outcome(
        session,
        SeasonReputationOutcome(
            club_id="club-3",
            season=7,
            league_finish=8,
            club_age_years=20,
            activity_consistency_ratio=0.4,
        ),
    )
    session.commit()

    decay_events = session.scalars(
        select(ReputationEventLog).where(
            ReputationEventLog.club_id == "club-3",
            ReputationEventLog.event_type == "inactivity_decay",
        )
    ).all()

    assert result.snapshot.score_before == 720
    assert result.snapshot.score_after == 710
    assert len(decay_events) == 1
    assert decay_events[0].delta == -10
