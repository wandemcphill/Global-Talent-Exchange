from __future__ import annotations

from pathlib import Path

from app.models.player_token_market import PlayerShareMarket


ROOT = Path(__file__).resolve().parents[2]


def test_player_share_market_exposes_nullable_released_supply_for_legacy_compatibility() -> None:
    assert "released_shares" in PlayerShareMarket.__table__.c
    assert PlayerShareMarket.__table__.c.released_shares.nullable is True


def test_primary_available_supply_distinguishes_released_from_lifetime_supply() -> None:
    market = PlayerShareMarket(
        player_id="player-1",
        total_shares=1000,
        released_shares=100,
        circulating_shares=35,
        share_price_coin="1.0000",
        status="active",
    )
    assert market.primary_available_shares == 65


def test_legacy_market_has_unknown_released_supply_instead_of_invented_history() -> None:
    market = PlayerShareMarket(
        player_id="player-legacy",
        total_shares=1000,
        circulating_shares=250,
        share_price_coin="1.0000",
        status="active",
    )
    assert market.released_shares is None
    assert market.primary_available_shares is None


def test_strict_issuer_seeds_initial_release_from_existing_launch_cap() -> None:
    source = (ROOT / "scripts" / "issue_player_share_markets_strict.py").read_text(encoding="utf-8")
    assert "market.released_shares = int(plan.initial_circulating_cap)" in source
    assert '"initial_released_shares": plan.initial_circulating_cap' in source


def test_release_script_is_dry_run_by_default_and_admin_attributed() -> None:
    source = (ROOT / "scripts" / "release_player_share_supply.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--actor-user-id", required=True)' in source
    assert 'parser.add_argument("--activate", action="store_true"' in source
    assert "service.release_shares" in source
