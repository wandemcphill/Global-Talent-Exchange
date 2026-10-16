from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.regen import RegenDiscoveryBadge


@dataclass(slots=True)
class RegenDiscoveryService:
    session: Session

    def award_badge(
        self,
        *,
        regen_id: str,
        club_id: str,
        badge_code: str,
        badge_name: str,
        metadata: dict[str, object] | None = None,
    ) -> RegenDiscoveryBadge:
        existing = self.session.scalar(
            select(RegenDiscoveryBadge).where(
                RegenDiscoveryBadge.regen_id == regen_id,
                RegenDiscoveryBadge.club_id == club_id,
                RegenDiscoveryBadge.badge_code == badge_code,
            )
        )
        if existing is not None:
            return existing
        badge = RegenDiscoveryBadge(
            regen_id=regen_id,
            club_id=club_id,
            badge_code=badge_code,
            badge_name=badge_name,
            metadata_json=metadata or {},
        )
        self.session.add(badge)
        self.session.flush()
        return badge

    def list_badges(self, regen_id: str) -> tuple[RegenDiscoveryBadge, ...]:
        badges = self.session.scalars(select(RegenDiscoveryBadge).where(RegenDiscoveryBadge.regen_id == regen_id)).all()
        return tuple(badges)


__all__ = ["RegenDiscoveryService"]
