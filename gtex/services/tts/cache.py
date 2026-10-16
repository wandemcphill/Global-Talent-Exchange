from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import logging

from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AudioCache:
    redis_url: str | None = None
    ttl_seconds: int = 43_200
    namespace: str = "gtex:tts:audio"
    _memory: dict[str, bytes] = field(default_factory=dict)
    _redis: Redis | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if not self.redis_url:
            return
        try:
            self._redis = Redis.from_url(self.redis_url, decode_responses=False)
            self._redis.ping()
        except Exception:
            logger.warning("tts.cache.redis_unavailable")
            self._redis = None

    def get_audio(self, *, text: str, voice_id: str, model_id: str, output_format: str) -> bytes | None:
        key = self._key(text=text, voice_id=voice_id, model_id=model_id, output_format=output_format)
        cached = self._memory.get(key)
        if cached is not None:
            return cached
        if self._redis is None:
            return None
        try:
            payload = self._redis.get(key)
        except RedisError:
            logger.warning("tts.cache.redis_get_failed")
            return None
        if payload is None:
            return None
        self._memory[key] = bytes(payload)
        return bytes(payload)

    def save_audio(self, *, text: str, voice_id: str, model_id: str, output_format: str, audio: bytes) -> None:
        if not audio:
            return
        key = self._key(text=text, voice_id=voice_id, model_id=model_id, output_format=output_format)
        payload = bytes(audio)
        self._memory[key] = payload
        if self._redis is None:
            return
        try:
            self._redis.set(name=key, value=payload, ex=max(self.ttl_seconds, 60))
        except RedisError:
            logger.warning("tts.cache.redis_set_failed")

    def _key(self, *, text: str, voice_id: str, model_id: str, output_format: str) -> str:
        digest = hashlib.md5(
            json.dumps(
                {
                    "text": text.strip(),
                    "voice_id": voice_id,
                    "model_id": model_id,
                    "output_format": output_format,
                },
                sort_keys=True,
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
        return f"{self.namespace}:{digest}"
