from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.trust_middleware import SharedTrustMiddleware
from app.leaderboards.models import LeaderboardMatchResult, LeaderboardPlayerRating, LeaderboardSeason, SeasonStatus
from app.leaderboards.ranking_service import RankingService
from app.models.base import Base
from app.models.user import User, UserRole
from app.models.user_region import UserRegionProfile
from app.viral.trust import InMemoryTrustStateStore, TrustFactorBreakdown, TrustScoreService, TrustState


def test_ranking_service_skips_low_trust_players_in_leaderboard_updates() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            UserRegionProfile.__table__,
            LeaderboardSeason.__table__,
            LeaderboardPlayerRating.__table__,
            LeaderboardMatchResult.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        session.add_all(
            [
                User(id="trusted-player", email="trusted@example.com", username="trusted", password_hash="hashed", role=UserRole.USER),
                User(id="low-trust-player", email="lowtrust@example.com", username="lowtrust", password_hash="hashed", role=UserRole.USER),
                LeaderboardSeason(
                    id="season-1",
                    start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
                    end_date=datetime(2026, 3, 31, tzinfo=timezone.utc),
                    status=SeasonStatus.ACTIVE,
                ),
            ]
        )
        session.commit()

        trust_store = InMemoryTrustStateStore()
        trust_store.save_trust_state(
            TrustState(
                user_id="low-trust-player",
                trust_score=0.1,
                suspicious_event_count=4,
                healthy_event_count=0,
                shadow_banned=False,
                monetization_eligible=False,
                ranking_eligible=False,
                suspicious_flags=("leaderboard_gate",),
                factors=TrustFactorBreakdown(
                    account_age=0.2,
                    session_consistency=0.2,
                    device_fingerprint_stability=0.2,
                    engagement_authenticity=0.2,
                    anomaly_detection=0.2,
                ),
                updated_at=datetime.now(timezone.utc),
            )
        )
        service = RankingService(
            session=session,
            trust_middleware=SharedTrustMiddleware(
                session=session,
                trust_service=TrustScoreService(store=trust_store),
            ),
        )

        update = service.record_match_result(
            season=session.get(LeaderboardSeason, "season-1"),
            match_id="match-low-trust",
            player_a_id="trusted-player",
            player_b_id="low-trust-player",
            result=1.0,
        )

        assert update.rating_update.player_a_delta == 0
        assert update.rating_update.player_b_delta == 0
        assert update.player_a.matches_played == 0
        assert update.player_b.matches_played == 0
        assert update.match_record.metadata_json["trust"]["match_weight"] == 0.0
