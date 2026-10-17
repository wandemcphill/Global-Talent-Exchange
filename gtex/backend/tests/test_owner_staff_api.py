from app.models.club_profile import ClubProfile
from app.owner_console.models import OwnerClubState


def _club(app_session_factory, owner_id: str) -> str:
    with app_session_factory() as session:
        club = ClubProfile(owner_user_id=owner_id, club_name="Lagos Lions", short_name="LAL", slug=f"lagos-lions-{owner_id[:8]}", primary_color="#0F766E", secondary_color="#0F172A", accent_color="#F4C24D", country_code="NG", city_name="Lagos")
        session.add(club)
        session.flush()
        session.add(OwnerClubState(club_id=club.id, owner_user_id=owner_id, club_name=club.club_name, stage="active", world_day=14, facilities_json={"academy": 1}))
        session.commit()
        return club.id


def p(suffix: str) -> str:
    return "/api/owner" + suffix


def test_staff_delegation_and_public_showroom_flow(client, app_session_factory, auth_user_factory):
    owner, stranger = auth_user_factory(), auth_user_factory()
    club_id = _club(app_session_factory, owner["user_id"])
    h = owner["headers"]

    assert client.get(p(f"/clubs/{club_id}/staff")).status_code == 401
    assert client.get(p(f"/clubs/{club_id}/staff"), headers=stranger["headers"]).status_code == 403

    overview = client.get(p(f"/clubs/{club_id}/staff"), headers=h)
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["staff"] == [] and set(body["candidates"]) == {"gm", "hoyd"}
    assert {r["task"] for r in body["reserved"]} == {"player_sale_above_threshold", "manager_hire_fire", "capital_move"}

    gm = body["candidates"]["gm"][0]
    hired = client.post(p(f"/clubs/{club_id}/staff/hire"), json={"candidate_id": gm["candidate_id"]}, headers=h)
    assert hired.status_code == 200, hired.text
    assert hired.json()["role"] == "gm" and hired.json()["name"] == gm["name"]
    again = client.post(p(f"/clubs/{club_id}/staff/hire"), json={"candidate_id": body["candidates"]["gm"][1]["candidate_id"]}, headers=h)
    assert again.status_code == 409

    policy = client.put(p(f"/clubs/{club_id}/delegation/transfer_bid"), json={"mode": "approval", "budget_cap": 2500}, headers=h)
    assert policy.status_code == 200, policy.text
    assert policy.json()["mode"] == "approval" and policy.json()["version"] == 2
    assert client.put(p(f"/clubs/{club_id}/delegation/capital_move"), json={"mode": "auto", "budget_cap": 1}, headers=h).status_code == 400

    run = client.post(p(f"/clubs/{club_id}/staff/run"), headers=h)
    assert run.status_code == 200, run.text
    assert set(run.json()) == {"executed", "recommended"}

    released = client.post(p(f"/clubs/{club_id}/staff/{hired.json()['id']}/release"), headers=h)
    assert released.status_code == 200, released.text

    owner_view = client.get(p(f"/clubs/{club_id}/showroom"), headers=h)
    assert owner_view.status_code == 200, owner_view.text
    assert {"top_players", "sponsors", "facilities"} <= set(owner_view.json())

    assert client.post(p(f"/clubs/{club_id}/showroom/share"), headers=stranger["headers"]).status_code == 403
    code = client.post(p(f"/clubs/{club_id}/showroom/share"), headers=h).json()["code"]
    assert code == client.post(p(f"/clubs/{club_id}/showroom/share"), headers=h).json()["code"]

    public = client.get(p(f"/public/showroom/{code}"))
    assert public.status_code == 200, public.text
    data = public.json()
    assert data["club_name"] == "Lagos Lions" and data["trophies"] == []
    assert "crest_url" in data
    assert not {"top_players", "sponsors", "facilities", "fans", "prestige"} & set(data)
    assert client.get(p("/public/showroom/does-not-exist")).status_code == 404
