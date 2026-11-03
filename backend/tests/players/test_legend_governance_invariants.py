from unittest.mock import MagicMock

from app.players.gsi_service import resolve_player_gsi, CANONICAL_GSI_OVERRIDES
from app.players.token_market_defaults import resolve_player_share_market_config
from app.players.real_player_service import ARCHIVED_DUPLICATE_PLAYER_IDS


def test_top_four_pantheon_at_98_only():
    """Strict invariant: ONLY Pelé, Maradona, Cristiano Ronaldo, and Lionel Messi can have 98."""
    ninety_eights = [name for name, (cur, _) in CANONICAL_GSI_OVERRIDES.items() if cur == 98]
    allowed_names = {
        "pelé",
        "pele",
        "edson arantes do nascimento",
        "edson arantes do nascimento (pelé)",
        "diego maradona",
        "diego armando maradona",
        "cristiano ronaldo",
        "lionel messi",
    }
    for name in ninety_eights:
        assert name in allowed_names, f"Unexpected 98 rating for {name}"


def test_non_pantheon_legend_cannot_exceed_96():
    """Any other legend attempting to claim 98+ gets capped at 96."""
    mock_legend = MagicMock()
    mock_legend.real_player_tier = "legend"
    mock_legend.source_provider = "gtex_legend_prime"
    mock_legend.legendary_profile_id = "leg-1"
    mock_legend.full_name = "Some Other Legend"
    mock_legend.canonical_display_name = "Some Other Legend"
    mock_legend.governed_gsi = 98
    mock_legend.governed_potential_gsi = 98
    mock_legend.provider_external_id = None

    cur, pot = resolve_player_gsi(mock_legend)
    assert cur <= 96, f"Expected cur <= 96, got {cur}"
    assert pot <= 96, f"Expected pot <= 96, got {pot}"


def test_legend_floor_is_80_on_the_dot():
    """Strict invariant: Starting point for legends is 80 on the dot (no legend below 80)."""
    mock_legend = MagicMock()
    mock_legend.real_player_tier = "legend"
    mock_legend.source_provider = "gtex_legend_prime"
    mock_legend.legendary_profile_id = "leg-2"
    mock_legend.full_name = "Obscure Legend"
    mock_legend.canonical_display_name = "Obscure Legend"
    mock_legend.governed_gsi = 72
    mock_legend.governed_potential_gsi = 72
    mock_legend.provider_external_id = None

    cur, pot = resolve_player_gsi(mock_legend)
    assert cur >= 80, f"Expected cur >= 80, got {cur}"
    assert pot >= 80, f"Expected pot >= 80, got {pot}"


def test_legend_market_is_one_of_one():
    """All legends have normalized_total_shares = 1."""
    mock_legend = MagicMock()
    mock_legend.id = "legend-player-id"
    mock_legend.full_name = "Zinedine Zidane"
    mock_legend.name = "Zinedine Zidane"
    mock_legend.real_player_tier = "legend"
    mock_legend.source_provider = "gtex_legend_prime"
    mock_legend.is_real_player = True
    mock_legend.legendary_profile_id = "lpp-123"

    cfg = resolve_player_share_market_config(mock_legend, total_shares=200)
    assert cfg.total_shares == 1, f"Expected 1 total share for legend, got {cfg.total_shares}"


def test_active_superstars_are_not_legends_and_have_200_shares():
    """Active players such as Harry Kane, Mbappé, Bellingham, Vinícius have 200 shares."""
    mock_kane = MagicMock()
    mock_kane.id = "50235403-679f-48c8-88a0-7614e76ccc0e"
    mock_kane.full_name = "Harry Kane"
    mock_kane.name = "Harry Kane"
    mock_kane.real_player_tier = "marquee"
    mock_kane.source_provider = "sportmonks"
    mock_kane.is_real_player = True
    mock_kane.legendary_profile_id = None

    cfg = resolve_player_share_market_config(mock_kane, total_shares=200)
    assert cfg.total_shares == 200, f"Expected 200 shares for Kane, got {cfg.total_shares}"


def test_archived_duplicates_list():
    """Verify specific retired duplicate IDs are recorded."""
    assert "106bbc0a-a8b3-408e-b856-a4dad15799fd" in ARCHIVED_DUPLICATE_PLAYER_IDS
    assert "55f70b9b-dae9-4a55-8721-ccf9bdaa0154" in ARCHIVED_DUPLICATE_PLAYER_IDS
    assert "0704b985-6e51-49fc-bf74-45820da69183" in ARCHIVED_DUPLICATE_PLAYER_IDS
    assert "862d907b-917a-4508-a19d-da3481ae778d" in ARCHIVED_DUPLICATE_PLAYER_IDS
