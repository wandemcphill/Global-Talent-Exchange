from __future__ import annotations


def _login(client, email: str, password: str) -> dict[str, str]:
    response = client.post('/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200, response.text
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_send_gift_and_summary_flow(client, demo_seed) -> None:
    sender = demo_seed.demo_users[0]
    recipient = demo_seed.demo_users[1]
    sender_headers = _login(client, sender.email, sender.password)

    response = client.post(
        '/gift-engine/send',
        headers=sender_headers,
        json={
            'recipient_user_id': recipient.user_id,
            'gift_key': 'cheer-burst',
            'quantity': '2.0000',
            'note': 'For the knockout drama',
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['gift_key'] == 'cheer-burst'
    assert payload['gross_amount'] == '50.0000'
    assert payload['platform_rake_amount'] == '15.0000'
    assert payload['recipient_net_amount'] == '35.0000'

    sender_summary = client.get('/gift-engine/me/summary', headers=sender_headers)
    assert sender_summary.status_code == 200, sender_summary.text
    assert sender_summary.json()['sent_total'] == '50.0000'
    assert sender_summary.json()['rake_total'] == '15.0000'

    recipient_headers = _login(client, recipient.email, recipient.password)
    recipient_summary = client.get('/gift-engine/me/summary', headers=recipient_headers)
    assert recipient_summary.status_code == 200, recipient_summary.text
    assert recipient_summary.json()['received_total'] == '35.0000'


def test_send_gift_rejects_self_send(client, demo_seed) -> None:
    sender = demo_seed.demo_users[0]
    sender_headers = _login(client, sender.email, sender.password)
    response = client.post(
        '/gift-engine/send',
        headers=sender_headers,
        json={
            'recipient_user_id': sender.user_id,
            'gift_key': 'cheer-burst',
            'quantity': '1.0000',
        },
    )
    assert response.status_code == 400
    assert 'cannot send gifts to themselves' in response.text.lower()
