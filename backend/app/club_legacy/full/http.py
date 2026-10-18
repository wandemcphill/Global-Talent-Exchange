"""Shared flag guard for the phase routers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError
from app.club_legacy.flags import legacy_enabled


def run_legacy(session: Session, fn: Callable[[], Any]) -> Any:
    if not legacy_enabled(session):
        raise HTTPException(status_code=404, detail={"code": "club_legacy_disabled"})
    try:
        result = fn()
        session.commit()
        return result
    except LegacyError as exc:
        session.rollback()
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "detail": exc.detail}) from exc
