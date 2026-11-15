from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.analytics_event import AnalyticsEvent
from app.models.auth_session import AuthSession
from app.models.base import utcnow
from app.models.club_profile import ClubLifecycleStatus, ClubProfile
from app.models.competition_match import CompetitionMatch
from app.models.user import User
from app.public_pulse.schemas import LiveWorldPulseView

# The browser sends a lightweight heartbeat every 30 seconds. A 90-second
# expiry tolerates a missed request while dropping closed/backgrounded tabs.
USERS_ONLINE_WINDOW_SECONDS = 90
TRAFFIC_HEARTBEAT_INTERVAL_SECONDS = 30
PUBLIC_PAGE_VIEW_EVENT = "public.visitor.page_view"
_LIVE_MATCH_STATUSES = frozenset({"live", "in_progress", "playing", "started", "first_half", "second_half", "halftime"})


def _visitor_key(visitor_id: UUID) -> str:
    settings = get_settings()
    secret = settings.auth_secret or settings.field_encryption_key or "gtex-public-traffic-v1"
    return hmac.new(secret.encode("utf-8"), visitor_id.bytes, hashlib.sha256).hexdigest()


def _safe_path(raw_path: str) -> str:
    # Store only the path. Query strings and fragments can contain personal or
    # security-sensitive values and are intentionally excluded from analytics.
    path = urlsplit(raw_path).path.strip() or "/"
    if not path.startswith("/") or path.startswith("//"):
        return "/"
    return path[:200]


@dataclass(slots=True)
class PublicPulseService:
    session: Session

    def record_page_view(self, *, visitor_id: UUID, path: str, user_id: str | None) -> None:
        self.session.add(
            AnalyticsEvent(
                name=PUBLIC_PAGE_VIEW_EVENT,
                user_id=user_id,
                metadata_json={
                    "visitor_key": _visitor_key(visitor_id),
                    "path": _safe_path(path),
                },
            )
        )

    def live_world_pulse(self) -> LiveWorldPulseView:
        now = utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = now - timedelta(seconds=USERS_ONLINE_WINDOW_SECONDS)

        clubs = int(
            self.session.scalar(
                select(func.count())
                .select_from(ClubProfile)
                .where(ClubProfile.lifecycle_status == ClubLifecycleStatus.ACTIVE)
            )
            or 0
        )
        users_online = int(
            self.session.scalar(
                select(func.count(func.distinct(AuthSession.user_id)))
                .join(User, User.id == AuthSession.user_id)
                .where(
                    AuthSession.last_used_at.is_not(None),
                    AuthSession.last_used_at >= cutoff,
                    AuthSession.expires_at > now,
                    AuthSession.revoked_at.is_(None),
                    User.is_active.is_(True),
                )
            )
            or 0
        )
        registered_users = int(
            self.session.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
        )
        page_view_filter = (
            AnalyticsEvent.name == PUBLIC_PAGE_VIEW_EVENT,
            AnalyticsEvent.created_at >= today_start,
        )
        page_views_today = int(
            self.session.scalar(
                select(func.count()).select_from(AnalyticsEvent).where(*page_view_filter)
            )
            or 0
        )
        visitors_today = int(
            self.session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.metadata_json["visitor_key"].as_string()))).where(
                    *page_view_filter
                )
            )
            or 0
        )

        players_online = self._managers_in_live_matches()
        return LiveWorldPulseView(
            clubs_on_gtex=clubs,
            users_online=users_online,
            players_online=players_online,
            users_online_window_seconds=USERS_ONLINE_WINDOW_SECONDS,
            visitors_today=visitors_today,
            page_views_today=page_views_today,
            registered_users=registered_users,
            generated_at=now,
            labels={
                "clubs_on_gtex": "Active clubs on GTEX",
                "users_online": "Registered users active now",
                "players_online": "Managers in live matches",
                "visitors_today": "Unique visitors today",
                "page_views_today": "Page views today",
                "registered_users": "Registered user accounts",
            },
        )

    def _managers_in_live_matches(self) -> int:
        live_matches = list(
            self.session.scalars(
                select(CompetitionMatch).where(func.lower(CompetitionMatch.status).in_(tuple(_LIVE_MATCH_STATUSES)))
            ).all()
        )
        if not live_matches:
            return 0
        club_ids = {match.home_club_id for match in live_matches} | {match.away_club_id for match in live_matches}
        if not club_ids:
            return 0
        owner_ids = self.session.scalars(
            select(ClubProfile.owner_user_id).where(
                ClubProfile.id.in_(club_ids),
                ClubProfile.owner_user_id.is_not(None),
            )
        ).all()
        return len({owner_id for owner_id in owner_ids if owner_id})


__all__ = [
    "PUBLIC_PAGE_VIEW_EVENT",
    "TRAFFIC_HEARTBEAT_INTERVAL_SECONDS",
    "USERS_ONLINE_WINDOW_SECONDS",
    "PublicPulseService",
]
