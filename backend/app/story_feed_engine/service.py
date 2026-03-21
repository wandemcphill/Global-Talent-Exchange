from __future__ import annotations

from dataclasses import dataclass

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
                    select(StoryFeedItem).where(StoryFeedItem.featured.is_(True)).order_by(StoryFeedItem.created_at.desc()).limit(10)
                ).all()
            ),
        }
