from __future__ import annotations

from enum import Enum

from sqlalchemy import Boolean, Enum as SqlEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GovernanceProposalScope(str, Enum):
    CLUB = "club"
    PLATFORM = "platform"


class GovernanceProposalStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class GovernanceVoteChoice(str, Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class GovernanceProposal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "governance_proposals"

    club_id: Mapped[str | None] = mapped_column(ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    proposer_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scope: Mapped[GovernanceProposalScope] = mapped_column(
        SqlEnum(GovernanceProposalScope, name="governanceproposalscope"), nullable=False, default=GovernanceProposalScope.CLUB
    )
    status: Mapped[GovernanceProposalStatus] = mapped_column(
        SqlEnum(GovernanceProposalStatus, name="governanceproposalstatus"), nullable=False, default=GovernanceProposalStatus.OPEN
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    voting_starts_at_iso: Mapped[str | None] = mapped_column(String(40), nullable=True)
    voting_ends_at_iso: Mapped[str | None] = mapped_column(String(40), nullable=True)
    minimum_tokens_required: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    quorum_token_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    yes_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    no_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    abstain_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    unique_voter_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(nullable=False, default=dict)


class GovernanceVote(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "governance_votes"
    __table_args__ = (
        UniqueConstraint("proposal_id", "voter_user_id", name="uq_governance_votes_proposal_user"),
    )

    proposal_id: Mapped[str] = mapped_column(ForeignKey("governance_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    voter_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    club_id: Mapped[str | None] = mapped_column(ForeignKey("club_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    choice: Mapped[GovernanceVoteChoice] = mapped_column(SqlEnum(GovernanceVoteChoice, name="governancevotechoice"), nullable=False)
    token_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    influence_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_proxy_vote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    metadata_json: Mapped[dict[str, object]] = mapped_column(nullable=False, default=dict)


__all__ = [
    "GovernanceProposal",
    "GovernanceProposalScope",
    "GovernanceProposalStatus",
    "GovernanceVote",
    "GovernanceVoteChoice",
]
