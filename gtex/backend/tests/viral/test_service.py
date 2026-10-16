from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import load_settings
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.models.base import Base
from app.models.clip_variant import ClipVariant
from app.models.competition_match import CompetitionMatch
from app.viral.distribution import ClipDistributionManager, InMemoryClipDistributionStore
from app.viral.service import ViralFeedService
from backend.tests.match_engine.helpers import build_request


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[CompetitionMatch.__table__, ClipVariant.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def _build_payload_with_manifestable_highlights():
    service = MatchSimulationService()
    for seed in range(1, 140):
        payload = service.build_replay_payload(build_request(seed=seed, match_id=f"viral-{seed:03d}"))
        if any(clip.event_id is not None for clip in payload.summary.highlight_package):
            return payload
    raise AssertionError("Expected a replay payload with event-backed highlight clips.")


def _distribution_manager() -> ClipDistributionManager:
    return ClipDistributionManager(store=InMemoryClipDistributionStore())


def test_viral_feed_service_builds_ranked_vertical_clips() -> None:
    session_factory = _session_factory()
    payload = _build_payload_with_manifestable_highlights()
    settings = load_settings(environ={"DATABASE_URL": "sqlite+pysqlite:///:memory:"})

    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=payload.match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id=payload.summary.home_stats.team_id,
                away_club_id=payload.summary.away_stats.team_id,
                metadata_json={"replay_payload": payload.model_dump(mode="json")},
            )
        )
        session.commit()

        feed = ViralFeedService(
            session=session,
            settings=settings,
            distribution_manager=_distribution_manager(),
        ).build_match_feed(payload.match_id)

    assert feed.clips
    assert feed.clips[0].clip_id == f"{payload.match_id}::{feed.clips[0].highlight_id}"
    assert feed.clips[0].viral_score >= feed.clips[-1].viral_score
    assert feed.clips[0].caption.hook
    assert feed.clips[0].distribution_accounts
    assert feed.clips[0].distribution_accounts[0].persona.name in {"HypeKing", "Tactician"}
    assert len(feed.clips[0].distribution_accounts[0].caption_tests) == 2
    assert {variant.variant_key for variant in feed.clips[0].distribution_accounts[0].caption_tests} == {"A", "B"}
    assert feed.clips[0].editor.aspect_ratio == "9:16"
    assert "whatsapp" in feed.clips[0].editor.share_targets
    assert len(feed.clips[0].formats) == 5
    assert {item.format_key for item in feed.clips[0].formats} == {
        "instant_clip",
        "cinematic_replay",
        "debate_clip",
        "tactical_breakdown",
        "meme_version",
    }
    assert feed.clips[0].analytics.clip_id == feed.clips[0].highlight_id
    assert feed.clips[0].duration_seconds is not None
    assert feed.clips[0].analytics.total_watch_time >= feed.clips[0].analytics.watch_time
    assert feed.clips[0].analytics.views_last_60min >= feed.clips[0].analytics.views_last_10min
    assert feed.clips[0].analytics.watch_time > 0
    assert 0.0 <= feed.clips[0].analytics.completion_rate <= 1.0
    assert feed.clips[0].feedback.recommendation
    assert feed.clips[0].feedback.viral_analysis
    assert feed.clips[0].distribution is not None
    assert feed.clips[0].distribution.impressions_served == 1
    assert feed.clips[0].distribution.impressions_cap >= 100
    assert feed.clips[0].metadata["distribution_key"] == f"clip:{feed.clips[0].clip_id}:distribution"


def test_viral_feed_service_exposes_variant_competition_and_winner_selection() -> None:
    session_factory = _session_factory()
    payload = _build_payload_with_manifestable_highlights()
    settings = load_settings(environ={"DATABASE_URL": "sqlite+pysqlite:///:memory:"})

    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=payload.match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id=payload.summary.home_stats.team_id,
                away_club_id=payload.summary.away_stats.team_id,
                metadata_json={"replay_payload": payload.model_dump(mode="json")},
            )
        )
        session.commit()

        service = ViralFeedService(
            session=session,
            settings=settings,
            distribution_manager=_distribution_manager(),
        )
        feed = service.build_match_feed(payload.match_id)
        clip_id = feed.clips[0].clip_id

        variants_response = service.get_clip_variants(clip_id)

        assert variants_response.resolved is False
        assert len(variants_response.variants) == 5
        assert {variant.format_type for variant in variants_response.variants} == {
            "instant",
            "cinematic",
            "debate",
            "tactical",
            "meme",
        }
        assert sum(variant.distribution_weight for variant in variants_response.variants) == 1.0
        leading_variant = next(
            variant for variant in variants_response.variants if variant.variant_id == variants_response.leading_variant_id
        )
        assert leading_variant.distribution_weight == 0.8

        winner_candidate = session.get(ClipVariant, leading_variant.variant_id)
        assert winner_candidate is not None
        winner_candidate.view_count = 1800
        winner_candidate.watch_time = 18.0
        winner_candidate.loop_rate = 0.55
        winner_candidate.shares = 260
        winner_candidate.comments = 140
        winner_candidate.completion_rate = 0.97
        winner_candidate.share_rate = 0.22
        winner_candidate.comment_rate = 0.11
        winner_candidate.updated_at = datetime.now(UTC) + timedelta(seconds=1)
        session.commit()

        winner_response = service.get_clip_winner(clip_id)

        assert winner_response.resolved is True
        assert winner_response.decision_reason == "view_threshold"
        assert winner_response.winner is not None
        assert winner_response.winner.variant_id == leading_variant.variant_id
        assert winner_response.winner.pushed_to_trending is True
        assert winner_response.winner.distribution_weight == 1.0
        losers = [variant for variant in service.get_clip_variants(clip_id).variants if variant.variant_id != leading_variant.variant_id]
        assert all(variant.distribution_weight == 0.0 for variant in losers)
        assert all(variant.promotion_status == "killed" for variant in losers)


def test_viral_feed_service_returns_only_eligible_clips() -> None:
    session_factory = _session_factory()
    payload = _build_payload_with_manifestable_highlights()
    settings = load_settings(environ={"DATABASE_URL": "sqlite+pysqlite:///:memory:"})

    with session_factory() as session:
        session.add(
            CompetitionMatch(
                id=payload.match_id,
                competition_id="competition-1",
                round_id="round-1",
                round_number=1,
                home_club_id=payload.summary.home_stats.team_id,
                away_club_id=payload.summary.away_stats.team_id,
                metadata_json={"replay_payload": payload.model_dump(mode="json")},
            )
        )
        session.commit()

        distribution_manager = _distribution_manager()
        service = ViralFeedService(
            session=session,
            settings=settings,
            distribution_manager=distribution_manager,
        )
        first_feed = service.build_match_feed(payload.match_id)

        assert len(first_feed.clips) >= 2
        capped_clip = first_feed.clips[0]
        state = distribution_manager.store.load(capped_clip.clip_id)
        assert state is not None
        state.impressions_served = state.impressions_cap
        distribution_manager.store.save(state)

        follow_up_feed = service.build_match_feed(payload.match_id)

    assert follow_up_feed.clips
    assert all(clip.clip_id != capped_clip.clip_id for clip in follow_up_feed.clips)
