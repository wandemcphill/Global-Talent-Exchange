"""In-process health for the simulation worker.

The API process does not share this memory. Operators read the worker log line,
and the database-backed counts come from AutonomousMatchExecutionService.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any

_LOCK = Lock()
_STATE: dict[str, Any] = {
    "mode": "stopped",
    "cycles": 0,
    "failures": 0,
    "last_successful_poll_at": None,
    "last_checkpoint_advancement_at": None,
    "last_error": None,
    "last_advanced": 0,
    "last_started": 0,
    "last_failed": 0,
}


def note_worker_mode(mode: str) -> None:
    with _LOCK:
        _STATE["mode"] = mode


def record_worker_cycle(
    *,
    advanced: int = 0,
    started: int = 0,
    failed: int = 0,
    error: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _LOCK:
        _STATE["cycles"] = int(_STATE["cycles"]) + 1
        _STATE["last_advanced"] = int(advanced)
        _STATE["last_started"] = int(started)
        _STATE["last_failed"] = int(failed)
        if error:
            _STATE["failures"] = int(_STATE["failures"]) + 1
            _STATE["last_error"] = error
            return
        _STATE["last_successful_poll_at"] = now
        _STATE["last_error"] = None
        if int(advanced) > 0 or int(started) > 0:
            _STATE["last_checkpoint_advancement_at"] = now


def worker_health_snapshot() -> dict[str, Any]:
    with _LOCK:
        return dict(_STATE)
