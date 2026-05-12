from __future__ import annotations

import os
from datetime import datetime, timezone

from app.core.config import load_settings
from app.ingestion.models import Player
from app.value_engine.models import PlayerProfileContext, ReferenceValueContext
from app.value_engine.read_models import PlayerValueSnapshotRecord
from app.value_engine.real_player_bridge import RealPlayerValuationAdapter


def _config():
    settings = load_settings(environ={**os.environ, "GTE_DATABASE_URL": "sqlite+pysqlite:///:memory:"})
    return settings.value_engine_weighting


def _player(*, real_player_tier: str = "featured", is_real_player: bool = True) -> Player:
    return Player(
        id="player-1",
        source_provider="curated-feed",
        provider_external_id="player-1",
        full_name="Victor Test",
        short_name="V. Test",
        is_real_player=is_real_player,
        real_player_tier=real_player_tier,
    )


class _StubScorer:
    def __init__(
        self,
        *,
        profile_baseline_market_value_eur: float,
        age_curve_multiplier: float = 1.18,
        competition_quality_multiplier: float = 1.08,
        club_quality_multiplier: float = 1.04,
        visibility_multiplier: float = 1.01,
    ) -> None:
        self.profile_baseline_market_value_eur = profile_baseline_market_value_eur
        self.age_curve_multiplier = age_curve_multiplier
        self.competition_quality_multiplier = competition_quality_multiplier
        self.club_quality_multiplier = club_quality_multiplier
        self.visibility_multiplier = visibility_multiplier

    def _profile_baseline_market_value_eur(self, _profile: PlayerProfileContext) -> float:
        return self.profile_baseline_market_value_eur

    def _age_curve_multiplier(self, _age_years: float | None) -> float:
        return self.age_curve_multiplier

    def _competition_quality_multiplier(self, _profile: PlayerProfileContext) -> float:
        return self.competition_quality_multiplier

    def _club_quality_multiplier(self, _profile: PlayerProfileContext) -> float:
        return self.club_quality_multiplier

    def _visibility_multiplier(self, _profile: PlayerProfileContext) -> float:
        return self.visibility_multiplier

    def _normalize_lookup_key(self, value: str) -> str:
        return value.strip().lower().replace("-", "_").replace(" ", "_")


def test_real_player_bridge_is_deterministic_for_identical_inputs() -> None:
    adapter = RealPlayerValuationAdapter(config=_config())
    adapter.scorer = _StubScorer(profile_baseline_market_value_eur=48_000_000.0)

    profile = PlayerProfileContext(
        age_years=24.0,
        position_family="forward",
        position_subrole="striker",
        competition_tier="league_a",
        club_tier="elite",
        profile_completeness_score=0.82,
        player_class="established",
    )
    reference_context = ReferenceValueContext(
        market_value_eur=60_000_000.0,
        source="reference_market_value_eur",
        confidence_tier="direct_verified_reference",
        confidence_score=88.0,
    )

    first = adapter.build(
        player=_player(),
        profile=profile,
        reference_context=reference_context,
        reference_market_value_eur=60_000_000.0,
        previous_snapshot=None,
    )
    second = adapter.build(
        player=_player(),
        profile=profile,
        reference_context=reference_context,
        reference_market_value_eur=60_000_000.0,
        previous_snapshot=None,
    )

    assert first == second
    assert first is not None
    assert first.bridge_market_value_eur == 61_508_798.4
    assert first.base_value_credits == 51.207
    assert first.floor_credits == 41.0
    assert first.ceiling_credits == 57.2
    assert first.actions == ()


def test_real_player_bridge_applies_ceiling_guard_and_smoothing() -> None:
    adapter = RealPlayerValuationAdapter(config=_config())
    adapter.scorer = _StubScorer(profile_baseline_market_value_eur=60_000_000.0)

    profile = PlayerProfileContext(
        age_years=22.0,
        position_family="forward",
        competition_tier="league_a",
        club_tier="elite",
        profile_completeness_score=0.90,
        player_class="prospect",
    )
    reference_context = ReferenceValueContext(
        market_value_eur=20_000_000.0,
        source="player.current_market_reference_value",
        confidence_tier="direct_verified_reference",
        confidence_score=86.0,
    )
    previous_snapshot = PlayerValueSnapshotRecord(
        id="snapshot-prev",
        player_id="player-1",
        player_name="Victor Test",
        as_of=datetime(2026, 3, 20, tzinfo=timezone.utc),
        previous_credits=210.0,
        target_credits=210.0,
        movement_pct=0.0,
        football_truth_value_credits=210.0,
        market_signal_value_credits=210.0,
        breakdown_json={"real_player_valuation": {"bridge_market_value_eur": 21_000_000.0}},
        drivers_json=[],
        reason_codes_json=[],
    )

    result = adapter.build(
        player=_player(real_player_tier="elite"),
        profile=profile,
        reference_context=reference_context,
        reference_market_value_eur=20_000_000.0,
        previous_snapshot=previous_snapshot,
    )

    assert result is not None
    assert result.bridge_market_value_eur == 21_700_000.0
    assert result.base_value_credits == 13.36
    assert result.actions == ("ceiling_guard", "smoothed")
    assert result.previous_bridge_market_value_eur == 21_000_000.0


def test_real_player_bridge_rejects_heuristic_reference_for_real_players() -> None:
    adapter = RealPlayerValuationAdapter(config=_config())
    adapter.scorer = _StubScorer(profile_baseline_market_value_eur=60_000_000.0)

    result = adapter.build(
        player=_player(real_player_tier="elite"),
        profile=PlayerProfileContext(),
        reference_context=ReferenceValueContext(
            market_value_eur=20_000_000.0,
            source="heuristic_profile_baseline",
            confidence_tier="heuristic_only",
            confidence_score=38.0,
            blended_with_profile_baseline=True,
        ),
        reference_market_value_eur=20_000_000.0,
        previous_snapshot=None,
    )

    assert result is None


def test_real_player_bridge_is_skipped_for_non_real_players() -> None:
    adapter = RealPlayerValuationAdapter(config=_config())
    result = adapter.build(
        player=_player(is_real_player=False),
        profile=PlayerProfileContext(),
        reference_context=ReferenceValueContext(
            market_value_eur=15_000_000.0,
            source="reference_market_value_eur",
            confidence_tier="direct_verified_reference",
            confidence_score=88.0,
        ),
        reference_market_value_eur=15_000_000.0,
        previous_snapshot=None,
    )

    assert result is None
