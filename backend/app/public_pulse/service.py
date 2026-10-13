from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.base import utcnow
from app.models.club_profile import ClubLifecycleStatus, ClubProfile
from app.models.competition_match import CompetitionMatch
from app.models.user import User
from app.public_pulse.schemas import LiveWorldPulseView

USERS_ONLINE_WINDOW_SECONDS = 300
_LIVE_MATCH_STATUSES = frozenset({"live", "in_progress", "playing", "started", "first_half", "second_half", "halftime"})


@dataclass(slots=True)
class PublicPulseService:
    session: Session

    def live_world_pulse(self) -> LiveWorldPulseView:
        clubs = int(
            self.session.scalar(
                select(func.count())
                .select_from(ClubProfile)
                .where(ClubProfile.lifecycle_status == ClubLifecycleStatus.ACTIVE)
            )
            or 0
        )
        cutoff = utcnow() - timedelta(seconds=USERS_ONLINE_WINDOW_SECONDS)
        users_online = int(
            self.session.scalar(
                select(func.count())
                .select_from(User)
                .where(User.last_login_at.is_not(None), User.last_login_at >= cutoff)
            )
            or 0
        )
        players_online = self._managers_in_live_matches()
        return LiveWorldPulseView(
            clubs_on_gtex=clubs,
            users_online=users_online,
            players_online=players_online,
            users_online_window_seconds=USERS_ONLINE_WINDOW_SECONDS,
            generated_at=utcnow(),
            labels={
                "clubs_on_gtex": "Clubs created on GTEX",
                "users_online": "Users active now",
                "players_online": "Managers in live matches",
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
