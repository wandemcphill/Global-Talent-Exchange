"""Shared request helper for the phase 7-9 routers."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError


def run(session: Session, fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
        session.commit()
        return result
    except LegacyError as exc:
        session.rollback()
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "detail": exc.detail}) from exc
