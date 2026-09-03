from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_finance.service import ClubFinanceService, DRAW_BONUS, WIN_BONUS
from app.club_ownership.schemas import (
    ClubDividendDistributionView,
    ClubGovernanceActionView,
    ClubGovernanceProposalRequest,
    ClubGovernanceProposalView,
    ClubGovernanceStateView,
    ClubGovernanceVoteRequest,
    ClubGovernanceVoteView,
    ClubHoldingView,
    ClubOwnershipView,
    ClubPortfolioHoldingView,
    ClubPortfolioView,
    ClubTokenTradeResultView,
    ClubTokenView,
    ClubTreasuryEntryView,
    ClubTreasuryView,
)
from app.models.club_ownership import (
    ClubDividendDistribution,
    ClubGovernanceState,
    ClubHolding,
    ClubToken,
    ClubTreasury,
    ClubTreasuryEntry,
)
from app.models.club_profile import ClubProfile
from app.models.governance_engine import (
    GovernanceProposal,
    GovernanceProposalScope,
    GovernanceProposalStatus,
    GovernanceVote,
    GovernanceVoteChoice,
)
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import InsufficientBalanceError, WalletService

DECIMAL_QUANTUM = Decimal("0.0001")
MIN_TOKEN_PRICE = Decimal("0.2500")
BASE_TOKEN_PRICE = Decimal("1.0000")


class ClubOwnershipError(ValueError):
    pass


class ClubOwnershipNotFoundError(ClubOwnershipError):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class ClubOwnershipService:
    session: Session
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()

    def get_ownership_view(self, *, club_id: str, user: User) -> ClubOwnershipView:
        club = self._require_club(club_id)
        token, treasury, governance = self._ensure_state(club_id)
        proposals = self._club_proposals(club_id)
        return ClubOwnershipView(
            club_id=club.id,
            club_name=club.club_name,
            token=self._token_view(token, treasury=treasury),
            my_holding=self._holding_view(self._holding(user.id, club_id)),
            governance=self._governance_view(governance),
            treasury=self._treasury_view(treasury),
            proposals=[self._proposal_view(item) for item in proposals],
        )

    def get_treasury_view(self, *, club_id: str) -> ClubTreasuryView:
        self._require_club(club_id)
        _, treasury, _ = self._ensure_state(club_id)
        return self._treasury_view(treasury)

    def list_user_club_portfolio(self, *, user: User) -> ClubPortfolioView:
        """Every club in which ``user`` holds ownership tokens, valued live.

        Read-only. This is the D -> B join: the portfolio surface folds these
        club-share positions in alongside player holdings.
        """
        holdings = list(
            self.session.scalars(
                select(ClubHolding)
                .where(ClubHolding.user_id == user.id)
                .order_by(ClubHolding.updated_at.desc())
            ).all()
        )
        views: list[ClubPortfolioHoldingView] = []
        total_market = Decimal("0.0000")
        total_cost = Decimal("0.0000")
        for holding in holdings:
            tokens = int(holding.tokens_owned)
            if tokens <= 0:
                continue
            club = self.session.get(ClubProfile, holding.club_id)
            if club is None:
                continue
            token, treasury, _ = self._ensure_state(holding.club_id)
            share_price = Decimal(token.price).quantize(DECIMAL_QUANTUM)
            avg_price = Decimal(holding.avg_price).quantize(DECIMAL_QUANTUM)
            market_value = (share_price * Decimal(tokens)).quantize(DECIMAL_QUANTUM)
            cost_basis = (avg_price * Decimal(tokens)).quantize(DECIMAL_QUANTUM)
            unrealized = (market_value - cost_basis).quantize(DECIMAL_QUANTUM)
            unrealized_pct = (
                float((unrealized / cost_basis) * Decimal("100"))
                if cost_basis > Decimal("0.0000")
                else None
            )
            circulating = int(token.circulating_supply)
            ownership_pct = (
                float((Decimal(tokens) / Decimal(circulating)) * Decimal("100"))
                if circulating > 0
                else None
            )
            total_market += market_value
            total_cost += cost_basis
            views.append(
                ClubPortfolioHoldingView(
                    club_id=club.id,
                    club_name=club.club_name,
                    tokens_owned=tokens,
                    avg_price_coin=avg_price,
                    share_price_coin=share_price,
                    market_value_coin=market_value,
                    cost_basis_coin=cost_basis,
                    unrealized_pl_coin=unrealized,
                    unrealized_pl_pct=unrealized_pct,
                    reward_tokens_earned=int(holding.reward_tokens_earned),
                    holder_count=int(token.holder_count),
                    circulating_supply=circulating,
                    total_supply=int(token.total_supply),
                    ownership_pct=ownership_pct,
                    performance_score=Decimal(token.performance_score).quantize(DECIMAL_QUANTUM),
                    win_rate=Decimal(token.win_rate).quantize(DECIMAL_QUANTUM),
                    fan_demand_score=Decimal(token.fan_demand_score).quantize(DECIMAL_QUANTUM),
                    treasury_balance_coin=Decimal(treasury.balance_coin).quantize(DECIMAL_QUANTUM),
                    governance_enabled=bool(token.governance_enabled),
                    metadata_json=dict(holding.metadata_json or {}),
                )
            )
        return ClubPortfolioView(
            club_count=len(views),
            total_market_value_coin=total_market.quantize(DECIMAL_QUANTUM),
            total_cost_basis_coin=total_cost.quantize(DECIMAL_QUANTUM),
            total_unrealized_pl_coin=(total_market - total_cost).quantize(DECIMAL_QUANTUM),
            holdings=views,
        )

    def buy_tokens(self, *, club_id: str, buyer: User, quantity: int) -> ClubTokenTradeResultView:
        if quantity <= 0:
            raise ClubOwnershipError("Token quantity must be positive.")
        self._require_club(club_id)
        token, treasury, _ = self._ensure_state(club_id)
        available_supply = max(int(token.total_supply) - int(token.circulating_supply), 0)
        if quantity > available_supply:
            raise ClubOwnershipError("Not enough club token supply is available.")

        unit_price = Decimal(token.price).quantize(DECIMAL_QUANTUM)
        gross = (unit_price * Decimal(quantity)).quantize(DECIMAL_QUANTUM)
        reference = f"club-token-buy:{club_id}:{buyer.id}:{uuid4().hex}"
        buyer_account = self.wallet_service.get_user_account(self.session, buyer, LedgerUnit.COIN)
        club_account = self.wallet_service.ensure_club_treasury_account(self.session, club_id, LedgerUnit.COIN)
        try:
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    self._posting(buyer_account, -gross),
                    self._posting(club_account, gross),
                ],
                reason=LedgerEntryReason.TRADE_SETTLEMENT,
                source_tag=LedgerSourceTag.CLUB_SALE_PURCHASE,
                transaction_type=LedgerTransactionType.TRADE_BUY,
                reference=reference,
                description=f"Purchased {quantity} club ownership tokens.",
                external_reference=reference,
                actor=buyer,
                idempotency_key=reference,
                metadata={"club_id": club_id, "quantity": quantity, "unit_price": str(unit_price)},
            )
        except InsufficientBalanceError as exc:
            raise ClubOwnershipError("Wallet balance is too low for this token purchase.") from exc

        holding = self._holding(buyer.id, club_id, create=True)
        previous_tokens = int(holding.tokens_owned)
        new_total = previous_tokens + quantity
        if new_total <= 0:
            raise ClubOwnershipError("Unable to resolve token position.")
        holding.avg_price = (
            ((Decimal(holding.avg_price) * Decimal(previous_tokens)) + gross) / Decimal(new_total)
        ).quantize(DECIMAL_QUANTUM)
        holding.tokens_owned = new_total
        token.circulating_supply = int(token.circulating_supply) + quantity
        if previous_tokens == 0:
            token.holder_count = int(token.holder_count) + 1
        self._record_treasury_flow(
            treasury=treasury,
            club_id=club_id,
            reference_key=reference,
            entry_type="token_purchase",
            direction="inflow",
            amount=gross,
            summary=f"{self._user_label(buyer)} bought {quantity} club tokens.",
            metadata={"buyer_user_id": buyer.id, "quantity": quantity, "unit_price": str(unit_price)},
        )
        self._adjust_fan_demand(token=token, quantity=quantity, direction="buy")
        self._reprice_token(token=token, treasury=treasury)
        self.session.flush()
        return ClubTokenTradeResultView(
            club_id=club_id,
            direction="buy",
            quantity=quantity,
            unit_price=unit_price,
            gross_amount_coin=gross,
            token=self._token_view(token, treasury=treasury),
            holding=self._holding_view(holding),
            treasury=self._treasury_view(treasury),
        )

    def sell_tokens(self, *, club_id: str, seller: User, quantity: int) -> ClubTokenTradeResultView:
        if quantity <= 0:
            raise ClubOwnershipError("Token quantity must be positive.")
        self._require_club(club_id)
        token, treasury, _ = self._ensure_state(club_id)
        holding = self._holding(seller.id, club_id)
        if holding is None or int(holding.tokens_owned) < quantity:
            raise ClubOwnershipError("You do not hold enough club tokens to sell that amount.")

        unit_price = Decimal(token.price).quantize(DECIMAL_QUANTUM)
        gross = (unit_price * Decimal(quantity)).quantize(DECIMAL_QUANTUM)
        if Decimal(treasury.balance_coin) < gross:
            raise ClubOwnershipError("Club treasury liquidity is too low to buy back these tokens.")

        reference = f"club-token-sell:{club_id}:{seller.id}:{uuid4().hex}"
        seller_account = self.wallet_service.get_user_account(self.session, seller, LedgerUnit.COIN)
        club_account = self.wallet_service.ensure_club_treasury_account(self.session, club_id, LedgerUnit.COIN)
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                self._posting(seller_account, gross),
                self._posting(club_account, -gross),
            ],
            reason=LedgerEntryReason.TRADE_SETTLEMENT,
            source_tag=LedgerSourceTag.CLUB_SALE_SALE,
            transaction_type=LedgerTransactionType.TRADE_SELL,
            reference=reference,
            description=f"Sold {quantity} club ownership tokens.",
            external_reference=reference,
            actor=seller,
            idempotency_key=reference,
            metadata={"club_id": club_id, "quantity": quantity, "unit_price": str(unit_price)},
        )

        holding.tokens_owned = int(holding.tokens_owned) - quantity
        if int(holding.tokens_owned) == 0:
            holding.avg_price = Decimal("0.0000")
            token.holder_count = max(int(token.holder_count) - 1, 0)
        token.circulating_supply = max(int(token.circulating_supply) - quantity, 0)
        self._record_treasury_flow(
            treasury=treasury,
            club_id=club_id,
            reference_key=reference,
            entry_type="token_sale",
            direction="outflow",
            amount=gross,
            summary=f"{self._user_label(seller)} sold {quantity} club tokens.",
            metadata={"seller_user_id": seller.id, "quantity": quantity, "unit_price": str(unit_price)},
        )
        self._adjust_fan_demand(token=token, quantity=quantity, direction="sell")
        self._reprice_token(token=token, treasury=treasury)
        self.session.flush()
        return ClubTokenTradeResultView(
            club_id=club_id,
            direction="sell",
            quantity=quantity,
            unit_price=unit_price,
            gross_amount_coin=gross,
            token=self._token_view(token, treasury=treasury),
            holding=self._holding_view(holding),
            treasury=self._treasury_view(treasury),
        )

    def create_proposal(
        self,
        *,
        club_id: str,
        proposer: User,
        payload: ClubGovernanceProposalRequest,
    ) -> ClubGovernanceActionView:
        self._require_club(club_id)
        token, _, governance = self._ensure_state(club_id)
        if not token.governance_enabled:
            raise ClubOwnershipError("Club governance is disabled for this token.")
        proposer_holding = self._holding(proposer.id, club_id)
        if proposer_holding is None or int(proposer_holding.tokens_owned) < int(payload.minimum_tokens_required):
            raise ClubOwnershipError("You do not hold enough tokens to create this proposal.")

        quorum = payload.quorum_token_weight
        if quorum is None:
            quorum = max(1, int(max(int(token.circulating_supply), 1) * 0.1))
        proposal = GovernanceProposal(
            club_id=club_id,
            proposer_user_id=proposer.id,
            scope=GovernanceProposalScope.CLUB,
            status=GovernanceProposalStatus.OPEN,
            title=payload.title,
            summary=payload.summary,
            category=f"club_{payload.proposal_kind}",
            voting_starts_at_iso=utcnow().isoformat(),
            voting_ends_at_iso=payload.voting_ends_at_iso,
            minimum_tokens_required=int(payload.minimum_tokens_required),
            quorum_token_weight=int(quorum),
            metadata_json={
                "source": "club_ownership_dao",
                "proposal_kind": payload.proposal_kind,
                "governance_payload": {
                    "formation": payload.formation,
                    "playstyle": payload.playstyle,
                    "budget_rules_json": dict(payload.budget_rules_json or {}),
                    "transfer_policy_json": dict(payload.transfer_policy_json or {}),
                },
                **dict(payload.metadata_json or {}),
            },
        )
        self.session.add(proposal)
        self.session.flush()
        governance.active_proposal_id = proposal.id
        self.session.flush()
        return ClubGovernanceActionView(
            proposal=self._proposal_view(proposal),
            vote=None,
            governance=self._governance_view(governance),
            executed=False,
            execution_summary=None,
        )

    def vote_on_proposal(
        self,
        *,
        club_id: str,
        voter: User,
        payload: ClubGovernanceVoteRequest,
    ) -> ClubGovernanceActionView:
        self._require_club(club_id)
        _, _, governance = self._ensure_state(club_id)
        proposal = self._require_proposal(club_id=club_id, proposal_id=payload.proposal_id)
        if proposal.status != GovernanceProposalStatus.OPEN:
            raise ClubOwnershipError("This proposal is no longer open for voting.")
        holding = self._holding(voter.id, club_id)
        if holding is None or int(holding.tokens_owned) < max(int(proposal.minimum_tokens_required), 1):
            raise ClubOwnershipError("You do not hold enough tokens to vote on this proposal.")

        choice = self._vote_choice(payload.choice)
        vote = self.session.scalar(
            select(GovernanceVote).where(
                GovernanceVote.proposal_id == proposal.id,
                GovernanceVote.voter_user_id == voter.id,
            )
        )
        if vote is None:
            vote = GovernanceVote(
                proposal_id=proposal.id,
                voter_user_id=voter.id,
                club_id=club_id,
                choice=choice,
            )
            self.session.add(vote)
        vote.choice = choice
        vote.token_weight = int(holding.tokens_owned)
        vote.influence_weight = int(holding.tokens_owned)
        vote.comment = payload.comment
        vote.metadata_json = {"source": "club_ownership_dao"}
        self.session.flush()

        self._refresh_vote_totals(proposal)
        executed, execution_summary = self._maybe_finalize_proposal(proposal)
        self.session.flush()
        return ClubGovernanceActionView(
            proposal=self._proposal_view(proposal),
            vote=self._vote_view(vote),
            governance=self._governance_view(governance),
            executed=executed,
            execution_summary=execution_summary,
        )

    def settle_match_result(
        self,
        *,
        match_id: str,
        home_club_id: str | None,
        away_club_id: str | None,
        home_score: int,
        away_score: int,
    ) -> None:
        for club_id in (home_club_id, away_club_id):
            if club_id is None:
                continue
            token, treasury, _ = self._ensure_state(club_id)
            payout = self._match_payout(
                club_id=club_id,
                home_club_id=home_club_id,
                away_club_id=away_club_id,
                home_score=home_score,
                away_score=away_score,
            )
            if payout > Decimal("0.0000"):
                self._credit_club_treasury(
                    club_id=club_id,
                    amount=payout,
                    reference_key=f"club-match-winnings:{match_id}:{club_id}",
                    description="Club DAO match winnings.",
                )
                self._record_treasury_flow(
                    treasury=treasury,
                    club_id=club_id,
                    reference_key=f"club-match-winnings:{match_id}:{club_id}",
                    entry_type="match_winnings",
                    direction="inflow",
                    amount=payout,
                    summary=f"Match winnings credited from result {home_score}-{away_score}.",
                    metadata={"match_id": match_id, "home_score": home_score, "away_score": away_score},
                )
                self._maybe_distribute_dividends(
                    club_id=club_id,
                    treasury=treasury,
                    source_amount=payout,
                    match_id=match_id,
                )
            self._apply_performance_result(
                token=token,
                club_id=club_id,
                home_club_id=home_club_id,
                away_club_id=away_club_id,
                home_score=home_score,
                away_score=away_score,
            )
            self._reprice_token(token=token, treasury=treasury)
        self.session.flush()

    def _ensure_state(self, club_id: str) -> tuple[ClubToken, ClubTreasury, ClubGovernanceState]:
        token = self.session.scalar(select(ClubToken).where(ClubToken.club_id == club_id))
        if token is None:
            token = ClubToken(club_id=club_id, price=BASE_TOKEN_PRICE, metadata_json={"matches_played": 0, "wins": 0, "draws": 0, "losses": 0})
            self.session.add(token)
            self.session.flush()
        treasury = self.session.scalar(select(ClubTreasury).where(ClubTreasury.club_id == club_id))
        if treasury is None:
            treasury = ClubTreasury(club_id=club_id)
            self.session.add(treasury)
            self.session.flush()
        governance = self.session.scalar(select(ClubGovernanceState).where(ClubGovernanceState.club_id == club_id))
        if governance is None:
            governance = ClubGovernanceState(
                club_id=club_id,
                budget_rules_json={"max_transfer_ratio_bps": 3500},
                transfer_policy_json={"fan_vote_required": True},
            )
            self.session.add(governance)
            self.session.flush()
        self.wallet_service.ensure_club_treasury_account(self.session, club_id, LedgerUnit.COIN)
        token.treasury_balance_snapshot = Decimal(treasury.balance_coin).quantize(DECIMAL_QUANTUM)
        self._reprice_token(token=token, treasury=treasury)
        return token, treasury, governance

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise ClubOwnershipNotFoundError("Club was not found.")
        return club

    def _require_proposal(self, *, club_id: str, proposal_id: str) -> GovernanceProposal:
        proposal = self.session.get(GovernanceProposal, proposal_id)
        if proposal is None or proposal.club_id != club_id:
            raise ClubOwnershipNotFoundError("Governance proposal was not found.")
        return proposal

    def _holding(self, user_id: str, club_id: str, *, create: bool = False) -> ClubHolding | None:
        holding = self.session.scalar(
            select(ClubHolding).where(
                ClubHolding.user_id == user_id,
                ClubHolding.club_id == club_id,
            )
        )
        if holding is None and create:
            holding = ClubHolding(user_id=user_id, club_id=club_id)
            self.session.add(holding)
            self.session.flush()
        return holding

    def _club_proposals(self, club_id: str) -> list[GovernanceProposal]:
        return list(
            self.session.scalars(
                select(GovernanceProposal)
                .where(GovernanceProposal.club_id == club_id)
                .order_by(GovernanceProposal.updated_at.desc(), GovernanceProposal.created_at.desc())
                .limit(12)
            ).all()
        )

    def _treasury_entries(self, club_id: str) -> list[ClubTreasuryEntry]:
        return list(
            self.session.scalars(
                select(ClubTreasuryEntry)
                .where(ClubTreasuryEntry.club_id == club_id)
                .order_by(ClubTreasuryEntry.created_at.desc())
                .limit(15)
            ).all()
        )

    def _recent_dividends(self, club_id: str) -> list[ClubDividendDistribution]:
        return list(
            self.session.scalars(
                select(ClubDividendDistribution)
                .where(ClubDividendDistribution.club_id == club_id)
                .order_by(ClubDividendDistribution.created_at.desc())
                .limit(15)
            ).all()
        )

    def _token_view(self, token: ClubToken, *, treasury: ClubTreasury) -> ClubTokenView:
        return ClubTokenView(
            club_id=token.club_id,
            total_supply=int(token.total_supply),
            circulating_supply=int(token.circulating_supply),
            available_supply=max(int(token.total_supply) - int(token.circulating_supply), 0),
            holder_count=int(token.holder_count),
            price=Decimal(token.price).quantize(DECIMAL_QUANTUM),
            governance_enabled=bool(token.governance_enabled),
            performance_score=Decimal(token.performance_score).quantize(DECIMAL_QUANTUM),
            win_rate=Decimal(token.win_rate).quantize(DECIMAL_QUANTUM),
            fan_demand_score=Decimal(token.fan_demand_score).quantize(DECIMAL_QUANTUM),
            treasury_balance_snapshot=Decimal(treasury.balance_coin).quantize(DECIMAL_QUANTUM),
            metadata_json=dict(token.metadata_json or {}),
        )

    @staticmethod
    def _holding_view(holding: ClubHolding | None) -> ClubHoldingView | None:
        if holding is None:
            return None
        return ClubHoldingView(
            user_id=holding.user_id,
            club_id=holding.club_id,
            tokens_owned=int(holding.tokens_owned),
            avg_price=Decimal(holding.avg_price).quantize(DECIMAL_QUANTUM),
            reward_tokens_earned=int(holding.reward_tokens_earned),
            metadata_json=dict(holding.metadata_json or {}),
        )

    @staticmethod
    def _governance_view(governance: ClubGovernanceState) -> ClubGovernanceStateView:
        return ClubGovernanceStateView(
            club_id=governance.club_id,
            formation=governance.formation,
            playstyle=governance.playstyle,
            budget_rules_json=dict(governance.budget_rules_json or {}),
            transfer_policy_json=dict(governance.transfer_policy_json or {}),
            fan_mandate_summary=governance.fan_mandate_summary,
            active_proposal_id=governance.active_proposal_id,
            last_executed_proposal_id=governance.last_executed_proposal_id,
            last_executed_at=governance.last_executed_at,
            metadata_json=dict(governance.metadata_json or {}),
        )

    def _treasury_view(self, treasury: ClubTreasury) -> ClubTreasuryView:
        return ClubTreasuryView(
            club_id=treasury.club_id,
            balance_coin=Decimal(treasury.balance_coin).quantize(DECIMAL_QUANTUM),
            lifetime_inflow_coin=Decimal(treasury.lifetime_inflow_coin).quantize(DECIMAL_QUANTUM),
            lifetime_outflow_coin=Decimal(treasury.lifetime_outflow_coin).quantize(DECIMAL_QUANTUM),
            winnings_pool_coin=Decimal(treasury.winnings_pool_coin).quantize(DECIMAL_QUANTUM),
            sponsorship_pool_coin=Decimal(treasury.sponsorship_pool_coin).quantize(DECIMAL_QUANTUM),
            entry_fee_pool_coin=Decimal(treasury.entry_fee_pool_coin).quantize(DECIMAL_QUANTUM),
            reserve_ratio_bps=int(treasury.reserve_ratio_bps),
            profit_share_bps=int(treasury.profit_share_bps),
            governance_budget_ratio_bps=int(treasury.governance_budget_ratio_bps),
            metadata_json=dict(treasury.metadata_json or {}),
            recent_entries=[self._entry_view(item) for item in self._treasury_entries(treasury.club_id)],
            recent_dividends=[self._dividend_view(item) for item in self._recent_dividends(treasury.club_id)],
        )

    @staticmethod
    def _entry_view(entry: ClubTreasuryEntry) -> ClubTreasuryEntryView:
        return ClubTreasuryEntryView(
            id=entry.id,
            reference_key=entry.reference_key,
            entry_type=entry.entry_type,
            direction=entry.direction,
            amount_coin=Decimal(entry.amount_coin).quantize(DECIMAL_QUANTUM),
            balance_after_coin=Decimal(entry.balance_after_coin).quantize(DECIMAL_QUANTUM),
            summary=entry.summary,
            proposal_id=entry.proposal_id,
            created_at=entry.created_at,
            metadata_json=dict(entry.metadata_json or {}),
        )

    @staticmethod
    def _dividend_view(item: ClubDividendDistribution) -> ClubDividendDistributionView:
        return ClubDividendDistributionView(
            id=item.id,
            reference_key=item.reference_key,
            user_id=item.user_id,
            gross_amount_coin=Decimal(item.gross_amount_coin).quantize(DECIMAL_QUANTUM),
            tokens_snapshot=int(item.tokens_snapshot),
            created_at=item.created_at,
            metadata_json=dict(item.metadata_json or {}),
        )

    @staticmethod
    def _proposal_view(item: GovernanceProposal) -> ClubGovernanceProposalView:
        return ClubGovernanceProposalView.model_validate(item, from_attributes=True)

    @staticmethod
    def _vote_view(item: GovernanceVote) -> ClubGovernanceVoteView:
        return ClubGovernanceVoteView.model_validate(item, from_attributes=True)

    def _refresh_vote_totals(self, proposal: GovernanceProposal) -> None:
        votes = list(
            self.session.scalars(
                select(GovernanceVote).where(GovernanceVote.proposal_id == proposal.id)
            ).all()
        )
        proposal.yes_weight = sum(item.influence_weight for item in votes if item.choice == GovernanceVoteChoice.YES)
        proposal.no_weight = sum(item.influence_weight for item in votes if item.choice == GovernanceVoteChoice.NO)
        proposal.abstain_weight = sum(item.influence_weight for item in votes if item.choice == GovernanceVoteChoice.ABSTAIN)
        proposal.unique_voter_count = len(votes)

    def _maybe_finalize_proposal(self, proposal: GovernanceProposal) -> tuple[bool, str | None]:
        if proposal.status != GovernanceProposalStatus.OPEN:
            return False, proposal.result_summary
        total_weight = int(proposal.yes_weight) + int(proposal.no_weight) + int(proposal.abstain_weight)
        quorum_target = max(int(proposal.quorum_token_weight), max(int(proposal.minimum_tokens_required), 1))
        quorum_met = total_weight >= quorum_target
        voting_closed = self._is_voting_closed(proposal.voting_ends_at_iso)
        passed = quorum_met and int(proposal.yes_weight) > int(proposal.no_weight)
        if not passed and not voting_closed:
            return False, None
        governance = self.session.scalar(select(ClubGovernanceState).where(ClubGovernanceState.club_id == proposal.club_id))
        if governance is None:
            raise ClubOwnershipNotFoundError("Club governance state was not found.")
        if passed:
            proposal.status = GovernanceProposalStatus.ACCEPTED
            summary = self._execute_proposal(proposal, governance)
            proposal.result_summary = summary
            return True, summary
        proposal.status = GovernanceProposalStatus.REJECTED
        governance.active_proposal_id = None
        summary = "Voting closed without enough support to pass."
        proposal.result_summary = summary
        return False, summary

    def _execute_proposal(self, proposal: GovernanceProposal, governance: ClubGovernanceState) -> str:
        payload = dict(proposal.metadata_json or {}).get("governance_payload") or {}
        formation = str(payload.get("formation") or governance.formation).strip() or governance.formation
        playstyle = str(payload.get("playstyle") or governance.playstyle).strip() or governance.playstyle
        budget_rules = dict(payload.get("budget_rules_json") or governance.budget_rules_json or {})
        transfer_policy = dict(payload.get("transfer_policy_json") or governance.transfer_policy_json or {})
        governance.formation = formation
        governance.playstyle = playstyle
        governance.budget_rules_json = budget_rules
        governance.transfer_policy_json = transfer_policy
        governance.active_proposal_id = None
        governance.last_executed_proposal_id = proposal.id
        governance.last_executed_at = utcnow()
        governance.fan_mandate_summary = f"Fans mandated {formation} with a {playstyle} approach."
        governance.metadata_json = {
            **dict(governance.metadata_json or {}),
            "last_proposal_kind": dict(proposal.metadata_json or {}).get("proposal_kind"),
            "last_execution_payload": payload,
        }
        return governance.fan_mandate_summary

    def _record_treasury_flow(
        self,
        *,
        treasury: ClubTreasury,
        club_id: str,
        reference_key: str,
        entry_type: str,
        direction: str,
        amount: Decimal,
        summary: str,
        metadata: dict[str, object] | None = None,
        proposal_id: str | None = None,
    ) -> ClubTreasuryEntry | None:
        if self.session.scalar(select(ClubTreasuryEntry).where(ClubTreasuryEntry.reference_key == reference_key)) is not None:
            return None
        normalized = Decimal(amount).quantize(DECIMAL_QUANTUM)
        if normalized <= Decimal("0.0000"):
            return None
        if direction == "inflow":
            treasury.balance_coin = (Decimal(treasury.balance_coin) + normalized).quantize(DECIMAL_QUANTUM)
            treasury.lifetime_inflow_coin = (Decimal(treasury.lifetime_inflow_coin) + normalized).quantize(DECIMAL_QUANTUM)
        else:
            if Decimal(treasury.balance_coin) < normalized:
                raise ClubOwnershipError("Treasury balance is too low for this movement.")
            treasury.balance_coin = (Decimal(treasury.balance_coin) - normalized).quantize(DECIMAL_QUANTUM)
            treasury.lifetime_outflow_coin = (Decimal(treasury.lifetime_outflow_coin) + normalized).quantize(DECIMAL_QUANTUM)
        if entry_type == "match_winnings":
            delta = normalized if direction == "inflow" else -normalized
            treasury.winnings_pool_coin = (Decimal(treasury.winnings_pool_coin) + delta).quantize(DECIMAL_QUANTUM)
        entry = ClubTreasuryEntry(
            treasury_id=treasury.id,
            club_id=club_id,
            proposal_id=proposal_id,
            reference_key=reference_key,
            entry_type=entry_type,
            direction=direction,
            amount_coin=normalized,
            balance_after_coin=Decimal(treasury.balance_coin).quantize(DECIMAL_QUANTUM),
            summary=summary,
            metadata_json=dict(metadata or {}),
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def _adjust_fan_demand(self, *, token: ClubToken, quantity: int, direction: str) -> None:
        step = (Decimal(quantity) / Decimal("5000")).quantize(DECIMAL_QUANTUM)
        demand = Decimal(token.fan_demand_score)
        if direction == "buy":
            demand += max(step, Decimal("0.0100"))
        else:
            demand -= max(step, Decimal("0.0100"))
        token.fan_demand_score = max(demand, Decimal("-1.5000")).quantize(DECIMAL_QUANTUM)

    def _reprice_token(self, *, token: ClubToken, treasury: ClubTreasury) -> None:
        treasury_per_token = Decimal(treasury.balance_coin) / Decimal(max(int(token.circulating_supply), 1))
        performance_component = Decimal(token.performance_score) * Decimal("0.1800")
        win_component = Decimal(token.win_rate) * Decimal("1.3500")
        demand_component = Decimal(token.fan_demand_score) * Decimal("0.2800")
        treasury_component = min(treasury_per_token, Decimal("2.5000")) * Decimal("0.1200")
        price = (Decimal("1.0000") + performance_component + win_component + demand_component + treasury_component).quantize(DECIMAL_QUANTUM)
        token.price = max(price, MIN_TOKEN_PRICE)
        token.treasury_balance_snapshot = Decimal(treasury.balance_coin).quantize(DECIMAL_QUANTUM)

    def _match_payout(
        self,
        *,
        club_id: str,
        home_club_id: str | None,
        away_club_id: str | None,
        home_score: int,
        away_score: int,
    ) -> Decimal:
        snapshot = ClubFinanceService(self.session).live_ops_service.multiplier_snapshot()
        if home_score == away_score:
            return (DRAW_BONUS * Decimal(str(snapshot.match_income_multiplier))).quantize(DECIMAL_QUANTUM)
        winner_club_id = home_club_id if home_score > away_score else away_club_id
        if club_id != winner_club_id:
            return Decimal("0.0000")
        return (WIN_BONUS * Decimal(str(snapshot.match_income_multiplier))).quantize(DECIMAL_QUANTUM)

    def _credit_club_treasury(self, *, club_id: str, amount: Decimal, reference_key: str, description: str) -> None:
        if self.session.scalar(select(ClubTreasuryEntry).where(ClubTreasuryEntry.reference_key == reference_key)) is not None:
            return
        club_account = self.wallet_service.ensure_club_treasury_account(self.session, club_id, LedgerUnit.COIN)
        source_account = self.wallet_service.ensure_operations_account(self.session, LedgerUnit.COIN)
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                self._posting(club_account, Decimal(amount).quantize(DECIMAL_QUANTUM)),
                self._posting(source_account, -Decimal(amount).quantize(DECIMAL_QUANTUM)),
            ],
            reason=LedgerEntryReason.COMPETITION_REWARD,
            source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
            transaction_type=LedgerTransactionType.MATCH_REWARD,
            reference=reference_key,
            description=description,
            external_reference=reference_key,
            idempotency_key=reference_key,
            metadata={"club_id": club_id, "amount": str(amount)},
        )

    def _maybe_distribute_dividends(self, *, club_id: str, treasury: ClubTreasury, source_amount: Decimal, match_id: str) -> None:
        holdings = [item for item in self.session.scalars(select(ClubHolding).where(ClubHolding.club_id == club_id)).all() if int(item.tokens_owned) > 0]
        if not holdings:
            return
        dividend_pool = (Decimal(source_amount) * Decimal(int(treasury.profit_share_bps)) / Decimal("10000")).quantize(DECIMAL_QUANTUM)
        if dividend_pool <= Decimal("0.0000") or Decimal(treasury.balance_coin) < dividend_pool:
            return
        total_tokens = sum(int(item.tokens_owned) for item in holdings)
        if total_tokens <= 0:
            return
        club_account = self.wallet_service.ensure_club_treasury_account(self.session, club_id, LedgerUnit.COIN)
        paid_total = Decimal("0.0000")
        remaining = dividend_pool
        for index, holding in enumerate(holdings):
            if index == len(holdings) - 1:
                share = remaining
            else:
                share = (dividend_pool * Decimal(int(holding.tokens_owned)) / Decimal(total_tokens)).quantize(DECIMAL_QUANTUM)
                remaining -= share
            if share <= Decimal("0.0000"):
                continue
            user = self.session.get(User, holding.user_id)
            if user is None:
                continue
            reference_key = f"club-dividend:{match_id}:{club_id}:{holding.user_id}"
            if self.session.scalar(
                select(ClubDividendDistribution).where(
                    ClubDividendDistribution.reference_key == f"club-dividend:{match_id}:{club_id}",
                    ClubDividendDistribution.user_id == holding.user_id,
                )
            ) is not None:
                continue
            user_account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.COIN)
            self.wallet_service.append_transaction(
                self.session,
                postings=[
                    self._posting(user_account, share),
                    self._posting(club_account, -share),
                ],
                reason=LedgerEntryReason.COMPETITION_REWARD,
                source_tag=LedgerSourceTag.PLAYER_SHARE_DIVIDEND,
                transaction_type=LedgerTransactionType.MATCH_REWARD,
                reference=reference_key,
                description="Club DAO dividend distribution.",
                external_reference=reference_key,
                idempotency_key=reference_key,
                metadata={"club_id": club_id, "match_id": match_id, "tokens_snapshot": int(holding.tokens_owned)},
            )
            self.session.add(
                ClubDividendDistribution(
                    treasury_id=treasury.id,
                    club_id=club_id,
                    user_id=holding.user_id,
                    reference_key=f"club-dividend:{match_id}:{club_id}",
                    gross_amount_coin=share,
                    tokens_snapshot=int(holding.tokens_owned),
                    metadata_json={"match_id": match_id},
                )
            )
            paid_total += share
        if paid_total > Decimal("0.0000"):
            self._record_treasury_flow(
                treasury=treasury,
                club_id=club_id,
                reference_key=f"club-dividend:{match_id}:{club_id}:aggregate",
                entry_type="dividend_distribution",
                direction="outflow",
                amount=paid_total,
                summary="Club DAO dividend distribution.",
                metadata={"match_id": match_id},
            )

    def _apply_performance_result(
        self,
        *,
        token: ClubToken,
        club_id: str,
        home_club_id: str | None,
        away_club_id: str | None,
        home_score: int,
        away_score: int,
    ) -> None:
        metadata = dict(token.metadata_json or {})
        matches_played = int(metadata.get("matches_played") or 0) + 1
        wins = int(metadata.get("wins") or 0)
        draws = int(metadata.get("draws") or 0)
        losses = int(metadata.get("losses") or 0)
        club_score = home_score if club_id == home_club_id else away_score
        opponent_score = away_score if club_id == home_club_id else home_score
        outcome_signal = Decimal("0.0000")
        if club_score > opponent_score:
            wins += 1
            outcome_signal = Decimal("1.0000")
            token.fan_demand_score = (Decimal(token.fan_demand_score) + Decimal("0.0600")).quantize(DECIMAL_QUANTUM)
        elif club_score == opponent_score:
            draws += 1
            outcome_signal = Decimal("0.1200")
            token.fan_demand_score = (Decimal(token.fan_demand_score) + Decimal("0.0150")).quantize(DECIMAL_QUANTUM)
        else:
            losses += 1
            outcome_signal = Decimal("-0.8500")
            token.fan_demand_score = (Decimal(token.fan_demand_score) - Decimal("0.0500")).quantize(DECIMAL_QUANTUM)
        token.performance_score = ((Decimal(token.performance_score) * Decimal("0.78")) + outcome_signal).quantize(DECIMAL_QUANTUM)
        token.win_rate = (Decimal(wins) / Decimal(matches_played)).quantize(DECIMAL_QUANTUM)
        token.metadata_json = {
            **metadata,
            "matches_played": matches_played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "last_result": {"club_score": club_score, "opponent_score": opponent_score},
        }

    @staticmethod
    def _vote_choice(choice: str) -> GovernanceVoteChoice:
        normalized = str(choice or "").strip().lower()
        try:
            return GovernanceVoteChoice(normalized)
        except ValueError as exc:
            raise ClubOwnershipError("Vote choice must be yes, no, or abstain.") from exc

    @staticmethod
    def _is_voting_closed(value: str | None) -> bool:
        if not value:
            return False
        try:
            resolved = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        if resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=UTC)
        return resolved <= utcnow()

    @staticmethod
    def _posting(account, amount: Decimal):
        from app.wallets.service import LedgerPosting

        return LedgerPosting(account=account, amount=Decimal(amount).quantize(DECIMAL_QUANTUM))

    @staticmethod
    def _user_label(user: User) -> str:
        return str(user.display_name or user.username or user.email or user.id)


__all__ = ["ClubOwnershipError", "ClubOwnershipNotFoundError", "ClubOwnershipService"]
