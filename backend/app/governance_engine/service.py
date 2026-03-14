from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.club_infra import ClubSupporterHolding
from backend.app.models.governance_engine import (
    GovernanceProposal,
    GovernanceProposalScope,
    GovernanceProposalStatus,
    GovernanceVote,
    GovernanceVoteChoice,
)
from backend.app.models.story_feed import StoryFeedItem
from backend.app.models.user import User, UserRole


class GovernanceEngineError(ValueError):
    pass


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

    def _holding_for(self, *, proposal: GovernanceProposal, user: User) -> ClubSupporterHolding | None:
        if proposal.scope == GovernanceProposalScope.PLATFORM or proposal.club_id is None:
            stmt = (
                select(ClubSupporterHolding)
                .where(ClubSupporterHolding.user_id == user.id)
                .order_by(ClubSupporterHolding.influence_points.desc(), ClubSupporterHolding.token_balance.desc())
            )
            return self.session.scalars(stmt).first()
        return self.session.scalar(
            select(ClubSupporterHolding).where(ClubSupporterHolding.club_id == proposal.club_id, ClubSupporterHolding.user_id == user.id)
        )

    def eligibility_for(self, *, proposal: GovernanceProposal, user: User) -> tuple[bool, str | None, ClubSupporterHolding | None]:
        if user.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return True, None, None
        holding = self._holding_for(proposal=proposal, user=user)
        if holding is None:
            return False, "No supporter holding found for this governance scope.", None
        if int(holding.token_balance) < int(proposal.minimum_tokens_required):
            return False, f"At least {proposal.minimum_tokens_required} supporter tokens are required.", holding
        return True, None, holding

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
            metadata_json=metadata_json,
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
        eligible, reason, holding = self.eligibility_for(proposal=proposal, user=voter)
        if not eligible:
            raise GovernanceEngineError(reason or "User is not eligible to vote on this proposal.")
        token_weight = int(getattr(holding, "token_balance", 1) or 1)
        influence_weight = int(getattr(holding, "influence_points", token_weight) or token_weight)
        vote = GovernanceVote(
            proposal_id=proposal.id,
            voter_user_id=voter.id,
            club_id=proposal.club_id,
            choice=choice,
            token_weight=token_weight,
            influence_weight=influence_weight,
            comment=comment,
            metadata_json={"scope": proposal.scope.value},
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
        holdings = list(self.session.scalars(select(ClubSupporterHolding).where(ClubSupporterHolding.user_id == user.id)).all())
        recent_vote_count = self.session.scalar(select(func.count(GovernanceVote.id)).where(GovernanceVote.voter_user_id == user.id)) or 0
        return {
            "open_proposal_count": self.session.scalar(select(func.count(GovernanceProposal.id)).where(GovernanceProposal.status == GovernanceProposalStatus.OPEN)) or 0,
            "clubs_with_tokens": len(holdings),
            "eligible_club_ids": [item.club_id for item in holdings if item.token_balance > 0],
            "recent_vote_count": int(recent_vote_count),
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
