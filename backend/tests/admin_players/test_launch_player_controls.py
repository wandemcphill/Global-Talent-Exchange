from datetime import date

from app.admin_engine.service import DEFAULT_FEATURE_FLAGS
from app.admin_players.service import calendar_age, dob_for_game_age


def test_match_3d_gameplay_stays_off_in_the_public_seed() -> None:
    seed = next(item for item in DEFAULT_FEATURE_FLAGS if item["feature_key"] == "match_3d_gameplay")
    assert seed["enabled"] is False
    assert seed["launch_state"] == "public"


def test_admin_age_edit_stores_a_game_birthday() -> None:
    today = date(2026, 11, 12)
    born = dob_for_game_age(24, today=today, existing=date(1991, 6, 28))
    assert calendar_age(born, today) == 24
    assert born.month == 6
    assert born.day == 28
