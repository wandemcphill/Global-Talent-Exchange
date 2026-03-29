from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin
from app.db import get_session
from app.models.base import Base
from app.models.clip_variant import ClipVariant
from app.models.user import User, UserRole
from app.orchestrator.global_state import InMemoryGlobalFeedStateStore
from app.orchestrator.orchestrator_service import AttentionOrchestratorService
from app.orchestrator.router import router as orchestrator_router
from app.orchestrator.schemas import AttentionOrchestratorConfigUpdateRequest
from app.simulation.content_agent import ContentAgent


def test_attention_orchestrator_guarantees_minimum_exposure_for_new_clips() -> None:
    service = AttentionOrchestratorService(state_store=InMemoryGlobalFeedStateStore())
    clip = ContentAgent(
        clip_id="match-1::clip-new",
        creator_id="creator-1",
        quality=0.42,
        format="instant_clip",
        trust=0.88,
        velocity=0.15,
        age_hours=1.0,
    ).as_clip()

    state = service.refresh_clip_state(clip)

    assert state.stage == "test"
    assert state.allocated_impressions >= 200
    assert clip.orchestrator is not None
    assert clip.orchestrator.allocated_impressions == state.allocated_impressions


def test_attention_orchestrator_filters_out_fully_consumed_clips() -> None:
    store = InMemoryGlobalFeedStateStore()
    service = AttentionOrchestratorService(state_store=store)
    clip = ContentAgent(
        clip_id="match-2::clip-capped",
        creator_id="creator-2",
        quality=0.52,
        format="instant_clip",
        trust=0.91,
        velocity=0.25,
        age_hours=48.0,
    ).as_clip()

    state = service.refresh_clip_state(clip)
    state.allocated_impressions = 1
    state.consumed_impressions = 1
    store.save_clip(state)

    assert service.filter_available([clip]) == []


def test_attention_orchestrator_variant_budget_manager_splits_and_locks_winner() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[ClipVariant.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        session.add_all(
            [
                ClipVariant(
                    variant_id="match-3::clip-base::instant",
                    base_clip_id="match-3::clip-base",
                    format_type="instant",
                    viral_score=0.91,
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json={},
                ),
                ClipVariant(
                    variant_id="match-3::clip-base::cinematic",
                    base_clip_id="match-3::clip-base",
                    format_type="cinematic",
                    viral_score=0.72,
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json={},
                ),
            ]
        )
        session.commit()

        service = AttentionOrchestratorService(
            state_store=InMemoryGlobalFeedStateStore(),
            session=session,
        )
        clip = ContentAgent(
            clip_id="match-3::clip-base",
            creator_id="creator-3",
            quality=0.76,
            format="instant_clip",
            trust=0.95,
            velocity=1.6,
            age_hours=2.0,
        ).as_clip()

        service.refresh_clip_state(clip)
        variants = {
            variant.variant_id: variant
            for variant in session.query(ClipVariant).filter(ClipVariant.base_clip_id == "match-3::clip-base").all()
        }
        assert variants["match-3::clip-base::instant"].distribution_weight > variants["match-3::clip-base::cinematic"].distribution_weight
        assert round(
            variants["match-3::clip-base::instant"].distribution_weight
            + variants["match-3::clip-base::cinematic"].distribution_weight,
            4,
        ) == 1.0
        assert variants["match-3::clip-base::instant"].metadata_json["variant_winner_score"] > 0.0
        assert variants["match-3::clip-base::instant"].metadata_json["global_exposure_feedback"] >= 0.0

        winner = variants["match-3::clip-base::cinematic"]
        winner.is_winner = True
        session.commit()

        service.refresh_clip_state(clip)
        locked_variants = {
            variant.variant_id: variant
            for variant in session.query(ClipVariant).filter(ClipVariant.base_clip_id == "match-3::clip-base").all()
        }
        assert locked_variants["match-3::clip-base::cinematic"].distribution_weight == 1.0
        assert locked_variants["match-3::clip-base::instant"].distribution_weight == 0.0


def test_attention_orchestrator_preserves_exploration_floor_for_five_variant_bursts() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[ClipVariant.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        session.add_all(
            [
                ClipVariant(
                    variant_id="match-4::clip-base::instant",
                    base_clip_id="match-4::clip-base",
                    format_type="instant",
                    viral_score=96.0,
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json={},
                ),
                ClipVariant(
                    variant_id="match-4::clip-base::cinematic",
                    base_clip_id="match-4::clip-base",
                    format_type="cinematic",
                    viral_score=84.0,
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json={},
                ),
                ClipVariant(
                    variant_id="match-4::clip-base::debate",
                    base_clip_id="match-4::clip-base",
                    format_type="debate",
                    viral_score=81.0,
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json={},
                ),
                ClipVariant(
                    variant_id="match-4::clip-base::tactical",
                    base_clip_id="match-4::clip-base",
                    format_type="tactical",
                    viral_score=78.0,
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json={},
                ),
                ClipVariant(
                    variant_id="match-4::clip-base::meme",
                    base_clip_id="match-4::clip-base",
                    format_type="meme",
                    viral_score=75.0,
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json={},
                ),
            ]
        )
        session.commit()

        service = AttentionOrchestratorService(
            state_store=InMemoryGlobalFeedStateStore(),
            session=session,
        )
        clip = ContentAgent(
            clip_id="match-4::clip-base",
            creator_id="creator-4",
            quality=0.8,
            format="instant_clip",
            trust=0.96,
            velocity=1.9,
            age_hours=1.0,
        ).as_clip()

        service.refresh_clip_state(clip)
        variants = list(
            session.query(ClipVariant)
            .filter(ClipVariant.base_clip_id == "match-4::clip-base")
            .order_by(ClipVariant.viral_score.desc())
            .all()
        )

        assert len(variants) == 5
        assert round(sum(variant.distribution_weight for variant in variants), 4) == 1.0
        for variant in variants[1:]:
            assert variant.distribution_weight >= 0.2


def test_attention_orchestrator_persists_variant_feedback_into_clip_metadata() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[ClipVariant.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        session.add_all(
            [
                ClipVariant(
                    variant_id="match-5::clip-base::instant",
                    base_clip_id="match-5::clip-base",
                    format_type="instant",
                    viral_score=91.0,
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json={},
                ),
                ClipVariant(
                    variant_id="match-5::clip-base::debate",
                    base_clip_id="match-5::clip-base",
                    format_type="debate",
                    viral_score=73.0,
                    distribution_weight=0.2,
                    promotion_status="exploring",
                    promotion_enabled=True,
                    pushed_to_trending=False,
                    is_winner=False,
                    metadata_json={},
                ),
            ]
        )
        session.commit()

        service = AttentionOrchestratorService(
            state_store=InMemoryGlobalFeedStateStore(),
            session=session,
        )
        clip = ContentAgent(
            clip_id="match-5::clip-base",
            creator_id="creator-5",
            quality=0.74,
            format="instant_clip",
            trust=0.94,
            velocity=1.8,
            age_hours=1.0,
        ).as_clip()

        state = service.refresh_clip_state(clip)

        assert state.metadata["variant_winner_score"] > 0.0
        assert state.metadata["global_exposure_feedback"] >= 0.0
        assert state.metadata["variant_budget_splits"]


def test_attention_orchestrator_enforces_agent_feed_cap_when_humans_are_available() -> None:
    service = AttentionOrchestratorService(state_store=InMemoryGlobalFeedStateStore())
    service.update_config(
        AttentionOrchestratorConfigUpdateRequest(
            max_agent_feed_ratio=0.25,
            min_human_exposure_guarantee=0.75,
        )
    )

    human_a = ContentAgent(
        clip_id="human-a",
        creator_id="creator-human-a",
        quality=0.70,
        format="instant_clip",
        trust=0.92,
        velocity=0.8,
        age_hours=1.0,
    ).as_clip()
    human_a.metadata["origin"] = "human_creator"
    human_b = ContentAgent(
        clip_id="human-b",
        creator_id="creator-human-b",
        quality=0.68,
        format="instant_clip",
        trust=0.9,
        velocity=0.78,
        age_hours=1.0,
    ).as_clip()
    human_b.metadata["origin"] = "human_creator"
    human_c = ContentAgent(
        clip_id="human-c",
        creator_id="creator-human-c",
        quality=0.66,
        format="instant_clip",
        trust=0.9,
        velocity=0.76,
        age_hours=1.0,
    ).as_clip()
    human_c.metadata["origin"] = "human_creator"

    agent_a = ContentAgent(
        clip_id="agent-a",
        creator_id="agent-creator-a",
        quality=0.98,
        format="instant_clip",
        trust=0.98,
        velocity=2.2,
        age_hours=1.0,
    ).as_clip()
    agent_a.metadata.update({"origin": "creator_agent", "is_agent_generated": True, "agent_id": "agent-001"})
    agent_b = ContentAgent(
        clip_id="agent-b",
        creator_id="agent-creator-b",
        quality=0.96,
        format="instant_clip",
        trust=0.97,
        velocity=2.0,
        age_hours=1.0,
    ).as_clip()
    agent_b.metadata.update({"origin": "creator_agent", "is_agent_generated": True, "agent_id": "agent-002"})

    feed = service.generate_feed(
        user=SimpleNamespace(preferences={}),
        clips=[agent_a, agent_b, human_a, human_b, human_c],
        limit=4,
    )

    agent_count = sum(1 for clip in feed if clip.metadata.get("origin") == "creator_agent")
    human_count = sum(1 for clip in feed if clip.metadata.get("origin") == "human_creator")

    assert len(feed) == 4
    assert agent_count <= 1
    assert human_count >= 3


def test_orchestrator_router_reads_updates_config_and_returns_metrics() -> None:
    app = FastAPI()
    app.include_router(orchestrator_router)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[User.__table__])
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    admin = User(
        id="admin-1",
        email="admin@example.com",
        username="admin",
        password_hash="hashed",
        role=UserRole.ADMIN,
    )

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin

    with session_factory() as session:
        service = AttentionOrchestratorService(
            state_store=InMemoryGlobalFeedStateStore(),
            session=session,
        )
        clip = ContentAgent(
            clip_id="match-4::clip-router",
            creator_id="creator-router",
            quality=0.65,
            format="instant_clip",
            trust=0.9,
            velocity=0.9,
            age_hours=3.0,
        ).as_clip()
        service.refresh_clip_state(clip)
        app.state.attention_orchestrator_store = service.state_store

    with TestClient(app) as client:
        config_response = client.get("/orchestrator/config")
        update_response = client.post("/orchestrator/config", json={"moment_boost": 1.8})
        metrics_response = client.get("/orchestrator/metrics")

    assert config_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["moment_boost"] == 1.8
    assert metrics_response.status_code == 200
    assert metrics_response.json()["clip_count"] == 1
    assert metrics_response.json()["sample_clips"][0]["clip_id"] == "match-4::clip-router"
