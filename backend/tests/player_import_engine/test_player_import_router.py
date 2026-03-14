from __future__ import annotations

from backend.app.models.club_profile import ClubProfile
from backend.app.models.user import User


def _ensure_club(session, owner: User) -> ClubProfile:
    club = session.query(ClubProfile).filter_by(owner_user_id=owner.id).first()
    if club is None:
        club = ClubProfile(
            owner_user_id=owner.id,
            club_name=f"{owner.username.title()} United",
            short_name=owner.username[:4].upper(),
            slug=f"{owner.username}-united",
            primary_color="#123456",
            secondary_color="#FFFFFF",
            accent_color="#00FF99",
            home_venue_name=f"{owner.username.title()} Arena",
        )
        session.add(club)
        session.commit()
        session.refresh(club)
    return club


def test_admin_can_import_players_and_generate_youth(client, app_session_factory, demo_seed, demo_auth_headers):
    with app_session_factory() as session:
        owner = session.get(User, demo_seed.demo_users[0].user_id)
        club = _ensure_club(session, owner)

    admin_login = client.post('/auth/login', json={'email': 'vidvimedialtd@gmail.com', 'password': 'NewPass1234!'})
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {'Authorization': f"Bearer {admin_login.json()['access_token']}"}

    create_job = client.post(
        '/admin/player-import/jobs',
        headers=admin_headers,
        json={
            'source_type': 'csv',
            'source_label': 'manual upload',
            'commit': True,
            'rows': [
                {
                    'external_source_id': 'manual-001',
                    'full_name': 'Ayo Balogun',
                    'position': 'ST',
                    'nationality_code': 'NG',
                    'age': 19,
                    'club_id': club.id,
                    'market_value_eur': 120000,
                },
                {
                    'external_source_id': 'manual-002',
                    'full_name': 'Seyi Mensah',
                    'position': 'CM',
                    'nationality_code': 'GH',
                    'age': 18,
                    'club_id': club.id,
                    'market_value_eur': 95000,
                },
            ],
        },
    )
    assert create_job.status_code == 201, create_job.text
    job = create_job.json()
    assert job['total_items'] == 2
    assert job['imported_items'] == 2
    assert all(item['status'] == 'imported' for item in job['items'])

    youth = client.post('/admin/player-import/youth/generate', headers=admin_headers, json={'club_id': club.id, 'count': 5, 'nationality_code': 'NG', 'region_label': 'Lagos Cluster'})
    assert youth.status_code == 200, youth.text
    body = youth.json()
    assert len(body['generated_prospects']) == 5
    assert body['job']['imported_items'] == 5

    prospects = client.get('/player-import/youth-prospects/me', headers=demo_auth_headers)
    assert prospects.status_code == 200, prospects.text
    assert len(prospects.json()) >= 5
