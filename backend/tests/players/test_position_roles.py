from app.owner_console.engine import normalize_position
from app.players.position_roles import display_codes, resolve_positions


def test_estevao_willian_plays_on_the_right_and_through_the_middle():
    primary, extras, reason = resolve_positions(
        name="Estêvão Willian",
        position="Winger",
        normalized_position="LW",
        profile_primary="Winger",
    )
    assert reason == "named"
    assert primary == "RW"
    assert extras == ["AM", "ST", "RM"]
    assert display_codes(primary, extras) == "RW / AM / ST / RM"

    filed, filed_extras, filed_reason = resolve_positions(
        name="Estêvão",
        position="RW / AM / ST / RM",
        normalized_position="rw",
    )
    assert filed_reason == "unchanged"
    assert display_codes(filed, filed_extras) == "RW / AM / ST / RM"

    other, other_extras, other_reason = resolve_positions(
        name="Estevão Barreto",
        position="AM / LW / RW / ST",
    )
    assert other_reason == "unchanged"
    assert other == "AM"
    assert other_extras == ["LW", "RW", "ST"]


def test_musiala_and_monga_are_not_defenders():
    musiala = resolve_positions(
        name="Jamal Musiala",
        position="DF",
        normalized_position="DF",
        secondaries=["Central Midfielder"],
        profile_primary="Attacking Midfielder",
        profile_secondaries=["Central Midfielder"],
    )
    assert musiala[0] == "AM"
    assert musiala[1] == ["LW", "LM", "CM"]
    assert display_codes(musiala[0], musiala[1]) == "AM / LW / LM / CM"

    monga = resolve_positions(
        name="Jeremy Monga",
        position="D/WB R",
        normalized_position="RB",
        secondaries=["RW"],
    )
    assert monga[0] == "LW"
    assert monga[1] == ["LM", "ST"]
    assert display_codes(monga[0], monga[1]) == "LW / LM / ST"


def test_szoboszlai_is_not_a_wing_back():
    primary, extras, reason = resolve_positions(
        name="Dominik Szoboszlai",
        position="WB R",
        normalized_position="WB R",
    )
    assert reason == "named"
    assert primary == "AM"
    assert extras == ["CM", "RW"]
    assert display_codes(primary, extras) == "AM / CM / RW"


def test_bruno_fernandes_is_an_attacking_midfielder():
    primary, extras, reason = resolve_positions(
        name="Bruno Fernandes",
        position="FW",
        normalized_position="FW",
    )
    assert reason == "named"
    assert display_codes(primary, extras) == "AM / CM"


def test_berisha_and_chiesa_are_wingers():
    berisha, berisha_extras, berisha_reason = resolve_positions(
        name="Bernard Berisha",
        position="CB",
        normalized_position="cb",
    )
    assert berisha_reason == "named"
    assert display_codes(berisha, berisha_extras) == "LW / LM"

    chiesa, chiesa_extras, chiesa_reason = resolve_positions(
        name="Federico Chiesa",
        position="WB L",
        normalized_position="WB L",
    )
    assert chiesa_reason == "named"
    assert display_codes(chiesa, chiesa_extras) == "RW / LW / ST"


def test_wing_back_code_is_not_a_centre_back():
    primary, extras, reason = resolve_positions(name="A Left Wing Back", position="D/WB L")
    assert reason == "unchanged"
    assert display_codes(primary, extras) == "LB / LWB"

    attack, attack_extras, attack_reason = resolve_positions(name="An Attacking Mid", position="AM RLC")
    assert attack_reason == "unchanged"
    assert display_codes(attack, attack_extras) == "AM / LW / RW"


def test_coarse_defender_bucket_loses_to_a_specific_profile():
    primary, extras, reason = resolve_positions(
        name="A Coarse Defender",
        position="DF",
        normalized_position="DF",
        profile_primary="Winger",
        profile_secondaries=[],
    )
    assert reason == "profile"
    assert primary == "LW"
    assert "RW" in extras


def test_generic_central_midfielder_does_not_move_a_coarse_bucket():
    primary, extras, reason = resolve_positions(
        name="Jesper Lindstrøm",
        position="DF",
        normalized_position="DF",
        profile_primary="Central Midfielder",
        profile_secondaries=["Central Midfielder"],
    )
    assert reason == "unchanged"
    assert primary == "CB"
    assert extras == []


def test_full_back_profile_does_not_inherit_a_generic_midfield_secondary():
    primary, extras, reason = resolve_positions(
        name="Hamari Traoré",
        position="DF",
        normalized_position="DF",
        profile_primary="Full-Back",
        profile_secondaries=["Central Midfielder"],
    )
    assert reason == "profile"
    assert primary == "FB"
    assert extras == []


def test_specific_normalized_code_wins_when_the_position_string_is_the_other_line():
    primary, extras, reason = resolve_positions(
        name="Bernardo Silva",
        position="D L",
        normalized_position="CM",
        secondaries=["CM", "RW"],
    )
    assert reason == "normalized"
    assert primary == "CM"
    assert extras == []


def test_goalkeeper_label_is_not_replaced_by_a_contradictory_code():
    primary, _extras, reason = resolve_positions(
        name="Omar Mohamed Salah Mohamed",
        position="Goalkeeper",
        normalized_position="RW",
    )
    assert reason == "unchanged"
    assert primary == "GK"


def test_specific_defender_is_left_alone():
    primary, extras, reason = resolve_positions(
        name="Bram Nuytinck",
        position="D C",
        normalized_position="D C",
    )
    assert reason == "unchanged"
    assert primary == "CB"
    assert extras == []


def test_attacking_midfielder_is_not_a_forward_or_defender():
    assert normalize_position("Attacking Midfielder") == "midfielder"
    assert normalize_position("AM / LW / LM / CM") == "midfielder"
    assert normalize_position("LW / LM / ST") == "forward"
    assert normalize_position("D/WB R") == "defender"
    assert normalize_position("Wing-Back") == "defender"
    assert normalize_position("DF") == "defender"
    assert normalize_position("") == "midfielder"
