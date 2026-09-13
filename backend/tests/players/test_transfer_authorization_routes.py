from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.player_lifecycle_service import PlayerLifecycleValidationError
from app.segments.player_lifecycle.transfer_authorization_routes import _require_club_owner


class _Session:
    def __init__(self, club) -> None:
        self.club = club

    def get(self, _model, _club_id):
        return self.club


def test_transfer_actor_must_own_buying_club() -> None:
    session = _Session(SimpleNamespace(id="club-1", owner_user_id="owner-1"))

    _require_club_owner(session, "club-1", SimpleNamespace(id="owner-1"), action="Creating a transfer bid")


def test_transfer_actor_cannot_write_for_another_club() -> None:
    session = _Session(SimpleNamespace(id="club-1", owner_user_id="owner-1"))

    with pytest.raises(Exception, match="do not control this club"):
        _require_club_owner(
            session,
            "club-1",
            SimpleNamespace(id="intruder-1"),
            action="Creating a transfer bid",
        )


def test_transfer_requires_a_club_id() -> None:
    session = _Session(None)

    with pytest.raises(Exception, match="requires a club"):
        _require_club_owner(
            session,
            None,
            SimpleNamespace(id="owner-1"),
            action="Creating a transfer bid",
        )
