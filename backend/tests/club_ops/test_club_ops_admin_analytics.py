from __future__ import annotations


def test_admin_analytics_endpoints_surface_summary_metrics(club_ops_client, seeded_ops_services) -> None:
    del seeded_ops_services

    ops_summary = club_ops_client.get("/api/admin/clubs/ops-summary")
    finance = club_ops_client.get("/api/admin/clubs/finance-analytics")
    sponsorship = club_ops_client.get("/api/admin/clubs/sponsorship-analytics")
    academy = club_ops_client.get("/api/admin/clubs/academy-analytics")
    scouting = club_ops_client.get("/api/admin/clubs/scouting-analytics")

    assert ops_summary.status_code == 200
    assert finance.status_code == 200
    assert sponsorship.status_code == 200
    assert academy.status_code == 200
    assert scouting.status_code == 200

    assert ops_summary.json()["tracked_club_count"] >= 1
    assert finance.json()["total_operating_balance_minor"] > 0
    assert sponsorship.json()["total_contract_value_minor"] > 0
    assert academy.json()["promoted_count"] >= 1
    assert scouting.json()["prospect_count"] >= 1
