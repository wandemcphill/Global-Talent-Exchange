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


def trader_signup_payload(
    *,
    email: str,
    trading_alias: str,
    full_name: str = "Trader User",
    password: str = TEST_PASSWORD,
    country: str = "NG",
    totp_secret: str = "JBSWY3DPEHPK3PXP",
    totp_code: str,
) -> dict[str, object]:
    trader_token = trading_alias.replace("_", "-")[:32] or "trader"
    return {
        "full_name": full_name,
        "trading_alias": trading_alias,
        "email": email,
        "password": password,
        "phone_number": "08000000000",
        "country": country,
        "preferred_currency": "coin",
        "trading_experience": "intermediate",
        "interests": ["p2p", "escrow"],
        "wallet_label": "GTEX Trading Wallet",
        "totp_secret": totp_secret,
        "recovery_phrase_hash": f"recovery-hash-{trader_token}",
        "security_pin_hash": f"security-pin-hash-{trader_token}",
        "totp_code": totp_code,
        "compliance": {
            "government_id_attachment_id": f"gov-{trader_token}",
            "selfie_attachment_id": f"selfie-{trader_token}",
            "proof_of_address_attachment_id": f"address-{trader_token}",
            "country_confirmation": country,
        },
    }
