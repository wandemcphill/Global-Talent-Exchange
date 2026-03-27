from __future__ import annotations

from sqlalchemy import select

from app.models.regen import RegenDiscoveryBadge, RegenLegacyRecord, RegenLineageProfile, RegenProfile, RegenScoutReport
from app.regen_universe.service import RegenUniverseService
from tests.regen_universe_support import build_regen_universe_session, seed_two_season_universe


def test_regen_universe_showcase_player_exposes_core_card_story_and_legacy() -> None:
    session = build_regen_universe_session()
    try:
        bundle = seed_two_season_universe(session)
        wonderkid = bundle["players"]["wonderkid"]
        regen = session.scalar(select(RegenProfile).where(RegenProfile.player_id == wonderkid.id))
        assert regen is not None

        regen.is_special_lineage = True
        regen.metadata_json = {
            **dict(regen.metadata_json or {}),
            "uniqueness_score": 0.91,
            "story_seed": {
                "background": "street footballer",
                "temperament": "aggressive",
                "ambition": "world_class",
                "pressure_response": "clutch",
                "snippet": "Street footballer with world-class ambition and a clutch edge.",
            },
        }
        session.add(
            RegenLineageProfile(
                regen_id=regen.id,
                relationship_type="son_of_legend",
                related_legend_type="real_legend",
                related_legend_ref_id="legend-77",
                lineage_country_code="NG",
                lineage_hometown_code="Lagos",
                is_real_legend_lineage=True,
                lineage_tier="elite",
                narrative_text="The latest branch of a famous Lagos bloodline.",
                metadata_json={"origin": "showcase-test"},
            )
        )
        session.add(
            RegenDiscoveryBadge(
                regen_id=regen.id,
                club_id="club-profile-1",
                badge_code="bloodline",
                badge_name="Bloodline",
                metadata_json={},
            )
        )
        session.add(
            RegenLegacyRecord(
                regen_id=regen.id,
                player_id=wonderkid.id,
                club_id="club-profile-1",
                appearances_total=82,
                goals_total=31,
                assists_total=18,
                awards_total=2,
                seasons_total=2,
                legacy_score=97.5,
                legacy_tier="elite",
                is_legend=False,
                narrative_summary="Already bending the family arc in his own direction.",
                metadata_json={
                    "trophies": 1,
                    "career_path": [{"club_name": "Prestige FC", "season_label": "2026/2027"}],
                },
            )
        )
        session.flush()

        showcase = RegenUniverseService(session).get_player_showcase(wonderkid.id)

        assert showcase is not None
        assert showcase["profile"].regen_type == "legend_regen"
        assert showcase["profile"].story_seed is not None
        assert showcase["profile"].story_seed.pressure_response == "clutch"
        assert showcase["profile"].uniqueness_score >= 0.9
        assert showcase["card"]["regen_type_badge"] == "Legend Echo"
        assert "Bloodline" in showcase["discovery_badges"]
        assert {badge["code"] for badge in showcase["card"]["badges"]} >= {"bloodline", "elite_potential"}
        assert showcase["legacy"]["legacy_score"] == 97.5
    finally:
        session.close()


def test_regen_universe_showcase_lists_rising_stars_bloodlines_and_feed() -> None:
    session = build_regen_universe_session()
    try:
        bundle = seed_two_season_universe(session)
        wonderkid = bundle["players"]["wonderkid"]
        breakout = bundle["players"]["breakout"]

        wonderkid_regen = session.scalar(select(RegenProfile).where(RegenProfile.player_id == wonderkid.id))
        breakout_regen = session.scalar(select(RegenProfile).where(RegenProfile.player_id == breakout.id))
        assert wonderkid_regen is not None
        assert breakout_regen is not None

        wonderkid_regen.current_gsi = 78
        wonderkid_regen.potential_range_json = {"minimum": 88, "maximum": 95}
        wonderkid_regen.metadata_json = {**dict(wonderkid_regen.metadata_json or {}), "uniqueness_score": 0.88}
        breakout_regen.current_gsi = 74
        breakout_regen.potential_range_json = {"minimum": 86, "maximum": 92}
        breakout_regen.metadata_json = {**dict(breakout_regen.metadata_json or {}), "uniqueness_score": 0.83}

        session.add_all(
            [
                RegenLineageProfile(
                    regen_id=wonderkid_regen.id,
                    relationship_type="son_of_legend",
                    related_legend_type="real_legend",
                    related_legend_ref_id="legend-shared",
                    lineage_country_code="NG",
                    lineage_hometown_code="Lagos",
                    is_real_legend_lineage=True,
                    lineage_tier="elite",
                    narrative_text="Shared bloodline branch one.",
                    metadata_json={},
                ),
                RegenLineageProfile(
                    regen_id=breakout_regen.id,
                    relationship_type="son_of_legend",
                    related_legend_type="real_legend",
                    related_legend_ref_id="legend-shared",
                    lineage_country_code="NG",
                    lineage_hometown_code="Lagos",
                    is_real_legend_lineage=True,
                    lineage_tier="elite",
                    narrative_text="Shared bloodline branch two.",
                    metadata_json={},
                ),
                RegenScoutReport(
                    regen_id=breakout_regen.id,
                    club_id="club-profile-1",
                    scout_identity="Lead Scout",
                    manager_style="youth_developer",
                    system_profile="4-3-3",
                    current_ability_estimate=74,
                    future_potential_estimate=92,
                    scout_confidence_bps=8600,
                    role_fit_score=86.0,
                    hidden_gem_score=84.0,
                    wonderkid_signal=True,
                    value_hint_coin=225000,
                    summary_text="Explosive attacker with a hidden-gem profile and immediate breakout runway.",
                    tags_json=["hidden_gem", "wonderkid"],
                    metadata_json={},
                ),
            ]
        )
        session.flush()

        service = RegenUniverseService(session)
        rising_stars = service.list_rising_stars(limit=3)
        bloodlines = service.list_bloodlines(limit=5)
        scouting_feed = service.list_scouting_feed(limit=12)

        assert rising_stars["entries"]
        assert rising_stars["entries"][0]["profile"].player_id == wonderkid.id
        bloodline = next((item for item in bloodlines["entries"] if item["origin_ref_id"] == "legend-shared"), None)
        assert bloodline is not None
        assert len(bloodline["entries"]) == 2
        feed_types = {item["feed_type"] for item in scouting_feed["items"]}
        assert "new_regen_discovered" in feed_types
        assert "hidden_gem" in feed_types
        assert "breakout_player" in feed_types
    finally:
        session.close()
