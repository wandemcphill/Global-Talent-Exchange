from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.club_profile import ClubProfile
from app.models.player_injury_case import PlayerInjuryCase
from app.models.player_contract import PlayerContract
from app.models.user import User, UserRole


PLAYER_LIFECYCLE_MUTATION_PREFIX = "/api/players/"
CONTRACT_MARKER = "/contracts"
INJURY_MARKER = "/injuries"


def _assert_club_owner(session: Session, *, actor: User, club_id: str | None, action: str) -> None:
    if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        return
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A club is required for {action}",
        )
    club = session.get(ClubProfile, club_id)
    if club is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lifecycle club was not found")
    if club.owner_user_id != actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only the {action} club owner can perform this lifecycle action",
        )


async def authorize_player_lifecycle_mutation(
    request: Request,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    if request.method != "POST":
        return

    path = request.url.path
    if not path.startswith(PLAYER_LIFECYCLE_MUTATION_PREFIX):
        return

    if CONTRACT_MARKER in path:
        tail = path.split(CONTRACT_MARKER, 1)[1]
        if tail == "":
            payload = await request.json()
            _assert_club_owner(
                session,
                actor=actor,
                club_id=str(payload.get("club_id") or "").strip(),
                action="contract",
            )
            return

        if tail.startswith("/") and tail.count("/") == 2 and tail.endswith("/renew"):
            contract_id = tail.split("/")[1].strip()
            contract = session.get(PlayerContract, contract_id)
            if contract is None:
                return
            _assert_club_owner(
                session,
                actor=actor,
                club_id=contract.club_id,
                action="contract",
            )
            return

    if INJURY_MARKER in path:
        tail = path.split(INJURY_MARKER, 1)[1]
        if tail == "":
            payload = await request.json()
            player_id = path.split(PLAYER_LIFECYCLE_MUTATION_PREFIX, 1)[1].split("/", 1)[0]
            club_id = str(payload.get("club_id") or "").strip()
            if not club_id:
                from app.ingestion.models import Player

                player = session.get(Player, player_id)
                if player is None:
                    return
                club_id = player.current_club_profile_id
            _assert_club_owner(
                session,
                actor=actor,
                club_id=club_id,
                action="injury",
            )
            return

        if tail.startswith("/") and tail.count("/") == 2 and tail.endswith("/recover"):
            injury_id = tail.split("/")[1].strip()
            injury = session.get(PlayerInjuryCase, injury_id)
            if injury is None:
                return
            _assert_club_owner(
                session,
                actor=actor,
                club_id=injury.club_id,
                action="injury",
            )
