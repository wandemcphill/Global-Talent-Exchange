from __future__ import annotations

from sqlalchemy.orm import Session

from app.admin_engine.service import AdminEngineService

FEATURE_KEY = "club_legacy"


def legacy_enabled(session: Session) -> bool:
    flags = AdminEngineService(session).list_feature_flags(active_only=True)
    return any(item.feature_key == FEATURE_KEY and item.enabled for item in flags)
