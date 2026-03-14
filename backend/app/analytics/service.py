from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.analytics_event import AnalyticsEvent


class AnalyticsService:
    def track_event(
        self,
        session: Session,
        *,
        name: str,
        user_id: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(
            name=name,
            user_id=user_id,
            metadata_json=metadata or {},
        )
        session.add(event)
        session.flush()
        return event

    def summary(self, session: Session, *, since_days: int = 30) -> tuple[datetime, list[dict[str, Any]]]:
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        rows = session.execute(
            select(AnalyticsEvent.name, func.count())
            .where(AnalyticsEvent.created_at >= since)
            .group_by(AnalyticsEvent.name)
            .order_by(func.count().desc())
        ).all()
        return since, [{"name": row[0], "count": int(row[1])} for row in rows]

    def funnel(self, session: Session, *, since_days: int = 30) -> tuple[datetime, list[dict[str, Any]]]:
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        steps = [
            "signup_started",
            "signup_completed",
            "deposit_confirmed",
            "kyc_approved",
            "withdrawal_paid",
        ]
        results: list[dict[str, Any]] = []
        for step in steps:
            count = session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.user_id)))
                .where(
                    AnalyticsEvent.created_at >= since,
                    AnalyticsEvent.name == step,
                    AnalyticsEvent.user_id.is_not(None),
                )
            )
            results.append({"name": step, "users": int(count or 0)})
        return since, results
