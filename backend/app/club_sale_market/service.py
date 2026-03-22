from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.calendar_engine.service import CalendarEngineService
from app.models.base import generate_uuid, utcnow
from app.models.club_dynasty_progress import ClubDynastyProgress
from app.models.club_profile import ClubProfile
from app.models.club_sale_market import (
    ClubSaleAuditEvent,
    ClubSaleInquiry,
    ClubSaleListing,
    ClubSaleOffer,
    ClubSaleTransfer,
    ClubValuationSnapshot,
)
from app.models.creator_share_market import CreatorClubShareHolding, CreatorClubShareMarket
from app.models.governance_engine import GovernanceProposal, GovernanceProposalScope, GovernanceProposalStatus
from app.models.user import User
from app.models.wallet import LedgerSourceTag, LedgerUnit
from app.services.club_valuation_service import ClubValuationBreakdown, ClubValuationService
from app.story_feed_engine.service import StoryFeedService
from app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
PLATFORM_FEE_BPS = 1_000
VISIBLE_LISTING_STATUSES = {"active", "under_offer"}
OWNER_LISTING_STATUSES = {"active", "under_offer"}
ALLOWED_VISIBILITIES = {"public", "private", "invite_only"}
ACTIVE_OFFER_STATUSES = {"pending", "accepted"}
INQUIRY_OPEN_STATUSES = {"open", "responded"}


class ClubSaleMarketError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(slots=True)
class ClubSaleMarketService:
    session: Session
    wallet_service: WalletService = field(default_factory=WalletService)
    valuation_service: ClubValuationService | None = None

    def __post_init__(self) -> None:
        if self.valuation_service is None:
            self.valuation_service = ClubValuationService(self.session)

    @staticmethod
    def _normalize_amount(value: Decimal | float | int | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)

    @staticmethod
    def _minor_to_coin(value: int | None) -> Decimal:
        return (Decimal(int(value or 0)) / Decimal("100")).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _coin_to_minor(value: Decimal | float | int | str | None) -> int:
        normalized = Decimal(str(value or 0))
        return int((normalized * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _json_amount(value: Decimal | float | int | str | None) -> str:
        return str(Decimal(str(value or 0)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP))

    @staticmethod
    def _display_amount(value: Decimal | float | int | str | None) -> str:
        return format(Decimal(str(value or 0)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP), "f")

    @staticmethod
    def _new_public_id(prefix: str) -> str:
        return f"{prefix}_{generate_uuid().replace('-', '')[:24]}"

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise ClubSaleMarketError("Club was not found.", reason="club_sale_club_not_found")
        return club

    def _require_owned_club(self, actor: User, club_id: str) -> ClubProfile:
        club = self._require_club(club_id)
        if club.owner_user_id != actor.id:
            raise ClubSaleMarketError(
                "Only the current club owner can manage club sale-market actions.",
                reason="club_sale_owner_required",
            )
        return club

    def _require_user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise ClubSaleMarketError("User was not found.", reason="club_sale_user_not_found")
        return user

    def _normalize_visibility(self, visibility: str) -> str:
        normalized = visibility.strip().lower()
        if normalized not in ALLOWED_VISIBILITIES:
            raise ClubSaleMarketError(
                "Sale visibility must be public, private, or invite_only.",
                reason="club_sale_visibility_invalid",
            )
        return normalized

    def _active_listing_for_club(self, club_id: str) -> ClubSaleListing | None:
        return self.session.scalar(
            select(ClubSaleListing)
            .where(
                ClubSaleListing.club_id == club_id,
                ClubSaleListing.status.in_(tuple(OWNER_LISTING_STATUSES)),
            )
            .order_by(ClubSaleListing.updated_at.desc())
        )

    def _require_owned_listing(self, actor: User, club_id: str) -> ClubSaleListing:
        self._require_owned_club(actor, club_id)
        listing = self._active_listing_for_club(club_id)
        if listing is None or listing.seller_user_id != actor.id:
            raise ClubSaleMarketError(
                "Club sale listing was not found for this owner.",
                reason="club_sale_listing_not_found",
            )
        return listing

    def _require_public_listing(self, club_id: str, *, actionable: bool = False) -> ClubSaleListing:
        listing = self._active_listing_for_club(club_id)
        if listing is None or listing.visibility != "public":
            raise ClubSaleMarketError(
                "Public club sale listing was not found.",
                reason="club_sale_public_listing_not_found",
            )
        if actionable and listing.status != "active":
            raise ClubSaleMarketError(
                "The club sale listing is not currently accepting inquiries or offers.",
                reason="club_sale_listing_unavailable",
            )
        return listing

    def _get_inquiry_by_public_id(self, inquiry_id: str) -> ClubSaleInquiry:
        inquiry = self.session.scalar(
            select(ClubSaleInquiry).where(ClubSaleInquiry.inquiry_id == inquiry_id)
        )
        if inquiry is None:
            raise ClubSaleMarketError("Inquiry was not found.", reason="club_sale_inquiry_not_found")
        return inquiry

    def _get_offer_by_public_id(self, offer_id: str) -> ClubSaleOffer:
        offer = self.session.scalar(select(ClubSaleOffer).where(ClubSaleOffer.offer_id == offer_id))
        if offer is None:
            raise ClubSaleMarketError("Offer was not found.", reason="club_sale_offer_not_found")
        return offer

    def _valuation_breakdown_payload(self, breakdown: ClubValuationBreakdown | ClubValuationSnapshot) -> dict[str, Any]:
        metadata_source = breakdown.metadata if isinstance(breakdown, ClubValuationBreakdown) else breakdown.metadata_json
        metadata_json = dict(metadata_source or {})
        return {
            "first_team_value": self._json_amount(getattr(breakdown, "first_team_value_coin")),
            "reserve_squad_value": self._json_amount(getattr(breakdown, "reserve_squad_value_coin")),
            "u19_squad_value": self._json_amount(getattr(breakdown, "u19_squad_value_coin")),
            "academy_value": self._json_amount(getattr(breakdown, "academy_value_coin")),
            "stadium_value": self._json_amount(getattr(breakdown, "stadium_value_coin")),
            "paid_enhancements_value": self._json_amount(getattr(breakdown, "paid_enhancements_value_coin")),
            "metadata_json": metadata_json,
        }

    def _valuation_payload(self, club: ClubProfile, breakdown: ClubValuationBreakdown) -> dict[str, Any]:
        total = self._normalize_amount(breakdown.total_value_coin)
        return {
            "club_id": club.id,
            "club_name": club.club_name,
            "currency": LedgerUnit.COIN.value,
            "system_valuation": total,
            "system_valuation_minor": self._coin_to_minor(total),
            "breakdown": {
                "first_team_value": self._normalize_amount(breakdown.first_team_value_coin),
                "reserve_squad_value": self._normalize_amount(breakdown.reserve_squad_value_coin),
                "u19_squad_value": self._normalize_amount(breakdown.u19_squad_value_coin),
                "academy_value": self._normalize_amount(breakdown.academy_value_coin),
                "stadium_value": self._normalize_amount(breakdown.stadium_value_coin),
                "paid_enhancements_value": self._normalize_amount(breakdown.paid_enhancements_value_coin),
                "metadata_json": dict(breakdown.metadata or {}),
            },
            "last_refreshed_at": utcnow(),
        }

    def _apply_listing_valuation_snapshot(
        self,
        listing: ClubSaleListing,
        *,
        actor_user_id: str | None,
        reason: str,
    ) -> None:
        snapshot = self.valuation_service.capture_snapshot(
            club_id=listing.club_id,
            actor_user_id=actor_user_id,
            reason=reason,
        )
        listing.valuation_snapshot_id = snapshot.id
        listing.system_valuation_minor = self._coin_to_minor(snapshot.total_value_coin)
        listing.valuation_breakdown_json = self._valuation_breakdown_payload(snapshot)
        listing.valuation_refreshed_at = snapshot.created_at

    def _listing_public_id(self, row_id: str | None) -> str | None:
        if row_id is None:
            return None
        listing = self.session.get(ClubSaleListing, row_id)
        return listing.listing_id if listing is not None else None

    def _inquiry_public_id(self, row_id: str | None) -> str | None:
        if row_id is None:
            return None
        inquiry = self.session.get(ClubSaleInquiry, row_id)
        return inquiry.inquiry_id if inquiry is not None else None

    def _offer_public_id(self, row_id: str | None) -> str | None:
        if row_id is None:
            return None
        offer = self.session.get(ClubSaleOffer, row_id)
        return offer.offer_id if offer is not None else None

    def _transfer_public_id(self, row_id: str | None) -> str | None:
        if row_id is None:
            return None
        transfer = self.session.get(ClubSaleTransfer, row_id)
        return transfer.transfer_id if transfer is not None else None

    def _listing_summary_payload(self, listing: ClubSaleListing) -> dict[str, Any]:
        club = self._require_club(listing.club_id)
        return {
            "listing_id": listing.listing_id,
            "club_id": listing.club_id,
            "club_name": club.club_name,
            "seller_user_id": listing.seller_user_id,
            "status": listing.status,
            "visibility": listing.visibility,
            "currency": LedgerUnit.COIN.value,
            "asking_price": self._normalize_amount(listing.asking_price),
            "system_valuation": self._minor_to_coin(int(listing.system_valuation_minor or 0)),
            "system_valuation_minor": int(listing.system_valuation_minor or 0),
            "valuation_last_refreshed_at": listing.valuation_refreshed_at,
            "created_at": listing.created_at,
            "updated_at": listing.updated_at,
        }

    def _listing_detail_payload(self, listing: ClubSaleListing) -> dict[str, Any]:
        payload = self._listing_summary_payload(listing)
        payload.update(
            {
                "valuation_breakdown": dict(listing.valuation_breakdown_json or {}),
                "note": listing.note,
                "metadata_json": dict(listing.metadata_json or {}),
            }
        )
        return payload

    def _inquiry_payload(self, inquiry: ClubSaleInquiry) -> dict[str, Any]:
        return {
            "inquiry_id": inquiry.inquiry_id,
            "club_id": inquiry.club_id,
            "listing_id": self._listing_public_id(inquiry.listing_id),
            "seller_user_id": inquiry.seller_user_id,
            "buyer_user_id": inquiry.buyer_user_id,
            "status": inquiry.status,
            "message": inquiry.message,
            "response_message": inquiry.response_message,
            "responded_by_user_id": inquiry.responded_by_user_id,
            "responded_at": inquiry.responded_at,
            "metadata_json": dict(inquiry.metadata_json or {}),
            "created_at": inquiry.created_at,
            "updated_at": inquiry.updated_at,
        }

    def _offer_payload(self, offer: ClubSaleOffer) -> dict[str, Any]:
        return {
            "offer_id": offer.offer_id,
            "club_id": offer.club_id,
            "listing_id": self._listing_public_id(offer.listing_id),
            "inquiry_id": self._inquiry_public_id(offer.inquiry_id),
            "parent_offer_id": self._offer_public_id(offer.parent_offer_id),
            "seller_user_id": offer.seller_user_id,
            "buyer_user_id": offer.buyer_user_id,
            "proposer_user_id": offer.proposer_user_id,
            "counterparty_user_id": offer.counterparty_user_id,
            "offer_type": offer.offer_type,
            "status": offer.status,
            "currency": LedgerUnit.COIN.value,
            "offer_price": self._normalize_amount(offer.offered_price),
            "message": offer.message,
            "responded_message": offer.responded_message,
            "responded_by_user_id": offer.responded_by_user_id,
            "responded_at": offer.responded_at,
            "accepted_at": offer.accepted_at,
            "rejected_at": offer.rejected_at,
            "expires_at": offer.expires_at,
            "metadata_json": dict(offer.metadata_json or {}),
            "created_at": offer.created_at,
            "updated_at": offer.updated_at,
        }

    def _transfer_payload(self, transfer: ClubSaleTransfer) -> dict[str, Any]:
        metadata = dict(transfer.metadata_json or {})
        return {
            "transfer_id": transfer.transfer_id,
            "club_id": transfer.club_id,
            "listing_id": self._listing_public_id(transfer.listing_id),
            "offer_id": self._offer_public_id(transfer.offer_id) or "",
            "seller_user_id": transfer.seller_user_id,
            "buyer_user_id": transfer.buyer_user_id,
            "currency": LedgerUnit.COIN.value,
            "executed_sale_price": self._normalize_amount(transfer.executed_sale_price),
            "platform_fee_amount": self._normalize_amount(transfer.platform_fee_amount),
            "seller_net_amount": self._normalize_amount(transfer.seller_net_amount),
            "platform_fee_bps": int(transfer.platform_fee_bps or PLATFORM_FEE_BPS),
            "status": transfer.status,
            "settlement_reference": transfer.settlement_reference,
            "ledger_transaction_id": transfer.ledger_transaction_id,
            "story_feed_item_id": metadata.get("story_feed_item_id"),
            "calendar_event_id": metadata.get("calendar_event_id"),
            "metadata_json": metadata,
            "ownership_transition": {
                "previous_owner_user_id": metadata.get("previous_owner_user_id", transfer.seller_user_id),
                "new_owner_user_id": metadata.get("new_owner_user_id", transfer.buyer_user_id),
                "ownership_lineage_index": int(metadata.get("ownership_lineage_index") or 1),
                "shareholder_count_preserved": int(metadata.get("shareholder_count_preserved") or 0),
                "shareholder_rights_preserved": bool(metadata.get("shareholder_rights_preserved")),
            },
            "created_at": transfer.created_at,
        }

    def _audit_payload(self, event: ClubSaleAuditEvent) -> dict[str, Any]:
        return {
            "id": event.id,
            "club_id": event.club_id,
            "listing_id": self._listing_public_id(event.listing_id),
            "inquiry_id": self._inquiry_public_id(event.inquiry_id),
            "offer_id": self._offer_public_id(event.offer_id),
            "transfer_id": self._transfer_public_id(event.transfer_id),
            "actor_user_id": event.actor_user_id,
            "action": event.action,
            "status_from": event.status_from,
            "status_to": event.status_to,
            "payload_json": dict(event.payload_json or {}),
            "created_at": event.created_at,
        }

    def _ownership_history_payload(self, *, club: ClubProfile, limit: int) -> dict[str, Any]:
        transfer_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(ClubSaleTransfer)
                .where(ClubSaleTransfer.club_id == club.id)
            )
            or 0
        )
        transfers = list(
            self.session.scalars(
                select(ClubSaleTransfer)
                .where(ClubSaleTransfer.club_id == club.id)
                .order_by(ClubSaleTransfer.created_at.desc())
                .limit(limit)
            ).all()
        )
        owner_pairs = self.session.execute(
            select(ClubSaleTransfer.seller_user_id, ClubSaleTransfer.buyer_user_id)
            .where(ClubSaleTransfer.club_id == club.id)
            .order_by(ClubSaleTransfer.created_at.asc())
        ).all()
        shareholder_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorClubShareHolding)
                .where(
                    CreatorClubShareHolding.club_id == club.id,
                    CreatorClubShareHolding.share_count > 0,
                )
            )
            or 0
        )
        active_governance_proposal_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(GovernanceProposal)
                .where(
                    GovernanceProposal.club_id == club.id,
                    GovernanceProposal.scope == GovernanceProposalScope.CLUB,
                    GovernanceProposal.status == GovernanceProposalStatus.OPEN,
                )
            )
            or 0
        )
        previous_owner_user_ids = list(dict.fromkeys([value for pair in owner_pairs for value in pair]))
        if club.owner_user_id not in previous_owner_user_ids:
            previous_owner_user_ids.append(club.owner_user_id)
        last_transfer = transfers[0] if transfers else None
        return {
            "current_owner_user_id": club.owner_user_id,
            "transfer_count": transfer_count,
            "ownership_eras": max(1, transfer_count + 1),
            "shareholder_count": shareholder_count,
            "active_governance_proposal_count": active_governance_proposal_count,
            "last_transfer_id": last_transfer.transfer_id if last_transfer is not None else None,
            "last_transfer_at": last_transfer.created_at if last_transfer is not None else None,
            "previous_owner_user_ids": previous_owner_user_ids,
            "recent_transfers": [
                {
                    "transfer_id": transfer.transfer_id,
                    "seller_user_id": transfer.seller_user_id,
                    "buyer_user_id": transfer.buyer_user_id,
                    "executed_sale_price": self._normalize_amount(transfer.executed_sale_price),
                    "created_at": transfer.created_at,
                    "metadata_json": transfer.metadata_json or {},
                }
                for transfer in transfers
            ],
        }

    def _dynasty_snapshot_payload(self, *, club_id: str, ownership_history: dict[str, Any]) -> dict[str, Any]:
        progress = self.session.scalar(
            select(ClubDynastyProgress).where(ClubDynastyProgress.club_id == club_id)
        )
        continuity_transfers = sum(
            1
            for item in ownership_history["recent_transfers"]
            if bool((item.get("metadata_json") or {}).get("shareholder_rights_preserved"))
        )
        return {
            "dynasty_score": int(progress.dynasty_score) if progress is not None else 0,
            "dynasty_level": int(progress.dynasty_level) if progress is not None else 1,
            "dynasty_title": progress.dynasty_title if progress is not None else "Foundations",
            "seasons_completed": int(progress.seasons_completed) if progress is not None else 0,
            "last_season_label": progress.last_season_label if progress is not None else None,
            "ownership_eras": int(ownership_history["ownership_eras"]),
            "shareholder_continuity_transfers": continuity_transfers,
            "showcase_summary_json": dict(progress.showcase_summary_json or {}) if progress is not None else {},
        }

    def _log_audit(
        self,
        *,
        club_id: str,
        action: str,
        actor_user_id: str | None,
        listing_id: str | None = None,
        inquiry_id: str | None = None,
        offer_id: str | None = None,
        transfer_id: str | None = None,
        status_from: str | None = None,
        status_to: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            ClubSaleAuditEvent(
                club_id=club_id,
                listing_id=listing_id,
                inquiry_id=inquiry_id,
                offer_id=offer_id,
                transfer_id=transfer_id,
                actor_user_id=actor_user_id,
                action=action,
                status_from=status_from,
                status_to=status_to,
                payload_json=payload or {},
            )
        )

    def _close_listing_workflows(
        self,
        listing: ClubSaleListing,
        *,
        actor_user_id: str,
        reason: str,
        inquiry_status: str = "closed",
        keep_offer_id: str | None = None,
    ) -> None:
        now = utcnow()
        for inquiry in self.session.scalars(
            select(ClubSaleInquiry).where(
                ClubSaleInquiry.club_id == listing.club_id,
                ClubSaleInquiry.status.in_(tuple(INQUIRY_OPEN_STATUSES)),
            )
        ).all():
            previous_status = inquiry.status
            inquiry.status = inquiry_status
            inquiry.responded_by_user_id = actor_user_id
            inquiry.responded_at = now
            if not inquiry.response_message:
                inquiry.response_message = reason
            self._log_audit(
                club_id=listing.club_id,
                action="inquiry_closed",
                actor_user_id=actor_user_id,
                listing_id=listing.id,
                inquiry_id=inquiry.id,
                status_from=previous_status,
                status_to=inquiry.status,
                payload={"reason": reason},
            )

        for offer in self.session.scalars(
            select(ClubSaleOffer).where(
                ClubSaleOffer.club_id == listing.club_id,
                ClubSaleOffer.status.in_(("pending", "accepted")),
                ClubSaleOffer.id != keep_offer_id,
            )
        ).all():
            previous_status = offer.status
            offer.status = "withdrawn"
            offer.responded_by_user_id = actor_user_id
            offer.responded_at = now
            offer.rejected_at = now
            if not offer.responded_message:
                offer.responded_message = reason
            self._log_audit(
                club_id=listing.club_id,
                action="offer_withdrawn",
                actor_user_id=actor_user_id,
                listing_id=listing.id,
                offer_id=offer.id,
                status_from=previous_status,
                status_to=offer.status,
                payload={"reason": reason},
            )

    def _supersede_other_pending_offers(self, club_id: str, *, keep_offer_id: str, actor_user_id: str) -> None:
        now = utcnow()
        for offer in self.session.scalars(
            select(ClubSaleOffer).where(
                ClubSaleOffer.club_id == club_id,
                ClubSaleOffer.status == "pending",
                ClubSaleOffer.id != keep_offer_id,
            )
        ).all():
            previous_status = offer.status
            offer.status = "superseded"
            offer.responded_by_user_id = actor_user_id
            offer.responded_at = now
            if not offer.responded_message:
                offer.responded_message = "Another offer path was accepted."
            self._log_audit(
                club_id=club_id,
                action="offer_superseded",
                actor_user_id=actor_user_id,
                listing_id=offer.listing_id,
                offer_id=offer.id,
                status_from=previous_status,
                status_to=offer.status,
            )

    def _preserve_shareholders_after_transfer(self, club_id: str, *, new_owner_user_id: str, transfer_id: str) -> int:
        market = self.session.scalar(
            select(CreatorClubShareMarket).where(CreatorClubShareMarket.club_id == club_id)
        )
        if market is None:
            return 0
        market.creator_user_id = new_owner_user_id
        shareholder_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorClubShareHolding)
                .where(
                    CreatorClubShareHolding.club_id == club_id,
                    CreatorClubShareHolding.share_count > 0,
                )
            )
            or 0
        )
        market.metadata_json = {
            **(market.metadata_json or {}),
            "last_club_sale_transfer_id": transfer_id,
            "club_sale_shareholders_preserved": True,
            "shareholder_rights_preserved_on_sale": True,
            "shareholder_count_preserved": shareholder_count,
        }
        for holding in self.session.scalars(
            select(CreatorClubShareHolding).where(CreatorClubShareHolding.club_id == club_id)
        ).all():
            holding.metadata_json = {
                **(holding.metadata_json or {}),
                "shareholder": int(holding.share_count or 0) > 0,
                "club_sale_shareholders_preserved": True,
                "last_club_sale_transfer_id": transfer_id,
            }
        return shareholder_count

    def _publish_transfer_surfaces(
        self,
        *,
        actor: User,
        club: ClubProfile,
        listing: ClubSaleListing,
        offer: ClubSaleOffer,
        transfer: ClubSaleTransfer,
    ) -> None:
        story_item = StoryFeedService(self.session).publish(
            story_type="club_sale_transfer",
            title=f"{club.club_name} completed a club transfer",
            body=(
                f"{club.club_name} changed ownership for {self._display_amount(transfer.executed_sale_price)} "
                f"{LedgerUnit.COIN.value}. The accepted offer is now settled on GTEX."
            ),
            subject_type="club_sale_transfer",
            subject_id=transfer.transfer_id,
            country_code=club.country_code,
            metadata_json={
                "club_id": club.id,
                "club_name": club.club_name,
                "listing_id": listing.listing_id,
                "offer_id": offer.offer_id,
                "transfer_id": transfer.transfer_id,
                "executed_sale_price": self._display_amount(transfer.executed_sale_price),
                "platform_fee_amount": self._display_amount(transfer.platform_fee_amount),
                "seller_net_amount": self._display_amount(transfer.seller_net_amount),
            },
            featured=transfer.executed_sale_price >= listing.asking_price,
            published_by_user_id=actor.id,
        )
        calendar_event = CalendarEngineService(self.session).upsert_sourced_event(
            event_key=f"club-sale-transfer:{transfer.id}",
            title=f"{club.club_name} ownership transfer",
            description=(
                f"Club sale transfer settled for {self._display_amount(transfer.executed_sale_price)} "
                f"{LedgerUnit.COIN.value}."
            ),
            source_type="club_sale_transfer",
            source_id=transfer.id,
            starts_on=transfer.created_at.date(),
            ends_on=transfer.created_at.date(),
            family="club_events",
            status="live",
            metadata_json={
                "club_id": club.id,
                "club_name": club.club_name,
                "listing_id": listing.listing_id,
                "offer_id": offer.offer_id,
                "transfer_id": transfer.transfer_id,
                "story_feed_item_id": story_item.id,
            },
            actor=actor,
        )
        transfer.metadata_json = {
            **(transfer.metadata_json or {}),
            "story_feed_item_id": story_item.id,
            "calendar_event_id": calendar_event.id,
        }

    def get_valuation(self, *, club_id: str) -> dict[str, Any]:
        club = self._require_club(club_id)
        breakdown = self.valuation_service.compute_visible_valuation(club_id=club_id)
        return self._valuation_payload(club, breakdown)

    def list_public_listings(self, *, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        stmt = (
            select(ClubSaleListing)
            .where(
                ClubSaleListing.visibility == "public",
                ClubSaleListing.status.in_(tuple(VISIBLE_LISTING_STATUSES)),
            )
            .order_by(ClubSaleListing.updated_at.desc())
        )
        items = list(self.session.scalars(stmt.offset(offset).limit(limit)).all())
        total = int(
            self.session.scalar(
                select(func.count())
                .select_from(ClubSaleListing)
                .where(
                    ClubSaleListing.visibility == "public",
                    ClubSaleListing.status.in_(tuple(VISIBLE_LISTING_STATUSES)),
                )
            )
            or 0
        )
        return {
            "total": total,
            "items": [self._listing_summary_payload(item) for item in items],
        }

    def get_public_listing(self, *, club_id: str) -> dict[str, Any]:
        listing = self._require_public_listing(club_id)
        return self._listing_detail_payload(listing)

    def list_my_listings(self, *, actor: User) -> dict[str, Any]:
        items = list(
            self.session.scalars(
                select(ClubSaleListing)
                .where(ClubSaleListing.seller_user_id == actor.id)
                .order_by(ClubSaleListing.updated_at.desc())
            ).all()
        )
        return {
            "total": len(items),
            "items": [self._listing_summary_payload(item) for item in items],
        }

    def create_listing(
        self,
        *,
        actor: User,
        club_id: str,
        asking_price: Decimal,
        visibility: str,
        note: str | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_owned_club(actor, club_id)
        if self._active_listing_for_club(club_id) is not None:
            raise ClubSaleMarketError(
                "An active club sale listing already exists for this club.",
                reason="club_sale_listing_already_active",
            )
        listing = ClubSaleListing(
            listing_id=self._new_public_id("club_listing"),
            club_id=club_id,
            seller_user_id=actor.id,
            visibility=self._normalize_visibility(visibility),
            status="active",
            asking_price=self._normalize_amount(asking_price),
            note=note,
            metadata_json=dict(metadata_json or {}),
            valuation_breakdown_json={},
        )
        self._apply_listing_valuation_snapshot(
            listing,
            actor_user_id=actor.id,
            reason="listing_created",
        )
        self.session.add(listing)
        self.session.flush()
        self._log_audit(
            club_id=club_id,
            action="listing_created",
            actor_user_id=actor.id,
            listing_id=listing.id,
            status_to=listing.status,
            payload={
                "asking_price": str(listing.asking_price),
                "visibility": listing.visibility,
                "system_valuation_minor": listing.system_valuation_minor,
            },
        )
        self.session.flush()
        return self._listing_detail_payload(listing)

    def update_listing(
        self,
        *,
        actor: User,
        club_id: str,
        asking_price: Decimal,
        visibility: str,
        note: str | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        listing = self._require_owned_listing(actor, club_id)
        if listing.status != "active":
            raise ClubSaleMarketError(
                "Only active club sale listings can be updated.",
                reason="club_sale_listing_update_blocked",
            )
        previous_visibility = listing.visibility
        previous_price = self._normalize_amount(listing.asking_price)
        listing.asking_price = self._normalize_amount(asking_price)
        listing.visibility = self._normalize_visibility(visibility)
        listing.note = note
        listing.metadata_json = dict(metadata_json or {})
        self._apply_listing_valuation_snapshot(
            listing,
            actor_user_id=actor.id,
            reason="listing_updated",
        )
        self._log_audit(
            club_id=club_id,
            action="listing_updated",
            actor_user_id=actor.id,
            listing_id=listing.id,
            status_from=listing.status,
            status_to=listing.status,
            payload={
                "previous_asking_price": str(previous_price),
                "asking_price": str(listing.asking_price),
                "previous_visibility": previous_visibility,
                "visibility": listing.visibility,
                "system_valuation_minor": listing.system_valuation_minor,
            },
        )
        self.session.flush()
        return self._listing_detail_payload(listing)

    def cancel_listing(self, *, actor: User, club_id: str, reason: str | None = None) -> dict[str, Any]:
        listing = self._require_owned_listing(actor, club_id)
        if listing.status not in {"active", "under_offer"}:
            raise ClubSaleMarketError(
                "Club sale listing can no longer be cancelled.",
                reason="club_sale_listing_cancel_blocked",
            )
        previous_status = listing.status
        listing.status = "cancelled"
        listing.closed_at = utcnow()
        closure_reason = reason or "Club sale listing was cancelled by the owner."
        self._close_listing_workflows(listing, actor_user_id=actor.id, reason=closure_reason)
        self._log_audit(
            club_id=club_id,
            action="listing_cancelled",
            actor_user_id=actor.id,
            listing_id=listing.id,
            status_from=previous_status,
            status_to=listing.status,
            payload={"reason": closure_reason},
        )
        self.session.flush()
        return self._listing_detail_payload(listing)

    def create_inquiry(
        self,
        *,
        actor: User,
        club_id: str,
        message: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        listing = self._require_public_listing(club_id, actionable=True)
        if actor.id == listing.seller_user_id:
            raise ClubSaleMarketError(
                "Owners cannot inquire on their own club sale listing.",
                reason="club_sale_self_inquiry_forbidden",
            )
        inquiry = ClubSaleInquiry(
            inquiry_id=self._new_public_id("club_inquiry"),
            club_id=club_id,
            listing_id=listing.id,
            seller_user_id=listing.seller_user_id,
            buyer_user_id=actor.id,
            status="open",
            message=message,
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(inquiry)
        self.session.flush()
        self._log_audit(
            club_id=club_id,
            action="inquiry_created",
            actor_user_id=actor.id,
            listing_id=listing.id,
            inquiry_id=inquiry.id,
            status_to=inquiry.status,
        )
        self.session.flush()
        return self._inquiry_payload(inquiry)

    def list_inquiries(self, *, actor: User, club_id: str) -> dict[str, Any]:
        self._require_owned_club(actor, club_id)
        items = list(
            self.session.scalars(
                select(ClubSaleInquiry)
                .where(
                    ClubSaleInquiry.club_id == club_id,
                    ClubSaleInquiry.seller_user_id == actor.id,
                )
                .order_by(ClubSaleInquiry.updated_at.desc())
            ).all()
        )
        return {
            "total": len(items),
            "items": [self._inquiry_payload(item) for item in items],
        }

    def respond_inquiry(
        self,
        *,
        actor: User,
        club_id: str,
        inquiry_id: str,
        response_message: str,
        close_thread: bool,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        inquiry = self._get_inquiry_by_public_id(inquiry_id)
        if inquiry.club_id != club_id:
            raise ClubSaleMarketError("Inquiry was not found.", reason="club_sale_inquiry_not_found")
        self._require_owned_club(actor, club_id)
        if inquiry.seller_user_id != actor.id:
            raise ClubSaleMarketError(
                "Only the listing owner can respond to inquiries.",
                reason="club_sale_owner_required",
            )
        if inquiry.status in {"closed", "archived", "rejected", "closed_on_transfer"}:
            raise ClubSaleMarketError(
                "Closed inquiries cannot be updated.",
                reason="club_sale_inquiry_closed",
            )
        previous_status = inquiry.status
        inquiry.response_message = response_message
        inquiry.responded_by_user_id = actor.id
        inquiry.responded_at = utcnow()
        inquiry.status = "closed" if close_thread else "responded"
        inquiry.metadata_json = {
            **(inquiry.metadata_json or {}),
            **dict(metadata_json or {}),
        }
        self._log_audit(
            club_id=club_id,
            action="inquiry_responded",
            actor_user_id=actor.id,
            listing_id=inquiry.listing_id,
            inquiry_id=inquiry.id,
            status_from=previous_status,
            status_to=inquiry.status,
        )
        self.session.flush()
        return self._inquiry_payload(inquiry)

    def archive_inquiry(
        self,
        *,
        actor: User,
        club_id: str,
        inquiry_id: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        inquiry = self._get_inquiry_by_public_id(inquiry_id)
        if inquiry.club_id != club_id:
            raise ClubSaleMarketError("Inquiry was not found.", reason="club_sale_inquiry_not_found")
        self._require_owned_club(actor, club_id)
        if inquiry.seller_user_id != actor.id:
            raise ClubSaleMarketError(
                "Only the listing owner can archive inquiries.",
                reason="club_sale_owner_required",
            )
        if inquiry.status in {"archived", "closed_on_transfer"}:
            raise ClubSaleMarketError(
                "Inquiry is no longer actionable.",
                reason="club_sale_inquiry_closed",
            )
        previous_status = inquiry.status
        inquiry.status = "archived"
        inquiry.responded_by_user_id = actor.id
        inquiry.responded_at = utcnow()
        inquiry.metadata_json = {
            **(inquiry.metadata_json or {}),
            **dict(metadata_json or {}),
        }
        self._log_audit(
            club_id=club_id,
            action="inquiry_archived",
            actor_user_id=actor.id,
            listing_id=inquiry.listing_id,
            inquiry_id=inquiry.id,
            status_from=previous_status,
            status_to=inquiry.status,
        )
        self.session.flush()
        return self._inquiry_payload(inquiry)

    def reject_inquiry(
        self,
        *,
        actor: User,
        club_id: str,
        inquiry_id: str,
        response_message: str | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        inquiry = self._get_inquiry_by_public_id(inquiry_id)
        if inquiry.club_id != club_id:
            raise ClubSaleMarketError("Inquiry was not found.", reason="club_sale_inquiry_not_found")
        self._require_owned_club(actor, club_id)
        if inquiry.seller_user_id != actor.id:
            raise ClubSaleMarketError(
                "Only the listing owner can reject inquiries.",
                reason="club_sale_owner_required",
            )
        if inquiry.status in {"rejected", "closed", "archived", "closed_on_transfer"}:
            raise ClubSaleMarketError(
                "Inquiry is no longer actionable.",
                reason="club_sale_inquiry_closed",
            )
        previous_status = inquiry.status
        inquiry.status = "rejected"
        inquiry.response_message = response_message
        inquiry.responded_by_user_id = actor.id
        inquiry.responded_at = utcnow()
        inquiry.metadata_json = {
            **(inquiry.metadata_json or {}),
            **dict(metadata_json or {}),
        }
        self._log_audit(
            club_id=club_id,
            action="inquiry_rejected",
            actor_user_id=actor.id,
            listing_id=inquiry.listing_id,
            inquiry_id=inquiry.id,
            status_from=previous_status,
            status_to=inquiry.status,
        )
        self.session.flush()
        return self._inquiry_payload(inquiry)

    def create_offer(
        self,
        *,
        actor: User,
        club_id: str,
        offer_price: Decimal,
        inquiry_id: str | None,
        message: str | None,
        expires_at,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        listing = self._require_public_listing(club_id, actionable=True)
        if actor.id == listing.seller_user_id:
            raise ClubSaleMarketError(
                "Owners cannot submit offers on their own club sale listing.",
                reason="club_sale_self_offer_forbidden",
            )
        existing_offer = self.session.scalar(
            select(ClubSaleOffer).where(
                ClubSaleOffer.club_id == club_id,
                ClubSaleOffer.buyer_user_id == actor.id,
                ClubSaleOffer.status.in_(tuple(ACTIVE_OFFER_STATUSES)),
            )
        )
        if existing_offer is not None:
            raise ClubSaleMarketError(
                "You already have an unresolved offer path for this club sale.",
                reason="club_sale_offer_already_open",
            )

        inquiry_row_id = None
        if inquiry_id is not None:
            inquiry = self._get_inquiry_by_public_id(inquiry_id)
            if inquiry.club_id != club_id or inquiry.buyer_user_id != actor.id:
                raise ClubSaleMarketError(
                    "Inquiry was not found for this buyer and club.",
                    reason="club_sale_inquiry_not_found",
                )
            inquiry_row_id = inquiry.id

        offer = ClubSaleOffer(
            offer_id=self._new_public_id("club_offer"),
            club_id=club_id,
            listing_id=listing.id,
            inquiry_id=inquiry_row_id,
            seller_user_id=listing.seller_user_id,
            buyer_user_id=actor.id,
            proposer_user_id=actor.id,
            counterparty_user_id=listing.seller_user_id,
            offer_type="offer",
            status="pending",
            offered_price=self._normalize_amount(offer_price),
            message=message,
            expires_at=expires_at,
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(offer)
        self.session.flush()
        self._log_audit(
            club_id=club_id,
            action="offer_created",
            actor_user_id=actor.id,
            listing_id=listing.id,
            inquiry_id=inquiry_row_id,
            offer_id=offer.id,
            status_to=offer.status,
            payload={"offer_price": str(offer.offered_price)},
        )
        self.session.flush()
        return self._offer_payload(offer)

    def list_offers(self, *, actor: User, club_id: str) -> dict[str, Any]:
        self._require_owned_club(actor, club_id)
        items = list(
            self.session.scalars(
                select(ClubSaleOffer)
                .where(
                    ClubSaleOffer.club_id == club_id,
                    ClubSaleOffer.seller_user_id == actor.id,
                )
                .order_by(ClubSaleOffer.updated_at.desc())
            ).all()
        )
        return {
            "total": len(items),
            "items": [self._offer_payload(item) for item in items],
        }

    def list_my_offers(self, *, actor: User) -> dict[str, Any]:
        items = list(
            self.session.scalars(
                select(ClubSaleOffer)
                .where(ClubSaleOffer.buyer_user_id == actor.id)
                .order_by(ClubSaleOffer.updated_at.desc())
            ).all()
        )
        return {
            "total": len(items),
            "items": [self._offer_payload(item) for item in items],
        }

    def counter_offer(
        self,
        *,
        actor: User,
        club_id: str,
        offer_id: str,
        offer_price: Decimal,
        message: str | None,
        expires_at,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        offer = self._get_offer_by_public_id(offer_id)
        if offer.club_id != club_id:
            raise ClubSaleMarketError("Offer was not found.", reason="club_sale_offer_not_found")
        self._require_owned_club(actor, club_id)
        if offer.seller_user_id != actor.id or offer.counterparty_user_id != actor.id or offer.status != "pending":
            raise ClubSaleMarketError(
                "Only the current listing owner can counter a pending buyer offer.",
                reason="club_sale_offer_not_actionable",
            )
        previous_status = offer.status
        offer.status = "countered"
        offer.responded_by_user_id = actor.id
        offer.responded_at = utcnow()
        offer.responded_message = message
        counter = ClubSaleOffer(
            offer_id=self._new_public_id("club_offer"),
            club_id=club_id,
            listing_id=offer.listing_id,
            inquiry_id=offer.inquiry_id,
            parent_offer_id=offer.id,
            seller_user_id=offer.seller_user_id,
            buyer_user_id=offer.buyer_user_id,
            proposer_user_id=actor.id,
            counterparty_user_id=offer.proposer_user_id,
            offer_type="counter",
            status="pending",
            offered_price=self._normalize_amount(offer_price),
            message=message,
            expires_at=expires_at,
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(counter)
        self.session.flush()
        self._log_audit(
            club_id=club_id,
            action="offer_countered",
            actor_user_id=actor.id,
            listing_id=offer.listing_id,
            inquiry_id=offer.inquiry_id,
            offer_id=counter.id,
            status_from=previous_status,
            status_to=counter.status,
            payload={
                "parent_offer_id": offer.offer_id,
                "offer_price": str(counter.offered_price),
            },
        )
        self.session.flush()
        return self._offer_payload(counter)

    def accept_offer(
        self,
        *,
        actor: User,
        club_id: str,
        offer_id: str,
        message: str | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        offer = self._get_offer_by_public_id(offer_id)
        if offer.club_id != club_id:
            raise ClubSaleMarketError("Offer was not found.", reason="club_sale_offer_not_found")
        if offer.status != "pending" or offer.counterparty_user_id != actor.id:
            raise ClubSaleMarketError(
                "Only the current counterparty can accept this pending offer.",
                reason="club_sale_offer_not_actionable",
            )
        if actor.id == offer.seller_user_id:
            self._require_owned_club(actor, club_id)
        previous_status = offer.status
        offer.status = "accepted"
        offer.responded_by_user_id = actor.id
        offer.responded_at = utcnow()
        offer.accepted_at = offer.responded_at
        offer.responded_message = message
        offer.metadata_json = {
            **(offer.metadata_json or {}),
            **dict(metadata_json or {}),
        }

        listing = self.session.get(ClubSaleListing, offer.listing_id) if offer.listing_id is not None else None
        if listing is None:
            raise ClubSaleMarketError(
                "Offer no longer points to an active club sale listing.",
                reason="club_sale_transfer_path_invalid",
            )
        if listing.status == "active":
            listing.status = "under_offer"

        self._supersede_other_pending_offers(club_id, keep_offer_id=offer.id, actor_user_id=actor.id)
        self._log_audit(
            club_id=club_id,
            action="offer_accepted",
            actor_user_id=actor.id,
            listing_id=offer.listing_id,
            inquiry_id=offer.inquiry_id,
            offer_id=offer.id,
            status_from=previous_status,
            status_to=offer.status,
            payload={"offer_price": str(offer.offered_price)},
        )
        self.session.flush()
        return self._offer_payload(offer)

    def reject_offer(
        self,
        *,
        actor: User,
        club_id: str,
        offer_id: str,
        message: str | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        offer = self._get_offer_by_public_id(offer_id)
        if offer.club_id != club_id:
            raise ClubSaleMarketError("Offer was not found.", reason="club_sale_offer_not_found")
        if offer.status != "pending" or offer.counterparty_user_id != actor.id:
            raise ClubSaleMarketError(
                "Only the current counterparty can reject this pending offer.",
                reason="club_sale_offer_not_actionable",
            )
        if actor.id == offer.seller_user_id:
            self._require_owned_club(actor, club_id)
        previous_status = offer.status
        offer.status = "rejected"
        offer.responded_by_user_id = actor.id
        offer.responded_at = utcnow()
        offer.rejected_at = offer.responded_at
        offer.responded_message = message
        offer.metadata_json = {
            **(offer.metadata_json or {}),
            **dict(metadata_json or {}),
        }
        self._log_audit(
            club_id=club_id,
            action="offer_rejected",
            actor_user_id=actor.id,
            listing_id=offer.listing_id,
            inquiry_id=offer.inquiry_id,
            offer_id=offer.id,
            status_from=previous_status,
            status_to=offer.status,
        )
        self.session.flush()
        return self._offer_payload(offer)

    def mark_offer_closed(
        self,
        *,
        actor: User,
        club_id: str,
        offer_id: str,
        message: str | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        offer = self._get_offer_by_public_id(offer_id)
        if offer.club_id != club_id:
            raise ClubSaleMarketError("Offer was not found.", reason="club_sale_offer_not_found")
        self._require_owned_club(actor, club_id)
        if offer.seller_user_id != actor.id:
            raise ClubSaleMarketError(
                "Only the listing owner can close offer paths.",
                reason="club_sale_owner_required",
            )
        if offer.status in {"closed", "executed", "withdrawn", "rejected", "superseded"}:
            raise ClubSaleMarketError(
                "Offer is no longer actionable.",
                reason="club_sale_offer_not_actionable",
            )
        listing = self.session.get(ClubSaleListing, offer.listing_id) if offer.listing_id is not None else None
        previous_status = offer.status
        offer.status = "closed"
        offer.responded_by_user_id = actor.id
        offer.responded_at = utcnow()
        offer.responded_message = message
        offer.metadata_json = {
            **(offer.metadata_json or {}),
            **dict(metadata_json or {}),
        }
        if previous_status == "accepted" and listing is not None and listing.status == "under_offer":
            listing.status = "active"
        self._log_audit(
            club_id=club_id,
            action="offer_closed",
            actor_user_id=actor.id,
            listing_id=offer.listing_id,
            inquiry_id=offer.inquiry_id,
            offer_id=offer.id,
            status_from=previous_status,
            status_to=offer.status,
        )
        self.session.flush()
        return self._offer_payload(offer)

    def execute_transfer(
        self,
        *,
        actor: User,
        club_id: str,
        offer_id: str,
        executed_sale_price: Decimal,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        club = self._require_owned_club(actor, club_id)
        offer = self._get_offer_by_public_id(offer_id)
        if offer.club_id != club_id or offer.status != "accepted" or offer.seller_user_id != actor.id:
            raise ClubSaleMarketError(
                "A valid accepted offer path is required before transfer execution.",
                reason="club_sale_transfer_path_invalid",
            )
        listing = self.session.get(ClubSaleListing, offer.listing_id) if offer.listing_id is not None else None
        if listing is None or listing.seller_user_id != actor.id or listing.status not in {"under_offer", "active"}:
            raise ClubSaleMarketError(
                "A valid active sale listing is required before transfer execution.",
                reason="club_sale_transfer_path_invalid",
            )
        existing_transfer = self.session.scalar(
            select(ClubSaleTransfer).where(ClubSaleTransfer.offer_id == offer.id)
        )
        if existing_transfer is not None:
            raise ClubSaleMarketError(
                "This accepted offer has already been settled.",
                reason="club_sale_transfer_already_settled",
            )

        buyer = self._require_user(offer.buyer_user_id)
        executed_sale_price = self._normalize_amount(executed_sale_price)
        if executed_sale_price <= Decimal("0.0000"):
            raise ClubSaleMarketError(
                "Executed sale price must be greater than zero.",
                reason="club_sale_transfer_price_invalid",
            )
        platform_fee_amount = self._normalize_amount(
            executed_sale_price * Decimal(PLATFORM_FEE_BPS) / Decimal(10_000)
        )
        seller_net_amount = self._normalize_amount(executed_sale_price - platform_fee_amount)
        valuation_snapshot = self.valuation_service.capture_snapshot(
            club_id=club_id,
            actor_user_id=actor.id,
            reason="transfer_executed",
        )
        settlement_reference = f"club-sale:{listing.listing_id}:{generate_uuid()}"

        buyer_account = self.wallet_service.get_user_account(self.session, buyer, LedgerUnit.COIN)
        seller_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=buyer_account,
                    amount=-executed_sale_price,
                    source_tag=LedgerSourceTag.CLUB_SALE_PURCHASE,
                ),
                LedgerPosting(
                    account=seller_account,
                    amount=seller_net_amount,
                    source_tag=LedgerSourceTag.CLUB_SALE_SALE,
                ),
                LedgerPosting(
                    account=platform_account,
                    amount=platform_fee_amount,
                    source_tag=LedgerSourceTag.CLUB_SALE_PLATFORM_FEE,
                ),
            ],
            reason=self.wallet_service.trade_settlement_reason,
            reference=settlement_reference,
            description="Club sale marketplace transfer settlement",
            external_reference=settlement_reference,
            actor=actor,
        )

        transfer = ClubSaleTransfer(
            transfer_id=self._new_public_id("club_transfer"),
            club_id=club_id,
            listing_id=listing.id,
            offer_id=offer.id,
            seller_user_id=actor.id,
            buyer_user_id=buyer.id,
            valuation_snapshot_id=valuation_snapshot.id,
            executed_sale_price=executed_sale_price,
            platform_fee_amount=platform_fee_amount,
            seller_net_amount=seller_net_amount,
            platform_fee_bps=PLATFORM_FEE_BPS,
            status="settled",
            settlement_reference=settlement_reference,
            ledger_transaction_id=entries[0].transaction_id if entries else None,
            metadata_json={
                **dict(metadata_json or {}),
                "listing_asking_price": str(self._normalize_amount(listing.asking_price)),
                "accepted_offer_id": offer.offer_id,
                "accepted_offer_price": str(self._normalize_amount(offer.offered_price)),
                "previous_owner_user_id": club.owner_user_id,
                "new_owner_user_id": buyer.id,
            },
        )
        self.session.add(transfer)
        self.session.flush()

        previous_owner_user_id = club.owner_user_id
        club.owner_user_id = buyer.id
        prior_transfer_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(ClubSaleTransfer)
                .where(ClubSaleTransfer.club_id == club_id)
            )
            or 0
        )

        listing_previous_status = listing.status
        listing.status = "transferred"
        listing.closed_at = utcnow()

        offer_previous_status = offer.status
        offer.status = "executed"
        offer.responded_by_user_id = actor.id
        offer.responded_at = utcnow()
        if offer.responded_message is None:
            offer.responded_message = "Transfer executed."

        self._close_listing_workflows(
            listing,
            actor_user_id=actor.id,
            reason="Club sale transfer was executed and the listing is now closed.",
            inquiry_status="closed_on_transfer",
            keep_offer_id=offer.id,
        )
        shareholder_count_preserved = self._preserve_shareholders_after_transfer(
            club_id,
            new_owner_user_id=buyer.id,
            transfer_id=transfer.transfer_id,
        )
        transfer.metadata_json = {
            **(transfer.metadata_json or {}),
            "previous_owner_user_id": previous_owner_user_id,
            "new_owner_user_id": buyer.id,
            "ownership_lineage_index": prior_transfer_count,
            "shareholder_count_preserved": shareholder_count_preserved,
            "shareholder_rights_preserved": shareholder_count_preserved > 0,
        }
        self._publish_transfer_surfaces(
            actor=actor,
            club=club,
            listing=listing,
            offer=offer,
            transfer=transfer,
        )
        self._log_audit(
            club_id=club_id,
            action="transfer_executed",
            actor_user_id=actor.id,
            listing_id=listing.id,
            offer_id=offer.id,
            transfer_id=transfer.id,
            status_from=listing_previous_status,
            status_to=listing.status,
            payload={
                "previous_owner_user_id": previous_owner_user_id,
                "new_owner_user_id": buyer.id,
                "executed_sale_price": str(executed_sale_price),
                "platform_fee_amount": str(platform_fee_amount),
                "seller_net_amount": str(seller_net_amount),
                "platform_fee_bps": PLATFORM_FEE_BPS,
                "valuation_snapshot_id": valuation_snapshot.id,
            },
        )
        self._log_audit(
            club_id=club_id,
            action="offer_executed",
            actor_user_id=actor.id,
            listing_id=listing.id,
            offer_id=offer.id,
            transfer_id=transfer.id,
            status_from=offer_previous_status,
            status_to=offer.status,
        )
        self.session.flush()
        return self._transfer_payload(transfer)

    def history_for_club(self, *, actor: User, club_id: str, limit: int = 50) -> dict[str, Any]:
        club = self._require_owned_club(actor, club_id)
        listings = list(
            self.session.scalars(
                select(ClubSaleListing)
                .where(ClubSaleListing.club_id == club_id)
                .order_by(ClubSaleListing.updated_at.desc())
                .limit(limit)
            ).all()
        )
        offers = list(
            self.session.scalars(
                select(ClubSaleOffer)
                .where(ClubSaleOffer.club_id == club_id)
                .order_by(ClubSaleOffer.updated_at.desc())
                .limit(limit)
            ).all()
        )
        transfers = list(
            self.session.scalars(
                select(ClubSaleTransfer)
                .where(ClubSaleTransfer.club_id == club_id)
                .order_by(ClubSaleTransfer.created_at.desc())
                .limit(limit)
            ).all()
        )
        audit_events = list(
            self.session.scalars(
                select(ClubSaleAuditEvent)
                .where(ClubSaleAuditEvent.club_id == club_id)
                .order_by(ClubSaleAuditEvent.created_at.desc())
                .limit(limit)
            ).all()
        )
        ownership_history = self._ownership_history_payload(club=club, limit=limit)
        return {
            "club_id": club_id,
            "listings": [self._listing_summary_payload(item) for item in listings],
            "offers": [self._offer_payload(item) for item in offers],
            "transfers": [self._transfer_payload(item) for item in transfers],
            "audit_events": [self._audit_payload(item) for item in audit_events],
            "ownership_history": ownership_history,
            "dynasty_snapshot": self._dynasty_snapshot_payload(
                club_id=club_id,
                ownership_history=ownership_history,
            ),
        }


__all__ = ["ClubSaleMarketError", "ClubSaleMarketService"]
