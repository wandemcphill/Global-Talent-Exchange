from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.app.club_identity.trophies.repository import InMemoryTrophyRepository
from backend.app.club_identity.trophies.service import (
    DuplicateTrophyAwardError,
    TrophyCabinetService,
)


def _service() -> TrophyCabinetService:
    return TrophyCabinetService(repository=InMemoryTrophyRepository())


def test_trophy_award_creation_persists_metadata_and_snapshot() -> None:
    service = _service()

    award = service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="league_title",
        season_label="2026",
        final_result_summary="Won league by 6 points",
        earned_at=datetime(2026, 5, 21, 20, 0, tzinfo=timezone.utc),
        captain_name="Ayo Captain",
        top_performer_name="Bola Striker",
        award_reference="league-2026-alpha",
    )
    archive = service.get_season_honors("club-alpha", season_label="2026")

    assert award.club_id == "club-alpha"
    assert award.trophy_type == "league_title"
    assert award.competition_region == "Africa"
    assert award.competition_tier == "domestic"
    assert award.captain_name == "Ayo Captain"
    assert award.top_performer_name == "Bola Striker"
    assert archive.season_records[0].total_honors_count == 1
    assert archive.season_records[0].honors[0].trophy_win_id == award.trophy_win_id


def test_multi_season_honors_retrieval_returns_latest_snapshots_per_season() -> None:
    service = _service()
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="league_title",
        season_label="2026",
        final_result_summary="Won league by 6 points",
        award_reference="league-2026",
    )
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="champions_league",
        season_label="2027",
        final_result_summary="Beat Beta United 2-1 in the final",
        award_reference="ucl-2027",
    )
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="fast_cup",
        season_label="2027",
        final_result_summary="Fast Cup Final 3-2",
        award_reference="fastcup-2027",
    )

    archive = service.get_season_honors("club-alpha")

    assert [record.season_label for record in archive.season_records] == ["2027", "2026"]
    assert archive.season_records[0].total_honors_count == 2
    assert archive.season_records[1].total_honors_count == 1


def test_major_vs_total_honors_counts_are_tracked_separately() -> None:
    service = _service()
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="league_title",
        season_label="2026",
        final_result_summary="League champions",
        award_reference="league-2026",
    )
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="world_super_cup",
        season_label="2027",
        final_result_summary="World Super Cup champions",
        award_reference="wsc-2027",
    )
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="fair_play",
        season_label="2027",
        final_result_summary="Lowest card count",
        award_reference="fairplay-2027",
    )

    cabinet = service.get_trophy_cabinet("club-alpha")

    assert cabinet.total_honors_count == 3
    assert cabinet.major_honors_count == 2
    assert cabinet.elite_honors_count == 1
    assert "1x African League Champion" in cabinet.summary_outputs
    assert "1x GTEX World Super Cup Winner" in cabinet.summary_outputs


def test_timeline_orders_honors_by_most_recent_earned_date() -> None:
    service = _service()
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="fast_cup",
        season_label="2025",
        final_result_summary="Fast Cup Final",
        earned_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
        award_reference="fast-2025",
    )
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="league_title",
        season_label="2026",
        final_result_summary="League champions",
        earned_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        award_reference="league-2026",
    )
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="world_super_cup",
        season_label="2027",
        final_result_summary="World champions",
        earned_at=datetime(2027, 8, 1, tzinfo=timezone.utc),
        award_reference="wsc-2027",
    )

    timeline = service.get_honors_timeline("club-alpha")

    assert [honor.trophy_type for honor in timeline.honors] == [
        "world_super_cup",
        "league_title",
        "fast_cup",
    ]


def test_duplicate_award_protection_uses_award_reference() -> None:
    service = _service()
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="league_title",
        season_label="2026",
        final_result_summary="League champions",
        award_reference="league-2026",
    )

    with pytest.raises(DuplicateTrophyAwardError):
        service.award_trophy(
            club_id="club-alpha",
            club_name="Alpha FC",
            trophy_type="league_title",
            season_label="2026",
            final_result_summary="League champions",
            award_reference="league-2026",
        )


def test_academy_and_senior_honors_can_be_retrieved_separately() -> None:
    service = _service()
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="league_title",
        season_label="2026",
        final_result_summary="Senior champions",
        award_reference="senior-2026",
    )
    service.award_trophy(
        club_id="club-alpha",
        club_name="Alpha FC",
        trophy_type="academy_champions_league",
        season_label="2026",
        final_result_summary="Academy continental champions",
        award_reference="academy-2026",
    )

    overall = service.get_trophy_cabinet("club-alpha")
    academy_only = service.get_trophy_cabinet("club-alpha", team_scope="academy")
    senior_only = service.get_trophy_cabinet("club-alpha", team_scope="senior")

    assert overall.total_honors_count == 2
    assert overall.senior_honors_count == 1
    assert overall.academy_honors_count == 1
    assert academy_only.total_honors_count == 1
    assert academy_only.summary_outputs == ("1x Academy Champions League Winner",)
    assert senior_only.summary_outputs == ("1x African League Champion",)
