from __future__ import annotations

from alembic import command
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import pytest

from app.core.database import build_alembic_config
from app.models import Base
from app.models.creator_campaign import CreatorCampaign
from app.models.creator_leaderboard_snapshot import CreatorLeaderboardSnapshot
from app.models.creator_profile import CreatorProfile
from app.models.referral_analytics_daily import ReferralAnalyticsDaily
from app.models.referral_attribution import ReferralAttribution
from app.models.referral_event import ReferralEvent
from app.models.referral_flag import ReferralFlag
from app.models.referral_reward import ReferralReward
from app.models.referral_reward_ledger import ReferralRewardLedger
from app.models.share_code import ShareCode
from app.services.share_code_generation_service import ShareCodeGenerationService
from app.schemas.share_code_core import ShareCodeGenerationRequest


def test_alembic_upgrade_creates_creator_referral_growth_tables(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'creator_referrals.db').as_posix()}"
    command.upgrade(build_alembic_config(database_url), "head")

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    try:
        inspector = inspect(engine)
        assert {
            "creator_profiles",
            "share_codes",
            "creator_campaigns",
            "referral_attributions",
            "referral_events",
            "referral_rewards",
            "referral_reward_ledger",
            "referral_flags",
            "referral_analytics_daily",
            "creator_leaderboard_snapshots",
        }.issubset(set(inspector.get_table_names()))
        assert {
            "creator_profiles",
            "share_codes",
            "creator_campaigns",
            "referral_attributions",
            "referral_events",
            "referral_rewards",
            "referral_reward_ledger",
            "referral_flags",
            "referral_analytics_daily",
            "creator_leaderboard_snapshots",
        }.issubset(set(Base.metadata.tables))
    finally:
        engine.dispose()


def test_share_code_generation_supports_vanity_and_generated_codes() -> None:
    service = ShareCodeGenerationService()

    vanity_code = service.generate(
        ShareCodeGenerationRequest.model_validate(
            {
                "code_type": "creator_share",
                "owner_user_id": "user-1",
                "owner_creator_id": "creator-1",
                "owner_handle": "Ayo Community",
                "vanity_code": "Ayo Crew",
            }
        ),
        existing_codes=("COMMUNITY01",),
    )
    generated_code = service.generate(
        ShareCodeGenerationRequest.model_validate(
            {
                "code_type": "user_referral",
                "owner_user_id": "user-2",
                "owner_handle": "Creator Hub",
            }
        ),
        existing_codes=(vanity_code.code,),
    )

    assert vanity_code.code == "AYOCREW"
    assert vanity_code.vanity_code == "AYOCREW"
    assert generated_code.code.startswith("USR")
    assert generated_code.code != vanity_code.code


def test_referral_reward_ledger_is_append_only() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    try:
        with session_local() as session:
            reward = ReferralReward(
                id="reward-1",
                reward_key="event-1:points:user-1",
                referred_user_id="user-2",
                beneficiary_user_id="user-1",
                trigger_event_type="verification_completed",
                reward_type="points",
                status="approved",
                reward_amount=100,
                reward_unit="points",
                reward_payload_json={},
            )
            session.add(reward)
            session.commit()

            entry = ReferralRewardLedger(
                entry_key="reward-1:created",
                reward_id="reward-1",
                entry_type="reward_created",
                amount=100,
                unit="points",
                status_after="approved",
                reference_id="reward-1",
                payload_json={"community_growth": True},
            )
            session.add(entry)
            session.commit()

            entry.payload_json = {"community_growth": False}
            with pytest.raises(ValueError, match="append-only"):
                session.commit()
            session.rollback()

            persisted = session.get(ReferralRewardLedger, entry.id)
            assert persisted is not None
            session.delete(persisted)
            with pytest.raises(ValueError, match="append-only"):
                session.commit()
    finally:
        engine.dispose()
