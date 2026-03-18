from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ingestion.models import Player
from backend.app.models.base import generate_uuid
from backend.app.models.creator_card import (
    CreatorCard,
    CreatorCardListing,
    CreatorCardLoan,
    CreatorCardSale,
    CreatorCardSwap,
)
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.user import User
from backend.app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from backend.app.common.enums.creator_profile_status import CreatorProfileStatus
from backend.app.wallets.service import LedgerPosting, WalletService


class CreatorCardError(ValueError):
    pass


class CreatorCardPermissionError(CreatorCardError):
    pass


class CreatorCardValidationError(CreatorCardError):
    pass


@dataclass(slots=True)
class CreatorCardService:
    session: Session
    wallet_service: WalletService = field(default_factory=WalletService)

    def assign_card(self, *, player_id: str, owner_user_id: str) -> dict[str, object]:
        owner_profile = self._creator_profile_for_user(owner_user_id)
        player = self._get_player(player_id)
        existing = self.session.scalar(select(CreatorCard).where(CreatorCard.player_id == player.id))
        if existing is not None:
            raise CreatorCardValidationError("creator_card_player_already_assigned")
        card = CreatorCard(
            player_id=player.id,
            owner_creator_profile_id=owner_profile.id,
            status="active",
            metadata_json={"assigned_at": datetime.now(UTC).isoformat()},
        )
        self.session.add(card)
        self.session.flush()
        return self._card_payload(card)

    def list_inventory(self, *, actor: User) -> list[dict[str, object]]:
        profile = self._creator_profile_for_user(actor.id)
        cards = self.session.scalars(
            select(CreatorCard)
            .where(CreatorCard.owner_creator_profile_id == profile.id)
            .order_by(CreatorCard.updated_at.desc())
        ).all()
        return [self._card_payload(card) for card in cards]

    def list_open_listings(self) -> list[dict[str, object]]:
        listings = self.session.scalars(
            select(CreatorCardListing)
            .where(CreatorCardListing.status == "open")
            .order_by(CreatorCardListing.created_at.desc())
        ).all()
        return [self._listing_payload(item) for item in listings]

    def create_listing(self, *, actor: User, creator_card_id: str, price_credits: Decimal) -> dict[str, object]:
        seller_profile = self._creator_profile_for_user(actor.id)
        if price_credits <= Decimal("0"):
            raise CreatorCardValidationError("creator_card_listing_price_invalid")
        card = self._get_card(creator_card_id)
        if card.owner_creator_profile_id != seller_profile.id:
            raise CreatorCardPermissionError("creator_card_owner_required")
        self._ensure_card_tradeable(card.id)
        listing = CreatorCardListing(
            creator_card_id=card.id,
            seller_creator_profile_id=seller_profile.id,
            price_credits=self._normalize_amount(price_credits),
            status="open",
            metadata_json={},
        )
        self.session.add(listing)
        self.session.flush()
        return self._listing_payload(listing)

    def buy_listing(self, *, actor: User, listing_id: str) -> dict[str, object]:
        buyer_user = actor
        buyer_profile = self._creator_profile_for_user(actor.id)
        listing = self._get_listing(listing_id)
        if listing.status != "open":
            raise CreatorCardValidationError("creator_card_listing_not_open")
        if listing.seller_creator_profile_id == buyer_profile.id:
            raise CreatorCardValidationError("creator_card_self_purchase_not_allowed")

        card = self._get_card(listing.creator_card_id)
        self._ensure_no_active_loan(card.id)
        seller_profile = self._get_creator_profile(listing.seller_creator_profile_id)
        seller_user = self._get_user(seller_profile.user_id)
        gross = self._normalize_amount(listing.price_credits)
        settlement_reference = f"creator-card-sale:{listing.id}:{generate_uuid()}"
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(
                    account=self.wallet_service.get_user_account(self.session, buyer_user, LedgerUnit.CREDIT),
                    amount=-gross,
                    source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
                ),
                LedgerPosting(
                    account=self.wallet_service.get_user_account(self.session, seller_user, LedgerUnit.CREDIT),
                    amount=gross,
                    source_tag=LedgerSourceTag.PLAYER_CARD_SALE,
                ),
            ],
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            reference=settlement_reference,
            description="Creator card sale settlement",
            actor=buyer_user,
        )
        card.owner_creator_profile_id = buyer_profile.id
        listing.status = "sold"
        sale = CreatorCardSale(
            creator_card_id=card.id,
            listing_id=listing.id,
            seller_creator_profile_id=seller_profile.id,
            buyer_creator_profile_id=buyer_profile.id,
            price_credits=gross,
            settlement_reference=settlement_reference,
            status="settled",
            metadata_json={},
        )
        self.session.add(sale)
        self.session.flush()
        return self._sale_payload(sale)

    def swap_cards(self, *, actor: User, offered_card_id: str, requested_card_id: str) -> dict[str, object]:
        proposer_profile = self._creator_profile_for_user(actor.id)
        offered_card = self._get_card(offered_card_id)
        requested_card = self._get_card(requested_card_id)
        if offered_card.id == requested_card.id:
            raise CreatorCardValidationError("creator_card_swap_requires_distinct_cards")
        if offered_card.owner_creator_profile_id != proposer_profile.id:
            raise CreatorCardPermissionError("creator_card_owner_required")
        if requested_card.owner_creator_profile_id == proposer_profile.id:
            raise CreatorCardValidationError("creator_card_swap_same_owner_not_allowed")
        self._ensure_card_tradeable(offered_card.id)
        self._ensure_card_tradeable(requested_card.id)

        counterparty_profile = self._get_creator_profile(requested_card.owner_creator_profile_id)
        offered_card.owner_creator_profile_id, requested_card.owner_creator_profile_id = (
            requested_card.owner_creator_profile_id,
            offered_card.owner_creator_profile_id,
        )
        swap = CreatorCardSwap(
            proposer_creator_profile_id=proposer_profile.id,
            counterparty_creator_profile_id=counterparty_profile.id,
            proposer_card_id=offered_card.id,
            counterparty_card_id=requested_card.id,
            status="executed",
            metadata_json={},
        )
        self.session.add(swap)
        self.session.flush()
        return self._swap_payload(swap)

    def loan_card(
        self,
        *,
        actor: User,
        creator_card_id: str,
        borrower_user_id: str,
        duration_days: int,
        loan_fee_credits: Decimal,
    ) -> dict[str, object]:
        if duration_days <= 0 or duration_days > 30:
            raise CreatorCardValidationError("creator_card_loan_duration_invalid")
        lender_user = actor
        lender_profile = self._creator_profile_for_user(actor.id)
        borrower_profile = self._creator_profile_for_user(borrower_user_id)
        borrower_user = self._get_user(borrower_user_id)
        if borrower_profile.id == lender_profile.id:
            raise CreatorCardValidationError("creator_card_self_loan_not_allowed")
        card = self._get_card(creator_card_id)
        if card.owner_creator_profile_id != lender_profile.id:
            raise CreatorCardPermissionError("creator_card_owner_required")
        self._ensure_card_tradeable(card.id)

        fee = self._normalize_amount(loan_fee_credits)
        if fee > Decimal("0"):
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=self.wallet_service.get_user_account(self.session, borrower_user, LedgerUnit.CREDIT),
                        amount=-fee,
                        source_tag=LedgerSourceTag.PLAYER_CARD_PURCHASE,
                    ),
                    LedgerPosting(
                        account=self.wallet_service.get_user_account(self.session, lender_user, LedgerUnit.CREDIT),
                        amount=fee,
                        source_tag=LedgerSourceTag.PLAYER_CARD_SALE,
                    ),
                ],
                reason=LedgerEntryReason.TRADE_SETTLEMENT,
                reference=f"creator-card-loan:{card.id}:{generate_uuid()}",
                description="Creator card loan settlement",
                actor=lender_user,
            )

        now = datetime.now(UTC)
        loan = CreatorCardLoan(
            creator_card_id=card.id,
            lender_creator_profile_id=lender_profile.id,
            borrower_creator_profile_id=borrower_profile.id,
            loan_fee_credits=fee,
            status="active",
            starts_at=now,
            ends_at=now + timedelta(days=duration_days),
            metadata_json={},
        )
        self.session.add(loan)
        self.session.flush()
        return self._loan_payload(loan)

    def return_loan(self, *, actor: User, loan_id: str) -> dict[str, object]:
        loan = self._get_loan(loan_id)
        if loan.status != "active":
            raise CreatorCardValidationError("creator_card_loan_not_active")
        actor_profile = self._creator_profile_for_user(actor.id)
        if actor_profile.id not in {loan.lender_creator_profile_id, loan.borrower_creator_profile_id}:
            raise CreatorCardPermissionError("creator_card_loan_party_required")
        loan.status = "returned"
        loan.returned_at = datetime.now(UTC)
        self.session.flush()
        return self._loan_payload(loan)

    def _creator_profile_for_user(self, user_id: str) -> CreatorProfile:
        creator_profile = self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == user_id))
        if creator_profile is None or creator_profile.status != CreatorProfileStatus.ACTIVE:
            raise CreatorCardPermissionError("creator_access_required")
        return creator_profile

    def _get_creator_profile(self, creator_profile_id: str) -> CreatorProfile:
        creator_profile = self.session.get(CreatorProfile, creator_profile_id)
        if creator_profile is None:
            raise CreatorCardValidationError("creator_profile_not_found")
        return creator_profile

    def _get_user(self, user_id: str) -> User:
        user = self.session.get(User, user_id)
        if user is None:
            raise CreatorCardValidationError("user_not_found")
        return user

    def _get_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise CreatorCardValidationError("creator_card_player_not_found")
        return player

    def _get_card(self, creator_card_id: str) -> CreatorCard:
        card = self.session.get(CreatorCard, creator_card_id)
        if card is None:
            raise CreatorCardValidationError("creator_card_not_found")
        return card

    def _get_listing(self, listing_id: str) -> CreatorCardListing:
        listing = self.session.get(CreatorCardListing, listing_id)
        if listing is None:
            raise CreatorCardValidationError("creator_card_listing_not_found")
        return listing

    def _get_loan(self, loan_id: str) -> CreatorCardLoan:
        loan = self.session.get(CreatorCardLoan, loan_id)
        if loan is None:
            raise CreatorCardValidationError("creator_card_loan_not_found")
        return loan

    def _ensure_card_tradeable(self, creator_card_id: str) -> None:
        open_listing = self.session.scalar(
            select(CreatorCardListing).where(
                CreatorCardListing.creator_card_id == creator_card_id,
                CreatorCardListing.status == "open",
            )
        )
        if open_listing is not None:
            raise CreatorCardValidationError("creator_card_already_listed")
        self._ensure_no_active_loan(creator_card_id)

    def _ensure_no_active_loan(self, creator_card_id: str) -> None:
        active_loan = self.session.scalar(
            select(CreatorCardLoan).where(
                CreatorCardLoan.creator_card_id == creator_card_id,
                CreatorCardLoan.status == "active",
            )
        )
        if active_loan is not None:
            raise CreatorCardValidationError("creator_card_active_loan_exists")

    def _card_payload(self, card: CreatorCard) -> dict[str, object]:
        player = self._get_player(card.player_id)
        owner_profile = self._get_creator_profile(card.owner_creator_profile_id)
        active_loan = self.session.scalar(
            select(CreatorCardLoan).where(
                CreatorCardLoan.creator_card_id == card.id,
                CreatorCardLoan.status == "active",
            )
        )
        return {
            "creator_card_id": card.id,
            "player_id": player.id,
            "player_name": player.full_name,
            "owner_creator_profile_id": owner_profile.id,
            "owner_user_id": owner_profile.user_id,
            "owner_handle": owner_profile.handle,
            "status": card.status,
            "active_loan_id": active_loan.id if active_loan is not None else None,
            "metadata_json": dict(card.metadata_json or {}),
            "created_at": card.created_at,
            "updated_at": card.updated_at,
        }

    def _listing_payload(self, listing: CreatorCardListing) -> dict[str, object]:
        card = self._get_card(listing.creator_card_id)
        player = self._get_player(card.player_id)
        seller_profile = self._get_creator_profile(listing.seller_creator_profile_id)
        return {
            "listing_id": listing.id,
            "creator_card_id": card.id,
            "seller_creator_profile_id": seller_profile.id,
            "seller_user_id": seller_profile.user_id,
            "seller_handle": seller_profile.handle,
            "player_id": player.id,
            "player_name": player.full_name,
            "price_credits": self._normalize_amount(listing.price_credits),
            "status": listing.status,
            "expires_at": listing.expires_at,
            "created_at": listing.created_at,
            "updated_at": listing.updated_at,
        }

    def _sale_payload(self, sale: CreatorCardSale) -> dict[str, object]:
        card = self._get_card(sale.creator_card_id)
        player = self._get_player(card.player_id)
        seller_profile = self._get_creator_profile(sale.seller_creator_profile_id)
        buyer_profile = self._get_creator_profile(sale.buyer_creator_profile_id)
        return {
            "sale_id": sale.id,
            "creator_card_id": sale.creator_card_id,
            "seller_creator_profile_id": sale.seller_creator_profile_id,
            "buyer_creator_profile_id": sale.buyer_creator_profile_id,
            "seller_user_id": seller_profile.user_id,
            "buyer_user_id": buyer_profile.user_id,
            "player_id": player.id,
            "player_name": player.full_name,
            "price_credits": self._normalize_amount(sale.price_credits),
            "settlement_reference": sale.settlement_reference,
            "status": sale.status,
            "created_at": sale.created_at,
        }

    def _swap_payload(self, swap: CreatorCardSwap) -> dict[str, object]:
        return {
            "swap_id": swap.id,
            "proposer_creator_profile_id": swap.proposer_creator_profile_id,
            "counterparty_creator_profile_id": swap.counterparty_creator_profile_id,
            "proposer_card_id": swap.proposer_card_id,
            "counterparty_card_id": swap.counterparty_card_id,
            "status": swap.status,
            "created_at": swap.created_at,
            "updated_at": swap.updated_at,
        }

    def _loan_payload(self, loan: CreatorCardLoan) -> dict[str, object]:
        card = self._get_card(loan.creator_card_id)
        player = self._get_player(card.player_id)
        lender_profile = self._get_creator_profile(loan.lender_creator_profile_id)
        borrower_profile = self._get_creator_profile(loan.borrower_creator_profile_id)
        return {
            "loan_id": loan.id,
            "creator_card_id": loan.creator_card_id,
            "lender_creator_profile_id": loan.lender_creator_profile_id,
            "borrower_creator_profile_id": loan.borrower_creator_profile_id,
            "lender_user_id": lender_profile.user_id,
            "borrower_user_id": borrower_profile.user_id,
            "player_id": player.id,
            "player_name": player.full_name,
            "loan_fee_credits": self._normalize_amount(loan.loan_fee_credits),
            "status": loan.status,
            "starts_at": loan.starts_at,
            "ends_at": loan.ends_at,
            "returned_at": loan.returned_at,
            "created_at": loan.created_at,
            "updated_at": loan.updated_at,
        }

    @staticmethod
    def _normalize_amount(value: Decimal | object) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.0001"))


__all__ = [
    "CreatorCardError",
    "CreatorCardPermissionError",
    "CreatorCardService",
    "CreatorCardValidationError",
]
