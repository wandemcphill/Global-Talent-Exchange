"""Phase B regression tests for live stream cursor handling.

Reconnecting spectators resume from a cursor. A negative cursor used to slice from the
end of the event log (``events[-3:]``), silently replaying the tail of the match, and
malformed cached entries were dropped without a trace.
"""

from __future__ import annotations

import logging

from app.live_matches.service import LiveMatchHub


class _DictCacheBackend:
    """Minimal in-process CacheBackend; no ``client`` attribute, so the JSON path runs."""

    enabled = True

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        del ttl_seconds
        self._values[key] = value

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self._values.pop(key, None)

    def increment(self, key: str, amount: int = 1, ttl_seconds: int | None = None) -> int:
        del key, amount, ttl_seconds
        return 0

    def ping(self) -> bool:
        return True


def _hub() -> LiveMatchHub:
    return LiveMatchHub(cache_backend=_DictCacheBackend())


def _seed_cache(hub: LiveMatchHub, match_id: str, events: list[dict]) -> None:
    hub._hot_cache.append_match_events(match_id, events, ttl_seconds=900)


def _event(sequence: int) -> dict:
    return {
        "match_id": "match-cursor",
        "event_id": f"match-cursor:{sequence:03d}",
        "minute": sequence,
        "event_type": "goal",
        "home_score": sequence,
        "away_score": 0,
        "commentary": f"Event {sequence}",
        "clock_label": f"{sequence}'",
    }


def test_negative_cursor_does_not_replay_the_tail_of_the_match() -> None:
    hub = _hub()
    _seed_cache(hub, "match-cursor", [_event(i) for i in range(1, 6)])

    events, next_cursor = hub.get_events_since("match-cursor", -3)

    assert next_cursor == 5
    assert [event.minute for event in events] == [1, 2, 3, 4, 5]


def test_cursor_resumes_from_the_requested_position() -> None:
    hub = _hub()
    _seed_cache(hub, "match-cursor", [_event(i) for i in range(1, 6)])

    events, next_cursor = hub.get_events_since("match-cursor", 3)

    assert next_cursor == 5
    assert [event.minute for event in events] == [4, 5]


def test_cursor_beyond_the_log_yields_nothing() -> None:
    hub = _hub()
    _seed_cache(hub, "match-cursor", [_event(i) for i in range(1, 4)])

    events, next_cursor = hub.get_events_since("match-cursor", 99)

    assert events == []
    assert next_cursor == 3


def test_unknown_match_returns_the_cursor_unchanged() -> None:
    events, next_cursor = _hub().get_events_since("no-such-match", 7)

    assert events == []
    assert next_cursor == 7


def test_malformed_cached_events_are_reported_not_silently_swallowed(caplog) -> None:
    hub = _hub()
    _seed_cache(hub, "match-cursor", [_event(1), {"garbage": True}, _event(3)])

    with caplog.at_level(logging.WARNING, logger="app.live_matches.service"):
        events, next_cursor = hub.get_events_since("match-cursor", 0)

    assert [event.minute for event in events] == [1, 3]
    assert next_cursor == 3
    assert any("malformed_cached_events" in record.getMessage() for record in caplog.records)
