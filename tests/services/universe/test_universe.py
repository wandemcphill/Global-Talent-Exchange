from __future__ import annotations

from services.universe import LeagueEngine, UniverseGenerator, UniverseStore, create_league, fixtures_by_round, generate_fixtures


def test_universe_generator_and_scheduler_create_full_league() -> None:
    generator = UniverseGenerator(seed=7)
    league = create_league(generator=generator, club_count=20)
    fixtures = generate_fixtures(league.clubs)

    assert len(league.clubs) == 20
    assert len({club.name for club in league.clubs}) == 20
    assert len(fixtures) == 380
    assert len(fixtures_by_round(fixtures)) == 38


def test_league_engine_simulates_publishable_result() -> None:
    generator = UniverseGenerator(seed=22)
    league = create_league(generator=generator, club_count=4)
    fixture = generate_fixtures(league.clubs, home_and_away=False)[0]

    result = LeagueEngine(seed=22).simulate_fixture(league=league, fixture=fixture)

    assert result.match_id.startswith("match_fix_")
    assert result.commentary_prompt
    assert result.pundit_prompt
    assert 35 <= result.viral_score <= 99
    assert result.highlight_payload["video_path"].endswith("/raw.mp4")
    assert result.highlight_payload["polished_video_path"].endswith("/polished.mp4")
    assert result.highlight_payload["match_id"] == result.match_id
    assert "commentary_prompt" in result.highlight_payload["metadata"]
    assert set(result.content_brief["narrative_flags"]) == {
        "rivalry",
        "revenge_match",
        "underdog",
        "pressure_match",
        "title_race",
    }


def test_universe_store_persists_fixture_and_match_history(tmp_path) -> None:
    generator = UniverseGenerator(seed=31)
    league = create_league(generator=generator, club_count=4)
    fixtures = generate_fixtures(league.clubs, home_and_away=False)
    engine = LeagueEngine(seed=31)
    result = engine.simulate_fixture(league=league, fixture=fixtures[0])
    store = UniverseStore(tmp_path / "universe.db")

    store.save_league(league)
    store.save_fixtures(league_id=league.league_id, fixtures=fixtures)
    store.save_match_result(result)

    scheduled = store.list_fixtures(league_id=league.league_id)
    recent_results = store.recent_results(league_id=league.league_id)
    head_to_head = store.recent_head_to_head(
        club_a_id=fixtures[0].home_club_id,
        club_b_id=fixtures[0].away_club_id,
    )

    assert len(scheduled) == len(fixtures)
    assert recent_results[0]["match_id"] == result.match_id
    assert head_to_head[0]["fixture_id"] == fixtures[0].fixture_id
