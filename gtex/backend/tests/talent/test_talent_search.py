"""Discovery search: filtering, pagination, stability and query bounding."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.talent.constants import (
    SEARCH_MAX_PAGE_SIZE,
    SEARCH_MAX_RESULT_WINDOW,
    AvailabilityStatus,
    VerificationTier,
    VisibilityState,
)
from app.talent.schemas import TalentSearchRequest

from .conftest import seed_talent


@pytest.fixture()
def catalogue(session: Session) -> dict[str, str]:
    """A small, deliberately varied catalogue of published talent."""

    ids: dict[str, str] = {}
    ids["striker_top"] = seed_talent(
        session,
        key="st-top",
        display_name="Amara Bello",
        position_code="ST",
        composite_score=88.0,
        form_score=72.0,
        competition_level_score=90.0,
        age_years=21,
        nationality_code="NGA",
        availability_status=AvailabilityStatus.OPEN_TO_OFFERS.value,
        verification_tier=VerificationTier.CREDENTIALS_VERIFIED.value,
        tactical_roles=["poacher", "pressing_forward"],
        signal_codes=["progression", "disciplinary_concern"],
        is_featured=True,
    ).player_id
    ids["midfielder_mid"] = seed_talent(
        session,
        key="cm-mid",
        display_name="Kofi Mensah",
        position_code="CM",
        composite_score=71.0,
        form_score=58.0,
        competition_level_score=64.0,
        age_years=26,
        nationality_code="GHA",
        location_country_code="GHA",
        location_region="Accra",
        availability_status=AvailabilityStatus.CONTRACTED.value,
        verification_tier=VerificationTier.IDENTITY_VERIFIED.value,
        tactical_roles=["box_to_box"],
        secondary_positions=["DM"],
        signal_codes=["consistent_performer"],
        experience_years=8.0,
    ).player_id
    ids["keeper_low"] = seed_talent(
        session,
        key="gk-low",
        display_name="Zainab Okoro",
        position_code="GK",
        composite_score=54.0,
        form_score=61.0,
        competition_level_score=48.0,
        age_years=19,
        nationality_code="NGA",
        availability_status=AvailabilityStatus.AVAILABLE.value,
        verification_tier=VerificationTier.UNVERIFIED.value,
        tactical_roles=["sweeper_keeper"],
        experience_years=1.0,
        preferred_foot="left",
    ).player_id
    ids["draft"] = seed_talent(
        session,
        key="draft",
        display_name="Hidden Draft",
        composite_score=99.0,
        visibility_state=VisibilityState.DRAFT.value,
    ).player_id
    ids["suspended"] = seed_talent(
        session,
        key="suspended",
        display_name="Suspended Talent",
        composite_score=97.0,
        visibility_state=VisibilityState.SUSPENDED.value,
    ).player_id
    return ids


def _search(client: TestClient, **params) -> dict:
    response = client.get("/talent/search", params=params)
    assert response.status_code == 200, response.text
    return response.json()


# ----------------------------------------------------------------------
# Visibility
# ----------------------------------------------------------------------


def test_search_returns_only_published_talent(client: TestClient, catalogue: dict[str, str]) -> None:
    payload = _search(client)

    returned = {item["player_id"] for item in payload["items"]}
    assert catalogue["draft"] not in returned
    assert catalogue["suspended"] not in returned
    assert payload["pagination"]["total"] == 3


def test_default_search_is_ranked_and_bounded(client: TestClient, catalogue: dict[str, str]) -> None:
    payload = _search(client)

    scores = [item["composite_score"] for item in payload["items"]]
    assert scores == sorted(scores, reverse=True)
    assert payload["pagination"]["per_page"] <= SEARCH_MAX_PAGE_SIZE
    assert payload["applied_filters"]["visibility_state"] == VisibilityState.PUBLISHED.value


# ----------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------


def test_position_filter_matches_primary_or_secondary(client: TestClient, catalogue: dict[str, str]) -> None:
    any_position = _search(client, positions=["DM"])
    preferred_only = _search(client, preferred_positions=["DM"])

    assert [item["player_id"] for item in any_position["items"]] == [catalogue["midfielder_mid"]]
    assert preferred_only["items"] == []


def test_filters_compose(client: TestClient, catalogue: dict[str, str]) -> None:
    payload = _search(client, nationality_codes=["NGA"], max_age=20)

    assert [item["player_id"] for item in payload["items"]] == [catalogue["keeper_low"]]


@pytest.mark.parametrize(
    ("params", "expected_key"),
    [
        ({"tactical_roles": ["sweeper_keeper"]}, "keeper_low"),
        ({"preferred_foot": "left"}, "keeper_low"),
        ({"availability": ["contracted"]}, "midfielder_mid"),
        ({"min_verification_tier": "credentials_verified"}, "striker_top"),
        ({"min_composite_score": 80}, "striker_top"),
        ({"min_competition_level_score": 80}, "striker_top"),
        ({"min_experience_years": 6}, "midfielder_mid"),
        ({"featured_only": True}, "striker_top"),
        ({"q": "kofi"}, "midfielder_mid"),
        ({"location_region": "accra"}, "midfielder_mid"),
    ],
)
def test_each_filter_narrows_to_the_expected_talent(
    client: TestClient, catalogue: dict[str, str], params: dict, expected_key: str
) -> None:
    payload = _search(client, **params)

    assert [item["player_id"] for item in payload["items"]] == [catalogue[expected_key]]


def test_age_range_filter(client: TestClient, catalogue: dict[str, str]) -> None:
    payload = _search(client, min_age=20, max_age=24)

    assert [item["player_id"] for item in payload["items"]] == [catalogue["striker_top"]]


def test_signal_filter_requires_all_requested_signals(client: TestClient, catalogue: dict[str, str]) -> None:
    # `progression` is public; asking for it anonymously is fine.
    payload = _search(client, required_signals=["progression"])
    assert [item["player_id"] for item in payload["items"]] == [catalogue["striker_top"]]

    payload = _search(client, required_signals=["progression", "consistent_performer"])
    assert payload["items"] == []


def test_unknown_filter_values_are_rejected(client: TestClient, catalogue: dict[str, str]) -> None:
    assert client.get("/talent/search", params={"positions": ["QB"]}).status_code == 422
    assert client.get("/talent/search", params={"tactical_roles": ["libero"]}).status_code == 422
    assert client.get("/talent/search", params={"availability": ["vibing"]}).status_code == 422


# ----------------------------------------------------------------------
# Sorting and stability
# ----------------------------------------------------------------------


@pytest.mark.parametrize("sort", ["ranking", "form", "age_asc", "age_desc", "competition_level", "name"])
def test_repeated_requests_return_an_identical_ordering(
    client: TestClient, catalogue: dict[str, str], sort: str
) -> None:
    first = _search(client, sort=sort)
    second = _search(client, sort=sort)

    assert [item["player_id"] for item in first["items"]] == [item["player_id"] for item in second["items"]]


def test_sort_selects_the_expected_leader(client: TestClient, catalogue: dict[str, str]) -> None:
    assert _search(client, sort="ranking")["items"][0]["player_id"] == catalogue["striker_top"]
    assert _search(client, sort="age_asc")["items"][0]["player_id"] == catalogue["keeper_low"]
    assert _search(client, sort="age_desc")["items"][0]["player_id"] == catalogue["midfielder_mid"]
    assert _search(client, sort="name")["items"][0]["display_name"] == "Amara Bello"


def test_equal_scores_break_ties_deterministically(session: Session, client: TestClient) -> None:
    for suffix in ("c", "a", "b"):
        seed_talent(session, key=f"tie-{suffix}", display_name=f"Tie {suffix}", composite_score=70.0)

    first = _search(client)
    second = _search(client)

    ids = [item["player_id"] for item in first["items"]]
    assert ids == sorted(ids)
    assert ids == [item["player_id"] for item in second["items"]]


# ----------------------------------------------------------------------
# Pagination
# ----------------------------------------------------------------------


def test_pagination_partitions_the_result_set(session: Session, client: TestClient) -> None:
    for index in range(12):
        seed_talent(
            session,
            key=f"page-{index:02d}",
            display_name=f"Page Talent {index:02d}",
            composite_score=50.0 + index,
        )

    first = _search(client, per_page=5, page=1)
    second = _search(client, per_page=5, page=2)
    third = _search(client, per_page=5, page=3)

    assert first["pagination"] == {
        "page": 1,
        "per_page": 5,
        "total": 12,
        "total_pages": 3,
        "has_next": True,
        "has_previous": False,
    }
    assert third["pagination"]["has_next"] is False
    assert third["pagination"]["has_previous"] is True

    seen = [item["player_id"] for page in (first, second, third) for item in page["items"]]
    assert len(seen) == 12
    assert len(set(seen)) == 12


def test_empty_result_set_reports_zero_pages(client: TestClient, catalogue: dict[str, str]) -> None:
    payload = _search(client, min_composite_score=99.5)

    assert payload["items"] == []
    assert payload["pagination"]["total"] == 0
    assert payload["pagination"]["total_pages"] == 0
    assert payload["pagination"]["has_next"] is False


def test_page_beyond_the_end_is_empty_but_valid(session: Session, client: TestClient) -> None:
    seed_talent(session, key="solo", display_name="Solo Talent")

    payload = _search(client, per_page=5, page=4)

    assert payload["items"] == []
    assert payload["pagination"]["total"] == 1


# ----------------------------------------------------------------------
# Query bounding
# ----------------------------------------------------------------------


def test_page_size_ceiling_is_enforced(client: TestClient) -> None:
    response = client.get("/talent/search", params={"per_page": SEARCH_MAX_PAGE_SIZE + 1})
    assert response.status_code == 422


def test_deep_paging_is_refused_rather_than_scanned(client: TestClient) -> None:
    too_deep = (SEARCH_MAX_RESULT_WINDOW // SEARCH_MAX_PAGE_SIZE) + 1
    response = client.get("/talent/search", params={"per_page": SEARCH_MAX_PAGE_SIZE, "page": too_deep})

    assert response.status_code == 422
    assert str(SEARCH_MAX_RESULT_WINDOW) in response.text


def test_result_window_is_enforced_for_non_http_callers() -> None:
    with pytest.raises(ValueError):
        TalentSearchRequest(page=1000, per_page=50)


def test_short_and_long_text_queries_are_rejected(client: TestClient) -> None:
    assert client.get("/talent/search", params={"q": "a"}).status_code == 422
    assert client.get("/talent/search", params={"q": "x" * 200}).status_code == 422


def test_inverted_ranges_are_rejected(client: TestClient) -> None:
    assert client.get("/talent/search", params={"min_age": 30, "max_age": 20}).status_code == 422
    assert (
        client.get("/talent/search", params={"min_composite_score": 90, "max_composite_score": 10}).status_code == 422
    )


def test_post_search_accepts_the_same_bounded_contract(client: TestClient, catalogue: dict[str, str]) -> None:
    response = client.post("/talent/search", json={"positions": ["ST"], "per_page": 10})

    assert response.status_code == 200, response.text
    assert [item["player_id"] for item in response.json()["items"]] == [catalogue["striker_top"]]

    rejected = client.post("/talent/search", json={"per_page": 5000})
    assert rejected.status_code == 422


def test_unknown_query_fields_are_rejected_by_the_body_contract(client: TestClient) -> None:
    response = client.post("/talent/search", json={"order_by": "'; DROP TABLE talent_profiles;--"})
    assert response.status_code == 422
