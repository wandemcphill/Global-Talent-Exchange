from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.models.base import utcnow
from app.models.club_squad_tier import SQUAD_TIERS, SQUAD_TIER_SOURCES, ClubSquadTierMembership
from app.squad_tiers.schemas import (
    AcademyIntakeView,
    SquadTierMemberView,
    SquadTiersView,
)

U21_MAX_AGE = 21


class SquadTierError(ValueError):
    """Raised on invalid squad-tier operations."""


def _player_age(date_of_birth: date | None) -> int | None:
    if date_of_birth is None:
        return None
    today = datetime.now(tz=timezone.utc).date()
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return max(0, years)


class SquadTierService:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ---- reads -------------------------------------------------------------

    def list_squad(self, club_id: str) -> SquadTiersView:
        rows = self._active_memberships(club_id)
        view = SquadTiersView(club_id=club_id, total=len(rows))
        for membership, player in rows:
            member = self._member_view(membership, player)
            if membership.tier == "first_team":
                view.first_team.append(member)
            elif membership.tier == "u21":
                view.u21.append(member)
            else:
                view.reserve.append(member)
        return view

    def academy_intake(self, club_id: str) -> AcademyIntakeView:
        view = AcademyIntakeView(club_id=club_id)
        for membership, player in self._active_memberships(club_id):
            if membership.tier == "first_team":
                continue
            member = self._member_view(membership, player)
            view.youth.append(member)
            if member.promotion_readiness in {"aged_out", "ready"}:
                view.ready_to_sign_up.append(member)
        return view

    # ---- writes ------------------------------------------------------------

    def assign_tier(
        self,
        *,
        club_id: str,
        player_id: str,
        tier: str,
        actor_user_id: str | None = None,
    ) -> SquadTierMemberView:
        if tier not in SQUAD_TIERS:
            raise SquadTierError(f"Unknown tier '{tier}'.")
        player = self.session.get(Player, player_id)
        if player is None:
            raise SquadTierError("Player not found.")
        age = _player_age(player.date_of_birth)
        if tier == "u21" and (age is None or age > U21_MAX_AGE):
            raise SquadTierError("Only players aged 21 or under can join the U21 squad.")

        membership = self._active_membership_for(club_id, player_id)
        now = utcnow()
        if membership is None:
            membership = ClubSquadTierMembership(
                club_id=club_id,
                player_id=player_id,
                tier=tier,
                source="manual",
                status="active",
                joined_club_at=now,
                joined_tier_at=now,
                metadata_json={"assigned_by": actor_user_id} if actor_user_id else {},
            )
            self.session.add(membership)
        elif membership.tier != tier:
            membership.tier = tier
            membership.joined_tier_at = now
            meta = dict(membership.metadata_json or {})
            meta["last_assigned_by"] = actor_user_id
            membership.metadata_json = meta
        self.session.flush()
        return self._member_view(membership, player)

    def ensure_membership(
        self,
        *,
        club_id: str,
        player_id: str,
        tier: str,
        source: str = "manual",
    ) -> ClubSquadTierMembership:
        """Idempotent create — integration hook for regen generation, son, transfer, academy promotion."""
        if tier not in SQUAD_TIERS:
            raise SquadTierError(f"Unknown tier '{tier}'.")
        if source not in SQUAD_TIER_SOURCES:
            source = "manual"
        existing = self._active_membership_for(club_id, player_id)
        if existing is not None:
            return existing
        now = utcnow()
        membership = ClubSquadTierMembership(
            club_id=club_id,
            player_id=player_id,
            tier=tier,
            source=source,
            status="active",
            joined_club_at=now,
            joined_tier_at=now,
        )
        self.session.add(membership)
        self.session.flush()
        return membership

    # ---- helpers -----------------------------------------------------------

    def _active_membership_for(
        self, club_id: str, player_id: str
    ) -> ClubSquadTierMembership | None:
        return self.session.scalar(
            select(ClubSquadTierMembership).where(
                ClubSquadTierMembership.club_id == club_id,
                ClubSquadTierMembership.player_id == player_id,
                ClubSquadTierMembership.status == "active",
            )
        )

    def _active_memberships(
        self, club_id: str
    ) -> list[tuple[ClubSquadTierMembership, Player]]:
        stmt = (
            select(ClubSquadTierMembership, Player)
            .join(Player, Player.id == ClubSquadTierMembership.player_id)
            .where(
                ClubSquadTierMembership.club_id == club_id,
                ClubSquadTierMembership.status == "active",
            )
        )
        return list(self.session.execute(stmt).all())

    def _member_view(
        self, membership: ClubSquadTierMembership, player: Player
    ) -> SquadTierMemberView:
        age = _player_age(player.date_of_birth)
        readiness = "settled"
        if membership.tier in {"u21", "reserve"}:
            if age is not None and age > U21_MAX_AGE:
                readiness = "aged_out"
            else:
                readiness = "developing"
        return SquadTierMemberView(
            player_id=player.id,
            player_name=player.full_name,
            position=player.normalized_position or player.position,
            secondary_positions=list(player.secondary_positions_json or []),
            age=age,
            tier=membership.tier,
            source=membership.source,
            promotion_readiness=readiness,
        )
