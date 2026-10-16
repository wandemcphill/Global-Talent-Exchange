from __future__ import annotations


def test_media_engine_view_purchase_and_snapshot(client, demo_auth_headers):
    view = client.post('/media-engine/views', headers=demo_auth_headers, json={'match_key': 'friendly-001', 'competition_key': 'friendly-cup', 'watch_seconds': 180})
    assert view.status_code == 201, view.text
    assert view.json()['match_key'] == 'friendly-001'

    purchase = client.post('/media-engine/purchases', headers=demo_auth_headers, json={'match_key': 'friendly-001', 'competition_key': 'friendly-cup'})
    assert purchase.status_code == 201, purchase.text
    assert purchase.json()['price_coin']

    snapshot = client.get('/media-engine/matches/friendly-001/snapshot', headers=demo_auth_headers)
    assert snapshot.status_code == 200, snapshot.text
    body = snapshot.json()
    assert body['total_views'] >= 1
    assert body['premium_purchases'] >= 1
    assert body['home_club_share_coin'] <= body['total_revenue_coin']
