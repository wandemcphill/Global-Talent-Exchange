from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from uuid import uuid4

from app.common.enums.academy_player_status import AcademyPlayerStatus
from app.schemas.academy_core import AcademyGraduationEventView, AcademyPlayerView


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AcademyGraduationService:
    def build_event(
        self,
        *,
        club_id: str,
        player: AcademyPlayerView,
        from_status: AcademyPlayerStatus,
        to_status: AcademyPlayerStatus,
        reason: str,
    ) -> AcademyGraduationEventView:
        return AcademyGraduationEventView(
            id=f"agr-{uuid4().hex[:12]}",
            club_id=club_id,
            player_id=player.id,
            player_name=player.display_name,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            created_at=_utcnow(),
        )


@lru_cache
def get_academy_graduation_service() -> AcademyGraduationService:
    return AcademyGraduationService()


__all__ = ["AcademyGraduationService", "get_academy_graduation_service"]
