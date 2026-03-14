from __future__ import annotations

from backend.app.models.club_profile import ClubProfile
from backend.app.models.user import User


def _ensure_club(session, owner: User) -> ClubProfile:
    club = session.query(ClubProfile).filter_by(owner_user_id=owner.id).first()
    if club is None:
        club = ClubProfile(
            owner_user_id=owner.id,
            club_name=f"{owner.username.title()} FC",
            short_name=owner.username[:4].upper(),
            slug=f"{owner.username}-fc",
            primary_color="#112233",
            secondary_color="#FFFFFF",
            accent_color="#FFD700",
            home_venue_name=f"{owner.username.title()} Park",
        )
        session.add(club)
        session.commit()
        session.refresh(club)
    return club


def test_club_infra_seed_and_support_flow(client, app_session_factory, demo_seed, demo_auth_headers):
    with app_session_factory() as session:
        owner = session.get(User, demo_seed.demo_users[0].user_id)
        club = _ensure_club(session, owner)

    admin_login = client.post('/auth/login', json={'email': 'vidvimedialtd@gmail.com', 'password': 'NewPass1234!'})
    assert admin_login.status_code == 200, admin_login.text
    admin_headers = {'Authorization': f"Bearer {admin_login.json()['access_token']}"}

    seed = client.post('/admin/club-infra/seed', headers=admin_headers)
    assert seed.status_code == 200, seed.text
    assert seed.json()['seeded_clubs'] >= 1

    mine = client.get('/club-infra/my', headers=demo_auth_headers)
    assert mine.status_code == 200, mine.text
    body = mine.json()
    assert body['club_id'] == club.id
    assert body['stadium']['capacity'] >= 5000
    assert body['supporter_token']['metadata_json']['non_financial'] is True

    support = client.post(f'/club-infra/clubs/{club.id}/support', headers=demo_auth_headers, json={'quantity': 3})
    assert support.status_code == 200, support.text
    supported = support.json()['dashboard']
    assert supported['my_holding']['token_balance'] >= 3
    assert supported['supporter_token']['circulating_supply'] >= 3

    upgrade = client.post('/club-infra/my/stadium/upgrade', headers=demo_auth_headers, json={'target_level': 2})
    assert upgrade.status_code == 200, upgrade.text
    assert upgrade.json()['dashboard']['stadium']['level'] == 2
