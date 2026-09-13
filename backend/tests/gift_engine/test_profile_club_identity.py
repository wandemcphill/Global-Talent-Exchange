from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.gift_engine.router import _resolve_recipient_context
from app.gift_engine.schemas import GiftSendRequest


def _session_for_club(*, owner_user_id: str, club_id: str) -> MagicMock:
    session = MagicMock()
    club = MagicMock(owner_user_id=owner_user_id, id=club_id)
    session.get.return_value = club
    return session


def test_gifting_without_club_keeps_profile_recipient() -> None:
    session = MagicMock()
    payload = GiftSendRequest(recipient_user_id="profile-friend", gift_key="fire")

    recipient_user_id, recipient_club_id = _resolve_recipient_context(payload=payload, session=session)

    assert recipient_user_id == "profile-friend"
    assert recipient_club_id is None
    session.get.assert_not_called()


def test_club_target_resolves_to_the_club_owner_profile() -> None:
    session = _session_for_club(owner_user_id="profile-friend", club_id="club-friend")
    payload = GiftSendRequest(recipient_club_id="club-friend", gift_key="fire")

    recipient_user_id, recipient_club_id = _resolve_recipient_context(payload=payload, session=session)

    assert recipient_user_id == "profile-friend"
    assert recipient_club_id == "club-friend"


def test_cannot_pair_a_club_with_a_different_profile() -> None:
    session = _session_for_club(owner_user_id="profile-owner", club_id="club-owner")
    payload = GiftSendRequest(
        recipient_user_id="profile-other",
        recipient_club_id="club-owner",
        gift_key="fire",
    )

    with pytest.raises(HTTPException) as exc_info:
        _resolve_recipient_context(payload=payload, session=session)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Recipient profile does not own the selected recipient club."
