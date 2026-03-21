from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.common.enums.competition_status import CompetitionStatus
from app.common.enums.competition_visibility import CompetitionVisibility


@dataclass(slots=True, frozen=True)
class CompetitionParticipant:
    user_id: str
    user_name: str | None
    joined_at: datetime


@dataclass(slots=True)
class JoinDecision:
    eligible: bool
    reason: str | None = None
    requires_invite: bool = False


@dataclass(slots=True)
class CompetitionJoinService:
    def evaluate_join(
        self,
        *,
        status: CompetitionStatus,
        visibility: CompetitionVisibility,
        participant_count: int,
        capacity: int,
        already_joined: bool,
        invite_valid: bool,
    ) -> JoinDecision:
        if already_joined:
            return JoinDecision(eligible=True, reason="already_joined", requires_invite=False)
        if status not in {CompetitionStatus.OPEN, CompetitionStatus.OPEN_FOR_JOIN}:
            return JoinDecision(eligible=False, reason="competition_not_open", requires_invite=False)
        if participant_count >= capacity:
            return JoinDecision(eligible=False, reason="competition_full", requires_invite=False)
        if visibility is CompetitionVisibility.INVITE_ONLY and not invite_valid:
            return JoinDecision(eligible=False, reason="invite_required", requires_invite=True)
        return JoinDecision(eligible=True)

    def join(
        self,
        *,
        participants: tuple[CompetitionParticipant, ...],
        user_id: str,
        user_name: str | None,
    ) -> tuple[CompetitionParticipant, ...]:
        if any(existing.user_id == user_id for existing in participants):
            return participants
        joined = CompetitionParticipant(
            user_id=user_id,
            user_name=user_name,
            joined_at=datetime.now(timezone.utc),
        )
        return (*participants, joined)

    def leave(
        self,
        *,
        participants: tuple[CompetitionParticipant, ...],
        user_id: str,
    ) -> tuple[CompetitionParticipant, ...]:
        return tuple(participant for participant in participants if participant.user_id != user_id)
