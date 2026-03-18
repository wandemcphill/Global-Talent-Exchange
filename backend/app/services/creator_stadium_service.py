from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.base import generate_uuid
from backend.app.models.club_infra import ClubStadium
from backend.app.models.creator_league import CreatorLeagueSeasonTier
from backend.app.models.creator_monetization import (
    CreatorStadiumControl,
    CreatorStadiumPlacement,
    CreatorStadiumPricing,
    CreatorStadiumProfile,
    CreatorStadiumTicketPurchase,
)
from backend.app.models.creator_share_market import CreatorClubShareHolding
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from backend.app.risk_ops_engine.service import RiskOpsService
from backend.app.services.creator_broadcast_service import (
    CreatorBeneficiary,
    CreatorBroadcastService,
    CreatorMatchContext,
)
from backend.app.services.spending_control_service import SpendingControlService, SpendingControlViolation
from backend.app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
CONTROL_KEY = "default"
MATCHDAY_TICKET = "matchday"
VIP_TICKET = "vip"
IN_STADIUM_AD = "in_stadium_ad"
SPONSOR_BANNER = "sponsor_banner"
STADIUM_LEVEL_CAPACITY = {
    1: 5000,
    2: 15000,
    3: 30000,
    4: 60000,
    5: 100000,
}
TICKET_CREATOR_SHARE = Decimal("0.5000")
PLACEMENT_CREATOR_SHARE = Decimal("0.5000")
SHAREHOLDER_TICKET_EARLY_ACCESS = timedelta(hours=48)
PUBLIC_TICKET_ACCESS = timedelta(hours=24)


class CreatorStadiumError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(frozen=True, slots=True)
class CreatorStadiumBundle:
    control: CreatorStadiumControl
    profile: CreatorStadiumProfile
    pricing: CreatorStadiumPricing | None


@dataclass(frozen=True, slots=True)
class CreatorMatchStadiumOffer:
    context: CreatorMatchContext
    control: CreatorStadiumControl
    profile: CreatorStadiumProfile
    pricing: CreatorStadiumPricing
    placements: tuple[CreatorStadiumPlacement, ...]
    sold_tickets: int
    sold_vip_tickets: int
    shareholder_ticket_access_opens_at: datetime | None
    public_ticket_access_opens_at: datetime | None
    ticket_access_phase: str
    actor_has_shareholder_access: bool

    @property
    def remaining_capacity(self) -> int:
        return max(0, int(self.profile.capacity) - int(self.sold_tickets))

    @property
    def remaining_vip_capacity(self) -> int:
        return max(0, int(self.profile.premium_seat_capacity) - int(self.sold_vip_tickets))


class CreatorStadiumService:
    def __init__(
        self,
        session: Session,
        *,
        wallet_service: WalletService | None = None,
        risk_ops: RiskOpsService | None = None,
        broadcast_service: CreatorBroadcastService | None = None,
    ) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService()
        self.risk_ops = risk_ops or RiskOpsService(session)
        self.broadcast_service = broadcast_service or CreatorBroadcastService(session, wallet_service=self.wallet_service)

    def get_admin_control(self) -> CreatorStadiumControl:
        item = self.session.scalar(
            select(CreatorStadiumControl).where(CreatorStadiumControl.control_key == CONTROL_KEY)
        )
        if item is None:
            item = CreatorStadiumControl(control_key=CONTROL_KEY, metadata_json={"stadium_levels": STADIUM_LEVEL_CAPACITY})
            self.session.add(item)
            self.session.flush()
        return item

    def update_admin_control(
        self,
        *,
        actor: User,
        max_matchday_ticket_price_coin: Decimal,
        max_season_pass_price_coin: Decimal,
        max_vip_ticket_price_coin: Decimal,
        max_stadium_level: int,
        vip_seat_ratio_bps: int,
        max_in_stadium_ad_slots: int,
        max_sponsor_banner_slots: int,
        ad_placement_enabled: bool,
        ticket_sales_enabled: bool = True,
        max_placement_price_coin: Decimal = Decimal("250.0000"),
    ) -> CreatorStadiumControl:
        control = self.get_admin_control()
        if max_stadium_level not in STADIUM_LEVEL_CAPACITY:
            raise CreatorStadiumError("Stadium level cap must be between level 1 and level 5.", reason="stadium_level_invalid")
        if vip_seat_ratio_bps <= 0:
            raise CreatorStadiumError("VIP seat ratio must be positive.", reason="vip_ratio_invalid")
        if max_in_stadium_ad_slots < 0 or max_sponsor_banner_slots < 0:
            raise CreatorStadiumError("Ad and banner slot limits must be zero or greater.", reason="slot_limit_invalid")
        normalized_placement_cap = self._normalize_amount(max_placement_price_coin)
        if normalized_placement_cap <= Decimal("0.0000"):
            raise CreatorStadiumError("Placement price cap must be positive.", reason="placement_price_cap_invalid")

        control.max_matchday_ticket_price_coin = self._normalize_amount(max_matchday_ticket_price_coin)
        control.max_season_pass_price_coin = self._normalize_amount(max_season_pass_price_coin)
        control.max_vip_ticket_price_coin = self._normalize_amount(max_vip_ticket_price_coin)
        control.max_stadium_level = max_stadium_level
        control.vip_seat_ratio_bps = vip_seat_ratio_bps
        control.max_in_stadium_ad_slots = max_in_stadium_ad_slots
        control.max_sponsor_banner_slots = max_sponsor_banner_slots
        control.ad_placement_enabled = bool(ad_placement_enabled)
        control.ticket_sales_enabled = bool(ticket_sales_enabled)
        control.max_placement_price_coin = normalized_placement_cap
        control.metadata_json = {"stadium_levels": STADIUM_LEVEL_CAPACITY}
        self._log_audit(
            actor_user_id=actor.id,
            action_key="creator_stadium.controls.updated",
            resource_id=control.id,
            detail="Creator stadium admin controls updated.",
            metadata_json={
                "control_key": control.control_key,
                "ticket_sales_enabled": bool(ticket_sales_enabled),
                "max_placement_price_coin": str(normalized_placement_cap),
            },
        )
        self._sync_profile_caps(control)
        self.session.flush()
        return control

    def get_club_bundle(self, *, club_id: str, season_id: str) -> CreatorStadiumBundle:
        control = self.get_admin_control()
        beneficiary = self._beneficiary_for_club(club_id)
        self._assert_club_in_season(club_id=club_id, season_id=season_id)
        profile = self._ensure_profile(club_id=club_id, creator_user_id=beneficiary.creator_user_id, control=control)
        pricing = self._pricing_for_season_club(season_id=season_id, club_id=club_id)
        return CreatorStadiumBundle(control=control, profile=profile, pricing=pricing)

    def configure_club_stadium(
        self,
        *,
        actor: User,
        club_id: str,
        season_id: str,
        matchday_ticket_price_coin: Decimal,
        season_pass_price_coin: Decimal,
        vip_ticket_price_coin: Decimal,
        visual_upgrade_level: int,
        custom_chant_text: str | None,
        custom_visuals_json: dict[str, Any] | None,
    ) -> CreatorStadiumBundle:
        control = self.get_admin_control()
        beneficiary = self._assert_actor_controls_club(actor=actor, club_id=club_id)
        self._assert_club_in_season(club_id=club_id, season_id=season_id)
        profile = self._ensure_profile(club_id=club_id, creator_user_id=beneficiary.creator_user_id, control=control)

        if visual_upgrade_level < 1 or visual_upgrade_level > int(profile.level):
            raise CreatorStadiumError(
                "Visual upgrade level must stay between 1 and the current stadium level.",
                reason="visual_upgrade_level_invalid",
            )

        matchday_price = self._validate_ticket_price(
            ticket_type=MATCHDAY_TICKET,
            amount=matchday_ticket_price_coin,
            cap=control.max_matchday_ticket_price_coin,
        )
        season_pass_price = self._validate_ticket_price(
            ticket_type="season_pass",
            amount=season_pass_price_coin,
            cap=control.max_season_pass_price_coin,
        )
        vip_price = self._validate_ticket_price(
            ticket_type=VIP_TICKET,
            amount=vip_ticket_price_coin,
            cap=control.max_vip_ticket_price_coin,
        )
        if vip_price < matchday_price:
            raise CreatorStadiumError(
                "VIP ticket pricing must be greater than or equal to the Matchday ticket price.",
                reason="vip_price_invalid",
            )

        pricing = self._pricing_for_season_club(season_id=season_id, club_id=club_id)
        if pricing is None:
            pricing = CreatorStadiumPricing(
                season_id=season_id,
                club_id=club_id,
                creator_user_id=beneficiary.creator_user_id,
                matchday_ticket_price_coin=matchday_price,
                season_pass_price_coin=season_pass_price,
                vip_ticket_price_coin=vip_price,
                metadata_json={},
            )
            self.session.add(pricing)

        profile.creator_user_id = beneficiary.creator_user_id
        profile.visual_upgrade_level = visual_upgrade_level
        profile.custom_chant_text = (custom_chant_text or "").strip() or None
        profile.custom_visuals_json = custom_visuals_json or {}
        profile.metadata_json = {"stadium_levels": STADIUM_LEVEL_CAPACITY}

        pricing.creator_user_id = beneficiary.creator_user_id
        pricing.matchday_ticket_price_coin = matchday_price
        pricing.season_pass_price_coin = season_pass_price
        pricing.vip_ticket_price_coin = vip_price
        pricing.metadata_json = {
            "creator_league_only": True,
            "price_caps_coin": {
                "matchday": str(control.max_matchday_ticket_price_coin),
                "season_pass": str(control.max_season_pass_price_coin),
                "vip": str(control.max_vip_ticket_price_coin),
            },
        }
        self.session.flush()
        self._log_audit(
            actor_user_id=actor.id,
            action_key="creator_stadium.config.updated",
            resource_id=profile.id,
            detail="Creator stadium pricing and fan experience updated.",
            metadata_json={"club_id": club_id, "season_id": season_id},
        )
        return CreatorStadiumBundle(control=control, profile=profile, pricing=pricing)

    def update_stadium_level(self, *, actor: User, club_id: str, level: int) -> CreatorStadiumProfile:
        control = self.get_admin_control()
        beneficiary = self._beneficiary_for_club(club_id)
        profile = self._ensure_profile(club_id=club_id, creator_user_id=beneficiary.creator_user_id, control=control)
        if level not in STADIUM_LEVEL_CAPACITY:
            raise CreatorStadiumError("Stadium level must be between level 1 and level 5.", reason="stadium_level_invalid")
        if level > int(control.max_stadium_level):
            raise CreatorStadiumError("Stadium level exceeds the current admin size cap.", reason="stadium_level_cap_exceeded")

        profile.level = level
        profile.capacity = STADIUM_LEVEL_CAPACITY[level]
        profile.premium_seat_capacity = self._premium_capacity_for(control=control, capacity=profile.capacity)
        if int(profile.visual_upgrade_level) > level:
            profile.visual_upgrade_level = level
        profile.metadata_json = {"stadium_levels": STADIUM_LEVEL_CAPACITY}
        self._log_audit(
            actor_user_id=actor.id,
            action_key="creator_stadium.level.updated",
            resource_id=profile.id,
            detail="Creator stadium level updated.",
            metadata_json={"club_id": club_id, "level": level, "capacity": profile.capacity},
        )
        self.session.flush()
        return profile

    def get_match_offer(
        self,
        *,
        match_id: str,
        actor: User | None = None,
        now: datetime | None = None,
    ) -> CreatorMatchStadiumOffer:
        context = self.broadcast_service.get_match_context(match_id)
        beneficiary = context.home_beneficiary
        if beneficiary is None:
            raise CreatorStadiumError(
                "Home creator club is not linked to an active creator profile.",
                reason="creator_profile_missing",
            )

        control = self.get_admin_control()
        profile = self._ensure_profile(
            club_id=context.match.home_club_id,
            creator_user_id=beneficiary.creator_user_id,
            control=control,
        )
        pricing = self._pricing_for_season_club(season_id=context.season.id, club_id=context.match.home_club_id)
        if pricing is None or not pricing.is_active:
            raise CreatorStadiumError(
                "Creator stadium pricing has not been configured for this match yet.",
                reason="stadium_pricing_not_configured",
            )

        placements = tuple(
            self.session.scalars(
                select(CreatorStadiumPlacement)
                .where(
                    CreatorStadiumPlacement.match_id == context.match.id,
                    CreatorStadiumPlacement.club_id == context.match.home_club_id,
                    CreatorStadiumPlacement.status == "active",
                )
                .order_by(CreatorStadiumPlacement.created_at.asc())
            ).all()
        )
        sold_tickets = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorStadiumTicketPurchase)
                .where(CreatorStadiumTicketPurchase.match_id == context.match.id)
            )
            or 0
        )
        sold_vip_tickets = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorStadiumTicketPurchase)
                .where(
                    CreatorStadiumTicketPurchase.match_id == context.match.id,
                    CreatorStadiumTicketPurchase.ticket_type == VIP_TICKET,
                )
            )
            or 0
        )
        shareholder_ticket_access_opens_at, public_ticket_access_opens_at, ticket_access_phase = self._ticket_access_window(
            match=context.match,
            now=now,
        )
        return CreatorMatchStadiumOffer(
            context=context,
            control=control,
            profile=profile,
            pricing=pricing,
            placements=placements,
            sold_tickets=sold_tickets,
            sold_vip_tickets=sold_vip_tickets,
            shareholder_ticket_access_opens_at=shareholder_ticket_access_opens_at,
            public_ticket_access_opens_at=public_ticket_access_opens_at,
            ticket_access_phase=ticket_access_phase,
            actor_has_shareholder_access=self._has_creator_shareholder_access(actor=actor, club_id=context.match.home_club_id),
        )

    def purchase_match_ticket(
        self,
        *,
        actor: User,
        match_id: str,
        ticket_type: str,
        now: datetime | None = None,
    ) -> CreatorStadiumTicketPurchase:
        normalized_type = (ticket_type or "").strip().lower()
        if normalized_type not in {MATCHDAY_TICKET, VIP_TICKET}:
            raise CreatorStadiumError(
                "Ticket type must be Matchday Ticket or VIP Ticket for single-match purchases.",
                reason="ticket_type_invalid",
            )

        offer = self.get_match_offer(match_id=match_id, actor=actor, now=now)
        if not offer.control.ticket_sales_enabled:
            raise CreatorStadiumError(
                "Creator stadium ticket sales are currently disabled by admin policy.",
                reason="ticket_sales_disabled",
            )
        if offer.ticket_access_phase == "closed":
            raise CreatorStadiumError(
                "Creator stadium ticket sales are not open yet for this match.",
                reason="ticket_sales_not_open",
            )
        if offer.ticket_access_phase == "shareholder_early" and not offer.actor_has_shareholder_access:
            raise CreatorStadiumError(
                "Early creator stadium ticket access is reserved for creator club fan shareholders.",
                reason="shareholder_early_access_required",
            )
        existing = self.session.scalar(
            select(CreatorStadiumTicketPurchase).where(
                CreatorStadiumTicketPurchase.user_id == actor.id,
                CreatorStadiumTicketPurchase.match_id == match_id,
            )
        )
        if existing is not None:
            if existing.ticket_type == normalized_type:
                return existing
            raise CreatorStadiumError(
                "A stadium ticket already exists for this user and match.",
                reason="stadium_ticket_already_owned",
            )
        if offer.remaining_capacity <= 0:
            raise CreatorStadiumError("This creator stadium is sold out for the selected match.", reason="stadium_sold_out")
        if normalized_type == VIP_TICKET and offer.remaining_vip_capacity <= 0:
            raise CreatorStadiumError("Premium fan seating is sold out for this match.", reason="vip_seating_sold_out")

        price = (
            self._normalize_amount(offer.pricing.vip_ticket_price_coin)
            if normalized_type == VIP_TICKET
            else self._normalize_amount(offer.pricing.matchday_ticket_price_coin)
        )
        control_evaluation = self._evaluate_ticket_purchase_controls(
            actor=actor,
            amount=price,
            ticket_type=normalized_type,
            offer=offer,
        )
        creator_share = self._normalize_amount(price * TICKET_CREATOR_SHARE)
        platform_share = self._normalize_amount(price - creator_share)

        item = CreatorStadiumTicketPurchase(
            user_id=actor.id,
            creator_user_id=offer.pricing.creator_user_id,
            season_id=offer.context.season.id,
            competition_id=offer.context.competition.id,
            match_id=offer.context.match.id,
            club_id=offer.context.match.home_club_id,
            ticket_type=normalized_type,
            seat_tier="premium" if normalized_type == VIP_TICKET else "general",
            price_coin=price,
            creator_share_coin=creator_share,
            platform_share_coin=platform_share,
            includes_live_video_access=True,
            includes_premium_seating=normalized_type == VIP_TICKET,
            includes_stadium_visual_upgrades=offer.pricing.stadium_visual_upgrades_enabled,
            includes_custom_chants=offer.pricing.custom_chants_enabled,
            includes_custom_visuals=offer.pricing.custom_visuals_enabled,
            metadata_json={
                "creator_league_only": True,
                "stadium_level": offer.profile.level,
                "stadium_capacity": offer.profile.capacity,
                "ticket_access_phase": offer.ticket_access_phase,
                "fan_experience": {
                    "live_video_match_access": True,
                    "stadium_visual_upgrades": offer.pricing.stadium_visual_upgrades_enabled,
                    "custom_club_chants": offer.pricing.custom_chants_enabled,
                    "custom_club_visuals": offer.pricing.custom_visuals_enabled,
                },
            },
        )
        self.session.add(item)
        self.session.flush()
        self._post_transaction(
            actor=actor,
            creator_user_id=offer.pricing.creator_user_id,
            total_amount=price,
            creator_share=creator_share,
            platform_share=platform_share,
            reference=f"creator-stadium-ticket:{item.id}",
            description=f"Creator stadium {normalized_type} ticket for match {offer.context.match.id}",
        )
        self._log_audit(
            actor_user_id=actor.id,
            action_key="creator_stadium.ticket.purchased",
            resource_id=item.id,
            detail="Creator stadium ticket purchased.",
            metadata_json={"match_id": match_id, "ticket_type": normalized_type},
        )
        self._distribute_shareholder_revenue(
            actor=actor,
            club_id=item.club_id,
            creator_user_id=item.creator_user_id,
            source_type="ticket_sales",
            source_reference_id=item.id,
            eligible_revenue_coin=item.creator_share_coin,
            season_id=item.season_id,
            competition_id=item.competition_id,
            match_id=item.match_id,
            metadata_json={"ticket_type": normalized_type},
        )
        SpendingControlService(self.session).record_evaluation(
            control_evaluation,
            entity_id=item.id,
            metadata_json={"creator_stadium_ticket_purchase_id": item.id},
        )
        return item

    def create_match_placement(
        self,
        *,
        actor: User,
        match_id: str,
        placement_type: str,
        slot_key: str,
        sponsor_name: str,
        price_coin: Decimal,
        creative_asset_url: str | None = None,
        copy_text: str | None = None,
        audit_note: str | None = None,
    ) -> CreatorStadiumPlacement:
        normalized_type = (placement_type or "").strip().lower()
        if normalized_type not in {IN_STADIUM_AD, SPONSOR_BANNER}:
            raise CreatorStadiumError(
                "Placement type must be in_stadium_ad or sponsor_banner.",
                reason="placement_type_invalid",
            )

        offer = self.get_match_offer(match_id=match_id)
        beneficiary = self._assert_actor_controls_club(actor=actor, club_id=offer.context.match.home_club_id)
        if not offer.control.ad_placement_enabled:
            raise CreatorStadiumError("The creator stadium ad placement system is currently disabled by admin.", reason="ad_placement_disabled")

        existing_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorStadiumPlacement)
                .where(
                    CreatorStadiumPlacement.match_id == offer.context.match.id,
                    CreatorStadiumPlacement.club_id == offer.context.match.home_club_id,
                    CreatorStadiumPlacement.placement_type == normalized_type,
                )
            )
            or 0
        )
        slot_limit = (
            int(offer.control.max_in_stadium_ad_slots)
            if normalized_type == IN_STADIUM_AD
            else int(offer.control.max_sponsor_banner_slots)
        )
        if existing_count >= slot_limit:
            raise CreatorStadiumError(
                "The configured slot limit has already been reached for this placement type.",
                reason="placement_slot_limit_reached",
            )

        gross_amount = self._normalize_amount(price_coin)
        if gross_amount <= Decimal("0.0000"):
            raise CreatorStadiumError("Placement price must be positive.", reason="placement_price_invalid")
        if gross_amount > self._normalize_amount(offer.control.max_placement_price_coin):
            raise CreatorStadiumError(
                "Placement pricing exceeds the current admin cap.",
                reason="placement_price_cap_exceeded",
            )
        creator_share = self._normalize_amount(gross_amount * PLACEMENT_CREATOR_SHARE)
        platform_share = self._normalize_amount(gross_amount - creator_share)

        item = CreatorStadiumPlacement(
            season_id=offer.context.season.id,
            competition_id=offer.context.competition.id,
            match_id=offer.context.match.id,
            club_id=offer.context.match.home_club_id,
            creator_user_id=beneficiary.creator_user_id,
            approved_by_admin_user_id=actor.id if actor.role.value in {"admin", "super_admin"} else None,
            placement_type=normalized_type,
            slot_key=(slot_key or "").strip().lower(),
            sponsor_name=sponsor_name.strip(),
            creative_asset_url=(creative_asset_url or "").strip() or None,
            copy_text=(copy_text or "").strip() or None,
            price_coin=gross_amount,
            creator_share_coin=creator_share,
            platform_share_coin=platform_share,
            status="active",
            audit_note=(audit_note or "").strip() or None,
            metadata_json={"creator_league_only": True, "slot_limit": slot_limit},
        )
        self.session.add(item)
        self.session.flush()
        self._log_audit(
            actor_user_id=actor.id,
            action_key="creator_stadium.placement.created",
            resource_id=item.id,
            detail="Creator stadium placement created.",
            metadata_json={"match_id": match_id, "placement_type": normalized_type, "slot_key": item.slot_key},
        )
        return item

    def list_match_placements(self, *, match_id: str) -> list[CreatorStadiumPlacement]:
        offer = self.get_match_offer(match_id=match_id)
        return list(offer.placements)

    def _beneficiary_for_club(self, club_id: str) -> CreatorBeneficiary:
        beneficiary = self.broadcast_service._beneficiaries_for_clubs((club_id,)).get(club_id)
        if beneficiary is None:
            raise CreatorStadiumError(
                "Creator club is not linked to an active creator profile.",
                reason="creator_profile_missing",
            )
        return beneficiary

    def _assert_actor_controls_club(self, *, actor: User, club_id: str) -> CreatorBeneficiary:
        beneficiary = self._beneficiary_for_club(club_id)
        if actor.role.value in {"admin", "super_admin"}:
            return beneficiary
        if beneficiary.creator_user_id != actor.id:
            raise CreatorStadiumError(
                "Only the scoped creator club owner can manage this stadium monetization surface.",
                reason="creator_scope_denied",
            )
        return beneficiary

    def _assert_club_in_season(self, *, club_id: str, season_id: str) -> None:
        count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorLeagueSeasonTier)
                .where(
                    CreatorLeagueSeasonTier.season_id == season_id,
                )
            )
            or 0
        )
        if count <= 0:
            raise CreatorStadiumError("Creator League season was not found.", reason="season_not_found")
        tiers = list(
            self.session.scalars(
                select(CreatorLeagueSeasonTier).where(CreatorLeagueSeasonTier.season_id == season_id)
            ).all()
        )
        if not any(club_id in (item.club_ids_json or []) for item in tiers):
            raise CreatorStadiumError(
                "Stadium monetization only applies to creator clubs in the selected season.",
                reason="stadium_creator_scope_invalid",
            )

    def _ensure_profile(
        self,
        *,
        club_id: str,
        creator_user_id: str,
        control: CreatorStadiumControl,
    ) -> CreatorStadiumProfile:
        item = self.session.scalar(
            select(CreatorStadiumProfile).where(CreatorStadiumProfile.club_id == club_id)
        )
        club_stadium = self.session.scalar(select(ClubStadium).where(ClubStadium.club_id == club_id))
        if item is None:
            item = CreatorStadiumProfile(
                club_id=club_id,
                creator_user_id=creator_user_id,
                club_stadium_id=club_stadium.id if club_stadium is not None else None,
                level=1,
                capacity=STADIUM_LEVEL_CAPACITY[1],
                premium_seat_capacity=self._premium_capacity_for(control=control, capacity=STADIUM_LEVEL_CAPACITY[1]),
                visual_upgrade_level=1,
                metadata_json={"stadium_levels": STADIUM_LEVEL_CAPACITY},
                custom_visuals_json={},
            )
            self.session.add(item)
            self.session.flush()
            return item

        item.creator_user_id = creator_user_id
        item.club_stadium_id = club_stadium.id if club_stadium is not None else item.club_stadium_id
        if int(item.level) not in STADIUM_LEVEL_CAPACITY:
            item.level = 1
            item.capacity = STADIUM_LEVEL_CAPACITY[1]
        if int(item.level) > int(control.max_stadium_level):
            item.level = int(control.max_stadium_level)
            item.capacity = STADIUM_LEVEL_CAPACITY[int(control.max_stadium_level)]
        if int(item.capacity) != STADIUM_LEVEL_CAPACITY[int(item.level)]:
            item.capacity = STADIUM_LEVEL_CAPACITY[int(item.level)]
        item.premium_seat_capacity = self._premium_capacity_for(control=control, capacity=int(item.capacity))
        if int(item.visual_upgrade_level) < 1:
            item.visual_upgrade_level = 1
        if int(item.visual_upgrade_level) > int(item.level):
            item.visual_upgrade_level = int(item.level)
        item.metadata_json = {"stadium_levels": STADIUM_LEVEL_CAPACITY}
        self.session.flush()
        return item

    def _sync_profile_caps(self, control: CreatorStadiumControl) -> None:
        profiles = list(self.session.scalars(select(CreatorStadiumProfile)).all())
        for profile in profiles:
            if int(profile.level) > int(control.max_stadium_level):
                profile.level = int(control.max_stadium_level)
                profile.capacity = STADIUM_LEVEL_CAPACITY[int(control.max_stadium_level)]
            profile.capacity = STADIUM_LEVEL_CAPACITY.get(int(profile.level), STADIUM_LEVEL_CAPACITY[1])
            profile.premium_seat_capacity = self._premium_capacity_for(control=control, capacity=int(profile.capacity))
            if int(profile.visual_upgrade_level) > int(profile.level):
                profile.visual_upgrade_level = int(profile.level)

    def _pricing_for_season_club(self, *, season_id: str, club_id: str) -> CreatorStadiumPricing | None:
        return self.session.scalar(
            select(CreatorStadiumPricing).where(
                CreatorStadiumPricing.season_id == season_id,
                CreatorStadiumPricing.club_id == club_id,
            )
        )

    def _validate_ticket_price(self, *, ticket_type: str, amount: Decimal, cap: Decimal) -> Decimal:
        normalized = self._normalize_amount(amount)
        if normalized <= Decimal("0.0000"):
            raise CreatorStadiumError("Ticket prices must be positive.", reason="ticket_price_invalid")
        if normalized > self._normalize_amount(cap):
            raise CreatorStadiumError(
                f"{ticket_type.replace('_', ' ').title()} pricing exceeds the current admin cap.",
                reason="ticket_price_cap_exceeded",
            )
        return normalized

    def _premium_capacity_for(self, *, control: CreatorStadiumControl, capacity: int) -> int:
        premium_capacity = int((Decimal(int(capacity)) * Decimal(int(control.vip_seat_ratio_bps)) / Decimal("10000")).to_integral_value(rounding=ROUND_HALF_UP))
        return max(1, premium_capacity)

    def _ticket_access_window(
        self,
        *,
        match,
        now: datetime | None = None,
    ) -> tuple[datetime | None, datetime | None, str]:
        scheduled_at = match.scheduled_at
        if scheduled_at is None:
            return None, None, "public"
        clock = now or datetime.now(UTC)
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=UTC)
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=UTC)
        shareholder_opens_at = scheduled_at - SHAREHOLDER_TICKET_EARLY_ACCESS
        public_opens_at = scheduled_at - PUBLIC_TICKET_ACCESS
        if clock < shareholder_opens_at:
            return shareholder_opens_at, public_opens_at, "closed"
        if clock < public_opens_at:
            return shareholder_opens_at, public_opens_at, "shareholder_early"
        return shareholder_opens_at, public_opens_at, "public"

    def _has_creator_shareholder_access(self, *, actor: User | None, club_id: str) -> bool:
        if actor is None:
            return False
        if actor.role.value in {"admin", "super_admin"}:
            return True
        return self.session.scalar(
            select(CreatorClubShareHolding.id).where(
                CreatorClubShareHolding.user_id == actor.id,
                CreatorClubShareHolding.club_id == club_id,
                CreatorClubShareHolding.share_count > 0,
            )
        ) is not None

    def _distribute_shareholder_revenue(
        self,
        *,
        actor: User,
        club_id: str,
        creator_user_id: str,
        source_type: str,
        source_reference_id: str,
        eligible_revenue_coin: Decimal,
        season_id: str | None,
        competition_id: str | None,
        match_id: str | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        from backend.app.services.creator_share_market_service import CreatorClubShareMarketError, CreatorClubShareMarketService

        try:
            CreatorClubShareMarketService(
                self.session,
                wallet_service=self.wallet_service,
                risk_ops=self.risk_ops,
            ).distribute_creator_revenue(
                actor=actor,
                club_id=club_id,
                creator_user_id=creator_user_id,
                source_type=source_type,
                source_reference_id=source_reference_id,
                eligible_revenue_coin=eligible_revenue_coin,
                season_id=season_id,
                competition_id=competition_id,
                match_id=match_id,
                metadata_json=metadata_json,
            )
        except CreatorClubShareMarketError as exc:
            if exc.reason != "share_market_not_found":
                raise CreatorStadiumError(exc.detail, reason=exc.reason) from exc

    def _post_transaction(
        self,
        *,
        actor: User,
        creator_user_id: str,
        total_amount: Decimal,
        creator_share: Decimal,
        platform_share: Decimal,
        reference: str,
        description: str,
    ) -> None:
        viewer_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
        creator_user = self.session.get(User, creator_user_id)
        if creator_user is None:
            raise CreatorStadiumError(
                "Creator beneficiary account was not found for this stadium transaction.",
                reason="creator_profile_missing",
            )
        creator_account = self.wallet_service.get_user_account(self.session, creator_user, LedgerUnit.COIN)
        try:
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=viewer_account,
                        amount=-self._normalize_amount(total_amount),
                        source_tag=LedgerSourceTag.VIDEO_VIEW_SPEND,
                    ),
                    LedgerPosting(
                        account=creator_account,
                        amount=self._normalize_amount(creator_share),
                        source_tag=LedgerSourceTag.MATCH_VIEW_REVENUE,
                    ),
                    LedgerPosting(
                        account=platform_account,
                        amount=self._normalize_amount(platform_share),
                        source_tag=LedgerSourceTag.MATCH_VIEW_REVENUE,
                    ),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                reference=reference,
                description=description,
                actor=actor,
            )
        except InsufficientBalanceError as exc:
            raise CreatorStadiumError(
                "Insufficient coin balance for this creator stadium transaction.",
                reason="insufficient_balance",
            ) from exc

    def _evaluate_ticket_purchase_controls(
        self,
        *,
        actor: User,
        amount: Decimal,
        ticket_type: str,
        offer: CreatorMatchStadiumOffer,
    ):
        reference_key = f"creator-purchase-control:stadium_ticket:{actor.id}:{generate_uuid()}"
        try:
            return SpendingControlService(self.session).evaluate_purchase(
                reference_key=reference_key,
                amount=amount,
                ledger_unit=LedgerUnit.COIN,
                actor_user_id=actor.id,
                purchase_scope="stadium_ticket",
                metadata_json={
                    "match_id": offer.context.match.id,
                    "competition_id": offer.context.competition.id,
                    "season_id": offer.context.season.id,
                    "club_id": offer.context.match.home_club_id,
                    "ticket_type": ticket_type,
                },
            )
        except SpendingControlViolation as exc:
            raise CreatorStadiumError(exc.detail, reason="spending_controls_blocked") from exc

    def _log_audit(
        self,
        *,
        actor_user_id: str | None,
        action_key: str,
        resource_id: str | None,
        detail: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> None:
        self.risk_ops.log_audit(
            actor_user_id=actor_user_id,
            action_key=action_key,
            resource_type="creator_stadium",
            resource_id=resource_id,
            detail=detail,
            metadata_json=metadata_json or {},
        )

    @staticmethod
    def _normalize_amount(value: Decimal | str | int | float) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


__all__ = [
    "CreatorMatchStadiumOffer",
    "CreatorStadiumBundle",
    "CreatorStadiumError",
    "CreatorStadiumService",
    "IN_STADIUM_AD",
    "MATCHDAY_TICKET",
    "SPONSOR_BANNER",
    "STADIUM_LEVEL_CAPACITY",
    "VIP_TICKET",
]
