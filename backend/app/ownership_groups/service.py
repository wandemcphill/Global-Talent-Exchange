from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.ingestion.models import Player
from app.models.base import generate_uuid
from app.models.club_profile import ClubProfile
from app.models.club_sale_market import ClubValuationSnapshot
from app.models.club_trophy import ClubTrophy
from app.models.notification_record import NotificationRecord
from app.models.ownership_group import (
    OwnershipGroup,
    OwnershipGroupBudgetMovement,
    OwnershipGroupClub,
    OwnershipGroupEvent,
)
from app.models.user import User

DECIMAL_QUANTUM = Decimal("0.0001")
INTERNAL_TRANSFER_VALUE_TOLERANCE = Decimal("0.2000")
INTERNAL_TRANSFER_LIMIT = 4
INTERNAL_TRANSFER_LOOKBACK_DAYS = 30


class OwnershipGroupError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(slots=True)
class OwnershipGroupService:
    session: Session
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def list_groups(self, *, actor: User) -> list[OwnershipGroup]:
        return list(
            self.session.scalars(
                select(OwnershipGroup)
                .where(OwnershipGroup.owner_user_id == actor.id)
                .order_by(OwnershipGroup.created_at.desc())
            ).all()
        )

    def get_group(self, *, actor: User, group_id: str) -> OwnershipGroup:
        group = self.session.get(OwnershipGroup, group_id)
        if group is None or group.owner_user_id != actor.id:
            raise OwnershipGroupError("Ownership group was not found.")
        return group

    def create_group(self, *, actor: User, payload) -> OwnershipGroup:
        owned_clubs = self._owned_clubs(actor.id)
        if len(owned_clubs) < 2:
            raise OwnershipGroupError("You need to own more than one club to create an ownership group.")
        selected_club_ids = payload.club_ids or [club.id for club in owned_clubs]
        if len(selected_club_ids) < 2:
            raise OwnershipGroupError("Ownership groups must start with at least two clubs.")
        group_name = payload.name.strip()
        existing = self.session.scalar(
            select(OwnershipGroup).where(
                OwnershipGroup.owner_user_id == actor.id,
                OwnershipGroup.name == group_name,
            )
        )
        if existing is not None:
            raise OwnershipGroupError("You already have an ownership group with this name.")
        group = OwnershipGroup(
            owner_user_id=actor.id,
            name=group_name,
            clubs_json=[],
            budget_pool=Decimal(payload.budget_pool).quantize(DECIMAL_QUANTUM),
            reputation_score=0.0,
            philosophy=payload.philosophy,
            shared_budget_enabled=payload.shared_budget_enabled,
            metadata_json={"budget_allocations": {}, "scouting_network_boost": 0.0, "branding_boost": 0.0},
        )
        self.session.add(group)
        self.session.flush()
        for club_id in selected_club_ids:
            self.add_club(actor=actor, group_id=group.id, club_id=club_id, notify=False)
        self._refresh_group_metrics(group)
        self._create_event(group, "empire_expansion", "Empire Expansion", {"club_count": len(group.clubs_json)})
        self._notify(
            user_id=actor.id,
            template_key="GROUP_CREATED",
            resource_id=group.id,
            message=f"Ownership group created: {group.name}.",
            metadata={"group_id": group.id, "club_count": len(group.clubs_json)},
        )
        self.session.flush()
        return group

    def add_club(self, *, actor: User, group_id: str, club_id: str, notify: bool = True) -> OwnershipGroup:
        group = self.get_group(actor=actor, group_id=group_id)
        club = self._require_owned_club(owner_user_id=actor.id, club_id=club_id)
        existing = self.session.scalar(select(OwnershipGroupClub).where(OwnershipGroupClub.club_id == club.id))
        if existing is not None and existing.group_id != group.id:
            raise OwnershipGroupError("Club already belongs to another ownership group.")
        if club.id in set(group.clubs_json or []):
            return group
        self.session.add(OwnershipGroupClub(group_id=group.id, club_id=club.id, metadata_json={}))
        group.clubs_json = [*list(group.clubs_json or []), club.id]
        self._refresh_group_metrics(group)
        self._create_event(group, "club_added", f"{club.club_name} joined {group.name}", {"club_id": club.id})
        if notify:
            self._notify(
                user_id=actor.id,
                template_key="CLUB_ADDED_TO_GROUP",
                resource_id=group.id,
                message=f"{club.club_name} added to {group.name}.",
                metadata={"group_id": group.id, "club_id": club.id},
            )
        self.session.flush()
        return group

    def allocate_budget(self, *, actor: User, group_id: str, club_id: str, amount: Decimal) -> OwnershipGroup:
        group = self.get_group(actor=actor, group_id=group_id)
        if not group.shared_budget_enabled:
            raise OwnershipGroupError("Shared budget is disabled for this ownership group.")
        if club_id not in set(group.clubs_json or []):
            raise OwnershipGroupError("Club is not attached to this ownership group.")
        normalized_amount = Decimal(amount).quantize(DECIMAL_QUANTUM)
        if normalized_amount > Decimal(group.budget_pool):
            raise OwnershipGroupError("Group budget pool is too small for this allocation.")
        allocations = self._budget_allocations(group)
        allocations[club_id] = (allocations.get(club_id, Decimal("0.0000")) + normalized_amount).quantize(DECIMAL_QUANTUM)
        group.budget_pool = (Decimal(group.budget_pool) - normalized_amount).quantize(DECIMAL_QUANTUM)
        group.metadata_json = {**dict(group.metadata_json or {}), "budget_allocations": {key: str(value) for key, value in allocations.items()}}
        self.session.add(
            OwnershipGroupBudgetMovement(
                group_id=group.id,
                source_club_id=None,
                target_club_id=club_id,
                movement_type="allocation",
                amount=normalized_amount,
                reference_key=f"group-allocation:{group.id}:{generate_uuid()}",
                created_by_user_id=actor.id,
                metadata_json={},
            )
        )
        self.session.flush()
        return group

    def transfer_budget(self, *, actor: User, group_id: str, source_club_id: str, target_club_id: str, amount: Decimal) -> OwnershipGroup:
        group = self.get_group(actor=actor, group_id=group_id)
        if not group.shared_budget_enabled:
            raise OwnershipGroupError("Shared budget is disabled for this ownership group.")
        attached_clubs = set(group.clubs_json or [])
        if source_club_id not in attached_clubs or target_club_id not in attached_clubs:
            raise OwnershipGroupError("Both clubs must belong to this ownership group.")
        if source_club_id == target_club_id:
            raise OwnershipGroupError("Source and target clubs must be different.")
        allocations = self._budget_allocations(group)
        normalized_amount = Decimal(amount).quantize(DECIMAL_QUANTUM)
        if allocations.get(source_club_id, Decimal("0.0000")) < normalized_amount:
            raise OwnershipGroupError("Source club allocation is too small for this transfer.")
        allocations[source_club_id] = (allocations.get(source_club_id, Decimal("0.0000")) - normalized_amount).quantize(DECIMAL_QUANTUM)
        allocations[target_club_id] = (allocations.get(target_club_id, Decimal("0.0000")) + normalized_amount).quantize(DECIMAL_QUANTUM)
        group.metadata_json = {**dict(group.metadata_json or {}), "budget_allocations": {key: str(value) for key, value in allocations.items()}}
        self.session.add(
            OwnershipGroupBudgetMovement(
                group_id=group.id,
                source_club_id=source_club_id,
                target_club_id=target_club_id,
                movement_type="internal_transfer",
                amount=normalized_amount,
                reference_key=f"group-transfer:{group.id}:{source_club_id}:{target_club_id}:{generate_uuid()}",
                created_by_user_id=actor.id,
                metadata_json={},
            )
        )
        self.session.flush()
        return group

    def validate_transfer(
        self,
        *,
        player_id: str,
        selling_club_id: str | None,
        buying_club_id: str | None,
        bid_amount: Decimal,
    ) -> dict[str, Any]:
        if selling_club_id is None or buying_club_id is None:
            return {"blocked": False, "recent_internal_transfer_count": 0}
        selling_group = self.get_group_for_club(selling_club_id)
        buying_group = self.get_group_for_club(buying_club_id)
        if selling_group is None or buying_group is None or selling_group.id != buying_group.id:
            return {"blocked": False, "recent_internal_transfer_count": 0}
        fair_value = self._fair_value_for_player(player_id)
        min_allowed = None
        max_allowed = None
        if fair_value > Decimal("0.0000"):
            min_allowed = (fair_value * (Decimal("1.0000") - INTERNAL_TRANSFER_VALUE_TOLERANCE)).quantize(DECIMAL_QUANTUM)
            max_allowed = (fair_value * (Decimal("1.0000") + INTERNAL_TRANSFER_VALUE_TOLERANCE)).quantize(DECIMAL_QUANTUM)
        recent_internal_transfer_count = self._recent_internal_transfer_count(selling_group.id)
        normalized_bid_amount = Decimal(bid_amount).quantize(DECIMAL_QUANTUM)
        blocked = False
        if min_allowed is not None and max_allowed is not None:
            blocked = normalized_bid_amount < min_allowed or normalized_bid_amount > max_allowed
        if recent_internal_transfer_count >= INTERNAL_TRANSFER_LIMIT:
            blocked = True
        reason = None
        if blocked:
            reason = "Internal transfers within the same ownership group must stay within the market-value guardrail."
            if recent_internal_transfer_count >= INTERNAL_TRANSFER_LIMIT:
                reason = "Ownership-group internal transfer limit reached for the last 30 days."
        return {
            "blocked": blocked,
            "reason": reason,
            "group_id": selling_group.id,
            "fair_value": fair_value,
            "min_allowed": min_allowed,
            "max_allowed": max_allowed,
            "recent_internal_transfer_count": recent_internal_transfer_count,
        }

    def get_group_for_club(self, club_id: str) -> OwnershipGroup | None:
        membership = self.session.scalar(select(OwnershipGroupClub).where(OwnershipGroupClub.club_id == club_id))
        if membership is None:
            return None
        return self.session.get(OwnershipGroup, membership.group_id)

    def detach_club(self, *, club_id: str) -> None:
        membership = self.session.scalar(select(OwnershipGroupClub).where(OwnershipGroupClub.club_id == club_id))
        if membership is None:
            return
        group = self.session.get(OwnershipGroup, membership.group_id)
        self.session.delete(membership)
        if group is None:
            return
        group.clubs_json = [value for value in list(group.clubs_json or []) if value != club_id]
        allocations = self._budget_allocations(group)
        allocations.pop(club_id, None)
        group.metadata_json = {**dict(group.metadata_json or {}), "budget_allocations": {key: str(value) for key, value in allocations.items()}}
        self._refresh_group_metrics(group)
        if not group.clubs_json:
            self.session.delete(group)
        self.session.flush()

    def ownership_map(self, club_ids: list[str]) -> dict[str, str]:
        if not club_ids:
            return {}
        memberships = list(
            self.session.scalars(select(OwnershipGroupClub).where(OwnershipGroupClub.club_id.in_(club_ids))).all()
        )
        return {membership.club_id: membership.group_id for membership in memberships}

    def build_competition_integrity_summary(self, club_ids: list[str]) -> dict[str, Any]:
        group_map = self.ownership_map(club_ids)
        collisions: dict[str, list[str]] = {}
        for club_id, group_id in group_map.items():
            collisions.setdefault(group_id, []).append(club_id)
        restricted = {group_id: clubs for group_id, clubs in collisions.items() if len(clubs) > 1}
        return {
            "shared_ownership_detected": bool(restricted),
            "restricted_groups": restricted,
        }

    def run_reputation_cycle(self) -> dict[str, int]:
        updated = 0
        triggered_events = 0
        for group in self.session.scalars(select(OwnershipGroup)).all():
            before = float(group.reputation_score or 0.0)
            self._refresh_group_metrics(group)
            updated += 1
            if before < 75.0 <= float(group.reputation_score):
                self._create_event(group, "brand_boom", "Brand Boom", {"reputation": group.reputation_score})
                triggered_events += 1
            elif Decimal(group.budget_pool) <= Decimal("0.0000") and len(group.clubs_json or []) > 1:
                self._create_event(group, "financial_crisis", "Financial Crisis", {"budget_pool": str(group.budget_pool)})
                triggered_events += 1
        self.session.flush()
        return {"groups_updated": updated, "events_triggered": triggered_events}

    def record_internal_transfer(self, *, group_id: str, source_club_id: str, target_club_id: str, amount: Decimal) -> None:
        self.session.add(
            OwnershipGroupBudgetMovement(
                group_id=group_id,
                source_club_id=source_club_id,
                target_club_id=target_club_id,
                movement_type="regulated_transfer",
                amount=Decimal(amount).quantize(DECIMAL_QUANTUM),
                reference_key=f"group-regulated-transfer:{group_id}:{generate_uuid()}",
                metadata_json={},
            )
        )
        self.session.flush()

    def club_value(self, club_id: str) -> Decimal:
        return self._club_value(club_id)

    def budget_allocations(self, group: OwnershipGroup) -> dict[str, Decimal]:
        return self._budget_allocations(group)

    def _refresh_group_metrics(self, group: OwnershipGroup) -> None:
        club_ids = list(group.clubs_json or [])
        total_value = sum((self._club_value(club_id) for club_id in club_ids), Decimal("0.0000")).quantize(DECIMAL_QUANTUM)
        trophy_score = Decimal(
            self.session.scalar(
                select(func.coalesce(func.sum(ClubTrophy.prestige_weight), 0)).where(ClubTrophy.club_id.in_(club_ids))
            )
            or 0
        )
        reputation = min(100.0, float((Decimal(len(club_ids)) * Decimal("8.0000")) + (trophy_score / Decimal("100.0000")) + (total_value / Decimal("50.0000"))))
        brand_strength = min(100.0, reputation + (len(club_ids) * 2.5))
        group.reputation_score = round(reputation, 2)
        group.global_brand_strength = round(brand_strength, 2)
        group.metadata_json = {
            **dict(group.metadata_json or {}),
            "scouting_network_boost": round(max(0.0, (len(club_ids) - 1) * 2.0), 2),
            "branding_boost": round(brand_strength * 0.05, 2),
        }

    def _club_value(self, club_id: str) -> Decimal:
        snapshot = self.session.scalar(
            select(ClubValuationSnapshot)
            .where(ClubValuationSnapshot.club_id == club_id)
            .order_by(ClubValuationSnapshot.created_at.desc())
        )
        if snapshot is None:
            return Decimal("0.0000")
        return Decimal(snapshot.total_value_coin).quantize(DECIMAL_QUANTUM)

    def _budget_allocations(self, group: OwnershipGroup) -> dict[str, Decimal]:
        raw = dict((group.metadata_json or {}).get("budget_allocations") or {})
        return {str(key): Decimal(str(value)).quantize(DECIMAL_QUANTUM) for key, value in raw.items()}

    def _recent_internal_transfer_count(self, group_id: str) -> int:
        lookback_starts_at = datetime.now(UTC) - timedelta(days=INTERNAL_TRANSFER_LOOKBACK_DAYS)
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(OwnershipGroupBudgetMovement)
                .where(
                    OwnershipGroupBudgetMovement.group_id == group_id,
                    OwnershipGroupBudgetMovement.movement_type == "regulated_transfer",
                    OwnershipGroupBudgetMovement.created_at >= lookback_starts_at,
                )
            )
            or 0
        )

    def _fair_value_for_player(self, player_id: str) -> Decimal:
        player = self.session.get(Player, player_id)
        if player is None:
            return Decimal("0.0000")
        baseline = Decimal(str(self.settings.value_engine_weighting.baseline_eur_per_credit or 100_000))
        return (Decimal(str(player.market_value_eur or 0)) / baseline).quantize(DECIMAL_QUANTUM)

    def _owned_clubs(self, owner_user_id: str) -> list[ClubProfile]:
        return list(
            self.session.scalars(
                select(ClubProfile).where(ClubProfile.owner_user_id == owner_user_id).order_by(ClubProfile.club_name.asc())
            ).all()
        )

    def _require_owned_club(self, *, owner_user_id: str, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None or club.owner_user_id != owner_user_id:
            raise OwnershipGroupError("Club was not found or is not owned by this user.")
        return club

    def _create_event(self, group: OwnershipGroup, event_type: str, headline: str, impact: dict[str, Any]) -> None:
        event = OwnershipGroupEvent(
            group_id=group.id,
            event_type=event_type,
            headline=headline,
            impact_json=dict(impact),
            metadata_json={},
        )
        self.session.add(event)
        self._notify(
            user_id=group.owner_user_id,
            template_key="GROUP_EVENT_TRIGGERED",
            resource_id=group.id,
            message=f"{group.name}: {headline}.",
            metadata={"group_id": group.id, "event_type": event_type, **dict(impact)},
        )

    def _notify(self, *, user_id: str | None, template_key: str, resource_id: str | None, message: str, metadata: dict[str, Any]) -> None:
        if user_id is None:
            return
        self.session.add(
            NotificationRecord(
                user_id=user_id,
                topic="ownership_group",
                template_key=template_key,
                resource_type="ownership_group",
                resource_id=resource_id,
                message=message[:255],
                metadata_json=dict(metadata),
            )
        )


__all__ = ["OwnershipGroupError", "OwnershipGroupService"]
