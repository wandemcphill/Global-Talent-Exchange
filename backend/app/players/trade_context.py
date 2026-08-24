from __future__ import annotations

from contextvars import ContextVar


_player_share_idempotency_key: ContextVar[str | None] = ContextVar(
    "player_share_idempotency_key",
    default=None,
)


def set_player_share_idempotency_key(value: str | None) -> None:
    normalized = value.strip() if isinstance(value, str) else None
    _player_share_idempotency_key.set(normalized or None)


def consume_player_share_idempotency_key() -> str | None:
    value = _player_share_idempotency_key.get()
    _player_share_idempotency_key.set(None)
    return value


__all__ = ["consume_player_share_idempotency_key", "set_player_share_idempotency_key"]
