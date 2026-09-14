from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.service import AuthService
from app.db import load_model_modules
from app.models import (
    Base,
    Competition,
    CompetitionEntry,
    CompetitionParticipant,
    CompetitionPrizeRule,
    CompetitionReward,
    CompetitionRewardPool,
    CompetitionRuleSet,
    RewardSettlement,
)
from app.reward_engine.service import RewardEngineService
from app.services.competition_lifecycle_service import CompetitionLifecycleService
from backend.tests.support.economic_policy import seed_economic_policy


@pytest.fixture()
def replay_session():
    load_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with SessionLocal() as db_session:
        seed_economic_policy(db_session)
        yield db_session


def _create_user(session, *, email: str, username: str):
    user = AuthService().register_user(
        session,
        email=email,
        username=username,
        password="SuperSecret1",  # pragma: allowlist secret
    )
    session.commit()
    return user


def test_competition_finalization_and_reward_settlement_replay_is_idempotent(replay_session) -> None:
    host = _create_user(replay_session, email="host-replay@example.com", username="hostreplay")
    winner = _create_user(replay_session, email="winner-replay@example.com", username="winnerreplay")
    runner_up = _create_user(replay_session, email="runnerup-replay@example.com", username="runnerupreplay")

    competition = Competition(
        host_user_id=host.id,
        name="Platform Replay Cup",
        description="Replay test cup",
        competition_type="league",
        source_type="gtex_platform",
        format="league",
        visibility="public",
        status="completed",
        start_mode="scheduled",
        stage="completed",
        currency="coin",
        entry_fee_minor=0,
        platform_fee_bps=0,
        host_fee_bps=0,
        host_creation_fee_minor=0,
        gross_pool_minor=0,
        net_prize_pool_minor=1_000_000,
        metadata_json={},
    )
    replay_session.add(competition)
    replay_session.flush()

    replay_session.add(
        CompetitionRuleSet(
            competition_id=competition.id,
            format="league",
            min_participants=2,
            max_participants=2,
            league_win_points=3,
            league_draw_points=1,
            league_loss_points=0,
            league_tie_break_order=["points", "goal_diff", "goals_for"],
            league_home_away=False,
            cup_allowed_participant_sizes=[],
            group_stage_enabled=False,
        )
    )
    replay_session.add(
        CompetitionPrizeRule(
            competition_id=competition.id,
            payout_mode="custom_percent",
            top_n=1,
            payout_percentages=[100],
        )
    )
    replay_session.add(
        CompetitionRewardPool(
            competition_id=competition.id,
            pool_type="promo_pool",
            currency="coin",
            amount_minor=1_000_000,
            status="planned",
            metadata_json={},
        )
    )

    winner_entry = CompetitionEntry(
        competition_id=competition.id,
        club_id=winner.id,
        user_id=winner.id,
        entry_type="direct",
        status="accepted",
        metadata_json={},
    )
    runner_up_entry = CompetitionEntry(
        competition_id=competition.id,
        club_id=runner_up.id,
        user_id=runner_up.id,
        entry_type="direct",
        status="accepted",
        metadata_json={},
    )
    replay_session.add_all([winner_entry, runner_up_entry])
    replay_session.flush()

    replay_session.add_all(
        [
            CompetitionParticipant(
                competition_id=competition.id,
                club_id=winner.id,
                entry_id=winner_entry.id,
                status="joined",
                points=3,
                goal_diff=2,
                goals_for=2,
            ),
            CompetitionParticipant(
                competition_id=competition.id,
                club_id=runner_up.id,
                entry_id=runner_up_entry.id,
                status="joined",
                points=0,
                goal_diff=-2,
                goals_for=0,
            ),
        ]
    )
    replay_session.commit()

    reward_engine = RewardEngineService(replay_session)
    reward_engine.credit_promo_pool(actor=host, amount=Decimal("100.0000"))

    lifecycle = CompetitionLifecycleService(replay_session)
    lifecycle.finalize_competition(competition, settle=True)
    replay_session.commit()

    lifecycle.finalize_competition(competition, settle=True)
    replay_session.commit()

    rewards = replay_session.scalars(
        select(CompetitionReward).where(CompetitionReward.competition_id == competition.id)
    ).all()
    settlements = replay_session.scalars(
        select(RewardSettlement).where(RewardSettlement.competition_key == competition.id)
    ).all()

    assert len(rewards) == 1
    assert len(settlements) == 1
    assert competition.status in {"settled", "completed"}
