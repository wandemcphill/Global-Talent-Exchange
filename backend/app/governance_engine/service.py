from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.club_dynasty_progress import ClubDynastyProgress
from backend.app.models.club_infra import ClubSupporterHolding
from backend.app.models.club_profile import ClubProfile
from backend.app.models.club_sale_market import ClubSaleTransfer
from backend.app.models.creator_share_market import CreatorClubShareHolding, CreatorClubShareMarket
from backend.app.models.governance_engine import (
    GovernanceProposal,
    GovernanceProposalScope,
    GovernanceProposalStatus,
    GovernanceVote,
    GovernanceVoteChoice,
)
from backend.app.models.story_feed import StoryFeedItem
from backend.app.models.user import User, UserRole
from backend.app.services.club_governance_policy import (
    fully_diluted_governance_shares,
    governance_policy_from_metadata,
    holder_cap_share_count,
    owner_approval_required,
    ownership_bps,
    quorum_share_count,
)


class GovernanceEngineError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class GovernanceEligibilityState:
    eligible: bool
    reason: str | None
    token_weight: int
    influence_weight: int
    share_count: int
    ownership_bps: int
    is_owner: bool
    governance_unit: str
    supporting_record: object | None = None


@dataclass(slots=True)
class GovernanceEngineService:
    session: Session

    def list_proposals(self, *, status: GovernanceProposalStatus | None = None, club_id: str | None = None) -> list[GovernanceProposal]:
        stmt = select(GovernanceProposal).order_by(GovernanceProposal.created_at.desc())
        if status is not None:
            stmt = stmt.where(GovernanceProposal.status == status)
        if club_id is not None:
            stmt = stmt.where(GovernanceProposal.club_id == club_id)
        return list(self.session.scalars(stmt).all())

    def get_proposal(self, proposal_id: str) -> GovernanceProposal:
        proposal = self.session.get(GovernanceProposal, proposal_id)
        if proposal is None:
            raise GovernanceEngineError("Governance proposal was not found.")
        return proposal

    def list_votes(self, proposal_id: str) -> list[GovernanceVote]:
        stmt = select(GovernanceVote).where(GovernanceVote.proposal_id == proposal_id).order_by(GovernanceVote.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def my_vote(self, *, proposal_id: str, user_id: str) -> GovernanceVote | None:
        return self.session.scalar(select(GovernanceVote).where(GovernanceVote.proposal_id == proposal_id, GovernanceVote.voter_user_id == user_id))

    def _platform_holding_for(self, *, user: User) -> ClubSupporterHolding | None:
        stmt = (
            select(ClubSupporterHolding)
            .where(ClubSupporterHolding.user_id == user.id)
            .order_by(ClubSupporterHolding.influence_points.desc(), ClubSupporterHolding.token_balance.desc())
        )
        return self.session.scalars(stmt).first()

    def _club_voting_state(
        self,
        *,
        club_id: str,
        user: User,
        minimum_tokens_required: int,
    ) -> GovernanceEligibilityState:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            return GovernanceEligibilityState(
                eligible=False,
                reason="Club governance target was not found.",
                token_weight=0,
                influence_weight=0,
                share_count=0,
                ownership_bps=0,
                is_owner=False,
                governance_unit="creator_club_shares",
            )
        market = self.session.scalar(
            select(CreatorClubShareMarket).where(CreatorClubShareMarket.club_id == club_id)
        )
        if club.owner_user_id == user.id:
            owner_weight = int(market.creator_controlled_shares) if market is not None else 1
            total_shares = self._club_total_governance_shares(market)
            return GovernanceEligibilityState(
                eligible=True,
                reason=None,
                token_weight=owner_weight,
                influence_weight=owner_weight,
                share_count=owner_weight,
                ownership_bps=ownership_bps(share_count=owner_weight, total_share_count=total_shares),
                is_owner=True,
                governance_unit="creator_club_shares",
                supporting_record=market,
            )

        if market is None:
            return GovernanceEligibilityState(
                eligible=False,
                reason="This club does not have an active canonical share governance market yet.",
                token_weight=0,
                influence_weight=0,
                share_count=0,
                ownership_bps=0,
                is_owner=False,
                governance_unit="creator_club_shares",
            )

        holding = self.session.scalar(
            select(CreatorClubShareHolding).where(
                CreatorClubShareHolding.club_id == club_id,
                CreatorClubShareHolding.user_id == user.id,
            )
        )
        if holding is None or int(holding.share_count) <= 0:
            return GovernanceEligibilityState(
                eligible=False,
                reason="No canonical club shareholding was found for this user.",
                token_weight=0,
                influence_weight=0,
                share_count=0,
                ownership_bps=0,
                is_owner=False,
                governance_unit="creator_club_shares",
            )
        share_count = int(holding.share_count)
        if share_count < int(minimum_tokens_required):
            return GovernanceEligibilityState(
                eligible=False,
                reason=f"At least {minimum_tokens_required} club shares are required.",
                token_weight=share_count,
                influence_weight=share_count,
                share_count=share_count,
                ownership_bps=ownership_bps(
                    share_count=share_count,
                    total_share_count=self._club_total_governance_shares(market),
                ),
                is_owner=False,
                governance_unit="creator_club_shares",
                supporting_record=holding,
            )
        return GovernanceEligibilityState(
            eligible=True,
            reason=None,
            token_weight=share_count,
            influence_weight=share_count,
            share_count=share_count,
            ownership_bps=ownership_bps(
                share_count=share_count,
                total_share_count=self._club_total_governance_shares(market),
            ),
            is_owner=False,
            governance_unit="creator_club_shares",
            supporting_record=holding,
        )

    def _eligibility_state_for(self, *, proposal: GovernanceProposal, user: User) -> GovernanceEligibilityState:
        if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return GovernanceEligibilityState(
                eligible=True,
                reason=None,
                token_weight=1,
                influence_weight=1,
                share_count=1,
                ownership_bps=0,
                is_owner=False,
                governance_unit="admin_override",
            )
        if proposal.scope == GovernanceProposalScope.CLUB and proposal.club_id:
            return self._club_voting_state(
                club_id=proposal.club_id,
                user=user,
                minimum_tokens_required=int(proposal.minimum_tokens_required),
            )
        holding = self._platform_holding_for(user=user)
        if holding is None:
            return GovernanceEligibilityState(
                eligible=False,
                reason="No supporter holding found for this governance scope.",
                token_weight=0,
                influence_weight=0,
                share_count=0,
                ownership_bps=0,
                is_owner=False,
                governance_unit="supporter_tokens",
            )
        if int(holding.token_balance) < int(proposal.minimum_tokens_required):
            return GovernanceEligibilityState(
                eligible=False,
                reason=f"At least {proposal.minimum_tokens_required} supporter tokens are required.",
                token_weight=int(holding.token_balance),
                influence_weight=int(holding.influence_points or holding.token_balance),
                share_count=int(holding.token_balance),
                ownership_bps=0,
                is_owner=False,
                governance_unit="supporter_tokens",
                supporting_record=holding,
            )
        token_weight = int(holding.token_balance or 0)
        influence_weight = int(holding.influence_points or token_weight)
        return GovernanceEligibilityState(
            eligible=True,
            reason=None,
            token_weight=token_weight,
            influence_weight=influence_weight,
            share_count=token_weight,
            ownership_bps=0,
            is_owner=False,
            governance_unit="supporter_tokens",
            supporting_record=holding,
        )

    def eligibility_for(self, *, proposal: GovernanceProposal, user: User) -> tuple[bool, str | None, object | None]:
        state = self._eligibility_state_for(proposal=proposal, user=user)
        return state.eligible, state.reason, state.supporting_record

    def create_proposal(
        self,
        *,
        proposer: User,
        club_id: str | None,
        scope: GovernanceProposalScope,
        title: str,
        summary: str,
        category: str,
        minimum_tokens_required: int,
        quorum_token_weight: int,
        voting_ends_at_iso: str | None,
        metadata_json: dict[str, object],
    ) -> GovernanceProposal:
        if scope == GovernanceProposalScope.CLUB and not club_id:
            raise GovernanceEngineError("Club governance proposals require a club_id.")
        proposal_metadata = dict(metadata_json or {})
        if scope == GovernanceProposalScope.CLUB and club_id:
            market = self.session.scalar(
                select(CreatorClubShareMarket).where(CreatorClubShareMarket.club_id == club_id)
            )
            policy = governance_policy_from_metadata(
                market.metadata_json if market is not None else {},
                max_shares_per_fan=int(market.max_shares_per_fan) if market is not None else None,
            )
            minimum_tokens_required = max(
                int(minimum_tokens_required),
                int(policy["proposal_share_threshold"]),
            )
            computed_quorum = quorum_share_count(
                total_governance_shares=self._club_total_governance_shares(market),
                quorum_share_bps=int(policy["quorum_share_bps"]),
            )
            quorum_token_weight = max(int(quorum_token_weight), computed_quorum)
            proposal_metadata = {
                **proposal_metadata,
                "governance_unit": "creator_club_shares",
                "vote_weight_model": policy["vote_weight_model"],
                "proposal_share_threshold": int(policy["proposal_share_threshold"]),
                "quorum_share_bps": int(policy["quorum_share_bps"]),
                "market_id": market.id if market is not None else None,
                "anti_takeover_max_holder_bps": int(policy["max_holder_bps"]),
            }
        else:
            proposal_metadata = {
                **proposal_metadata,
                "governance_unit": "supporter_tokens",
                "vote_weight_model": "supporter_influence_points",
            }
        if proposer.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            fake = GovernanceProposal(club_id=club_id, proposer_user_id=proposer.id, scope=scope, title=title, summary=summary, category=category, minimum_tokens_required=minimum_tokens_required, quorum_token_weight=quorum_token_weight)
            eligible, reason, _ = self.eligibility_for(proposal=fake, user=proposer)
            if not eligible:
                raise GovernanceEngineError(reason or "User is not eligible to open this proposal.")
        proposal = GovernanceProposal(
            club_id=club_id,
            proposer_user_id=proposer.id,
            scope=scope,
            status=GovernanceProposalStatus.OPEN,
            title=title,
            summary=summary,
            category=category,
            voting_starts_at_iso=datetime.now(UTC).isoformat(),
            voting_ends_at_iso=voting_ends_at_iso,
            minimum_tokens_required=minimum_tokens_required,
            quorum_token_weight=quorum_token_weight,
            metadata_json=proposal_metadata,
        )
        self.session.add(proposal)
        self.session.flush()
        self._publish_story(
            title=f"Governance proposal opened: {title}",
            body=summary[:240],
            story_type="governance_proposal_opened",
            metadata={"proposal_id": proposal.id, "club_id": club_id, "scope": scope.value},
        )
        self.session.flush()
        return proposal

    def cast_vote(self, *, proposal_id: str, voter: User, choice: GovernanceVoteChoice, comment: str | None = None) -> tuple[GovernanceProposal, GovernanceVote]:
        proposal = self.get_proposal(proposal_id)
        if proposal.status != GovernanceProposalStatus.OPEN:
            raise GovernanceEngineError("Voting is closed for this proposal.")
        state = self._eligibility_state_for(proposal=proposal, user=voter)
        if not state.eligible:
            raise GovernanceEngineError(state.reason or "User is not eligible to vote on this proposal.")
        vote = GovernanceVote(
            proposal_id=proposal.id,
            voter_user_id=voter.id,
            club_id=proposal.club_id,
            choice=choice,
            token_weight=state.token_weight,
            influence_weight=state.influence_weight,
            comment=comment,
            metadata_json={
                "scope": proposal.scope.value,
                "governance_unit": state.governance_unit,
                "ownership_bps": state.ownership_bps,
                "is_owner_vote": state.is_owner,
            },
        )
        self.session.add(vote)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise GovernanceEngineError("You have already voted on this proposal.") from exc
        self.recompute_tallies(proposal)
        return proposal, vote

    def recompute_tallies(self, proposal: GovernanceProposal) -> GovernanceProposal:
        votes = self.list_votes(proposal.id)
        proposal.yes_weight = sum(item.influence_weight for item in votes if item.choice == GovernanceVoteChoice.YES)
        proposal.no_weight = sum(item.influence_weight for item in votes if item.choice == GovernanceVoteChoice.NO)
        proposal.abstain_weight = sum(item.influence_weight for item in votes if item.choice == GovernanceVoteChoice.ABSTAIN)
        proposal.unique_voter_count = len(votes)
        self.session.add(proposal)
        self.session.flush()
        return proposal

    def close_proposal(self, *, proposal_id: str, status: GovernanceProposalStatus, result_summary: str | None = None) -> GovernanceProposal:
        if status not in {GovernanceProposalStatus.CLOSED, GovernanceProposalStatus.ACCEPTED, GovernanceProposalStatus.REJECTED}:
            raise GovernanceEngineError("Proposal can only be closed, accepted, or rejected.")
        proposal = self.get_proposal(proposal_id)
        self.recompute_tallies(proposal)
        total_weight = int(proposal.yes_weight) + int(proposal.no_weight) + int(proposal.abstain_weight)
        if status == GovernanceProposalStatus.CLOSED:
            status = GovernanceProposalStatus.ACCEPTED if proposal.yes_weight > proposal.no_weight and total_weight >= int(proposal.quorum_token_weight) else GovernanceProposalStatus.REJECTED
        proposal.status = status
        proposal.result_summary = result_summary or (
            f"Voting closed with yes={proposal.yes_weight}, no={proposal.no_weight}, abstain={proposal.abstain_weight}, quorum_target={proposal.quorum_token_weight}."
        )
        self.session.add(proposal)
        self._publish_story(
            title=f"Governance proposal {proposal.status.value}: {proposal.title}",
            body=proposal.result_summary[:240],
            story_type="governance_proposal_closed",
            metadata={"proposal_id": proposal.id, "status": proposal.status.value, "club_id": proposal.club_id},
        )
        self.session.flush()
        return proposal

    def overview_for_user(self, *, user: User) -> dict[str, object]:
        holdings = list(
            self.session.scalars(
                select(CreatorClubShareHolding).where(
                    CreatorClubShareHolding.user_id == user.id,
                    CreatorClubShareHolding.share_count > 0,
                )
            ).all()
        )
        owned_club_ids = list(
            self.session.scalars(
                select(ClubProfile.id).where(ClubProfile.owner_user_id == user.id)
            ).all()
        )
        supporter_holding_club_ids = list(
            self.session.scalars(
                select(ClubSupporterHolding.club_id).where(
                    ClubSupporterHolding.user_id == user.id,
                    ClubSupporterHolding.token_balance > 0,
                )
            ).all()
        )
        eligible_club_ids = sorted(
            {
                *owned_club_ids,
                *(item.club_id for item in holdings),
                *supporter_holding_club_ids,
            }
        )
        recent_vote_count = self.session.scalar(select(func.count(GovernanceVote.id)).where(GovernanceVote.voter_user_id == user.id)) or 0
        return {
            "open_proposal_count": self.session.scalar(select(func.count(GovernanceProposal.id)).where(GovernanceProposal.status == GovernanceProposalStatus.OPEN)) or 0,
            "clubs_with_tokens": len(eligible_club_ids),
            "eligible_club_ids": eligible_club_ids,
            "recent_vote_count": int(recent_vote_count),
        }

    def build_club_panel(self, *, club_id: str, user: User) -> dict[str, object]:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise GovernanceEngineError("Club governance target was not found.")
        market = self.session.scalar(
            select(CreatorClubShareMarket).where(CreatorClubShareMarket.club_id == club_id)
        )
        policy = governance_policy_from_metadata(
            market.metadata_json if market is not None else {},
            max_shares_per_fan=int(market.max_shares_per_fan) if market is not None else None,
        )
        total_governance_shares = self._club_total_governance_shares(market)
        viewer_state = self._club_voting_state(
            club_id=club_id,
            user=user,
            minimum_tokens_required=int(policy["proposal_share_threshold"]),
        )
        proposals = list(
            self.session.scalars(
                select(GovernanceProposal)
                .where(
                    GovernanceProposal.club_id == club_id,
                    GovernanceProposal.scope == GovernanceProposalScope.CLUB,
                )
                .order_by(GovernanceProposal.updated_at.desc())
                .limit(5)
            ).all()
        )
        open_proposal_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(GovernanceProposal)
                .where(
                    GovernanceProposal.club_id == club_id,
                    GovernanceProposal.scope == GovernanceProposalScope.CLUB,
                    GovernanceProposal.status == GovernanceProposalStatus.OPEN,
                )
            )
            or 0
        )
        transfers = list(
            self.session.scalars(
                select(ClubSaleTransfer)
                .where(ClubSaleTransfer.club_id == club_id)
                .order_by(ClubSaleTransfer.created_at.desc())
                .limit(5)
            ).all()
        )
        dynasty = self.session.scalar(
            select(ClubDynastyProgress).where(ClubDynastyProgress.club_id == club_id)
        )
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
        last_transfer = transfers[0] if transfers else None
        shareholder_continuity_transfers = sum(
            1 for transfer in transfers if bool((transfer.metadata_json or {}).get("shareholder_rights_preserved"))
        )
        transfer_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(ClubSaleTransfer)
                .where(ClubSaleTransfer.club_id == club_id)
            )
            or 0
        )
        return {
            "club_id": club_id,
            "current_owner_user_id": club.owner_user_id,
            "market_id": market.id if market is not None else None,
            "market_status": market.status if market is not None else "owner_only",
            "governance_unit": "creator_club_shares",
            "viewer_is_owner": viewer_state.is_owner,
            "viewer_share_count": viewer_state.share_count,
            "viewer_vote_weight": viewer_state.influence_weight,
            "viewer_ownership_bps": viewer_state.ownership_bps,
            "viewer_can_create_proposals": viewer_state.eligible,
            "viewer_can_vote": viewer_state.eligible,
            "viewer_eligibility_reason": viewer_state.reason,
            "viewer_owner_approval_required": owner_approval_required(
                policy,
                ownership_bps=viewer_state.ownership_bps,
            ),
            "total_governance_shares": total_governance_shares,
            "quorum_share_weight": quorum_share_count(
                total_governance_shares=total_governance_shares,
                quorum_share_bps=int(policy["quorum_share_bps"]),
            ),
            "anti_takeover_cap_share_count": holder_cap_share_count(
                total_governance_shares=total_governance_shares,
                max_holder_bps=int(policy["max_holder_bps"]),
            ),
            "shareholder_count": shareholder_count,
            "open_proposal_count": open_proposal_count,
            "ownership_eras": max(1, transfer_count + 1),
            "policy": policy,
            "recent_proposals": [
                {
                    "id": proposal.id,
                    "title": proposal.title,
                    "status": proposal.status,
                    "yes_weight": proposal.yes_weight,
                    "no_weight": proposal.no_weight,
                    "abstain_weight": proposal.abstain_weight,
                    "created_at": proposal.created_at,
                    "updated_at": proposal.updated_at,
                }
                for proposal in proposals
            ],
            "ownership_history": {
                "transfer_count": transfer_count,
                "last_transfer_id": last_transfer.transfer_id if last_transfer is not None else None,
                "last_transfer_at": last_transfer.created_at if last_transfer is not None else None,
                "shareholder_continuity_transfers": shareholder_continuity_transfers,
                "recent_transfers": [
                    {
                        "transfer_id": transfer.transfer_id,
                        "seller_user_id": transfer.seller_user_id,
                        "buyer_user_id": transfer.buyer_user_id,
                        "executed_sale_price": transfer.executed_sale_price,
                        "created_at": transfer.created_at,
                        "metadata_json": transfer.metadata_json or {},
                    }
                    for transfer in transfers
                ],
            },
            "dynasty_snapshot": {
                "dynasty_score": int(dynasty.dynasty_score) if dynasty is not None else 0,
                "dynasty_level": int(dynasty.dynasty_level) if dynasty is not None else 1,
                "dynasty_title": dynasty.dynasty_title if dynasty is not None else "Foundations",
                "seasons_completed": int(dynasty.seasons_completed) if dynasty is not None else 0,
                "last_season_label": dynasty.last_season_label if dynasty is not None else None,
                "ownership_eras": max(1, transfer_count + 1),
                "shareholder_continuity_transfers": shareholder_continuity_transfers,
                "showcase_summary_json": dict(dynasty.showcase_summary_json or {}) if dynasty is not None else {},
            },
        }

    def _publish_story(self, *, title: str, body: str, story_type: str, metadata: dict[str, object]) -> None:
        story = StoryFeedItem(
            story_type=story_type,
            title=title,
            body=body,
            metadata_json=metadata,
            audience="public",
            subject_type="club" if metadata.get("club_id") else "platform",
            subject_id=metadata.get("club_id"),
            featured=False,
        )
        self.session.add(story)

    @staticmethod
    def _club_total_governance_shares(market: CreatorClubShareMarket | None) -> int:
        if market is None:
            return 1
        return fully_diluted_governance_shares(
            creator_controlled_shares=int(market.creator_controlled_shares),
            fan_share_supply=int(market.max_shares_issued),
        )
