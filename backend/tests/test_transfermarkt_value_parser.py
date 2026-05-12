from __future__ import annotations

from backend.scripts.import_transfermarkt_real_players import _parse_market_value_eur


def test_parse_market_value_eur_handles_common_units() -> None:
    assert _parse_market_value_eur("\u20ac1.5m") == 1_500_000.0
    assert _parse_market_value_eur("\u20ac750k") == 750_000.0
    assert _parse_market_value_eur("EUR2bn") == 2_000_000_000.0
    assert _parse_market_value_eur("-") is None
