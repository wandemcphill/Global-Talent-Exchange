from __future__ import annotations

from backend.app.club_identity.dynasty.services.dynasty_detector import DynastyDetectorService
from backend.app.club_identity.models.dynasty_models import EraLabel


def test_4_season_rolling_window_dynasty_detection(rolling_window_seasons) -> None:
    profile = DynastyDetectorService().build_profile(rolling_window_seasons)

    assert profile.current_era_label is EraLabel.DOMINANT_ERA
    assert profile.current_snapshot is not None
    assert profile.current_snapshot.metrics.window_start_season_id == rolling_window_seasons[1].season_id
    assert profile.current_snapshot.metrics.window_end_season_id == rolling_window_seasons[-1].season_id


def test_emerging_power_trigger(emerging_power_seasons) -> None:
    profile = DynastyDetectorService().build_profile(emerging_power_seasons)

    assert profile.current_era_label is EraLabel.EMERGING_POWER
    assert profile.active_dynasty_flag is True


def test_continental_dynasty_trigger(continental_dynasty_seasons) -> None:
    profile = DynastyDetectorService().build_profile(continental_dynasty_seasons)

    assert profile.current_era_label is EraLabel.CONTINENTAL_DYNASTY
    assert "Champions League" in " ".join(profile.reasons)


def test_global_dynasty_trigger(global_dynasty_seasons) -> None:
    profile = DynastyDetectorService().build_profile(global_dynasty_seasons)

    assert profile.current_era_label is EraLabel.GLOBAL_DYNASTY
    assert profile.dynasty_score >= 100


def test_fallen_giant_trigger(fallen_giant_seasons) -> None:
    profile = DynastyDetectorService().build_profile(fallen_giant_seasons)

    assert profile.current_era_label is EraLabel.FALLEN_GIANT
    assert profile.active_dynasty_flag is False
    assert profile.eras[-1].era_label is EraLabel.FALLEN_GIANT


def test_streak_reset_logic(streak_reset_seasons) -> None:
    profile = DynastyDetectorService().build_profile(streak_reset_seasons)

    assert profile.active_streaks.top_four == 1
    assert profile.active_streaks.trophy_seasons == 1
    assert profile.active_streaks.positive_reputation == 1
