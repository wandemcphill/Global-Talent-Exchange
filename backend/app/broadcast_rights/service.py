from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.club_finance.service import ClubFinanceService
from app.models.base import generate_uuid
from app.models.broadcast_rights import (
    BroadcastAccessGrant,
    BroadcastRevenueDistribution,
    BroadcastRight,
    BroadcastRightsAuction,
    BroadcastRightsBid,
    ViewSession,
)
from app.models.club_profile import ClubProfile
from app.models.competition import Competition
from app.models.competition_match import CompetitionMatch
from app.models.media_engine import MatchView, PremiumVideoPurchase
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

PLATFORM_OWNER_ID = "platform"
DECIMAL_QUANTUM = Decimal("0.0001")
DEFAULT_PLATFORM_SHARE_PERCENTAGE = Decimal("20.00")
NON_EXCLUSIVE_SHARE_CAP = Decimal("80.00")
BASE_AD_REVENUE_PER_VIEW = Decimal("0.0100")
STADIUM_AD_BONUS_PER_VIEW = Decimal("0.0050")
SPONSORED_OVERLAY_BONUS_PER_VIEW = Decimal("0.0100")
PREMIUM_FEATURE_BONUS_PER_VIEW = Decimal("0.0025")


class BroadcastRightsError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(slots=True)
class BroadcastRightsService:
    session: Session
    wallet_service: WalletService = field(default_factory=WalletService)

    def get_summary(self, competition_id: str, *, as_of: date | None = None) -> dict[str, Any]:
        competition = self._require_competition(competition_id)
        rights = self._active_rights_for_competition(competition_id, as_of=as_of)
        auctions = list(
            self.session.scalars(
                select(BroadcastRightsAuction)
                .where(BroadcastRightsAuction.competition_id == competition_id)
                .order_by(BroadcastRightsAuction.created_at.desc())
            ).all()
        )
        return {
            "competition": competition,
            "rights": rights,
            "auctions": auctions,
            "revenue_generated": self._competition_revenue(competition_id),
            "viewers": self._competition_viewers(competition_id),
        }

    def acquire_rights(self, *, actor: User, competition_id: str, payload) -> BroadcastRight:
        competition = self._require_competition(competition_id)
        self._validate_right_window(payload.start_date, payload.end_date)
        self._validate_new_right(
            competition_id=competition.id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            exclusivity=payload.exclusivity,
            revenue_share_percentage=Decimal(payload.revenue_share_percentage),
        )
        price = Decimal(payload.acquisition_price).quantize(DECIMAL_QUANTUM)
        try:
            self.wallet_service.settle_available_funds(
                self.session,
                user=actor,
                amount=price,
                reference=f"broadcast-rights:{competition.id}:acquire",
                description=f"Broadcast rights purchase for {competition.name}",
                external_reference=competition.id,
                unit=LedgerUnit.COIN,
                source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            )
        except InsufficientBalanceError as exc:
            raise BroadcastRightsError("Insufficient GTex Coin balance to acquire broadcast rights.") from exc
        item = BroadcastRight(
            competition_id=competition.id,
            owner_id=actor.id,
            acquisition_price=price,
            revenue_share_percentage=Decimal(payload.revenue_share_percentage),
            exclusivity=payload.exclusivity,
            start_date=payload.start_date,
            end_date=payload.end_date,
            metadata_json=self._right_metadata(payload),
        )
        self.session.add(item)
        self.session.flush()
        self._notify(
            user_id=actor.id,
            topic="broadcast_rights",
            template_key="BROADCAST_RIGHTS_WON",
            resource_type="broadcast_right",
            resource_id=item.id,
            message=f"You acquired broadcast rights for {competition.name}.",
            metadata={"competition_id": competition.id, "acquisition_price": str(price)},
        )
        return item

    def create_auction(self, *, actor: User, competition_id: str, payload) -> BroadcastRightsAuction:
        competition = self._require_competition(competition_id)
        self._validate_right_window(payload.start_date, payload.end_date)
        self._validate_new_right(
            competition_id=competition.id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            exclusivity=payload.exclusivity,
            revenue_share_percentage=Decimal(payload.revenue_share_percentage),
        )
        if payload.ends_at <= datetime.now(UTC):
            raise BroadcastRightsError("Auction end time must be in the future.")
        existing = self.session.scalar(
            select(BroadcastRightsAuction).where(
                BroadcastRightsAuction.competition_id == competition.id,
                BroadcastRightsAuction.status == "open",
            )
        )
        if existing is not None:
            raise BroadcastRightsError("An active broadcast-rights auction already exists.")
        item = BroadcastRightsAuction(
            competition_id=competition.id,
            seller_owner_id=actor.id,
            reserve_price=Decimal(payload.reserve_price).quantize(DECIMAL_QUANTUM),
            revenue_share_percentage=Decimal(payload.revenue_share_percentage),
            exclusivity=payload.exclusivity,
            start_date=payload.start_date,
            end_date=payload.end_date,
            starts_at=datetime.now(UTC),
            ends_at=payload.ends_at,
            metadata_json=self._right_metadata(payload),
        )
        self.session.add(item)
        self.session.flush()
        return item

    def place_bid(self, *, actor: User, auction_id: str, payload) -> BroadcastRightsBid:
        auction = self.session.get(BroadcastRightsAuction, auction_id)
        if auction is None:
            raise BroadcastRightsError("Broadcast rights auction was not found.")
        if auction.status != "open" or auction.ends_at <= datetime.now(UTC):
            raise BroadcastRightsError("Broadcast rights auction is no longer open.")
        if auction.seller_owner_id == actor.id and auction.seller_owner_id != PLATFORM_OWNER_ID:
            raise BroadcastRightsError("You cannot bid on your own broadcast-rights auction.")
        amount = Decimal(payload.amount).quantize(DECIMAL_QUANTUM)
        if amount < Decimal(auction.reserve_price):
            raise BroadcastRightsError("Bid amount must meet the reserve price.")
        balance = self.wallet_service.get_wallet_summary(self.session, actor, currency=LedgerUnit.COIN).available_balance
        if balance < amount:
            raise BroadcastRightsError("Insufficient GTex Coin balance for this auction bid.")
        item = self.session.scalar(
            select(BroadcastRightsBid).where(
                BroadcastRightsBid.auction_id == auction.id,
                BroadcastRightsBid.bidder_user_id == actor.id,
            )
        )
        if item is None:
            item = BroadcastRightsBid(
                auction_id=auction.id,
                bidder_user_id=actor.id,
                amount=amount,
                status="submitted",
                metadata_json={"balance_snapshot": str(balance)},
            )
            self.session.add(item)
        else:
            item.amount = amount
            item.status = "submitted"
            item.metadata_json = {**dict(item.metadata_json or {}), "balance_snapshot": str(balance)}
        self.session.flush()
        return item

    def grant_access(self, *, actor: User, right_id: str, payload) -> BroadcastAccessGrant:
        right = self.session.get(BroadcastRight, right_id)
        if right is None:
            raise BroadcastRightsError("Broadcast right was not found.")
        if right.owner_id != actor.id:
            raise BroadcastRightsError("Only the rights holder can grant stream access.")
        item = self.session.scalar(
            select(BroadcastAccessGrant).where(
                BroadcastAccessGrant.broadcast_right_id == right.id,
                BroadcastAccessGrant.user_id == payload.user_id,
            )
        )
        if item is None:
            item = BroadcastAccessGrant(
                broadcast_right_id=right.id,
                user_id=payload.user_id,
                granted_by_user_id=actor.id,
                expires_at=payload.expires_at,
                metadata_json={},
            )
            self.session.add(item)
        else:
            item.granted_by_user_id = actor.id
            item.expires_at = payload.expires_at
        self.session.flush()
        return item

    def resolve_match_access(
        self,
        *,
        actor: User,
        match_id: str,
        competition_id: str | None = None,
        pay_to_view: bool = False,
    ) -> dict[str, Any]:
        context = self._match_context(match_id=match_id, competition_id=competition_id)
        rights = self._active_rights_for_competition(context["competition_id"], as_of=context["reference_date"])
        enhancement = self._match_enhancement_payload(rights)
        if not rights:
            return {
                "match_id": match_id,
                "competition_id": context["competition_id"],
                "has_access": True,
                "access_source": "open",
                "requires_payment": False,
                **enhancement,
                "rights_owner_id": None,
            }
        if any(item.owner_id == actor.id for item in rights):
            return {
                "match_id": match_id,
                "competition_id": context["competition_id"],
                "has_access": True,
                "access_source": "rights_owner",
                "requires_payment": False,
                **enhancement,
                "rights_owner_id": rights[0].owner_id,
            }
        if self._active_grant(right_ids=[item.id for item in rights], user_id=actor.id) is not None:
            return {
                "match_id": match_id,
                "competition_id": context["competition_id"],
                "has_access": True,
                "access_source": "grant",
                "requires_payment": False,
                **enhancement,
                "rights_owner_id": rights[0].owner_id,
            }
        existing_view = self.session.scalar(
            select(ViewSession).where(ViewSession.match_id == match_id, ViewSession.user_id == actor.id)
        )
        if existing_view is not None and Decimal(existing_view.paid_amount) > Decimal("0.0000"):
            return {
                "match_id": match_id,
                "competition_id": context["competition_id"],
                "has_access": True,
                "access_source": "paid_view",
                "requires_payment": False,
                **enhancement,
                "rights_owner_id": rights[0].owner_id,
            }
        if not enhancement["exclusive"]:
            return {
                "match_id": match_id,
                "competition_id": context["competition_id"],
                "has_access": True,
                "access_source": "non_exclusive",
                "requires_payment": False,
                **enhancement,
                "rights_owner_id": rights[0].owner_id,
            }
        if pay_to_view:
            if enhancement["viewing_fee_coin"] > Decimal("0.0000"):
                self._charge_view_fee(
                    actor=actor,
                    match_id=match_id,
                    amount=enhancement["viewing_fee_coin"],
                )
            self.record_view_session(
                actor=actor,
                match_id=match_id,
                competition_id=context["competition_id"],
                paid_amount=enhancement["viewing_fee_coin"],
                source="spectate_fee",
            )
            return {
                "match_id": match_id,
                "competition_id": context["competition_id"],
                "has_access": True,
                "access_source": "paid_view",
                "requires_payment": False,
                **enhancement,
                "rights_owner_id": rights[0].owner_id,
            }
        return {
            "match_id": match_id,
            "competition_id": context["competition_id"],
            "has_access": False,
            "access_source": None,
            "requires_payment": enhancement["viewing_fee_coin"] > Decimal("0.0000"),
            **enhancement,
            "rights_owner_id": rights[0].owner_id,
        }

    def record_view_session(
        self,
        *,
        actor: User,
        match_id: str,
        competition_id: str | None,
        paid_amount: Decimal,
        source: str,
    ) -> ViewSession:
        amount = Decimal(paid_amount).quantize(DECIMAL_QUANTUM)
        context = self._match_context(match_id=match_id, competition_id=competition_id)
        item = self.session.scalar(
            select(ViewSession).where(ViewSession.match_id == match_id, ViewSession.user_id == actor.id)
        )
        if item is None:
            item = ViewSession(
                user_id=actor.id,
                match_id=match_id,
                competition_id=context["competition_id"],
                paid_amount=amount,
                metadata_json={"sources": [source]},
            )
            self.session.add(item)
        else:
            item.paid_amount = (Decimal(item.paid_amount) + amount).quantize(DECIMAL_QUANTUM)
            sources = list((item.metadata_json or {}).get("sources", []))
            if source not in sources:
                sources.append(source)
            item.metadata_json = {**dict(item.metadata_json or {}), "sources": sources}
            if item.competition_id is None:
                item.competition_id = context["competition_id"]
        self.session.flush()
        return item

    def get_match_enhancements(self, *, match_id: str, competition_id: str | None = None) -> dict[str, Any]:
        context = self._match_context(match_id=match_id, competition_id=competition_id)
        rights = self._active_rights_for_competition(context["competition_id"], as_of=context["reference_date"])
        enhancement = self._match_enhancement_payload(rights)
        return {
            "competition_id": context["competition_id"],
            "rights_owner_id": rights[0].owner_id if rights else None,
            **enhancement,
        }

    def distribute_match_revenue(
        self,
        *,
        match_id: str,
        competition_id: str | None = None,
        home_club_id: str | None = None,
        away_club_id: str | None = None,
    ) -> dict[str, Any]:
        context = self._match_context(
            match_id=match_id,
            competition_id=competition_id,
            home_club_id=home_club_id,
            away_club_id=away_club_id,
        )
        totals = self._match_revenue_totals(
            match_id=match_id,
            competition_id=context["competition_id"],
            reference_date=context["reference_date"],
        )
        targets = self._distribution_targets(
            match_id=match_id,
            competition_id=context["competition_id"],
            home_club_id=context["home_club_id"],
            away_club_id=context["away_club_id"],
            total_revenue=totals["total_revenue"],
            rights=totals["rights"],
        )
        existing: dict[tuple[str, str, str | None], Decimal] = {}
        rows = list(
            self.session.scalars(
                select(BroadcastRevenueDistribution).where(BroadcastRevenueDistribution.match_id == match_id)
            ).all()
        )
        for row in rows:
            key = (row.recipient_type, row.recipient_id, row.broadcast_right_id)
            existing[key] = (existing.get(key, Decimal("0.0000")) + Decimal(row.amount)).quantize(DECIMAL_QUANTUM)
        for target in targets:
            key = (target["recipient_type"], target["recipient_id"], target.get("broadcast_right_id"))
            delta = (Decimal(target["amount"]) - existing.get(key, Decimal("0.0000"))).quantize(DECIMAL_QUANTUM)
            if delta <= Decimal("0.0000"):
                continue
            row = BroadcastRevenueDistribution(
                match_id=match_id,
                competition_id=context["competition_id"],
                broadcast_right_id=target.get("broadcast_right_id"),
                recipient_type=target["recipient_type"],
                recipient_id=target["recipient_id"],
                amount=delta,
                reference_key=f"broadcast:{match_id}:{generate_uuid()}",
                metadata_json=dict(target["metadata"]),
            )
            self.session.add(row)
            existing[key] = (existing.get(key, Decimal("0.0000")) + delta).quantize(DECIMAL_QUANTUM)
            self._record_recipient_finance(row=row, target=target)
        self.session.flush()
        recipients: list[dict[str, Any]] = []
        rights_holder_share = Decimal("0.0000")
        platform_share = Decimal("0.0000")
        participating_club_share = Decimal("0.0000")
        for target in targets:
            key = (target["recipient_type"], target["recipient_id"], target.get("broadcast_right_id"))
            amount = existing.get(key, Decimal("0.0000")).quantize(DECIMAL_QUANTUM)
            payload = {"recipient_type": target["recipient_type"], "recipient_id": target["recipient_id"], "amount": amount}
            payload.update(dict(target["metadata"]))
            recipients.append(payload)
            if target["recipient_type"] == "rights_holder":
                rights_holder_share += amount
            elif target["recipient_type"] == "platform":
                platform_share += amount
            elif target["recipient_type"] == "club":
                participating_club_share += amount
        return {
            "match_id": match_id,
            "competition_id": context["competition_id"],
            "total_revenue": totals["total_revenue"],
            "rights_holder_share": rights_holder_share.quantize(DECIMAL_QUANTUM),
            "platform_share": platform_share.quantize(DECIMAL_QUANTUM),
            "participating_club_share": participating_club_share.quantize(DECIMAL_QUANTUM),
            "recipients": recipients,
        }

    def run_revenue_distribution_cycle(self) -> dict[str, int]:
        processed_matches = 0
        match_ids = {
            value
            for value in self.session.scalars(select(ViewSession.match_id)).all()
            if isinstance(value, str) and value
        }
        for match_id in sorted(match_ids):
            self.distribute_match_revenue(match_id=match_id)
            processed_matches += 1
        settled_auctions = self.settle_ended_auctions()
        return {"processed_matches": processed_matches, "settled_auctions": settled_auctions}

    def expire_rights_and_relist(self, *, as_of: date | None = None) -> dict[str, int]:
        reference_date = as_of or datetime.now(UTC).date()
        expired_rights = 0
        relisted_auctions = 0
        for right in self.session.scalars(select(BroadcastRight).where(BroadcastRight.end_date < reference_date)).all():
            metadata = dict(right.metadata_json or {})
            if metadata.get("expiration_processed_at") is not None:
                continue
            metadata["expiration_processed_at"] = datetime.now(UTC).isoformat()
            metadata["status"] = "expired"
            right.metadata_json = metadata
            expired_rights += 1
            open_auction = self.session.scalar(
                select(BroadcastRightsAuction).where(
                    BroadcastRightsAuction.competition_id == right.competition_id,
                    BroadcastRightsAuction.status == "open",
                )
            )
            if open_auction is not None:
                continue
            self.session.add(
                BroadcastRightsAuction(
                    competition_id=right.competition_id,
                    seller_owner_id=PLATFORM_OWNER_ID,
                    reserve_price=Decimal(right.acquisition_price).quantize(DECIMAL_QUANTUM),
                    revenue_share_percentage=Decimal(right.revenue_share_percentage),
                    exclusivity=bool(right.exclusivity),
                    start_date=reference_date,
                    end_date=reference_date + timedelta(days=30),
                    starts_at=datetime.now(UTC),
                    ends_at=datetime.now(UTC) + timedelta(days=2),
                    status="open",
                    metadata_json=dict(right.metadata_json or {}),
                )
            )
            relisted_auctions += 1
        self.session.flush()
        return {"expired_rights": expired_rights, "relisted_auctions": relisted_auctions}

    def settle_ended_auctions(self) -> int:
        settled_auctions = 0
        auctions = list(
            self.session.scalars(
                select(BroadcastRightsAuction).where(
                    BroadcastRightsAuction.status == "open",
                    BroadcastRightsAuction.ends_at <= datetime.now(UTC),
                )
            ).all()
        )
        for auction in auctions:
            bids = list(
                self.session.scalars(
                    select(BroadcastRightsBid)
                    .where(BroadcastRightsBid.auction_id == auction.id)
                    .order_by(BroadcastRightsBid.amount.desc(), BroadcastRightsBid.created_at.asc())
                ).all()
            )
            winning_bid = next((bid for bid in bids if Decimal(bid.amount) >= Decimal(auction.reserve_price)), None)
            if winning_bid is None:
                auction.status = "closed_unsold"
                for bid in bids:
                    bid.status = "outbid"
                continue
            try:
                self._validate_new_right(
                    competition_id=auction.competition_id,
                    start_date=auction.start_date,
                    end_date=auction.end_date,
                    exclusivity=bool(auction.exclusivity),
                    revenue_share_percentage=Decimal(auction.revenue_share_percentage),
                )
            except BroadcastRightsError:
                winning_bid.status = "invalid"
                auction.status = "closed_conflict"
                for bid in bids:
                    if bid.id != winning_bid.id:
                        bid.status = "outbid"
                continue
            winner = self.session.get(User, winning_bid.bidder_user_id)
            if winner is None:
                winning_bid.status = "invalid"
                auction.status = "closed_unsold"
                continue
            try:
                self.wallet_service.settle_available_funds(
                    self.session,
                    user=winner,
                    amount=Decimal(winning_bid.amount).quantize(DECIMAL_QUANTUM),
                    reference=f"broadcast-auction:{auction.id}",
                    description="Broadcast rights auction settlement",
                    external_reference=auction.id,
                    unit=LedgerUnit.COIN,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                )
            except InsufficientBalanceError:
                winning_bid.status = "payment_failed"
                auction.status = "closed_unsold"
                continue
            seller = self.session.get(User, auction.seller_owner_id) if auction.seller_owner_id != PLATFORM_OWNER_ID else None
            if seller is not None and seller.id != winner.id:
                self.wallet_service.credit_trade_proceeds(
                    self.session,
                    user=seller,
                    amount=Decimal(winning_bid.amount).quantize(DECIMAL_QUANTUM),
                    reference=f"broadcast-auction-proceeds:{auction.id}",
                    description="Broadcast rights auction proceeds",
                    external_reference=auction.id,
                    unit=LedgerUnit.COIN,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                )
            right = BroadcastRight(
                competition_id=auction.competition_id,
                owner_id=winning_bid.bidder_user_id,
                acquisition_price=Decimal(winning_bid.amount).quantize(DECIMAL_QUANTUM),
                revenue_share_percentage=Decimal(auction.revenue_share_percentage),
                exclusivity=bool(auction.exclusivity),
                start_date=auction.start_date,
                end_date=auction.end_date,
                metadata_json=dict(auction.metadata_json or {}),
            )
            self.session.add(right)
            self.session.flush()
            auction.status = "settled"
            auction.winning_right_id = right.id
            winning_bid.status = "winning"
            for bid in bids:
                if bid.id != winning_bid.id:
                    bid.status = "outbid"
            self._notify(
                user_id=winner.id,
                topic="broadcast_rights",
                template_key="BROADCAST_RIGHTS_WON",
                resource_type="broadcast_right",
                resource_id=right.id,
                message="You won a broadcast-rights auction.",
                metadata={"competition_id": auction.competition_id, "auction_id": auction.id},
            )
            settled_auctions += 1
        self.session.flush()
        return settled_auctions

    def _record_recipient_finance(self, *, row: BroadcastRevenueDistribution, target: dict[str, Any]) -> None:
        user_id: str | None = None
        if target["recipient_type"] == "rights_holder" and target["recipient_id"] != PLATFORM_OWNER_ID:
            user_id = target["recipient_id"]
        elif target["recipient_type"] == "club":
            user_id = target["metadata"].get("owner_user_id")
        if user_id is None:
            return
        amount = Decimal(row.amount).quantize(DECIMAL_QUANTUM)
        ClubFinanceService(self.session).record_broadcast_distribution(
            user_id=user_id,
            amount=amount,
            reference_key=row.reference_key,
            metadata={
                "match_id": row.match_id,
                "competition_id": row.competition_id,
                "recipient_type": target["recipient_type"],
                **dict(target["metadata"]),
            },
        )
        self._notify(
            user_id=user_id,
            topic="broadcast_rights",
            template_key="VIEWING_REVENUE_EARNED",
            resource_type="broadcast_distribution",
            resource_id=row.id,
            message=f"Broadcast revenue earned: {amount} GTex Coin.",
            metadata={"amount": str(amount), **dict(target["metadata"])},
        )

    def _distribution_targets(
        self,
        *,
        match_id: str,
        competition_id: str | None,
        home_club_id: str | None,
        away_club_id: str | None,
        total_revenue: Decimal,
        rights: list[BroadcastRight],
    ) -> list[dict[str, Any]]:
        total = Decimal(total_revenue).quantize(DECIMAL_QUANTUM)
        if total <= Decimal("0.0000"):
            return []
        targets: list[dict[str, Any]] = []
        total_rights_pct = sum((Decimal(item.revenue_share_percentage) for item in rights), Decimal("0.00"))
        platform_pct = min(DEFAULT_PLATFORM_SHARE_PERCENTAGE, max(Decimal("0.00"), Decimal("100.00") - total_rights_pct))
        for item in rights:
            amount = (total * Decimal(item.revenue_share_percentage) / Decimal("100.00")).quantize(DECIMAL_QUANTUM)
            targets.append(
                {
                    "recipient_type": "rights_holder",
                    "recipient_id": item.owner_id,
                    "broadcast_right_id": item.id,
                    "amount": amount,
                    "metadata": {"owner_id": item.owner_id, "competition_id": competition_id, "match_id": match_id},
                }
            )
        targets.append(
            {
                "recipient_type": "platform",
                "recipient_id": PLATFORM_OWNER_ID,
                "broadcast_right_id": None,
                "amount": (total * platform_pct / Decimal("100.00")).quantize(DECIMAL_QUANTUM),
                "metadata": {"competition_id": competition_id, "match_id": match_id},
            }
        )
        club_ids = [club_id for club_id in (home_club_id, away_club_id) if club_id]
        remaining = (total - sum((Decimal(item["amount"]) for item in targets), Decimal("0.0000"))).quantize(DECIMAL_QUANTUM)
        if club_ids and remaining > Decimal("0.0000"):
            distributed = Decimal("0.0000")
            for index, club_id in enumerate(club_ids):
                if index == len(club_ids) - 1:
                    amount = (remaining - distributed).quantize(DECIMAL_QUANTUM)
                else:
                    amount = (remaining / Decimal(len(club_ids))).quantize(DECIMAL_QUANTUM)
                    distributed = (distributed + amount).quantize(DECIMAL_QUANTUM)
                targets.append(
                    {
                        "recipient_type": "club",
                        "recipient_id": club_id,
                        "broadcast_right_id": None,
                        "amount": amount,
                        "metadata": {
                            "club_id": club_id,
                            "owner_user_id": self._club_owner_id(club_id),
                            "competition_id": competition_id,
                            "match_id": match_id,
                        },
                    }
                )
        return targets

    def _match_revenue_totals(self, *, match_id: str, competition_id: str | None, reference_date: date) -> dict[str, Any]:
        rights = self._active_rights_for_competition(competition_id, as_of=reference_date)
        enhancement = self._match_enhancement_payload(rights)
        match_view_count = int(
            self.session.scalar(select(func.count()).select_from(MatchView).where(MatchView.match_key == match_id)) or 0
        )
        paid_view_count = int(
            self.session.scalar(select(func.count()).select_from(ViewSession).where(ViewSession.match_id == match_id)) or 0
        )
        viewers = max(match_view_count, paid_view_count)
        premium_revenue = Decimal(
            self.session.scalar(
                select(func.coalesce(func.sum(PremiumVideoPurchase.price_coin), 0)).where(
                    PremiumVideoPurchase.match_key == match_id
                )
            )
            or Decimal("0.0000")
        ).quantize(DECIMAL_QUANTUM)
        paid_view_revenue = Decimal(
            self.session.scalar(
                select(func.coalesce(func.sum(ViewSession.paid_amount), 0)).where(ViewSession.match_id == match_id)
            )
            or Decimal("0.0000")
        ).quantize(DECIMAL_QUANTUM)
        base_ad = (Decimal(viewers) * BASE_AD_REVENUE_PER_VIEW).quantize(DECIMAL_QUANTUM)
        enhancement_rate = (
            Decimal(len(enhancement["stadium_ads"])) * STADIUM_AD_BONUS_PER_VIEW
            + Decimal(len(enhancement["sponsored_overlays"])) * SPONSORED_OVERLAY_BONUS_PER_VIEW
            + Decimal(sum(1 for enabled in enhancement["premium_features"].values() if enabled)) * PREMIUM_FEATURE_BONUS_PER_VIEW
        )
        enhancement_revenue = (Decimal(viewers) * enhancement_rate).quantize(DECIMAL_QUANTUM)
        return {
            "rights": rights,
            "total_revenue": (premium_revenue + paid_view_revenue + base_ad + enhancement_revenue).quantize(DECIMAL_QUANTUM),
        }

    def _competition_revenue(self, competition_id: str) -> Decimal:
        value = self.session.scalar(
            select(func.coalesce(func.sum(BroadcastRevenueDistribution.amount), 0)).where(
                BroadcastRevenueDistribution.competition_id == competition_id
            )
        )
        return Decimal(value or 0).quantize(DECIMAL_QUANTUM)

    def _competition_viewers(self, competition_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(ViewSession).where(ViewSession.competition_id == competition_id)
            )
            or 0
        )

    def _active_rights_for_competition(self, competition_id: str | None, *, as_of: date | None = None) -> list[BroadcastRight]:
        if not competition_id:
            return []
        reference_date = as_of or datetime.now(UTC).date()
        return list(
            self.session.scalars(
                select(BroadcastRight)
                .where(
                    BroadcastRight.competition_id == competition_id,
                    BroadcastRight.start_date <= reference_date,
                    BroadcastRight.end_date >= reference_date,
                )
                .order_by(BroadcastRight.exclusivity.desc(), BroadcastRight.created_at.asc())
            ).all()
        )

    def _active_grant(self, *, right_ids: list[str], user_id: str) -> BroadcastAccessGrant | None:
        if not right_ids:
            return None
        now = datetime.now(UTC)
        return self.session.scalar(
            select(BroadcastAccessGrant).where(
                BroadcastAccessGrant.broadcast_right_id.in_(right_ids),
                BroadcastAccessGrant.user_id == user_id,
                (BroadcastAccessGrant.expires_at.is_(None)) | (BroadcastAccessGrant.expires_at >= now),
            )
        )

    def _match_context(
        self,
        *,
        match_id: str,
        competition_id: str | None = None,
        home_club_id: str | None = None,
        away_club_id: str | None = None,
    ) -> dict[str, Any]:
        match = self.session.get(CompetitionMatch, match_id)
        if match is None:
            return {
                "competition_id": competition_id,
                "home_club_id": home_club_id,
                "away_club_id": away_club_id,
                "reference_date": datetime.now(UTC).date(),
            }
        reference_date = match.match_date
        if reference_date is None and match.completed_at is not None:
            reference_date = match.completed_at.astimezone(UTC).date()
        return {
            "competition_id": competition_id or match.competition_id,
            "home_club_id": home_club_id or match.home_club_id,
            "away_club_id": away_club_id or match.away_club_id,
            "reference_date": reference_date or datetime.now(UTC).date(),
        }

    @staticmethod
    def _match_enhancement_payload(rights: list[BroadcastRight]) -> dict[str, Any]:
        premium_features: dict[str, bool] = {}
        sponsored_overlays: list[dict[str, Any]] = []
        stadium_ads: list[dict[str, Any]] = []
        viewing_fee_coin = Decimal("0.0000")
        for right in rights:
            metadata = dict(right.metadata_json or {})
            premium_features.update({str(key): bool(value) for key, value in dict(metadata.get("premium_features") or {}).items()})
            sponsored_overlays.extend(list(metadata.get("sponsored_overlays") or []))
            stadium_ads.extend(list(metadata.get("ad_inventory") or []))
            viewing_fee_coin = max(
                viewing_fee_coin,
                Decimal(str(metadata.get("viewing_fee_coin", "0.0000"))).quantize(DECIMAL_QUANTUM),
            )
        return {
            "exclusive": any(item.exclusivity for item in rights),
            "premium_features": premium_features,
            "sponsored_overlays": sponsored_overlays,
            "stadium_ads": stadium_ads,
            "viewing_fee_coin": viewing_fee_coin,
        }

    def _charge_view_fee(self, *, actor: User, match_id: str, amount: Decimal) -> None:
        normalized_amount = Decimal(amount).quantize(DECIMAL_QUANTUM)
        if normalized_amount <= Decimal("0.0000"):
            return
        user_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.COIN)
        try:
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=user_account,
                        amount=-normalized_amount,
                        source_tag=LedgerSourceTag.VIDEO_VIEW_SPEND,
                    ),
                    LedgerPosting(
                        account=platform_account,
                        amount=normalized_amount,
                        source_tag=LedgerSourceTag.MATCH_VIEW_REVENUE,
                    ),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                reference=f"broadcast-view:{match_id}:{actor.id}",
                description="Broadcast pay-per-view access",
                external_reference=match_id,
                actor=actor,
            )
        except InsufficientBalanceError as exc:
            raise BroadcastRightsError("Insufficient GTex Coin balance to unlock this broadcast.") from exc

    def _validate_new_right(
        self,
        *,
        competition_id: str,
        start_date: date,
        end_date: date,
        exclusivity: bool,
        revenue_share_percentage: Decimal,
    ) -> None:
        overlapping = list(
            self.session.scalars(
                select(BroadcastRight).where(
                    BroadcastRight.competition_id == competition_id,
                    BroadcastRight.start_date <= end_date,
                    BroadcastRight.end_date >= start_date,
                )
            ).all()
        )
        if exclusivity and overlapping:
            raise BroadcastRightsError("Exclusive rights cannot overlap existing broadcast rights.")
        if not exclusivity and any(item.exclusivity for item in overlapping):
            raise BroadcastRightsError("Non-exclusive rights cannot overlap an exclusive broadcast-rights package.")
        if not exclusivity:
            share_total = sum((Decimal(item.revenue_share_percentage) for item in overlapping), Decimal("0.00"))
            if share_total + Decimal(revenue_share_percentage) > NON_EXCLUSIVE_SHARE_CAP:
                raise BroadcastRightsError("Non-exclusive revenue-share cap exceeded for this competition.")

    @staticmethod
    def _validate_right_window(start_date: date, end_date: date) -> None:
        if end_date < start_date:
            raise BroadcastRightsError("Broadcast-rights end date cannot be before the start date.")

    @staticmethod
    def _right_metadata(payload) -> dict[str, Any]:
        return {
            "viewing_fee_coin": str(Decimal(payload.viewing_fee_coin).quantize(DECIMAL_QUANTUM)),
            "premium_features": dict(payload.premium_features),
            "ad_inventory": list(payload.ad_inventory),
            "sponsored_overlays": list(payload.sponsored_overlays),
        }

    def _require_competition(self, competition_id: str) -> Competition:
        item = self.session.get(Competition, competition_id)
        if item is None:
            raise BroadcastRightsError("Competition was not found.")
        return item

    def _club_owner_id(self, club_id: str) -> str | None:
        club = self.session.get(ClubProfile, club_id)
        return club.owner_user_id if club is not None else None

    def _notify(
        self,
        *,
        user_id: str | None,
        topic: str,
        template_key: str,
        resource_type: str,
        resource_id: str | None,
        message: str,
        metadata: dict[str, Any],
    ) -> None:
        if user_id is None:
            return
        self.session.add(
            NotificationRecord(
                user_id=user_id,
                topic=topic,
                template_key=template_key,
                resource_type=resource_type,
                resource_id=resource_id,
                message=message[:255],
                metadata_json=dict(metadata),
            )
        )


__all__ = ["BroadcastRightsError", "BroadcastRightsService", "PLATFORM_OWNER_ID"]
