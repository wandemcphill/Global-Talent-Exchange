from __future__ import annotations

from app.infinite_league.service import InfiniteLeagueRuntime


def test_infinite_league_seed_hydrates_existing_matches_across_runtimes(tmp_path) -> None:
    first = InfiniteLeagueRuntime(
        root_path=tmp_path,
        enabled=False,
        auto_advance=False,
        club_count=4,
        initial_match_count=2,
    )
    second = InfiniteLeagueRuntime(
        root_path=tmp_path,
        enabled=False,
        auto_advance=False,
        club_count=4,
        initial_match_count=2,
    )

    first.ensure_seeded()
    second.ensure_seeded()

    assert len(first._match_order) == 2
    assert len(second._match_order) == 2
    assert {record.result.match_id for record in first._records.values()} == {
        record.result.match_id for record in second._records.values()
    }
    assert len(first.store.recent_results(limit=10)) == 2
    assert len(first.publisher_queue.list_jobs()) >= 1
