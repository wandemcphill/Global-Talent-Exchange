from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.gift_engine.router import _resolve_recipient_context, _validate_existing_gift_identity
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


def test_missing_club_is_rejected() -> None:
    session = MagicMock()
    session.get.return_value = None
    payload = GiftSendRequest(recipient_club_id="missing-club", gift_key="fire")

    with pytest.raises(HTTPException) as exc_info:
        _resolve_recipient_context(payload=payload, session=session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Recipient club was not found."


def _transaction(*, sender: str, recipient: str, club: str | None) -> MagicMock:
    return MagicMock(sender_user_id=sender, recipient_user_id=recipient, recipient_club_id=club)


def test_idempotent_replay_allows_same_profile_and_club_context() -> None:
    item = _transaction(sender="sender-1", recipient="recipient-1", club="club-1")

    _validate_existing_gift_identity(
        item=item,
        sender_user_id="sender-1",
        recipient_user_id="recipient-1",
        recipient_club_id="club-1",
    )


def test_idempotent_replay_rejects_different_profile() -> None:
    item = _transaction(sender="sender-1", recipient="recipient-1", club="club-1")

    with pytest.raises(HTTPException) as exc_info:
        _validate_existing_gift_identity(
            item=item,
            sender_user_id="sender-2",
            recipient_user_id="recipient-1",
            recipient_club_id="club-1",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Idempotent gift reference belongs to a different sender or recipient profile."


def test_idempotent_replay_rejects_different_club_context() -> None:
    item = _transaction(sender="sender-1", recipient="recipient-1", club="club-1")

    with pytest.raises(HTTPException) as exc_info:
        _validate_existing_gift_identity(
            item=item,
            sender_user_id="sender-1",
            recipient_user_id="recipient-1",
            recipient_club_id="club-2",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Idempotent gift reference belongs to a different recipient club context."


def test_idempotent_replay_cannot_introduce_club_context_to_profile_only_gift() -> None:
    item = _transaction(sender="sender-1", recipient="recipient-1", club=None)

    with pytest.raises(HTTPException) as exc_info:
        _validate_existing_gift_identity(
            item=item,
            sender_user_id="sender-1",
            recipient_user_id="recipient-1",
            recipient_club_id="club-1",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Idempotent gift reference belongs to a different recipient club context."
