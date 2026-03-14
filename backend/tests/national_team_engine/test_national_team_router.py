from __future__ import annotations


def _login(client, *, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_national_team_competition_and_entry(client, demo_seed) -> None:
    admin_headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")
    response = client.post(
        "/admin/national-team-engine/competitions",
        headers=admin_headers,
        json={
            "key": "gtex-world-cup-2030",
            "title": "GTEX World Cup",
            "season_label": "2030",
            "region_type": "global",
            "age_band": "senior",
            "format_type": "cup",
            "status": "published",
        },
    )
    assert response.status_code == 200, response.text
    competition = response.json()

    manager_user = demo_seed.demo_users[0]
    entry_response = client.post(
        f"/admin/national-team-engine/competitions/{competition['id']}/entries",
        headers=admin_headers,
        json={
            "country_code": "NG",
            "country_name": "Nigeria",
            "manager_user_id": manager_user.id,
            "metadata_json": {"seed": 1},
        },
    )
    assert entry_response.status_code == 200, entry_response.text
    entry = entry_response.json()
    assert entry["country_code"] == "NG"
    assert entry["manager_user_id"] == manager_user.id

    list_response = client.get("/national-team-engine/competitions")
    assert list_response.status_code == 200
    assert any(item["key"] == "gtex-world-cup-2030" for item in list_response.json())


def test_admin_can_upsert_squad_and_user_can_view_history(client, demo_seed) -> None:
    admin_headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")
    user_headers = _login(client, email=demo_seed.demo_users[0].email, password=demo_seed.demo_users[0].password)
    competition_id = client.get("/national-team-engine/competitions").json()[0]["id"]
    entry_response = client.post(
        f"/admin/national-team-engine/competitions/{competition_id}/entries",
        headers=admin_headers,
        json={
            "country_code": "GH",
            "country_name": "Ghana",
            "manager_user_id": demo_seed.demo_users[0].id,
            "metadata_json": {"seed": 2},
        },
    )
    assert entry_response.status_code == 200, entry_response.text
    entry = entry_response.json()

    squad_response = client.post(
        f"/admin/national-team-engine/entries/{entry['id']}/squad",
        headers=admin_headers,
        json={
            "members": [
                {
                    "user_id": demo_seed.demo_users[0].id,
                    "player_name": "Demo Captain",
                    "shirt_number": 8,
                    "role_label": "captain",
                    "status": "selected",
                },
                {
                    "user_id": demo_seed.demo_users[1].id,
                    "player_name": "Demo Striker",
                    "shirt_number": 9,
                    "role_label": "forward",
                    "status": "selected",
                },
            ]
        },
    )
    assert squad_response.status_code == 200, squad_response.text
    detail = squad_response.json()
    assert detail["squad_size"] == 2
    assert len(detail["squad_members"]) == 2

    history_response = client.get("/national-team-engine/me/history", headers=user_headers)
    assert history_response.status_code == 200, history_response.text
    history = history_response.json()
    assert len(history["managed_entries"]) >= 1
    assert len(history["squad_memberships"]) >= 1
