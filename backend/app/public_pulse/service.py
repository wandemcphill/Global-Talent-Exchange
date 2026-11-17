from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta
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
# Rolling windows, not calendar weeks or months. A Monday or month-start reset
# would understate reach for advertisers early in the period. "Today" stays a
# UTC calendar day so the live board still resets at midnight.
TRAFFIC_ROLLING_WEEK = timedelta(days=7)
TRAFFIC_ROLLING_MONTH = timedelta(days=30)
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

    def record_page_view(self, *, visitor_id: UUID, path: str) -> None:
        # Keep browsing telemetry separate from account identity. Authenticated
        # presence is measured from AuthSession heartbeats, not page-view joins.
        self.session.add(
            AnalyticsEvent(
                name=PUBLIC_PAGE_VIEW_EVENT,
                user_id=None,
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
        visitors_today, page_views_today = self._traffic_totals(since=today_start)
        visitors_last_7_days, page_views_last_7_days = self._traffic_totals(since=now - TRAFFIC_ROLLING_WEEK)
        visitors_last_30_days, page_views_last_30_days = self._traffic_totals(since=now - TRAFFIC_ROLLING_MONTH)
        visitors_all_time, page_views_all_time = self._traffic_totals(since=None)

        players_online = self._managers_in_live_matches()
        return LiveWorldPulseView(
            clubs_on_gtex=clubs,
            users_online=users_online,
            players_online=players_online,
            users_online_window_seconds=USERS_ONLINE_WINDOW_SECONDS,
            visitors_today=visitors_today,
            visitors_last_7_days=visitors_last_7_days,
            visitors_last_30_days=visitors_last_30_days,
            visitors_all_time=visitors_all_time,
            page_views_today=page_views_today,
            page_views_last_7_days=page_views_last_7_days,
            page_views_last_30_days=page_views_last_30_days,
            page_views_all_time=page_views_all_time,
            registered_users=registered_users,
            generated_at=now,
            labels={
                "clubs_on_gtex": "Active clubs on GTEX",
                "users_online": "Registered users active now",
                "players_online": "Managers in live matches",
                "visitors_today": "Unique visitors today",
                "visitors_last_7_days": "Unique visitors in the last 7 days",
                "visitors_last_30_days": "Unique visitors in the last 30 days",
                "visitors_all_time": "Unique visitors all time",
                "page_views_today": "Page views today",
                "page_views_last_7_days": "Page views in the last 7 days",
                "page_views_last_30_days": "Page views in the last 30 days",
                "page_views_all_time": "Page views all time",
                "registered_users": "Registered user accounts",
            },
        )

    def _traffic_totals(self, *, since: datetime | None) -> tuple[int, int]:
        """Return unique visitors and page views for one window.

        A visitor is one browser, counted once per window. A page view is every
        recorded page open, so the same visitor can contribute many page views.
        Passing since=None keeps the full stored history.
        """
        filters = [AnalyticsEvent.name == PUBLIC_PAGE_VIEW_EVENT]
        if since is not None:
            filters.append(AnalyticsEvent.created_at >= since)
        page_views = int(
            self.session.scalar(select(func.count()).select_from(AnalyticsEvent).where(*filters)) or 0
        )
        visitors = int(
            self.session.scalar(
                select(func.count(func.distinct(AnalyticsEvent.metadata_json["visitor_key"].as_string()))).where(
                    *filters
                )
            )
            or 0
        )
        return visitors, page_views

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
