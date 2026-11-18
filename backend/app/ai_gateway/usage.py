from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Published list prices used only as estimates. Override with env when finance needs a different rate.
_DEFAULT_RATES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4o": (2.50, 10.00),
}


def estimate_cost_usd(model: str | None, input_tokens: int, output_tokens: int) -> float:
    import os

    input_override = os.getenv("OPENAI_INPUT_USD_PER_MILLION")
    output_override = os.getenv("OPENAI_OUTPUT_USD_PER_MILLION")
    if input_override and output_override:
        try:
            input_rate = float(input_override)
            output_rate = float(output_override)
        except ValueError:
            input_rate, output_rate = _DEFAULT_RATES.get(model or "", (0.15, 0.60))
    else:
        input_rate, output_rate = _DEFAULT_RATES.get(model or "", (0.15, 0.60))
    cost = (max(input_tokens, 0) * input_rate + max(output_tokens, 0) * output_rate) / 1_000_000
    return round(cost, 6)


@dataclass(slots=True)
class UsageEntry:
    feature: str
    user_id: str | None
    status: str
    error_code: str | None
    model: str | None
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    latency_ms: int
    cache_hit: bool
    request_hash: str | None
    created_at: datetime


class MemoryUsageStore:
    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self.entries: list[UsageEntry] = []
        self.user_limits: dict[str, tuple[int, int]] = {}

    def record(self, entry: UsageEntry) -> None:
        self.entries.append(entry)

    def user_request_limit(self, user_id: str | None) -> tuple[int, int] | None:
        if not user_id:
            return None
        return self.user_limits.get(user_id)

    def recent_user_count(self, user_id: str | None, window_seconds: int) -> int:
        if not user_id:
            return 0
        return self._count(window_seconds, user_id=user_id)

    def recent_global_count(self, window_seconds: int) -> int:
        return self._count(window_seconds)

    def feature_count_today(self, feature: str) -> int:
        start = self._start_of_day()
        return sum(1 for entry in self.entries if entry.feature == feature and entry.created_at >= start)

    def spend_since(self, start: datetime) -> float:
        return round(
            sum(entry.estimated_cost_usd for entry in self.entries if entry.created_at >= start and not entry.cache_hit),
            6,
        )

    def summary(self) -> dict[str, Any]:
        today = self._start_of_day()
        month = today.replace(day=1)
        return _summarize(self.entries, today=today, month=month)

    def recent_errors(self, limit: int = 20) -> list[dict[str, Any]]:
        failed = [entry for entry in self.entries if entry.status != "success"]
        return [_public_error(entry) for entry in failed[-limit:]]

    def _count(self, window_seconds: int, user_id: str | None = None) -> int:
        cutoff = self._clock() - timedelta(seconds=window_seconds)
        total = 0
        for entry in self.entries:
            if entry.created_at < cutoff:
                continue
            if user_id is not None and entry.user_id != user_id:
                continue
            total += 1
        return total

    def _start_of_day(self) -> datetime:
        now = self._clock()
        return now.replace(hour=0, minute=0, second=0, microsecond=0)


class SqlUsageStore:
    def __init__(self, session_factory: Callable[[], Any] | None = None, fallback: MemoryUsageStore | None = None) -> None:
        self._session_factory = session_factory
        self.fallback = fallback or MemoryUsageStore()

    def record(self, entry: UsageEntry) -> None:
        try:
            self._insert(entry)
        except Exception:
            logger.warning("ai_usage_log_persist_failed feature=%s", entry.feature)
            self.fallback.record(entry)

    def user_request_limit(self, user_id: str | None) -> tuple[int, int] | None:
        if not user_id:
            return None
        try:
            from sqlalchemy import select

            from app.models.ai_gateway import AiRequestLimit

            with self._open() as session:
                row = session.scalar(
                    select(AiRequestLimit).where(
                        AiRequestLimit.subject_type == "user",
                        AiRequestLimit.subject_key == user_id,
                    )
                )
            if row is None:
                return self.fallback.user_request_limit(user_id)
            return int(row.max_requests), int(row.window_seconds)
        except Exception:
            return self.fallback.user_request_limit(user_id)

    def recent_user_count(self, user_id: str | None, window_seconds: int) -> int:
        if not user_id:
            return 0
        try:
            return self._count(window_seconds, user_id=user_id)
        except Exception:
            return self.fallback.recent_user_count(user_id, window_seconds)

    def recent_global_count(self, window_seconds: int) -> int:
        try:
            return self._count(window_seconds)
        except Exception:
            return self.fallback.recent_global_count(window_seconds)

    def feature_count_today(self, feature: str) -> int:
        try:
            from sqlalchemy import func, select

            from app.models.ai_gateway import AiUsageLog

            with self._open() as session:
                value = session.scalar(
                    select(func.count(AiUsageLog.id)).where(
                        AiUsageLog.feature_key == feature,
                        AiUsageLog.created_at >= self._start_of_day(),
                    )
                )
            return int(value or 0)
        except Exception:
            return self.fallback.feature_count_today(feature)

    def spend_since(self, start: datetime) -> float:
        try:
            from sqlalchemy import func, select

            from app.models.ai_gateway import AiUsageLog

            with self._open() as session:
                value = session.scalar(
                    select(func.coalesce(func.sum(AiUsageLog.estimated_cost_usd), 0)).where(
                        AiUsageLog.created_at >= start,
                        AiUsageLog.cache_hit.is_(False),
                    )
                )
            return round(float(value or 0), 6)
        except Exception:
            return self.fallback.spend_since(start)

    def summary(self) -> dict[str, Any]:
        try:
            from sqlalchemy import select

            from app.models.ai_gateway import AiUsageLog

            with self._open() as session:
                rows = list(session.scalars(select(AiUsageLog).order_by(AiUsageLog.created_at.asc())).all())
            entries = [_entry_from_row(row) for row in rows]
            today = self._start_of_day()
            return _summarize(entries, today=today, month=today.replace(day=1))
        except Exception:
            return self.fallback.summary()

    def recent_errors(self, limit: int = 20) -> list[dict[str, Any]]:
        try:
            from sqlalchemy import select

            from app.models.ai_gateway import AiUsageLog

            with self._open() as session:
                rows = list(
                    session.scalars(
                        select(AiUsageLog)
                        .where(AiUsageLog.status != "success")
                        .order_by(AiUsageLog.created_at.desc())
                        .limit(limit)
                    ).all()
                )
            return [_public_error(_entry_from_row(row)) for row in reversed(rows)]
        except Exception:
            return self.fallback.recent_errors(limit)

    def _insert(self, entry: UsageEntry) -> None:
        from app.models.ai_gateway import AiUsageLog

        with self._open() as session:
            session.add(
                AiUsageLog(
                    provider="openai",
                    feature_key=entry.feature[:64],
                    user_id=entry.user_id,
                    status=entry.status[:16],
                    error_code=entry.error_code,
                    model=entry.model,
                    input_tokens=entry.input_tokens,
                    output_tokens=entry.output_tokens,
                    estimated_cost_usd=entry.estimated_cost_usd,
                    latency_ms=entry.latency_ms,
                    cache_hit=entry.cache_hit,
                    request_hash=entry.request_hash,
                    created_at=entry.created_at,
                )
            )
            session.commit()

    def _count(self, window_seconds: int, user_id: str | None = None) -> int:
        from sqlalchemy import func, select

        from app.models.ai_gateway import AiUsageLog

        cutoff = datetime.now(UTC) - timedelta(seconds=window_seconds)
        filters = [AiUsageLog.created_at >= cutoff]
        if user_id is not None:
            filters.append(AiUsageLog.user_id == user_id)
        with self._open() as session:
            value = session.scalar(select(func.count(AiUsageLog.id)).where(*filters))
        return int(value or 0)

    def _open(self) -> Any:
        if self._session_factory is not None:
            return self._session_factory()
        from app.core.database import get_session_factory

        return get_session_factory()()

    @staticmethod
    def _start_of_day() -> datetime:
        now = datetime.now(UTC)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _entry_from_row(row: Any) -> UsageEntry:
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return UsageEntry(
        feature=row.feature_key,
        user_id=row.user_id,
        status=row.status,
        error_code=row.error_code,
        model=row.model,
        input_tokens=int(row.input_tokens or 0),
        output_tokens=int(row.output_tokens or 0),
        estimated_cost_usd=float(row.estimated_cost_usd or 0),
        latency_ms=int(row.latency_ms or 0),
        cache_hit=bool(row.cache_hit),
        request_hash=row.request_hash,
        created_at=created,
    )


def _public_error(entry: UsageEntry) -> dict[str, Any]:
    return {
        "feature": entry.feature,
        "status": entry.status,
        "error_code": entry.error_code,
        "model": entry.model,
        "created_at": entry.created_at.isoformat(),
    }


def _summarize(entries: list[UsageEntry], *, today: datetime, month: datetime) -> dict[str, Any]:
    def _bucket(selected: list[UsageEntry]) -> dict[str, Any]:
        return {
            "request_count": len(selected),
            "success_count": sum(1 for entry in selected if entry.status == "success"),
            "error_count": sum(1 for entry in selected if entry.status == "error"),
            "blocked_count": sum(1 for entry in selected if entry.status == "blocked"),
            "input_tokens": sum(entry.input_tokens for entry in selected),
            "output_tokens": sum(entry.output_tokens for entry in selected),
            "estimated_cost_usd": round(
                sum(entry.estimated_cost_usd for entry in selected if not entry.cache_hit),
                6,
            ),
        }

    by_feature: dict[str, int] = {}
    for entry in entries:
        by_feature[entry.feature] = by_feature.get(entry.feature, 0) + 1
    return {
        "today": _bucket([entry for entry in entries if entry.created_at >= today]),
        "month": _bucket([entry for entry in entries if entry.created_at >= month]),
        "all_time": _bucket(entries),
        "by_feature": by_feature,
    }
