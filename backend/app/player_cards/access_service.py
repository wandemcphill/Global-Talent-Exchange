from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_identity.models.reputation import ClubReputationProfile
from app.core.config import Settings, get_settings
from app.ingestion.models import Player
from app.integrity_engine.service import IntegrityEngineService
from app.models.base import utcnow
from app.models.card_access import CardLoanContract, CardLoanListing, StarterSquadRental
from app.models.club_infra import ClubFacility
from app.models.club_profile import ClubProfile
from app.models.player_cards import PlayerCard, PlayerCardHistory, PlayerCardHolding, PlayerCardOwnerHistory, PlayerCardTier
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerUnit
from app.player_cards.service import (
    PlayerCardMarketError,
    PlayerCardNotFoundError,
    PlayerCardPermissionError,
    PlayerCardValidationError,
)
from app.services.regen_service import RegenClubContext, RegenGenerationEngine
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService


DEFAULT_STARTER_RENTAL_FEE = Decimal("5.0000")
DEFAULT_STARTER_RENTAL_TERM_DAYS = 7
DEFAULT_MAX_LOAN_DURATION_DAYS = 30


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class CardLoanError(PlayerCardMarketError):
    pass


class StarterRentalError(PlayerCardMarketError):
    pass


@dataclass(slots=True)
class CardLoanService:
    session: Session
    wallet_service: WalletService = field(default_factory=WalletService)

    def list_listings(
        self,
        *,
        position: str | None = None,
        tier_code: str | None = None,
        max_cost: Decimal | None = None,
        max_duration_days: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(CardLoanListing, PlayerCard, PlayerCardTier, Player)
            .join(PlayerCard, PlayerCard.id == CardLoanListing.player_card_id)
            .join(PlayerCardTier, PlayerCardTier.id == PlayerCard.tier_id)
            .join(Player, Player.id == PlayerCard.player_id)
            .where(CardLoanListing.status == "open", CardLoanListing.available_slots > 0)
            .order_by(CardLoanListing.loan_fee_credits.asc(), CardLoanListing.created_at.desc())
            .limit(limit)
        )
        if position:
            normalized = position.strip().upper()
            stmt = stmt.where(func.upper(func.coalesce(Player.position, "")) == normalized)
        if tier_code:
            stmt = stmt.where(func.lower(PlayerCardTier.code) == tier_code.strip().lower())
        if max_cost is not None:
            stmt = stmt.where(CardLoanListing.loan_fee_credits <= max_cost)
        if max_duration_days is not None:
            stmt = stmt.where(CardLoanListing.duration_days <= max_duration_days)

        rows = self.session.execute(stmt).all()
        return [self._listing_payload(listing, card, tier, player) for listing, card, tier, player in rows]

    def create_listing(
        self,
        *,
        actor: User,
        player_card_id: str,
        total_slots: int,
        duration_days: int,
        loan_fee_credits: Decimal,
        usage_restrictions: dict[str, Any] | None = None,
        terms: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> dict[str, Any]:
        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise PlayerCardPermissionError("Admin accounts cannot create player-card loans.")
        if total_slots <= 0:
            raise PlayerCardValidationError("Loan slot count must be positive.")
        if duration_days <= 0 or duration_days > DEFAULT_MAX_LOAN_DURATION_DAYS:
            raise PlayerCardValidationError(f"Loan duration must be between 1 and {DEFAULT_MAX_LOAN_DURATION_DAYS} days.")
        if loan_fee_credits <= Decimal("0"):
            raise PlayerCardValidationError("Loan fee must be greater than zero.")

        card = self._get_card(player_card_id)
        holding = self._get_holding(actor.id, player_card_id)
        available = holding.quantity_total - holding.quantity_reserved
        if available < total_slots:
            raise PlayerCardValidationError("Not enough unreserved card quantity is available to loan.")

        holding.quantity_reserved += total_slots
        listing = CardLoanListing(
            player_card_id=card.id,
            owner_user_id=actor.id,
            total_slots=total_slots,
            available_slots=total_slots,
            duration_days=duration_days,
            loan_fee_credits=self._normalize_amount(loan_fee_credits),
            currency=LedgerUnit.COIN.value,
            status="open",
            expires_at=expires_at,
            usage_restrictions_json=usage_restrictions or {},
            terms_json=terms or {},
            metadata_json={},
        )
        self.session.add(listing)
        self._append_card_history(card.id, "loan.listed", actor.id, metadata={"loan_listing_id": listing.id, "slots": total_slots})
        self._append_owner_history(card.id, from_user_id=actor.id, to_user_id=None, quantity=total_slots, event_type="loan_listed", reference_id=listing.id)
        self.session.flush()
        return self._listing_payload(listing, card, self._get_tier(card.tier_id), self._get_player(card.player_id))

    def borrow_listing(
        self,
        *,
        actor: User,
        listing_id: str,
        competition_id: str | None = None,
        squad_scope: str | None = None,
    ) -> dict[str, Any]:
        listing = self._get_listing(listing_id)
        if listing.status != "open" or listing.available_slots <= 0:
            raise PlayerCardValidationError("Loan listing is not available.")
        if listing.owner_user_id == actor.id:
            raise PlayerCardValidationError("You cannot borrow your own card loan listing.")
        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise PlayerCardPermissionError("Admin accounts cannot borrow player-card loans.")

        card = self._get_card(listing.player_card_id)
        owner = self.session.get(User, listing.owner_user_id)
        if owner is None:
            raise PlayerCardValidationError("Loan owner was not found.")

        self._ensure_borrower_has_no_player_version(actor.id, card.player_id)
        self._ensure_usage_allowed(listing.usage_restrictions_json, competition_id=competition_id, squad_scope=squad_scope)
        self._collect_fee(actor=actor, owner=owner, fee=self._normalize_amount(listing.loan_fee_credits), reference=f"player-card-loan:{listing.id}:{utcnow().timestamp()}")

        borrowed_at = datetime.now(UTC)
        contract = CardLoanContract(
            listing_id=listing.id,
            player_card_id=card.id,
            owner_user_id=owner.id,
            borrower_user_id=actor.id,
            loan_fee_credits=self._normalize_amount(listing.loan_fee_credits),
            currency=LedgerUnit.COIN.value,
            status="active",
            borrowed_at=borrowed_at,
            due_at=borrowed_at + timedelta(days=listing.duration_days),
            usage_snapshot_json={
                "competition_id": competition_id,
                "squad_scope": squad_scope,
                "restrictions": dict(listing.usage_restrictions_json or {}),
            },
            metadata_json={},
        )
        listing.available_slots -= 1
        self.session.add(contract)
        self._append_card_history(card.id, "loan.borrowed", actor.id, metadata={"loan_contract_id": contract.id, "loan_listing_id": listing.id})
        self._append_owner_history(card.id, from_user_id=owner.id, to_user_id=actor.id, quantity=1, event_type="loan_borrowed", reference_id=contract.id)
        self._run_loan_integrity_checks(contract)
        self.session.flush()
        return self._contract_payload(contract, listing, card, self._get_tier(card.tier_id), self._get_player(card.player_id))

    def return_loan(self, *, actor: User, contract_id: str) -> dict[str, Any]:
        contract = self._get_contract(contract_id)
        if contract.status != "active":
            raise PlayerCardValidationError("Loan contract is not active.")
        if actor.id not in {contract.borrower_user_id, contract.owner_user_id} and actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise PlayerCardPermissionError("Only the borrower, owner, or an admin can complete the return.")

        listing = self._get_listing(contract.listing_id)
        card = self._get_card(contract.player_card_id)
        holding = self._get_holding(contract.owner_user_id, contract.player_card_id)
        now = datetime.now(UTC)
        due_at = _as_utc(contract.due_at)

        contract.status = "expired" if due_at <= now else "returned"
        contract.returned_at = now
        if listing.status == "open" and (listing.expires_at is None or listing.expires_at > now):
            listing.available_slots = min(listing.total_slots, listing.available_slots + 1)
        else:
            holding.quantity_reserved = max(0, holding.quantity_reserved - 1)

        self._append_card_history(card.id, "loan.returned", actor.id, metadata={"loan_contract_id": contract.id})
        self._append_owner_history(card.id, from_user_id=contract.borrower_user_id, to_user_id=contract.owner_user_id, quantity=1, event_type="loan_returned", reference_id=contract.id)
        self.session.flush()
        return self._contract_payload(contract, listing, card, self._get_tier(card.tier_id), self._get_player(card.player_id))

    def reclaim_expired_loans(self, *, owner_user_id: str | None = None) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        stmt = select(CardLoanContract).where(CardLoanContract.status == "active", CardLoanContract.due_at <= now)
        if owner_user_id is not None:
            stmt = stmt.where(CardLoanContract.owner_user_id == owner_user_id)
        contracts = list(self.session.scalars(stmt).all())
        reclaimed: list[dict[str, Any]] = []
        system_actor = self.session.get(User, owner_user_id) if owner_user_id is not None else None
        for contract in contracts:
            actor = system_actor or self.session.get(User, contract.owner_user_id)
            if actor is None:
                continue
            reclaimed.append(self.return_loan(actor=actor, contract_id=contract.id))
        return reclaimed

    def validate_contract_usage(
        self,
        *,
        borrower_user_id: str,
        player_card_id: str,
        competition_id: str | None = None,
        squad_scope: str | None = None,
    ) -> bool:
        contract = self.session.scalar(
            select(CardLoanContract).where(
                CardLoanContract.borrower_user_id == borrower_user_id,
                CardLoanContract.player_card_id == player_card_id,
                CardLoanContract.status == "active",
            )
        )
        if contract is None:
            return False
        if _as_utc(contract.due_at) <= datetime.now(UTC):
            return False
        restrictions = (contract.usage_snapshot_json or {}).get("restrictions") or {}
        self._ensure_usage_allowed(restrictions, competition_id=competition_id, squad_scope=squad_scope)
        return True

    def _collect_fee(self, *, actor: User, owner: User, fee: Decimal, reference: str) -> None:
        buyer_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        owner_account = self.wallet_service.get_user_account(self.session, owner, LedgerUnit.COIN)
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=buyer_account, amount=-fee),
                LedgerPosting(account=owner_account, amount=fee),
            ],
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            reference=reference,
            description="Player card loan fee settlement",
            actor=actor,
        )

    def _run_loan_integrity_checks(self, contract: CardLoanContract) -> None:
        integrity_service = IntegrityEngineService(self.session)
        pair_count = self.session.scalar(
            select(func.count(CardLoanContract.id)).where(
                CardLoanContract.owner_user_id == contract.owner_user_id,
                CardLoanContract.borrower_user_id == contract.borrower_user_id,
                CardLoanContract.created_at >= (datetime.now(UTC) - timedelta(days=7)),
            )
        ) or 0
        if pair_count >= 3:
            subject = f"loan-pair:{contract.owner_user_id}:{contract.borrower_user_id}"
            for user_id in (contract.owner_user_id, contract.borrower_user_id):
                integrity_service.register_incident_once(
                    user_id=user_id,
                    incident_type="repeated_card_loan_pair",
                    subject=subject,
                    severity="medium",
                    title="Repeated card loan pair detected",
                    description=f"{pair_count} loans were created between the same two accounts in the last 7 days.",
                    score_delta=Decimal("-8.50"),
                    metadata_json={"owner_user_id": contract.owner_user_id, "borrower_user_id": contract.borrower_user_id, "count": int(pair_count)},
                )

    def _ensure_borrower_has_no_player_version(self, user_id: str, player_id: str) -> None:
        held_version = self.session.scalar(
            select(func.count(PlayerCardHolding.id))
            .join(PlayerCard, PlayerCard.id == PlayerCardHolding.player_card_id)
            .where(
                PlayerCardHolding.owner_user_id == user_id,
                PlayerCardHolding.quantity_total > 0,
                PlayerCard.player_id == player_id,
            )
        ) or 0
        if held_version > 0:
            raise PlayerCardValidationError("You already control a version of this player.")

        active_loan = self.session.scalar(
            select(func.count(CardLoanContract.id))
            .join(PlayerCard, PlayerCard.id == CardLoanContract.player_card_id)
            .where(
                CardLoanContract.borrower_user_id == user_id,
                CardLoanContract.status == "active",
                PlayerCard.player_id == player_id,
            )
        ) or 0
        if active_loan > 0:
            raise PlayerCardValidationError("You already have an active loan for this player.")

    def _ensure_usage_allowed(
        self,
        restrictions: dict[str, Any] | None,
        *,
        competition_id: str | None,
        squad_scope: str | None,
    ) -> None:
        payload = restrictions or {}
        allowed_competitions = {str(item) for item in payload.get("allowed_competition_ids", [])}
        blocked_competitions = {str(item) for item in payload.get("blocked_competition_ids", [])}
        allowed_squad_scopes = {str(item) for item in payload.get("allowed_squad_scopes", [])}

        if competition_id and allowed_competitions and competition_id not in allowed_competitions:
            raise PlayerCardValidationError("This loan is not eligible for the requested competition.")
        if competition_id and competition_id in blocked_competitions:
            raise PlayerCardValidationError("This loan is blocked from the requested competition.")
        if squad_scope and allowed_squad_scopes and squad_scope not in allowed_squad_scopes:
            raise PlayerCardValidationError("This loan cannot be used in the requested squad scope.")

    def _listing_payload(self, listing: CardLoanListing, card: PlayerCard, tier: PlayerCardTier, player: Player) -> dict[str, Any]:
        return {
            "loan_listing_id": listing.id,
            "player_card_id": card.id,
            "player_id": player.id,
            "player_name": player.full_name,
            "position": player.position,
            "tier_code": tier.code,
            "tier_name": tier.name,
            "edition_code": card.edition_code,
            "owner_user_id": listing.owner_user_id,
            "total_slots": listing.total_slots,
            "available_slots": listing.available_slots,
            "duration_days": listing.duration_days,
            "loan_fee_credits": float(self._normalize_amount(listing.loan_fee_credits)),
            "currency": listing.currency,
            "status": listing.status,
            "usage_restrictions_json": dict(listing.usage_restrictions_json or {}),
            "terms_json": dict(listing.terms_json or {}),
            "expires_at": listing.expires_at,
            "created_at": listing.created_at,
        }

    def _contract_payload(
        self,
        contract: CardLoanContract,
        listing: CardLoanListing,
        card: PlayerCard,
        tier: PlayerCardTier,
        player: Player,
    ) -> dict[str, Any]:
        payload = self._listing_payload(listing, card, tier, player)
        payload.update(
            {
                "loan_contract_id": contract.id,
                "borrower_user_id": contract.borrower_user_id,
                "borrowed_at": contract.borrowed_at,
                "due_at": contract.due_at,
                "returned_at": contract.returned_at,
                "contract_status": contract.status,
                "usage_snapshot_json": dict(contract.usage_snapshot_json or {}),
            }
        )
        return payload

    def _append_card_history(self, player_card_id: str, event_type: str, actor_user_id: str | None, *, metadata: dict[str, Any] | None = None) -> None:
        self.session.add(
            PlayerCardHistory(
                player_card_id=player_card_id,
                event_type=event_type,
                description=None,
                delta_supply=0,
                delta_available=0,
                actor_user_id=actor_user_id,
                metadata_json=metadata or {},
            )
        )

    def _append_owner_history(
        self,
        player_card_id: str,
        *,
        from_user_id: str | None,
        to_user_id: str | None,
        quantity: int,
        event_type: str,
        reference_id: str | None,
    ) -> None:
        self.session.add(
            PlayerCardOwnerHistory(
                player_card_id=player_card_id,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                quantity=quantity,
                event_type=event_type,
                reference_id=reference_id,
                metadata_json={"temporary_access": True},
            )
        )

    def _get_card(self, player_card_id: str) -> PlayerCard:
        card = self.session.get(PlayerCard, player_card_id)
        if card is None:
            raise PlayerCardNotFoundError("Player card was not found.")
        return card

    def _get_listing(self, listing_id: str) -> CardLoanListing:
        listing = self.session.get(CardLoanListing, listing_id)
        if listing is None:
            raise PlayerCardNotFoundError("Card loan listing was not found.")
        return listing

    def _get_contract(self, contract_id: str) -> CardLoanContract:
        contract = self.session.get(CardLoanContract, contract_id)
        if contract is None:
            raise PlayerCardNotFoundError("Card loan contract was not found.")
        return contract

    def _get_holding(self, user_id: str, player_card_id: str) -> PlayerCardHolding:
        holding = self.session.scalar(
            select(PlayerCardHolding).where(
                PlayerCardHolding.owner_user_id == user_id,
                PlayerCardHolding.player_card_id == player_card_id,
            )
        )
        if holding is None:
            raise PlayerCardValidationError("You do not own that player card.")
        return holding

    def _get_player(self, player_id: str) -> Player:
        player = self.session.get(Player, player_id)
        if player is None:
            raise PlayerCardNotFoundError("Player was not found.")
        return player

    def _get_tier(self, tier_id: str) -> PlayerCardTier:
        tier = self.session.get(PlayerCardTier, tier_id)
        if tier is None:
            raise PlayerCardNotFoundError("Player card tier was not found.")
        return tier

    @staticmethod
    def _normalize_amount(amount: Decimal | Any) -> Decimal:
        return Decimal(str(amount)).quantize(Decimal("0.0001"))


@dataclass(slots=True)
class StarterSquadRentalService:
    session: Session
    settings: Settings = field(default_factory=get_settings)
    wallet_service: WalletService = field(default_factory=WalletService)
    engine: RegenGenerationEngine | None = None

    def __post_init__(self) -> None:
        if self.engine is None:
            self.engine = RegenGenerationEngine(self.settings)

    def create_rental(
        self,
        *,
        actor: User,
        club_id: str | None = None,
        include_academy: bool = True,
        first_team_count: int = 18,
        academy_count: int = 18,
        term_days: int = DEFAULT_STARTER_RENTAL_TERM_DAYS,
        rental_fee_credits: Decimal = DEFAULT_STARTER_RENTAL_FEE,
    ) -> dict[str, Any]:
        if first_team_count <= 0:
            raise PlayerCardValidationError("Starter squad rentals require at least one first-team player.")
        if academy_count < 0:
            raise PlayerCardValidationError("Academy player count cannot be negative.")
        self._ensure_user_is_eligible(actor.id)

        if rental_fee_credits > Decimal("0"):
            user_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.CREDIT)
            platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.CREDIT)
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(account=user_account, amount=-self._normalize_amount(rental_fee_credits)),
                    LedgerPosting(account=platform_account, amount=self._normalize_amount(rental_fee_credits)),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                reference=f"starter-rental:{actor.id}:{utcnow().timestamp()}",
                description="Starter squad rental onboarding fee",
                actor=actor,
            )

        now = datetime.now(UTC)
        club_context = self._club_context(club_id)
        team_bundle = self.engine.generate_starter_regens(
            club_id=club_id or f"starter-rental:{actor.id}",
            season_label=str(now.year),
            club_context=club_context,
            count=first_team_count,
            used_names=set(),
        )

        academy_bundle = None
        resolved_academy_count = academy_count if include_academy else 0
        if include_academy and academy_count > 0:
            academy_bundle = self.engine.generate_academy_intake(
                club_id=club_id or f"starter-rental:{actor.id}",
                season_label=str(now.year),
                club_context=club_context,
                intake_size=academy_count,
                used_names={item.display_name for item in team_bundle.regens},
            )

        rental = StarterSquadRental(
            user_id=actor.id,
            club_id=club_id,
            status="active",
            rental_fee_credits=self._normalize_amount(rental_fee_credits),
            currency=LedgerUnit.CREDIT.value,
            term_days=term_days,
            starts_at=now,
            ends_at=now + timedelta(days=term_days),
            first_team_count=first_team_count,
            academy_count=resolved_academy_count,
            is_non_tradable=True,
            roster_json=[self._rental_player_payload(item, squad_scope="first_team") for item in team_bundle.regens],
            academy_roster_json=[
                self._rental_player_payload(item, squad_scope="academy") for item in (academy_bundle.regens if academy_bundle is not None else ())
            ],
            metadata_json={
                "starter_badge": "starter_rental",
                "transition_paths": ["market_purchase", "loan_market", "scouting", "development"],
                "club_id": club_id,
            },
        )
        self.session.add(rental)
        self.session.flush()
        return self._rental_payload(rental)

    def get_active_rental(self, *, actor: User) -> dict[str, Any] | None:
        self.expire_due_rentals()
        rental = self.session.scalar(
            select(StarterSquadRental)
            .where(StarterSquadRental.user_id == actor.id, StarterSquadRental.status == "active")
            .order_by(StarterSquadRental.created_at.desc())
        )
        return None if rental is None else self._rental_payload(rental)

    def expire_due_rentals(self) -> int:
        now = datetime.now(UTC)
        rentals = list(
            self.session.scalars(
                select(StarterSquadRental).where(StarterSquadRental.status == "active", StarterSquadRental.ends_at <= now)
            ).all()
        )
        for rental in rentals:
            rental.status = "expired"
        return len(rentals)

    def _ensure_user_is_eligible(self, user_id: str) -> None:
        active_rental = self.session.scalar(
            select(func.count(StarterSquadRental.id)).where(
                StarterSquadRental.user_id == user_id,
                StarterSquadRental.status == "active",
            )
        ) or 0
        if active_rental > 0:
            raise PlayerCardValidationError("You already have an active starter squad rental.")

        permanent_cards = self.session.scalar(
            select(func.count(PlayerCardHolding.id)).where(
                PlayerCardHolding.owner_user_id == user_id,
                PlayerCardHolding.quantity_total > 0,
            )
        ) or 0
        if permanent_cards > 0:
            raise PlayerCardValidationError("Starter squad rentals are only available before you own permanent player cards.")

    def _club_context(self, club_id: str | None) -> RegenClubContext:
        if not club_id:
            return RegenClubContext(first_team_gsi=52.0, club_reputation=10.0, academy_level=45.0, academy_investment=35.0)

        club = self.session.get(ClubProfile, club_id)
        facilities = self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club_id))
        reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club_id))
        return RegenClubContext(
            country_code=club.country_code if club is not None else None,
            region_name=club.region_name if club is not None else None,
            city_name=club.city_name if club is not None else None,
            training_level=float((facilities.training_level if facilities is not None else 2) * 18),
            academy_level=float((facilities.academy_level if facilities is not None else 2) * 18),
            academy_investment=float((facilities.academy_level if facilities is not None else 2) * 14),
            first_team_gsi=52.0,
            club_reputation=float(reputation.current_score if reputation is not None else 10),
        )

    def _rental_player_payload(self, item: Any, *, squad_scope: str) -> dict[str, Any]:
        potential = getattr(item, "potential_range", None)
        return {
            "rental_player_id": item.regen_id,
            "player_name": item.display_name,
            "primary_position": item.primary_position,
            "secondary_positions": list(item.secondary_positions),
            "current_gsi": item.current_gsi,
            "locked_gsi": item.current_gsi,
            "potential_maximum": getattr(potential, "maximum", item.current_gsi),
            "status": "starter_rental",
            "starter_badge": "starter_rental",
            "non_tradable": True,
            "ownership_type": "rental",
            "squad_scope": squad_scope,
        }

    def _rental_payload(self, rental: StarterSquadRental) -> dict[str, Any]:
        return {
            "starter_rental_id": rental.id,
            "user_id": rental.user_id,
            "club_id": rental.club_id,
            "status": rental.status,
            "rental_fee_credits": float(self._normalize_amount(rental.rental_fee_credits)),
            "currency": rental.currency,
            "term_days": rental.term_days,
            "starts_at": rental.starts_at,
            "ends_at": rental.ends_at,
            "first_team_count": rental.first_team_count,
            "academy_count": rental.academy_count,
            "is_non_tradable": rental.is_non_tradable,
            "roster": list(rental.roster_json or []),
            "academy_roster": list(rental.academy_roster_json or []),
            "metadata_json": dict(rental.metadata_json or {}),
            "created_at": rental.created_at,
        }

    @staticmethod
    def _normalize_amount(amount: Decimal | Any) -> Decimal:
        return Decimal(str(amount)).quantize(Decimal("0.0001"))


__all__ = ["CardLoanService", "StarterSquadRentalService", "CardLoanError", "StarterRentalError", "InsufficientBalanceError"]
