from __future__ import annotations


def _login(client, email: str, password: str) -> dict[str, str]:
    response = client.post('/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200, response.text
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_admin_can_settle_reward_and_user_can_view_summary(client, demo_seed) -> None:
    recipient = demo_seed.demo_users[0]
    admin_headers = _login(client, 'vidvimedialtd@gmail.com', 'NewPass1234!')

    response = client.post(
        '/admin/reward-engine/settlements',
        headers=admin_headers,
        json={
            'user_id': recipient.user_id,
            'competition_key': 'gtex-world-cup-2026',
            'title': 'World Cup Semi-Final Bonus',
            'gross_amount': '250.0000',
            'reward_source': 'gtex_promotional_pool',
            'note': 'Semi-final appearance and viewership bonus',
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['gross_amount'] == '250.0000'
    assert payload['platform_fee_amount'] == '25.0000'
    assert payload['net_amount'] == '225.0000'

    user_headers = _login(client, recipient.email, recipient.password)
    settlements = client.get('/reward-engine/me/settlements', headers=user_headers)
    assert settlements.status_code == 200, settlements.text
    assert settlements.json()[0]['competition_key'] == 'gtex-world-cup-2026'

    summary = client.get('/reward-engine/me/summary', headers=user_headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()['total_rewards'] == '225.0000'
    assert summary.json()['total_platform_fee'] == '25.0000'
