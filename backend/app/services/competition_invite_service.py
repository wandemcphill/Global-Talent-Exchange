from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from secrets import token_hex
from threading import RLock


@dataclass(slots=True, frozen=True)
class CompetitionInvite:
    invite_code: str
    competition_id: str
    issued_by: str
    created_at: datetime
    expires_at: datetime | None
    max_uses: int
    uses: int = 0
    note: str | None = None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at

    def can_use(self) -> bool:
        return self.uses < self.max_uses


@dataclass(slots=True)
class CompetitionInviteService:
    _invites_by_competition: dict[str, list[CompetitionInvite]]
    _lock: RLock = field(default_factory=RLock)

    def create_invite(
        self,
        *,
        competition_id: str,
        issued_by: str,
        max_uses: int,
        expires_at: datetime | None,
        note: str | None,
    ) -> CompetitionInvite:
        invite = CompetitionInvite(
            invite_code=token_hex(6),
            competition_id=competition_id,
            issued_by=issued_by,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            max_uses=max_uses,
            uses=0,
            note=note,
        )
        with self._lock:
            self._invites_by_competition.setdefault(competition_id, []).append(invite)
        return invite

    def list_invites(self, competition_id: str) -> tuple[CompetitionInvite, ...]:
        with self._lock:
            return tuple(self._invites_by_competition.get(competition_id, ()))

    def has_valid_invite(self, competition_id: str, invite_code: str | None) -> bool:
        if invite_code is None:
            return False
        now = datetime.now(timezone.utc)
        with self._lock:
            invites = self._invites_by_competition.get(competition_id, [])
            for invite in invites:
                if invite.invite_code == invite_code and not invite.is_expired(now) and invite.can_use():
                    return True
        return False

    def redeem_invite(self, competition_id: str, invite_code: str) -> CompetitionInvite | None:
        now = datetime.now(timezone.utc)
        with self._lock:
            invites = self._invites_by_competition.get(competition_id, [])
            for index, invite in enumerate(invites):
                if invite.invite_code != invite_code:
                    continue
                if invite.is_expired(now) or not invite.can_use():
                    return None
                updated = CompetitionInvite(
                    invite_code=invite.invite_code,
                    competition_id=invite.competition_id,
                    issued_by=invite.issued_by,
                    created_at=invite.created_at,
                    expires_at=invite.expires_at,
                    max_uses=invite.max_uses,
                    uses=invite.uses + 1,
                    note=invite.note,
                )
                invites[index] = updated
                return updated
        return None
