from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.owner_console import staff
from app.owner_console.models import OwnerClubState, OwnerInboxItem
from app.owner_console.service import OwnerError
from app.owner_console.staff_models import OwnerClubStaff


def _state(day: int = 14) -> OwnerClubState:
    return OwnerClubState(club_id="c1", owner_user_id="u1", club_name="Lagos Lions", stage="active", world_day=day, facilities_json={"academy": 2})


def test_continent_is_game_logic_lookup():
    assert staff.continent_for("ng") == "africa"
    assert staff.continent_for("BR") == "south_america"
    assert staff.continent_for(None) == "africa"


def test_salary_scales_with_quality_inside_range():
    assert staff.salary_for(1) == Decimal("300.00")
    assert staff.salary_for(20) == Decimal("3000.00")
    assert Decimal("300") < staff.salary_for(10) < Decimal("3000")


def test_candidates_are_deterministic_per_week_and_within_bounds():
    a = staff.candidates(_state(), "gm", "NG")
    assert a == staff.candidates(_state(15), "gm", "NG")
    assert len(a) == 3 and all(6 <= c["quality"] <= 18 for c in a)
    assert set(a[0]["attributes"]) == {"negotiation", "scouting", "financial_discipline", "judgement"}
    assert a[0]["personality"]["network"] == "africa"


def test_reserved_tasks_cannot_be_delegated():
    assert set(staff.RESERVED) == {"player_sale_above_threshold", "manager_hire_fire", "capital_move"}
    assert not set(staff.RESERVED) & set(staff.TASKS)


def test_set_policy_rejects_reserved_task(monkeypatch):
    monkeypatch.setattr(staff, "_owned", lambda *a: _state())
    with pytest.raises(OwnerError):
        staff.set_policy(None, "u1", "c1", "capital_move", "auto", Decimal("1"))


def test_public_showroom_hides_finances_and_players(monkeypatch):
    full = {k: k for k in staff.PUBLIC_SHOWROOM_KEYS} | {"facilities": {}, "sponsors": [], "top_players": [], "fans": 1, "prestige": 2}
    monkeypatch.setattr(staff, "showroom", lambda session, club_id: full)
    out = staff.public_showroom(None, "c1")
    assert set(out) == set(staff.PUBLIC_SHOWROOM_KEYS)
    assert not {"facilities", "sponsors", "top_players", "fans", "prestige"} & set(out)


def test_cost_reads_bid_and_budget():
    bid = OwnerInboxItem(kind="transfer_bid", payload_json={"bid": 12400}, actions_json=[], user_id="u1", sender="s", title="t", what="w", why="y", is_decision=True)
    assert staff._cost(bid, "transfer_bid") == Decimal("12400.00")
    req = OwnerInboxItem(kind="manager_request", payload_json={"budget": 4000}, actions_json=[], user_id="u1", sender="s", title="t", what="w", why="y", is_decision=True)
    assert staff._cost(req, "small_signing") == Decimal("4000.00")


def test_better_gm_has_lower_acceptance_bar():
    class S:
        def __init__(self, value):
            self.value = value

        def get(self, *_):
            return type("P", (), {"value_coin": self.value})()

    item = OwnerInboxItem(kind="transfer_bid", payload_json={"bid": 11000, "player_id": "p"}, actions_json=[], user_id="u1", sender="s", title="t", what="w", why="y", is_decision=True)
    elite = OwnerClubStaff(role="gm", name="A", quality=20, salary_per_cycle=Decimal(1), club_id="c1", owner_user_id="u1", hired_at=datetime.now(timezone.utc))
    novice = OwnerClubStaff(role="gm", name="B", quality=4, salary_per_cycle=Decimal(1), club_id="c1", owner_user_id="u1", hired_at=datetime.now(timezone.utc))
    assert staff._judge(S(10000), elite, item, "transfer_bid")[0] == "accept"
    assert staff._judge(S(10000), novice, item, "transfer_bid")[0] == "reject"
