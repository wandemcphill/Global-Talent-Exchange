from app.players.acquisition_pricing import acquisition_price
from app.players.position_roles import display_codes, resolve_positions


def test_prime_centre_back_costs_more_than_a_striker_leaving_his_prime() -> None:
    striker = acquisition_price(88, 88, age=30, position="ST", tier="established")
    centre_back = acquisition_price(88, 88, age=30, position="CB", tier="established")
    assert centre_back > striker * 1.08


def test_young_winger_with_a_ceiling_costs_more_than_the_same_rating_at_its_peak() -> None:
    # Rodri is a 30-year-old midfielder at his peak. Yamal is the same rating with years left.
    rodri = acquisition_price(91, 91, age=30.4, position="DM", tier="marquee")
    yamal = acquisition_price(91, 96, age=18.4, position="RW", tier="marquee")
    assert yamal > rodri * 1.12


def test_cole_palmer_is_not_priced_like_a_legend() -> None:
    palmer = acquisition_price(87, 92, age=24.5, position="AM", tier="marquee")
    yamal = acquisition_price(91, 96, age=18.4, position="RW", tier="marquee")
    cubarsi = acquisition_price(86, 94, age=18.8, position="CB", tier="wonderkid")
    rodri = acquisition_price(91, 91, age=30.4, position="DM", tier="marquee")
    assert palmer < 400
    assert yamal > palmer
    assert rodri > palmer
    assert cubarsi < rodri


def test_a_lower_rating_in_its_prime_does_not_cost_more_than_a_better_one() -> None:
    ordinary = acquisition_price(84, 84, age=27, position="CM", tier="established")
    palmer = acquisition_price(87, 92, age=24.5, position="AM", tier="marquee")
    assert ordinary < palmer


def test_fame_raises_the_price_without_jumping_a_clear_rating_gap() -> None:
    famous = acquisition_price(87, 87, age=26, position="AM", tier="marquee")
    unknown = acquisition_price(87, 87, age=26, position="AM", tier="watchlist")
    better = acquisition_price(91, 91, age=26, position="AM", tier="watchlist")
    assert famous > unknown
    assert better > famous


def test_legends_stay_at_their_prime_price() -> None:
    prime = acquisition_price(90, 90, age=27, position="ST", tier="legend", is_legend=True)
    older = acquisition_price(90, 90, age=40, position="ST", tier="legend", is_legend=True)
    assert prime == older == 900.0


def test_tunde_akinsola_plays_on_the_right_and_across_the_attack() -> None:
    primary, extras, reason = resolve_positions(
        name="Tunde Akinsola",
        position="Left Winger",
        normalized_position="lw",
    )
    assert reason == "named"
    assert primary == "RW"
    assert extras == ["RM", "AM", "ST", "LM", "LW"]
    assert display_codes(primary, extras) == "RW / RM / AM / ST / LM / LW"


def test_camoranesi_and_guti_positions() -> None:
    camoranesi, camoranesi_extras, camoranesi_reason = resolve_positions(
        name="Mauro Camoranesi",
        position="RW",
        normalized_position="rw",
    )
    assert camoranesi_reason == "named"
    assert camoranesi == "LM"
    assert camoranesi_extras == ["LW", "RM", "CM", "AM", "ST"]
    assert display_codes(camoranesi, camoranesi_extras) == "LM / LW / RM / CM / AM / ST"

    guti, guti_extras, guti_reason = resolve_positions(
        name="José María Gutiérrez Hernández",
        position="AM",
        normalized_position="am",
    )
    assert guti_reason == "named"
    assert guti == "DM"
    assert guti_extras == ["CM", "AM"]
    assert display_codes(guti, guti_extras) == "DM / CM / AM"

    other_guti, other_extras, other_reason = resolve_positions(
        name="Guti",
        position="CB",
        normalized_position="cb",
    )
    assert other_reason == "unchanged"
    assert other_guti == "CB"
    assert other_extras == []


def test_cole_palmer_also_plays_wide_and_as_a_striker() -> None:
    primary, extras, reason = resolve_positions(
        name="Cole Jermaine Palmer",
        position="AM",
        normalized_position="am",
    )
    assert reason == "named"
    assert primary == "AM"
    assert extras == ["RW", "RM", "ST"]
    assert display_codes(primary, extras) == "AM / RW / RM / ST"
