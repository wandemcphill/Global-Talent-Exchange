from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.club_profile import ClubProfile
from app.models.club_sale_market import ClubSaleTransfer
from app.models.creator_provisioning import CreatorSquad
from app.models.creator_share_market import (
    CreatorClubShareDistribution,
    CreatorClubShareHolding,
    CreatorClubShareMarket,
    CreatorClubShareMarketControl,
    CreatorClubSharePayout,
    CreatorClubSharePurchase,
)
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.risk_ops_engine.service import RiskOpsService
from app.services.club_governance_policy import (
    default_governance_policy,
    fully_diluted_governance_shares,
    governance_policy_from_metadata,
    holder_cap_share_count,
    owner_approval_required,
    ownership_bps,
)
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_CONTROL_KEY = "default"
MATCH_VIDEO_REVENUE_SOURCE = "match_video"
GIFTS_REVENUE_SOURCE = "gifts"
SEASON_PASS_REVENUE_SOURCE = "season_pass"
TICKET_SALES_REVENUE_SOURCE = "ticket_sales"


class CreatorClubShareMarketError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


@dataclass(frozen=True, slots=True)
class CreatorClubShareBenefitState:
    shareholder: bool
    share_count: int
    has_priority_chat_visibility: bool
    has_early_ticket_access: bool
    has_cosmetic_voting_rights: bool
    tournament_qualification_method: str | None
    cosmetic_vote_power: int


class CreatorClubShareMarketService:
    def __init__(
        self,
        session: Session,
        *,
        wallet_service: WalletService | None = None,
        risk_ops: RiskOpsService | None = None,
    ) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService()
        self.risk_ops = risk_ops or RiskOpsService(session)

    def get_admin_control(self) -> CreatorClubShareMarketControl:
        control = self.session.scalar(
            select(CreatorClubShareMarketControl).where(
                CreatorClubShareMarketControl.control_key == DEFAULT_CONTROL_KEY,
            )
        )
        if control is None:
            control = CreatorClubShareMarketControl(
                control_key=DEFAULT_CONTROL_KEY,
                metadata_json={},
            )
            self.session.add(control)
            self.session.flush()
        return control

    def update_admin_control(
        self,
        *,
        actor: User,
        max_shares_per_club: int,
        max_shares_per_fan: int,
        shareholder_revenue_share_bps: int,
        issuance_enabled: bool = True,
        purchase_enabled: bool = True,
        max_primary_purchase_value_coin: Decimal = Decimal("2500.0000"),
    ) -> CreatorClubShareMarketControl:
        if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise CreatorClubShareMarketError(
                "Admin access is required to update creator club share-market controls.",
                reason="admin_required",
            )
        if max_shares_per_club <= 0:
            raise CreatorClubShareMarketError(
                "Max shares per club must be greater than zero.",
                reason="max_shares_per_club_invalid",
            )
        if max_shares_per_fan <= 0:
            raise CreatorClubShareMarketError(
                "Max shares per fan must be greater than zero.",
                reason="max_shares_per_fan_invalid",
            )
        if max_shares_per_fan > max_shares_per_club:
            raise CreatorClubShareMarketError(
                "Max shares per fan cannot exceed the max shares per club.",
                reason="max_shares_per_fan_invalid",
            )
        if shareholder_revenue_share_bps < 0 or shareholder_revenue_share_bps > 10000:
            raise CreatorClubShareMarketError(
                "Shareholder revenue distribution must stay between 0 and 10000 basis points.",
                reason="shareholder_revenue_share_invalid",
            )
        normalized_primary_purchase_cap = self._normalize_amount(max_primary_purchase_value_coin)
        if normalized_primary_purchase_cap <= Decimal("0.0000"):
            raise CreatorClubShareMarketError(
                "Max primary purchase value must be greater than zero.",
                reason="share_purchase_value_cap_invalid",
            )

        market_cap_conflict = self.session.scalar(
            select(func.count())
            .select_from(CreatorClubShareMarket)
            .where(CreatorClubShareMarket.max_shares_issued > max_shares_per_club)
        )
        if int(market_cap_conflict or 0) > 0:
            raise CreatorClubShareMarketError(
                "Existing creator club share markets exceed the requested club cap.",
                reason="share_market_cap_conflict",
            )
        holding_cap_conflict = self.session.scalar(
            select(func.count())
            .select_from(CreatorClubShareHolding)
            .where(CreatorClubShareHolding.share_count > max_shares_per_fan)
        )
        if int(holding_cap_conflict or 0) > 0:
            raise CreatorClubShareMarketError(
                "Existing shareholder balances exceed the requested fan cap.",
                reason="share_holding_cap_conflict",
            )

        control = self.get_admin_control()
        control.max_shares_per_club = max_shares_per_club
        control.max_shares_per_fan = max_shares_per_fan
        control.shareholder_revenue_share_bps = shareholder_revenue_share_bps
        control.issuance_enabled = bool(issuance_enabled)
        control.purchase_enabled = bool(purchase_enabled)
        control.max_primary_purchase_value_coin = normalized_primary_purchase_cap
        control.metadata_json = {
            "creator_control_policy": "creator_retains_majority_control",
            "governance_policy": default_governance_policy(max_shares_per_fan=max_shares_per_fan),
        }

        for market in self.session.scalars(select(CreatorClubShareMarket)).all():
            market.max_shares_per_fan = min(int(market.max_shares_per_fan), max_shares_per_fan)
            market.shareholder_revenue_share_bps = shareholder_revenue_share_bps
            market.metadata_json = {
                **(market.metadata_json or {}),
                "governance_policy": governance_policy_from_metadata(
                    market.metadata_json,
                    max_shares_per_fan=int(market.max_shares_per_fan),
                ),
            }

        self._log_audit(
            actor_user_id=actor.id,
            action_key="creator_share_market.control.updated",
            resource_id=control.id,
            detail="Creator club share-market admin controls updated.",
            metadata_json={
                "max_shares_per_club": max_shares_per_club,
                "max_shares_per_fan": max_shares_per_fan,
                "shareholder_revenue_share_bps": shareholder_revenue_share_bps,
                "issuance_enabled": bool(issuance_enabled),
                "purchase_enabled": bool(purchase_enabled),
                "max_primary_purchase_value_coin": str(normalized_primary_purchase_cap),
            },
        )
        self.session.flush()
        return control

    def issue_market(
        self,
        *,
        actor: User,
        club_id: str,
        share_price_coin: Decimal,
        max_shares_issued: int,
        max_shares_per_fan: int | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> CreatorClubShareMarket:
        creator_user_id = self._assert_actor_controls_creator_club(actor=actor, club_id=club_id)
        control = self.get_admin_control()
        if not control.issuance_enabled:
            raise CreatorClubShareMarketError(
                "Creator club fan-share issuance is currently disabled by admin policy.",
                reason="share_market_issuance_disabled",
            )
        normalized_price = self._normalize_amount(share_price_coin)
        if normalized_price <= Decimal("0.0000"):
            raise CreatorClubShareMarketError(
                "Fan-share price must be greater than zero.",
                reason="share_price_invalid",
            )
        if max_shares_issued <= 0:
            raise CreatorClubShareMarketError(
                "Max shares issued must be greater than zero.",
                reason="max_shares_issued_invalid",
            )
        if max_shares_issued > int(control.max_shares_per_club):
            raise CreatorClubShareMarketError(
                "Requested fan-share supply exceeds the admin club cap.",
                reason="max_shares_issued_cap_exceeded",
            )

        resolved_fan_cap = max_shares_per_fan if max_shares_per_fan is not None else min(
            int(control.max_shares_per_fan),
            max_shares_issued,
        )
        if resolved_fan_cap <= 0 or resolved_fan_cap > max_shares_issued:
            raise CreatorClubShareMarketError(
                "Max shares per fan must stay between 1 and the club issue cap.",
                reason="max_shares_per_fan_invalid",
            )
        if resolved_fan_cap > int(control.max_shares_per_fan):
            raise CreatorClubShareMarketError(
                "Requested fan-share cap exceeds the admin fan cap.",
                reason="max_shares_per_fan_cap_exceeded",
            )
        governance_policy = governance_policy_from_metadata(
            {
                **(control.metadata_json or {}),
                **dict(metadata_json or {}),
            },
            max_shares_per_fan=resolved_fan_cap,
        )

        market = self.session.scalar(
            select(CreatorClubShareMarket).where(CreatorClubShareMarket.club_id == club_id)
        )
        if market is None:
            market = CreatorClubShareMarket(
                club_id=club_id,
                creator_user_id=creator_user_id,
                issued_by_user_id=actor.id,
                status="active",
                share_price_coin=normalized_price,
                max_shares_issued=max_shares_issued,
                max_shares_per_fan=resolved_fan_cap,
                creator_controlled_shares=self._creator_controlled_shares(max_shares_issued),
                shareholder_revenue_share_bps=int(control.shareholder_revenue_share_bps),
                metadata_json={},
            )
            self.session.add(market)
        else:
            if int(market.shares_sold) > max_shares_issued:
                raise CreatorClubShareMarketError(
                    "Max shares issued cannot drop below already purchased shares.",
                    reason="max_shares_issued_below_sold",
                )
            max_holding = int(
                self.session.scalar(
                    select(func.coalesce(func.max(CreatorClubShareHolding.share_count), 0)).where(
                        CreatorClubShareHolding.club_id == club_id,
                    )
                )
                or 0
            )
            if max_holding > resolved_fan_cap:
                raise CreatorClubShareMarketError(
                    "Max shares per fan cannot drop below an existing shareholder balance.",
                    reason="max_shares_per_fan_below_existing_holding",
                )
            market.creator_user_id = creator_user_id
            market.share_price_coin = normalized_price
            market.max_shares_issued = max_shares_issued
            market.max_shares_per_fan = resolved_fan_cap
            market.creator_controlled_shares = self._creator_controlled_shares(max_shares_issued)
            market.shareholder_revenue_share_bps = int(control.shareholder_revenue_share_bps)
            market.status = "active"

        market.metadata_json = {
            **(market.metadata_json or {}),
            **dict(metadata_json or {}),
            "admin_control_key": control.control_key,
            "product_scope": "creator_club_fan_shares",
            "creator_retains_control": True,
            "governance_policy": governance_policy,
        }
        self._log_audit(
            actor_user_id=actor.id,
            action_key="creator_share_market.market.issued",
            resource_id=market.id,
            detail="Creator club fan shares issued or updated.",
            metadata_json={
                "club_id": club_id,
                "share_price_coin": str(normalized_price),
                "max_shares_issued": max_shares_issued,
                "max_shares_per_fan": resolved_fan_cap,
            },
        )
        self.session.flush()
        return market

    def get_market(self, *, club_id: str) -> CreatorClubShareMarket:
        market = self.session.scalar(
            select(CreatorClubShareMarket).where(CreatorClubShareMarket.club_id == club_id)
        )
        if market is None:
            raise CreatorClubShareMarketError(
                "Creator club fan-share market was not found.",
                reason="share_market_not_found",
            )
        return market

    def get_holding(self, *, club_id: str, user_id: str) -> CreatorClubShareHolding | None:
        return self.session.scalar(
            select(CreatorClubShareHolding).where(
                CreatorClubShareHolding.club_id == club_id,
                CreatorClubShareHolding.user_id == user_id,
            )
        )

    def get_benefit_state(self, *, club_id: str, user_id: str) -> CreatorClubShareBenefitState:
        holding = self.get_holding(club_id=club_id, user_id=user_id)
        share_count = int(holding.share_count) if holding is not None else 0
        shareholder = share_count > 0
        return CreatorClubShareBenefitState(
            shareholder=shareholder,
            share_count=share_count,
            has_priority_chat_visibility=shareholder,
            has_early_ticket_access=shareholder,
            has_cosmetic_voting_rights=shareholder,
            tournament_qualification_method="shareholder" if shareholder else None,
            cosmetic_vote_power=share_count,
        )

    def list_distributions(self, *, club_id: str, limit: int = 50) -> list[CreatorClubShareDistribution]:
        return list(
            self.session.scalars(
                select(CreatorClubShareDistribution)
                .where(CreatorClubShareDistribution.club_id == club_id)
                .order_by(CreatorClubShareDistribution.created_at.desc())
                .limit(limit)
            ).all()
        )

    def purchase_shares(
        self,
        *,
        actor: User,
        club_id: str,
        share_count: int,
    ) -> CreatorClubSharePurchase:
        control = self.get_admin_control()
        if not control.purchase_enabled:
            raise CreatorClubShareMarketError(
                "Creator club fan-share purchases are currently disabled by admin policy.",
                reason="share_purchase_disabled",
            )
        market = self.get_market(club_id=club_id)
        if market.status != "active":
            raise CreatorClubShareMarketError(
                "Creator club fan shares are not currently available.",
                reason="share_market_inactive",
            )
        if actor.id == market.creator_user_id:
            raise CreatorClubShareMarketError(
                "Creators cannot buy their own club fan shares.",
                reason="creator_purchase_forbidden",
            )
        if share_count <= 0:
            raise CreatorClubShareMarketError(
                "Share purchase quantity must be greater than zero.",
                reason="share_count_invalid",
            )
        if int(market.shares_sold) + share_count > int(market.max_shares_issued):
            raise CreatorClubShareMarketError(
                "Requested fan-share quantity exceeds the remaining supply.",
                reason="share_supply_exhausted",
            )

        holding = self.get_holding(club_id=club_id, user_id=actor.id)
        current_balance = int(holding.share_count) if holding is not None else 0
        if current_balance + share_count > int(market.max_shares_per_fan):
            raise CreatorClubShareMarketError(
                "Requested purchase exceeds the fan-share cap for a single supporter.",
                reason="shareholder_cap_exceeded",
            )
        total_governance_shares = self._total_governance_shares(market)
        governance_policy = self._governance_policy(market)
        projected_balance = current_balance + share_count
        anti_takeover_cap = holder_cap_share_count(
            total_governance_shares=total_governance_shares,
            max_holder_bps=int(governance_policy["max_holder_bps"]),
        )
        if (
            bool(governance_policy.get("anti_takeover_enabled"))
            and anti_takeover_cap > 0
            and projected_balance > anti_takeover_cap
        ):
            raise CreatorClubShareMarketError(
                "Requested purchase exceeds the anti-takeover ownership cap for a single shareholder.",
                reason="shareholder_anti_takeover_cap_exceeded",
            )

        total_price_coin = self._normalize_amount(Decimal(share_count) * Decimal(str(market.share_price_coin)))
        if total_price_coin > self._normalize_amount(control.max_primary_purchase_value_coin):
            raise CreatorClubShareMarketError(
                "Requested fan-share purchase exceeds the current admin purchase-value cap.",
                reason="share_purchase_value_cap_exceeded",
            )
        purchase = CreatorClubSharePurchase(
            market_id=market.id,
            club_id=club_id,
            creator_user_id=market.creator_user_id,
            user_id=actor.id,
            share_count=share_count,
            share_price_coin=self._normalize_amount(market.share_price_coin),
            total_price_coin=total_price_coin,
            metadata_json={
                "product_scope": "creator_club_fan_shares",
                "shareholder_revenue_share_bps": int(market.shareholder_revenue_share_bps),
                "governance_policy": governance_policy,
            },
        )
        self.session.add(purchase)
        self.session.flush()

        creator_user = self.session.get(User, market.creator_user_id)
        if creator_user is None:
            raise CreatorClubShareMarketError(
                "Creator beneficiary account was not found for this fan-share purchase.",
                reason="creator_account_missing",
            )
        buyer_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        creator_account = self.wallet_service.get_user_account(self.session, creator_user, LedgerUnit.COIN)
        try:
            entries = self.wallet_service.append_transaction(
                self.session,
                postings=[
                    LedgerPosting(
                        account=buyer_account,
                        amount=-total_price_coin,
                        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    ),
                    LedgerPosting(
                        account=creator_account,
                        amount=total_price_coin,
                        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    ),
                ],
                reason=LedgerEntryReason.ADJUSTMENT,
                reference=f"creator-share-purchase:{purchase.id}",
                description=f"Creator club fan shares for club {club_id}",
                actor=actor,
            )
        except InsufficientBalanceError as exc:
            raise CreatorClubShareMarketError(
                "Insufficient GTEX Coin balance for this creator club fan-share purchase.",
                reason="insufficient_balance",
            ) from exc
        purchase.ledger_transaction_id = entries[0].transaction_id if entries else None

        if holding is None:
            holding = CreatorClubShareHolding(
                market_id=market.id,
                club_id=club_id,
                user_id=actor.id,
                share_count=0,
                total_spent_coin=Decimal("0.0000"),
                revenue_earned_coin=Decimal("0.0000"),
                metadata_json={},
            )
            self.session.add(holding)

        holding.market_id = market.id
        holding.share_count = current_balance + share_count
        holding.total_spent_coin = self._normalize_amount(Decimal(str(holding.total_spent_coin)) + total_price_coin)
        post_purchase_ownership_bps = self._ownership_bps(
            share_count=holding.share_count,
            total_share_count=total_governance_shares,
        )
        holding.metadata_json = {
            **(holding.metadata_json or {}),
            "shareholder": True,
            "ownership_bps": post_purchase_ownership_bps,
            "governance_eligible": holding.share_count >= int(governance_policy["proposal_share_threshold"]),
            "owner_approval_required": owner_approval_required(
                governance_policy,
                ownership_bps=post_purchase_ownership_bps,
            ),
            "last_purchase_id": purchase.id,
        }
        purchase.metadata_json = {
            **(purchase.metadata_json or {}),
            "pre_purchase_share_count": current_balance,
            "post_purchase_share_count": holding.share_count,
            "post_purchase_ownership_bps": post_purchase_ownership_bps,
            "total_governance_shares": total_governance_shares,
            "anti_takeover_cap_share_count": anti_takeover_cap,
            "governance_eligible": holding.share_count >= int(governance_policy["proposal_share_threshold"]),
        }

        market.shares_sold = int(market.shares_sold) + share_count
        market.total_purchase_volume_coin = self._normalize_amount(
            Decimal(str(market.total_purchase_volume_coin)) + total_price_coin
        )
        market.metadata_json = {
            **(market.metadata_json or {}),
            "last_purchase_id": purchase.id,
            "last_shareholder_user_id": actor.id,
            "governance_policy": governance_policy,
        }
        self._log_audit(
            actor_user_id=actor.id,
            action_key="creator_share_market.shares.purchased",
            resource_id=purchase.id,
            detail="Creator club fan shares purchased.",
            metadata_json={
                "club_id": club_id,
                "share_count": share_count,
                "total_price_coin": str(total_price_coin),
            },
        )
        self.session.flush()
        return purchase

    def distribute_creator_revenue(
        self,
        *,
        actor: User,
        club_id: str,
        creator_user_id: str,
        source_type: str,
        source_reference_id: str,
        eligible_revenue_coin: Decimal,
        season_id: str | None = None,
        competition_id: str | None = None,
        match_id: str | None = None,
        metadata_json: dict[str, object] | None = None,
    ) -> CreatorClubShareDistribution:
        market = self.get_market(club_id=club_id)
        existing = self.session.scalar(
            select(CreatorClubShareDistribution).where(
                CreatorClubShareDistribution.club_id == club_id,
                CreatorClubShareDistribution.source_type == source_type,
                CreatorClubShareDistribution.source_reference_id == source_reference_id,
            )
        )
        if existing is not None:
            return existing

        eligible_amount = self._normalize_amount(eligible_revenue_coin)
        if eligible_amount < Decimal("0.0000"):
            raise CreatorClubShareMarketError(
                "Eligible creator revenue cannot be negative.",
                reason="eligible_revenue_invalid",
            )

        holdings = list(
            self.session.scalars(
                select(CreatorClubShareHolding)
                .where(
                    CreatorClubShareHolding.club_id == club_id,
                    CreatorClubShareHolding.share_count > 0,
                )
                .order_by(CreatorClubShareHolding.user_id.asc())
            ).all()
        )
        distributed_share_count = sum(int(item.share_count) for item in holdings)
        shareholder_pool_coin = self._normalize_amount(
            eligible_amount * Decimal(int(market.shareholder_revenue_share_bps)) / Decimal("10000")
        )
        creator_retained_coin = self._normalize_amount(eligible_amount - shareholder_pool_coin)
        distribution = CreatorClubShareDistribution(
            market_id=market.id,
            club_id=club_id,
            creator_user_id=creator_user_id,
            source_type=source_type,
            source_reference_id=source_reference_id,
            season_id=season_id,
            competition_id=competition_id,
            match_id=match_id,
            eligible_revenue_coin=eligible_amount,
            shareholder_pool_coin=shareholder_pool_coin,
            creator_retained_coin=creator_retained_coin,
            shareholder_revenue_share_bps=int(market.shareholder_revenue_share_bps),
            distributed_share_count=distributed_share_count,
            recipient_count=0,
            status="skipped",
            metadata_json={
                **dict(metadata_json or {}),
                "distribution_formula": "eligible_revenue * shareholder_revenue_share_bps / 10000",
            },
        )
        self.session.add(distribution)
        self.session.flush()

        if shareholder_pool_coin > Decimal("0.0000") and distributed_share_count > 0:
            payouts = self._allocate_shareholder_pool(
                pool_coin=shareholder_pool_coin,
                holdings=holdings,
            )
            creator_user = self.session.get(User, creator_user_id)
            if creator_user is None:
                raise CreatorClubShareMarketError(
                    "Creator beneficiary account was not found for shareholder revenue distribution.",
                    reason="creator_account_missing",
                )
            creator_account = self.wallet_service.get_user_account(self.session, creator_user, LedgerUnit.COIN)
            postings = [
                LedgerPosting(
                    account=creator_account,
                    amount=-shareholder_pool_coin,
                    source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                )
            ]
            positive_payouts: list[tuple[CreatorClubShareHolding, Decimal]] = []
            for holding_item, payout_coin in payouts:
                if payout_coin <= Decimal("0.0000"):
                    continue
                holder_user = self.session.get(User, holding_item.user_id)
                if holder_user is None:
                    continue
                holder_account = self.wallet_service.get_user_account(self.session, holder_user, LedgerUnit.COIN)
                postings.append(
                    LedgerPosting(
                        account=holder_account,
                        amount=payout_coin,
                        source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
                    )
                )
                positive_payouts.append((holding_item, payout_coin))

            try:
                entries = self.wallet_service.append_transaction(
                    self.session,
                    postings=postings,
                    reason=LedgerEntryReason.ADJUSTMENT,
                    reference=f"creator-share-distribution:{distribution.id}",
                    description=f"Creator club shareholder revenue payout for {source_type}:{source_reference_id}",
                    actor=actor,
                )
            except InsufficientBalanceError as exc:
                raise CreatorClubShareMarketError(
                    "Creator revenue distribution could not settle because the creator wallet balance is unavailable.",
                    reason="distribution_balance_unavailable",
                ) from exc
            transaction_id = entries[0].transaction_id if entries else None
            distribution.recipient_count = len(positive_payouts)
            distribution.status = "settled"
            market.total_revenue_distributed_coin = self._normalize_amount(
                Decimal(str(market.total_revenue_distributed_coin)) + shareholder_pool_coin
            )
            for holding_item, payout_coin in positive_payouts:
                holding_item.revenue_earned_coin = self._normalize_amount(
                    Decimal(str(holding_item.revenue_earned_coin)) + payout_coin
                )
                payout = CreatorClubSharePayout(
                    distribution_id=distribution.id,
                    holding_id=holding_item.id,
                    club_id=club_id,
                    user_id=holding_item.user_id,
                    share_count=int(holding_item.share_count),
                    payout_coin=payout_coin,
                    ownership_bps=self._ownership_bps(
                        share_count=int(holding_item.share_count),
                        total_share_count=distributed_share_count,
                    ),
                    ledger_transaction_id=transaction_id,
                    metadata_json={"source_type": source_type},
                )
                self.session.add(payout)
        self._log_audit(
            actor_user_id=actor.id,
            action_key="creator_share_market.revenue.distributed",
            resource_id=distribution.id,
            detail="Creator club shareholder revenue distributed.",
            metadata_json={
                "club_id": club_id,
                "source_type": source_type,
                "source_reference_id": source_reference_id,
                "shareholder_pool_coin": str(shareholder_pool_coin),
            },
        )
        self.session.flush()
        return distribution

    def serialize_control(self, control: CreatorClubShareMarketControl) -> dict[str, object]:
        return {
            "id": control.id,
            "control_key": control.control_key,
            "max_shares_per_club": control.max_shares_per_club,
            "max_shares_per_fan": control.max_shares_per_fan,
            "shareholder_revenue_share_bps": control.shareholder_revenue_share_bps,
            "issuance_enabled": control.issuance_enabled,
            "purchase_enabled": control.purchase_enabled,
            "max_primary_purchase_value_coin": control.max_primary_purchase_value_coin,
            "metadata_json": control.metadata_json or {},
            "created_at": control.created_at,
            "updated_at": control.updated_at,
        }

    def serialize_holding(self, holding: CreatorClubShareHolding | None) -> dict[str, object] | None:
        if holding is None:
            return None
        return {
            "id": holding.id,
            "market_id": holding.market_id,
            "club_id": holding.club_id,
            "user_id": holding.user_id,
            "share_count": holding.share_count,
            "total_spent_coin": holding.total_spent_coin,
            "revenue_earned_coin": holding.revenue_earned_coin,
            "metadata_json": holding.metadata_json or {},
            "created_at": holding.created_at,
            "updated_at": holding.updated_at,
        }

    def serialize_benefits(self, benefits: CreatorClubShareBenefitState) -> dict[str, object]:
        return {
            "shareholder": benefits.shareholder,
            "share_count": benefits.share_count,
            "has_priority_chat_visibility": benefits.has_priority_chat_visibility,
            "has_early_ticket_access": benefits.has_early_ticket_access,
            "has_cosmetic_voting_rights": benefits.has_cosmetic_voting_rights,
            "tournament_qualification_method": benefits.tournament_qualification_method,
            "cosmetic_vote_power": benefits.cosmetic_vote_power,
        }

    def serialize_market(
        self,
        market: CreatorClubShareMarket,
        *,
        viewer: User | None = None,
    ) -> dict[str, object]:
        viewer_holding = self.get_holding(club_id=market.club_id, user_id=viewer.id) if viewer is not None else None
        viewer_benefits = (
            self.get_benefit_state(club_id=market.club_id, user_id=viewer.id)
            if viewer is not None
            else CreatorClubShareBenefitState(False, 0, False, False, False, None, 0)
        )
        shareholder_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(CreatorClubShareHolding)
                .where(
                    CreatorClubShareHolding.club_id == market.club_id,
                    CreatorClubShareHolding.share_count > 0,
                )
            )
            or 0
        )
        governance_policy = self._governance_policy(market)
        creator_control_bps = self._ownership_bps(
            share_count=int(market.creator_controlled_shares),
            total_share_count=self._total_governance_shares(market),
        )
        return {
            "id": market.id,
            "club_id": market.club_id,
            "creator_user_id": market.creator_user_id,
            "issued_by_user_id": market.issued_by_user_id,
            "status": market.status,
            "share_price_coin": market.share_price_coin,
            "max_shares_issued": market.max_shares_issued,
            "shares_sold": market.shares_sold,
            "shares_remaining": max(0, int(market.max_shares_issued) - int(market.shares_sold)),
            "max_shares_per_fan": market.max_shares_per_fan,
            "creator_controlled_shares": market.creator_controlled_shares,
            "creator_control_bps": creator_control_bps,
            "shareholder_revenue_share_bps": market.shareholder_revenue_share_bps,
            "shareholder_count": shareholder_count,
            "total_purchase_volume_coin": market.total_purchase_volume_coin,
            "total_revenue_distributed_coin": market.total_revenue_distributed_coin,
            "metadata_json": market.metadata_json or {},
            "governance_policy": governance_policy,
            "ownership_ledger": self._serialize_ownership_ledger(
                market,
                shareholder_count=shareholder_count,
            ),
            "created_at": market.created_at,
            "updated_at": market.updated_at,
            "viewer_holding": self.serialize_holding(viewer_holding),
            "viewer_benefits": self.serialize_benefits(viewer_benefits),
        }

    def serialize_purchase(self, purchase: CreatorClubSharePurchase) -> dict[str, object]:
        return {
            "id": purchase.id,
            "market_id": purchase.market_id,
            "club_id": purchase.club_id,
            "creator_user_id": purchase.creator_user_id,
            "user_id": purchase.user_id,
            "share_count": purchase.share_count,
            "share_price_coin": purchase.share_price_coin,
            "total_price_coin": purchase.total_price_coin,
            "ledger_transaction_id": purchase.ledger_transaction_id,
            "metadata_json": purchase.metadata_json or {},
            "created_at": purchase.created_at,
            "updated_at": purchase.updated_at,
        }

    def serialize_distribution(self, distribution: CreatorClubShareDistribution) -> dict[str, object]:
        payouts = list(
            self.session.scalars(
                select(CreatorClubSharePayout)
                .where(CreatorClubSharePayout.distribution_id == distribution.id)
                .order_by(CreatorClubSharePayout.payout_coin.desc(), CreatorClubSharePayout.created_at.asc())
            ).all()
        )
        return {
            "id": distribution.id,
            "market_id": distribution.market_id,
            "club_id": distribution.club_id,
            "creator_user_id": distribution.creator_user_id,
            "source_type": distribution.source_type,
            "source_reference_id": distribution.source_reference_id,
            "season_id": distribution.season_id,
            "competition_id": distribution.competition_id,
            "match_id": distribution.match_id,
            "eligible_revenue_coin": distribution.eligible_revenue_coin,
            "shareholder_pool_coin": distribution.shareholder_pool_coin,
            "creator_retained_coin": distribution.creator_retained_coin,
            "shareholder_revenue_share_bps": distribution.shareholder_revenue_share_bps,
            "distributed_share_count": distribution.distributed_share_count,
            "recipient_count": distribution.recipient_count,
            "status": distribution.status,
            "metadata_json": distribution.metadata_json or {},
            "created_at": distribution.created_at,
            "updated_at": distribution.updated_at,
            "payouts": [
                {
                    "id": payout.id,
                    "distribution_id": payout.distribution_id,
                    "holding_id": payout.holding_id,
                    "club_id": payout.club_id,
                    "user_id": payout.user_id,
                    "share_count": payout.share_count,
                    "payout_coin": payout.payout_coin,
                    "ownership_bps": payout.ownership_bps,
                    "ledger_transaction_id": payout.ledger_transaction_id,
                    "metadata_json": payout.metadata_json or {},
                    "created_at": payout.created_at,
                    "updated_at": payout.updated_at,
                }
                for payout in payouts
            ],
        }

    def _serialize_ownership_ledger(
        self,
        market: CreatorClubShareMarket,
        *,
        shareholder_count: int,
        limit: int = 8,
    ) -> dict[str, object]:
        club = self.session.get(ClubProfile, market.club_id)
        total_governance_shares = self._total_governance_shares(market)
        transfers = list(
            self.session.scalars(
                select(ClubSaleTransfer)
                .where(ClubSaleTransfer.club_id == market.club_id)
                .order_by(ClubSaleTransfer.created_at.desc())
                .limit(limit)
            ).all()
        )
        purchases = list(
            self.session.scalars(
                select(CreatorClubSharePurchase)
                .where(CreatorClubSharePurchase.club_id == market.club_id)
                .order_by(CreatorClubSharePurchase.created_at.desc())
                .limit(limit)
            ).all()
        )
        entries: list[dict[str, object]] = []
        for transfer in transfers:
            transfer_metadata = dict(transfer.metadata_json or {})
            entries.append(
                {
                    "entry_type": "club_sale_transfer",
                    "entry_reference_id": transfer.transfer_id,
                    "user_id": transfer.buyer_user_id,
                    "share_delta": 0,
                    "ownership_bps": self._ownership_bps(
                        share_count=int(market.creator_controlled_shares),
                        total_share_count=total_governance_shares,
                    ),
                    "created_at": transfer.created_at,
                    "summary": f"Club control transferred from {transfer.seller_user_id} to {transfer.buyer_user_id}.",
                    "metadata_json": {
                        **transfer_metadata,
                        "previous_owner_user_id": transfer_metadata.get("previous_owner_user_id", transfer.seller_user_id),
                        "new_owner_user_id": transfer_metadata.get("new_owner_user_id", transfer.buyer_user_id),
                    },
                }
            )
        for purchase in purchases:
            purchase_metadata = dict(purchase.metadata_json or {})
            entries.append(
                {
                    "entry_type": "share_purchase",
                    "entry_reference_id": purchase.id,
                    "user_id": purchase.user_id,
                    "share_delta": int(purchase.share_count),
                    "ownership_bps": int(
                        purchase_metadata.get("post_purchase_ownership_bps")
                        or self._holding_ownership_bps(
                            club_id=market.club_id,
                            user_id=purchase.user_id,
                            total_share_count=total_governance_shares,
                        )
                    ),
                    "created_at": purchase.created_at,
                    "summary": f"{purchase.user_id} acquired {purchase.share_count} club shares.",
                    "metadata_json": purchase_metadata,
                }
            )
        entries.sort(key=lambda item: item["created_at"], reverse=True)
        last_transfer = transfers[0] if transfers else None
        return {
            "current_owner_user_id": club.owner_user_id if club is not None else market.creator_user_id,
            "total_governance_shares": total_governance_shares,
            "shareholder_count": shareholder_count,
            "circulating_share_count": int(market.shares_sold),
            "last_transfer_id": last_transfer.transfer_id if last_transfer is not None else None,
            "last_transfer_at": last_transfer.created_at if last_transfer is not None else None,
            "recent_entries": entries[:limit],
        }

    def _holding_ownership_bps(self, *, club_id: str, user_id: str, total_share_count: int) -> int:
        holding = self.get_holding(club_id=club_id, user_id=user_id)
        if holding is None:
            return 0
        return self._ownership_bps(
            share_count=int(holding.share_count),
            total_share_count=total_share_count,
        )

    def _governance_policy(self, market: CreatorClubShareMarket) -> dict[str, object]:
        return governance_policy_from_metadata(
            market.metadata_json,
            max_shares_per_fan=int(market.max_shares_per_fan),
        )

    def _total_governance_shares(self, market: CreatorClubShareMarket) -> int:
        return fully_diluted_governance_shares(
            creator_controlled_shares=int(market.creator_controlled_shares),
            fan_share_supply=int(market.max_shares_issued),
        )

    def _assert_actor_controls_creator_club(self, *, actor: User, club_id: str) -> str:
        club = self.session.scalar(select(ClubProfile).where(ClubProfile.id == club_id))
        if club is None:
            raise CreatorClubShareMarketError(
                "Creator club was not found.",
                reason="creator_club_not_found",
            )
        squad_exists = self.session.scalar(
            select(CreatorSquad.id).where(CreatorSquad.club_id == club_id)
        )
        if squad_exists is None:
            raise CreatorClubShareMarketError(
                "Creator club provisioning is required before issuing fan shares.",
                reason="creator_club_not_provisioned",
            )
        creator_user_id = club.owner_user_id
        if creator_user_id is None:
            raise CreatorClubShareMarketError(
                "Creator club owner could not be resolved.",
                reason="creator_club_owner_missing",
            )
        if actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN} and actor.id != creator_user_id:
            raise CreatorClubShareMarketError(
                "Only the creator club owner can issue fan shares for this club.",
                reason="creator_scope_denied",
            )
        return creator_user_id

    def _allocate_shareholder_pool(
        self,
        *,
        pool_coin: Decimal,
        holdings: list[CreatorClubShareHolding],
    ) -> list[tuple[CreatorClubShareHolding, Decimal]]:
        if pool_coin <= Decimal("0.0000") or not holdings:
            return []
        total_shares = sum(int(item.share_count) for item in holdings)
        if total_shares <= 0:
            return []
        remaining = self._normalize_amount(pool_coin)
        allocations: list[tuple[CreatorClubShareHolding, Decimal]] = []
        for index, holding in enumerate(holdings):
            if index == len(holdings) - 1:
                payout_coin = remaining
            else:
                raw_amount = (Decimal(int(holding.share_count)) * pool_coin) / Decimal(total_shares)
                payout_coin = raw_amount.quantize(AMOUNT_QUANTUM, rounding=ROUND_DOWN)
                remaining = self._normalize_amount(remaining - payout_coin)
            allocations.append((holding, self._normalize_amount(payout_coin)))
        return allocations

    @staticmethod
    def _creator_controlled_shares(max_shares_issued: int) -> int:
        return int(max_shares_issued) + 1

    @staticmethod
    def _ownership_bps(*, share_count: int, total_share_count: int) -> int:
        return ownership_bps(
            share_count=share_count,
            total_share_count=total_share_count,
        )

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
            resource_type="creator_share_market",
            resource_id=resource_id,
            detail=detail,
            metadata_json=metadata_json or {},
        )

    @staticmethod
    def _normalize_amount(value: Decimal | str | int | float) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


__all__ = [
    "CreatorClubShareBenefitState",
    "CreatorClubShareMarketError",
    "CreatorClubShareMarketService",
    "GIFTS_REVENUE_SOURCE",
    "MATCH_VIDEO_REVENUE_SOURCE",
    "SEASON_PASS_REVENUE_SOURCE",
    "TICKET_SALES_REVENUE_SOURCE",
]
