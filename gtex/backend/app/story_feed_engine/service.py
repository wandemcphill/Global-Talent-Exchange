from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.story_feed import StoryFeedItem

MODERATION_PUBLISHED = "published"
MODERATION_SCHEDULED = "scheduled"
MODERATION_REJECTED = "rejected"


class StoryFeedNotFoundError(LookupError):
    pass


class StoryFeedModerationError(ValueError):
    pass


@dataclass(slots=True)
class StoryFeedService:
    session: Session

    def publish(
        self,
        *,
        story_type: str,
        title: str,
        body: str,
        audience: str = "public",
        subject_type: str | None = None,
        subject_id: str | None = None,
        country_code: str | None = None,
        metadata_json: dict | None = None,
        featured: bool = False,
        published_by_user_id: str | None = None,
        scheduled_for: datetime | None = None,
    ) -> StoryFeedItem:
        status = MODERATION_PUBLISHED
        schedule_at = self._normalize_schedule(scheduled_for) if scheduled_for is not None else None
        if schedule_at is not None:
            status = MODERATION_SCHEDULED
        item = StoryFeedItem(
            story_type=story_type.strip().lower(),
            title=title.strip(),
            body=body.strip(),
            audience=audience.strip().lower(),
            subject_type=subject_type.strip().lower() if subject_type else None,
            subject_id=subject_id,
            country_code=country_code.strip().upper() if country_code else None,
            metadata_json=metadata_json or {},
            featured=featured,
            moderation_status=status,
            scheduled_for=schedule_at,
            published_by_user_id=published_by_user_id,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def publish_idempotent(
        self,
        *,
        idempotency_key: str,
        source: str,
        story_type: str,
        title: str,
        body: str,
        audience: str = "public",
        subject_type: str | None = None,
        subject_id: str | None = None,
        country_code: str | None = None,
        metadata_json: dict | None = None,
        featured: bool = False,
        published_by_user_id: str | None = None,
    ) -> tuple[StoryFeedItem, bool]:
        """Publish once per idempotency_key. Returns (item, created)."""
        key = idempotency_key.strip()
        if not key:
            raise ValueError("idempotency_key is required")
        existing = self.find_by_idempotency_key(key)
        if existing is not None:
            return existing, False

        meta: dict[str, Any] = dict(metadata_json or {})
        meta["idempotency_key"] = key
        meta["source"] = source.strip().lower()
        item = self.publish(
            story_type=story_type,
            title=title,
            body=body,
            audience=audience,
            subject_type=subject_type,
            subject_id=subject_id,
            country_code=country_code,
            metadata_json=meta,
            featured=featured,
            published_by_user_id=published_by_user_id,
        )
        return item, True

    def get(self, story_id: str) -> StoryFeedItem:
        item = self.session.get(StoryFeedItem, story_id)
        if item is None:
            raise StoryFeedNotFoundError(f"Story feed item {story_id} was not found.")
        return item

    def schedule(
        self,
        *,
        story_id: str,
        scheduled_for: datetime,
        moderated_by_user_id: str | None = None,
    ) -> StoryFeedItem:
        item = self.get(story_id)
        if item.moderation_status == MODERATION_REJECTED:
            raise StoryFeedModerationError("Rejected stories cannot be scheduled.")
        schedule_at = self._normalize_schedule(scheduled_for)
        item.moderation_status = MODERATION_SCHEDULED
        item.scheduled_for = schedule_at
        self._annotate_moderation(
            item,
            action="schedule",
            moderated_by_user_id=moderated_by_user_id,
            extra={"scheduled_for": schedule_at.isoformat()},
        )
        self.session.flush()
        return item

    def reject(
        self,
        *,
        story_id: str,
        reason: str | None = None,
        moderated_by_user_id: str | None = None,
    ) -> StoryFeedItem:
        item = self.get(story_id)
        if item.moderation_status == MODERATION_REJECTED:
            return item
        cleaned_reason = (reason or "").strip() or None
        item.moderation_status = MODERATION_REJECTED
        item.scheduled_for = None
        item.featured = False
        self._annotate_moderation(
            item,
            action="reject",
            moderated_by_user_id=moderated_by_user_id,
            extra={"reason": cleaned_reason} if cleaned_reason else None,
        )
        self.session.flush()
        return item

    def find_by_idempotency_key(self, idempotency_key: str) -> StoryFeedItem | None:
        key = idempotency_key.strip()
        if not key:
            return None
        short = key.rsplit(":", 1)[-1]
        candidates = list(
            self.session.scalars(
                select(StoryFeedItem)
                .where(StoryFeedItem.subject_id == short)
                .order_by(StoryFeedItem.created_at.desc())
                .limit(40)
            ).all()
        )
        for item in candidates:
            if str((item.metadata_json or {}).get("idempotency_key") or "") == key:
                return item
        # Fallback: recent window scan (JSON path indexes vary by dialect).
        recent = list(
            self.session.scalars(select(StoryFeedItem).order_by(StoryFeedItem.created_at.desc()).limit(250)).all()
        )
        for item in recent:
            if str((item.metadata_json or {}).get("idempotency_key") or "") == key:
                return item
        return None

    def promote_due_scheduled(self) -> int:
        now = utcnow()
        due = list(
            self.session.scalars(
                select(StoryFeedItem).where(
                    StoryFeedItem.moderation_status == MODERATION_SCHEDULED,
                    StoryFeedItem.scheduled_for.is_not(None),
                    StoryFeedItem.scheduled_for <= now,
                )
            ).all()
        )
        for item in due:
            item.moderation_status = MODERATION_PUBLISHED
            item.scheduled_for = None
            self._annotate_moderation(item, action="auto_publish", moderated_by_user_id=None)
        if due:
            self.session.flush()
        return len(due)

    def list_feed(
        self,
        *,
        limit: int = 50,
        story_type: str | None = None,
        country_code: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        featured_only: bool = False,
        include_moderated: bool = False,
    ) -> list[StoryFeedItem]:
        self.promote_due_scheduled()
        stmt = select(StoryFeedItem)
        if story_type:
            stmt = stmt.where(StoryFeedItem.story_type == story_type.strip().lower())
        if country_code:
            stmt = stmt.where(StoryFeedItem.country_code == country_code.strip().upper())
        if subject_type:
            stmt = stmt.where(StoryFeedItem.subject_type == subject_type.strip().lower())
        if subject_id:
            stmt = stmt.where(StoryFeedItem.subject_id == subject_id)
        if featured_only:
            stmt = stmt.where(StoryFeedItem.featured.is_(True))
        if not include_moderated:
            stmt = stmt.where(StoryFeedItem.moderation_status == MODERATION_PUBLISHED)
        stmt = stmt.order_by(StoryFeedItem.featured.desc(), StoryFeedItem.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def digest(self, *, country_code: str | None = None) -> dict[str, list[StoryFeedItem]]:
        self.promote_due_scheduled()
        return {
            "top_stories": self.list_feed(limit=10),
            "country_spotlight": self.list_feed(limit=10, country_code=country_code) if country_code else [],
            "feature_stories": list(
                self.session.scalars(
                    select(StoryFeedItem)
                    .where(
                        StoryFeedItem.featured.is_(True),
                        StoryFeedItem.moderation_status == MODERATION_PUBLISHED,
                    )
                    .order_by(StoryFeedItem.created_at.desc())
                    .limit(10)
                ).all()
            ),
        }

    def _normalize_schedule(self, scheduled_for: datetime) -> datetime:
        if scheduled_for.tzinfo is None:
            schedule_at = scheduled_for.replace(tzinfo=timezone.utc)
        else:
            schedule_at = scheduled_for.astimezone(timezone.utc)
        if schedule_at <= utcnow():
            raise StoryFeedModerationError("scheduled_for must be in the future.")
        return schedule_at

    def _annotate_moderation(
        self,
        item: StoryFeedItem,
        *,
        action: str,
        moderated_by_user_id: str | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        meta = dict(item.metadata_json or {})
        entry: dict[str, Any] = {
            "action": action,
            "status": item.moderation_status,
            "at": utcnow().isoformat(),
        }
        if moderated_by_user_id:
            entry["moderated_by_user_id"] = moderated_by_user_id
        if extra:
            entry.update(extra)
        history = list(meta.get("moderation_history") or [])
        history.append(entry)
        meta["moderation_history"] = history[-20:]
        meta["moderation"] = entry
        item.metadata_json = meta
