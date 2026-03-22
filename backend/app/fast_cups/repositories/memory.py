from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from threading import RLock

from app.fast_cups.models.domain import FastCup, FastCupDivision, FastCupNotFoundError
from app.fast_cups.repositories.base import FastCupRepository


class InMemoryFastCupRepository(FastCupRepository):
    def __init__(self) -> None:
        self._cups: dict[str, FastCup] = {}
        self._lock = RLock()

    def save(self, cup: FastCup) -> FastCup:
        with self._lock:
            self._cups[cup.cup_id] = replace(cup)
            return self._cups[cup.cup_id]

    def save_many(self, cups: tuple[FastCup, ...] | list[FastCup]) -> tuple[FastCup, ...]:
        return tuple(self.save(cup) for cup in cups)

    def get(self, cup_id: str) -> FastCup:
        with self._lock:
            try:
                cup = self._cups[cup_id]
            except KeyError as exc:
                raise FastCupNotFoundError(f"Fast cup '{cup_id}' was not found") from exc
            return replace(cup)

    def exists(self, cup_id: str) -> bool:
        with self._lock:
            return cup_id in self._cups

    def list_all(self) -> tuple[FastCup, ...]:
        with self._lock:
            return tuple(replace(cup) for cup in self._cups.values())

    def list_upcoming(
        self,
        *,
        now: datetime,
        division: FastCupDivision | None = None,
        size: int | None = None,
    ) -> tuple[FastCup, ...]:
        with self._lock:
            cups = [
                replace(cup)
                for cup in self._cups.values()
                if cup.slot.kickoff_at >= now
                and (division is None or cup.division is division)
                and (size is None or cup.size == size)
            ]
        return tuple(sorted(cups, key=lambda cup: (cup.slot.kickoff_at, cup.division.value, cup.size)))
