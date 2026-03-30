from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from threading import RLock
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access_control.service import AccessControlService
from app.core.events import DomainEvent, EventPublisher
from app.ingestion.models import Player
from app.models.access_control import OrganizationRole, OrganizationType
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.models.player_agency_state import PlayerAgencyState
from app.models.player_contract import PlayerContract
from app.models.player_personality import PlayerPersonality
from app.models.regen import RegenProfile
from app.models.transfer_market import (
    ClubTeamDynamics,
    CoachDemand,
    CoachProfile,
    MarketWatchlistEntry,
    PlayerCoachRelationship,
    PlayerDecisionProfile,
    TransferListing,
    TransferListingBid,
    TransferNegotiation,
)
from app.models.user import User, UserRole
from app.schemas.player_agency import ContractDecisionRequest, TransferDecisionRequest
from app.schemas.player_lifecycle import TransferBidAcceptRequest, TransferBidCreateRequest, TransferBidRejectRequest
from app.services.player_agency_context_service import PlayerAgencyContextService, clamp, quantize_amount
from app.services.player_agency_service import PlayerAgencyService
from app.services.player_lifecycle_service import (
    PlayerLifecycleError,
    PlayerLifecycleNotFoundError,
    PlayerLifecycleService,
    PlayerLifecycleValidationError,
)
from app.transfer_market.schemas import (
    AgentNegotiationView,
    ClubTeamDynamicsView,
    CoachDemandView,
    CoachOpinionView,
    CoachProfileUpsertRequest,
    CoachProfileView,
    ContractOfferRequest,
    MarketWatchlistEntryView,
    PlayerDecisionProfileUpsertRequest,
    PlayerDecisionProfileView,
    PlayerDecisionView,
    TeamDynamicsUpsertRequest,
    TransferBidderView,
    TransferListingCreateRequest,
    TransferListingView,
    TransferMarketJobRunView,
    TransferMarketPlayerView,
    TransferMarketStateView,
    TransferMarketStreamEventView,
    TransferNegotiationView,
    WatchlistEntryCreateRequest,
)

ANTI_SNIPING_WINDOW_SECONDS = 30
ANTI_SNIPING_EXTENSION_SECONDS = 90
LATE_HIJACK_WINDOW_SECONDS = 60
PLAYER_DECISION_DELAY_HOURS = 12
AGENT_COUNTER_DEADLINE_HOURS = 12
TRANSFER_MARKET_EXECUTION_ROLES = frozenset({OrganizationRole.ADMIN, OrganizationRole.CLUB})
TRANSFER_MARKET_WATCHLIST_ROLES = frozenset(
    {OrganizationRole.ADMIN, OrganizationRole.CLUB, OrganizationRole.SCOUT}
)


class TransferMarketError(Exception):
    """Base transfer market error."""


class TransferMarketNotFoundError(TransferMarketError):
    """Raised when a transfer market resource cannot be found."""


class TransferMarketValidationError(TransferMarketError):
    """Raised when transfer market validation fails."""


class TransferMarketPermissionError(TransferMarketError):
    """Raised when the authenticated actor lacks required access."""


@dataclass(slots=True)
class _TransferMarketRuntime:
    listing_id: str
    channel: str
    status: str
    snapshot: TransferListingView | None = None
    events: list[TransferMarketStreamEventView] = field(default_factory=list)


@dataclass(slots=True)
class TransferMarketHub:
    _listings: dict[str, _TransferMarketRuntime] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def update_listing(self, snapshot: TransferListingView) -> None:
        with self._lock:
            runtime = self._listings.get(snapshot.id)
            if runtime is None:
                runtime = _TransferMarketRuntime(
                    listing_id=snapshot.id,
                    channel=f"transfer:{snapshot.id}",
                    status=snapshot.status,
                )
                self._listings[snapshot.id] = runtime
            runtime.status = snapshot.status
            runtime.snapshot = snapshot

    def publish_event(self, listing_id: str, event_type: str, payload: dict[str, Any]) -> TransferMarketStreamEventView:
        event = TransferMarketStreamEventView(
            event_id=f"tm_{uuid4().hex[:12]}",
            event_type=event_type,
            created_at=utcnow(),
            payload=payload,
        )
        with self._lock:
            runtime = self._listings.get(listing_id)
            if runtime is None:
                runtime = _TransferMarketRuntime(
                    listing_id=listing_id,
                    channel=f"transfer:{listing_id}",
                    status="open",
                )
                self._listings[listing_id] = runtime
            runtime.events.append(event)
        return event

    def get_state(self, listing_id: str) -> TransferMarketStateView | None:
        with self._lock:
            runtime = self._listings.get(listing_id)
            if runtime is None:
                return None
            return TransferMarketStateView(
                listing_id=runtime.listing_id,
                channel=runtime.channel,
                status=runtime.status,
                event_count=len(runtime.events),
                snapshot=runtime.snapshot,
            )

    def get_events_since(self, listing_id: str, cursor: int) -> tuple[list[TransferMarketStreamEventView], int]:
        with self._lock:
            runtime = self._listings.get(listing_id)
            if runtime is None:
                return [], cursor
            return list(runtime.events[cursor:]), len(runtime.events)


def ensure_transfer_market_hub(app: FastAPI) -> TransferMarketHub:
    hub = getattr(app.state, "transfer_market_hub", None)
    if hub is None:
        hub = TransferMarketHub()
        app.state.transfer_market_hub = hub
    return hub


@dataclass(slots=True)
class TransferMarketService:
    session: Session
    event_publisher: EventPublisher | None = None
    hub: TransferMarketHub | None = None
    context_service: PlayerAgencyContextService = field(init=False)

    def __post_init__(self) -> None:
        self.context_service = PlayerAgencyContextService(self.session)

    def _access_control(self) -> AccessControlService:
        return AccessControlService(self.session)

    def _require_admin_actor(
        self,
        actor: User,
        *,
        forbidden_detail: str = "transfer_market_admin_access_required",
    ) -> None:
        if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise TransferMarketPermissionError(forbidden_detail)

    def _require_actor_club_access(
        self,
        actor: User,
        club_id: str,
        *,
        allowed_roles: frozenset[OrganizationRole] = TRANSFER_MARKET_EXECUTION_ROLES,
        forbidden_detail: str = "transfer_market_club_access_required",
    ) -> ClubProfile:
        try:
            return self._access_control().require_club_access(
                user=actor,
                club_id=club_id,
                allowed_roles=set(allowed_roles),
                forbidden_detail=forbidden_detail,
            )
        except LookupError as exc:
            raise TransferMarketNotFoundError(str(exc)) from exc
        except PermissionError as exc:
            raise TransferMarketPermissionError(str(exc)) from exc

    def _resolve_actor_club_id(
        self,
        actor: User,
        requested_club_id: str | None,
        *,
        allowed_roles: frozenset[OrganizationRole] = TRANSFER_MARKET_EXECUTION_ROLES,
        forbidden_detail: str = "transfer_market_club_access_required",
    ) -> str:
        cleaned_club_id = (requested_club_id or "").strip()
        if cleaned_club_id:
            self._require_actor_club_access(
                actor,
                cleaned_club_id,
                allowed_roles=allowed_roles,
                forbidden_detail=forbidden_detail,
            )
            return cleaned_club_id

        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise TransferMarketValidationError("Club identity must be specified for admin transfer-market actions.")

        context = self._access_control().bind_user_access_context(actor)
        eligible_club_ids = list(
            dict.fromkeys(
                membership.organization_id
                for membership in context.memberships
                if membership.organization_type == OrganizationType.CLUB and membership.role in allowed_roles
            )
        )
        for owned_club_id in self.session.scalars(select(ClubProfile.id).where(ClubProfile.owner_user_id == actor.id)).all():
            if owned_club_id not in eligible_club_ids:
                eligible_club_ids.append(owned_club_id)
        active_club_id = context.active_organization_id
        if (
            context.active_organization_type == OrganizationType.CLUB
            and active_club_id is not None
            and active_club_id in eligible_club_ids
        ):
            return active_club_id
        if len(eligible_club_ids) == 1:
            return eligible_club_ids[0]
        if not eligible_club_ids:
            raise TransferMarketPermissionError(forbidden_detail)
        raise TransferMarketValidationError("Club identity must be specified when multiple club contexts are available.")

    def _require_actor_any_club_access(
        self,
        actor: User,
        club_ids: list[str],
        *,
        allowed_roles: frozenset[OrganizationRole] = TRANSFER_MARKET_EXECUTION_ROLES,
        forbidden_detail: str = "transfer_market_club_access_required",
    ) -> None:
        unique_club_ids = list(dict.fromkeys(club_ids))
        if not unique_club_ids:
            raise TransferMarketPermissionError(forbidden_detail)
        last_permission_error: TransferMarketPermissionError | None = None
        for club_id in unique_club_ids:
            try:
                self._require_actor_club_access(
                    actor,
                    club_id,
                    allowed_roles=allowed_roles,
                    forbidden_detail=forbidden_detail,
                )
            except TransferMarketPermissionError as exc:
                last_permission_error = exc
                continue
            else:
                return
        if last_permission_error is not None:
            raise last_permission_error
        raise TransferMarketPermissionError(forbidden_detail)

    def list_listings(
        self,
        *,
        status: str | None = None,
        player_id: str | None = None,
        club_id: str | None = None,
        reference_at: datetime | None = None,
    ) -> list[TransferListingView]:
        statement = select(TransferListing).order_by(TransferListing.created_at.desc())
        if status is not None:
            statement = statement.where(TransferListing.status == status)
        if player_id is not None:
            statement = statement.where(TransferListing.player_id == player_id)
        if club_id is not None:
            statement = statement.where(
                (TransferListing.selling_club_id == club_id) | (TransferListing.highest_bidder_id == club_id)
            )
        effective_at = self._coerce_utc(reference_at or utcnow())
        return [self.to_listing_view(item, reference_at=effective_at) for item in self.session.scalars(statement).all()]

    def get_listing(self, listing_id: str, *, reference_at: datetime | None = None) -> TransferListingView:
        listing = self._require_listing(listing_id)
        return self.to_listing_view(listing, reference_at=self._coerce_utc(reference_at or utcnow()))

    def get_current_player_club(self, player_id: str, *, on_date: date | None = None) -> ClubProfile:
        club_id = self._current_player_club_id(player_id, on_date=on_date or utcnow().date())
        if club_id is None:
            raise TransferMarketValidationError("Player is not currently assigned to a club.")
        return self._require_club(club_id)

    def create_listing(
        self,
        payload: TransferListingCreateRequest,
        *,
        actor: User,
        selling_club_id: str | None = None,
        reference_at: datetime | None = None,
    ) -> TransferListingView:
        effective_at = self._coerce_utc(reference_at or utcnow())
        expires_at = self._coerce_utc(payload.expires_at)
        if expires_at <= effective_at:
            raise TransferMarketValidationError("Transfer listing expiry must be in the future.")
        resolved_selling_club_id = self._resolve_actor_club_id(
            actor,
            selling_club_id or payload.selling_club_id,
            allowed_roles=TRANSFER_MARKET_EXECUTION_ROLES,
            forbidden_detail="transfer_market_club_access_required",
        )
        player = self._require_player(payload.player_id)
        seller = self._require_club(resolved_selling_club_id)
        existing = self.session.scalar(
            select(TransferListing).where(
                TransferListing.player_id == payload.player_id,
                TransferListing.status == "open",
            )
        )
        if existing is not None:
            raise TransferMarketValidationError("Player already has an open transfer listing.")
        current_club_id = self._current_player_club_id(player.id, on_date=effective_at.date())
        if current_club_id is not None and current_club_id != seller.id:
            raise TransferMarketValidationError("Selling club must match the player's current club.")
        listing = TransferListing(
            window_id=payload.window_id,
            player_id=player.id,
            selling_club_id=seller.id,
            base_price=payload.base_price,
            current_highest_bid=payload.base_price,
            highest_bidder_id=None,
            status="open",
            expires_at=expires_at,
            reserve_price=payload.reserve_price,
            metadata_json={
                "notes": payload.notes or "",
                "drama_events": [],
            },
        )
        self.session.add(listing)
        self.session.commit()
        self.session.refresh(listing)
        snapshot = self.to_listing_view(listing, reference_at=effective_at)
        self._sync_listing_snapshot(snapshot)
        self._push_listing_event(
            listing.id,
            "listing_opened",
            {"listing_id": listing.id, "player_id": listing.player_id, "expires_at": snapshot.expires_at.isoformat()},
        )
        return snapshot

    def place_bid(
        self,
        listing_id: str,
        *,
        actor: User,
        bidder_club_id: str | None = None,
        amount: Decimal,
        activity_context: str | None = None,
        reference_at: datetime | None = None,
    ) -> TransferListingView:
        effective_at = self._coerce_utc(reference_at or utcnow())
        resolved_bidder_club_id = self._resolve_actor_club_id(
            actor,
            bidder_club_id,
            allowed_roles=TRANSFER_MARKET_EXECUTION_ROLES,
            forbidden_detail="transfer_market_club_access_required",
        )
        listing = self._require_listing(listing_id)
        if listing.status != "open":
            raise TransferMarketValidationError("Bids can only be placed on open transfer listings.")
        if effective_at >= self._coerce_utc(listing.expires_at):
            self._finalize_listing(listing_id, reference_at=effective_at)
            raise TransferMarketValidationError("This transfer auction has already expired.")
        if resolved_bidder_club_id == listing.selling_club_id:
            raise TransferMarketValidationError("Selling club cannot bid on its own listing.")
        self._require_club(resolved_bidder_club_id)
        current_highest = listing.current_highest_bid or listing.base_price
        if amount <= current_highest:
            raise TransferMarketValidationError("Bid must exceed the current highest bid.")

        previous_bidder_id = listing.highest_bidder_id
        previous_amount = listing.current_highest_bid
        bid = TransferListingBid(
            listing_id=listing.id,
            bidder_club_id=resolved_bidder_club_id,
            amount=amount,
            timestamp=effective_at,
            metadata_json={"activity_context": activity_context or ""},
        )
        self.session.add(bid)
        listing.current_highest_bid = amount
        listing.highest_bidder_id = resolved_bidder_club_id
        listing.bid_count += 1
        listing.last_bid_at = effective_at
        time_remaining = max(0, int((self._coerce_utc(listing.expires_at) - effective_at).total_seconds()))
        extended = False
        if time_remaining <= ANTI_SNIPING_WINDOW_SECONDS:
            listing.expires_at = self._coerce_utc(listing.expires_at) + timedelta(seconds=ANTI_SNIPING_EXTENSION_SECONDS)
            listing.anti_sniping_extension_count += 1
            extended = True
        if previous_bidder_id and previous_bidder_id != resolved_bidder_club_id and time_remaining <= LATE_HIJACK_WINDOW_SECONDS:
            self._append_drama_event(
                listing,
                event_type="late_hijack",
                headline="Late hijack",
                effective_at=effective_at,
                metadata={
                    "from_club_id": previous_bidder_id,
                    "to_club_id": resolved_bidder_club_id,
                    "amount": str(amount),
                },
            )
        self.session.commit()
        self.session.refresh(listing)
        self.session.refresh(bid)

        snapshot = self.to_listing_view(listing, reference_at=effective_at)
        self._sync_listing_snapshot(snapshot)
        bidder = self._require_club(resolved_bidder_club_id)
        player = self._require_player(listing.player_id)
        self._push_listing_event(
            listing.id,
            "new_bid",
            {
                "listing_id": listing.id,
                "bid_id": bid.id,
                "bidder_club_id": resolved_bidder_club_id,
                "bidder_club_name": bidder.club_name,
                "amount": str(amount),
                "time_remaining": snapshot.time_remaining,
            },
        )
        self._push_listing_event(
            listing.id,
            "bidder_activity",
            {
                "listing_id": listing.id,
                "activity": activity_context or "bid_placed",
                "bidder_club_id": resolved_bidder_club_id,
                "bidder_club_name": bidder.club_name,
            },
        )
        if extended:
            self._push_listing_event(
                listing.id,
                "auction_extended",
                {
                    "listing_id": listing.id,
                    "expires_at": snapshot.expires_at.isoformat(),
                    "time_remaining": snapshot.time_remaining,
                },
            )

        self._notify_club_owner(
            club_id=listing.selling_club_id,
            event_name="transfer_market.new_bid_placed",
            template_key="NEW_BID_PLACED",
            message=f"{bidder.club_name} bid {amount} for {player.full_name}.",
            resource_id=listing.id,
            payload={"bid_id": bid.id, "amount": str(amount), "bidder_club_id": resolved_bidder_club_id},
        )
        if previous_bidder_id and previous_bidder_id != resolved_bidder_club_id:
            self._notify_club_owner(
                club_id=previous_bidder_id,
                event_name="transfer_market.outbid_alert",
                template_key="OUTBID_ALERT",
                message=f"You were outbid for {player.full_name}.",
                resource_id=listing.id,
                payload={
                    "previous_amount": str(previous_amount),
                    "new_amount": str(amount),
                    "new_bidder_club_id": resolved_bidder_club_id,
                },
            )
        if previous_bidder_id and previous_bidder_id != resolved_bidder_club_id and time_remaining <= LATE_HIJACK_WINDOW_SECONDS:
            self._notify_club_owner(
                club_id=listing.selling_club_id,
                event_name="transfer_market.transfer_hijack",
                template_key="TRANSFER_HIJACK",
                message=f"{bidder.club_name} launched a late hijack for {player.full_name}.",
                resource_id=listing.id,
                payload={"bid_id": bid.id, "amount": str(amount), "bidder_club_id": resolved_bidder_club_id},
            )
        return snapshot

    def finalize_listing(
        self,
        listing_id: str,
        *,
        actor: User,
        reference_at: datetime | None = None,
    ) -> TransferListingView:
        listing = self._require_listing(listing_id)
        self._require_actor_club_access(
            actor,
            listing.selling_club_id,
            allowed_roles=TRANSFER_MARKET_EXECUTION_ROLES,
            forbidden_detail="transfer_market_listing_close_access_required",
        )
        return self._finalize_listing(listing_id, reference_at=reference_at)

    def _finalize_listing(self, listing_id: str, *, reference_at: datetime | None = None) -> TransferListingView:
        effective_at = self._coerce_utc(reference_at or utcnow())
        listing = self._require_listing(listing_id)
        if listing.status in {"closed", "sold"}:
            return self.to_listing_view(listing, reference_at=effective_at)

        listing.status = "closed"
        listing.closed_at = effective_at
        winning_bid = self._winning_bid_for_listing(listing.id)
        if winning_bid is not None:
            self._ensure_negotiation(listing, winning_bid, effective_at)
            self._append_drama_event(
                listing,
                event_type="auction_won",
                headline="Auction winner decided",
                effective_at=effective_at,
                metadata={"winning_bid_id": winning_bid.id, "bidder_club_id": winning_bid.bidder_club_id, "amount": str(winning_bid.amount)},
            )
        else:
            self._append_drama_event(
                listing,
                event_type="auction_closed",
                headline="Auction closed without bids",
                effective_at=effective_at,
                metadata={},
            )
        self.session.commit()
        self.session.refresh(listing)
        snapshot = self.to_listing_view(listing, reference_at=effective_at)
        self._sync_listing_snapshot(snapshot)
        self._push_listing_event(
            listing.id,
            "auction_closed",
            {
                "listing_id": listing.id,
                "status": listing.status,
                "highest_bidder_id": listing.highest_bidder_id,
                "current_highest_bid": str(listing.current_highest_bid),
            },
        )
        return snapshot

    def get_negotiation(self, listing_id: str, *, actor: User) -> TransferNegotiationView:
        negotiation = self._require_negotiation_by_listing(listing_id)
        self._require_actor_any_club_access(
            actor,
            [negotiation.selling_club_id, negotiation.bidder_club_id],
            allowed_roles=TRANSFER_MARKET_EXECUTION_ROLES,
            forbidden_detail="transfer_market_negotiation_access_required",
        )
        return self.to_negotiation_view(negotiation)

    def submit_contract_offer(
        self,
        listing_id: str,
        payload: ContractOfferRequest,
        *,
        actor: User,
        bidder_club_id: str | None = None,
        reference_at: datetime | None = None,
    ) -> TransferNegotiationView:
        effective_at = self._coerce_utc(reference_at or utcnow())
        listing = self._require_listing(listing_id)
        if listing.status == "open":
            if effective_at >= self._coerce_utc(listing.expires_at):
                self._finalize_listing(listing_id, reference_at=effective_at)
                listing = self._require_listing(listing_id)
            else:
                raise TransferMarketValidationError("Auction must close before contract talks start.")
        negotiation = self._require_negotiation_by_listing(listing.id)
        self._require_actor_club_access(
            actor,
            negotiation.bidder_club_id,
            allowed_roles=TRANSFER_MARKET_EXECUTION_ROLES,
            forbidden_detail="transfer_market_contract_offer_access_required",
        )
        resolved_bidder_club_id = (bidder_club_id or payload.bidder_club_id or negotiation.bidder_club_id or "").strip()
        if resolved_bidder_club_id != negotiation.bidder_club_id:
            raise TransferMarketValidationError("Only the auction winner can submit a contract offer.")
        payload = payload.model_copy(update={"bidder_club_id": resolved_bidder_club_id})

        player = self._require_player(negotiation.player_id)
        negotiation.wage_offer_amount = payload.wage_offer_amount
        negotiation.contract_years = payload.contract_years
        negotiation.expected_role = payload.expected_role
        negotiation.clauses_json = {
            **dict(negotiation.clauses_json or {}),
            **dict(payload.clauses_json or {}),
        }
        if payload.release_clause_amount is not None:
            negotiation.clauses_json = {
                **dict(negotiation.clauses_json or {}),
                "release_clause_amount": str(payload.release_clause_amount),
            }

        coach_opinion = self._evaluate_coach_opinion(
            player=player,
            destination_club_id=resolved_bidder_club_id,
        )
        player_decision = self._evaluate_player_decision(
            player=player,
            listing=listing,
            negotiation=negotiation,
            payload=payload,
            coach_opinion=coach_opinion,
            reference_at=effective_at,
        )
        agent_negotiation = self._evaluate_agent_negotiation(
            player=player,
            payload=payload,
            player_decision=player_decision,
        )
        concerns = list(dict.fromkeys([
            *player_decision.concerns,
            *(agent_negotiation.demands or []),
            coach_opinion.reason if coach_opinion.stance == "reject" else "",
        ]))
        concerns = [item for item in concerns if item]
        negotiation.player_decision_json = player_decision.model_dump(mode="json")
        negotiation.coach_opinion_json = coach_opinion.model_dump(mode="json")
        negotiation.agent_response = agent_negotiation.action
        negotiation.coach_stance = coach_opinion.stance
        negotiation.coach_reason = coach_opinion.reason
        negotiation.concerns_json = concerns
        negotiation.metadata_json = {
            **dict(negotiation.metadata_json or {}),
            "agent_negotiation": agent_negotiation.model_dump(mode="json"),
            "notes": payload.notes or "",
            "bonus_terms": payload.bonus_terms or "",
        }

        coach_profile = self._ensure_coach_profile(resolved_bidder_club_id)
        if coach_opinion.stance == "reject" and coach_profile.authority_level >= 70:
            negotiation.status = "coach_blocked"
            negotiation.resolved_at = effective_at
            negotiation.decision_due_at = None
            self._append_drama_event(
                listing,
                event_type="coach_disagreement",
                headline="Coach disagreement",
                effective_at=effective_at,
                metadata={"reason": coach_opinion.reason, "bidder_club_id": resolved_bidder_club_id},
            )
            self._notify_club_owner(
                club_id=resolved_bidder_club_id,
                event_name="transfer_market.coach_disagreement",
                template_key="COACH_DISAGREEMENT",
                message=f"Coach blocked the move for {player.full_name}.",
                resource_id=listing.id,
                payload={"reason": coach_opinion.reason},
            )
            self._apply_rejection_fallout(player.id, severity=4.0)
        elif player_decision.action == "reject" or agent_negotiation.action == "reject":
            negotiation.status = "rejected"
            negotiation.resolved_at = effective_at
            negotiation.decision_due_at = None
            self._append_drama_event(
                listing,
                event_type="deal_collapsed",
                headline="Deal collapsed",
                effective_at=effective_at,
                metadata={"reason": concerns[0] if concerns else "player_rejected"},
            )
            self._notify_club_owner(
                club_id=resolved_bidder_club_id,
                event_name="transfer_market.player_rejected_offer",
                template_key="PLAYER_REJECTED_OFFER",
                message=f"{player.full_name} rejected the contract offer.",
                resource_id=listing.id,
                payload={"reason": concerns[0] if concerns else "rejected"},
            )
            self._apply_rejection_fallout(player.id, severity=6.0)
        elif agent_negotiation.action == "counter_offer":
            negotiation.status = "counter_offer"
            negotiation.decision_due_at = effective_at + timedelta(hours=AGENT_COUNTER_DEADLINE_HOURS)
            negotiation.resolved_at = None
        elif player_decision.action == "delay" or agent_negotiation.action == "stall":
            negotiation.status = "player_delayed"
            negotiation.decision_due_at = effective_at + timedelta(hours=PLAYER_DECISION_DELAY_HOURS)
            negotiation.resolved_at = None
            self._apply_delay_fallout(player.id)
        else:
            try:
                accepted_bid, player_contract_id = self._complete_transfer(
                    listing=listing,
                    negotiation=negotiation,
                    payload=payload,
                    reference_at=effective_at,
                )
            except (PlayerLifecycleError, TransferMarketError) as exc:
                negotiation.status = "collapsed"
                negotiation.resolved_at = effective_at
                negotiation.decision_due_at = None
                updated_concerns = list(dict.fromkeys([*concerns, str(exc)]))
                negotiation.concerns_json = updated_concerns
                self._append_drama_event(
                    listing,
                    event_type="deal_collapsed",
                    headline="Deal collapsed",
                    effective_at=effective_at,
                    metadata={"reason": str(exc)},
                )
            else:
                negotiation.status = "completed"
                negotiation.resolved_at = effective_at
                negotiation.decision_due_at = None
                negotiation.lifecycle_transfer_bid_id = accepted_bid.id
                negotiation.player_contract_id = player_contract_id
                listing.status = "sold"
                self._append_drama_event(
                    listing,
                    event_type="transfer_completed",
                    headline="Transfer completed",
                    effective_at=effective_at,
                    metadata={
                        "lifecycle_transfer_bid_id": accepted_bid.id,
                        "player_contract_id": player_contract_id,
                    },
                )
                self._notify_club_owner(
                    club_id=resolved_bidder_club_id,
                    event_name="transfer_market.transfer_completed",
                    template_key="TRANSFER_COMPLETED",
                    message=f"{player.full_name} completed the transfer.",
                    resource_id=listing.id,
                    payload={
                        "lifecycle_transfer_bid_id": accepted_bid.id,
                        "player_contract_id": player_contract_id,
                    },
                )
                self._apply_completion_effects(
                    player_id=player.id,
                    selling_club_id=listing.selling_club_id,
                    destination_club_id=resolved_bidder_club_id,
                    coach_opinion=coach_opinion,
                )

        self.session.commit()
        self.session.refresh(negotiation)
        self.session.refresh(listing)
        snapshot = self.to_listing_view(listing, reference_at=effective_at)
        self._sync_listing_snapshot(snapshot)
        self._push_listing_event(
            listing.id,
            "negotiation_updated",
            {
                "listing_id": listing.id,
                "status": negotiation.status,
                "decision_due_at": negotiation.decision_due_at.isoformat() if negotiation.decision_due_at else None,
            },
        )
        return self.to_negotiation_view(negotiation)

    def run_background_jobs(self, *, actor: User, reference_at: datetime | None = None) -> TransferMarketJobRunView:
        self._require_admin_actor(actor)
        effective_at = self._coerce_utc(reference_at or utcnow())
        closed_auctions = 0
        completed_transfers = 0
        rejected_negotiations = 0
        collapsed_negotiations = 0

        open_listings = list(
            self.session.scalars(
                select(TransferListing).where(
                    TransferListing.status == "open",
                    TransferListing.expires_at <= effective_at,
                )
            ).all()
        )
        for listing in open_listings:
            self._finalize_listing(listing.id, reference_at=effective_at)
            closed_auctions += 1

        delayed_negotiations = list(
            self.session.scalars(
                select(TransferNegotiation).where(
                    TransferNegotiation.status == "player_delayed",
                    TransferNegotiation.decision_due_at.is_not(None),
                    TransferNegotiation.decision_due_at <= effective_at,
                )
            ).all()
        )
        for negotiation in delayed_negotiations:
            listing = self._require_listing(negotiation.listing_id)
            score = float((negotiation.player_decision_json or {}).get("decision_score") or 0.0)
            if score >= 68.0 and negotiation.coach_stance != "reject" and negotiation.agent_response != "reject":
                try:
                    accepted_bid, player_contract_id = self._complete_transfer(
                        listing=listing,
                        negotiation=negotiation,
                        payload=self._payload_from_negotiation(negotiation),
                        reference_at=effective_at,
                    )
                except (PlayerLifecycleError, TransferMarketError):
                    negotiation.status = "collapsed"
                    negotiation.resolved_at = effective_at
                    collapsed_negotiations += 1
                else:
                    negotiation.status = "completed"
                    negotiation.resolved_at = effective_at
                    negotiation.lifecycle_transfer_bid_id = accepted_bid.id
                    negotiation.player_contract_id = player_contract_id
                    listing.status = "sold"
                    completed_transfers += 1
            else:
                negotiation.status = "rejected"
                negotiation.resolved_at = effective_at
                self._apply_rejection_fallout(negotiation.player_id, severity=5.0)
                rejected_negotiations += 1
            negotiation.decision_due_at = None
            self.session.commit()
            self.session.refresh(negotiation)
            self.session.refresh(listing)
            self._sync_listing_snapshot(self.to_listing_view(listing, reference_at=effective_at))
            self._push_listing_event(
                listing.id,
                "negotiation_timer_processed",
                {"listing_id": listing.id, "status": negotiation.status},
            )

        counter_negotiations = list(
            self.session.scalars(
                select(TransferNegotiation).where(
                    TransferNegotiation.status == "counter_offer",
                    TransferNegotiation.decision_due_at.is_not(None),
                    TransferNegotiation.decision_due_at <= effective_at,
                )
            ).all()
        )
        for negotiation in counter_negotiations:
            listing = self._require_listing(negotiation.listing_id)
            negotiation.status = "collapsed"
            negotiation.resolved_at = effective_at
            negotiation.decision_due_at = None
            self._append_drama_event(
                listing,
                event_type="deal_collapsed",
                headline="Deal collapsed",
                effective_at=effective_at,
                metadata={"reason": "agent_counter_expired"},
            )
            collapsed_negotiations += 1
            self.session.commit()
            self.session.refresh(negotiation)
            self.session.refresh(listing)
            self._sync_listing_snapshot(self.to_listing_view(listing, reference_at=effective_at))
            self._push_listing_event(
                listing.id,
                "agent_timer_processed",
                {"listing_id": listing.id, "status": negotiation.status},
            )

        return TransferMarketJobRunView(
            closed_auctions=closed_auctions,
            completed_transfers=completed_transfers,
            rejected_negotiations=rejected_negotiations,
            collapsed_negotiations=collapsed_negotiations,
        )

    def upsert_player_decision_profile(
        self,
        player_id: str,
        payload: PlayerDecisionProfileUpsertRequest,
    ) -> PlayerDecisionProfileView:
        self._require_player(player_id)
        profile = self._ensure_player_decision_profile(player_id)
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
        self.session.commit()
        self.session.refresh(profile)
        return self._to_player_decision_profile_view(profile)

    def upsert_coach_profile(self, club_id: str, payload: CoachProfileUpsertRequest, *, actor: User) -> CoachProfileView:
        self._require_actor_club_access(
            actor,
            club_id,
            allowed_roles=TRANSFER_MARKET_EXECUTION_ROLES,
            forbidden_detail="transfer_market_coach_profile_access_required",
        )
        self._require_club(club_id)
        profile = self._ensure_coach_profile(club_id)
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
        self.session.commit()
        self.session.refresh(profile)
        return self._to_coach_profile_view(profile)

    def create_coach_demand(self, club_id: str, payload, *, actor: User) -> CoachDemandView:
        self._require_actor_club_access(
            actor,
            club_id,
            allowed_roles=TRANSFER_MARKET_EXECUTION_ROLES,
            forbidden_detail="transfer_market_coach_demand_access_required",
        )
        profile = self._ensure_coach_profile(club_id)
        demand = CoachDemand(
            coach_profile_id=profile.id,
            club_id=club_id,
            need=payload.need,
            urgency=payload.urgency,
            active=payload.active,
            metadata_json=payload.metadata_json,
        )
        self.session.add(demand)
        self.session.commit()
        self.session.refresh(demand)
        return self._to_coach_demand_view(demand)

    def upsert_team_dynamics(
        self,
        club_id: str,
        payload: TeamDynamicsUpsertRequest,
        *,
        actor: User,
    ) -> ClubTeamDynamicsView:
        self._require_actor_club_access(
            actor,
            club_id,
            allowed_roles=TRANSFER_MARKET_EXECUTION_ROLES,
            forbidden_detail="transfer_market_team_dynamics_access_required",
        )
        self._require_club(club_id)
        dynamics = self._ensure_team_dynamics(club_id)
        for key, value in payload.model_dump().items():
            setattr(dynamics, key, value)
        self.session.commit()
        self.session.refresh(dynamics)
        return self._to_team_dynamics_view(dynamics)

    def add_watchlist_entry(
        self,
        payload: WatchlistEntryCreateRequest,
        *,
        actor: User,
        club_id: str | None = None,
    ) -> MarketWatchlistEntryView:
        resolved_club_id = self._resolve_actor_club_id(
            actor,
            club_id or payload.club_id,
            allowed_roles=TRANSFER_MARKET_WATCHLIST_ROLES,
            forbidden_detail="transfer_market_club_access_required",
        )
        self._require_club(resolved_club_id)
        self._require_player(payload.player_id)
        entry = self.session.scalar(
            select(MarketWatchlistEntry).where(
                MarketWatchlistEntry.club_id == resolved_club_id,
                MarketWatchlistEntry.player_id == payload.player_id,
            )
        )
        if entry is None:
            entry = MarketWatchlistEntry(club_id=resolved_club_id, player_id=payload.player_id)
            self.session.add(entry)
            self.session.flush()
        entry.source = payload.source
        entry.discovery_score = payload.discovery_score
        entry.metadata_json = payload.metadata_json
        open_listing = self.session.scalar(
            select(TransferListing).where(
                TransferListing.player_id == payload.player_id,
                TransferListing.status == "open",
            )
        )
        if open_listing is not None:
            open_listing.watchlist_count = self._watchlist_count(payload.player_id)
        self.session.commit()
        self.session.refresh(entry)
        if open_listing is not None:
            self.session.refresh(open_listing)
            self._sync_listing_snapshot(self.to_listing_view(open_listing, reference_at=utcnow()))
        return self._to_watchlist_entry_view(entry)

    def to_listing_view(self, listing: TransferListing, *, reference_at: datetime | None = None) -> TransferListingView:
        effective_at = self._coerce_utc(reference_at or utcnow())
        player = self._require_player(listing.player_id)
        current_club = self.session.get(ClubProfile, player.current_club_profile_id) if player.current_club_profile_id else None
        clubs = self._clubs_by_ids(
            [listing.selling_club_id, listing.highest_bidder_id, player.current_club_profile_id]
            + [bid.bidder_club_id for bid in self._listing_bids(listing.id)]
        )
        bids = [
            TransferBidderView(
                bid_id=item.id,
                club_id=item.bidder_club_id,
                club_name=clubs.get(item.bidder_club_id).club_name if clubs.get(item.bidder_club_id) is not None else None,
                amount=item.amount,
                timestamp=self._coerce_utc(item.timestamp),
                is_highest=item.id == self._winning_bid_id(listing.id),
            )
            for item in self._listing_bids(listing.id)
        ]
        current_bid = next((item for item in bids if item.is_highest), None)
        negotiation = self.session.scalar(select(TransferNegotiation).where(TransferNegotiation.listing_id == listing.id))
        return TransferListingView(
            id=listing.id,
            window_id=listing.window_id,
            player_id=listing.player_id,
            selling_club_id=listing.selling_club_id,
            base_price=listing.base_price,
            current_highest_bid=listing.current_highest_bid,
            highest_bidder_id=listing.highest_bidder_id,
            status=listing.status,
            expires_at=self._coerce_utc(listing.expires_at),
            time_remaining=max(0, int((self._coerce_utc(listing.expires_at) - effective_at).total_seconds())),
            player=TransferMarketPlayerView(
                id=player.id,
                full_name=player.full_name,
                normalized_position=player.normalized_position,
                current_club_id=player.current_club_profile_id,
                current_club_name=current_club.club_name if current_club is not None else None,
                current_competition_id=player.current_competition_id,
            ),
            current_bid=current_bid,
            bidders=bids,
            watchlist_count=self._watchlist_count(listing.player_id),
            bid_count=len(bids),
            suggested_price=self._suggested_price(listing.player_id, listing=listing),
            market_signal=self._market_signal(listing.player_id, listing=listing, reference_at=effective_at),
            channel=f"transfer:{listing.id}",
            negotiation_id=negotiation.id if negotiation is not None else None,
        )

    def to_negotiation_view(self, negotiation: TransferNegotiation) -> TransferNegotiationView:
        player_decision = None
        if negotiation.player_decision_json:
            player_decision = PlayerDecisionView.model_validate(negotiation.player_decision_json)
        coach_opinion = None
        if negotiation.coach_opinion_json:
            coach_opinion = CoachOpinionView.model_validate(negotiation.coach_opinion_json)
        agent_negotiation = None
        raw_agent = dict(negotiation.metadata_json or {}).get("agent_negotiation")
        if isinstance(raw_agent, dict):
            agent_negotiation = AgentNegotiationView.model_validate(raw_agent)
        return TransferNegotiationView(
            id=negotiation.id,
            listing_id=negotiation.listing_id,
            winning_bid_id=negotiation.winning_bid_id,
            player_id=negotiation.player_id,
            selling_club_id=negotiation.selling_club_id,
            bidder_club_id=negotiation.bidder_club_id,
            status=negotiation.status,
            wage_offer_amount=negotiation.wage_offer_amount,
            contract_years=negotiation.contract_years,
            expected_role=negotiation.expected_role,
            player_decision=player_decision,
            coach_opinion=coach_opinion,
            agent_negotiation=agent_negotiation,
            concerns=list(negotiation.concerns_json or []),
            decision_due_at=self._coerce_utc(negotiation.decision_due_at) if negotiation.decision_due_at else None,
            resolved_at=self._coerce_utc(negotiation.resolved_at) if negotiation.resolved_at else None,
            lifecycle_transfer_bid_id=negotiation.lifecycle_transfer_bid_id,
            player_contract_id=negotiation.player_contract_id,
        )

    def _evaluate_player_decision(
        self,
        *,
        player: Player,
        listing: TransferListing,
        negotiation: TransferNegotiation,
        payload: ContractOfferRequest,
        coach_opinion: CoachOpinionView,
        reference_at: datetime,
    ) -> PlayerDecisionView:
        del negotiation
        decision_profile = self._ensure_player_decision_profile(player.id)
        player_state = self.session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == player.id))
        personality = self.session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == player.id))
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
        destination_club = self._require_club(payload.bidder_club_id)
        current_relationship = self._player_coach_relationship(player.id, listing.selling_club_id)
        destination_relationship = self._player_coach_relationship(player.id, payload.bidder_club_id)

        club_reputation = clamp(self._club_reputation_score(destination_club))
        playtime_probability = clamp(self._playtime_probability(payload.bidder_club_id, player.normalized_position))
        league_level = clamp(self._club_league_score(destination_club))
        salary_offer = clamp(
            float(
                quantize_amount(payload.wage_offer_amount)
                / max(
                    quantize_amount(decision_profile.wage_expectation_amount or 1)
                    if decision_profile.wage_expectation_amount > 0
                    else quantize_amount(
                        (player_state.salary_expectation_amount if player_state is not None else Decimal("1.0"))
                        or Decimal("1.0")
                    ),
                    Decimal("1.0"),
                )
            )
            * 72.0
        )
        personal_preferences = self._personal_preference_score(
            decision_profile=decision_profile,
            destination_club=destination_club,
            coach_profile=self._ensure_coach_profile(payload.bidder_club_id),
        )
        coach_relationship_score = clamp(
            (destination_relationship.relationship_score * 0.55)
            + ((100.0 - current_relationship.relationship_score) * 0.45)
        )
        ambition_fit = clamp(
            (club_reputation * 0.52)
            + (league_level * 0.20)
            + (float(decision_profile.ambition_level) * 0.28)
        )
        agency_transfer_score, agency_contract_score = self._agency_scores(
            player=player,
            regen=regen,
            payload=payload,
            reference_at=reference_at,
        )
        emotional_push = clamp(
            ((100.0 - self._resolved_happiness(decision_profile, player_state)) * 0.34)
            + (decision_profile.frustration * 0.28)
            + (self._resolved_ambition(decision_profile, personality) * 0.16)
            - (self._resolved_loyalty(decision_profile, personality) * 0.22)
        )
        long_tenure_bonus = self._long_tenure_bonus(player.id, on_date=reference_at.date())
        instability_penalty = self._instability_penalty(player.id)
        dressing_room_score = 100.0 - self._destination_chemistry_risk(payload.bidder_club_id)

        component_scores = {
            "salary_offer": round(salary_offer, 2),
            "club_reputation": round(club_reputation, 2),
            "playtime_probability": round(playtime_probability, 2),
            "league_level": round(league_level, 2),
            "personal_preferences": round(personal_preferences, 2),
            "coach_relationship": round(coach_relationship_score, 2),
            "ambition_fit": round(ambition_fit, 2),
            "coach_opinion": round((coach_opinion.tactical_fit + coach_opinion.personality_fit) / 2.0, 2),
            "agency_transfer": round(agency_transfer_score, 2),
            "agency_contract": round(agency_contract_score, 2),
            "dressing_room": round(dressing_room_score, 2),
            "emotional_push": round(emotional_push, 2),
        }
        score = clamp(
            (salary_offer * 0.18)
            + (club_reputation * 0.14)
            + (playtime_probability * 0.16)
            + (league_level * 0.09)
            + (personal_preferences * 0.12)
            + (coach_relationship_score * 0.11)
            + (ambition_fit * 0.10)
            + (((coach_opinion.tactical_fit + coach_opinion.personality_fit) / 2.0) * 0.05)
            + (agency_transfer_score * 0.03)
            + (agency_contract_score * 0.03)
            + (dressing_room_score * 0.05)
            + (emotional_push * 0.06)
            - (long_tenure_bonus * 0.10)
            - (instability_penalty * 0.08)
        )

        concerns: list[str] = []
        if playtime_probability < 58.0:
            concerns.append("Minutes are not guaranteed.")
        if personal_preferences < 55.0:
            concerns.append("The move clashes with personal preferences.")
        if coach_relationship_score < 52.0:
            concerns.append("Coach chemistry still looks uncertain.")
        if coach_opinion.stance == "reject":
            concerns.append(coach_opinion.reason)
        if dressing_room_score < 55.0:
            concerns.append("Dressing room chemistry looks fragile.")
        if payload.release_clause_amount is None and self._resolved_ambition(decision_profile, personality) >= 68.0:
            concerns.append("Agent wants a release clause.")

        if coach_opinion.stance == "reject" and score < 80.0:
            action = "reject"
        elif score >= 72.0:
            action = "accept"
        elif score >= 55.0:
            action = "delay"
        else:
            action = "reject"

        interest_level = "high" if score >= 72.0 else "medium" if score >= 55.0 else "low"
        preferences = {
            "preferred_leagues": list(decision_profile.preferred_leagues_json or []),
            "preferred_play_style": decision_profile.preferred_play_style,
            "wage_expectation_amount": str(decision_profile.wage_expectation_amount),
            "ambition_level": decision_profile.ambition_level,
        }
        return PlayerDecisionView(
            interest_level=interest_level,
            concerns=concerns,
            preferences=preferences,
            action=action,
            decision_score=round(score, 2),
            component_scores=component_scores,
        )

    def _evaluate_coach_opinion(
        self,
        *,
        player: Player,
        destination_club_id: str,
    ) -> CoachOpinionView:
        coach = self._ensure_coach_profile(destination_club_id)
        demands = list(
            self.session.scalars(
                select(CoachDemand).where(CoachDemand.club_id == destination_club_id, CoachDemand.active.is_(True))
            ).all()
        )
        tactical_fit = clamp(self._coach_tactical_fit(player.normalized_position, coach, demands))
        squad_depth_fit = clamp(100.0 - (self._club_position_depth(destination_club_id, player.normalized_position) * 18.0))
        personality = self.session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == player.id))
        discipline_target = float(dict(coach.personality_json or {}).get("discipline", 50.0))
        personality_fit = clamp(
            ((personality.professionalism if personality is not None else 50) * 0.42)
            + ((personality.adaptability if personality is not None else 50) * 0.24)
            + ((100 - abs((personality.temperament if personality is not None else 50) - discipline_target)) * 0.34)
        )
        combined = clamp((tactical_fit * 0.42) + (squad_depth_fit * 0.28) + (personality_fit * 0.30))
        normalized_position = (player.normalized_position or "").strip().lower().replace(" ", "_")
        urgent_profile_mismatch = any(
            demand.urgency == "high"
            and normalized_position
            and normalized_position not in demand.need.strip().lower().replace(" ", "_")
            for demand in demands
        )
        if urgent_profile_mismatch and coach.authority_level >= 75.0:
            stance = "reject"
            reason = "Coach wants a different profile for this window."
        elif combined >= 72.0:
            stance = "approve"
            reason = "Coach sees a clear tactical and personality fit."
        elif combined <= 45.0:
            stance = "reject"
            reason = "Coach does not like the tactical or personality fit."
        else:
            stance = "neutral"
            reason = "Coach is unconvinced but willing to listen."
        return CoachOpinionView(
            stance=stance,
            reason=reason,
            tactical_fit=round(tactical_fit, 2),
            squad_depth_fit=round(squad_depth_fit, 2),
            personality_fit=round(personality_fit, 2),
        )

    def _evaluate_agent_negotiation(
        self,
        *,
        player: Player,
        payload: ContractOfferRequest,
        player_decision: PlayerDecisionView,
    ) -> AgentNegotiationView:
        decision_profile = self._ensure_player_decision_profile(player.id)
        personality = self.session.scalar(select(PlayerPersonality).where(PlayerPersonality.player_id == player.id))
        demands: list[str] = []
        clauses = dict(payload.clauses_json or {})
        notes: list[str] = []
        expected_wage = decision_profile.wage_expectation_amount
        if expected_wage <= 0:
            agency_state = self.session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == player.id))
            expected_wage = agency_state.salary_expectation_amount if agency_state is not None else Decimal("0")
        greed = personality.greed if personality is not None else 50
        ambition = self._resolved_ambition(decision_profile, personality)
        patience = personality.patience if personality is not None else 50

        if player_decision.action == "reject":
            return AgentNegotiationView(action="reject", demands=player_decision.concerns, clauses=clauses, notes="Agent advised a rejection.")
        if payload.release_clause_amount is None and ambition >= 68.0:
            demands.append("release clause")
            clauses["release_clause_requested"] = True
            notes.append("Agent wants a release clause.")
        if expected_wage > 0 and payload.wage_offer_amount < (expected_wage * Decimal("1.05")) and greed >= 58:
            target_wage = quantize_amount(max(expected_wage * Decimal("1.10"), payload.wage_offer_amount))
            demands.append("higher wages")
            clauses["requested_wage_amount"] = str(target_wage)
            notes.append("Agent is pushing for a higher wage.")
        if demands:
            return AgentNegotiationView(
                action="counter_offer",
                demands=demands,
                clauses=clauses,
                notes=" ".join(notes) or "Agent made a counter-offer.",
            )
        if player_decision.action == "delay" or patience <= 42:
            return AgentNegotiationView(
                action="stall",
                demands=[],
                clauses=clauses,
                notes="Agent is stalling to test the market.",
            )
        return AgentNegotiationView(action="accept", demands=[], clauses=clauses, notes="Agent is satisfied with the terms.")

    def _complete_transfer(
        self,
        *,
        listing: TransferListing,
        negotiation: TransferNegotiation,
        payload: ContractOfferRequest,
        reference_at: datetime,
    ) -> tuple[Any, str | None]:
        lifecycle_service = PlayerLifecycleService(self.session)
        window_id, outside_window = self._resolve_window_id(listing=listing, reference_at=reference_at.date())
        bid = lifecycle_service.create_bid(
            window_id,
            TransferBidCreateRequest(
                player_id=listing.player_id,
                selling_club_id=listing.selling_club_id,
                buying_club_id=payload.bidder_club_id,
                bid_amount=listing.current_highest_bid,
                wage_offer_amount=payload.wage_offer_amount,
                contract_years=payload.contract_years,
                sell_on_clause_pct=self._sell_on_clause_pct(payload.clauses_json),
                notes=payload.notes,
                allow_outside_window=outside_window,
                exemption_reason="transfer_market_auction" if outside_window else None,
            ),
            submitted_on=reference_at.date(),
        )
        contract_ends_on = (payload.contract_starts_on or reference_at.date()) + timedelta(days=(365 * payload.contract_years) - 1)
        try:
            accepted = lifecycle_service.accept_bid(
                window_id,
                bid.id,
                TransferBidAcceptRequest(
                    contract_ends_on=contract_ends_on,
                    contract_starts_on=payload.contract_starts_on or reference_at.date(),
                    wage_amount=payload.wage_offer_amount,
                    bonus_terms=payload.bonus_terms,
                    release_clause_amount=payload.release_clause_amount,
                    signed_on=reference_at.date(),
                ),
                reference_on=reference_at.date(),
            )
        except (PlayerLifecycleValidationError, PlayerLifecycleNotFoundError) as exc:
            lifecycle_service.reject_bid(
                window_id,
                bid.id,
                TransferBidRejectRequest(reason=f"transfer_market_failed: {exc}"),
            )
            raise TransferMarketValidationError(str(exc)) from exc
        contract_id = None
        if isinstance(getattr(accepted, "structured_terms_json", None), dict):
            contract_id = accepted.structured_terms_json.get("contract_id")
        return accepted, str(contract_id) if contract_id is not None else None

    def _ensure_negotiation(
        self,
        listing: TransferListing,
        winning_bid: TransferListingBid,
        effective_at: datetime,
    ) -> TransferNegotiation:
        negotiation = self.session.scalar(select(TransferNegotiation).where(TransferNegotiation.listing_id == listing.id))
        if negotiation is None:
            negotiation = TransferNegotiation(
                listing_id=listing.id,
                winning_bid_id=winning_bid.id,
                player_id=listing.player_id,
                selling_club_id=listing.selling_club_id,
                bidder_club_id=winning_bid.bidder_club_id,
                status="awaiting_contract_offer",
                decision_due_at=effective_at + timedelta(hours=PLAYER_DECISION_DELAY_HOURS),
                metadata_json={},
            )
            self.session.add(negotiation)
            self.session.flush()
        else:
            negotiation.winning_bid_id = winning_bid.id
            negotiation.bidder_club_id = winning_bid.bidder_club_id
        return negotiation

    def _resolve_window_id(self, *, listing: TransferListing, reference_at: date) -> tuple[str, bool]:
        lifecycle_service = PlayerLifecycleService(self.session)
        if listing.window_id:
            window = lifecycle_service.get_transfer_window(listing.window_id)
            is_active = window.opens_on <= reference_at <= window.closes_on
            return window.id, not is_active
        seller = self._require_club(listing.selling_club_id)
        active_windows = lifecycle_service.list_transfer_windows(territory_code=seller.country_code, active_on=reference_at)
        if not active_windows:
            active_windows = lifecycle_service.list_transfer_windows(active_on=reference_at)
        if active_windows:
            return active_windows[0].id, False
        fallback_windows = lifecycle_service.list_transfer_windows(territory_code=seller.country_code)
        if not fallback_windows:
            fallback_windows = lifecycle_service.list_transfer_windows()
        if not fallback_windows:
            raise TransferMarketValidationError("No transfer window is available to settle this auction.")
        return fallback_windows[0].id, True

    def _payload_from_negotiation(self, negotiation: TransferNegotiation) -> ContractOfferRequest:
        release_clause_amount = None
        raw_release = dict(negotiation.clauses_json or {}).get("release_clause_amount")
        if raw_release is not None:
            release_clause_amount = Decimal(str(raw_release))
        return ContractOfferRequest(
            bidder_club_id=negotiation.bidder_club_id,
            wage_offer_amount=negotiation.wage_offer_amount or Decimal("0"),
            contract_years=negotiation.contract_years,
            expected_role=negotiation.expected_role,
            release_clause_amount=release_clause_amount,
            clauses_json=dict(negotiation.clauses_json or {}),
            notes=str(dict(negotiation.metadata_json or {}).get("notes") or ""),
            bonus_terms=str(dict(negotiation.metadata_json or {}).get("bonus_terms") or "") or None,
        )

    def _agency_scores(
        self,
        *,
        player: Player,
        regen: RegenProfile | None,
        payload: ContractOfferRequest,
        reference_at: datetime,
    ) -> tuple[float, float]:
        if regen is None:
            current_contract = self.context_service.get_current_contract(player.id, reference_on=reference_at.date())
            current_wage = current_contract.wage_amount if current_contract is not None else Decimal("0")
            transfer_score = clamp(float(payload.wage_offer_amount / max(current_wage or Decimal("1"), Decimal("1"))) * 65.0)
            contract_score = clamp(float(payload.wage_offer_amount / max(current_wage or Decimal("1"), Decimal("1"))) * 68.0)
            return transfer_score, contract_score
        agency = PlayerAgencyService(self.session)
        transfer = agency.evaluate_transfer_opportunity(
            player.id,
            TransferDecisionRequest(
                destination_club_id=payload.bidder_club_id,
                offered_wage_amount=payload.wage_offer_amount,
                contract_years=payload.contract_years,
                expected_role=payload.expected_role,
                requested_on=reference_at.date(),
            ),
            reference_on=reference_at.date(),
        )
        contract = agency.evaluate_contract_offer(
            player.id,
            ContractDecisionRequest(
                offering_club_id=payload.bidder_club_id,
                offered_wage_amount=payload.wage_offer_amount,
                contract_years=payload.contract_years,
                role_promised=payload.expected_role,
                release_clause_amount=payload.release_clause_amount,
                is_renewal=False,
                requested_on=reference_at.date(),
            ),
            reference_on=reference_at.date(),
        )
        return transfer.decision_score, contract.decision_score

    def _coach_tactical_fit(self, position: str | None, coach: CoachProfile, demands: list[CoachDemand]) -> float:
        normalized_position = (position or "").strip().lower()
        philosophy = coach.tactical_philosophy.strip().lower()
        fit = 55.0
        if normalized_position in {"defender", "centre-back", "full-back"} and philosophy in {"pressing", "counter", "balanced"}:
            fit += 8.0
        if normalized_position in {"midfielder", "defensive_midfielder"} and philosophy in {"possession", "balanced"}:
            fit += 10.0
        if normalized_position in {"forward", "striker", "winger"} and philosophy in {"direct", "pressing", "counter"}:
            fit += 10.0
        matched_urgent_demand = False
        high_urgency_mismatch = False
        for demand in demands:
            need = demand.need.strip().lower().replace(" ", "_")
            if normalized_position and normalized_position.replace(" ", "_") in need:
                fit += 18.0 if demand.urgency == "high" else 10.0
                matched_urgent_demand = matched_urgent_demand or demand.urgency == "high"
            elif demand.urgency == "high":
                high_urgency_mismatch = True
        if matched_urgent_demand:
            fit += 8.0
        elif high_urgency_mismatch:
            fit -= 28.0
        return fit

    def _personal_preference_score(
        self,
        *,
        decision_profile: PlayerDecisionProfile,
        destination_club: ClubProfile,
        coach_profile: CoachProfile,
    ) -> float:
        score = 50.0
        preferred_leagues = {item.strip().lower() for item in list(decision_profile.preferred_leagues_json or []) if item}
        if destination_club.country_code and destination_club.country_code.strip().lower() in preferred_leagues:
            score += 22.0
        preferred_style = (decision_profile.preferred_play_style or "").strip().lower()
        if preferred_style and preferred_style in {
            coach_profile.tactical_philosophy.strip().lower(),
            coach_profile.transfer_preference.strip().lower(),
        }:
            score += 18.0
        if preferred_style and preferred_style not in {
            coach_profile.tactical_philosophy.strip().lower(),
            coach_profile.transfer_preference.strip().lower(),
        }:
            score -= 8.0
        return clamp(score)

    def _apply_completion_effects(
        self,
        *,
        player_id: str,
        selling_club_id: str,
        destination_club_id: str,
        coach_opinion: CoachOpinionView,
    ) -> None:
        selling_dynamics = self._ensure_team_dynamics(selling_club_id)
        destination_dynamics = self._ensure_team_dynamics(destination_club_id)
        if player_id in list(selling_dynamics.leaders_json or []):
            selling_dynamics.chemistry_risk = clamp(selling_dynamics.chemistry_risk + 8.0)
        destination_dynamics.chemistry_risk = clamp(
            destination_dynamics.chemistry_risk + max(0.0, 58.0 - ((coach_opinion.tactical_fit + coach_opinion.personality_fit) / 2.0)) * 0.08
        )
        relationship = self._player_coach_relationship(player_id, destination_club_id)
        relationship.relationship_score = clamp(relationship.relationship_score + ((coach_opinion.personality_fit - 50.0) * 0.20) + 6.0)
        relationship.integration_success_modifier = clamp(
            relationship.integration_success_modifier + (((coach_opinion.tactical_fit + coach_opinion.personality_fit) / 2.0) - 50.0),
            -25.0,
            25.0,
        )
        relationship.conflict_level = clamp(max(0.0, relationship.conflict_level - 8.0))
        player_state = self.session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == player_id))
        if player_state is not None:
            player_state.happiness = clamp(player_state.happiness + 8.0)
            player_state.transfer_appetite = clamp(max(0.0, player_state.transfer_appetite - 18.0))
        decision_profile = self._ensure_player_decision_profile(player_id)
        decision_profile.frustration = clamp(max(0.0, decision_profile.frustration - 15.0))

    def _apply_delay_fallout(self, player_id: str) -> None:
        decision_profile = self._ensure_player_decision_profile(player_id)
        decision_profile.frustration = clamp(decision_profile.frustration + 6.0)
        player_state = self.session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == player_id))
        if player_state is not None:
            player_state.happiness = clamp(player_state.happiness - 3.0)

    def _apply_rejection_fallout(self, player_id: str, *, severity: float) -> None:
        decision_profile = self._ensure_player_decision_profile(player_id)
        decision_profile.frustration = clamp(decision_profile.frustration + severity)
        player_state = self.session.scalar(select(PlayerAgencyState).where(PlayerAgencyState.player_id == player_id))
        if player_state is not None:
            player_state.happiness = clamp(player_state.happiness - severity)
            player_state.transfer_appetite = clamp(player_state.transfer_appetite + (severity * 1.2))

    def _destination_chemistry_risk(self, club_id: str) -> float:
        dynamics = self._ensure_team_dynamics(club_id)
        return float(dynamics.chemistry_risk)

    def _suggested_price(self, player_id: str, *, listing: TransferListing) -> Decimal:
        demand = Decimal(str(min(0.45, (listing.bid_count * 0.08) + (self._watchlist_count(player_id) * 0.02))))
        price = quantize_amount(listing.base_price * (Decimal("1.00") + demand))
        if listing.bid_count == 0 and self._watchlist_count(player_id) == 0:
            price = quantize_amount(listing.base_price * Decimal("0.95"))
        return max(price, listing.base_price)

    def _market_signal(self, player_id: str, *, listing: TransferListing, reference_at: datetime) -> str:
        demand_score = (listing.bid_count * 16) + (self._watchlist_count(player_id) * 6)
        time_pressure = max(0, 180 - int((self._coerce_utc(listing.expires_at) - reference_at).total_seconds()))
        if demand_score >= 48:
            return "surging"
        if demand_score >= 18:
            return "heated"
        if demand_score <= 0 and time_pressure >= 150:
            return "cooling"
        return "stable"

    def _watchlist_count(self, player_id: str) -> int:
        return len(
            list(self.session.scalars(select(MarketWatchlistEntry).where(MarketWatchlistEntry.player_id == player_id)).all())
        )

    def _current_player_club_id(self, player_id: str, *, on_date: date) -> str | None:
        current_contract = self.context_service.get_current_contract(player_id, reference_on=on_date)
        if current_contract is not None:
            return current_contract.club_id
        player = self._require_player(player_id)
        return player.current_club_profile_id

    def _club_reputation_score(self, club: ClubProfile) -> float:
        score = 50.0
        if club.country_code:
            score += 5.0
        if club.city_name:
            score += 3.0
        listing_count = len(
            list(self.session.scalars(select(TransferListing).where(TransferListing.selling_club_id == club.id)).all())
        )
        return clamp(score + (listing_count * 1.2))

    def _club_league_score(self, club: ClubProfile) -> float:
        country_bonus = 8.0 if club.country_code and club.country_code != "NG" else 0.0
        return clamp(55.0 + country_bonus)

    def _playtime_probability(self, club_id: str, position: str | None) -> float:
        depth = self._club_position_depth(club_id, position)
        return clamp(92.0 - (depth * 18.0))

    def _club_position_depth(self, club_id: str, position: str | None) -> int:
        normalized = (position or "").strip().lower()
        if not normalized:
            return 2
        current_contracts = list(
            self.session.scalars(
                select(PlayerContract).where(PlayerContract.club_id == club_id, PlayerContract.status.in_(("active", "expiring")))
            ).all()
        )
        if not current_contracts:
            return 1
        players = self._players_by_ids([item.player_id for item in current_contracts])
        depth = 0
        for contract in current_contracts:
            player = players.get(contract.player_id)
            if player is not None and (player.normalized_position or "").strip().lower() == normalized:
                depth += 1
        return max(1, depth)

    def _long_tenure_bonus(self, player_id: str, *, on_date: date) -> float:
        current_contract = self.context_service.get_current_contract(player_id, reference_on=on_date)
        if current_contract is None:
            return 0.0
        tenure_days = max(0, (on_date - current_contract.starts_on).days)
        return clamp(tenure_days / 18.0, 0.0, 100.0)

    def _instability_penalty(self, player_id: str) -> float:
        completed_moves = len(
            list(
                self.session.scalars(
                    select(TransferNegotiation).where(
                        TransferNegotiation.player_id == player_id,
                        TransferNegotiation.status == "completed",
                    )
                ).all()
            )
        )
        return clamp(completed_moves * 12.0)

    def _sell_on_clause_pct(self, clauses_json: dict[str, Any]) -> Decimal | None:
        raw = clauses_json.get("sell_on_clause_pct")
        if raw is None:
            return None
        return Decimal(str(raw))

    def _player_coach_relationship(self, player_id: str, club_id: str) -> PlayerCoachRelationship:
        relationship = self.session.scalar(
            select(PlayerCoachRelationship).where(
                PlayerCoachRelationship.player_id == player_id,
                PlayerCoachRelationship.club_id == club_id,
            )
        )
        if relationship is None:
            relationship = PlayerCoachRelationship(player_id=player_id, club_id=club_id)
            self.session.add(relationship)
            self.session.flush()
        return relationship

    def _ensure_player_decision_profile(self, player_id: str) -> PlayerDecisionProfile:
        profile = self.session.scalar(select(PlayerDecisionProfile).where(PlayerDecisionProfile.player_id == player_id))
        if profile is None:
            profile = PlayerDecisionProfile(player_id=player_id)
            self.session.add(profile)
            self.session.flush()
        return profile

    def _ensure_coach_profile(self, club_id: str) -> CoachProfile:
        profile = self.session.scalar(select(CoachProfile).where(CoachProfile.club_id == club_id))
        if profile is None:
            profile = CoachProfile(club_id=club_id)
            self.session.add(profile)
            self.session.flush()
        return profile

    def _ensure_team_dynamics(self, club_id: str) -> ClubTeamDynamics:
        dynamics = self.session.scalar(select(ClubTeamDynamics).where(ClubTeamDynamics.club_id == club_id))
        if dynamics is None:
            dynamics = ClubTeamDynamics(club_id=club_id)
            self.session.add(dynamics)
            self.session.flush()
        return dynamics

    def _listing_bids(self, listing_id: str) -> list[TransferListingBid]:
        return list(
            self.session.scalars(
                select(TransferListingBid)
                .where(TransferListingBid.listing_id == listing_id)
                .order_by(TransferListingBid.amount.desc(), TransferListingBid.timestamp.desc())
            ).all()
        )

    def _winning_bid_for_listing(self, listing_id: str) -> TransferListingBid | None:
        bids = self._listing_bids(listing_id)
        return bids[0] if bids else None

    def _winning_bid_id(self, listing_id: str) -> str | None:
        bid = self._winning_bid_for_listing(listing_id)
        return bid.id if bid is not None else None

    def _append_drama_event(
        self,
        listing: TransferListing,
        *,
        event_type: str,
        headline: str,
        effective_at: datetime,
        metadata: dict[str, Any],
    ) -> None:
        payload = dict(listing.metadata_json or {})
        events = list(payload.get("drama_events") or [])
        events.append(
            {
                "type": event_type,
                "headline": headline,
                "occurred_at": self._coerce_utc(effective_at).isoformat(),
                **metadata,
            }
        )
        payload["drama_events"] = events[-10:]
        listing.metadata_json = payload

    def _notify_club_owner(
        self,
        *,
        club_id: str,
        event_name: str,
        template_key: str,
        message: str,
        resource_id: str,
        payload: dict[str, Any],
    ) -> None:
        owner_user_id = self._club_owner_user_id(club_id)
        if owner_user_id is None:
            return
        self._publish_domain_event(
            event_name,
            {
                "user_id": owner_user_id,
                "resource_id": resource_id,
                "template_key": template_key,
                "message": message,
                **payload,
            },
        )

    def _publish_domain_event(self, name: str, payload: dict[str, Any]) -> None:
        if self.event_publisher is None:
            return
        self.event_publisher.publish(DomainEvent(name=name, payload=payload))

    def _sync_listing_snapshot(self, snapshot: TransferListingView) -> None:
        if self.hub is None:
            return
        self.hub.update_listing(snapshot)

    def _push_listing_event(self, listing_id: str, event_type: str, payload: dict[str, Any]) -> None:
        if self.hub is None:
            return
        self.hub.publish_event(listing_id, event_type, payload)

    def _club_owner_user_id(self, club_id: str) -> str | None:
        club = self.session.get(ClubProfile, club_id)
        return club.owner_user_id if club is not None else None

    def _players_by_ids(self, player_ids: list[str]) -> dict[str, Player]:
        unique_ids = [item for item in dict.fromkeys(player_ids) if item]
        if not unique_ids:
            return {}
        return {
            item.id: item
            for item in self.session.scalars(select(Player).where(Player.id.in_(unique_ids))).all()
        }

    def _clubs_by_ids(self, club_ids: list[str | None]) -> dict[str, ClubProfile]:
        unique_ids = [item for item in dict.fromkeys(club_ids) if item]
        if not unique_ids:
            return {}
        return {
            item.id: item
            for item in self.session.scalars(select(ClubProfile).where(ClubProfile.id.in_(unique_ids))).all()
        }

    @staticmethod
    def _to_player_decision_profile_view(profile: PlayerDecisionProfile) -> PlayerDecisionProfileView:
        return PlayerDecisionProfileView(
            id=profile.id,
            player_id=profile.player_id,
            preferred_leagues_json=list(profile.preferred_leagues_json or []),
            preferred_play_style=profile.preferred_play_style,
            wage_expectation_amount=profile.wage_expectation_amount,
            ambition_level=profile.ambition_level,
            happiness=profile.happiness,
            loyalty=profile.loyalty,
            ambition=profile.ambition,
            frustration=profile.frustration,
            metadata_json=dict(profile.metadata_json or {}),
        )

    @staticmethod
    def _to_coach_profile_view(profile: CoachProfile) -> CoachProfileView:
        return CoachProfileView(
            id=profile.id,
            club_id=profile.club_id,
            personality_json=dict(profile.personality_json or {}),
            tactical_philosophy=profile.tactical_philosophy,
            authority_level=profile.authority_level,
            transfer_preference=profile.transfer_preference,
            metadata_json=dict(profile.metadata_json or {}),
        )

    @staticmethod
    def _to_coach_demand_view(demand: CoachDemand) -> CoachDemandView:
        return CoachDemandView(
            id=demand.id,
            coach_profile_id=demand.coach_profile_id,
            club_id=demand.club_id,
            need=demand.need,
            urgency=demand.urgency,
            active=demand.active,
            metadata_json=dict(demand.metadata_json or {}),
        )

    @staticmethod
    def _to_team_dynamics_view(dynamics: ClubTeamDynamics) -> ClubTeamDynamicsView:
        return ClubTeamDynamicsView(
            id=dynamics.id,
            club_id=dynamics.club_id,
            leaders_json=list(dynamics.leaders_json or []),
            cliques_json=list(dynamics.cliques_json or []),
            morale_groups_json=list(dynamics.morale_groups_json or []),
            chemistry_risk=dynamics.chemistry_risk,
            metadata_json=dict(dynamics.metadata_json or {}),
        )

    @staticmethod
    def _to_watchlist_entry_view(entry: MarketWatchlistEntry) -> MarketWatchlistEntryView:
        return MarketWatchlistEntryView(
            id=entry.id,
            club_id=entry.club_id,
            player_id=entry.player_id,
            source=entry.source,
            discovery_score=entry.discovery_score,
            metadata_json=dict(entry.metadata_json or {}),
        )

    @staticmethod
    def _resolved_happiness(profile: PlayerDecisionProfile, state: PlayerAgencyState | None) -> float:
        if state is not None:
            return clamp((profile.happiness * 0.58) + (state.happiness * 0.42))
        return clamp(profile.happiness)

    @staticmethod
    def _resolved_loyalty(profile: PlayerDecisionProfile, personality: PlayerPersonality | None) -> float:
        if personality is not None:
            return clamp((profile.loyalty * 0.46) + (personality.loyalty * 0.54))
        return clamp(profile.loyalty)

    @staticmethod
    def _resolved_ambition(profile: PlayerDecisionProfile, personality: PlayerPersonality | None) -> float:
        if personality is not None:
            return clamp((profile.ambition * 0.44) + (personality.ambition * 0.56))
        return clamp(profile.ambition)

    @staticmethod
    def _coerce_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _require_listing(self, listing_id: str) -> TransferListing:
        listing = self.session.get(TransferListing, listing_id)
        if listing is None:
            raise TransferMarketNotFoundError(f"Transfer listing {listing_id} was not found.")
        return listing

    def _require_negotiation_by_listing(self, listing_id: str) -> TransferNegotiation:
        negotiation = self.session.scalar(select(TransferNegotiation).where(TransferNegotiation.listing_id == listing_id))
        if negotiation is None:
            raise TransferMarketNotFoundError("Transfer negotiation was not found for this listing.")
        return negotiation

    def _require_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise TransferMarketNotFoundError(f"Player {player_id} was not found.")
        return player

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise TransferMarketNotFoundError(f"Club {club_id} was not found.")
        return club


__all__ = [
    "TransferMarketError",
    "TransferMarketHub",
    "TransferMarketNotFoundError",
    "TransferMarketService",
    "TransferMarketValidationError",
    "ensure_transfer_market_hub",
]
