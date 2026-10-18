"""Shared flag guard for the phase routers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError
from app.club_legacy.flags import legacy_enabled
from app.club_legacy.models import ClubLegacyAuditEvent


def _disabled() -> None:
    raise HTTPException(status_code=404, detail={"code": "club_legacy_disabled"})


def _finish_error(session: Session, exc: LegacyError) -> None:
    saved = list(session.info.get("legacy_refusals", []))
    session.rollback()
    if saved:
        for item in saved:
            session.add(ClubLegacyAuditEvent(**item))
        session.commit()
    raise HTTPException(status_code=exc.status, detail={"code": exc.code, "detail": exc.detail}) from exc


def run_legacy(session: Session, fn: Callable[[], Any]) -> Any:
    if not legacy_enabled(session):
        _disabled()
    try:
        result = fn()
        session.commit()
        return result
    except LegacyError as exc:
        _finish_error(session, exc)


def run(session: Session, fn, *args, **kwargs):
    if not legacy_enabled(session):
        _disabled()
    try:
        result = fn(*args, **kwargs)
        session.commit()
        return result
    except LegacyError as exc:
        _finish_error(session, exc)
