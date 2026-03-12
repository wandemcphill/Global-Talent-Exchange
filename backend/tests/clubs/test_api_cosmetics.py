from __future__ import annotations

def test_cosmetic_catalog_and_purchase_endpoints_are_explicit_and_auditable(client, create_club) -> None:
    profile = create_club(slug="shop-fc")
    club_id = profile["id"]

    catalog_response = client.get("/api/clubs/catalog")
    assert catalog_response.status_code == 200
    items = catalog_response.json()["items"]
    assert items

    purchase_response = client.post(
        "/api/clubs/catalog/purchase",
        json={
            "club_id": club_id,
            "catalog_item_id": items[0]["id"],
            "payment_reference": "pay-ref-1",
        },
    )
    purchases_response = client.get(f"/api/clubs/{club_id}/purchases")

    assert purchase_response.status_code == 201
    assert purchases_response.status_code == 200
    purchase = purchase_response.json()
    assert purchase["purchase_ref"].startswith("club-purchase-")
    assert purchase["metadata_json"]["sku"] == items[0]["sku"]
    assert purchases_response.json()["purchases"][0]["payment_reference"] == "pay-ref-1"
