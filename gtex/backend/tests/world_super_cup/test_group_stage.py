from __future__ import annotations

from datetime import datetime, timezone

from app.world_super_cup.services.tournament import WorldSuperCupService


def test_group_stage_advances_top_two_from_all_eight_groups() -> None:
    plan = WorldSuperCupService().build_demo_tournament(datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc))

    groups = plan.group_stage.groups
    tables = plan.group_stage.tables
    advancing_clubs = plan.group_stage.advancing_clubs

    assert len(groups) == 8
    assert all(len(group.clubs) == 4 for group in groups)
    assert len(advancing_clubs) == 16
    assert len({club.club_id for club in advancing_clubs}) == 16

    advancing_by_group = {}
    for row in tables:
        if row.position <= 2:
            advancing_by_group.setdefault(row.group_name, []).append(row.club.club_id)

    assert sorted(advancing_by_group) == ["A", "B", "C", "D", "E", "F", "G", "H"]
    assert all(len(clubs) == 2 for clubs in advancing_by_group.values())
