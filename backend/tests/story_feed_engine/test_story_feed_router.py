from __future__ import annotations


def _login(client, *, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_story_feed_lists_auto_generated_national_team_stories(client, demo_seed) -> None:
    admin_headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")
    response = client.post(
        "/admin/national-team-engine/competitions",
        headers=admin_headers,
        json={
            "key": "afcon-2032",
            "title": "AFCON Showcase",
            "season_label": "2032",
            "region_type": "africa",
            "age_band": "senior",
            "format_type": "cup",
            "status": "published",
        },
    )
    assert response.status_code == 200, response.text

    feed_response = client.get("/story-feed")
    assert feed_response.status_code == 200
    stories = feed_response.json()
    assert any(item["story_type"] == "national_team_launch" for item in stories)


def test_admin_can_publish_manual_story_and_digest_surfaces_it(client) -> None:
    admin_headers = _login(client, email="vidvimedialtd@gmail.com", password="NewPass1234!")
    response = client.post(
        "/admin/story-feed",
        headers=admin_headers,
        json={
            "story_type": "featured_update",
            "title": "Transfer window heating up",
            "body": "Several clubs are circling academy standouts this week.",
            "subject_type": "club_sale_transfer",
            "subject_id": "club_transfer_demo",
            "country_code": "NG",
            "featured": True,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["featured"] is True

    digest_response = client.get("/story-feed/digest?country_code=NG")
    assert digest_response.status_code == 200, digest_response.text
    digest = digest_response.json()
    assert any(item["story_type"] == "featured_update" for item in digest["feature_stories"])

    filtered_response = client.get("/story-feed?subject_type=club_sale_transfer&subject_id=club_transfer_demo&featured_only=true")
    assert filtered_response.status_code == 200, filtered_response.text
    filtered_payload = filtered_response.json()
    assert len(filtered_payload) == 1
    assert filtered_payload[0]["subject_id"] == "club_transfer_demo"
