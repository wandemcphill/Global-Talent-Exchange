from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DateTime, Integer, JSON, Numeric, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from app.fast_cups.models.domain import (
    CupReward,
    FastCup,
    FastCupBracket,
    FastCupDivision,
    FastCupEntrant,
    FastCupMatch,
    FastCupNotFoundError,
    FastCupResultSummary,
    FastCupRound,
    FastCupSlot,
    FastCupStage,
    FastCupStatus,
    PayoutLedgerEvent,
)
from app.fast_cups.repositories.base import FastCupRepository
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FastCupRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fast_cup_records"
    __table_args__ = (UniqueConstraint("cup_id", name="uq_fast_cup_records_cup_id"),)

    cup_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    division: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    buy_in: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class DatabaseFastCupRepository(FastCupRepository):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, cup: FastCup) -> FastCup:
        payload = _serialize_value(cup)
        if not isinstance(payload, dict):
            raise TypeError("Fast cup payload serialization must produce a mapping.")
        with self._session_factory() as session:
            existing = session.scalar(select(FastCupRecord).where(FastCupRecord.cup_id == cup.cup_id))
            if existing is None:
                session.add(
                    FastCupRecord(
                        cup_id=cup.cup_id,
                        division=cup.division.value,
                        size=cup.size,
                        kickoff_at=_normalize_datetime(cup.slot.kickoff_at),
                        buy_in=cup.buy_in,
                        currency=cup.currency,
                        payload_json=payload,
                    )
                )
            else:
                existing.division = cup.division.value
                existing.size = cup.size
                existing.kickoff_at = _normalize_datetime(cup.slot.kickoff_at)
                existing.buy_in = cup.buy_in
                existing.currency = cup.currency
                existing.payload_json = payload
            session.commit()
        return _deserialize_fast_cup(payload)

    def save_many(self, cups: tuple[FastCup, ...] | list[FastCup]) -> tuple[FastCup, ...]:
        return tuple(self.save(cup) for cup in cups)

    def get(self, cup_id: str) -> FastCup:
        with self._session_factory() as session:
            row = session.scalar(select(FastCupRecord).where(FastCupRecord.cup_id == cup_id))
        if row is None:
            raise FastCupNotFoundError(f"Fast cup '{cup_id}' was not found")
        return _deserialize_fast_cup(row.payload_json)

    def exists(self, cup_id: str) -> bool:
        with self._session_factory() as session:
            return session.scalar(select(FastCupRecord.id).where(FastCupRecord.cup_id == cup_id)) is not None

    def list_all(self) -> tuple[FastCup, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(FastCupRecord).order_by(FastCupRecord.kickoff_at.asc(), FastCupRecord.division.asc(), FastCupRecord.size.asc())
            ).all()
        return tuple(_deserialize_fast_cup(row.payload_json) for row in rows)

    def list_upcoming(
        self,
        *,
        now: datetime,
        division: FastCupDivision | None = None,
        size: int | None = None,
    ) -> tuple[FastCup, ...]:
        statement = (
            select(FastCupRecord)
            .where(FastCupRecord.kickoff_at >= _normalize_datetime(now))
            .order_by(FastCupRecord.kickoff_at.asc(), FastCupRecord.division.asc(), FastCupRecord.size.asc())
        )
        if division is not None:
            statement = statement.where(FastCupRecord.division == division.value)
        if size is not None:
            statement = statement.where(FastCupRecord.size == size)
        with self._session_factory() as session:
            rows = session.scalars(statement).all()
        return tuple(_deserialize_fast_cup(row.payload_json) for row in rows)


def _serialize_value(value: object) -> object:
    if is_dataclass(value):
        return {key: _serialize_value(item) for key, item in asdict(value).items()}
    if isinstance(value, datetime):
        return _normalize_datetime(value).isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _deserialize_fast_cup(payload: dict[str, object]) -> FastCup:
    bracket_payload = payload.get("bracket")
    result_summary_payload = payload.get("result_summary")
    return FastCup(
        cup_id=str(payload["cup_id"]),
        title=str(payload["title"]),
        division=FastCupDivision(str(payload["division"])),
        size=int(payload["size"]),
        buy_in=Decimal(str(payload["buy_in"])),
        currency=str(payload["currency"]),
        slot=_deserialize_slot(_expect_dict(payload["slot"])),
        status=FastCupStatus(str(payload.get("status", FastCupStatus.REGISTRATION_OPEN.value))),
        entrants=tuple(_deserialize_entrant(_expect_dict(entry)) for entry in _expect_list(payload.get("entrants", []))),
        bracket=_deserialize_bracket(_expect_dict(bracket_payload)) if isinstance(bracket_payload, dict) else None,
        result_summary=_deserialize_result_summary(_expect_dict(result_summary_payload))
        if isinstance(result_summary_payload, dict)
        else None,
    )


def _deserialize_slot(payload: dict[str, object]) -> FastCupSlot:
    from app.common.enums.fixture_window import FixtureWindow

    return FastCupSlot(
        registration_opens_at=_parse_datetime(payload["registration_opens_at"]),
        registration_closes_at=_parse_datetime(payload["registration_closes_at"]),
        kickoff_at=_parse_datetime(payload["kickoff_at"]),
        expected_completion_at=_parse_datetime(payload["expected_completion_at"]),
        window=FixtureWindow(str(payload.get("window", FixtureWindow.FAST_CUP_OPEN.value))),
    )


def _deserialize_entrant(payload: dict[str, object]) -> FastCupEntrant:
    return FastCupEntrant(
        club_id=str(payload["club_id"]),
        club_name=str(payload["club_name"]),
        division=FastCupDivision(str(payload["division"])),
        rating=int(payload["rating"]),
        registered_at=_parse_datetime(payload["registered_at"]),
    )


def _deserialize_match(payload: dict[str, object]) -> FastCupMatch:
    home = payload.get("home")
    away = payload.get("away")
    winner = payload.get("winner")
    return FastCupMatch(
        tie_id=str(payload["tie_id"]),
        stage=FastCupStage(str(payload["stage"])),
        round_number=int(payload["round_number"]),
        slot_number=int(payload["slot_number"]),
        scheduled_at=_parse_datetime(payload["scheduled_at"]),
        presentation_min_minutes=int(payload["presentation_min_minutes"]),
        presentation_max_minutes=int(payload["presentation_max_minutes"]),
        home=_deserialize_entrant(_expect_dict(home)) if isinstance(home, dict) else None,
        away=_deserialize_entrant(_expect_dict(away)) if isinstance(away, dict) else None,
        winner=_deserialize_entrant(_expect_dict(winner)) if isinstance(winner, dict) else None,
        home_goals=_optional_int(payload.get("home_goals")),
        away_goals=_optional_int(payload.get("away_goals")),
        home_penalties=_optional_int(payload.get("home_penalties")),
        away_penalties=_optional_int(payload.get("away_penalties")),
        decided_by_penalties=bool(payload.get("decided_by_penalties", False)),
        penalties_if_tied=bool(payload.get("penalties_if_tied", True)),
        extra_time_allowed=bool(payload.get("extra_time_allowed", False)),
        key_moments=tuple(str(item) for item in _expect_list(payload.get("key_moments", []))),
        home_source_tie_id=_optional_str(payload.get("home_source_tie_id")),
        away_source_tie_id=_optional_str(payload.get("away_source_tie_id")),
    )


def _deserialize_round(payload: dict[str, object]) -> FastCupRound:
    return FastCupRound(
        stage=FastCupStage(str(payload["stage"])),
        round_number=int(payload["round_number"]),
        scheduled_at=_parse_datetime(payload["scheduled_at"]),
        presentation_max_minutes=int(payload["presentation_max_minutes"]),
        matches=tuple(_deserialize_match(_expect_dict(match)) for match in _expect_list(payload.get("matches", []))),
    )


def _deserialize_bracket(payload: dict[str, object]) -> FastCupBracket:
    champion = payload.get("champion")
    runner_up = payload.get("runner_up")
    semifinalists = payload.get("semifinalists", [])
    return FastCupBracket(
        rounds=tuple(_deserialize_round(_expect_dict(item)) for item in _expect_list(payload.get("rounds", []))),
        total_rounds=int(payload["total_rounds"]),
        total_matches=int(payload["total_matches"]),
        expected_duration_minutes=int(payload["expected_duration_minutes"]),
        simulated=bool(payload.get("simulated", False)),
        champion=_deserialize_entrant(_expect_dict(champion)) if isinstance(champion, dict) else None,
        runner_up=_deserialize_entrant(_expect_dict(runner_up)) if isinstance(runner_up, dict) else None,
        semifinalists=tuple(_deserialize_entrant(_expect_dict(item)) for item in _expect_list(semifinalists)),
    )


def _deserialize_reward(payload: dict[str, object]) -> CupReward:
    return CupReward(
        club_id=str(payload["club_id"]),
        club_name=str(payload["club_name"]),
        finish=str(payload["finish"]),
        amount=Decimal(str(payload["amount"])),
        currency=str(payload["currency"]),
    )


def _deserialize_ledger_event(payload: dict[str, object]) -> PayoutLedgerEvent:
    return PayoutLedgerEvent(
        event_key=str(payload["event_key"]),
        event_type=str(payload["event_type"]),
        aggregate_id=str(payload["aggregate_id"]),
        amount=Decimal(str(payload["amount"])),
        currency=str(payload["currency"]),
        payload={str(key): str(value) for key, value in _expect_dict(payload.get("payload", {})).items()},
    )


def _deserialize_result_summary(payload: dict[str, object]) -> FastCupResultSummary:
    return FastCupResultSummary(
        cup_id=str(payload["cup_id"]),
        division=FastCupDivision(str(payload["division"])),
        size=int(payload["size"]),
        champion=_deserialize_entrant(_expect_dict(payload["champion"])),
        runner_up=_deserialize_entrant(_expect_dict(payload["runner_up"])),
        semifinalists=tuple(_deserialize_entrant(_expect_dict(item)) for item in _expect_list(payload.get("semifinalists", []))),
        total_rounds=int(payload["total_rounds"]),
        total_matches=int(payload["total_matches"]),
        expected_duration_minutes=int(payload["expected_duration_minutes"]),
        concluded_at=_parse_datetime(payload["concluded_at"]),
        prize_pool=Decimal(str(payload["prize_pool"])),
        reward_pool=Decimal(str(payload["reward_pool"])),
        platform_fee=Decimal(str(payload["platform_fee"])),
        currency=str(payload["currency"]),
        penalty_shootouts=int(payload["penalty_shootouts"]),
        rewards=tuple(_deserialize_reward(_expect_dict(item)) for item in _expect_list(payload.get("rewards", []))),
        events=tuple(_deserialize_ledger_event(_expect_dict(item)) for item in _expect_list(payload.get("events", []))),
    )


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_datetime(value: object) -> datetime:
    return _normalize_datetime(datetime.fromisoformat(str(value)))


def _expect_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected dictionary payload, got {type(value)!r}")
    return value


def _expect_list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"Expected list payload, got {type(value)!r}")
    return value


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


__all__ = ["DatabaseFastCupRepository", "FastCupRecord"]
