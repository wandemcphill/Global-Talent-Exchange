from __future__ import annotations

from datetime import datetime
from typing import Protocol

from backend.app.fast_cups.models.domain import FastCup, FastCupDivision


class FastCupRepository(Protocol):
    def save(self, cup: FastCup) -> FastCup: ...

    def save_many(self, cups: tuple[FastCup, ...] | list[FastCup]) -> tuple[FastCup, ...]: ...

    def get(self, cup_id: str) -> FastCup: ...

    def exists(self, cup_id: str) -> bool: ...

    def list_all(self) -> tuple[FastCup, ...]: ...

    def list_upcoming(
        self,
        *,
        now: datetime,
        division: FastCupDivision | None = None,
        size: int | None = None,
    ) -> tuple[FastCup, ...]: ...


__all__ = ["FastCupRepository"]
