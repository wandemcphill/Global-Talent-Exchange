from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.live_matches import router as live_router
from app.live_matches.generated_stream_policy import GENERATED_LIVE_MATCHES_FLAG
from app.routes import match_viewer as match_viewer_router


class _Metrics:
    def __init__(self) -> None:
        self.generated_results: list[str] = []

    def record_legacy_match_runtime_generated_match(self, *, result: str) -> None:
        self.generated_results.append(result)


class _Hub:
    def __init__(self) -> None:
        self.started: list[dict[str, object]] = []

    def get_state(self, match_id: str):
        return None

    def start_synthetic_stream(self, **kwargs) -> None:
        self.started.append(kwargs)


def _app(metrics: _Metrics | None = None):
    return SimpleNamespace(state=SimpleNamespace(metrics=metrics))


def test_generated_live_match_bootstrap_is_quarantined_by_default(monkeypatch) -> None:
    monkeypatch.delenv(GENERATED_LIVE_MATCHES_FLAG, raising=False)
    monkeypatch.setattr(
        live_router,
        "ensure_infinite_league_runtime",
        lambda app: pytest.fail("generated runtime must stay hidden without the internal flag"),
    )
    metrics = _Metrics()
    hub = _Hub()

    assert (
        live_router._bootstrap_infinite_league_stream(
            _app(metrics),
            hub,
            "missing-match",
        )
        is False
    )

    assert hub.started == []
    assert metrics.generated_results == ["quarantined"]


def test_generated_live_match_bootstrap_requires_internal_flag(monkeypatch) -> None:
    monkeypatch.setenv(GENERATED_LIVE_MATCHES_FLAG, "1")
    stream = SimpleNamespace(
        match_id="internal-generated-match",
        home_team_id="home",
        away_team_id="away",
        home_team_name="Home",
        away_team_name="Away",
        base_home_possession=55,
        base_away_possession=45,
        events=[],
        atmosphere_profile="internal",
        sync_strategy="deterministic_playback",
        checkpoint_interval_seconds=15,
        max_latency_ms=320,
    )
    monkeypatch.setattr(
        live_router,
        "ensure_infinite_league_runtime",
        lambda app: SimpleNamespace(live_stream=lambda match_id: stream),
    )
    hub = _Hub()

    assert live_router._bootstrap_infinite_league_stream(_app(_Metrics()), hub, "match-1") is True

    assert len(hub.started) == 1
    assert hub.started[0]["match_id"] == "internal-generated-match"
    assert hub.started[0]["read_only"] is True


def test_match_viewer_does_not_resolve_infinite_league_by_default(monkeypatch) -> None:
    monkeypatch.delenv(GENERATED_LIVE_MATCHES_FLAG, raising=False)
    monkeypatch.setattr(
        match_viewer_router,
        "ensure_infinite_league_runtime",
        lambda app: pytest.fail("match viewer must not read generated live streams by default"),
    )
    monkeypatch.setattr(
        match_viewer_router,
        "ensure_live_match_hub",
        lambda app: SimpleNamespace(get_state=lambda match_key: None),
    )

    resolved = match_viewer_router._resolve_live_view_state(
        match_key="missing-match",
        request=SimpleNamespace(app=_app()),
        match=None,
        service=object(),
    )

    assert resolved is None
