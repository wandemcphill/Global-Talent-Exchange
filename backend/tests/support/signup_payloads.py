from __future__ import annotations

from backend.tests.support.secrets import TEST_PASSWORD


def player_signup_payload(
    *,
    email: str,
    username: str | None = None,
    full_name: str = "Test User",
    password: str = TEST_PASSWORD,
    country: str = "NG",
) -> dict[str, object]:
    del username
    return {
        "full_name": full_name,
        "email": email,
        "password": password,
        "country": country,
        "preferred_position": "Forward",
        "date_of_birth": "2006-05-12",
        "pin": "2718",
        "recovery_questions": [
            {
                "question": "Which academy did I first train with?",
                "answer": "Surulere Stars",
            },
            {
                "question": "What nickname did my first coach call me?",
                "answer": "Flash",
            },
        ],
    }
