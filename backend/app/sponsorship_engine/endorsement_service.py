"""Admin outbound regen endorsement deals (60/40 owner/platform)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.access_control import PlayerOwnership
from app.models.regen_endorsement import RegenEndorsementDeal, RegenEndorsementStatus
from app.models.user import User, UserRole
from app.story_feed_engine.service import StoryFeedService


class RegenEndorsementError(ValueError):
    pass


@dataclass(slots=True)
class RegenEndorsementService:
    session: Session

    def create_offer(
        self,
        *,
        actor: User,
        player_id: str,
        sponsor_name: str,
        brand_label: str,
        deal_value_minor: int,
        term_months: int = 3,
        badge_label: str = "Endorsed",
        creative_url: str | None = None,
        notes: str | None = None,
        activate: bool = False,
    ) -> RegenEndorsementDeal:
        player = self.session.get(Player, player_id)
        if player is None:
            raise RegenEndorsementError("Player was not found.")
        ownership = self.session.scalar(
            select(PlayerOwnership).where(PlayerOwnership.player_id == player_id).limit(1)
        )
        owner_user_id = ownership.agent_user_id if ownership is not None else None
        now = datetime.now(UTC)
        status = RegenEndorsementStatus.ACTIVE if activate else RegenEndorsementStatus.OFFERED
        deal = RegenEndorsementDeal(
            player_id=player_id,
            owner_user_id=owner_user_id,
            sponsor_name=sponsor_name.strip(),
            brand_label=brand_label.strip(),
            status=status,
            term_months=term_months,
            deal_value_minor=deal_value_minor,
            owner_share_ratio=Decimal("0.6000"),
            platform_share_ratio=Decimal("0.4000"),
            badge_label=badge_label.strip() or "Endorsed",
            creative_url=creative_url,
            offered_by_user_id=actor.id,
            starts_at=now if activate else None,
            ends_at=(now + timedelta(days=30 * term_months)) if activate else None,
            notes=notes,
            metadata_json={"split": "60/40"},
        )
        self.session.add(deal)
        self.session.flush()
        if activate:
            self._publish_story(deal, player)
        return deal

    def respond(
        self,
        *,
        actor: User,
        deal_id: str,
        accept: bool,
    ) -> RegenEndorsementDeal:
        deal = self.session.get(RegenEndorsementDeal, deal_id)
        if deal is None:
            raise RegenEndorsementError("Endorsement deal was not found.")
        if deal.owner_user_id and deal.owner_user_id != actor.id and actor.role != UserRole.ADMIN:
            raise RegenEndorsementError("Only the player owner or admin can respond.")
        if deal.status != RegenEndorsementStatus.OFFERED:
            raise RegenEndorsementError("Deal is no longer awaiting a response.")
        if accept:
            now = datetime.now(UTC)
            deal.status = RegenEndorsementStatus.ACTIVE
            deal.starts_at = now
            deal.ends_at = now + timedelta(days=30 * deal.term_months)
            player = self.session.get(Player, deal.player_id)
            if player is not None:
                self._publish_story(deal, player)
        else:
            deal.status = RegenEndorsementStatus.DECLINED
        self.session.flush()
        return deal

    def list_for_player(self, *, player_id: str) -> list[RegenEndorsementDeal]:
        return list(
            self.session.scalars(
                select(RegenEndorsementDeal)
                .where(RegenEndorsementDeal.player_id == player_id)
                .order_by(RegenEndorsementDeal.created_at.desc())
            ).all()
        )

    def active_badge(self, *, player_id: str) -> dict[str, Any] | None:
        deal = self.session.scalar(
            select(RegenEndorsementDeal)
            .where(
                RegenEndorsementDeal.player_id == player_id,
                RegenEndorsementDeal.status == RegenEndorsementStatus.ACTIVE,
            )
            .order_by(RegenEndorsementDeal.created_at.desc())
            .limit(1)
        )
        if deal is None:
            return None
        return {
            "deal_id": deal.id,
            "badge_label": deal.badge_label,
            "sponsor_name": deal.sponsor_name,
            "brand_label": deal.brand_label,
            "creative_url": deal.creative_url,
        }

    def _publish_story(self, deal: RegenEndorsementDeal, player: Player) -> None:
        name = (
            getattr(player, "canonical_display_name", None)
            or getattr(player, "full_name", None)
            or "Regen star"
        )
        StoryFeedService(self.session).publish(
            story_type="sponsorship_update",
            title=f"{name} lands {deal.sponsor_name} endorsement",
            body=f"{deal.brand_label} signs a GTEX regen deal (60% owner · 40% platform).",
            subject_type="player",
            subject_id=player.id,
            metadata_json={"deal_id": deal.id, "sponsor_name": deal.sponsor_name},
            published_by_user_id=deal.offered_by_user_id,
        )


__all__ = ["RegenEndorsementError", "RegenEndorsementService"]
