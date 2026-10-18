"""Flag gate shared by the phase 4-6 routers."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.club_legacy.delegation import LegacyError
from app.club_legacy.flags import legacy_enabled
from app.club_legacy.models import ClubLegacyAuditEvent


def run_legacy(session: Session, fn):
    if not legacy_enabled(session):
        raise HTTPException(status_code=404, detail={"code": "club_legacy_disabled"})
    try:
        result = fn()
        session.commit()
        return result
    except LegacyError as exc:
        saved = list(session.info.get("legacy_refusals", []))
        session.rollback()
        if saved:
            for item in saved:
                session.add(ClubLegacyAuditEvent(**item))
            session.commit()
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "detail": exc.detail}) from exc
