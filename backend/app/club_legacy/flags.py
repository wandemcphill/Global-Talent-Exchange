from __future__ import annotations

from sqlalchemy.orm import Session

from app.admin_engine.service import AdminEngineService
from app.club_legacy.delegation import LegacyError

FEATURE_KEY = "club_legacy"
MARKET_KEY = "club_legacy_market"
PRESEASON_KEY = "club_legacy_preseason"
SPONSORS_KEY = "club_legacy_sponsors"
GOVERNANCE_KEY = "club_legacy_governance"
SUBSYSTEM_KEYS = (MARKET_KEY, PRESEASON_KEY, SPONSORS_KEY, GOVERNANCE_KEY)


def flag_enabled(session: Session, feature_key: str) -> bool:
    flags = AdminEngineService(session).list_feature_flags(active_only=True)
    return any(item.feature_key == feature_key and item.enabled for item in flags)


def legacy_enabled(session: Session) -> bool:
    return flag_enabled(session, FEATURE_KEY)


def require_enabled(session: Session, *feature_keys: str) -> None:
    """Parent flag hides every Club Legacy route. A subsystem flag hides only its own."""
    if not legacy_enabled(session):
        raise LegacyError("club_legacy_disabled", 404)
    for feature_key in feature_keys:
        if not flag_enabled(session, feature_key):
            raise LegacyError(f"{feature_key}_disabled", 404)
