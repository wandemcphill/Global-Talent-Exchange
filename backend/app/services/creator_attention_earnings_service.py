from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import logging
from typing import Any

from fastapi import FastAPI
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.event_backbone import defer_session_callback_until_commit
from app.models.base import generate_uuid, utcnow
from app.models.creator_attention_earnings import (
    ClipEarningEventType,
    ClipEarningsLog,
    CreatorWallet,
)
from app.models.creator_profile import CreatorProfile
from app.models.user import User
from app.services.earnings import normalize_amount

logger = logging.getLogger(__name__)

CREATOR_WALLET_REDIS_KEY = "creator_wallet:{creator_user_id}"
CLIP_EARNINGS_REDIS_KEY = "clip_earnings:{clip_id}"
DEFAULT_IMPRESSION_BASE_RATE = Decimal("0.0020")
DEFAULT_ENGAGEMENT_BONUS = Decimal("0.0100")
DEFAULT_VIRALITY_BONUS = Decimal("0.0250")

LIKE_EVENT_NAMES = frozenset({"clip.like", "clip_like", "like"})
SHARE_EVENT_NAMES = frozenset({"clip.share", "clip_share", "share"})


@dataclass(slots=True)
class CreatorAttentionEarningsCache:
    redis_url: str | None = None
    _client: Redis | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.redis_url:
            return
        try:
            self._client = Redis.from_url(self.redis_url, decode_responses=True)
            self._client.ping()
        except RedisError:
            logger.warning("creator_attention_earnings.redis.unavailable")
            self._client = None

    def record_delta(
        self,
        *,
        creator_user_id: str,
        clip_id: str,
        impression_delta: int,
        like_delta: int,
        share_delta: int,
        earnings_delta_credit: Decimal,
        wallet_balance_credit: Decimal,
        event_type: str,
        event_at: datetime,
    ) -> None:
        if self._client is None:
            return
        wallet_key = CREATOR_WALLET_REDIS_KEY.format(creator_user_id=creator_user_id)
        clip_key = CLIP_EARNINGS_REDIS_KEY.format(clip_id=clip_id)
        earnings_value = float(normalize_amount(earnings_delta_credit))
        balance_value = str(normalize_amount(wallet_balance_credit))
        event_time = event_at.isoformat()
        try:
            pipeline = self._client.pipeline()
            if impression_delta:
                pipeline.hincrby(wallet_key, "total_impressions", int(impression_delta))
                pipeline.hincrby(clip_key, "impressions", int(impression_delta))
            if like_delta:
                pipeline.hincrby(wallet_key, "total_likes", int(like_delta))
                pipeline.hincrby(clip_key, "likes", int(like_delta))
            if share_delta:
                pipeline.hincrby(wallet_key, "total_shares", int(share_delta))
                pipeline.hincrby(clip_key, "shares", int(share_delta))
            if earnings_value:
                pipeline.hincrbyfloat(wallet_key, "total_earnings_credit", earnings_value)
                pipeline.hincrbyfloat(wallet_key, "available_balance_credit", earnings_value)
                pipeline.hincrbyfloat(clip_key, "earnings_credit", earnings_value)
            pipeline.hset(
                wallet_key,
                mapping={
                    "last_event_at": event_time,
                    "last_event_type": event_type,
                    "available_balance_credit": balance_value,
                },
            )
            pipeline.hset(
                clip_key,
                mapping={
                    "creator_user_id": creator_user_id,
                    "last_event_at": event_time,
                    "last_event_type": event_type,
                },
            )
            pipeline.execute()
        except RedisError:
            logger.warning("creator_attention_earnings.redis.write_failed creator_user_id=%s clip_id=%s", creator_user_id, clip_id)


def build_creator_attention_earnings_cache(*, settings: Settings | None = None) -> CreatorAttentionEarningsCache:
    resolved_settings = settings
    if resolved_settings is None:
        try:
            resolved_settings = get_settings()
        except Exception:
            resolved_settings = None
    return CreatorAttentionEarningsCache(
        redis_url=(resolved_settings.redis_url if resolved_settings is not None else None)
    )


def ensure_creator_attention_earnings_cache(
    app: FastAPI,
    *,
    settings: Settings | None = None,
) -> CreatorAttentionEarningsCache:
    cache = getattr(app.state, "creator_attention_earnings_cache", None)
    if cache is None:
        cache = build_creator_attention_earnings_cache(
            settings=settings or getattr(app.state, "settings", None)
        )
        app.state.creator_attention_earnings_cache = cache
    return cache


@dataclass(slots=True)
class CreatorAttentionEarningsService:
    session: Session
    app: FastAPI | None = None
    settings: Settings | None = None
    cache: CreatorAttentionEarningsCache | None = None
    impression_base_rate: Decimal = DEFAULT_IMPRESSION_BASE_RATE
    engagement_bonus: Decimal = DEFAULT_ENGAGEMENT_BONUS
    virality_bonus: Decimal = DEFAULT_VIRALITY_BONUS
    _storage_available: bool | None = field(init=False, default=None, repr=False)
    _creator_profiles_available: bool | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        if self.settings is None:
            if self.app is not None:
                self.settings = getattr(self.app.state, "settings", None)
            if self.settings is None:
                try:
                    self.settings = get_settings()
                except Exception:
                    self.settings = None
        if self.cache is None:
            self.cache = (
                ensure_creator_attention_earnings_cache(self.app, settings=self.settings)
                if self.app is not None
                else build_creator_attention_earnings_cache(settings=self.settings)
            )
        self.impression_base_rate = normalize_amount(self.impression_base_rate)
        self.engagement_bonus = normalize_amount(self.engagement_bonus)
        self.virality_bonus = normalize_amount(self.virality_bonus)

    def track_impression(
        self,
        *,
        clip,
        viewer_user_id: str | None,
        feed_source: str,
        session_id: str | None = None,
        slot_index: int | None = None,
        reference_key: str | None = None,
    ) -> ClipEarningsLog | None:
        metadata = {
            "feed_source": feed_source,
            "session_id": session_id,
            "slot_index": slot_index,
            "match_id": getattr(clip, "match_id", None),
            "event_origin": "feed_delivery",
        }
        return self._record_event(
            event_type=ClipEarningEventType.IMPRESSION,
            clip_id=str(getattr(clip, "clip_id", "") or "").strip(),
            viewer_user_id=viewer_user_id,
            clip=clip,
            metadata=metadata,
            reference_key=reference_key,
        )

    def track_engagement_event(
        self,
        *,
        name: str,
        clip_id: str,
        viewer_user_id: str | None,
        metadata: dict[str, Any] | None = None,
        reference_key: str | None = None,
    ) -> ClipEarningsLog | None:
        resolved_event_type = self._event_type_from_name(name)
        if resolved_event_type is None:
            return None
        return self._record_event(
            event_type=resolved_event_type,
            clip_id=clip_id,
            viewer_user_id=viewer_user_id,
            metadata=metadata,
            reference_key=reference_key,
        )

    def _record_event(
        self,
        *,
        event_type: ClipEarningEventType,
        clip_id: str,
        viewer_user_id: str | None,
        clip: Any | None = None,
        metadata: dict[str, Any] | None = None,
        reference_key: str | None = None,
    ) -> ClipEarningsLog | None:
        resolved_clip_id = str(clip_id or "").strip()
        if not resolved_clip_id or not self._supports_storage():
            return None

        clip_metadata = dict(getattr(clip, "metadata", {}) or {})
        event_metadata = dict(metadata or {})
        creator_user_id = self._resolve_creator_user_id(
            clip_metadata={**clip_metadata, **event_metadata}
        )
        if creator_user_id is None:
            return None
        if viewer_user_id and viewer_user_id == creator_user_id:
            return None
        resolved_reference = self._resolve_reference_key(
            event_type=event_type,
            clip_id=resolved_clip_id,
            viewer_user_id=viewer_user_id,
            reference_key=reference_key,
        )
        existing = self.session.scalar(
            select(ClipEarningsLog).where(ClipEarningsLog.reference_key == resolved_reference)
        )
        if existing is not None:
            return existing

        impression_delta = 1 if event_type is ClipEarningEventType.IMPRESSION else 0
        like_delta = 1 if event_type is ClipEarningEventType.LIKE else 0
        share_delta = 1 if event_type is ClipEarningEventType.SHARE else 0
        base_rate_credit = self.impression_base_rate if impression_delta else Decimal("0.0000")
        engagement_bonus_credit = self.engagement_bonus if like_delta else Decimal("0.0000")
        virality_bonus_credit = self.virality_bonus if share_delta else Decimal("0.0000")
        earnings_delta_credit = normalize_amount(
            base_rate_credit + engagement_bonus_credit + virality_bonus_credit
        )
        if earnings_delta_credit <= Decimal("0.0000"):
            return None

        wallet = self._get_or_create_wallet(creator_user_id=creator_user_id)
        event_at = utcnow()
        log_savepoint = self.session.begin_nested()
        try:
            wallet.total_impressions += impression_delta
            wallet.total_likes += like_delta
            wallet.total_shares += share_delta
            wallet.total_earnings_credit = normalize_amount(
                wallet.total_earnings_credit + earnings_delta_credit
            )
            wallet.available_balance_credit = normalize_amount(
                wallet.available_balance_credit + earnings_delta_credit
            )
            wallet.last_event_at = event_at
            wallet.metadata_json = {
                **dict(wallet.metadata_json or {}),
                "last_clip_id": resolved_clip_id,
                "last_event_type": event_type.value,
                "last_feed_source": event_metadata.get("feed_source"),
            }

            log = ClipEarningsLog(
                clip_id=resolved_clip_id,
                creator_user_id=creator_user_id,
                viewer_user_id=viewer_user_id,
                event_type=event_type,
                reference_key=resolved_reference,
                impression_delta=impression_delta,
                like_delta=like_delta,
                share_delta=share_delta,
                base_rate_credit=base_rate_credit,
                engagement_bonus_credit=engagement_bonus_credit,
                virality_bonus_credit=virality_bonus_credit,
                earnings_delta_credit=earnings_delta_credit,
                creator_wallet_balance_credit=wallet.available_balance_credit,
                metadata_json={
                    **clip_metadata,
                    **event_metadata,
                },
            )
            self.session.add(log)
            self.session.flush()
        except IntegrityError:
            log_savepoint.rollback()
            existing = self.session.scalar(
                select(ClipEarningsLog).where(ClipEarningsLog.reference_key == resolved_reference)
            )
            if existing is not None:
                return existing
            raise
        else:
            log_savepoint.commit()
        self._defer_cache_update(
            creator_user_id=creator_user_id,
            clip_id=resolved_clip_id,
            impression_delta=impression_delta,
            like_delta=like_delta,
            share_delta=share_delta,
            earnings_delta_credit=earnings_delta_credit,
            wallet_balance_credit=wallet.available_balance_credit,
            event_type=event_type.value,
            event_at=event_at,
        )
        self._defer_metrics_update(
            event_type=event_type.value,
            earnings_delta_credit=earnings_delta_credit,
        )
        return log

    def _get_or_create_wallet(self, *, creator_user_id: str) -> CreatorWallet:
        statement = select(CreatorWallet).where(CreatorWallet.creator_user_id == creator_user_id)
        if self._supports_row_locks():
            statement = statement.with_for_update()
        wallet = self.session.scalar(statement)
        if wallet is not None:
            return wallet
        savepoint = self.session.begin_nested()
        try:
            wallet = CreatorWallet(
                creator_user_id=creator_user_id,
                total_impressions=0,
                total_likes=0,
                total_shares=0,
                total_earnings_credit=Decimal("0.0000"),
                available_balance_credit=Decimal("0.0000"),
                metadata_json={},
            )
            self.session.add(wallet)
            self.session.flush()
        except IntegrityError:
            savepoint.rollback()
            wallet = self.session.scalar(statement)
            if wallet is None:
                raise
        else:
            savepoint.commit()
        assert wallet is not None
        return wallet

    def _defer_cache_update(
        self,
        *,
        creator_user_id: str,
        clip_id: str,
        impression_delta: int,
        like_delta: int,
        share_delta: int,
        earnings_delta_credit: Decimal,
        wallet_balance_credit: Decimal,
        event_type: str,
        event_at: datetime,
    ) -> None:
        if self.cache is None:
            return
        defer_session_callback_until_commit(
            self.session,
            callback=lambda cache=self.cache,
            creator_user_id=creator_user_id,
            clip_id=clip_id,
            impression_delta=impression_delta,
            like_delta=like_delta,
            share_delta=share_delta,
            earnings_delta_credit=earnings_delta_credit,
            wallet_balance_credit=wallet_balance_credit,
            event_type=event_type,
            event_at=event_at: cache.record_delta(
                creator_user_id=creator_user_id,
                clip_id=clip_id,
                impression_delta=impression_delta,
                like_delta=like_delta,
                share_delta=share_delta,
                earnings_delta_credit=earnings_delta_credit,
                wallet_balance_credit=wallet_balance_credit,
                event_type=event_type,
                event_at=event_at,
            ),
        )

    def _defer_metrics_update(
        self,
        *,
        event_type: str,
        earnings_delta_credit: Decimal,
    ) -> None:
        metrics = self._metrics()
        if metrics is None:
            return
        defer_session_callback_until_commit(
            self.session,
            callback=lambda metrics=metrics,
            event_type=event_type,
            earnings_delta_credit=earnings_delta_credit: metrics.record_creator_earnings(
                event_type=event_type,
                result="committed",
                earnings_delta_credit=earnings_delta_credit,
            ),
        )

    def _resolve_creator_user_id(self, *, clip_metadata: dict[str, Any]) -> str | None:
        creator_user_id = self._candidate_user_id(
            clip_metadata,
            "creator_user_id",
            "author_user_id",
            "owner_user_id",
        )
        if creator_user_id is not None:
            return creator_user_id

        creator_id = self._candidate_string(clip_metadata, "creator_id", "creator_key")
        if creator_id is None:
            return None
        if self._user_exists(creator_id):
            return creator_id
        if not self._supports_creator_profiles():
            return None
        try:
            profile = self.session.get(CreatorProfile, creator_id)
            if profile is not None:
                return str(profile.user_id)
            profile = self.session.scalar(
                select(CreatorProfile).where(CreatorProfile.handle == creator_id)
            )
            if profile is not None:
                return str(profile.user_id)
        except Exception:
            return None
        return None

    def _candidate_user_id(self, payload: dict[str, Any], *keys: str) -> str | None:
        value = self._candidate_string(payload, *keys)
        if value is None:
            return None
        if self._user_exists(value):
            return value
        return None

    @staticmethod
    def _candidate_string(payload: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _user_exists(self, user_id: str) -> bool:
        if not hasattr(self.session, "get"):
            return False
        try:
            return self.session.get(User, user_id) is not None
        except Exception:
            return False

    def _supports_storage(self) -> bool:
        if self._storage_available is not None:
            return self._storage_available
        try:
            bind = self.session.get_bind() if hasattr(self.session, "get_bind") else None
            if bind is None:
                self._storage_available = False
                return False
            inspector = inspect(bind)
            self._storage_available = all(
                inspector.has_table(table_name)
                for table_name in (CreatorWallet.__tablename__, ClipEarningsLog.__tablename__, User.__tablename__)
            )
        except Exception:
            self._storage_available = False
        return self._storage_available

    def _supports_creator_profiles(self) -> bool:
        if self._creator_profiles_available is not None:
            return self._creator_profiles_available
        try:
            bind = self.session.get_bind() if hasattr(self.session, "get_bind") else None
            if bind is None:
                self._creator_profiles_available = False
                return False
            self._creator_profiles_available = bool(inspect(bind).has_table(CreatorProfile.__tablename__))
        except Exception:
            self._creator_profiles_available = False
        return self._creator_profiles_available

    def _supports_row_locks(self) -> bool:
        bind = self.session.get_bind() if hasattr(self.session, "get_bind") else None
        return bind is not None and bind.dialect.name != "sqlite"

    def _metrics(self):
        if self.app is None:
            return None
        return getattr(self.app.state, "metrics", None)

    @staticmethod
    def _event_type_from_name(name: str) -> ClipEarningEventType | None:
        normalized = str(name or "").strip().lower()
        if normalized in LIKE_EVENT_NAMES:
            return ClipEarningEventType.LIKE
        if normalized in SHARE_EVENT_NAMES:
            return ClipEarningEventType.SHARE
        return None

    @staticmethod
    def _build_reference_key(*, event_type: ClipEarningEventType) -> str:
        return f"creator-attention:{event_type.value}:{generate_uuid()}"

    def _resolve_reference_key(
        self,
        *,
        event_type: ClipEarningEventType,
        clip_id: str,
        viewer_user_id: str | None,
        reference_key: str | None,
    ) -> str:
        if event_type in {ClipEarningEventType.LIKE, ClipEarningEventType.SHARE} and viewer_user_id:
            return f"creator-attention:{event_type.value}:{clip_id}:{viewer_user_id}"
        resolved = (reference_key or self._build_reference_key(event_type=event_type)).strip()
        if resolved:
            return resolved
        return self._build_reference_key(event_type=event_type)


def build_creator_attention_earnings_service(
    *,
    session: Session,
    app: FastAPI | None = None,
) -> CreatorAttentionEarningsService:
    return CreatorAttentionEarningsService(session=session, app=app)


__all__ = [
    "CreatorAttentionEarningsCache",
    "CreatorAttentionEarningsService",
    "build_creator_attention_earnings_cache",
    "build_creator_attention_earnings_service",
    "ensure_creator_attention_earnings_cache",
]
