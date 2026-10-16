"""Scout workflow: shortlists and side-by-side comparison."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.talent.constants import SHORTLIST_MAX_PER_OWNER, VisibilityState
from app.talent.ranking import COMPONENT_ORDER

from .conftest import make_user, seed_talent


@pytest.fixture()
def scouts(session: Session):
    first = make_user(session, username="scout_one", role=UserRole.SCOUT)
    second = make_user(session, username="scout_two", role=UserRole.SCOUT)
    session.commit()
    return {"one": first, "two": second}


@pytest.fixture()
def talents(session: Session) -> dict[str, str]:
    return {
        "striker": seed_talent(
            session, key="sl-st", display_name="Ada Eze", position_code="ST", composite_score=82.0
        ).player_id,
        "midfielder": seed_talent(
            session, key="sl-cm", display_name="Ben Toure", position_code="CM", composite_score=68.0
        ).player_id,
        "draft": seed_talent(
            session,
            key="sl-draft",
            display_name="Unpublished",
            visibility_state=VisibilityState.DRAFT.value,
        ).player_id,
    }


def _create_list(client: TestClient, name: str = "Summer targets") -> dict:
    response = client.post("/talent/shortlists", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


# ----------------------------------------------------------------------
# Shortlist lifecycle
# ----------------------------------------------------------------------


def test_shortlist_create_read_update_delete(client: TestClient, identity, scouts) -> None:
    identity.user = scouts["one"]

    created = _create_list(client)
    assert created["entry_count"] == 0

    listed = client.get("/talent/shortlists").json()["shortlists"]
    assert [item["id"] for item in listed] == [created["id"]]

    renamed = client.patch(f"/talent/shortlists/{created['id']}", json={"name": "Winter targets", "is_archived": True})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Winter targets"
    assert renamed.json()["is_archived"] is True

    assert client.delete(f"/talent/shortlists/{created['id']}").status_code == 204
    assert client.get("/talent/shortlists").json()["shortlists"] == []


def test_duplicate_shortlist_names_are_rejected(client: TestClient, identity, scouts) -> None:
    identity.user = scouts["one"]
    _create_list(client)

    duplicate = client.post("/talent/shortlists", json={"name": "Summer targets"})
    assert duplicate.status_code == 400


def test_shortlist_count_is_capped(client: TestClient, identity, scouts, monkeypatch) -> None:
    identity.user = scouts["one"]
    monkeypatch.setattr("app.talent.service.SHORTLIST_MAX_PER_OWNER", 2)

    _create_list(client, "One")
    _create_list(client, "Two")
    refused = client.post("/talent/shortlists", json={"name": "Three"})

    assert refused.status_code == 400
    assert "limit" in refused.json()["detail"].lower()


def test_the_real_cap_is_bounded() -> None:
    assert 0 < SHORTLIST_MAX_PER_OWNER <= 100


# ----------------------------------------------------------------------
# Entries
# ----------------------------------------------------------------------


def test_adding_a_talent_captures_the_score_at_that_moment(client: TestClient, identity, scouts, talents) -> None:
    identity.user = scouts["one"]
    shortlist = _create_list(client)

    response = client.post(
        f"/talent/shortlists/{shortlist['id']}/entries",
        json={"player_id": talents["striker"], "status": "target", "priority": 5, "note": "Watch vs Kano."},
    )

    assert response.status_code == 201, response.text
    entry = response.json()["entries"][0]
    assert entry["player_id"] == talents["striker"]
    assert entry["status"] == "target"
    assert entry["score_at_add"] == 82.0
    assert entry["note"] == "Watch vs Kano."
    assert entry["talent"]["display_name"] == "Ada Eze"


def test_entries_are_ordered_by_priority_then_stably(client: TestClient, identity, scouts, talents) -> None:
    identity.user = scouts["one"]
    shortlist = _create_list(client)

    client.post(
        f"/talent/shortlists/{shortlist['id']}/entries",
        json={"player_id": talents["midfielder"], "priority": 1},
    )
    response = client.post(
        f"/talent/shortlists/{shortlist['id']}/entries",
        json={"player_id": talents["striker"], "priority": 9},
    )

    ids = [entry["player_id"] for entry in response.json()["entries"]]
    assert ids == [talents["striker"], talents["midfielder"]]
    assert ids == [
        entry["player_id"] for entry in client.get(f"/talent/shortlists/{shortlist['id']}").json()["entries"]
    ]


def test_a_talent_cannot_be_added_twice(client: TestClient, identity, scouts, talents) -> None:
    identity.user = scouts["one"]
    shortlist = _create_list(client)
    payload = {"player_id": talents["striker"]}

    assert client.post(f"/talent/shortlists/{shortlist['id']}/entries", json=payload).status_code == 201
    duplicate = client.post(f"/talent/shortlists/{shortlist['id']}/entries", json=payload)
    assert duplicate.status_code == 400


def test_unpublished_talent_cannot_be_shortlisted(client: TestClient, identity, scouts, talents) -> None:
    identity.user = scouts["one"]
    shortlist = _create_list(client)

    response = client.post(f"/talent/shortlists/{shortlist['id']}/entries", json={"player_id": talents["draft"]})
    assert response.status_code == 404


def test_entry_update_and_removal(client: TestClient, identity, scouts, talents) -> None:
    identity.user = scouts["one"]
    shortlist = _create_list(client)
    created = client.post(
        f"/talent/shortlists/{shortlist['id']}/entries", json={"player_id": talents["striker"]}
    ).json()
    entry_id = created["entries"][0]["id"]

    updated = client.patch(
        f"/talent/shortlists/{shortlist['id']}/entries/{entry_id}",
        json={"status": "contacted", "priority": 10, "note": "Agent replied."},
    )
    assert updated.status_code == 200
    assert updated.json()["entries"][0]["status"] == "contacted"

    removed = client.delete(f"/talent/shortlists/{shortlist['id']}/entries/{entry_id}")
    assert removed.status_code == 204
    assert client.get(f"/talent/shortlists/{shortlist['id']}").json()["entry_count"] == 0


# ----------------------------------------------------------------------
# Ownership isolation
# ----------------------------------------------------------------------


def test_a_scout_cannot_see_another_scouts_shortlists(client: TestClient, identity, scouts) -> None:
    identity.user = scouts["one"]
    mine = _create_list(client, "Private board")

    identity.user = scouts["two"]
    assert client.get("/talent/shortlists").json()["shortlists"] == []
    # Existence of someone else's list is not disclosed: 404, not 403.
    assert client.get(f"/talent/shortlists/{mine['id']}").status_code == 404


def test_a_scout_cannot_mutate_another_scouts_shortlist(client: TestClient, identity, scouts, talents) -> None:
    identity.user = scouts["one"]
    mine = _create_list(client, "Private board")

    identity.user = scouts["two"]
    assert client.patch(f"/talent/shortlists/{mine['id']}", json={"name": "Hijacked"}).status_code == 404
    assert client.delete(f"/talent/shortlists/{mine['id']}").status_code == 404
    assert (
        client.post(f"/talent/shortlists/{mine['id']}/entries", json={"player_id": talents["striker"]}).status_code
        == 404
    )


def test_private_scouting_notes_stay_with_their_owner(client: TestClient, identity, scouts, talents) -> None:
    identity.user = scouts["one"]
    shortlist = _create_list(client)
    client.post(
        f"/talent/shortlists/{shortlist['id']}/entries",
        json={"player_id": talents["striker"], "note": "Weak left foot, would low-ball."},
    )

    identity.user = scouts["two"]
    assert client.get(f"/talent/shortlists/{shortlist['id']}").status_code == 404

    # And the note is nowhere in the public view of that talent.
    identity.user = None
    profile = client.get(f"/talent/{talents['striker']}").text
    assert "low-ball" not in profile


# ----------------------------------------------------------------------
# Compare
# ----------------------------------------------------------------------


def test_compare_returns_a_component_matrix(client: TestClient, talents) -> None:
    response = client.post(
        "/talent/compare",
        json={"player_ids": [talents["striker"], talents["midfielder"]]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [item["player_id"] for item in payload["talents"]] == [
        talents["striker"],
        talents["midfielder"],
    ]
    assert [row["component"] for row in payload["component_matrix"]] == list(COMPONENT_ORDER)
    for row in payload["component_matrix"]:
        assert set(row["scores"]) == {talents["striker"], talents["midfielder"]}


def test_compare_reports_talents_it_cannot_show(client: TestClient, talents) -> None:
    response = client.post(
        "/talent/compare",
        json={"player_ids": [talents["striker"], talents["draft"], "ghost-id"]},
    )

    payload = response.json()
    assert [item["player_id"] for item in payload["talents"]] == [talents["striker"]]
    assert set(payload["missing_player_ids"]) == {talents["draft"], "ghost-id"}


def test_compare_requires_at_least_two_distinct_talents(client: TestClient, talents) -> None:
    assert client.post("/talent/compare", json={"player_ids": [talents["striker"]]}).status_code == 422
    assert (
        client.post("/talent/compare", json={"player_ids": [talents["striker"], talents["striker"]]}).status_code == 422
    )


def test_compare_is_bounded(client: TestClient, session: Session) -> None:
    ids = [seed_talent(session, key=f"cmp-{index}", display_name=f"Cmp {index}").player_id for index in range(8)]

    response = client.post("/talent/compare", json={"player_ids": ids})
    assert response.status_code == 422


def test_compare_respects_the_viewer_scope(client: TestClient, identity, scouts, session: Session, talents) -> None:
    anonymous = client.post("/talent/compare", json={"player_ids": [talents["striker"], talents["midfielder"]]}).json()
    assert all("location_city" not in item for item in anonymous["talents"])

    identity.user = scouts["one"]
    as_scout = client.post("/talent/compare", json={"player_ids": [talents["striker"], talents["midfielder"]]}).json()
    assert all("location_city" in item for item in as_scout["talents"])
