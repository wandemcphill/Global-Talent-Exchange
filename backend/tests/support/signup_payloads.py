from __future__ import annotations

from backend.tests.support.secrets import TEST_PASSWORD


def user_signup_payload(
    *,
    email: str,
    username: str | None = None,
    full_name: str = "Test User",
    password: str = TEST_PASSWORD,
    country: str = "NG",
) -> dict[str, object]:
    resolved_username = username or email.split("@", maxsplit=1)[0].replace("-", "_").replace(".", "_")
    club_token = resolved_username.replace("_", "-")[:32] or "test"
    return {
        "email": email,
        "username": resolved_username,
        "password": password,
        "full_name": full_name,
        "country": country,
        "state": "Test State",
        "city": "Test City",
        "club_name": f"{full_name} Sporting",
        "club_short_tag": club_token[:8].upper(),
        "club_country": country,
        "club_state": "Test State",
        "club_locality": "Test City",
        "club_type": "community",
        "football_identity": "club_owner",
        "compliance": {
            "government_id_attachment_id": f"gov-{club_token}",
            "selfie_attachment_id": f"selfie-{club_token}",
            "country_confirmation": country,
        },
    }


def creator_signup_payload(
    *,
    email: str,
    username: str,
    creator_name: str = "Creator User",
    password: str = TEST_PASSWORD,
    country: str = "US",
) -> dict[str, object]:
    return {
        "creator_name": creator_name,
        "username": username,
        "email": email,
        "password": password,
        "country": country,
        "category": "football_news",
        "main_club_supported": "GTEX FC",
        "primary_language": "English",
        "monetization": ["donations", "fan_coin_revenue"],
    }
