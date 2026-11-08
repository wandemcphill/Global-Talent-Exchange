from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.club_identity.dna_router import router as dna_router


@pytest.fixture
def studio_client() -> TestClient:
    test_app = FastAPI()
    test_app.include_router(dna_router)
    return TestClient(test_app)


def test_studio_recommendation_endpoint(studio_client: TestClient):
    resp = studio_client.post(
        "/api/clubs/studio/recommend",
        json={
            "club_name": "Olympique Belleville",
            "country_code": "FRA",
            "city_name": "Paris",
            "recruitment_focus": "academy",
            "preferred_age_bracket": "U21",
            "nationality_focus": "preferred",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["club_name"] == "Olympique Belleville"
    assert data["primary_philosophy"] == "academy_first"
    assert "youth_development" in data["secondary_philosophies"]
    assert data["age_mode"] == "preferred"
    assert data["preferred_max_age"] == 21
    assert data["target_nationalities"] == ["FRA"]
    assert len(data["crest_concepts"]) == 3
    assert "concept_id" in data["crest_concepts"][0]
    assert data["crest_concepts"][0]["svg_markup"].startswith("<svg")
    assert data["crest_concepts"][0]["data_uri"].startswith("data:image/svg+xml;base64,")
    assert "home" in data["kit_concepts"]
    assert "away" in data["kit_concepts"]
    assert "third" in data["kit_concepts"]
    assert "goalkeeper" in data["kit_concepts"]


def test_studio_conversational_edit_endpoint(studio_client: TestClient):
    current_kit = {
        "primary_color": "#1E3A8A",
        "secondary_color": "#FFFFFF",
        "accent_color": "#F59E0B",
        "pattern_type": "solid",
        "collar_style": "crew",
        "sleeve_style": "short",
    }
    current_crest = {
        "shape": "shield",
        "icon_family": "lion",
        "primary_color": "#1E3A8A",
        "secondary_color": "#FFFFFF",
        "accent_color": "#F59E0B",
        "initials": "OB",
        "trophy_stars": 1,
        "style": "traditional",
    }
    resp = studio_client.post(
        "/api/clubs/studio/edit",
        json={
            "current_kit": current_kit,
            "current_crest": current_crest,
            "instruction": "give me vertical stripes and change primary color to dark blue and gold with polo collar",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["kit"]["pattern_type"] == "stripes"
    assert data["kit"]["collar_style"] == "polo"
    assert data["kit"]["accent_color"] == "#F59E0B"
    assert "summary" in data
    assert "stripes" in data["summary"].lower()
    assert data["crest"]["svg_markup"].startswith("<svg")
