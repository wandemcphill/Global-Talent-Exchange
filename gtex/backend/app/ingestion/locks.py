from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import utcnow

from .constants import DEFAULT_LOCK_TTL_SECONDS
from .models import IngestionJobLock


class LockAcquisitionError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LockHandle:
    lock_key: str
    owner_token: str
    expires_at: object
    acquired: bool


class IngestionLockManager:
    def __init__(self, session: Session):
        self.session = session

    def acquire(self, lock_key: str, *, ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS) -> LockHandle:
        now = utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)
        owner_token = str(uuid4())
        lock = self.session.scalar(select(IngestionJobLock).where(IngestionJobLock.lock_key == lock_key))
        if lock is not None and self._coerce_datetime(lock.expires_at) > now:
            return LockHandle(lock_key=lock_key, owner_token=owner_token, expires_at=lock.expires_at, acquired=False)
        try:
            if lock is None:
                lock = IngestionJobLock(
                    lock_key=lock_key,
                    owner_token=owner_token,
                    acquired_at=now,
                    last_heartbeat_at=now,
                    expires_at=expires_at,
                )
                self.session.add(lock)
            else:
                lock.owner_token = owner_token
                lock.acquired_at = now
                lock.last_heartbeat_at = now
                lock.expires_at = expires_at
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            return LockHandle(lock_key=lock_key, owner_token=owner_token, expires_at=expires_at, acquired=False)
        return LockHandle(lock_key=lock_key, owner_token=owner_token, expires_at=expires_at, acquired=True)

    def heartbeat(self, handle: LockHandle, *, ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS) -> None:
        lock = self.session.scalar(select(IngestionJobLock).where(IngestionJobLock.lock_key == handle.lock_key))
        if lock is None or lock.owner_token != handle.owner_token:
            raise LockAcquisitionError(f"Lock '{handle.lock_key}' is no longer owned by this worker.")
        now = utcnow()
        lock.last_heartbeat_at = now
        lock.expires_at = now + timedelta(seconds=ttl_seconds)
        self.session.commit()

    def release(self, handle: LockHandle) -> None:
        lock = self.session.scalar(select(IngestionJobLock).where(IngestionJobLock.lock_key == handle.lock_key))
        if lock is None:
            self.session.rollback()
            return
        if lock.owner_token == handle.owner_token:
            self.session.delete(lock)
            self.session.commit()
            return
        self.session.rollback()

    def _coerce_datetime(self, value):
        if value.tzinfo is None:
            return value.replace(tzinfo=utcnow().tzinfo)
        return value
