from __future__ import annotations

from app.world_simulation.schemas import (
    ClubWorldProfileUpsertRequest,
    FootballCultureUpsertRequest,
    WorldNarrativeUpsertRequest,
)
from app.world_simulation.service import FootballWorldService


def test_club_context_merges_curated_world_profile_and_narrative_hooks(session, seeded_context) -> None:
    service = FootballWorldService(session)
    service.upsert_culture(
        culture_key="lagos-night-pressure",
        payload=FootballCultureUpsertRequest(
            display_name="Lagos Night Pressure",
            scope_type="city",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            play_style_summary="Fast starts and loud atmospheres push home momentum.",
            supporter_traits_json=["electric", "traveling"],
            rivalry_themes_json=["coastal bragging rights"],
            talent_archetypes_json=["direct winger", "box-crasher"],
            climate_notes="Humidity sharpens the tempo late in matches.",
        ),
    )
    service.upsert_club_world_profile(
        club_id="club-alpha",
        payload=ClubWorldProfileUpsertRequest(
            culture_key="lagos-night-pressure",
            narrative_phase="continental_push",
            supporter_mood="electric",
            derby_heat_score=74,
            global_appeal_score=68,
            identity_keywords_json=["harbor city", "lights"],
            transfer_identity_tags_json=["win-now"],
            fan_culture_tags_json=["noise", "ritual"],
            world_flags_json=["continental_push"],
            metadata_json={"curated_by": "test"},
        ),
    )
    service.upsert_narrative_arc(
        narrative_slug="alpha-under-lights",
        payload=WorldNarrativeUpsertRequest(
            club_id="club-alpha",
            arc_type="title_charge",
            headline="Alpha under lights",
            summary="Alpha's night fixtures are becoming appointment viewing.",
            importance_score=88,
            simulation_horizon="seasonal",
            tags_json=["derby", "headline"],
            impact_vectors_json=["fan_engagement_lift", "transfer_attention"],
        ),
    )
    session.commit()

    context = service.club_context("club-alpha")
    hook_keys = {item["hook_key"] for item in context["simulation_hooks"]}

    assert context["culture"] is not None
    assert context["culture"].culture_key == "lagos-night-pressure"
    assert context["world_profile"]["source"] == "curated"
    assert context["world_profile"]["narrative_phase"] == "continental_push"
    assert context["world_profile"]["supporter_mood"] == "electric"
    assert context["world_profile"]["derby_heat_score"] >= 74
    assert context["active_narratives"][0].slug == "alpha-under-lights"
    assert {"culture-resonance", "derby-volatility", "fan-engagement-lift", "transfer-attention"}.issubset(hook_keys)


def test_competition_context_uses_narratives_and_participant_density(session, seeded_context) -> None:
    service = FootballWorldService(session)
    service.upsert_narrative_arc(
        narrative_slug="mythic-derby-cup-chaos",
        payload=WorldNarrativeUpsertRequest(
            competition_id="competition-1",
            arc_type="cup_chaos",
            headline="Mythic Derby Cup chaos",
            summary="The bracket has tilted into rivalry territory earlier than expected.",
            importance_score=72,
            simulation_horizon="match_window",
            tags_json=["rivalry"],
            impact_vectors_json=["storyline_acceleration"],
        ),
    )
    session.commit()

    context = service.competition_context("competition-1")
    hook_keys = {item["hook_key"] for item in context["simulation_hooks"]}

    assert context["participant_count"] == 2
    assert context["active_narratives"][0].slug == "mythic-derby-cup-chaos"
    assert "fan-attention-window" in hook_keys
    assert "discovery-lift" in hook_keys
    assert "storyline-acceleration" in hook_keys
