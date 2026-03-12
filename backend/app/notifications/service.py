from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from backend.app.config.competition_constants import FAST_CUP_REGISTRATION_INTERVAL_MINUTES
from backend.app.core.events import DomainEvent


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


NOTIFICATION_TEMPLATE_TOPICS = {
    "match_starts_10m": "match",
    "match_starts_1m": "match",
    "match_live_now": "match",
    "you_won": "result",
    "you_lost": "result",
    "qualified": "qualification",
    "reached_playoff": "qualification",
    "qualified_champions_league": "qualification",
    "qualified_world_super_cup": "qualification",
    "fast_cup_starts_soon": "fast_cup",
}


@dataclass(frozen=True, slots=True)
class Notification:
    notification_id: str
    user_id: str | None
    topic: str
    template_key: str | None
    resource_id: str | None
    fixture_id: str | None
    competition_id: str | None
    message: str
    metadata: dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class NotificationCenter:
    _notifications: list[Notification] = field(default_factory=list)
    _dedupe_keys: set[str] = field(default_factory=set)
    _lock: RLock = field(default_factory=RLock)

    def handle_event(self, event: DomainEvent) -> None:
        for notification in self._translate(event):
            with self._lock:
                self._notifications.append(notification)

    def list_for_user(self, user_id: str, limit: int = 20) -> list[Notification]:
        with self._lock:
            items = [item for item in self._notifications if item.user_id in {None, user_id}]
            return list(reversed(items[-limit:]))

    def _translate(self, event: DomainEvent) -> list[Notification]:
        payload = event.payload
        created_at = event.occurred_at
        competition_notifications = self._translate_competition_event(event)
        if competition_notifications:
            return competition_notifications
        notifications: list[Notification] = []
        if event.name.startswith("wallet."):
            user_id = payload.get("user_id")
            if isinstance(user_id, str):
                notifications.append(
                    Notification(
                        notification_id=f"ntf_{uuid4().hex[:12]}",
                        user_id=user_id,
                        topic="wallet",
                        template_key=None,
                        resource_id=self._resource_id(payload),
                        fixture_id=self._fixture_id(payload),
                        competition_id=self._competition_id(payload),
                        message=event.name.replace(".", " "),
                        metadata=self._metadata(payload),
                        created_at=created_at,
                    )
                )
        elif event.name.startswith("market."):
            for key in ("seller_user_id", "buyer_user_id", "user_id"):
                user_id = payload.get(key)
                if isinstance(user_id, str):
                    notifications.append(
                        Notification(
                            notification_id=f"ntf_{uuid4().hex[:12]}",
                            user_id=user_id,
                            topic="market",
                            template_key=None,
                            resource_id=self._resource_id(payload),
                            fixture_id=self._fixture_id(payload),
                            competition_id=self._competition_id(payload),
                            message=event.name.replace(".", " "),
                            metadata=self._metadata(payload),
                            created_at=created_at,
                        )
                    )
        elif event.name.startswith("value.") or event.name.startswith("jobs."):
            notifications.append(
                Notification(
                    notification_id=f"ntf_{uuid4().hex[:12]}",
                    user_id=None,
                    topic=event.name.split(".", maxsplit=1)[0],
                    template_key=None,
                    resource_id=self._resource_id(payload),
                    fixture_id=self._fixture_id(payload),
                    competition_id=self._competition_id(payload),
                    message=event.name.replace(".", " "),
                    metadata=self._metadata(payload),
                    created_at=created_at,
                )
            )
        return notifications

    def _translate_competition_event(self, event: DomainEvent) -> list[Notification]:
        template_key = self._template_key_for_event(event)
        if template_key is None:
            return []

        payload = event.payload
        user_ids = self._user_ids(payload)
        if not user_ids:
            user_ids = (None,)

        resource_id = self._resource_id(payload)
        fixture_id = self._fixture_id(payload)
        competition_id = self._competition_id(payload)
        metadata = self._metadata(payload)
        notifications: list[Notification] = []
        for user_id in user_ids:
            dedupe_key = self._dedupe_key(
                template_key=template_key,
                user_id=user_id,
                resource_id=resource_id,
                fixture_id=fixture_id,
                competition_id=competition_id,
            )
            with self._lock:
                if dedupe_key in self._dedupe_keys:
                    continue
                self._dedupe_keys.add(dedupe_key)
            notifications.append(
                Notification(
                    notification_id=f"ntf_{uuid4().hex[:12]}",
                    user_id=user_id,
                    topic=NOTIFICATION_TEMPLATE_TOPICS[template_key],
                    template_key=template_key,
                    resource_id=resource_id,
                    fixture_id=fixture_id,
                    competition_id=competition_id,
                    message=self._render_competition_message(template_key, payload),
                    metadata=metadata,
                    created_at=event.occurred_at,
                )
            )
        return notifications

    @staticmethod
    def _template_key_for_event(event: DomainEvent) -> str | None:
        payload = event.payload
        template_key = payload.get("template_key")
        if isinstance(template_key, str) and template_key in NOTIFICATION_TEMPLATE_TOPICS:
            return template_key

        if event.name == "competition.match.starting":
            minutes_until_start = payload.get("minutes_until_start")
            if minutes_until_start == 10:
                return "match_starts_10m"
            if minutes_until_start == 1:
                return "match_starts_1m"
            return None
        if event.name == "competition.match.live":
            return "match_live_now"
        if event.name == "competition.match.result":
            result = payload.get("result")
            if result == "won":
                return "you_won"
            if result == "lost":
                return "you_lost"
            return None
        if event.name == "competition.qualification.updated":
            status = payload.get("qualification_status")
            return {
                "qualified": "qualified",
                "playoff": "reached_playoff",
                "champions_league": "qualified_champions_league",
                "world_super_cup": "qualified_world_super_cup",
            }.get(status)
        if event.name == "competition.fast_cup.starting":
            return "fast_cup_starts_soon"
        return None

    def _render_competition_message(self, template_key: str, payload: dict[str, Any]) -> str:
        match_label = self._match_label(payload)
        competition_name = payload.get("competition_name")
        if not isinstance(competition_name, str) or not competition_name:
            competition_name = "your competition"
        scoreline = self._scoreline_label(payload)

        if template_key == "match_starts_10m":
            return f"{match_label} starts in 10 minutes."
        if template_key == "match_starts_1m":
            return f"{match_label} starts in 1 minute."
        if template_key == "match_live_now":
            return f"{match_label} is live now."
        if template_key == "you_won":
            return f"You won {match_label}{scoreline}."
        if template_key == "you_lost":
            return f"You lost {match_label}{scoreline}."
        if template_key == "qualified":
            return f"You qualified from {competition_name}."
        if template_key == "reached_playoff":
            return f"You reached the playoff stage in {competition_name}."
        if template_key == "qualified_champions_league":
            return f"You qualified for the Champions League from {competition_name}."
        if template_key == "qualified_world_super_cup":
            return f"You qualified for the World Super Cup from {competition_name}."
        if template_key == "fast_cup_starts_soon":
            return f"The next fast cup starts in {FAST_CUP_REGISTRATION_INTERVAL_MINUTES} minutes."
        raise ValueError(f"Unsupported notification template: {template_key}")

    @staticmethod
    def _match_label(payload: dict[str, Any]) -> str:
        home_club_name = payload.get("home_club_name")
        away_club_name = payload.get("away_club_name")
        if isinstance(home_club_name, str) and isinstance(away_club_name, str):
            return f"{home_club_name} vs {away_club_name}"
        fixture_label = payload.get("fixture_label")
        if isinstance(fixture_label, str) and fixture_label:
            return fixture_label
        return "Your match"

    @staticmethod
    def _scoreline_label(payload: dict[str, Any]) -> str:
        home_goals = payload.get("home_goals")
        away_goals = payload.get("away_goals")
        if isinstance(home_goals, int) and isinstance(away_goals, int):
            return f" {home_goals}-{away_goals}"
        return ""

    @staticmethod
    def _user_ids(payload: dict[str, Any]) -> tuple[str | None, ...]:
        candidate_ids: list[str | None] = []
        if isinstance(payload.get("user_id"), str):
            candidate_ids.append(payload["user_id"])
        user_ids = payload.get("user_ids")
        if isinstance(user_ids, (list, tuple)):
            candidate_ids.extend(user_id for user_id in user_ids if isinstance(user_id, str))
        return tuple(dict.fromkeys(candidate_ids))

    @staticmethod
    def _resource_id(payload: dict[str, Any]) -> str | None:
        for key in ("resource_id", "fixture_id", "competition_id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    @staticmethod
    def _fixture_id(payload: dict[str, Any]) -> str | None:
        fixture_id = payload.get("fixture_id")
        return fixture_id if isinstance(fixture_id, str) and fixture_id else None

    @staticmethod
    def _competition_id(payload: dict[str, Any]) -> str | None:
        competition_id = payload.get("competition_id")
        return competition_id if isinstance(competition_id, str) and competition_id else None

    @staticmethod
    def _metadata(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in payload.items()
            if key
            not in {
                "user_id",
                "user_ids",
            }
        }

    @staticmethod
    def _dedupe_key(
        *,
        template_key: str,
        user_id: str | None,
        resource_id: str | None,
        fixture_id: str | None,
        competition_id: str | None,
    ) -> str:
        return ":".join(
            (
                template_key,
                user_id or "broadcast",
                resource_id or "-",
                fixture_id or "-",
                competition_id or "-",
            )
        )
