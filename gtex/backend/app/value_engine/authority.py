from __future__ import annotations

from typing import Any


def _coerce_positive_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    if candidate <= 0:
        return None
    return candidate


def authoritative_published_card_value_credits(
    *,
    summary_payload: dict[str, Any] | None = None,
    breakdown_payload: dict[str, Any] | None = None,
) -> float | None:
    summary_value = _coerce_positive_float((summary_payload or {}).get("published_card_value_credits"))
    if summary_value is not None:
        return round(summary_value, 2)
    breakdown_value = _coerce_positive_float((breakdown_payload or {}).get("published_card_value_credits"))
    if breakdown_value is not None:
        return round(breakdown_value, 2)
    return None


def authoritative_reference_credits(
    *,
    summary: Any | None = None,
    latest_snapshot: Any | None = None,
    summary_payload: dict[str, Any] | None = None,
    breakdown_payload: dict[str, Any] | None = None,
) -> float | None:
    published_value = authoritative_published_card_value_credits(
        summary_payload=summary_payload,
        breakdown_payload=breakdown_payload,
    )
    if published_value is not None:
        return published_value

    summary_value = _coerce_positive_float(getattr(summary, "current_value_credits", None))
    if summary_value is not None:
        return round(summary_value, 2)

    snapshot_value = _coerce_positive_float(getattr(latest_snapshot, "target_credits", None))
    if snapshot_value is not None:
        return round(snapshot_value, 2)

    return None


def real_player_requires_authoritative_value(player: Any | None) -> bool:
    return bool(getattr(player, "is_real_player", False))


def real_player_authoritative_value_missing(
    *,
    player: Any | None,
    summary: Any | None = None,
    latest_snapshot: Any | None = None,
    summary_payload: dict[str, Any] | None = None,
    breakdown_payload: dict[str, Any] | None = None,
) -> bool:
    if not real_player_requires_authoritative_value(player):
        return False
    return (
        authoritative_reference_credits(
            summary=summary,
            latest_snapshot=latest_snapshot,
            summary_payload=summary_payload,
            breakdown_payload=breakdown_payload,
        )
        is None
    )


__all__ = [
    "authoritative_published_card_value_credits",
    "authoritative_reference_credits",
    "real_player_authoritative_value_missing",
    "real_player_requires_authoritative_value",
]
