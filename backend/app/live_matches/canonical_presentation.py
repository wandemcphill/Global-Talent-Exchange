"""Map canonical match and execution rows onto one broadcast presentation.

The match lifecycle, the execution row, and the frame the viewer happens to be
holding are three different facts. A scheduled fixture must stay pre-match even
when a precomputed timeline already contains a 90th-minute frame, and an
unknown execution status must not be reported as full time.
"""

from __future__ import annotations

from dataclasses import dataclass

_PRESENTATION_BY_EXECUTION_STATUS = {
    "scheduled": "pre_match",
    "in_progress": "live",
    "paused": "paused",
    "halted": "halted",
    "completed": "full_time",
    "cancelled": "cancelled",
    "abandoned": "abandoned",
}

_API_STATUS_BY_PRESENTATION = {
    "pre_match": "SCHEDULED",
    "live": "LIVE",
    "paused": "PAUSED",
    "halted": "HALTED",
    "full_time": "FT",
    "cancelled": "CANCELLED",
    "abandoned": "ABANDONED",
    "unknown": "UNKNOWN",
}


@dataclass(frozen=True, slots=True)
class CanonicalPresentation:
    presentation: str
    api_status: str
    broadcast_phase: str
    is_live: bool
    is_terminal: bool
    inconsistent: bool


def resolve_canonical_presentation(
    *,
    match_status: str | None,
    execution_status: str | None,
    clock_phase: str | None,
) -> CanonicalPresentation:
    """Combine the fixture status and the execution status without promoting unfinished work to full time."""

    match_state = str(match_status or "").strip().lower()
    execution_state = str(execution_status or "").strip().lower()
    phase = str(clock_phase or "").strip().lower()
    inconsistent = False

    presentation = _PRESENTATION_BY_EXECUTION_STATUS.get(execution_state)
    if presentation is None:
        presentation = "unknown"
        inconsistent = True

    # A fixture row that was marked completed while its execution is still
    # scheduled, live, paused, or halted is a disagreement. Keep the unfinished
    # execution on screen. Do not let the fixture row close the broadcast.
    if presentation in {"pre_match", "live", "paused", "halted", "unknown"} and match_state == "completed":
        inconsistent = True

    # The reverse disagreement is the same kind of fault: an execution row that
    # says completed while the fixture has not reached a terminal status.
    if presentation == "full_time" and match_state not in {"completed", ""}:
        inconsistent = True
        if match_state == "scheduled":
            presentation = "pre_match"
        elif match_state == "in_progress":
            presentation = "live"
        elif match_state == "paused":
            presentation = "paused"
        elif match_state in {"cancelled", "abandoned"}:
            presentation = match_state
        else:
            presentation = "unknown"

    # Halftime is a pause. An execution left in_progress with a halftime clock
    # must not be painted as a running match or as full time.
    if phase == "halftime" and presentation in {"live", "paused"}:
        if presentation != "paused":
            inconsistent = True
        presentation = "paused"

    if phase == "completed" and presentation not in {"full_time", "cancelled", "abandoned"}:
        inconsistent = True

    if presentation == "full_time":
        broadcast_phase = "full_time"
        api_status = "FT"
    elif presentation == "pre_match":
        broadcast_phase = "pre_match"
        api_status = "SCHEDULED"
    elif presentation == "paused" and phase == "halftime":
        broadcast_phase = "halftime"
        api_status = "HALFTIME"
    elif presentation == "paused":
        broadcast_phase = phase or "paused"
        api_status = "PAUSED"
    elif presentation == "live":
        broadcast_phase = phase if phase and phase not in {"completed", "pre_match"} else "first_half"
        api_status = "LIVE"
    elif presentation == "halted":
        broadcast_phase = "halted"
        api_status = "HALTED"
    elif presentation in {"cancelled", "abandoned"}:
        broadcast_phase = presentation
        api_status = _API_STATUS_BY_PRESENTATION[presentation]
    else:
        broadcast_phase = "unknown"
        api_status = "UNKNOWN"

    return CanonicalPresentation(
        presentation=presentation,
        api_status=api_status,
        broadcast_phase=broadcast_phase,
        is_live=presentation == "live",
        is_terminal=presentation in {"full_time", "cancelled", "abandoned"},
        inconsistent=inconsistent,
    )


def canonical_sample_time_seconds(
    *,
    first_time_seconds: float,
    last_time_seconds: float,
    duration_seconds: float,
    last_clock_minute: float,
    clock_minute: int,
    target_end_minute: int,
    presentation: str,
) -> float:
    """Pick the timeline position that matches the persisted execution, not the last stored frame."""

    span = max(float(duration_seconds), float(last_time_seconds), 0.0)
    if presentation == "pre_match" or int(clock_minute) <= 0:
        return max(0.0, float(first_time_seconds))
    if presentation == "full_time":
        return span
    target = max(1, int(target_end_minute))
    # A checkpoint rebuild only contains frames up to the current minute.
    # Sampling that timeline as a fraction of a full 90 minutes would rewind it.
    if abs(float(last_clock_minute) - float(clock_minute)) <= 1.5 and int(clock_minute) < target:
        return float(last_time_seconds)
    ratio = min(1.0, max(0.0, float(clock_minute) / float(target)))
    return round(span * ratio, 2)


def viewer_clock_is_behind(*, last_clock_minute: float | None, clock_minute: int) -> bool:
    """A stored viewer that ends before the execution checkpoint cannot be the authority."""

    if last_clock_minute is None:
        return True
    return float(last_clock_minute) + 1.0 < float(clock_minute)
