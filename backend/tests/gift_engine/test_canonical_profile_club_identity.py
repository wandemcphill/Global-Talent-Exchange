from unittest.mock import MagicMock

import pytest

from app.gift_engine.canonical_service import CanonicalGiftEngineService
from app.gift_engine.service import GiftEngineError


def _service(*, club=None) -> CanonicalGiftEngineService:
    session = MagicMock()
    session.get.return_value = club
    return CanonicalGiftEngineService(session=session)


def _club(*, owner_user_id: str, club_id: str) -> MagicMock:
    return MagicMock(owner_user_id=owner_user_id, id=club_id)


def test_canonical_club_context_resolves_to_owner_profile() -> None:
    service = _service(club=_club(owner_user_id="profile-owner", club_id="club-owner"))

    recipient_user_id, recipient_club_id = service._resolve_canonical_recipient_identity(
        recipient_user_id=None,
        recipient_club_id="club-owner",
    )

    assert recipient_user_id == "profile-owner"
    assert recipient_club_id == "club-owner"


def test_canonical_club_context_rejects_different_profile() -> None:
    service = _service(club=_club(owner_user_id="profile-owner", club_id="club-owner"))

    with pytest.raises(GiftEngineError) as exc_info:
        service._resolve_canonical_recipient_identity(
            recipient_user_id="profile-other",
            recipient_club_id="club-owner",
        )

    assert exc_info.value.reason == "recipient_club_identity_mismatch"
    assert exc_info.value.detail == "Recipient profile does not own the selected recipient club."


def test_canonical_club_context_rejects_missing_club() -> None:
    service = _service(club=None)

    with pytest.raises(GiftEngineError) as exc_info:
        service._resolve_canonical_recipient_identity(
            recipient_user_id="profile-owner",
            recipient_club_id="missing-club",
        )

    assert exc_info.value.reason == "recipient_club_not_found"
    assert exc_info.value.detail == "Recipient club was not found."


def test_canonical_profile_only_gift_keeps_profile_identity() -> None:
    service = _service()

    recipient_user_id, recipient_club_id = service._resolve_canonical_recipient_identity(
        recipient_user_id="profile-owner",
        recipient_club_id=None,
    )

    assert recipient_user_id == "profile-owner"
    assert recipient_club_id is None
