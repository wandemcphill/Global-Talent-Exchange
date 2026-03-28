from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from math import log1p, sqrt
from typing import Any, Protocol

from fastapi import FastAPI
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.creator_profile import CreatorProfile
from app.models.follow import Follow
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.models.user_affinity_profile import UserAffinityProfile
from app.users.affinity_service import UserAffinityService

logger = logging.getLogger(__name__)

FOLLOWERS_KEY_TEMPLATE = "user:{user_id}:followers"
FOLLOWING_KEY_TEMPLATE = "user:{user_id}:following"
FOLLOWING_FEED_KEY_TEMPLATE = "user:{user_id}:following_feed"
FOLLOWING_FEED_CACHE_SUBJECT_SUFFIX = ":following"
FOLLOW_NOTIFICATION_TEMPLATE_KEY = "FOLLOWED_CREATOR_NEW_CLIP"
VIRAL_NOTIFICATION_TEMPLATE_KEY = "FOLLOWED_CREATOR_VIRAL"
NOTIFICATION_RESOURCE_TYPE = "viral_clip"


class FollowGraphError(ValueError):
    pass


class FollowGraphNotFoundError(FollowGraphError):
    pass


class FollowGraphCache(Protocol):
    def get_followers(self, user_id: str) -> set[str] | None:
        ...

    def get_following(self, user_id: str) -> set[str] | None:
        ...

    def store_followers(self, user_id: str, follower_ids: set[str]) -> None:
        ...

    def store_following(self, user_id: str, following_ids: set[str]) -> None:
        ...

    def add_edge(self, follower_id: str, following_id: str) -> None:
        ...

    def remove_edge(self, follower_id: str, following_id: str) -> None:
        ...


@dataclass(slots=True)
class NullFollowGraphCache:
    def get_followers(self, user_id: str) -> set[str] | None:  # noqa: ARG002
        return None

    def get_following(self, user_id: str) -> set[str] | None:  # noqa: ARG002
        return None

    def store_followers(self, user_id: str, follower_ids: set[str]) -> None:  # noqa: ARG002
        return None

    def store_following(self, user_id: str, following_ids: set[str]) -> None:  # noqa: ARG002
        return None

    def add_edge(self, follower_id: str, following_id: str) -> None:  # noqa: ARG002
        return None

    def remove_edge(self, follower_id: str, following_id: str) -> None:  # noqa: ARG002
        return None


@dataclass(slots=True)
class RedisFollowGraphCache:
    redis_url: str
    _client: Redis = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = Redis.from_url(self.redis_url, decode_responses=True)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except RedisError:
            logger.warning("users.follow_graph.redis.ping_failed")
            return False

    def get_followers(self, user_id: str) -> set[str] | None:
        return self._members_if_present(FOLLOWERS_KEY_TEMPLATE.format(user_id=user_id))

    def get_following(self, user_id: str) -> set[str] | None:
        return self._members_if_present(FOLLOWING_KEY_TEMPLATE.format(user_id=user_id))

    def store_followers(self, user_id: str, follower_ids: set[str]) -> None:
        self._replace_members(FOLLOWERS_KEY_TEMPLATE.format(user_id=user_id), follower_ids)

    def store_following(self, user_id: str, following_ids: set[str]) -> None:
        self._replace_members(FOLLOWING_KEY_TEMPLATE.format(user_id=user_id), following_ids)

    def add_edge(self, follower_id: str, following_id: str) -> None:
        try:
            pipeline = self._client.pipeline()
            pipeline.sadd(FOLLOWING_KEY_TEMPLATE.format(user_id=follower_id), following_id)
            pipeline.sadd(FOLLOWERS_KEY_TEMPLATE.format(user_id=following_id), follower_id)
            pipeline.execute()
        except RedisError:
            logger.warning(
                "users.follow_graph.redis.add_edge_failed follower_id=%s following_id=%s",
                follower_id,
                following_id,
            )

    def remove_edge(self, follower_id: str, following_id: str) -> None:
        try:
            pipeline = self._client.pipeline()
            pipeline.srem(FOLLOWING_KEY_TEMPLATE.format(user_id=follower_id), following_id)
            pipeline.srem(FOLLOWERS_KEY_TEMPLATE.format(user_id=following_id), follower_id)
            pipeline.execute()
        except RedisError:
            logger.warning(
                "users.follow_graph.redis.remove_edge_failed follower_id=%s following_id=%s",
                follower_id,
                following_id,
            )

    def _members_if_present(self, key: str) -> set[str] | None:
        try:
            pipeline = self._client.pipeline()
            pipeline.exists(key)
            pipeline.smembers(key)
            exists, members = pipeline.execute()
        except RedisError:
            logger.warning("users.follow_graph.redis.members_failed key=%s", key)
            return None
        if not exists:
            return None
        return {str(member) for member in members}

    def _replace_members(self, key: str, member_ids: set[str]) -> None:
        try:
            pipeline = self._client.pipeline()
            pipeline.delete(key)
            if member_ids:
                pipeline.sadd(key, *sorted(member_ids))
            pipeline.execute()
        except RedisError:
            logger.warning("users.follow_graph.redis.replace_failed key=%s member_count=%s", key, len(member_ids))


@dataclass(slots=True)
class FollowGraphService:
    session: Session
    cache: FollowGraphCache = field(default_factory=NullFollowGraphCache)

    def follow(self, *, actor: User, following_id: str) -> dict[str, Any]:
        target = self._require_user(following_id)
        if actor.id == target.id:
            raise FollowGraphError("Users cannot follow themselves.")

        edge = self.session.get(
            Follow,
            {
                "follower_id": actor.id,
                "following_id": target.id,
            },
        )
        if edge is None:
            self.session.add(Follow(follower_id=actor.id, following_id=target.id))
            self.session.flush()
            self.cache.add_edge(actor.id, target.id)
            UserAffinityService(self.session).boost_creator_affinity(
                user_id=actor.id,
                creator_id=target.id,
            )

        return {
            "follower_id": actor.id,
            "following_id": target.id,
            "following": True,
            "target_followers_count": self.followers_count(target.id),
            "current_following_count": self.following_count(actor.id),
        }

    def unfollow(self, *, actor: User, following_id: str) -> dict[str, Any]:
        target = self._require_user(following_id)
        edge = self.session.get(
            Follow,
            {
                "follower_id": actor.id,
                "following_id": target.id,
            },
        )
        if edge is not None:
            self.session.delete(edge)
            self.session.flush()
            self.cache.remove_edge(actor.id, target.id)

        return {
            "follower_id": actor.id,
            "following_id": target.id,
            "following": False,
            "target_followers_count": self.followers_count(target.id),
            "current_following_count": self.following_count(actor.id),
        }

    def list_followers(self, *, user_id: str, limit: int = 50) -> dict[str, Any]:
        self._require_user(user_id)
        if not self._table_exists(Follow.__tablename__):
            return {"user_id": user_id, "total": 0, "users": []}
        rows = list(
            self.session.execute(
                select(User, Follow.created_at)
                .join(Follow, Follow.follower_id == User.id)
                .where(Follow.following_id == user_id)
                .order_by(Follow.created_at.desc(), User.username.asc())
                .limit(max(limit, 1))
            ).all()
        )
        users = [row[0] for row in rows]
        creator_profiles = self._creator_profiles([user.id for user in users])
        follower_counts = self.follower_counts([user.id for user in users])
        return {
            "user_id": user_id,
            "total": self.followers_count(user_id),
            "users": [
                self._follow_user_view(
                    user,
                    followed_at=rows[index][1],
                    creator_profile=creator_profiles.get(user.id),
                    followers_count=follower_counts.get(user.id, 0),
                )
                for index, user in enumerate(users)
            ],
        }

    def list_following(self, *, user_id: str, limit: int = 50) -> dict[str, Any]:
        self._require_user(user_id)
        if not self._table_exists(Follow.__tablename__):
            return {"user_id": user_id, "total": 0, "users": []}
        rows = list(
            self.session.execute(
                select(User, Follow.created_at)
                .join(Follow, Follow.following_id == User.id)
                .where(Follow.follower_id == user_id)
                .order_by(Follow.created_at.desc(), User.username.asc())
                .limit(max(limit, 1))
            ).all()
        )
        users = [row[0] for row in rows]
        creator_profiles = self._creator_profiles([user.id for user in users])
        follower_counts = self.follower_counts([user.id for user in users])
        return {
            "user_id": user_id,
            "total": self.following_count(user_id),
            "users": [
                self._follow_user_view(
                    user,
                    followed_at=rows[index][1],
                    creator_profile=creator_profiles.get(user.id),
                    followers_count=follower_counts.get(user.id, 0),
                )
                for index, user in enumerate(users)
            ],
        }

    def suggest_users(self, *, actor: User, limit: int = 20) -> dict[str, Any]:
        if not self._table_exists(User.__tablename__):
            return {"user_id": actor.id, "suggestions": [], "generated_at": datetime.now(UTC)}

        followed_ids = self.following_ids(actor.id)
        candidate_limit = max(limit * 5, limit, 20)
        stmt = select(User).where(User.id != actor.id, User.is_active.is_(True))
        if followed_ids:
            stmt = stmt.where(User.id.notin_(tuple(sorted(followed_ids))))
        if self._table_exists(CreatorProfile.__tablename__):
            stmt = stmt.join(CreatorProfile, CreatorProfile.user_id == User.id)
        candidates = list(self.session.scalars(stmt.order_by(User.created_at.desc()).limit(candidate_limit)).all())
        if not candidates:
            return {"user_id": actor.id, "suggestions": [], "generated_at": datetime.now(UTC)}

        candidate_ids = [user.id for user in candidates]
        creator_profiles = self._creator_profiles(candidate_ids)
        affinity_profiles = self._affinity_profiles([actor.id, *candidate_ids])
        follower_counts = self.follower_counts(candidate_ids)
        current_profile = affinity_profiles.get(actor.id)
        current_vector = dict(current_profile.affinity_vector_json or {}) if current_profile is not None else {}
        current_creators = dict(current_profile.favorite_creators_json or {}) if current_profile is not None else {}
        current_formats = dict(current_profile.favorite_formats_json or {}) if current_profile is not None else {}
        social_boosts = {
            user_id: round(log1p(float(follower_counts.get(user_id, 0))), 6)
            for user_id in candidate_ids
        }
        max_social_boost = max(social_boosts.values(), default=0.0)

        ranked: list[dict[str, Any]] = []
        for user in candidates:
            candidate_profile = affinity_profiles.get(user.id)
            candidate_vector = dict(candidate_profile.affinity_vector_json or {}) if candidate_profile is not None else {}
            candidate_creators = dict(candidate_profile.favorite_creators_json or {}) if candidate_profile is not None else {}
            candidate_formats = dict(candidate_profile.favorite_formats_json or {}) if candidate_profile is not None else {}

            affinity_similarity = self._cosine_similarity(current_vector, candidate_vector)
            format_similarity = self._cosine_similarity(current_formats, candidate_formats)
            shared_engagement_score = self._cosine_similarity(current_creators, candidate_creators)
            social_boost = social_boosts.get(user.id, 0.0)
            social_signal = 0.0 if max_social_boost <= 0 else round(social_boost / max_social_boost, 6)
            score = round(
                (0.45 * affinity_similarity)
                + (0.20 * format_similarity)
                + (0.20 * shared_engagement_score)
                + (0.15 * social_signal),
                6,
            )
            ranked.append(
                {
                    **self._follow_user_view(
                        user,
                        followed_at=None,
                        creator_profile=creator_profiles.get(user.id),
                        followers_count=follower_counts.get(user.id, 0),
                    ),
                    "affinity_similarity": round(affinity_similarity, 6),
                    "shared_engagement_score": round(shared_engagement_score, 6),
                    "social_boost": social_boost,
                    "score": score,
                    "reason": self._suggestion_reason(
                        affinity_similarity=affinity_similarity,
                        shared_engagement_score=shared_engagement_score,
                        followers_count=follower_counts.get(user.id, 0),
                        has_creator_profile=user.id in creator_profiles,
                    ),
                }
            )

        ranked.sort(
            key=lambda item: (
                -float(item["score"]),
                -int(item["followers_count"]),
                str(item["username"]).lower(),
            )
        )
        return {
            "user_id": actor.id,
            "suggestions": ranked[: max(limit, 1)],
            "generated_at": datetime.now(UTC),
        }

    def followers_count(self, user_id: str) -> int:
        if not self._table_exists(Follow.__tablename__):
            return 0
        cached = self.cache.get_followers(user_id)
        if cached is not None:
            return len(cached)
        return int(
            self.session.scalar(
                select(func.count()).select_from(Follow).where(Follow.following_id == user_id)
            )
            or 0
        )

    def following_count(self, user_id: str) -> int:
        if not self._table_exists(Follow.__tablename__):
            return 0
        cached = self.cache.get_following(user_id)
        if cached is not None:
            return len(cached)
        return int(
            self.session.scalar(
                select(func.count()).select_from(Follow).where(Follow.follower_id == user_id)
            )
            or 0
        )

    def follower_counts(self, user_ids: list[str] | set[str] | tuple[str, ...]) -> dict[str, int]:
        resolved_ids = [user_id for user_id in dict.fromkeys(str(item) for item in user_ids if str(item).strip())]
        if not resolved_ids:
            return {}
        if not self._table_exists(Follow.__tablename__):
            return {user_id: 0 for user_id in resolved_ids}
        rows = list(
            self.session.execute(
                select(Follow.following_id, func.count())
                .where(Follow.following_id.in_(resolved_ids))
                .group_by(Follow.following_id)
            ).all()
        )
        counts = {str(user_id): int(count) for user_id, count in rows}
        return {user_id: counts.get(user_id, 0) for user_id in resolved_ids}

    def network_popularity_counts(
        self,
        *,
        user_id: str,
        creator_user_ids: list[str] | set[str] | tuple[str, ...],
    ) -> dict[str, int]:
        resolved_creator_ids = [
            creator_id
            for creator_id in dict.fromkeys(str(item) for item in creator_user_ids if str(item).strip())
        ]
        if not resolved_creator_ids:
            return {}
        if not self._table_exists(Follow.__tablename__):
            return {creator_id: 0 for creator_id in resolved_creator_ids}
        network_following_ids = self.following_ids(user_id)
        if not network_following_ids:
            return {creator_id: 0 for creator_id in resolved_creator_ids}
        rows = list(
            self.session.execute(
                select(Follow.following_id, func.count())
                .where(
                    Follow.follower_id.in_(tuple(sorted(network_following_ids))),
                    Follow.following_id.in_(tuple(resolved_creator_ids)),
                )
                .group_by(Follow.following_id)
            ).all()
        )
        counts = {str(creator_id): int(count) for creator_id, count in rows}
        return {creator_id: counts.get(creator_id, 0) for creator_id in resolved_creator_ids}

    def following_ids(self, user_id: str) -> set[str]:
        if not self._table_exists(Follow.__tablename__):
            return set()
        cached = self.cache.get_following(user_id)
        if cached is not None:
            return cached
        following_ids = {
            str(item)
            for item in self.session.scalars(
                select(Follow.following_id).where(Follow.follower_id == user_id)
            ).all()
        }
        self.cache.store_following(user_id, following_ids)
        return following_ids

    def follower_ids(self, user_id: str) -> set[str]:
        if not self._table_exists(Follow.__tablename__):
            return set()
        cached = self.cache.get_followers(user_id)
        if cached is not None:
            return cached
        follower_ids = {
            str(item)
            for item in self.session.scalars(
                select(Follow.follower_id).where(Follow.following_id == user_id)
            ).all()
        }
        self.cache.store_followers(user_id, follower_ids)
        return follower_ids

    def resolve_creator_user_id(self, clip: Any) -> str | None:
        metadata = self._clip_metadata(clip)
        for key in ("creator_user_id", "creator_id", "author_user_id"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        creator_profile_id = metadata.get("creator_profile_id")
        if not isinstance(creator_profile_id, str) or not creator_profile_id.strip():
            return None
        if not self._table_exists(CreatorProfile.__tablename__):
            return None
        profile = self.session.get(CreatorProfile, creator_profile_id.strip())
        if profile is None:
            return None
        return str(profile.user_id)

    def _clip_metadata(self, clip: Any) -> dict[str, Any]:
        if isinstance(clip, Mapping):
            raw_metadata = clip.get("metadata")
        else:
            raw_metadata = getattr(clip, "metadata", {})
        return dict(raw_metadata or {}) if isinstance(raw_metadata, Mapping) else {}

    def _creator_profiles(self, user_ids: list[str]) -> dict[str, CreatorProfile]:
        if not user_ids or not self._table_exists(CreatorProfile.__tablename__):
            return {}
        return {
            item.user_id: item
            for item in self.session.scalars(
                select(CreatorProfile).where(CreatorProfile.user_id.in_(tuple(user_ids)))
            ).all()
        }

    def _affinity_profiles(self, user_ids: list[str]) -> dict[str, UserAffinityProfile]:
        if not user_ids or not self._table_exists(UserAffinityProfile.__tablename__):
            return {}
        return {
            item.user_id: item
            for item in self.session.scalars(
                select(UserAffinityProfile).where(UserAffinityProfile.user_id.in_(tuple(user_ids)))
            ).all()
        }

    def _follow_user_view(
        self,
        user: User,
        *,
        followed_at: datetime | None,
        creator_profile: CreatorProfile | None,
        followers_count: int,
    ) -> dict[str, Any]:
        return {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "full_name": user.full_name,
            "creator_handle": creator_profile.handle if creator_profile is not None else None,
            "creator_tier": creator_profile.tier if creator_profile is not None else None,
            "followers_count": int(followers_count),
            "followed_at": followed_at,
        }

    def _require_user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise FollowGraphNotFoundError("User was not found.")
        return user

    def _table_exists(self, table_name: str) -> bool:
        try:
            return bool(inspect(self.session.connection()).has_table(table_name))
        except Exception:
            return False

    @staticmethod
    def _cosine_similarity(left: Mapping[str, float], right: Mapping[str, float]) -> float:
        if not left or not right:
            return 0.0
        shared_keys = set(left).intersection(right)
        if not shared_keys:
            return 0.0
        dot = sum(float(left[key]) * float(right[key]) for key in shared_keys)
        left_norm = sqrt(sum(float(value) ** 2 for value in left.values()))
        right_norm = sqrt(sum(float(value) ** 2 for value in right.values()))
        if left_norm <= 0 or right_norm <= 0:
            return 0.0
        return round(min(max(dot / (left_norm * right_norm), 0.0), 1.0), 6)

    @staticmethod
    def _suggestion_reason(
        *,
        affinity_similarity: float,
        shared_engagement_score: float,
        followers_count: int,
        has_creator_profile: bool,
    ) -> str:
        if shared_engagement_score >= affinity_similarity and shared_engagement_score >= 0.15:
            return "Shared engagement patterns"
        if affinity_similarity >= 0.15:
            return "Similar affinity profile"
        if followers_count > 0:
            return "Popular creator signal"
        if has_creator_profile:
            return "Active creator profile"
        return "Recommended for discovery"


@dataclass(slots=True)
class FollowGraphNotificationService:
    session: Session
    follow_graph_service: FollowGraphService

    def process_new_clips(self, clips: list[Any]) -> int:
        delivered = 0
        seen: set[tuple[str, str]] = set()
        for clip in clips:
            creator_id = self.follow_graph_service.resolve_creator_user_id(clip)
            clip_id = self._clip_id(clip)
            if not creator_id or not clip_id:
                continue
            dedupe_key = (creator_id, clip_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            delivered += self._deliver(
                template_key=FOLLOW_NOTIFICATION_TEMPLATE_KEY,
                creator_id=creator_id,
                clip=clip,
                message_template="{creator} posted a new clip: {title}",
            )
        return delivered

    def process_viral_clips(self, clips: list[Any], *, minimum_viral_score: float = 85.0) -> int:
        delivered = 0
        seen: set[tuple[str, str]] = set()
        for clip in clips:
            creator_id = self.follow_graph_service.resolve_creator_user_id(clip)
            clip_id = self._clip_id(clip)
            if not creator_id or not clip_id:
                continue
            if self._viral_score(clip) < minimum_viral_score:
                continue
            dedupe_key = (creator_id, clip_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            delivered += self._deliver(
                template_key=VIRAL_NOTIFICATION_TEMPLATE_KEY,
                creator_id=creator_id,
                clip=clip,
                message_template="{creator} is going viral: {title}",
            )
        return delivered

    def _deliver(
        self,
        *,
        template_key: str,
        creator_id: str,
        clip: Any,
        message_template: str,
    ) -> int:
        bind = self.session.get_bind()
        if bind is None or not self.follow_graph_service._table_exists(NotificationRecord.__tablename__):
            return 0
        follower_ids = self.follow_graph_service.follower_ids(creator_id)
        if not follower_ids:
            return 0
        resource_id = self._resource_id(clip)
        title = self._clip_title(clip)
        delivered = 0

        with Session(bind=bind, expire_on_commit=False) as notification_session:
            existing_user_ids = set(
                notification_session.scalars(
                    select(NotificationRecord.user_id).where(
                        NotificationRecord.template_key == template_key,
                        NotificationRecord.resource_type == NOTIFICATION_RESOURCE_TYPE,
                        NotificationRecord.resource_id == resource_id,
                        NotificationRecord.user_id.in_(tuple(sorted(follower_ids))),
                    )
                ).all()
            )
            creator = notification_session.get(User, creator_id)
            creator_label = "Creator"
            if creator is not None:
                creator_label = creator.display_name or creator.full_name or creator.username or creator_label
            message = message_template.format(creator=creator_label, title=title)[:255]
            metadata = {
                "creator_id": creator_id,
                "clip_id": self._clip_id(clip),
                "title": title,
                "viral_score": self._viral_score(clip),
            }

            for follower_id in sorted(follower_ids):
                if follower_id in existing_user_ids:
                    continue
                notification_session.add(
                    NotificationRecord(
                        user_id=follower_id,
                        topic="social_graph",
                        template_key=template_key,
                        resource_type=NOTIFICATION_RESOURCE_TYPE,
                        resource_id=resource_id,
                        message=message,
                        metadata_json=metadata,
                    )
                )
                delivered += 1
            if delivered:
                notification_session.commit()
        return delivered

    def _resource_id(self, clip: Any) -> str:
        return self._clip_id(clip)[:64]

    @staticmethod
    def _clip_id(clip: Any) -> str:
        if isinstance(clip, Mapping):
            value = clip.get("clip_id")
        else:
            value = getattr(clip, "clip_id", None)
        return str(value).strip() if value is not None and str(value).strip() else ""

    @staticmethod
    def _clip_title(clip: Any) -> str:
        if isinstance(clip, Mapping):
            value = clip.get("title")
        else:
            value = getattr(clip, "title", None)
        candidate = str(value).strip() if value is not None else ""
        return candidate or "New clip"

    @staticmethod
    def _viral_score(clip: Any) -> float:
        if isinstance(clip, Mapping):
            value = clip.get("viral_score", 0.0)
        else:
            value = getattr(clip, "viral_score", 0.0)
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0


def build_follow_graph_cache(*, settings: Settings | None = None) -> FollowGraphCache:
    resolved_settings = settings or get_settings()
    if resolved_settings.redis_url:
        cache = RedisFollowGraphCache(resolved_settings.redis_url)
        if cache.ping():
            return cache
    return NullFollowGraphCache()


def ensure_follow_graph_cache(app: FastAPI, *, settings: Settings | None = None) -> FollowGraphCache:
    cache = getattr(app.state, "follow_graph_cache", None)
    if cache is None:
        cache = build_follow_graph_cache(settings=settings or getattr(app.state, "settings", None))
        app.state.follow_graph_cache = cache
    return cache


def build_follow_graph_service(*, app: FastAPI, session: Session) -> FollowGraphService:
    settings = getattr(app.state, "settings", None) or get_settings()
    return FollowGraphService(
        session=session,
        cache=ensure_follow_graph_cache(app, settings=settings),
    )


def build_follow_notification_service(*, app: FastAPI, session: Session) -> FollowGraphNotificationService:
    return FollowGraphNotificationService(
        session=session,
        follow_graph_service=build_follow_graph_service(app=app, session=session),
    )


def following_feed_cache_subject(user_id: str) -> str:
    return f"{user_id}{FOLLOWING_FEED_CACHE_SUBJECT_SUFFIX}"


__all__ = [
    "FOLLOWERS_KEY_TEMPLATE",
    "FOLLOWING_FEED_KEY_TEMPLATE",
    "FOLLOWING_KEY_TEMPLATE",
    "FOLLOW_NOTIFICATION_TEMPLATE_KEY",
    "FollowGraphCache",
    "FollowGraphError",
    "FollowGraphNotFoundError",
    "FollowGraphNotificationService",
    "FollowGraphService",
    "NullFollowGraphCache",
    "RedisFollowGraphCache",
    "VIRAL_NOTIFICATION_TEMPLATE_KEY",
    "build_follow_graph_cache",
    "build_follow_graph_service",
    "build_follow_notification_service",
    "ensure_follow_graph_cache",
    "following_feed_cache_subject",
]
