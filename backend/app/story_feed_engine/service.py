from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.story_feed import StoryFeedItem


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
    ) -> StoryFeedItem:
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

    def list_feed(
        self,
        *,
        limit: int = 50,
        story_type: str | None = None,
        country_code: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        featured_only: bool = False,
    ) -> list[StoryFeedItem]:
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
        stmt = stmt.order_by(StoryFeedItem.featured.desc(), StoryFeedItem.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt).all())

    def digest(self, *, country_code: str | None = None) -> dict[str, list[StoryFeedItem]]:
        return {
            "top_stories": self.list_feed(limit=10),
            "country_spotlight": self.list_feed(limit=10, country_code=country_code) if country_code else [],
            "feature_stories": list(
                self.session.scalars(
                    select(StoryFeedItem)
                    .where(StoryFeedItem.featured.is_(True))
                    .order_by(StoryFeedItem.created_at.desc())
                    .limit(10)
                ).all()
            ),
        }
