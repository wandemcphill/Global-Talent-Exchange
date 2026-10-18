from decimal import Decimal

from app.models.club_profile import ClubProfile
from backend.tests.test_owner_staff_api import _club, p


def test_public_club_page_net_worth_and_money_history(client, app_session_factory, auth_user_factory):
    owner, stranger = auth_user_factory(), auth_user_factory()
    club_id = _club(app_session_factory, owner["user_id"])
    h = owner["headers"]

    page = client.get(p(f"/public/clubs/{club_id}"))
    assert page.status_code == 200, page.text
    data = page.json()
    assert set(data) == {"club_id", "overview", "honours", "staff", "facilities", "commercial"}
    o = data["overview"]
    assert o["club_name"] == "Lagos Lions" and o["city"] == "Lagos" and o["country_code"] == "NG"
    assert o["continent"] == {"code": "africa", "label": "Africa"}
    assert data["staff"]["owner"]
    assert set(data["honours"]) == {"trophies", "record", "milestones"}
    flat = page.text
    for secret in ("cash", "salary", "per_match_gross", "budget_cap", "club_share", "ledger"):
        assert secret not in flat

    assert client.get(p("/public/clubs/not-a-club")).status_code == 404
    with app_session_factory() as session:
        session.get(ClubProfile, club_id).visibility = "private"
        session.commit()
    assert client.get(p(f"/public/clubs/{club_id}")).status_code == 404
    with app_session_factory() as session:
        session.get(ClubProfile, club_id).visibility = "public"
        session.commit()

    assert client.get(p("/net-worth")).status_code == 401
    worth = client.get(p("/net-worth"), headers=h)
    assert worth.status_code == 200, worth.text
    w = worth.json()
    assert len(w["clubs"]) == 1 and w["clubs"][0]["stake_pct"] == "100.00"
    assert Decimal(w["net_worth"]) == Decimal(w["personal_cash"]) + Decimal(w["equity"]) - Decimal(w["liabilities"])
    assert Decimal(w["clubs"][0]["stake_value"]) == Decimal(w["clubs"][0]["valuation"]["total"])
    assert client.get(p("/net-worth"), headers=stranger["headers"]).json()["clubs"] == []

    assert client.get(p(f"/clubs/{club_id}/money-history"), headers=stranger["headers"]).status_code == 403
    history = client.get(p(f"/clubs/{club_id}/money-history"), headers=h)
    assert history.status_code == 200, history.text
    m = history.json()
    assert set(m) >= {"lifetime_income", "lifetime_spend", "income_by_type", "spend_by_type", "value_history", "events"}
    assert Decimal(m["lifetime_income"]) - Decimal(m["lifetime_spend"]) == (Decimal(m["events"][0]["balance_after"]) if m["events"] else Decimal("0"))
