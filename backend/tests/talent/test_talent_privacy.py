"""Privacy and authorization of talent projections.

Two distinct questions are tested here: *can this viewer see the profile at
all* (visibility), and *which fields do they get* (scope). Plus the invariant
that binds them: no talent payload, at any scope, may carry identity,
compliance or payment data.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.talent.constants import RESTRICTED_SIGNAL_CODES, ViewerScope, VisibilityState
from app.talent.privacy import (
    PRIVATE_FIELD_FRAGMENTS,
    assert_no_private_fields,
    project_profile,
    resolve_viewer_scope,
)

from .conftest import make_user, seed_talent

PORTFOLIO = [
    {"kind": "video", "url": "https://media.example/approved.mp4", "title": "Highlights", "approved": True},
    {"kind": "video", "url": "https://media.example/pending.mp4", "title": "Trial", "approved": False},
]


@pytest.fixture()
def talent(session: Session):
    owner = make_user(session, username="talent_owner")
    profile = seed_talent(
        session,
        key="privacy",
        display_name="Chidi Nwosu",
        owner_user_id=owner.id,
        location_city="Ikeja",
        signal_codes=["progression", "disciplinary_concern"],
        portfolio=PORTFOLIO,
        internal_notes="Reviewer flagged the agent contact as unverified.",
    )
    session.commit()
    return profile


@pytest.fixture()
def viewers(session: Session):
    scout = make_user(session, username="club_scout", role=UserRole.SCOUT)
    admin = make_user(session, username="talent_admin", role=UserRole.ADMIN)
    bystander = make_user(session, username="random_fan")
    session.commit()
    return {"scout": scout, "admin": admin, "bystander": bystander}


def _profile(client: TestClient, player_id: str) -> dict:
    response = client.get(f"/talent/{player_id}")
    assert response.status_code == 200, response.text
    return response.json()["profile"]


# ----------------------------------------------------------------------
# Scope resolution
# ----------------------------------------------------------------------


def test_viewer_scope_resolution(session: Session, talent, viewers) -> None:
    owner = session.get(type(viewers["scout"]), talent.owner_user_id)

    assert resolve_viewer_scope(talent, None) is ViewerScope.PUBLIC
    assert resolve_viewer_scope(talent, viewers["bystander"]) is ViewerScope.PUBLIC
    assert resolve_viewer_scope(talent, viewers["scout"]) is ViewerScope.SCOUT
    assert resolve_viewer_scope(talent, owner) is ViewerScope.OWNER
    assert resolve_viewer_scope(talent, viewers["admin"]) is ViewerScope.ADMIN


def test_a_signed_in_ordinary_user_is_not_a_scout(client: TestClient, identity, talent, viewers) -> None:
    identity.user = viewers["bystander"]
    payload = _profile(client, talent.player_id)

    assert payload["viewer_scope"] == ViewerScope.PUBLIC.value
    assert "location_city" not in payload


# ----------------------------------------------------------------------
# Field scoping
# ----------------------------------------------------------------------


def test_public_projection_withholds_locating_and_internal_fields(client: TestClient, talent) -> None:
    payload = _profile(client, talent.player_id)

    for withheld in (
        "location_city",
        "date_of_birth",
        "owner_user_id",
        "moderation_state",
        "internal_notes",
        "suspension_reason",
        "metadata",
        "ranking_inputs_digest",
    ):
        assert withheld not in payload, f"public payload must not expose {withheld}"

    # It still carries everything a discovery surface legitimately needs.
    assert payload["age_years"] is not None
    assert payload["position_code"]
    assert payload["nationality_code"]
    assert payload["location_region"]
    assert payload["composite_score"] > 0


def test_scout_projection_adds_city_and_ranking_lineage(client: TestClient, identity, talent, viewers) -> None:
    identity.user = viewers["scout"]
    payload = _profile(client, talent.player_id)

    assert payload["viewer_scope"] == ViewerScope.SCOUT.value
    assert payload["location_city"] == "Ikeja"
    assert "ranking_inputs_digest" in payload
    # Still not the talent's private or moderation data.
    assert "date_of_birth" not in payload
    assert "internal_notes" not in payload


def test_owner_projection_adds_their_own_private_fields(
    session: Session, client: TestClient, identity, talent, viewers
) -> None:
    identity.user = session.get(type(viewers["scout"]), talent.owner_user_id)
    payload = _profile(client, talent.player_id)

    assert payload["viewer_scope"] == ViewerScope.OWNER.value
    assert payload["date_of_birth"] is not None
    assert payload["moderation_state"]
    assert payload["owner_user_id"] == talent.owner_user_id
    # Reviewer-facing notes remain admin-only, even about yourself.
    assert "internal_notes" not in payload


def test_admin_projection_adds_moderation_context(client: TestClient, identity, talent, viewers) -> None:
    identity.user = viewers["admin"]
    payload = _profile(client, talent.player_id)

    assert payload["viewer_scope"] == ViewerScope.ADMIN.value
    assert payload["internal_notes"]
    assert "suspension_reason" in payload
    assert "metadata" in payload


# ----------------------------------------------------------------------
# The hard invariant
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "scope",
    [ViewerScope.PUBLIC, ViewerScope.SCOUT, ViewerScope.OWNER, ViewerScope.ADMIN],
)
def test_no_scope_ever_exposes_identity_or_payment_fields(talent, scope: ViewerScope) -> None:
    payload = project_profile(talent, scope=scope)

    assert_no_private_fields(payload)


def test_the_private_field_guard_actually_catches_a_leak() -> None:
    with pytest.raises(AssertionError):
        assert_no_private_fields({"profile": {"kyc_status": "verified"}})
    with pytest.raises(AssertionError):
        assert_no_private_fields({"contacts": [{"user_email": "a@b.c"}]})


def test_account_identifiers_never_appear_in_a_talent_payload(
    session: Session, client: TestClient, identity, talent, viewers
) -> None:
    owner = session.get(type(viewers["scout"]), talent.owner_user_id)
    identity.user = viewers["scout"]

    serialized = json.dumps(_profile(client, talent.player_id))

    assert owner.email not in serialized
    assert owner.username not in serialized
    assert owner.password_hash not in serialized


def test_private_field_fragments_cover_the_obvious_domains() -> None:
    for fragment in ("kyc", "password", "email", "phone", "payment", "wallet", "passport"):
        assert fragment in PRIVATE_FIELD_FRAGMENTS


# ----------------------------------------------------------------------
# Signal scoping
# ----------------------------------------------------------------------


def test_negative_signals_are_withheld_from_anonymous_traffic(client: TestClient, identity, talent, viewers) -> None:
    def _card_codes() -> set[str]:
        response = client.get("/talent/search")
        assert response.status_code == 200, response.text
        card = next(item for item in response.json()["items"] if item["player_id"] == talent.player_id)
        return set(card["signal_codes"] or [])

    public_codes = _card_codes()
    assert "progression" in public_codes
    assert public_codes.isdisjoint(RESTRICTED_SIGNAL_CODES)

    identity.user = viewers["scout"]
    assert "disciplinary_concern" in _card_codes()


def test_restricted_signal_filters_are_refused_not_silently_dropped(
    client: TestClient, identity, talent, viewers
) -> None:
    anonymous = client.get("/talent/search", params={"required_signals": ["disciplinary_concern"]})
    assert anonymous.status_code == 403

    identity.user = viewers["scout"]
    allowed = client.get("/talent/search", params={"required_signals": ["disciplinary_concern"]})
    assert allowed.status_code == 200


# ----------------------------------------------------------------------
# Portfolio moderation
# ----------------------------------------------------------------------


def test_only_approved_media_is_shown_outside_owner_and_admin_views(
    session: Session, client: TestClient, identity, talent, viewers
) -> None:
    public_urls = {item["url"] for item in _profile(client, talent.player_id)["portfolio"]}
    assert public_urls == {"https://media.example/approved.mp4"}

    identity.user = viewers["scout"]
    scout_urls = {item["url"] for item in _profile(client, talent.player_id)["portfolio"]}
    assert scout_urls == public_urls

    identity.user = session.get(type(viewers["scout"]), talent.owner_user_id)
    owner_urls = {item["url"] for item in _profile(client, talent.player_id)["portfolio"]}
    assert len(owner_urls) == 2


# ----------------------------------------------------------------------
# Visibility gating
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "state", [VisibilityState.DRAFT.value, VisibilityState.HIDDEN.value, VisibilityState.SUSPENDED.value]
)
def test_unpublished_profiles_are_not_readable_by_the_public_or_scouts(
    session: Session, client: TestClient, identity, viewers, state: str
) -> None:
    profile = seed_talent(session, key=f"gated-{state}", display_name="Gated", visibility_state=state)
    session.commit()

    assert client.get(f"/talent/{profile.player_id}").status_code == 404

    identity.user = viewers["scout"]
    assert client.get(f"/talent/{profile.player_id}").status_code == 404

    identity.user = viewers["admin"]
    assert client.get(f"/talent/{profile.player_id}").status_code == 200


def test_the_talent_can_still_read_their_own_suspended_profile(session: Session, client: TestClient, identity) -> None:
    owner = make_user(session, username="suspended_owner")
    profile = seed_talent(
        session,
        key="own-suspended",
        display_name="Suspended Owner",
        owner_user_id=owner.id,
        visibility_state=VisibilityState.SUSPENDED.value,
    )
    session.commit()

    identity.user = owner
    payload = _profile(client, profile.player_id)

    assert payload["visibility_state"] == VisibilityState.SUSPENDED.value
    # They learn they are suspended, not the reviewer's reasoning.
    assert "suspension_reason" not in payload


def test_unpublished_profiles_are_absent_from_ranking_and_signal_endpoints(
    session: Session, client: TestClient
) -> None:
    profile = seed_talent(
        session, key="gated-detail", display_name="Gated Detail", visibility_state=VisibilityState.DRAFT.value
    )
    session.commit()

    assert client.get(f"/talent/{profile.player_id}/ranking").status_code == 404
    assert client.get(f"/talent/{profile.player_id}/signals").status_code == 404


def test_unknown_player_returns_not_found(client: TestClient) -> None:
    assert client.get("/talent/does-not-exist").status_code == 404


# ----------------------------------------------------------------------
# Authorization on the scout workflow
# ----------------------------------------------------------------------


def test_shortlist_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/talent/shortlists").status_code == 401
    assert client.post("/talent/shortlists", json={"name": "Targets"}).status_code == 401


def test_admin_endpoints_reject_non_admin_callers(client: TestClient, identity, talent, viewers) -> None:
    identity.user = viewers["scout"]
    identity.admin = None

    assert client.get(f"/admin/talent/{talent.player_id}").status_code == 403
    assert (
        client.post(
            f"/admin/talent/{talent.player_id}/visibility",
            json={"visibility_state": "published"},
        ).status_code
        == 403
    )
