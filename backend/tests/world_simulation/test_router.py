from __future__ import annotations


def test_world_read_endpoints_expose_context_and_narratives(client) -> None:
    client.put(
        "/admin/world/cultures/lagos-night-pressure",
        json={
            "display_name": "Lagos Night Pressure",
            "scope_type": "city",
            "country_code": "NG",
            "region_name": "Lagos",
            "city_name": "Lagos",
            "play_style_summary": "Fast starts and loud atmospheres push home momentum.",
            "supporter_traits_json": ["electric", "traveling"],
            "rivalry_themes_json": ["coastal bragging rights"],
            "talent_archetypes_json": ["direct winger", "box-crasher"],
            "climate_notes": "Humidity sharpens the tempo late in matches.",
            "active": True,
            "metadata_json": {},
        },
    )
    client.put(
        "/admin/world/clubs/club-alpha/context",
        json={
            "culture_key": "lagos-night-pressure",
            "narrative_phase": "continental_push",
            "supporter_mood": "electric",
            "derby_heat_score": 70,
            "global_appeal_score": 66,
            "identity_keywords_json": ["harbor city", "lights"],
            "transfer_identity_tags_json": ["win-now"],
            "fan_culture_tags_json": ["noise", "ritual"],
            "world_flags_json": ["continental_push"],
            "metadata_json": {},
        },
    )
    client.put(
        "/admin/world/narratives/alpha-under-lights",
        json={
            "club_id": "club-alpha",
            "arc_type": "title_charge",
            "headline": "Alpha under lights",
            "summary": "Alpha's late kickoffs are becoming a local myth.",
            "importance_score": 84,
            "simulation_horizon": "seasonal",
            "tags_json": ["derby", "headline"],
            "impact_vectors_json": ["fan_engagement_lift"],
            "metadata_json": {},
        },
    )
    client.put(
        "/admin/world/narratives/mythic-derby-cup-chaos",
        json={
            "competition_id": "competition-1",
            "arc_type": "cup_chaos",
            "headline": "Mythic Derby Cup chaos",
            "summary": "The bracket has tilted toward rivalry matchups.",
            "importance_score": 72,
            "simulation_horizon": "match_window",
            "tags_json": ["rivalry"],
            "impact_vectors_json": ["storyline_acceleration"],
            "metadata_json": {},
        },
    )

    cultures_response = client.get("/api/world/cultures")
    club_context_response = client.get("/api/world/clubs/club-alpha/context")
    narratives_response = client.get("/api/world/narratives", params={"club_id": "club-alpha"})
    competition_context_response = client.get("/api/world/competitions/competition-1/context")

    assert cultures_response.status_code == 200
    assert club_context_response.status_code == 200
    assert narratives_response.status_code == 200
    assert competition_context_response.status_code == 200

    cultures_payload = cultures_response.json()
    club_payload = club_context_response.json()
    narratives_payload = narratives_response.json()
    competition_payload = competition_context_response.json()

    assert any(item["culture_key"] == "lagos-night-pressure" for item in cultures_payload)
    assert club_payload["club_id"] == "club-alpha"
    assert club_payload["world_profile"]["supporter_mood"] == "electric"
    assert any(item["hook_key"] == "fan-engagement-lift" for item in club_payload["simulation_hooks"])
    assert narratives_payload[0]["slug"] == "alpha-under-lights"
    assert competition_payload["competition_id"] == "competition-1"
    assert any(item["hook_key"] == "storyline-acceleration" for item in competition_payload["simulation_hooks"])


def test_admin_world_routes_validate_missing_targets(client) -> None:
    narrative_response = client.put(
        "/admin/world/narratives/missing-club-arc",
        json={
            "club_id": "club-missing",
            "arc_type": "rebuild",
            "headline": "Missing club arc",
            "summary": "",
            "importance_score": 30,
            "simulation_horizon": "seasonal",
            "tags_json": [],
            "impact_vectors_json": [],
            "metadata_json": {},
        },
    )
    club_context_response = client.get("/api/world/clubs/club-missing/context")

    assert narrative_response.status_code == 404
    assert narrative_response.json()["detail"] == "club_not_found"
    assert club_context_response.status_code == 404
    assert club_context_response.json()["detail"] == "club_not_found"
