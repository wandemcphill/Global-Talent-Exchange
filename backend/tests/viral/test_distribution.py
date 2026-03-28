from __future__ import annotations

from app.viral.distribution import (
    ClipDistributionManager,
    InMemoryClipDistributionStore,
    TEST_STAGE,
    EXPAND_STAGE,
    VIRAL_STAGE,
)


def _manager(**kwargs) -> ClipDistributionManager:
    return ClipDistributionManager(store=InMemoryClipDistributionStore(), **kwargs)


def test_distribution_manager_promotes_caps_by_stage() -> None:
    manager = _manager()

    test_state = manager.refresh_distribution(
        clip_id="clip-test",
        viral_score=42,
        analytics={"view_count": 120, "completion_rate": 0.72, "share_rate": 0.03, "skips": 18},
        performance_tier="iterating",
    )
    expand_state = manager.refresh_distribution(
        clip_id="clip-expand",
        viral_score=88,
        analytics={"view_count": 420, "completion_rate": 0.81, "share_rate": 0.05, "skips": 44},
        performance_tier="high_retention",
    )
    viral_state = manager.refresh_distribution(
        clip_id="clip-viral",
        viral_score=135,
        analytics={"view_count": 1200, "completion_rate": 0.94, "share_rate": 0.12, "skips": 48},
        performance_tier="high_retention",
    )

    assert test_state.expansion_stage == TEST_STAGE
    assert 100 <= test_state.impressions_cap <= 500
    assert expand_state.expansion_stage == EXPAND_STAGE
    assert 1_000 <= expand_state.impressions_cap <= 10_000
    assert viral_state.expansion_stage == VIRAL_STAGE
    assert 10_000 <= viral_state.impressions_cap <= 1_000_000


def test_distribution_manager_freezes_when_performance_drops() -> None:
    manager = _manager(min_impressions_before_freeze=10)

    seeded = manager.refresh_distribution(
        clip_id="clip-freeze",
        viral_score=82,
        analytics={"view_count": 200, "completion_rate": 0.78, "share_rate": 0.03, "skips": 24},
        performance_tier="iterating",
    )
    manager.allocate_impressions("clip-freeze", count=seeded.impressions_cap)

    frozen = manager.refresh_distribution(
        clip_id="clip-freeze",
        viral_score=82,
        analytics={"view_count": 200, "completion_rate": 0.2, "share_rate": 0.002, "skips": 160},
        performance_tier="retention_risk",
    )

    assert frozen.frozen is True
    assert frozen.freeze_reason == "performance_drop"
    assert manager.is_eligible(frozen) is False


def test_distribution_manager_does_not_overshoot_cap() -> None:
    manager = _manager()

    state = manager.refresh_distribution(
        clip_id="clip-cap",
        viral_score=24,
        analytics={"view_count": 90, "completion_rate": 0.69, "share_rate": 0.02, "skips": 20},
        performance_tier="iterating",
    )
    state.impressions_cap = 3
    manager.store.save(state)

    manager.allocate_impressions("clip-cap", count=1)
    manager.allocate_impressions("clip-cap", count=4)
    updated = manager.store.load("clip-cap")

    assert updated is not None
    assert updated.impressions_served == 3
    assert updated.remaining_impressions == 0
    assert manager.is_eligible(updated) is False


def test_distribution_manager_preserves_existing_cap_within_stage_refresh() -> None:
    manager = _manager()

    seeded = manager.refresh_distribution(
        clip_id="clip-strict-cap",
        viral_score=24,
        analytics={"view_count": 90, "completion_rate": 0.69, "share_rate": 0.02, "skips": 20},
        performance_tier="iterating",
    )
    seeded.impressions_cap = 1
    seeded.impressions_served = 0
    manager.store.save(seeded)

    refreshed = manager.refresh_distribution(
        clip_id="clip-strict-cap",
        viral_score=24,
        analytics={"view_count": 90, "completion_rate": 0.69, "share_rate": 0.02, "skips": 20},
        performance_tier="iterating",
    )

    assert refreshed.expansion_stage == TEST_STAGE
    assert refreshed.impressions_cap == 1


def test_distribution_manager_applies_cascade_cap_multiplier() -> None:
    manager = _manager()

    base_state = manager.refresh_distribution(
        clip_id="clip-base",
        viral_score=88,
        analytics={"view_count": 420, "completion_rate": 0.81, "share_rate": 0.05, "skips": 44},
        performance_tier="high_retention",
    )
    boosted_state = manager.refresh_distribution(
        clip_id="clip-boosted",
        viral_score=88,
        analytics={"view_count": 420, "completion_rate": 0.81, "share_rate": 0.05, "skips": 44},
        performance_tier="high_retention",
        cap_multiplier=3,
    )

    assert boosted_state.impressions_cap == base_state.impressions_cap * 3


def test_distribution_manager_doubles_caps_for_moment_source() -> None:
    manager = _manager()

    base_state = manager.refresh_distribution(
        clip_id="clip-standard",
        viral_score=88,
        analytics={"view_count": 420, "completion_rate": 0.81, "share_rate": 0.05, "skips": 44},
        performance_tier="high_retention",
    )
    moment_state = manager.refresh_distribution(
        clip_id="clip-moment",
        viral_score=88,
        analytics={"view_count": 420, "completion_rate": 0.81, "share_rate": 0.05, "skips": 44},
        performance_tier="high_retention",
        clip_source="moment",
    )

    assert moment_state.impressions_cap == base_state.impressions_cap * 2


def test_distribution_manager_freezes_when_viral_score_drops_below_stage_threshold() -> None:
    manager = _manager()

    seeded = manager.refresh_distribution(
        clip_id="clip-viral-drop",
        viral_score=96,
        analytics={"view_count": 420, "completion_rate": 0.84, "share_rate": 0.06, "skips": 40},
        performance_tier="high_retention",
    )
    allocation = manager.allocate_impressions("clip-viral-drop", count=25)

    dropped = manager.refresh_distribution(
        clip_id="clip-viral-drop",
        viral_score=40,
        analytics={"view_count": 420, "completion_rate": 0.84, "share_rate": 0.06, "skips": 40},
        performance_tier="high_retention",
    )

    assert seeded.expansion_stage == EXPAND_STAGE
    assert allocation.allocated is True
    assert dropped.frozen is True
    assert dropped.freeze_reason == "viral_score_drop"
    assert dropped.impressions_cap == dropped.impressions_served
    assert manager.allocate_impressions("clip-viral-drop", count=1).allocated is False
