from __future__ import annotations


def test_sponsorship_placements_fallback(client):
    response = client.post(
        "/sponsorship/placements",
        json={
            "competition_id": "friendly-cup",
            "stage_name": "Group Stage",
            "region_code": "NA",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["placements"]
    for placement in body["placements"]:
        assert placement["sponsor_name"] == "GTEX"
        assert placement["fallback"] is True
