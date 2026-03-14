from __future__ import annotations


def _login(client, email: str, password: str) -> dict[str, str]:
    response = client.post('/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200, response.text
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_user_can_create_report_and_admin_can_action_it(client, demo_seed, demo_auth_headers) -> None:
    reporter = demo_seed.demo_users[0]
    subject = demo_seed.demo_users[1]

    create_response = client.post(
        '/moderation/reports',
        headers=demo_auth_headers,
        json={
            'target_type': 'user',
            'target_id': subject.user_id,
            'subject_user_id': subject.user_id,
            'reason_code': 'fraud',
            'description': 'Suspicious trading and wallet behaviour kept repeating during league onboarding.',
        },
    )
    assert create_response.status_code == 201, create_response.text
    report = create_response.json()
    assert report['reporter_user_id'] == reporter.user_id
    assert report['subject_user_id'] == subject.user_id
    assert report['status'] == 'open'
    assert report['priority'] in {'high', 'critical'}

    my_reports = client.get('/moderation/me/reports', headers=demo_auth_headers)
    assert my_reports.status_code == 200
    assert any(item['id'] == report['id'] for item in my_reports.json())

    admin_headers = _login(client, 'vidvimedialtd@gmail.com', 'NewPass1234!')
    summary = client.get('/admin/moderation/reports/summary', headers=admin_headers)
    assert summary.status_code == 200
    assert summary.json()['open_count'] >= 1

    queue = client.get('/admin/moderation/reports?status=open', headers=admin_headers)
    assert queue.status_code == 200
    assert any(item['id'] == report['id'] for item in queue.json())

    assign_response = client.post(
        f"/admin/moderation/reports/{report['id']}/assign",
        headers=admin_headers,
        json={'priority': 'critical'},
    )
    assert assign_response.status_code == 200, assign_response.text
    assigned = assign_response.json()
    assert assigned['status'] == 'in_review'
    assert assigned['priority'] == 'critical'
    assert assigned['assigned_admin_user_id']

    resolve_response = client.post(
        f"/admin/moderation/reports/{report['id']}/resolve",
        headers=admin_headers,
        json={
            'resolution_action': 'wallet_review',
            'resolution_note': 'Escalated to treasury review and temporarily restricted risky cash-out surfaces.',
            'dismiss': False,
        },
    )
    assert resolve_response.status_code == 200, resolve_response.text
    resolved = resolve_response.json()
    assert resolved['status'] == 'actioned'
    assert resolved['resolution_action'] == 'wallet_review'
    assert resolved['resolved_by_user_id']


def test_duplicate_open_report_is_rejected(client, demo_seed, demo_auth_headers) -> None:
    subject = demo_seed.demo_users[2]
    payload = {
        'target_type': 'competition',
        'target_id': f'comp-{subject.user_id[:6]}',
        'reason_code': 'spam',
        'description': 'This competition keeps reposting spam invites into the same room.',
    }
    first = client.post('/moderation/reports', headers=demo_auth_headers, json=payload)
    assert first.status_code == 201, first.text

    duplicate = client.post('/moderation/reports', headers=demo_auth_headers, json=payload)
    assert duplicate.status_code == 400
    assert 'already exists' in duplicate.json()['detail']
